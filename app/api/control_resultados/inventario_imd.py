"""Endpoints HTTP del modulo "IMD-SMD TERMINADO".

Consumido por LISTA_DE_CONTROL_DE_RESULTADOS / Control de inventario.
JS cliente: app/static/js/inventario-imd-terminado-module.js
Template:   app/templates/Control de proceso/inventario_imd_terminado_ajax.html

Rutas:
  GET /control_resultados/inventario_imd_terminado  -> render template (canonica)
  GET /api/inventario_general                        -> tabla inv_resumen_modelo
  GET /api/ubicacion                                 -> tabla ubicacionimdinv
  GET /api/movimientos                               -> tabla movimientosimd_smd

Migrado desde app/routes.py el 2026-05-27. La ruta legacy
`/control_proceso/inventario_imd_terminado` queda como alias-redirect en
routes.py para no romper sidebars cacheados durante la transicion.

WF_003: las 3 APIs GET reciben @login_requerido (antes eran publicas:
exponian inventario sin sesion).

NOTA WF_002: los IDs internos del template usan sufijo `-imd` y algunos
`INVIMDPCBID_*`. No se renombran en este PR: el container raiz
`inventario-imd-terminado-unique-container` ya da scoping CSS y no hay
otro modulo con esos IDs hoy. Refactorizar a prefijo unico queda pendiente.
"""

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from app.api.shared import (
    execute_query,
    login_requerido,
    obtener_fecha_hora_mexico,
    requiere_permiso_dropdown,
)

import logging
logger = logging.getLogger(__name__)


bp = Blueprint("control_resultados_inventario_imd", __name__)


IMD_PERMISO_PAGINA = "LISTA_DE_CONTROL_DE_RESULTADOS"
IMD_PERMISO_SECCION = "Control de inventario"
IMD_PERMISO_BOTON = "IMD-SMD TERMINADO"


# Decorador con el permiso fijo del modulo, construido sobre el canonico de
# app/api/shared/permisos.py (la fachada accede a auth_system de forma lazy en
# el request, asi que no hay import circular al cargar este modulo).
_requiere_permiso_imd = requiere_permiso_dropdown(
    IMD_PERMISO_PAGINA, IMD_PERMISO_SECCION, IMD_PERMISO_BOTON
)


# ---------------------------------------------------------------------------
# Render template
# ---------------------------------------------------------------------------


@bp.route("/control_resultados/inventario_imd_terminado")
@login_requerido
@_requiere_permiso_imd
def inventario_imd_terminado_ajax():
    """Ruta AJAX canonica para cargar el contenido de Inventario IMD Terminado."""
    try:
        logger.info(" Iniciando carga de Inventario IMD Terminado AJAX...")
        result = render_template(
            "Control de proceso/inventario_imd_terminado_ajax.html"
        )
        logger.info(
            f" Template Inventario IMD Terminado AJAX renderizado exitosamente, tamano: {len(result)} caracteres"
        )
        return result
    except Exception as e:
        import traceback

        logger.error(f" Error al cargar template Inventario IMD Terminado AJAX: {e}")
        logger.info(traceback.format_exc())
        return f"Error al cargar el contenido: {str(e)}", 500


# ---------------------------------------------------------------------------
# API: inventario general (tabla inv_resumen_modelo)
# ---------------------------------------------------------------------------


@bp.route("/api/inventario_general", methods=["GET"])
@login_requerido
def api_inventario_general():
    """Endpoint para inventario general IMD desde tabla inv_resumen_modelo"""
    try:
        q = request.args.get("q", "", type=str).strip()
        stock = request.args.get("stock", "", type=str).strip()  # "", ">0", "=0"

        where_conditions = []
        params = []

        if q:
            where_conditions.append("(modelo LIKE %s OR nparte LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])

        if stock == ">0":
            where_conditions.append("stock_total > 0")
        elif stock == "=0":
            where_conditions.append("stock_total = 0")

        where_sql = (
            ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        )

        sql = f"""
            SELECT
              modelo,
              nparte,
              stock_total,
              ubicaciones,
              DATE_FORMAT(ultima_entrada, '%Y-%m-%d %H:%i:%s') AS ultima_entrada,
              DATE_FORMAT(ultima_salida,  '%Y-%m-%d %H:%i:%s') AS ultima_salida,
              tipo_inventario
            FROM inv_resumen_modelo
            {where_sql}
            ORDER BY modelo, nparte
            LIMIT 2000
        """

        results = execute_query(sql, params, fetch="all")

        return jsonify({"status": "success", "items": results or []})

    except Exception as e:
        logger.error(f"Error en api_inventario_general: {e}")
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


# ---------------------------------------------------------------------------
# API: ubicacion (tabla ubicacionimdinv)
# ---------------------------------------------------------------------------


@bp.route("/api/ubicacion", methods=["GET"])
@login_requerido
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

        # Normalizamos fecha: usamos fecha_subida si existe, si no, parseamos 'fecha'
        fecha_expr = "COALESCE(DATE(fecha), STR_TO_DATE(fecha, '%Y-%m-%d'))"

        if desde:
            where_conditions.append(f"{fecha_expr} >= %s")
            params.append(desde)
        if hasta:
            where_conditions.append(f"{fecha_expr} <= %s")
            params.append(hasta)
        if q:
            where_conditions.append(
                "(modelo LIKE %s OR nparte LIKE %s OR ubicacion LIKE %s OR carro LIKE %s)"
            )
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        if ubic:
            where_conditions.append("ubicacion = %s")
            params.append(ubic)
        if carro:
            where_conditions.append("carro = %s")
            params.append(carro)

        where_sql = (
            ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        )

        sql = f"""
            SELECT
              modelo,
              nparte,
              fecha,
              ubicacion,
              cantidad,
              tipo_inventario,
              comentario,
              carro
            FROM ubicacionimdinv
            {where_sql}
            ORDER BY {fecha_expr} DESC, modelo, nparte
            LIMIT 5000
        """

        results = execute_query(sql, params, fetch="all")

        return jsonify({"status": "success", "items": results or []})

    except Exception as e:
        logger.error(f"Error en api_ubicacion: {e}")
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


# ---------------------------------------------------------------------------
# API: movimientos (tabla movimientosimd_smd)
# ---------------------------------------------------------------------------


@bp.route("/api/movimientos", methods=["GET"])
@login_requerido
def api_movimientos():
    """Endpoint para movimientos IMD desde tabla movimientosimd_smd"""
    try:
        desde = request.args.get("desde", "", type=str).strip()
        hasta = request.args.get("hasta", "", type=str).strip()
        q = request.args.get("q", "", type=str).strip()
        tipo = request.args.get(
            "tipo", "", type=str
        ).strip()  # ENTRADA / SALIDA / AJUSTE / ""

        if not desde:
            # Mantener la consulta inicial acotada al dia actual en horario de Mexico.
            desde = obtener_fecha_hora_mexico().strftime("%Y-%m-%d")

        where_conditions = []
        params = []

        # Filtros de fecha simplificados - usar directamente el campo fecha
        if desde:
            where_conditions.append("fecha >= %s")
            params.append(desde)
        if hasta:
            where_conditions.append("fecha <= %s")
            params.append(hasta + " 23:59:59")
        if tipo:
            where_conditions.append("UPPER(tipo) = %s")
            params.append(tipo.upper())
        if q:
            # El modelo no esta en la tabla de movimientos; lo deducimos con un subquery
            where_conditions.append(
                "(nparte LIKE %s OR ubicacion LIKE %s OR carro LIKE %s)"
            )
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

        where_sql = (
            ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        )

        sql = f"""
            SELECT
              fecha AS fecha_hora,
              UPPER(tipo) AS tipo,
              nparte,
              -- Deducimos el modelo de la ultima ubicacion conocida para esa parte
              (SELECT u.modelo
                 FROM ubicacionimdinv u
                WHERE u.nparte = m.nparte
                ORDER BY u.fecha DESC
                LIMIT 1) AS modelo,
              cantidad,
              ubicacion,
              tipo_inventario,
              comentario,
              carro
            FROM movimientosimd_smd m
            {where_sql}
            ORDER BY fecha DESC
            LIMIT 5000
        """

        results = execute_query(sql, params, fetch="all")

        return jsonify({"status": "success", "items": results or []})

    except Exception as e:
        logger.error(f"Error en api_movimientos: {e}")
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


# ---------------------------------------------------------------------------
# Fase 4 (2026-05-28): 2 endpoints de consulta de inventario migrados desde
# routes.py. Operan sobre inv_resumen_modelo (mismo dominio que las APIs ya
# residentes aqui sobre inv_resumen_modelo / ubicacionimdinv / movimientosimd_smd).
# ---------------------------------------------------------------------------


@bp.route("/api/inventario/modelo/<codigo_modelo>", methods=["GET"])
@login_requerido
def api_inventario_modelo(codigo_modelo):
    """API para obtener inventario por codigo de modelo"""
    try:
        query = """
        SELECT modelo, nparte, stock_total, ubicaciones,
               ultima_entrada, ultima_salida, updated_at
        FROM inv_resumen_modelo
        WHERE nparte = %s
        """

        inventario = execute_query(query, (codigo_modelo,), fetch="all")

        resultado = []
        for item in inventario:
            resultado.append(
                {
                    "modelo": item["modelo"],
                    "nparte": item["nparte"],
                    "stock_total": item["stock_total"] or 0,
                    "ubicaciones": item["ubicaciones"] or "",
                    "ultima_entrada": item["ultima_entrada"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if item["ultima_entrada"]
                    else "",
                    "ultima_salida": item["ultima_salida"].strftime("%Y-%m-%d %H:%M:%S")
                    if item["ultima_salida"]
                    else "",
                    "updated_at": item["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if item["updated_at"]
                    else "",
                }
            )

        return jsonify(resultado)

    except Exception as e:
        logger.error(f" Error en API inventario modelo {codigo_modelo}: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/inventario", methods=["GET"])
@login_requerido
def api_inventario():
    """API para consultar inventario por modelo y/o nparte"""
    try:
        modelo = request.args.get("modelo", "").strip()
        nparte = request.args.get("nparte", "").strip()

        if not modelo:
            return jsonify({"error": "Parametro modelo es requerido"}), 400

        if nparte:
            query = """
            SELECT modelo, nparte, stock_total, ubicaciones, ultima_entrada, ultima_salida, updated_at
            FROM inv_resumen_modelo
            WHERE modelo = %s AND nparte = %s
            """
            result = execute_query(query, (modelo, nparte), fetch="one")

            if result:
                return jsonify(
                    {
                        "modelo": result["modelo"],
                        "nparte": result["nparte"],
                        "stock_total": result["stock_total"] or 0,
                    }
                )
            else:
                return jsonify({"modelo": modelo, "nparte": nparte, "stock_total": 0})
        else:
            query = """
            SELECT modelo, SUM(stock_total) as stock_total
            FROM inv_resumen_modelo
            WHERE modelo = %s
            GROUP BY modelo
            """
            result = execute_query(query, (modelo,), fetch="one")

            if result:
                return jsonify(
                    {
                        "modelo": result["modelo"],
                        "stock_total": result["stock_total"] or 0,
                    }
                )
            else:
                return jsonify({"modelo": modelo, "stock_total": 0})

    except Exception as e:
        logger.error(f" Error consultando inventario: {e}")
        return jsonify({"error": str(e)}), 500
