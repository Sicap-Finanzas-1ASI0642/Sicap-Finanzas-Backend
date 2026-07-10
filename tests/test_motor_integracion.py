"""
tests/test_motor_integracion.py
===============================
Pruebas integradoras de calcular_motor_sicap contra los dos casos ancla
validados corriendo la app real, más la validación de cuota inicial >= precio.

  - TB-26 · CASO 1 : soles, sin gracia, balón 30%.
  - TB-27 · CASO 2 : dólares, gracia total 2 + parcial 1, balón 40%.
  - TB-28 · ValueError cuota_inicial >= precio (motor_financiero.py:571).
"""

from decimal import Decimal

import pytest

from services.motor_financiero import (
    calcular_motor_sicap,
    TIPO_NORMAL,
    TIPO_GRACIA_TOTAL,
    TIPO_GRACIA_PARCIAL,
    TIPO_BALON,
)


def _d(v) -> Decimal:
    return Decimal(str(v))


def test_tb26_caso1_integrador(caso_1_resultado, aprox_monto, aprox_tasa):
    """TB-26 · CASO 1 · MF 71920, TEA 12.5%, plazo 60, balón 30%, COK 18%.

    Anclas de la app real: i=0.986358%, CB=21576.00, PV*≈59946.85,
    cuota=1328.53, TCEA=13.7995%, TIR mensual=0.986358%, VAN=+6569.43,
    saldo final=0.00.
    """
    r = caso_1_resultado
    assert float(r.monto_financiado) == aprox_monto(71920.00)
    assert len(r.cronograma) == 60

    assert float(r.tasa_mensual) == aprox_tasa(0.00986358)
    assert float(r.tea_efectiva) == aprox_tasa(0.125)
    assert float(r.cuota_balon_monto) == aprox_monto(21576.00)
    assert float(r.cuota_ordinaria) == aprox_monto(1328.53)
    assert float(r.tcea) == aprox_tasa(0.13799504)
    assert float(r.tir_mensual) == aprox_tasa(0.00986358)
    assert float(r.van) == aprox_monto(6569.43)

    # todas NORMAL salvo la última que es BALON; el saldo cierra a 0
    for f in r.cronograma[:-1]:
        assert f.tipo_periodo == TIPO_NORMAL
    assert r.cronograma[-1].tipo_periodo == TIPO_BALON
    assert float(r.cronograma[-1].saldo_final) == aprox_monto(0.00)


def test_tb27_caso2_integrador(caso_2_resultado, aprox_monto, aprox_tasa):
    """TB-27 · CASO 2 · MF 29250, TNA 15% m=12, plazo 36, gracia T2+P1, balón 40%.

    Anclas: TEA=16.0755%, i=1.25%, S₂ tras gracia total≈29985.83
    (ancla original 29985.82; Δ +0.01), interés gracia parcial≈374.82,
    cuota ordinaria≈825.90 (ancla original 825.89; Δ +0.01), n=33,
    TIR mensual≈1.25%, VAN≈+279.02.
    """
    r = caso_2_resultado
    assert float(r.monto_financiado) == aprox_monto(29250.00)
    assert len(r.cronograma) == 36

    assert float(r.tea_efectiva) == aprox_tasa(0.16075452)
    assert float(r.tasa_mensual) == aprox_tasa(0.0125)

    # estructura de la gracia
    assert r.cronograma[0].tipo_periodo == TIPO_GRACIA_TOTAL
    assert r.cronograma[1].tipo_periodo == TIPO_GRACIA_TOTAL
    assert r.cronograma[2].tipo_periodo == TIPO_GRACIA_PARCIAL

    # S₂ tras gracia total (valor real 29985.83)
    assert float(r.cronograma[1].saldo_final) == aprox_monto(29985.83)
    # interés de la gracia parcial
    assert float(r.cronograma[2].interes) == aprox_monto(374.82)
    # cuota ordinaria (valor real 825.90)
    assert float(r.cuota_ordinaria) == aprox_monto(825.90)

    assert float(r.tir_mensual) == aprox_tasa(0.0125)
    assert float(r.van) == aprox_monto(279.02)

    # el saldo cierra a 0
    assert float(r.cronograma[-1].saldo_final) == aprox_monto(0.00)


def test_tb28_cuota_inicial_mayor_igual_precio():
    """TB-28 · validación · cuota inicial >= precio lanza ValueError (motor:571)."""
    with pytest.raises(ValueError):
        calcular_motor_sicap(
            precio_base=50000,
            cuota_inicial_monto=50000,   # == precio → monto financiado 0
            plazo_meses=24,
            tipo_tasa="TEA",
            tasa_valor=0.12,
            capitalizacion_m=None,
            periodos_gracia_total=0,
            periodos_gracia_parcial=0,
            cuota_balon_pct=0,
            seguro_vehicular_pct=0.0005,
            seguro_desgravamen_pct=0.0004,
            costo_portes=0,
            costo_comisiones=0,
        )
