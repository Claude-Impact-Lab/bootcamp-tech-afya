import pytest

from app.cfm_client import (
    CFMClient,
    CFMDoctorInactive,
    CFMDoctorNotFound,
    CFMInvalidInput,
    CFMUnavailable,
)


ACTIVE_RESULT = """MEDICA EXEMPLO
CRM: 12345/SP
Data de Inscrição: 01/01/2020
Primeira inscrição na UF: 01/01/2020
Inscrição: Principal
Situação: Regular
Especialidades/Áreas de Atuação:
CARDIOLOGIA - RQE Nº: 1111
PEDIATRIA - RQE Nº: 2222
Endereço: Exibição não autorizada pelo médico.
"""


def novo_cliente(result_text: str, calls: list[tuple[str, str]] | None = None) -> CFMClient:
    def query_runner(crm: str, uf: str) -> str:
        if calls is not None:
            calls.append((crm, uf))
        return result_text

    return CFMClient(
        query_runner=query_runner,
        cache_ttl_seconds=3600,
        min_request_interval_seconds=0,
    )


def test_find_doctor_converte_resultado_real_da_pagina():
    medico = novo_cliente(ACTIVE_RESULT).find_doctor("12345", "sp")

    assert medico.nome == "MEDICA EXEMPLO"
    assert medico.crm == "12345"
    assert medico.uf == "SP"
    assert medico.situacao == "Regular"
    assert medico.tipo_inscricao == "Principal"
    assert medico.especialidades == (
        "CARDIOLOGIA - RQE Nº: 1111",
        "PEDIATRIA - RQE Nº: 2222",
    )


def test_find_doctor_aceita_crm_antigo_com_poucos_digitos():
    result = ACTIVE_RESULT.replace("12345/SP", "197/RO")
    medico = novo_cliente(result).find_doctor("197", "RO")

    assert medico.crm == "197"
    assert medico.uf == "RO"


def test_find_doctor_interpreta_prefixo_52_e_digito_do_crm_rj():
    result = ACTIVE_RESULT.replace("12345/SP", "5212345-6/RJ")
    medico = novo_cliente(result).find_doctor("123456", "RJ")

    assert medico.crm == "123456"
    assert medico.uf == "RJ"


def test_find_doctor_interpreta_resultado_vazio():
    with pytest.raises(CFMDoctorNotFound):
        novo_cliente("Nenhum resultado encontrado").find_doctor("12345", "SP")


def test_find_doctor_confirma_crm_e_uf_do_resultado():
    with pytest.raises(CFMDoctorNotFound):
        novo_cliente(ACTIVE_RESULT).find_doctor("54321", "SP")


def test_find_doctor_recusa_situacao_inativa():
    result = ACTIVE_RESULT.replace("Situação: Regular", "Situação: Cancelado")

    with pytest.raises(CFMDoctorInactive) as captured:
        novo_cliente(result).find_doctor("12345", "SP")

    assert captured.value.doctor.situacao == "Cancelado"


def test_find_doctor_usa_cache_por_crm_e_uf():
    calls: list[tuple[str, str]] = []
    client = novo_cliente(ACTIVE_RESULT, calls)

    client.find_doctor("12345", "SP")
    client.find_doctor("12345", "sp")

    assert calls == [("12345", "SP")]


@pytest.mark.parametrize(
    ("crm", "uf"),
    [("", "SP"), ("12345678", "SP"), ("12A45", "SP"), ("12345", "XX")],
)
def test_find_doctor_valida_entrada_sem_abrir_navegador(crm: str, uf: str):
    with pytest.raises(CFMInvalidInput):
        novo_cliente(ACTIVE_RESULT).find_doctor(crm, uf)


def test_find_doctor_recusa_formato_inesperado():
    with pytest.raises(CFMUnavailable):
        novo_cliente("Resposta sem os campos esperados").find_doctor("12345", "SP")
