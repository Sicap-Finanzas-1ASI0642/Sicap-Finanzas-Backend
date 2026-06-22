from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class Usuario(Base):
    """Operadores/ejecutivos del sistema SICAP (no confundir con clientes)."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    nombre_completo = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    dni = Column(String(8), unique=True, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(TIMESTAMP, server_default=func.now())

    # Relaciones
    simulaciones = relationship("Simulacion", back_populates="usuario")