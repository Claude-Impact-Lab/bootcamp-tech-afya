from datetime import date

import httpx
import pytest

from app.integrations.cfm_soap import CFMSoapService
from app.services.cfm import CFMUnavailableError
from app.services.doctor_verification import (
    DoctorIrregular,
    DoctorNameMismatch,
    DoctorVerificationService,
)

CFM_URL = "https://cfm.test/ServicoConsultaMedicos"


def soap_response(body: str) -> str:
    return f"""
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body><ConsultarResponse><dadosMedico>{body}</dadosMedico></ConsultarResponse></soap:Body>
    </soap:Envelope>
    """


def service_with_response(xml: str):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["content-type"] == "text/xml; charset=utf-8"
        assert request.headers["soapaction"] == '""'
        request_body = request.content.decode()
        assert "<crm>123456</crm>" in request_body
        assert "<uf>SP</uf>" in request_body
        assert "<chave>ABCDEFGH</chave>" in request_body
        return httpx.Response(200, text=xml)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return CFMSoapService("ABCDEFGH", CFM_URL, client=client), client


def test_cfm_soap_interpreta_medico_com_multiplas_especialidades():
    xml = soap_response(
        """
        <crm>123456</crm><dataAtualizacao>14/08/2026</dataAtualizacao>
        <especialidade>CARDIOLOGIA - RQE Nº: 1111</especialidade>
        <especialidade>CLÍNICA MÉDICA - RQE Nº: 2222</especialidade>
        <nome>José da Silva</nome><situacao>A</situacao><tipoInscricao>P</tipoInscricao><uf>SP</uf>
        """
    )
    service, client = service_with_response(xml)
    try:
        doctor = service.find_doctor("123456", "SP")
    finally:
        client.close()

    assert doctor is not None
    assert doctor.official_name == "José da Silva"
    assert doctor.source_updated_at == date(2026, 8, 14)
    assert [specialty.rqe for specialty in doctor.specialties] == ["1111", "2222"]


def test_cfm_soap_aceita_medico_sem_especialidade():
    xml = soap_response(
        "<crm>123456</crm><nome>José da Silva</nome><situacao>A</situacao><tipoInscricao>P</tipoInscricao><uf>SP</uf>"
    )
    service, client = service_with_response(xml)
    try:
        doctor = service.find_doctor("123456", "SP")
    finally:
        client.close()

    assert doctor is not None
    assert doctor.specialties == ()


def test_cfm_soap_converte_codigo_8101_em_medico_nao_encontrado():
    service, client = service_with_response(soap_response("<codigoErro>8101</codigoErro>"))
    try:
        assert service.find_doctor("123456", "SP") is None
    finally:
        client.close()


def test_cfm_soap_trata_codigo_transitorio_como_indisponibilidade():
    service, client = service_with_response(soap_response("<codigoErro>2040</codigoErro>"))
    try:
        with pytest.raises(CFMUnavailableError) as error:
            service.find_doctor("123456", "SP")
    finally:
        client.close()

    assert error.value.code == "2040"


def test_cfm_soap_trata_timeout_como_indisponibilidade():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("tempo esgotado", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = CFMSoapService("ABCDEFGH", CFM_URL, client=client)
    try:
        with pytest.raises(CFMUnavailableError):
            service.find_doctor("123456", "SP")
    finally:
        client.close()


class StubCFMService:
    def __init__(self, doctor):
        self.doctor = doctor

    def find_doctor(self, crm, uf):
        return self.doctor


def test_comparacao_de_nome_ignora_maiusculas_acentos_e_espacos():
    xml = soap_response(
        "<crm>123456</crm><nome>José  da Silva</nome><situacao>A</situacao><tipoInscricao>P</tipoInscricao><uf>SP</uf>"
    )
    service, client = service_with_response(xml)
    try:
        official_doctor = service.find_doctor("123456", "SP")
    finally:
        client.close()

    verifier = DoctorVerificationService(StubCFMService(official_doctor))
    assert verifier.verify("  JOSE DA SILVA ", "123456", "SP") == official_doctor


def test_comparacao_de_nome_rejeita_pessoas_diferentes():
    xml = soap_response(
        "<crm>123456</crm><nome>José da Silva</nome><situacao>A</situacao><tipoInscricao>P</tipoInscricao><uf>SP</uf>"
    )
    service, client = service_with_response(xml)
    try:
        official_doctor = service.find_doctor("123456", "SP")
    finally:
        client.close()

    verifier = DoctorVerificationService(StubCFMService(official_doctor))
    with pytest.raises(DoctorNameMismatch):
        verifier.verify("José Carlos da Silva", "123456", "SP")


def test_verificacao_rejeita_situacao_diferente_de_regular():
    xml = soap_response(
        "<crm>123456</crm><nome>José da Silva</nome><situacao>L</situacao><tipoInscricao>P</tipoInscricao><uf>SP</uf>"
    )
    service, client = service_with_response(xml)
    try:
        official_doctor = service.find_doctor("123456", "SP")
    finally:
        client.close()

    verifier = DoctorVerificationService(StubCFMService(official_doctor))
    with pytest.raises(DoctorIrregular):
        verifier.verify("José da Silva", "123456", "SP")
