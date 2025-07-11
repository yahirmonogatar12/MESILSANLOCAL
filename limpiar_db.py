from app.db import get_db_connection

def limpiar_base_datos():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Limpiar tabla de materiales
    cursor.execute('DELETE FROM control_material_almacen')
    
    conn.commit()
    conn.close()
    print("Base de datos limpiada - tabla materiales vacía")

if __name__ == "__main__":
    limpiar_base_datos()
