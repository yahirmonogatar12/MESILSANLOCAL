#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar el sistema de permisos del usuario admin en el hosting
"""

import mysql.connector
import os
from dotenv import load_dotenv

# Cargar variables de entorno del hosting
load_dotenv('hosting_config_mysql_directo.env')

def conectar_hosting():
    """Conectar a la base de datos del hosting"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USERNAME'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            port=int(os.getenv('MYSQL_PORT', 3306))
        )
        print(f"✅ Conexión exitosa al hosting: {os.getenv('MYSQL_DATABASE')}")
        return connection
    except Exception as e:
        print(f"❌ Error conectando al hosting: {e}")
        return None

def probar_permisos_admin():
    """Probar el sistema de permisos para el usuario admin"""
    connection = conectar_hosting()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("🔍 Probando sistema de permisos para usuario 'admin'...\n")
        
        # 1. Verificar que el usuario admin existe
        cursor.execute("SELECT id, username, activo FROM usuarios_sistema WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        
        if not admin_user:
            print("❌ Usuario 'admin' no encontrado")
            return
            
        print(f"✅ Usuario admin encontrado: ID {admin_user[0]}, activo: {admin_user[2]}")
        
        # 2. Verificar roles del usuario admin
        cursor.execute("""
            SELECT r.id, r.nombre, r.nivel
            FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN roles r ON ur.rol_id = r.id
            WHERE u.username = 'admin' AND u.activo = 1 AND r.activo = 1
            ORDER BY r.nivel DESC
        """)
        
        roles = cursor.fetchall()
        if not roles:
            print("❌ Usuario 'admin' no tiene roles asignados")
            return
            
        print(f"✅ Roles del usuario admin:")
        for rol in roles:
            print(f"  - {rol[1]} (ID: {rol[0]}, Nivel: {rol[2]})")
        
        rol_principal = roles[0]  # El de mayor nivel
        print(f"\n🔑 Rol principal: {rol_principal[1]}")
        
        # 3. Verificar permisos asignados al rol
        cursor.execute("""
            SELECT COUNT(*) 
            FROM rol_permisos_botones 
            WHERE rol_id = %s
        """, (rol_principal[0],))
        
        total_permisos = cursor.fetchone()[0]
        print(f"📊 Total de permisos asignados al rol '{rol_principal[1]}': {total_permisos}")
        
        if total_permisos == 0:
            print("⚠️ El rol no tiene permisos asignados")
            return
        
        # 4. Mostrar algunos permisos específicos
        cursor.execute("""
            SELECT pagina, seccion, boton 
            FROM rol_permisos_botones 
            WHERE rol_id = %s 
            ORDER BY pagina, seccion, boton
            LIMIT 10
        """, (rol_principal[0],))
        
        permisos_muestra = cursor.fetchall()
        print(f"\n📝 Primeros 10 permisos del rol '{rol_principal[1]}':")
        for permiso in permisos_muestra:
            print(f"  - {permiso[0]} > {permiso[1]} > {permiso[2]}")
        
        # 5. Probar consulta de verificación de permisos (simulando la función del sistema)
        print(f"\n🧪 Probando verificación de permisos específicos...")
        
        # Probar algunos permisos específicos
        permisos_prueba = [
            ('LISTA_DE_MATERIALES', 'Control de material', 'Control de material de almacén'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Control de salida'),
            ('LISTA_INFORMACIONBASICA', 'Administración de usuario', 'Administración de autoridad')
        ]
        
        for pagina, seccion, boton in permisos_prueba:
            cursor.execute("""
                SELECT COUNT(*) FROM usuarios_sistema u
                JOIN usuario_roles ur ON u.id = ur.usuario_id
                JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
                WHERE u.username = %s AND rpb.pagina = %s AND rpb.seccion = %s AND rpb.boton = %s
                AND u.activo = 1
            """, ('admin', pagina, seccion, boton))
            
            tiene_permiso = cursor.fetchone()[0] > 0
            estado = "✅ SÍ" if tiene_permiso else "❌ NO"
            print(f"  {estado} - {pagina} > {seccion} > {boton}")
        
        # 6. Verificar permisos por página
        cursor.execute("""
            SELECT pagina, COUNT(*) as total
            FROM rol_permisos_botones 
            WHERE rol_id = %s 
            GROUP BY pagina
            ORDER BY total DESC
        """, (rol_principal[0],))
        
        permisos_por_pagina = cursor.fetchall()
        print(f"\n📋 Permisos por página:")
        for pagina, total in permisos_por_pagina:
            print(f"  - {pagina}: {total} permisos")
        
        print(f"\n✅ Prueba de permisos completada exitosamente")
        
    except Exception as e:
        print(f"❌ Error probando permisos: {e}")
    finally:
        if connection:
            connection.close()
            print("\n🔐 Conexión cerrada")

if __name__ == "__main__":
    print("🚀 Iniciando prueba de permisos para usuario admin...\n")
    probar_permisos_admin()