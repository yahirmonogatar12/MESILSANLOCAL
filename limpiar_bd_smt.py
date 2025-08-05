#!/usr/bin/env python3
"""
Script para limpiar completamente la base de datos SMT y reprocesar archivos
"""

import mysql.connector
from mysql.connector import Error

def limpiar_base_datos():
    """Eliminar todos los registros para reprocesamiento"""
    
    # Configuración de base de datos
    db_config = {
        'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
        'port': 11550,
        'user': 'db_rrpq0erbdujn',
        'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
        'database': 'db_rrpq0erbdujn',
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    print("=== LIMPIEZA COMPLETA DE BASE DE DATOS SMT ===")
    
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # 1. Contar registros antes de eliminar
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        registros_antes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM archivos_procesados_smt")
        archivos_antes = cursor.fetchone()[0]
        
        print(f"📊 ESTADO ACTUAL:")
        print(f"   - Registros SMT: {registros_antes}")
        print(f"   - Archivos procesados: {archivos_antes}")
        
        # 2. Eliminar todos los registros de la tabla principal
        print(f"\n🗑️ ELIMINANDO REGISTROS...")
        cursor.execute("DELETE FROM historial_cambio_material_smt")
        registros_eliminados = cursor.rowcount
        print(f"   ✅ Eliminados {registros_eliminados} registros de historial_cambio_material_smt")
        
        # 3. Eliminar control de archivos procesados para que se reprocesen
        cursor.execute("DELETE FROM archivos_procesados_smt")
        archivos_eliminados = cursor.rowcount
        print(f"   ✅ Eliminados {archivos_eliminados} archivos de control")
        
        # 4. Reiniciar AUTO_INCREMENT
        cursor.execute("ALTER TABLE historial_cambio_material_smt AUTO_INCREMENT = 1")
        cursor.execute("ALTER TABLE archivos_procesados_smt AUTO_INCREMENT = 1")
        print(f"   ✅ Contadores AUTO_INCREMENT reiniciados")
        
        # 5. Verificar limpieza
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        registros_despues = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM archivos_procesados_smt")
        archivos_despues = cursor.fetchone()[0]
        
        print(f"\n✅ LIMPIEZA COMPLETADA:")
        print(f"   - Registros SMT restantes: {registros_despues}")
        print(f"   - Archivos en control: {archivos_despues}")
        
        if registros_despues == 0 and archivos_despues == 0:
            print(f"\n🎉 BASE DE DATOS COMPLETAMENTE LIMPIA")
            print(f"   El monitor reprocesará todos los archivos CSV con el mapeo corregido")
        else:
            print(f"\n⚠️ Algunos registros no se eliminaron correctamente")
        
    except Error as e:
        print(f"❌ Error limpiando base de datos: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    print("⚠️  ADVERTENCIA: Este script eliminará TODOS los registros SMT")
    print("   Esto permitirá que se reprocesen con el mapeo corregido")
    
    confirmacion = input("\n¿Confirmas la eliminación? (SI/no): ").strip().upper()
    
    if confirmacion == "SI":
        limpiar_base_datos()
        print(f"\n🚀 PRÓXIMO PASO:")
        print(f"   Reinicia el monitor SMT para que reprocese todos los archivos")
    else:
        print("❌ Operación cancelada")
