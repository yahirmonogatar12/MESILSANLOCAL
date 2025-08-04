#!/usr/bin/env python3
"""
Comparar archivos detectados por el monitor vs archivos reales
"""

import os
import glob
import mysql.connector
from datetime import datetime

def conectar_bd():
    """Conectar a la base de datos"""
    try:
        return mysql.connector.connect(
            host='up-de-fra1-mysql-1.db.run-on-seenode.com',
            port=11550,
            user='db_rrpq0erbdujn',
            password='5fUNbSRcPP3LN9K2I33Pr0ge',
            database='db_rrpq0erbdujn',
            charset='utf8mb4'
        )
    except Exception as e:
        print(f"Error conectando a BD: {e}")
        return None

def archivos_procesados_en_bd():
    """Obtener lista de archivos procesados según la BD"""
    conn = conectar_bd()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT archivo, registros_procesados, fecha_procesado FROM archivos_procesados_smt ORDER BY fecha_procesado DESC")
        return cursor.fetchall()
    except Exception as e:
        print(f"Error consultando BD: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def archivos_en_carpetas():
    """Obtener lista de archivos CSV en las carpetas"""
    carpetas = [
        r"C:\LOT CHECK ALL\1line",
        r"C:\LOT CHECK ALL\2line",
        r"C:\LOT CHECK ALL\3line",
        r"C:\LOT CHECK ALL\4line"
    ]
    
    archivos_encontrados = {}
    
    for carpeta in carpetas:
        if os.path.exists(carpeta):
            archivos = glob.glob(os.path.join(carpeta, "*.csv"))
            carpeta_nombre = os.path.basename(carpeta)
            archivos_encontrados[carpeta_nombre] = [os.path.basename(f) for f in archivos]
        else:
            print(f"⚠️  Carpeta no existe: {carpeta}")
    
    return archivos_encontrados

def main():
    print("=" * 70)
    print("COMPARACIÓN: ARCHIVOS DETECTADOS vs ARCHIVOS PROCESADOS")
    print("=" * 70)
    
    # Obtener archivos de carpetas
    print("\n📁 ARCHIVOS EN CARPETAS:")
    archivos_carpetas = archivos_en_carpetas()
    
    total_archivos_carpetas = 0
    for carpeta, archivos in archivos_carpetas.items():
        print(f"\n{carpeta}: {len(archivos)} archivos")
        total_archivos_carpetas += len(archivos)
        
        # Mostrar algunos archivos
        for archivo in sorted(archivos)[-3:]:
            print(f"   📄 {archivo}")
        
        if len(archivos) > 3:
            print(f"   ... y {len(archivos) - 3} más")
    
    print(f"\nTotal en carpetas: {total_archivos_carpetas} archivos")
    
    # Obtener archivos procesados
    print(f"\n💾 ARCHIVOS PROCESADOS EN BD:")
    archivos_bd = archivos_procesados_en_bd()
    
    if archivos_bd:
        print(f"Total procesados: {len(archivos_bd)} archivos")
        print(f"\nÚltimos 10 procesados:")
        
        for archivo, registros, fecha in archivos_bd[:10]:
            print(f"   ✅ {archivo} ({registros} registros) - {fecha}")
    else:
        print("❌ No se pudieron obtener archivos procesados (problema de BD?)")
    
    # Comparar
    print(f"\n🔍 ANÁLISIS:")
    archivos_bd_nombres = [archivo[0] for archivo in archivos_bd] if archivos_bd else []
    todos_archivos_carpetas = []
    
    for archivos in archivos_carpetas.values():
        todos_archivos_carpetas.extend(archivos)
    
    no_procesados = []
    for archivo in todos_archivos_carpetas:
        if archivo not in archivos_bd_nombres:
            no_procesados.append(archivo)
    
    if no_procesados:
        print(f"⚠️  Archivos SIN procesar: {len(no_procesados)}")
        for archivo in sorted(no_procesados)[:5]:
            print(f"   📄 {archivo}")
        if len(no_procesados) > 5:
            print(f"   ... y {len(no_procesados) - 5} más")
    else:
        print(f"✅ Todos los archivos han sido procesados")
    
    print(f"\n" + "=" * 70)

if __name__ == "__main__":
    main()
