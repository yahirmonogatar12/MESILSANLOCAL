#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para configurar MySQL en servidor remoto
Host: 100.111.108.116
Usuario: ilsanmes
Contraseña: ISEMM2025
"""

import pymysql
import getpass

def conectar_como_root():
    """Conectar como usuario root para crear usuario y base de datos"""
    print("🔐 Conectando como usuario root al servidor MySQL remoto...")
    print("📍 Host: 100.111.108.116")
    
    # Solicitar credenciales de root
    root_user = input("Usuario root MySQL (default: root): ").strip() or "root"
    root_password = getpass.getpass("Contraseña root MySQL: ")
    
    try:
        connection = pymysql.connect(
            host='100.111.108.116',
            port=3306,
            user=root_user,
            password=root_password,
            charset='utf8mb4',
            autocommit=True
        )
        print(f"✅ Conectado como {root_user}@100.111.108.116:3306")
        return connection
    except Exception as e:
        print(f"❌ Error conectando como root: {e}")
        return None

def crear_usuario_y_bd(connection):
    """Crear usuario ilsanmes y base de datos isemm_mes"""
    cursor = connection.cursor()
    
    print("\n🔧 Configurando usuario y base de datos...")
    
    try:
        # Crear base de datos
        cursor.execute("CREATE DATABASE IF NOT EXISTS isemm_mes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print("✅ Base de datos 'isemm_mes' creada")
        
        # Crear usuario (eliminar si existe)
        cursor.execute("DROP USER IF EXISTS 'ilsanmes'@'%'")
        cursor.execute("CREATE USER 'ilsanmes'@'%' IDENTIFIED BY 'ISEMM2025'")
        print("✅ Usuario 'ilsanmes' creado")
        
        # Otorgar todos los permisos en la base de datos
        cursor.execute("GRANT ALL PRIVILEGES ON isemm_mes.* TO 'ilsanmes'@'%'")
        cursor.execute("FLUSH PRIVILEGES")
        print("✅ Permisos otorgados a 'ilsanmes'")
        
        # Verificar que el usuario puede conectar
        cursor.execute("SELECT User, Host FROM mysql.user WHERE User = 'ilsanmes'")
        result = cursor.fetchone()
        if result:
            print(f"✅ Usuario verificado: {result[0]}@{result[1]}")
        
    except Exception as e:
        print(f"❌ Error configurando usuario/BD: {e}")
        return False
    
    finally:
        cursor.close()
    
    return True

def conectar_como_ilsanmes():
    """Conectar como usuario ilsanmes"""
    try:
        connection = pymysql.connect(
            host='100.111.108.116',
            port=3306,
            user='ilsanmes',
            password='ISEMM2025',
            database='isemm_mes',
            charset='utf8mb4',
            autocommit=True
        )
        print("✅ Conectado como ilsanmes a base de datos isemm_mes")
        return connection
    except Exception as e:
        print(f"❌ Error conectando como ilsanmes: {e}")
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
    print("🎉 ¡CONFIGURACIÓN MYSQL REMOTO COMPLETADA!")
    print("="*60)
    print("\n📊 RESUMEN DE CONFIGURACIÓN:")
    print("   🏠 Host: 100.111.108.116:3306")
    print("   🗄️  Base de datos: isemm_mes")
    print("   👤 Usuario: ilsanmes")
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
    print("\n✅ El sistema ISEMM MES está listo para usar con MySQL remoto")

def probar_conexion_directa():
    """Probar conexión directa con las credenciales actuales"""
    print("\n🧪 Probando conexión directa con credenciales actuales...")
    try:
        connection = pymysql.connect(
            host='100.111.108.116',
            port=3306,
            user='ilsanmes',
            password='ISEMM2025',
            charset='utf8mb4',
            connect_timeout=10
        )
        print("✅ ¡Conexión exitosa! El usuario ya existe y funciona.")
        
        # Verificar si la base de datos existe
        cursor = connection.cursor()
        cursor.execute("SHOW DATABASES LIKE 'isemm_mes'")
        result = cursor.fetchone()
        
        if result:
            print("✅ Base de datos 'isemm_mes' ya existe")
            # Conectar a la base de datos específica
            connection.select_db('isemm_mes')
            
            # Verificar tablas existentes
            cursor.execute("SHOW TABLES")
            tablas = cursor.fetchall()
            
            if tablas:
                print(f"✅ Se encontraron {len(tablas)} tablas existentes:")
                for tabla in tablas:
                    print(f"   - {tabla[0]}")
                return connection, True  # Base de datos y tablas ya existen
            else:
                print("⚠️ Base de datos existe pero no tiene tablas")
                return connection, False  # Solo crear tablas
        else:
            print("⚠️ Base de datos 'isemm_mes' no existe")
            cursor.execute("CREATE DATABASE isemm_mes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print("✅ Base de datos 'isemm_mes' creada")
            connection.select_db('isemm_mes')
            return connection, False  # Crear tablas
            
    except Exception as e:
        print(f"❌ Error en conexión directa: {e}")
        return None, False

def main():
    """Función principal"""
    print("🚀 CONFIGURACIÓN MYSQL REMOTO PARA ISEMM MES")
    print("📍 Servidor: 100.111.108.116:3306")
    print("📋 Usuario: ilsanmes")
    print("📋 Contraseña: ISEMM2025")
    print("📋 Base de datos: isemm_mes")
    print("="*60)
    
    # Primero probar conexión directa
    connection, tablas_existen = probar_conexion_directa()
    
    if connection:
        if tablas_existen:
            print("\n🎉 ¡El sistema ya está configurado y listo para usar!")
            mostrar_resumen()
        else:
            print("\n🔧 Creando tablas faltantes...")
            crear_tablas(connection)
            insertar_datos_iniciales(connection)
            mostrar_resumen()
        
        connection.close()
        return
    
    # Si la conexión directa falla, intentar configurar desde root
    print("\n⚠️ Conexión directa falló. Intentando configurar desde root...")
    
    # Conectar como root
    root_conn = conectar_como_root()
    if not root_conn:
        print("❌ No se pudo conectar como root. Verifica las credenciales.")
        return
    
    # Crear usuario y base de datos
    if not crear_usuario_y_bd(root_conn):
        print("❌ Error creando usuario/base de datos")
        root_conn.close()
        return
    
    root_conn.close()
    print("\n🔌 Conexión root cerrada")
    
    # Conectar como ilsanmes
    isemm_conn = conectar_como_ilsanmes()
    if not isemm_conn:
        print("❌ No se pudo conectar como ilsanmes")
        return
    
    try:
        # Crear tablas
        crear_tablas(isemm_conn)
        
        # Insertar datos iniciales
        insertar_datos_iniciales(isemm_conn)
        
        # Mostrar resumen
        mostrar_resumen()
        
    except Exception as e:
        print(f"❌ Error durante la configuración: {e}")
    
    finally:
        isemm_conn.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    main()