from pydantic import BaseModel


class CFMDoctorInfo(BaseModel):
    nome: str
    crm: str
    uf: str
    tipo_inscricao: str
    situacao: str
    especialidade: str | None = None


class CFMError(Exception):
    """Erro base para qualquer falha na integração com o CFM."""
    pass


class DoctorNotFoundError(CFMError):
    """O CRM/UF informado não corresponde a nenhum médico registrado."""
    pass


# Simulação do webservice do CFM, enquanto não há acesso à API oficial paga.
# Chave: (crm, uf). Valor: dados do médico, no formato que o CFM devolveria.
_MEDICOS_SIMULADOS = {
    ("123456", "SP"): CFMDoctorInfo(
        nome="Dr. Rodrigo Pita",
        crm="123456",
        uf="SP",
        tipo_inscricao="Principal",
        situacao="Ativo",
        especialidade="Cardiologia",
    ),
    ("654321", "RJ"): CFMDoctorInfo(
        nome="Dra. Natascha Nunes",
        crm="654321",
        uf="RJ",
        tipo_inscricao="Principal",
        situacao="Ativo",
        especialidade=None,
    ),
}


def find_doctor(crm: str, uf: str) -> CFMDoctorInfo:
    """Consulta o CFM (simulado, por enquanto) por um médico via CRM/UF.

    Levanta DoctorNotFoundError se o médico não for encontrado.
    """
    medico = _MEDICOS_SIMULADOS.get((crm, uf))

    if medico is None:
        raise DoctorNotFoundError(f"Médico com CRM {crm}/{uf} não encontrado")

    return medico