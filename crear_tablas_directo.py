#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script directo para crear tablas en MySQL remoto
Asume que el usuario ilsanmes ya existe
"""

import pymysql
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def crear_conexion():
    """Crear conexión a MySQL remoto"""
    try:
        # Primero intentar conectar sin base de datos específica
        connection = pymysql.connect(
            host='100.111.108.116',
            port=3306,
            user='ILSANMES',
            password='ISEMM2025',
            charset='utf8mb4',
            autocommit=True,
            connect_timeout=30
        )
        print(f"✅ Conectado a MySQL: 100.111.108.116:3306")
        
        # Crear base de datos si no existe
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS isemm2025 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print("✅ Base de datos 'isemm2025' verificada/creada")
        
        # Seleccionar la base de datos
        connection.select_db('isemm2025')
        cursor.close()
        
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
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
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
        """
    }
    
    print("\n🔧 Creando tablas en MySQL...")
    
    tablas_creadas = 0
    for nombre_tabla, sql in tablas.items():
        try:
            cursor.execute(sql)
            print(f"✅ Tabla '{nombre_tabla}' creada exitosamente")
            tablas_creadas += 1
        except Exception as e:
            print(f"❌ Error creando tabla '{nombre_tabla}': {e}")
    
    cursor.close()
    print(f"\n🎉 Proceso completado: {tablas_creadas}/{len(tablas)} tablas creadas")
    return tablas_creadas

def insertar_datos_iniciales(connection):
    """Insertar datos iniciales necesarios"""
    cursor = connection.cursor()
    
    print("\n📝 Insertando datos iniciales...")
    
    datos_insertados = 0
    
    # Insertar usuario administrador por defecto
    try:
        cursor.execute("""
            INSERT IGNORE INTO usuarios (username, password_hash, email, nombre_completo, rol, departamento)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ('admin', 'admin123', 'admin@isemm.com', 'Administrador del Sistema', 'admin', 'TI'))
        if cursor.rowcount > 0:
            print("✅ Usuario administrador creado (admin/admin123)")
            datos_insertados += 1
        else:
            print("ℹ️ Usuario administrador ya existe")
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
            if cursor.rowcount > 0:
                print(f"✅ Rol '{nombre}' creado")
                datos_insertados += 1
            else:
                print(f"ℹ️ Rol '{nombre}' ya existe")
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
            if cursor.rowcount > 0:
                print(f"✅ Configuración '{clave}' creada")
                datos_insertados += 1
            else:
                print(f"ℹ️ Configuración '{clave}' ya existe")
        except Exception as e:
            print(f"⚠️ Configuración '{clave}': {e}")
    
    cursor.close()
    print(f"\n✅ Datos iniciales: {datos_insertados} registros nuevos insertados")
    return datos_insertados

def verificar_tablas(connection):
    """Verificar qué tablas existen"""
    cursor = connection.cursor()
    
    try:
        cursor.execute("SHOW TABLES")
        tablas = cursor.fetchall()
        
        if tablas:
            print(f"\n📋 Tablas existentes ({len(tablas)}):")
            for tabla in tablas:
                # Contar registros en cada tabla
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {tabla[0]}")
                    count = cursor.fetchone()[0]
                    print(f"   ✅ {tabla[0]} ({count} registros)")
                except:
                    print(f"   ✅ {tabla[0]}")
        else:
            print("\n⚠️ No se encontraron tablas")
            
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
    
    cursor.close()

def main():
    """Función principal"""
    print("🚀 CREACIÓN DIRECTA DE TABLAS MYSQL")
    print("📍 Servidor: 100.111.108.116:3306")
    print("👤 Usuario: ILSANMES")
    print("🗄️ Base de datos: isemm2025")
    print("="*50)
    
    # Crear conexión
    connection = crear_conexion()
    if not connection:
        print("❌ No se pudo conectar a MySQL.")
        print("\n💡 Posibles soluciones:")
        print("   1. Verificar que el usuario 'ILSANMES' existe")
        print("   2. Verificar que la contraseña 'ISEMM2025' es correcta")
        print("   3. Verificar conectividad de red al servidor")
        print("   4. Verificar que el puerto 3306 está abierto")
        return
    
    try:
        # Verificar estado actual
        verificar_tablas(connection)
        
        # Crear tablas
        tablas_creadas = crear_tablas(connection)
        
        # Insertar datos iniciales
        datos_insertados = insertar_datos_iniciales(connection)
        
        # Verificar resultado final
        verificar_tablas(connection)
        
        print("\n" + "="*50)
        print("🎉 ¡CONFIGURACIÓN COMPLETADA!")
        print("="*50)
        print(f"📊 Resumen:")
        print(f"   🏠 Servidor: 100.111.108.116:3306")
        print(f"   🗄️ Base de datos: isemm2025")
        print(f"   👤 Usuario: ILSANMES")
        print(f"   📋 Tablas procesadas: {tablas_creadas}")
        print(f"   📝 Datos insertados: {datos_insertados}")
        print("\n👤 Usuario administrador:")
        print("   Usuario: admin")
        print("   Contraseña: admin123")
        print("\n🚀 Próximos pasos:")
        print("   1. Reiniciar la aplicación Flask")
        print("   2. La aplicación detectará MySQL automáticamente")
        print("   3. Iniciar sesión con admin/admin123")
        print("\n✅ Sistema listo para usar")
        
    except Exception as e:
        print(f"❌ Error durante la configuración: {e}")
    
    finally:
        connection.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    main()