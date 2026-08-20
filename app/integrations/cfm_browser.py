"""Consulta local do portal público do CFM em um Chrome visível e isolado."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.services.cfm import (
    CFMDoctor,
    CFMInvalidResponseError,
    CFMUnavailableError,
    CFMSpecialty,
)
from app.services.crm_numbers import crm_digits


CFM_SEARCH_URL = "https://portal.cfm.org.br/busca-medicos/"
CFM_SEARCH_ENDPOINT = "/api_rest_php/api/v2/medicos/buscar_medicos"
CFM_DETAILS_ENDPOINT = "/api_rest_php/api/v2/medicos/buscar_foto/"


@dataclass(frozen=True, slots=True)
class CFMSearchInput:
    """Valores confirmados no formulário público antes do envio."""

    requested_digits: str
    query_digits: str
    displayed_prefix: str


class CFMBrowserService:
    """Automatiza somente a navegação; um eventual CAPTCHA é resolvido pela pessoa."""

    _browser_lock = threading.Lock()

    def __init__(
        self,
        timeout_seconds: str | float = 120,
        headless: bool = False,
        channel: str = "chrome",
    ) -> None:
        self.timeout_seconds = float(timeout_seconds)
        if self.timeout_seconds <= 0:
            raise ValueError("O timeout do navegador deve ser positivo")
        self.headless = headless
        self.channel = channel

    def find_doctor(self, crm: str, uf: str) -> CFMDoctor | None:
        if not self._browser_lock.acquire(blocking=False):
            raise CFMUnavailableError(
                "Já existe uma validação do CFM em andamento", code="BROWSER_BUSY"
            )

        browser = None
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel=self.channel, headless=self.headless)
                context = browser.new_context(locale="pt-BR")
                page = context.new_page()
                page.set_default_timeout(min(30_000, int(self.timeout_seconds * 1_000)))
                page.goto(CFM_SEARCH_URL, wait_until="domcontentloaded")
                deadline = time.monotonic() + self.timeout_seconds
                main_responses: list[Any] = []
                detail_responses: list[Any] = []

                def capture_response(response: Any) -> None:
                    if CFM_SEARCH_ENDPOINT in response.url:
                        main_responses.append(response)
                    elif CFM_DETAILS_ENDPOINT in response.url:
                        detail_responses.append(response)

                page.on("response", capture_response)
                search_input = self._prepare_and_submit(page, crm, uf)
                payload = self._wait_for_main_payload(page, main_responses, deadline)
                doctor = self._parse_payload(
                    payload,
                    crm,
                    uf,
                    query_crm=search_input.query_digits,
                    displayed_prefix=search_input.displayed_prefix,
                )
                if doctor is None:
                    return None
                detail_payload = self._wait_for_detail_payload(
                    page, detail_responses, deadline
                )
                return self._merge_detail_payload(doctor, detail_payload)
        except PlaywrightTimeoutError as exc:
            raise CFMUnavailableError(
                "A consulta expirou aguardando a página ou a resolução do CAPTCHA",
                code="CAPTCHA_OR_TIMEOUT",
            ) from exc
        except CFMInvalidResponseError:
            raise
        except PlaywrightError as exc:
            raise CFMUnavailableError(
                "A janela do Chrome foi fechada ou a consulta não pôde continuar",
                code="BROWSER_CLOSED",
            ) from exc
        finally:
            if browser is not None:
                try:
                    browser.close()
                except PlaywrightError:
                    pass
            self._browser_lock.release()

    @staticmethod
    def _prepare_and_submit(page: Any, crm: str, uf: str) -> CFMSearchInput:
        requested_digits = crm_digits(crm)
        page.wait_for_selector("#buscaForm")
        page.wait_for_selector("#crm")
        page.wait_for_selector(
            f"#uf option[value='{uf.upper()}']",
            state="attached",
        )

        page.select_option("#uf", uf.upper())
        if page.input_value("#uf").upper() != uf.upper():
            raise CFMInvalidResponseError(
                "Não foi possível selecionar a UF na página do CFM",
                code="UF_NOT_SELECTED",
            )

        prefix_field = page.locator(".basic-addon")
        displayed_prefix = (
            crm_digits(prefix_field.inner_text())
            if prefix_field.count() and prefix_field.is_visible()
            else ""
        )
        crm_field = page.locator("#crm")
        maxlength_text = crm_field.get_attribute("maxlength") or "0"
        maxlength = int(maxlength_text) if maxlength_text.isdigit() else 0
        query_digits = requested_digits
        applied_prefix = ""
        if maxlength and len(query_digits) > maxlength:
            if displayed_prefix and requested_digits.startswith(displayed_prefix):
                query_digits = requested_digits[len(displayed_prefix) :]
                applied_prefix = displayed_prefix
            if len(query_digits) > maxlength:
                raise CFMInvalidResponseError(
                    "O CRM não corresponde ao formato exibido pela página do CFM",
                    code="CRM_FORMAT_NOT_ACCEPTED",
                )

        crm_field.fill(query_digits)
        if crm_digits(crm_field.input_value()) != query_digits:
            raise CFMInvalidResponseError(
                "Não foi possível preencher o CRM na página do CFM",
                code="CRM_NOT_FILLED",
            )

        button = page.locator("#buscaForm .btn-buscar.btnPesquisar")
        button.scroll_into_view_if_needed()
        page.bring_to_front()
        button.click()
        return CFMSearchInput(
            requested_digits=requested_digits,
            query_digits=query_digits,
            displayed_prefix=applied_prefix,
        )

    def _wait_for_main_payload(
        self, page: Any, responses: list[Any], deadline: float
    ) -> Any:
        """Espera a página prosseguir; durante o CAPTCHA não executa nenhum clique."""

        while time.monotonic() < deadline:
            if page.is_closed():
                raise CFMUnavailableError(
                    "A janela do Chrome foi fechada durante a validação",
                    code="BROWSER_CLOSED",
                )
            while responses:
                payload = self._response_json(responses.pop(0))
                if self._captcha_was_rejected(payload):
                    # A própria página reinicia o reCAPTCHA. O usuário resolve e o
                    # callback oficial envia uma nova consulta, sem novo clique nosso.
                    continue
                return payload
            page.wait_for_timeout(200)
        raise CFMUnavailableError(
            "A consulta expirou aguardando a resolução do CAPTCHA ou o resultado",
            code="CAPTCHA_OR_TIMEOUT",
        )

    def _wait_for_detail_payload(
        self, page: Any, responses: list[Any], deadline: float
    ) -> Any | None:
        detail_deadline = min(deadline, time.monotonic() + 5)
        while time.monotonic() < detail_deadline:
            if page.is_closed():
                return None
            if responses:
                return self._response_json(responses.pop(0))
            page.wait_for_timeout(100)
        return None

    @staticmethod
    def _response_json(response: Any) -> Any:
        try:
            return response.json()
        except (PlaywrightError, ValueError) as exc:
            raise CFMInvalidResponseError(
                "O CFM retornou uma resposta que não é JSON", code="INVALID_JSON"
            ) from exc

    @staticmethod
    def _captcha_was_rejected(payload: Any) -> bool:
        if isinstance(payload, str):
            text = payload
        elif isinstance(payload, dict):
            text = " ".join(
                str(payload.get(key, ""))
                for key in ("status", "message", "mensagem", "error")
            )
        else:
            return False
        normalized = text.casefold()
        if normalized.strip() in {"expirou", "invalidinput"}:
            return True
        return "captcha" in normalized and any(
            word in normalized for word in ("expir", "invál", "inval", "erro")
        )

    @classmethod
    def _parse_payload(
        cls,
        payload: Any,
        requested_crm: str,
        requested_uf: str,
        *,
        query_crm: str | None = None,
        displayed_prefix: str = "",
    ) -> CFMDoctor | None:
        rows = cls._find_rows(payload)
        if not rows:
            return None
        requested_digits = crm_digits(requested_crm)
        query_digits = crm_digits(query_crm or requested_crm)
        row = next(
            (
                item
                for item in rows
                if str(item.get("SG_UF", "")).upper() == requested_uf.upper()
                and crm_digits(str(item.get("NU_CRM_NATURAL") or item.get("NU_CRM") or ""))
                == query_digits
            ),
            None,
        )
        if row is None:
            return None

        name = str(row.get("NM_MEDICO") or row.get("NM_SOCIAL") or "").strip()
        status = str(row.get("SITUACAO") or row.get("COD_SITUACAO") or "").strip()
        returned_crm = str(row.get("NU_CRM") or row.get("NU_CRM_NATURAL") or "").strip()
        returned_digits = crm_digits(returned_crm)
        full_digits = displayed_prefix + returned_digits if displayed_prefix else returned_digits
        if full_digits != requested_digits:
            return None
        crm_display = (
            f"{full_digits[:-1]}-{full_digits[-1]}"
            if requested_uf.upper() == "RJ" and displayed_prefix and len(full_digits) > 1
            else returned_crm
        )
        if not name or not status or not crm_digits(crm_display):
            raise CFMInvalidResponseError("Resposta do CFM sem os campos obrigatórios", code="MISSING_FIELDS")

        institution = row.get("NM_INSTITUICAO_GRADUACAO") or row.get("NM_FACULDADE_ESTRANGEIRA_GRADUACAO")
        return CFMDoctor(
            crm_display=crm_display,
            uf=str(row.get("SG_UF") or requested_uf).upper(),
            official_name=name,
            registration_status=status,
            registration_type=cls._optional_text(row.get("TIPO_INSCRICAO")),
            source_updated_at=None,
            specialties=cls._parse_specialties(row.get("ESPECIALIDADE")),
            registration_date=cls._parse_date(row.get("DT_INSCRICAO")),
            first_registration_uf=cls._optional_text(row.get("PRIM_INSCRICAO_UF")),
            graduation_institution=cls._optional_text(institution),
            graduation_year=cls._optional_text(row.get("DT_GRADUACAO")),
        )

    @classmethod
    def _find_rows(cls, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            if all(isinstance(item, dict) for item in payload):
                return payload
            return []
        if not isinstance(payload, dict):
            raise CFMInvalidResponseError("Formato inesperado na resposta do CFM", code="INVALID_SHAPE")
        for key in ("dados", "data", "resultado", "result", "medicos"):
            value = payload.get(key)
            rows = cls._find_rows(value) if isinstance(value, (dict, list)) else []
            if rows:
                return rows
        if any(key in payload for key in ("NM_MEDICO", "NU_CRM", "NU_CRM_NATURAL")):
            return [payload]
        return []

    @classmethod
    def _parse_specialties(cls, value: Any) -> tuple[CFMSpecialty, ...]:
        if not value:
            return ()
        descriptions = re.split(r"\s*(?:&|\n|;)\s*", str(value))
        result = []
        for description in descriptions:
            description = description.strip()
            if not description:
                continue
            match = re.search(r"\bRQE\s*(?:N[º°o.]*)?\s*:?\s*(\d+)", description, re.IGNORECASE)
            name = re.split(r"\s*[-–—]?\s*RQE\b", description, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -")
            result.append(CFMSpecialty(name=name or description, rqe=match.group(1) if match else None, official_description=description))
        return tuple(result)

    @classmethod
    def _merge_detail_payload(
        cls, doctor: CFMDoctor, payload: Any | None
    ) -> CFMDoctor:
        if payload is None:
            return doctor
        rows = cls._find_rows(payload)
        if not rows:
            return doctor
        values = rows[0]
        document_type = cls._optional_text(values.get("DS_TP_DOC_ESP"))
        detail_rqes = set(re.findall(r"\d+", str(values.get("DS_TP_DOC_ESP_RQE") or "")))
        specialties = doctor.specialties
        if document_type and detail_rqes:
            specialties = tuple(
                CFMSpecialty(
                    name=specialty.name,
                    rqe=specialty.rqe,
                    official_description=(
                        f"{specialty.official_description} ({document_type})"
                        if specialty.rqe in detail_rqes
                        else specialty.official_description
                    ),
                )
                for specialty in doctor.specialties
            )

        photo_url = doctor.photo_url
        authorization = cls._optional_text(values.get("AUTORIZACAO_IMAGEM"))
        photo_crm = cls._optional_text(values.get("CRM"))
        photo_uf = cls._optional_text(values.get("UF_CRM"))
        photo_hash = cls._optional_text(values.get("HASH"))
        # O JavaScript oficial exibe a foto sempre que a autorização não é
        # explicitamente "N". Em respostas reais, esse campo pode vir nulo
        # mesmo quando CRM, UF e hash válidos são devolvidos e usados no DOM.
        if authorization != "N" and all((photo_crm, photo_uf, photo_hash)):
            query = urlencode({"crm": photo_crm, "uf": photo_uf, "hash": photo_hash})
            photo_url = (
                "https://portal.cfm.org.br/wp-content/themes/portalcfm/"
                f"assets/php/foto_medico.php?{query}"
            )

        return replace(
            doctor,
            specialties=specialties,
            photo_url=photo_url,
        )

    @staticmethod
    def _parse_date(value: Any):
        text = str(value or "").strip()
        for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text[:10], date_format).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None
