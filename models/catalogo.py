from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from core.database import Base

class Banco(Base):
    __tablename__ = "bancos"

    id = Column(Integer, primary_key=True, index=True)
    nombre_banco = Column(String(100), nullable=False)
    simulaciones = relationship("Simulacion", back_populates="banco")

class TipoMoneda(Base):
    __tablename__ = "tipos_moneda"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(3), unique=True, nullable=False) # PEN OR USD
    nombre_moneda = Column(String(30), nullable=False)
    simbolo = Column(String(5), nullable=False)
    simulaciones = relationship("Simulacion", back_populates="moneda")
