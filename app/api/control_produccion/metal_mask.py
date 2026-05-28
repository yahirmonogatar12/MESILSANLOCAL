"""Endpoints HTTP del modulo Control de metal mask.

Migrado desde `app/routes.py` (2026-05-26). Sin cambios funcionales.

Rutas:
  GET  /control-mask-metal-ajax  -> render HTML del modulo
  GET  /api/masks                -> listar masks (filtra por disuse)
  POST /api/masks                -> crear mask
  PUT  /api/masks/<int:mask_id>  -> actualizar mask

NO mover aqui `/api/masks/info` (routes.py:17174): es compartida con el
modulo "Control de operacion SMT" (`control-operacion-smt-ajax.js:1560`).

DDL `init_metal_mask_tables` migrado a este modulo el 2026-05-28; lo invoca
`app/startup_init.py` para garantizar la existencia de las tablas `masks`
y `storage_boxes` al arranque.
"""

from functools import wraps

from flask import Blueprint, jsonify, render_template, request

# Importar directo desde modulos fuente (NO desde app.api.shared) para
# evitar import circular: shared -> routes -> metal_mask -> shared.
from app.db_mysql import execute_query


# `login_requerido` y `requiere_permiso_dropdown` viven en `app.routes`.
# Se importan dentro de las funciones que los necesitan (tarde) para evitar
# que metal_mask arrastre app.routes al ser importado por shared.
def login_requerido(f):
    """Proxy del decorador real definido en `app.routes`."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import routes as _r
        return _r.login_requerido(f)(*args, **kwargs)

    return decorated_function


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


bp = Blueprint("control_produccion_metal_mask", __name__)


# =============================
# CONTROL DE METAL MASK
# =============================

METAL_MASK_PERMISO_PAGINA = "LISTA_CONTROLDEPRODUCCION"
METAL_MASK_PERMISO_SECCION = "Control de SMT"
METAL_MASK_PERMISO_BOTON = "Control de mask de metal"


@bp.route("/control-mask-metal-ajax")
@login_requerido
@requiere_permiso_dropdown(
    METAL_MASK_PERMISO_PAGINA, METAL_MASK_PERMISO_SECCION, METAL_MASK_PERMISO_BOTON
)
def control_mask_metal_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de Control de mask de metal."""
    try:
        return render_template("Control de produccion/control_mask_metal_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Control de mask de metal AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# API: Masks
@bp.route("/api/masks", methods=["GET"])
@login_requerido
def api_list_masks():
    try:
        disuse = request.args.get("disuse", "ALL")
        sql = (
            "SELECT id, management_no, storage_box, pcb_code, side, "
            "COALESCE(DATE_FORMAT(production_date, '%Y-%m-%d'), '') AS production_date, "
            "used_count, max_count, allowance, model_name, tension_min, tension_max, thickness, "
            "supplier, registration_date, disuse FROM masks"
        )
        params = []
        if disuse and disuse != "ALL":
            sql += " WHERE disuse=%s"
            params.append(disuse)
        sql += " ORDER BY id DESC"
        rows = execute_query(sql, tuple(params) if params else None, fetch="all") or []

        # Normalizacion ligera de tipos para JSON
        out = []
        for r in rows:
            r = dict(r)
            for k in ("used_count", "max_count", "allowance"):
                try:
                    r[k] = int(r.get(k) or 0)
                except Exception:
                    pass
            for k in ("tension_min", "tension_max", "thickness"):
                v = r.get(k)
                try:
                    r[k] = float(v) if v is not None else None
                except Exception:
                    pass
            out.append(r)
        return jsonify(out)
    except Exception as e:
        print(f"Error en api_list_masks: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/masks", methods=["POST"])
@login_requerido
def api_create_mask():
    try:
        data = request.get_json(force=True) or {}
        data.setdefault("used_count", 0)
        data.setdefault("max_count", 0)
        data.setdefault("allowance", 0)
        data.setdefault("disuse", "Uso")

        pd = data.get("production_date")
        if isinstance(pd, str) and len(pd) >= 10:
            data["production_date"] = pd[:10]
        else:
            data["production_date"] = None

        cols = (
            "management_no",
            "storage_box",
            "pcb_code",
            "side",
            "production_date",
            "used_count",
            "max_count",
            "allowance",
            "model_name",
            "tension_min",
            "tension_max",
            "thickness",
            "supplier",
            "registration_date",
            "disuse",
        )
        placeholders = ",".join(["%s"] * len(cols))
        values = [data.get(c) for c in cols]
        sql = f"INSERT INTO masks ({','.join(cols)}) VALUES ({placeholders})"
        execute_query(sql, tuple(values))
        return jsonify({"success": True, "message": "Registrado", "data": data}), 201
    except Exception as e:
        msg = str(e)
        if "Duplicate entry" in msg:
            return jsonify({"error": "El Nomero de Gestion ya existe"}), 400
        print(f"Error en api_create_mask: {e}")
        return jsonify({"error": msg}), 500


@bp.route("/api/masks/<int:mask_id>", methods=["PUT"])
@login_requerido
def api_update_mask(mask_id: int):
    try:
        p = request.get_json(force=True) or {}
        required = p.get("management_no", "").strip()
        if not required:
            return jsonify({"error": "Nomero de Gestion es requerido"}), 400

        sql = (
            "UPDATE masks SET management_no=%s, storage_box=%s, pcb_code=%s, side=%s, "
            "production_date=%s, used_count=%s, max_count=%s, allowance=%s, "
            "model_name=%s, tension_min=%s, tension_max=%s, thickness=%s, "
            "supplier=%s, registration_date=%s, disuse=%s WHERE id=%s"
        )
        params = (
            p.get("management_no", "").strip(),
            p.get("storage_box", "").strip(),
            p.get("pcb_code", "").strip(),
            p.get("side", "").strip(),
            (p.get("production_date") or None),
            p.get("used_count", 0),
            p.get("max_count", 0),
            p.get("allowance", 0),
            p.get("model_name", "").strip(),
            p.get("tension_min", 0),
            p.get("tension_max", 0),
            p.get("thickness", 0),
            p.get("supplier", "").strip(),
            p.get("registration_date", "").strip(),
            p.get("disuse", "Uso"),
            mask_id,
        )
        affected = execute_query(sql, params)
        if affected == 0:
            return jsonify({"error": "Moscara no encontrada"}), 404
        return jsonify({"success": True, "message": "Actualizado"})
    except Exception as e:
        msg = str(e)
        if "Duplicate entry" in msg:
            return jsonify({"error": "El Nomero de Gestion ya existe"}), 400
        print(f"Error en api_update_mask: {e}")
        return jsonify({"error": msg}), 500


# =============================
# GET /api/metal-mask/test  (health check)
# =============================
# Migracion 2026-05-27: ruta reintegrada en su blueprint (caller huerfano en
# control-operacion-smt-ajax.js:2581 - `testMetalMaskConnection`).
# Verifica conectividad a la tabla `masks` antes de cargar el historial.
# Respuesta: {success: bool, count?: int, error?: str}.

@bp.route("/api/metal-mask/test", methods=["GET"])
@login_requerido
def api_metal_mask_test():
    """Health check de conectividad a la tabla masks (consumido por Control de operacion SMT)."""
    try:
        row = execute_query("SELECT COUNT(*) AS c FROM masks", fetch="one")
        count = 0
        if row:
            count = row.get("c") if isinstance(row, dict) else row[0]
        return jsonify({"success": True, "count": int(count or 0)})
    except Exception as e:
        print(f"Error en api_metal_mask_test: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Bootstrap DDL (invocado desde app/startup_init.py al arranque)
# ---------------------------------------------------------------------------


def init_metal_mask_tables():
    """Crea/ajusta tablas `masks` y `storage_boxes` si no existen.

    Migrado desde `app/routes.py` el 2026-05-28. Sin cambios funcionales.
    """
    try:
        # Tabla principal de masks (nombres de columna en ingles, usados por el frontend).
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS masks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                management_no VARCHAR(64) UNIQUE,
                storage_box VARCHAR(64),
                pcb_code VARCHAR(64),
                side VARCHAR(16),
                production_date DATE,
                used_count INT DEFAULT 0,
                max_count INT DEFAULT 0,
                allowance INT DEFAULT 0,
                model_name VARCHAR(255),
                tension_min DECIMAL(6,2),
                tension_max DECIMAL(6,2),
                thickness DECIMAL(6,2),
                supplier VARCHAR(128),
                registration_date VARCHAR(64),
                disuse ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        # Asegurar valores del ENUM en caso de historiales previos (migracion suave).
        try:
            execute_query(
                "ALTER TABLE masks MODIFY COLUMN disuse ENUM('Use','Disuse','Uso','Desuso','Scrap') DEFAULT 'Uso'"
            )
            execute_query("UPDATE masks SET disuse='Uso' WHERE disuse='Use'")
            execute_query("UPDATE masks SET disuse='Desuso' WHERE disuse='Disuse'")
            execute_query(
                "ALTER TABLE masks MODIFY COLUMN disuse ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso'"
            )
        except Exception:
            # Si falla (p.ej. por no existir la tabla/columna aun), continuar.
            pass

        # Tabla de cajas de almacenamiento.
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS storage_boxes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                management_no VARCHAR(64) UNIQUE,
                code VARCHAR(64),
                name VARCHAR(64),
                location VARCHAR(64),
                storage_status ENUM('Disponible','Ocupado','Mantenimiento') DEFAULT 'Disponible',
                used_status ENUM('Usado','No Usado') DEFAULT 'Usado',
                note TEXT,
                registration_date VARCHAR(64),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        print(" Tablas Metal Mask creadas/verificadas")
    except Exception as e:
        print(f"Error creando/verificando tablas Metal Mask: {e}")
