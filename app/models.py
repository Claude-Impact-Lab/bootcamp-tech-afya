from sqlalchemy import Column, DateTime, Integer, String

from app.db import Base


class Usuario(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    # Um usuário comum pode ter temporariamente um cadastro médico pendente com
    # o mesmo e-mail. A regra de unicidade é aplicada pelo fluxo de negócio.
    email = Column(String, nullable=False)
    senha = Column(String, nullable=True)
    crm = Column(String, nullable=True)
    uf = Column(String, nullable=True)
    cfm_status = Column(String, nullable=True)
    cfm_validated_at = Column(DateTime(timezone=True), nullable=True)
    cfm_data_inscricao = Column(String, nullable=True)
    cfm_primeira_inscricao_uf = Column(String, nullable=True)
    cfm_tipo_inscricao = Column(String, nullable=True)
    cfm_situacao = Column(String, nullable=True)
    cfm_inscricoes_outros_estados = Column(String, nullable=True)
    cfm_especialidades_areas = Column(String, nullable=True)
    cfm_endereco = Column(String, nullable=True)
    cfm_telefone = Column(String, nullable=True)
    cfm_instituicao_graduacao = Column(String, nullable=True)
    cfm_ano_formatura = Column(String, nullable=True)
