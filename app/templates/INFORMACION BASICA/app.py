# -*- coding: utf-8 -*-
import os, re
from flask import Flask, render_template, request, jsonify
import pymysql
from pymysql.cursors import DictCursor

# === DB config (override with env if you want) ===
MYSQL_HOST = os.getenv("MYSQL_HOST", "up-de-fra1-mysql-1.db.run-on-seenode.com")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "11550"))
MYSQL_USER = os.getenv("MYSQL_USER", "db_rrpq0erbdujn")
MYSQL_PASS = os.getenv("MYSQL_PASS", "5fUNbSRcPP3LN9K2I33Pr0ge")
MYSQL_DB   = os.getenv("MYSQL_DB",   "db_rrpq0erbdujn")

app = Flask(__name__, static_folder="static", template_folder="templates")

_valid_tbl = re.compile(r"^[A-Za-z0-9_]+$")

def _conn():
    return pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASS,
        database=MYSQL_DB, charset="utf8mb4", cursorclass=DictCursor, autocommit=True
    )

def _safe_table(t):
    if not t or not _valid_tbl.match(t):
        raise ValueError("Nombre de tabla inválido")
    return t

def _get_columns(table):
    q = '''
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
    ORDER BY ORDINAL_POSITION
    '''
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(q, (MYSQL_DB, table))
        return [r["COLUMN_NAME"] for r in cur.fetchall()]

@app.get("/")
def index():
    table = request.args.get("table", "raw")
    table = _safe_table(table)
    return render_template("index.html", table=table)

@app.get("/api/columns")
def api_columns():
    table = _safe_table(request.args.get("table", "raw"))
    cols = _get_columns(table)
    return jsonify({"table": table, "columns": cols})

@app.get("/api/data")
def api_data():
    table   = _safe_table(request.args.get("table", "raw"))
    limit   = min(max(int(request.args.get("limit", 200)), 1), 2000)
    offset  = max(int(request.args.get("offset", 0)), 0)
    search  = (request.args.get("search") or "").strip()

    cols = _get_columns(table)
    if not cols:
        return jsonify({"table": table, "columns": [], "rows": [], "total": 0})

    base_sql = f"SELECT * FROM `{table}`"
    where = ""
    params = []
    if search:
        like = " OR ".join([f"CAST(`{c}` AS CHAR) LIKE %s" for c in cols])
        where = f" WHERE ({like})"
        params += [f"%{search}%"] * len(cols)

    count_sql = f"SELECT COUNT(*) AS c FROM `{table}`{where}"
    data_sql  = f"{base_sql}{where} LIMIT %s OFFSET %s"

    with _conn() as conn, conn.cursor() as cur:
        cur.execute(count_sql, params)
        total = cur.fetchone()["c"]
        cur.execute(data_sql, params + [limit, offset])
        rows = cur.fetchall()

    return jsonify({
        "table": table,
        "columns": cols,
        "rows": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
        "search": search
    })

@app.get("/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    app.run(debug=True)
