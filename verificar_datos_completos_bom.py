#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar si se están cargando todos los datos de BOM para un modelo específico
"""

import pymysql
import requests
from app.config_mysql import get_mysql_connection_string

def get_db_connection():
    """Crear conexión a MySQL"""
    try:
        config = get_mysql_connection_string()
        if not config:
            print("Error: No se pudo obtener configuración de MySQL")
            return None
            
        connection = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['passwd'],
            database=config['db'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def verificar_datos_directos_bd(modelo):
    """Verificar datos directamente en la base de datos"""
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        
        print(f"=== Verificación directa en BD para modelo {modelo} ===")
        
        # Contar registros totales para el modelo
        cursor.execute("SELECT COUNT(*) as total FROM bom WHERE modelo = %s", (modelo,))
        total = cursor.fetchone()['total']
        print(f"📊 Total de registros en BD: {total}")
        
        # Obtener primeros 5 registros para verificar estructura
        cursor.execute("SELECT * FROM bom WHERE modelo = %s ORDER BY numero_parte LIMIT 5", (modelo,))
        primeros = cursor.fetchall()
        
        print(f"\n🔍 Primeros 5 registros:")
        for i, registro in enumerate(primeros, 1):
            print(f"  {i}. Número parte: {registro.get('numero_parte', 'N/A')}")
            print(f"     Descripción: {registro.get('descripcion', 'N/A')}")
            print(f"     Vendor: {registro.get('vender', 'N/A')}")
            print(f"     Cantidad: {registro.get('cantidad_total', 'N/A')}")
            print()
        
        # Verificar si hay campos NULL o vacíos
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(numero_parte) as con_numero_parte,
                COUNT(descripcion) as con_descripcion,
                COUNT(vender) as con_vendor
            FROM bom WHERE modelo = %s
        """, (modelo,))
        
        stats = cursor.fetchone()
        print(f"📈 Estadísticas de campos:")
        print(f"  - Total registros: {stats['total']}")
        print(f"  - Con número de parte: {stats['con_numero_parte']}")
        print(f"  - Con descripción: {stats['con_descripcion']}")
        print(f"  - Con vendor: {stats['con_vendor']}")
        
        return total
        
    except Exception as e:
        print(f"Error verificando datos directos: {e}")
        return 0
    finally:
        conn.close()

def hacer_login():
    """Hacer login con credenciales correctas"""
    try:
        session = requests.Session()
        
        login_data = {
            'username': 'Problema',
            'password': 'Problema'
        }
        
        response = session.post(
            'http://127.0.0.1:5000/login',
            data=login_data,
            allow_redirects=False
        )
        
        if response.status_code == 302:
            print("✓ Login exitoso")
            return session
        else:
            print(f"✗ Login falló: código {response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ Error en login: {e}")
        return None

def probar_endpoint_listar_bom(session, modelo):
    """Probar el endpoint /listar_bom"""
    try:
        data = {'modelo': modelo}
        
        response = session.post(
            'http://127.0.0.1:5000/listar_bom',
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"\n=== Endpoint /listar_bom para modelo {modelo} ===")
        print(f"Código de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"✓ Datos recibidos: {len(data)} registros")
                    
                    if len(data) > 0:
                        print(f"\n🔍 Primeros 3 registros del endpoint:")
                        for i, registro in enumerate(data[:3], 1):
                            print(f"  {i}. Número parte: {registro.get('numero_parte', 'N/A')}")
                            print(f"     Descripción: {registro.get('descripcion', 'N/A')}")
                            print(f"     Vendor: {registro.get('vender', 'N/A')}")
                            print(f"     Cantidad: {registro.get('cantidad_total', 'N/A')}")
                            print()
                    
                    return len(data)
                else:
                    print(f"❌ Formato de respuesta incorrecto: {type(data)}")
                    return 0
                    
            except Exception as e:
                print(f"❌ Error parseando JSON: {e}")
                print(f"Respuesta raw: {response.text[:200]}...")
                return 0
        else:
            print(f"❌ Error en endpoint: {response.text}")
            return 0
            
    except Exception as e:
        print(f"✗ Error probando endpoint: {e}")
        return 0

def verificar_limitaciones_execute_query():
    """Verificar si hay limitaciones en execute_query"""
    print(f"\n=== Verificando función execute_query ===")
    
    try:
        from app.config_mysql import execute_query
        
        # Probar consulta directa
        query = "SELECT COUNT(*) as total FROM bom WHERE modelo = %s"
        result = execute_query(query, ('EBR30299301',), fetch='one')
        
        if result:
            print(f"✓ execute_query funciona correctamente")
            print(f"📊 Total desde execute_query: {result['total']}")
            return True
        else:
            print(f"❌ execute_query devolvió None")
            return False
            
    except Exception as e:
        print(f"❌ Error probando execute_query: {e}")
        return False

def main():
    modelo_test = 'EBR30299301'
    
    print(f"Verificando carga completa de datos BOM para modelo {modelo_test}...\n")
    
    # 1. Verificar datos directos en BD
    total_bd = verificar_datos_directos_bd(modelo_test)
    
    # 2. Verificar función execute_query
    execute_ok = verificar_limitaciones_execute_query()
    
    # 3. Hacer login
    session = hacer_login()
    if not session:
        print("❌ No se puede continuar sin login")
        return
    
    # 4. Probar endpoint
    total_endpoint = probar_endpoint_listar_bom(session, modelo_test)
    
    # Comparar resultados
    print(f"\n=== COMPARACIÓN DE RESULTADOS ===")
    print(f"📊 Registros en BD: {total_bd}")
    print(f"📊 Registros del endpoint: {total_endpoint}")
    
    if total_bd == total_endpoint and total_bd > 0:
        print(f"✅ ¡Todos los datos se cargan correctamente!")
        print(f"✅ No hay pérdida de datos entre BD y endpoint")
    elif total_bd > total_endpoint:
        print(f"⚠️ Se están perdiendo datos:")
        print(f"  - Diferencia: {total_bd - total_endpoint} registros")
        print(f"  - Posible limitación en execute_query o endpoint")
    elif total_endpoint > total_bd:
        print(f"❌ El endpoint devuelve más datos que la BD (error)")
    else:
        print(f"❌ No se encontraron datos")

if __name__ == '__main__':
    main()