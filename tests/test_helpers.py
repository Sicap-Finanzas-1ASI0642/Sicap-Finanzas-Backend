"""
tests/test_helpers.py
=====================
Cobertura de ramas de los helpers puros del motor:
  - _cuota_francesa : caso normal y rama n_restante <= 0 (retorna 0).
  - _fecha_cuota    : rama fecha_inicio None y con fecha (inicio + 30·n días).
"""

from decimal import Decimal
from datetime import date

from services.motor_financiero import (
    _m1_convertir_tasas,
    _cuota_francesa,
    _fecha_cuota,
)


def _d(v) -> Decimal:
    return Decimal(str(v))


# ── _cuota_francesa ────────────────────────────────────────────────────────────

def test_tb05_cuota_francesa_normal(aprox_monto):
    """TB-05 · caso normal (ejercicio libro 7-1) · 33759.20 @ TEA 7.5%, 36m ≈ 1046.31."""
    _, tem = _m1_convertir_tasas("TEA", _d("0.075"), None)
    cuota = _cuota_francesa(_d("33759.20"), tem, 36)
    assert float(cuota) == aprox_monto(1046.31)


def test_tb06_cuota_francesa_n_cero(aprox_monto):
    """TB-06 · rama n_restante <= 0 · retorna 0.00 sin lanzar."""
    _, tem = _m1_convertir_tasas("TEA", _d("0.075"), None)
    assert float(_cuota_francesa(_d("50000"), tem, 0)) == aprox_monto(0.00)
    # también con n negativo cae en la misma rama
    assert float(_cuota_francesa(_d("50000"), tem, -3)) == aprox_monto(0.00)


# ── _fecha_cuota ───────────────────────────────────────────────────────────────

def test_tb07_fecha_cuota_none():
    """TB-07 · rama fecha_inicio is None · retorna None."""
    assert _fecha_cuota(None, 5) is None


def test_tb08_fecha_cuota_con_fecha():
    """TB-08 · con fecha · inicio + 30·n días (base comercial 30/360)."""
    # 3 cuotas × 30 días = 90 días desde 2025-01-01 → 2025-04-01
    assert _fecha_cuota(date(2025, 1, 1), 3) == date(2025, 4, 1)
    assert _fecha_cuota(date(2025, 1, 1), 1) == date(2025, 1, 31)
