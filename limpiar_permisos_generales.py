#!/usr/bin/env python3
"""
Script para eliminar permisos generales y dejar solo permisos_botones
"""

import sqlite3
import os

def limpiar_permisos_generales():
    # Conectar a la base de datos
    db_path = os.path.join('app', 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔍 Verificando permisos generales actuales...")
        
        # Mostrar permisos generales actuales
        cursor.execute('SELECT id, modulo, accion, descripcion FROM permisos')
        permisos_generales = cursor.fetchall()
        
        print(f"📋 Encontrados {len(permisos_generales)} permisos generales:")
        for permiso in permisos_generales:
            print(f"   ID: {permiso[0]} | {permiso[1]}.{permiso[2]} | {permiso[3]}")
        
        if permisos_generales:
            respuesta = input(f"\n❓ ¿Eliminar todos los {len(permisos_generales)} permisos generales? (s/N): ")
            
            if respuesta.lower() in ['s', 'si', 'sí', 'y', 'yes']:
                print("🗑️ Eliminando permisos generales...")
                
                # Eliminar relaciones rol-permisos primero
                cursor.execute('DELETE FROM rol_permisos')
                print("   ✅ Relaciones rol-permisos eliminadas")
                
                # Eliminar permisos generales
                cursor.execute('DELETE FROM permisos')
                print("   ✅ Permisos generales eliminados")
                
                conn.commit()
                print("✅ Limpieza completada. Solo quedan los permisos_botones")
                
                # Verificar permisos_botones
                cursor.execute('SELECT COUNT(*) FROM permisos_botones WHERE activo = 1')
                count_botones = cursor.fetchone()[0]
                print(f"📊 Permisos de botones disponibles: {count_botones}")
                
            else:
                print("❌ Operación cancelada")
        else:
            print("✅ No hay permisos generales para eliminar")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    limpiar_permisos_generales()
