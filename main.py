from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import models, schemas, utils
from database import SessionLocal, engine

# Crear tablas automáticamente al iniciar
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SICAP API - Sistema Completo")

# Configuración de CORS para que tu React/Frontend pueda conectarse
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- ENDPOINT: REGISTRAR USUARIO ---
@app.post("/usuarios/registrar", response_model=schemas.Usuario)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # Verificar si el username ya existe
    existe = db.query(models.Usuario).filter(models.Usuario.username == usuario.username).first()
    if existe:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    
    nuevo_usuario = models.Usuario(
        username=usuario.username,
        password_hash=usuario.password, # En producción usa hashing
        nombre_completo=usuario.nombre_completo,
        email=usuario.email,
        dni=usuario.dni
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

# --- ENDPOINT: LOGIN ---
@app.post("/login", response_model=schemas.LoginResponse)
def login(datos: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.username == datos.username).first()
    if not user or user.password_hash != datos.password:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    return {
        "mensaje": "Login exitoso",
        "usuario_id": user.id,
        "username": user.username,
        "nombre_completo": user.nombre_completo
    }

# --- ENDPOINT: SIMULAR Y GUARDAR ---
@app.post("/simular", response_model=schemas.Simulacion)
def realizar_simulacion(entrada: schemas.SimulacionCreate, db: Session = Depends(get_db)):
    # 1. Calcular con el motor financiero
    res = utils.calcular_motor_sicap(entrada)
    
    # 2. Guardar cabecera de simulación
    sim = models.Simulacion(
        **entrada.dict(),
        monto_prestamo=res["monto_prestamo"],
        van=res["van"],
        tir=res["tir"],
        tcea=res["tcea"]
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)

    # 3. Guardar el cronograma detallado
    for cuota in res["cronograma"]:
        db.add(models.Cronograma(simulacion_id=sim.id, **cuota))
    db.commit()
    
    return sim

@app.get("/bancos")
def listar_bancos(db: Session = Depends(get_db)):
    return db.query(models.Banco).all()