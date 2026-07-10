"""
tests/test_m3_compra_inteligente.py
===================================
Cobertura de ramas de _m3_compra_inteligente (MÓDULO 3 — Cuota Balón).

Ramas cubiertas:
  - Balón = 0            : CB = 0 y PV* == saldo (no se descuenta nada).
  - Balón > 0            : CB > 0, VP_CB < CB y PV* < saldo.
  - base_balon is None   : rama de compatibilidad (usa saldo_efectivo como base).
  - base_balon explícito : balón sobre el capital original (ancla Caso 1).
"""

from decimal import Decimal

from services.motor_financiero import (
    _m1_convertir_tasas,
    _m3_compra_inteligente,
    _cuota_francesa,
)


def _d(v) -> Decimal:
    return Decimal(str(v))


def test_tb09_balon_cero(aprox_monto):
    """TB-09 · balón = 0 · CB = 0 y PV* igual al saldo."""
    _, tem = _m1_convertir_tasas("TEA", _d("0.12"), None)
    saldo = _d("50000.00")
    cb, vp_cb, pv_star = _m3_compra_inteligente(saldo, _d("0"), tem, 36)
    assert float(cb) == aprox_monto(0.00)
    assert float(vp_cb) == aprox_monto(0.00)
    assert pv_star == saldo


def test_tb10_balon_positivo(aprox_monto):
    """TB-10 · balón > 0 (30%) · CB = 15000, VP_CB < CB, PV* < saldo, cuota menor."""
    _, tem = _m1_convertir_tasas("TEA", _d("0.12"), None)
    saldo = _d("50000.00")
    cb, vp_cb, pv_star = _m3_compra_inteligente(saldo, _d("0.30"), tem, 36)

    assert float(cb) == aprox_monto(15000.00)
    assert vp_cb < cb
    assert pv_star < saldo

    cuota_con = _cuota_francesa(pv_star, tem, 36)
    cuota_sin = _cuota_francesa(saldo, tem, 36)
    assert cuota_con < cuota_sin


def test_tb11_base_balon_none(aprox_monto):
    """TB-11 · rama base_balon is None · usa saldo_efectivo como base del balón."""
    _, tem = _m1_convertir_tasas("TEA", _d("0.12"), None)
    saldo = _d("50000.00")
    cb, _, _ = _m3_compra_inteligente(saldo, _d("0.30"), tem, 36, base_balon=None)
    # base = saldo_efectivo = 50000 → CB = 50000 × 0.30 = 15000
    assert float(cb) == aprox_monto(15000.00)


def test_tb12_base_balon_explicita_caso1(aprox_monto):
    """TB-12 · ancla Caso 1 · base 71920, balón 30%, TEA 12.5%, n=60.

    CB = 21576.00, PV* = 59946.85 (valores de la app real).
    """
    _, tem = _m1_convertir_tasas("TEA", _d("0.125"), None)
    saldo = _d("71920.00")
    cb, vp_cb, pv_star = _m3_compra_inteligente(
        saldo, _d("0.30"), tem, 60, base_balon=_d("71920.00")
    )
    assert float(cb) == aprox_monto(21576.00)
    assert float(pv_star) == aprox_monto(59946.85)
    assert float(_cuota_francesa(pv_star, tem, 60)) == aprox_monto(1328.53)
