# 🚀 Missão 05: Relacionamentos (User ↔ Doctor)

## Objetivo

Adicionar um modelo `Doctor` (Médico) e estabelecer um relacionamento entre usuários e médicos.

- Um **User** pode ter um **Doctor** associado (1:1 ou 1:N)
- Médicos com informações específicas (CRM, especialidade)

---

## O que será implementado

### 1. Novo modelo: Doctor

```python
class Doctor(Base):
    __tablename__ = "doctors"
    
    id: int                    # PRIMARY KEY
    user_id: int               # FOREIGN KEY → users.id
    crm: str                   # Conselho Regional de Medicina
    especialidade: str         # Ex: Cardiologia, Pediatria
    created_at: datetime       # Timestamp
    
    # Relacionamento com User
    user: Relationship("User")
```

### 2. Atualizar modelo User

```python
class User(Base):
    __tablename__ = "users"
    
    id: int
    name: str
    password: str
    
    # Novo: relacionamento com Doctor
    doctor: Relationship("Doctor", back_populates="user")
    # ou useless = None se nenhum doctor associado
```

### 3. Schemas Pydantic

```python
class DoctorCreate(BaseModel):
    crm: str  # min_length=8
    especialidade: str
    user_id: int

class DoctorResponse(BaseModel):
    id: int
    crm: str
    especialidade: str
    user_id: int
    
    model_config = {"from_attributes": True}

class UserWithDoctor(BaseModel):
    id: int
    name: str
    doctor: DoctorResponse | None = None  # Pode não ter doctor
```

### 4. Novas rotas

```python
# Criar médico para um usuário
POST /doctors
Body: {"crm": "123456/SP", "especialidade": "Cardiologia", "user_id": 1}
Response: 201 Created

# Listar todos os médicos
GET /doctors
Response: 200 OK → [{"id": 1, "crm": "...", ...}]

# Buscar um médico
GET /doctors/{doctor_id}
Response: 200 OK ou 404

# Atualizar médico
PUT /doctors/{doctor_id}
Response: 200 OK ou 404

# Deletar médico
DELETE /doctors/{doctor_id}
Response: 204 ou 404

# Buscar usuário com seus dados de médico
GET /users/{user_id}/doctor
Response: 200 OK → {"id": 1, "name": "Alice", "doctor": {"crm": "..."}}
```

---

## Estrutura do banco de dados

```
ANTES (apenas User):
┌────────────────────┐
│      users         │
├────────────────────┤
│ id (PK)            │
│ name               │
│ password           │
└────────────────────┘

DEPOIS (User + Doctor com FK):
┌────────────────────┐         ┌─────────────────────┐
│      users         │ 1  ∞    │     doctors         │
├────────────────────┤         ├─────────────────────┤
│ id (PK)            │◄────────│ user_id (FK)        │
│ name               │         │ id (PK)             │
│ password           │         │ crm                 │
└────────────────────┘         │ especialidade       │
                                │ created_at          │
                                └─────────────────────┘
```

### SQL que será gerado

```sql
-- Tabela Users (já existe)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Nova tabela Doctors
CREATE TABLE doctors (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    crm VARCHAR(20) NOT NULL UNIQUE,
    especialidade VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

> **ON DELETE CASCADE:** Se um usuário for deletado, seu médico também será

---

## Passo a passo de implementação

### Passo 1: Atualizar models.py

```python
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Relationship
from datetime import datetime

# Adicionar ao User:
class User(Base):
    # ... campos anteriores ...
    doctor: Relationship["Doctor"] = Relationship(back_populates="user")

# Adicionar novo modelo:
class Doctor(Base):
    __tablename__ = "doctors"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    crm: Mapped[str] = mapped_column(String(20), unique=True)
    especialidade: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user: Relationship["User"] = Relationship(back_populates="doctor")

# Adicionar schemas:
class DoctorCreate(BaseModel):
    crm: str  # Validator: min_length=8
    especialidade: str  # Validator: min_length=3
    user_id: int

class DoctorResponse(BaseModel):
    id: int
    crm: str
    especialidade: str
    user_id: int
    
    model_config = {"from_attributes": True}
```

### Passo 2: Adicionar rotas em main.py

```python
@app.post("/doctors", status_code=201)
def create_doctor(doctor: DoctorCreate, db: Session) -> DoctorResponse:
    # 1. Validar que user existe
    user = db.query(User).filter(User.id == doctor.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario não encontrado")
    
    # 2. Criar doctor
    db_doctor = Doctor(**doctor.dict())
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    
    return DoctorResponse.model_validate(db_doctor)

@app.get("/doctors")
def list_doctors(db: Session) -> list[DoctorResponse]:
    doctors = db.query(Doctor).all()
    return [DoctorResponse.model_validate(d) for d in doctors]

@app.get("/doctors/{doctor_id}")
def get_doctor(doctor_id: int, db: Session) -> DoctorResponse:
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Medico não encontrado")
    return DoctorResponse.model_validate(doctor)

@app.put("/doctors/{doctor_id}")
def update_doctor(doctor_id: int, doctor: DoctorCreate, db: Session) -> DoctorResponse:
    db_doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not db_doctor:
        raise HTTPException(status_code=404, detail="Medico não encontrado")
    
    db_doctor.crm = doctor.crm
    db_doctor.especialidade = doctor.especialidade
    db.commit()
    db.refresh(db_doctor)
    
    return DoctorResponse.model_validate(db_doctor)

@app.delete("/doctors/{doctor_id}", status_code=204)
def delete_doctor(doctor_id: int, db: Session):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Medico não encontrado")
    db.delete(doctor)
    db.commit()
```

### Passo 3: Atualizar testes

```python
def test_cria_doctor(client):
    # Primeiro criar um usuário
    user_response = client.post("/users", json={"name": "Dr. Silva", "password": "senha123"})
    user_id = user_response.json()["id"]
    
    # Depois criar um doctor
    response = client.post("/doctors", json={
        "crm": "12345678",
        "especialidade": "Cardiologia",
        "user_id": user_id
    })
    
    assert response.status_code == 201
    assert response.json()["crm"] == "12345678"

def test_nao_cria_doctor_para_user_inexistente(client):
    response = client.post("/doctors", json={
        "crm": "12345678",
        "especialidade": "Cardiologia",
        "user_id": 9999
    })
    assert response.status_code == 404

def test_lista_doctors(client):
    response = client.get("/doctors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# ... mais testes para PUT e DELETE
```

### Passo 4: Testar

```bash
uv run pytest -v
```

Esperado: novos testes passam (provavelmente 18+ testes no total)

---

## Desafios adicionais (bônus)

1. **Validação de CRM:** Usar um validator Pydantic para validar formato CRM (ex: `12345678/SP`)
2. **Cascade delete:** Verificar que deleting user também deleta seu doctor
3. **Unique constraint:** Garantir que cada user tem no máximo 1 doctor
4. **Timestamp:** Adicionar `updated_at` ao doctor
5. **Rota combinada:** `GET /users/{id}` retornar dados do doctor se houver

---

## Referência: SQLAlchemy Relationships

```python
# 1:1 Relationship
class User(Base):
    doctor: Relationship["Doctor"] = Relationship(
        back_populates="user",
        uselist=False  # ← Apenas um doctor por user
    )

# 1:N Relationship (um user, muitos appointments)
class User(Base):
    appointments: Relationship["Appointment"] = Relationship(
        back_populates="user",
        uselist=True  # ← Lista de appointments
    )
```

---

## Próximo: Missão 06 (Autenticação)

Depois de completar a Missão 05, você terá:
- ✅ Modelos relacionados
- ✅ Rotas CRUD para doctors
- ✅ Testes de relacionamentos

A Missão 06 vai adicionar:
- JWT tokens para autenticação
- Proteção de rotas (só usuários logados)
- Login e logout

---

**Comece quando estiver pronto!** 🚀

