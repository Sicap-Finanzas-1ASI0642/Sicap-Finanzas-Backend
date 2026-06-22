from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.security import get_current_user
from models.vehiculo import Vehiculo
from models.usuario import Usuario
from schemas.entidades import VehiculoCreate, VehiculoUpdate, VehiculoOut

router = APIRouter(prefix="/vehiculos", tags=["Vehículos"])


@router.post("/", response_model=VehiculoOut, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(
        datos: VehiculoCreate,
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
):
    vehiculo = Vehiculo(**datos.model_dump())
    db.add(vehiculo)
    db.commit()
    db.refresh(vehiculo)
    return vehiculo


@router.get("/", response_model=List[VehiculoOut])
def listar_vehiculos(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
):
    return db.query(Vehiculo).offset(skip).limit(limit).all()


@router.get("/{vehiculo_id}", response_model=VehiculoOut)
def obtener_vehiculo(
        vehiculo_id: int,
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
):
    v = db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return v


@router.put("/{vehiculo_id}", response_model=VehiculoOut)
def actualizar_vehiculo(
        vehiculo_id: int,
        datos: VehiculoUpdate,
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
):
    v = db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    for campo, valor in datos.model_dump(exclude_none=True).items():
        setattr(v, campo, valor)
    db.commit()
    db.refresh(v)
    return v


@router.delete("/{vehiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_vehiculo(
        vehiculo_id: int,
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
):
    v = db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    db.delete(v)
    db.commit()
