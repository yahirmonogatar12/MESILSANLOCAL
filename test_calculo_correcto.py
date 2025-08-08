import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print('=== Probando consulta corregida con estructura real ===')
    
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
        
        # Buscar un código de material para testing
        print("=== Buscando códigos de material disponibles ===")
        cursor.execute("SELECT DISTINCT codigo_material FROM control_material_almacen LIMIT 5")
        materiales = cursor.fetchall()
        print("Materiales disponibles:", materiales)
        
        if materiales:
            codigo_test = materiales[0][0]
            print(f"\n=== Probando con código: {codigo_test} ===")
            
            # Datos de entrada (control_material_almacen)
            print("\n--- Entradas ---")
            cursor.execute("""
                SELECT numero_lote_material, cantidad_actual, fecha_recibo 
                FROM control_material_almacen 
                WHERE codigo_material = %s
            """, (codigo_test,))
            entradas = cursor.fetchall()
            total_entradas = 0
            for entrada in entradas:
                print(f"Lote: {entrada[0]}, Cantidad: {entrada[1]}, Fecha: {entrada[2]}")
                total_entradas += entrada[1] if entrada[1] else 0
            print(f"Total entradas: {total_entradas}")
            
            # Datos de salida (control_material_salida)
            print("\n--- Salidas ---")
            cursor.execute("""
                SELECT numero_lote, cantidad_salida, fecha_salida 
                FROM control_material_salida 
                WHERE codigo_material_recibido = %s
            """, (codigo_test,))
            salidas = cursor.fetchall()
            total_salidas = 0
            for salida in salidas:
                print(f"Lote: {salida[0]}, Cantidad: {salida[1]}, Fecha: {salida[2]}")
                total_salidas += float(salida[1]) if salida[1] else 0
            print(f"Total salidas: {total_salidas}")
            
            # Cálculo correcto
            cantidad_real = total_entradas - total_salidas
            print(f"\n=== RESULTADO CORRECTO ===")
            print(f"Entradas: {total_entradas}")
            print(f"Salidas: {total_salidas}")
            print(f"Cantidad real: {cantidad_real}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
