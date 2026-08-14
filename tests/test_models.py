import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models import Base, Doctor, User


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_user_pode_ter_um_perfil_medico(db):
    user = User(nome="Ana Souza", email="ana@exemplo.com")
    user.doctor = Doctor(crm="123456", uf="SP")

    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.doctor is not None
    assert user.doctor.user_id == user.id
    assert user.doctor.crm == "123456"
    assert user.doctor.user is user


def test_usuario_nao_pode_ter_dois_perfis_medicos(db):
    user = User(nome="Ana Souza", email="ana@exemplo.com")
    db.add(user)
    db.commit()

    db.add(Doctor(user_id=user.id, crm="123456", uf="SP"))
    db.commit()
    db.add(Doctor(user_id=user.id, crm="654321", uf="RJ"))

    with pytest.raises(IntegrityError):
        db.commit()


def test_excluir_usuario_remove_seu_perfil_medico(db):
    user = User(
        nome="Ana Souza",
        email="ana@exemplo.com",
        doctor=Doctor(crm="123456", uf="SP"),
    )
    db.add(user)
    db.commit()

    db.delete(user)
    db.commit()

    assert db.scalar(select(Doctor)) is None
