import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar las variables del archivo .env
load_dotenv()

# Obtener la URL de conexión
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Crear el Motor de conexión
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Crear el generador de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear la Clase Base
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()