#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir db.py y asegurar compatibilidad total con MySQL
"""

import os
import shutil
from datetime import datetime

def crear_backup(archivo_path):
    """Crear backup de un archivo"""
    backup_path = f"{archivo_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(archivo_path, backup_path)
    print(f"📁 Backup: {backup_path}")
    return backup_path

def corregir_db_py():
    """Corregir db.py para compatibilidad total con MySQL"""
    archivo = "app/db.py"
    print(f"🔧 Corrigiendo {archivo}")
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Crear backup
        crear_backup(archivo)
        
        # Correcciones específicas
        # 1. AUTOINCREMENT -> AUTO_INCREMENT
        contenido = contenido.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "INT AUTO_INCREMENT PRIMARY KEY")
        contenido = contenido.replace("AUTOINCREMENT", "AUTO_INCREMENT")
        
        # 2. Placeholders ? -> %s
        contenido = contenido.replace("?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?", "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?, ?, ?, ?, ?", "%s, %s, %s, %s, %s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?, ?, ?, ?", "%s, %s, %s, %s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?, ?, ?", "%s, %s, %s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?, ?", "%s, %s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?, ?", "%s, %s, %s, %s")
        contenido = contenido.replace("?, ?, ?", "%s, %s, %s")
        contenido = contenido.replace("?, ?", "%s, %s")
        contenido = contenido.replace("= ?", "= %s")
        contenido = contenido.replace("(?)", "(%s)")
        
        # 3. Agregar función para detectar si estamos usando MySQL
        if "def is_mysql_connection" not in contenido:
            mysql_detection = '''

def is_mysql_connection():
    """Detectar si estamos usando MySQL"""
    from .db_mysql import MYSQL_AVAILABLE
    return MYSQL_AVAILABLE

'''
            # Insertar después de los imports
            import_end = contenido.find('\n\n')
            if import_end != -1:
                contenido = contenido[:import_end] + mysql_detection + contenido[import_end:]
        
        # 4. Modificar get_db_connection para usar MySQL cuando esté disponible
        if "def get_db_connection():" in contenido:
            old_function = '''def get_db_connection():
    """Obtener conexión a la base de datos"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None'''
        
            new_function = '''def get_db_connection():
    """Obtener conexión a la base de datos (MySQL preferido, SQLite como fallback)"""
    try:
        # Intentar MySQL primero
        if is_mysql_connection():
            from .db_mysql import get_mysql_connection
            return get_mysql_connection()
        else:
            # Fallback a SQLite
            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            return conn
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        # Último recurso: SQLite
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e2:
            print(f"Error crítico conectando a SQLite: {e2}")
            return None'''
            
            contenido = contenido.replace(old_function, new_function)
        
        # Escribir archivo corregido
        with open(archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"✅ {archivo} corregido")
        return True
        
    except Exception as e:
        print(f"❌ Error en {archivo}: {e}")
        return False

def corregir_db_mysql_py():
    """Asegurar que db_mysql.py tenga la función get_mysql_connection"""
    archivo = "app/db_mysql.py"
    print(f"🔧 Verificando {archivo}")
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Verificar si ya existe get_mysql_connection
        if "def get_mysql_connection():" not in contenido:
            # Crear backup
            crear_backup(archivo)
            
            # Agregar función get_mysql_connection
            mysql_connection_func = '''

def get_mysql_connection():
    """Obtener conexión MySQL con row_factory simulado"""
    try:
        import mysql.connector
        from .config_mysql import MYSQL_CONFIG
        
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        
        # Simular row_factory de SQLite
        class MySQLRowFactory:
            def __init__(self, cursor):
                self.cursor = cursor
                self.columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            def fetchone(self):
                row = self.cursor.fetchone()
                if row:
                    return dict(zip(self.columns, row))
                return None
            
            def fetchall(self):
                rows = self.cursor.fetchall()
                return [dict(zip(self.columns, row)) for row in rows]
            
            def execute(self, query, params=None):
                return self.cursor.execute(query, params)
            
            def close(self):
                return self.cursor.close()
        
        # Reemplazar cursor con wrapper
        original_cursor = conn.cursor
        def cursor_wrapper():
            cursor = original_cursor()
            return MySQLRowFactory(cursor)
        
        conn.cursor = cursor_wrapper
        return conn
        
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

'''
            # Agregar al final del archivo
            contenido += mysql_connection_func
            
            # Escribir archivo corregido
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            print(f"✅ {archivo} actualizado con get_mysql_connection")
            return True
        else:
            print(f"ℹ️ {archivo} ya tiene get_mysql_connection")
            return False
        
    except Exception as e:
        print(f"❌ Error en {archivo}: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Corrigiendo db.py para MySQL")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    archivos_corregidos = 0
    
    # Corregir archivos
    if corregir_db_py():
        archivos_corregidos += 1
    
    if corregir_db_mysql_py():
        archivos_corregidos += 1
    
    print("="*50)
    print(f"📊 Archivos procesados: {archivos_corregidos}")
    print("✅ Corrección de db.py completada")
    
    if archivos_corregidos > 0:
        print("\n⚠️ IMPORTANTE:")
        print("• Se crearon backups de los archivos modificados")
        print("• Reinicia la aplicación para aplicar los cambios")

if __name__ == "__main__":
    main()