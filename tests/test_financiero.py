"""
tests/test_motor_financiero.py
==============================
Casos de prueba del motor financiero SICAP.

Cada caso tiene valores esperados calculados manualmente con las
fórmulas del libro Senmache (2025), capítulos 4, 7, 8 y 9.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import date

from services.motor_financiero import (
    calcular_motor_sicap,
    _m1_convertir_tasas,
    _m3_compra_inteligente,
    _cuota_francesa,
    TIPO_GRACIA_TOTAL,
    TIPO_GRACIA_PARCIAL,
    TIPO_NORMAL,
    TIPO_BALON,
)


def _d(v) -> Decimal:
    return Decimal(str(v))


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 1: Conversión de tasas
# ══════════════════════════════════════════════════════════════════════════════

def test_tea_a_tem():
    """TEA 12% → TEM esperada ≈ 0.94888% (Fórmula N°19)."""
    tea, tem = _m1_convertir_tasas("TEA", _d("0.12"), None)
    assert tea == _d("0.12000000"), f"TEA debe mantenerse: {tea}"
    # (1.12)^(1/12) - 1 = 0.00948879...
    assert abs(tem - _d("0.00948879")) < _d("0.000001"), f"TEM incorrecta: {tem}"


def test_tna_a_tea_mensual():
    """TNA 12% capitalización mensual (m=12) → TEA ≈ 12.6825%."""
    tea, tem = _m1_convertir_tasas("TNA", _d("0.12"), 12)
    # TEA = (1 + 0.12/12)^12 - 1 = 0.126825...
    assert abs(tea - _d("0.12682503")) < _d("0.000001"), f"TEA incorrecta: {tea}"


def test_tna_capitalizacion_diaria():
    """TNA 12% capitalización diaria (m=360) → TEA ≈ 12.7475%."""
    tea, tem = _m1_convertir_tasas("TNA", _d("0.12"), 360)
    # TEA = (1 + 0.12/360)^360 - 1 = 0.127475...
    assert abs(tea - _d("0.12747459")) < _d("0.000001"), f"TEA incorrecta: {tea}"


# ══════════════════════════════════════════════════════════════════════════════
# Cuota francesa simple
# ══════════════════════════════════════════════════════════════════════════════

def test_cuota_francesa_basica():
    """
    Caso del libro ejercicio 7-1:
    Préstamo USD 33,759.20 (42,199 × 80%), TEA 7.5%, 36 meses.
    Cuota esperada ≈ USD 1,046.31
    """
    _, tem = _m1_convertir_tasas("TEA", _d("0.075"), None)
    cuota = _cuota_francesa(_d("33759.20"), tem, 36)
    assert abs(cuota - _d("1046.31")) < _d("0.50"), f"Cuota incorrecta: {cuota}"


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 3: Compra Inteligente
# ══════════════════════════════════════════════════════════════════════════════

def test_compra_inteligente_sin_balon():
    """Con cuota_balon_pct = 0, el PV* debe ser igual al saldo."""
    _, tem = _m1_convertir_tasas("TEA", _d("0.12"), None)
    saldo = _d("50000.00")
    cb, vp_cb, pv_star = _m3_compra_inteligente(saldo, _d("0"), tem, 36)
    assert cb == _d("0.00"), "Sin balón, CB debe ser 0"
    assert pv_star == saldo, "Sin balón, PV* debe ser igual al saldo"


def test_compra_inteligente_30pct():
    """
    Saldo 50,000, balón 30%, TEA 12%, n=36.
    CB = 15,000
    VP_CB = 15,000 / (1 + TEM)^36
    PV* = 50,000 - VP_CB
    La cuota debe ser menor que sin balón.
    """
    _, tem = _m1_convertir_tasas("TEA", _d("0.12"), None)
    saldo = _d("50000.00")
    cb, vp_cb, pv_star = _m3_compra_inteligente(saldo, _d("0.30"), tem, 36)

    assert cb == _d("15000.00"), f"Balón incorrecto: {cb}"
    assert vp_cb < cb, "El VP del balón debe ser menor al monto del balón"
    assert pv_star < saldo, "PV* debe ser menor al saldo (se descuenta el balón)"

    cuota_con_balon = _cuota_francesa(pv_star, tem, 36)
    cuota_sin_balon = _cuota_francesa(saldo, tem, 36)
    assert cuota_con_balon < cuota_sin_balon, "La cuota con balón debe ser menor"


# ══════════════════════════════════════════════════════════════════════════════
# Motor completo: caso estándar sin gracia ni balón
# ══════════════════════════════════════════════════════════════════════════════

def test_motor_basico_sin_extras():
    """
    Caso base: precio S/50,000, cuota inicial S/10,000, plazo 24 meses,
    TEA 12%, sin gracia, sin balón, seguros mínimos, sin portes.
    Verifica que el saldo final del cronograma sea ≈ 0.
    """
    resultado = calcular_motor_sicap(
        precio_base=50000,
        cuota_inicial_monto=10000,
        plazo_meses=24,
        tipo_tasa="TEA",
        tasa_valor=0.12,
        capitalizacion_m=None,
        periodos_gracia_total=0,
        periodos_gracia_parcial=0,
        cuota_balon_pct=0,
        seguro_vehicular_pct=0.0050,
        seguro_desgravamen_pct=0.0004,
        costo_portes=0,
        costo_comisiones=0,
        fecha_inicio=date(2025, 1, 1),
    )

    assert resultado.monto_financiado == _d("40000.00")
    assert len(resultado.cronograma) == 24

    # El saldo final de la última cuota debe ser 0 (o muy cercano)
    saldo_final = resultado.cronograma[-1].saldo_final
    assert abs(saldo_final) < _d("1.00"), f"Saldo final no convergió a 0: {saldo_final}"

    # Todos los períodos deben ser NORMAL
    for fila in resultado.cronograma:
        assert fila.tipo_periodo == TIPO_NORMAL

    # La TCEA debe ser mayor que la TEA (incluye seguros)
    assert resultado.tcea > resultado.tea_efectiva, "TCEA debe ser > TEA"

    print(f"\n[Motor básico]")
    print(f"  Monto financiado : S/ {resultado.monto_financiado}")
    print(f"  Cuota ordinaria  : S/ {resultado.cuota_ordinaria}")
    print(f"  TEA              : {resultado.tea_efectiva:.6%}")
    print(f"  TCEA             : {resultado.tcea:.6%}")
    print(f"  VAN              : S/ {resultado.van}")
    print(f"  TIR mensual      : {resultado.tir_mensual:.8%}")


# ══════════════════════════════════════════════════════════════════════════════
# Motor completo: con períodos de gracia
# ══════════════════════════════════════════════════════════════════════════════

def test_motor_gracia_total():
    """
    Gracia total: 2 meses de gracia total + 22 meses ordinarios = 24 total.
    Las 2 primeras filas deben ser GRACIA_T con cuota_total = 0.
    El saldo al final de gracia debe ser mayor al inicial (capitalización).
    """
    resultado = calcular_motor_sicap(
        precio_base=50000,
        cuota_inicial_monto=10000,
        plazo_meses=24,
        tipo_tasa="TEA",
        tasa_valor=0.12,
        capitalizacion_m=None,
        periodos_gracia_total=2,
        periodos_gracia_parcial=0,
        cuota_balon_pct=0,
        seguro_vehicular_pct=0.0050,
        seguro_desgravamen_pct=0.0004,
        costo_portes=3.50,
        costo_comisiones=0,
        fecha_inicio=date(2025, 1, 1),
    )

    assert len(resultado.cronograma) == 24

    # Filas de gracia
    fila_g1 = resultado.cronograma[0]
    fila_g2 = resultado.cronograma[1]
    assert fila_g1.tipo_periodo == TIPO_GRACIA_TOTAL
    assert fila_g2.tipo_periodo == TIPO_GRACIA_TOTAL
    assert fila_g1.cuota_total == _d("0.00"), "En gracia total no se paga nada"
    assert fila_g2.cuota_total == _d("0.00")
    assert fila_g2.saldo_inicial > _d("40000.00"), "Saldo debe crecer por capitalización"

    # Filas ordinarias
    for fila in resultado.cronograma[2:]:
        assert fila.tipo_periodo == TIPO_NORMAL

    saldo_final = resultado.cronograma[-1].saldo_final
    assert abs(saldo_final) < _d("1.00"), f"Saldo final no es 0: {saldo_final}"

    print(f"\n[Gracia total 2 meses]")
    print(f"  Saldo tras gracia: S/ {resultado.cronograma[1].saldo_final}")
    print(f"  Cuota ordinaria  : S/ {resultado.cuota_ordinaria}")


def test_motor_gracia_parcial():
    """
    2 meses de gracia parcial: el cliente paga solo intereses,
    el capital se mantiene igual.
    """
    resultado = calcular_motor_sicap(
        precio_base=50000,
        cuota_inicial_monto=10000,
        plazo_meses=24,
        tipo_tasa="TEA",
        tasa_valor=0.12,
        capitalizacion_m=None,
        periodos_gracia_total=0,
        periodos_gracia_parcial=2,
        cuota_balon_pct=0,
        seguro_vehicular_pct=0.0050,
        seguro_desgravamen_pct=0.0004,
        costo_portes=3.50,
        costo_comisiones=0,
        fecha_inicio=date(2025, 1, 1),
    )

    fila_p1 = resultado.cronograma[0]
    fila_p2 = resultado.cronograma[1]
    assert fila_p1.tipo_periodo == TIPO_GRACIA_PARCIAL
    assert fila_p2.tipo_periodo == TIPO_GRACIA_PARCIAL
    assert fila_p1.amortizacion == _d("0.00"), "En gracia parcial no hay amortización"
    # El saldo inicial del período 2 debe ser igual al saldo final del período 1
    assert fila_p1.saldo_final == fila_p2.saldo_inicial, "Capital no debe cambiar en gracia parcial"
    # La cuota es solo interés + seguros + portes (> 0)
    assert fila_p1.cuota_total > _d("0.00"), "En gracia parcial sí se paga (intereses)"

    print(f"\n[Gracia parcial 2 meses]")
    print(f"  Cuota mes 1 (gracia): S/ {fila_p1.cuota_total}")
    print(f"  Saldo mes 1 final   : S/ {fila_p1.saldo_final}")


# ══════════════════════════════════════════════════════════════════════════════
# Motor completo: con Compra Inteligente (balón)
# ══════════════════════════════════════════════════════════════════════════════

def test_motor_compra_inteligente():
    """
    Balón 30%: la cuota ordinaria debe ser notablemente menor,
    y la última fila debe ser tipo BALON con cuota_total alta.
    """
    sin_balon = calcular_motor_sicap(
        precio_base=50000,
        cuota_inicial_monto=10000,
        plazo_meses=24,
        tipo_tasa="TEA",
        tasa_valor=0.12,
        capitalizacion_m=None,
        periodos_gracia_total=0,
        periodos_gracia_parcial=0,
        cuota_balon_pct=0,
        seguro_vehicular_pct=0.0050,
        seguro_desgravamen_pct=0.0004,
        costo_portes=3.50,
        costo_comisiones=0,
    )

    con_balon = calcular_motor_sicap(
        precio_base=50000,
        cuota_inicial_monto=10000,
        plazo_meses=24,
        tipo_tasa="TEA",
        tasa_valor=0.12,
        capitalizacion_m=None,
        periodos_gracia_total=0,
        periodos_gracia_parcial=0,
        cuota_balon_pct=0.30,
        seguro_vehicular_pct=0.0050,
        seguro_desgravamen_pct=0.0004,
        costo_portes=3.50,
        costo_comisiones=0,
    )

    assert con_balon.cuota_ordinaria < sin_balon.cuota_ordinaria, \
        "Compra Inteligente debe reducir la cuota ordinaria"

    ultima_fila = con_balon.cronograma[-1]
    assert ultima_fila.tipo_periodo == TIPO_BALON, "La última fila debe ser BALON"
    assert ultima_fila.cuota_total > sin_balon.cronograma[-1].cuota_total, \
        "La cuota final con balón debe ser mayor"

    print(f"\n[Compra Inteligente 30%]")
    print(f"  Cuota sin balón  : S/ {sin_balon.cuota_ordinaria}")
    print(f"  Cuota con balón  : S/ {con_balon.cuota_ordinaria}")
    print(f"  Monto balón      : S/ {con_balon.cuota_balon_monto}")
    print(f"  Cuota final      : S/ {ultima_fila.cuota_total}")


# ══════════════════════════════════════════════════════════════════════════════
# Runner manual
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        test_tea_a_tem,
        test_tna_a_tea_mensual,
        test_tna_capitalizacion_diaria,
        test_cuota_francesa_basica,
        test_compra_inteligente_sin_balon,
        test_compra_inteligente_30pct,
        test_motor_basico_sin_extras,
        test_motor_gracia_total,
        test_motor_gracia_parcial,
        test_motor_compra_inteligente,
    ]

    pasados = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            pasados += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"Resultado: {pasados}/{len(tests)} tests pasados")