#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar si la tabla rol_permisos_botones existe en la base de datos del hosting
"""

import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('hosting_config.env')

def ejecutar_query_hosting(query, params=None):
    """Ejecutar query en la base de datos del hosting a través del proxy HTTP"""
    try:
        proxy_url = os.getenv('MYSQL_PROXY_URL')
        api_key = os.getenv('PROXY_API_KEY')
        
        if not proxy_url or not api_key:
            print("❌ Error: MYSQL_PROXY_URL o PROXY_API_KEY no configurados")
            return None
            
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        }
        
        data = {
            'query': query
        }
        
        if params:
            data['params'] = params
            
        response = requests.post(f"{proxy_url}/execute", json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Conexión exitosa a la base de datos del hosting")
                return result.get('data', [])
            else:
                print(f"❌ Error en query: {result.get('error')}")
                return None
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error ejecutando query: {e}")
        return None

def verificar_tabla_rol_permisos_botones():
    """Verificar si existe la tabla rol_permisos_botones"""
    
    try:
        # Verificar si la tabla existe
        query_existe = """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'rol_permisos_botones'
        """
        
        resultado = ejecutar_query_hosting(query_existe)
        if resultado is None:
            return
            
        existe = resultado[0][0] > 0
        
        if existe:
            print("✅ La tabla 'rol_permisos_botones' SÍ existe en la base de datos")
            
            # Obtener estructura de la tabla
            estructura = ejecutar_query_hosting("DESCRIBE rol_permisos_botones")
            if estructura:
                print("\n📋 Estructura de la tabla 'rol_permisos_botones':")
                for campo in estructura:
                    print(f"  - {campo[0]} ({campo[1]}) - {campo[3] if campo[3] else 'NOT NULL'}")
            
            # Contar registros
            count_result = ejecutar_query_hosting("SELECT COUNT(*) FROM rol_permisos_botones")
            if count_result:
                total_registros = count_result[0][0]
                print(f"\n📊 Total de registros: {total_registros}")
                
                if total_registros > 0:
                    # Mostrar algunos registros de ejemplo
                    registros = ejecutar_query_hosting("SELECT * FROM rol_permisos_botones LIMIT 5")
                    if registros:
                        print("\n📝 Primeros 5 registros:")
                        for registro in registros:
                            print(f"  {registro}")
                        
                    # Verificar roles únicos
                    roles_result = ejecutar_query_hosting("SELECT DISTINCT rol_id FROM rol_permisos_botones")
                    if roles_result:
                        roles = [r[0] for r in roles_result]
                        print(f"\n👥 Roles con permisos asignados: {roles}")
        else:
            print("❌ La tabla 'rol_permisos_botones' NO existe en la base de datos")
            
            # Listar todas las tablas que contienen 'permiso' en el nombre
            query_tablas = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name LIKE '%permiso%'
            """
            
            tablas_permisos = ejecutar_query_hosting(query_tablas)
            if tablas_permisos:
                print("\n📋 Tablas relacionadas con permisos encontradas:")
                for tabla in tablas_permisos:
                    print(f"  - {tabla[0]}")
            else:
                print("\n❌ No se encontraron tablas relacionadas con permisos")
        
    except Exception as e:
        print(f"❌ Error verificando la tabla: {e}")
    
    print("\n🔐 Verificación completada")

if __name__ == "__main__":
    print("🔍 Verificando existencia de tabla 'rol_permisos_botones' en hosting...\n")
    verificar_tabla_rol_permisos_botones()