"""
conftest.py (raíz del proyecto)
===============================
Configuración compartida de pytest para el backend SICAP.

Este archivo, al vivir en la raíz del repositorio (que NO tiene __init__.py),
fija el rootdir de pytest y lo inserta en sys.path en modo *prepend*. Con eso
los tests pueden hacer:

    from services.motor_financiero import calcular_motor_sicap

sin el hack manual `sys.path.insert(...)` que usaba tests/test_financiero.py.

Además expone:
  - Tolerancias de comparación (montos y tasas) como helpers de pytest.approx.
  - Fixtures con los parámetros y resultados de los dos casos ancla validados
    contra la app real (Caso 1 soles con balón; Caso 2 dólares con gracia).
"""

import os
import sys
from decimal import Decimal
from datetime import date

import pytest

# ── Asegurar que la raíz del repo esté en sys.path ─────────────────────────────
# (reemplaza el sys.path.insert manual de los tests individuales)
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.motor_financiero import calcular_motor_sicap  # noqa: E402


# ── Tolerancias de comparación ─────────────────────────────────────────────────
# Montos (S/, US$): 1 céntimo. Tasas (i, TEA, TCEA, TIR): 1e-4.
ABS_MONTO = 0.01
ABS_TASA = 0.0001


@pytest.fixture
def aprox_monto():
    """Comparador de montos con tolerancia absoluta de 0.01.

    Uso:  assert float(res.cuota_ordinaria) == aprox_monto(1328.53)
    """
    def _cmp(valor):
        return pytest.approx(float(valor), abs=ABS_MONTO)
    return _cmp


@pytest.fixture
def aprox_tasa():
    """Comparador de tasas con tolerancia absoluta de 0.0001.

    Uso:  assert float(res.tcea) == aprox_tasa(0.137995)
    """
    def _cmp(valor):
        return pytest.approx(float(valor), abs=ABS_TASA)
    return _cmp


# ── Parámetros de los casos ancla ──────────────────────────────────────────────
# Caso 1: soles, sin gracia, con balón 30%.
#   precio 81920 - cuota inicial 10000 => monto financiado 71920.
CASO_1_PARAMS = dict(
    precio_base=81920,
    cuota_inicial_monto=10000,
    plazo_meses=60,
    tipo_tasa="TEA",
    tasa_valor=0.125,
    capitalizacion_m=None,
    periodos_gracia_total=0,
    periodos_gracia_parcial=0,
    cuota_balon_pct=0.30,
    seguro_vehicular_pct=0.0005,
    seguro_desgravamen_pct=0.0004,
    costo_portes=3.50,
    costo_comisiones=0,
    cok_anual=0.18,
    fecha_inicio=date(2025, 1, 1),
)

# Caso 2: dólares, gracia total 2 + parcial 1, con balón 40%.
#   precio 39250 - cuota inicial 10000 => monto financiado 29250.
CASO_2_PARAMS = dict(
    precio_base=39250,
    cuota_inicial_monto=10000,
    plazo_meses=36,
    tipo_tasa="TNA",
    tasa_valor=0.15,
    capitalizacion_m=12,
    periodos_gracia_total=2,
    periodos_gracia_parcial=1,
    cuota_balon_pct=0.40,
    seguro_vehicular_pct=0.0005,
    seguro_desgravamen_pct=0.0004,
    costo_portes=3.50,
    costo_comisiones=0,
    cok_anual=0.18,
    fecha_inicio=date(2025, 1, 1),
)


@pytest.fixture(scope="session")
def caso_1_params():
    return dict(CASO_1_PARAMS)


@pytest.fixture(scope="session")
def caso_2_params():
    return dict(CASO_2_PARAMS)


@pytest.fixture(scope="session")
def caso_1_resultado():
    """ResultadoMotor del Caso 1 (calculado una sola vez por sesión)."""
    return calcular_motor_sicap(**CASO_1_PARAMS)


@pytest.fixture(scope="session")
def caso_2_resultado():
    """ResultadoMotor del Caso 2 (calculado una sola vez por sesión)."""
    return calcular_motor_sicap(**CASO_2_PARAMS)
