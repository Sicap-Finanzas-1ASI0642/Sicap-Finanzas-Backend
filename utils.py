import numpy_financial as npf
from decimal import Decimal

def calcular_motor_sicap(data):
    # 1. Variables base
    precio = float(data.precio_venta)
    inicial = precio * (float(data.cuota_inicial_pct) / 100)
    monto_financiar = precio - inicial
    plazo = data.plazo_meses
    
    # 2. Convertir Tasa a TEM (Tasa Efectiva Mensual)
    tasa_anual = float(data.tasa_valor) / 100
    if data.tipo_tasa == "TNA":
        # Convertir TNA a TEA asumiendo capitalización diaria (360)
        tasa_anual = (1 + tasa_anual / 360) ** 360 - 1
    
    tem = (1 + tasa_anual) ** (1/12) - 1
    
    # 3. Generar Cronograma
    cronograma = []
    saldo = monto_financiar
    flujos = [-monto_financiar] # Para el cálculo de la TIR
    
    for i in range(1, plazo + 1):
        interes = saldo * tem
        
        # Lógica de Gracia
        if i <= data.meses_gracia:
            if data.tipo_periodo_gracia == "Total":
                amortizacion = 0
                cuota_pagar = 0
                saldo += interes # El interés se capitaliza
            else: # Gracia Parcial
                amortizacion = 0
                cuota_pagar = interes
        else:
            # Cálculo de cuota francesa simple
            restante = plazo - max(i-1, data.meses_gracia)
            cuota_pagar = saldo * (tem * (1 + tem)**restante) / ((1 + tem)**restante - 1)
            amortizacion = cuota_pagar - interes
            saldo -= amortizacion

        fila = {
            "nro_cuota": i,
            "saldo_inicial": round(saldo + amortizacion if i > data.meses_gracia else saldo, 2),
            "amortizacion": round(amortizacion, 2),
            "interes": round(interes, 2),
            "seguro_desgravamen": 0, # Implementar según lógica de banco
            "seguro_vehicular": 0,
            "comision_cuota": 0,
            "portes_cuota": 0,
            "cuota_total": round(cuota_pagar, 2),
            "saldo_final": round(max(saldo, 0), 2)
        }
        cronograma.append(fila)
        flujos.append(cuota_pagar)

    # 4. Indicadores VAN y TIR
    # VAN = Sumatoria de flujos descontados a una tasa de oportunidad (ej. 10%)
    cok = 0.10 / 12
    van = npf.npv(cok, flujos)
    tir = npf.irr(flujos)

    return {
        "monto_prestamo": monto_financiar,
        "cronograma": cronograma,
        "van": round(van, 2),
        "tir": round(tir, 6),
        "tcea": round(tasa_anual * 1.05, 6) # Estimación simple para el ejemplo
    }