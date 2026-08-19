"""
Testes da estrutura de integração com o CFM (Missão 07): Port + Fake + fábrica.

Nenhum destes testes acessa a rede — é exatamente o ponto do adapter isolado.
"""

import os

import pytest

from app.cfm.client import CFMDoctorInfo
from app.cfm.dependency import get_cfm_client
from app.cfm.fake_client import FakeCFMClient
from app.cfm.http_client import CFMHttpClient


def test_fake_client_encontra_medico_cadastrado():
    """CRM/UF presentes na tabela em memória retornam os dados do médico."""
    cliente = FakeCFMClient()

    resultado = cliente.find_doctor("123456", "SP")

    assert resultado is not None
    assert resultado.nome == "Ana Souza Fictícia"
    assert resultado.situacao_inscricao == "Ativo"


def test_fake_client_normaliza_uf_minuscula():
    """A busca deve funcionar mesmo se a UF vier em minúsculas."""
    cliente = FakeCFMClient()

    resultado = cliente.find_doctor("654321", "rj")

    assert resultado is not None
    assert resultado.uf == "RJ"


def test_fake_client_retorna_none_para_medico_inexistente():
    """CRM/UF que não estão na tabela retornam None (não encontrado no CFM)."""
    cliente = FakeCFMClient()

    resultado = cliente.find_doctor("999999", "SP")

    assert resultado is None


def test_fake_client_aceita_tabela_customizada():
    """Os testes de outros módulos podem montar cenários próprios."""
    tabela = {("111111", "MG"): CFMDoctorInfo(
        nome="Médico de Teste",
        crm="111111",
        uf="MG",
        tipo_inscricao="Principal",
        situacao_inscricao="Ativo",
        especialidade_registrada=None,
    )}
    cliente = FakeCFMClient(medicos=tabela)

    assert cliente.find_doctor("111111", "MG") is not None
    assert cliente.find_doctor("123456", "SP") is None


def test_get_cfm_client_retorna_fake_por_padrao(monkeypatch):
    """Sem CFM_CLIENT definido, a fábrica deve devolver o FakeCFMClient."""
    monkeypatch.delenv("CFM_CLIENT", raising=False)

    cliente = get_cfm_client()

    assert isinstance(cliente, FakeCFMClient)


def test_get_cfm_client_retorna_http_quando_configurado(monkeypatch):
    """Com CFM_CLIENT=http, a fábrica deve devolver o adapter real (ainda pendente)."""
    monkeypatch.setenv("CFM_CLIENT", "http")

    cliente = get_cfm_client()

    assert isinstance(cliente, CFMHttpClient)


def test_cfm_http_client_ainda_nao_implementado():
    """O adapter real deve falhar de forma explícita até o contrato oficial existir."""
    cliente = CFMHttpClient()

    with pytest.raises(NotImplementedError):
        cliente.find_doctor("123456", "SP")
