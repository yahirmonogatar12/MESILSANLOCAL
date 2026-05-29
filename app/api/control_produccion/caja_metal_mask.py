"""Endpoints HTTP del modulo Control de caja de metal mask.

Migrado desde `app/routes.py` (2026-05-26). Sin cambios funcionales.

Rutas:
  GET  /control-caja-mask-metal-ajax      -> render HTML del modulo
  GET  /api/storage                       -> listar cajas (paginado + filtros)
  POST /api/storage                       -> crear caja
  PUT  /api/storage/<int:storage_id>      -> actualizar caja

`/api/storage` GET es consumida tambien por `MetalMask.js` (listar cajas
disponibles dentro del storage-modal del modulo Metal Mask). Esto sigue
funcionando sin cambios porque los Blueprints comparten URL space.
"""

from functools import wraps

from flask import Blueprint, jsonify, render_template, request

# Importar directo desde modulos fuente (NO desde app.api.shared) para
# evitar import circular: shared -> routes -> caja_metal_mask -> shared.
from app.db_mysql import execute_query


# Decorador de auth centralizado (antes era un proxy duplicado en cada
# modulo). app.api.shared lo reexporta desde app.routes de forma lazy.
from app.api.shared import login_requerido

import logging
logger = logging.getLogger(__name__)


def requiere_permiso_dropdown(pagina, seccion, boton):
    """Proxy del decorador real definido en `app.routes`."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app import routes as _r
            real_decorator = _r.requiere_permiso_dropdown(pagina, seccion, boton)
            return real_decorator(f)(*args, **kwargs)

        return decorated_function

    return decorator


bp = Blueprint("control_produccion_caja_metal_mask", __name__)


# =============================
# CONTROL DE CAJA DE METAL MASK
# =============================

CAJA_PERMISO_PAGINA = "LISTA_CONTROLDEPRODUCCION"
CAJA_PERMISO_SECCION = "Control de SMT"
CAJA_PERMISO_BOTON = "Control de caja de mask de metal"


@bp.route("/control-caja-mask-metal-ajax")
@login_requerido
@requiere_permiso_dropdown(
    CAJA_PERMISO_PAGINA, CAJA_PERMISO_SECCION, CAJA_PERMISO_BOTON
)
def control_caja_mask_metal_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de Control de caja de mask de metal."""
    try:
        return render_template(
            "Control de produccion/control_caja_mask_metal_ajax.html"
        )
    except Exception as e:
        logger.error(f"Error al cargar template Control de caja de mask de metal AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# API: Storage Boxes
@bp.route("/api/storage", methods=["GET"])
@login_requerido
def api_get_storage():
    try:
        offset = int(request.args.get("offset", 0))
        limit = int(request.args.get("limit", 100))
        search = (request.args.get("search", "") or "").strip()
        filter_storage_status = (
            request.args.get("filter_storage_status", "") or ""
        ).strip()
        filter_used_status = (request.args.get("filter_used_status", "") or "").strip()

        clauses = []
        params = []
        if search:
            like = f"%{search}%"
            clauses.append(
                "(management_no LIKE %s OR code LIKE %s OR name LIKE %s OR location LIKE %s OR note LIKE %s)"
            )
            params += [like, like, like, like, like]
        if filter_storage_status:
            clauses.append("storage_status=%s")
            params.append(filter_storage_status)
        if filter_used_status:
            clauses.append("used_status=%s")
            params.append(filter_used_status)
        where = " AND ".join(clauses) if clauses else "1=1"

        total_row = execute_query(
            f"SELECT COUNT(*) AS total FROM storage_boxes WHERE {where}",
            tuple(params) if params else None,
            fetch="one",
        ) or {"total": 0}
        data = (
            execute_query(
                f"""
            SELECT id, management_no, code, name, location, storage_status, used_status, note, registration_date
            FROM storage_boxes WHERE {where}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
                tuple(params + [limit, offset]) if params else (limit, offset),
                fetch="all",
            )
            or []
        )
        return jsonify({"data": data, "total": total_row.get("total", 0)})
    except Exception as e:
        logger.error(f"Error en api_get_storage: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/storage", methods=["POST"])
@login_requerido
def api_add_storage():
    try:
        p = request.get_json(force=True) or {}
        management_no = (p.get("management_no", "") or "").strip()
        if not management_no:
            return jsonify({"error": "Nomero de Gestion es requerido"}), 400
        sql = (
            "INSERT INTO storage_boxes (management_no, code, name, location, storage_status, used_status, note, registration_date) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        )
        params = (
            management_no,
            (p.get("code", "") or "").strip(),
            (p.get("name", "") or "").strip(),
            (p.get("location", "") or "").strip(),
            (p.get("storage_status", "Disponible") or "Disponible"),
            (p.get("used_status", "Usado") or "Usado"),
            (p.get("note", "") or "").strip(),
            (p.get("registration_date", "") or "").strip(),
        )
        execute_query(sql, params)
        return jsonify(
            {
                "success": True,
                "message": "Caja de almacenamiento registrada exitosamente",
            }
        )
    except Exception as e:
        msg = str(e)
        if "Duplicate entry" in msg:
            return jsonify(
                {
                    "error": f'El Nomero de Gestion "{management_no}" ya existe. Por favor use un codigo/ubicacion diferente.'
                }
            ), 400
        logger.error(f"Error en api_add_storage: {e}")
        return jsonify({"error": msg}), 500


@bp.route("/api/storage/<int:storage_id>", methods=["PUT"])
@login_requerido
def api_update_storage(storage_id: int):
    try:
        p = request.get_json(force=True) or {}
        management_no = (p.get("management_no", "") or "").strip()
        if not management_no:
            return jsonify({"error": "Nomero de Gestion es requerido"}), 400
        sql = (
            "UPDATE storage_boxes SET management_no=%s, code=%s, name=%s, location=%s, "
            "storage_status=%s, used_status=%s, note=%s, registration_date=%s WHERE id=%s"
        )
        params = (
            management_no,
            (p.get("code", "") or "").strip(),
            (p.get("name", "") or "").strip(),
            (p.get("location", "") or "").strip(),
            (p.get("storage_status", "Disponible") or "Disponible"),
            (p.get("used_status", "Usado") or "Usado"),
            (p.get("note", "") or "").strip(),
            (p.get("registration_date", "") or "").strip(),
            storage_id,
        )
        affected = execute_query(sql, params)
        if affected == 0:
            return jsonify({"error": "Caja de almacenamiento no encontrada"}), 404
        return jsonify(
            {
                "success": True,
                "message": "Caja de almacenamiento actualizada exitosamente",
            }
        )
    except Exception as e:
        msg = str(e)
        if "Duplicate entry" in msg:
            return jsonify({"error": "El Nomero de Gestion ya existe"}), 400
        logger.error(f"Error en api_update_storage: {e}")
        return jsonify({"error": msg}), 500
