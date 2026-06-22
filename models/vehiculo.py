from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base

class Vehiculo(Base):
    """Vehiculo a financiar registrado en el catálogo del sistema SICAP"""
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    marca = Column(String(50), nullable=False)
    modelo = Column(String(50), nullable=False)
    anio = Column(Integer, nullable=False)
    condicion = Column(String(10), nullable=False) # nuevo o seminuevo
    precio_base = Column(Numeric(12, 2), nullable=False)
    fecha_registro = Column(TIMESTAMP, server_default=func.now())

    simulaciones = relationship("Simulacion", back_populates="vehiculo")

