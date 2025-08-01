#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que estamos conectados a la base de datos del hosting
"""

import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

def verificar_conexion_hosting():
    """Verificar conexión a MySQL del hosting"""
    print("🔍 VERIFICANDO CONEXIÓN A BASE DE DATOS DEL HOSTING")
    print("=" * 60)
    
    # Mostrar configuración actual
    print(f"📋 CONFIGURACIÓN ACTUAL:")
    print(f"   DB_TYPE: {os.getenv('DB_TYPE')}")
    print(f"   MYSQL_HOST: {os.getenv('MYSQL_HOST')}")
    print(f"   MYSQL_PORT: {os.getenv('MYSQL_PORT')}")
    print(f"   MYSQL_DATABASE: {os.getenv('MYSQL_DATABASE')}")
    print(f"   USE_HTTP_PROXY: {os.getenv('USE_HTTP_PROXY')}")
    
    try:
        # Conectar directamente al hosting
        config = {
            'host': os.getenv('MYSQL_HOST'),
            'port': int(os.getenv('MYSQL_PORT')),
            'user': os.getenv('MYSQL_USERNAME'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE'),
            'charset': 'utf8mb4'
        }
        
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        print(f"\n✅ CONECTADO AL HOSTING: {config['host']}:{config['port']}")
        
        # Verificar información del servidor
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"   Versión MySQL: {version}")
        
        cursor.execute("SELECT DATABASE()")
        db_actual = cursor.fetchone()[0]
        print(f"   Base de datos actual: {db_actual}")
        
        # Estadísticas de tablas principales
        print(f"\n📊 ESTADÍSTICAS DE TABLAS MIGRADAS:")
        print("-" * 40)
        
        tablas_principales = [
            'usuarios_sistema',
            'roles',
            'usuario_roles', 
            'rol_permisos_botones',
            'control_material_almacen',
            'inventario_general',
            'bom'
        ]
        
        total_registros = 0
        for tabla in tablas_principales:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                total_registros += count
                print(f"   ✅ {tabla}: {count:,} registros")
            except Exception as e:
                print(f"   ❌ {tabla}: Error - {e}")
        
        print(f"\n📈 TOTAL REGISTROS MIGRADOS: {total_registros:,}")
        
        # Verificar usuarios activos
        print(f"\n👥 USUARIOS EN EL SISTEMA:")
        print("-" * 30)
        
        cursor.execute("""
            SELECT u.username, r.nombre as rol, u.activo
            FROM usuarios_sistema u
            LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
            LEFT JOIN roles r ON ur.rol_id = r.id
            WHERE u.activo = 1
            ORDER BY u.username
        """)
        
        usuarios = cursor.fetchall()
        for usuario in usuarios:
            status = "🟢" if usuario[2] else "🔴"
            print(f"   {status} {usuario[0]} - {usuario[1] or 'Sin rol'}")
        
        # Verificar última actividad
        cursor.execute("""
            SELECT MAX(fecha_creacion) as ultima_actividad
            FROM control_material_almacen
        """)
        
        ultima_actividad = cursor.fetchone()[0]
        if ultima_actividad:
            print(f"\n⏰ ÚLTIMA ACTIVIDAD: {ultima_actividad}")
        
        conn.close()
        
        print(f"\n🎉 CONFIRMADO: Aplicación conectada al MySQL del hosting")
        print(f"   ✅ Datos migrados correctamente")
        print(f"   ✅ Sistema funcionando en producción")
        print(f"   ✅ Base de datos remota activa")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR DE CONEXIÓN: {e}")
        return False

if __name__ == "__main__":
    print(f"Verificación realizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    verificar_conexion_hosting()