"""
Contrato (port) da integração com o CFM.

Define exatamente o que o domínio precisa saber sobre um médico externo,
sem nenhum detalhe de como essa informação foi obtida (HTTP, arquivo, fake).
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CFMDoctorInfo:
    """Dados públicos de um médico, conforme o webservice do CFM disponibiliza.

    Não inclui CPF, endereço, telefone ou e-mail — o CFM não fornece isso.
    """

    nome: str
    crm: str
    uf: str
    tipo_inscricao: str
    situacao_inscricao: str
    especialidade_registrada: str | None = None


class CFMClient(Protocol):
    """Porta que o domínio usa para consultar um médico no CFM.

    Qualquer adapter (real ou fake) deve implementar exatamente esta
    assinatura, para que o domínio nunca dependa do formato do CFM.
    """

    def find_doctor(self, crm: str, uf: str) -> CFMDoctorInfo | None:
        """Retorna os dados do médico se o CRM/UF existir e estiver ativo no CFM.

        Retorna `None` quando o CFM não encontra nenhum registro para o par
        CRM/UF informado. Erros de rede/indisponibilidade devem ser tratados
        pelo adapter concreto (ver Missão 08 para timeout/retry).
        """
        ...
