"""Consulta local da pagina publica de medicos do CFM com Playwright.

O navegador e exibido para que o proprio medico possa resolver um eventual
CAPTCHA. Este modulo nao tenta obter, reutilizar ou contornar tokens do CAPTCHA.
"""

from __future__ import annotations

import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from typing import Callable

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

CFM_PORTAL_URL = "https://portal.cfm.org.br/busca-medicos/"
UFS_VALIDAS = frozenset(
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
)


class CFMError(Exception):
    """Erro base para a integracao com o CFM."""


class CFMInvalidInput(CFMError):
    """CRM ou UF nao passou pela validacao defensiva do cliente."""


class CFMDoctorNotFound(CFMError):
    """O CFM nao encontrou o CRM na UF pesquisada."""


class CFMUnavailable(CFMError):
    """A pagina ou a consulta do CFM esta indisponivel."""


class CFMValidationTimeout(CFMError):
    """A pagina nao retornou um resultado dentro do limite configurado."""


class CFMConfigurationError(CFMError):
    """O Chrome/Playwright local nao esta disponivel ou foi mal configurado."""


class CFMDoctorInactive(CFMError):
    """O CRM existe, mas nao esta em situacao ativa/regular."""

    def __init__(self, doctor: CFMDoctor) -> None:
        self.doctor = doctor
        super().__init__(f"CRM {doctor.crm}/{doctor.uf} esta {doctor.situacao}")


@dataclass(frozen=True)
class CFMDoctor:
    """Dados publicos exibidos no resultado da busca do CFM."""

    nome: str
    crm: str
    uf: str
    situacao: str
    tipo_inscricao: str | None
    especialidades: tuple[str, ...]


def _sem_acentos(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _crm_comparavel(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    return digits.lstrip("0") or "0"


class CFMClient:
    """Automatiza somente a consulta; o CAPTCHA continua sendo humano.

    As consultas sao serializadas para evitar varias janelas e respeitar o
    portal. Resultados, inclusive "nao encontrado", usam cache por CRM + UF.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = 120,
        browser_channel: str = "chrome",
        browser_path: str | None = None,
        cache_ttl_seconds: float = 3600,
        min_request_interval_seconds: float = 3,
        query_runner: Callable[[str, str], str] | None = None,
    ) -> None:
        self._timeout_ms = max(1, int(timeout_seconds * 1000))
        self._browser_channel = browser_channel.strip() or "chrome"
        self._browser_path = browser_path.strip() if browser_path else None
        self._cache_ttl_seconds = max(0, cache_ttl_seconds)
        self._min_request_interval_seconds = max(0, min_request_interval_seconds)
        self._query_runner = query_runner or self._query_with_playwright
        self._cache: dict[tuple[str, str], tuple[float, CFMDoctor | None]] = {}
        self._lock = threading.Lock()
        self._last_request_finished_at = 0.0

    def find_doctor(self, crm: str, uf: str) -> CFMDoctor:
        """Consulta CRM/UF, confirma a correspondencia e exige situacao ativa."""
        crm = crm.strip()
        uf = uf.strip().upper()
        if not re.fullmatch(r"\d{1,7}", crm) or uf not in UFS_VALIDAS:
            raise CFMInvalidInput("CRM ou UF invalido")

        cache_key = (_crm_comparavel(crm), uf)
        with self._lock:
            cached = self._get_cached(cache_key)
            if cached is not False:
                return self._require_active(cached)

            elapsed = time.monotonic() - self._last_request_finished_at
            remaining = self._min_request_interval_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)

            try:
                result_text = self._query_runner(crm, uf)
                doctor = self._parse_result(result_text, expected_crm=crm, expected_uf=uf)
                self._cache[cache_key] = (
                    time.monotonic() + self._cache_ttl_seconds,
                    doctor,
                )
            except CFMDoctorNotFound:
                self._cache[cache_key] = (
                    time.monotonic() + self._cache_ttl_seconds,
                    None,
                )
                raise
            finally:
                self._last_request_finished_at = time.monotonic()

        return self._require_active(doctor)

    def _get_cached(self, key: tuple[str, str]) -> CFMDoctor | None | bool:
        cached = self._cache.get(key)
        if cached is None:
            return False
        expires_at, doctor = cached
        if expires_at <= time.monotonic():
            self._cache.pop(key, None)
            return False
        if doctor is None:
            raise CFMDoctorNotFound("CRM nao encontrado no CFM")
        return doctor

    @staticmethod
    def _require_active(doctor: CFMDoctor) -> CFMDoctor:
        normalized_status = _sem_acentos(doctor.situacao).strip().casefold()
        if normalized_status not in {"ativo", "ativa", "regular"}:
            raise CFMDoctorInactive(doctor)
        return doctor

    def _query_with_playwright(self, crm: str, uf: str) -> str:
        dialogs: list[str] = []
        try:
            with sync_playwright() as playwright:
                browser = None
                context = None
                try:
                    launch_options: dict[str, object] = {"headless": False}
                    if self._browser_path:
                        launch_options["executable_path"] = self._browser_path
                    else:
                        launch_options["channel"] = self._browser_channel

                    browser = playwright.chromium.launch(**launch_options)
                    context = browser.new_context()
                    page = context.new_page()
                    page.set_default_timeout(self._timeout_ms)

                    def close_dialog(dialog) -> None:
                        dialogs.append(dialog.message)
                        dialog.dismiss()

                    page.on("dialog", close_dialog)
                    page.goto(
                        CFM_PORTAL_URL,
                        wait_until="domcontentloaded",
                        timeout=min(self._timeout_ms, 45_000),
                    )

                    form = page.locator("#buscaForm")
                    form.get_by_placeholder("Digite o CRM").fill(crm)
                    form.locator("select#uf").select_option(uf)
                    form.get_by_role("button", name="ENVIAR", exact=True).click()

                    result = page.locator(".resultado-item").first
                    try:
                        result.wait_for(state="visible", timeout=self._timeout_ms)
                    except PlaywrightTimeoutError as error:
                        if dialogs:
                            raise CFMUnavailable(dialogs[-1]) from error
                        raise CFMValidationTimeout(
                            "A validacao expirou; conclua o CAPTCHA e tente novamente"
                        ) from error
                    return result.inner_text()
                finally:
                    if context is not None:
                        context.close()
                    if browser is not None:
                        browser.close()
        except (CFMUnavailable, CFMValidationTimeout):
            raise
        except PlaywrightTimeoutError as error:
            raise CFMValidationTimeout("Tempo limite ao acessar o CFM") from error
        except PlaywrightError as error:
            message = str(error)
            if "Executable doesn't exist" in message or "browserType.launch" in message:
                raise CFMConfigurationError(
                    "Chrome local nao encontrado; instale o Chrome ou configure CFM_BROWSER_PATH"
                ) from error
            raise CFMUnavailable("Falha ao consultar a pagina do CFM") from error

    @staticmethod
    def _parse_result(result_text: str, *, expected_crm: str, expected_uf: str) -> CFMDoctor:
        if "nenhum resultado encontrado" in _sem_acentos(result_text).casefold():
            raise CFMDoctorNotFound("CRM nao encontrado no CFM")

        lines = [line.strip() for line in result_text.splitlines() if line.strip()]
        crm_match = re.search(r"CRM:\s*([0-9]+(?:-[0-9A-Z])?)/([A-Z]{2})", result_text, re.IGNORECASE)
        status_match = re.search(r"Situa[cç][aã]o:\s*([^\r\n]+)", result_text, re.IGNORECASE)
        registration_match = re.search(
            r"(?:^|\n)Inscri[cç][aã]o:\s*([^\r\n]+)",
            result_text,
            re.IGNORECASE,
        )
        if not lines or crm_match is None or status_match is None:
            raise CFMUnavailable("O CFM retornou um resultado em formato inesperado")

        found_crm, found_uf = crm_match.groups()
        found_uf = found_uf.upper()
        crm_candidates = {_crm_comparavel(found_crm)}
        found_digits = "".join(character for character in found_crm if character.isdigit())
        if found_uf == "RJ" and found_digits.startswith("52"):
            crm_candidates.add(_crm_comparavel(found_digits[2:]))
        if _crm_comparavel(expected_crm) not in crm_candidates or found_uf != expected_uf:
            raise CFMDoctorNotFound("O resultado nao corresponde ao CRM e UF informados")

        specialties: tuple[str, ...] = ()
        specialties_match = re.search(
            r"Especialidades/[ÁA]reas de Atua[çc][ãa]o:\s*(.*?)(?:\nEndere[çc]o:|\nTelefone:|\nInstitui[çc][ãa]o|\Z)",
            result_text,
            re.IGNORECASE | re.DOTALL,
        )
        if specialties_match:
            specialties = tuple(
                line.strip()
                for line in specialties_match.group(1).splitlines()
                if line.strip() and "sem especialidade registrada" not in line.casefold()
            )

        return CFMDoctor(
            nome=lines[0],
            crm=expected_crm,
            uf=found_uf,
            situacao=status_match.group(1).strip(),
            tipo_inscricao=registration_match.group(1).strip() if registration_match else None,
            especialidades=specialties,
        )
