from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.security import get_current_user
from models.cliente import Cliente
from models.usuario import Usuario
from schemas.entidades import ClienteCreate, ClienteUpdate, ClienteOut

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def crear_cliente(
        datos: ClienteCreate,
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
):
    if db.query(Cliente).filter(Cliente.dni == datos.dni).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un cliente con DNI {datos.dni}",
        )
    if db.query(Cliente).filter(Cliente.email == datos.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya está registrado",
        )
    cliente = Cliente(**datos.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.get("/", response_model=List[ClienteOut])
def listar_clientes(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
):
    return db.query(Cliente).offset(skip).limit(limit).all()


@router.get("/{cliente_id}", response_model=ClienteOut)
def obtener_cliente(
        cliente_id: int,
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.put("/{cliente_id}", response_model=ClienteOut)
def actualizar_cliente(
        cliente_id: int,
        datos: ClienteUpdate,
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    for campo, valor in datos.model_dump(exclude_none=True).items():
        setattr(cliente, campo, valor)

    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cliente(
        cliente_id: int,
        db: Session = Depends(get_db),
        _: Usuario = Depends(get_current_user),
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    db.delete(cliente)
    db.commit()
