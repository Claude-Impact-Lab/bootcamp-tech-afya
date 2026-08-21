"""Consulta de CRM no formulário público do CFM usando um navegador real.

O portal executa a pesquisa por JavaScript e pode solicitar reCAPTCHA. A
automação usa o fluxo normal da página e nunca tenta resolver ou contornar o
CAPTCHA. Quando a consulta não pode ser concluída, o cadastro fica pendente.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import os
from time import monotonic
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


CFM_SEARCH_URL = "https://portal.cfm.org.br/busca-medicos"
CFM_API_PATH = "/api_rest_php/api/v2/medicos/buscar_medicos"


class CfmLookupStatus(StrEnum):
    FOUND = "VALIDATED"
    NOT_FOUND = "NOT_FOUND"
    UNAVAILABLE = "VALIDATION_PENDING"


@dataclass(frozen=True)
class CfmLookup:
    status: CfmLookupStatus
    name: str | None = None


def crm_for_cfm(crm: str, uf: str) -> str:
    """Devolve o número que deve ser digitado/comparado no portal.

    No RJ, o portal mostra o prefixo fixo ``52`` fora do input. Por isso ele é
    removido quando já veio junto do CRM informado na aplicação.
    """
    digits = "".join(char for char in str(crm) if char.isdigit())
    if uf.strip().upper() == "RJ" and digits.startswith("52"):
        digits = digits[2:]
    return digits.lstrip("0") or "0"


def _first_value(record: dict[str, Any], *keys: str) -> Any:
    lowered = {str(key).lower(): value for key, value in record.items()}
    return next((lowered[key.lower()] for key in keys if key.lower() in lowered), None)


def _extract_records(payload: Any) -> list[dict[str, Any]] | None:
    """Extrai a lista de médicos sem acoplar o domínio ao envelope da API."""
    root = payload
    if isinstance(root, list) and len(root) == 1 and isinstance(root[0], dict):
        root = root[0]

    if isinstance(root, dict):
        data = _first_value(root, "dados", "data", "medicos", "results", "items")
    else:
        data = root

    if isinstance(data, dict):
        data = _first_value(data, "medicos", "results", "items", "data", "dados")
    if not isinstance(data, list):
        return None
    return [item for item in data if isinstance(item, dict)]


def parse_cfm_response(payload: Any, crm: str, uf: str) -> CfmLookup:
    """Compara exatamente UF e CRM na resposta produzida pelo próprio portal."""
    records = _extract_records(payload)
    if records is None:
        return CfmLookup(CfmLookupStatus.UNAVAILABLE)

    requested_uf = uf.strip().upper()
    requested_crm = crm_for_cfm(crm, requested_uf)

    for record in records:
        found_uf = str(_first_value(record, "SG_UF", "uf", "ufMedico") or "").strip().upper()
        found_crm = _first_value(record, "NU_CRM", "crm", "crmMedico")
        if found_uf != requested_uf or found_crm is None:
            continue
        if crm_for_cfm(str(found_crm), found_uf) == requested_crm:
            name = _first_value(record, "NM_MEDICO", "nome", "nomeMedico")
            return CfmLookup(CfmLookupStatus.FOUND, str(name).strip() if name else None)

    # Uma resposta válida, mesmo vazia ou com outro CRM, é um resultado negativo.
    return CfmLookup(CfmLookupStatus.NOT_FOUND)


CancellationCheck = Callable[[], bool]
BrowserLookup = Callable[[str, str, bool, float, bool, CancellationCheck], CfmLookup]


class CfmClient:
    """Automatiza o formulário do CFM e captura a resposta AJAX da pesquisa.

    Modos aceitos em ``CFM_BROWSER_MODE``:
    - ``background`` (padrão): usa Chromium normal fora da área visível e só
      mostra a janela se houver desafio de reCAPTCHA;
    - ``headless_then_headed``: tenta headless antes do modo em segundo plano;
    - ``headless``: nunca abre janela;
    - ``headed``: mostra a janela desde o início.
    """

    def __init__(
        self,
        *,
        timeout: float = 12.0,
        interactive_timeout: float = 55.0,
        mode: str | None = None,
        browser_lookup: BrowserLookup | None = None,
        cancelled: CancellationCheck | None = None,
    ):
        self.timeout = timeout
        self.interactive_timeout = interactive_timeout
        self.mode = (mode or os.getenv("CFM_BROWSER_MODE", "background")).lower()
        self._browser_lookup = browser_lookup or self._find_with_browser
        self._cancelled = cancelled or (lambda: False)

    def find_doctor(self, crm: str, uf: str) -> CfmLookup:
        attempts = {
            "headless": [(True, self.timeout, False)],
            "background": [(False, self.interactive_timeout, False)],
            "headed": [(False, self.interactive_timeout, True)],
            "headless_then_headed": [
                (True, self.timeout, False),
                (False, self.interactive_timeout, False),
            ],
        }.get(self.mode, [(False, self.interactive_timeout, False)])

        for headless, timeout, show_on_start in attempts:
            if self._cancelled():
                return CfmLookup(CfmLookupStatus.UNAVAILABLE)
            result = self._browser_lookup(
                crm_for_cfm(crm, uf),
                uf.strip().upper(),
                headless,
                timeout,
                show_on_start,
                self._cancelled,
            )
            if result.status is not CfmLookupStatus.UNAVAILABLE:
                return result
        return CfmLookup(CfmLookupStatus.UNAVAILABLE)

    @staticmethod
    def _find_with_browser(
        crm: str,
        uf: str,
        headless: bool,
        timeout: float,
        show_on_start: bool,
        cancelled: CancellationCheck,
    ) -> CfmLookup:
        deadline = monotonic() + timeout

        def remaining_ms(limit: int | None = None) -> int:
            remaining = max(1, int((deadline - monotonic()) * 1000))
            return min(remaining, limit) if limit else remaining

        try:
            with sync_playwright() as playwright:
                launch_args = [] if headless or show_on_start else ["--window-position=-32000,-32000"]
                browser = playwright.chromium.launch(
                    headless=headless,
                    args=launch_args,
                    timeout=remaining_ms(15_000),
                )
                try:
                    if cancelled():
                        return CfmLookup(CfmLookupStatus.UNAVAILABLE)
                    context = browser.new_context(
                        locale="pt-BR",
                        timezone_id="America/Sao_Paulo",
                        viewport={"width": 1280, "height": 900},
                    )
                    page = context.new_page()
                    cdp = context.new_cdp_session(page) if not headless else None
                    window_id = None
                    if cdp:
                        window_id = cdp.send("Browser.getWindowForTarget")["windowId"]

                    page.goto(CFM_SEARCH_URL, wait_until="domcontentloaded", timeout=remaining_ms(15_000))
                    if cancelled():
                        return CfmLookup(CfmLookupStatus.UNAVAILABLE)
                    page.locator("#uf").wait_for(state="visible", timeout=remaining_ms(15_000))
                    page.locator("#uf").select_option(label=uf)
                    page.locator("#crm").fill(crm)

                    # Aguarda os scripts que registram o submit e chamam o
                    # reCAPTCHA invisível. O clique continua sendo o da página.
                    page.wait_for_function(
                        "typeof window.jQuery !== 'undefined' && "
                        "typeof window.getInfo === 'function'",
                        timeout=remaining_ms(15_000),
                    )
                    if cancelled():
                        return CfmLookup(CfmLookupStatus.UNAVAILABLE)
                    if show_on_start:
                        page.bring_to_front()

                    responses = []
                    page.on(
                        "response",
                        lambda response: responses.append(response)
                        if CFM_API_PATH in response.url
                        else None,
                    )
                    page.locator("button.btnPesquisar").click()

                    captcha_revealed = show_on_start
                    challenge_selectors = (
                        "iframe[src*='recaptcha'][title*='challenge']",
                        "iframe[src*='recaptcha/api2/bframe']",
                    )
                    while not responses and monotonic() < deadline and not cancelled():
                        has_challenge = any(
                            page.locator(selector).count()
                            and page.locator(selector).first.is_visible()
                            for selector in challenge_selectors
                        )
                        if has_challenge and not captcha_revealed and cdp and window_id is not None:
                            cdp.send(
                                "Browser.setWindowBounds",
                                {
                                    "windowId": window_id,
                                    "bounds": {
                                        "windowState": "normal",
                                        "left": 80,
                                        "top": 60,
                                        "width": 1280,
                                        "height": 900,
                                    },
                                },
                            )
                            page.bring_to_front()
                            captcha_revealed = True
                        page.wait_for_timeout(min(250, remaining_ms()))

                    if cancelled() or not responses:
                        return CfmLookup(CfmLookupStatus.UNAVAILABLE)
                    response = responses[-1]
                    if not response.ok:
                        return CfmLookup(CfmLookupStatus.UNAVAILABLE)
                    return parse_cfm_response(response.json(), crm, uf)
                finally:
                    browser.close()
        except (PlaywrightTimeoutError, PlaywrightError, ValueError, OSError):
            return CfmLookup(CfmLookupStatus.UNAVAILABLE)
