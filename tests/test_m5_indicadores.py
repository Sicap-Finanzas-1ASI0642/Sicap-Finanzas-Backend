"""
tests/test_m5_indicadores.py
============================
Cobertura de ramas de _m5_indicadores y del solver de TIR:
  - _npv               : VAN a una tasa conocida.
  - _npv_derivada      : signo de la derivada y rama que retorna 0 (guard derivada==0).
  - _biseccion_tir     : convergencia normal + fallback sin cambio de signo (→ 0.01).
  - _m5_indicadores    : TIR financiera y TCEA se calculan por separado.

Nota sobre la rama `derivada == 0` de _biseccion_tir:
    Con flujos reales (FC0 > 0 y al menos un FC negativo) la derivada del VAN
    en el punto medio nunca es exactamente 0, por lo que forzar esa línea dentro
    de _biseccion_tir sería artificioso. El predicado se cubre a nivel de
    _npv_derivada (TB-22), que sí puede devolver 0 y es lo que dispara el guard.
"""

from decimal import Decimal

from services.motor_financiero import (
    _npv,
    _npv_derivada,
    _biseccion_tir,
    _m5_indicadores,
    calcular_motor_sicap,
)


def _d(v) -> Decimal:
    return Decimal(str(v))


def test_tb20_npv_tasa_conocida(aprox_monto):
    """TB-20 · _npv a tasa conocida · VAN de [-1000,500,500,500] al 10% ≈ 243.43."""
    flujos = [_d("-1000"), _d("500"), _d("500"), _d("500")]
    van = _npv(_d("0.10"), flujos)
    assert float(van) == aprox_monto(243.4260)


def test_tb21_npv_derivada_signo():
    """TB-21 · _npv_derivada · con flujos futuros positivos la derivada es < 0."""
    flujos = [_d("-1000"), _d("500"), _d("500"), _d("500")]
    assert _npv_derivada(_d("0.10"), flujos) < _d("0")


def test_tb22_npv_derivada_cero():
    """TB-22 · rama guard · _npv_derivada retorna 0 cuando solo hay FC0 (k=0 se omite)."""
    assert _npv_derivada(_d("0.10"), [_d("100")]) == _d("0")


def test_tb23_biseccion_convergencia(aprox_tasa):
    """TB-23 · convergencia normal · TIR de [-1000, 1100] = 10%."""
    tir = _biseccion_tir([_d("-1000"), _d("1100")])
    assert float(tir) == aprox_tasa(0.10)


def test_tb24_biseccion_fallback_sin_cambio_signo(aprox_tasa):
    """TB-24 · fallback · sin cambio de signo (todos ≥ 0) devuelve 0.01."""
    tir = _biseccion_tir([_d("1000"), _d("500"), _d("500")])
    assert float(tir) == aprox_tasa(0.01)


def test_tb25_tir_financiera_vs_tcea(aprox_tasa):
    """TB-25 · _m5_indicadores · TIR financiera > 0 y TCEA > TIR financiera anualizada."""
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
        costo_portes=3.50,
        costo_comisiones=0,
    )
    tir_fin_anual = (1 + resultado.tir_mensual) ** _d(12) - 1
    assert resultado.tir_mensual > _d("0.00")
    assert resultado.tcea > tir_fin_anual
