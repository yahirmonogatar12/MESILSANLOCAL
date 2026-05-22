"""Endpoints HTTP del modulo AOI (Automated Optical Inspection).

Reglas de turnos:
  - DIA: 7:30 - 17:30
  - TIEMPO_EXTRA: 17:30 - 22:00
  - NOCHE: 22:30 - 7:00 (del dia siguiente)
  - Gaps de transicion: 22:00-22:30 cuenta como TIEMPO_EXTRA, 7:00-7:30 como NOCHE

Rutas:
  GET /api/shift-now   -> turno actual + fecha logica
  GET /api/realtime    -> tabla del turno actual (linea/modelo/lado/cantidad)
  GET /api/day         -> tabla por dia logico

Migrado desde `app/aoi_api.py` (2026-05-22). El archivo legacy usaba
`pymysql.connect(...)` directo; ahora consume `execute_query()` segun WF_003.
"""

from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request

from app.api.shared import execute_query
from app.auth_system import AuthSystem


bp = Blueprint("aoi_api", __name__)


def classify_shift(dt: datetime) -> str:
    """Clasificar turno segun hora. Ver docstring del modulo."""
    mins = dt.hour * 60 + dt.minute

    if 7 * 60 + 30 <= mins < 17 * 60 + 30:
        return "DIA"

    if 17 * 60 + 30 <= mins < 22 * 60 + 0:
        return "TIEMPO_EXTRA"

    if mins >= 22 * 60 + 30 or mins < 7 * 60 + 0:
        return "NOCHE"

    # Gaps de transicion
    if 22 * 60 + 0 <= mins < 22 * 60 + 30:
        return "TIEMPO_EXTRA"
    if 7 * 60 + 0 <= mins < 7 * 60 + 30:
        return "NOCHE"

    return "DIA"


def compute_shift_date(dt: datetime, shift: str) -> date:
    """Para turno NOCHE despues de medianoche, la fecha es del dia anterior."""
    mins = dt.hour * 60 + dt.minute
    if shift == "NOCHE" and mins < 7 * 60 + 0:
        return (dt - timedelta(days=1)).date()
    return dt.date()


@bp.get("/api/shift-now")
def api_shift_now():
    now = AuthSystem.get_mexico_time()
    shift = classify_shift(now)
    sdate = compute_shift_date(now, shift)
    return jsonify({"now": now.isoformat(), "shift": shift, "shift_date": sdate.strftime("%Y-%m-%d")})


@bp.get("/api/realtime")
def api_realtime():
    now = AuthSystem.get_mexico_time()
    shift = classify_shift(now)
    sdate = compute_shift_date(now, shift).strftime("%Y-%m-%d")

    sql = """
    SELECT linea, modelo, lado, SUM(pieces) AS cantidad
    FROM (
      SELECT
        CASE line_no WHEN 1 THEN 'A' WHEN 2 THEN 'B' WHEN 3 THEN 'C' ELSE CONCAT('L', line_no) END AS linea,
        model AS modelo,
        CASE WHEN board_side IN ('TOP','BOT') THEN board_side ELSE '1 SIDE' END AS lado,
        piece_w AS pieces
      FROM aoi_file_log
      WHERE shift_date=%s AND shift=%s
    ) t
    GROUP BY linea, modelo, lado
    ORDER BY FIELD(linea,'A','B','C'), modelo, FIELD(lado,'TOP','BOT','1 SIDE','NA')
    """
    rows = execute_query(sql, (sdate, shift), fetch="all") or []
    result = [
        {
            "linea": r["linea"],
            "modelo": r["modelo"],
            "lado": r["lado"],
            "cantidad": int(r["cantidad"] or 0),
        }
        for r in rows
    ]
    return jsonify({"shift_date": sdate, "shift": shift, "rows": result})


@bp.get("/api/day")
def api_day():
    d = request.args.get("date")
    if not d:
        return jsonify({"rows": []})

    sql = """
    SELECT fecha, turno, linea, modelo, lado, SUM(pieces) AS cantidad
    FROM (
      SELECT
        shift_date AS fecha,
        shift AS turno,
        CASE line_no WHEN 1 THEN 'A' WHEN 2 THEN 'B' WHEN 3 THEN 'C' ELSE CONCAT('L', line_no) END AS linea,
        model AS modelo,
        CASE WHEN board_side IN ('TOP','BOT') THEN board_side ELSE '1 SIDE' END AS lado,
        piece_w AS pieces
      FROM aoi_file_log
      WHERE shift_date=%s
    ) t
    GROUP BY fecha, turno, linea, modelo, lado
    ORDER BY FIELD(turno,'DIA','TIEMPO_EXTRA','NOCHE'),
             FIELD(linea,'A','B','C'),
             modelo,
             FIELD(lado,'TOP','BOT','1 SIDE','NA')
    """
    rows = execute_query(sql, (d,), fetch="all") or []
    result = []
    for r in rows:
        fecha_val = r["fecha"]
        if hasattr(fecha_val, "strftime"):
            fecha_str = fecha_val.strftime("%Y-%m-%d")
        else:
            fecha_str = str(fecha_val) if fecha_val else ""
        result.append({
            "fecha": fecha_str,
            "turno": r["turno"],
            "linea": r["linea"],
            "modelo": r["modelo"],
            "lado": r["lado"],
            "cantidad": int(r["cantidad"] or 0),
        })
    return jsonify({"rows": result})
