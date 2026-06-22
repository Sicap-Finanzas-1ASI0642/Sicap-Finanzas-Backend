from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal

from core.database import get_db
from core.security import get_current_user
from models import Simulacion, Cronograma, Cliente, Vehiculo, Banco, TipoMoneda
from models.usuario import Usuario
from schemas.simulacion import SimulacionCreate, SimulacionOut, SimulacionResumen
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