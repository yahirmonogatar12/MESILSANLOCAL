import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print('=== Revisando estructura de tablas ===')
    
    config = {
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USERNAME'),
        'passwd': os.getenv('MYSQL_PASSWORD'),
        'db': os.getenv('MYSQL_DATABASE'),
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # Primero vamos a ver la estructura de las tablas
        print("=== Estructura de control_material_almacen ===")
        cursor.execute("DESCRIBE control_material_almacen")
        for row in cursor.fetchall():
            print(f"Columna: {row[0]}, Tipo: {row[1]}")
        
        print("\n=== Estructura de control_material_salida ===")
        cursor.execute("DESCRIBE control_material_salida")
        for row in cursor.fetchall():
            print(f"Columna: {row[0]}, Tipo: {row[1]}")
        
        print("\n=== Datos de ejemplo en control_material_almacen ===")
        cursor.execute("SELECT * FROM control_material_almacen WHERE codigo_material = '3220003110' LIMIT 3")
        for row in cursor.fetchall():
            print(row)
        
        print("\n=== Datos de ejemplo en control_material_salida ===")
        cursor.execute("SELECT * FROM control_material_salida WHERE codigo_material = '3220003110' LIMIT 3")
        for row in cursor.fetchall():
            print(row)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
