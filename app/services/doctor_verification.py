"""Regras para validar a identidade profissional retornada pelo CFM."""

import unicodedata

from app.services.cfm import CFMDoctor, CFMService
from app.services.crm_numbers import crm_digits


def normalize_name(value: str) -> str:
    """Ignora caixa, acentos e espaços excedentes sem fazer comparação aproximada."""

    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(without_accents.split())


class DoctorVerificationFailure(Exception):
    """Falha determinística que impede validar o perfil profissional."""

    public_message = "Não foi possível validar os dados profissionais no CFM"


class DoctorNotFound(DoctorVerificationFailure):
    public_message = "CRM e UF não encontrados no CFM"


class DoctorNameMismatch(DoctorVerificationFailure):
    public_message = "O nome informado não corresponde ao nome registrado no CFM"


class DoctorIrregular(DoctorVerificationFailure):
    public_message = "O CRM foi encontrado, mas não está regular no CFM"


class DoctorVerificationService:
    """Aplica as regras da aplicação sobre a consulta oficial do CFM."""

    def __init__(self, cfm_service: CFMService) -> None:
        self.cfm_service = cfm_service

    def lookup_for_manual_review(self, crm: str, uf: str) -> CFMDoctor:
        """Obtém os dados oficiais sem substituir a decisão do administrador."""

        doctor = self.cfm_service.find_doctor(crm, uf)
        if doctor is None:
            raise DoctorNotFound
        if doctor.uf.upper() != uf.upper() or crm_digits(doctor.crm_display) != crm_digits(crm):
            raise DoctorNotFound
        return doctor

    def verify(self, name: str, crm: str, uf: str) -> CFMDoctor:
        doctor = self.lookup_for_manual_review(crm, uf)
        if normalize_name(doctor.registration_status) not in {"a", "regular"}:
            raise DoctorIrregular
        if normalize_name(name) != normalize_name(doctor.official_name):
            raise DoctorNameMismatch
        return doctor
