from app.cfm_client import (
    CfmClient,
    CfmLookup,
    CfmLookupStatus,
    crm_for_cfm,
    parse_cfm_response,
)


def test_find_doctor_retorna_resultado_do_navegador():
    def fake_lookup(crm: str, uf: str, headless: bool, timeout: float) -> CfmLookup:
        assert (crm, uf, headless) == ("123", "SP", True)
        return CfmLookup(CfmLookupStatus.FOUND, "Médica Teste")

    result = CfmClient(mode="headless", browser_lookup=fake_lookup).find_doctor("123", "sp")

    assert result.status is CfmLookupStatus.FOUND
    assert result.name == "Médica Teste"


def test_find_doctor_tenta_janela_visivel_se_oculto_for_bloqueado():
    attempts: list[bool] = []

    def fake_lookup(crm: str, uf: str, headless: bool, timeout: float) -> CfmLookup:
        attempts.append(headless)
        return CfmLookup(CfmLookupStatus.UNAVAILABLE if headless else CfmLookupStatus.NOT_FOUND)

    result = CfmClient(mode="headless_then_headed", browser_lookup=fake_lookup).find_doctor("123", "SP")

    assert attempts == [True, False]
    assert result.status is CfmLookupStatus.NOT_FOUND


def test_parse_cfm_response_valida_apenas_crm_e_uf_exatos():
    payload = [{"status": 1, "dados": [{"NM_MEDICO": "Médica Teste", "SG_UF": "SP", "NU_CRM": "123"}]}]

    assert parse_cfm_response(payload, "123", "SP").status is CfmLookupStatus.FOUND
    assert parse_cfm_response(payload, "124", "SP").status is CfmLookupStatus.NOT_FOUND
    assert parse_cfm_response(payload, "123", "RJ").status is CfmLookupStatus.NOT_FOUND


def test_parse_cfm_response_vazia_retorna_nao_encontrado():
    result = parse_cfm_response([{"status": 1, "dados": []}], "123", "SP")

    assert result.status is CfmLookupStatus.NOT_FOUND


def test_parse_cfm_response_desconhecida_fica_pendente():
    result = parse_cfm_response({"erro": "captcha"}, "123", "SP")

    assert result.status is CfmLookupStatus.UNAVAILABLE


def test_crm_do_rio_nao_repete_o_prefixo_52_do_portal():
    assert crm_for_cfm("5212345", "RJ") == "12345"
    assert crm_for_cfm("12345", "RJ") == "12345"


def test_resposta_do_rio_ignora_prefixo_52_nos_dois_lados():
    payload = [{"dados": [{"SG_UF": "RJ", "NU_CRM": "12345"}]}]

    assert parse_cfm_response(payload, "5212345", "RJ").status is CfmLookupStatus.FOUND
