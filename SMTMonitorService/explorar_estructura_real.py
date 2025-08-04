#!/usr/bin/env python3
"""
Script para explorar la estructura real de la tabla historial_cambio_material_smt
"""

import mysql.connector
from mysql.connector import Error

# CREDENCIALES CORRECTAS
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

def explorar_estructura_completa():
    """Explorar completamente la estructura de la tabla"""
    print("EXPLORANDO ESTRUCTURA COMPLETA DE LA TABLA")
    print("=" * 60)
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("✅ Conectado a la base de datos")
        
        # 1. Verificar que la tabla existe
        cursor.execute("SHOW TABLES LIKE 'historial_cambio_material_smt'")
        tabla_existe = cursor.fetchone()
        
        if not tabla_existe:
            print("❌ Tabla 'historial_cambio_material_smt' NO encontrada")
            
            # Mostrar todas las tablas
            cursor.execute("SHOW TABLES")
            tablas = cursor.fetchall()
            print(f"\nTablas disponibles:")
            for tabla in tablas:
                print(f"   - {tabla[0]}")
            return False
        
        print("✅ Tabla 'historial_cambio_material_smt' encontrada")
        
        # 2. Mostrar estructura detallada
        print(f"\n📋 ESTRUCTURA DETALLADA DE LA TABLA:")
        cursor.execute("DESCRIBE historial_cambio_material_smt")
        columnas = cursor.fetchall()
        
        print(f"Total de columnas: {len(columnas)}")
        print("-" * 80)
        print(f"{'#':<3} {'Nombre':<30} {'Tipo':<20} {'Null':<5} {'Key':<5} {'Default':<15}")
        print("-" * 80)
        
        for i, col in enumerate(columnas, 1):
            nombre = col[0]
            tipo = col[1]
            null = col[2]
            key = col[3] if col[3] else ''
            default = str(col[4]) if col[4] is not None else 'NULL'
            print(f"{i:<3} {nombre:<30} {tipo:<20} {null:<5} {key:<5} {default:<15}")
        
        # 3. Contar registros
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        count = cursor.fetchone()[0]
        print(f"\n📊 Total de registros: {count}")
        
        # 4. Si hay registros, mostrar algunos ejemplos
        if count > 0:
            print(f"\n📋 PRIMEROS 2 REGISTROS (datos reales):")
            
            # Obtener nombres de columnas
            nombres_columnas = [col[0] for col in columnas]
            
            cursor.execute("SELECT * FROM historial_cambio_material_smt LIMIT 2")
            registros = cursor.fetchall()
            
            for i, registro in enumerate(registros, 1):
                print(f"\n--- REGISTRO {i} ---")
                for j, valor in enumerate(registro):
                    if j < len(nombres_columnas):
                        nombre_col = nombres_columnas[j]
                        print(f"   {nombre_col}: {valor}")
        
        # 5. Buscar columnas que podrían ser de tiempo/fecha
        print(f"\n🕐 COLUMNAS DE FECHA/TIEMPO DETECTADAS:")
        columnas_tiempo = []
        
        for col in columnas:
            nombre = col[0].lower()
            tipo = col[1].lower()
            
            if any(palabra in nombre for palabra in ['fecha', 'time', 'date', 'created', 'updated', 'timestamp']):
                columnas_tiempo.append((col[0], col[1]))
                print(f"   ✅ {col[0]} ({col[1]}) - por nombre")
            elif any(tipo_tiempo in tipo for tipo_tiempo in ['datetime', 'timestamp', 'date', 'time']):
                if col[0] not in [c[0] for c in columnas_tiempo]:
                    columnas_tiempo.append((col[0], col[1]))
                    print(f"   ✅ {col[0]} ({col[1]}) - por tipo")
        
        if not columnas_tiempo:
            print("   ⚠️  No se encontraron columnas de fecha/tiempo obvias")
        
        # 6. Buscar columnas que podrían contener datos del CSV
        print(f"\n📄 POSIBLES COLUMNAS PARA DATOS CSV:")
        columnas_csv = []
        
        palabras_csv = ['barcode', 'serial', 'part', 'component', 'station', 'operator', 'result', 'linea', 'maquina']
        
        for col in columnas:
            nombre = col[0].lower()
            for palabra in palabras_csv:
                if palabra in nombre:
                    columnas_csv.append((col[0], col[1]))
                    print(f"   ✅ {col[0]} ({col[1]}) - contiene '{palabra}'")
                    break
        
        if not columnas_csv:
            print("   ⚠️  No se encontraron columnas obvias para datos CSV")
            print("   📋 Todas las columnas disponibles:")
            for col in columnas:
                print(f"      - {col[0]} ({col[1]})")
        
        return True, columnas, columnas_tiempo, columnas_csv
        
    except Error as e:
        print(f"❌ Error: {e}")
        return False, [], [], []
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def generar_mapeo_sugerido(columnas, columnas_tiempo, columnas_csv):
    """Generar un mapeo sugerido para el servicio"""
    print(f"\n🔧 MAPEO SUGERIDO PARA EL SERVICIO:")
    print("=" * 50)
    
    # Mapeo básico basado en patrones comunes
    mapeo_sugerido = {}
    nombres_columnas = [col[0] for col in columnas]
    
    # Buscar columnas por patrones
    patrones = {
        'id': ['id', 'ID'],
        'timestamp': [col[0] for col in columnas_tiempo] if columnas_tiempo else [],
        'barcode': ['barcode', 'codigo_barras', 'code'],
        'serial_number': ['serial', 'numero_serie', 'serial_number'],
        'part_number': ['part', 'parte', 'componente', 'part_number'],
        'linea': ['linea', 'line', 'linha'],
        'maquina': ['maquina', 'machine', 'estacion', 'station'],
        'operator': ['operator', 'operador', 'usuario'],
        'result': ['result', 'resultado', 'status', 'estado']
    }
    
    for campo_necesario, posibles_nombres in patrones.items():
        for nombre_posible in posibles_nombres:
            for col_real in nombres_columnas:
                if nombre_posible.lower() in col_real.lower():
                    mapeo_sugerido[campo_necesario] = col_real
                    print(f"   {campo_necesario:15} → {col_real}")
                    break
            if campo_necesario in mapeo_sugerido:
                break
        
        if campo_necesario not in mapeo_sugerido:
            print(f"   {campo_necesario:15} → ❌ NO ENCONTRADO")
    
    return mapeo_sugerido

def crear_verificador_compatible(columnas, mapeo):
    """Crear un verificador compatible con la estructura real"""
    
    # Determinar columna de tiempo para queries
    columna_tiempo = None
    for campo, columna in mapeo.items():
        if 'time' in campo or 'fecha' in campo:
            columna_tiempo = columna
            break
    
    if not columna_tiempo and columnas:
        # Buscar cualquier columna de tipo datetime/timestamp
        for col in columnas:
            if any(tipo in col[1].lower() for tipo in ['datetime', 'timestamp', 'date']):
                columna_tiempo = col[0]
                break
    
    verificador_codigo = f'''#!/usr/bin/env python3
"""
Verificador compatible con la estructura real de historial_cambio_material_smt
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime

DB_CONFIG = {{
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}}

def verificar_datos():
    print("VERIFICANDO DATOS EN TABLA REAL")
    print("=" * 50)
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Total de registros
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        total = cursor.fetchone()[0]
        print(f"📊 Total de registros: {{total}}")
        
        # Si hay columna de tiempo, mostrar registros por fecha
        {f"""
        # Registros de hoy (usando {columna_tiempo})
        cursor.execute(f"SELECT COUNT(*) FROM historial_cambio_material_smt WHERE DATE({columna_tiempo}) = CURDATE()")
        hoy = cursor.fetchone()[0]
        print(f"📅 Registros de hoy: {{hoy}}")
        
        # Registros de la última hora
        cursor.execute(f"SELECT COUNT(*) FROM historial_cambio_material_smt WHERE {columna_tiempo} >= DATE_SUB(NOW(), INTERVAL 1 HOUR)")
        ultima_hora = cursor.fetchone()[0]
        print(f"🕐 Registros última hora: {{ultima_hora}}")
        """ if columna_tiempo else "# No hay columna de tiempo identificada"}
        
        # Últimos 5 registros
        print(f"\\n📋 ÚLTIMOS 5 REGISTROS:")
        {f'cursor.execute("SELECT * FROM historial_cambio_material_smt ORDER BY {columna_tiempo} DESC LIMIT 5")' if columna_tiempo else 'cursor.execute("SELECT * FROM historial_cambio_material_smt LIMIT 5")'}
        registros = cursor.fetchall()
        
        if registros:
            # Obtener nombres de columnas
            cursor.execute("DESCRIBE historial_cambio_material_smt")
            columnas_info = cursor.fetchall()
            nombres_cols = [col[0] for col in columnas_info]
            
            for i, reg in enumerate(registros, 1):
                print(f"\\n--- REGISTRO {{i}} ---")
                for j, valor in enumerate(reg):
                    if j < len(nombres_cols):
                        print(f"   {{nombres_cols[j]}}: {{valor}}")
        else:
            print("   No hay registros en la tabla")
        
        return True
        
    except Error as e:
        print(f"❌ Error: {{e}}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    verificar_datos()
    input("Presiona Enter para continuar...")
'''
    
    with open('verificar_estructura_real.py', 'w', encoding='utf-8') as f:
        f.write(verificador_codigo)
    
    print(f"✅ Creado: verificar_estructura_real.py")

def main():
    print("EXPLORADOR DE ESTRUCTURA REAL DE TABLA")
    print("=" * 60)
    
    resultado = explorar_estructura_completa()
    
    if not resultado[0]:
        print("❌ No se pudo explorar la tabla")
        return
    
    columnas, columnas_tiempo, columnas_csv = resultado[1], resultado[2], resultado[3]
    
    # Generar mapeo sugerido
    mapeo = generar_mapeo_sugerido(columnas, columnas_tiempo, columnas_csv)
    
    # Crear verificador compatible
    crear_verificador_compatible(columnas, mapeo)
    
    print(f"\n" + "=" * 60)
    print("✅ EXPLORACIÓN COMPLETADA")
    print("=" * 60)
    print("PRÓXIMOS PASOS:")
    print("1. Revisar la estructura mostrada arriba")
    print("2. Ejecutar: python verificar_estructura_real.py")
    print("3. Ajustar el servicio smt_monitor_service.py con el mapeo correcto")
    print("\nNOTA: El servicio necesita ser modificado para usar")
    print("las columnas reales de la tabla, no las que asumimos.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {{e}}")
    
    input("\\nPresiona Enter para continuar...")'''

    with open('explorar_estructura_real.py', 'w', encoding='utf-8') as f:
        f.write(verificador_codigo)
    
    print(f"✅ Creado: explorar_estructura_real.py")

def main():
    print("EXPLORADOR DE ESTRUCTURA REAL DE TABLA")
    print("=" * 60)
    
    resultado = explorar_estructura_completa()
    
    if not resultado[0]:
        print("❌ No se pudo explorar la tabla")
        return
    
    columnas, columnas_tiempo, columnas_csv = resultado[1], resultado[2], resultado[3]
    
    # Generar mapeo sugerido
    mapeo = generar_mapeo_sugerido(columnas, columnas_tiempo, columnas_csv)
    
    # Crear verificador compatible
    crear_verificador_compatible(columnas, mapeo)
    
    print(f"\n" + "=" * 60)
    print("✅ EXPLORACIÓN COMPLETADA")
    print("=" * 60)
    print("PRÓXIMOS PASOS:")
    print("1. Revisar la estructura mostrada arriba")
    print("2. Ejecutar: python verificar_estructura_real.py")
    print("3. Ajustar el servicio smt_monitor_service.py con el mapeo correcto")
    print("\nNOTA: El servicio necesita ser modificado para usar")
    print("las columnas reales de la tabla, no las que asumimos.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
