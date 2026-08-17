"""Implementação SOAP 1.1 do Webservice oficial de Listagem de Médicos."""

import re
import ssl
from datetime import datetime
from xml.etree.ElementTree import Element, QName, SubElement, tostring
from xml.etree.ElementTree import ParseError

import httpx
from defusedxml.ElementTree import fromstring
from defusedxml.common import DefusedXmlException

from app.services.cfm import (
    CFMAuthenticationError,
    CFMConfigurationError,
    CFMDoctor,
    CFMInvalidResponseError,
    CFMService,
    CFMSpecialty,
    CFMUnavailableError,
)

SOAP_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope/"
CFM_NAMESPACE = "http://servico.cfm.org.br/"
TRANSIENT_ERROR_CODES = frozenset({"2010", "2030", "2040"})
SPECIALTY_PATTERN = re.compile(
    r"^(?P<name>.*?)\s*-\s*RQE\s*N(?:º|°)?\s*:\s*(?P<rqe>\d+)",
    flags=re.IGNORECASE,
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_element(root: Element, name: str) -> Element | None:
    return next((element for element in root.iter() if _local_name(element.tag) == name), None)


def _first_text(root: Element, name: str) -> str | None:
    element = _first_element(root, name)
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _required_text(root: Element, name: str) -> str:
    value = _first_text(root, name)
    if value is None:
        raise CFMInvalidResponseError(f"Resposta do CFM sem o campo {name}")
    return value


def _parse_specialty(value: str) -> CFMSpecialty:
    description = value.strip()
    match = SPECIALTY_PATTERN.match(" ".join(description.split()))
    if match is None:
        return CFMSpecialty(name=" ".join(description.split()), rqe=None, official_description=description)
    return CFMSpecialty(
        name=match.group("name").strip(),
        rqe=match.group("rqe"),
        official_description=description,
    )


class CFMSoapService(CFMService):
    """Consulta pontual ao endpoint SOAP contratado junto ao CFM."""

    def __init__(
        self,
        access_key: str | None,
        url: str | None,
        timeout_seconds: str | float = 10,
        client: httpx.Client | None = None,
    ) -> None:
        self.access_key = (access_key or "").strip()
        self.url = (url or "").strip()
        self.timeout_seconds = timeout_seconds
        self.client = client

    def find_doctor(self, crm: str, uf: str) -> CFMDoctor | None:
        timeout = self._validated_timeout()
        payload = self._build_envelope(crm, uf)
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '""',
        }

        try:
            if self.client is not None:
                response = self.client.post(self.url, content=payload, headers=headers, timeout=timeout)
            else:
                context = ssl.create_default_context()
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                context.maximum_version = ssl.TLSVersion.TLSv1_2
                with httpx.Client(verify=context, timeout=timeout) as client:
                    response = client.post(self.url, content=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise CFMUnavailableError("Não foi possível acessar o CFM") from exc

        if response.status_code != 200:
            raise CFMUnavailableError(
                f"CFM respondeu com HTTP {response.status_code}",
                code=f"HTTP_{response.status_code}",
            )
        return self._parse_response(response.content)

    def _validated_timeout(self) -> float:
        if not self.access_key:
            raise CFMConfigurationError("CFM_ACCESS_KEY não foi configurada")
        if len(self.access_key) != 8:
            raise CFMConfigurationError("CFM_ACCESS_KEY deve possuir 8 caracteres")
        if not self.url:
            raise CFMConfigurationError("CFM_WS_URL não foi configurada")
        try:
            timeout = float(self.timeout_seconds)
        except (TypeError, ValueError) as exc:
            raise CFMConfigurationError("CFM_TIMEOUT_SECONDS deve ser numérico") from exc
        if timeout <= 0:
            raise CFMConfigurationError("CFM_TIMEOUT_SECONDS deve ser maior que zero")
        return timeout

    def _build_envelope(self, crm: str, uf: str) -> bytes:
        envelope = Element(QName(SOAP_NAMESPACE, "Envelope"))
        body = SubElement(envelope, QName(SOAP_NAMESPACE, "Body"))
        operation = SubElement(body, QName(CFM_NAMESPACE, "Consultar"))
        SubElement(operation, "crm").text = crm
        SubElement(operation, "uf").text = uf
        SubElement(operation, "chave").text = self.access_key
        return tostring(envelope, encoding="utf-8", xml_declaration=True)

    def _parse_response(self, content: bytes) -> CFMDoctor | None:
        try:
            root = fromstring(content)
        except (ParseError, DefusedXmlException) as exc:
            raise CFMInvalidResponseError("O CFM devolveu um XML inválido") from exc

        data = _first_element(root, "dadosMedico")
        if data is None:
            raise CFMInvalidResponseError("Resposta do CFM sem dadosMedico")

        error_code = _first_text(data, "codigoErro")
        if error_code == "8101":
            return None
        if error_code in TRANSIENT_ERROR_CODES:
            raise CFMUnavailableError("Falha temporária informada pelo CFM", code=error_code)
        if error_code == "3010":
            raise CFMAuthenticationError("Chave de acesso recusada pelo CFM", code=error_code)
        if error_code is not None:
            raise CFMInvalidResponseError("Requisição recusada pelo CFM", code=error_code)

        updated_at_text = _first_text(data, "dataAtualizacao")
        try:
            updated_at = datetime.strptime(updated_at_text, "%d/%m/%Y").date() if updated_at_text else None
        except ValueError as exc:
            raise CFMInvalidResponseError("Data de atualização inválida no retorno do CFM") from exc

        specialties = tuple(
            _parse_specialty(element.text)
            for element in data.iter()
            if _local_name(element.tag) == "especialidade" and element.text and element.text.strip()
        )
        return CFMDoctor(
            crm_display=_required_text(data, "crm"),
            uf=_required_text(data, "uf"),
            official_name=_required_text(data, "nome"),
            registration_status=_required_text(data, "situacao"),
            registration_type=_first_text(data, "tipoInscricao"),
            source_updated_at=updated_at,
            specialties=specialties,
        )
