"""
tests/test_m4_cronograma.py
===========================
Cobertura de ramas de _m4_cronograma (MÓDULO 4 — cronograma francés).

Ramas cubiertas:
  - Cierre de saldo a 0 sin balón (rama es_ultima → tipo NORMAL).
  - Última fila BALON (rama es_ultima con tiene_balon = True).
  - saldo_final acotado por max(saldo_final, 0) → nunca negativo.
"""

from decimal import Decimal

from services.motor_financiero import (
    _m1_convertir_tasas,
    _m3_compra_inteligente,
    _m4_cronograma,
    TIPO_NORMAL,
    TIPO_BALON,
)


def _d(v) -> Decimal:
    return Decimal(str(v))


def _tem12():
    _, tem = _m1_convertir_tasas("TEA", _d("0.12"), None)
    return tem


def test_tb17_cierre_saldo_sin_balon(aprox_monto):
    """TB-17 · cierre a 0 sin balón · 24 filas NORMAL, saldo_final último ≈ 0."""
    tem = _tem12()
    saldo = _d("40000.00")
    filas = _m4_cronograma(
        saldo_post_gracia=saldo,
        pv_ajustado=saldo,          # sin balón: PV* == saldo
        cuota_balon_monto=_d("0.00"),
        tem=tem,
        n_ordinario=24,
        nro_inicio=0,
        fecha_inicio=None,
        seguro_vehicular_pct=_d("0.0005"),
        seguro_desgravamen_pct=_d("0.0004"),
        portes=_d("3.50"),
        comision=_d("0.00"),
    )
    assert len(filas) == 24
    for f in filas:
        assert f.tipo_periodo == TIPO_NORMAL
    assert float(filas[-1].saldo_final) == aprox_monto(0.00)


def test_tb18_ultima_fila_balon(aprox_monto):
    """TB-18 · última fila BALON · con balón > 0 la última fila es tipo BALON."""
    tem = _tem12()
    saldo = _d("40000.00")
    cb, _, pv = _m3_compra_inteligente(saldo, _d("0.30"), tem, 24)
    filas = _m4_cronograma(
        saldo_post_gracia=saldo,
        pv_ajustado=pv,
        cuota_balon_monto=cb,
        tem=tem,
        n_ordinario=24,
        nro_inicio=0,
        fecha_inicio=None,
        seguro_vehicular_pct=_d("0.0005"),
        seguro_desgravamen_pct=_d("0.0004"),
        portes=_d("3.50"),
        comision=_d("0.00"),
    )
    ultima = filas[-1]
    assert ultima.tipo_periodo == TIPO_BALON
    # todas las intermedias son NORMAL
    for f in filas[:-1]:
        assert f.tipo_periodo == TIPO_NORMAL
    # la cuota final (que absorbe el balón) es notablemente mayor a una intermedia
    assert ultima.cuota_total > filas[0].cuota_total


def test_tb19_saldo_final_no_negativo():
    """TB-19 · límite · ninguna fila tiene saldo_final negativo (max(·, 0))."""
    tem = _tem12()
    saldo = _d("40000.00")
    cb, _, pv = _m3_compra_inteligente(saldo, _d("0.30"), tem, 24)
    filas = _m4_cronograma(
        saldo_post_gracia=saldo,
        pv_ajustado=pv,
        cuota_balon_monto=cb,
        tem=tem,
        n_ordinario=24,
        nro_inicio=0,
        fecha_inicio=None,
        seguro_vehicular_pct=_d("0.0005"),
        seguro_desgravamen_pct=_d("0.0004"),
        portes=_d("3.50"),
        comision=_d("0.00"),
    )
    for f in filas:
        assert f.saldo_final >= _d("0.00")
