from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, TIMESTAMP, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    nombre_completo = Column(String(100))
    email = Column(String(100))
    dni = Column(String(8))
    simulaciones = relationship("Simulacion", back_populates="usuario")

class Banco(Base):
    __tablename__ = "bancos"
    id = Column(Integer, primary_key=True, index=True)
    nombre_banco = Column(String(100), nullable=False)

class TipoMoneda(Base):
    __tablename__ = "tipos_moneda"
    id = Column(Integer, primary_key=True, index=True)
    nombre_moneda = Column(String(20))
    simbolo = Column(String(5))

class Simulacion(Base):
    __tablename__ = "simulaciones"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    banco_id = Column(Integer, ForeignKey("bancos.id"))
    moneda_id = Column(Integer, ForeignKey("tipos_moneda.id"))
    
    marca_vehiculo = Column(String(50))
    modelo_vehiculo = Column(String(50))
    anio_vehiculo = Column(Integer)
    precio_venta = Column(Numeric(15, 2))
    cuota_inicial_pct = Column(Numeric(5, 2))
    monto_prestamo = Column(Numeric(15, 2))
    plazo_meses = Column(Integer)
    tasa_valor = Column(Numeric(12, 10))
    tipo_tasa = Column(String(10))
    capitalizacion = Column(String(20))
    tipo_periodo_gracia = Column(String(20))
    meses_gracia = Column(Integer, default=0)
    cuota_balon_pct = Column(Numeric(5, 2))
    
    seguro_desgravamen_pct = Column(Numeric(12, 10))
    seguro_vehicular_pct = Column(Numeric(12, 10))
    costo_portes = Column(Numeric(10, 2))
    costo_comisiones = Column(Numeric(10, 2))
    
    van = Column(Numeric(15, 2))
    tir = Column(Numeric(12, 10))
    tcea = Column(Numeric(12, 10))
    fecha_simulacion = Column(TIMESTAMP, server_default=func.now())

    usuario = relationship("Usuario", back_populates="simulaciones")
    cronograma = relationship("Cronograma", back_populates="simulacion", cascade="all, delete-orphan")

class Cronograma(Base):
    __tablename__ = "cronogramas"
    id = Column(Integer, primary_key=True, index=True)
    simulacion_id = Column(Integer, ForeignKey("simulaciones.id"))
    nro_cuota = Column(Integer, nullable=False)
    saldo_inicial = Column(Numeric(15, 2))
    amortizacion = Column(Numeric(15, 2))
    interes = Column(Numeric(15, 2))
    seguro_desgravamen = Column(Numeric(15, 2))
    seguro_vehicular = Column(Numeric(15, 2))
    comision_cuota = Column(Numeric(15, 2))
    portes_cuota = Column(Numeric(15, 2))
    cuota_total = Column(Numeric(15, 2))
    saldo_final = Column(Numeric(15, 2))

    simulacion = relationship("Simulacion", back_populates="cronograma")