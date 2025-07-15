import sqlite3
import os
import pandas as pd

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
    
    # Tabla para control de salida de material
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS control_material_salida (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_material_recibido TEXT,
            numero_lote TEXT,
            modelo TEXT,
            depto_salida TEXT,
            proceso_salida TEXT,
            cantidad_salida REAL,
            fecha_salida TEXT,
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (codigo_material_recibido) REFERENCES control_material_almacen(codigo_material_recibido)
        )
    ''')
    
    # Tabla para inventario general (unificado por número de parte)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventario_general (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_parte TEXT UNIQUE NOT NULL,
            codigo_material TEXT,
            propiedad_material TEXT,
            especificacion TEXT,
            cantidad_total REAL DEFAULT 0,
            fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla para BOM (Bill of Materials)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo TEXT NOT NULL,
            codigo_material TEXT,
            numero_parte TEXT,
            side TEXT,
            tipo_material TEXT,
            classification TEXT,
            especificacion_material TEXT,
            vender TEXT,
            cantidad_total REAL,
            cantidad_original REAL,
            ubicacion TEXT,
            material_sustituto TEXT,
            material_original TEXT,
            registrador TEXT,
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(modelo, numero_parte, side)
        )
    ''')
    
    conn.commit()
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

# ========== FUNCIONES PARA INVENTARIO GENERAL ==========

def actualizar_inventario_general_entrada(numero_parte, codigo_material, propiedad_material, especificacion, cantidad_entrada):
    """
    Actualizar el inventario general al registrar una entrada.
    Unifica por número de parte y suma las cantidades.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Verificar si ya existe el número de parte
        cursor.execute('''
            SELECT * FROM inventario_general WHERE numero_parte = ?
        ''', (numero_parte,))
        existente = cursor.fetchone()
        
        if existente:
            # Actualizar registro existente
            nueva_cantidad_entradas = existente['cantidad_entradas'] + cantidad_entrada
            nueva_cantidad_total = nueva_cantidad_entradas - existente['cantidad_salidas']
            
            cursor.execute('''
                UPDATE inventario_general 
                SET cantidad_entradas = ?,
                    cantidad_total = ?,
                    fecha_actualizacion = datetime('now')
                WHERE numero_parte = ?
            ''', (nueva_cantidad_entradas, nueva_cantidad_total, numero_parte))
            
            print(f"✅ Inventario actualizado para {numero_parte}: +{cantidad_entrada} (Total: {nueva_cantidad_total})")
        else:
            # Crear nuevo registro
            cursor.execute('''
                INSERT INTO inventario_general (
                    numero_parte, codigo_material, propiedad_material, especificacion,
                    cantidad_total, cantidad_entradas, cantidad_salidas
                ) VALUES (?, ?, ?, ?, ?, ?, 0)
            ''', (numero_parte, codigo_material, propiedad_material, especificacion, cantidad_entrada, cantidad_entrada))
            
            print(f"✅ Nuevo registro en inventario para {numero_parte}: {cantidad_entrada}")
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Error al actualizar inventario general (entrada): {e}")
        return False
    finally:
        conn.close()

def actualizar_inventario_general_salida(numero_parte, cantidad_salida):
    """
    Actualizar el inventario general al registrar una salida.
    Resta de la cantidad total del número de parte.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Buscar el registro existente
        cursor.execute('''
            SELECT * FROM inventario_general WHERE numero_parte = ?
        ''', (numero_parte,))
        existente = cursor.fetchone()
        
        if existente:
            # Actualizar registro existente
            nueva_cantidad_salidas = existente['cantidad_salidas'] + cantidad_salida
            nueva_cantidad_total = existente['cantidad_entradas'] - nueva_cantidad_salidas
            
            # Validar que no quede en negativo
            if nueva_cantidad_total < 0:
                print(f"⚠️ ADVERTENCIA: Inventario negativo para {numero_parte}: {nueva_cantidad_total}")
                # Podrías decidir si permitir negativos o no
            
            cursor.execute('''
                UPDATE inventario_general 
                SET cantidad_salidas = ?,
                    cantidad_total = ?,
                    fecha_actualizacion = datetime('now')
                WHERE numero_parte = ?
            ''', (nueva_cantidad_salidas, nueva_cantidad_total, numero_parte))
            
            print(f"✅ Inventario actualizado para {numero_parte}: -{cantidad_salida} (Total: {nueva_cantidad_total})")
            conn.commit()
            return True
        else:
            print(f"❌ ERROR: No existe registro en inventario para {numero_parte}")
            return False
        
    except Exception as e:
        print(f"❌ Error al actualizar inventario general (salida): {e}")
        return False
    finally:
        conn.close()

def obtener_inventario_general():
    """
    Obtener todo el inventario general (para uso futuro).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT * FROM inventario_general 
            ORDER BY numero_parte ASC
        ''')
        registros = cursor.fetchall()
        return [dict(registro) for registro in registros]
        
    except Exception as e:
        print(f"❌ Error al obtener inventario general: {e}")
        return []
    finally:
        conn.close()

def recalcular_inventario_general():
    """
    Función para recalcular todo el inventario general desde cero.
    Útil para sincronizar si hay inconsistencias.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        print("🔄 Recalculando inventario general...")
        
        # Limpiar tabla de inventario
        cursor.execute('DELETE FROM inventario_general')
        
        # Obtener todas las entradas agrupadas por número de parte
        cursor.execute('''
            SELECT 
                numero_parte,
                codigo_material,
                propiedad_material,
                especificacion,
                SUM(cantidad_actual) as total_entradas
            FROM control_material_almacen 
            WHERE numero_parte IS NOT NULL AND numero_parte != ''
            GROUP BY numero_parte
        ''')
        entradas = cursor.fetchall()
        
        # Insertar entradas en inventario general
        for entrada in entradas:
            cursor.execute('''
                INSERT INTO inventario_general (
                    numero_parte, codigo_material, propiedad_material, especificacion,
                    cantidad_entradas, cantidad_salidas, cantidad_total
                ) VALUES (?, ?, ?, ?, ?, 0, ?)
            ''', (
                entrada['numero_parte'],
                entrada['codigo_material'],
                entrada['propiedad_material'],
                entrada['especificacion'],
                entrada['total_entradas'],
                entrada['total_entradas']
            ))
        
        # Obtener todas las salidas agrupadas por número de parte
        cursor.execute('''
            SELECT 
                a.numero_parte,
                SUM(s.cantidad_salida) as total_salidas
            FROM control_material_salida s
            JOIN control_material_almacen a ON s.codigo_material_recibido = a.codigo_material_recibido
            WHERE a.numero_parte IS NOT NULL AND a.numero_parte != ''
            GROUP BY a.numero_parte
        ''')
        salidas = cursor.fetchall()
        
        # Actualizar salidas en inventario general
        for salida in salidas:
            cursor.execute('''
                UPDATE inventario_general 
                SET cantidad_salidas = ?,
                    cantidad_total = cantidad_entradas - ?,
                    fecha_actualizacion = datetime('now')
                WHERE numero_parte = ?
            ''', (salida['total_salidas'], salida['total_salidas'], salida['numero_parte']))
        
        conn.commit()
        print("✅ Inventario general recalculado exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al recalcular inventario general: {e}")
        return False
    finally:
        conn.close()

def get_bom(modelo):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bom WHERE modelo = ?", (modelo,))
    bom_data = cursor.fetchall()
    conn.close()
    return [dict(row) for row in bom_data]

def exportar_bom_a_dataframe():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM bom", conn)
    conn.close()
    return df

def insertar_bom_desde_dataframe(df, modelo, registrador):
    conn = get_db_connection()
    # Renombrar columnas del DataFrame para que coincidan con la BD
    column_mapping = {
        'Código de material': 'codigo_material',
        'Número de parte': 'numero_parte',
        'Side': 'side',
        'Tipo de material': 'tipo_material',
        'Classification': 'classification',
        'Especificación de material': 'especificacion_material',
        'Vender': 'vender',
        'Cantidad total': 'cantidad_total',
        'Cantidad original': 'cantidad_original',
        'Ubicación': 'ubicacion',
        'Material sustituto': 'material_sustituto',
        'Material original': 'material_original'
    }
    df = df.rename(columns=column_mapping)

    # Asegurarse de que todas las columnas esperadas existan
    expected_cols = list(column_mapping.values())
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None # O un valor por defecto apropiado

    with conn:
        for _, row in df.iterrows():
            # Usar .get() para evitar errores si una columna no existe en la fila
            numero_parte = row.get('numero_parte')
            side = row.get('side')

            if not numero_parte:
                continue # O manejar el error como prefieras

            # Usar INSERT OR IGNORE y luego UPDATE para manejar conflictos
            conn.execute('''
                INSERT OR IGNORE INTO bom (modelo, numero_parte, side, registrador)
                VALUES (?, ?, ?, ?)
            ''', (modelo, numero_parte, side, registrador))

            # Actualizar la fila con el resto de los datos
            conn.execute('''
                UPDATE bom SET
                    codigo_material = ?, tipo_material = ?, classification = ?, 
                    especificacion_material = ?, vender = ?, cantidad_total = ?, 
                    cantidad_original = ?, ubicacion = ?, material_sustituto = ?, 
                    material_original = ?, fecha_registro = CURRENT_TIMESTAMP
                WHERE modelo = ? AND numero_parte = ? AND (side = ? OR (side IS NULL AND ? IS NULL))
            ''', (
                row.get('codigo_material'), row.get('tipo_material'), row.get('classification'),
                row.get('especificacion_material'), row.get('vender'), row.get('cantidad_total'),
                row.get('cantidad_original'), row.get('ubicacion'), row.get('material_sustituto'),
                row.get('material_original'), modelo, numero_parte, side, side
            ))