import sys
sys.path.append(".")
from app.config_mysql import get_mysql_connection

print("=== ELIMINANDO Y RECREANDO TRIGGER CON PYMYSQL DIRECTO ===")

try:
    connection = get_mysql_connection()
    cursor = connection.cursor()
    
    # 1. Eliminar trigger existente
    print("1. Eliminando trigger existente...")
    cursor.execute("DROP TRIGGER IF EXISTS tr_fix_especificacion_salida")
    connection.commit()
    print("    Trigger eliminado")
    
    # 2. Verificar que se eliminó
    cursor.execute("SHOW TRIGGERS")
    triggers = cursor.fetchall()
    trigger_exists = False
    for trigger in triggers:
        if "tr_fix_especificacion_salida" in trigger[0]:
            trigger_exists = True
            print(f"    Trigger aún existe: {trigger[0]}")
            break
    
    if not trigger_exists:
        print("    Trigger eliminado exitosamente")
    
    # 3. No crear trigger nuevo - dejar que funcione sin trigger
    print("\\n2. Dejando la tabla SIN trigger problemático")
    print("    Ahora los valores insertados se guardarán tal como se envían")
    
    cursor.close()
    connection.close()
    
    print("\\n=== ELIMINACIÓN COMPLETADA ===")
    
except Exception as e:
    print(f"Error: {e}")
