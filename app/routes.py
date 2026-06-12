import logging
import os
import secrets
import time
import traceback
from functools import wraps

# Intentar importar MySQLdb, si no esta disponible usar PyMySQL como alternativa.
# Solo necesario para garantizar disponibilidad del binding para otros modulos
# (auth_system, db_mysql) - no se consume directamente aqui.
try:
    import MySQLdb  # noqa: F401
except ImportError:
    import pymysql

    pymysql.install_as_MySQLdb()
    import MySQLdb  # noqa: F401

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.exceptions import HTTPException

# Importar sistema de autenticacion mejorado
from .auth_system import AuthSystem
from .api.shared import permisos
from .api.shared.datetime_helpers import obtener_fecha_hora_mexico
from .api.shared.public_routes import is_public_api_route
from .db import get_db_connection
from .db_mysql import execute_query

# Fase 2 (2026-05-28): Re-exports zombies eliminados.
#   - ICT helpers (4)        : ya consumidos directo desde app.api.shared.ict_helpers
#   - Vision helpers (15)    : idem desde app.api.shared.vision_helpers
#   - Excel helpers (4)      : idem desde app.api.shared.excel_helpers
#   - Almacen embarques (2)  : Fase 3.1 termino la migracion ("Control de salida
#                              de lineas" ya vive en su blueprint, los importa
#                              directo). routes.py ya no consume nada de aqui.
# Fase 5 (2026-05-28): Imports masivos heredados eliminados (72 simbolos no
# usados tras mover el grueso de la logica a blueprints). routes.py ahora solo
# importa lo que sus rutas core de auth/sesion/landing/listas realmente usan.
#
# Migrados a app/api/ y registrados via registrar_blueprints_api() en app_factory.py:
#   admin_api          -> app/api/admin/permisos.py
#   api_po_wo          -> app/api/control_produccion/po_wo.py
#   api_raw_modelos    -> app/api/shared/raw_modelos.py
#   shipping_api       -> app/api/pda/shipping.py
#   shipping_material_api -> app/api/pda/shipping_material.py
#   tickets_portal     -> app/api/portal/tickets.py
#   user_admin         -> app/api/admin/usuarios.py

app = Flask(__name__)
logger = logging.getLogger(__name__)


def _env_flag(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on", "si")


# ---------------------------------------------------------------------------
# Seguridad de sesion
# ---------------------------------------------------------------------------
# SECRET_KEY: nunca usar una clave hardcodeada/publica para firmar cookies.
#   - Si esta en el entorno, se usa (camino correcto).
#   - Si NO esta y MES_ENV=production -> abortar el arranque (fail-loud).
#   - Si NO esta en dev/local -> clave efimera aleatoria (las sesiones no
#     sobreviven a un reinicio; se avisa para configurar SECRET_KEY).
_secret_key = os.getenv("SECRET_KEY")
if not _secret_key:
    if os.getenv("MES_ENV", "development").strip().lower() == "production":
        raise RuntimeError(
            "SECRET_KEY no esta definida y MES_ENV=production. "
            "Define SECRET_KEY en el entorno antes de arrancar."
        )
    _secret_key = secrets.token_hex(32)
    logger.warning(
        "SECRET_KEY no definida: usando clave efimera aleatoria. Las sesiones "
        "se invalidaran al reiniciar. Define SECRET_KEY en .env."
    )
app.secret_key = _secret_key

# Flags de la cookie de sesion:
#   - HTTPONLY + SAMESITE=Lax siempre (mitigan robo via XSS y CSRF).
#   - SECURE solo bajo HTTPS: MES_SESSION_COOKIE_SECURE (default False para
#     server local en HTTP). Ponlo en 1 cuando se sirva por HTTPS.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=_env_flag("MES_SESSION_COOKIE_SECURE", False),
)


@app.errorhandler(Exception)
def _handle_uncaught_exception(error):
    """Red de seguridad global: convierte excepciones no atrapadas en 500.

    Acompana al cambio de execute_query (que ahora re-lanza en vez de
    tragar el error): un fallo de BD se vuelve un 500 visible y logueado,
    no un []/0 que parece exito. Las HTTPException (404/403/redirects)
    pasan sin tocar.
    """
    if isinstance(error, HTTPException):
        return error

    logger.exception("Excepcion no atrapada en %s %s", request.method, request.path)

    wants_json = (
        request.path.startswith("/api/")
        or request.accept_mimetypes.best == "application/json"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    if wants_json:
        return jsonify({"error": "Error interno del servidor"}), 500
    return "Error interno del servidor", 500


# El control real del startup (should_run_startup_init / run_startup_init) vive
# en app/startup_init.py y lo invoca app_factory.create_app(). routes.py ya no
# duplica esa logica.

# smd_inventory: modulo borrado (commit c9a312b). Mantener como nota historica
# para evitar que reaparezca como "TODO migrar" en futuros audits.

# shipping y shipping_material (apps moviles PDA) registrados
# via registrar_blueprints_api() en app_factory.py

# api_po_wo y api_raw migrados a app/api/ y se registran centralmente
# desde app_factory.py via registrar_blueprints_api().

# Las inicializaciones (init_db, auth_system.init_database, shipping)
# se movieron a app/startup_init.py. Solo se instancia auth_system aqui
# porque otros decoradores en este archivo lo usan a nivel de modulo.
auth_system = AuthSystem()

# Registrar Blueprints de administración


@app.route("/api/health", methods=["GET"])
def api_health():
    database_status = "unavailable"

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        database_status = "ok"
    except Exception:
        database_status = "error"

    return jsonify(
        {
            "status": "OK",
            "service": "MESILSANLOCAL",
            "database": database_status,
            "timestamp": obtener_fecha_hora_mexico().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

# smt_routes_date_fixed migrado a app/api/control_calidad/smt_historial_simple.py
# smt_routes_clean      migrado a app/api/control_calidad/smt_historial.py
# Ambos se registran via registrar_blueprints_api() en app_factory.py

# user_admin (con url_prefix="/admin") y admin_bp ahora se registran
# desde app/api/__init__.py via registrar_blueprints_api()
# tickets_portal: registro movido a app/api/__init__.py


# `requiere_permiso_dropdown` se centralizo en app/api/shared/permisos.py.
# Se reexporta aqui para no romper referencias heredadas a
# `routes.requiere_permiso_dropdown`.
requiere_permiso_dropdown = permisos.requiere_permiso_dropdown


# Filtros de Jinja2 para permisos de botones (delegan en la fachada permisos).
@app.template_filter("tiene_permiso_boton")
def tiene_permiso_boton(nombre_boton):
    """Filtro para verificar si el usuario actual tiene permiso para un botón específico"""
    if "usuario" not in session:
        return False
    return permisos.puede_boton_por_nombre(session["usuario"], nombre_boton)


@app.template_filter("permisos_botones_pagina")
def permisos_botones_pagina(usuario, pagina):
    """Filtro para obtener todos los permisos de botones de una página"""
    if not usuario:
        return {}
    return permisos.permisos_botones(usuario, pagina)


# 2026-05-29: el fallback legacy a usuarios.json (cargar_usuarios) se elimino;
# el login usa solo el sistema de BD (auth_system).


# ACTUALIZADO: Usar el sistema de autenticación avanzado
def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        logger.debug("Verificando sesion avanzada: %s", session.get("usuario"))

        # Verificar si hay usuario en sesión
        if "usuario" not in session:
            logger.debug("No hay usuario en sesion")
            return redirect(url_for("auth_sesion.inicio"))

        usuario = session.get("usuario")

        # Evita un round-trip a MySQL remoto en cada request AJAX.
        now_ts = int(time.time())
        last_touch_ts = int(session.get("_last_activity_touch_ts", 0) or 0)
        if now_ts - last_touch_ts >= 300:
            auth_system._actualizar_actividad_sesion(usuario)
            session["_last_activity_touch_ts"] = now_ts
            session.modified = True

        return f(*args, **kwargs)

    return decorada


PUBLIC_ROUTE_ENDPOINTS = {
    # Fase 6 (2026-05-28): index/inicio/login viven en el blueprint auth_sesion,
    # por eso aparecen con prefijo. api_health/favicon/front_plan_static siguen
    # siendo top-level en routes.py.
    "auth_sesion.index",
    "auth_sesion.inicio",
    "auth_sesion.login",
    "api_health",
    "favicon",
    "front_plan_static",
    "static",
}


def _request_expects_json():
    accept = request.headers.get("Accept", "")
    requested_with = request.headers.get("X-Requested-With", "")
    return (
        request.path.startswith("/api/")
        or request.is_json
        or "application/json" in accept
        or requested_with == "XMLHttpRequest"
    )


@app.before_request
def require_login_by_default():
    """Protect routes by default and keep a short explicit public allowlist."""
    endpoint = request.endpoint

    # Let Flask resolve 404/405 normally when there is no matched endpoint.
    if endpoint is None:
        return None

    # Static assets and a small set of public endpoints remain accessible.
    if endpoint in PUBLIC_ROUTE_ENDPOINTS or endpoint.endswith(".static"):
        return None

    # Las apps PDA autentican contra /api/shipping/auth/login y luego consumen
    # endpoints del mismo blueprint sin sesión web del portal corporativo.
    if is_public_api_route(request.path):
        return None

    if "usuario" in session:
        return None

    if _request_expects_json():
        return jsonify({"error": "Usuario no autenticado", "redirect": "/login"}), 401

    return redirect(url_for("auth_sesion.inicio"))


# Fase 6 (2026-05-28): render_landing_page movido a app/api/auth/sesion.py
# (helper privado del blueprint auth, solo consumido por index/inicio/login).


# Fase 6 (2026-05-28): /, /login, /inicio movidos a app/api/auth/sesion.py
# (junto con render_landing_page). Los endpoints quedan como auth_sesion.index /
# auth_sesion.login / auth_sesion.inicio (el endpoint= solo fija el nombre local;
# el blueprint antepone el prefijo). url_for() los referencia con ese prefijo.


# Fase 6 (2026-05-28): /api/mi-perfil movido a app/api/auth/sesion.py.


@app.route("/calendario")
@login_requerido
def calendario():
    """Página del calendario de producción"""
    return render_template("calendario.html")


@app.route("/defect-management")
@login_requerido
def defect_management():
    """Módulo de Gestión de Defectos (En Desarrollo)"""
    # TODO: Implementar módulo completo de gestión de defectos
    return render_template(
        "info.html",
        titulo="Gestión de Defectos",
        mensaje="Módulo en desarrollo. Próximamente disponible.",
        tipo="warning",
    )


@app.route("/favicon.eco")
def favicon():
    """Servir favicon usando un icono existente"""
    return send_from_directory(
        os.path.join(app.root_path, "static", "icons"),
        "produccion.png",
        mimetype="image/png",
    )


# Fase 1 (2026-05-28): /sistemas, /soporte, /documentacion borradas —
# sin consumidores en app/static + app/templates.


@app.route("/ILSAN-ELECTRONICS")
@login_requerido
def material():
    usuario = session.get("usuario", "Invitado")
    nombre_completo = session.get("nombre_completo", None)

    # Si no tenemos el nombre completo en la sesión, obtenerlo de la BD
    if not nombre_completo and usuario != "Invitado":
        logger.warning(
            f"⚠️ Nombre completo no encontrado en sesión para {usuario}, obteniendo de BD..."
        )
        from .auth_system import auth_system

        info_usuario = auth_system.obtener_informacion_usuario(usuario)
        if info_usuario and info_usuario["nombre_completo"]:
            nombre_completo = info_usuario["nombre_completo"]
            session["nombre_completo"] = (
                nombre_completo  # Guardar en sesión para futuras consultas
            )
            logger.info(f" Nombre completo obtenido de BD: {nombre_completo}")
        else:
            nombre_completo = usuario  # Fallback al username
            session["nombre_completo"] = usuario
            logger.error(
                f"⚠️ No se pudo obtener nombre completo de BD, usando username: {usuario}"
            )

    # Si todavía no tenemos nombre completo, usar el username
    if not nombre_completo:
        nombre_completo = usuario

    permisos = session.get("permisos", {})

    # Verificar si tiene permisos de administración de usuarios
    tiene_permisos_usuarios = False
    if isinstance(permisos, dict) and "sistema" in permisos:
        tiene_permisos_usuarios = "usuarios" in permisos["sistema"]

    return render_template(
        "MainTemplate.html",
        usuario=nombre_completo,  # Pasar nombre completo en lugar de username
        tiene_permisos_usuarios=tiene_permisos_usuarios,
    )


@app.route("/dashboard")
@login_requerido
def dashboard():
    """Alias para la página principal (MainTemplate)"""
    usuario = session.get("usuario")
    nombre_completo = session.get("nombre_completo")

    # Si no tenemos nombre completo, intentar obtenerlo
    if not nombre_completo and usuario:
        try:
            query = "SELECT nombre_completo FROM users WHERE usuario = %s"
            result = execute_query(query, (usuario,), fetch="one")
            if result and result.get("nombre_completo"):
                nombre_completo = result["nombre_completo"]
                session["nombre_completo"] = nombre_completo
        except Exception as e:
            logger.error(f"⚠️ Error obteniendo nombre completo para dashboard: {e}")
            nombre_completo = usuario

    if not nombre_completo:
        nombre_completo = usuario

    permisos = session.get("permisos", {})
    tiene_permisos_usuarios = False
    if isinstance(permisos, dict) and "sistema" in permisos:
        tiene_permisos_usuarios = "usuarios" in permisos["sistema"]

    return render_template(
        "MainTemplate.html",
        usuario=nombre_completo,
        tiene_permisos_usuarios=tiene_permisos_usuarios,
    )


# Fase 6 (2026-05-28): /logout movido a app/api/auth/sesion.py.


# =============================
# FRONT PLAN: Vistas y estáticos
# =============================


# Alias para servir los assets originales de FRONT PLAN ubicados en
# app/FRONT PLAN/static sin depender de moverlos físicamente.
@app.route("/front-plan/static/<path:filename>")
def front_plan_static(filename):
    try:
        base_dir = os.path.join(os.path.dirname(__file__), "FRONT PLAN", "static")
        return send_from_directory(base_dir, filename)
    except Exception as e:
        return jsonify({"error": f"Recurso no encontrado: {str(e)}"}), 404


# Migracion 2026-05-26: view_plan_main movido a app/api/control_produccion/plan_assy.py


# Limpieza 2026-05-27: view_control_main eliminado (modulo Control de operacion de linea Main borrado)


# Rutas AJAX para cargar módulos en el área de Control de Proceso (prompts)
# Migracion 2026-05-26: plan_main_assy_ajax movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: plan_main_imd_ajax movido a app/api/control_produccion/plan_imd.py


# Fase 3.2 (2026-05-28): /plan-main-smt-ajax movido a
# app/api/control_produccion/plan_smt.py (modulo dueno del template).


# Limpieza 2026-05-27: ctrl_operacion_linea_main_ajax eliminado (modulo Control de operacion de linea Main borrado)



# Fase 2 (2026-05-28): Re-export zombie de Cuchillas de corte eliminado.
# Las 10 constantes/helpers (CUCHILLAS_*, _cuchillas_*, crear_trigger_*)
# vivian aqui solo por inercia. Tras Fase 2:
#   - `_cuchillas_rows_to_json`: material_admin.py importa directo del blueprint.
#   - Las 9 restantes no tenian consumidor externo.
# El modulo entero vive en app/api/control_produccion/cuchillas_corte.py.


# Migracion 2026-05-27: snapshot inventario (constantes, DDL, captura,
# worker daemon, endpoints) movido a app/api/shared/snapshot_inventario.py.
# startup_init.py importa crear_tablas_snapshot_inventario() e
# iniciar_snapshot_inv_worker() desde el blueprint.

# Bootstrap de snapshot inventario movido a app/startup_init.py



# =============================
# FRONT PLAN: API mínima plan_main
# =============================


# Fase 6 (2026-05-28): Re-exports zombies de plan_lot_no y bom_revisions
# eliminados. Sus consumidores (plan_assy, plan_imd, plan_smt) los importan
# directo desde shared/* sin pasar por routes.py.


# Migracion 2026-05-26: api_plan_list movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: helpers _PLAN_BOM_ASSIGNMENT_COLUMNS_READY, etc. movidos a shared/bom_revisions.py


# Migracion 2026-05-26: api_plan_bom_revisions movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_input_main_scan_lots movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_input_main_assign_lot movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_input_main_create_plan movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_create movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_update movido a app/api/control_produccion/plan_assy.py


# Fase 4 (2026-05-28): /api/raw/search movido a
# app/api/shared/raw_modelos.py (mismo url_prefix /api/raw + /search).


# Migracion 2026-05-26: api_plan_status movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_save_sequences movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_pending movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_reschedule movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_export_excel movido a app/api/control_produccion/plan_assy.py


# ====== RUTAS API PARA PLAN IMD ======


# Migracion 2026-05-26: api_plan_imd_list movido a app/api/control_produccion/plan_imd.py


# Migracion 2026-05-26: api_plan_imd_create movido a app/api/control_produccion/plan_imd.py


# Migracion 2026-05-26: api_plan_imd_batch_update movido a app/api/control_produccion/plan_imd.py


# Migracion 2026-05-26: api_plan_imd_update movido a app/api/control_produccion/plan_imd.py


# Migracion 2026-05-26: api_plan_imd_save_sequences movido a app/api/control_produccion/plan_imd.py


# Migracion 2026-05-26: api_plan_imd_pending movido a app/api/control_produccion/plan_imd.py


# Migracion 2026-05-26: api_plan_imd_pending_reschedule movido a app/api/control_produccion/plan_imd.py


# Migracion 2026-05-26: api_plan_imd_reschedule movido a app/api/control_produccion/plan_imd.py


# Migracion 2026-05-26: api_plan_imd_export_excel movido a app/api/control_produccion/plan_imd.py


# Migracion 2026-05-26: api_plan_imd_import_excel movido a app/api/control_produccion/plan_imd.py


# ====== RUTAS API PARA PLAN SMT (tabla plan_smt) ======
# Migrado a app/api/control_produccion/plan_smt.py (2026-05-25).
# Las 9 rutas se registran via blueprint en app/api/__init__.py.
# 2026-05-28: `crear_tabla_plan_smt_v2` ahora se importa directo desde el
# blueprint en `app/startup_init.py` (re-export aqui eliminado).


# Migracion 2026-05-26: api_plan_main_list movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-27: /api/work-orders/import movido a
# app/api/control_produccion/po_wo.py como POST /api/work_orders/import.
# La URL legacy /api/work-orders/import responde con 308 redirect (alias).


@app.route("/cargar_template", methods=["POST"])
@login_requerido
def cargar_template():
    template_path = None  # Initialize template_path
    try:
        data = request.get_json()
        template_path = data.get("template_path")

        if not template_path:
            return jsonify({"error": "No se especificó la ruta del template"}), 400

        # Validar que la ruta del template sea segura
        if ".." in template_path or template_path.startswith("/"):
            return jsonify({"error": "Ruta de template no válida"}), 400

        # Renderizar el template y devolver el HTML
        html_content = render_template(template_path)
        return html_content

    except Exception as e:
        template_name = template_path if template_path else "unknown"
        logger.error(f"Error al cargar template {template_name}: {str(e)}")
        return jsonify({"error": f"Error al cargar el template: {str(e)}"}), 500


# Limpieza 2026-05-26: rutas /guardar_entrada_aereo y /listar_entradas_aereo eliminadas.
# Sin consumidores en app/static/js/ ni en app/templates/. Tabla entrada_aereo (SQLite legacy)
# tampoco se lee desde ningun otro lado. Documentadas como huerfanas en
# Documentacion/VERIFICACION_DETALLADA_HUERFANAS.md lineas 39-40.


# Función de conexión movida a db.py - usar get_db_connection() importada


# Fase 1 (2026-05-28): /guardar_cliente_seleccionado y /cargar_cliente_seleccionado
# borradas — sin consumidores en app/static + app/templates. Sus helpers privados
# `cargar_configuracion_usuario` y `guardar_configuracion_usuario` se eliminaron tambien.


# Limpieza 2026-06-12: /informacion_basica/control_de_material eliminada junto con
# su template (INFORMACION BASICA/CONTROL_DE_MATERIAL.html), control_material.css y
# material-edit-drawer.js. El modulo se reconstruira desde cero; el boton del sidebar
# muestra un stub definido en MainTemplate.html (mostrarControlMaterialInfo).


# Rutas para cargar contenido dinámicamente (AJAX)
@app.route("/listas/informacion_basica")
@login_requerido
def lista_informacion_basica():
    """Cargar dinámicamente la lista de Información Básica"""
    try:
        return render_template("LISTAS/LISTA_INFORMACIONBASICA.html")
    except Exception as e:
        logger.error(f"Error al cargar LISTA_INFORMACIONBASICA: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/listas/control_material")
@login_requerido
def lista_control_material():
    """Cargar dinámicamente la lista de Control de Material"""
    try:
        return render_template("LISTAS/LISTA_DE_MATERIALES.html")
    except Exception as e:
        logger.error(f"Error al cargar LISTA_DE_MATERIALES: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/listas/control_produccion")
@login_requerido
def lista_control_produccion():
    """Cargar dinámicamente la lista de Control de Producción"""
    try:
        return render_template("LISTAS/LISTA_CONTROLDEPRODUCCION.html")
    except Exception as e:
        logger.error(f"Error al cargar LISTA_CONTROLDEPRODUCCION: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# Renders HTML de Control de produccion migrados a
# app/api/control_produccion/views.py (2026-05-25):
#   /control_produccion/control_embarque
#   /Control de embarque
#   /control_produccion/crear_plan
#   /control_produccion/plan_smt
# Se registran via blueprint en app/api/__init__.py.


# ==========================================
# AGENTE GENERADOR DE PLAN SMD
# ==========================================
# Migrado a app/api/control_produccion/plan_smd.py (2026-05-25).
# Las 4 rutas se registran via blueprint en app/api/__init__.py.
# 2026-05-28: `crear_tabla_plan_smd` y `crear_tabla_plan_smd_runs` se
# importan directo desde el blueprint en `app/startup_init.py` (re-exports
# eliminados).


# Migracion 2026-05-27: GET /api/work-orders movido a
# app/api/control_produccion/po_wo.py como GET /api/work_orders
# (con flag ?include_import_status=1 para el shape legacy).
# La URL legacy /api/work-orders responde con 301 redirect (alias).


# Fase 4 (2026-05-28): /api/inventario/modelo/<codigo_modelo> movido a
# app/api/control_resultados/inventario_imd.py.



# Limpieza 2026-05-27: control_produccion_smt_ajax eliminado (modulo descartado)


# Ruta eliminada - Control de operacion de linea SMT será reemplazado por Control BOM


# Limpieza 2026-05-27: control_operacion_linea_smt_ajax eliminado (modulo descartado)


# Rutas AJAX para todos los módulos de Control de Proceso
# Limpieza 2026-05-27: control_impresion_identificacion_smt_ajax eliminado (modulo descartado)


# Limpieza 2026-05-27: control_registro_identificacion_smt_ajax eliminado (modulo descartado)


# Fase 3.1 (2026-05-28): 10 renders cortos de Control de proceso movidos a
# app/api/control_proceso/renders.py (sin cambios de URL).



# Fase 3.1 (2026-05-28): "Control de salida de lineas" completo (3 helpers
# + 3 endpoints) movido a app/api/control_proceso/control_salida_lineas.py.
# Continua aqui solo el bloque _obtener_control_salida_lineas que se va junto.





# Fase 3.1 (2026-05-28): 5 renders restantes de Control de proceso movidos a
# app/api/control_proceso/renders.py (sin cambios de URL):
# /registro-movimiento-identificacion-ajax, /control-otras-identificaciones-ajax,
# /control-movimiento-ns-producto-ajax, /model-sn-management-ajax, /control-scrap-ajax.


# Fase 3.2 (2026-05-28): Renders de Control de produccion movidos a sus
# blueprints (sin cambios de URL):
#   /line-material-status-ajax       -> control_produccion/renders.py
#   /estandares-soldadura-ajax       -> control_produccion/renders.py
#   /registro-recibo-soldadura-ajax  -> control_produccion/renders.py
#   /control-salida-soldadura-ajax   -> control_produccion/renders.py
#   /historial-tension-mask-metal-ajax -> control_produccion/metal_mask.py
# (Las 3 rutas template de Control de SMT — Metal Mask, Squeegee, Caja Metal Mask
# — ya estaban en sus blueprints desde 2026-05-26.)


# Fase 3.1 (2026-05-28): alias 301 /control_proceso/inventario_imd_terminado
# movido a app/api/control_proceso/renders.py.


@app.route("/listas/control_proceso")
@login_requerido
def lista_control_proceso():
    """Cargar dinámicamente la lista de Control de Proceso"""
    try:
        return render_template("LISTAS/LISTA_CONTROL_DE_PROCESO.html")
    except Exception as e:
        logger.error(f"Error al cargar LISTA_CONTROL_DE_PROCESO: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/listas/control_calidad")
@login_requerido
def lista_control_calidad():
    """Cargar dinámicamente la lista de Control de Calidad"""
    try:
        return render_template("LISTAS/LISTA_CONTROL_DE_CALIDAD.html")
    except Exception as e:
        logger.error(f"Error al cargar LISTA_CONTROL_DE_CALIDAD: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/listas/control_resultados")
@login_requerido
def lista_control_resultados():
    """Cargar dinámicamente la lista de Control de Resultados"""
    try:
        return render_template("LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html")
    except Exception as e:
        logger.error(f"Error al cargar LISTA_DE_CONTROL_DE_RESULTADOS: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# Migracion 2026-05-27: /historial-aoi y /historial-aoi-ajax movidos a
# app/api/control_resultados/aoi.py como /historial_aoi/ajax (canonica).
# Las dos URLs legacy responden con 301 redirect (alias en el blueprint).


# Migracion 2026-05-27: Historial ICT %% Pass/Fail + Historial ICT (render) movidos a
# app/api/control_resultados/historial_ict_pass_fail.py y historial_ict.py.
# Aliases 301: /historial-maquina-ict-pass-fail{,-ajax}, /historial-ict-ajax.

# Migracion 2026-05-27: Historial de Cambios de Parametros ICT movido a
# app/api/control_resultados/historial_cambios_parametros_ict.py.
# Alias 301: /historial-cambios-parametros-ict-ajax.
# DDL crear_indice_history_ict_audit() y crear_indice_history_ict_ts_nopart()
# arrancan desde startup_init.py importando del blueprint.


# Migracion 2026-05-27: /historial-aoi-ajax movido a
# app/api/control_resultados/aoi.py (ver alias arriba).


@app.route("/listas/control_reporte")
@login_requerido
def lista_control_reporte():
    """Cargar dinámicamente la lista de Control de Reporte"""
    try:
        return render_template("LISTAS/LISTA_DE_CONTROL_DE_REPORTE.html")
    except Exception as e:
        logger.error(f"Error al cargar LISTA_DE_CONTROL_DE_REPORTE: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/listas/configuracion_programa")
@login_requerido
def lista_configuracion_programa():
    """Cargar dinámicamente la lista de Configuración de Programa"""
    try:
        return render_template("LISTAS/LISTA_DE_CONFIGPG.html")
    except Exception as e:
        logger.error(f"Error al cargar LISTA_DE_CONFIGPG: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/material/info")
@login_requerido
def material_info():
    """Cargar dinámicamente la información general de material"""
    try:
        return render_template("info.html")
    except Exception as e:
        logger.error(f"Error al cargar info.html: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route("/templates/LISTAS/<filename>")
def serve_list_template(filename):
    """Servir plantillas de listas para el menú móvil"""
    try:
        # Verificar que el archivo existe y es uno de los permitidos
        allowed_files = [
            "LISTA_INFORMACIONBASICA.html",
            "LISTA_DE_MATERIALES.html",
            "LISTA_CONTROLDEPRODUCCION.html",
            "LISTA_CONTROL_DE_PROCESO.html",
            "LISTA_CONTROL_DE_CALIDAD.html",
            "LISTA_DE_CONFIGPG.html",
            "LISTA_DE_CONTROL_DE_REPORTE.html",
            "LISTA_DE_CONTROL_DE_RESULTADOS.html",
        ]

        if filename not in allowed_files:
            return "Archivo no encontrado", 404

        # Leer el archivo directamente
        template_folder = app.template_folder or "templates"
        template_path = os.path.join(template_folder, "LISTAS", filename)

        if not os.path.exists(template_path):
            return f"Archivo no encontrado: {template_path}", 404

        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        return content, 200, {"Content-Type": "text/html; charset=utf-8"}

    except Exception as e:
        logger.error(f"Error sirviendo plantilla {filename}: {str(e)}")
        return f"Error cargando la plantilla: {str(e)}", 500


# ===== RUTAS PARA EL SISTEMA DE PERMISOS DROPDOWNS =====


@app.route("/verificar_permiso_dropdown", methods=["POST"])
def verificar_permiso_dropdown():
    """
    Verificar si el usuario actual tiene permiso para un dropdown específico
    """
    try:
        if "usuario" not in session:
            return jsonify(
                {"tiene_permiso": False, "error": "Usuario no autenticado"}
            ), 401

        # Obtener datos desde JSON
        data = request.get_json()
        if not data:
            return jsonify(
                {"tiene_permiso": False, "error": "Datos JSON requeridos"}
            ), 400

        pagina = data.get("pagina", "").strip()
        seccion = data.get("seccion", "").strip()
        boton = data.get("boton", "").strip()

        if not all([pagina, seccion, boton]):
            return jsonify(
                {"tiene_permiso": False, "error": "Parámetros incompletos"}
            ), 400

        username = session.get("usuario")
        rol_nombre = auth_system.obtener_rol_principal_usuario(username)

        if not rol_nombre:
            return jsonify(
                {"tiene_permiso": False, "error": "Usuario no encontrado o sin roles"}
            ), 404

        tiene_permiso = permisos.puede_boton(username, pagina, seccion, boton)

        return jsonify(
            {
                "tiene_permiso": tiene_permiso,
                "usuario": username,
                "rol": rol_nombre,
                "permiso": f"{pagina} > {seccion} > {boton}",
            }
        )

    except Exception as e:
        logger.error(f"Error verificando permiso: {e}")
        return jsonify({"tiene_permiso": False, "error": str(e)}), 500


@app.route("/obtener_permisos_usuario_actual", methods=["GET"])
@login_requerido
def obtener_permisos_usuario_actual():
    """
    Obtener todos los permisos del usuario actual para caché en frontend
    """
    try:
        if "usuario" not in session:
            return jsonify({"permisos": [], "error": "Usuario no autenticado"}), 401

        username = session["usuario"]
        rol_nombre = auth_system.obtener_rol_principal_usuario(username)
        if not rol_nombre:
            return jsonify(
                {"permisos": {}, "error": "Usuario no encontrado o sin roles"}
            ), 404

        permisos_usuario = permisos.permisos_botones(username)

        # Formatear permisos para JavaScript en estructura jerárquica
        permisos_jerarquicos = {}
        total_permisos = 0

        for pagina, secciones in permisos_usuario.items():
            permisos_jerarquicos[pagina] = {}
            for seccion, botones in secciones.items():
                permisos_jerarquicos[pagina][seccion] = []
                for item in botones:  # ya normalizados a dict por la fachada
                    boton = item.get("boton")
                    if not boton:
                        continue
                    permisos_jerarquicos[pagina][seccion].append(boton)
                    total_permisos += 1

        return jsonify(
            {
                "permisos": permisos_jerarquicos,
                "usuario": username,
                "rol": rol_nombre,
                "total_permisos": total_permisos,
            }
        )

    except Exception as e:
        logger.error(f"Error obteniendo permisos: {e}")
        return jsonify({"permisos": [], "error": str(e)}), 500


# Fase 1 (2026-05-28): CSV VIEWER ROUTES eliminadas — /csv-viewer (csv_viewer)
# sin consumidores en app/static + app/templates.

# Fase 3.3 (2026-05-28): /historial-cambio-material-smt[-ajax] movidos a
# app/api/control_calidad/smt_historial.py (blueprint smt_api, ya dueno de
# /smt/historial que renderiza el mismo template).


# Fase 1 (2026-05-28): /api/csv_data (get_csv_data) borrada — sin consumidores.
# Fase 1 (2026-05-28): /api/csv_stats (get_csv_stats) borrada — sin consumidores.
# Tambien se elimino dead code (codigo huerfano dentro del except, jamas alcanzable).
# Fase 1 (2026-05-28): /api/filter_data (filter_csv_data) borrada — sin consumidores
# en app/static ni app/templates. Pertenecia al ecosistema CSV viewer ya retirado.


# Fase 5 (anticipada, 2026-05-28): crear_patron_caracteres borrado
# (0 consumidores en codigo vivo).


# Fase 1 (2026-05-28): cargar_configuracion_usuario / guardar_configuracion_usuario
# borradas con guardar_cliente_seleccionado y cargar_cliente_seleccionado (eran sus unicos consumidores).


# Fase 4 (2026-05-28): /importar_excel_plan_produccion movido a
# app/api/control_produccion/plan_assy.py.

@app.route("/produccion/info")
@login_requerido
def produccion_info():
    try:
        return render_template("CONTROL DE PRODUCCION/info_produccion.html")
    except Exception as e:
        return f"Error al cargar información de producción: {str(e)}", 500


# Migracion 2026-05-27: GET /api/wo/exportar movido a
# app/api/control_produccion/po_wo.py (misma URL, mismo comportamiento).



# Fase 4 (2026-05-28): /api/inventario movido a
# app/api/control_resultados/inventario_imd.py.


# ============================================================================
# RUTAS PARA CONTROL DE CALIDAD
# ============================================================================


# Fase 3.3 (2026-05-28): /control-resultado-reparacion-ajax y
# /control-item-reparado-ajax movidos a app/api/control_calidad/renders.py.


# Eliminado 2026-05-27: "Historial de cambio de material por maquina" dado de baja
# (modulo no usado). Rutas borradas:
#   /historial-cambio-material-maquina-ajax  (render)
#   /api/historial-cambio-material-maquina   (GET)


# Fase 4 (2026-05-28): /api/historial_smt_latest y /api/historial_smt_latest_v2
# movidos a app/api/control_calidad/smt_historial.py (junto con el helper
# convertir_linea_smt).

# Fase 4 (2026-05-28): 4 rutas Metal Mask migradas a
# app/api/control_produccion/metal_mask.py:
#   /api/masks/info, POST y GET /api/metal-mask/history,
#   /api/metal-mask/update-used-count.


# Fase 3.3 (2026-05-28): 7 renders de Control de calidad movidos a sus blueprints
# (sin cambios de URL):
#   /historial-uso-mask-metal-ajax            -> control_produccion/metal_mask.py
#   /historial-uso-squeegee-ajax              -> control_produccion/squeegee.py
#   /process-interlock-history-ajax           -> control_calidad/renders.py
#   /control-master-sample-smt-ajax           -> control_calidad/renders.py
#   /historial-inspeccion-master-sample-smt-ajax -> control_calidad/renders.py
#   /control-inspeccion-oqc-ajax              -> control_calidad/renders.py


# Migracion 2026-05-28: /historial-liberacion-lqc-ajax, /api/smt-scanner/{lineas,datos}
# + helpers _lqc_* movidos a app/api/control_calidad/historial_liberacion_lqc.py
# Las URLs canonicas ahora son /historial_liberacion_lqc/ajax y /api/lqc/{lineas,datos};
# el blueprint expone aliases 301 desde las viejas para no romper consumidores externos.




# Migracion 2026-05-27:
#   /api/inventario_general, /api/ubicacion, /api/movimientos
#     -> app/api/control_resultados/inventario_imd.py
#   /api/snapshot_inventario/{fechas,general,ubicacion,trigger}
#     + DDL + worker daemon + funcion de captura
#     -> app/api/shared/snapshot_inventario.py
# Las 6 GETs ahora exigen @login_requerido (antes eran publicas).


# === RUTAS MIGRADAS ===
# /api/mysql, /api/mysql/columns, /api/mysql/data, /api/mysql/update,
# /api/mysql/create, /api/mysql/usuario-actual, /api/mysql/delete,
# /visor-mysql, /control-modelos-visor-ajax
# Migradas a app/api/informacion_basica/control_modelos_visor.py
# Se registran automaticamente via registrar_blueprints_api() en app_factory.py



# Fase 5 (anticipada, 2026-05-28): generar_lot_no_secuencial borrado
# (0 consumidores en codigo vivo).


# Limpieza 2026-05-27: api_plan_run_start eliminado (modulo Control de operacion de linea Main borrado)


# Limpieza 2026-05-27: api_plan_run_end eliminado (modulo Control de operacion de linea Main borrado)


# Limpieza 2026-05-27: api_plan_run_pause eliminado (modulo Control de operacion de linea Main borrado)


# Limpieza 2026-05-27: api_plan_run_resume eliminado (modulo Control de operacion de linea Main borrado)


# Limpieza 2026-05-27: api_plan_run_status eliminado (modulo Control de operacion de linea Main borrado)


# Migracion 2026-05-28: crear_tabla_trazabilidad e init_metal_mask_tables
# movidos a app/api/control_produccion/{trazabilidad,metal_mask}.py.
# startup_init.py los importa directo desde sus blueprints (no via _routes).



# Migracion 2026-05-26: rutas alternas /control/metal-mask y
# /control/metal-mask/caja eliminadas (no consumidas por el frontend; el
# sidebar y scriptMain.js usan /control-mask-metal-ajax y
# /control-caja-mask-metal-ajax que ahora viven en sus blueprints).

# Migracion 2026-05-26: api_list_masks + api_create_mask + api_update_mask movidos a
# app/api/control_produccion/metal_mask.py


# Migracion 2026-05-26: api_get_storage + api_add_storage + api_update_storage
# movidos a app/api/control_produccion/caja_metal_mask.py (sigue siendo
# consumida tambien por MetalMask.js -- los blueprints comparten URL space).


# Fase 4 (2026-05-28): /api/bom-smt-data movido a
# app/api/informacion_basica/control_bom.py.


# Fase 4 (2026-05-28): `convertir_linea_smt` movido a smt_historial.py junto
# con su unico consumidor (api_historial_smt_latest_v2). Fase 5 (anticipada):
# `convertir_linea_smt_reverso` borrado (0 consumidores en codigo vivo).


# Helpers ICT movidos a app/api/shared/ict_helpers.py (2026-05-27).
# Ya NO se reexportan desde routes: los consumidores los importan directo de ese
# modulo (ver "Re-exports zombies eliminados" al inicio del archivo).

# Migracion 2026-05-27: 31 helpers Vision + 2 helpers Excel + 2 renders + 6 APIs
# movidos a 4 archivos nuevos:
#   app/api/shared/vision_helpers.py    (13 helpers Vision compartidos)
#   app/api/shared/excel_helpers.py     (_send_excel_download +
#                                        _create_vision_pass_fail_excel_image +
#                                        18 helpers PNG internos)
#   app/api/control_resultados/historial_vision.py            (render + 4 APIs)
#   app/api/control_resultados/historial_vision_pass_fail.py  (render + 2 APIs)
# Aliases 301: /historial-vision{,-ajax}, /historial-vision-pass-fail{,-ajax}.
# Helpers Vision y Excel: se importan directo de app/api/shared/* (sin re-export en routes).


# Migracion 2026-05-27: Historial ICT (defects) movido a
# app/api/control_resultados/historial_ict.py.
# Aliases 301: /historial-ict, /historial-ict-ajax, /ict/front-full-defects2.
# Helpers _ict_format_row, _ict_find_history_record, _ict_load_local_parameters
# y _append_indexable_text_filter movidos a app/api/shared/ict_helpers.py
# (se importan directo de ahi; routes.py ya no los reexporta).
