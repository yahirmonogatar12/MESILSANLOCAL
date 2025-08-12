"""
API Routes para el sistema PO → WO
Endpoints REST para embarques (PO) y work_orders (WO)
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, date
import re
from app.db_mysql import db
from app.models_po_wo import Embarque, WorkOrder, validar_codigo_po, validar_codigo_wo, generar_codigo_po, generar_codigo_wo

# Crear blueprint para las rutas API
api_po_wo = Blueprint('api_po_wo', __name__, url_prefix='/api')


def validar_fecha(fecha_str):
    """Validar formato de fecha YYYY-MM-DD"""
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False


def manejo_errores(func):
    """Decorator para manejo centralizado de errores"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Error en {func.__name__}: {e}")
            return jsonify({
                "ok": False, 
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }), 500
    wrapper.__name__ = func.__name__
    return wrapper


# =============================================================================
# ENDPOINTS PARA EMBARQUES (PO)
# =============================================================================

@api_po_wo.route('/embarques', methods=['POST'])
@manejo_errores
def crear_po():
    """
    POST /api/embarques
    Crear nueva Purchase Order (PO)
    """
    try:
        data = request.get_json(force=True)
        
        # Validaciones
        codigo_po = data.get('codigo_po', '').strip()
        cliente = data.get('cliente', '').strip()
        fecha_registro_str = data.get('fecha_registro', '')
        estado = data.get('estado', 'PLAN')
        
        # Validar código PO
        if not codigo_po:
            return jsonify({
                "ok": False, 
                "code": "VALIDATION_ERROR", 
                "field": "codigo_po",
                "message": "Código PO es requerido"
            }), 400
            
        if not validar_codigo_po(codigo_po):
            return jsonify({
                "ok": False, 
                "code": "VALIDATION_ERROR", 
                "field": "codigo_po",
                "message": "Formato de código PO inválido (debe ser PO-YYMMDD-####)"
            }), 400
        
        # Validar fecha
        fecha_registro = None
        if fecha_registro_str:
            if not validar_fecha(fecha_registro_str):
                return jsonify({
                    "ok": False, 
                    "code": "VALIDATION_ERROR", 
                    "field": "fecha_registro",
                    "message": "Formato de fecha inválido (debe ser YYYY-MM-DD)"
                }), 400
            fecha_registro = datetime.strptime(fecha_registro_str, '%Y-%m-%d').date()
        
        # Validar estado
        estados_validos = ['PLAN', 'PREPARACION', 'EMBARCADO', 'EN_TRANSITO', 'ENTREGADO']
        if estado not in estados_validos:
            return jsonify({
                "ok": False, 
                "code": "VALIDATION_ERROR", 
                "field": "estado",
                "message": f"Estado inválido. Válidos: {estados_validos}"
            }), 400
        
        # Crear embarque
        nuevo_embarque = Embarque(
            codigo_po=codigo_po,
            cliente=cliente,
            fecha_registro=fecha_registro,
            estado=estado
        )
        
        db.session.add(nuevo_embarque)
        db.session.commit()
        
        print(f" PO creada: {codigo_po}")
        return jsonify({"ok": True, "id": nuevo_embarque.id}), 201
        
    except Exception as e:
        db.session.rollback()
        
        # Manejar duplicados
        if "codigo_po" in str(e) and "Duplicate" in str(e):
            return jsonify({"ok": False, "code": "DUPLICATE_PO"}), 409
            
        raise e


@api_po_wo.route('/embarques', methods=['GET'])
@manejo_errores
def listar_pos():
    """
    GET /api/embarques
    Listar Purchase Orders con filtros opcionales
    """
    # Filtros opcionales
    estado = request.args.get('estado')
    codigo_po = request.args.get('codigo_po')
    
    # Construir query
    query = Embarque.query
    
    if estado:
        query = query.filter_by(estado=estado)
    
    if codigo_po:
        query = query.filter_by(codigo_po=codigo_po)
    
    # Ordenar por fecha de modificación descendente
    embarques = query.order_by(Embarque.modificado.desc()).all()
    
    # Convertir a diccionario
    resultado = [embarque.to_dict() for embarque in embarques]
    
    print(f" Listando {len(resultado)} POs")
    return jsonify(resultado), 200


@api_po_wo.route('/embarques/<codigo_po>/estado', methods=['PUT'])
@manejo_errores
def cambiar_estado_po(codigo_po):
    """
    PUT /api/embarques/{codigo_po}/estado
    Cambiar estado de una PO
    """
    data = request.get_json(force=True)
    nuevo_estado = data.get('estado', '').strip()
    
    # Validar estado
    estados_validos = ['PLAN', 'PREPARACION', 'EMBARCADO', 'EN_TRANSITO', 'ENTREGADO']
    if nuevo_estado not in estados_validos:
        return jsonify({
            "ok": False, 
            "code": "VALIDATION_ERROR", 
            "field": "estado",
            "message": f"Estado inválido. Válidos: {estados_validos}"
        }), 400
    
    # Buscar embarque
    embarque = Embarque.query.filter_by(codigo_po=codigo_po).first()
    if not embarque:
        return jsonify({"ok": False, "code": "PO_NOT_FOUND"}), 404
    
    # Actualizar estado
    embarque.estado = nuevo_estado
    db.session.commit()
    
    print(f" Estado PO {codigo_po} cambiado a {nuevo_estado}")
    return jsonify({"ok": True, "estado": nuevo_estado}), 200


# =============================================================================
# ENDPOINTS PARA WORK ORDERS (WO)
# =============================================================================

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
        codigo_po = data.get('codigo_po', '').strip()
        modelo = data.get('modelo', '').strip()
        cantidad_planeada = data.get('cantidad_planeada')
        fecha_operacion_str = data.get('fecha_operacion', '')
        modificador = data.get('modificador', 'AGENTE').strip()
        
        # Validar código WO
        if not codigo_wo:
            return jsonify({
                "ok": False, 
                "code": "VALIDATION_ERROR", 
                "field": "codigo_wo",
                "message": "Código WO es requerido"
            }), 400
            
        if not validar_codigo_wo(codigo_wo):
            return jsonify({
                "ok": False, 
                "code": "VALIDATION_ERROR", 
                "field": "codigo_wo",
                "message": "Formato de código WO inválido (debe ser WO-YYMMDD-####)"
            }), 400
        
        # Validar existencia de PO
        if not codigo_po:
            return jsonify({
                "ok": False, 
                "code": "VALIDATION_ERROR", 
                "field": "codigo_po",
                "message": "Código PO es requerido"
            }), 400
            
        embarque = Embarque.query.filter_by(codigo_po=codigo_po).first()
        if not embarque:
            return jsonify({"ok": False, "code": "PO_NOT_FOUND"}), 404
        
        # Validar cantidad planeada
        try:
            cantidad_planeada = int(cantidad_planeada)
            if cantidad_planeada <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({
                "ok": False, 
                "code": "VALIDATION_ERROR", 
                "field": "cantidad_planeada",
                "message": "Cantidad planeada debe ser un entero mayor a 0"
            }), 400
        
        # Validar fecha de operación
        fecha_operacion = None
        if fecha_operacion_str:
            if not validar_fecha(fecha_operacion_str):
                return jsonify({
                    "ok": False, 
                    "code": "VALIDATION_ERROR", 
                    "field": "fecha_operacion",
                    "message": "Formato de fecha inválido (debe ser YYYY-MM-DD)"
                }), 400
            fecha_operacion = datetime.strptime(fecha_operacion_str, '%Y-%m-%d').date()
        
        # Crear Work Order
        nueva_wo = WorkOrder(
            codigo_wo=codigo_wo,
            codigo_po=codigo_po,
            modelo=modelo,
            cantidad_planeada=cantidad_planeada,
            fecha_operacion=fecha_operacion,
            modificador=modificador
        )
        
        db.session.add(nueva_wo)
        db.session.commit()
        
        print(f" WO creada: {codigo_wo} → {codigo_po}")
        return jsonify({"ok": True, "id": nueva_wo.id}), 201
        
    except Exception as e:
        db.session.rollback()
        
        # Manejar duplicados
        if "codigo_wo" in str(e) and "Duplicate" in str(e):
            return jsonify({"ok": False, "code": "DUPLICATE_WO"}), 409
            
        raise e


@api_po_wo.route('/work_orders', methods=['GET'])
@manejo_errores
def listar_wos():
    """
    GET /api/work_orders
    Listar Work Orders con filtros opcionales
    """
    # Filtros opcionales
    po = request.args.get('po')  # Filtrar por código PO
    codigo_wo = request.args.get('codigo_wo')
    
    # Construir query
    query = WorkOrder.query
    
    if po:
        query = query.filter_by(codigo_po=po)
    
    if codigo_wo:
        query = query.filter_by(codigo_wo=codigo_wo)
    
    # Ordenar por fecha de modificación descendente
    work_orders = query.order_by(WorkOrder.fecha_modificacion.desc()).all()
    
    # Convertir a diccionario
    resultado = [wo.to_dict() for wo in work_orders]
    
    print(f" Listando {len(resultado)} WOs")
    return jsonify(resultado), 200


@api_po_wo.route('/work_orders/<codigo_wo>/estado', methods=['PUT'])
@manejo_errores
def cambiar_estado_wo(codigo_wo):
    """
    PUT /api/work_orders/{codigo_wo}/estado
    Cambiar estado de una WO
    """
    data = request.get_json(force=True)
    nuevo_estado = data.get('estado', '').strip()
    
    # Validar estado
    estados_validos = ['CREADA', 'PLANIFICADA', 'EN_PRODUCCION', 'CERRADA']
    if nuevo_estado not in estados_validos:
        return jsonify({
            "ok": False, 
            "code": "VALIDATION_ERROR", 
            "field": "estado",
            "message": f"Estado inválido. Válidos: {estados_validos}"
        }), 400
    
    # Buscar work order
    work_order = WorkOrder.query.filter_by(codigo_wo=codigo_wo).first()
    if not work_order:
        return jsonify({"ok": False, "code": "WO_NOT_FOUND"}), 404
    
    # Actualizar estado
    work_order.estado_wo = nuevo_estado
    db.session.commit()
    
    print(f" Estado WO {codigo_wo} cambiado a {nuevo_estado}")
    return jsonify({"ok": True, "estado": nuevo_estado}), 200


@api_po_wo.route('/work_orders/<codigo_wo>', methods=['DELETE'])
@manejo_errores
def eliminar_wo(codigo_wo):
    """
    DELETE /api/work_orders/{codigo_wo}
    Eliminar Work Order (para rollback)
    """
    work_order = WorkOrder.query.filter_by(codigo_wo=codigo_wo).first()
    if not work_order:
        return jsonify({"ok": False, "code": "WO_NOT_FOUND"}), 404
    
    db.session.delete(work_order)
    db.session.commit()
    
    print(f"🗑️ WO eliminada: {codigo_wo}")
    return jsonify({"ok": True}), 200


# =============================================================================
# ENDPOINTS AUXILIARES
# =============================================================================

@api_po_wo.route('/generar_codigo_po', methods=['GET'])
@manejo_errores
def endpoint_generar_codigo_po():
    """
    GET /api/generar_codigo_po
    Generar código PO único
    """
    codigo = generar_codigo_po()
    return jsonify({"codigo_po": codigo}), 200


@api_po_wo.route('/generar_codigo_wo', methods=['GET'])
@manejo_errores
def endpoint_generar_codigo_wo():
    """
    GET /api/generar_codigo_wo
    Generar código WO único
    """
    codigo = generar_codigo_wo()
    return jsonify({"codigo_wo": codigo}), 200


# =============================================================================
# INICIALIZACIÓN
# =============================================================================

def registrar_rutas_po_wo(app):
    """
    Registrar todas las rutas del sistema PO → WO
    """
    app.register_blueprint(api_po_wo)
    print(" Rutas API PO → WO registradas")
