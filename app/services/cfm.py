"""Contrato interno para consultar dados profissionais no CFM."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CFMSpecialty:
    """Especialidade tal como foi normalizada a partir do retorno oficial."""

    name: str
    rqe: str | None
    official_description: str


@dataclass(frozen=True, slots=True)
class CFMDoctor:
    """Resposta do CFM independente de SOAP, XML ou fornecedor."""

    crm_display: str
    uf: str
    official_name: str
    registration_status: str
    registration_type: str | None
    source_updated_at: date | None
    specialties: tuple[CFMSpecialty, ...]
    registration_date: date | None = None
    first_registration_uf: str | None = None
    graduation_institution: str | None = None
    graduation_year: str | None = None
    photo_url: str | None = None


class CFMService(Protocol):
    """Adapter que poderá receber outra implementação sem mudar o cadastro."""

    def find_doctor(self, crm: str, uf: str) -> CFMDoctor | None:
        """Busca um médico por CRM e UF; devolve ``None`` quando não existe."""


class CFMServiceError(Exception):
    """Erro base da integração oficial."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class CFMConfigurationError(CFMServiceError):
    """Credencial ou configuração local ausente/inválida."""


class CFMAuthenticationError(CFMServiceError):
    """Chave recusada pelo CFM."""


class CFMUnavailableError(CFMServiceError):
    """Falha de rede, timeout ou erro transitório do CFM."""


class CFMInvalidResponseError(CFMServiceError):
    """Resposta do CFM fora do contrato documentado."""
