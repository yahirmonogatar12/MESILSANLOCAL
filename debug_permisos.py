#!/usr/bin/env python3
"""
Script para diagnosticar permisos del usuario Daniel
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db_mysql import get_connection

def diagnosticar_usuario_daniel():
    """Diagnostica los permisos del usuario Daniel"""
    try:
        conexion = get_connection()
        cursor = conexion.cursor()
        
        print("🔍 DIAGNÓSTICO DE PERMISOS - USUARIO DANIEL")
        print("=" * 50)
        
        # 1. Primero ver qué tablas existen
        cursor.execute("SHOW TABLES")
        tablas = cursor.fetchall()
        print("📋 Tablas disponibles:")
        for tabla in tablas:
            print(f"   - {tabla[0]}")
        print()
        
        # 2. Ver estructura de tabla usuarios si existe
        try:
            cursor.execute("DESCRIBE usuarios")
            columnas = cursor.fetchall()
            print("🗃️ Estructura tabla 'usuarios':")
            for col in columnas:
                print(f"   - {col[0]} ({col[1]})")
            print()
        except Exception as e:
            print(f"⚠️ Tabla 'usuarios' no existe o error: {e}")
            
        # 3. Buscar usuario Daniel con diferentes estructuras posibles
        try:
            cursor.execute("SELECT * FROM usuarios WHERE username = %s", ('Daniel',))
            usuario_info = cursor.fetchone()
            if usuario_info:
                print(f"✅ Usuario Daniel encontrado:")
                print(f"   ID: {usuario_info[0]}")
                print(f"   Username: {usuario_info[1]}")
                print(f"   Area: {usuario_info[3]}")
                print(f"   Activo: {usuario_info[4]}")
                print(f"   Fecha creación: {usuario_info[5]}")
                
                usuario_id = usuario_info[0]
                
                # 4. Buscar roles del usuario
                cursor.execute("""
                    SELECT r.nombre, r.descripcion 
                    FROM roles r
                    JOIN usuario_roles ur ON r.id = ur.rol_id
                    WHERE ur.usuario_id = %s
                """, (usuario_id,))
                roles = cursor.fetchall()
                
                print(f"\n🎭 ROLES ASIGNADOS ({len(roles)}):")
                for rol in roles:
                    print(f"   - {rol[0]} ({rol[1]})")
                    
                    # Verificar si es admin
                    if rol[0].lower() in ['admin', 'superadmin']:
                        print(f"   ⚠️ ROL ADMINISTRATIVO DETECTADO")
                        print(f"   Este rol bypasea las restricciones de permisos!")
                
                # 5. Buscar permisos específicos
                print(f"\n📋 PERMISOS ESPECÍFICOS:")
                cursor.execute("""
                    SELECT p.pagina, p.seccion, p.boton, rp.habilitado
                    FROM permisos p
                    JOIN rol_permisos rp ON p.id = rp.permiso_id
                    JOIN usuario_roles ur ON rp.rol_id = ur.rol_id
                    WHERE ur.usuario_id = %s
                    ORDER BY p.pagina, p.seccion, p.boton
                """, (usuario_id,))
                permisos = cursor.fetchall()
                
                if permisos:
                    print(f"   Total permisos: {len(permisos)}")
                    
                    # Filtrar permisos de LISTA_DE_MATERIALES
                    materiales_permisos = [p for p in permisos if p[0] == 'LISTA_DE_MATERIALES']
                    print(f"\n🎯 PERMISOS LISTA_DE_MATERIALES ({len(materiales_permisos)}):")
                    
                    for pagina, seccion, boton, habilitado in materiales_permisos:
                        estado = "✅ HABILITADO" if habilitado else "❌ DESHABILITADO"
                        print(f"   {estado} | {seccion} > {boton}")
                        
                else:
                    print("   No se encontraron permisos específicos")
                    
            else:
                print("❌ Usuario 'Daniel' no encontrado")
                
                # Mostrar usuarios existentes
                cursor.execute("SELECT username FROM usuarios LIMIT 10")
                usuarios = cursor.fetchall()
                print("👥 Usuarios disponibles:")
                for usuario in usuarios:
                    print(f"   - {usuario[0]}")
                    
        except Exception as e:
            print(f"❌ Error consultando usuario: {e}")
            
        # 6. Estructura de permisos
        print(f"\n🗃️ Estructura tabla 'permisos':")
        try:
            cursor.execute("DESCRIBE permisos")
            columnas = cursor.fetchall()
            for col in columnas:
                print(f"   - {col[0]} ({col[1]})")
        except Exception as e:
            print(f"❌ Error: {e}")
            
        print(f"\n�️ Estructura tabla 'rol_permisos':")
        try:
            cursor.execute("DESCRIBE rol_permisos")
            columnas = cursor.fetchall()
            for col in columnas:
                print(f"   - {col[0]} ({col[1]})")
        except Exception as e:
            print(f"❌ Error: {e}")
            
    except Exception as e:
        print(f"❌ Error durante el diagnóstico: {e}")
    finally:
        if 'conexion' in locals():
            conexion.close()

if __name__ == "__main__":
    diagnosticar_usuario_daniel()
