from pydantic import BaseModel, field_validator, model_validator
from decimal import Decimal
from typing import List, Optional
from datetime import date, datetime


# ── Cronograma (output) ────────────────────────────────────────────────────────

class CronogramaOut(BaseModel):
    nro_cuota: int
    fecha_vencimiento: Optional[date]
    tipo_periodo: str          # 'GRACIA_T' | 'GRACIA_P' | 'NORMAL' | 'BALON'
    saldo_inicial: Decimal
    interes: Decimal
    amortizacion: Decimal
    seguro_desgravamen: Decimal
    seguro_vehicular: Decimal
    portes: Decimal
    comision: Decimal
    cuota_total: Decimal
    saldo_final: Decimal

    model_config = {"from_attributes": True}


# ── Simulación: entrada ────────────────────────────────────────────────────────

class SimulacionCreate(BaseModel):
    # Entidades relacionadas
    cliente_id: int
    vehiculo_id: int
    banco_id: int
    moneda_id: int

    # Cuota inicial (monto fijo, no porcentaje)
    cuota_inicial_monto: Decimal

    # Parámetros del crédito
    plazo_meses: int
    tipo_tasa: str          # 'TEA' | 'TNA'
    tasa_valor: Decimal     # decimal puro, ej. 0.1200 = 12%
    capitalizacion_m: Optional[int] = None  # obligatorio si tipo_tasa == 'TNA'

    # Períodos de gracia
    periodos_gracia_total: int = 0
    periodos_gracia_parcial: int = 0

    # Compra Inteligente
    cuota_balon_pct: Decimal = Decimal("0.00")  # 0.30 = 30%

    # Costos periódicos
    seguro_vehicular_pct: Decimal    # % mensual sobre saldo, ej. 0.0050
    seguro_desgravamen_pct: Decimal  # % mensual sobre saldo, ej. 0.0004
    costo_portes: Decimal = Decimal("0.00")
    costo_comisiones: Decimal = Decimal("0.00")

    # Fecha de inicio para calcular fechas de vencimiento
    fecha_inicio: date

    @field_validator("tipo_tasa")
    @classmethod
    def tipo_tasa_valido(cls, v: str) -> str:
        if v.upper() not in ("TEA", "TNA"):
            raise ValueError("El tipo de tasa debe ser 'TEA' o 'TNA'")
        return v.upper()

    @field_validator("plazo_meses")
    @classmethod
    def plazo_valido(cls, v: int) -> int:
        if not (12 <= v <= 60):
            raise ValueError("El plazo debe estar entre 12 y 60 meses")
        if v % 12 != 0:
            raise ValueError("El plazo debe ser múltiplo de 12")
        return v

    @field_validator("tasa_valor")
    @classmethod
    def tasa_positiva(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("La tasa debe ser mayor a 0")
        return v

    @field_validator("cuota_balon_pct")
    @classmethod
    def balon_rango(cls, v: Decimal) -> Decimal:
        if not (Decimal("0.00") <= v <= Decimal("0.50")):
            raise ValueError("El porcentaje de cuota balón debe estar entre 0% y 50%")
        return v
    
    
    @field_validator("cuota_inicial_monto", "costo_portes", "costo_comisiones")
    @classmethod
    def montos_no_negativos(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Los montos no pueden ser negativos")
        return v

    @field_validator("periodos_gracia_total", "periodos_gracia_parcial")
    @classmethod
    def periodos_gracia_rango(cls, v: int) -> int:
        if not (0 <= v <= 6):
            raise ValueError("Los periodos de gracia deben estar entre 0 y 6 meses")
        return v

    @field_validator("seguro_vehicular_pct", "seguro_desgravamen_pct")
    @classmethod
    def seguros_rango(cls, v: Decimal) -> Decimal:
        if not (Decimal("0.0000") <= v <= Decimal("0.0100")):
            raise ValueError("Los seguros deben estar entre 0% y 1% mensual")
        return v
    

    @model_validator(mode="after")
    def validar_capitalizacion_y_gracia(self) -> "SimulacionCreate":
        # Si es TNA, capitalizacion_m es obligatorio
        if self.tipo_tasa == "TNA" and self.capitalizacion_m is None:
            raise ValueError("capitalizacion_m es obligatorio cuando tipo_tasa = 'TNA'")
        if self.capitalizacion_m is not None and self.capitalizacion_m not in (1, 2, 4, 12, 360):
            raise ValueError("capitalizacion_m debe ser 1, 2, 4, 12 ó 360")

        # Gracia no puede superar el plazo
        total_gracia = self.periodos_gracia_total + self.periodos_gracia_parcial
        if total_gracia >= self.plazo_meses:
            raise ValueError(
                "La suma de períodos de gracia debe ser menor que el plazo total"
            )
        return self


# ── Simulación: salida (resumen) ───────────────────────────────────────────────

class SimulacionOut(BaseModel):
    id: int
    cliente_id: int
    vehiculo_id: int
    banco_id: int
    moneda_id: int
    monto_financiado: Decimal
    cuota_balon_monto: Decimal
    tea_efectiva: Decimal
    tasa_mensual: Decimal
    cuota_ordinaria: Decimal
    van: Decimal
    tir_mensual: Decimal
    tcea: Decimal
    total_intereses: Decimal
    total_seguros: Decimal
    total_portes: Decimal
    costo_total_credito: Decimal
    fecha_inicio: date
    fecha_simulacion: datetime
    cronograma: List[CronogramaOut] = []

    model_config = {"from_attributes": True}


class SimulacionResumen(BaseModel):
    """Para listados (sin cronograma detallado)."""
    id: int
    cliente_id: int
    vehiculo_id: int
    monto_financiado: Decimal
    plazo_meses: int
    tea_efectiva: Decimal
    tcea: Decimal
    cuota_ordinaria: Decimal
    fecha_simulacion: datetime

    model_config = {"from_attributes": True}