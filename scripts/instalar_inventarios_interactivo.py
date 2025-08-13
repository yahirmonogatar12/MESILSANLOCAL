#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador mejorado para sistema de inventarios múltiples por tipo de material
Ejecuta scripts SQL por separado para evitar problemas con delimitadores
"""

import mysql.connector
import os
import sys
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

def conectar_db():
    """Establece conexión con la base de datos"""
    try:
        print("🔐 Conectando a la base de datos remota...")
        print(f"   Host: {DB_CONFIG['host']}")
        print(f"   Puerto: {DB_CONFIG['port']}")
        print(f"   Base de datos: {DB_CONFIG['database']}")
        
        connection = mysql.connector.connect(**DB_CONFIG)
        connection.autocommit = False  # Control manual de transacciones
        print("✅ Conexión exitosa a la base de datos")
        return connection
    except mysql.connector.Error as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        print("💡 Verifique que los datos de conexión sean correctos")
        return None

def ejecutar_script_sql(connection, ruta_script, descripcion):
    """Ejecuta un script SQL específico"""
    print(f"\n📄 Ejecutando: {descripcion}")
    print(f"📁 Archivo: {ruta_script}")
    
    if not os.path.exists(ruta_script):
        print(f"❌ Archivo no encontrado: {ruta_script}")
        return False
    
    try:
        cursor = connection.cursor()
        
        # Leer el contenido del archivo
        with open(ruta_script, 'r', encoding='utf-8') as file:
            contenido = file.read()
        
        # Dividir en statements individuales
        statements = []
        current_statement = ""
        
        for linea in contenido.split('\n'):
            linea = linea.strip()
            
            # Ignorar comentarios y líneas vacías
            if not linea or linea.startswith('--'):
                continue
                
            current_statement += linea + '\n'
            
            # Si termina con ';' y no está dentro de un delimiter
            if linea.endswith(';') and 'DELIMITER' not in current_statement:
                statements.append(current_statement.strip())
                current_statement = ""
        
        # Agregar el último statement si existe
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        # Ejecutar cada statement
        ejecutados = 0
        errores = 0
        
        for i, statement in enumerate(statements):
            if not statement or statement.isspace():
                continue
                
            try:
                # Ejecutar statement directamente
                cursor.execute(statement)
                    
                ejecutados += 1
                print(f"  ✓ Statement {i+1} ejecutado correctamente")
                
            except mysql.connector.Error as e:
                errores += 1
                print(f"  ❌ Error en statement {i+1}: {e}")
                print(f"     Statement: {statement[:100]}...")
        
        # Commit de los cambios
        connection.commit()
        
        print(f"\n📊 Resumen de {descripcion}:")
        print(f"   ✓ Ejecutados: {ejecutados}")
        print(f"   ❌ Errores: {errores}")
        
        return errores == 0
        
    except Exception as e:
        print(f"❌ Error general ejecutando {descripcion}: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()

def verificar_tablas_creadas(connection):
    """Verifica que las tablas principales se hayan creado"""
    print("\n🔍 Verificando tablas creadas...")
    
    tablas_esperadas = [
        'InventarioRollosIMD',
        'InventarioRollosMAIN', 
        'HistorialMovimientosRollosIMD',
        'HistorialMovimientosRollosMAIN'
    ]
    
    try:
        cursor = connection.cursor()
        tablas_encontradas = []
        
        for tabla in tablas_esperadas:
            cursor.execute(f"SHOW TABLES LIKE '{tabla}'")
            if cursor.fetchone():
                tablas_encontradas.append(tabla)
                print(f"  ✓ {tabla}")
            else:
                print(f"  ❌ {tabla} - NO ENCONTRADA")
        
        cursor.close()
        return len(tablas_encontradas) == len(tablas_esperadas)
        
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
        return False

def verificar_triggers(connection):
    """Verifica que los triggers se hayan creado"""
    print("\n🔍 Verificando triggers...")
    
    triggers_esperados = [
        'tr_distribuir_salidas_por_tipo',
        'tr_historial_imd_insert',
        'tr_historial_main_insert'
    ]
    
    try:
        cursor = connection.cursor()
        triggers_encontrados = []
        
        for trigger in triggers_esperados:
            cursor.execute(f"SHOW TRIGGERS LIKE '{trigger}'")
            if cursor.fetchone():
                triggers_encontrados.append(trigger)
                print(f"  ✓ {trigger}")
            else:
                print(f"  ❌ {trigger} - NO ENCONTRADO")
        
        cursor.close()
        return len(triggers_encontrados) == len(triggers_esperados)
        
    except Exception as e:
        print(f"❌ Error verificando triggers: {e}")
        return False

def verificar_vistas(connection):
    """Verifica que las vistas se hayan creado"""
    print("\n🔍 Verificando vistas...")
    
    vistas_esperadas = [
        'vista_inventario_consolidado',
        'vista_resumen_inventarios',
        'vista_actividad_reciente',
        'vista_alertas_inventario'
    ]
    
    try:
        cursor = connection.cursor()
        vistas_encontradas = []
        
        for vista in vistas_esperadas:
            cursor.execute(f"SHOW TABLES LIKE '{vista}'")
            if cursor.fetchone():
                vistas_encontradas.append(vista)
                print(f"  ✓ {vista}")
            else:
                print(f"  ❌ {vista} - NO ENCONTRADA")
        
        cursor.close()
        return len(vistas_encontradas) == len(vistas_esperadas)
        
    except Exception as e:
        print(f"❌ Error verificando vistas: {e}")
        return False

def probar_distribucion_automatica(connection):
    """Prueba la distribución automática con datos de ejemplo"""
    print("\n🧪 Probando distribución automática...")
    
    try:
        cursor = connection.cursor()
        
        # Verificar si ya existen datos de prueba en control_material_almacen
        cursor.execute("""
            SELECT COUNT(*) as count FROM control_material_almacen 
            WHERE propiedad_material IN ('IMD', 'MAIN')
        """)
        
        result = cursor.fetchone()
        if result[0] > 0:
            print(f"  ✓ Ya existen {result[0]} materiales IMD/MAIN en almacén")
        else:
            print("  ⚠️  No hay materiales IMD/MAIN en almacén para probar")
            print("     Agregue algunos materiales con propiedad_material = 'IMD' o 'MAIN' para probar")
        
        # Verificar distribución automática actual
        cursor.execute("SELECT COUNT(*) FROM InventarioRollosIMD")
        imd_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM InventarioRollosMAIN") 
        main_count = cursor.fetchone()[0]
        
        print(f"  📊 Inventario IMD actual: {imd_count} rollos")
        print(f"  📊 Inventario MAIN actual: {main_count} rollos")
        
        cursor.close()
        return True
        
    except Exception as e:
        print(f"❌ Error probando distribución: {e}")
        return False

def main():
    """Función principal del instalador"""
    print("=" * 60)
    print("🚀 INSTALADOR DE INVENTARIOS MÚLTIPLES POR TIPO")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Conectar a la base de datos
    connection = conectar_db()
    if not connection:
        sys.exit(1)
    
    # Definir rutas de scripts
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    
    scripts = [
        {
            'archivo': os.path.join(scripts_dir, 'crear_inventarios_base.sql'),
            'descripcion': 'Creación de tablas base (IMD y MAIN)'
        },
        {
            'archivo': os.path.join(scripts_dir, 'crear_triggers_distribucion.sql'),
            'descripcion': 'Creación de triggers de distribución automática'
        },
        {
            'archivo': os.path.join(scripts_dir, 'crear_vistas_consolidadas.sql'),
            'descripcion': 'Creación de vistas consolidadas'
        }
    ]
    
    # Ejecutar scripts
    scripts_exitosos = 0
    for script in scripts:
        if ejecutar_script_sql(connection, script['archivo'], script['descripcion']):
            scripts_exitosos += 1
    
    print(f"\n📊 RESUMEN DE INSTALACIÓN:")
    print(f"   Scripts ejecutados: {scripts_exitosos}/{len(scripts)}")
    
    if scripts_exitosos == len(scripts):
        print("   🎉 ¡Instalación completada exitosamente!")
        
        # Verificaciones
        print("\n" + "=" * 40)
        print("🔍 VERIFICACIONES POST-INSTALACIÓN")
        print("=" * 40)
        
        tablas_ok = verificar_tablas_creadas(connection)
        triggers_ok = verificar_triggers(connection)
        vistas_ok = verificar_vistas(connection)
        
        # Pruebas
        print("\n" + "=" * 40)
        print("🧪 PRUEBAS DEL SISTEMA")
        print("=" * 40)
        
        distribucion_ok = probar_distribucion_automatica(connection)
        
        # Resultado final
        print("\n" + "=" * 60)
        if tablas_ok and triggers_ok and vistas_ok:
            print("✅ SISTEMA DE INVENTARIOS MÚLTIPLES INSTALADO CORRECTAMENTE")
            print("\n📋 PRÓXIMOS PASOS:")
            print("1. Verificar que el sistema está funcionando con datos reales")
            print("2. Configurar la interfaz web para IMD y MAIN")
            print("3. Crear material con propiedad_material = 'IMD' o 'MAIN' para probar")
            print("4. Generar salidas de material para activar la distribución automática")
        else:
            print("⚠️  INSTALACIÓN COMPLETADA CON ADVERTENCIAS")
            print("   Revise los errores anteriores y complete manualmente si es necesario")
        print("=" * 60)
        
    else:
        print("   ❌ Instalación incompleta - Revise los errores anteriores")
    
    # Cerrar conexión
    connection.close()
    
    input("\nPresione Enter para salir...")

if __name__ == "__main__":
    main()
