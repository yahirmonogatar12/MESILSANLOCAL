# -*- coding: utf-8 -*-
"""
Rutas de Calidad
APIs para gestión de control de calidad, AOI, ICT, defectos
"""

import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, session, render_template

from .utils import login_requerido, obtener_fecha_hora_mexico
from ..database.db_mysql import execute_query, get_mysql_connection

calidad_bp = Blueprint('calidad', __name__)


# ============== VISTAS CALIDAD ==============

@calidad_bp.route('/historial-aoi')
@login_requerido
def historial_aoi():
    """Página de Historial AOI"""
    try:
        return render_template('Control de resultados/Historial AOI.html')
    except Exception as e:
        print(f"Error al cargar Historial AOI: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@calidad_bp.route('/historial-aoi-ajax')
@login_requerido
def historial_aoi_ajax():
    """Ruta AJAX para Historial AOI"""
    try:
        return render_template('Control de resultados/Historial AOI.html')
    except Exception as e:
        print(f"Error al cargar template de Historial AOI: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@calidad_bp.route('/historial-ict-ajax')
@login_requerido
def historial_ict_ajax():
    """Ruta AJAX para Historial ICT"""
    try:
        return render_template('Control de resultados/history_ict.html')
    except Exception as e:
        print(f"Error al cargar template de Historial ICT: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@calidad_bp.route('/reporte-diario-inspeccion-proceso-ajax')
@login_requerido
def reporte_diario_inspeccion_proceso_ajax():
    """Ruta AJAX para Reporte diario de inspección de proceso"""
    try:
        return render_template('Control de proceso/reporte_diario_inspeccion_proceso_ajax.html')
    except Exception as e:
        print(f"Error al cargar template: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@calidad_bp.route('/historial-operacion-proceso-ajax')
@login_requerido
def historial_operacion_proceso_ajax():
    """Ruta AJAX para Historial de operación de proceso"""
    try:
        return render_template('Control de proceso/historial_operacion_proceso_ajax.html')
    except Exception as e:
        print(f"Error al cargar template: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@calidad_bp.route('/control-scrap-ajax')
@login_requerido
def control_scrap_ajax():
    """Ruta AJAX para Control Scrap"""
    try:
        return render_template('Control de proceso/control_scrap_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control Scrap AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# ============== API INVENTARIO IMD ==============

@calidad_bp.route('/api/inventario_general', methods=['GET'])
def api_inventario_general():
    """Endpoint para inventario general IMD desde tabla inv_resumen_modelo"""
    try:
        q = request.args.get("q", "", type=str).strip()
        stock = request.args.get("stock", "", type=str).strip()

        where_conditions = []
        params = []
        
        if q:
            where_conditions.append("(modelo LIKE %s OR nparte LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])
            
        if stock == ">0":
            where_conditions.append("stock_total > 0")
        elif stock == "=0":
            where_conditions.append("stock_total = 0")

        where_sql = ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        
        sql = f"""
            SELECT modelo, nparte, stock_total, ubicaciones,
                   DATE_FORMAT(ultima_entrada, '%Y-%m-%d %H:%i:%s') AS ultima_entrada,
                   DATE_FORMAT(ultima_salida, '%Y-%m-%d %H:%i:%s') AS ultima_salida,
                   tipo_inventario
            FROM inv_resumen_modelo
            {where_sql}
            ORDER BY modelo, nparte
            LIMIT 2000
        """
        
        results = execute_query(sql, params, fetch='all')
        
        return jsonify({
            'status': 'success',
            'items': results or []
        })
        
    except Exception as e:
        print(f"Error en api_inventario_general: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'items': []
        }), 500


@calidad_bp.route('/api/ubicacion', methods=['GET'])
def api_ubicacion():
    """Endpoint para ubicaciones IMD desde tabla ubicacionimdinv"""
    try:
        desde = request.args.get("desde", "", type=str).strip()
        hasta = request.args.get("hasta", "", type=str).strip()
        q = request.args.get("q", "", type=str).strip()
        ubic = request.args.get("ubicacion", "", type=str).strip()
        carro = request.args.get("carro", "", type=str).strip()

        where_conditions = []
        params = []

        fecha_expr = "COALESCE(DATE(fecha), STR_TO_DATE(fecha, '%Y-%m-%d'))"

        if desde:
            where_conditions.append(f"{fecha_expr} >= %s")
            params.append(desde)
        if hasta:
            where_conditions.append(f"{fecha_expr} <= %s")
            params.append(hasta)
        if q:
            where_conditions.append("(modelo LIKE %s OR nparte LIKE %s OR ubicacion LIKE %s OR carro LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        if ubic:
            where_conditions.append("ubicacion = %s")
            params.append(ubic)
        if carro:
            where_conditions.append("carro = %s")
            params.append(carro)

        where_sql = ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        
        sql = f"""
            SELECT modelo, nparte, fecha, ubicacion, cantidad,
                   tipo_inventario, comentario, carro
            FROM ubicacionimdinv
            {where_sql}
            ORDER BY {fecha_expr} DESC, modelo, nparte
            LIMIT 5000
        """
        
        results = execute_query(sql, params, fetch='all')
        
        return jsonify({
            'status': 'success',
            'items': results or []
        })
        
    except Exception as e:
        print(f"Error en api_ubicacion: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'items': []
        }), 500


@calidad_bp.route('/api/movimientos', methods=['GET'])
def api_movimientos():
    """Endpoint para movimientos IMD desde tabla movimientosimd_smd"""
    try:
        desde = request.args.get("desde", "", type=str).strip()
        hasta = request.args.get("hasta", "", type=str).strip()
        q = request.args.get("q", "", type=str).strip()
        tipo = request.args.get("tipo", "", type=str).strip()

        where_conditions = []
        params = []
        
        if desde:
            where_conditions.append("fecha >= %s")
            params.append(desde)
        if hasta:
            where_conditions.append("fecha <= %s")
            params.append(hasta + ' 23:59:59')
        if tipo:
            where_conditions.append("UPPER(tipo) = %s")
            params.append(tipo.upper())
        if q:
            where_conditions.append("(nparte LIKE %s OR ubicacion LIKE %s OR carro LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

        where_sql = ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        
        sql = f"""
            SELECT
              fecha AS fecha_hora,
              UPPER(tipo) AS tipo,
              nparte,
              (SELECT u.modelo FROM ubicacionimdinv u
               WHERE u.nparte = m.nparte ORDER BY u.fecha DESC LIMIT 1) AS modelo,
              cantidad, ubicacion, tipo_inventario, comentario, carro
            FROM movimientosimd_smd m
            {where_sql}
            ORDER BY fecha DESC
            LIMIT 5000
        """
        
        results = execute_query(sql, params, fetch='all')
        
        return jsonify({
            'status': 'success',
            'items': results or []
        })
        
    except Exception as e:
        print(f"Error en api_movimientos: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'items': []
        }), 500


# ============== API PLAN SMD ==============

@calidad_bp.route("/api/plan-smd-diario", methods=['GET'])
def api_plan_smd_diario():
    """API para plan SMD diario con cruce AOI"""
    date = request.args.get("date")
    shift = request.args.get("shift", "").strip()
    
    if not date:
        return jsonify({"error": "missing 'date' (YYYY-MM-DD)"}), 400

    aoi_where = "WHERE shift_date = %s"
    params = [date]
    if shift:
        aoi_where += " AND shift = %s"
        params.append(shift)

    sql = f"""
    SELECT
      pd.id, pd.linea, pd.lote, pd.nparte, UPPER(pd.nparte) AS ebr,
      pd.modelo, pd.tipo, pd.turno, pd.ct, pd.uph,
      pd.qty, pd.fisico, pd.falta, pd.pct, pd.comentarios, 
      pd.fecha_creacion, pd.usuario_creacion,
      COALESCE(a.producido, 0) AS producido,
      (COALESCE(a.producido,0) >= pd.qty) AS completo
    FROM
      (
        SELECT
          p.id, UPPER(p.linea) AS linea, p.lote, p.nparte, p.modelo, p.tipo, 
          p.turno, p.ct, p.uph, p.qty, p.fisico, p.falta, p.pct, p.comentarios, 
          p.fecha_creacion, p.usuario_creacion
        FROM plan_smd p
        WHERE DATE(p.fecha_creacion) = %s
      ) pd
    LEFT JOIN (
        SELECT UPPER(line_no) AS linea, UPPER(model) AS modelo,
               SUM(piece_w) AS producido
        FROM aoi_file_log
        {aoi_where}
        GROUP BY UPPER(line_no), UPPER(model)
    ) a ON a.linea = pd.linea AND UPPER(pd.modelo) = a.modelo
    ORDER BY pd.linea, pd.id
    """
    
    params.insert(0, date)  # Para el WHERE pd
    
    try:
        rows = execute_query(sql, tuple(params), fetch='all')
        return jsonify({"items": rows or []})
    except Exception as e:
        print(f"Error en api_plan_smd_diario: {e}")
        return jsonify({"error": str(e)}), 500


# ============== API AOI ==============

@calidad_bp.route('/api/aoi/historial', methods=['GET'])
@login_requerido
def api_aoi_historial():
    """API para obtener historial de AOI"""
    try:
        fecha_desde = request.args.get('desde', '')
        fecha_hasta = request.args.get('hasta', '')
        linea = request.args.get('linea', '')
        modelo = request.args.get('modelo', '')
        
        where_conditions = []
        params = []
        
        if fecha_desde:
            where_conditions.append("shift_date >= %s")
            params.append(fecha_desde)
        if fecha_hasta:
            where_conditions.append("shift_date <= %s")
            params.append(fecha_hasta)
        if linea:
            where_conditions.append("line_no = %s")
            params.append(linea)
        if modelo:
            where_conditions.append("model LIKE %s")
            params.append(f"%{modelo}%")
        
        where_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        sql = f"""
            SELECT shift_date, shift, line_no, model, 
                   SUM(piece_w) as total_piezas,
                   SUM(pass_w) as total_pass,
                   SUM(fail_w) as total_fail,
                   board_side
            FROM aoi_file_log
            {where_sql}
            GROUP BY shift_date, shift, line_no, model, board_side
            ORDER BY shift_date DESC, line_no
            LIMIT 1000
        """
        
        results = execute_query(sql, params if params else None, fetch='all')
        
        return jsonify({
            'success': True,
            'data': results or []
        })
        
    except Exception as e:
        print(f"Error en api_aoi_historial: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
