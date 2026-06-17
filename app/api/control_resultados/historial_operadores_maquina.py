"""Historial de Operadores por Maquina (solo lectura).

Consulta la vista MySQL `historial_estaciones_qa` (JOIN de
`station_sessions_qa` + `stations_qa` + `operators_qa`, con horas ya
convertidas de UTC a -06:00). Los datos los genera el proyecto externo
"Bloqueo calidad" (QualityLock.Api); aqui NO se modifica nada.

WF_001: opcion en LISTA_DE_CONTROL_DE_RESULTADOS / Historial de maquinas calidad.
WF_002: template AJAX en Control de resultados/historial_operadores_maquina_ajax.html.
WF_003: blueprint dueno del render y la API JSON.
WF_004: CSS persistente en MainTemplate.html y asegurado desde JS.

Rutas:
  GET /control_resultados/historial_operadores_maquina      -> render template
  GET /api/control_resultados/historial_operadores_maquina  -> sesiones (JSON)
"""

import datetime
import logging

from flask import Blueprint, jsonify, render_template, request

from app.api.shared import (
    excel_response,
    execute_query,
    formatear_fecha,
    formatear_fecha_hora,
    formatear_hora,
    login_requerido,
    obtener_fecha_mexico,
    requiere_permiso_dropdown,
    sanitizar_texto,
)

logger = logging.getLogger(__name__)

bp = Blueprint("control_resultados_historial_operadores_maquina", __name__)

PERMISO_PAGINA = "LISTA_DE_CONTROL_DE_RESULTADOS"
PERMISO_SECCION = "Historial de maquinas calidad"
PERMISO_BOTON = "Historial de Operadores por Maquina"

_requiere_permiso = requiere_permiso_dropdown(
    PERMISO_PAGINA, PERMISO_SECCION, PERMISO_BOTON
)

TIPOS = {"ICT", "FCT", "Packing"}
ESTADOS = {"Open", "Closed", "AutoClosed", "Ajuste"}

# Etiqueta legible por estado para el export; default "Cerrada".
ESTADO_TEXTO = {"Open": "En curso", "Ajuste": "Ajuste", "AutoClosed": "Cerrada (auto)"}


# Alias local del helper compartido (app/api/shared/request_helpers.py).
_text = sanitizar_texto


def _fmt_duracion(segundos):
    """'En curso' si la sesion sigue abierta; si no, H:MM:SS acumulado."""
    if segundos is None:
        return "En curso"
    total = int(segundos)
    h, resto = divmod(total, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _row_to_json(row):
    duracion_seg = row.get("duracion_seg")
    return {
        # session_id es un UUID (char), no un autoincrement numerico.
        "session_id": str(row.get("session_id") or ""),
        "estacion": row.get("estacion") or "",
        "tipo": row.get("tipo") or "",
        "nombre_estacion": row.get("nombre_estacion") or "",
        "linea": row.get("linea") or "",
        "usuario": row.get("usuario") or "",
        "username": row.get("username") or "",
        "fecha": formatear_fecha(row.get("fecha")),
        "hora_entrada": formatear_hora(row.get("hora_entrada")),
        "hora_salida": formatear_hora(row.get("hora_salida")),
        "duracion_seg": int(duracion_seg) if duracion_seg is not None else None,
        "duracion": _fmt_duracion(duracion_seg),
        "estado": row.get("estado") or "",
        "inicio_online": bool(row.get("inicio_online")),
        "fin_online": bool(row.get("fin_online")),
        "inicio_local": formatear_fecha_hora(row.get("inicio_local")),
        "fin_local": formatear_fecha_hora(row.get("fin_local")),
    }


@bp.route("/control_resultados/historial_operadores_maquina")
@login_requerido
@_requiere_permiso
def historial_operadores_maquina_ajax():
    """Render AJAX del modulo Historial de Operadores por Maquina."""
    try:
        # Los filtros de fecha arrancan en el dia actual (zona Mexico GMT-6,
        # la misma zona a la que la vista convierte los timestamps).
        return render_template(
            "Control de resultados/historial_operadores_maquina_ajax.html",
            hoy=obtener_fecha_mexico(),
        )
    except Exception as e:
        logger.error("Error al cargar Historial de Operadores por Maquina: %s", e)
        return f"Error al cargar el contenido: {str(e)}", 500


def _build_filters():
    """Filtros comunes (q, tipo, estado, fechas) para listado y export."""
    q = _text(request.args.get("q"), 80)
    tipo = _text(request.args.get("tipo"), 16)
    estado = _text(request.args.get("estado"), 16)
    fecha_desde = _text(request.args.get("fecha_desde"), 10)
    fecha_hasta = _text(request.args.get("fecha_hasta"), 10)

    where = ["1 = 1"]
    params = []
    if q:
        where.append(
            """
            (
                estacion LIKE %s OR
                nombre_estacion LIKE %s OR
                linea LIKE %s OR
                usuario LIKE %s OR
                username LIKE %s
            )
            """
        )
        like = f"%{q}%"
        params.extend([like, like, like, like, like])
    if tipo in TIPOS:
        where.append("tipo = %s")
        params.append(tipo)
    if estado in ESTADOS:
        where.append("estado = %s")
        params.append(estado)
    if fecha_desde:
        where.append("fecha >= %s")
        params.append(fecha_desde)
    if fecha_hasta:
        where.append("fecha <= %s")
        params.append(fecha_hasta)
    return " AND ".join(where), params


def _query_sessions():
    """Ejecuta el listado filtrado de la vista y devuelve filas serializadas."""
    where_sql, params = _build_filters()
    sql = f"""
        SELECT session_id, estacion, tipo, nombre_estacion, linea, usuario, username,
               fecha, hora_entrada, hora_salida, duracion_seg, estado,
               inicio_online, fin_online, inicio_local, fin_local
        FROM historial_estaciones_qa
        WHERE {where_sql}
        ORDER BY inicio_local DESC
        LIMIT 1000
    """
    rows = execute_query(sql, tuple(params) if params else None, fetch="all") or []
    return [_row_to_json(row) for row in rows]


@bp.route("/api/control_resultados/historial_operadores_maquina", methods=["GET"])
@login_requerido
@_requiere_permiso
def list_historial_operadores_maquina():
    """Listar sesiones de la vista historial_estaciones_qa con filtros."""
    try:
        records = _query_sessions()
        return jsonify({"success": True, "records": records, "total": len(records)})
    except Exception as exc:
        logger.exception("Error listando historial_estaciones_qa: %s", exc)
        return jsonify({"success": False, "error": str(exc), "records": []}), 500


@bp.route("/api/control_resultados/historial_operadores_maquina/export", methods=["GET"])
@login_requerido
@_requiere_permiso
def export_historial_operadores_maquina():
    """Exportar el historial filtrado a Excel (helper shared excel_response)."""
    try:
        records = _query_sessions()
        items = [
            {
                **r,
                "estado_texto": ESTADO_TEXTO.get(r["estado"], "Cerrada"),
            }
            for r in records
        ]
        headers = [
            "Línea", "Estación", "Nombre", "Tipo", "Usuario", "Badge",
            "Fecha", "Entrada", "Salida", "Duración", "Estado",
        ]
        keys = [
            "linea", "estacion", "nombre_estacion", "tipo", "usuario", "username",
            "fecha", "hora_entrada", "hora_salida", "duracion", "estado_texto",
        ]
        widths = [10, 14, 26, 10, 22, 14, 12, 10, 10, 12, 10]
        filename = (
            f"historial_operadores_maquina_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        return excel_response(
            items, headers, keys, widths,
            sheet="Operadores por Maquina", filename=filename,
        )
    except Exception as exc:
        logger.exception("Error exportando historial_estaciones_qa: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500
