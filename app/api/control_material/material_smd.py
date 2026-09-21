"""Control de material SMD (Control de material > Material por areas).

Consulta de solo lectura sobre las tablas que escribe la app
Control_inventario_SMD (misma BD mes_production):
  - Entradas:   control_material_almacen_smd  (fecha_recibo, sin cancelados)
  - Salidas:    control_material_salida_smd   (fecha_salida, sin cancelados)
  - Inventario: inventario_lotes_smd          (stock actual > 0) en dos modos:
      detallado (por lote) y general (suma por numero de parte)
Misma logica que warehousing.search / outgoing.search / inventory.getLots /
inventory.getSummary de esa app.

Rutas:
  GET /material/smd                  -> fragmento AJAX
  GET /api/material/smd              -> vista, start, end, cf_<col>, page, per_page
  GET /api/material/smd/export       -> Excel con los mismos filtros (sin paginar)
"""

import logging
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, jsonify, render_template, request

from app.api.shared import (
    excel_response,
    execute_query,
    login_requerido,
    obtener_fecha_hora_mexico,
    requiere_permiso_dropdown,
    sanitizar_texto,
)

logger = logging.getLogger(__name__)

bp = Blueprint("control_material_material_smd", __name__)

_requiere_permiso = requiere_permiso_dropdown(
    "LISTA_DE_MATERIALES", "Material por áreas", "Control de material SMD"
)

PER_PAGE_OPTIONS = {100, 200, 500, 1000}
EXPORT_MAX = 50000

# Ultima fila de almacen por etiqueta (la tabla tiene historicos repetidos).
_ULTIMA_ALMACEN = (
    "(SELECT {expr} FROM control_material_almacen_smd cma "
    "WHERE cma.codigo_material_recibido = il.codigo_material_recibido "
    "ORDER BY cma.id DESC LIMIT 1)"
)

# vista -> tabla, condiciones fijas (+params), columna de fecha, columnas
# (clave, expresion SQL, encabezado Excel, ancho), orden y columna a sumar.
VISTAS = {
    "entradas": {
        "from": "control_material_almacen_smd",
        "base": ("COALESCE(cancelado, 0) = %s", [0]),
        "fecha": "fecha_recibo",
        "cols": [
            ("fecha", "DATE_FORMAT(fecha_recibo, '%%Y-%%m-%%d')", "Fecha", 12),
            ("hora", "DATE_FORMAT(fecha_recibo, '%%H:%%i:%%s')", "Hora", 10),
            ("codigo", "codigo_material_recibido", "Codigo", 30),
            ("part_no", "numero_parte", "Part No", 18),
            ("lote", "numero_lote_material", "Lote", 20),
            ("cantidad", "cantidad_actual", "Cantidad", 10),
            ("unidad", "COALESCE(unidad_medida, 'EA')", "Unidad", 8),
            ("ubicacion", "COALESCE(ubicacion_destino, ubicacion_salida)", "Ubicacion", 14),
            ("cliente", "cliente", "Cliente", 12),
            ("especificacion", "especificacion", "Especificacion", 34),
            ("usuario", "usuario_registro", "Usuario", 22),
        ],
        "orden": "fecha_recibo DESC, id DESC",
        "suma": "cantidad_actual",
    },
    "salidas": {
        "from": "control_material_salida_smd cms",
        "base": ("COALESCE(cms.cancelado, 0) = %s", [0]),
        "fecha": "cms.fecha_salida",
        "cols": [
            ("fecha", "DATE_FORMAT(cms.fecha_salida, '%%Y-%%m-%%d')", "Fecha", 12),
            ("hora", "DATE_FORMAT(cms.fecha_salida, '%%H:%%i:%%s')", "Hora", 10),
            ("codigo", "cms.codigo_material_recibido", "Codigo", 30),
            ("part_no", "cms.numero_parte", "Part No", 18),
            ("lote", "cms.numero_lote", "Lote", 20),
            ("cantidad", "cms.cantidad_salida", "Cantidad", 10),
            ("unidad", "COALESCE((SELECT cma.unidad_medida FROM control_material_almacen_smd cma "
                       "WHERE cma.codigo_material_recibido = cms.codigo_material_recibido "
                       "ORDER BY cma.id DESC LIMIT 1), 'EA')", "Unidad", 8),
            ("modelo", "cms.modelo", "Modelo", 14),
            ("depto", "cms.depto_salida", "Depto", 12),
            ("proceso", "cms.proceso_salida", "Proceso", 16),
            ("linea", "cms.linea_proceso", "Linea", 10),
            ("usuario", "cms.usuario_registro", "Usuario", 22),
        ],
        "orden": "cms.fecha_salida DESC, cms.id DESC",
        "suma": "cms.cantidad_salida",
    },
    # Inventario detallado: un renglon por lote (inventory.getLots sin fechas).
    "inventario": {
        "from": "inventario_lotes_smd il LEFT JOIN materiales m ON m.numero_parte = il.numero_parte",
        "base": ("il.stock_actual > %s", [0]),
        "fecha": None,  # stock actual: no depende del rango de fechas
        "cols": [
            ("part_no", "il.numero_parte", "Part No", 18),
            ("lote", "il.numero_lote", "Lote", 20),
            ("codigo", "il.codigo_material_recibido", "Codigo", 30),
            ("entrada", "il.total_entrada", "Entrada", 10),
            ("salida", "il.total_salida", "Salida", 10),
            ("stock", "il.stock_actual", "Stock", 10),
            ("unidad", "IFNULL(m.unidad_medida, 'EA')", "Unidad", 8),
            ("ubicacion", _ULTIMA_ALMACEN.format(expr="COALESCE(cma.ubicacion_destino, cma.ubicacion_salida)"), "Ubicacion", 14),
            ("fecha_recibo", "DATE_FORMAT(il.primer_recibo, '%%Y-%%m-%%d')", "Fecha recibo", 12),
            ("especificacion", "COALESCE(m.especificacion_material, "
                               + _ULTIMA_ALMACEN.format(expr="cma.especificacion") + ")", "Especificacion", 34),
        ],
        "orden": "il.numero_parte, il.numero_lote",
        "suma": "il.stock_actual",
    },
    # Inventario general: suma por numero de parte (inventory.getSummary sin fechas).
    # Tabla derivada para que los filtros de columna apliquen sobre los totales.
    "inventario_general": {
        "from": (
            "(SELECT il.numero_parte, MAX(IFNULL(m.unidad_medida, 'EA')) AS unidad, "
            "MAX(m.especificacion_material) AS especificacion, SUM(il.stock_actual) AS stock, "
            "COUNT(DISTINCT il.numero_lote) AS lotes, SUM(il.stock_actual > 0) AS lotes_con_stock "
            "FROM inventario_lotes_smd il LEFT JOIN materiales m ON m.numero_parte = il.numero_parte "
            "GROUP BY il.numero_parte) g"
        ),
        "base": ("g.stock > %s", [0]),
        "fecha": None,
        "cols": [
            ("part_no", "g.numero_parte", "Part No", 18),
            # Sin registro en materiales: especificacion de la ultima entrada de almacen.
            ("especificacion", "COALESCE(g.especificacion, (SELECT cma.especificacion "
                               "FROM inventario_lotes_smd il2 JOIN control_material_almacen_smd cma "
                               "ON cma.codigo_material_recibido = il2.codigo_material_recibido "
                               "WHERE il2.numero_parte = g.numero_parte ORDER BY cma.id DESC LIMIT 1))",
             "Especificacion", 40),
            ("unidad", "g.unidad", "Unidad", 8),
            ("stock", "g.stock", "Stock total", 12),
            ("lotes", "g.lotes", "Lotes distintos", 14),
            # Como la app SMD: cuenta etiquetas (codigo recibido) con stock, no lotes.
            ("lotes_con_stock", "g.lotes_con_stock", "Etiquetas con stock", 16),
        ],
        "orden": "g.numero_parte",
        "suma": "g.stock",
    },
}


def _vista():
    nombre = (request.args.get("vista") or "entradas").strip().lower()
    if nombre not in VISTAS:
        raise ValueError("Vista invalida (entradas, salidas, inventario o inventario_general)")
    return VISTAS[nombre]


def _where(vista):
    """WHERE + params: base de la vista, rango de fechas (si aplica) y cf_*."""
    base_sql, base_params = vista["base"]
    where, params = [base_sql], list(base_params)
    if vista["fecha"]:
        hoy = obtener_fecha_hora_mexico().strftime("%Y-%m-%d")
        start = request.args.get("start") or hoy
        end = request.args.get("end") or start
        for valor in (start, end):
            datetime.strptime(valor, "%Y-%m-%d")  # ValueError -> 400
        where += [f"{vista['fecha']} >= %s", f"{vista['fecha']} < DATE_ADD(%s, INTERVAL 1 DAY)"]
        params += [start, end]
    for clave, expr, _h, _w in vista["cols"]:
        valor = sanitizar_texto(request.args.get(f"cf_{clave}"), 128)
        if valor:
            where.append(f"COALESCE(CAST({expr} AS CHAR), '') LIKE %s")
            params.append(f"%{valor}%")
    return " WHERE " + " AND ".join(where), params


def _numero(valor):
    """Decimal de MySQL -> int si es entero (500.00 -> 500), float si no."""
    if isinstance(valor, Decimal):
        return int(valor) if valor == valor.to_integral_value() else float(valor)
    return valor


def _filas(vista, where, params, limit, offset=0):
    select = ", ".join(f"{expr} AS {clave}" for clave, expr, _h, _w in vista["cols"])
    sql = f"SELECT {select} FROM {vista['from']}{where} ORDER BY {vista['orden']} LIMIT %s OFFSET %s"
    rows = execute_query(sql, tuple(params) + (limit, offset), fetch="all") or []
    return [{k: _numero(v) for k, v in r.items()} for r in rows]


@bp.route("/material/smd")
@login_requerido
@_requiere_permiso
def material_smd_ajax():
    try:
        return render_template("Control de material/material_smd_ajax.html")
    except Exception as e:
        logger.error(f"Error al cargar Control de material SMD: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/api/material/smd", methods=["GET"])
@login_requerido
@_requiere_permiso
def api_material_smd():
    try:
        vista = _vista()
        where, params = _where(vista)
        try:
            page = max(1, int(request.args.get("page", 1)))
            per_page = int(request.args.get("per_page", 1000))
        except (TypeError, ValueError):
            page, per_page = 1, 1000
        if per_page not in PER_PAGE_OPTIONS:
            per_page = 1000

        resumen = execute_query(
            f"SELECT COUNT(*) AS total, COALESCE(SUM({vista['suma']}), 0) AS piezas "
            f"FROM {vista['from']}{where}",
            tuple(params), fetch="one",
        ) or {}
        total = int(resumen.get("total") or 0)
        total_pages = max(1, -(-total // per_page))
        page = min(page, total_pages)
        return jsonify({
            "success": True,
            "rows": _filas(vista, where, params, per_page, (page - 1) * per_page),
            "total": total,
            "piezas": _numero(resumen.get("piezas") or 0),
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error en Control de material SMD: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/material/smd/export", methods=["GET"])
@login_requerido
@_requiere_permiso
def api_material_smd_export():
    try:
        vista = _vista()
        where, params = _where(vista)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    rows = _filas(vista, where, params, EXPORT_MAX)
    claves, _e, headers, widths = zip(*vista["cols"])
    nombre = (request.args.get("vista") or "entradas").strip().lower()
    return excel_response(
        rows, headers, claves, widths, f"SMD {nombre}",
        f"Material_SMD_{nombre}_{obtener_fecha_hora_mexico():%Y%m%d_%H%M}", freeze="A2",
    )
