"""Endpoints HTTP para consultar la tabla RAW de modelos SMT.

Ubicado en `shared/` porque es un catalogo de modelos que consumen varios
modulos del navbar (actualmente Control de produccion: crear-plan,
plan-smd, control-embarque). Si en el futuro lo usa solo una seccion,
moverlo a esa carpeta.

Rutas (mismo url_prefix `/api/raw` que el legacy):
  GET /api/raw/modelos    -> lista de part_no distintos
  GET /api/raw/ct_uph     -> CT y UPH para un part_no (filtro opcional por linea)
  GET /api/raw/search     -> busqueda flexible por part_no/model (Fase 4)

Migrado desde `app/api_raw_modelos.py` (2026-05-22). Sin cambios funcionales.
Fase 4 (2026-05-28): `/api/raw/search` migrado desde routes.py.
"""

from functools import wraps

from flask import Blueprint, jsonify, request

# Import directo desde db_mysql para evitar circular (este modulo vive
# dentro de shared/ y shared/__init__.py re-exporta execute_query).
from app.db_mysql import execute_query


# Patron proxy anti-circular: `login_requerido` vive en app.routes y se
# resuelve tarde para no arrastrar el ciclo shared -> routes -> shared.
def login_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from app import routes as _r
        return _r.login_requerido(f)(*args, **kwargs)

    return decorated


bp = Blueprint("api_raw", __name__, url_prefix="/api/raw")


@bp.route("/modelos", methods=["GET"])
def listar_modelos_raw():
    """Listar modelos desde la tabla RAW tomando la columna part_no.

    Respuesta JSON: { success: bool, data: [str], count: int }
    """
    try:
        query = (
            "SELECT DISTINCT part_no "
            "FROM raw "
            "WHERE part_no IS NOT NULL AND TRIM(part_no) <> '' "
            "ORDER BY part_no"
        )
        result = execute_query(query, fetch="all") or []
        modelos = [row.get("part_no") for row in result if row.get("part_no")]
        return jsonify({"success": True, "data": modelos, "count": len(modelos)})
    except Exception as e:
        print(f"Error listando modelos RAW (part_no): {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/ct_uph", methods=["GET"])
def obtener_ct_uph():
    """Obtener CT y UPH desde tabla raw_smd por part_no y linea opcional.

    Params:
      - part_no: requerido
      - linea: opcional (ej. 'SMT A')

    Respuesta: { success: True, part_no, model, ct, uph }
    """
    try:
        part_no = (request.args.get("part_no") or "").strip()
        linea = (request.args.get("linea") or "").strip()
        if not part_no:
            return jsonify({"success": False, "error": "part_no requerido"}), 400

        base_sql = (
            "SELECT part_no, model, ct, uph "
            "FROM raw_smd WHERE TRIM(part_no)=TRIM(%s)"
        )
        params = [part_no]
        if linea:
            base_sql += " AND TRIM(linea)=TRIM(%s)"
            params.append(linea)
        base_sql += " ORDER BY updated_at DESC, id DESC LIMIT 1"

        row = execute_query(base_sql, tuple(params), fetch="one") or {}
        return jsonify({
            "success": True,
            "part_no": row.get("part_no") or part_no,
            "model": row.get("model") or None,
            "ct": row.get("ct") if row.get("ct") is not None else None,
            "uph": row.get("uph") if row.get("uph") is not None else None,
        })
    except Exception as e:
        print(f"Error obteniendo CT/UPH raw_smd: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Fase 4 (2026-05-28): /api/raw/search migrado desde routes.py.
# ---------------------------------------------------------------------------


@bp.route("/search", methods=["GET"])
@login_requerido
def api_raw_search():
    """Buscar datos en la tabla RAW por part_no o model"""
    try:
        part_no = request.args.get("part_no", "").strip()
        if not part_no:
            return jsonify({"error": "part_no requerido"}), 400

        # Buscar con multiples campos para mayor flexibilidad
        # Usar TRIM para ignorar espacios y comparacion case-insensitive
        sql = """
            SELECT part_no, model, project, c_t as ct, uph
            FROM raw
            WHERE TRIM(model) = %s
               OR TRIM(part_no) = %s
               OR TRIM(part_no) LIKE %s
               OR UPPER(TRIM(part_no)) = UPPER(%s)
            LIMIT 1
        """
        params = (part_no, part_no, f"%{part_no}%", part_no)

        # CRITICO: Usar fetch='all' para obtener los datos, no el rowcount
        result = execute_query(sql, params, fetch="all")

        if result and isinstance(result, (list, tuple)) and len(result) > 0:
            row = result[0]
            data = {
                "part_no": row.get("part_no", "")
                if row.get("part_no") is not None
                else "",
                "model": row.get("model", "") if row.get("model") is not None else "",
                "model_code": row.get("model", "")
                if row.get("model") is not None
                else "",
                "project": row.get("project", "")
                if row.get("project") is not None
                else "",
                "ct": str(row.get("ct", "0")) if row.get("ct") is not None else "0",
                "uph": str(row.get("uph", "0")) if row.get("uph") is not None else "0",
            }
            return jsonify([data])
        else:
            return jsonify([])

    except Exception as e:
        print(f"Error en api_raw_search: {e}")
        return jsonify({"error": str(e)}), 500
