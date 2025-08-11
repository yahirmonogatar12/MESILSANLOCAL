"""
Modelos de base de datos para el sistema PO → WO
Basado en la especificación del agente de IA
"""

from .db_mysql import execute_query
from .config_mysql import get_db_connection
from datetime import datetime, date
import re

def crear_tablas_po_wo():
    """Crear las tablas necesarias para el sistema PO → WO"""
    try:
        # Tabla embarques (PO)
        query_embarques = """
        CREATE TABLE IF NOT EXISTS embarques (
            id INT AUTO_INCREMENT PRIMARY KEY,
            codigo_po VARCHAR(32) UNIQUE NOT NULL,
            cliente VARCHAR(64),
            fecha_registro DATE,
            estado ENUM('PLAN','PREPARACION','EMBARCADO','EN_TRANSITO','ENTREGADO') DEFAULT 'PLAN',
            modificado DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            usuario_creacion VARCHAR(64),
            nombre_po VARCHAR(100),
            modelo VARCHAR(64),
            proveedor VARCHAR(64),
            total_cantidad_entregada INT DEFAULT 0,
            codigo_entrega VARCHAR(32),
            fecha_entrega DATE,
            cantidad_entregada INT DEFAULT 0,
            INDEX idx_codigo_po (codigo_po),
            INDEX idx_estado (estado),
            INDEX idx_fecha_registro (fecha_registro)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        # Tabla work_orders (WO)
        query_work_orders = """
        CREATE TABLE IF NOT EXISTS work_orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            codigo_wo VARCHAR(32) UNIQUE NOT NULL,
            codigo_po VARCHAR(32) NOT NULL,
            modelo VARCHAR(64),
            cantidad_planeada INT CHECK (cantidad_planeada > 0),
            fecha_operacion DATE,
            modificador VARCHAR(64),
            fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            estado ENUM('CREADA','PLANIFICADA','EN_PRODUCCION','CERRADA') DEFAULT 'CREADA',
            usuario_creacion VARCHAR(64),
            INDEX idx_codigo_wo (codigo_wo),
            INDEX idx_codigo_po (codigo_po),
            INDEX idx_estado (estado),
            INDEX idx_fecha_operacion (fecha_operacion),
            FOREIGN KEY (codigo_po) REFERENCES embarques(codigo_po) ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        # Ejecutar creación de tablas
        execute_query(query_embarques)
        print("✅ Tabla embarques creada/verificada")
        
        execute_query(query_work_orders)
        print("✅ Tabla work_orders creada/verificada")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas PO → WO: {e}")
        return False

def validar_codigo_po(codigo_po):
    """Validar formato del código PO: PO-YYMMDD-####"""
    if not codigo_po:
        return False, "Código PO no puede estar vacío"
    
    patron = r'^PO-\d{6}-\d{4}$'
    if not re.match(patron, codigo_po):
        return False, "Formato inválido. Debe ser PO-YYMMDD-####"
    
    return True, "Válido"

def validar_codigo_wo(codigo_wo):
    """Validar formato del código WO: WO-YYMMDD-####"""
    if not codigo_wo:
        return False, "Código WO no puede estar vacío"
    
    patron = r'^WO-\d{6}-\d{4}$'
    if not re.match(patron, codigo_wo):
        return False, "Formato inválido. Debe ser WO-YYMMDD-####"
    
    return True, "Válido"

def generar_codigo_po():
    """Generar código PO único: PO-YYMMDD-####"""
    try:
        fecha_actual = datetime.now()
        fecha_str = fecha_actual.strftime("%y%m%d")
        
        # Obtener el último número secuencial del día
        query = """
        SELECT codigo_po FROM embarques 
        WHERE codigo_po LIKE %s 
        ORDER BY codigo_po DESC 
        LIMIT 1
        """
        
        patron = f"PO-{fecha_str}-%"
        resultado = execute_query(query, (patron,), fetch='one')
        
        if resultado and resultado.get('codigo_po'):
            ultimo_codigo = resultado['codigo_po']
            # Extraer el número secuencial (últimos 4 dígitos)
            secuencial = int(ultimo_codigo[-4:]) + 1
        else:
            secuencial = 1
        
        # Formatear con ceros a la izquierda
        codigo_po = f"PO-{fecha_str}-{secuencial:04d}"
        
        return codigo_po
        
    except Exception as e:
        print(f"❌ Error generando código PO: {e}")
        return None

def generar_codigo_wo():
    """Generar código WO único: WO-YYMMDD-####"""
    try:
        fecha_actual = datetime.now()
        fecha_str = fecha_actual.strftime("%y%m%d")
        
        # Obtener el último número secuencial del día
        query = """
        SELECT codigo_wo FROM work_orders 
        WHERE codigo_wo LIKE %s 
        ORDER BY codigo_wo DESC 
        LIMIT 1
        """
        
        patron = f"WO-{fecha_str}-%"
        resultado = execute_query(query, (patron,), fetch='one')
        
        if resultado and resultado.get('codigo_wo'):
            ultimo_codigo = resultado['codigo_wo']
            # Extraer el número secuencial (últimos 4 dígitos)
            secuencial = int(ultimo_codigo[-4:]) + 1
        else:
            secuencial = 1
        
        # Formatear con ceros a la izquierda
        codigo_wo = f"WO-{fecha_str}-{secuencial:04d}"
        
        return codigo_wo
        
    except Exception as e:
        print(f"❌ Error generando código WO: {e}")
        return None

def verificar_po_existe(codigo_po):
    """Verificar si una PO ya existe"""
    try:
        query = "SELECT id FROM embarques WHERE codigo_po = %s"
        resultado = execute_query(query, (codigo_po,), fetch='one')
        return resultado is not None
    except Exception as e:
        print(f"❌ Error verificando existencia de PO: {e}")
        return False

def verificar_wo_existe(codigo_wo):
    """Verificar si una WO ya existe"""
    try:
        query = "SELECT id FROM work_orders WHERE codigo_wo = %s"
        resultado = execute_query(query, (codigo_wo,), fetch='one')
        return resultado is not None
    except Exception as e:
        print(f"❌ Error verificando existencia de WO: {e}")
        return False

def obtener_po_por_codigo(codigo_po):
    """Obtener información completa de una PO por código"""
    try:
        query = """
        SELECT id, codigo_po, cliente, fecha_registro, estado, modificado, usuario_creacion,
               nombre_po, modelo, proveedor, total_cantidad_entregada, 
               codigo_entrega, fecha_entrega, cantidad_entregada
        FROM embarques 
        WHERE codigo_po = %s
        """
        resultado = execute_query(query, (codigo_po,), fetch='one')
        
        if resultado:
            return {
                'id': resultado['id'],
                'codigo_po': resultado['codigo_po'],
                'cliente': resultado['cliente'],
                'fecha_registro': resultado['fecha_registro'].isoformat() if resultado['fecha_registro'] else None,
                'estado': resultado['estado'],
                'modificado': resultado['modificado'].isoformat() if resultado['modificado'] else None,
                'usuario_creacion': resultado['usuario_creacion'],
                'nombre_po': resultado['nombre_po'],
                'modelo': resultado['modelo'],
                'proveedor': resultado['proveedor'],
                'total_cantidad_entregada': resultado['total_cantidad_entregada'],
                'codigo_entrega': resultado['codigo_entrega'],
                'fecha_entrega': resultado['fecha_entrega'].isoformat() if resultado['fecha_entrega'] else None,
                'cantidad_entregada': resultado['cantidad_entregada']
            }
        return None
        
    except Exception as e:
        print(f"❌ Error obteniendo PO por código: {e}")
        return None

def obtener_wo_por_codigo(codigo_wo):
    """Obtener información completa de una WO por código"""
    try:
        query = """
        SELECT id, codigo_wo, codigo_po, modelo, cantidad_planeada, 
               fecha_operacion, modificador, fecha_modificacion, estado, usuario_creacion
        FROM work_orders 
        WHERE codigo_wo = %s
        """
        resultado = execute_query(query, (codigo_wo,), fetch='one')
        
        if resultado:
            return {
                'id': resultado['id'],
                'codigo_wo': resultado['codigo_wo'],
                'codigo_po': resultado['codigo_po'],
                'modelo': resultado['modelo'],
                'cantidad_planeada': resultado['cantidad_planeada'],
                'fecha_operacion': resultado['fecha_operacion'].isoformat() if resultado['fecha_operacion'] else None,
                'modificador': resultado['modificador'],
                'fecha_modificacion': resultado['fecha_modificacion'].isoformat() if resultado['fecha_modificacion'] else None,
                'estado': resultado['estado'],
                'usuario_creacion': resultado['usuario_creacion']
            }
        return None
        
    except Exception as e:
        print(f"❌ Error obteniendo WO por código: {e}")
        return None

def listar_pos_por_estado(estado=None):
    """Listar POs filtradas por estado"""
    try:
        if estado:
            query = """
            SELECT codigo_po, cliente, fecha_registro, estado, modificado, usuario_creacion,
                   nombre_po, modelo, proveedor, total_cantidad_entregada, 
                   codigo_entrega, fecha_entrega, cantidad_entregada
            FROM embarques 
            WHERE estado = %s
            ORDER BY fecha_registro DESC, modificado DESC
            """
            resultados = execute_query(query, (estado,), fetch='all')
        else:
            query = """
            SELECT codigo_po, cliente, fecha_registro, estado, modificado, usuario_creacion,
                   nombre_po, modelo, proveedor, total_cantidad_entregada, 
                   codigo_entrega, fecha_entrega, cantidad_entregada
            FROM embarques 
            ORDER BY fecha_registro DESC, modificado DESC
            """
            resultados = execute_query(query, fetch='all')
        
        pos = []
        for row in resultados:
            pos.append({
                'codigo_po': row['codigo_po'],
                'cliente': row['cliente'],
                'fecha_registro': row['fecha_registro'].isoformat() if row['fecha_registro'] else None,
                'estado': row['estado'],
                'modificado': row['modificado'].isoformat() if row['modificado'] else None,
                'usuario_creacion': row['usuario_creacion'],
                'nombre_po': row['nombre_po'],
                'modelo': row['modelo'],
                'proveedor': row['proveedor'],
                'total_cantidad_entregada': row['total_cantidad_entregada'],
                'codigo_entrega': row['codigo_entrega'],
                'fecha_entrega': row['fecha_entrega'].isoformat() if row['fecha_entrega'] else None,
                'cantidad_entregada': row['cantidad_entregada']
            })
        
        return pos
        
    except Exception as e:
        print(f"❌ Error listando POs: {e}")
        return []

def listar_wos_por_po(codigo_po=None):
    """Listar WOs filtradas por PO"""
    try:
        if codigo_po:
            query = """
            SELECT codigo_wo, codigo_po, modelo, cantidad_planeada, 
                   fecha_operacion, modificador, fecha_modificacion, estado, usuario_creacion
            FROM work_orders 
            WHERE codigo_po = %s
            ORDER BY fecha_operacion DESC, fecha_modificacion DESC
            """
            resultados = execute_query(query, (codigo_po,), fetch='all')
        else:
            query = """
            SELECT codigo_wo, codigo_po, modelo, cantidad_planeada, 
                   fecha_operacion, modificador, fecha_modificacion, estado, usuario_creacion
            FROM work_orders 
            ORDER BY fecha_operacion DESC, fecha_modificacion DESC
            """
            resultados = execute_query(query, fetch='all')
        
        wos = []
        for row in resultados:
            wos.append({
                'codigo_wo': row['codigo_wo'],
                'codigo_po': row['codigo_po'],
                'modelo': row['modelo'],
                'cantidad_planeada': row['cantidad_planeada'],
                'fecha_operacion': row['fecha_operacion'].isoformat() if row['fecha_operacion'] else None,
                'modificador': row['modificador'],
                'fecha_modificacion': row['fecha_modificacion'].isoformat() if row['fecha_modificacion'] else None,
                'estado': row['estado'],
                'usuario_creacion': row['usuario_creacion']
            })
        
        return wos
        
    except Exception as e:
        print(f"❌ Error listando WOs: {e}")
        return []

def listar_wos(fecha_desde=None, fecha_hasta=None):
    """Listar todas las Work Orders con filtros opcionales de fecha"""
    try:
        base_query = """
        SELECT codigo_wo, codigo_po, modelo, cantidad_planeada, 
               fecha_operacion, modificador, fecha_modificacion, estado, usuario_creacion
        FROM work_orders 
        """
        
        params = []
        where_conditions = []
        
        if fecha_desde:
            where_conditions.append("fecha_operacion >= %s")
            params.append(fecha_desde)
            
        if fecha_hasta:
            where_conditions.append("fecha_operacion <= %s")
            params.append(fecha_hasta)
        
        if where_conditions:
            query = base_query + "WHERE " + " AND ".join(where_conditions) + " ORDER BY fecha_operacion DESC, fecha_modificacion DESC"
        else:
            query = base_query + "ORDER BY fecha_operacion DESC, fecha_modificacion DESC"
        
        resultados = execute_query(query, params, fetch='all')
        
        wos = []
        for row in resultados:
            wos.append({
                'codigo_wo': row['codigo_wo'],
                'codigo_po': row['codigo_po'],
                'modelo': row['modelo'],
                'cantidad_planeada': row['cantidad_planeada'],
                'fecha_operacion': row['fecha_operacion'].isoformat() if row['fecha_operacion'] else None,
                'modificador': row['modificador'],
                'fecha_modificacion': row['fecha_modificacion'].isoformat() if row['fecha_modificacion'] else None,
                'estado': row['estado'],
                'usuario_creacion': row['usuario_creacion']
            })
        
        return wos
        
    except Exception as e:
        print(f"❌ Error listando WOs: {e}")
        return []

def obtener_modelos_unicos_bom():
    """Obtener modelos únicos de la tabla BOM para dropdown"""
    try:
        query = """
        SELECT DISTINCT modelo 
        FROM bom 
        WHERE modelo IS NOT NULL AND modelo != '' 
        ORDER BY modelo ASC
        """
        resultados = execute_query(query, fetch='all')
        
        modelos = []
        for row in resultados:
            if row['modelo']:  # Verificar que no sea None o vacío
                modelos.append(row['modelo'])
        
        return modelos
        
    except Exception as e:
        print(f"❌ Error obteniendo modelos de BOM: {e}")
        return []

def migrar_tabla_embarques():
    """Migrar tabla embarques para agregar nuevos campos"""
    try:
        # Lista de nuevas columnas a agregar (sin IF NOT EXISTS que no es compatible con MySQL)
        nuevas_columnas = [
            ("nombre_po", "ADD COLUMN nombre_po VARCHAR(100)"),
            ("modelo", "ADD COLUMN modelo VARCHAR(64)"),
            ("proveedor", "ADD COLUMN proveedor VARCHAR(64)"),
            ("total_cantidad_entregada", "ADD COLUMN total_cantidad_entregada INT DEFAULT 0"),
            ("codigo_entrega", "ADD COLUMN codigo_entrega VARCHAR(32)"),
            ("fecha_entrega", "ADD COLUMN fecha_entrega DATE"),
            ("cantidad_entregada", "ADD COLUMN cantidad_entregada INT DEFAULT 0")
        ]
        
        # Verificar qué columnas ya existen
        check_query = "SHOW COLUMNS FROM embarques"
        columnas_existentes = execute_query(check_query, fetch='all')
        nombres_existentes = [col['Field'] for col in columnas_existentes]
        
        for nombre_columna, sql_comando in nuevas_columnas:
            if nombre_columna not in nombres_existentes:
                try:
                    query = f"ALTER TABLE embarques {sql_comando}"
                    execute_query(query)
                    print(f"✅ Columna agregada: {nombre_columna}")
                except Exception as e:
                    print(f"⚠️ Error agregando columna {nombre_columna}: {e}")
            else:
                print(f"ℹ️ Columna ya existe: {nombre_columna}")
        
        print("🎉 Migración de tabla embarques completada")
        
    except Exception as e:
        print(f"❌ Error migrando tabla embarques: {e}")

def migrar_tabla_work_orders():
    """Migrar tabla work_orders para agregar nuevos campos"""
    try:
        # Lista de nuevas columnas a agregar
        nuevas_columnas = [
            ("orden_proceso", "ADD COLUMN orden_proceso VARCHAR(32) DEFAULT 'NORMAL'"),
            ("nombre_modelo", "ADD COLUMN nombre_modelo VARCHAR(64)"),
            ("codigo_modelo", "ADD COLUMN codigo_modelo VARCHAR(64)")
        ]
        
        # Verificar qué columnas ya existen
        check_query = "SHOW COLUMNS FROM work_orders"
        columnas_existentes = execute_query(check_query, fetch='all')
        nombres_existentes = [col['Field'] for col in columnas_existentes]
        
        for nombre_columna, sql_comando in nuevas_columnas:
            if nombre_columna not in nombres_existentes:
                try:
                    query = f"ALTER TABLE work_orders {sql_comando}"
                    execute_query(query)
                    print(f"✅ Columna WO agregada: {nombre_columna}")
                except Exception as e:
                    print(f"⚠️ Error agregando columna WO {nombre_columna}: {e}")
            else:
                print(f"ℹ️ Columna WO ya existe: {nombre_columna}")
        
        print("🎉 Migración de tabla work_orders completada")
        
    except Exception as e:
        print(f"❌ Error migrando tabla work_orders: {e}")

# Inicializar tablas al importar el módulo
try:
    crear_tablas_po_wo()
    migrar_tabla_embarques()  # Migrar campos nuevos PO
    migrar_tabla_work_orders()  # Migrar campos nuevos WO
    print("🎯 Modelos PO → WO inicializados correctamente")
except Exception as e:
    print(f"❌ Error inicializando modelos PO → WO: {e}")
