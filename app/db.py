import sqlite3
import os

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entrada_aereo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            forma_material TEXT,
            cliente TEXT,
            codigo_material TEXT,
            fecha_fabricacion TEXT,
            origen_material TEXT,
            cantidad_actual INTEGER,
            fecha_recibo TEXT,
            lote_material TEXT,
            codigo_recibido TEXT,
            numero_parte TEXT,
            propiedad TEXT
        )
    ''')
    
    # Tabla para materiales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materiales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_material TEXT UNIQUE,
            numero_parte TEXT,
            propiedad_material TEXT,
            classification TEXT,
            especificacion_material TEXT,
            unidad_empaque TEXT,
            ubicacion_material TEXT,
            vendedor TEXT,
            prohibido_sacar INTEGER DEFAULT 0,
            reparable INTEGER DEFAULT 0,
            nivel_msl TEXT,
            espesor_msl TEXT,
            fecha_registro TEXT
        )
    ''')
    
    # Tabla para control de material de almacén
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS control_material_almacen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            forma_material TEXT,
            cliente TEXT,
            codigo_material_original TEXT,
            codigo_material TEXT,
            material_importacion_local TEXT,
            fecha_recibo TEXT,
            fecha_fabricacion TEXT,
            cantidad_actual INTEGER,
            numero_lote_material TEXT,
            codigo_material_recibido TEXT,
            numero_parte TEXT,
            cantidad_estandarizada TEXT,
            codigo_material_final TEXT,
            propiedad_material TEXT,
            especificacion TEXT,
            material_importacion_local_final TEXT,
            estado_desecho INTEGER DEFAULT 0,
            ubicacion_salida TEXT,
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla para configuraciones de usuario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuraciones_usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            clave TEXT,
            valor TEXT,
            fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario, clave)
        )
    ''')
    
    conn.commit()
    
    # Migrar datos existentes si es necesario
    try:
        cursor.execute("PRAGMA table_info(materiales)")
        columns = cursor.fetchall()
        
        # Verificar si las columnas necesitan ser actualizadas
        prohibido_sacar_type = None
        reparable_type = None
        
        for column in columns:
            if column[1] == 'prohibido_sacar':
                prohibido_sacar_type = column[2]
            elif column[1] == 'reparable':
                reparable_type = column[2]
        
        # Si las columnas son TEXT, convertir a INTEGER
        if prohibido_sacar_type == 'TEXT':
            cursor.execute('''
                UPDATE materiales 
                SET prohibido_sacar = CASE 
                    WHEN prohibido_sacar = '1' OR prohibido_sacar = 'true' OR prohibido_sacar = 'True' THEN 1
                    ELSE 0
                END
            ''')
            
        if reparable_type == 'TEXT':
            cursor.execute('''
                UPDATE materiales 
                SET reparable = CASE 
                    WHEN reparable = '1' OR reparable = 'true' OR reparable = 'True' THEN 1
                    ELSE 0
                END
            ''')
            
        conn.commit()
        
    except Exception as e:
        print(f"Error durante la migración: {e}")
    
    conn.close()

def guardar_configuracion_usuario(usuario, clave, valor):
    """Guardar una configuración específica del usuario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Usar REPLACE para actualizar si existe o insertar si no existe
        cursor.execute('''
            INSERT OR REPLACE INTO configuraciones_usuario (usuario, clave, valor, fecha_actualizacion)
            VALUES (?, ?, ?, datetime('now'))
        ''', (usuario, clave, valor))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al guardar configuración: {e}")
        return False
    finally:
        conn.close()

def cargar_configuracion_usuario(usuario, clave, valor_por_defecto=''):
    """Cargar una configuración específica del usuario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT valor FROM configuraciones_usuario 
            WHERE usuario = ? AND clave = ?
        ''', (usuario, clave))
        resultado = cursor.fetchone()
        if resultado:
            return resultado['valor']
        else:
            return valor_por_defecto
    except Exception as e:
        print(f"Error al cargar configuración: {e}")
        return valor_por_defecto
    finally:
        conn.close()