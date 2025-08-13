import sys
sys.path.append(".")
from app.config_mysql import get_db_connection
import MySQLdb.cursors

# Hacer la inserción directamente sin execute_query
codigo_material = "0RH5602C622,202508130004"

try:
    with get_db_connection() as conn:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        query = """
        INSERT INTO control_material_salida (
            codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida,
            proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        from datetime import datetime
        fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        params = (
            "TEST_DIRECT,202508130006",
            "TEST_DIRECT", 
            "",
            "",
            "",
            "SMD",
            1,
            None,
            fecha_registro,
            "56KJ 1/10W SMD - INSERCIÓN DIRECTA"
        )
        
        print(f"Ejecutando inserción directa...")
        print(f"Parámetros: {params}")
        
        cursor.execute(query, params)
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        
        print(f"Filas afectadas: {affected_rows}")
        
        # Verificar inmediatamente
        cursor2 = conn.cursor(MySQLdb.cursors.DictCursor)
        verify_query = """
        SELECT especificacion_material 
        FROM control_material_salida 
        WHERE codigo_material_recibido = %s
        ORDER BY fecha_registro DESC 
        LIMIT 1
        """
        cursor2.execute(verify_query, ("TEST_DIRECT,202508130006",))
        result = cursor2.fetchone()
        cursor2.close()
        
        if result:
            actual_spec = result["especificacion_material"]
            print(f"Especificación guardada: \"{actual_spec}\"")
        else:
            print("No se encontró el registro")
            
except Exception as e:
    print(f"Error: {e}")
