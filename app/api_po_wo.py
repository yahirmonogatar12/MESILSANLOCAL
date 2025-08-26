"""
API Routes para el sistema PO → WO
Endpoints REST para embarques (PO) y work_orders (WO)
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, date
import re
import functools
from app.db_mysql import execute_query

# Crear blueprint para las rutas API
api_po_wo = Blueprint('api_po_wo', __name__, url_prefix='/api')


def validar_fecha(fecha_str):
    """Validar formato de fecha YYYY-MM-DD"""
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False


def validar_codigo_po(codigo):
    """Validar formato PO-YYMMDD-####"""
    patron = r'^PO-\d{6}-\d{4}$'
    return bool(re.match(patron, codigo))


def validar_codigo_wo(codigo):
    """Validar formato WO-YYMMDD-####"""
    patron = r'^WO-\d{6}-\d{4}$'
    return bool(re.match(patron, codigo))


def generar_codigo_wo():
    """Generar código WO automático"""
    fecha_actual = datetime.now()
    fecha_str = fecha_actual.strftime('%y%m%d')
    
    # Buscar el último número de secuencia para hoy
    query = "SELECT codigo_wo FROM work_orders WHERE codigo_wo LIKE %s ORDER BY codigo_wo DESC LIMIT 1"
    resultado = execute_query(query, (f'WO-{fecha_str}-%',), fetch='one')
    
    if resultado:
        ultimo_codigo = resultado['codigo_wo']
        ultimo_numero = int(ultimo_codigo.split('-')[-1])
        nuevo_numero = ultimo_numero + 1
    else:
        nuevo_numero = 1
    
    return f"WO-{fecha_str}-{nuevo_numero:04d}"


def manejo_errores(func):
    """Decorator para manejo centralizado de errores"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Error en {func.__name__}: {e}")
            return jsonify({
                "ok": False, 
                "code": "INTERNAL_ERROR", 
                "message": "Error interno del servidor"
            }), 500
    return wrapper


@api_po_wo.route('/work_orders', methods=['POST'])
@manejo_errores
def crear_wo():
    """
    POST /api/work_orders
    Crear nueva Work Order (WO)
    """
    try:
        data = request.get_json(force=True)
        
        # Validaciones
        codigo_wo = data.get('codigo_wo', '').strip()
        modelo = data.get('modelo', '').strip()
        codigo_po = data.get('codigo_po', '').strip()
        fecha_operacion_str = data.get('fecha_operacion', '')
        cantidad_planeada = data.get('cantidad_planeada', 0)
        modificador = data.get('usuario_creador', 'Usuario no identificado').strip()
        
        # Generar código WO si no se proporciona
        if not codigo_wo:
            codigo_wo = generar_codigo_wo()
        elif not validar_codigo_wo(codigo_wo):
            return jsonify({
                "ok": False, 
                "code": "VALIDATION_ERROR", 
                "field": "codigo_wo",
                "message": "Formato de código WO inválido (debe ser WO-YYMMDD-####)"
            }), 400
        
        # Validar modelo
        if not modelo:
            return jsonify({
                "ok": False, 
                "code": "VALIDATION_ERROR", 
                "field": "modelo",
                "message": "Modelo es requerido"
            }), 400
        
        # Validar fecha
        fecha_operacion = None
        if fecha_operacion_str:
            if not validar_fecha(fecha_operacion_str):
                return jsonify({
                    "ok": False, 
                    "code": "VALIDATION_ERROR", 
                    "field": "fecha_operacion",
                    "message": "Formato de fecha inválido (debe ser YYYY-MM-DD)"
                }), 400
            fecha_operacion = fecha_operacion_str
        
        # Validar cantidad
        try:
            cantidad_planeada = int(cantidad_planeada)
            if cantidad_planeada <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({
                "ok": False, 
                "code": "VALIDATION_ERROR", 
                "field": "cantidad_planeada",
                "message": "Cantidad planeada debe ser un número entero positivo"
            }), 400
        
        # Verificar si ya existe el código WO
        query_check = "SELECT id FROM work_orders WHERE codigo_wo = %s"
        existe = execute_query(query_check, (codigo_wo,), fetch='one')
        if existe:
            return jsonify({
                "ok": False, 
                "code": "DUPLICATE_WO",
                "message": f"Ya existe una WO con código {codigo_wo}"
            }), 409
        
        # Crear work order
        query_insert = """
            INSERT INTO work_orders (codigo_wo, modelo, codigo_po, fecha_operacion, cantidad_planeada, estado, fecha_modificacion, modificador)
            VALUES (%s, %s, %s, %s, %s, 'CREADA', NOW(), %s)
        """
        
        execute_query(query_insert, (codigo_wo, modelo, codigo_po, fecha_operacion, cantidad_planeada, modificador))
        
        print(f"✅ WO creada: {codigo_wo}")
        return jsonify({
            "ok": True, 
            "codigo_wo": codigo_wo,
            "message": "Work Order creada exitosamente"
        }), 201
        
    except Exception as e:
        print(f"❌ Error creando WO: {e}")
        return jsonify({
            "ok": False, 
            "code": "INTERNAL_ERROR", 
            "message": "Error interno del servidor"
        }), 500


@api_po_wo.route('/generar_codigo_wo', methods=['GET'])
@manejo_errores
def generar_codigo_wo_endpoint():
    """
    GET /api/generar_codigo_wo
    Generar código WO automático
    """
    codigo = generar_codigo_wo()
    return jsonify({"ok": True, "codigo_wo": codigo})


@api_po_wo.route('/work_orders', methods=['GET'])
@manejo_errores
def listar_wos():
    """
    GET /api/work_orders
    Listar Work Orders con filtros opcionales
    Por defecto solo muestra WO con estado 'CREADA' (excluye 'PLANIFICADA')
    """
    # Filtros opcionales
    estado = request.args.get('estado')
    codigo_wo = request.args.get('codigo_wo')
    modelo = request.args.get('modelo')
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    incluir_planificadas = request.args.get('incluir_planificadas', 'false').lower() == 'true'
    
    # Construir query
    query = "SELECT * FROM work_orders WHERE 1=1"
    params = []
    
    # Por defecto, excluir WO planificadas a menos que se solicite explícitamente
    if not incluir_planificadas and not estado:
        query += " AND estado = 'CREADA'"
    elif estado:
        query += " AND estado = %s"
        params.append(estado)
    
    if codigo_wo:
        query += " AND codigo_wo = %s"
        params.append(codigo_wo)
    
    if modelo:
        query += " AND modelo LIKE %s"
        params.append(f"%{modelo}%")
    
    if fecha_desde:
        query += " AND fecha_operacion >= %s"
        params.append(fecha_desde)
    
    if fecha_hasta:
        query += " AND fecha_operacion <= %s"
        params.append(fecha_hasta)
    
    # Ordenar por fecha de modificación descendente
    query += " ORDER BY fecha_modificacion DESC"
    
    work_orders = execute_query(query, params, fetch='all') or []
    
    print(f"📋 Listando {len(work_orders)} WOs (estado filtrado: {estado or 'CREADA por defecto'})")
    return jsonify({"ok": True, "work_orders": work_orders})


@api_po_wo.route('/wo/listar', methods=['GET'])
@manejo_errores
def listar_wos_alternativo():
    """
    GET /api/wo/listar
    Ruta alternativa para compatibilidad con el frontend
    Por defecto solo muestra WO con estado 'CREADA' (excluye 'PLANIFICADA')
    """
    # Filtros opcionales
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')
    estado = request.args.get('estado')
    codigo_wo = request.args.get('codigo_wo')
    modelo = request.args.get('modelo')
    incluir_planificadas = request.args.get('incluir_planificadas', 'false').lower() == 'true'
    
    # Construir query
    query = "SELECT * FROM work_orders WHERE 1=1"
    params = []
    
    if fecha_desde:
        query += " AND fecha_operacion >= %s"
        params.append(fecha_desde)
    
    if fecha_hasta:
        query += " AND fecha_operacion <= %s"
        params.append(fecha_hasta)
    
    # Por defecto, excluir WO planificadas a menos que se solicite explícitamente
    if not incluir_planificadas and not estado:
        query += " AND estado = 'CREADA'"
    elif estado:
        query += " AND estado = %s"
        params.append(estado)
    
    if codigo_wo:
        query += " AND codigo_wo = %s"
        params.append(codigo_wo)
    
    if modelo:
        query += " AND modelo LIKE %s"
        params.append(f"%{modelo}%")
    
    # Ordenar por fecha de operación y modificación descendente
    query += " ORDER BY fecha_operacion DESC, fecha_modificacion DESC"
    
    try:
        work_orders = execute_query(query, params, fetch='all') or []
        
        # Formatear fechas para el frontend
        for wo in work_orders:
            if wo.get('fecha_operacion'):
                if hasattr(wo['fecha_operacion'], 'isoformat'):
                    wo['fecha_operacion'] = wo['fecha_operacion'].isoformat()
            if wo.get('fecha_modificacion'):
                if hasattr(wo['fecha_modificacion'], 'isoformat'):
                    wo['fecha_modificacion'] = wo['fecha_modificacion'].isoformat()
        
        print(f"📋 Listando {len(work_orders)} WOs (ruta alternativa - estado filtrado: {estado or 'CREADA por defecto'})")
        return jsonify({"success": True, "data": work_orders})
        
    except Exception as e:
        print(f"❌ Error listando WOs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_po_wo.route('/wo/<codigo>/estado', methods=['PUT'])
@manejo_errores
def actualizar_estado_wo(codigo):
    """
    PUT /api/wo/{codigo}/estado
    Actualizar estado de una Work Order
    """
    try:
        data = request.get_json(force=True)
        nuevo_estado = data.get('estado', '').strip().upper()
        modificador = data.get('modificador', 'Sistema').strip()
        
        # Validar estado
        estados_validos = ['CREADA', 'PLANIFICADA', 'EN_PRODUCCION', 'CERRADA']
        if nuevo_estado not in estados_validos:
            return jsonify({
                "ok": False,
                "code": "VALIDATION_ERROR",
                "message": f"Estado inválido. Estados válidos: {', '.join(estados_validos)}"
            }), 400
        
        # Verificar que la WO existe
        query_check = "SELECT id, estado FROM work_orders WHERE codigo_wo = %s"
        wo_actual = execute_query(query_check, (codigo,), fetch='one')
        
        if not wo_actual:
            return jsonify({
                "ok": False,
                "code": "NOT_FOUND",
                "message": f"No se encontró la WO con código {codigo}"
            }), 404
        
        # Actualizar estado
        query_update = """
            UPDATE work_orders 
            SET estado = %s, modificador = %s, fecha_modificacion = NOW()
            WHERE codigo_wo = %s
        """
        
        execute_query(query_update, (nuevo_estado, modificador, codigo))
        
        print(f"✅ Estado de WO {codigo} actualizado de {wo_actual['estado']} a {nuevo_estado}")
        return jsonify({
            "ok": True,
            "message": f"Estado de WO {codigo} actualizado a {nuevo_estado}",
            "estado_anterior": wo_actual['estado'],
            "estado_nuevo": nuevo_estado
        })
        
    except Exception as e:
        print(f"❌ Error actualizando estado de WO {codigo}: {e}")
        return jsonify({
            "ok": False,
            "code": "INTERNAL_ERROR",
            "message": "Error interno del servidor"
        }), 500


@api_po_wo.route('/wo/actualizar-po', methods=['POST'])
@manejo_errores
def actualizar_po_wo():
    """
    POST /api/wo/actualizar-po
    Actualizar código PO de una Work Order
    """
    try:
        data = request.get_json(force=True)
        codigo_wo = data.get('codigo_wo', '').strip()
        nuevo_codigo_po = data.get('codigo_po', '').strip() or 'SIN-PO'
        
        # Validar que se proporcione el código WO
        if not codigo_wo:
            return jsonify({
                "success": False,
                "error": "Código WO es requerido"
            }), 400
        
        # Verificar que la WO existe
        query_check = "SELECT id, codigo_po FROM work_orders WHERE codigo_wo = %s"
        wo_actual = execute_query(query_check, (codigo_wo,), fetch='one')
        
        if not wo_actual:
            return jsonify({
                "success": False,
                "error": f"No se encontró la WO con código {codigo_wo}"
            }), 404
        
        # Actualizar código PO
        query_update = """
            UPDATE work_orders 
            SET codigo_po = %s, fecha_modificacion = NOW()
            WHERE codigo_wo = %s
        """
        
        execute_query(query_update, (nuevo_codigo_po, codigo_wo))
        
        print(f"✅ PO actualizado: WO {codigo_wo} -> PO {nuevo_codigo_po}")
        return jsonify({
            "success": True,
            "message": f"Código PO actualizado exitosamente",
            "codigo_wo": codigo_wo,
            "codigo_po_anterior": wo_actual['codigo_po'],
            "codigo_po_nuevo": nuevo_codigo_po
        })
        
    except Exception as e:
        print(f"❌ Error actualizando PO de WO: {e}")
        return jsonify({
            "success": False,
            "error": "Error interno del servidor"
        }), 500


@api_po_wo.route('/wo/actualizar', methods=['POST'])
@manejo_errores
def actualizar_wo_completa():
    """
    POST /api/wo/actualizar
    Actualizar Work Order completa (modelo, cantidad, PO)
    """
    try:
        data = request.get_json(force=True)
        codigo_wo = data.get('codigo_wo', '').strip()
        modelo = data.get('modelo', '').strip()
        cantidad_planeada = data.get('cantidad_planeada', 0)
        codigo_po = data.get('codigo_po', '').strip() or 'SIN-PO'
        
        # Validaciones
        if not codigo_wo:
            return jsonify({
                "success": False,
                "error": "Código WO es requerido"
            }), 400
        
        if not modelo:
            return jsonify({
                "success": False,
                "error": "Modelo es requerido"
            }), 400
        
        if not cantidad_planeada or cantidad_planeada < 1:
            return jsonify({
                "success": False,
                "error": "Cantidad planeada debe ser mayor a 0"
            }), 400
        
        # Verificar que la WO existe
        query_check = "SELECT id, modelo, cantidad_planeada, codigo_po FROM work_orders WHERE codigo_wo = %s"
        wo_actual = execute_query(query_check, (codigo_wo,), fetch='one')
        
        if not wo_actual:
            return jsonify({
                "success": False,
                "error": f"No se encontró la WO con código {codigo_wo}"
            }), 404
        
        # Actualizar los campos
        query_update = """
            UPDATE work_orders 
            SET modelo = %s, cantidad_planeada = %s, codigo_po = %s, fecha_modificacion = NOW()
            WHERE codigo_wo = %s
        """
        
        execute_query(query_update, (modelo, cantidad_planeada, codigo_po, codigo_wo))
        
        print(f"✅ WO actualizada: {codigo_wo} -> Modelo: {modelo}, Cantidad: {cantidad_planeada}, PO: {codigo_po}")
        return jsonify({
            "success": True,
            "message": f"WO {codigo_wo} actualizada exitosamente"
        })
        
    except Exception as e:
        print(f"❌ Error actualizando WO: {e}")
        return jsonify({
            "success": False,
            "error": "Error interno del servidor"
        }), 500


@api_po_wo.route('/wo/eliminar', methods=['DELETE'])
@manejo_errores
def eliminar_wo():
    """
    DELETE /api/wo/eliminar
    Eliminar Work Order
    """
    try:
        data = request.get_json(force=True)
        codigo_wo = data.get('codigo_wo', '').strip()
        
        if not codigo_wo:
            return jsonify({
                "success": False,
                "error": "Código WO es requerido"
            }), 400
        
        # Verificar que la WO existe
        query_check = "SELECT id FROM work_orders WHERE codigo_wo = %s"
        wo_actual = execute_query(query_check, (codigo_wo,), fetch='one')
        
        if not wo_actual:
            return jsonify({
                "success": False,
                "error": f"No se encontró la WO con código {codigo_wo}"
            }), 404
        
        # Eliminar la WO
        query_delete = "DELETE FROM work_orders WHERE codigo_wo = %s"
        execute_query(query_delete, (codigo_wo,))
        
        print(f"✅ WO eliminada: {codigo_wo}")
        return jsonify({
            "success": True,
            "message": f"WO {codigo_wo} eliminada exitosamente"
        })
        
    except Exception as e:
        print(f"❌ Error eliminando WO: {e}")
        return jsonify({
            "success": False,
            "error": "Error interno del servidor"
        }), 500


@api_po_wo.route('/po/listar', methods=['GET'])
@manejo_errores
def listar_pos():
    """Listar Purchase Orders para compatibilidad con frontend"""
    try:
        # Obtener parámetros de filtro
        estado = request.args.get('estado')
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        
        # Construir consulta base
        query = """
            SELECT 
                codigo_po,
                modelo,
                cantidad_planeada,
                fecha_operacion,
                estado,
                created_at
            FROM work_orders 
            WHERE codigo_po IS NOT NULL AND codigo_po != ''
        """
        
        params = []
        
        # Agregar filtros
        if estado:
            query += " AND estado = %s"
            params.append(estado)
            
        if fecha_desde:
            query += " AND fecha_operacion >= %s"
            params.append(fecha_desde)
            
        if fecha_hasta:
            query += " AND fecha_operacion <= %s"
            params.append(fecha_hasta)
            
        query += " ORDER BY created_at DESC"
        
        # Ejecutar consulta
        result = execute_query(query, params)
        
        if result['success']:
            pos = []
            for row in result['data']:
                po = {
                    'codigo_po': row[0],
                    'modelo': row[1],
                    'cantidad_planeada': row[2],
                    'fecha_operacion': row[3].strftime('%Y-%m-%d') if row[3] else None,
                    'estado': row[4],
                    'created_at': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else None
                }
                pos.append(po)
            
            print(f"✅ {len(pos)} POs listadas exitosamente")
            return jsonify({
                "success": True,
                "data": pos,
                "total": len(pos)
            })
        else:
            print(f"❌ Error en consulta de POs: {result['error']}")
            return jsonify({"success": False, "error": result['error']}), 500
        
    except Exception as e:
        print(f"❌ Error listando POs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def registrar_rutas_po_wo(app):
    """Registrar el blueprint de PO/WO en la aplicación Flask"""
    app.register_blueprint(api_po_wo)
    print("✅ Rutas PO/WO registradas")
