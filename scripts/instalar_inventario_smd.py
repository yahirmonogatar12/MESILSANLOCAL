#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador del Sistema de Inventario de Rollos SMD
Ejecuta el script SQL y configura las APIs necesarias
"""

import mysql.connector
import os
import sys
from datetime import datetime

# Configuración de base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def conectar_db():
    """Establecer conexión con la base de datos"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        print("✓ Conexión a base de datos establecida")
        return connection
    except Exception as e:
        print(f"✗ Error conectando a la base de datos: {e}")
        return None

def ejecutar_script_sql():
    """Ejecutar el script SQL de creación de tablas"""
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'crear_inventario_rollos_smd.sql')
        
        if not os.path.exists(script_path):
            print(f"✗ No se encontró el archivo SQL: {script_path}")
            return False
        
        connection = conectar_db()
        if not connection:
            return False
        
        cursor = connection.cursor()
        
        # Leer y ejecutar el script SQL
        with open(script_path, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        
        # Dividir en statements individuales
        statements = []
        current_statement = ""
        delimiter = ";"
        
        for line in sql_script.split('\n'):
            line = line.strip()
            
            # Manejar DELIMITER
            if line.startswith('DELIMITER'):
                delimiter = line.split()[1]
                continue
            
            if line and not line.startswith('--'):
                current_statement += line + '\n'
                
                if line.endswith(delimiter) and delimiter != "//":
                    statements.append(current_statement.rstrip(delimiter).strip())
                    current_statement = ""
                elif delimiter == "//" and line.endswith("//"):
                    statements.append(current_statement.rstrip("//").strip())
                    current_statement = ""
                    delimiter = ";"
        
        # Añadir último statement si existe
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        # Ejecutar cada statement
        for i, statement in enumerate(statements):
            if statement.strip():
                try:
                    print(f"Ejecutando statement {i+1}/{len(statements)}...")
                    cursor.execute(statement)
                    connection.commit()
                    print(f"✓ Statement {i+1} ejecutado correctamente")
                except Exception as e:
                    print(f"✗ Error en statement {i+1}: {e}")
                    print(f"Statement: {statement[:100]}...")
                    # Continuar con el siguiente statement
        
        cursor.close()
        connection.close()
        print("✓ Script SQL ejecutado completamente")
        return True
        
    except Exception as e:
        print(f"✗ Error ejecutando script SQL: {e}")
        return False

def verificar_instalacion():
    """Verificar que las tablas se crearon correctamente"""
    try:
        connection = conectar_db()
        if not connection:
            return False
        
        cursor = connection.cursor()
        
        # Verificar tablas principales
        tablas_requeridas = [
            'InventarioRollosSMD',
            'HistorialMovimientosRollosSMD'
        ]
        
        for tabla in tablas_requeridas:
            cursor.execute(f"SHOW TABLES LIKE '{tabla}'")
            result = cursor.fetchone()
            if result:
                print(f"✓ Tabla {tabla} existe")
                
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"  - Registros: {count}")
            else:
                print(f"✗ Tabla {tabla} no encontrada")
                return False
        
        # Verificar triggers
        cursor.execute("SHOW TRIGGERS LIKE 'trigger_registro_rollo_smd_salida'")
        if cursor.fetchone():
            print("✓ Trigger de registro automático instalado")
        else:
            print("✗ Trigger de registro automático no encontrado")
        
        cursor.execute("SHOW TRIGGERS LIKE 'trigger_actualizar_rollo_smd_mounter'")
        if cursor.fetchone():
            print("✓ Trigger de actualización de mounter instalado")
        else:
            print("✗ Trigger de actualización de mounter no encontrado")
        
        # Verificar procedimientos
        cursor.execute("SHOW PROCEDURE STATUS WHERE Name = 'sp_marcar_rollo_agotado'")
        if cursor.fetchone():
            print("✓ Procedimiento de marcado de agotado instalado")
        else:
            print("✗ Procedimiento de marcado de agotado no encontrado")
        
        # Verificar vista
        cursor.execute("SHOW TABLES LIKE 'vista_estado_rollos_smd'")
        if cursor.fetchone():
            print("✓ Vista de estado de rollos instalada")
        else:
            print("✗ Vista de estado de rollos no encontrada")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"✗ Error verificando instalación: {e}")
        return False

def crear_datos_prueba():
    """Crear algunos datos de prueba para testing"""
    try:
        connection = conectar_db()
        if not connection:
            return False
        
        cursor = connection.cursor()
        
        # Datos de prueba
        datos_prueba = [
            ('RESISTOR_0603_1K', 'SMD_RESISTOR_0603_1K_20241201_120000', 5000, 5000, 'ACTIVO'),
            ('CAPACITOR_0805_10UF', 'SMD_CAPACITOR_0805_10UF_20241201_120100', 3000, 3000, 'ACTIVO'),
            ('LED_RED_0603', 'SMD_LED_RED_0603_20241201_120200', 2000, 1500, 'EN_USO')
        ]
        
        for numero_parte, codigo_barras, cantidad_inicial, cantidad_actual, estado in datos_prueba:
            cursor.execute("""
                INSERT IGNORE INTO InventarioRollosSMD 
                (numero_parte, codigo_barras, cantidad_inicial, cantidad_actual, estado, observaciones)
                VALUES (%s, %s, %s, %s, %s, 'Datos de prueba generados automáticamente')
            """, (numero_parte, codigo_barras, cantidad_inicial, cantidad_actual, estado))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("✓ Datos de prueba creados")
        return True
        
    except Exception as e:
        print(f"✗ Error creando datos de prueba: {e}")
        return False

def actualizar_rutas_principales():
    """Información para actualizar routes.py principal"""
    info_integracion = """
    
=== INTEGRACIÓN CON APLICACIÓN PRINCIPAL ===

Para completar la instalación, agregue las siguientes líneas a su archivo routes.py principal:

1. Importar el nuevo módulo:
   from .smd_inventory_api import register_smd_inventory_routes

2. Registrar las rutas (en la función de inicialización de la app):
   register_smd_inventory_routes(app)

3. Agregar ruta al menú principal:
   @app.route('/smd/inventario')
   def smd_inventario():
       return redirect('/smd/inventario')

=== RUTAS DISPONIBLES ===

• GET  /smd/inventario - Página principal del inventario
• GET  /api/smd/inventario/rollos - Lista de rollos con filtros
• GET  /api/smd/inventario/rollo/<id> - Detalle de rollo específico
• POST /api/smd/inventario/rollo/<id>/marcar_agotado - Marcar rollo como agotado
• POST /api/smd/inventario/rollo/<id>/asignar_mounter - Asignar rollo a mounter
• GET  /api/smd/inventario/stats - Estadísticas del inventario
• POST /api/smd/inventario/sincronizar - Sincronizar con almacén

=== FUNCIONAMIENTO AUTOMÁTICO ===

El sistema funcionará automáticamente:
• Los triggers detectarán salidas del almacén hacia SMD
• Se crearán registros automáticamente en InventarioRollosSMD
• Los cambios en mounters actualizarán el estado de los rollos
• Se mantendrá historial completo de movimientos

"""
    print(info_integracion)

def main():
    """Función principal de instalación"""
    print("=" * 60)
    print("INSTALADOR DEL SISTEMA DE INVENTARIO DE ROLLOS SMD")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("Iniciando instalación...")
    print()
    
    # Paso 1: Ejecutar script SQL
    print("1. Ejecutando script SQL...")
    if not ejecutar_script_sql():
        print("✗ Falló la ejecución del script SQL")
        return False
    print()
    
    # Paso 2: Verificar instalación
    print("2. Verificando instalación...")
    if not verificar_instalacion():
        print("✗ Falló la verificación de instalación")
        return False
    print()
    
    # Paso 3: Crear datos de prueba
    print("3. Creando datos de prueba...")
    if not crear_datos_prueba():
        print("⚠ No se pudieron crear datos de prueba (no crítico)")
    print()
    
    # Paso 4: Mostrar información de integración
    print("4. Información de integración...")
    actualizar_rutas_principales()
    
    print("=" * 60)
    print("✓ INSTALACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 60)
    print()
    print("El sistema de inventario de rollos SMD está listo para usar.")
    print("Recuerde integrar las rutas en su aplicación principal.")
    print()
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✗ Instalación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Error inesperado: {e}")
        sys.exit(1)
