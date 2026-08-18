"""Adapter para a consulta pública de médicos no portal do CFM.

O restante da aplicação conhece somente ``find_doctor(crm, uf)``. Caso o portal
exija reCAPTCHA, este adapter não tenta contorná-lo: devolve ``UNAVAILABLE`` para
que a interface ofereça a consulta manual.
"""

from dataclasses import dataclass
from enum import StrEnum
import re

import httpx


CFM_SEARCH_URL = "https://portal.cfm.org.br/busca-medicos"


class CfmLookupStatus(StrEnum):
    FOUND = "VALIDATED"
    NOT_FOUND = "NOT_FOUND"
    UNAVAILABLE = "VALIDATION_PENDING"


@dataclass(frozen=True)
class CfmLookup:
    status: CfmLookupStatus
    name: str | None = None


def crm_for_cfm(crm: str, uf: str) -> str:
    """Devolve o valor do campo CRM do portal.

    No RJ, o portal já mostra o prefixo fixo ``52`` fora do input. Portanto,
    esse prefixo não deve ser enviado nem comparado como parte do CRM digitado.
    """
    digits = "".join(char for char in crm if char.isdigit())
    if uf.strip().upper() == "RJ" and digits.startswith("52"):
        return digits[2:]
    return digits


class CfmClient:
    """Consulta o formulário público com timeout curto e sem burlar CAPTCHA."""

    def __init__(self, *, timeout: float = 8.0, client: httpx.Client | None = None):
        self.timeout = timeout
        self._client = client

    def find_doctor(self, crm: str, uf: str) -> CfmLookup:
        crm_busca = crm_for_cfm(crm, uf)
        try:
            if self._client is not None:
                response = self._client.post(CFM_SEARCH_URL, data={"crm": crm_busca, "uf": uf})
            else:
                with httpx.Client(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers={"User-Agent": "UserManager/1.0 (educational project)"},
                ) as client:
                    response = client.post(CFM_SEARCH_URL, data={"crm": crm_busca, "uf": uf})
        except httpx.HTTPError:
            return CfmLookup(CfmLookupStatus.UNAVAILABLE)

        if response.status_code != 200:
            return CfmLookup(CfmLookupStatus.UNAVAILABLE)

        page = response.text
        normalized = " ".join(page.lower().split())
        if "não foi encontrado" in normalized or "nenhum médico encontrado" in normalized:
            return CfmLookup(CfmLookupStatus.NOT_FOUND)

        # O portal pode aceitar a busca sem desafio visual; só marcamos validado
        # quando a página traz um resultado inequívoco para o CRM solicitado.
        crm_pattern = re.escape(str(crm_busca).lstrip("0") or "0")
        has_result = any(label in normalized for label in ("dados do médico", "resultado da busca", "médico encontrado"))
        if has_result and re.search(rf"crm\s*[:\-]?\s*{crm_pattern}(?!\d)", normalized):
            return CfmLookup(CfmLookupStatus.FOUND)

        # Página sem resultado identificável normalmente é a tela de CAPTCHA ou
        # uma alteração no portal. O cadastro segue pendente para nova consulta.
        return CfmLookup(CfmLookupStatus.UNAVAILABLE)
