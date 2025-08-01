#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir problemas de claves externas en MySQL
"""

import mysql.connector
from datetime import datetime

# Importar configuración MySQL del sistema
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from config_mysql import get_mysql_connection
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("⚠️ No se pudo importar configuración MySQL")

def conectar_mysql():
    """Conectar a MySQL usando configuración del sistema"""
    if not MYSQL_AVAILABLE:
        print("❌ MySQL no disponible")
        return None
    
    try:
        conn = get_mysql_connection()
        if conn:
            print("✅ Conectado a MySQL")
            return conn
        else:
            print("❌ No se pudo obtener conexión MySQL")
            return None
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

def corregir_tabla_inventario():
    """Corregir problemas de clave externa en tabla inventario"""
    conn = conectar_mysql()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        print("🔧 Corrigiendo tabla inventario...")
        
        # 1. Verificar si la tabla inventario existe
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'inventario'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("ℹ️ Tabla inventario no existe, creándola...")
            
            # Crear tabla inventario sin restricciones de clave externa problemáticas
            cursor.execute("""
                CREATE TABLE inventario (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    numero_parte VARCHAR(255) NOT NULL,
                    codigo_material VARCHAR(255),
                    especificacion TEXT,
                    cantidad_disponible INT DEFAULT 0,
                    cantidad_reservada INT DEFAULT 0,
                    cantidad_total INT DEFAULT 0,
                    ubicacion VARCHAR(255),
                    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    activo BOOLEAN DEFAULT TRUE,
                    INDEX idx_numero_parte (numero_parte),
                    INDEX idx_codigo_material (codigo_material)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ Tabla inventario creada")
        else:
            print("ℹ️ Tabla inventario ya existe")
            
            # Eliminar restricciones de clave externa problemáticas
            try:
                cursor.execute("ALTER TABLE inventario DROP FOREIGN KEY inventario_ibfk_1")
                print("✅ Restricción inventario_ibfk_1 eliminada")
            except:
                print("ℹ️ Restricción inventario_ibfk_1 no existe o ya fue eliminada")
        
        # 2. Verificar tabla materiales
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'materiales'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("ℹ️ Tabla materiales no existe, creándola...")
            
            cursor.execute("""
                CREATE TABLE materiales (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    numero_parte VARCHAR(255) UNIQUE NOT NULL,
                    codigo_material VARCHAR(255),
                    especificacion TEXT,
                    descripcion TEXT,
                    unidad_medida VARCHAR(50),
                    precio_unitario DECIMAL(10,2),
                    proveedor VARCHAR(255),
                    categoria VARCHAR(100),
                    activo BOOLEAN DEFAULT TRUE,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_numero_parte (numero_parte),
                    INDEX idx_codigo_material (codigo_material)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ Tabla materiales creada")
        else:
            print("ℹ️ Tabla materiales ya existe")
        
        # 3. Crear índices necesarios si no existen
        try:
            cursor.execute("CREATE INDEX idx_materiales_numero_parte ON materiales(numero_parte)")
            print("✅ Índice idx_materiales_numero_parte creado")
        except:
            print("ℹ️ Índice idx_materiales_numero_parte ya existe")
        
        # 4. Agregar clave externa opcional (sin restricción estricta)
        try:
            cursor.execute("""
                ALTER TABLE inventario 
                ADD CONSTRAINT fk_inventario_materiales 
                FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte) 
                ON DELETE SET NULL ON UPDATE CASCADE
            """)
            print("✅ Clave externa opcional agregada")
        except Exception as e:
            print(f"ℹ️ No se pudo agregar clave externa opcional: {e}")
        
        conn.commit()
        print("✅ Correcciones aplicadas")
        return True
        
    except Exception as e:
        print(f"❌ Error corrigiendo tabla inventario: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def verificar_tablas_sistema():
    """Verificar que todas las tablas del sistema existan"""
    conn = conectar_mysql()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        print("🔍 Verificando tablas del sistema...")
        
        # Lista de tablas críticas
        tablas_criticas = [
            'usuarios_sistema',
            'roles',
            'permisos_botones',
            'usuario_roles',
            'rol_permisos_botones',
            'sesiones_activas',
            'auditoria',
            'materiales',
            'inventario',
            'control_material_almacen',
            'control_material_salida'
        ]
        
        tablas_existentes = []
        tablas_faltantes = []
        
        for tabla in tablas_criticas:
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            """, (tabla,))
            
            if cursor.fetchone()[0] > 0:
                tablas_existentes.append(tabla)
            else:
                tablas_faltantes.append(tabla)
        
        print(f"✅ Tablas existentes ({len(tablas_existentes)}): {', '.join(tablas_existentes)}")
        
        if tablas_faltantes:
            print(f"⚠️ Tablas faltantes ({len(tablas_faltantes)}): {', '.join(tablas_faltantes)}")
        else:
            print("✅ Todas las tablas críticas existen")
        
        return len(tablas_faltantes) == 0
        
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def optimizar_mysql():
    """Aplicar optimizaciones para MySQL"""
    conn = conectar_mysql()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        print("⚡ Aplicando optimizaciones MySQL...")
        
        # Configuraciones de rendimiento
        optimizaciones = [
            "SET GLOBAL innodb_buffer_pool_size = 128M",
            "SET GLOBAL query_cache_size = 32M",
            "SET GLOBAL max_connections = 200"
        ]
        
        for opt in optimizaciones:
            try:
                cursor.execute(opt)
                print(f"✅ {opt}")
            except Exception as e:
                print(f"⚠️ {opt} - {e}")
        
        # Verificar configuración
        cursor.execute("SHOW VARIABLES LIKE 'innodb_buffer_pool_size'")
        result = cursor.fetchone()
        if result:
            print(f"📊 InnoDB Buffer Pool: {result[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error aplicando optimizaciones: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def main():
    """Función principal"""
    print("🚀 Corrigiendo claves externas y optimizando MySQL")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    exito = True
    
    # 1. Corregir tabla inventario
    if not corregir_tabla_inventario():
        exito = False
    
    print()
    
    # 2. Verificar tablas del sistema
    if not verificar_tablas_sistema():
        print("⚠️ Algunas tablas críticas faltan")
    
    print()
    
    # 3. Aplicar optimizaciones
    if not optimizar_mysql():
        print("⚠️ No se pudieron aplicar todas las optimizaciones")
    
    print("="*60)
    
    if exito:
        print("✅ Corrección de claves externas completada")
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. Reinicia la aplicación Flask")
        print("2. Verifica que el login funcione correctamente")
        print("3. Prueba las funcionalidades principales")
    else:
        print("❌ Hubo errores durante la corrección")
        print("\n🔧 RECOMENDACIONES:")
        print("1. Verifica la conexión a MySQL")
        print("2. Asegúrate de que el usuario tenga permisos")
        print("3. Revisa los logs de MySQL")

if __name__ == "__main__":
    main()