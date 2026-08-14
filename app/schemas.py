from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    nome: str
    email: EmailStr

class UserCreate(UserBase):
    pass