from enum import Enum
from pydantic import BaseModel, EmailStr, field_validator


class UserBase(BaseModel):
    nome: str
    email: EmailStr


class UserCreate(UserBase):
    pass


class UF(str, Enum):
    AC = "AC"
    AL = "AL"
    AP = "AP"
    AM = "AM"
    BA = "BA"
    CE = "CE"
    DF = "DF"
    ES = "ES"
    GO = "GO"
    MA = "MA"
    MT = "MT"
    MS = "MS"
    MG = "MG"
    PA = "PA"
    PB = "PB"
    PR = "PR"
    PE = "PE"
    PI = "PI"
    RJ = "RJ"
    RN = "RN"
    RS = "RS"
    RO = "RO"
    RR = "RR"
    SC = "SC"
    SP = "SP"
    SE = "SE"
    TO = "TO"


class DoctorCreate(BaseModel):
    crm: str
    uf: UF

    @field_validator("uf", mode="before")
    @classmethod
    def normalizar_uf(cls, valor):
        if isinstance(valor, str):
            return valor.upper()
        return valor

    @field_validator("crm")
    @classmethod
    def validar_crm(cls, valor):
        if not valor.isdigit():
            raise ValueError("CRM deve conter apenas números")
        if not (4 <= len(valor) <= 7):
            raise ValueError("CRM deve ter entre 4 e 7 dígitos")
        return valor