# aoi_api.py
# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta, date
import pymysql
from .auth_system import AuthSystem
import os
from dotenv import load_dotenv

load_dotenv()

aoi_api = Blueprint("aoi_api", __name__)

# ----- Config DB (variables de entorno obligatorias - sin fallback) -----
DB = dict(
    host=os.getenv('MYSQL_HOST'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database=os.getenv('MYSQL_DATABASE'),
    charset="utf8mb4",
    autocommit=True,
)
def db():
    return pymysql.connect(**DB)

# ----- Reglas de turno -----
def classify_shift(dt: datetime) -> str:
    """
    Clasificar turno según hora:
    - DÍA: 7:30 - 17:30
    - TIEMPO_EXTRA: 17:30 - 22:00
    - NOCHE: 22:30 - 7:00 (del día siguiente)
    - Gap 22:00-22:30: se considera fin de TIEMPO_EXTRA
    - Gap 7:00-7:30: se considera fin de NOCHE
    """
    mins = dt.hour * 60 + dt.minute
    
    # DÍA: 7:30 (450 mins) hasta 17:30 (1050 mins)
    if 7*60+30 <= mins < 17*60+30:
        return "DIA"
    
    # TIEMPO_EXTRA: 17:30 (1050 mins) hasta 22:00 (1320 mins)
    if 17*60+30 <= mins < 22*60+0:
        return "TIEMPO_EXTRA"
    
    # NOCHE: 22:30 (1350 mins) hasta 7:00 (420 mins del día siguiente)
    if mins >= 22*60+30 or mins < 7*60+0:
        return "NOCHE"
    
    # Gaps de transición
    if 22*60+0 <= mins < 22*60+30:
        return "TIEMPO_EXTRA"  # Gap 22:00-22:30 -> fin de tiempo extra
    if 7*60+0 <= mins < 7*60+30:
        return "NOCHE"  # Gap 7:00-7:30 -> fin de noche
    
    return "DIA"  # Fallback

def compute_shift_date(dt: datetime, shift: str) -> date:
    """
    Calcular la fecha lógica del turno.
    Para turno NOCHE después de medianoche, la fecha es del día anterior.
    """
    mins = dt.hour * 60 + dt.minute
    # Si es NOCHE y estamos antes de las 7:00, pertenece al día anterior
    if shift == "NOCHE" and mins < 7*60+0:
        return (dt - timedelta(days=1)).date()
    return dt.date()

# ----- API: banner turno actual -----
@aoi_api.get("/api/shift-now")
def api_shift_now():
    now = AuthSystem.get_mexico_time()
    shift = classify_shift(now)
    sdate = compute_shift_date(now, shift)
    return jsonify({"now": now.isoformat(), "shift": shift, "shift_date": sdate.strftime("%Y-%m-%d")})

# ----- API: tabla turno en tiempo real -----
@aoi_api.get("/api/realtime")
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