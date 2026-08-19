"""
Adapter real para o webservice oficial do CFM — AINDA NÃO IMPLEMENTADO.

O contrato técnico (endpoint, método HTTP, parâmetros e formato de resposta)
não é público: só é liberado após petição (paga para empresas privadas,
gratuita para entidades públicas) via SEI-Medicina, com assinatura de Termo
de Sigilo. Ver https://sistemas.cfm.org.br/listamedicos/informacoes.

Não inventamos esse contrato. Esta classe existe para já reservar o ponto de
extensão (mesma assinatura de `CFMClient`); implemente `find_doctor` assim que
a especificação oficial e a chave de acesso estiverem disponíveis.
"""

from app.cfm.client import CFMClient, CFMDoctorInfo


class CFMHttpClient:
    """Adapter real (pendente) do `CFMClient`, via HTTP com `httpx`."""

    def __init__(
        self,
        base_url: str | None = None,
        chave_acesso: str | None = None,
        timeout: float = 5.0,
    ):
        self._base_url = base_url
        self._chave_acesso = chave_acesso
        self._timeout = timeout

    def find_doctor(self, crm: str, uf: str) -> CFMDoctorInfo | None:
        raise NotImplementedError(
            "CFMHttpClient ainda não pode ser implementado: o contrato oficial "
            "do webservice do CFM (endpoint, parâmetros, formato de resposta) "
            "não é público. Consulte "
            "https://sistemas.cfm.org.br/listamedicos/informacoes, obtenha a "
            "chave de acesso e o 'Documento de Especificação de Integração WS "
            "CFM' junto ao CFM, e então implemente este método. Até lá, use "
            "FakeCFMClient (padrão via CFM_CLIENT=fake)."
        )


# Verificação estática de que CFMHttpClient satisfaz o Protocol CFMClient.
_conformidade: CFMClient = CFMHttpClient()
