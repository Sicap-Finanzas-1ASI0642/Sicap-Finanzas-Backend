"""
tests/test_m2_gracia.py
=======================
Cobertura de ramas de _m2_aplicar_gracia (MÓDULO 2 — períodos de gracia).

Ramas cubiertas:
  - Sin gracia (0, 0)          : no genera filas, saldo sin cambio.
  - Gracia total               : capitaliza interés, cuota_total = 0, seguros = 0.
  - Gracia parcial             : paga solo interés, capital constante.
  - Combinada total + parcial  : ancla Caso 2 (S₂ tras gracia total, interés parcial).
"""

from decimal import Decimal

from services.motor_financiero import (
    _m2_aplicar_gracia,
    TIPO_GRACIA_TOTAL,
    TIPO_GRACIA_PARCIAL,
)


def _d(v) -> Decimal:
    return Decimal(str(v))


def test_tb13_sin_gracia():
    """TB-13 · sin gracia (0,0) · no hay filas, nro = 0, saldo sin cambio."""
    saldo, nro, filas = _m2_aplicar_gracia(
        saldo_inicial=_d("40000.00"),
        tem=_d("0.00948879"),
        periodos_gracia_total=0,
        periodos_gracia_parcial=0,
        fecha_inicio=None,
        portes=_d("3.50"),
        comision=_d("0.00"),
        seguro_vehicular_pct=_d("0.0005"),
        seguro_desgravamen_pct=_d("0.0004"),
    )
    assert filas == []
    assert nro == 0
    assert saldo == _d("40000.00")


def test_tb14_gracia_total(aprox_monto):
    """TB-14 · gracia total · capitaliza interés, cuota 0, seguros/portes 0."""
    saldo, nro, filas = _m2_aplicar_gracia(
        saldo_inicial=_d("40000.00"),
        tem=_d("0.00948879"),
        periodos_gracia_total=2,
        periodos_gracia_parcial=0,
        fecha_inicio=None,
        portes=_d("3.50"),
        comision=_d("0.00"),
        seguro_vehicular_pct=_d("0.0005"),
        seguro_desgravamen_pct=_d("0.0004"),
    )
    assert len(filas) == 2
    assert nro == 2
    for f in filas:
        assert f.tipo_periodo == TIPO_GRACIA_TOTAL
        assert float(f.cuota_total) == aprox_monto(0.00)
        assert float(f.seguro_vehicular) == aprox_monto(0.00)
        assert float(f.seguro_desgravamen) == aprox_monto(0.00)
        assert float(f.portes) == aprox_monto(0.00)
        assert float(f.comision) == aprox_monto(0.00)
        assert float(f.amortizacion) == aprox_monto(0.00)
    # el saldo crece por capitalización del interés
    assert saldo > _d("40000.00")
    assert filas[1].saldo_inicial > filas[0].saldo_inicial


def test_tb15_gracia_parcial(aprox_monto):
    """TB-15 · gracia parcial · paga solo interés, capital constante."""
    saldo, nro, filas = _m2_aplicar_gracia(
        saldo_inicial=_d("40000.00"),
        tem=_d("0.00948879"),
        periodos_gracia_total=0,
        periodos_gracia_parcial=2,
        fecha_inicio=None,
        portes=_d("3.50"),
        comision=_d("0.00"),
        seguro_vehicular_pct=_d("0.0005"),
        seguro_desgravamen_pct=_d("0.0004"),
    )
    assert len(filas) == 2
    for f in filas:
        assert f.tipo_periodo == TIPO_GRACIA_PARCIAL
        assert float(f.amortizacion) == aprox_monto(0.00)
        # el capital no cambia: saldo_final == saldo_inicial de la fila
        assert f.saldo_final == f.saldo_inicial
        assert f.cuota_total > _d("0.00")
    # el saldo de salida es igual al de entrada (capital intacto)
    assert saldo == _d("40000.00")


def test_tb16_gracia_combinada_caso2(aprox_monto):
    """TB-16 · ancla Caso 2 · gracia total 2 + parcial 1, saldo 29250, TEM 1.25%.

    S tras gracia total ≈ 29985.83 (ancla original 29985.82; Δ +0.01 por
    ROUND_HALF_UP acumulado). Interés de la gracia parcial ≈ 374.82.
    """
    saldo, nro, filas = _m2_aplicar_gracia(
        saldo_inicial=_d("29250.00"),
        tem=_d("0.0125"),
        periodos_gracia_total=2,
        periodos_gracia_parcial=1,
        fecha_inicio=None,
        portes=_d("0.00"),
        comision=_d("0.00"),
        seguro_vehicular_pct=_d("0.0005"),
        seguro_desgravamen_pct=_d("0.0004"),
    )
    assert len(filas) == 3
    assert nro == 3
    assert filas[0].tipo_periodo == TIPO_GRACIA_TOTAL
    assert filas[1].tipo_periodo == TIPO_GRACIA_TOTAL
    assert filas[2].tipo_periodo == TIPO_GRACIA_PARCIAL
    # S₂: saldo al final de la 2ª gracia total
    assert float(filas[1].saldo_final) == aprox_monto(29985.83)
    # interés de la gracia parcial (3ª fila)
    assert float(filas[2].interes) == aprox_monto(374.82)
