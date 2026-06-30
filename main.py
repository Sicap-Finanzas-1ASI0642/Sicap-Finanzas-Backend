from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.database import engine
from models import *  # noqa: F401, F403
from core.database import Base
from routers import (
    auth_router,
    clientes_router,
    vehiculos_router,
    simulaciones_router,
    catalogo_router,
)

# ── Archivos estáticos ─────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# ── Crear tablas ───────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Aplicación ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SICAP API",
    description="Simulador de Créditos Automotrices Perú — Motor de cálculo financiero",
    version="2.0.0",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: especificar dominios del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files ───────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(vehiculos_router)
app.include_router(simulaciones_router)
app.include_router(catalogo_router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "sistema": "SICAP API v2.0"}

@app.get("/ayuda", tags=["Ayuda"])
def obtener_ayuda():
    """
    Devuelve la información de ayuda técnica del sistema SICAP.

    El frontend puede usar esta respuesta para mostrar un botón de ayuda,
    abrir el manual PDF o informar si el archivo aún no está disponible.
    """
    ayuda_path = STATIC_DIR / "ayuda.pdf"
    disponible = ayuda_path.exists() and ayuda_path.stat().st_size > 0

    return {
        "titulo": "Manual de ayuda SICAP",
        "descripcion": "Guía de uso del simulador de créditos automotrices.",
        "disponible": disponible,
        "url": "/static/ayuda.pdf" if disponible else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)