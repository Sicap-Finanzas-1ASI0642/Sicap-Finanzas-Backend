from sqlalchemy import Column, Integer, TIMESTAMP, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base

class Cliente(Base):
    """
    Persona natural solicitante del crédito vehicular.
    Entidad distinta del usuario (operador del sistema).
    """
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    dni = Column(String(8), unique=True, nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False)
    telefono = Column(String(15), nullable=True)
    ingreso_mensual = Column(Numeric(12, 2), nullable=False)
    fecha_registro = Column(TIMESTAMP, server_default=func.now())

    simulaciones = relationship("Simulacion", back_populates="cliente")

