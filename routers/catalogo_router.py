from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from core.database import get_db
from core.security import get_current_user
from models.catalogo import Banco, TipoMoneda
from models.usuario import Usuario

router = APIRouter(prefix="/catalogo", tags=["Catálogo"])


class BancoOut(BaseModel):
    id: int
    nombre_banco: str
    model_config = {"from_attributes": True}


class MonedaOut(BaseModel):
    id: int
    codigo: str
    nombre_moneda: str
    simbolo: str
    model_config = {"from_attributes": True}


@router.get("/bancos", response_model=List[BancoOut])
def listar_bancos(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return db.query(Banco).all()


@router.get("/monedas", response_model=List[MonedaOut])
def listar_monedas(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return db.query(TipoMoneda).all()