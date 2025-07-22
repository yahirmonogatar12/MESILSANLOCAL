#!/usr/bin/env python3
"""
Script para asignar todos los permisos de botones al rol superadmin
"""

import sqlite3
import os

def asignar_permisos_superadmin():
    """Asignar todos los permisos de botones al rol superadmin"""
    # Conectar a la base de datos
    db_path = os.path.join('app', 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔍 Verificando rol superadmin...")
        
        # Encontrar el ID del rol superadmin
        cursor.execute('SELECT id FROM roles WHERE nombre = ? AND activo = 1', ('superadmin',))
        rol_result = cursor.fetchone()
        
        if not rol_result:
            print("❌ Rol superadmin no encontrado")
            return
        
        rol_id = rol_result[0]
        print(f"✅ Rol superadmin encontrado (ID: {rol_id})")
        
        # Obtener todos los permisos de botones activos
        cursor.execute('SELECT id FROM permisos_botones WHERE activo = 1')
        permisos_botones = cursor.fetchall()
        
        print(f"📋 Encontrados {len(permisos_botones)} permisos de botones")
        
        # Verificar permisos actuales del rol
        cursor.execute('SELECT COUNT(*) FROM rol_permisos_botones WHERE rol_id = ?', (rol_id,))
        permisos_actuales = cursor.fetchone()[0]
        print(f"📊 Permisos actuales del rol superadmin: {permisos_actuales}")
        
        respuesta = input(f"\n❓ ¿Asignar todos los {len(permisos_botones)} permisos al rol superadmin? (s/N): ")
        
        if respuesta.lower() in ['s', 'si', 'sí', 'y', 'yes']:
            print("🔧 Asignando permisos...")
            
            # Limpiar permisos existentes del rol
            cursor.execute('DELETE FROM rol_permisos_botones WHERE rol_id = ?', (rol_id,))
            print("   🗑️ Permisos existentes eliminados")
            
            # Asignar todos los permisos de botones
            permisos_insertados = 0
            for permiso in permisos_botones:
                permiso_id = permiso[0]
                try:
                    cursor.execute('''
                        INSERT INTO rol_permisos_botones (rol_id, permiso_boton_id)
                        VALUES (?, ?)
                    ''', (rol_id, permiso_id))
                    permisos_insertados += 1
                except sqlite3.IntegrityError:
                    # Permiso ya existe, continuar
                    pass
            
            conn.commit()
            print(f"   ✅ {permisos_insertados} permisos asignados al rol superadmin")
            
            # Verificar la asignación
            cursor.execute('SELECT COUNT(*) FROM rol_permisos_botones WHERE rol_id = ?', (rol_id,))
            permisos_finales = cursor.fetchone()[0]
            print(f"✅ Verificación: {permisos_finales} permisos asignados correctamente")
            
            # Mostrar algunos ejemplos de permisos asignados
            cursor.execute('''
                SELECT pb.pagina, pb.seccion, pb.boton
                FROM permisos_botones pb
                JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
                WHERE rpb.rol_id = ? AND pb.activo = 1
                ORDER BY pb.pagina, pb.seccion, pb.boton
                LIMIT 10
            ''', (rol_id,))
            
            ejemplos = cursor.fetchall()
            print(f"\n📋 Ejemplos de permisos asignados:")
            for ejemplo in ejemplos:
                pagina, seccion, boton = ejemplo
                print(f"   ✅ {pagina} > {seccion} > {boton}")
            
            if len(ejemplos) == 10:
                print("   ... y muchos más")
                
        else:
            print("❌ Operación cancelada")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    asignar_permisos_superadmin()
