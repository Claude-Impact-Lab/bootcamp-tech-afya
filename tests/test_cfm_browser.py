import time
from datetime import date

from app.integrations.cfm_browser import CFMBrowserService
from app.services.cfm import CFMDoctor, CFMSpecialty
from app.services.crm_numbers import crm_digits
from app.services.doctor_verification import DoctorVerificationService


def test_formatacao_do_crm_e_removida_sem_inferir_a_uf():
    assert crm_digits("52106072-4") == "521060724"
    assert crm_digits("123456") == "123456"


def test_parser_extrai_dados_profissionais_retornados_pelo_cfm():
    doctor = CFMBrowserService._parse_payload(
        {
            "dados": [
                {
                    "NM_MEDICO": "Raphael Eli Gomes Costa",
                    "NU_CRM": "1060724",
                    "NU_CRM_NATURAL": "1060724",
                    "SG_UF": "RJ",
                    "SITUACAO": "Regular",
                    "TIPO_INSCRICAO": "Principal",
                    "DT_INSCRICAO": "14/08/2020",
                    "PRIM_INSCRICAO_UF": "SC",
                    "ESPECIALIDADE": "CARDIOLOGIA - RQE Nº: 43892 & CLÍNICA MÉDICA",
                    "NM_INSTITUICAO_GRADUACAO": "Universidade de Exemplo",
                    "DT_GRADUACAO": "2019",
                }
            ]
        },
        "521060724",
        "RJ",
        query_crm="1060724",
        displayed_prefix="52",
    )

    assert doctor is not None
    assert doctor.crm_display == "52106072-4"
    assert doctor.official_name == "Raphael Eli Gomes Costa"
    assert doctor.registration_status == "Regular"
    assert doctor.registration_date == date(2020, 8, 14)
    assert doctor.specialties[0].name == "CARDIOLOGIA"
    assert doctor.specialties[0].rqe == "43892"
    assert doctor.graduation_institution == "Universidade de Exemplo"


def test_validacao_compara_crm_completo_com_retorno_natural_do_rj():
    class BrowserResult:
        def find_doctor(self, crm, uf):
            return CFMBrowserService._parse_payload(
                {
                    "dados": [
                        {
                            "NM_MEDICO": "RAPHAEL ELI GOMES COSTA",
                            "NU_CRM": "1060724",
                            "NU_CRM_NATURAL": "1060724",
                            "SG_UF": "RJ",
                            "SITUACAO": "Regular",
                        }
                    ]
                },
                crm,
                uf,
                query_crm="1060724",
                displayed_prefix="52",
            )

    result = DoctorVerificationService(BrowserResult()).verify(
        "Raphael Eli Gomes Costa", "521060724", "RJ"
    )

    assert result.crm_display == "52106072-4"


def test_servico_aceita_situacao_regular_do_portal():
    class BrowserResult:
        def find_doctor(self, crm, uf):
            return CFMBrowserService._parse_payload(
                {"dados": [{"NM_MEDICO": "Ana Médica", "NU_CRM": crm, "SG_UF": uf, "SITUACAO": "Regular"}]},
                crm,
                uf,
            )

    result = DoctorVerificationService(BrowserResult()).verify("Ana Medica", "123456", "SP")
    assert result.registration_status == "Regular"


def test_parser_nao_aceita_resultado_de_outro_crm_ou_uf():
    payload = {
        "dados": [
            {"NM_MEDICO": "Ana Médica", "NU_CRM": "999999", "SG_UF": "RJ", "SITUACAO": "Regular"}
        ]
    }
    assert CFMBrowserService._parse_payload(payload, "123456", "SP") is None


def test_preparo_preenche_campos_e_clica_uma_unica_vez():
    class Field:
        def __init__(self, *, text="", visible=True, maxlength=None):
            self.value = ""
            self.clicks = 0
            self.text = text
            self.visible = visible
            self.maxlength = maxlength

        def fill(self, value):
            self.value = value

        def input_value(self):
            return self.value

        def count(self):
            return 1

        def is_visible(self):
            return self.visible

        def inner_text(self):
            return self.text

        def get_attribute(self, name):
            return self.maxlength if name == "maxlength" else None

        def scroll_into_view_if_needed(self):
            pass

        def click(self):
            self.clicks += 1

    class Page:
        def __init__(self):
            self.crm = Field(maxlength="7")
            self.button = Field()
            self.prefix = Field(text="52", visible=False)
            self.uf = ""
            self.waits = []

        def wait_for_selector(self, selector, **kwargs):
            self.waits.append((selector, kwargs))

        def locator(self, selector):
            if selector == "#crm":
                return self.crm
            if selector == ".basic-addon":
                return self.prefix
            return self.button

        def select_option(self, selector, value):
            self.uf = value

        def input_value(self, selector):
            return self.uf

        def bring_to_front(self):
            pass

    page = Page()
    search_input = CFMBrowserService._prepare_and_submit(page, "123456-7", "sp")

    assert page.crm.value == "1234567"
    assert page.uf == "SP"
    assert page.button.clicks == 1
    assert search_input.query_digits == "1234567"
    assert ("#uf option[value='SP']", {"state": "attached"}) in page.waits


def test_preparo_do_rj_usa_prefixo_exibido_pela_pagina():
    class Field:
        def __init__(self, *, text="", maxlength=None):
            self.value = ""
            self.text = text
            self.maxlength = maxlength
            self.clicks = 0

        def fill(self, value): self.value = value
        def input_value(self): return self.value
        def count(self): return 1
        def is_visible(self): return True
        def inner_text(self): return self.text
        def get_attribute(self, name): return self.maxlength if name == "maxlength" else None
        def scroll_into_view_if_needed(self): pass
        def click(self): self.clicks += 1

    class Page:
        def __init__(self):
            self.crm = Field(maxlength="7")
            self.prefix = Field(text="52")
            self.button = Field()
            self.uf = ""

        def wait_for_selector(self, selector, **kwargs): pass
        def select_option(self, selector, value): self.uf = value
        def input_value(self, selector): return self.uf
        def bring_to_front(self): pass
        def locator(self, selector):
            return {"#crm": self.crm, ".basic-addon": self.prefix}.get(selector, self.button)

    page = Page()
    search_input = CFMBrowserService._prepare_and_submit(page, "521060724", "RJ")

    assert page.crm.value == "1060724"
    assert search_input.displayed_prefix == "52"
    assert search_input.query_digits == "1060724"
    assert page.button.clicks == 1


def test_espera_captcha_sem_realizar_novo_clique():
    responses = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class Page:
        waits = 0

        def is_closed(self):
            return False

        def wait_for_timeout(self, milliseconds):
            self.waits += 1
            if self.waits == 1:
                responses.append(Response("invalidinput"))
            elif self.waits == 2:
                responses.append(Response({"status": True, "dados": []}))

    page = Page()
    payload = CFMBrowserService(timeout_seconds=1)._wait_for_main_payload(
        page, responses, time.monotonic() + 1
    )

    assert payload == {"status": True, "dados": []}
    assert page.waits == 2


def test_resposta_complementar_enriquece_descricao_do_rqe():
    doctor = CFMDoctor(
        crm_display="123456",
        uf="SP",
        official_name="Ana Médica",
        registration_status="Regular",
        registration_type="Principal",
        source_updated_at=None,
        specialties=(CFMSpecialty("CARDIOLOGIA", "43892", "CARDIOLOGIA - RQE Nº: 43892"),),
    )

    result = CFMBrowserService._merge_detail_payload(
        doctor,
        {
            "status": True,
            "dados": [
                {
                    "DS_TP_DOC_ESP": "Título de especialista",
                    "DS_TP_DOC_ESP_RQE": "43892",
                    "AUTORIZACAO_IMAGEM": "S",
                    "CRM": "123456",
                    "UF_CRM": "SP",
                    "HASH": "chave com espaço",
                }
            ],
        },
    )

    assert result.specialties[0].rqe == "43892"
    assert "Título de especialista" in result.specialties[0].official_description
    assert result.photo_url == (
        "https://portal.cfm.org.br/wp-content/themes/portalcfm/assets/php/"
        "foto_medico.php?crm=123456&uf=SP&hash=chave+com+espa%C3%A7o"
    )


def test_foto_nao_e_exposta_quando_o_medico_nao_autoriza():
    doctor = CFMDoctor(
        crm_display="123456",
        uf="SP",
        official_name="Ana Médica",
        registration_status="Regular",
        registration_type="Principal",
        source_updated_at=None,
        specialties=(),
    )

    result = CFMBrowserService._merge_detail_payload(
        doctor,
        {
            "status": True,
            "dados": [
                {
                    "AUTORIZACAO_IMAGEM": "N",
                    "CRM": "123456",
                    "UF_CRM": "SP",
                    "HASH": "segredo",
                }
            ],
        },
    )

    assert result.photo_url is None


def test_foto_e_exposta_quando_cfm_devolve_autorizacao_nula_com_hash_valido():
    doctor = CFMDoctor(
        crm_display="52106072-4",
        uf="RJ",
        official_name="Raphael Eli Gomes Costa",
        registration_status="Regular",
        registration_type="Principal",
        source_updated_at=None,
        specialties=(),
    )

    result = CFMBrowserService._merge_detail_payload(
        doctor,
        {
            "status": True,
            "dados": [
                {
                    "AUTORIZACAO_IMAGEM": None,
                    "CRM": "1060724",
                    "UF_CRM": "RJ",
                    "HASH": "hash-valido",
                }
            ],
        },
    )

    assert result.photo_url == (
        "https://portal.cfm.org.br/wp-content/themes/portalcfm/assets/php/"
        "foto_medico.php?crm=1060724&uf=RJ&hash=hash-valido"
    )
