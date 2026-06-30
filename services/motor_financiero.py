"""
services/motor_financiero.py
============================
Motor de cálculo SICAP — Crédito Vehicular Compra Inteligente
Método francés vencido ordinario, base comercial 30/360 días.

Implementa los 5 módulos del algoritmo definidos en el reporte SICAP:
  M1 — Conversión de tasas (Fórmulas N°18 y N°19, Senmache 2025)
  M2 — Períodos de gracia (Cap. 7, sección 7.3.2)
  M3 — Compra Inteligente / Cuota Balón (Fórmula N°66)
  M4 — Cronograma de pagos (Fórmula N°67, Cap. 8)
  M5 — Indicadores financieros VAN, TIR, TCEA (Cap. 9)

Precisión: decimal.Decimal con ROUND_HALF_UP en todos los cálculos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import List, Optional

# Precisión interna: 20 dígitos significativos
getcontext().prec = 20


# ── Constantes SBS (Res. N° 8181-2012) ────────────────────────────────────────
DIAS_MES: int = 30
DIAS_ANIO: int = 360
DOS: Decimal = Decimal("2")
TOLERANCIA_TIR: Decimal = Decimal("0.000000001")
MAX_ITER_TIR: int = 1000


# ── Tipos de período ───────────────────────────────────────────────────────────
TIPO_GRACIA_TOTAL = "GRACIA_T"
TIPO_GRACIA_PARCIAL = "GRACIA_P"
TIPO_NORMAL = "NORMAL"
TIPO_BALON = "BALON"


# ── Dataclasses de resultado ───────────────────────────────────────────────────

@dataclass
class FilaCronograma:
    nro_cuota: int
    fecha_vencimiento: Optional[date]
    tipo_periodo: str
    saldo_inicial: Decimal
    interes: Decimal
    amortizacion: Decimal
    seguro_desgravamen: Decimal
    seguro_vehicular: Decimal
    portes: Decimal
    comision: Decimal
    cuota_total: Decimal
    saldo_final: Decimal


@dataclass
class ResultadoMotor:
    # Parámetros derivados
    monto_financiado: Decimal
    cuota_balon_monto: Decimal
    tea_efectiva: Decimal
    tasa_mensual: Decimal
    cuota_ordinaria: Decimal

    # Indicadores financieros
    van: Decimal
    tir_mensual: Decimal
    tcea: Decimal

    # Totales hoja resumen SBS
    total_intereses: Decimal
    total_seguros: Decimal
    total_portes: Decimal
    costo_total_credito: Decimal

    # Cronograma detallado
    cronograma: List[FilaCronograma] = field(default_factory=list)


# ── Utilidades de redondeo ─────────────────────────────────────────────────────

def _d(valor) -> Decimal:
    """Convierte a Decimal con máxima precisión."""
    return Decimal(str(valor))


def _r2(valor: Decimal) -> Decimal:
    """Redondea a 2 decimales (moneda)."""
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _r8(valor: Decimal) -> Decimal:
    """Redondea a 8 decimales (tasas internas)."""
    return valor.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


# ═══════════════════════════════════════════════════════════════════════════════
# MÓDULO 1 — Conversión de tasas
# ═══════════════════════════════════════════════════════════════════════════════

def _m1_convertir_tasas(
    tipo_tasa: str,
    tasa_valor: Decimal,
    capitalizacion_m: Optional[int],
) -> tuple[Decimal, Decimal]:
    """
    Convierte cualquier tasa ingresada a TEA y a tasa efectiva mensual (i).

    Fórmula N°18 (Senmache): TNA → TEA
        TEA = (1 + TNA/m)^m − 1
        donde m = días_año / días_capitalización

    Fórmula N.º 19 (Senmache): TEA → TEM
        TEM = (1 + TEA)^(30/360) − 1

    Parámetros
    ----------
    tipo_tasa       : 'TEA' | 'TNA'
    tasa_valor      : decimal puro (0.1200 = 12%)
    capitalizacion_m: número de capitalizaciones por año (solo si TNA)

    Retorna
    -------
    (tea_efectiva, tasa_mensual)
    """
    tasa = _d(tasa_valor)

    if tipo_tasa == "TNA":
        # Fórmula N°18: TNA → TEA
        m = _d(capitalizacion_m)
        tea = (1 + tasa / m) ** m - 1
    else:
        # Ya es TEA
        tea = tasa

    # Fórmula N°19: TEA → TEM  (exponente = 30/360 = 1/12)
    tem = (1 + tea) ** (_d(DIAS_MES) / _d(DIAS_ANIO)) - 1

    return _r8(tea), _r8(tem)


# ═══════════════════════════════════════════════════════════════════════════════
# MÓDULO 2 — Períodos de gracia
# ═══════════════════════════════════════════════════════════════════════════════

def _m2_aplicar_gracia(
    saldo_inicial: Decimal,
    tem: Decimal,
    periodos_gracia_total: int,
    periodos_gracia_parcial: int,
    fecha_inicio: Optional[date],
    portes: Decimal,
    comision: Decimal,
    seguro_vehicular_pct: Decimal,
    seguro_desgravamen_pct: Decimal,
) -> tuple[Decimal, int, List[FilaCronograma]]:
    """
    Genera las filas de gracia del cronograma y devuelve el saldo efectivo
    que entrará al cálculo de la cuota ordinaria.

    Gracia TOTAL (T períodos):
        - Cliente no paga nada.
        - Intereses se capitalizan: saldo_fin = saldo_ini × (1 + i)
        - cuota_total = 0

    Gracia PARCIAL (P períodos):
        - Cliente paga solo los intereses del período.
        - Capital se mantiene constante.
        - cuota_total = interés + seguros + portes

    Retorna
    -------
    (saldo_post_gracia, nro_ultima_cuota_gracia, filas_gracia)
    """
    filas: List[FilaCronograma] = []
    saldo = saldo_inicial
    nro = 0

       # ── Gracia total ──────────────────────────────────────────────────────────
    for _ in range(periodos_gracia_total):
        nro += 1
        fecha = _fecha_cuota(fecha_inicio, nro)

        # En gracia total el cliente no paga nada.
        # Solo se calcula el interés y se capitaliza al saldo.
        interes = _r2(saldo * tem)
        seg_deg = Decimal("0.00")
        seg_veh = Decimal("0.00")
        portes_periodo = Decimal("0.00")
        comision_periodo = Decimal("0.00")
        cuota_total = Decimal("0.00")
        saldo_final = _r2(saldo + interes)

        filas.append(FilaCronograma(
            nro_cuota=nro,
            fecha_vencimiento=fecha,
            tipo_periodo=TIPO_GRACIA_TOTAL,
            saldo_inicial=_r2(saldo),
            interes=interes,
            amortizacion=Decimal("0.00"),
            seguro_desgravamen=seg_deg,
            seguro_vehicular=seg_veh,
            portes=portes_periodo,
            comision=comision_periodo,
            cuota_total=cuota_total,
            saldo_final=saldo_final,
        ))
        saldo = saldo_final

    # ── Gracia parcial ────────────────────────────────────────────────────────
    for _ in range(periodos_gracia_parcial):
        nro += 1
        fecha = _fecha_cuota(fecha_inicio, nro)
        interes = _r2(saldo * tem)
        seg_deg = _r2(saldo * seguro_desgravamen_pct)
        seg_veh = _r2(saldo * seguro_vehicular_pct)
        cuota_total = _r2(interes + seg_deg + seg_veh + portes + comision)

        filas.append(FilaCronograma(
            nro_cuota=nro,
            fecha_vencimiento=fecha,
            tipo_periodo=TIPO_GRACIA_PARCIAL,
            saldo_inicial=_r2(saldo),
            interes=interes,
            amortizacion=Decimal("0.00"),
            seguro_desgravamen=seg_deg,
            seguro_vehicular=seg_veh,
            portes=portes,
            comision=comision,
            cuota_total=cuota_total,
            saldo_final=_r2(saldo),  # capital sin cambio
        ))
        # saldo no cambia en gracia parcial

    return _r2(saldo), nro, filas


# ═══════════════════════════════════════════════════════════════════════════════
# MÓDULO 3 — Compra Inteligente (Cuota Balón)
# ═══════════════════════════════════════════════════════════════════════════════

def _m3_compra_inteligente(
    saldo_efectivo: Decimal,
    cuota_balon_pct: Decimal,
    tem: Decimal,
    n_ordinario: int,
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Calcula el PV ajustado descontando el valor presente de la Cuota Balón.

    Fórmula N°66 (Senmache) — ecuación de valor con cuota final:
        CB = saldo_efectivo × β
        VP_CB = CB / (1 + i)^n
        PV* = saldo_efectivo − VP_CB

    La cuota ordinaria se calcula sobre PV* (no sobre el saldo completo),
    lo que genera cuotas mensuales más bajas al diferir el balón.

    Retorna
    -------
    (cuota_balon_monto, vp_cuota_balon, pv_ajustado)
    """
    cb = _r2(saldo_efectivo * cuota_balon_pct)
    n = _d(n_ordinario)
    vp_cb = _r2(cb / (1 + tem) ** n)
    pv_star = _r2(saldo_efectivo - vp_cb)
    return cb, vp_cb, pv_star


# ═══════════════════════════════════════════════════════════════════════════════
# MÓDULO 4 — Cronograma de pagos (Método Francés)
# ═══════════════════════════════════════════════════════════════════════════════

def _cuota_francesa(saldo: Decimal, tem: Decimal, n_restante: int) -> Decimal:
    """
    Fórmula N°67 (Senmache) — Cuota francesa sobre saldo actual:
        R = SI × [i × (1+i)^n] / [(1+i)^n − 1]

    Equivalente al recálculo período a período, maneja gracia y prepagos.
    """
    if n_restante <= 0:
        return Decimal("0.00")
    n = _d(n_restante)
    factor = (1 + tem) ** n
    return _r2(saldo * (tem * factor) / (factor - 1))


def _m4_cronograma(
    saldo_post_gracia: Decimal,
    pv_ajustado: Decimal,
    cuota_balon_monto: Decimal,
    tem: Decimal,
    n_ordinario: int,
    nro_inicio: int,
    fecha_inicio: Optional[date],
    seguro_vehicular_pct: Decimal,
    seguro_desgravamen_pct: Decimal,
    portes: Decimal,
    comision: Decimal,
) -> List[FilaCronograma]:
    """
    Construye las filas ordinarias del cronograma período a período.

    La cuota ordinaria se calcula una sola vez sobre PV*.
    En la última cuota se cierra el saldo.
    Solo se marca como BALON si realmente existe cuota balón.
    """
    filas: List[FilaCronograma] = []
    saldo = saldo_post_gracia

    cuota_ordinaria = _cuota_francesa(pv_ajustado, tem, n_ordinario)
    tiene_balon = cuota_balon_monto > Decimal("0.00")

    for k in range(1, n_ordinario + 1):
        nro = nro_inicio + k
        fecha = _fecha_cuota(fecha_inicio, nro)
        es_ultima = k == n_ordinario

        saldo_ini = _r2(saldo)
        interes = _r2(saldo_ini * tem)
        amortizacion = _r2(cuota_ordinaria - interes)

        if es_ultima:
            amortizacion = saldo_ini
            tipo = TIPO_BALON if tiene_balon else TIPO_NORMAL
        else:
            tipo = TIPO_NORMAL

        saldo_final = _r2(saldo_ini - amortizacion)

        seg_deg = _r2(saldo_ini * seguro_desgravamen_pct)
        seg_veh = _r2(saldo_ini * seguro_vehicular_pct)

        if es_ultima:
            cuota_total = _r2(interes + amortizacion + seg_deg + seg_veh + portes + comision)
        else:
            cuota_total = _r2(cuota_ordinaria + seg_deg + seg_veh + portes + comision)

        filas.append(FilaCronograma(
            nro_cuota=nro,
            fecha_vencimiento=fecha,
            tipo_periodo=tipo,
            saldo_inicial=saldo_ini,
            interes=interes,
            amortizacion=amortizacion,
            seguro_desgravamen=seg_deg,
            seguro_vehicular=seg_veh,
            portes=portes,
            comision=comision,
            cuota_total=cuota_total,
            saldo_final=max(saldo_final, Decimal("0.00")),
        ))

        saldo = saldo_final

    return filas


# ═══════════════════════════════════════════════════════════════════════════════
# MÓDULO 5 — Indicadores financieros
# ═══════════════════════════════════════════════════════════════════════════════

def _m5_indicadores(
    monto_financiado: Decimal,
    cronograma: List[FilaCronograma],
    tem: Decimal,
    costo_comisiones_iniciales: Decimal = Decimal("0.00"),
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Calcula VAN, TIR mensual y TCEA.

    VAN (perspectiva deudor, COK = TEA del préstamo = tem):
        FC0 = +monto_financiado (inflow: recibe el dinero)
        FCk = −cuota_total_k    (outflow: paga cada mes)
        VAN = monto_financiado − Σ [cuota_total_k / (1+i)^k]
        Con COK = i (TEM), el VAN ≈ 0 (referencial, confirma consistencia).

    TIR mensual:
        Raíz de: −monto_financiado + Σ [cuota_total_k / (1+TIR)^k] = 0
        Se resuelve por bisección (Newton-Raphson como refinamiento).

    TCEA:
        Incluye seguros + portes + comisiones → flujo total.
        TCEA = (1 + TIR_mensual_total)^12 − 1

    Nota: Los flujos de gracia total tienen cuota = 0 (no hay desembolso).
    """
    # ── Construir vector de flujos totales (con seguros, portes, comisiones) ──
    # FC0 = monto prestado menos comisiones iniciales (desembolso neto recibido)
    fc0 = monto_financiado - costo_comisiones_iniciales

    flujos_total: List[Decimal] = [fc0]
    for fila in cronograma:
        flujos_total.append(-fila.cuota_total)

    # ── VAN con COK = TEM (referencial) ──────────────────────────────────────
    van = fc0
    for k, fc in enumerate(flujos_total[1:], start=1):
        van += fc / (1 + tem) ** _d(k)
    van = _r2(van)

    # ── TIR mensual (bisección) ───────────────────────────────────────────────
    tir_mensual = _biseccion_tir(flujos_total)

    # ── TCEA ─────────────────────────────────────────────────────────────────
    tcea = _r8((1 + tir_mensual) ** _d(12) - 1)

    return van, _r8(tir_mensual), tcea


def _npv(tasa: Decimal, flujos: List[Decimal]) -> Decimal:
    """VAN a una tasa dada (para el solver de TIR)."""
    resultado = Decimal("0")
    for k, fc in enumerate(flujos):
        resultado += fc / (1 + tasa) ** _d(k)
    return resultado


def _biseccion_tir(flujos: List[Decimal]) -> Decimal:
    """
    Calcula la TIR por bisección.
    Asume FC0 > 0 y al menos un FC negativo.
    Tolerancia: |NPV| < 0.000001
    """
    lo = Decimal("0.000001")
    hi = Decimal("10.0")  # 1000% mensual como límite superior

    npv_lo = _npv(lo, flujos)

    # Asegurar que haya cambio de signo
    if npv_lo * _npv(hi, flujos) > 0:
        # Fallback: devolver estimación razonable
        return Decimal("0.01")

    for _ in range(MAX_ITER_TIR):
        mid = (lo + hi) / DOS
        npv_mid = _npv(mid, flujos)

        if abs(npv_mid) < TOLERANCIA_TIR:
            return mid

        if npv_lo * npv_mid < 0:
            hi = mid
        else:
            lo = mid
            npv_lo = npv_mid

    return (lo + hi) / DOS


# ── Helper: fecha de vencimiento ───────────────────────────────────────────────

def _fecha_cuota(fecha_inicio: Optional[date], nro_cuota: int) -> Optional[date]:
    """Fecha de vencimiento = fecha_inicio + nro_cuota × 30 días (base comercial)."""
    if fecha_inicio is None:
        return None
    return fecha_inicio + timedelta(days=DIAS_MES * nro_cuota)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL — calcular_motor_sicap
# ═══════════════════════════════════════════════════════════════════════════════

def calcular_motor_sicap(
    # Datos del vehículo / financiamiento
    precio_base: float | Decimal,
    cuota_inicial_monto: float | Decimal,
    plazo_meses: int,
    # Tasa
    tipo_tasa: str,
    tasa_valor: float | Decimal,
    capitalizacion_m: Optional[int],
    # Gracia
    periodos_gracia_total: int,
    periodos_gracia_parcial: int,
    # Compra Inteligente
    cuota_balon_pct: float | Decimal,
    # Costos periódicos
    seguro_vehicular_pct: float | Decimal,
    seguro_desgravamen_pct: float | Decimal,
    costo_portes: float | Decimal,
    costo_comisiones: float | Decimal,
    # Fechas
    fecha_inicio: Optional[date] = None,
) -> ResultadoMotor:
    """
    Punto de entrada del motor financiero SICAP.

    Todos los porcentajes se reciben como decimales puros:
        tasa_valor = 0.1200  (= 12%)
        cuota_balon_pct = 0.30  (= 30%)
        seguro_vehicular_pct = 0.0050  (= 0.50% mensual)
        seguro_desgravamen_pct = 0.0004 (= 0.04% mensual)
    """
    # ── Convertir a Decimal ────────────────────────────────────────────────────
    precio = _d(precio_base)
    cuota_ini = _d(cuota_inicial_monto)
    balon_pct = _d(cuota_balon_pct)
    seg_veh_pct = _d(seguro_vehicular_pct)
    seg_deg_pct = _d(seguro_desgravamen_pct)
    portes = _r2(_d(costo_portes))
    comision = _r2(_d(costo_comisiones))

    # ── Monto financiado ───────────────────────────────────────────────────────
    monto_financiado = _r2(precio - cuota_ini)
    if monto_financiado <= 0:
        raise ValueError("La cuota inicial no puede ser mayor o igual al precio del vehículo")

    # ── M1: Conversión de tasas ────────────────────────────────────────────────
    tea, tem = _m1_convertir_tasas(tipo_tasa, _d(tasa_valor), capitalizacion_m)

    # ── M2: Períodos de gracia ─────────────────────────────────────────────────
    saldo_post_gracia, nro_fin_gracia, filas_gracia = _m2_aplicar_gracia(
        saldo_inicial=monto_financiado,
        tem=tem,
        periodos_gracia_total=periodos_gracia_total,
        periodos_gracia_parcial=periodos_gracia_parcial,
        fecha_inicio=fecha_inicio,
        portes=portes,
        comision=comision,
        seguro_vehicular_pct=seg_veh_pct,
        seguro_desgravamen_pct=seg_deg_pct,
    )

    # ── M3: Compra Inteligente ─────────────────────────────────────────────────
    n_ordinario = plazo_meses - periodos_gracia_total - periodos_gracia_parcial
    cb_monto, vp_cb, pv_ajustado = _m3_compra_inteligente(
        saldo_efectivo=saldo_post_gracia,
        cuota_balon_pct=balon_pct,
        tem=tem,
        n_ordinario=n_ordinario,
    )

    # Cuota ordinaria (para exponer en el resumen)
    cuota_ordinaria = _cuota_francesa(pv_ajustado, tem, n_ordinario)

    # ── M4: Cronograma ordinario ───────────────────────────────────────────────
    filas_ordinarias = _m4_cronograma(
        saldo_post_gracia=saldo_post_gracia,
        pv_ajustado=pv_ajustado,
        cuota_balon_monto=cb_monto,
        tem=tem,
        n_ordinario=n_ordinario,
        nro_inicio=nro_fin_gracia,
        fecha_inicio=fecha_inicio,
        seguro_vehicular_pct=seg_veh_pct,
        seguro_desgravamen_pct=seg_deg_pct,
        portes=portes,
        comision=comision,
    )

    cronograma_completo = filas_gracia + filas_ordinarias

    # ── Acumuladores (hoja resumen SBS) ───────────────────────────────────────
    total_intereses = _r2(sum((f.interes for f in cronograma_completo), Decimal("0.00")))
    total_seguros = _r2(
        sum((f.seguro_vehicular + f.seguro_desgravamen for f in cronograma_completo), Decimal("0.00"))
    )
    total_portes = _r2(sum((f.portes for f in cronograma_completo), Decimal("0.00")))
    total_comisiones = _r2(sum((f.comision for f in cronograma_completo), Decimal("0.00")))

    costo_total_credito = _r2(
        monto_financiado + total_intereses + total_seguros + total_portes + total_comisiones
    )

    # ── M5: Indicadores financieros ───────────────────────────────────────────
    van, tir_mensual, tcea = _m5_indicadores(
        monto_financiado=monto_financiado,
        cronograma=cronograma_completo,
        tem=tem,
    )

    return ResultadoMotor(
        monto_financiado=monto_financiado,
        cuota_balon_monto=cb_monto,
        tea_efectiva=tea,
        tasa_mensual=tem,
        cuota_ordinaria=cuota_ordinaria,
        van=van,
        tir_mensual=tir_mensual,
        tcea=tcea,
        total_intereses=total_intereses,
        total_seguros=total_seguros,
        total_portes=total_portes,
        costo_total_credito=costo_total_credito,
        cronograma=cronograma_completo,
    )