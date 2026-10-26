"""Endpoints HTTP del modulo "Process interlock History".

Consumido por LISTA_CONTROL_DE_CALIDAD / Interlock History. Mismo layout y
estilo que el Historial de ICT.

JS cliente: app/static/js/historial_tabla.js (generico)
Template:   app/templates/Control de calidad/process_interlock_history_ajax.html

Rutas:
  GET /process-interlock-history-ajax        -> render template
  GET /api/process-interlock/data            -> listar con filtros + paginacion
  GET /api/process-interlock/opciones        -> lineas / turnos / modos / motivos
  GET /api/process-interlock/export          -> exportar filtrado a Excel
  GET /api/process-interlock/vision/data     -> rechazos del escaner ICT (pestana 2)
  GET /api/process-interlock/vision/opciones
  GET /api/process-interlock/vision/export

Pestana "Rechazos escaner ICT": `vision_check_rejections_QA` la escribe la API de
QualityLock (Bloqueo calidad) cuando la verificacion MES no deja teclear un codigo
del escaner COM en la prueba (sin historial de Vision, ultima inspeccion NG o no es
EBR), y cuando la misma PCB se escanea 2+ veces en una sesion del escaner COM
(REPETIDO, una fila por escaneo). Misma base; aqui solo se lee.

La tabla `interlock_stop_smd` la escribe el proyecto ESCANEO_INPUT (su
`central/src/worker.js`, via applyInterlockStop) sobre la MISMA base
`mes_production`, asi que aqui solo se lee. Una fila = un ciclo de interlock
que detuvo la banda por una causa identificada; responde cuanto tiempo estuvo
parada cada linea y por que.

stop_reason lo clasifica el edge (`backend/src/edge/routes/serial.routes.js`,
`clasificarParo`):
  NOT_SCANNED   la pieza se retiro sin escanear (>= 3s; por debajo es rebote
                del sensor y no se registra)
  SCAN_TARDIO   el escaneo tardo mas que el umbral de alerta (20s)
  SCAN_REJECTED el escaneo se rechazo (sin plan en progreso, etc.)

Reemplaza 2026-09-22 el placeholder de `renders.py`, que solo pintaba un
titulo y un parrafo.
"""

import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request

from app.api.shared import excel_response_ict, execute_query, login_requerido


logger = logging.getLogger(__name__)


bp = Blueprint("process_interlock_history", __name__)


TABLA = "interlock_stop_smd"

# (clave json, etiqueta, columna SQL o None si es derivada)
COLUMNAS = [
    ("fecha", "Fecha", "working_date"),
    ("turno", "Turno", "shift"),
    ("linea", "Linea", "line_code"),
    ("modo", "Modo", "scanner_mode"),
    ("detectado", "Detectado", "detected_at"),
    ("liberado", "Liberado", "released_at"),
    ("duracion", "Duracion", None),  # duration_ms formateado
    ("motivo", "Motivo", "stop_reason"),
    ("cierre", "Cierre", "close_reason"),
    ("detalle", "Detalle", "detail"),
    ("lote", "Lote", "lot_no"),
    ("parte", "No Parte", "part_no"),
    ("ciclo", "Ciclo", "cycle_id"),
]

_COLUMNAS_SQL = {clave: columna for clave, _e, columna in COLUMNAS if columna}

# Deteccion de fraccion de segundo = rebote del sensor / el tiempo que tarda en
# escanear, no un paro. El edge ya usa este mismo umbral
# (NOT_SCANNED_MIN_MS en serial.routes.js) pero hay historico que se colo antes
# de que existiera: son el 77% de las filas y el 0.7% del tiempo detenido.
# Solo se ocultan los NOT_SCANNED: un SCAN_REJECTED de 0.4s si es un error real.
_RUIDO_MS = 3000

_SELECT = (
    "SELECT working_date, shift, line_code, scanner_mode, detected_at, "
    "released_at, duration_ms, stop_reason, close_reason, detail, "
    "lot_no, part_no, cycle_id "
    f"FROM {TABLA} "
)


def _fmt_duracion(ms):
    """1500 -> 1.5s | 36092 -> 36.1s | 3661000 -> 1h 01m 01s."""
    ms = int(ms or 0)
    segundos = ms / 1000
    if segundos < 60:
        return f"{segundos:.1f}s"
    total = int(segundos)
    horas, resto = divmod(total, 3600)
    minutos, seg = divmod(resto, 60)
    if horas:
        return f"{horas}h {minutos:02d}m {seg:02d}s"
    return f"{minutos}m {seg:02d}s"


def _fmt_row(row):
    def _dt(clave):
        valor = row.get(clave)
        return valor.strftime("%Y-%m-%d %H:%M:%S") if valor else ""

    fecha = row.get("working_date")
    return {
        "fecha": fecha.strftime("%Y-%m-%d") if fecha else "",
        "turno": row.get("shift") or "",
        "linea": row.get("line_code") or "",
        "modo": (row.get("scanner_mode") or "").upper(),
        "detectado": _dt("detected_at"),
        "liberado": _dt("released_at"),
        "duracion": _fmt_duracion(row.get("duration_ms")),
        "duracion_ms": int(row.get("duration_ms") or 0),
        "motivo": row.get("stop_reason") or "",
        "cierre": row.get("close_reason") or "",
        "detalle": row.get("detail") or "",
        "lote": row.get("lot_no") or "",
        "parte": row.get("part_no") or "",
        "ciclo": row.get("cycle_id") if row.get("cycle_id") is not None else "",
        # Fila resaltada: SCAN_REJECTED es el error real. NOT_SCANNED es el
        # caso comun (pieza retirada sin escanear) y resaltarlo tinta media
        # tabla de rojo.
        "_destacar": (row.get("stop_reason") or "") == "SCAN_REJECTED",
    }


def _build_where():
    """WHERE + params de la request. Nombres de columna desde la allowlist."""
    where_sql = "WHERE 1=1"
    params = []

    def _add(clause, *vals):
        nonlocal where_sql
        where_sql += " " + clause
        params.extend(vals)

    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    if fecha_desde:
        _add("AND working_date>=%s", fecha_desde)
    if fecha_hasta:
        _add("AND working_date<=%s", fecha_hasta)

    for arg, columna in (
        ("linea", "line_code"),
        ("turno", "shift"),
        ("modo", "scanner_mode"),
        ("motivo", "stop_reason"),
    ):
        valor = request.args.get(arg, "").strip()
        if valor:
            _add(f"AND {columna}=%s", valor)

    # "Paros de mas de N segundos": la pregunta operativa tipica.
    min_seg = request.args.get("min_seg", "").strip()
    if min_seg:
        try:
            _add("AND duration_ms>=%s", int(float(min_seg) * 1000))
        except ValueError:
            pass

    # Por defecto fuera el ruido; el checkbox del fragmento lo vuelve a incluir.
    if request.args.get("incluir_cortos", "").strip() not in ("1", "true", "on"):
        _add("AND NOT (stop_reason=%s AND duration_ms<%s)", "NOT_SCANNED", _RUIDO_MS)

    busqueda = request.args.get("busqueda", "").strip()
    if busqueda:
        patron = f"%{busqueda}%"
        _add(
            "AND (detail LIKE %s OR lot_no LIKE %s OR part_no LIKE %s)",
            patron, patron, patron,
        )

    for clave, columna in _COLUMNAS_SQL.items():
        valor = request.args.get(f"cf_{clave}", "").strip()
        if valor:
            _add(f"AND CAST({columna} AS CHAR) LIKE %s", f"%{valor}%")

    # `duracion` se muestra formateada; el filtro del encabezado se aplica
    # sobre los segundos, que es lo que la gente escribe ("mas de 30").
    cf_duracion = request.args.get("cf_duracion", "").strip()
    if cf_duracion:
        try:
            _add("AND duration_ms>=%s", int(float(cf_duracion) * 1000))
        except ValueError:
            _add("AND 1=0")

    return where_sql, params


def _paginacion():
    """(page, per_page) de la request; per_page entre 1 y 1000."""
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get("per_page", "1000"))
    except ValueError:
        per_page = 1000
    return page, max(1, min(per_page, 1000))


# ---------------------------------------------------------------------------
# Rechazos del escaner ICT (vision_check_rejections_QA)
# ---------------------------------------------------------------------------

TABLA_VISION = "vision_check_rejections_QA"

# La tabla guarda UTC (como todas las _QA). Mexico no tiene horario de verano
# desde 2022: -06:00 fijo, igual que la vista historial_estaciones_QA.
_UTC_A_LOCAL = timedelta(hours=-6)
_HORA_LOCAL_SQL = "CONVERT_TZ(rejected_at_utc, '+00:00', '-06:00')"

VISION_TIPOS = {
    "SIN_HISTORIAL": "Sin historial",
    "NG": "NG en Vision",
    "NO_EBR": "No es EBR",
    # No es rechazo: misma PCB escaneada 2+ veces en una sesion del escaner COM (una fila
    # por escaneo, con su hora). El codigo si se tecleo en la prueba.
    "REPETIDO": "Escaneo repetido",
}

VISION_COLUMNAS = [
    ("hora", "Fecha / hora", _HORA_LOCAL_SQL),
    ("estacion", "Estacion", "station_code"),
    ("linea", "Linea", "line"),
    ("codigo", "Codigo", "code"),
    ("tipo", "Tipo", None),  # rejection_type con etiqueta legible
    ("motivo", "Motivo", "reason"),
    ("maquina", "Maquina Vision", "machine"),
    ("inspeccion", "Ultima inspeccion", "inspected_at"),
]

_VISION_SELECT = (
    f"SELECT {_HORA_LOCAL_SQL} AS hora, station_code, line, code, rejection_type, "
    f"reason, machine, inspected_at FROM {TABLA_VISION} "
)


def _vision_tipos_que_coinciden(texto):
    """Codigos de rejection_type cuya etiqueta o codigo contiene el texto ("sin" -> SIN_HISTORIAL)."""
    texto = texto.strip().lower()
    return [
        codigo for codigo, etiqueta in VISION_TIPOS.items()
        if texto in etiqueta.lower() or texto in codigo.lower()
    ]


def _fmt_vision_row(row):
    def _dt(clave):
        valor = row.get(clave)
        return valor.strftime("%Y-%m-%d %H:%M:%S") if valor else ""

    tipo = row.get("rejection_type") or ""
    return {
        "hora": _dt("hora"),
        "estacion": row.get("station_code") or "",
        "linea": row.get("line") or "",
        "codigo": row.get("code") or "",
        "tipo": VISION_TIPOS.get(tipo, tipo),
        "motivo": row.get("reason") or "",
        "maquina": row.get("machine") or "",
        "inspeccion": _dt("inspected_at"),
        # La pieza llego a la prueba con NG en Vision: el caso grave.
        "_destacar": tipo == "NG",
    }


def _build_vision_where():
    """WHERE + params de la pestana de rechazos. Fechas en hora local -> rango UTC."""
    where_sql = "WHERE 1=1"
    params = []

    def _add(clause, *vals):
        nonlocal where_sql
        where_sql += " " + clause
        params.extend(vals)

    for arg, dias in (("fecha_desde", 0), ("fecha_hasta", 1)):
        valor = request.args.get(arg, "").strip()
        if not valor:
            continue
        try:
            dia = datetime.strptime(valor, "%Y-%m-%d") + timedelta(days=dias)
        except ValueError:
            continue
        # Medianoche local -> UTC; rejected_at_utc tiene indice (no se envuelve en funciones).
        limite = (dia - _UTC_A_LOCAL).strftime("%Y-%m-%d %H:%M:%S")
        _add("AND rejected_at_utc>=%s" if dias == 0 else "AND rejected_at_utc<%s", limite)

    for arg, columna in (("linea", "line"), ("estacion", "station_code")):
        valor = request.args.get(arg, "").strip()
        if valor:
            _add(f"AND {columna}=%s", valor)

    tipo = request.args.get("tipo", "").strip()
    if tipo:
        codigos = _vision_tipos_que_coinciden(tipo) or [""]
        _add(f"AND rejection_type IN ({','.join(['%s'] * len(codigos))})", *codigos)

    busqueda = request.args.get("busqueda", "").strip()
    if busqueda:
        patron = f"%{busqueda}%"
        _add("AND (code LIKE %s OR reason LIKE %s)", patron, patron)

    for clave, _e, columna in VISION_COLUMNAS:
        valor = request.args.get(f"cf_{clave}", "").strip()
        if not valor:
            continue
        if clave == "tipo":
            codigos = _vision_tipos_que_coinciden(valor) or [""]
            _add(f"AND rejection_type IN ({','.join(['%s'] * len(codigos))})", *codigos)
        else:
            _add(f"AND CAST({columna} AS CHAR) LIKE %s", f"%{valor}%")

    return where_sql, params


# ---------------------------------------------------------------------------
# Render template
# ---------------------------------------------------------------------------


@bp.route("/process-interlock-history-ajax")
@login_requerido
def process_interlock_history_ajax():
    """Fragmento AJAX del historial de paros del interlock."""
    try:
        return render_template(
            "Control de calidad/process_interlock_history_ajax.html",
            columnas=[(clave, etiqueta) for clave, etiqueta, _c in COLUMNAS],
            columnas_vision=[(clave, etiqueta) for clave, etiqueta, _c in VISION_COLUMNAS],
        )
    except Exception as e:
        logger.error(f"Error al cargar Process interlock History: {e}")
        return f"Error al cargar el contenido: {e}", 500


# ---------------------------------------------------------------------------
# APIs
# ---------------------------------------------------------------------------


@bp.route("/api/process-interlock/data")
@login_requerido
def process_interlock_data():
    """Paros con filtros y paginacion.

    Ademas del total de filas devuelve `total_ms`: el tiempo detenido que
    suman TODOS los registros filtrados, no solo la pagina. Es el dato por el
    que existe la tabla.
    """
    try:
        where_sql, params = _build_where()

        page, per_page = _paginacion()

        resumen = execute_query(
            f"SELECT COUNT(*) AS n, COALESCE(SUM(duration_ms),0) AS ms FROM {TABLA} "
            + where_sql,
            tuple(params),
            fetch="one",
        ) or {}
        total = int(resumen.get("n", 0))
        total_ms = int(resumen.get("ms", 0))

        offset = (page - 1) * per_page
        rows = execute_query(
            _SELECT + where_sql + " ORDER BY detected_at DESC LIMIT %s OFFSET %s",
            tuple(params) + (per_page, offset),
            fetch="all",
        ) or []

        return jsonify({
            "rows": [_fmt_row(row) for row in rows],
            "total": total,
            "total_ms": total_ms,
            "total_detenido": _fmt_duracion(total_ms),
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        })
    except Exception as e:
        logger.exception("Error en /api/process-interlock/data")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/process-interlock/opciones")
@login_requerido
def process_interlock_opciones():
    """Valores distintos para poblar los selects de los filtros."""
    try:
        def distintos(columna):
            filas = execute_query(
                f"SELECT DISTINCT {columna} AS v FROM {TABLA} "
                f"WHERE {columna} IS NOT NULL AND {columna}<>'' ORDER BY {columna}",
                fetch="all",
            ) or []
            return [f["v"] for f in filas]

        # Cada clave nombra el sufijo del <select> que rellena (contrato de
        # historial_tabla.js): pih-linea, pih-turno, pih-modo, pih-motivo.
        return jsonify({
            "linea": distintos("line_code"),
            "turno": distintos("shift"),
            "modo": distintos("scanner_mode"),
            "motivo": distintos("stop_reason"),
        })
    except Exception as e:
        logger.exception("Error en /api/process-interlock/opciones")
        return jsonify({
            "error": str(e),
            "linea": [], "turno": [], "modo": [], "motivo": [],
        }), 500


@bp.route("/api/process-interlock/export")
@login_requerido
def process_interlock_export():
    """Exportar los paros filtrados a Excel (mismos filtros que /data)."""
    try:
        where_sql, params = _build_where()
        rows = execute_query(
            _SELECT + where_sql + " ORDER BY detected_at DESC LIMIT 10000",
            tuple(params),
            fetch="all",
        ) or []
        claves = [clave for clave, _e, _c in COLUMNAS]
        headers = [etiqueta for _k, etiqueta, _c in COLUMNAS]
        return excel_response_ict(
            [_fmt_row(row) for row in rows],
            headers,
            claves,
            widths=[16] * len(headers),
            sheet="Process interlock",
            filename=(
                "process_interlock_history_"
                + datetime.now().strftime("%Y%m%d_%H%M%S")
            ),
        )
    except Exception as e:
        logger.exception("Error en /api/process-interlock/export")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/process-interlock/vision/data")
@login_requerido
def process_interlock_vision_data():
    """Rechazos del escaner ICT con filtros y paginacion (mas recientes primero)."""
    try:
        where_sql, params = _build_vision_where()
        page, per_page = _paginacion()

        resumen = execute_query(
            f"SELECT COUNT(*) AS n FROM {TABLA_VISION} " + where_sql,
            tuple(params),
            fetch="one",
        ) or {}
        total = int(resumen.get("n", 0))

        rows = execute_query(
            _VISION_SELECT + where_sql + " ORDER BY id DESC LIMIT %s OFFSET %s",
            tuple(params) + (per_page, (page - 1) * per_page),
            fetch="all",
        ) or []

        return jsonify({
            "rows": [_fmt_vision_row(row) for row in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        })
    except Exception as e:
        logger.exception("Error en /api/process-interlock/vision/data")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/process-interlock/vision/opciones")
@login_requerido
def process_interlock_vision_opciones():
    """Lineas y estaciones con rechazos, y los tipos (pvr-linea, pvr-estacion, pvr-tipo)."""
    try:
        def distintos(columna):
            filas = execute_query(
                f"SELECT DISTINCT {columna} AS v FROM {TABLA_VISION} "
                f"WHERE {columna}<>'' ORDER BY {columna}",
                fetch="all",
            ) or []
            return [f["v"] for f in filas]

        return jsonify({
            "linea": distintos("line"),
            "estacion": distintos("station_code"),
            "tipo": list(VISION_TIPOS.values()),
        })
    except Exception as e:
        logger.exception("Error en /api/process-interlock/vision/opciones")
        return jsonify({
            "error": str(e),
            "linea": [], "estacion": [], "tipo": list(VISION_TIPOS.values()),
        }), 500


@bp.route("/api/process-interlock/vision/export")
@login_requerido
def process_interlock_vision_export():
    """Exportar los rechazos filtrados a Excel (mismos filtros que /vision/data)."""
    try:
        where_sql, params = _build_vision_where()
        rows = execute_query(
            _VISION_SELECT + where_sql + " ORDER BY id DESC LIMIT 10000",
            tuple(params),
            fetch="all",
        ) or []
        return excel_response_ict(
            [_fmt_vision_row(row) for row in rows],
            [etiqueta for _k, etiqueta, _c in VISION_COLUMNAS],
            [clave for clave, _e, _c in VISION_COLUMNAS],
            widths=[20, 12, 10, 28, 16, 60, 14, 20],
            sheet="Rechazos escaner ICT",
            filename=(
                "rechazos_escaner_ict_"
                + datetime.now().strftime("%Y%m%d_%H%M%S")
            ),
        )
    except Exception as e:
        logger.exception("Error en /api/process-interlock/vision/export")
        return jsonify({"error": str(e)}), 500
