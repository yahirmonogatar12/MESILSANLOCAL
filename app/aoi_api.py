# aoi_api.py
# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta, date
import pymysql

aoi_api = Blueprint("aoi_api", __name__)

# ----- Config DB -----
DB = dict(
    host="up-de-fra1-mysql-1.db.run-on-seenode.com",
    port=11550,
    user="db_rrpq0erbdujn",
    password="5fUNbSRcPP3LN9K2I33Pr0ge",
    database="db_rrpq0erbdujn",
    charset="utf8mb4",
    autocommit=True,
)
def db():
    return pymysql.connect(**DB)

# ----- Reglas de turno (idénticas al loader) -----
def classify_shift(dt: datetime) -> str:
    # DÍA 07:40–17:39, EXTRA 17:40–22:49, NOCHE 22:50–07:30 (incluye 07:30)
    mins = dt.hour * 60 + dt.minute
    if 7*60+40 <= mins < 17*60+40:  return "DIA"
    if 17*60+40 <= mins < 22*60+50: return "TIEMPO_EXTRA"
    if mins >= 22*60+50 or mins <= 7*60+30: return "NOCHE"
    return "DIA"  # 07:31–07:39

def compute_shift_date(dt: datetime, shift: str) -> date:
    if shift == "NOCHE" and (dt.hour*60 + dt.minute) <= 7*60+30:
        return (dt - timedelta(days=1)).date()
    return dt.date()

# ----- API: banner turno actual -----
@aoi_api.get("/api/shift-now")
def api_shift_now():
    now = datetime.now()
    shift = classify_shift(now)
    sdate = compute_shift_date(now, shift)
    return jsonify({"now": now.isoformat(), "shift": shift, "shift_date": sdate.strftime("%Y-%m-%d")})

# ----- API: tabla turno en tiempo real -----
@aoi_api.get("/api/realtime")
def api_realtime():
    now = datetime.now()
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
    with db().cursor() as cur:
        cur.execute(sql, (sdate, shift))
        rows = [{"linea":a, "modelo":m, "lado":l, "cantidad":int(p)} for (a,m,l,p) in cur.fetchall()]
    return jsonify({"shift_date": sdate, "shift": shift, "rows": rows})

# ----- API: tabla por día lógico -----
@aoi_api.get("/api/day")
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
    with db().cursor() as cur:
        cur.execute(sql, (d,))
        rows = [{"fecha":f.strftime("%Y-%m-%d"), "turno":t, "linea":ln, "modelo":m, "lado":l, "cantidad":int(p)}
                for (f,t,ln,m,l,p) in cur.fetchall()]
    return jsonify({"rows": rows})