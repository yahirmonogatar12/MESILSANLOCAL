import sys
sys.path.append(".")
from app.db_mysql import execute_query

print("=== CORRIGIENDO TRIGGER PROBLEMÁTICO ===")

# 1. Eliminar el trigger actual
drop_query = "DROP TRIGGER IF EXISTS tr_fix_especificacion_salida"
result_drop = execute_query(drop_query)
print(f"Trigger anterior eliminado: {result_drop}")

# 2. Crear el trigger corregido que use especificacion en lugar de propiedad_material
create_query = """
CREATE TRIGGER tr_fix_especificacion_salida
BEFORE INSERT ON control_material_salida
FOR EACH ROW
BEGIN
    DECLARE real_especificacion VARCHAR(512);
    
    -- Obtener la ESPECIFICACIÓN COMPLETA del material (no solo la propiedad)
    SELECT especificacion INTO real_especificacion
    FROM control_material_almacen 
    WHERE codigo_material_recibido = NEW.codigo_material_recibido
    LIMIT 1;
    
    -- Solo actualizar si la especificación está vacía y encontramos una válida
    IF (NEW.especificacion_material IS NULL OR NEW.especificacion_material = \"\") 
       AND real_especificacion IS NOT NULL 
       AND real_especificacion != \"\" THEN
        SET NEW.especificacion_material = real_especificacion;
    END IF;
END
"""

try:
    result_create = execute_query(create_query)
    print(f"Trigger corregido creado: {result_create}")
    print()
    print(" TRIGGER CORREGIDO:")
    print("- Ahora usa ESPECIFICACIÓN COMPLETA en lugar de solo propiedad")
    print("- Solo actualiza si especificacion_material está vacía")
    print("- Preserva el valor enviado por la aplicación")
except Exception as e:
    print(f"Error creando trigger: {e}")

