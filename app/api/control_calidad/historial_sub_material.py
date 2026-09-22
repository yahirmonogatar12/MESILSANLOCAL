"""Endpoints HTTP de "Historial de Sub Material": pasta, metal mask y squeegee.

Consumido por LISTA_CONTROL_DE_CALIDAD / Historial de Sub Material. Mismo
layout y estilo que el Historial de ICT.

JS cliente: app/static/js/historial_tabla.js (generico)
Template:   app/templates/Control de calidad/historial_sub_material_ajax.html

Rutas (las de render conservan su URL historica para no tocar sidebar ni
permisos; `<tipo>` es pasta, mask o squeegee):
  GET /historial-uso-pegamento-soldadura-ajax     -> render pasta
  GET /historial-uso-mask-metal-ajax              -> render mask
  GET /historial-uso-squeegee-ajax                -> render squeegee
  GET /api/historial-sub-material/<tipo>/data     -> listar + paginacion
  GET /api/historial-sub-material/<tipo>/opciones -> valores de los selects
  GET /api/historial-sub-material/<tipo>/export   -> exportar a Excel

Origen de los datos (todo en `mes_production`, solo lectura):
  - pasta: `solder_paste_process_smd`, que escribe Control_inventario_SMD. Una
    fila = un ciclo de un bote de pasta: sale de frio -> llega a ambiente ->
    se agita -> entra a linea -> se consume / scrap / regresa a frio.
  - mask y squeegee: `tooling_plan_assignment_smd`, que escribe ESCANEO_INPUT
    al autorizar un plan SMT. Una fila = una asignacion de herramental a un
    plan, y lleva el metal mask y hasta dos squeegees.

2026-09-22: reemplaza los tres modulos anteriores. El de mask leia
`metal_mask_history`, que tiene 1 fila de prueba mientras el uso real se
registra en `tooling_plan_assignment_smd`; los de pasta y squeegee eran
placeholders sin datos.

ponytail: un modulo parametrizado por tipo, no tres copias. Mask y squeegee
comparten tabla y solo cambian de columna de herramental.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import Blueprint, abort, jsonify, render_template, request

from app.api.shared import excel_response_ict, execute_query, login_requerido


logger = logging.getLogger(__name__)


bp = Blueprint("historial_sub_material", __name__)


_COLUMNAS_TOOLING_COMUNES = [
    ("fecha", "Fecha", "working_date"),
    ("turno", "Turno", "shift"),
    ("linea", "Linea", "line_code"),
]
_COLUMNAS_TOOLING_COLA = [
    ("lote", "Lote", "lot_no"),
    ("parte", "No Parte", "part_no"),
    ("modelo", "Modelo", "model_code"),
    ("plan", "Plan", "plan_count"),
    ("usos", "Usos Planeados", "planned_uses"),
    ("origen", "Origen", "count_source"),
    ("asignado", "Asignado", "assigned_at"),
]

_TIPOS = {
    "pasta": {
        "tabla": "solder_paste_process_smd",
        "titulo": "Historial de uso de pegamento de soldadura",
        "orden": "removed_from_cold_at DESC, id DESC",
        "fecha_sql": "DATE(removed_from_cold_at)",
        "columnas": [
            ("codigo", "Codigo Material", "codigo_material_recibido"),
            ("parte", "No Parte", "numero_parte"),
            ("lote", "Lote", "numero_lote"),
            ("ciclo", "Ciclo", "cycle_no"),
            ("estado", "Estado", "status"),
            ("linea", "Linea", "line_code"),
            ("sacado_frio", "Sacado de Frio", "removed_from_cold_at"),
            ("listo_ambiente", "Listo Ambiente", "ambient_ready_at"),
            ("agitado", "Agitacion Lista", "agitation_completed_at"),
            ("en_linea", "En Linea", "line_started_at"),
            ("expira", "Expira", "expires_at"),
            ("consumido", "Consumido", "consumed_at"),
            ("cantidad", "Cantidad", "issued_quantity"),
            ("unidad", "Unidad", "unit"),
            ("operador", "Operador", "started_by"),
        ],
        # sufijo del <select> -> columna
        "selects": {"linea": "line_code", "estado": "status"},
        "codigo_sql": ["codigo_material_recibido"],
        "busqueda_sql": ["codigo_material_recibido", "numero_parte", "numero_lote"],
        "destacar": ("status", {"SCRAP", "CANCELLED"}),
    },
    "mask": {
        "tabla": "tooling_plan_assignment_smd",
        "titulo": "Historial de uso de mask de metal",
        "orden": "assigned_at DESC",
        "fecha_sql": "working_date",
        "columnas": (
            _COLUMNAS_TOOLING_COMUNES
            + [("mask", "Metal Mask", "metal_mask_code")]
            + _COLUMNAS_TOOLING_COLA
        ),
        "selects": {"linea": "line_code", "turno": "shift"},
        "codigo_sql": ["metal_mask_code"],
        "busqueda_sql": ["lot_no", "part_no", "model_code"],
        "destacar": None,
    },
    "squeegee": {
        "tabla": "tooling_plan_assignment_smd",
        "titulo": "Historial de uso de squeegee",
        "orden": "assigned_at DESC",
        "fecha_sql": "working_date",
        "columnas": (
            _COLUMNAS_TOOLING_COMUNES
            + [
                ("squeegee", "Squeegee", "squeegee_code"),
                ("squeegee_2", "Squeegee 2", "squeegee_code_2"),
            ]
            + _COLUMNAS_TOOLING_COLA
        ),
        "selects": {"linea": "line_code", "turno": "shift"},
        # Un plan lleva hasta dos squeegees: el filtro busca en los dos.
        "codigo_sql": ["squeegee_code", "squeegee_code_2"],
        "busqueda_sql": ["lot_no", "part_no", "model_code"],
        "destacar": None,
    },
}

# Render historico -> tipo. Se conservan para no tocar sidebar ni permisos.
_RUTAS_RENDER = {
    "/historial-uso-pegamento-soldadura-ajax": "pasta",
    "/historial-uso-mask-metal-ajax": "mask",
    "/historial-uso-squeegee-ajax": "squeegee",
}


def _tipo_o_404(tipo):
    cfg = _TIPOS.get((tipo or "").lower())
    if not cfg:
        abort(404)
    return cfg


def _fmt_valor(valor):
    """Valor listo para la tabla: fechas legibles, numeros sin ruido."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(valor, date):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, timedelta):  # MySQL TIME
        total = int(valor.total_seconds())
        return f"{total // 3600:02d}:{total // 60 % 60:02d}:{total % 60:02d}"
    if isinstance(valor, Decimal):
        # 500.0000 -> 500 ; 2.5000 -> 2.5
        return f"{valor.normalize():f}"
    return valor


def _fmt_row(row, cfg):
    salida = {
        clave: _fmt_valor(row.get(columna))
        for clave, _etiqueta, columna in cfg["columnas"]
    }
    destacar = cfg["destacar"]
    if destacar:
        columna, malos = destacar
        salida["_destacar"] = str(row.get(columna) or "").upper() in malos
    else:
        salida["_destacar"] = False
    return salida


def _build_where(cfg):
    """WHERE + params de la request. Columnas siempre desde `cfg`."""
    where_sql = "WHERE 1=1"
    params = []

    def _add(clause, *vals):
        nonlocal where_sql
        where_sql += " " + clause
        params.extend(vals)

    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    if fecha_desde:
        _add(f"AND {cfg['fecha_sql']}>=%s", fecha_desde)
    if fecha_hasta:
        _add(f"AND {cfg['fecha_sql']}<=%s", fecha_hasta)

    for sufijo, columna in cfg["selects"].items():
        valor = request.args.get(sufijo, "").strip()
        if valor:
            _add(f"AND {columna}=%s", valor)

    codigo = request.args.get("codigo", "").strip()
    if codigo:
        columnas = cfg["codigo_sql"]
        _add(
            "AND (" + " OR ".join(f"{c} LIKE %s" for c in columnas) + ")",
            *[f"%{codigo}%"] * len(columnas),
        )

    busqueda = request.args.get("busqueda", "").strip()
    if busqueda:
        columnas = cfg["busqueda_sql"]
        _add(
            "AND (" + " OR ".join(f"{c} LIKE %s" for c in columnas) + ")",
            *[f"%{busqueda}%"] * len(columnas),
        )

    for clave, _etiqueta, columna in cfg["columnas"]:
        valor = request.args.get(f"cf_{clave}", "").strip()
        if valor:
            _add(f"AND CAST({columna} AS CHAR) LIKE %s", f"%{valor}%")

    return where_sql, params


def _select(cfg):
    columnas = [columna for _k, _e, columna in cfg["columnas"]]
    if cfg["destacar"]:
        extra = cfg["destacar"][0]
        if extra not in columnas:
            columnas.append(extra)
    return f"SELECT {', '.join(columnas)} FROM {cfg['tabla']} "


# ---------------------------------------------------------------------------
# Render template (URLs historicas)
# ---------------------------------------------------------------------------


def _render(tipo):
    cfg = _TIPOS[tipo]
    try:
        return render_template(
            "Control de calidad/historial_sub_material_ajax.html",
            tipo=tipo,
            titulo=cfg["titulo"],
            selects=sorted(cfg["selects"]),
            columnas=[(clave, etiqueta) for clave, etiqueta, _c in cfg["columnas"]],
        )
    except Exception as e:
        logger.error(f"Error al cargar Historial de sub material {tipo}: {e}")
        return f"Error al cargar el contenido: {e}", 500


@bp.route("/historial-uso-pegamento-soldadura-ajax")
@login_requerido
def historial_uso_pegamento_soldadura_ajax():
    """Historial de uso de pegamento de soldadura (pasta)."""
    return _render("pasta")


@bp.route("/historial-uso-mask-metal-ajax")
@login_requerido
def historial_uso_mask_metal_ajax():
    """Historial de uso de mask de metal."""
    return _render("mask")


@bp.route("/historial-uso-squeegee-ajax")
@login_requerido
def historial_uso_squeegee_ajax():
    """Historial de uso de squeegee."""
    return _render("squeegee")


# ---------------------------------------------------------------------------
# APIs
# ---------------------------------------------------------------------------


@bp.route("/api/historial-sub-material/<tipo>/data")
@login_requerido
def historial_sub_material_data(tipo):
    """Registros con filtros y paginacion.

    Paginacion: `page` (1-based) y `per_page` (default 1000, max 1000).
    """
    cfg = _tipo_o_404(tipo)
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
            + f" ORDER BY {cfg['orden']} LIMIT %s OFFSET %s",
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
        logger.exception("Error en /api/historial-sub-material/%s/data", tipo)
        return jsonify({"error": str(e)}), 500


@bp.route("/api/historial-sub-material/<tipo>/opciones")
@login_requerido
def historial_sub_material_opciones(tipo):
    """Valores distintos de cada select. La clave nombra el sufijo del <select>."""
    cfg = _tipo_o_404(tipo)
    try:
        salida = {}
        for sufijo, columna in cfg["selects"].items():
            filas = execute_query(
                f"SELECT DISTINCT {columna} AS v FROM {cfg['tabla']} "
                f"WHERE {columna} IS NOT NULL AND {columna}<>'' ORDER BY {columna}",
                fetch="all",
            ) or []
            salida[sufijo] = [f["v"] for f in filas]
        return jsonify(salida)
    except Exception as e:
        logger.exception("Error en /api/historial-sub-material/%s/opciones", tipo)
        return jsonify({"error": str(e), **{s: [] for s in cfg["selects"]}}), 500


@bp.route("/api/historial-sub-material/<tipo>/export")
@login_requerido
def historial_sub_material_export(tipo):
    """Exportar lo filtrado a Excel (mismos filtros que /data)."""
    cfg = _tipo_o_404(tipo)
    try:
        where_sql, params = _build_where(cfg)
        rows = execute_query(
            _select(cfg) + where_sql + f" ORDER BY {cfg['orden']} LIMIT 10000",
            tuple(params),
            fetch="all",
        ) or []
        claves = [clave for clave, _e, _c in cfg["columnas"]]
        headers = [etiqueta for _k, etiqueta, _c in cfg["columnas"]]
        return excel_response_ict(
            [_fmt_row(row, cfg) for row in rows],
            headers,
            claves,
            widths=[18] * len(headers),
            sheet=f"Historial {tipo}",
            filename=(
                f"historial_sub_material_{tipo}_"
                + datetime.now().strftime("%Y%m%d_%H%M%S")
            ),
        )
    except Exception as e:
        logger.exception("Error en /api/historial-sub-material/%s/export", tipo)
        return jsonify({"error": str(e)}), 500
