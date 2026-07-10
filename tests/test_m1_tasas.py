"""
tests/test_m1_tasas.py
======================
Cobertura de ramas de _m1_convertir_tasas (MÓDULO 1 — conversión de tasas).

Ramas cubiertas:
  - Rama TEA  : la tasa ya es efectiva anual, solo se calcula TEM (Fórmula N°19).
  - Rama TNA  : se convierte TNA -> TEA (Fórmula N°18) según capitalización m.
"""

from decimal import Decimal

from services.motor_financiero import _m1_convertir_tasas


def _d(v) -> Decimal:
    return Decimal(str(v))


def test_tb01_rama_tea(aprox_tasa):
    """TB-01 · rama TEA · TEA 12% se mantiene y TEM ≈ 0.94888%."""
    tea, tem = _m1_convertir_tasas("TEA", _d("0.12"), None)
    assert float(tea) == aprox_tasa(0.12)
    assert float(tem) == aprox_tasa(0.00948879)


def test_tb02_rama_tna_mensual(aprox_tasa):
    """TB-02 · rama TNA · TNA 12% cap. mensual (m=12) → TEA ≈ 12.6825%."""
    tea, tem = _m1_convertir_tasas("TNA", _d("0.12"), 12)
    assert float(tea) == aprox_tasa(0.12682503)


def test_tb03_rama_tna_diaria(aprox_tasa):
    """TB-03 · rama TNA (límite de m) · TNA 12% cap. diaria (m=360) → TEA ≈ 12.7474%."""
    tea, tem = _m1_convertir_tasas("TNA", _d("0.12"), 360)
    # Valor real del motor: 0.12747431
    assert float(tea) == aprox_tasa(0.12747431)


def test_tb04_rama_tna_caso2_ancla(aprox_tasa):
    """TB-04 · ancla Caso 2 · TNA 15% m=12 → TEA ≈ 16.0755% y TEM = 1.25% exacta."""
    tea, tem = _m1_convertir_tasas("TNA", _d("0.15"), 12)
    assert float(tea) == aprox_tasa(0.16075452)
    assert float(tem) == aprox_tasa(0.0125)
