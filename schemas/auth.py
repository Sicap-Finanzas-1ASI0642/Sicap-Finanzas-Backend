from pydantic import BaseModel, EmailStr, field_validator
import re


class UsuarioCreate(BaseModel):
    username: str
    nombre_completo: str
    email: EmailStr
    dni: str
    password: str

    @field_validator("dni")
    @classmethod
    def dni_valido(cls, v: str) -> str:
        if not re.fullmatch(r"\d{8}", v):
            raise ValueError("El DNI debe tener exactamente 8 dígitos")
        return v

    @field_validator("password")
    @classmethod
    def password_minimo(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v


class UsuarioOut(BaseModel):
    id: int
    username: str
    nombre_completo: str
    email: str
    dni: str
    activo: bool

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut