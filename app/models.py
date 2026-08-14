from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel, Field, field_validator

Base = declarative_base()


class User(Base):
    """Modelo de usuário no banco de dados."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)


# Schemas Pydantic para validação e serialização
class UserCreate(BaseModel):
    """Dados de entrada para criar um usuário."""
    name: str = Field(min_length=1)
    password: str = Field(min_length=6)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("password must be at least 6 characters")
        return value


class UserResponse(BaseModel):
    """Resposta da API com dados do usuário."""
    id: int
    name: str

    model_config = {"from_attributes": True}
