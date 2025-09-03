#!/usr/bin/env python3
"""
Script para probar el registro de entradas y salidas con zona horaria corregida
"""

import requests
import json
from datetime import datetime, timedelta

# Configuración
BASE_URL = "http://localhost:5000"
LOGIN_URL = f"{BASE_URL}/login"
REGISTER_URL = f"{BASE_URL}/guardar_control_almacen"
SALIDA_URL = f"{BASE_URL}/procesar_salida_material"

def test_timezone_fix():
    """Probar que las fechas se registren correctamente"""
    print("=== PRUEBA DE CORRECCIÓN DE ZONA HORARIA ===")
    
    # 1. Mostrar horas actuales
    print(f"\n1. HORAS DE REFERENCIA:")
    utc_now = datetime.utcnow()
    local_now = datetime.now()
    mexico_time = utc_now - timedelta(hours=6)
    
    print(f"   UTC:         {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Local:       {local_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   México:      {mexico_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 2. Login (si es necesario)
    session = requests.Session()
    
    # 3. Registrar material de entrada
    print(f"\n2. REGISTRANDO MATERIAL DE ENTRADA...")
    fecha_hoy = mexico_time.strftime('%Y-%m-%d')
    
    material_data = {
        "forma_material": "DIODO",
        "cliente": "ILSAN_ELECTRONICS", 
        "codigo_material_original": "TEST_TIMEZONE_001",
        "codigo_material": "TEST_TIMEZONE_001",
        "material_importacion_local": "LOCAL",
        "fecha_recibo": fecha_hoy,
        "fecha_fabricacion": fecha_hoy,
        "cantidad_actual": 100,
        "numero_lote_material": "LOTE_TZ_001",
        "codigo_material_recibido": f"TEST_TIMEZONE_001,{mexico_time.strftime('%Y%m%d')}0001",
        "numero_parte": "TEST_TZ_PART_001",
        "cantidad_estandarizada": 100,
        "codigo_material_final": "TEST_TIMEZONE_001_FINAL",
        "propiedad_material": "Prueba de zona horaria",
        "especificacion": "Material de prueba para validar zona horaria México",
        "material_importacion_local_final": "LOCAL",
        "estado_desecho": False,
        "ubicacion_salida": "ALMACEN_PRINCIPAL"
    }
    
    print(f"   Código: {material_data['codigo_material_recibido']}")
    print(f"   Fecha recibo: {material_data['fecha_recibo']}")
    print(f"   Cantidad: {material_data['cantidad_actual']}")
    
    # Enviar request (simulado, ya que necesita autenticación)
    print(f"   Status: [SIMULADO] - En sistema real verificar fechas en BD")
    
    # 4. Procesar salida
    print(f"\n3. REGISTRANDO SALIDA DE MATERIAL...")
    
    salida_data = {
        "codigo_material_recibido": material_data['codigo_material_recibido'],
        "cantidad_salida": 10,
        "modelo": "TEST_MODEL",
        "proceso_salida": "PRODUCCION",
        "depto_salida": "SMD_LINE_1"
    }
    
    print(f"   Código: {salida_data['codigo_material_recibido']}")
    print(f"   Cantidad salida: {salida_data['cantidad_salida']}")
    print(f"   Status: [SIMULADO] - En sistema real verificar fechas en BD")
    
    # 5. Mostrar qué verificar
    print(f"\n4. VERIFICACIONES EN BASE DE DATOS:")
    print(f"   📋 ENTRADA (tabla: control_material_almacen)")
    print(f"      - fecha_recibo debe ser: {fecha_hoy}")
    print(f"      - fecha_fabricacion debe ser: {fecha_hoy}")
    print(f"      - Campos automáticos deben usar hora México (~{mexico_time.strftime('%H:%M')})")
    
    print(f"\n   📤 SALIDA (tabla: control_material_salida)")
    print(f"      - fecha_registro debe usar hora México (~{mexico_time.strftime('%H:%M')})")
    print(f"      - NO debe usar UTC (que sería ~{utc_now.strftime('%H:%M')})")
    
    print(f"\n5. CONSULTAS SQL PARA VERIFICAR:")
    print(f"""
   -- Verificar entrada registrada:
   SELECT fecha_recibo, fecha_fabricacion, DATE_FORMAT(fecha_registro, '%H:%i') as hora_registro
   FROM control_material_almacen 
   WHERE codigo_material_recibido = '{material_data['codigo_material_recibido']}'
   ORDER BY id DESC LIMIT 1;
   
   -- Verificar salida registrada:
   SELECT DATE_FORMAT(fecha_registro, '%H:%i') as hora_registro_salida
   FROM control_material_salida 
   WHERE codigo_material_recibido = '{material_data['codigo_material_recibido']}'
   ORDER BY fecha_registro DESC LIMIT 1;
   
   -- Comparar con hora actual de MySQL:
   SELECT DATE_FORMAT(NOW(), '%H:%i') as mysql_now_utc,
          DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 6 HOUR), '%H:%i') as mexico_calculado;
    """)
    
    print(f"\n✅ RESULTADO ESPERADO:")
    print(f"   - Todas las horas deben coincidir con México (~{mexico_time.strftime('%H:%M')})")
    print(f"   - NO deben coincidir con UTC (~{utc_now.strftime('%H:%M')})")
    print(f"   - La diferencia debe ser exactamente -6 horas respecto a MySQL NOW()")

if __name__ == "__main__":
    test_timezone_fix()
