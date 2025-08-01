#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar la estructura real de la tabla usuarios_sistema
"""

import pymysql

def verificar_estructura():
    """Verificar estructura de tabla usuarios_sistema"""
    try:
        # Configuración de MySQL del hosting
        config = {
            'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
            'port': 11550,
            'user': 'db_rrpq0erbdujn',
            'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
            'database': 'db_rrpq0erbdujn',
            'charset': 'utf8mb4'
        }
        
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        print("📋 ESTRUCTURA DE TABLA usuarios_sistema:")
        print("-" * 50)
        
        # Describir estructura
        cursor.execute("DESCRIBE usuarios_sistema")
        columnas = cursor.fetchall()
        
        for col in columnas:
            print(f"   {col[0]} - {col[1]} - {col[2]} - {col[3]} - {col[4]} - {col[5]}")
        
        print("\n📊 DATOS DE USUARIOS:")
        print("-" * 50)
        
        # Obtener todos los usuarios
        cursor.execute("SELECT * FROM usuarios_sistema LIMIT 5")
        usuarios = cursor.fetchall()
        
        # Obtener nombres de columnas
        cursor.execute("SHOW COLUMNS FROM usuarios_sistema")
        nombres_columnas = [col[0] for col in cursor.fetchall()]
        
        print(f"Columnas: {', '.join(nombres_columnas)}")
        print()
        
        for usuario in usuarios:
            print(f"Usuario: {usuario}")
        
        print("\n🔍 VERIFICAR USUARIO YAHIR:")
        print("-" * 50)
        
        # Buscar usuario Yahir específicamente
        cursor.execute("SELECT * FROM usuarios_sistema WHERE username = %s", ('Yahir',))
        yahir = cursor.fetchone()
        
        if yahir:
            print(f"✅ Usuario Yahir encontrado: {yahir}")
            
            # Verificar su rol
            cursor.execute("""
                SELECT ur.usuario_id, ur.rol_id, r.nombre_rol 
                FROM usuario_roles ur 
                JOIN roles r ON ur.rol_id = r.id 
                WHERE ur.usuario_id = %s
            """, (yahir[0],))
            
            roles = cursor.fetchall()
            print(f"   Roles: {roles}")
        else:
            print("❌ Usuario Yahir no encontrado")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verificar_estructura()