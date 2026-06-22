from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(vehiculos_router)
app.include_router(simulaciones_router)
app.include_router(catalogo_router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "sistema": "SICAP API v2.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)