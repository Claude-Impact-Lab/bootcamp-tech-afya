import httpx

from app.cfm_client import CfmClient, CfmLookupStatus, crm_for_cfm


def client_with_page(page: str, status_code: int = 200) -> CfmClient:
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, text=page))
    return CfmClient(client=httpx.Client(transport=transport))


def test_find_doctor_retorna_nao_encontrado():
    result = client_with_page("Nenhum médico encontrado").find_doctor("123", "SP")

    assert result.status is CfmLookupStatus.NOT_FOUND


def test_find_doctor_retorna_validado_com_resultado_inequivoco():
    page = "Resultado da busca: Médico encontrado. CRM: 123"

    result = client_with_page(page).find_doctor("123", "SP")

    assert result.status is CfmLookupStatus.FOUND


def test_find_doctor_retorna_pendente_quando_portal_nao_responde():
    result = client_with_page("erro", status_code=503).find_doctor("123", "SP")

    assert result.status is CfmLookupStatus.UNAVAILABLE


def test_crm_do_rio_nao_repete_o_prefixo_52_do_portal():
    assert crm_for_cfm("5212345", "RJ") == "12345"
    assert crm_for_cfm("12345", "RJ") == "12345"
