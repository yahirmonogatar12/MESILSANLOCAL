"""Control de material por areas (Control de material > Material por areas).

Consulta de solo lectura sobre las tablas que escriben las apps de cada area
(misma BD mes_production). Cada area usa el mismo esquema con otro sufijo:
  - Entradas:   control_material_almacen_<sfx>  (fecha_recibo, sin cancelados)
  - Salidas:    control_material_salida_<sfx>   (fecha_salida, sin cancelados)
  - Inventario: inventario_lotes_<sfx>          (stock actual > 0) en dos modos:
      detallado (por lote) y general (suma por numero de parte)
  - MICOM ademas: inventario chamber (control_material_chamber_micom, micoms
      programados); IPM ademas: inventario completo (control_material_completo_ipm,
      IPM armados). Solo stock, detallado por lote y general por llave.
Misma logica que warehousing.search / outgoing.search / inventory.getLots /
inventory.getSummary de Control_inventario_SMD, MICOM e IPM_Control.

Areas: smd (Control_inventario_SMD), micom (MICOM), ipm (IPM_Control).

Rutas (<area> = smd | micom | ipm):
  GET /material/<area>                  -> fragmento AJAX
  GET /api/material/<area>              -> vista, start, end, cf_<col>, page, per_page
  GET /api/material/<area>/export       -> Excel con los mismos filtros (sin paginar)
"""

import logging
from datetime import datetime
from decimal import Decimal
from functools import wraps

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

bp = Blueprint("control_material_material_areas", __name__)

# area -> sufijo de tablas, titulo, boton de permiso (LISTA_DE_MATERIALES) y
# tipos de inventario que ofrece el selector "Consulta" (valor, etiqueta).
AREAS = {
    "smd": {
        "sfx": "smd", "titulo": "SMD", "boton": "Control de material SMD",
        "inventarios": [("inventario", "Inventario")],
    },
    "micom": {
        "sfx": "micom", "titulo": "MICOM", "boton": "Control de material Micom",
        "inventarios": [("inventario", "Inventario virgen"), ("inventario_chamber", "Inventario chamber")],
    },
    "ipm": {
        "sfx": "ipm", "titulo": "IPM", "boton": "Control de material IPM",
        "inventarios": [("inventario", "Inventario virgen"), ("inventario_completo", "Inventario completo")],
    },
}
_AREA = "<any(" + ", ".join(AREAS) + "):area>"

_PERMISOS = {
    area: requiere_permiso_dropdown("LISTA_DE_MATERIALES", "Material por áreas", cfg["boton"])
    for area, cfg in AREAS.items()
}


def _con_permiso(fn):
    """Aplica el permiso del boton del area que viene en la URL."""
    @wraps(fn)
    def wrapper(area):
        return _PERMISOS[area](fn)(area)
    return wrapper


PER_PAGE_OPTIONS = {100, 200, 500, 1000}
EXPORT_MAX = 50000


def _vistas(sfx):
    """Vistas de un area: tabla, condiciones fijas (+params), columna de fecha,
    columnas (clave, expresion SQL, encabezado Excel, ancho), orden y suma."""
    almacen = f"control_material_almacen_{sfx}"
    # Ultima fila de almacen por etiqueta (la tabla puede tener historicos repetidos).
    ultima_almacen = (
        f"(SELECT {{expr}} FROM {almacen} cma "
        "WHERE cma.codigo_material_recibido = il.codigo_material_recibido "
        "ORDER BY cma.id DESC LIMIT 1)"
    )
    return {
        "entradas": {
            "from": almacen,
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
            "from": f"control_material_salida_{sfx} cms",
            "base": ("COALESCE(cms.cancelado, 0) = %s", [0]),
            "fecha": "cms.fecha_salida",
            "cols": [
                ("fecha", "DATE_FORMAT(cms.fecha_salida, '%%Y-%%m-%%d')", "Fecha", 12),
                ("hora", "DATE_FORMAT(cms.fecha_salida, '%%H:%%i:%%s')", "Hora", 10),
                ("codigo", "cms.codigo_material_recibido", "Codigo", 30),
                ("part_no", "cms.numero_parte", "Part No", 18),
                ("lote", "cms.numero_lote", "Lote", 20),
                ("cantidad", "cms.cantidad_salida", "Cantidad", 10),
                ("unidad", f"COALESCE((SELECT cma.unidad_medida FROM {almacen} cma "
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
            "from": f"inventario_lotes_{sfx} il LEFT JOIN materiales m ON m.numero_parte = il.numero_parte",
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
                ("ubicacion", ultima_almacen.format(expr="COALESCE(cma.ubicacion_destino, cma.ubicacion_salida)"), "Ubicacion", 14),
                ("fecha_recibo", "DATE_FORMAT(il.primer_recibo, '%%Y-%%m-%%d')", "Fecha recibo", 12),
                ("especificacion", "COALESCE(m.especificacion_material, "
                                   + ultima_almacen.format(expr="cma.especificacion") + ")", "Especificacion", 34),
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
                f"FROM inventario_lotes_{sfx} il LEFT JOIN materiales m ON m.numero_parte = il.numero_parte "
                "GROUP BY il.numero_parte) g"
            ),
            "base": ("g.stock > %s", [0]),
            "fecha": None,
            "cols": [
                ("part_no", "g.numero_parte", "Part No", 18),
                # Sin registro en materiales: especificacion de la ultima entrada de almacen.
                ("especificacion", f"COALESCE(g.especificacion, (SELECT cma.especificacion "
                                   f"FROM inventario_lotes_{sfx} il2 JOIN {almacen} cma "
                                   "ON cma.codigo_material_recibido = il2.codigo_material_recibido "
                                   "WHERE il2.numero_parte = g.numero_parte ORDER BY cma.id DESC LIMIT 1))",
                 "Especificacion", 40),
                ("unidad", "g.unidad", "Unidad", 8),
                ("stock", "g.stock", "Stock total", 12),
                ("lotes", "g.lotes", "Lotes distintos", 14),
                # Como las apps: cuenta etiquetas (codigo recibido) con stock, no lotes.
                ("lotes_con_stock", "g.lotes_con_stock", "Etiquetas con stock", 16),
            ],
            "orden": "g.numero_parte",
            "suma": "g.stock",
        },
    }


# Inventario de material ya procesado, solo stock (sin entrada/salida/ubicacion):
#   MICOM chamber  -> micoms programados, llave = etiqueta de programacion
#                     (inventory.getChamberLots / getChamberSummary de MICOM)
#   IPM completo   -> IPM armados, llave = part no IPM
#                     (inventory.getCompletoLots / getCompletoSummary de IPM_Control)
def _vistas_procesado(sufijo, tabla, col_lote, clave_sql, lote_label, clave_label, part_no=True,
                      espec_general="MAX(c.source_specification)"):
    extra = [("part_no", "c.source_part_number", "Part No", 22)] if part_no else []
    extra_g = [("part_no", "g.part_no", "Part No", 22)] if part_no else []
    return {
        f"inventario_{sufijo}": {
            "from": f"{tabla} c",
            "base": ("COALESCE(c.qty_actual, 0) > %s", [0]),
            "fecha": None,
            "cols": [
                (f"lote_{sufijo}", f"c.{col_lote}", lote_label, 34),
                ("programacion", clave_sql, clave_label, 24),
                *extra,
                ("especificacion", "c.source_specification", "Especificacion", 30),
                ("stock", "COALESCE(c.qty_actual, 0)", "Stock", 10),
                ("fecha_recibo", "DATE_FORMAT(c.created_at, '%%Y-%%m-%%d')", "Fecha creacion", 12),
                ("usuario", "c.usuario_registro", "Usuario", 22),
            ],
            "orden": f"{clave_sql}, c.created_at",
            "suma": "COALESCE(c.qty_actual, 0)",
        },
        f"inventario_{sufijo}_general": {
            "from": (
                f"(SELECT {clave_sql} AS programacion, MAX(c.source_part_number) AS part_no, "
                f"{espec_general} AS especificacion, "
                f"SUM(COALESCE(c.qty_actual, 0)) AS stock, COUNT(DISTINCT c.{col_lote}) AS lotes, "
                "SUM(COALESCE(c.qty_actual, 0) > 0) AS lotes_con_stock "
                f"FROM {tabla} c GROUP BY programacion) g"
            ),
            "base": ("g.stock > %s", [0]),
            "fecha": None,
            "cols": [
                ("programacion", "g.programacion", clave_label, 24),
                *extra_g,
                ("especificacion", "g.especificacion", "Especificacion", 30),
                ("stock", "g.stock", "Stock total", 12),
                ("lotes", "g.lotes", "Lotes distintos", 14),
                ("lotes_con_stock", "g.lotes_con_stock", "Lotes con stock", 14),
            ],
            "orden": "g.programacion",
            "suma": "g.stock",
        },
    }


_EXTRAS = {
    "micom": _vistas_procesado(
        "chamber", "control_material_chamber_micom", "chamber_lot",
        "COALESCE(NULLIF(REPLACE(TRIM(COALESCE(NULLIF(c.programming_qr_label_text, ''), "
        "NULLIF(c.micom_label_text, ''))), ' ', '|'), ''), NULLIF(c.source_part_number, ''), 'UNKNOWN')",
        "Lote chamber", "Programacion",
    ),
    # En IPM source_part_number es la misma llave: no se repite como columna.
    # Los lotes UNION guardan "UNION: lote + lote" como especificacion: en el
    # general se prefiere la de un lote armado (origen IPM).
    "ipm": _vistas_procesado(
        "completo", "control_material_completo_ipm", "completo_lot",
        "COALESCE(NULLIF(TRIM(c.ipm_numero_parte), ''), NULLIF(c.source_part_number, ''), 'UNKNOWN')",
        "Lote completo", "Part No IPM", part_no=False,
        espec_general="COALESCE(MAX(CASE WHEN c.origen <> 'UNION' THEN c.source_specification END), "
                      "MAX(c.source_specification))",
    ),
}

VISTAS = {area: {**_vistas(cfg["sfx"]), **_EXTRAS.get(area, {})} for area, cfg in AREAS.items()}


def _vista(area):
    nombre = (request.args.get("vista") or "entradas").strip().lower()
    if nombre not in VISTAS[area]:
        raise ValueError("Vista invalida: " + ", ".join(VISTAS[area]))
    return nombre, VISTAS[area][nombre]


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


@bp.route(f"/material/{_AREA}")
@login_requerido
@_con_permiso
def material_area_ajax(area):
    try:
        return render_template(
            "Control de material/material_area_ajax.html",
            area=area, titulo=AREAS[area]["titulo"], inventarios=AREAS[area]["inventarios"],
        )
    except Exception as e:
        logger.error(f"Error al cargar Control de material {area}: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route(f"/api/material/{_AREA}", methods=["GET"])
@login_requerido
@_con_permiso
def api_material_area(area):
    try:
        _nombre, vista = _vista(area)
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
        logger.error(f"Error en Control de material {area}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route(f"/api/material/{_AREA}/export", methods=["GET"])
@login_requerido
@_con_permiso
def api_material_area_export(area):
    try:
        nombre, vista = _vista(area)
        where, params = _where(vista)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    rows = _filas(vista, where, params, EXPORT_MAX)
    claves, _e, headers, widths = zip(*vista["cols"])
    titulo = AREAS[area]["titulo"]
    # Hoja legible (<=31 chars): "MICOM chamber general", "IPM completo", "SMD inventario general"...
    hoja = nombre.replace("inventario_chamber", "chamber").replace("inventario_completo", "completo").replace("_", " ")
    return excel_response(
        rows, headers, claves, widths, f"{titulo} {hoja}",
        f"Material_{titulo}_{nombre}_{obtener_fecha_hora_mexico():%Y%m%d_%H%M}", freeze="A2",
    )
