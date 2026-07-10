"""
tests/test_validaciones.py
==========================
Validación de la regla de gracia vs plazo en las dos capas del sistema.

  - TB-29 · El schema Pydantic SimulacionCreate SÍ rechaza
            gracia_total + gracia_parcial >= plazo_meses
            (schemas/simulacion.py, model_validator "validar_capitalizacion_y_gracia").

  - TB-30 · El motor calcular_motor_sicap NO valida esa regla (defecto pendiente
            de defense-in-depth). Marcado xfail(strict=True): hoy NO lanza y el
            cronograma queda degenerado (saldo final ≠ 0). El día que se agregue
            el guard al motor este test hará XPASS y, por strict=True, fallará
            para avisar que debe convertirse en un assert normal.
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from schemas.simulacion import SimulacionCreate
from services.motor_financiero import calcular_motor_sicap


def _payload_valido(**overrides):
    base = dict(
        cliente_id=1,
        vehiculo_id=1,
        banco_id=1,
        moneda_id=1,
        cuota_inicial_monto=Decimal("10000"),
        plazo_meses=12,
        tipo_tasa="TEA",
        tasa_valor=Decimal("0.12"),
        periodos_gracia_total=6,
        periodos_gracia_parcial=6,   # 6 + 6 = 12 >= plazo 12 → debe fallar
        cuota_balon_pct=Decimal("0.00"),
        seguro_vehicular_pct=Decimal("0.0005"),
        seguro_desgravamen_pct=Decimal("0.0004"),
        fecha_inicio=date(2025, 1, 1),
    )
    base.update(overrides)
    return base


def test_tb29_schema_rechaza_gracia_mayor_igual_plazo():
    """TB-29 · el schema rechaza gracia_total + gracia_parcial >= plazo."""
    with pytest.raises(ValidationError):
        SimulacionCreate(**_payload_valido())


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Defecto pendiente: el motor no valida gracia_total + gracia_parcial "
        ">= plazo_meses. Hoy no lanza y genera un cronograma degenerado."
    ),
)
def test_tb30_motor_no_valida_gracia_mayor_igual_plazo():
    """TB-30 · comportamiento DESEADO: el motor debería lanzar cuando la gracia
    cubre o supera el plazo. Hoy no lo hace → xfail estricto documenta el defecto.
    """
    with pytest.raises(ValueError):
        calcular_motor_sicap(
            precio_base=50000,
            cuota_inicial_monto=10000,
            plazo_meses=12,
            tipo_tasa="TEA",
            tasa_valor=0.12,
            capitalizacion_m=None,
            periodos_gracia_total=6,
            periodos_gracia_parcial=6,   # 6 + 6 = 12 = plazo → n_ordinario = 0
            cuota_balon_pct=0,
            seguro_vehicular_pct=0.0005,
            seguro_desgravamen_pct=0.0004,
            costo_portes=0,
            costo_comisiones=0,
            fecha_inicio=date(2025, 1, 1),
        )
