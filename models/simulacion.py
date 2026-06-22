from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, TIMESTAMP, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class Simulacion(Base):
    """
    Cabecera de una simulación de crédito vehicular.
    Almacena todos los parámetros de entrada y los indicadores calculados.
    """

    __tablename__ = "simulaciones"

    id = Column(Integer, primary_key=True, index=True)

    # ── Claves foráneas ──────────────────────────────────────────────────────
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False)
    banco_id = Column(Integer, ForeignKey("bancos.id"), nullable=False)
    moneda_id = Column(Integer, ForeignKey("tipos_moneda.id"), nullable=False)

    # ── Parámetros financieros de entrada ────────────────────────────────────
    cuota_inicial_monto = Column(Numeric(12, 2), nullable=False)   # monto fijo de cuota inicial
    monto_financiado = Column(Numeric(12, 2), nullable=False)       # precio_base - cuota_inicial
    plazo_meses = Column(Integer, nullable=False)

    tipo_tasa = Column(String(3), nullable=False)       # 'TEA' | 'TNA'
    tasa_valor = Column(Numeric(8, 6), nullable=False)  # decimal puro, ej. 0.1200 = 12%
    capitalizacion_m = Column(Integer, nullable=True)   # solo si TNA: 12, 4, 2, 360, etc.

    periodos_gracia_total = Column(Integer, default=0, nullable=False)
    periodos_gracia_parcial = Column(Integer, default=0, nullable=False)

    cuota_balon_pct = Column(Numeric(5, 4), default=0, nullable=False)  # 0.30 = 30%
    cuota_balon_monto = Column(Numeric(12, 2), nullable=False)           # calculado

    seguro_vehicular_pct = Column(Numeric(6, 4), nullable=False)     # % mensual sobre saldo
    seguro_desgravamen_pct = Column(Numeric(6, 4), nullable=False)   # % mensual sobre saldo
    costo_portes = Column(Numeric(8, 2), default=0, nullable=False)
    costo_comisiones = Column(Numeric(10, 2), default=0, nullable=False)

    fecha_inicio = Column(Date, nullable=False)  # fecha del primer desembolso

    # ── Indicadores calculados ───────────────────────────────────────────────
    tea_efectiva = Column(Numeric(8, 6), nullable=False)    # TEA final usada en el cálculo
    tasa_mensual = Column(Numeric(10, 8), nullable=False)   # i mensual efectiva
    cuota_ordinaria = Column(Numeric(12, 2), nullable=False)
    van = Column(Numeric(12, 2), nullable=False)
    tir_mensual = Column(Numeric(10, 8), nullable=False)
    tcea = Column(Numeric(8, 6), nullable=False)
    total_intereses = Column(Numeric(12, 2), nullable=False)
    total_seguros = Column(Numeric(12, 2), nullable=False)
    total_portes = Column(Numeric(10, 2), nullable=False)
    costo_total_credito = Column(Numeric(12, 2), nullable=False)

    fecha_simulacion = Column(TIMESTAMP, server_default=func.now())

    # ── Relaciones ───────────────────────────────────────────────────────────
    usuario = relationship("Usuario", back_populates="simulaciones")
    cliente = relationship("Cliente", back_populates="simulaciones")
    vehiculo = relationship("Vehiculo", back_populates="simulaciones")
    banco = relationship("Banco", back_populates="simulaciones")
    moneda = relationship("TipoMoneda", back_populates="simulaciones")
    cronograma = relationship(
        "Cronograma",
        back_populates="simulacion",
        cascade="all, delete-orphan",
        order_by="Cronograma.nro_cuota",
    )


class Cronograma(Base):
    """
    Detalle período a período del plan de pagos.
    Una fila por cuota, incluyendo períodos de gracia.
    """

    __tablename__ = "cronogramas"

    id = Column(Integer, primary_key=True, index=True)
    simulacion_id = Column(Integer, ForeignKey("simulaciones.id"), nullable=False)

    nro_cuota = Column(Integer, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)  # fecha_inicio + nro_cuota * 30 días
    tipo_periodo = Column(String(10), nullable=False)  # 'GRACIA_T' | 'GRACIA_P' | 'NORMAL' | 'BALON'

    saldo_inicial = Column(Numeric(15, 2), nullable=False)
    interes = Column(Numeric(15, 2), nullable=False)
    amortizacion = Column(Numeric(15, 2), nullable=False)
    seguro_desgravamen = Column(Numeric(10, 2), nullable=False)
    seguro_vehicular = Column(Numeric(10, 2), nullable=False)
    portes = Column(Numeric(8, 2), nullable=False)
    comision = Column(Numeric(8, 2), nullable=False)
    cuota_total = Column(Numeric(15, 2), nullable=False)
    saldo_final = Column(Numeric(15, 2), nullable=False)

    simulacion = relationship("Simulacion", back_populates="cronograma")