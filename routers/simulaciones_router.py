from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal

from core.database import get_db
from core.security import get_current_user
from models import Simulacion, Cronograma, Cliente, Vehiculo, Banco, TipoMoneda
from models.usuario import Usuario
from schemas.simulacion import (
    SimulacionCreate,
    SimulacionOut,
    SimulacionResumen,
    HojaResumenOut,
)
from services.motor_financiero import calcular_motor_sicap

router = APIRouter(prefix="/simulaciones", tags=["Simulaciones"])


@router.post("/", response_model=SimulacionOut, status_code=status.HTTP_201_CREATED)
def crear_simulacion(
    datos: SimulacionCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    """
    Ejecuta el motor financiero SICAP y persiste la simulación con su cronograma.
    """
    # ── Validar existencia de entidades relacionadas ──────────────────────────
    cliente = db.query(Cliente).filter(Cliente.id == datos.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == datos.vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    if not db.query(Banco).filter(Banco.id == datos.banco_id).first():
        raise HTTPException(status_code=404, detail="Banco no encontrado")

    if not db.query(TipoMoneda).filter(TipoMoneda.id == datos.moneda_id).first():
        raise HTTPException(status_code=404, detail="Moneda no encontrada")

    # ── Validar cuota inicial vs precio ───────────────────────────────────────
    if datos.cuota_inicial_monto >= vehiculo.precio_base:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La cuota inicial no puede ser mayor o igual al precio del vehículo",
        )

    # ── Ejecutar motor financiero ─────────────────────────────────────────────
    try:
        resultado = calcular_motor_sicap(
            precio_base=Decimal(str(vehiculo.precio_base)),
            cuota_inicial_monto=datos.cuota_inicial_monto,
            plazo_meses=datos.plazo_meses,
            tipo_tasa=datos.tipo_tasa,
            tasa_valor=datos.tasa_valor,
            capitalizacion_m=int(datos.capitalizacion_m) if datos.capitalizacion_m is not None else None,
            periodos_gracia_total=datos.periodos_gracia_total,
            periodos_gracia_parcial=datos.periodos_gracia_parcial,
            cuota_balon_pct=datos.cuota_balon_pct,
            seguro_vehicular_pct=datos.seguro_vehicular_pct,
            seguro_desgravamen_pct=datos.seguro_desgravamen_pct,
            costo_portes=datos.costo_portes,
            costo_comisiones=datos.costo_comisiones,
            fecha_inicio=datos.fecha_inicio,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # ── Persistir cabecera de simulación ──────────────────────────────────────
    sim = Simulacion(
        usuario_id=usuario_actual.id,
        cliente_id=datos.cliente_id,
        vehiculo_id=datos.vehiculo_id,
        banco_id=datos.banco_id,
        moneda_id=datos.moneda_id,
        cuota_inicial_monto=datos.cuota_inicial_monto,
        monto_financiado=resultado.monto_financiado,
        plazo_meses=datos.plazo_meses,
        tipo_tasa=datos.tipo_tasa,
        tasa_valor=datos.tasa_valor,
        capitalizacion_m=datos.capitalizacion_m,
        periodos_gracia_total=datos.periodos_gracia_total,
        periodos_gracia_parcial=datos.periodos_gracia_parcial,
        cuota_balon_pct=datos.cuota_balon_pct,
        cuota_balon_monto=resultado.cuota_balon_monto,
        seguro_vehicular_pct=datos.seguro_vehicular_pct,
        seguro_desgravamen_pct=datos.seguro_desgravamen_pct,
        costo_portes=datos.costo_portes,
        costo_comisiones=datos.costo_comisiones,
        fecha_inicio=datos.fecha_inicio,
        tea_efectiva=resultado.tea_efectiva,
        tasa_mensual=resultado.tasa_mensual,
        cuota_ordinaria=resultado.cuota_ordinaria,
        van=resultado.van,
        tir_mensual=resultado.tir_mensual,
        tcea=resultado.tcea,
        total_intereses=resultado.total_intereses,
        total_seguros=resultado.total_seguros,
        total_portes=resultado.total_portes,
        costo_total_credito=resultado.costo_total_credito,
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)

    # ── Persistir cronograma ──────────────────────────────────────────────────
    filas_db = [
        Cronograma(
            simulacion_id=sim.id,
            nro_cuota=f.nro_cuota,
            fecha_vencimiento=f.fecha_vencimiento if f.fecha_vencimiento is not None else None,
            tipo_periodo=f.tipo_periodo,
            saldo_inicial=f.saldo_inicial,
            interes=f.interes,
            amortizacion=f.amortizacion,
            seguro_desgravamen=f.seguro_desgravamen,
            seguro_vehicular=f.seguro_vehicular,
            portes=f.portes,
            comision=f.comision,
            cuota_total=f.cuota_total,
            saldo_final=f.saldo_final,
        )
        for f in resultado.cronograma
    ]
    db.bulk_save_objects(filas_db)
    db.commit()
    db.refresh(sim)

    return sim


@router.put("/{simulacion_id}", response_model=SimulacionOut)
def actualizar_simulacion(
    simulacion_id: int,
    datos: SimulacionCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    """
    Edita una simulación existente, recalcula el motor financiero
    y reemplaza el cronograma anterior por uno nuevo.
    """
    # ── Buscar simulación del usuario autenticado ─────────────────────────────
    sim = (
        db.query(Simulacion)
        .filter(
            Simulacion.id == simulacion_id,
            Simulacion.usuario_id == usuario_actual.id,
        )
        .first()
    )

    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")

    # ── Validar existencia de entidades relacionadas ──────────────────────────
    cliente = db.query(Cliente).filter(Cliente.id == datos.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == datos.vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    if not db.query(Banco).filter(Banco.id == datos.banco_id).first():
        raise HTTPException(status_code=404, detail="Banco no encontrado")

    if not db.query(TipoMoneda).filter(TipoMoneda.id == datos.moneda_id).first():
        raise HTTPException(status_code=404, detail="Moneda no encontrada")

    # ── Validar cuota inicial vs precio del vehículo ──────────────────────────
    if datos.cuota_inicial_monto >= vehiculo.precio_base:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La cuota inicial no puede ser mayor o igual al precio del vehículo",
        )

    # ── Recalcular motor financiero ───────────────────────────────────────────
    try:
        resultado = calcular_motor_sicap(
            precio_base=Decimal(str(vehiculo.precio_base)),
            cuota_inicial_monto=datos.cuota_inicial_monto,
            plazo_meses=datos.plazo_meses,
            tipo_tasa=datos.tipo_tasa,
            tasa_valor=datos.tasa_valor,
            capitalizacion_m=int(datos.capitalizacion_m) if datos.capitalizacion_m is not None else None,
            periodos_gracia_total=datos.periodos_gracia_total,
            periodos_gracia_parcial=datos.periodos_gracia_parcial,
            cuota_balon_pct=datos.cuota_balon_pct,
            seguro_vehicular_pct=datos.seguro_vehicular_pct,
            seguro_desgravamen_pct=datos.seguro_desgravamen_pct,
            costo_portes=datos.costo_portes,
            costo_comisiones=datos.costo_comisiones,
            fecha_inicio=datos.fecha_inicio,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # ── Actualizar cabecera de simulación ─────────────────────────────────────
    sim.cliente_id = datos.cliente_id
    sim.vehiculo_id = datos.vehiculo_id
    sim.banco_id = datos.banco_id
    sim.moneda_id = datos.moneda_id

    sim.cuota_inicial_monto = datos.cuota_inicial_monto
    sim.monto_financiado = resultado.monto_financiado
    sim.plazo_meses = datos.plazo_meses

    sim.tipo_tasa = datos.tipo_tasa
    sim.tasa_valor = datos.tasa_valor
    sim.capitalizacion_m = datos.capitalizacion_m

    sim.periodos_gracia_total = datos.periodos_gracia_total
    sim.periodos_gracia_parcial = datos.periodos_gracia_parcial

    sim.cuota_balon_pct = datos.cuota_balon_pct
    sim.cuota_balon_monto = resultado.cuota_balon_monto

    sim.seguro_vehicular_pct = datos.seguro_vehicular_pct
    sim.seguro_desgravamen_pct = datos.seguro_desgravamen_pct
    sim.costo_portes = datos.costo_portes
    sim.costo_comisiones = datos.costo_comisiones

    sim.fecha_inicio = datos.fecha_inicio

    sim.tea_efectiva = resultado.tea_efectiva
    sim.tasa_mensual = resultado.tasa_mensual
    sim.cuota_ordinaria = resultado.cuota_ordinaria
    sim.van = resultado.van
    sim.tir_mensual = resultado.tir_mensual
    sim.tcea = resultado.tcea
    sim.total_intereses = resultado.total_intereses
    sim.total_seguros = resultado.total_seguros
    sim.total_portes = resultado.total_portes
    sim.costo_total_credito = resultado.costo_total_credito

    # ── Reemplazar cronograma anterior ────────────────────────────────────────
    db.query(Cronograma).filter(
        Cronograma.simulacion_id == sim.id
    ).delete(synchronize_session=False)

    db.flush()

    nuevas_filas = [
        Cronograma(
            simulacion_id=sim.id,
            nro_cuota=f.nro_cuota,
            fecha_vencimiento=f.fecha_vencimiento if f.fecha_vencimiento is not None else None,
            tipo_periodo=f.tipo_periodo,
            saldo_inicial=f.saldo_inicial,
            interes=f.interes,
            amortizacion=f.amortizacion,
            seguro_desgravamen=f.seguro_desgravamen,
            seguro_vehicular=f.seguro_vehicular,
            portes=f.portes,
            comision=f.comision,
            cuota_total=f.cuota_total,
            saldo_final=f.saldo_final,
        )
        for f in resultado.cronograma
    ]

    db.bulk_save_objects(nuevas_filas)
    db.commit()
    db.refresh(sim)
    db.expire(sim, ["cronograma"])

    return sim

@router.get("/", response_model=List[SimulacionResumen])
def listar_simulaciones(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    """Lista las simulaciones del usuario autenticado (sin cronograma)."""
    return (
        db.query(Simulacion)
        .filter(Simulacion.usuario_id == usuario_actual.id)
        .order_by(Simulacion.fecha_simulacion.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{simulacion_id}", response_model=SimulacionOut)
def obtener_simulacion(
    simulacion_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    """Retorna una simulación completa con su cronograma."""
    sim = (
        db.query(Simulacion)
        .filter(
            Simulacion.id == simulacion_id,
            Simulacion.usuario_id == usuario_actual.id,
        )
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    return sim


@router.get("/{simulacion_id}/hoja-resumen", response_model=HojaResumenOut)
def obtener_hoja_resumen(
    simulacion_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    """
    Retorna la hoja resumen de una simulación guardada.

    Esta respuesta está pensada para que el frontend muestre al usuario
    el resumen de transparencia del crédito: cliente, vehículo, banco,
    moneda, tasas, indicadores financieros y costos totales.
    """
    sim = (
        db.query(Simulacion)
        .filter(
            Simulacion.id == simulacion_id,
            Simulacion.usuario_id == usuario_actual.id,
        )
        .first()
    )

    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")

    total_comisiones = sum((fila.comision for fila in sim.cronograma), Decimal("0.00"))
    total_a_pagar = sum((fila.cuota_total for fila in sim.cronograma), Decimal("0.00"))

    return {
        "cliente": sim.cliente,
        "vehiculo": sim.vehiculo,
        "banco": sim.banco,
        "moneda": sim.moneda,
        "credito": {
            "simulacion_id": sim.id,
            "fecha_inicio": sim.fecha_inicio,
            "fecha_simulacion": sim.fecha_simulacion,
            "cuota_inicial_monto": sim.cuota_inicial_monto,
            "monto_financiado": sim.monto_financiado,
            "plazo_meses": sim.plazo_meses,
            "tipo_tasa": sim.tipo_tasa,
            "tasa_valor": sim.tasa_valor,
            "capitalizacion_m": sim.capitalizacion_m,
            "tea_efectiva": sim.tea_efectiva,
            "tasa_mensual": sim.tasa_mensual,
            "cuota_ordinaria": sim.cuota_ordinaria,
            "periodos_gracia_total": sim.periodos_gracia_total,
            "periodos_gracia_parcial": sim.periodos_gracia_parcial,
            "cuota_balon_pct": sim.cuota_balon_pct,
            "cuota_balon_monto": sim.cuota_balon_monto,
        },
        "indicadores": {
            "van": sim.van,
            "tir_mensual": sim.tir_mensual,
            "tcea": sim.tcea,
        },
        "costos": {
            "seguro_vehicular_pct": sim.seguro_vehicular_pct,
            "seguro_desgravamen_pct": sim.seguro_desgravamen_pct,
            "costo_portes": sim.costo_portes,
            "costo_comisiones": sim.costo_comisiones,
            "total_intereses": sim.total_intereses,
            "total_seguros": sim.total_seguros,
            "total_portes": sim.total_portes,
            "total_comisiones": total_comisiones,
            "total_a_pagar": total_a_pagar,
            "costo_total_credito": sim.costo_total_credito,
        },
    }

@router.delete("/{simulacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_simulacion(
    simulacion_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user),
):
    sim = (
        db.query(Simulacion)
        .filter(
            Simulacion.id == simulacion_id,
            Simulacion.usuario_id == usuario_actual.id,
        )
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    db.delete(sim)
    db.commit()