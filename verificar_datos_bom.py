#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar datos en la tabla BOM y el funcionamiento del endpoint de modelos
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

def verificar_tabla_bom():
    """Verificar datos en la tabla BOM"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        print("=== Verificación de tabla BOM ===")
        
        # Verificar si la tabla existe
        cursor.execute("SHOW TABLES LIKE 'bom'")
        tabla_existe = cursor.fetchone()
        
        if not tabla_existe:
            print("❌ La tabla 'bom' no existe")
            return False
        
        print("✓ La tabla 'bom' existe")
        
        # Contar registros totales
        cursor.execute("SELECT COUNT(*) as total FROM bom")
        total = cursor.fetchone()['total']
        print(f"📊 Total de registros en BOM: {total}")
        
        if total == 0:
            print("⚠️ La tabla BOM está vacía - no hay modelos para mostrar")
            return False
        
        # Obtener modelos únicos
        cursor.execute("SELECT DISTINCT modelo FROM bom ORDER BY modelo LIMIT 10")
        modelos = cursor.fetchall()
        
        print(f"🏷️ Modelos únicos encontrados ({len(modelos)}):")
        for modelo in modelos:
            print(f"  - {modelo['modelo']}")
        
        # Verificar estructura de la tabla
        cursor.execute("DESCRIBE bom")
        columnas = cursor.fetchall()
        
        print(f"\n🏗️ Estructura de la tabla BOM:")
        for col in columnas:
            print(f"  - {col['Field']}: {col['Type']} ({col['Null']})")
        
        return True
        
    except Exception as e:
        print(f"Error verificando tabla BOM: {e}")
        return False
    finally:
        conn.close()

def hacer_login():
    """Hacer login para obtener sesión"""
    try:
        session = requests.Session()
        
        # Datos de login
        login_data = {
            'username': 'Problema',
            'password': 'Problema123'
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

def probar_endpoint_modelos():
    """Probar el endpoint de listar modelos BOM"""
    print("\n=== Prueba del endpoint /listar_modelos_bom ===")
    
    # Hacer login
    session = hacer_login()
    if not session:
        return False
    
    try:
        response = session.get('http://127.0.0.1:5000/listar_modelos_bom')
        
        print(f"Código de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✓ Respuesta JSON válida")
                print(f"📊 Modelos devueltos: {len(data)}")
                
                if len(data) > 0:
                    print(f"🏷️ Primeros modelos:")
                    for i, modelo in enumerate(data[:5]):
                        print(f"  {i+1}. {modelo}")
                    return True
                else:
                    print("⚠️ El endpoint devuelve una lista vacía")
                    return False
                    
            except Exception as e:
                print(f"❌ Error parseando JSON: {e}")
                print(f"Respuesta raw: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Error en endpoint: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error probando endpoint: {e}")
        return False

def insertar_datos_prueba():
    """Insertar algunos datos de prueba si la tabla está vacía"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        print("\n=== Insertando datos de prueba ===")
        
        datos_prueba = [
            ('EBR30299301', 'R001', 'Resistor 10K', 2, 'TOP', 'A1', 'Resistor', 'Proveedor1'),
            ('EBR30299301', 'C001', 'Capacitor 100nF', 1, 'TOP', 'B1', 'Capacitor', 'Proveedor2'),
            ('EBR30299302', 'R002', 'Resistor 1K', 3, 'BOTTOM', 'C1', 'Resistor', 'Proveedor1'),
            ('EBR30299302', 'IC001', 'Microcontrolador', 1, 'TOP', 'D1', 'IC', 'Proveedor3')
        ]
        
        query = """
            INSERT INTO bom (modelo, numero_parte, descripcion, cantidad, side, ubicacion, categoria, proveedor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                descripcion = VALUES(descripcion),
                cantidad = VALUES(cantidad)
        """
        
        insertados = 0
        for dato in datos_prueba:
            try:
                cursor.execute(query, dato)
                insertados += 1
            except Exception as e:
                print(f"Error insertando {dato[0]}-{dato[1]}: {e}")
        
        conn.commit()
        print(f"✓ Insertados {insertados} registros de prueba")
        return True
        
    except Exception as e:
        print(f"Error insertando datos de prueba: {e}")
        return False
    finally:
        conn.close()

def main():
    print("Verificando datos BOM y endpoint de modelos...\n")
    
    # 1. Verificar datos en la tabla BOM
    tiene_datos = verificar_tabla_bom()
    
    # 2. Si no hay datos, insertar algunos de prueba
    if not tiene_datos:
        print("\n🔧 La tabla BOM está vacía, insertando datos de prueba...")
        if insertar_datos_prueba():
            print("✓ Datos de prueba insertados, verificando nuevamente...")
            tiene_datos = verificar_tabla_bom()
    
    # 3. Probar el endpoint
    endpoint_ok = probar_endpoint_modelos()
    
    # Resumen
    print("\n=== RESUMEN ===")
    if tiene_datos and endpoint_ok:
        print("🎉 ¡Todo funciona correctamente!")
        print("✅ Hay datos en la tabla BOM")
        print("✅ El endpoint de modelos funciona")
    else:
        print("❌ Hay problemas:")
        if not tiene_datos:
            print("  - No hay datos en la tabla BOM")
        if not endpoint_ok:
            print("  - El endpoint de modelos no funciona correctamente")

if __name__ == '__main__':
    main()