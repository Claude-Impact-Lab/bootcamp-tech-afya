from sqlalchemy import Column, Integer, String

from app.db import Base


class Usuario(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    senha = Column(String, nullable=True)
    crm = Column(String, nullable=True)
    uf = Column(String, nullable=True)
