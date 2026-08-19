import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models import Base, Doctor, DoctorSpecialty, User


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


def test_medico_pode_ter_varias_especialidades_oficiais(db):
    user = User(
        nome="Ana Souza",
        email="ana@exemplo.com",
        doctor=Doctor(
            crm="123456",
            uf="SP",
            crm_verified=True,
            verification_status="verified",
            specialties=[
                DoctorSpecialty(
                    official_name="CARDIOLOGIA",
                    rqe="1111",
                    official_description="CARDIOLOGIA - RQE Nº: 1111",
                ),
                DoctorSpecialty(
                    official_name="CLÍNICA MÉDICA",
                    rqe="2222",
                    official_description="CLÍNICA MÉDICA - RQE Nº: 2222",
                ),
            ],
        ),
    )
    db.add(user)
    db.commit()

    assert [specialty.rqe for specialty in user.doctor.specialties] == ["1111", "2222"]

    db.delete(user)
    db.commit()
    assert db.scalar(select(DoctorSpecialty)) is None


def test_medico_persiste_dados_pessoais_complementares(db):
    user = User(
        nome="Ana Souza",
        email="ana@exemplo.com",
        doctor=Doctor(
            crm="123456",
            uf="SP",
            cpf="52998224725",
            marital_status="casado",
            mobile_phone="11999998888",
        ),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.doctor.to_dict()["cpf"] == "52998224725"
    assert user.doctor.to_dict()["marital_status"] == "casado"
    assert user.doctor.to_dict()["mobile_phone"] == "11999998888"
