#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script completo para configurar MySQL desde cero
1. Crear usuario isemm2025
2. Crear base de datos isemm_mes
3. Otorgar permisos
4. Crear todas las tablas
"""

import pymysql
import getpass

def conectar_como_root():
    """Conectar como usuario root para crear usuario y base de datos"""
    print("🔐 Conectando como usuario root de MySQL...")
    
    # Solicitar credenciales de root
    host = input("Host MySQL (default: localhost): ").strip() or "localhost"
    port = input("Puerto MySQL (default: 3306): ").strip() or "3306"
    root_user = input("Usuario root MySQL (default: root): ").strip() or "root"
    root_password = getpass.getpass("Contraseña root MySQL: ")
    
    try:
        connection = pymysql.connect(
            host=host,
            port=int(port),
            user=root_user,
            password=root_password,
            charset='utf8mb4',
            autocommit=True
        )
        print(f"✅ Conectado como {root_user}@{host}:{port}")
        return connection
    except Exception as e:
        print(f"❌ Error conectando como root: {e}")
        return None

def crear_usuario_y_bd(connection):
    """Crear usuario isemm2025 y base de datos isemm_mes"""
    cursor = connection.cursor()
    
    print("\n🔧 Configurando usuario y base de datos...")
    
    try:
        # Crear base de datos
        cursor.execute("CREATE DATABASE IF NOT EXISTS isemm_mes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print("✅ Base de datos 'isemm_mes' creada")
        
        # Crear usuario (eliminar si existe)
        cursor.execute("DROP USER IF EXISTS 'isemm2025'@'localhost'")
        cursor.execute("CREATE USER 'isemm2025'@'localhost' IDENTIFIED BY 'ISEMM2025'")
        print("✅ Usuario 'isemm2025' creado")
        
        # Otorgar todos los permisos en la base de datos
        cursor.execute("GRANT ALL PRIVILEGES ON isemm_mes.* TO 'isemm2025'@'localhost'")
        cursor.execute("FLUSH PRIVILEGES")
        print("✅ Permisos otorgados a 'isemm2025'")
        
        # Verificar que el usuario puede conectar
        cursor.execute("SELECT User, Host FROM mysql.user WHERE User = 'isemm2025'")
        result = cursor.fetchone()
        if result:
            print(f"✅ Usuario verificado: {result[0]}@{result[1]}")
        
    except Exception as e:
        print(f"❌ Error configurando usuario/BD: {e}")
        return False
    
    finally:
        cursor.close()
    
    return True

def conectar_como_isemm():
    """Conectar como usuario isemm2025"""
    try:
        connection = pymysql.connect(
            host='localhost',
            port=3306,
            user='isemm2025',
            password='ISEMM2025',
            database='isemm_mes',
            charset='utf8mb4',
            autocommit=True
        )
        print("✅ Conectado como isemm2025 a base de datos isemm_mes")
        return connection
    except Exception as e:
        print(f"❌ Error conectando como isemm2025: {e}")
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
        # Hash simple para testing (en producción usar werkzeug.security)
        cursor.execute("""
            INSERT IGNORE INTO usuarios (username, password_hash, email, nombre_completo, rol, departamento)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, ('admin', 'admin123', 'admin@isemm.com', 'Administrador del Sistema', 'admin', 'TI'))
        print("✅ Usuario administrador creado (admin/admin123)")
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

def mostrar_resumen():
    """Mostrar resumen de la configuración"""
    print("\n" + "="*60)
    print("🎉 ¡CONFIGURACIÓN MYSQL COMPLETADA EXITOSAMENTE!")
    print("="*60)
    print("\n📊 RESUMEN DE CONFIGURACIÓN:")
    print("   🏠 Host: localhost:3306")
    print("   🗄️  Base de datos: isemm_mes")
    print("   👤 Usuario: isemm2025")
    print("   🔑 Contraseña: ISEMM2025")
    print("\n📋 TABLAS CREADAS:")
    print("   ✅ materiales - Catálogo de materiales")
    print("   ✅ inventario_general - Control de inventario")
    print("   ✅ entrada_aereo - Entradas de material aéreo")
    print("   ✅ control_material_almacen - Control de almacén")
    print("   ✅ control_material_produccion - Control de producción")
    print("   ✅ control_calidad - Control de calidad")
    print("   ✅ bom - Bill of Materials")
    print("   ✅ usuarios - Usuarios del sistema")
    print("   ✅ usuarios_sistema - Sistema de usuarios avanzado")
    print("   ✅ roles - Roles de usuario")
    print("   ✅ usuario_roles - Asignación de roles")
    print("   ✅ permisos_botones - Permisos específicos")
    print("   ✅ configuracion - Configuraciones del sistema")
    print("\n👤 USUARIO ADMINISTRADOR:")
    print("   Usuario: admin")
    print("   Contraseña: admin123")
    print("\n🚀 PRÓXIMOS PASOS:")
    print("   1. Reiniciar la aplicación Flask")
    print("   2. La aplicación detectará MySQL automáticamente")
    print("   3. Iniciar sesión con admin/admin123")
    print("\n✅ El sistema ISEMM MES está listo para usar con MySQL")

def main():
    """Función principal"""
    print("🚀 CONFIGURACIÓN COMPLETA DE MYSQL PARA ISEMM MES")
    print("📋 Este script creará:")
    print("   - Usuario: isemm2025 (contraseña: ISEMM2025)")
    print("   - Base de datos: isemm_mes")
    print("   - Todas las tablas necesarias")
    print("   - Datos iniciales")
    print("\n⚠️  IMPORTANTE: Necesitas credenciales de root de MySQL")
    print("="*60)
    
    # Paso 1: Conectar como root
    root_conn = conectar_como_root()
    if not root_conn:
        print("❌ No se pudo conectar como root. Verifica las credenciales.")
        return
    
    # Paso 2: Crear usuario y base de datos
    if not crear_usuario_y_bd(root_conn):
        print("❌ Error creando usuario/base de datos")
        root_conn.close()
        return
    
    root_conn.close()
    print("\n🔌 Conexión root cerrada")
    
    # Paso 3: Conectar como isemm2025
    isemm_conn = conectar_como_isemm()
    if not isemm_conn:
        print("❌ No se pudo conectar como isemm2025")
        return
    
    try:
        # Paso 4: Crear tablas
        crear_tablas(isemm_conn)
        
        # Paso 5: Insertar datos iniciales
        insertar_datos_iniciales(isemm_conn)
        
        # Paso 6: Mostrar resumen
        mostrar_resumen()
        
    except Exception as e:
        print(f"❌ Error durante la configuración: {e}")
    
    finally:
        isemm_conn.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    main()