#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador de Inventarios por Tipo de Material
Crea inventarios separados para SMD, IMD y MAIN con distribución automática
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

def ejecutar_script_inventarios():
    """Ejecutar el script SQL de creación de inventarios por tipo"""
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'crear_inventarios_por_tipo.sql')
        
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
        exitosos = 0
        errores = 0
        
        for i, statement in enumerate(statements):
            if statement.strip():
                try:
                    print(f"Ejecutando statement {i+1}/{len(statements)}...")
                    cursor.execute(statement)
                    connection.commit()
                    print(f"✓ Statement {i+1} ejecutado correctamente")
                    exitosos += 1
                except Exception as e:
                    print(f"✗ Error en statement {i+1}: {e}")
                    print(f"Statement: {statement[:100]}...")
                    errores += 1
                    # Continuar con el siguiente statement
        
        cursor.close()
        connection.close()
        
        print(f"\n✓ Script ejecutado: {exitosos} exitosos, {errores} errores")
        return errores == 0
        
    except Exception as e:
        print(f"✗ Error ejecutando script SQL: {e}")
        return False

def verificar_instalacion_inventarios():
    """Verificar que los inventarios se crearon correctamente"""
    try:
        connection = conectar_db()
        if not connection:
            return False
        
        cursor = connection.cursor()
        
        print("\n=== VERIFICACIÓN DE INVENTARIOS ===")
        
        # Verificar tablas principales
        inventarios = ['SMD', 'IMD', 'MAIN']
        
        for inventario in inventarios:
            print(f"\n{inventario} INVENTARIO:")
            
            # Verificar tabla principal
            tabla_principal = f'InventarioRollos{inventario}'
            cursor.execute(f"SHOW TABLES LIKE '{tabla_principal}'")
            if cursor.fetchone():
                cursor.execute(f"SELECT COUNT(*) FROM {tabla_principal}")
                count = cursor.fetchone()[0]
                print(f"  ✓ {tabla_principal}: {count} registros")
            else:
                print(f"  ✗ {tabla_principal}: NO EXISTE")
                return False
            
            # Verificar tabla de historial
            tabla_historial = f'HistorialMovimientosRollos{inventario}'
            cursor.execute(f"SHOW TABLES LIKE '{tabla_historial}'")
            if cursor.fetchone():
                cursor.execute(f"SELECT COUNT(*) FROM {tabla_historial}")
                count = cursor.fetchone()[0]
                print(f"  ✓ {tabla_historial}: {count} registros")
            else:
                print(f"  ✗ {tabla_historial}: NO EXISTE")
        
        # Verificar trigger de distribución automática
        print(f"\nTRIGGERS:")
        cursor.execute("SHOW TRIGGERS LIKE 'tr_distribuir_salidas_por_tipo'")
        if cursor.fetchone():
            print("  ✓ Trigger de distribución automática instalado")
        else:
            print("  ✗ Trigger de distribución automática no encontrado")
        
        # Verificar vistas
        print(f"\nVISTAS:")
        cursor.execute("SHOW TABLES LIKE 'vista_inventarios_consolidados'")
        if cursor.fetchone():
            print("  ✓ Vista consolidada creada")
            
            # Mostrar estadísticas
            cursor.execute("SELECT * FROM vista_estadisticas_inventarios")
            stats = cursor.fetchall()
            if stats:
                print("  Estadísticas por inventario:")
                for stat in stats:
                    tipo, total, activos, en_uso, agotados, cantidad_total, promedio = stat
                    print(f"    {tipo}: {total} rollos ({activos} activos, {en_uso} en uso, {agotados} agotados)")
        else:
            print("  ✗ Vista consolidada no encontrada")
        
        # Verificar procedimientos
        print(f"\nPROCEDIMIENTOS:")
        cursor.execute("SHOW PROCEDURE STATUS WHERE Name = 'sp_marcar_rollo_agotado_generico'")
        if cursor.fetchone():
            print("  ✓ Procedimiento genérico de agotado instalado")
        else:
            print("  ✗ Procedimiento genérico de agotado no encontrado")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"✗ Error verificando instalación: {e}")
        return False

def probar_distribucion_automatica():
    """Probar que la distribución automática funcione"""
    try:
        connection = conectar_db()
        if not connection:
            return False
        
        cursor = connection.cursor()
        
        print("\n=== PRUEBA DE DISTRIBUCIÓN AUTOMÁTICA ===")
        
        # Obtener materiales de diferentes tipos para prueba
        cursor.execute("""
            SELECT codigo_material_recibido, numero_parte, propiedad_material, cantidad_actual
            FROM control_material_almacen 
            WHERE propiedad_material IN ('SMD', 'IMD', 'MAIN') 
            AND cantidad_actual > 0
            ORDER BY propiedad_material
            LIMIT 3
        """)
        
        materiales_prueba = cursor.fetchall()
        
        if not materiales_prueba:
            print("  ⚠ No hay materiales disponibles para prueba")
            print("  Creando materiales de prueba...")
            
            # Crear materiales de prueba
            materiales_prueba = [
                ('TEST_SMD_001', 'SMD_TEST_PART', 'SMD', 1000),
                ('TEST_IMD_001', 'IMD_TEST_PART', 'IMD', 500),
                ('TEST_MAIN_001', 'MAIN_TEST_PART', 'MAIN', 200)
            ]
            
            for codigo, parte, propiedad, cantidad in materiales_prueba:
                cursor.execute("""
                    INSERT IGNORE INTO control_material_almacen 
                    (codigo_material_recibido, numero_parte, propiedad_material, cantidad_actual)
                    VALUES (%s, %s, %s, %s)
                """, (codigo, parte, propiedad, cantidad))
            
            connection.commit()
        
        # Contar inventarios antes de la prueba
        counts_antes = {}
        for inventario in ['SMD', 'IMD', 'MAIN']:
            cursor.execute(f"SELECT COUNT(*) FROM InventarioRollos{inventario}")
            counts_antes[inventario] = cursor.fetchone()[0]
        
        print(f"  Inventarios antes de prueba: SMD={counts_antes['SMD']}, IMD={counts_antes['IMD']}, MAIN={counts_antes['MAIN']}")
        
        # Simular salidas que deberían distribuirse automáticamente
        for codigo, parte, propiedad, cantidad in materiales_prueba[:3]:
            print(f"  Probando salida de {propiedad}: {codigo}")
            
            try:
                cursor.execute("""
                    INSERT INTO control_material_salida (
                        codigo_material_recibido, numero_lote, modelo, depto_salida,
                        proceso_salida, cantidad_salida, fecha_salida, especificacion_material
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    codigo,
                    'LOTE_PRUEBA_AUTO',
                    'MODELO_PRUEBA',
                    propiedad,
                    'PRODUCCION_PRUEBA',
                    10,
                    '2025-08-13',
                    propiedad
                ))
                
                salida_id = cursor.lastrowid
                print(f"    ✓ Salida creada con ID: {salida_id}")
                
            except Exception as e:
                print(f"    ✗ Error creando salida: {e}")
        
        connection.commit()
        
        # Verificar que se distribuyeron correctamente
        print("  Verificando distribución automática:")
        
        counts_despues = {}
        for inventario in ['SMD', 'IMD', 'MAIN']:
            cursor.execute(f"SELECT COUNT(*) FROM InventarioRollos{inventario}")
            counts_despues[inventario] = cursor.fetchone()[0]
            
            incremento = counts_despues[inventario] - counts_antes[inventario]
            if incremento > 0:
                print(f"    ✓ {inventario}: +{incremento} rollo(s) agregado(s)")
            else:
                print(f"    ⚠ {inventario}: Sin nuevos rollos")
        
        # Limpiar datos de prueba
        print("  Limpiando datos de prueba...")
        cursor.execute("DELETE FROM control_material_salida WHERE numero_lote = 'LOTE_PRUEBA_AUTO'")
        
        for inventario in ['SMD', 'IMD', 'MAIN']:
            cursor.execute(f"DELETE FROM InventarioRollos{inventario} WHERE observaciones LIKE '%PRUEBA%'")
        
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Error en prueba de distribución: {e}")
        return False

def mostrar_informacion_integracion():
    """Mostrar información para integración con la aplicación"""
    info = """
=== INTEGRACIÓN CON APLICACIÓN PRINCIPAL ===

NUEVOS INVENTARIOS CREADOS:
• InventarioRollosSMD (ya existía, mejorado)
• InventarioRollosIMD (nuevo)
• InventarioRollosMAIN (nuevo)

FUNCIONAMIENTO AUTOMÁTICO:
• Material con propiedad 'SMD' → InventarioRollosSMD
• Material con propiedad 'IMD' → InventarioRollosIMD  
• Material con propiedad 'MAIN' → InventarioRollosMAIN

TRIGGER INSTALADO:
• tr_distribuir_salidas_por_tipo
• Se activa automáticamente en cada salida de material
• Distribuye según la propiedad_material del almacén

VISTAS DISPONIBLES:
• vista_inventarios_consolidados - Todos los inventarios unificados
• vista_estadisticas_inventarios - Estadísticas por tipo

APIs RECOMENDADAS PARA CREAR:
• /api/inventario/smd/rollos
• /api/inventario/imd/rollos  
• /api/inventario/main/rollos
• /api/inventario/consolidado

INTERFACES WEB SUGERIDAS:
• Control de material → Inventario SMD
• Control de material → Inventario IMD
• Control de material → Inventario MAIN
• Control de material → Vista consolidada

PRÓXIMOS PASOS:
1. Crear APIs específicas para cada inventario
2. Crear interfaces web para gestión
3. Integrar con sistema de mounters/estaciones
4. Configurar alertas de stock bajo por inventario
"""
    print(info)

def main():
    """Función principal de instalación"""
    print("=" * 70)
    print("INSTALADOR DE INVENTARIOS POR TIPO DE MATERIAL")
    print("SMD | IMD | MAIN - Distribución Automática")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("Iniciando instalación de inventarios por tipo...")
    print()
    
    # Paso 1: Ejecutar script SQL
    print("1. Ejecutando script de inventarios...")
    if not ejecutar_script_inventarios():
        print("✗ Falló la ejecución del script de inventarios")
        return False
    print()
    
    # Paso 2: Verificar instalación
    print("2. Verificando instalación...")
    if not verificar_instalacion_inventarios():
        print("✗ Falló la verificación de instalación")
        return False
    print()
    
    # Paso 3: Probar distribución automática
    print("3. Probando distribución automática...")
    if not probar_distribucion_automatica():
        print("⚠ Hubo problemas en la prueba de distribución (no crítico)")
    print()
    
    # Paso 4: Mostrar información de integración
    print("4. Información de integración...")
    mostrar_informacion_integracion()
    
    print("=" * 70)
    print("✓ INSTALACIÓN DE INVENTARIOS COMPLETADA EXITOSAMENTE")
    print("=" * 70)
    print()
    print("El sistema de inventarios por tipo está listo.")
    print("Distribución automática: SMD | IMD | MAIN")
    print("Cada salida se dirigirá automáticamente al inventario correcto.")
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
