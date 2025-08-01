#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear todas las tablas necesarias en MySQL
Usuario: isemm2025
Contraseña: ISEMM2025
Base de datos: isemm_mes
"""

import pymysql
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def crear_conexion():
    """Crear conexión a MySQL"""
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USERNAME', 'isemm2025'),
            password=os.getenv('MYSQL_PASSWORD', 'ISEMM2025'),
            database=os.getenv('MYSQL_DATABASE', 'isemm_mes'),
            charset='utf8mb4',
            autocommit=True
        )
        print(f"✅ Conectado a MySQL: {os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}")
        return connection
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

def crear_tablas(connection):
    """Crear todas las tablas necesarias"""
    cursor = connection.cursor()
    
    tablas = {
        'materiales': """
            CREATE TABLE IF NOT EXISTS materiales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(100) UNIQUE NOT NULL,
                descripcion TEXT,
                categoria VARCHAR(100),
                ubicacion VARCHAR(100),
                cantidad_disponible INT DEFAULT 0,
                cantidad_minima INT DEFAULT 0,
                unidad_medida VARCHAR(50),
                costo_unitario DECIMAL(10,2),
                proveedor VARCHAR(200),
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                prohibidoSacar BOOLEAN DEFAULT FALSE,
                reparable BOOLEAN DEFAULT FALSE,
                activo BOOLEAN DEFAULT TRUE
            )
        """,
        
        'inventario_general': """
            CREATE TABLE IF NOT EXISTS inventario_general (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(100) NOT NULL,
                descripcion TEXT,
                cantidad_disponible INT DEFAULT 0,
                ubicacion VARCHAR(100),
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte) ON UPDATE CASCADE
            )
        """,
        
        'entrada_aereo': """
            CREATE TABLE IF NOT EXISTS entrada_aereo (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(100) NOT NULL,
                descripcion TEXT,
                cantidad INT NOT NULL,
                ubicacion VARCHAR(100),
                fecha_entrada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario VARCHAR(100),
                observaciones TEXT
            )
        """,
        
        'control_material_almacen': """
            CREATE TABLE IF NOT EXISTS control_material_almacen (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(100) NOT NULL,
                descripcion TEXT,
                cantidad_entrada INT DEFAULT 0,
                cantidad_salida INT DEFAULT 0,
                cantidad_actual INT DEFAULT 0,
                ubicacion VARCHAR(100),
                fecha_movimiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tipo_movimiento ENUM('entrada', 'salida') NOT NULL,
                usuario VARCHAR(100),
                observaciones TEXT
            )
        """,
        
        'control_material_produccion': """
            CREATE TABLE IF NOT EXISTS control_material_produccion (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(100) NOT NULL,
                descripcion TEXT,
                cantidad_requerida INT NOT NULL,
                cantidad_utilizada INT DEFAULT 0,
                orden_produccion VARCHAR(100),
                fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_utilizacion TIMESTAMP NULL,
                estado ENUM('asignado', 'en_uso', 'completado', 'cancelado') DEFAULT 'asignado',
                usuario VARCHAR(100),
                observaciones TEXT
            )
        """,
        
        'control_calidad': """
            CREATE TABLE IF NOT EXISTS control_calidad (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(100) NOT NULL,
                lote VARCHAR(100),
                cantidad_inspeccionada INT NOT NULL,
                cantidad_aprobada INT DEFAULT 0,
                cantidad_rechazada INT DEFAULT 0,
                fecha_inspeccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                inspector VARCHAR(100),
                resultado ENUM('aprobado', 'rechazado', 'pendiente') DEFAULT 'pendiente',
                observaciones TEXT,
                criterios_calidad JSON
            )
        """,
        
        'bom': """
            CREATE TABLE IF NOT EXISTS bom (
                id INT AUTO_INCREMENT PRIMARY KEY,
                modelo VARCHAR(100) NOT NULL,
                numero_parte VARCHAR(100) NOT NULL,
                descripcion TEXT,
                cantidad_requerida DECIMAL(10,3) NOT NULL,
                unidad VARCHAR(50),
                nivel INT DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                activo BOOLEAN DEFAULT TRUE,
                INDEX idx_modelo (modelo),
                INDEX idx_numero_parte (numero_parte)
            )
        """,
        
        'usuarios': """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                nombre_completo VARCHAR(200),
                rol ENUM('admin', 'supervisor', 'operador', 'viewer') DEFAULT 'viewer',
                departamento VARCHAR(100),
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_acceso TIMESTAMP NULL,
                intentos_fallidos INT DEFAULT 0,
                bloqueado_hasta TIMESTAMP NULL
            )
        """,
        
        'usuarios_sistema': """
            CREATE TABLE IF NOT EXISTS usuarios_sistema (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                nombre_completo VARCHAR(200),
                departamento VARCHAR(100),
                cargo VARCHAR(100),
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_acceso TIMESTAMP NULL,
                intentos_fallidos INT DEFAULT 0,
                bloqueado_hasta TIMESTAMP NULL,
                creado_por VARCHAR(50),
                modificado_por VARCHAR(50),
                fecha_modificacion TIMESTAMP NULL
            )
        """,
        
        'roles': """
            CREATE TABLE IF NOT EXISTS roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(50) UNIQUE NOT NULL,
                descripcion TEXT,
                permisos JSON,
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        
        'usuario_roles': """
            CREATE TABLE IF NOT EXISTS usuario_roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT NOT NULL,
                rol_id INT NOT NULL,
                fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                activo BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios_sistema(id) ON DELETE CASCADE,
                FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE,
                UNIQUE KEY unique_usuario_rol (usuario_id, rol_id)
            )
        """,
        
        'permisos_botones': """
            CREATE TABLE IF NOT EXISTS permisos_botones (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario VARCHAR(50) NOT NULL,
                boton VARCHAR(100) NOT NULL,
                permitido BOOLEAN DEFAULT FALSE,
                fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_usuario_boton (usuario, boton)
            )
        """,
        
        'configuracion': """
            CREATE TABLE IF NOT EXISTS configuracion (
                id INT AUTO_INCREMENT PRIMARY KEY,
                clave VARCHAR(100) UNIQUE NOT NULL,
                valor TEXT,
                descripcion TEXT,
                tipo ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """,
        
        'auditoria': """
            CREATE TABLE IF NOT EXISTS auditoria (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tabla VARCHAR(100) NOT NULL,
                operacion ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
                registro_id VARCHAR(100),
                datos_anteriores JSON,
                datos_nuevos JSON,
                usuario VARCHAR(50),
                fecha_operacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent TEXT
            )
        """
    }
    
    print("\n🔧 Creando tablas en MySQL...")
    
    for nombre_tabla, sql in tablas.items():
        try:
            cursor.execute(sql)
            print(f"✅ Tabla '{nombre_tabla}' creada exitosamente")
        except Exception as e:
            print(f"❌ Error creando tabla '{nombre_tabla}': {e}")
    
    cursor.close()
    print("\n🎉 Proceso de creación de tablas completado")

def insertar_datos_iniciales(connection):
    """Insertar datos iniciales necesarios"""
    cursor = connection.cursor()
    
    print("\n📝 Insertando datos iniciales...")
    
    # Insertar usuario administrador por defecto
    try:
        cursor.execute("""
            INSERT IGNORE INTO usuarios (username, password_hash, email, nombre_completo, rol, departamento)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ('admin', 'pbkdf2:sha256:600000$salt$hash', 'admin@isemm.com', 'Administrador del Sistema', 'admin', 'TI'))
        print("✅ Usuario administrador creado")
    except Exception as e:
        print(f"⚠️ Usuario administrador: {e}")
    
    # Insertar roles básicos
    roles_basicos = [
        ('admin', 'Administrador del sistema', '{"all": true}'),
        ('supervisor', 'Supervisor de área', '{"read": true, "write": true, "delete": false}'),
        ('operador', 'Operador de producción', '{"read": true, "write": true, "delete": false}'),
        ('viewer', 'Solo lectura', '{"read": true, "write": false, "delete": false}')
    ]
    
    for nombre, descripcion, permisos in roles_basicos:
        try:
            cursor.execute("""
                INSERT IGNORE INTO roles (nombre, descripcion, permisos)
                VALUES (%s, %s, %s)
            """, (nombre, descripcion, permisos))
            print(f"✅ Rol '{nombre}' creado")
        except Exception as e:
            print(f"⚠️ Rol '{nombre}': {e}")
    
    # Insertar configuraciones básicas
    configuraciones = [
        ('sistema_nombre', 'ISEMM MES', 'Nombre del sistema', 'string'),
        ('version', '2.0.0', 'Versión del sistema', 'string'),
        ('backup_automatico', 'true', 'Activar backup automático', 'boolean'),
        ('max_intentos_login', '3', 'Máximo intentos de login', 'number')
    ]
    
    for clave, valor, descripcion, tipo in configuraciones:
        try:
            cursor.execute("""
                INSERT IGNORE INTO configuracion (clave, valor, descripcion, tipo)
                VALUES (%s, %s, %s, %s)
            """, (clave, valor, descripcion, tipo))
            print(f"✅ Configuración '{clave}' creada")
        except Exception as e:
            print(f"⚠️ Configuración '{clave}': {e}")
    
    cursor.close()
    print("\n✅ Datos iniciales insertados")

def main():
    """Función principal"""
    print("🚀 Iniciando creación de tablas MySQL para ISEMM MES")
    print("📋 Usuario: isemm2025")
    print("📋 Base de datos: isemm_mes")
    print("="*60)
    
    # Crear conexión
    connection = crear_conexion()
    if not connection:
        print("❌ No se pudo conectar a MySQL. Verifica las credenciales.")
        return
    
    try:
        # Crear tablas
        crear_tablas(connection)
        
        # Insertar datos iniciales
        insertar_datos_iniciales(connection)
        
        print("\n🎉 ¡Todas las tablas han sido creadas exitosamente!")
        print("\n📊 Resumen:")
        print("   - Base de datos: isemm_mes")
        print("   - Usuario MySQL: isemm2025")
        print("   - Tablas principales: materiales, inventario_general, bom, usuarios")
        print("   - Tablas de control: entrada_aereo, control_material_almacen, control_calidad")
        print("   - Tablas de sistema: roles, permisos_botones, configuracion, auditoria")
        print("\n✅ El sistema está listo para usar con MySQL")
        
    except Exception as e:
        print(f"❌ Error durante la creación: {e}")
    
    finally:
        connection.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    main()