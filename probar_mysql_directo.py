#!/usr/bin/env python3
"""
Probar conexión directa a MySQL del hosting
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def probar_conexion_mysql():
    """Probar conexión directa a MySQL"""
    try:
        import pymysql
        
        # Configuración desde .env
        config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', '3306')),
            'user': os.getenv('MYSQL_USERNAME', ''),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', ''),
            'charset': 'utf8mb4',
            'autocommit': True
        }
        
        print("=== PROBANDO CONEXIÓN MYSQL ===")
        print(f"🔗 Host: {config['host']}")
        print(f"🔌 Puerto: {config['port']}")
        print(f"🗄️ Base de datos: {config['database']}")
        print(f"👤 Usuario: {config['user']}")
        
        # Conectar
        connection = pymysql.connect(**config)
        print("✅ Conexión MySQL exitosa")
        
        # Probar consulta
        cursor = connection.cursor()
        
        # Verificar tabla inventario_consolidado
        cursor.execute("SHOW TABLES LIKE 'inventario_consolidado'")
        tabla_existe = cursor.fetchone()
        
        if tabla_existe:
            print("✅ Tabla inventario_consolidado encontrada")
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM inventario_consolidado")
            total_registros = cursor.fetchone()[0]
            print(f"📊 Total registros en inventario_consolidado: {total_registros}")
            
            # Mostrar primeros 3 registros
            cursor.execute("""
                SELECT 
                    numero_parte, 
                    total_entradas, 
                    total_salidas, 
                    cantidad_actual 
                FROM inventario_consolidado 
                ORDER BY fecha_ultima_entrada DESC 
                LIMIT 3
            """)
            
            registros = cursor.fetchall()
            print("\n📋 PRIMEROS 3 REGISTROS:")
            for i, reg in enumerate(registros, 1):
                numero_parte, entradas, salidas, cantidad = reg
                print(f"  {i}. {numero_parte}: E:{entradas} - S:{salidas} = {cantidad}")
            
        else:
            print("❌ Tabla inventario_consolidado NO encontrada")
            
            # Mostrar todas las tablas disponibles
            cursor.execute("SHOW TABLES")
            tablas = cursor.fetchall()
            print(f"\n📋 TABLAS DISPONIBLES ({len(tablas)}):")
            for tabla in tablas:
                print(f"  - {tabla[0]}")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    probar_conexion_mysql()
