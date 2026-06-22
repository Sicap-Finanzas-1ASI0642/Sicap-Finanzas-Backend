from pydantic import BaseModel, EmailStr, field_validator
from decimal import Decimal
from typing import Optional
from datetime import datetime
import re


# ── Cliente ────────────────────────────────────────────────────────────────────

class ClienteBase(BaseModel):
    nombre: str
    apellido: str
    dni: str
    email: EmailStr
    telefono: Optional[str] = None
    ingreso_mensual: Decimal

    @field_validator("dni")
    @classmethod
    def dni_valido(cls, v: str) -> str:
        if not re.fullmatch(r"\d{8}", v):
            raise ValueError("El DNI debe tener exactamente 8 dígitos")
        return v

    @field_validator("ingreso_mensual")
    @classmethod
    def ingreso_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El ingreso mensual debe ser mayor a 0")
        return v


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    ingreso_mensual: Optional[Decimal] = None


class ClienteOut(ClienteBase):
    id: int
    fecha_registro: datetime

    model_config = {"from_attributes": True}


# ── Vehículo ───────────────────────────────────────────────────────────────────

class VehiculoBase(BaseModel):
    marca: str
    modelo: str
    anio: int
    condicion: str       # 'nuevo' | 'seminuevo'
    precio_base: Decimal

    @field_validator("condicion")
    @classmethod
    def condicion_valida(cls, v: str) -> str:
        if v.lower() not in ("nuevo", "seminuevo"):
            raise ValueError("La condición debe ser 'nuevo' o 'seminuevo'")
        return v.lower()

    @field_validator("precio_base")
    @classmethod
    def precio_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El precio base debe ser mayor a 0")
        return v

    @field_validator("anio")
    @classmethod
    def anio_valido(cls, v: int) -> int:
        if not (2000 <= v <= 2027):
            raise ValueError("El año debe estar entre 2000 y el año actual + 1")
        return v


class VehiculoCreate(VehiculoBase):
    pass


class VehiculoUpdate(BaseModel):
    marca: Optional[str] = None
    modelo: Optional[str] = None
    anio: Optional[int] = None
    condicion: Optional[str] = None
    precio_base: Optional[Decimal] = None


class VehiculoOut(VehiculoBase):
    id: int
    fecha_registro: datetime

    model_config = {"from_attributes": True}