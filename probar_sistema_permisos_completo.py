#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar el sistema completo de permisos después de las correcciones
"""

import os
import sys
import requests
from dotenv import load_dotenv
import pymysql

# Cargar configuración del hosting
load_dotenv('hosting_config_mysql_directo.env')

def conectar_hosting():
    """Conectar a la base de datos del hosting"""
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USERNAME'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"❌ Error conectando al hosting: {e}")
        return None

def verificar_usuario_admin(conn):
    """Verificar el usuario admin y sus roles"""
    try:
        cursor = conn.cursor()
        
        # Verificar usuario admin
        cursor.execute("""
            SELECT id, username, activo 
            FROM usuarios_sistema 
            WHERE username = 'admin'
        """)
        usuario = cursor.fetchone()
        
        if not usuario:
            print("❌ Usuario 'admin' no encontrado")
            return False
            
        print(f"✅ Usuario admin encontrado: ID {usuario['id']}, Activo: {usuario['activo']}")
        
        # Verificar roles del usuario
        cursor.execute("""
            SELECT r.id, r.nombre, r.nivel, ur.fecha_asignacion
            FROM usuario_roles ur
            JOIN roles r ON ur.rol_id = r.id
            WHERE ur.usuario_id = %s
            ORDER BY r.nivel DESC
        """, (usuario['id'],))
        
        roles = cursor.fetchall()
        
        if roles:
            print(f"\n🎭 Roles del usuario admin:")
            for rol in roles:
                print(f"   - {rol['nombre']} (ID: {rol['id']}, Nivel: {rol['nivel']})")
                print(f"     📅 Asignado: {rol['fecha_asignacion']}")
        else:
            print("❌ No se encontraron roles para el usuario admin")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error verificando usuario admin: {e}")
        return False

def verificar_permisos_admin(conn):
    """Verificar permisos del usuario admin"""
    try:
        cursor = conn.cursor()
        
        # Contar permisos totales del admin
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM usuario_roles ur
            JOIN roles r ON ur.rol_id = r.id
            JOIN rol_permisos_botones rpb ON r.id = rpb.rol_id
            JOIN usuarios_sistema u ON ur.usuario_id = u.id
            WHERE u.username = 'admin'
        """)
        
        total_permisos = cursor.fetchone()['total']
        print(f"\n🔐 Total de permisos del usuario admin: {total_permisos}")
        
        # Mostrar algunos permisos específicos
        cursor.execute("""
            SELECT rpb.pagina, rpb.seccion, rpb.boton
            FROM usuario_roles ur
            JOIN roles r ON ur.rol_id = r.id
            JOIN rol_permisos_botones rpb ON r.id = rpb.rol_id
            JOIN usuarios_sistema u ON ur.usuario_id = u.id
            WHERE u.username = 'admin'
            ORDER BY rpb.pagina, rpb.seccion, rpb.boton
            LIMIT 10
        """)
        
        permisos_muestra = cursor.fetchall()
        
        if permisos_muestra:
            print("\n📋 Primeros 10 permisos del admin:")
            for permiso in permisos_muestra:
                print(f"   - {permiso['pagina']} > {permiso['seccion']} > {permiso['boton']}")
        
        # Verificar permisos por página
        cursor.execute("""
            SELECT rpb.pagina, COUNT(*) as cantidad
            FROM usuario_roles ur
            JOIN roles r ON ur.rol_id = r.id
            JOIN rol_permisos_botones rpb ON r.id = rpb.rol_id
            JOIN usuarios_sistema u ON ur.usuario_id = u.id
            WHERE u.username = 'admin'
            GROUP BY rpb.pagina
            ORDER BY cantidad DESC
        """)
        
        permisos_por_pagina = cursor.fetchall()
        
        if permisos_por_pagina:
            print("\n📊 Distribución de permisos por página:")
            for pagina in permisos_por_pagina:
                print(f"   - {pagina['pagina']}: {pagina['cantidad']} permisos")
        
        return total_permisos > 0
        
    except Exception as e:
        print(f"❌ Error verificando permisos: {e}")
        return False

def probar_verificacion_permiso_especifico(conn):
    """Probar verificación de un permiso específico"""
    try:
        cursor = conn.cursor()
        
        # Simular verificación de permiso específico
        test_pagina = "LISTA_INFORMACIONBASICA"
        test_seccion = "Administración de usuario"
        test_boton = "Administración de autoridad"
        
        cursor.execute("""
            SELECT COUNT(*) as tiene_permiso
            FROM usuario_roles ur
            JOIN roles r ON ur.rol_id = r.id
            JOIN rol_permisos_botones rpb ON r.id = rpb.rol_id
            JOIN usuarios_sistema u ON ur.usuario_id = u.id
            WHERE u.username = 'admin'
            AND rpb.pagina = %s
            AND rpb.seccion = %s
            AND rpb.boton = %s
        """, (test_pagina, test_seccion, test_boton))
        
        resultado = cursor.fetchone()
        tiene_permiso = resultado['tiene_permiso'] > 0
        
        print(f"\n🧪 Prueba de permiso específico:")
        print(f"   Página: {test_pagina}")
        print(f"   Sección: {test_seccion}")
        print(f"   Botón: {test_boton}")
        print(f"   Resultado: {'✅ TIENE PERMISO' if tiene_permiso else '❌ NO TIENE PERMISO'}")
        
        return tiene_permiso
        
    except Exception as e:
        print(f"❌ Error probando permiso específico: {e}")
        return False

def main():
    """Función principal"""
    print("🔍 Probando sistema completo de permisos después de las correcciones...\n")
    
    # Conectar a la base de datos
    conn = conectar_hosting()
    if not conn:
        return
    
    try:
        # Verificar usuario admin
        if not verificar_usuario_admin(conn):
            print("❌ Falló la verificación del usuario admin")
            return
        
        # Verificar permisos
        if not verificar_permisos_admin(conn):
            print("❌ Falló la verificación de permisos")
            return
        
        # Probar permiso específico
        if not probar_verificacion_permiso_especifico(conn):
            print("❌ Falló la prueba de permiso específico")
            return
        
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("✅ El sistema de permisos está funcionando correctamente")
        print("✅ El usuario admin tiene acceso a los botones")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()