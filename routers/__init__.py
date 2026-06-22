from routers.auth_router import router as auth_router
from routers.clientes_router import router as clientes_router
from routers.vehiculos_router import router as vehiculos_router
from routers.simulaciones_router import router as simulaciones_router
from routers.catalogo_router import router as catalogo_router

__all__ = [
    "auth_router",
    "clientes_router",
    "vehiculos_router",
    "simulaciones_router",
    "catalogo_router",
]