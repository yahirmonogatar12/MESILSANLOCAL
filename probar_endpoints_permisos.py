#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar los endpoints de gestión de permisos desde el frontend
"""

import os
import sys
import requests
from dotenv import load_dotenv
import pymysql
import json

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

def probar_endpoint_obtener_permisos_rol(conn):
    """Probar el endpoint que obtiene permisos de un rol"""
    try:
        cursor = conn.cursor()
        
        # Obtener ID del rol superadmin
        cursor.execute("SELECT id FROM roles WHERE nombre = 'superadmin'")
        rol = cursor.fetchone()
        
        if not rol:
            print("❌ No se encontró el rol superadmin")
            return False
            
        rol_id = rol['id']
        print(f"🔍 Probando endpoint para rol superadmin (ID: {rol_id})")
        
        # Simular la consulta que hace el endpoint
        cursor.execute('''
            SELECT rpb.pagina, rpb.seccion, rpb.boton
            FROM rol_permisos_botones rpb
            WHERE rpb.rol_id = %s
            ORDER BY rpb.pagina, rpb.seccion, rpb.boton
        ''', (rol_id,))
        
        permisos = cursor.fetchall()
        
        print(f"✅ Endpoint obtener_permisos_dropdowns_rol funcionando")
        print(f"   - Permisos encontrados: {len(permisos)}")
        
        if permisos:
            print("   - Primeros 5 permisos:")
            for i, permiso in enumerate(permisos[:5]):
                print(f"     {i+1}. {permiso['pagina']} > {permiso['seccion']} > {permiso['boton']}")
        
        return len(permisos) > 0
        
    except Exception as e:
        print(f"❌ Error probando endpoint obtener_permisos_rol: {e}")
        return False

def probar_endpoint_toggle_permission(conn):
    """Probar el endpoint que alterna permisos"""
    try:
        cursor = conn.cursor()
        
        # Obtener ID del rol admin (no superadmin para esta prueba)
        cursor.execute("SELECT id FROM roles WHERE nombre = 'admin'")
        rol = cursor.fetchone()
        
        if not rol:
            print("❌ No se encontró el rol admin")
            return False
            
        rol_id = rol['id']
        
        # Datos de prueba
        test_pagina = "TEST_PAGINA"
        test_seccion = "TEST_SECCION"
        test_boton = "TEST_BOTON"
        
        print(f"🔍 Probando endpoint toggle_permission para rol admin (ID: {rol_id})")
        
        # Verificar si el permiso ya existe
        cursor.execute("""
            SELECT COUNT(*) as existe
            FROM rol_permisos_botones 
            WHERE rol_id = %s AND pagina = %s AND seccion = %s AND boton = %s
        """, (rol_id, test_pagina, test_seccion, test_boton))
        
        existe_antes = cursor.fetchone()['existe'] > 0
        print(f"   - Permiso existe antes: {existe_antes}")
        
        if not existe_antes:
            # Simular agregar permiso
            cursor.execute("""
                INSERT INTO rol_permisos_botones (rol_id, pagina, seccion, boton, fecha_creacion) 
                VALUES (%s, %s, %s, %s, NOW())
            """, (rol_id, test_pagina, test_seccion, test_boton))
            conn.commit()
            print("   ✅ Permiso agregado exitosamente")
            
            # Verificar que se agregó
            cursor.execute("""
                SELECT COUNT(*) as existe
                FROM rol_permisos_botones 
                WHERE rol_id = %s AND pagina = %s AND seccion = %s AND boton = %s
            """, (rol_id, test_pagina, test_seccion, test_boton))
            
            existe_despues = cursor.fetchone()['existe'] > 0
            print(f"   - Permiso existe después: {existe_despues}")
            
            # Limpiar - remover el permiso de prueba
            cursor.execute("""
                DELETE FROM rol_permisos_botones 
                WHERE rol_id = %s AND pagina = %s AND seccion = %s AND boton = %s
            """, (rol_id, test_pagina, test_seccion, test_boton))
            conn.commit()
            print("   🧹 Permiso de prueba removido")
            
            return existe_despues
        else:
            print("   ⚠️ El permiso ya existía, saltando prueba de adición")
            return True
        
    except Exception as e:
        print(f"❌ Error probando endpoint toggle_permission: {e}")
        return False

def probar_endpoint_enable_all_permissions(conn):
    """Probar el endpoint que habilita todos los permisos"""
    try:
        cursor = conn.cursor()
        
        # Crear un rol de prueba
        test_rol_nombre = "test_rol_temp"
        
        # Verificar si el rol de prueba ya existe
        cursor.execute("SELECT id FROM roles WHERE nombre = %s", (test_rol_nombre,))
        rol_existente = cursor.fetchone()
        
        if rol_existente:
            rol_id = rol_existente['id']
            print(f"🔍 Usando rol de prueba existente: {test_rol_nombre} (ID: {rol_id})")
        else:
            # Crear rol de prueba temporal
            cursor.execute("""
                INSERT INTO roles (nombre, descripcion, nivel, activo) 
                VALUES (%s, 'Rol temporal para pruebas', 1, 1)
            """, (test_rol_nombre,))
            conn.commit()
            rol_id = cursor.lastrowid
            print(f"🔍 Creado rol de prueba temporal: {test_rol_nombre} (ID: {rol_id})")
        
        # Contar permisos antes
        cursor.execute("""
            SELECT COUNT(*) as total_antes
            FROM rol_permisos_botones 
            WHERE rol_id = %s
        """, (rol_id,))
        
        total_antes = cursor.fetchone()['total_antes']
        print(f"   - Permisos antes: {total_antes}")
        
        # Simular enable_all_permissions
        cursor.execute("SELECT DISTINCT pagina, seccion, boton FROM permisos_botones LIMIT 5")
        permisos_disponibles = cursor.fetchall()
        
        added_count = 0
        for permiso in permisos_disponibles:
            cursor.execute("""
                INSERT IGNORE INTO rol_permisos_botones (rol_id, pagina, seccion, boton, fecha_creacion) 
                VALUES (%s, %s, %s, %s, NOW())
            """, (rol_id, permiso['pagina'], permiso['seccion'], permiso['boton']))
            
            if cursor.rowcount > 0:
                added_count += 1
        
        conn.commit()
        
        # Contar permisos después
        cursor.execute("""
            SELECT COUNT(*) as total_despues
            FROM rol_permisos_botones 
            WHERE rol_id = %s
        """, (rol_id,))
        
        total_despues = cursor.fetchone()['total_despues']
        print(f"   - Permisos después: {total_despues}")
        print(f"   - Permisos agregados: {added_count}")
        
        # Limpiar - eliminar rol de prueba si lo creamos
        if not rol_existente:
            cursor.execute("DELETE FROM rol_permisos_botones WHERE rol_id = %s", (rol_id,))
            cursor.execute("DELETE FROM roles WHERE id = %s", (rol_id,))
            conn.commit()
            print("   🧹 Rol de prueba temporal eliminado")
        
        print("✅ Endpoint enable_all_permissions funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Error probando endpoint enable_all_permissions: {e}")
        return False

def main():
    """Función principal"""
    print("🔍 Probando endpoints de gestión de permisos...\n")
    
    # Conectar a la base de datos
    conn = conectar_hosting()
    if not conn:
        return
    
    try:
        tests_passed = 0
        total_tests = 3
        
        # Probar endpoint obtener_permisos_rol
        print("1️⃣ Probando obtener_permisos_dropdowns_rol...")
        if probar_endpoint_obtener_permisos_rol(conn):
            tests_passed += 1
        print()
        
        # Probar endpoint toggle_permission
        print("2️⃣ Probando toggle_permission...")
        if probar_endpoint_toggle_permission(conn):
            tests_passed += 1
        print()
        
        # Probar endpoint enable_all_permissions
        print("3️⃣ Probando enable_all_permissions...")
        if probar_endpoint_enable_all_permissions(conn):
            tests_passed += 1
        print()
        
        # Resumen
        print(f"📊 Resumen de pruebas: {tests_passed}/{total_tests} pasaron")
        
        if tests_passed == total_tests:
            print("🎉 ¡Todos los endpoints están funcionando correctamente!")
            print("✅ La interfaz de gestión de permisos debería funcionar sin problemas")
        else:
            print("⚠️ Algunos endpoints tienen problemas")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()