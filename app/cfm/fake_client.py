"""
Implementação de desenvolvimento/teste do `CFMClient` — sem rede nenhuma.

Usada por padrão (ver `app/cfm/dependency.py`) enquanto o contrato oficial do
webservice do CFM não está disponível, e nos testes automatizados, para nunca
depender do serviço externo estar no ar.
"""

from app.cfm.client import CFMClient, CFMDoctorInfo

# Médicos fictícios para desenvolvimento local e testes — não são pessoas reais.
_MEDICOS_PADRAO: dict[tuple[str, str], CFMDoctorInfo] = {
    ("123456", "SP"): CFMDoctorInfo(
        nome="Ana Souza Fictícia",
        crm="123456",
        uf="SP",
        tipo_inscricao="Principal",
        situacao_inscricao="Ativo",
        especialidade_registrada="Clínica Médica",
    ),
    ("654321", "RJ"): CFMDoctorInfo(
        nome="Bruno Lima Fictício",
        crm="654321",
        uf="RJ",
        tipo_inscricao="Principal",
        situacao_inscricao="Ativo",
        especialidade_registrada="Cardiologia",
    ),
}


class FakeCFMClient:
    """Implementa `CFMClient` consultando uma tabela em memória.

    Aceita um dicionário próprio de médicos (`medicos`) para os testes
    montarem cenários específicos; sem argumentos, usa `_MEDICOS_PADRAO`.
    """

    def __init__(self, medicos: dict[tuple[str, str], CFMDoctorInfo] | None = None):
        self._medicos = medicos if medicos is not None else dict(_MEDICOS_PADRAO)

    def find_doctor(self, crm: str, uf: str) -> CFMDoctorInfo | None:
        return self._medicos.get((crm.strip(), uf.strip().upper()))


# Verificação estática de que FakeCFMClient satisfaz o Protocol CFMClient.
_conformidade: CFMClient = FakeCFMClient()
