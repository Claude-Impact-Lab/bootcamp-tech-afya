"""Consulta de CRM no formulário público do CFM usando um navegador real.

O portal executa a pesquisa por JavaScript e pode solicitar reCAPTCHA. A
automação usa o fluxo normal da página e nunca tenta resolver ou contornar o
CAPTCHA. Quando a consulta não pode ser concluída, o cadastro fica pendente.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import os
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


BrowserLookup = Callable[[str, str, bool, float], CfmLookup]


class CfmClient:
    """Automatiza o formulário do CFM e captura a resposta AJAX da pesquisa.

    Modos aceitos em ``CFM_BROWSER_MODE``:
    - ``headless_then_headed``: tenta oculto e abre uma janela se necessário;
    - ``headless``: nunca abre janela;
    - ``headed`` (padrão): abre a janela, pois o reCAPTCHA atual bloqueia o
      Chromium oculto.
    """

    def __init__(
        self,
        *,
        timeout: float = 12.0,
        interactive_timeout: float = 45.0,
        mode: str | None = None,
        browser_lookup: BrowserLookup | None = None,
    ):
        self.timeout = timeout
        self.interactive_timeout = interactive_timeout
        self.mode = (mode or os.getenv("CFM_BROWSER_MODE", "headed")).lower()
        self._browser_lookup = browser_lookup or self._find_with_browser

    def find_doctor(self, crm: str, uf: str) -> CfmLookup:
        attempts = {
            "headless": [(True, self.timeout)],
            "headed": [(False, self.interactive_timeout)],
            "headless_then_headed": [
                (True, self.timeout),
                (False, self.interactive_timeout),
            ],
        }.get(self.mode, [(True, self.timeout)])

        for headless, timeout in attempts:
            result = self._browser_lookup(crm_for_cfm(crm, uf), uf.strip().upper(), headless, timeout)
            if result.status is not CfmLookupStatus.UNAVAILABLE:
                return result
        return CfmLookup(CfmLookupStatus.UNAVAILABLE)

    @staticmethod
    def _find_with_browser(crm: str, uf: str, headless: bool, timeout: float) -> CfmLookup:
        timeout_ms = int(timeout * 1000)
        setup_timeout_ms = min(timeout_ms, 15_000)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=headless)
                try:
                    context = browser.new_context(
                        locale="pt-BR",
                        timezone_id="America/Sao_Paulo",
                        viewport={"width": 1280, "height": 900},
                    )
                    page = context.new_page()
                    page.goto(CFM_SEARCH_URL, wait_until="domcontentloaded", timeout=setup_timeout_ms)
                    page.locator("#uf").wait_for(state="visible", timeout=setup_timeout_ms)
                    page.locator("#uf").select_option(label=uf)
                    page.locator("#crm").fill(crm)

                    # Aguarda os scripts que registram o submit e chamam o
                    # reCAPTCHA invisível. O clique continua sendo o da página.
                    page.wait_for_function(
                        "typeof window.jQuery !== 'undefined' && "
                        "typeof window.getInfo === 'function'",
                        timeout=setup_timeout_ms,
                    )
                    if not headless:
                        page.bring_to_front()

                    with page.expect_response(
                        lambda response: CFM_API_PATH in response.url,
                        timeout=timeout_ms,
                    ) as response_info:
                        page.locator("button.btnPesquisar").click()

                    response = response_info.value
                    if not response.ok:
                        return CfmLookup(CfmLookupStatus.UNAVAILABLE)
                    return parse_cfm_response(response.json(), crm, uf)
                finally:
                    browser.close()
        except (PlaywrightTimeoutError, PlaywrightError, ValueError, OSError):
            return CfmLookup(CfmLookupStatus.UNAVAILABLE)
