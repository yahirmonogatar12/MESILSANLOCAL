import os
from app.config_mysql import MYSQL_CONFIG, get_mysql_connection_string
import pymysql

# Mostrar configuración
print('=== Configuración MySQL ===')
config = get_mysql_connection_string()
if config:
    print(f'Host: {config["host"]}')
    print(f'Puerto: {config["port"]}')
    print(f'Base de datos: {config["db"]}')
    print(f'Usuario: {config["user"]}')
    print('=== Probando conexión ===')
    
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # Verificar cantidad total para algunos registros
        print('=== Verificando cantidad total ===')
        cursor.execute('''
            SELECT 
                numero_parte,
                SUM(cantidad_actual) as cantidad_total,
                COUNT(*) as total_lotes
            FROM control_material_almacen 
            WHERE cantidad_actual > 0
            GROUP BY numero_parte 
            LIMIT 5
        ''')
        
        results = cursor.fetchall()
        for row in results:
            print(f'Parte: {row[0]}, Cantidad Total: {row[1]}, Lotes: {row[2]}')
            
        cursor.close()
        conn.close()
        print('✅ Conexión MySQL exitosa')
        
    except Exception as e:
        print(f'❌ Error de conexión MySQL: {e}')
else:
    print('❌ No se pudo obtener configuración MySQL')
