#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear la tabla rol_permisos_botones en el hosting
y migrar los datos desde la base de datos local
"""

import mysql.connector
import sqlite3
import os
from dotenv import load_dotenv

# Cargar variables de entorno del hosting
load_dotenv('hosting_config_mysql_directo.env')

def conectar_hosting():
    """Conectar a la base de datos del hosting"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USERNAME'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            port=int(os.getenv('MYSQL_PORT', 3306))
        )
        print(f"✅ Conexión exitosa al hosting: {os.getenv('MYSQL_DATABASE')}")
        return connection
    except Exception as e:
        print(f"❌ Error conectando al hosting: {e}")
        return None

def conectar_local():
    """Conectar a la base de datos local SQLite"""
    try:
        db_path = 'app/database/ISEMM_MES.db'
        if not os.path.exists(db_path):
            print(f"❌ No se encontró la base de datos local: {db_path}")
            return None
            
        connection = sqlite3.connect(db_path)
        print("✅ Conexión exitosa a la base de datos local")
        return connection
    except Exception as e:
        print(f"❌ Error conectando a la base de datos local: {e}")
        return None

def crear_tabla_rol_permisos_botones(hosting_conn):
    """Crear la tabla rol_permisos_botones en el hosting"""
    try:
        cursor = hosting_conn.cursor()
        
        # Crear la tabla
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS rol_permisos_botones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            rol_id INT NOT NULL,
            pagina VARCHAR(100) NOT NULL,
            seccion VARCHAR(100) NOT NULL,
            boton VARCHAR(100) NOT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE,
            UNIQUE KEY unique_permiso (rol_id, pagina, seccion, boton)
        )
        """
        
        cursor.execute(create_table_sql)
        hosting_conn.commit()
        print("✅ Tabla 'rol_permisos_botones' creada exitosamente")
        
    except Exception as e:
        print(f"❌ Error creando la tabla: {e}")
        raise

def migrar_datos_rol_permisos_botones(local_conn, hosting_conn):
    """Migrar datos de rol_permisos_botones desde local al hosting"""
    try:
        local_cursor = local_conn.cursor()
        hosting_cursor = hosting_conn.cursor()
        
        # Verificar si la tabla existe en local
        local_cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='rol_permisos_botones'
        """)
        
        if not local_cursor.fetchone():
            print("⚠️ La tabla 'rol_permisos_botones' no existe en la base de datos local")
            return
        
        # Obtener datos de la tabla local con JOIN a permisos_botones
        local_cursor.execute("""
            SELECT rpb.rol_id, pb.pagina, pb.seccion, pb.boton
            FROM rol_permisos_botones rpb
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
        """)
        datos_locales = local_cursor.fetchall()
        
        if not datos_locales:
            print("⚠️ No hay datos en la tabla local 'rol_permisos_botones'")
            return
        
        print(f"📊 Encontrados {len(datos_locales)} registros en la tabla local")
        
        # Insertar datos en el hosting
        insert_sql = """
            INSERT IGNORE INTO rol_permisos_botones (rol_id, pagina, seccion, boton)
            VALUES (%s, %s, %s, %s)
        """
        
        registros_insertados = 0
        for dato in datos_locales:
            try:
                hosting_cursor.execute(insert_sql, dato)
                if hosting_cursor.rowcount > 0:
                    registros_insertados += 1
            except Exception as e:
                print(f"⚠️ Error insertando registro {dato}: {e}")
        
        hosting_conn.commit()
        print(f"✅ {registros_insertados} registros migrados exitosamente")
        
    except Exception as e:
        print(f"❌ Error migrando datos: {e}")
        raise

def asignar_permisos_superadmin(hosting_conn):
    """Asignar todos los permisos al rol superadmin"""
    try:
        cursor = hosting_conn.cursor()
        
        # Obtener el ID del rol superadmin
        cursor.execute("SELECT id FROM roles WHERE nombre = 'superadmin'")
        result = cursor.fetchone()
        
        if not result:
            print("⚠️ No se encontró el rol 'superadmin'")
            return
            
        superadmin_id = result[0]
        print(f"🔑 ID del rol superadmin: {superadmin_id}")
        
        # Obtener todos los permisos de botones disponibles
        cursor.execute("SELECT DISTINCT pagina, seccion, boton FROM permisos_botones")
        todos_permisos = cursor.fetchall()
        
        if not todos_permisos:
            print("⚠️ No se encontraron permisos en la tabla 'permisos_botones'")
            return
            
        print(f"📋 Encontrados {len(todos_permisos)} permisos únicos")
        
        # Asignar todos los permisos al superadmin
        insert_sql = """
            INSERT IGNORE INTO rol_permisos_botones (rol_id, pagina, seccion, boton)
            VALUES (%s, %s, %s, %s)
        """
        
        permisos_asignados = 0
        for permiso in todos_permisos:
            try:
                cursor.execute(insert_sql, (superadmin_id, permiso[0], permiso[1], permiso[2]))
                if cursor.rowcount > 0:
                    permisos_asignados += 1
            except Exception as e:
                print(f"⚠️ Error asignando permiso {permiso}: {e}")
        
        hosting_conn.commit()
        print(f"✅ {permisos_asignados} permisos asignados al rol superadmin")
        
    except Exception as e:
        print(f"❌ Error asignando permisos al superadmin: {e}")
        raise

def verificar_resultado(hosting_conn):
    """Verificar el resultado de la migración"""
    try:
        cursor = hosting_conn.cursor()
        
        # Contar total de registros
        cursor.execute("SELECT COUNT(*) FROM rol_permisos_botones")
        total = cursor.fetchone()[0]
        print(f"\n📊 Total de registros en rol_permisos_botones: {total}")
        
        # Contar por rol
        cursor.execute("""
            SELECT r.nombre, COUNT(rpb.id)
            FROM roles r
            LEFT JOIN rol_permisos_botones rpb ON r.id = rpb.rol_id
            GROUP BY r.id, r.nombre
            ORDER BY r.nombre
        """)
        
        roles_permisos = cursor.fetchall()
        print("\n👥 Permisos por rol:")
        for rol, count in roles_permisos:
            print(f"  - {rol}: {count} permisos")
            
    except Exception as e:
        print(f"❌ Error verificando resultado: {e}")

def main():
    """Función principal"""
    print("🚀 Iniciando creación y migración de tabla 'rol_permisos_botones'...\n")
    
    # Conectar a ambas bases de datos
    hosting_conn = conectar_hosting()
    if not hosting_conn:
        return
        
    local_conn = conectar_local()
    
    try:
        # Crear la tabla en el hosting
        crear_tabla_rol_permisos_botones(hosting_conn)
        
        # Migrar datos desde local si existe
        if local_conn:
            migrar_datos_rol_permisos_botones(local_conn, hosting_conn)
        
        # Asignar todos los permisos al superadmin
        asignar_permisos_superadmin(hosting_conn)
        
        # Verificar resultado
        verificar_resultado(hosting_conn)
        
        print("\n✅ Proceso completado exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error en el proceso: {e}")
    finally:
        if local_conn:
            local_conn.close()
        if hosting_conn:
            hosting_conn.close()
        print("\n🔐 Conexiones cerradas")

if __name__ == "__main__":
    main()