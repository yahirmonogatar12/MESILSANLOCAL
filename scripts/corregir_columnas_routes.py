#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir errores de nombres de columnas en routes.py
"""

import re

def corregir_routes_py():
    ruta_archivo = r"c:\Users\yahir\OneDrive\Escritorio\MES\MES\MESILSANLOCAL\app\routes.py"
    
    print("🔧 Corrigiendo errores de columnas en routes.py...")
    
    try:
        # Leer el archivo
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Hacer una copia de respaldo
        with open(ruta_archivo + '.backup', 'w', encoding='utf-8') as f:
            f.write(contenido)
        print("✅ Backup creado: routes.py.backup")
        
        # Correcciones
        correcciones = 0
        
        # 1. Corregir cantidad_recibida por cantidad_actual en control_material_almacen
        patron1 = r"SELECT SUM\(cantidad_recibida\) as total_entradas\s+FROM control_material_almacen"
        if re.search(patron1, contenido):
            contenido = re.sub(patron1, "SELECT SUM(cantidad_actual) as total_entradas\n            FROM control_material_almacen", contenido)
            correcciones += 1
            print("✅ Corregido: cantidad_recibida → cantidad_actual en SELECT")
        
        # 2. Corregir cantidad_actual por cantidad_total en inventario_general
        patron2 = r"INSERT INTO inventario_general \(numero_parte, cantidad_actual, fecha_actualizacion\)"
        if re.search(patron2, contenido):
            contenido = re.sub(patron2, "INSERT INTO inventario_general (numero_parte, cantidad_total, fecha_actualizacion)", contenido)
            correcciones += 1
            print("✅ Corregido: cantidad_actual → cantidad_total en INSERT")
        
        patron3 = r"cantidad_actual = %s,"
        contenido = re.sub(patron3, "cantidad_total = %s,", contenido)
        if patron3 in contenido:
            correcciones += 1
            print("✅ Corregido: cantidad_actual → cantidad_total en UPDATE")
        
        # 3. Buscar y corregir otros casos de cantidad_recibida
        if "cantidad_recibida" in contenido:
            # En casos donde debería ser cantidad_actual
            contenido = contenido.replace("cantidad_recibida", "cantidad_actual")
            correcciones += 1
            print("✅ Corregido: cantidad_recibida → cantidad_actual en otros casos")
        
        # Escribir el archivo corregido
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"\n📊 Resumen:")
        print(f"   ✅ Correcciones aplicadas: {correcciones}")
        print(f"   📄 Archivo actualizado: routes.py")
        print(f"   💾 Backup disponible: routes.py.backup")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    corregir_routes_py()
    input("Presione Enter para continuar...")
