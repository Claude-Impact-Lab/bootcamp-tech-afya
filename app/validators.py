"""
Validação local de CRM e UF — única fonte de verdade da regra de negócio.

Esta é a Missão 06: validação de formato apenas. Não há consulta ao CFM
nem verificação de existência real do médico (isso é a Missão 07+).
"""

import re

# As 27 UFs válidas do Brasil (26 estados + Distrito Federal).
UFS_VALIDAS: frozenset[str] = frozenset(
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
        "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
        "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
)

# CRM: somente dígitos, de 4 a 20 caracteres (regra já usada no projeto).
CRM_REGEX = re.compile(r"^\d{4,20}$")

# Especialidades disponíveis na Ficha do Médico (Etapa 2).
ESPECIALIDADES_VALIDAS: tuple[str, ...] = (
    "Clínica Médica",
    "Cardiologia",
    "Dermatologia",
    "Endocrinologia",
    "Ginecologia e Obstetrícia",
    "Neurologia",
    "Oftalmologia",
    "Ortopedia",
    "Pediatria",
    "Psiquiatria",
    "Radiologia",
    "Urologia",
    "Cirurgia Geral",
    "Medicina de Família e Comunidade",
    "Medicina Intensiva",
    "Outra",
)

# Idiomas selecionáveis na Ficha do Médico (Etapa 2).
IDIOMAS_VALIDOS: tuple[str, ...] = ("Português", "Inglês", "Espanhol", "Francês")


class RegraInvalidaError(ValueError):
    """Erro de validação de domínio com o campo e a mensagem já formatados."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(message)


def normalizar_uf(uf: str) -> str:
    """Normaliza a UF para maiúsculas e garante que é uma das 27 UFs válidas."""
    uf_normalizada = uf.strip().upper()
    if uf_normalizada not in UFS_VALIDAS:
        raise RegraInvalidaError(
            "uf",
            f"UF '{uf}' inválida. Informe uma sigla de estado brasileiro "
            "existente, por exemplo: SP, RJ ou MG.",
        )
    return uf_normalizada


def normalizar_crm(crm: str) -> str:
    """Remove espaços nas bordas e garante que o CRM tem apenas dígitos (4 a 20)."""
    crm_normalizado = crm.strip()
    if not CRM_REGEX.match(crm_normalizado):
        raise RegraInvalidaError(
            "crm",
            f"CRM '{crm}' inválido. Use somente números, com 4 a 20 dígitos "
            "e sem letras ou símbolos (ex.: 123456).",
        )
    return crm_normalizado


def validar_uf_pydantic(cls, value: str | None) -> str | None:
    """Adaptador reutilizável para uso direto em `field_validator` do Pydantic."""
    if value is None:
        return None
    try:
        return normalizar_uf(value)
    except RegraInvalidaError as erro:
        raise ValueError(erro.message) from erro


def validar_crm_pydantic(cls, value: str | None) -> str | None:
    """Adaptador reutilizável para uso direto em `field_validator` do Pydantic."""
    if value is None:
        return None
    try:
        return normalizar_crm(value)
    except RegraInvalidaError as erro:
        raise ValueError(erro.message) from erro


def campo_obrigatorio_pydantic(mensagem: str):
    """Gera um validador de `field_validator` que rejeita valores em branco."""

    def _validar(cls, value: str) -> str:
        valor_normalizado = value.strip() if isinstance(value, str) else value
        if not valor_normalizado:
            raise ValueError(mensagem)
        return valor_normalizado

    return _validar


def validar_especialidade_pydantic(cls, value: str) -> str:
    """Garante que a especialidade escolhida está na lista centralizada."""
    valor = value.strip() if isinstance(value, str) else value
    if valor not in ESPECIALIDADES_VALIDAS:
        raise ValueError("Selecione uma especialidade válida da lista.")
    return valor


def normalizar_idiomas_pydantic(cls, value: list[str]) -> list[str]:
    """Garante que cada idioma informado está entre os suportados."""
    invalidos = [idioma for idioma in value if idioma not in IDIOMAS_VALIDOS]
    if invalidos:
        raise ValueError(
            f"Idioma(s) inválido(s): {', '.join(invalidos)}. "
            f"Opções válidas: {', '.join(IDIOMAS_VALIDOS)}."
        )
    return value
