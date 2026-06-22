from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import hash_password, verify_password, create_access_token
from models.usuario import Usuario
from schemas.auth import UsuarioCreate, UsuarioOut, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registrar", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def registrar_usuario(datos: UsuarioCreate, db: Session = Depends(get_db)):
    """Registra un nuevo operador/ejecutivo en el sistema."""
    if db.query(Usuario).filter(Usuario.username == datos.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre de usuario ya está en uso",
        )
    if db.query(Usuario).filter(Usuario.email == datos.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya está registrado",
        )
    if db.query(Usuario).filter(Usuario.dni == datos.dni).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El DNI ya está registrado",
        )

    nuevo = Usuario(
        username=datos.username,
        password_hash=hash_password(datos.password),
        nombre_completo=datos.nombre_completo,
        email=datos.email,
        dni=datos.dni,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.post("/token")  # Este es solo para Swagger UI
def login_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(
        Usuario.username == form_data.username
    ).first()

    if not usuario or not verify_password(form_data.password, str(usuario.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    token = create_access_token(data={"sub": str(usuario.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=LoginResponse)
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    """Autentica al usuario y devuelve un JWT."""
    usuario: Usuario | None = db.query(Usuario).filter(Usuario.username == datos.username).first()

    if not usuario or not verify_password(datos.password, str(usuario.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    token = create_access_token(data={"sub": str(usuario.id)})
    return LoginResponse(access_token=token, usuario=UsuarioOut.model_validate(usuario))
