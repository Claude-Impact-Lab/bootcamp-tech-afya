"""Adaptador do Web Service SOAP do Conselho Federal de Medicina."""

from dataclasses import dataclass
import os
import time
import xml.etree.ElementTree as ET

import httpx


CFM_URL = (
    "https://ws.cfm.org.br:8080/WebServiceConsultaMedicos/"
    "ServicoConsultaMedicos"
)
TRANSIENT_CFM_CODES = {"2010", "2030", "2040"}


class CFMUnavailableError(Exception):
    """Falha temporaria: a validacao deve ficar pendente."""


@dataclass(frozen=True)
class CFMDoctor:
    found: bool
    name: str | None = None
    registration_status: str | None = None
    registration_type: str | None = None


class CFMClient:
    """Cliente pequeno e substituivel por mock nos testes."""

    def __init__(
        self,
        access_key: str | None = None,
        url: str | None = None,
        timeout: float | None = None,
        max_attempts: int = 2,
        retry_delay: float = 0.2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.access_key = access_key or os.getenv("CFM_ACCESS_KEY")
        self.url = url or os.getenv("CFM_API_URL", CFM_URL)
        self.timeout = timeout or float(os.getenv("CFM_TIMEOUT_SECONDS", "3"))
        self.max_attempts = max_attempts
        self.retry_delay = retry_delay
        self.transport = transport

    def find_doctor(self, crm: str, uf: str) -> CFMDoctor:
        if not self.access_key:
            raise CFMUnavailableError("Chave de acesso do CFM nao configurada.")

        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                return self._request(crm, uf)
            except CFMUnavailableError as error:
                last_error = error
                if attempt + 1 < self.max_attempts and self.retry_delay:
                    time.sleep(self.retry_delay)
        raise CFMUnavailableError("CFM indisponivel apos as tentativas.") from last_error

    def _request(self, crm: str, uf: str) -> CFMDoctor:
        envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
 xmlns:ser="http://servico.cfm.org.br/">
 <soapenv:Body><ser:Consultar><crm>{crm}</crm><uf>{uf}</uf>
 <chave>{self.access_key}</chave></ser:Consultar></soapenv:Body>
</soapenv:Envelope>"""
        try:
            with httpx.Client(transport=self.transport, timeout=self.timeout) as client:
                response = client.post(
                    self.url,
                    content=envelope.encode("utf-8"),
                    headers={
                        "Content-Type": "text/xml; charset=utf-8",
                        "SOAPAction": '""',
                    },
                )
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except (httpx.HTTPError, ET.ParseError) as error:
            raise CFMUnavailableError("Falha temporaria na comunicacao com o CFM.") from error

        data = next((item for item in root.iter() if _local_name(item.tag) == "dadosMedico"), None)
        if data is None:
            raise CFMUnavailableError("Resposta inesperada do CFM.")
        values = {_local_name(item.tag): item.text for item in data}
        code = values.get("codigoErro")
        if code == "8101":
            return CFMDoctor(found=False)
        if code in TRANSIENT_CFM_CODES:
            raise CFMUnavailableError(f"Falha temporaria do CFM: {code}.")
        if code:
            return CFMDoctor(found=False)
        return CFMDoctor(
            found=True,
            name=values.get("nome"),
            registration_status=values.get("situacao"),
            registration_type=values.get("tipoInscricao"),
        )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def get_cfm_client() -> CFMClient:
    return CFMClient()
