from pydantic import BaseModel, EmailStr
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

# --- USUARIOS ---
class UsuarioBase(BaseModel):
    username: str
    nombre_completo: str
    email: EmailStr
    dni: str

class UsuarioCreate(UsuarioBase):
    password: str # El Frontend envía esto para registrar

class Usuario(UsuarioBase):
    id: int
    class Config: from_attributes = True

class UsuarioLogin(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    mensaje: str
    usuario_id: int
    username: str
    nombre_completo: str

# --- BANCOS Y CRONOGRAMA ---
class Banco(BaseModel):
    id: int
    nombre_banco: str
    class Config: from_attributes = True

class Cronograma(BaseModel):
    nro_cuota: int
    saldo_inicial: Decimal
    amortizacion: Decimal
    interes: Decimal
    seguro_desgravamen: Decimal
    seguro_vehicular: Decimal
    comision_cuota: Decimal
    portes_cuota: Decimal
    cuota_total: Decimal
    saldo_final: Decimal
    class Config: from_attributes = True

# --- SIMULACIONES ---
class SimulacionCreate(BaseModel):
    usuario_id: int
    banco_id: int
    moneda_id: int
    marca_vehiculo: str
    modelo_vehiculo: str
    anio_vehiculo: int
    precio_venta: Decimal
    cuota_inicial_pct: Decimal
    plazo_meses: int
    tasa_valor: Decimal
    tipo_tasa: str
    capitalizacion: str
    tipo_periodo_gracia: str
    meses_gracia: int
    cuota_balon_pct: Decimal
    # --- ESTO FALTABA PARA TU FRONTEND ---
    seguro_desgravamen_pct: Decimal
    seguro_vehicular_pct: Decimal
    costo_portes: Decimal
    costo_comisiones: Decimal

class Simulacion(SimulacionCreate):
    id: int
    monto_prestamo: Decimal
    van: Decimal
    tir: Decimal
    tcea: Decimal
    fecha_simulacion: datetime
    cronograma: List[Cronograma] = []
    class Config: from_attributes = True