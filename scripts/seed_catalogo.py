"""
Seed idempotente del catálogo base (bancos y tipos de moneda).

No hay endpoints de creación para Banco/TipoMoneda (routers/catalogo_router.py
solo expone GET), así que este script es la forma de poblarlos tanto en
desarrollo local (SQLite) como en Railway (Postgres). Usa la misma
DATABASE_URL definida en .env / core/database.py.

Uso:
    python -m scripts.seed_catalogo
"""

from core.database import Base, SessionLocal, engine
from models.catalogo import Banco, TipoMoneda

BANCOS = ["BCP", "BBVA", "Interbank", "Scotiabank"]

MONEDAS = [
    {"codigo": "PEN", "nombre_moneda": "Sol peruano", "simbolo": "S/"},
    {"codigo": "USD", "nombre_moneda": "Dólar americano", "simbolo": "$"},
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for nombre in BANCOS:
            if not db.query(Banco).filter(Banco.nombre_banco == nombre).first():
                db.add(Banco(nombre_banco=nombre))

        for moneda in MONEDAS:
            if not db.query(TipoMoneda).filter(TipoMoneda.codigo == moneda["codigo"]).first():
                db.add(TipoMoneda(**moneda))

        db.commit()
        print(f"Catálogo listo: {db.query(Banco).count()} bancos, {db.query(TipoMoneda).count()} monedas.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
