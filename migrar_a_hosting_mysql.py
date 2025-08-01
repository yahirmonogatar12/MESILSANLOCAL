#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para migrar datos desde MySQL local (Tailscale) a MySQL del hosting
Autor: Asistente AI
Fecha: 2025-07-31
"""

import pymysql
import os
from datetime import datetime
import json

# Configuración de la base de datos origen (Tailscale)
ORIGEN_CONFIG = {
    'host': '100.111.108.116',
    'port': 3306,
    'database': 'isemm2025',
    'username': 'ILSANMES',
    'password': 'ISEMM2025'
}

# Configuración de la base de datos destino (Hosting)
DESTINO_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'database': 'db_rrpq0erbdujn',
    'username': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge'
}

# Lista de tablas a migrar
TABLAS_A_MIGRAR = [
    'usuarios',
    'materiales',
    'inventario',
    'movimientos_inventario',
    'bom',
    'configuracion',
    'entrada_aereo',
    'control_material_almacen',
    'control_material_produccion',
    'control_calidad'
]

def conectar_bd(config, nombre=""):
    """Conectar a una base de datos MySQL"""
    try:
        conexion = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['username'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"✅ Conectado a {nombre} ({config['host']}:{config['port']})")
        return conexion
    except Exception as e:
        print(f"❌ Error conectando a {nombre}: {e}")
        return None

def obtener_estructura_tabla(cursor, tabla):
    """Obtener la estructura de una tabla"""
    cursor.execute(f"SHOW CREATE TABLE {tabla}")
    resultado = cursor.fetchone()
    return resultado['Create Table']

def crear_tabla_en_destino(cursor_destino, tabla, estructura):
    """Crear tabla en la base de datos destino"""
    try:
        cursor_destino.execute(f"DROP TABLE IF EXISTS {tabla}")
        cursor_destino.execute(estructura)
        print(f"✅ Tabla {tabla} creada en destino")
        return True
    except Exception as e:
        print(f"❌ Error creando tabla {tabla}: {e}")
        return False

def migrar_datos_tabla(cursor_origen, cursor_destino, tabla):
    """Migrar datos de una tabla"""
    try:
        # Obtener todos los datos de la tabla origen
        cursor_origen.execute(f"SELECT * FROM {tabla}")
        datos = cursor_origen.fetchall()
        
        if not datos:
            print(f"⚠️  Tabla {tabla} está vacía")
            return True
        
        # Preparar la consulta de inserción
        columnas = list(datos[0].keys())
        placeholders = ', '.join(['%s'] * len(columnas))
        columnas_str = ', '.join([f"`{col}`" for col in columnas])
        
        query_insert = f"INSERT INTO {tabla} ({columnas_str}) VALUES ({placeholders})"
        
        # Insertar datos en lotes
        valores = []
        for fila in datos:
            valores.append(tuple(fila.values()))
        
        cursor_destino.executemany(query_insert, valores)
        print(f"✅ Migrados {len(datos)} registros de {tabla}")
        return True
        
    except Exception as e:
        print(f"❌ Error migrando datos de {tabla}: {e}")
        return False

def main():
    """Función principal de migración"""
    print("🚀 Iniciando migración de datos MySQL")
    print("=" * 50)
    
    # Conectar a ambas bases de datos
    conn_origen = conectar_bd(ORIGEN_CONFIG, "MySQL Origen (Tailscale)")
    conn_destino = conectar_bd(DESTINO_CONFIG, "MySQL Destino (Hosting)")
    
    if not conn_origen or not conn_destino:
        print("❌ No se pudo conectar a las bases de datos")
        return False
    
    try:
        cursor_origen = conn_origen.cursor()
        cursor_destino = conn_destino.cursor()
        
        # Estadísticas de migración
        tablas_exitosas = 0
        tablas_fallidas = 0
        
        print("\n📋 Iniciando migración de tablas...")
        print("-" * 30)
        
        for tabla in TABLAS_A_MIGRAR:
            print(f"\n🔄 Procesando tabla: {tabla}")
            
            try:
                # Verificar si la tabla existe en origen
                cursor_origen.execute(f"SHOW TABLES LIKE '{tabla}'")
                if not cursor_origen.fetchone():
                    print(f"⚠️  Tabla {tabla} no existe en origen, saltando...")
                    continue
                
                # Obtener estructura de la tabla
                estructura = obtener_estructura_tabla(cursor_origen, tabla)
                
                # Crear tabla en destino
                if crear_tabla_en_destino(cursor_destino, tabla, estructura):
                    # Migrar datos
                    if migrar_datos_tabla(cursor_origen, cursor_destino, tabla):
                        tablas_exitosas += 1
                        conn_destino.commit()
                    else:
                        tablas_fallidas += 1
                        conn_destino.rollback()
                else:
                    tablas_fallidas += 1
                    
            except Exception as e:
                print(f"❌ Error procesando tabla {tabla}: {e}")
                tablas_fallidas += 1
                conn_destino.rollback()
        
        # Resumen final
        print("\n" + "=" * 50)
        print("📊 RESUMEN DE MIGRACIÓN")
        print("=" * 50)
        print(f"✅ Tablas migradas exitosamente: {tablas_exitosas}")
        print(f"❌ Tablas con errores: {tablas_fallidas}")
        print(f"📋 Total de tablas procesadas: {tablas_exitosas + tablas_fallidas}")
        
        if tablas_exitosas > 0:
            print("\n🎉 ¡Migración completada!")
            print("\n📝 Próximos pasos:")
            print("1. Configura las variables de entorno en tu hosting")
            print("2. Usa el archivo: hosting_config_mysql_directo.env")
            print("3. Desplega tu aplicación")
            print("4. Ya no necesitas el proxy MySQL local")
            
        return tablas_exitosas > 0
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        return False
        
    finally:
        # Cerrar conexiones
        if conn_origen:
            conn_origen.close()
            print("\n🔌 Conexión origen cerrada")
        if conn_destino:
            conn_destino.close()
            print("🔌 Conexión destino cerrada")

if __name__ == "__main__":
    print("🔄 MIGRACIÓN MYSQL: LOCAL → HOSTING")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n⚠️  IMPORTANTE: Asegúrate de que ambas bases de datos estén accesibles")
    print("\nPresiona Enter para continuar o Ctrl+C para cancelar...")
    
    try:
        input()
        exito = main()
        if exito:
            print("\n🎯 ¡Migración exitosa! Tu aplicación está lista para el hosting.")
        else:
            print("\n⚠️  Migración incompleta. Revisa los errores arriba.")
    except KeyboardInterrupt:
        print("\n❌ Migración cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")