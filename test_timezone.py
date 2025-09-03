#!/usr/bin/env python3
"""
Script para probar la configuración de zona horaria
"""

from datetime import datetime, timedelta
from app.config_mysql import execute_query

def test_timezone():
    """Probar configuración de zona horaria"""
    
    print("=== PRUEBA DE ZONA HORARIA ===")
    
    # 1. Hora de Python (sistema)
    print(f"\n1. PYTHON:")
    print(f"   Sistema UTC:     {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Sistema Local:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 2. Hora de México calculada
    print(f"\n2. MÉXICO (GMT-6):")
    utc_now = datetime.utcnow()
    mexico_time = utc_now - timedelta(hours=6)
    print(f"   México:          {mexico_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 3. Hora de MySQL
    print(f"\n3. MYSQL:")
    try:
        result = execute_query("SELECT NOW() as mysql_now", fetch='one')
        if result:
            print(f"   MySQL NOW():     {result['mysql_now']}")
        
        # Zona horaria de MySQL
        result = execute_query("SELECT @@system_time_zone as system_tz, @@time_zone as session_tz", fetch='one')
        if result:
            print(f"   Sistema TZ:      {result['system_tz']}")
            print(f"   Sesión TZ:       {result['session_tz']}")
            
    except Exception as e:
        print(f"   Error MySQL:     {e}")
    
    # 4. Probar una inserción de prueba
    print(f"\n4. PRUEBA DE INSERCIÓN:")
    try:
        # Crear tabla temporal
        execute_query("""
            CREATE TEMPORARY TABLE test_timezone (
                id INT AUTO_INCREMENT PRIMARY KEY,
                python_time VARCHAR(50),
                mexico_time VARCHAR(50),
                mysql_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insertar datos
        python_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        mexico_formatted = mexico_time.strftime('%Y-%m-%d %H:%M:%S')
        
        execute_query("""
            INSERT INTO test_timezone (python_time, mexico_time) 
            VALUES (%s, %s)
        """, (python_time, mexico_formatted))
        
        # Consultar resultado
        result = execute_query("""
            SELECT python_time, mexico_time, mysql_timestamp 
            FROM test_timezone 
            ORDER BY id DESC 
            LIMIT 1
        """, fetch='one')
        
        if result:
            print(f"   Python insertado: {result['python_time']}")
            print(f"   México insertado: {result['mexico_time']}")
            print(f"   MySQL timestamp:  {result['mysql_timestamp']}")
            
    except Exception as e:
        print(f"   Error prueba:     {e}")
    
    print(f"\n=== COMPARACIÓN ===")
    print(f"Diferencia esperada entre UTC y México: -6 horas")
    print(f"Si MySQL muestra 18:00 y debería ser 12:00, entonces MySQL está en UTC")
    print(f"Solución: Usar nuestra función obtener_fecha_hora_mexico() siempre")

if __name__ == "__main__":
    test_timezone()
