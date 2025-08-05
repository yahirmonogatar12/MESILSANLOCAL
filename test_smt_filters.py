#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Probar filtros SMT
"""

import requests
import json
from datetime import datetime, timedelta

def test_smt_filters():
    """Probar los filtros de SMT"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Probando filtros de SMT Simple...")
    
    # Prueba 1: Sin filtros
    print("\n1️⃣ Prueba sin filtros:")
    try:
        response = requests.get(f"{base_url}/api/historial_smt_data")
        data = response.json()
        print(f"   📊 Registros: {data.get('total', 0)}")
        print(f"   ✅ Status: {data.get('status', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Prueba 2: Con filtro de fecha
    print("\n2️⃣ Prueba con filtro de fecha (hoy):")
    hoy = datetime.now().strftime('%Y-%m-%d')
    try:
        response = requests.get(f"{base_url}/api/historial_smt_data?fecha_desde={hoy}&fecha_hasta={hoy}")
        data = response.json()
        print(f"   📊 Registros para {hoy}: {data.get('total', 0)}")
        print(f"   ✅ Status: {data.get('status', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Prueba 3: Con rango de fechas (últimos 7 días)
    print("\n3️⃣ Prueba con rango de fechas (últimos 7 días):")
    hace_7_dias = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    try:
        response = requests.get(f"{base_url}/api/historial_smt_data?fecha_desde={hace_7_dias}&fecha_hasta={hoy}")
        data = response.json()
        print(f"   📊 Registros últimos 7 días: {data.get('total', 0)}")
        print(f"   ✅ Status: {data.get('status', 'unknown')}")
        
        # Mostrar muestra de datos
        if data.get('data') and len(data['data']) > 0:
            print(f"   📋 Muestra del primer registro:")
            primer_registro = data['data'][0]
            print(f"      Fecha: {primer_registro.get('fecha_formateada', primer_registro.get('ScanDate'))}")
            print(f"      Hora: {primer_registro.get('hora_formateada', primer_registro.get('ScanTime'))}")
            print(f"      Resultado: {primer_registro.get('Result')}")
            print(f"      Línea: {primer_registro.get('linea')}")
            print(f"      Máquina: {primer_registro.get('maquina')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Prueba 4: Estadísticas
    print("\n4️⃣ Prueba de estadísticas:")
    try:
        response = requests.get(f"{base_url}/api/smt_stats")
        data = response.json()
        if data.get('status') == 'success':
            stats = data.get('stats', {})
            print(f"   📊 Total: {stats.get('total', 0)}")
            print(f"   📊 Hoy: {stats.get('hoy', 0)}")
            print(f"   📊 Por resultado: {stats.get('por_resultado', {})}")
        print(f"   ✅ Status: {data.get('status', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_smt_filters()
