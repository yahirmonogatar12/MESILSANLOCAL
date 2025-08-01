"""Funciones de base de datos adaptadas para MySQL
Migración desde SQLite a MySQL para el hosting"""

import os
from .config_mysql import execute_query, test_connection
from datetime import datetime
import json

# Verificar si MySQL está disponible
try:
    from .config_mysql import MYSQL_AVAILABLE
except ImportError:
    MYSQL_AVAILABLE = False

print(f"Módulo db_mysql cargado - MySQL disponible: {MYSQL_AVAILABLE}")

def init_db():
    """Inicializar base de datos MySQL y crear tablas"""
    if not MYSQL_AVAILABLE:
        print("⚠️ MySQL no disponible - usando modo fallback")
        return False
        
    try:
        # Probar conexión
        if not test_connection():
            print("❌ Error conectando a MySQL")
            return False
            
        # Crear tablas necesarias
        create_tables()
        print("✅ Base de datos MySQL inicializada correctamente")
        return True
    except Exception as e:
        print(f"Error inicializando MySQL: {e}")
        return False

def create_tables():
    """Crear tablas necesarias en MySQL"""
    tables = {
        'usuarios': '''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                area VARCHAR(255),
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion DATETIME DEFAULT NOW()
            )
        ''',
        'materiales': '''
            CREATE TABLE IF NOT EXISTS materiales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(255) UNIQUE NOT NULL,
                descripcion TEXT,
                categoria VARCHAR(255),
                ubicacion VARCHAR(255),
                stock_minimo INT DEFAULT 0,
                stock_maximo INT DEFAULT 0,
                unidad_medida VARCHAR(50),
                proveedor VARCHAR(255),
                fecha_creacion DATETIME DEFAULT NOW()
            )
        ''',
        'inventario': '''
            CREATE TABLE IF NOT EXISTS inventario (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(255) UNIQUE NOT NULL,
                cantidad_actual INT DEFAULT 0,
                ultima_actualizacion DATETIME DEFAULT NOW(),
                FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte)
            )
        ''',
        'movimientos_inventario': '''
            CREATE TABLE IF NOT EXISTS movimientos_inventario (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(255) NOT NULL,
                tipo_movimiento VARCHAR(50) NOT NULL,
                cantidad INT NOT NULL,
                comentarios TEXT,
                fecha_movimiento DATETIME DEFAULT NOW(),
                usuario VARCHAR(255)
            )
        ''',
        'bom': '''
            CREATE TABLE IF NOT EXISTS bom (
                id INT AUTO_INCREMENT PRIMARY KEY,
                modelo VARCHAR(255) NOT NULL,
                numero_parte VARCHAR(255) NOT NULL,
                descripcion TEXT,
                cantidad INT DEFAULT 1,
                side VARCHAR(50),
                ubicacion VARCHAR(255),
                categoria VARCHAR(255),
                proveedor VARCHAR(255),
                fecha_registro DATETIME DEFAULT NOW(),
                UNIQUE KEY unique_bom (modelo, numero_parte, side)
            )
        ''',
        'configuracion': '''
            CREATE TABLE IF NOT EXISTS configuracion (
                id INT AUTO_INCREMENT PRIMARY KEY,
                clave VARCHAR(255) UNIQUE NOT NULL,
                valor TEXT,
                fecha_actualizacion DATETIME DEFAULT NOW()
            )
        '''
    }
    
    for table_name, create_sql in tables.items():
        try:
            execute_query(create_sql)
            print(f"✅ Tabla {table_name} creada/verificada")
        except Exception as e:
            print(f"❌ Error creando tabla {table_name}: {e}")

def get_connection():
    """Obtener conexión a MySQL"""
    if not MYSQL_AVAILABLE:
        return None
    from .config_mysql import get_mysql_connection
    return get_mysql_connection()

# === FUNCIONES DE USUARIOS ===

def crear_usuario(username, password_hash, area=''):
    """Crear usuario en MySQL"""
    try:
        query = "INSERT INTO usuarios_sistema (username, password_hash, departamento) VALUES (%s, %s, %s)"
        result = execute_query(query, (username, password_hash, area))
        return result > 0
    except Exception as e:
        print(f"Error creando usuario: {e}")
        return False

def obtener_usuario(username):
    """Obtener usuario por username"""
    try:
        query = "SELECT * FROM usuarios_sistema WHERE username = %s AND activo = 1"
        return execute_query(query, (username,), fetch='one')
    except Exception as e:
        print(f"Error obteniendo usuario: {e}")
        return None

def verificar_usuario(username, password_hash):
    """Verificar credenciales de usuario"""
    try:
        query = "SELECT * FROM usuarios_sistema WHERE username = %s AND password_hash = %s AND activo = 1"
        return execute_query(query, (username, password_hash), fetch='one')
    except Exception as e:
        print(f"Error verificando usuario: {e}")
        return None

# === FUNCIONES DE MATERIALES ===

def obtener_materiales():
    """Obtener lista de materiales desde MySQL"""
    try:
        query = "SELECT * FROM materiales ORDER BY numero_parte"
        return execute_query(query, fetch='all') or []
    except Exception as e:
        print(f"Error obteniendo materiales: {e}")
        return []

def guardar_material(data):
    """Guardar material en MySQL"""
    try:
        query = """
            INSERT INTO materiales (numero_parte, descripcion, categoria, ubicacion, 
                                  stock_minimo, stock_maximo, unidad_medida, proveedor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                descripcion = VALUES(descripcion),
                categoria = VALUES(categoria),
                ubicacion = VALUES(ubicacion),
                stock_minimo = VALUES(stock_minimo),
                stock_maximo = VALUES(stock_maximo),
                unidad_medida = VALUES(unidad_medida),
                proveedor = VALUES(proveedor)
        """
        
        params = (
            data.get('numero_parte'),
            data.get('descripcion'),
            data.get('categoria'),
            data.get('ubicacion'),
            data.get('stock_minimo', 0),
            data.get('stock_maximo', 0),
            data.get('unidad_medida'),
            data.get('proveedor')
        )
        
        result = execute_query(query, params)
        return result > 0
    except Exception as e:
        print(f"Error guardando material: {e}")
        return False

def obtener_material_por_numero(numero_parte):
    """Obtener material por número de parte"""
    try:
        query = "SELECT * FROM materiales WHERE numero_parte = %s"
        return execute_query(query, (numero_parte,), fetch='one')
    except Exception as e:
        print(f"Error obteniendo material: {e}")
        return None

# === FUNCIONES DE INVENTARIO ===

def obtener_inventario():
    """Obtener inventario actual desde MySQL"""
    try:
        query = """
            SELECT m.*, COALESCE(i.cantidad_actual, 0) as cantidad_actual, 
                   i.ultima_actualizacion
            FROM materiales m
            LEFT JOIN inventario i ON m.numero_parte = i.numero_parte
            ORDER BY m.numero_parte
        """
        return execute_query(query, fetch='all') or []
    except Exception as e:
        print(f"Error obteniendo inventario: {e}")
        return []

def actualizar_inventario(numero_parte, cantidad, tipo_movimiento='ajuste', comentarios='', usuario=''):
    """Actualizar inventario en MySQL"""
    try:
        # Actualizar inventario actual
        query_inventario = """
            INSERT INTO inventario (numero_parte, cantidad_actual, ultima_actualizacion)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                cantidad_actual = %s,
                ultima_actualizacion = NOW()
        """
        
        execute_query(query_inventario, (numero_parte, cantidad, cantidad))
        
        # Registrar movimiento
        query_movimiento = """
            INSERT INTO movimientos_inventario 
            (numero_parte, tipo_movimiento, cantidad, comentarios, fecha_movimiento, usuario)
            VALUES (%s, %s, %s, %s, NOW(), %s)
        """
        
        execute_query(query_movimiento, (numero_parte, tipo_movimiento, cantidad, comentarios, usuario))
        
        return True
    except Exception as e:
        print(f"Error actualizando inventario: {e}")
        return False

def obtener_movimientos_inventario(numero_parte=None, limit=100):
    """Obtener movimientos de inventario"""
    try:
        if numero_parte:
            query = """
                SELECT * FROM movimientos_inventario 
                WHERE numero_parte = %s 
                ORDER BY fecha_movimiento DESC 
                LIMIT %s
            """
            return execute_query(query, (numero_parte, limit), fetch='all') or []
        else:
            query = """
                SELECT * FROM movimientos_inventario 
                ORDER BY fecha_movimiento DESC 
                LIMIT %s
            """
            return execute_query(query, (limit,), fetch='all') or []
    except Exception as e:
        print(f"Error obteniendo movimientos: {e}")
        return []

# === FUNCIONES DE BOM ===

def obtener_bom_por_modelo(modelo):
    """Obtener BOM por modelo desde MySQL"""
    try:
        query = "SELECT * FROM bom WHERE modelo = %s ORDER BY numero_parte"
        return execute_query(query, (modelo,), fetch='all') or []
    except Exception as e:
        print(f"Error obteniendo BOM: {e}")
        return []

def guardar_bom_item(data):
    """Guardar item de BOM en MySQL"""
    try:
        query = """
            INSERT INTO bom (modelo, numero_parte, descripcion, cantidad, side, 
                           ubicacion, categoria, proveedor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                descripcion = VALUES(descripcion),
                cantidad = VALUES(cantidad),
                ubicacion = VALUES(ubicacion),
                categoria = VALUES(categoria),
                proveedor = VALUES(proveedor)
        """
        
        params = (
            data.get('modelo'),
            data.get('numero_parte'),
            data.get('descripcion'),
            data.get('cantidad', 1),
            data.get('side'),
            data.get('ubicacion'),
            data.get('categoria'),
            data.get('proveedor')
        )
        
        result = execute_query(query, params)
        return result > 0
    except Exception as e:
        print(f"Error guardando BOM item: {e}")
        return False

def obtener_modelos_bom():
    """Obtener lista de modelos en BOM"""
    try:
        query = "SELECT DISTINCT modelo FROM bom ORDER BY modelo"
        result = execute_query(query, fetch='all') or []
        # Devolver objetos con propiedad 'modelo' para compatibilidad con template
        return [{'modelo': row['modelo']} for row in result]
    except Exception as e:
        print(f"Error obteniendo modelos BOM: {e}")
        return []

def listar_bom_por_modelo(modelo):
    """Listar BOM por modelo específico o todos"""
    try:
        if modelo == 'todos':
            query = "SELECT * FROM bom ORDER BY modelo, numero_parte"
            resultados = execute_query(query, fetch='all') or []
        else:
            query = "SELECT * FROM bom WHERE modelo = %s ORDER BY numero_parte"
            resultados = execute_query(query, (modelo,), fetch='all') or []
        
        # Mapear nombres de columnas de la BD a nombres esperados por el frontend
        datos_mapeados = []
        for row in resultados:
            item_mapeado = {
                'id': row.get('id'),
                'modelo': row.get('modelo'),
                'codigoMaterial': row.get('codigo_material'),
                'numeroParte': row.get('numero_parte'),
                'side': row.get('side'),
                'tipoMaterial': row.get('tipo_material'),
                'classification': row.get('classification'),
                'especificacionMaterial': row.get('especificacion_material'),
                'vender': row.get('vender'),
                'cantidadTotal': row.get('cantidad_total'),
                'cantidadOriginal': row.get('cantidad_original'),
                'ubicacion': row.get('ubicacion'),
                'materialSustituto': row.get('material_sustituto'),
                'materialOriginal': row.get('material_original'),
                'registrador': row.get('registrador'),
                'fechaRegistro': row.get('fecha_registro')
            }
            datos_mapeados.append(item_mapeado)
        
        return datos_mapeados
        
    except Exception as e:
        print(f"Error listando BOM por modelo: {e}")
        return []

def insertar_bom_desde_dataframe(df, registrador):
    """Insertar datos de BOM desde un DataFrame de pandas"""
    try:
        insertados = 0
        omitidos = 0
        
        for index, row in df.iterrows():
            # Verificar que tenga al menos modelo y número de parte
            modelo = str(row.get('Modelo', '')).strip()
            numero_parte = str(row.get('Numero de parte', '') or row.get('Número de parte', '')).strip()
            
            if not modelo or not numero_parte:
                omitidos += 1
                continue
            
            # Preparar datos para insertar
            data = {
                'modelo': modelo,
                'numero_parte': numero_parte,
                'descripcion': str(row.get('Descripcion', '') or row.get('Descripción', '')).strip(),
                'cantidad': int(row.get('Cantidad', 1) or 1),
                'side': str(row.get('Side', '') or row.get('Lado', '')).strip(),
                'ubicacion': str(row.get('Ubicacion', '') or row.get('Ubicación', '')).strip(),
                'categoria': str(row.get('Categoria', '') or row.get('Categoría', '')).strip(),
                'proveedor': str(row.get('Proveedor', '')).strip()
            }
            
            # Insertar usando la función existente
            if guardar_bom_item(data):
                insertados += 1
            else:
                omitidos += 1
        
        return {
            'insertados': insertados,
            'omitidos': omitidos
        }
        
    except Exception as e:
        print(f"Error insertando BOM desde DataFrame: {e}")
        return {
            'insertados': 0,
            'omitidos': len(df) if df is not None else 0
        }

# === FUNCIONES DE CONFIGURACIÓN ===

def guardar_configuracion(clave, valor):
    """Guardar configuración en MySQL"""
    try:
        query = """
            INSERT INTO configuracion (clave, valor, fecha_actualizacion)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                valor = VALUES(valor),
                fecha_actualizacion = NOW()
        """
        
        # Convertir valor a JSON si es necesario
        if isinstance(valor, (dict, list)):
            valor = json.dumps(valor)
        
        result = execute_query(query, (clave, valor))
        return result > 0
    except Exception as e:
        print(f"Error guardando configuración: {e}")
        return False

def cargar_configuracion(clave, valor_por_defecto=None):
    """Cargar configuración desde MySQL"""
    try:
        query = "SELECT valor FROM configuracion WHERE clave = %s"
        result = execute_query(query, (clave,), fetch='one')
        
        if result:
            valor = result['valor']
            # Intentar parsear JSON
            try:
                return json.loads(valor)
            except:
                return valor
        
        return valor_por_defecto
    except Exception as e:
        print(f"Error cargando configuración: {e}")
        return valor_por_defecto

# === FUNCIONES DE MIGRACIÓN ===

def migrar_desde_sqlite(sqlite_db_path):
    """Migrar datos desde SQLite a MySQL"""
    try:
        import sqlite3
        
        # Conectar a SQLite
        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        print("🔄 Iniciando migración desde SQLite...")
        
        # Migrar usuarios
        try:
            sqlite_cursor.execute("SELECT * FROM usuarios")
            usuarios = sqlite_cursor.fetchall()
            for usuario in usuarios:
                crear_usuario(usuario['username'], usuario['password_hash'], usuario.get('area', ''))
            print(f"✅ Migrados {len(usuarios)} usuarios")
        except Exception as e:
            print(f"⚠️ Error migrando usuarios: {e}")
        
        # Migrar materiales
        try:
            sqlite_cursor.execute("SELECT * FROM materiales")
            materiales = sqlite_cursor.fetchall()
            for material in materiales:
                data = {
                    'numero_parte': material['numero_parte'],
                    'descripcion': material.get('descripcion'),
                    'categoria': material.get('categoria'),
                    'ubicacion': material.get('ubicacion'),
                    'stock_minimo': material.get('stock_minimo', 0),
                    'stock_maximo': material.get('stock_maximo', 0),
                    'unidad_medida': material.get('unidad_medida'),
                    'proveedor': material.get('proveedor')
                }
                guardar_material(data)
            print(f"✅ Migrados {len(materiales)} materiales")
        except Exception as e:
            print(f"⚠️ Error migrando materiales: {e}")
        
        # Migrar inventario
        try:
            sqlite_cursor.execute("SELECT * FROM inventario")
            inventarios = sqlite_cursor.fetchall()
            for inv in inventarios:
                actualizar_inventario(
                    inv['numero_parte'], 
                    inv.get('cantidad_actual', 0),
                    'migración',
                    'Migrado desde SQLite'
                )
            print(f"✅ Migrados {len(inventarios)} registros de inventario")
        except Exception as e:
            print(f"⚠️ Error migrando inventario: {e}")
        
        sqlite_conn.close()
        print("🎉 Migración completada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        return False

# === FUNCIONES DE PRUEBA ===

def test_mysql_functions():
    """Probar funciones de MySQL"""
    print("\n🧪 Probando funciones de MySQL...")
    
    try:
        # Probar conexión
        if test_connection():
            print("✅ Conexión MySQL OK")
        else:
            print("❌ Error en conexión MySQL")
            return False
        
        # Inicializar base de datos
        if init_db():
            print("✅ Inicialización MySQL OK")
        else:
            print("❌ Error en inicialización MySQL")
        
        print("🎉 Pruebas de MySQL completadas")
        return True
        
    except Exception as e:
        print(f"❌ Error en pruebas MySQL: {e}")
        return False

if __name__ == "__main__":
    test_mysql_functions()

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

