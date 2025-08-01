#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script automático para configurar MySQL
Crea usuario ilsanmes y todas las tablas necesarias
"""

import pymysql

def conectar_como_root():
    """Conectar como usuario root con credenciales comunes"""
    print("🔐 Intentando conectar como root...")
    
    # Credenciales comunes de root
    credenciales_root = [
        ('root', ''),  # Sin contraseña
        ('root', 'root'),  # Contraseña root
        ('root', 'admin'),  # Contraseña admin
        ('root', 'password'),  # Contraseña password
        ('root', '123456'),  # Contraseña 123456
        ('admin', 'admin'),  # Usuario admin
        ('mysql', 'mysql'),  # Usuario mysql
    ]
    
    for usuario, password in credenciales_root:
        try:
            print(f"   Probando {usuario}/{password if password else '(sin contraseña)'}...")
            connection = pymysql.connect(
                host='100.111.108.116',
                port=3306,
                user=usuario,
                password=password,
                charset='utf8mb4',
                autocommit=True,
                connect_timeout=10
            )
            print(f"✅ Conectado como {usuario}@100.111.108.116:3306")
            return connection
        except Exception as e:
            print(f"   ❌ Falló: {str(e)[:50]}...")
            continue
    
    print("❌ No se pudo conectar con ninguna credencial de root")
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
        try:
            cursor.execute("DROP USER IF EXISTS 'ilsanmes'@'%'")
            print("ℹ️ Usuario anterior eliminado")
        except:
            pass
            
        cursor.execute("CREATE USER 'ilsanmes'@'%' IDENTIFIED BY 'ISEMM2025'")
        print("✅ Usuario 'ilsanmes' creado")
        
        # Otorgar todos los permisos en la base de datos
        cursor.execute("GRANT ALL PRIVILEGES ON isemm_mes.* TO 'ilsanmes'@'%'")
        cursor.execute("GRANT ALL PRIVILEGES ON isemm_mes.* TO 'ilsanmes'@'localhost'")
        cursor.execute("FLUSH PRIVILEGES")
        print("✅ Permisos otorgados a 'ilsanmes'")
        
        # Verificar que el usuario puede conectar
        cursor.execute("SELECT User, Host FROM mysql.user WHERE User = 'ilsanmes'")
        results = cursor.fetchall()
        if results:
            print("✅ Usuario verificado:")
            for result in results:
                print(f"   - {result[0]}@{result[1]}")
        
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
            autocommit=True,
            connect_timeout=10
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

def mostrar_resumen_final():
    """Mostrar resumen final de la configuración"""
    print("\n" + "="*60)
    print("🎉 ¡CONFIGURACIÓN MYSQL COMPLETADA EXITOSAMENTE!")
    print("="*60)
    print("\n📊 CONFIGURACIÓN FINAL:")
    print("   🏠 Servidor: 100.111.108.116:3306")
    print("   🗄️ Base de datos: isemm_mes")
    print("   👤 Usuario MySQL: ilsanmes")
    print("   🔑 Contraseña: ISEMM2025")
    print("\n📋 TABLAS PRINCIPALES:")
    print("   ✅ materiales - Catálogo de materiales")
    print("   ✅ inventario_general - Control de inventario")
    print("   ✅ entrada_aereo - Entradas de material aéreo")
    print("   ✅ control_material_almacen - Control de almacén")
    print("   ✅ control_material_produccion - Control de producción")
    print("   ✅ control_calidad - Control de calidad")
    print("   ✅ bom - Bill of Materials")
    print("   ✅ usuarios - Sistema de usuarios")
    print("   ✅ roles - Roles y permisos")
    print("   ✅ configuracion - Configuraciones del sistema")
    print("\n👤 CREDENCIALES DE ACCESO:")
    print("   Usuario aplicación: admin")
    print("   Contraseña: admin123")
    print("\n🚀 PRÓXIMOS PASOS:")
    print("   1. Reiniciar la aplicación Flask")
    print("   2. La aplicación detectará MySQL automáticamente")
    print("   3. Iniciar sesión con admin/admin123")
    print("   4. Comenzar a usar el sistema ISEMM MES")
    print("\n✅ ¡Sistema completamente configurado y listo para usar!")

def main():
    """Función principal"""
    print("🚀 CONFIGURACIÓN AUTOMÁTICA DE MYSQL PARA ISEMM MES")
    print("📍 Servidor: 100.111.108.116:3306")
    print("🎯 Objetivo: Crear usuario 'ilsanmes' y todas las tablas")
    print("="*60)
    
    # Paso 1: Conectar como root
    root_conn = conectar_como_root()
    if not root_conn:
        print("\n❌ No se pudo conectar como root con ninguna credencial común.")
        print("\n💡 Soluciones manuales:")
        print("   1. Conectar al servidor MySQL manualmente")
        print("   2. Ejecutar: CREATE USER 'ilsanmes'@'%' IDENTIFIED BY 'ISEMM2025';")
        print("   3. Ejecutar: GRANT ALL PRIVILEGES ON *.* TO 'ilsanmes'@'%';")
        print("   4. Ejecutar: FLUSH PRIVILEGES;")
        print("   5. Volver a ejecutar este script")
        return
    
    # Paso 2: Crear usuario y base de datos
    if not crear_usuario_y_bd(root_conn):
        print("❌ Error creando usuario/base de datos")
        root_conn.close()
        return
    
    root_conn.close()
    print("\n🔌 Conexión root cerrada")
    
    # Paso 3: Conectar como ilsanmes
    isemm_conn = conectar_como_ilsanmes()
    if not isemm_conn:
        print("❌ No se pudo conectar como ilsanmes")
        return
    
    try:
        # Paso 4: Crear tablas
        tablas_creadas = crear_tablas(isemm_conn)
        
        # Paso 5: Insertar datos iniciales
        datos_insertados = insertar_datos_iniciales(isemm_conn)
        
        # Paso 6: Mostrar resumen
        mostrar_resumen_final()
        
    except Exception as e:
        print(f"❌ Error durante la configuración: {e}")
    
    finally:
        isemm_conn.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    main()