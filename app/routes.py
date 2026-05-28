import json
import os
import re
import socket
import subprocess
import csv
import hashlib
import io
import tempfile
import threading
import time
import traceback
import struct
import zlib
from concurrent.futures import ThreadPoolExecutor

# Intentar importar MySQLdb, si no está disponible usar PyMySQL como alternativa
try:
    import MySQLdb
except ImportError:
    import pymysql

    pymysql.install_as_MySQLdb()
    import MySQLdb

from datetime import datetime, timedelta
from datetime import time as dt_time
from decimal import Decimal
from functools import wraps
from pathlib import Path


def obtener_fecha_hora_mexico():
    """Obtener fecha y hora actual en zona horaria de México (GMT-6)"""
    try:
        # Calcular hora de México Central (GMT-6)
        utc_now = datetime.utcnow()
        mexico_time = utc_now - timedelta(hours=6)
        return mexico_time
    except Exception as e:
        # Fallback a hora local
        return datetime.now()


import pandas as pd
from flask import (
    Flask,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

# Migrados a app/api/ y registrados via registrar_blueprints_api() en app_factory.py:
#   admin_api          -> app/api/admin/permisos.py
#   api_po_wo          -> app/api/control_produccion/po_wo.py
#                         (2026-05-27: absorbio /api/work-orders, /api/work-orders/import,
#                          /api/wo/exportar que aun vivian en este archivo)
#   api_raw_modelos    -> app/api/shared/raw_modelos.py

# Importar sistema de autenticación mejorado
from .auth_system import AuthSystem
from .db import (
    agregar_control_material_almacen,
    get_db_connection,
    init_db,
    migrar_datos_sqlite,
    obtener_control_material_almacen,
    test_database_connection,
)
from .db_mysql import (
    actualizar_inventario,
    actualizar_material_completo,
    cargar_configuracion,
    execute_query,
    guardar_configuracion,
    guardar_material,
    obtener_inventario,
    obtener_materiales,
)
from .config_mysql import get_pooled_connection

# Importar modelos y funciones PO → WO
from .po_wo_models import (
    crear_tablas_po_wo,
    generar_codigo_po,
    generar_codigo_wo,
    listar_pos_con_filtros,
    listar_pos_por_estado,
    listar_wos_con_filtros,
    listar_wos_por_po,
    obtener_po_por_codigo,
    obtener_wo_por_codigo,
    validar_codigo_po,
    validar_codigo_wo,
    verificar_po_existe,
    verificar_wo_existe,
)
# shipping_api migrado a app/api/pda/shipping.py
# Se registra via registrar_blueprints_api() en app_factory.py
from .api.pda.shipping import init_shipping_tables
# shipping_material_api migrado a app/api/pda/shipping_material.py
# Se registra via registrar_blueprints_api() en app_factory.py
from .api.pda.shipping_material import (
    SHIPPING_TABLES,
    adjust_shipping_movement_record,
    assign_exit_departure_value,
    delete_shipping_movement_record,
    ensure_inventory_record,
    generate_movement_folio,
    get_departure_history_records,
    get_dict_cursor,
    init_shipping_material_tables,
    normalize_integer,
    normalize_part_number,
    normalize_search,
    rebuild_part_inventory_state,
    to_sql_datetime,
)
from .services.ict_lgd_parser import (
    IctLgdError,
    IctLgdNotFoundError,
    IctLgdPathError,
    get_lgd_parameters_for_barcode,
    resolve_lgd_path,
)

# Fase 2 (2026-05-28): Re-exports zombies eliminados.
#   - ICT helpers (4)        : ya consumidos directo desde app.api.shared.ict_helpers
#   - Vision helpers (15)    : idem desde app.api.shared.vision_helpers
#   - Excel helpers (4)      : idem desde app.api.shared.excel_helpers
#   - Almacen embarques (2)  : Fase 3.1 termino la migracion ("Control de salida
#                              de lineas" ya vive en su blueprint, los importa
#                              directo). routes.py ya no consume nada de aqui.
# tickets_portal migrado a app/api/portal/tickets.py
# Se registra via registrar_blueprints_api() en app_factory.py
# user_admin migrado a app/api/admin/usuarios.py

app = Flask(__name__)
app.secret_key = os.getenv(
    "SECRET_KEY", "fallback_key_for_development_only"
)  # Necesario para usar sesiones


def _env_flag(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on", "si")


def should_run_startup_init():
    # Overrides explícitos
    if _env_flag("MES_FORCE_STARTUP_INIT", False):
        return True
    if _env_flag("MES_SKIP_STARTUP_INIT", False):
        return False

    # Si estamos en dev con reloader, solo correr en el proceso real
    if _env_flag("MES_USE_RELOADER", False):
        return os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    # Sin reloader: correr init normalmente
    return True


STARTUP_INIT_ENABLED = should_run_startup_init()
_startup_t0 = time.time()


def _startup_log(msg):
    elapsed = round(time.time() - _startup_t0, 2)
    print(f"[startup {elapsed}s] {msg}")


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


def requiere_permiso_dropdown(pagina, seccion, boton):
    """Decorador para verificar permisos específicos de dropdowns"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "usuario" not in session:
                return jsonify(
                    {"error": "Usuario no autenticado", "redirect": "/login"}
                ), 401

            try:
                username = session["usuario"]
                print(
                    f" Verificando permisos para usuario: {username}, página: {pagina}, sección: {seccion}, botón: {boton}"
                )

                rol_nombre = auth_system.obtener_rol_principal_usuario(username)
                if not rol_nombre:
                    print(" Usuario sin roles asignados")
                    return jsonify({"error": "Usuario sin roles asignados"}), 403

                print(f" Rol del usuario: {rol_nombre}")
                if rol_nombre == "superadmin":
                    print(" Superadmin: permiso concedido")
                    return f(*args, **kwargs)

                tiene_permiso = auth_system.verificar_permiso_boton(
                    username, pagina, seccion, boton
                )
                print(f" Tiene permiso: {tiene_permiso}")

                if not tiene_permiso:
                    print(f" Sin permisos para: {pagina} > {seccion} > {boton}")
                    # Respuesta diferente para AJAX vs navegación directa
                    if (
                        request.headers.get("Content-Type") == "application/json"
                        or request.is_json
                    ):
                        return jsonify(
                            {
                                "error": f"No tienes permisos para acceder a: {boton}",
                                "permiso_requerido": f"{pagina} > {seccion} > {boton}",
                            }
                        ), 403
                    else:
                        # Para carga AJAX de HTML, devolver mensaje de error
                        return (
                            f"""
                        <div style="
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            justify-content: center;
                            height: 400px;
                            background: #2c2c2c;
                            color: #e0e0e0;
                            border-radius: 10px;
                            margin: 20px;
                            text-align: center;
                        ">
                            <i class="fas fa-lock" style="font-size: 3rem; color: #dc3545; margin-bottom: 20px;"></i>
                            <h3>Acceso Denegado</h3>
                            <p>No tienes permisos para acceder a: <strong>{boton}</strong></p>
                            <p style="font-size: 0.9rem; opacity: 0.7;">Permiso requerido: {pagina} > {seccion} > {boton}</p>
                        </div>
                        """,
                            403,
                        )

                print(f" Permisos verificados correctamente, ejecutando función...")
                return f(*args, **kwargs)

            except Exception as e:
                print(f" Error verificando permisos: {e}")
                import traceback

                traceback.print_exc()
                return jsonify({"error": "Error interno del servidor"}), 500

        return decorated_function

    return decorator


# Filtros de Jinja2 para permisos de botones
@app.template_filter("tiene_permiso_boton")
def tiene_permiso_boton(nombre_boton):
    """Filtro para verificar si el usuario actual tiene permiso para un botón específico"""
    try:
        # Obtener el usuario de la sesión actual
        if "usuario" not in session:
            return False

        username = session["usuario"]
        if auth_system.obtener_rol_principal_usuario(username) == "superadmin":
            return True

        permisos_botones = auth_system.obtener_permisos_botones_usuario(username)
        for secciones in permisos_botones.values():
            for botones in secciones.values():
                for item in botones:
                    if isinstance(item, dict) and item.get("boton") == nombre_boton:
                        return True
                    if item == nombre_boton:
                        return True

        return False

    except Exception as e:
        print(f"Error verificando permiso de botón '{nombre_boton}': {e}")
        return False


@app.template_filter("permisos_botones_pagina")
def permisos_botones_pagina(usuario, pagina):
    """Filtro para obtener todos los permisos de botones de una página"""
    if not usuario:
        return {}
    return auth_system.obtener_permisos_botones_usuario(usuario, pagina)


# DEPRECADO: Función antigua para compatibilidad temporal
def cargar_usuarios():
    """Función deprecada - se mantiene para compatibilidad"""
    ruta = os.path.join(os.path.dirname(__file__), "database", "usuarios.json")
    ruta = os.path.abspath(ruta)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(" usuarios.json no encontrado, usando solo sistema de BD")
        return {}


# ACTUALIZADO: Usar el sistema de autenticación avanzado
def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        print(" Verificando sesión avanzada:", session.get("usuario"))

        # Verificar si hay usuario en sesión
        if "usuario" not in session:
            print("No hay usuario en sesión")
            return redirect(url_for("inicio"))

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
    "index",
    "inicio",
    "login",
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


def _is_public_api_route():
    """APIs que no dependen de la sesión web del portal."""
    path = request.path.rstrip("/")
    exact_paths = {
        "/api/shipping/auth/login",
        "/api/shipping/auth/logout",
        "/api/shipping/permissions/available",
        "/api/shipping/departments",
        "/api/shipping/cargos",
        "/api/shipping/entries",
        "/api/shipping/stats/today",
        "/api/shipping/stats/summary",
        "/api/shipping/material/entries",
        "/api/shipping/material/entries/boxes",
        "/api/shipping/material/exits",
        "/api/shipping/material/exits/boxes",
        "/api/shipping/material/returns",
        "/api/shipping/material/inventory",
        "/api/shipping/material/stats/today",
    }
    public_prefixes = (
        "/api/shipping/auth/verify/",
        "/api/shipping/users/",
        "/api/shipping/quality/",
        "/api/shipping/entries/",
        "/api/shipping/material/boxes/",
    )
    return path in exact_paths or any(path.startswith(prefix) for prefix in public_prefixes)


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
    if _is_public_api_route():
        return None

    if "usuario" in session:
        return None

    if _request_expects_json():
        return jsonify({"error": "Usuario no autenticado", "redirect": "/login"}), 401

    return redirect(url_for("inicio"))


def render_landing_page(login_error=None, login_username=None):
    """Renderiza la landing page con o sin sesión activa."""
    authenticated = "usuario" in session
    nombre_completo = None
    permisos = {}
    roles = []

    if authenticated:
        usuario = session.get("usuario")
        nombre_completo = session.get("nombre_completo", usuario)
        permisos = session.get("permisos", {})
        roles = session.get("roles") or auth_system.obtener_roles_usuario(usuario)

    upcoming_apps = [
        {
            "name": "Más Herramientas",
            "description": "Expansión futura",
            "long_description": "Nuevas aplicaciones serán agregadas pronto.",
            "icon": "rocket",
        }
    ]

    return render_template(
        "landing.html",
        nombre_usuario=nombre_completo,
        permisos=permisos,
        roles=roles,
        upcoming_apps=upcoming_apps,
        usuario_autenticado=authenticated,
        login_error=login_error,
        login_username=login_username,
    )


@app.route("/")
def index():
    return redirect(url_for("inicio"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return redirect(url_for("inicio"))

    is_ajax = request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")

    user = request.form.get("username", "").strip()
    pw = request.form.get("password", "")
    print(f" Intento de login: {user}")

    # PRIORIDAD 1: Intentar con el nuevo sistema de BD
    resultado_auth = auth_system.verificar_usuario(user, pw)

    # verificar_usuario devuelve (success, message) en lugar de diccionario
    if isinstance(resultado_auth, tuple):
        auth_success, auth_message = resultado_auth
    else:
        auth_success = (
            resultado_auth.get("success", False)
            if isinstance(resultado_auth, dict)
            else False
        )
        auth_message = (
            resultado_auth.get("message", "Error desconocido")
            if isinstance(resultado_auth, dict)
            else str(resultado_auth)
        )

    if auth_success:
        print(f" Login exitoso con sistema BD: {user}")
        session["usuario"] = user

        # Obtener información completa del usuario
        info_usuario = auth_system.obtener_informacion_usuario(user)
        if info_usuario:
            session["nombre_completo"] = info_usuario["nombre_completo"]
            session["email"] = info_usuario["email"]
            session["departamento"] = info_usuario["departamento"]
            print(f" Información completa cargada para {user}:")
            print(f"  - Nombre completo: {info_usuario['nombre_completo']}")
            print(f"  - Email: {info_usuario['email']}")
            print(f"  - Departamento: {info_usuario['departamento']}")
        else:
            # Fallback si no se puede obtener la información
            session["nombre_completo"] = user  # Usar username como fallback
            print(
                f"⚠️ No se pudo cargar información completa para {user}, usando username como fallback"
            )

        # Registrar auditoría
        auth_system.registrar_auditoria(
            usuario=user,
            modulo="sistema",
            accion="login",
            descripcion="Inicio de sesión exitoso",
            resultado="EXITOSO",
        )

        # Obtener permisos del usuario
        permisos_resultado = auth_system.obtener_permisos_usuario(user)

        # Verificar si devuelve tupla (permisos, rol_id) o solo permisos
        if isinstance(permisos_resultado, tuple):
            permisos, rol_id = permisos_resultado
        else:
            permisos = permisos_resultado
            rol_id = None

        session["permisos"] = permisos
        session["roles"] = auth_system.obtener_roles_usuario(user)
        session["rol_principal"] = session["roles"][0] if session["roles"] else None
        session.modified = True
        print(f" Permisos establecidos en sesión para {user}: {permisos}")

        # Redirigir siempre al hub de aplicaciones (landing page)
        print(f" Login exitoso para {user}, redirigiendo al hub de aplicaciones")
        redirect_url = url_for("inicio")
        if is_ajax:
            return jsonify({"success": True, "redirect": redirect_url})
        return redirect(redirect_url)

    # FALLBACK: Intentar con el sistema antiguo (usuarios.json)
    try:
        usuarios_json = cargar_usuarios()
        if user in usuarios_json and usuarios_json[user] == pw:
            print(f" Login exitoso con sistema JSON (fallback): {user}")
            session["usuario"] = user

            # Para usuarios del sistema JSON, usar el username como nombre completo
            session["nombre_completo"] = (
                user  # Fallback para usuarios del sistema antiguo
            )
            session["email"] = ""  # Sin email para usuarios del sistema antiguo
            session["departamento"] = (
                ""  # Sin departamento para usuarios del sistema antiguo
            )
            print(f"⚠️ Usuario del sistema JSON (fallback): {user}")

            # Registrar auditoría del fallback
            auth_system.registrar_auditoria(
                usuario=user,
                modulo="sistema",
                accion="login_json",
                descripcion="Inicio de sesión con sistema JSON (fallback)",
                resultado="EXITOSO",
            )

            # Redirigir según el usuario (lógica original)
            redirect_url = url_for("inicio")
            if user.startswith("Materiales") or user == "1111":
                redirect_url = url_for("material")
            elif user.startswith("Produccion") or user == "2222":
                redirect_url = url_for("produccion")
            elif user.startswith("DDESARROLLO") or user == "3333":
                redirect_url = url_for("desarrollo")

            if is_ajax:
                return jsonify({"success": True, "redirect": redirect_url})
            return redirect(redirect_url)
    except Exception as e:
        print(f" Error en fallback JSON: {e}")

    # Si llega aquí, login falló
    print(f" Login falló: {user} ({auth_message})")
    auth_system.registrar_auditoria(
        usuario=user,
        modulo="sistema",
        accion="login_failed",
        descripcion="Intento de login fallido - credenciales incorrectas",
        resultado="ERROR",
    )

    error_message = "Usuario o contraseña incorrectos. Por favor, intente de nuevo"

    if is_ajax:
        return jsonify({"success": False, "message": error_message}), 401

    return render_landing_page(login_error=error_message, login_username=user)


@app.route("/inicio")
def inicio():
    """Landing page / Hub de aplicaciones"""
    return render_landing_page()


@app.route("/api/mi-perfil", methods=["GET", "POST"])
def api_mi_perfil():
    """Consultar o actualizar el perfil del usuario autenticado."""
    usuario = session.get("usuario")
    if not usuario:
        return jsonify({"success": False, "message": "Sesion expirada"}), 401

    roles = session.get("roles") or auth_system.obtener_roles_usuario(usuario) or []
    rol_principal = session.get("rol_principal") or (roles[0] if roles else "")
    if roles and session.get("roles") != roles:
        session["roles"] = roles
        session["rol_principal"] = rol_principal
        session.modified = True

    info_usuario = auth_system.obtener_informacion_usuario(usuario)

    if request.method == "GET":
        nombre_completo = session.get("nombre_completo") or usuario
        email = session.get("email") or ""
        editable = bool(info_usuario)

        if info_usuario:
            nombre_completo = info_usuario.get("nombre_completo") or nombre_completo
            email = info_usuario.get("email") or email
            session["nombre_completo"] = nombre_completo
            session["email"] = email
            session.modified = True

        return jsonify(
            {
                "success": True,
                "perfil": {
                    "username": usuario,
                    "nombre_completo": nombre_completo,
                    "email": email,
                    "rol": rol_principal,
                    "roles": roles,
                    "editable": editable,
                },
            }
        )

    payload = request.get_json(silent=True) or request.form
    nombre_completo = (payload.get("nombre_completo") or "").strip()
    email = (payload.get("email") or "").strip()
    current_password = payload.get("current_password") or ""
    new_password = payload.get("new_password") or ""
    confirm_password = payload.get("confirm_password") or ""
    change_password = bool(current_password or new_password or confirm_password)

    if not nombre_completo:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "El nombre completo es obligatorio",
                }
            ),
            400,
        )

    if len(nombre_completo) > 120:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "El nombre completo es demasiado largo",
                }
            ),
            400,
        )

    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "El correo electronico no es valido",
                }
            ),
            400,
        )

    if change_password:
        if not current_password:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Debes escribir tu contrasena actual",
                    }
                ),
                400,
            )

        if not new_password:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Debes escribir una nueva contrasena",
                    }
                ),
                400,
            )

        if len(new_password) < 6:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "La nueva contrasena debe tener al menos 6 caracteres",
                    }
                ),
                400,
            )

        if new_password != confirm_password:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "La confirmacion de la nueva contrasena no coincide",
                    }
                ),
                400,
            )

        if new_password == current_password:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "La nueva contrasena debe ser diferente a la actual",
                    }
                ),
                400,
            )

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            raise RuntimeError("No se pudo obtener conexion a la base de datos")

        cursor = conn.cursor()
        if change_password:
            cursor.execute(
                """
                SELECT password_hash
                FROM usuarios_sistema
                WHERE username = %s
                """,
                (usuario,),
            )
            usuario_row = cursor.fetchone()
            password_hash_actual = ""

            if isinstance(usuario_row, dict):
                password_hash_actual = usuario_row.get("password_hash") or ""
            elif usuario_row:
                password_hash_actual = usuario_row[0]

            if not password_hash_actual:
                conn.rollback()
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "No fue posible validar tu contrasena actual",
                        }
                    ),
                    404,
                )

            if password_hash_actual != auth_system.hash_password(current_password):
                conn.rollback()
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "La contrasena actual es incorrecta",
                        }
                    ),
                    400,
                )

            cursor.execute(
                """
                UPDATE usuarios_sistema
                SET nombre_completo = %s,
                    email = %s,
                    password_hash = %s,
                    modificado_por = %s,
                    fecha_modificacion = %s,
                    intentos_fallidos = 0,
                    bloqueado_hasta = NULL
                WHERE username = %s
                """,
                (
                    nombre_completo,
                    email,
                    auth_system.hash_password(new_password),
                    usuario,
                    auth_system.get_mexico_time_mysql(),
                    usuario,
                ),
            )
        else:
            cursor.execute(
                """
                UPDATE usuarios_sistema
                SET nombre_completo = %s,
                    email = %s,
                    modificado_por = %s,
                    fecha_modificacion = %s
                WHERE username = %s
                """,
                (
                    nombre_completo,
                    email,
                    usuario,
                    auth_system.get_mexico_time_mysql(),
                    usuario,
                ),
            )

        if cursor.rowcount == 0:
            conn.rollback()
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "No fue posible actualizar este usuario",
                    }
                ),
                404,
            )

        conn.commit()
    except Exception as exc:
        if conn:
            conn.rollback()
        print(f"Error actualizando perfil de {usuario}: {exc}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "No fue posible guardar los cambios",
                }
            ),
            500,
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    session["nombre_completo"] = nombre_completo
    session["email"] = email
    session.modified = True

    auth_system.registrar_auditoria(
        usuario=usuario,
        modulo="sistema",
        accion="actualizar_perfil",
        descripcion=(
            "Actualizacion de perfil y contrasena desde la landing page"
            if change_password
            else "Actualizacion de perfil desde la landing page"
        ),
        resultado="EXITOSO",
    )

    return jsonify(
        {
            "success": True,
            "message": (
                "Perfil y contrasena actualizados correctamente"
                if change_password
                else "Perfil actualizado correctamente"
            ),
            "perfil": {
                "username": usuario,
                "nombre_completo": nombre_completo,
                "email": email,
                "rol": rol_principal,
                "roles": roles,
                "editable": True,
            },
        }
    )


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
        print(
            f"⚠️ Nombre completo no encontrado en sesión para {usuario}, obteniendo de BD..."
        )
        from .auth_system import auth_system

        info_usuario = auth_system.obtener_informacion_usuario(usuario)
        if info_usuario and info_usuario["nombre_completo"]:
            nombre_completo = info_usuario["nombre_completo"]
            session["nombre_completo"] = (
                nombre_completo  # Guardar en sesión para futuras consultas
            )
            print(f" Nombre completo obtenido de BD: {nombre_completo}")
        else:
            nombre_completo = usuario  # Fallback al username
            session["nombre_completo"] = usuario
            print(
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
            print(f"⚠️ Error obteniendo nombre completo para dashboard: {e}")
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


@app.route("/logout")
def logout():
    usuario = session.get("usuario", "unknown")

    # Registrar auditoría del logout
    if usuario != "unknown":
        auth_system.registrar_auditoria(
            usuario=usuario,
            modulo="sistema",
            accion="logout",
            descripcion="Cierre de sesión",
            resultado="EXITOSO",
        )
        print(f"🚪 Logout exitoso: {usuario}")

    # Limpiar sesión completa
    session.clear()

    return redirect(url_for("inicio"))


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


# Migracion 2026-05-26: _fp_safe_date y _fp_generate_lot_no consolidados en
# app/api/shared/plan_lot_no.py. Antes vivian duplicados aqui y en plan_smt.py.
from app.api.shared.plan_lot_no import (  # noqa: E402, F401
    _fp_generate_lot_no,
    _fp_safe_date,
)

# Migracion 2026-05-26: _ensure_plan_bom_assignment_columns, _plan_has_ks_snapshot
# y _validate_plan_bom_assignment consolidados en app/api/shared/bom_revisions.py
# (junto a los helpers existentes _ks_current_bom_revision, etc.).
# Antes vivian duplicados aqui y en plan_assy.py.
from app.api.shared.bom_revisions import (  # noqa: E402, F401
    _ks_current_bom_revision,
    _eco_for_part_revision,
    _plan_bom_revision_catalog,
    _ensure_plan_bom_assignment_columns,
    _plan_has_ks_snapshot,
    _validate_plan_bom_assignment,
)


# Migracion 2026-05-26: api_plan_list movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: helpers _PLAN_BOM_ASSIGNMENT_COLUMNS_READY, etc. movidos a shared/bom_revisions.py


# Migracion 2026-05-26: api_plan_bom_revisions movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_input_main_scan_lots movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_input_main_assign_lot movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_input_main_create_plan movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_create movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: api_plan_update movido a app/api/control_produccion/plan_assy.py


@app.route("/api/raw/search", methods=["GET"])
@login_requerido
def api_raw_search():
    """Buscar datos en la tabla RAW por part_no o model"""
    try:
        part_no = request.args.get("part_no", "").strip()
        if not part_no:
            return jsonify({"error": "part_no requerido"}), 400

        # Buscar con múltiples campos para mayor flexibilidad
        # Usar TRIM para ignorar espacios y comparación case-insensitive
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

        # CRÍTECO: Usar fetch='all' para obtener los datos, no el rowcount
        result = execute_query(sql, params, fetch="all")

        # Verificar que result sea una lista/tupla antes de usar len()
        if result and isinstance(result, (list, tuple)) and len(result) > 0:
            row = result[0]

            # execute_query con fetch='all' retorna lista de diccionarios
            # Acceder como diccionario, no como tupla
            data = {
                "part_no": row.get("part_no", "")
                if row.get("part_no") is not None
                else "",
                "model": row.get("model", "") if row.get("model") is not None else "",
                "model_code": row.get("model", "")
                if row.get("model") is not None
                else "",  # Alias
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
        print(f"Error al cargar template {template_name}: {str(e)}")
        return jsonify({"error": f"Error al cargar el template: {str(e)}"}), 500


# Limpieza 2026-05-26: rutas /guardar_entrada_aereo y /listar_entradas_aereo eliminadas.
# Sin consumidores en app/static/js/ ni en app/templates/. Tabla entrada_aereo (SQLite legacy)
# tampoco se lee desde ningun otro lado. Documentadas como huerfanas en
# Documentacion/VERIFICACION_DETALLADA_HUERFANAS.md lineas 39-40.


# Función de conexión movida a db.py - usar get_db_connection() importada


# Fase 1 (2026-05-28): /guardar_cliente_seleccionado y /cargar_cliente_seleccionado
# borradas — sin consumidores en app/static + app/templates. Sus helpers privados
# `cargar_configuracion_usuario` y `guardar_configuracion_usuario` se eliminaron tambien.


@app.route("/informacion_basica/control_de_material")
@login_requerido
def control_de_material_ajax():
    """Ruta para cargar dinámicamente el contenido de Control de Material"""
    try:
        return render_template("INFORMACION BASICA/CONTROL_DE_MATERIAL.html")
    except Exception as e:
        print(f"Error al cargar template Control de Material: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# Rutas para cargar contenido dinámicamente (AJAX)
@app.route("/listas/informacion_basica")
@login_requerido
def lista_informacion_basica():
    """Cargar dinámicamente la lista de Información Básica"""
    try:
        return render_template("LISTAS/LISTA_INFORMACIONBASICA.html")
    except Exception as e:
        print(f"Error al cargar LISTA_INFORMACIONBASICA: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/listas/control_material")
@login_requerido
def lista_control_material():
    """Cargar dinámicamente la lista de Control de Material"""
    try:
        return render_template("LISTAS/LISTA_DE_MATERIALES.html")
    except Exception as e:
        print(f"Error al cargar LISTA_DE_MATERIALES: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/listas/control_produccion")
@login_requerido
def lista_control_produccion():
    """Cargar dinámicamente la lista de Control de Producción"""
    try:
        return render_template("LISTAS/LISTA_CONTROLDEPRODUCCION.html")
    except Exception as e:
        print(f"Error al cargar LISTA_CONTROLDEPRODUCCION: {e}")
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


@app.route("/api/inventario/modelo/<codigo_modelo>", methods=["GET"])
@login_requerido
def api_inventario_modelo(codigo_modelo):
    """API para obtener inventario por código de modelo"""
    try:
        query = """
        SELECT modelo, nparte, stock_total, ubicaciones,
               ultima_entrada, ultima_salida, updated_at
        FROM inv_resumen_modelo
        WHERE nparte = %s
        """

        inventario = execute_query(query, (codigo_modelo,), fetch="all")

        # Formatear respuesta
        resultado = []
        for item in inventario:
            resultado.append(
                {
                    "modelo": item["modelo"],
                    "nparte": item["nparte"],
                    "stock_total": item["stock_total"] or 0,
                    "ubicaciones": item["ubicaciones"] or "",
                    "ultima_entrada": item["ultima_entrada"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if item["ultima_entrada"]
                    else "",
                    "ultima_salida": item["ultima_salida"].strftime("%Y-%m-%d %H:%M:%S")
                    if item["ultima_salida"]
                    else "",
                    "updated_at": item["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if item["updated_at"]
                    else "",
                }
            )

        return jsonify(resultado)

    except Exception as e:
        print(f" Error en API inventario modelo {codigo_modelo}: {e}")
        return jsonify({"error": str(e)}), 500



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
        print(f"Error al cargar LISTA_CONTROL_DE_PROCESO: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/listas/control_calidad")
@login_requerido
def lista_control_calidad():
    """Cargar dinámicamente la lista de Control de Calidad"""
    try:
        return render_template("LISTAS/LISTA_CONTROL_DE_CALIDAD.html")
    except Exception as e:
        print(f"Error al cargar LISTA_CONTROL_DE_CALIDAD: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/listas/control_resultados")
@login_requerido
def lista_control_resultados():
    """Cargar dinámicamente la lista de Control de Resultados"""
    try:
        return render_template("LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html")
    except Exception as e:
        print(f"Error al cargar LISTA_DE_CONTROL_DE_RESULTADOS: {e}")
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
        print(f"Error al cargar LISTA_DE_CONTROL_DE_REPORTE: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/listas/configuracion_programa")
@login_requerido
def lista_configuracion_programa():
    """Cargar dinámicamente la lista de Configuración de Programa"""
    try:
        return render_template("LISTAS/LISTA_DE_CONFIGPG.html")
    except Exception as e:
        print(f"Error al cargar LISTA_DE_CONFIGPG: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/material/info")
@login_requerido
def material_info():
    """Cargar dinámicamente la información general de material"""
    try:
        return render_template("info.html")
    except Exception as e:
        print(f"Error al cargar info.html: {e}")
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
        print(f"Error sirviendo plantilla {filename}: {str(e)}")
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

        tiene_permiso = auth_system.verificar_permiso_boton(
            username, pagina, seccion, boton
        )

        return jsonify(
            {
                "tiene_permiso": tiene_permiso,
                "usuario": username,
                "rol": rol_nombre,
                "permiso": f"{pagina} > {seccion} > {boton}",
            }
        )

    except Exception as e:
        print(f"Error verificando permiso: {e}")
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

        permisos = auth_system.obtener_permisos_botones_usuario(username)

        # Formatear permisos para JavaScript en estructura jerárquica
        permisos_jerarquicos = {}
        total_permisos = 0

        for pagina, secciones in permisos.items():
            permisos_jerarquicos[pagina] = {}
            for seccion, botones in secciones.items():
                permisos_jerarquicos[pagina][seccion] = []
                for item in botones:
                    boton = item.get("boton") if isinstance(item, dict) else item
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
        print(f"Error obteniendo permisos: {e}")
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


def crear_patron_caracteres(
    texto_original, part_start, part_length, lot_start, lot_length
):
    """
    Crea un patrón de caracteres donde:
    - Caracteres específicos se mantienen como están
    - Números se marcan como 'N'
    - Letras se marcan como 'A'
    - Las zonas de número de parte y lote se marcan como 'X' (cualquier carácter)
    """
    patron = list(texto_original)

    # Marcar la zona del número de parte como 'X' (cualquier carácter)
    for i in range(part_start, part_start + part_length):
        if i < len(patron):
            patron[i] = "X"

    # Marcar la zona del lote como 'X' solo si existe lote
    if lot_start != -1 and lot_length > 0:
        for i in range(lot_start, lot_start + lot_length):
            if i < len(patron):
                patron[i] = "X"

    # Para el resto de caracteres, determinar el tipo
    for i, char in enumerate(patron):
        if char != "X":  # Si no es una zona variable
            if char.isdigit():
                patron[i] = "N"  # Número específico
            elif char.isalpha():
                patron[i] = "A"  # Letra específica
            # Los caracteres especiales y espacios se mantienen como están

    return "".join(patron)


# Fase 1 (2026-05-28): cargar_configuracion_usuario / guardar_configuracion_usuario
# borradas con guardar_cliente_seleccionado y cargar_cliente_seleccionado (eran sus unicos consumidores).


@app.route("/importar_excel_plan_produccion", methods=["POST"])
@login_requerido
def importar_excel_plan_produccion():
    """Importar plan de producción desde Excel"""
    conn = None
    cursor = None
    temp_path = None

    try:
        if "file" not in request.files:
            return jsonify(
                {"success": False, "error": "No se proporcionó archivo"}
            ), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No se seleccionó archivo"}), 400

        if (
            not file
            or not file.filename
            or not file.filename.lower().endswith((".xlsx", ".xls"))
        ):
            return jsonify(
                {
                    "success": False,
                    "error": "Formato de archivo no válido. Use .xlsx o .xls",
                }
            ), 400

        # Guardar el archivo temporalmente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), "temp_" + filename)
        file.save(temp_path)

        # Leer el archivo Excel
        try:
            # Intentar leer con encabezados primero
            df = pd.read_excel(
                temp_path, engine="openpyxl" if filename.endswith(".xlsx") else "xlrd"
            )

            # Si las primeras filas contienen datos directamente (sin encabezados claros)
            # y las columnas tienen nombres genéricos como 0, 1, 2, etc.
            if all(isinstance(col, int) for col in df.columns):
                # Leer sin encabezados y asignar nombres de columnas
                df = pd.read_excel(
                    temp_path,
                    header=None,
                    engine="openpyxl" if filename.endswith(".xlsx") else "xlrd",
                )
                # Asignar nombres basados en la posición
                if len(df.columns) >= 3:
                    df.columns = ["Modelo", "Numero_Parte", "Cantidad"] + [
                        f"Col_{i}" for i in range(3, len(df.columns))
                    ]
                elif len(df.columns) == 2:
                    df.columns = ["Modelo", "Cantidad"]
                else:
                    df.columns = ["Modelo"]
        except Exception as e:
            try:
                # Intentar leer sin encabezados como respaldo
                df = pd.read_excel(temp_path, header=None)
                if len(df.columns) >= 3:
                    df.columns = ["Modelo", "Numero_Parte", "Cantidad"] + [
                        f"Col_{i}" for i in range(3, len(df.columns))
                    ]
                elif len(df.columns) == 2:
                    df.columns = ["Modelo", "Cantidad"]
                else:
                    df.columns = ["Modelo"]
            except Exception as e2:
                return jsonify(
                    {
                        "success": False,
                        "error": f"Error al leer el archivo Excel: {str(e2)}",
                    }
                ), 500

        # Verificar que el DataFrame no esté vacío
        if df.empty:
            return jsonify(
                {"success": False, "error": "El archivo Excel está vacío"}
            ), 400

        # Obtener usuario de la sesión
        usuario_actual = session.get("usuario", "USUARIO_EXCEL")

        # Obtener fecha de operación seleccionada por el usuario
        fecha_operacion_usuario = request.form.get("fecha_operacion", "").strip()
        if fecha_operacion_usuario:
            print(
                f" Fecha de operación personalizada seleccionada: {fecha_operacion_usuario}"
            )
        else:
            print(" Usando fechas del Excel o fecha actual como respaldo")

        # Función auxiliar para obtener nombre del modelo desde raw
        def obtener_nombre_modelo(codigo_modelo):
            """Obtener nombre (project) desde raw por part_no"""
            try:
                if not codigo_modelo:
                    return ""
                cursor.execute(
                    "SELECT project FROM raw WHERE TRIM(part_no)=TRIM(%s) ORDER BY id DESC LIMIT 1",
                    (codigo_modelo,),
                )
                row = cursor.fetchone()
                return (row.get("project") if row else "") or ""
            except Exception as e:
                print(f"Error obteniendo nombre modelo para {codigo_modelo}: {e}")
                return ""

        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()

        # Asegurar que la tabla work_orders tenga la columna linea
        try:
            cursor.execute("SHOW COLUMNS FROM work_orders LIKE 'linea'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE work_orders ADD COLUMN linea VARCHAR(32)")
                print(" Columna 'linea' agregada a work_orders")
        except Exception as e:
            print(f"Error agregando columna linea: {e}")

        registros_insertados = 0
        registros_actualizados = 0
        errores = []

        # Mapeo de columnas (flexible para diferentes nombres)
        mapeo_columnas = {
            "linea": ["Linea", "linea", "Line", "LINEA", "Línea"],
            "modelo": ["Modelo", "modelo", "Model", "MODELO"],
            "numero_parte": [
                "Numero de parte",
                "Número de parte",
                "numero_parte",
                "Part Number",
                "NUMERO_PARTE",
                "Numero_Parte",
            ],
            "cantidad": ["Cantidad", "cantidad", "Quantity", "CANTIDAD"],
            "fecha_operacion": [
                "Fecha",
                "fecha_operacion",
                "Fecha de operación",
                "Date",
                "FECHA",
            ],
            "codigo_po": [
                "PO",
                "codigo_po",
                "Código PO",
                "Purchase Order",
                "CODIGO_PO",
            ],
        }

        # Debug: Mostrar información del DataFrame
        print(f"Columnas en el DataFrame: {list(df.columns)}")
        print(f"Primeras 3 filas del DataFrame:")
        print(df.head(3))

        # Detectar columnas disponibles
        columnas_detectadas = {}
        for campo, posibles_nombres in mapeo_columnas.items():
            for nombre in posibles_nombres:
                if nombre in df.columns:
                    columnas_detectadas[campo] = nombre
                    break

        print(f"Columnas detectadas: {columnas_detectadas}")

        # Verificar que al menos tengamos modelo y cantidad
        if "modelo" not in columnas_detectadas or "cantidad" not in columnas_detectadas:
            # Información detallada para debugging
            error_msg = (
                f"El archivo debe contener al menos las columnas: Modelo y Cantidad. "
            )
            error_msg += f"Columnas encontradas: {list(df.columns)}. "
            error_msg += f"Mapeo detectado: {columnas_detectadas}"

            return jsonify({"success": False, "error": error_msg}), 400

        # Procesar cada fila del DataFrame
        for index, row in df.iterrows():
            try:
                # Extraer datos de la fila
                modelo = str(row.get(columnas_detectadas["modelo"], "")).strip()
                cantidad = row.get(columnas_detectadas["cantidad"], 0)

                # Validar datos básicos
                if not modelo or modelo == "nan":
                    errores.append(f"Fila {index + 2}: Modelo vacío")
                    continue

                try:
                    cantidad = (
                        int(float(cantidad))
                        if cantidad and str(cantidad) != "nan"
                        else 0
                    )
                except (ValueError, TypeError):
                    cantidad = 0

                if cantidad <= 0:
                    errores.append(f"Fila {index + 2}: Cantidad inválida ({cantidad})")
                    continue

                # Datos opcionales
                linea = str(row.get(columnas_detectadas.get("linea", ""), "")).strip()
                if linea == "nan":
                    linea = ""

                numero_parte = str(
                    row.get(columnas_detectadas.get("numero_parte", ""), "")
                ).strip()
                if numero_parte == "nan":
                    numero_parte = ""

                codigo_po = str(
                    row.get(columnas_detectadas.get("codigo_po", ""), "SIN-PO")
                ).strip()
                if codigo_po == "nan" or not codigo_po:
                    codigo_po = "SIN-PO"

                # Fecha de operación - priorizar la fecha seleccionada por el usuario
                fecha_operacion_usuario = request.form.get(
                    "fecha_operacion", ""
                ).strip()

                if fecha_operacion_usuario:
                    # Usar la fecha seleccionada por el usuario
                    fecha_operacion = fecha_operacion_usuario
                else:
                    # Usar la fecha del Excel o fecha actual como respaldo
                    fecha_operacion = row.get(
                        columnas_detectadas.get("fecha_operacion", ""), ""
                    )
                    if pd.isna(fecha_operacion) or fecha_operacion == "nan":
                        fecha_operacion = datetime.now().strftime("%Y-%m-%d")
                    else:
                        try:
                            if isinstance(fecha_operacion, str):
                                # Intentar convertir string a fecha
                                from dateutil import parser

                                fecha_operacion = parser.parse(
                                    fecha_operacion
                                ).strftime("%Y-%m-%d")
                            else:
                                # Es datetime o similar
                                fecha_operacion = fecha_operacion.strftime("%Y-%m-%d")
                        except:
                            fecha_operacion = datetime.now().strftime("%Y-%m-%d")

                # Generar código WO único
                fecha_codigo = datetime.now().strftime("%y%m%d")

                # Buscar el último número de secuencia para hoy
                cursor.execute(
                    """
                    SELECT codigo_wo FROM work_orders
                    WHERE codigo_wo LIKE %s
                    ORDER BY codigo_wo DESC LIMIT 1
                """,
                    (f"WO-{fecha_codigo}-%",),
                )

                ultimo_wo = cursor.fetchone()
                if ultimo_wo:
                    try:
                        ultimo_numero = int(ultimo_wo["codigo_wo"].split("-")[-1])
                        nuevo_numero = ultimo_numero + 1
                    except:
                        nuevo_numero = 1
                else:
                    nuevo_numero = 1

                codigo_wo = f"WO-{fecha_codigo}-{nuevo_numero:04d}"

                # Obtener nombre del modelo desde la tabla raw
                codigo_modelo = modelo
                nombre_modelo = obtener_nombre_modelo(codigo_modelo)

                # Insertar nueva WO
                cursor.execute(
                    """
                    INSERT INTO work_orders
                    (codigo_wo, codigo_po, modelo, codigo_modelo, nombre_modelo, linea,
                     cantidad_planeada, fecha_operacion, usuario_creacion, modificador, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'CREADA')
                """,
                    (
                        codigo_wo,
                        codigo_po,
                        modelo
                        if modelo
                        else numero_parte,  # Usar modelo o numero_parte como respaldo
                        codigo_modelo,
                        nombre_modelo,
                        linea,
                        cantidad,
                        fecha_operacion,
                        usuario_actual,
                        usuario_actual,
                    ),
                )

                registros_insertados += 1

            except Exception as e:
                errores.append(f"Fila {index + 2}: {str(e)}")
                continue

        # Confirmar transacción
        conn.commit()

        # Preparar respuesta
        mensaje = f"Importación completada. {registros_insertados} WOs creadas."
        if fecha_operacion_usuario:
            mensaje += f" Fecha de operación aplicada: {fecha_operacion_usuario}."
        if errores:
            mensaje += f" {len(errores)} errores encontrados."

        return jsonify(
            {
                "success": True,
                "message": mensaje,
                "registros_procesados": registros_insertados,
                "errores": len(errores),
                "fecha_aplicada": fecha_operacion_usuario or "Fechas del Excel/Actual",
                "detalles": {
                    "insertados": registros_insertados,
                    "errores": errores[:10]
                    if errores
                    else [],  # Solo primeros 10 errores
                },
            }
        )

    except Exception as e:
        print(f"Error general en importar_excel_plan_produccion: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500

    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            print(f"Error en cleanup: {str(e)}")


@app.route("/produccion/info")
@login_requerido
def produccion_info():
    try:
        return render_template("CONTROL DE PRODUCCION/info_produccion.html")
    except Exception as e:
        return f"Error al cargar información de producción: {str(e)}", 500


# Migracion 2026-05-27: GET /api/wo/exportar movido a
# app/api/control_produccion/po_wo.py (misma URL, mismo comportamiento).



@app.route("/api/inventario", methods=["GET"])
@login_requerido
def api_inventario():
    """API para consultar inventario por modelo y/o nparte"""
    try:
        modelo = request.args.get("modelo", "").strip()
        nparte = request.args.get("nparte", "").strip()

        if not modelo:
            return jsonify({"error": "Parámetro modelo es requerido"}), 400

        if nparte:
            # Consultar inventario específico por modelo y nparte
            query = """
            SELECT modelo, nparte, stock_total, ubicaciones, ultima_entrada, ultima_salida, updated_at
            FROM inv_resumen_modelo
            WHERE modelo = %s AND nparte = %s
            """
            result = execute_query(query, (modelo, nparte), fetch="one")

            if result:
                return jsonify(
                    {
                        "modelo": result["modelo"],
                        "nparte": result["nparte"],
                        "stock_total": result["stock_total"] or 0,
                    }
                )
            else:
                return jsonify({"modelo": modelo, "nparte": nparte, "stock_total": 0})
        else:
            # Consultar inventario total del modelo
            query = """
            SELECT modelo, SUM(stock_total) as stock_total
            FROM inv_resumen_modelo
            WHERE modelo = %s
            GROUP BY modelo
            """
            result = execute_query(query, (modelo,), fetch="one")

            if result:
                return jsonify(
                    {
                        "modelo": result["modelo"],
                        "stock_total": result["stock_total"] or 0,
                    }
                )
            else:
                return jsonify({"modelo": modelo, "stock_total": 0})

    except Exception as e:
        print(f" Error consultando inventario: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# RUTAS PARA CONTROL DE CALIDAD
# ============================================================================


# Fase 3.3 (2026-05-28): /control-resultado-reparacion-ajax y
# /control-item-reparado-ajax movidos a app/api/control_calidad/renders.py.


# Eliminado 2026-05-27: "Historial de cambio de material por maquina" dado de baja
# (modulo no usado). Rutas borradas:
#   /historial-cambio-material-maquina-ajax  (render)
#   /api/historial-cambio-material-maquina   (GET)


# ==========================
# Historial SMT (ultimo por linea/maquina/slot)
# ==========================
@app.route("/api/historial_smt_latest", methods=["GET"])
@login_requerido
def api_historial_smt_latest():
    """Devuelve el ultimo escaneo por (linea, maquina, SlotNo) desde la tabla
    historial_cambio_material_smt. Pensado para el panel de Control de Operacion SMT
    que requiere el ultimo material escaneado para hacer match con el BOM.

    Parametros:
      - linea: opcional. Ej: 'SMT B'. Si se omite, devuelve para todas las lineas.
    """
    try:
        linea = request.args.get("linea", "").strip()

        from .db_mysql import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        where_sub = ""
        params = []
        if linea:
            where_sub = "WHERE linea = %s"
            params.append(linea)

        # Seleccionar el ultimo registro por grupo usando fecha_subida
        query = f"""
            SELECT h.id, h.linea, h.maquina, h.archivo, h.ScanDate, h.ScanTime,
                   h.SlotNo, h.Result, h.PreviousBarcode, h.Productdate,
                   h.PartName, h.Quantity, h.SEQ, h.Vendor, h.LOTNO,
                   h.Barcode, h.FeederBase, h.fecha_subida,
                   CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                        WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                        ELSE 'UNKNOWN' END AS side_norm
            FROM historial_cambio_material_smt h
            INNER JOIN (
                SELECT linea, maquina, SlotNo,
                       CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                            WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                            ELSE 'UNKNOWN' END AS side_norm,
                       MAX(fecha_subida) AS max_fecha
                FROM historial_cambio_material_smt
                {where_sub}
                GROUP BY linea, maquina, SlotNo, side_norm
            ) m
            ON h.linea = m.linea AND h.maquina = m.maquina
               AND h.SlotNo = m.SlotNo AND h.fecha_subida = m.max_fecha
               AND (
                    (CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                          WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                          ELSE 'UNKNOWN' END) = m.side_norm
               )
            {("WHERE h.linea = %s" if linea else "")}
            ORDER BY h.linea, h.maquina, h.SlotNo, side_norm
        """

        if linea:
            # Parametros para subconsulta y para el filtro externo
            cursor.execute(query, params + params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()

        data = []
        for r in rows:
            # Indices alineados al SELECT de arriba
            linea_v = r[1] if len(r) > 1 else ""
            maquina_v = r[2] if len(r) > 2 else ""
            scan_date = r[4] if len(r) > 4 else ""
            scan_time = r[5] if len(r) > 5 else ""
            slot_no = r[6] if len(r) > 6 else ""
            part_name = r[10] if len(r) > 10 else ""
            quantity = r[11] if len(r) > 11 else 0
            vendor = r[13] if len(r) > 13 else ""
            feeder_base = r[16] if len(r) > 16 else ""

            # Normalizaciones amigables para el frontend existente
            formatted = {
                "linea": linea_v,
                "maquina": maquina_v,  # usado para extraer mounter (mN)
                "Equipment": maquina_v,  # alias por compatibilidad
                "SlotNo": slot_no,
                "FeederBase": feeder_base,
                "RegistDate": scan_date,  # el frontend ya acepta varios nombres
                "fecha_formateada": scan_date,
                "PartName": part_name,  # se usa para matching contra BOM Material Code
                "Quantity": quantity,
                "Vendor": vendor,
                "ScanDate": scan_date,
                "ScanTime": scan_time,
            }
            data.append(formatted)

        cursor.close()
        conn.close()

        return jsonify({"success": True, "data": data, "total": len(data)})
    except Exception as e:
        print(f"Error en api_historial_smt_latest: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


# Variante robusta con lado FRONT/REAR agrupado explicitamente
@app.route("/api/historial_smt_latest_v2", methods=["GET"])
@login_requerido
def api_historial_smt_latest_v2():
    try:
        linea_input = request.args.get("linea", "").strip()
        # Convertir nombre de línea a formato de BD
        linea = convertir_linea_smt(linea_input)

        from .db_mysql import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        where_sub = ""
        params = []
        if linea:
            where_sub = "WHERE linea = %s"
            params.append(linea)

        query = f"""
            SELECT h.id, h.linea, h.maquina, h.archivo, h.ScanDate, h.ScanTime,
                   h.SlotNo, h.Result, h.PreviousBarcode, h.Productdate,
                   h.PartName, h.Quantity, h.SEQ, h.Vendor, h.LOTNO,
                   h.Barcode, h.FeederBase, h.fecha_subida,
                   CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                        WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                        ELSE 'UNKNOWN' END AS side_norm
            FROM historial_cambio_material_smt h
            INNER JOIN (
                SELECT linea, maquina, SlotNo,
                       (CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                             WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                             ELSE 'UNKNOWN' END) AS side_norm,
                       MAX(fecha_subida) AS max_fecha
                FROM historial_cambio_material_smt
                {where_sub}
                GROUP BY linea, maquina, SlotNo,
                         (CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                               WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                               ELSE 'UNKNOWN' END)
            ) m
              ON h.linea = m.linea AND h.maquina = m.maquina
             AND h.SlotNo = m.SlotNo AND h.fecha_subida = m.max_fecha
             AND (
                 (CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                       WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                       ELSE 'UNKNOWN' END) = m.side_norm
             )
            {("WHERE h.linea = %s" if linea else "")}
            ORDER BY h.linea, h.maquina, h.SlotNo, m.side_norm
        """

        if linea:
            cursor.execute(query, params + params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()
        data = []
        for r in rows:
            linea_v = r[1] if len(r) > 1 else ""
            maquina_v = r[2] if len(r) > 2 else ""
            scan_date = r[4] if len(r) > 4 else ""
            scan_time = r[5] if len(r) > 5 else ""
            slot_no = r[6] if len(r) > 6 else ""
            part_name = r[10] if len(r) > 10 else ""
            quantity = r[11] if len(r) > 11 else 0
            vendor = r[13] if len(r) > 13 else ""
            feeder_base = r[16] if len(r) > 16 else ""

            formatted = {
                "linea": linea_v,
                "maquina": maquina_v,
                "Equipment": maquina_v,
                "SlotNo": slot_no,
                "FeederBase": feeder_base,
                "RegistDate": scan_date,
                "fecha_formateada": scan_date,
                "PartName": part_name,
                "Quantity": quantity,
                "Vendor": vendor,
                "ScanDate": scan_date,
                "ScanTime": scan_time,
            }
            data.append(formatted)

        cursor.close()
        conn.close()

        return jsonify({"success": True, "data": data, "total": len(data)})
    except Exception as e:
        print("Error en api_historial_smt_latest_v2:", e)
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================
# Metal Mask info lookup
# ==========================
@app.route("/api/masks/info", methods=["GET"])
@login_requerido
def api_masks_info():
    try:
        code = request.args.get("code", "").strip()
        if not code:
            return jsonify({"success": False, "error": "code requerido"}), 400

        from .db_mysql import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        q = """
            SELECT management_no, storage_box, pcb_code, side, production_date,
                   used_count, max_count, allowance, model_name, tension_min,
                   tension_max, thickness, supplier, registration_date, disuse
            FROM masks
            WHERE management_no = %s
            LIMIT 1
        """
        cursor.execute(q, [code])
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return jsonify(
                {"success": False, "found": False, "message": "No encontrado"}
            )

        fields = [
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
        ]
        data = {
            fields[i]: (row[i] if i < len(row) else None) for i in range(len(fields))
        }

        def to_int(v):
            try:
                return int(v)
            except Exception:
                try:
                    return int(float(v))
                except Exception:
                    return 0

        data["used_count"] = to_int(data.get("used_count"))
        data["max_count"] = to_int(data.get("max_count"))
        data["allowance"] = to_int(data.get("allowance"))

        return jsonify({"success": True, "found": True, "data": data})
    except Exception as e:
        print("Error en api_masks_info:", e)
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


# Fase 3.3 (2026-05-28): /historial-uso-pegamento-soldadura-ajax movido a
# app/api/control_calidad/renders.py.


# ==========================
# API para historial de Metal Mask
# ==========================
@app.route("/api/metal-mask/history", methods=["POST"])
@login_requerido
def api_save_metal_mask_history():
    """Guardar historial de uso de Metal Mask"""
    try:
        data = request.get_json()

        # Validar datos requeridos
        required_fields = ["mask_code", "model_code", "linea", "quantity_used"]
        for field in required_fields:
            if not data.get(field):
                return jsonify(
                    {"success": False, "error": f"{field} es requerido"}
                ), 400

        from .db_mysql import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        # Crear tabla si no existe
        create_table_query = """
            CREATE TABLE IF NOT EXISTS metal_mask_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mask_code VARCHAR(50) NOT NULL,
                model_code VARCHAR(50) NOT NULL,
                linea VARCHAR(20) NOT NULL,
                quantity_used INT NOT NULL DEFAULT 0,
                scan_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                usuario VARCHAR(50),
                plan_id INT,
                run_id INT,
                available_uses INT DEFAULT 0,
                total_uses INT DEFAULT 0,
                status ENUM('OK', 'NG', 'WARNING') DEFAULT 'OK',
                notes TEXT,
                INDEX idx_mask_code (mask_code),
                INDEX idx_model_code (model_code),
                INDEX idx_linea (linea),
                INDEX idx_scan_date (scan_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        cursor.execute(create_table_query)
        conn.commit()

        # Insertar registro de historial
        insert_query = """
            INSERT INTO metal_mask_history
            (mask_code, model_code, linea, quantity_used, usuario, plan_id, run_id,
             available_uses, total_uses, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        usuario = session.get("usuario_logueado", "Sistema")
        plan_id = data.get("plan_id")
        run_id = data.get("run_id")
        available_uses = data.get("available_uses", 0)
        total_uses = data.get("total_uses", 0)
        status = data.get("status", "OK")
        notes = data.get("notes", "")

        cursor.execute(
            insert_query,
            [
                data["mask_code"],
                data["model_code"],
                data["linea"],
                data["quantity_used"],
                usuario,
                plan_id,
                run_id,
                available_uses,
                total_uses,
                status,
                notes,
            ],
        )

        history_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify(
            {
                "success": True,
                "history_id": history_id,
                "message": "Historial de Metal Mask guardado correctamente",
            }
        )

    except Exception as e:
        print("Error en api_save_metal_mask_history:", e)
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/metal-mask/history", methods=["GET"])
@login_requerido
def api_get_metal_mask_history():
    """Obtener historial de uso de Metal Mask"""
    try:
        # Parámetros de filtro
        mask_code = request.args.get("mask_code", "").strip()
        model_code = request.args.get("model_code", "").strip()
        linea = request.args.get("linea", "").strip()
        date_from = request.args.get("date_from", "").strip()
        date_to = request.args.get("date_to", "").strip()
        limit = int(request.args.get("limit", 100))

        from .db_mysql import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        # Construir consulta con filtros
        where_conditions = []
        params = []

        if mask_code:
            where_conditions.append("mask_code = %s")
            params.append(mask_code)

        if model_code:
            where_conditions.append("model_code = %s")
            params.append(model_code)

        if linea:
            where_conditions.append("linea = %s")
            params.append(linea)

        if date_from:
            where_conditions.append("scan_date >= %s")
            params.append(date_from)

        if date_to:
            where_conditions.append("scan_date <= %s")
            params.append(date_to + " 23:59:59")

        where_clause = (
            "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        )

        query = f"""
            SELECT id, mask_code, model_code, linea, quantity_used,
                   DATE_FORMAT(scan_date, '%%Y-%%m-%%d %%H:%%i:%%s') as scan_date,
                   usuario, plan_id, run_id, available_uses, total_uses,
                   status, notes
            FROM metal_mask_history
            {where_clause}
            ORDER BY scan_date DESC
            LIMIT %s
        """

        params.append(limit)
        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convertir a lista de diccionarios
        columns = [
            "id",
            "mask_code",
            "model_code",
            "linea",
            "quantity_used",
            "scan_date",
            "usuario",
            "plan_id",
            "run_id",
            "available_uses",
            "total_uses",
            "status",
            "notes",
        ]

        data = [dict(zip(columns, row)) for row in rows]

        cursor.close()
        conn.close()

        return jsonify({"success": True, "data": data, "count": len(data)})

    except Exception as e:
        print(" Error en api_get_metal_mask_history:", e)
        print(" Traceback completo:")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/metal-mask/update-used-count", methods=["POST"])
@login_requerido
def api_update_metal_mask_used_count():
    """Actualizar used_count de Metal Mask al finalizar plan"""
    try:
        data = request.get_json()
        plan_id = data.get("plan_id")
        cantidad_producida = int(data.get("cantidad_producida", 0))

        if not plan_id or cantidad_producida <= 0:
            return jsonify(
                {
                    "success": False,
                    "error": "plan_id y cantidad_producida son requeridos",
                }
            )

        from .db_mysql import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        # 1. Obtener información del plan para saber el modelo y línea
        cursor.execute(
            """
            SELECT modelo, linea, nparte
            FROM plan_smd
            WHERE id = %s
        """,
            (plan_id,),
        )
        plan_info = cursor.fetchone()

        if not plan_info:
            return jsonify({"success": False, "error": "Plan no encontrado"})

        modelo, linea, nparte = plan_info

        # 2. Buscar Metal Masks que se usaron para este modelo/línea
        # Prioridad 1: Buscar por plan_id específico
        cursor.execute(
            """
            SELECT DISTINCT mask_code, COUNT(*) as usage_count
            FROM metal_mask_history
            WHERE plan_id = %s
            GROUP BY mask_code
            ORDER BY usage_count DESC, scan_date DESC
        """,
            (plan_id,),
        )

        mask_codes = [row[0] for row in cursor.fetchall()]

        # Prioridad 2: Si no hay historial del plan, buscar por modelo/línea reciente
        if not mask_codes:
            cursor.execute(
                """
                SELECT DISTINCT mask_code, COUNT(*) as usage_count
                FROM metal_mask_history
                WHERE model_code = %s AND linea = %s
                AND scan_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY mask_code
                ORDER BY usage_count DESC, scan_date DESC
                LIMIT 3
            """,
                (modelo, linea),
            )
            mask_codes = [row[0] for row in cursor.fetchall()]

        # Prioridad 3: Buscar cualquier mask para el modelo (último recurso)
        if not mask_codes:
            cursor.execute(
                """
                SELECT DISTINCT mask_code
                FROM metal_mask_history
                WHERE model_code = %s
                ORDER BY scan_date DESC
                LIMIT 1
            """,
                (modelo,),
            )
            mask_codes = [row[0] for row in cursor.fetchall()]

        updated_count = 0

        # 3. Actualizar used_count en la tabla masks para cada mask_code encontrada
        for mask_code in mask_codes:
            cursor.execute(
                """
                UPDATE masks
                SET used_count = used_count + %s
                WHERE management_no = %s
            """,
                (cantidad_producida, mask_code),
            )

            if cursor.rowcount > 0:
                updated_count += cursor.rowcount
                print(
                    f" Metal Mask {mask_code} - used_count incrementado en {cantidad_producida}"
                )

        # 4. Registrar el update en el historial para cada mask actualizada
        for mask_code in mask_codes:
            # Obtener información actualizada de la mask
            cursor.execute(
                """
                SELECT used_count, max_count, allowance
                FROM masks
                WHERE management_no = %s
            """,
                (mask_code,),
            )

            mask_info = cursor.fetchone()
            if mask_info:
                used_count, max_count, allowance = mask_info
                available_uses = max(0, (max_count + allowance) - used_count)

                cursor.execute(
                    """
                    INSERT INTO metal_mask_history
                    (mask_code, model_code, linea, quantity_used, plan_id,
                     available_uses, total_uses, status, notes, usuario, scan_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                    (
                        mask_code,
                        modelo,
                        linea,
                        cantidad_producida,
                        plan_id,
                        available_uses,
                        used_count,
                        "END_PLAN",
                        f"Finalización de plan {plan_id} - Producido: {cantidad_producida}",
                        session.get("usuario", "sistema"),
                    ),
                )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify(
            {
                "success": True,
                "updated_masks": updated_count,
                "cantidad_producida": cantidad_producida,
                "plan_id": plan_id,
                "masks_actualizadas": mask_codes,
            }
        )

    except Exception as e:
        print(" Error actualizando used_count:", e)
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


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



def generar_lot_no_secuencial(q, like, prefix, fecha):
    """Genera un numero de lote secuencial basado en la consulta"""
    last = execute_query(q, (like,), fetch="one")
    if last and last.get("lot_no"):
        try:
            seq = int(last["lot_no"].split("-")[-1]) + 1
        except Exception:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{fecha}-{seq:04d}"


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


@app.route("/api/bom-smt-data", methods=["GET"])
@login_requerido
def api_bom_smt_data():
    """API para obtener datos del BOM SMT basado en lonea y modelo"""
    try:
        # Obtener parometros
        linea = request.args.get("linea", "")
        model_code = request.args.get("model_code", "")

        if not linea or not model_code:
            return jsonify(
                {"success": False, "error": "Lonea y modelo son requeridos"}
            ), 400

        print(f"API BOM SMT - Filtros:")
        print(f"  Linea: {linea}")
        print(f"  Modelo: {model_code}")

        from .db_mysql import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        # Mapear lonea SMT a nomero de lonea
        mapeo_lineas = {
            "SMT A": "2",
            "SMT B": "2",
            "SMT C": "3",
            "SMT D": "4",
            "1LINE": "2",
            "2LINE": "2",
            "3LINE": "3",
            "4LINE": "4",
        }

        linea_numero = mapeo_lineas.get(linea, "2")

        # Consultar ambas tablas (bom_smt_f y bom_smt_r) - solo elementos con cantidad > 0
        query_f = """
            SELECT
                id, linea, model_code, mounter, slot, material_code,
                description, feeder_info, qty, raw_filename,
                created_at, updated_at, 'FRONT' as tabla_tipo
            FROM bom_smt_f
            WHERE linea = %s AND model_code LIKE %s AND qty > 0
            ORDER BY mounter, slot
        """

        query_r = """
            SELECT
                id, linea, model_code, mounter, slot, material_code,
                description, feeder_info, qty, raw_filename,
                created_at, updated_at, 'REAR' as tabla_tipo
            FROM bom_smt_r
            WHERE linea = %s AND model_code LIKE %s AND qty > 0
            ORDER BY mounter, slot
        """

        # Buscar por modelo (puede contener EBR)
        model_pattern = f"%{model_code}%"

        # Ejecutar consultas
        cursor.execute(query_f, [linea_numero, model_pattern])
        resultados_f = cursor.fetchall()

        cursor.execute(query_r, [linea_numero, model_pattern])
        resultados_r = cursor.fetchall()

        # Combinar resultados
        todos_resultados = list(resultados_f) + list(resultados_r)

        print(
            f"Encontrados {len(todos_resultados)} registros BOM ({len(resultados_f)} F + {len(resultados_r)} R)"
        )
        print(
            f"Parametros de busqueda - Linea numero: {linea_numero}, Patron modelo: {model_pattern}"
        )

        # Formatear datos - solo incluir elementos con cantidad > 0
        formatted_data = []
        for row in todos_resultados:
            try:
                qty_value = row[8] if len(row) > 8 else 0

                # Solo incluir si qty > 0
                if qty_value <= 0:
                    continue

                formatted_row = {
                    "id": row[0] if len(row) > 0 else "",
                    "linea": row[1] if len(row) > 1 else "",
                    "model_code": row[2] if len(row) > 2 else "",
                    "mounter": row[3] if len(row) > 3 else "",
                    "slot": row[4] if len(row) > 4 else "",
                    "material_code": row[5] if len(row) > 5 else "",
                    "description": row[6] if len(row) > 6 else "",
                    "feeder_info": row[7] if len(row) > 7 else "",
                    "qty": qty_value,
                    "raw_filename": row[9] if len(row) > 9 else "",
                    "created_at": str(row[10]) if len(row) > 10 and row[10] else "",
                    "updated_at": str(row[11]) if len(row) > 11 and row[11] else "",
                    "tabla_tipo": row[12] if len(row) > 12 else "",
                    "status": "pending",  # Por defecto pendiente, se actualizaro con el mapeo
                }
                formatted_data.append(formatted_row)

            except Exception as row_error:
                print(f"Error procesando fila BOM: {row_error}")
                continue

        cursor.close()
        conn.close()

        print(f"BOM filtrado: {len(formatted_data)} elementos con qty > 0")

        return jsonify(
            {
                "success": True,
                "data": formatted_data,
                "total": len(formatted_data),
                "linea": linea,
                "model_code": model_code,
                "total_raw": len(todos_resultados),
                "total_filtered": len(formatted_data),
            }
        )

    except Exception as e:
        print(f"Error en api_bom_smt_data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ====== FUNCIÓN PARA CONVERTIR NOMBRES DE LÍNEA ======
def convertir_linea_smt(linea_nombre):
    """
    Convierte nombres de línea SMT a formato de BD
    SMT A = 1line
    SMT B = 2line
    SMT C = 3line
    SMT D = 4line
    """
    conversion = {
        "SMT A": "1line",
        "SMT B": "2line",
        "SMT C": "3line",
        "SMT D": "4line",
    }
    return conversion.get(linea_nombre, linea_nombre)


def convertir_linea_smt_reverso(linea_bd):
    """
    Convierte formato de BD a nombres de línea SMT
    1line = SMT A
    2line = SMT B
    3line = SMT C
    4line = SMT D
    """
    conversion = {
        "1line": "SMT A",
        "2line": "SMT B",
        "3line": "SMT C",
        "4line": "SMT D",
    }
    return conversion.get(linea_bd, linea_bd)


# Helpers ICT movidos a app/api/shared/ict_helpers.py (2026-05-27).
# Reexportados arriba si algun consumidor legacy aun los importa de routes.

# Migracion 2026-05-27: 31 helpers Vision + 2 helpers Excel + 2 renders + 6 APIs
# movidos a 4 archivos nuevos:
#   app/api/shared/vision_helpers.py    (13 helpers Vision compartidos)
#   app/api/shared/excel_helpers.py     (_send_excel_download +
#                                        _create_vision_pass_fail_excel_image +
#                                        18 helpers PNG internos)
#   app/api/control_resultados/historial_vision.py            (render + 4 APIs)
#   app/api/control_resultados/historial_vision_pass_fail.py  (render + 2 APIs)
# Aliases 301: /historial-vision{,-ajax}, /historial-vision-pass-fail{,-ajax}.
# Helpers Vision y Excel reexportados arriba para no romper consumidores legacy.


# Migracion 2026-05-27: Historial ICT (defects) movido a
# app/api/control_resultados/historial_ict.py.
# Aliases 301: /historial-ict, /historial-ict-ajax, /ict/front-full-defects2.
# Helpers _ict_format_row, _ict_find_history_record, _ict_load_local_parameters
# y _append_indexable_text_filter movidos a app/api/shared/ict_helpers.py
# y reexportados arriba via from .api.shared.ict_helpers import (...).
