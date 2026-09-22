"""Endpoints HTTP de "Historial de cambio de material" de IMD y ASSY.

Consumido por LISTA_CONTROL_DE_CALIDAD / Historial de material, junto al de
SMT (`smt_historial.py`). Mismo layout y estilo que el Historial de ICT.

JS cliente: app/static/js/historial_tabla.js (generico)
Template:   app/templates/Control de calidad/historial_material_area_ajax.html

Rutas (`<area>` es imd o assy):
  GET /historial-material/<area>/ajax        -> render template
  GET /api/historial-material/<area>/data    -> listar con filtros + paginacion
  GET /api/historial-material/<area>/opciones-> lineas disponibles
  GET /api/historial-material/<area>/export  -> exportar filtrado a Excel

Las tablas `history_material_imd` / `history_material_assy` las escribe el
proyecto "Verificacion BOM" (server-node) sobre la MISMA base `mes_production`,
asi que aqui solo se leen. Esquema casi identico entre areas; la unica
diferencia es que ASSY tiene columna `ubicacion` e IMD no.

ponytail: un solo modulo parametrizado por area en vez de dos copias. Si
manana aparece una tercera area, se agrega una entrada en `_AREAS`.
"""

import logging
from datetime import datetime

from flask import Blueprint, abort, jsonify, render_template, request

from app.api.shared import excel_response_ict, execute_query, login_requerido


logger = logging.getLogger(__name__)


bp = Blueprint("historial_material_areas", __name__)


# Columnas comunes a las dos areas, en el orden en que se muestran.
_COLUMNAS_BASE = [
    # (clave json, etiqueta, columna SQL)
    ("fecha", "Fecha", "fecha"),
    ("hora", "Hora", "hora"),
    ("linea", "Linea", "linea"),
    ("tipo", "Tipo", None),  # derivada del contenedor/posicion
    ("contenedor", "Contenedor", "contenedor"),
    ("material", "Material", "material"),
    ("posicion", "Posicion", "posicion"),
    ("lote_proveedor", "Lote Proveedor", "lote_proveedor"),
]
_COLUMNAS_COLA = [
    ("proveedor", "Proveedor", "proveedor"),
    ("spec", "Spec", "spec"),
    ("qty", "Qty", "qty"),
    ("resultado", "Resultado", "result"),
]

_AREAS = {
    "imd": {
        "tabla": "history_material_imd",
        "titulo": "Historial de cambio de material de IMD",
        "columnas": _COLUMNAS_BASE + _COLUMNAS_COLA,
    },
    "assy": {
        "tabla": "history_material_assy",
        "titulo": "Historial de cambio de material de ASSY",
        "columnas": (
            _COLUMNAS_BASE
            + [("ubicacion", "Ubicacion", "ubicacion")]
            + _COLUMNAS_COLA
        ),
    },
}


def _area_o_404(area):
    cfg = _AREAS.get((area or "").lower())
    if not cfg:
        abort(404)
    return cfg


def _tipo(contenedor, posicion):
    """MD / RACK / CNT, igual que el cliente Flutter de Verificacion BOM."""
    if str(contenedor or "").startswith("MD-"):
        return "MD"
    if str(posicion or "").upper().startswith("RACK"):
        return "RACK"
    return "CNT"


def _fmt_row(row, cfg):
    salida = {}
    for clave, _etiqueta, columna in cfg["columnas"]:
        if clave == "tipo":
            salida[clave] = _tipo(row.get("contenedor"), row.get("posicion"))
        elif clave == "fecha":
            fecha = row.get("fecha")
            salida[clave] = fecha.strftime("%Y-%m-%d") if fecha else ""
        elif clave == "hora":
            # MySQL devuelve TIME como timedelta.
            hora = row.get("hora")
            if hora is None:
                salida[clave] = ""
            else:
                total = int(getattr(hora, "total_seconds", lambda: 0)())
                salida[clave] = f"{total // 3600:02d}:{total // 60 % 60:02d}:{total % 60:02d}"
        else:
            valor = row.get(columna)
            salida[clave] = "" if valor is None else valor
    # Fila resaltada en la tabla: aqui lo malo es un material rechazado.
    salida["_destacar"] = str(row.get("result") or "").upper() == "NG"
    return salida


def _build_where(cfg):
    """WHERE + params de la request. Los nombres de columna salen de `cfg`."""
    where_sql = "WHERE 1=1"
    params = []

    def _add(clause, *vals):
        nonlocal where_sql
        where_sql += " " + clause
        params.extend(vals)

    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    if fecha_desde:
        _add("AND fecha>=%s", fecha_desde)
    if fecha_hasta:
        _add("AND fecha<=%s", fecha_hasta)

    linea = request.args.get("linea", "").strip()
    if linea:
        _add("AND linea=%s", linea)

    material = request.args.get("material", "").strip()
    if material:
        _add("AND material LIKE %s", f"{material}%")

    resultado = request.args.get("resultado", "").strip()
    if resultado:
        _add("AND result=%s", resultado)

    contenedor = request.args.get("contenedor", "").strip()
    if contenedor:
        _add("AND contenedor LIKE %s", f"%{contenedor}%")

    # Filtros por encabezado.
    columnas_sql = {
        clave: columna for clave, _e, columna in cfg["columnas"] if columna
    }
    for clave, columna in columnas_sql.items():
        valor = request.args.get(f"cf_{clave}", "").strip()
        if valor:
            _add(f"AND CAST({columna} AS CHAR) LIKE %s", f"%{valor}%")

    # `tipo` no es columna: se deriva igual que en `_tipo()`, pero en SQL para
    # que el filtro por encabezado abarque toda la tabla y no solo la pagina.
    # Los patrones van parametrizados: un '%' literal dentro del SQL rompe el
    # formateo de pymysql cuando la query lleva params.
    tipo = request.args.get("cf_tipo", "").strip().upper()
    if tipo:
        if "MD".startswith(tipo):
            _add("AND contenedor LIKE %s", "MD-%")
        elif "RACK".startswith(tipo):
            _add("AND contenedor NOT LIKE %s AND posicion LIKE %s", "MD-%", "RACK%")
        elif "CNT".startswith(tipo):
            _add("AND contenedor NOT LIKE %s AND posicion NOT LIKE %s", "MD-%", "RACK%")
        else:
            _add("AND 1=0")  # texto que no corresponde a ningun tipo

    return where_sql, params


def _select(cfg):
    columnas = sorted({c for _k, _e, c in cfg["columnas"] if c} | {"contenedor", "posicion"})
    return f"SELECT {', '.join(columnas)} FROM {cfg['tabla']} "


# ---------------------------------------------------------------------------
# Render template
# ---------------------------------------------------------------------------


@bp.route("/historial-material/<area>/ajax")
@login_requerido
def historial_material_area_ajax(area):
    """Fragmento AJAX del historial de material de un area."""
    cfg = _area_o_404(area)
    try:
        return render_template(
            "Control de calidad/historial_material_area_ajax.html",
            area=area.lower(),
            titulo=cfg["titulo"],
            columnas=[(clave, etiqueta) for clave, etiqueta, _c in cfg["columnas"]],
        )
    except Exception as e:
        logger.error(f"Error al cargar Historial de material {area}: {e}")
        return f"Error al cargar el contenido: {e}", 500


# ---------------------------------------------------------------------------
# APIs
# ---------------------------------------------------------------------------


@bp.route("/api/historial-material/<area>/data")
@login_requerido
def historial_material_area_data(area):
    """Registros con filtros y paginacion.

    Paginacion: `page` (1-based) y `per_page` (default 1000, max 1000).
    Respuesta: { rows, total, page, per_page, total_pages }.
    """
    cfg = _area_o_404(area)
    try:
        where_sql, params = _build_where(cfg)

        try:
            page = max(1, int(request.args.get("page", "1")))
        except ValueError:
            page = 1
        try:
            per_page = int(request.args.get("per_page", "1000"))
        except ValueError:
            per_page = 1000
        per_page = max(1, min(per_page, 1000))

        count_row = execute_query(
            f"SELECT COUNT(*) AS n FROM {cfg['tabla']} " + where_sql,
            tuple(params),
            fetch="one",
        ) or {}
        total = int(count_row.get("n", 0))

        offset = (page - 1) * per_page
        rows = execute_query(
            _select(cfg) + where_sql
            + " ORDER BY fecha DESC, hora DESC LIMIT %s OFFSET %s",
            tuple(params) + (per_page, offset),
            fetch="all",
        ) or []

        return jsonify({
            "rows": [_fmt_row(row, cfg) for row in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        })
    except Exception as e:
        logger.exception("Error en /api/historial-material/%s/data", area)
        return jsonify({"error": str(e)}), 500


@bp.route("/api/historial-material/<area>/opciones")
@login_requerido
def historial_material_area_opciones(area):
    """Lineas distintas del area, para poblar el select."""
    cfg = _area_o_404(area)
    try:
        lineas = execute_query(
            f"SELECT DISTINCT linea FROM {cfg['tabla']} "
            "WHERE linea IS NOT NULL AND linea<>'' ORDER BY linea",
            fetch="all",
        ) or []
        # La clave nombra el sufijo del <select> que rellena (contrato de
        # historial_tabla.js), no el plural.
        return jsonify({"linea": [r["linea"] for r in lineas]})
    except Exception as e:
        logger.exception("Error en /api/historial-material/%s/opciones", area)
        return jsonify({"error": str(e), "linea": []}), 500


@bp.route("/api/historial-material/<area>/export")
@login_requerido
def historial_material_area_export(area):
    """Exportar el historial filtrado a Excel (mismos filtros que /data)."""
    cfg = _area_o_404(area)
    try:
        where_sql, params = _build_where(cfg)
        rows = execute_query(
            _select(cfg) + where_sql
            + " ORDER BY fecha DESC, hora DESC LIMIT 10000",
            tuple(params),
            fetch="all",
        ) or []
        claves = [clave for clave, _e, _c in cfg["columnas"]]
        headers = [etiqueta for _k, etiqueta, _c in cfg["columnas"]]
        return excel_response_ict(
            [_fmt_row(row, cfg) for row in rows],
            headers,
            claves,
            widths=[16] * len(headers),
            sheet=f"Historial {area.upper()}",
            filename=(
                f"historial_material_{area.lower()}_"
                + datetime.now().strftime("%Y%m%d_%H%M%S")
            ),
        )
    except Exception as e:
        logger.exception("Error en /api/historial-material/%s/export", area)
        return jsonify({"error": str(e)}), 500
