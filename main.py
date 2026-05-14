from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import models, schemas, utils
from database import SessionLocal, engine

# Inicializar la aplicación
app = FastAPI(title="API SICAP - Simulador Financiero")

# Configurar CORS para que React pueda conectarse
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint para Simular y Guardar el Crédito
@app.post("/simular", response_model=schemas.ResultadoSimulacion)
def realizar_simulacion(entrada: schemas.SimulacionEntrada, db: Session = Depends(SessionLocal)):
    # 1. Ejecutar el Algoritmo (Punto 7 del informe)
    resultados = utils.calcular_motor_sicap(entrada)
    
    # 2. Guardar Cliente en la Base de Datos (Railway)
    nuevo_cliente = models.Cliente(
        nombre=entrada.nombre_cliente,
        apellido=entrada.apellido_cliente,
        dni=entrada.dni_cliente,
        email=entrada.email_cliente,
        telefono=entrada.telefono_cliente,
        ingreso_mensual=entrada.ingreso_mensual
    )
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)

    # 3. Guardar Cabecera del Préstamo
    nuevo_prestamo = models.Prestamo(
        cliente_id=nuevo_cliente.id,
        marca_vehiculo=entrada.marca_vehiculo,
        modelo_vehiculo=entrada.modelo_vehiculo,
        anio_vehiculo=entrada.anio_vehiculo,
        precio_base=entrada.precio_base,
        cuota_inicial=entrada.cuota_inicial,
        plazo_meses=entrada.plazo_meses,
        tasa_valor=entrada.tasa_valor,
        monto_financiado=resultados["monto_financiado"],
        tcea=resultados["tcea"],
        van=resultados["van"],
        tir_mensual=resultados["tir_mensual"]
    )
    db.add(nuevo_prestamo)
    db.commit()
    db.refresh(nuevo_prestamo)

    # 4. Guardar Cronograma Detallado
    for cuota in resultados["cronograma"]:
        nuevo_paso = models.Cronograma(
            prestamo_id=nuevo_prestamo.id,
            **cuota # Esto mapea automáticamente los campos del diccionario
        )
        db.add(nuevo_paso)
    
    db.commit()
    return resultados