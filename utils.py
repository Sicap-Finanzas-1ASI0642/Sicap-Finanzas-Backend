import numpy_financial as npf
from decimal import Decimal, ROUND_HALF_UP

def calcular_motor_sicap(datos):
    # 1. Preparación de Datos (Análisis 6.1.1)
    # Monto a financiar (Precio - Inicial)
    p_base = float(datos.precio_base)
    c_inicial = float(datos.cuota_inicial)
    monto_financiado = p_base - c_inicial
    
    # Cuota Balón (Monto que se paga al final)
    cuota_balon = monto_financiado * float(datos.cuota_balon_pct)
    n = datos.plazo_meses
    
    # 2. Conversión de Tasas (Marco Teórico 5.2)
    # TEA a TEM (Tasa Efectiva Mensual)
    tea = float(datos.tasa_valor)
    tem = (1 + tea)**(1/12) - 1
    
    # 3. Cálculo de Cuota Ordinaria (Método Francés con Cuota Balón)
    # Fórmula: R = [PV - Balon/(1+i)^n] / [(1-(1+i)^-n)/i]
    vp_balon = cuota_balon / (1 + tem)**n
    numerador_cuota = monto_financiado - vp_balon
    denominador_cuota = (1 - (1 + tem)**-n) / tem
    cuota_mensual_base = numerador_cuota / denominador_cuota
    
    cronograma = []
    saldo_inicial = monto_financiado
    flujos_caja = [-monto_financiado] # Inicia con el desembolso para VAN/TIR
    
    # 4. Generación del Cronograma (Datos de Salida 6.1.2)
    for k in range(1, n + 1):
        interes_mes = saldo_inicial * tem
        amortizacion_mes = cuota_mensual_base - interes_mes
        
        # Seguros y Portes
        seg_vehicular = p_base * float(datos.seguro_vehicular_pct)
        seg_desgravamen = saldo_inicial * float(datos.seguro_desgravamen_pct)
        portes = float(datos.portes)
        
        # Sumar cuota balón solo en el último mes
        pago_balon_final = cuota_balon if k == n else 0
        cuota_total_k = cuota_mensual_base + pago_balon_final + seg_vehicular + seg_desgravamen + portes
        
        saldo_final = saldo_inicial - amortizacion_mes
        
        cronograma.append({
            "numero_cuota": k,
            "saldo_inicial": round(saldo_inicial, 2),
            "interes": round(interes_mes, 2),
            "amortizacion": round(amortizacion_mes, 2),
            "cuota_total": round(cuota_total_k, 2),
            "saldo_final": max(0, round(saldo_final, 2))
        })
        
        flujos_caja.append(cuota_total_k)
        saldo_inicial = saldo_final

    # 5. Cálculo de Indicadores Finales
    tir_mensual = npf.irr(flujos_caja)
    tcea = (1 + tir_mensual)**12 - 1
    van = npf.npv(tem, flujos_caja)

    return {
        "cronograma": cronograma,
        "monto_financiado": round(monto_financiado, 2),
        "cuota_balon_monto": round(cuota_balon, 2),
        "tcea": round(tcea * 100, 4),
        "van": round(van, 2),
        "tir_mensual": round(tir_mensual * 100, 4)
    }