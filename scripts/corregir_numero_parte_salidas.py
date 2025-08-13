#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir el problema del numero_parte en las salidas de material
"""

import mysql.connector
from datetime import datetime

# Configuración de base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_0900_ai_ci'
}

def verificar_estructura_tablas():
    """Verificar la estructura de las tablas"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("🔍 VERIFICANDO ESTRUCTURA DE TABLAS")
        print("=" * 60)
        
        # Verificar control_material_salida
        print("\n📋 Estructura de control_material_salida:")
        cursor.execute("DESCRIBE control_material_salida")
        columnas_salida = cursor.fetchall()
        
        tiene_numero_parte_salida = False
        for columna in columnas_salida:
            print(f"   {columna[0]} - {columna[1]}")
            if columna[0] == 'numero_parte':
                tiene_numero_parte_salida = True
        
        # Verificar control_material_almacen
        print("\n📋 Estructura de control_material_almacen:")
        cursor.execute("DESCRIBE control_material_almacen")
        columnas_almacen = cursor.fetchall()
        
        tiene_numero_parte_almacen = False
        for columna in columnas_almacen:
            print(f"   {columna[0]} - {columna[1]}")
            if columna[0] == 'numero_parte':
                tiene_numero_parte_almacen = True
        
        print(f"\n📊 RESULTADO:")
        print(f"   control_material_salida tiene numero_parte: {'✅ SÍ' if tiene_numero_parte_salida else '❌ NO'}")
        print(f"   control_material_almacen tiene numero_parte: {'✅ SÍ' if tiene_numero_parte_almacen else '❌ NO'}")
        
        cursor.close()
        conn.close()
        
        return tiene_numero_parte_salida, tiene_numero_parte_almacen
        
    except Exception as e:
        print(f"❌ Error verificando estructura: {e}")
        return False, False

def agregar_columna_numero_parte():
    """Agregar la columna numero_parte a control_material_salida si no existe"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🔧 AGREGANDO COLUMNA numero_parte A control_material_salida...")
        
        cursor.execute("""
            ALTER TABLE control_material_salida 
            ADD COLUMN numero_parte TEXT AFTER codigo_material_recibido
        """)
        
        conn.commit()
        print("✅ Columna numero_parte agregada exitosamente")
        
        cursor.close()
        conn.close()
        return True
        
    except mysql.connector.Error as e:
        if "Duplicate column name" in str(e):
            print("ℹ️  La columna numero_parte ya existe")
            return True
        else:
            print(f"❌ Error agregando columna: {e}")
            return False

def actualizar_salidas_existentes():
    """Actualizar salidas existentes con el numero_parte correspondiente"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🔄 ACTUALIZANDO SALIDAS EXISTENTES CON numero_parte...")
        
        # Actualizar salidas que no tienen numero_parte
        cursor.execute("""
            UPDATE control_material_salida cms
            JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
            SET cms.numero_parte = cma.numero_parte
            WHERE cms.numero_parte IS NULL OR cms.numero_parte = ''
        """)
        
        filas_actualizadas = cursor.rowcount
        conn.commit()
        
        print(f"✅ {filas_actualizadas} salidas actualizadas con numero_parte")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando salidas: {e}")
        return False

def verificar_correccion():
    """Verificar que las correcciones funcionaron"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n✅ VERIFICANDO CORRECCIONES...")
        
        # Contar salidas sin numero_parte
        cursor.execute("SELECT COUNT(*) FROM control_material_salida WHERE numero_parte IS NULL OR numero_parte = ''")
        sin_numero_parte = cursor.fetchone()[0]
        
        # Contar salidas con numero_parte
        cursor.execute("SELECT COUNT(*) FROM control_material_salida WHERE numero_parte IS NOT NULL AND numero_parte != ''")
        con_numero_parte = cursor.fetchone()[0]
        
        # Mostrar ejemplo
        cursor.execute("""
            SELECT id, codigo_material_recibido, numero_parte, modelo, fecha_salida 
            FROM control_material_salida 
            WHERE numero_parte IS NOT NULL AND numero_parte != ''
            ORDER BY id DESC 
            LIMIT 3
        """)
        
        ejemplos = cursor.fetchall()
        
        print(f"📊 ESTADÍSTICAS:")
        print(f"   Salidas sin numero_parte: {sin_numero_parte}")
        print(f"   Salidas con numero_parte: {con_numero_parte}")
        
        if ejemplos:
            print(f"\n📋 EJEMPLOS DE SALIDAS CORREGIDAS:")
            for ejemplo in ejemplos:
                print(f"   ID: {ejemplo[0]} | Código: {ejemplo[1]} | Número Parte: {ejemplo[2]} | Modelo: {ejemplo[3]}")
        
        cursor.close()
        conn.close()
        
        return sin_numero_parte == 0
        
    except Exception as e:
        print(f"❌ Error verificando: {e}")
        return False

def generar_codigo_corregido_routes():
    """Generar el código corregido para routes.py"""
    print("\n📝 GENERANDO CÓDIGO CORREGIDO PARA routes.py...")
    
    codigo_corregido = """
# CÓDIGO CORREGIDO PARA routes.py
# Reemplazar el INSERT de control_material_salida existente con este:

# Primero obtener el numero_parte desde control_material_almacen
cursor.execute('''
    SELECT numero_parte, especificacion 
    FROM control_material_almacen 
    WHERE codigo_material_recibido = %s
    LIMIT 1
''', (codigo_material_recibido,))

resultado_almacen = cursor.fetchone()
numero_parte_real = resultado_almacen[0] if resultado_almacen else codigo_material_recibido
especificacion_real = resultado_almacen[1] if resultado_almacen else data.get('especificacion_material', '')

# Registrar la salida en control_material_salida CON numero_parte
cursor.execute('''
    INSERT INTO control_material_salida (
        codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida, 
        proceso_salida, cantidad_salida, fecha_salida, especificacion_material
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
''', (
    codigo_material_recibido,
    numero_parte_real,  # ← NUEVO: numero_parte desde almacen
    data.get('numero_lote', ''),
    data.get('modelo', ''),
    data.get('depto_salida', ''),
    data.get('proceso_salida', ''),
    cantidad_salida,
    fecha_salida,
    especificacion_real  # ← MEJORADO: especificacion desde almacen
))
"""
    
    with open(r"c:\Users\yahir\OneDrive\Escritorio\MES\MES\MESILSANLOCAL\scripts\codigo_corregido_routes.py", 'w', encoding='utf-8') as f:
        f.write(codigo_corregido)
    
    print("✅ Código corregido guardado en: scripts/codigo_corregido_routes.py")

def main():
    """Función principal"""
    print("🔧 CORRECCIÓN DEL PROBLEMA DE numero_parte EN SALIDAS")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Verificar estructura
    tiene_salida, tiene_almacen = verificar_estructura_tablas()
    
    if not tiene_almacen:
        print("❌ PROBLEMA: control_material_almacen no tiene numero_parte")
        return
    
    # 2. Agregar columna si no existe
    if not tiene_salida:
        if not agregar_columna_numero_parte():
            print("❌ No se pudo agregar la columna numero_parte")
            return
    
    # 3. Actualizar salidas existentes
    if not actualizar_salidas_existentes():
        print("❌ No se pudieron actualizar las salidas existentes")
        return
    
    # 4. Verificar correcciones
    if verificar_correccion():
        print("\n🎉 ¡CORRECCIÓN COMPLETADA EXITOSAMENTE!")
        print("✅ Todas las salidas ahora tienen numero_parte")
    else:
        print("\n⚠️  Corrección parcial - revisar salidas sin numero_parte")
    
    # 5. Generar código para routes.py
    generar_codigo_corregido_routes()
    
    print("\n📋 PRÓXIMOS PASOS:")
    print("1. 🔄 Actualizar el código en routes.py con el código generado")
    print("2. 🔄 Actualizar el trigger para usar numero_parte real")
    print("3. ✅ Verificar que las nuevas salidas incluyan numero_parte")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Proceso cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error general: {e}")
    finally:
        input("\nPresione Enter para salir...")
