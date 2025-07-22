#!/usr/bin/env python3
"""
Script para restaurar permisos esenciales del sistema para superadmin
"""

import sqlite3
import os

def restaurar_permisos_sistema():
    """Restaurar solo los permisos esenciales del sistema"""
    # Conectar a la base de datos
    db_path = os.path.join('app', 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔧 Restaurando permisos esenciales del sistema...")
        
        # Permisos esenciales que necesita el sistema
        permisos_esenciales = [
            ('sistema', 'acceso', 'Acceso al sistema'),
            ('sistema', 'usuarios', 'Gestionar usuarios'),
            ('sistema', 'auditoria', 'Ver logs de auditoría'),
        ]
        
        print(f"📋 Creando {len(permisos_esenciales)} permisos esenciales...")
        
        permisos_creados = 0
        for modulo, accion, descripcion in permisos_esenciales:
            cursor.execute('''
                INSERT OR IGNORE INTO permisos (modulo, accion, descripcion) 
                VALUES (?, ?, ?)
            ''', (modulo, accion, descripcion))
            
            if cursor.rowcount > 0:
                permisos_creados += 1
                print(f"   ✅ {modulo}.{accion} - {descripcion}")
            else:
                print(f"   ℹ️ {modulo}.{accion} - Ya existe")
        
        print(f"📊 {permisos_creados} permisos nuevos creados")
        
        # Obtener el ID del rol superadmin
        cursor.execute('SELECT id FROM roles WHERE nombre = ? AND activo = 1', ('superadmin',))
        rol_result = cursor.fetchone()
        
        if not rol_result:
            print("❌ Rol superadmin no encontrado")
            return
        
        superadmin_id = rol_result[0]
        print(f"✅ Rol superadmin encontrado (ID: {superadmin_id})")
        
        # Asignar todos los permisos esenciales al superadmin
        permisos_asignados = 0
        for modulo, accion, _ in permisos_esenciales:
            # Obtener ID del permiso
            cursor.execute('SELECT id FROM permisos WHERE modulo = ? AND accion = ?', (modulo, accion))
            permiso_result = cursor.fetchone()
            
            if permiso_result:
                permiso_id = permiso_result[0]
                
                # Asignar al rol superadmin
                cursor.execute('''
                    INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id)
                    VALUES (?, ?)
                ''', (superadmin_id, permiso_id))
                
                if cursor.rowcount > 0:
                    permisos_asignados += 1
                    print(f"   ✅ Asignado: {modulo}.{accion}")
                else:
                    print(f"   ℹ️ Ya asignado: {modulo}.{accion}")
        
        conn.commit()
        
        print(f"\n✅ Proceso completado:")
        print(f"   📊 {permisos_creados} permisos creados")
        print(f"   📊 {permisos_asignados} permisos asignados a superadmin")
        
        # Verificar el estado final
        cursor.execute('''
            SELECT p.modulo, p.accion, p.descripcion
            FROM permisos p
            JOIN rol_permisos rp ON p.id = rp.permiso_id
            WHERE rp.rol_id = ?
            ORDER BY p.modulo, p.accion
        ''', (superadmin_id,))
        
        permisos_finales = cursor.fetchall()
        print(f"\n📋 Permisos del sistema asignados a superadmin ({len(permisos_finales)}):")
        for permiso in permisos_finales:
            modulo, accion, descripcion = permiso
            print(f"   🔑 {modulo}.{accion} - {descripcion}")
        
        # Verificar permisos de botones también
        cursor.execute('''
            SELECT COUNT(*) 
            FROM rol_permisos_botones rpb
            WHERE rpb.rol_id = ?
        ''', (superadmin_id,))
        
        count_botones = cursor.fetchone()[0]
        print(f"\n📊 Permisos de botones del superadmin: {count_botones}")
        
        print(f"\n🎯 Ahora el superadmin debería poder:")
        print("   ✅ Acceder al panel de administración")
        print("   ✅ Gestionar usuarios")
        print("   ✅ Ver auditoría")
        print("   ✅ Usar todas las funcionalidades de botones")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    restaurar_permisos_sistema()
