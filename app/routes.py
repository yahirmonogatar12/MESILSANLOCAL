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

from datetime import date, datetime, timedelta
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


# smd_inventory ahora se registra via app/api/__init__.py

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


@app.route("/sistemas")
@login_requerido
def sistemas():
    """Redirige al hub de inicio"""
    return redirect(url_for("inicio"))


@app.route("/soporte")
@login_requerido
def soporte():
    """Página de soporte técnico"""
    return (
        render_template("soporte.html")
        if os.path.exists("app/templates/soporte.html")
        else f"<h1>Soporte Técnico</h1><p>En construcción. <a href='/inicio'>Volver al inicio</a></p>"
    )


@app.route("/documentacion")
@login_requerido
def documentacion():
    """Página de documentación"""
    return (
        render_template("documentacion.html")
        if os.path.exists("app/templates/documentacion.html")
        else f"<h1>Documentación</h1><p>En construcción. <a href='/inicio'>Volver al inicio</a></p>"
    )


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


@app.route("/control-main")
@login_requerido
def view_control_main():
    # Panel de control de operación (plantilla en Control de proceso)
    return render_template("Control de proceso/Control de operacion de linea Main.html")


# Rutas AJAX para cargar módulos en el área de Control de Proceso (prompts)
# Migracion 2026-05-26: plan_main_assy_ajax movido a app/api/control_produccion/plan_assy.py


# Migracion 2026-05-26: plan_main_imd_ajax movido a app/api/control_produccion/plan_imd.py


@app.route("/plan-main-smt-ajax")
@login_requerido
def plan_main_smt_ajax():
    try:
        return render_template("Control de proceso/Control_produccion_smt_plan.html")
    except Exception as e:
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/control-operacion-linea-main-ajax")
@login_requerido
def ctrl_operacion_linea_main_ajax():
    try:
        return render_template(
            "Control de proceso/Control de operacion de linea Main.html"
        )
    except Exception as e:
        return f"Error al cargar el contenido: {str(e)}", 500



# =============================
# CONTROL DE CUCHILLAS DE CORTE (ASSY)
# =============================
# Migrado a app/api/control_produccion/cuchillas_corte.py (2026-05-25).
# Las 17 rutas se registran via blueprint en app/api/__init__.py.
# Reexportamos los helpers y funciones de bootstrap aqui para preservar
# `_routes.crear_tablas_cuchillas_corte()` (startup_init) y
# `from app.routes import _cuchillas_rows_to_json` (app.api.shared).
from app.api.control_produccion.cuchillas_corte import (  # noqa: E402, F401
    CUCHILLAS_PERMISO_PAGINA,
    CUCHILLAS_PERMISO_SECCION,
    CUCHILLAS_PERMISO_BOTON,
    CUCHILLAS_SOURCE_DEFAULT,
    CUCHILLAS_SOURCE_ALLOWED,
    CUCHILLAS_HOURLY_SYNC_SECONDS,
    _cuchillas_row_to_json,
    _cuchillas_rows_to_json,
    _cuchillas_execute_raw,
    crear_tablas_cuchillas_corte,
    crear_trigger_cuchillas_corte_plan_main,
    iniciar_cuchillas_hourly_sync_worker,
)
# Bootstrap de cuchillas movido a app/startup_init.py


# ===============================
# SNAPSHOT DIARIO DE INVENTARIO
# ===============================
import pytz

_SNAPSHOT_INV_TZ = pytz.timezone("America/Monterrey")
_SNAPSHOT_INV_TARGET_HOUR = 7
_SNAPSHOT_INV_TARGET_MINUTE = 30
_snapshot_inv_thread = None
_snapshot_inv_lock = threading.Lock()


def crear_tablas_snapshot_inventario():
    """Crear tablas para almacenar snapshots diarios de inventario"""
    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS snapshot_inventario_general (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                fecha_snapshot DATE NOT NULL,
                modelo VARCHAR(100),
                nparte VARCHAR(100),
                stock_total INT DEFAULT 0,
                ubicaciones TEXT,
                ultima_entrada DATETIME,
                ultima_salida DATETIME,
                tipo_inventario VARCHAR(50),
                created_at DATETIME DEFAULT NOW(),
                INDEX idx_snap_ig_fecha (fecha_snapshot),
                INDEX idx_snap_ig_fecha_nparte (fecha_snapshot, nparte)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("[snapshot-inv] Tabla snapshot_inventario_general OK")
    except Exception as e:
        print(f"[snapshot-inv] Error creando snapshot_inventario_general: {e}")

    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS snapshot_ubicacion (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                fecha_snapshot DATE NOT NULL,
                modelo VARCHAR(100),
                nparte VARCHAR(100),
                fecha VARCHAR(50),
                ubicacion VARCHAR(100),
                cantidad INT DEFAULT 0,
                tipo_inventario VARCHAR(50),
                comentario TEXT,
                carro VARCHAR(100),
                created_at DATETIME DEFAULT NOW(),
                INDEX idx_snap_ub_fecha (fecha_snapshot),
                INDEX idx_snap_ub_fecha_modelo (fecha_snapshot, modelo)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("[snapshot-inv] Tabla snapshot_ubicacion OK")
    except Exception as e:
        print(f"[snapshot-inv] Error creando snapshot_ubicacion: {e}")


def _snapshot_inv_tomar(fecha_override=None):
    """Tomar snapshot de inventario general y ubicación para una fecha.
    Idempotente: si ya existe snapshot para esa fecha, no inserta."""
    fecha = fecha_override or datetime.now(_SNAPSHOT_INV_TZ).date()
    fecha_str = str(fecha)

    # Verificar si ya existe snapshot para esta fecha
    existing = execute_query(
        "SELECT COUNT(*) AS cnt FROM snapshot_inventario_general WHERE fecha_snapshot = %s",
        [fecha_str], fetch="one"
    )
    if existing and existing.get("cnt", 0) > 0:
        print(f"[snapshot-inv] Ya existe snapshot para {fecha_str}, omitiendo")
        return {"fecha": fecha_str, "inventario_general": 0, "ubicacion": 0, "skipped": True}

    # Snapshot de inventario general (inv_resumen_modelo)
    rows_ig = execute_query("""
        INSERT INTO snapshot_inventario_general
            (fecha_snapshot, modelo, nparte, stock_total, ubicaciones, ultima_entrada, ultima_salida, tipo_inventario)
        SELECT
            %s, modelo, nparte, stock_total, ubicaciones, ultima_entrada, ultima_salida, tipo_inventario
        FROM inv_resumen_modelo
    """, [fecha_str])

    # Snapshot de ubicación (ubicacionimdinv)
    rows_ub = execute_query("""
        INSERT INTO snapshot_ubicacion
            (fecha_snapshot, modelo, nparte, fecha, ubicacion, cantidad, tipo_inventario, comentario, carro)
        SELECT
            %s, modelo, nparte, fecha, ubicacion, cantidad, tipo_inventario, comentario, carro
        FROM ubicacionimdinv
    """, [fecha_str])

    result = {
        "fecha": fecha_str,
        "inventario_general": rows_ig if isinstance(rows_ig, int) else 0,
        "ubicacion": rows_ub if isinstance(rows_ub, int) else 0,
        "skipped": False
    }
    print(f"[snapshot-inv] Snapshot completado: {result}")
    return result


def _snapshot_inv_daily_loop():
    """Loop background que duerme hasta las 7:30 AM Monterrey, toma snapshot, repite."""
    while True:
        try:
            now = datetime.now(_SNAPSHOT_INV_TZ)
            target_today = now.replace(
                hour=_SNAPSHOT_INV_TARGET_HOUR,
                minute=_SNAPSHOT_INV_TARGET_MINUTE,
                second=0, microsecond=0
            )
            if now >= target_today:
                target = target_today + timedelta(days=1)
            else:
                target = target_today

            sleep_seconds = max(60, (target - now).total_seconds())
            print(f"[snapshot-inv] Durmiendo {sleep_seconds:.0f}s hasta {target.strftime('%Y-%m-%d %H:%M')}")
            time.sleep(sleep_seconds)

            result = _snapshot_inv_tomar()
            print(f"[snapshot-inv] Resultado: {result}")
        except Exception as e:
            print(f"[snapshot-inv] Error: {e}")
            time.sleep(300)


def iniciar_snapshot_inv_worker():
    """Iniciar thread daemon para snapshot diario de inventario"""
    global _snapshot_inv_thread
    if _env_flag("SNAPSHOT_INV_DISABLE", False):
        print("[snapshot-inv] Deshabilitado por SNAPSHOT_INV_DISABLE")
        return

    with _snapshot_inv_lock:
        if _snapshot_inv_thread and _snapshot_inv_thread.is_alive():
            return
        _snapshot_inv_thread = threading.Thread(
            target=_snapshot_inv_daily_loop,
            name="snapshot-inv-daily",
            daemon=True,
        )
        _snapshot_inv_thread.start()
        print("[snapshot-inv] Worker iniciado (target 07:30 America/Monterrey)")


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
# Reexportamos `crear_tabla_plan_smt_v2` para preservar `startup_init.py`.
from app.api.control_produccion.plan_smt import (  # noqa: E402, F401
    crear_tabla_plan_smt_v2,
)


# Migracion 2026-05-26: api_plan_main_list movido a app/api/control_produccion/plan_assy.py


@app.route("/api/work-orders/import", methods=["POST"])
@login_requerido
def api_work_orders_import():
    try:
        data = request.get_json() or {}
        wo_ids = data.get("wo_ids", [])
        import_date = data.get(
            "import_date", None
        )  # Fecha de importación desde el frontend

        if not wo_ids:
            return jsonify({"error": "No se seleccionaron work orders"}), 400

        # Parsear fecha de importación si se proporciona
        fecha_importacion = None
        if import_date:
            try:
                fecha_importacion = datetime.strptime(import_date, "%Y-%m-%d").date()
            except Exception as e:
                return jsonify(
                    {"error": f"Fecha de importación inválida: {str(e)}"}
                ), 400

        imported = 0
        plans = []
        errors = []

        # Recolectar WOs validas primero para poder ordenar por linea
        wo_list = []
        for wo_id in wo_ids:
            row = execute_query(
                "SELECT * FROM work_orders WHERE id = %s", (wo_id,), fetch="one"
            )
            if not row:
                errors.append(f"WO id {wo_id} no encontrado")
                continue
            wo = row
            # Verificar si ya existe (buscar por wo_id para ser más preciso)
            existing = execute_query(
                "SELECT lot_no, status FROM plan_main WHERE wo_id = %s OR wo_code = %s",
                (wo_id, wo.get("codigo_wo")),
                fetch="one",
            )
            if existing:
                lot_existente = (
                    existing.get("lot_no")
                    if isinstance(existing, dict)
                    else existing[0]
                )
                errors.append(
                    f"WO {wo.get('codigo_wo')} ya fue importada como LOT: {lot_existente}"
                )
                continue
            wo_list.append((wo_id, wo))

        # Ordenar por linea para que los lotes sean consecutivos por linea
        wo_list.sort(key=lambda x: x[1].get("linea") or "ZZZ")

        for wo_id, wo in wo_list:
            # Obtener part_no y línea del WO
            # En work_orders: 'modelo' es el part_no (ej: EBR42005002)
            # La línea viene directamente de la columna 'linea' del WO
            part_no = wo.get("modelo") or wo.get("codigo_modelo") or ""
            line = wo.get("linea") or "MAIN_LINE"  # Línea del WO directamente

            # Buscar información adicional en raw (CT, UPH, MODEL, PROJECT)
            # Usar consulta combinada como en FRONT PLAN original
            # NO buscar linea en raw, solo CT, UPH, MODEL y PROJECT
            raw_data_query = """
                SELECT part_no, model, project, c_t as ct, uph
                FROM raw
                WHERE model = %s OR model = %s OR part_no = %s OR part_no LIKE %s
                ORDER BY id DESC
                LIMIT 1
            """
            raw_params = (
                wo.get("modelo"),
                wo.get("codigo_modelo"),
                wo.get("codigo_modelo"),
                f"%{wo.get('modelo')}%",
            )

            raw_data = execute_query(raw_data_query, raw_params, fetch="one")

            # Extraer datos de raw o usar valores por defecto
            if raw_data:
                part_no = raw_data.get("part_no") or part_no
                model_code = raw_data.get("model") or wo.get("modelo") or ""
                project = raw_data.get("project") or wo.get("nombre_modelo") or ""

                # Normalizar CT y UPH
                try:
                    ct = float(raw_data.get("ct") or 0)
                except:
                    ct = 0.0
                try:
                    uph_raw = raw_data.get("uph")
                    if uph_raw and str(uph_raw).strip().isdigit():
                        uph = int(str(uph_raw).strip())
                    else:
                        uph = 0
                except:
                    uph = 0
            else:
                # Si no hay datos en raw, usar lo que venga de la WO
                part_no = wo.get("codigo_modelo") or wo.get("modelo") or ""
                model_code = wo.get("modelo") or ""
                project = wo.get("nombre_modelo") or ""
                ct = 0.0
                uph = 0

            # Generar lot y crear plan
            # Usar fecha de importación si se proporciona, sino usar fecha_operacion de la WO
            if fecha_importacion:
                fecha_dt = fecha_importacion
            else:
                fecha_op = wo.get("fecha_operacion")
                try:
                    if isinstance(fecha_op, str):
                        fecha_dt = _fp_safe_date(fecha_op) or datetime.utcnow().date()
                    else:
                        fecha_dt = (
                            fecha_op.date()
                            if hasattr(fecha_op, "date")
                            else datetime.utcnow().date()
                        )
                except Exception:
                    fecha_dt = datetime.utcnow().date()

            lot_no = _fp_generate_lot_no(
                datetime.combine(fecha_dt, datetime.min.time())
            )

            # Insertar plan con wo_id para rastrear la importación
            insert_sql = (
                "INSERT INTO plan_main (lot_no, wo_id, wo_code, po_code, working_date, line, model_code, part_no, project, process, plan_count, ct, uph, routing, status, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PLAN',NOW())"
            )
            params = (
                lot_no,
                wo_id,  # Agregar wo_id para rastreo
                wo.get("codigo_wo"),
                wo.get("codigo_po"),
                fecha_dt,
                line,
                model_code,
                part_no,
                project,
                "MAIN",
                int(wo.get("cantidad_planeada") or 0),
                ct,
                uph,
                1,  # routing por defecto: DIA
            )
            execute_query(insert_sql, params)
            imported += 1
            plans.append({"lot_no": lot_no, "wo_code": wo.get("codigo_wo")})
        return jsonify(
            {"success": True, "imported": imported, "plans": plans, "errors": errors}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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


@app.route("/buscar_material_por_numero_parte", methods=["GET"])
@login_requerido
def buscar_material_por_numero_parte():
    """
    Busca materiales en inventario por número de parte usando MySQL
    """
    try:
        numero_parte = request.args.get("numero_parte", "").strip()

        if not numero_parte:
            return jsonify({"success": False, "error": "Número de parte requerido"})

        # Usar funciones de MySQL en lugar de SQLite
        from .db_mysql import (
            buscar_material_por_numero_parte_mysql,
            calcular_inventario_general_mysql,
        )

        # Buscar materiales por número de parte usando MySQL
        materiales = buscar_material_por_numero_parte_mysql(numero_parte)

        # Calcular inventario general para este número de parte
        inventario_info = calcular_inventario_general_mysql(numero_parte)

        # Preparar respuesta con información completa
        response_data = []
        for material in materiales:
            material_data = {
                "codigo_material_recibido": material["codigo_material_recibido"],
                "codigo_material_original": material["codigo_material_original"] or "",
                "codigo_material": material["codigo_material"] or "",
                "especificacion": material["especificacion"] or "",
                "numero_parte": material["numero_parte"],
                "cantidad_actual": material["cantidad_actual"] or 0,
                "numero_lote_material": material["numero_lote_material"] or "",
                "fecha_recibo": material["fecha_recibo"] or "",
                "database_type": "MySQL",  # Indicador de que se está usando MySQL
            }
            response_data.append(material_data)

        # Agregar información del inventario general si está disponible
        result = {
            "success": True,
            "materiales": response_data,
            "total_materiales": len(response_data),
            "numero_parte_buscado": numero_parte,
            "database_type": "MySQL",
        }

        if inventario_info:
            result["inventario_general"] = inventario_info

        if materiales:
            return jsonify(result)
        else:
            return jsonify(
                {
                    "success": False,
                    "error": f"No se encontraron materiales con número de parte: {numero_parte}",
                }
            )

    except Exception as e:
        print(f" ERROR en buscar_material_por_numero_parte (MySQL): {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Limpieza 2026-05-26: rutas /guardar_entrada_aereo y /listar_entradas_aereo eliminadas.
# Sin consumidores en app/static/js/ ni en app/templates/. Tabla entrada_aereo (SQLite legacy)
# tampoco se lee desde ningun otro lado. Documentadas como huerfanas en
# Documentacion/VERIFICACION_DETALLADA_HUERFANAS.md lineas 39-40.


# Función de conexión movida a db.py - usar get_db_connection() importada


# Rutas para manejo de materiales
@app.route("/guardar_material", methods=["POST"])
def guardar_material_route():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    try:
        # Obtener usuario de la sesión
        usuario_actual = session.get("usuario", "USUARIO_MANUAL")

        # Preparar datos del material
        material_data = {
            "codigo_material": data.get("codigoMaterial"),
            "numero_parte": data.get("numeroParte"),
            "propiedad_material": data.get("propiedadMaterial"),
            "classification": data.get("classification"),
            "especificacion_material": data.get("especificacionMaterial"),
            "unidad_empaque": data.get("unidadEmpaque"),
            "ubicacion_material": data.get("ubicacionMaterial"),
            "vendedor": data.get("vendedor"),
            "prohibido_sacar": int(data.get("prohibidoSacar", 0)),
            "reparable": int(data.get("reparable", 0)),
            "nivel_msl": data.get("nivelMSL"),
            "espesor_msl": data.get("espesorMSL"),
        }

        # Usar función de db_mysql.py con información del usuario
        print(f" Material registrado manualmente por: {usuario_actual}")
        success = guardar_material(material_data, usuario_registro=usuario_actual)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify(
                {"success": False, "error": "Error al guardar material"}
            ), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/listar_materiales")
def listar_materiales():
    try:
        # Usar función de db_mysql.py que ya devuelve el formato correcto
        materiales = obtener_materiales() or []

        # La función obtener_materiales() ya devuelve el formato correcto
        # No necesitamos procesamiento adicional
        return jsonify(materiales)

    except Exception as e:
        print(f"Error obteniendo materiales: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/inventario/lotes_detalle", methods=["POST"])
@login_requerido
def consultar_lotes_detalle():
    """Endpoint para obtener detalles específicos de lotes por número de parte"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        numero_parte = data.get("numero_parte", "").strip()

        if not numero_parte:
            return jsonify(
                {"success": False, "error": "Número de parte requerido"}
            ), 400

        from .db import is_mysql_connection

        using_mysql = is_mysql_connection()

        conn = get_db_connection()
        if conn is None:
            return jsonify(
                {"success": False, "error": "No se pudo conectar a la base de datos"}
            ), 500

        cursor = conn.cursor()

        # Query para obtener todos los lotes de un número de parte específico (solo con inventario disponible)
        if using_mysql:
            query = """
                SELECT
                    codigo_material_recibido,
                    numero_lote_material,
                    total_entrada as cantidad_total_entrada,
                    total_salidas,
                    (total_entrada - total_salidas) as cantidad_disponible,
                    fecha_recibo,
                    fecha_fabricacion,
                    especificacion,
                    propiedad_material,
                    ubicacion_salida,
                    codigo_material,
                    codigo_material_original
                FROM (
                    SELECT
                        cma.codigo_material_recibido,
                        cma.numero_lote_material,
                        SUM(cma.cantidad_actual) as total_entrada,
                        COALESCE((
                            SELECT SUM(cms.cantidad_salida)
                            FROM control_material_salida cms
                            WHERE cms.codigo_material_recibido = cma.codigo_material_recibido
                        ), 0) as total_salidas,
                        MIN(cma.fecha_recibo) as fecha_recibo,
                        MIN(cma.fecha_fabricacion) as fecha_fabricacion,
                        MIN(cma.especificacion) as especificacion,
                        MIN(cma.propiedad_material) as propiedad_material,
                        MIN(cma.ubicacion_salida) as ubicacion_salida,
                        MIN(cma.codigo_material) as codigo_material,
                        MIN(cma.codigo_material_original) as codigo_material_original
                    FROM control_material_almacen cma
                    WHERE cma.numero_parte = %s
                    GROUP BY cma.codigo_material_recibido, cma.numero_lote_material
                ) lotes_calc
                WHERE (total_entrada - total_salidas) > 0
                ORDER BY fecha_recibo DESC
            """
            cursor.execute(query, [numero_parte])
        else:
            # Fallback para SQLite (aunque no lo usamos)
            return jsonify({"success": False, "error": "Solo MySQL soportado"}), 500
        rows = cursor.fetchall()

        lotes_detalle = []
        for i, row in enumerate(rows):
            try:
                lote_data = {
                    "codigo_material_recibido": row["codigo_material_recibido"],
                    "numero_lote": row["numero_lote_material"],
                    "cantidad_original": float(row["cantidad_total_entrada"])
                    if row["cantidad_total_entrada"]
                    else 0.0,
                    "total_salidas": float(row["total_salidas"])
                    if row["total_salidas"]
                    else 0.0,
                    "cantidad_disponible": float(row["cantidad_disponible"])
                    if row["cantidad_disponible"]
                    else 0.0,
                    "fecha_recibo": row["fecha_recibo"].strftime("%Y-%m-%d")
                    if row["fecha_recibo"]
                    else "",
                    "fecha_fabricacion": row["fecha_fabricacion"].strftime("%Y-%m-%d")
                    if row["fecha_fabricacion"]
                    else "",
                    "especificacion": row["especificacion"] or "",
                    "propiedad_material": row["propiedad_material"] or "COMMON USE",
                    "ubicacion": row["ubicacion_salida"] or "",
                    "codigo_material": row["codigo_material"] or "",
                    "codigo_material_original": row["codigo_material_original"] or "",
                }
                lotes_detalle.append(lote_data)
            except Exception as e:
                print(f" Error procesando fila {i + 1}: {e}")
                print(f" Datos de la fila: {row}")
                continue

        print(
            f" Detalles de lotes consultados: {len(lotes_detalle)} lotes encontrados para {numero_parte}"
        )

        return jsonify(
            {
                "success": True,
                "numero_parte": numero_parte,
                "lotes": lotes_detalle,
                "total_lotes": len(lotes_detalle),
            }
        )

    except Exception as e:
        print(f" Error al consultar detalles de lotes: {e}")
        return jsonify(
            {
                "success": False,
                "error": f"Error al consultar detalles de lotes: {str(e)}",
            }
        ), 500

    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass
        try:
            if conn is not None:
                conn.close()
        except:
            pass


@app.route("/importar_excel", methods=["POST"])
def importar_excel():
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
            df = pd.read_excel(
                temp_path, engine="openpyxl" if filename.endswith(".xlsx") else "xlrd"
            )
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
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

        # Obtener las columnas del Excel
        columnas_excel = df.columns.tolist()
        print(f"Columnas detectadas en Excel: {columnas_excel}")

        # Mapeo de columnas (flexible para diferentes nombres)
        mapeo_columnas = {
            "codigo_material": [
                "Codigo de material",
                "Código de material",
                "codigo_material",
                "Código+de+material",
            ],
            "numero_parte": [
                "Numero de parte",
                "Número de parte",
                "numero_parte",
                "Número+de+parte",
            ],
            "propiedad_material": [
                "Propiedad de material",
                "propiedad_material",
                "Propiedad+de+material",
            ],
            "classification": [
                "Classification",
                "classification",
                "Clasificación",
                "Clasificacion",
            ],
            "especificacion_material": [
                "Especificacion de material",
                "Especificación de material",
                "especificacion_material",
                "Especificación+de+material",
            ],
            "unidad_empaque": [
                "Unidad de empaque",
                "unidad_empaque",
                "Unidad+de+empaque",
            ],
            "ubicacion_material": [
                "Ubicacion de material",
                "Ubicación de material",
                "ubicacion_material",
                "Ubicación+de+material",
            ],
            "vendedor": ["Vendedor", "vendedor", "Proveedor", "proveedor"],
            "prohibido_sacar": [
                "Prohibido sacar",
                "prohibido_sacar",
                "Prohibido+sacar",
            ],
            "reparable": ["Reparable", "reparable"],
            "nivel_msl": ["Nivel de MSL", "nivel_msl", "Nivel+de+MSL"],
            "espesor_msl": ["Espesor de MSL", "espesor_msl", "Espesor+de+MSL"],
        }

        def obtener_valor_columna(row, campo):
            """Obtiene el valor de una columna usando el mapeo flexible"""
            posibles_nombres = mapeo_columnas.get(campo, [campo])

            for nombre in posibles_nombres:
                if nombre in row:
                    valor = row[nombre]
                    if pd.isna(valor) or valor is None:
                        return ""
                    return str(valor).strip()

            # Si no encuentra la columna, usar posición por índice como fallback
            try:
                campos_orden = [
                    "codigo_material",
                    "numero_parte",
                    "propiedad_material",
                    "classification",
                    "especificacion_material",
                    "unidad_empaque",
                    "ubicacion_material",
                    "vendedor",
                    "prohibido_sacar",
                    "reparable",
                    "nivel_msl",
                    "espesor_msl",
                ]
                if campo in campos_orden:
                    idx = campos_orden.index(campo)
                    if idx < len(columnas_excel):
                        valor = row.get(columnas_excel[idx], "")
                        if pd.isna(valor) or valor is None:
                            return ""
                        return str(valor).strip()
            except:
                pass

            return ""

        def convertir_checkbox(valor):
            """Convierte valores de checkbox del Excel a 0 o 1"""
            if not valor or pd.isna(valor):
                return "0"

            valor_str = str(valor).strip().lower()

            # Valores que se consideran como "true" o "checked"
            valores_true = [
                "1",
                "true",
                "yes",
                "sí",
                "si",
                "checked",
                "x",
                "on",
                "habilitado",
                "activo",
            ]
            # Valores que se consideran como "false" o "unchecked"
            valores_false = [
                "0",
                "false",
                "no",
                "unchecked",
                "off",
                "deshabilitado",
                "inactivo",
                "",
            ]

            if valor_str in valores_true:
                return "1"
            elif valor_str in valores_false:
                return "0"
            else:
                # Si no reconoce el valor, asumir false por seguridad
                return "0"

        def limpiar_numero(valor):
            """Limpia números eliminando decimales innecesarios (.0)"""
            if not valor or pd.isna(valor):
                return ""

            try:
                numero = float(valor)
                if numero % 1 == 0:  # Es un número entero
                    return str(int(numero))  # Devolver como entero sin decimales
                else:
                    return str(numero)  # Mantener decimales si son necesarios
            except (ValueError, TypeError):
                # Si no es un número válido, devolver como string
                return str(valor).strip()

        # Insertar los datos usando funciones de MySQL
        registros_insertados = 0
        errores = []

        for index, row in df.iterrows():
            try:
                # Convert index to int safely
                row_number = (
                    int(index) + 1
                    if isinstance(index, (int, float))
                    else len(errores) + registros_insertados + 1
                )

                # Obtener valores usando el mapeo flexible
                codigo_material = obtener_valor_columna(row, "codigo_material")
                numero_parte = obtener_valor_columna(row, "numero_parte")
                propiedad_material = obtener_valor_columna(row, "propiedad_material")
                classification = obtener_valor_columna(row, "classification")
                especificacion_material = obtener_valor_columna(
                    row, "especificacion_material"
                )
                unidad_empaque = limpiar_numero(
                    obtener_valor_columna(row, "unidad_empaque")
                )
                ubicacion_material = obtener_valor_columna(row, "ubicacion_material")
                vendedor = obtener_valor_columna(row, "vendedor")

                # Convertir valores de checkbox correctamente
                prohibido_sacar = int(
                    convertir_checkbox(obtener_valor_columna(row, "prohibido_sacar"))
                )
                reparable = int(
                    convertir_checkbox(obtener_valor_columna(row, "reparable"))
                )

                nivel_msl = limpiar_numero(obtener_valor_columna(row, "nivel_msl"))
                espesor_msl = obtener_valor_columna(row, "espesor_msl")

                # Validar que al menos el código de material no esté vacío
                if not codigo_material:
                    errores.append(f"Fila {row_number}: Código de material vacío")
                    continue

                # Preparar datos del material
                material_data = {
                    "codigo_material": codigo_material,
                    "numero_parte": numero_parte,
                    "propiedad_material": propiedad_material,
                    "classification": classification,
                    "especificacion_material": especificacion_material,
                    "unidad_empaque": unidad_empaque,
                    "ubicacion_material": ubicacion_material,
                    "vendedor": vendedor,
                    "prohibido_sacar": prohibido_sacar,
                    "reparable": reparable,
                    "nivel_msl": nivel_msl,
                    "espesor_msl": espesor_msl,
                }

                # Obtener usuario de la sesión para registro
                usuario_actual = session.get("usuario", "USUARIO_MANUAL")

                success = guardar_material(
                    material_data, usuario_registro=usuario_actual
                )

                if success:
                    registros_insertados += 1
                else:
                    error_msg = f"Fila {row_number}: Error al guardar en base de datos"
                    errores.append(error_msg)

            except Exception as e:
                row_number = (
                    int(index) + 1
                    if isinstance(index, (int, float))
                    else len(errores) + registros_insertados + 1
                )
                error_msg = f"Error en fila {row_number}: {str(e)}"
                errores.append(error_msg)
                continue

        # Preparar respuesta
        mensaje = f"Se importaron {registros_insertados} registros exitosamente"
        if errores:
            mensaje += f". Se encontraron {len(errores)} errores"
            if len(errores) <= 5:
                mensaje += f": {'; '.join(errores)}"

        return jsonify({"success": True, "message": mensaje})

    except Exception as e:
        print(f"Error general en importar_excel: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify(
            {"success": False, "error": f"Error al procesar el archivo: {str(e)}"}
        ), 500

    finally:
        # Limpiar archivo temporal
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass


@app.route("/actualizar_campo_material", methods=["POST"])
def actualizar_campo_material():
    """Actualizar un campo específico de un material"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {"success": False, "error": "No se proporcionaron datos"}
            ), 400

        codigo_material = data.get("codigoMaterial")
        campo = data.get("campo")
        valor = data.get("valor")

        if not codigo_material or not campo:
            return jsonify({"success": False, "error": "Faltan datos requeridos"}), 400

        # Validar que el campo es permitido para actualizar
        campos_permitidos = ["prohibidoSacar", "reparable"]
        if campo not in campos_permitidos:
            return jsonify(
                {"success": False, "error": "Campo no permitido para actualización"}
            ), 400

        # Mapear nombres de campo a nombres de columna en la base de datos
        mapeo_campos = {"prohibidoSacar": "prohibido_sacar", "reparable": "reparable"}

        columna_db = mapeo_campos.get(campo)
        if not columna_db:
            return jsonify({"success": False, "error": "Campo no válido"}), 400

        # Verificar que el material existe
        query_verificar = (
            "SELECT codigo_material FROM materiales WHERE codigo_material = %s"
        )
        material_existe = execute_query(
            query_verificar, (codigo_material,), fetch="one"
        )

        if not material_existe:
            return jsonify({"success": False, "error": "Material no encontrado"}), 404

        # Actualizar el campo
        query_actualizar = (
            f"UPDATE materiales SET {columna_db} = %s WHERE codigo_material = %s"
        )
        rows_affected = execute_query(query_actualizar, (int(valor), codigo_material))

        if rows_affected == 0:
            return jsonify(
                {"success": False, "error": "No se pudo actualizar el material"}
            ), 500

        return jsonify({"success": True, "message": "Campo actualizado correctamente"})

    except Exception as e:
        print(f"Error al actualizar campo: {str(e)}")
        return jsonify(
            {"success": False, "error": f"Error interno del servidor: {str(e)}"}
        ), 500


@app.route("/actualizar_material_completo", methods=["POST"])
@login_requerido
def actualizar_material_completo_route():
    """Actualizar todos los campos de un material existente"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No se recibieron datos"}), 400

        codigo_original = data.get("codigo_material_original")
        nuevos_datos = data.get("nuevos_datos")

        if not codigo_original:
            return jsonify(
                {"success": False, "error": "Código de material original requerido"}
            ), 400

        if not nuevos_datos:
            return jsonify({"success": False, "error": "Nuevos datos requeridos"}), 400

        # Limpiar el código original (eliminar espacios y caracteres extraños)
        codigo_limpio = str(codigo_original).strip()

        # Llamar a la función de db_mysql
        resultado = actualizar_material_completo(codigo_limpio, nuevos_datos)

        if resultado["success"]:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400

    except Exception as e:
        error_msg = str(e)
        print(f" Error en actualizar_material_completo_route: {error_msg}")
        return jsonify(
            {"success": False, "error": f"Error interno del servidor: {error_msg}"}
        ), 500


@app.route("/exportar_excel", methods=["GET"])
@login_requerido
def exportar_excel():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener todos los materiales
        cursor.execute("""
            SELECT codigo_material, numero_parte, propiedad_material, classification,
                   especificacion_material, unidad_empaque, ubicacion_material, vendedor,
                   prohibido_sacar, reparable, nivel_msl, espesor_msl, fecha_registro
            FROM materiales
            ORDER BY fecha_registro DESC
        """)
        materiales = cursor.fetchall()

        conn.close()

        if not materiales:
            # Crear un DataFrame vacío con headers
            df = pd.DataFrame(
                columns=[
                    "Código de material",
                    "Número de parte",
                    "Propiedad de material",
                    "Classification",
                    "Especificación de material",
                    "Unidad de empaque",
                    "Ubicación de material",
                    "Vendedor",
                    "Prohibido sacar",
                    "Reparable",
                    "Nivel de MSL",
                    "Espesor de MSL",
                    "Fecha de registro",
                ]
            )
        else:
            # Convertir a DataFrame
            data = []
            for material in materiales:
                data.append(
                    {
                        "Código de material": material["codigo_material"],
                        "Número de parte": material["numero_parte"],
                        "Propiedad de material": material["propiedad_material"],
                        "Classification": material["classification"],
                        "Especificación de material": material[
                            "especificacion_material"
                        ],
                        "Unidad de empaque": material["unidad_empaque"],
                        "Ubicación de material": material["ubicacion_material"],
                        "Vendedor": material["vendedor"],
                        "Prohibido sacar": "Sí"
                        if material["prohibido_sacar"] == 1
                        else "No",
                        "Reparable": "Sí" if material["reparable"] == 1 else "No",
                        "Nivel de MSL": material["nivel_msl"],
                        "Espesor de MSL": material["espesor_msl"],
                        "Fecha de registro": material["fecha_registro"],
                    }
                )
            df = pd.DataFrame(data)
            print(f"DataFrame creado con {len(df)} filas")

        # Crear archivo Excel en memoria
        from io import BytesIO

        output = BytesIO()

        print("Creando archivo Excel...")
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Materiales")

        output.seek(0)
        print("Archivo Excel creado exitosamente")

        # Crear nombre del archivo
        fecha_actual = obtener_fecha_hora_mexico().strftime("%Y-%m-%d_%H-%M-%S")
        nombre_archivo = f"materiales_export_{fecha_actual}.xlsx"

        print(f"Enviando archivo: {nombre_archivo}")
        # Devolver el archivo directamente
        return send_file(
            output,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        print(f"Error en exportar_excel: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/obtener_codigos_material")
def obtener_codigos_material():
    """Endpoint para obtener códigos de material para el dropdown del control de almacén con búsqueda inteligente"""
    conn = None
    cursor = None
    try:
        print(" Iniciando obtener_codigos_material...")

        # Obtener parámetro de búsqueda si existe
        busqueda = request.args.get("busqueda", "").strip()

        conn = get_db_connection()
        if not conn:
            print(" Error: No se pudo obtener conexión a la base de datos")
            return jsonify([])

        cursor = conn.cursor()

        # Si hay parámetro de búsqueda, implementar búsqueda inteligente
        if busqueda:
            print(f" Búsqueda inteligente para: '{busqueda}'")

            # Query con búsqueda parcial usando LIKE con wildcards
            # Busca en código_material y numero_parte
            cursor.execute(
                """
                SELECT codigo_material, numero_parte, especificacion_material,
                       propiedad_material, unidad_empaque,
                       CASE
                           WHEN codigo_material LIKE %s THEN 1
                           WHEN numero_parte LIKE %s THEN 2
                           WHEN codigo_material LIKE %s THEN 3
                           WHEN numero_parte LIKE %s THEN 4
                           ELSE 5
                       END as relevancia
                FROM materiales
                WHERE codigo_material IS NOT NULL AND codigo_material != ''
                AND (
                    codigo_material LIKE %s OR
                    numero_parte LIKE %s OR
                    especificacion_material LIKE %s OR
                    propiedad_material LIKE %s
                )
                ORDER BY relevancia ASC, codigo_material ASC
                LIMIT 50
            """,
                (
                    f"{busqueda}%",  # Empieza con
                    f"{busqueda}%",  # Empieza con (numero_parte)
                    f"%{busqueda}%",  # Contiene
                    f"%{busqueda}%",  # Contiene (numero_parte)
                    f"%{busqueda}%",  # Para WHERE - contiene en codigo_material
                    f"%{busqueda}%",  # Para WHERE - contiene en numero_parte
                    f"%{busqueda}%",  # Para WHERE - contiene en especificacion
                    f"%{busqueda}%",  # Para WHERE - contiene en propiedad
                ),
            )
        else:
            # Sin búsqueda, devolver todos los materiales
            cursor.execute("""
                SELECT codigo_material, numero_parte, especificacion_material,
                       propiedad_material, unidad_empaque
                FROM materiales
                WHERE codigo_material IS NOT NULL AND codigo_material != ''
                ORDER BY codigo_material ASC
                LIMIT 1000
            """)

        rows = cursor.fetchall()

        print(
            f" Se encontraron {len(rows)} materiales"
            + (f" para búsqueda '{busqueda}'" if busqueda else "")
        )

        codigos = []
        for row in rows:
            # Usar nombres de columnas en lugar de índices (MySQL con PyMySQL devuelve diccionarios)
            material = {
                "codigo": row["codigo_material"] if row["codigo_material"] else "",
                "nombre": row["numero_parte"]
                if row["numero_parte"]
                else row["codigo_material"]
                if row["codigo_material"]
                else "",
                "spec": row["especificacion_material"]
                if row["especificacion_material"]
                else "",
                "numero_parte": row["numero_parte"] if row["numero_parte"] else "",
                "cantidad_estandarizada": str(row["unidad_empaque"])
                if row["unidad_empaque"]
                else "",
                "propiedad_material": row["propiedad_material"]
                if row["propiedad_material"]
                else "",
                "especificacion_material": row["especificacion_material"]
                if row["especificacion_material"]
                else "",
                # Agregar campo de coincidencia para debugging
                "coincidencia": busqueda in (row["codigo_material"] or "")
                or busqueda in (row["numero_parte"] or "")
                if busqueda
                else False,
            }
            codigos.append(material)

        print(f" Devolviendo {len(codigos)} materiales formateados")
        return jsonify(codigos)

    except Exception as e:
        print(f" Error en obtener_codigos_material MySQL: {str(e)}")
        import traceback

        traceback.print_exc()

        # En caso de error, devolver datos de prueba para que el sistema funcione
        print(" Devolviendo datos de prueba como fallback...")
        datos_prueba = [
            {
                "codigo": "M2606809020",
                "nombre": "M2606809020",
                "spec": "68F 1608",
                "cantidad_estandarizada": "1000",
                "propiedad_material": "68F 1608",
                "numero_parte": "M2606809020",
                "especificacion_material": "68F 1608",
                "coincidencia": False,
            },
            {
                "codigo": "M2609109005",
                "nombre": "M2609109005",
                "spec": "91F 1608",
                "cantidad_estandarizada": "2000",
                "propiedad_material": "91F 1608",
                "numero_parte": "M2609109005",
                "especificacion_material": "91F 1608",
                "coincidencia": False,
            },
        ]
        return jsonify(datos_prueba)

    finally:
        try:
            if cursor is not None:
                cursor.close()
        except:
            pass
        try:
            if conn is not None:
                conn.close()
        except:
            pass


@app.route("/guardar_control_almacen", methods=["POST"])
@login_requerido
def guardar_control_almacen():
    """Endpoint para guardar los datos del formulario de control de material de almacén"""
    try:
        data = request.get_json()

        # Validar campos requeridos
        if not data.get("codigo_material_original"):
            return jsonify(
                {"success": False, "error": "Código de material original es requerido"}
            ), 400

        # Usar la función correcta de db.py
        resultado = agregar_control_material_almacen(data)

        if resultado:
            print(
                f" Registro de almacén guardado exitosamente para {data.get('numero_parte', 'N/A')}"
            )

            return jsonify(
                {"success": True, "message": "Registro guardado exitosamente"}
            )
        else:
            return jsonify(
                {"success": False, "error": "Error al guardar en la base de datos"}
            ), 500

    except Exception as e:
        print(f"Error al guardar control de almacén: {str(e)}")


@app.route("/obtener_secuencial_lote_interno", methods=["POST"])
@login_requerido
def obtener_secuencial_lote_interno():
    """Obtener el siguiente secuencial para lote interno del día"""
    try:
        data = request.get_json()
        fecha = data.get("fecha", "")  # Formato: DD.MM.YYYY

        if not fecha:
            return jsonify({"siguiente_secuencial": 1}), 200

        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Obtener el máximo secuencial para esta fecha en control_material_almacen
            # Buscar lotes internos que coincidan con el patrón DD.MM.YYYY.XXXX
            query = """
                SELECT numero_lote_material,
                       CAST(SUBSTRING_INDEX(numero_lote_material, '.', -1) AS UNSIGNED) as seq
                FROM control_material_almacen
                WHERE numero_lote_material LIKE %s
                ORDER BY seq DESC
                LIMIT 1
            """
            cursor.execute(query, (f"{fecha}.%",))

            result = cursor.fetchone()

            print(f"DEBUG: Consultando secuencial para fecha: {fecha}")
            print(f"DEBUG: Resultado de query: {result}")

            # Si get_db_connection devuelve DictCursor, result será dict
            # Si no, será tupla
            if result:
                if isinstance(result, dict):
                    max_seq = result.get("seq", 0) or 0
                else:
                    # Tupla: (numero_lote_material, seq)
                    max_seq = result[1] if len(result) > 1 and result[1] else 0
            else:
                max_seq = 0

            siguiente_secuencial = max_seq + 1

            print(
                f"DEBUG: max_seq encontrado: {max_seq}, siguiente: {siguiente_secuencial}"
            )

            conn.close()
            return jsonify({"siguiente_secuencial": siguiente_secuencial}), 200

        except Exception as e:
            print(f"Error consultando secuencial: {e}")
            conn.close()
            return jsonify({"siguiente_secuencial": 1}), 200

    except Exception as e:
        print(f"Error en obtener_secuencial_lote_interno: {str(e)}")
        return jsonify({"error": str(e), "siguiente_secuencial": 1}), 500


@app.route("/consultar_control_almacen", methods=["GET"])
@login_requerido
def consultar_control_almacen():
    """Endpoint para consultar los registros de control de material de almacén"""
    conn = None
    cursor = None
    try:
        fecha_inicio = request.args.get("fecha_inicio")
        fecha_fin = request.args.get("fecha_fin")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Construir query con filtros de fecha si se proporcionan
        query = """
            SELECT * FROM control_material_almacen
            WHERE 1=1
        """
        params = []

        if fecha_inicio:
            query += " AND date(fecha_recibo) >= %s"
            params.append(fecha_inicio)

        if fecha_fin:
            query += " AND date(fecha_recibo) <= %s"
            params.append(fecha_fin)

        query += " ORDER BY fecha_registro DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        registros = []
        for row in rows:
            registros.append(
                {
                    "id": row["id"],
                    "forma_material": row["forma_material"],
                    "cliente": row["cliente"],
                    "codigo_material_original": row["codigo_material_original"],
                    "codigo_material": row["codigo_material"],
                    "material_importacion_local": row["material_importacion_local"],
                    "fecha_recibo": row["fecha_recibo"],
                    "fecha_fabricacion": row["fecha_fabricacion"],
                    "cantidad_actual": row["cantidad_actual"],
                    "numero_lote_material": row["numero_lote_material"],
                    "codigo_material_recibido": row["codigo_material_recibido"],
                    "numero_parte": row["numero_parte"],
                    "cantidad_estandarizada": row["cantidad_estandarizada"],
                    "codigo_material_final": row["codigo_material_final"],
                    "propiedad_material": row["propiedad_material"],
                    "especificacion": row["especificacion"],
                    "material_importacion_local_final": row[
                        "material_importacion_local_final"
                    ],
                    "estado_desecho": row["estado_desecho"],
                    "ubicacion_salida": row["ubicacion_salida"],
                    "fecha_registro": row["fecha_registro"],
                }
            )

        return jsonify(registros)

    except Exception as e:
        print(f"Error al consultar control de almacén: {str(e)}")
        return jsonify({"error": f"Error al consultar: {str(e)}"}), 500

    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass


@app.route("/actualizar_control_almacen", methods=["POST"])
@login_requerido
def actualizar_control_almacen():
    """Endpoint para actualizar un registro de control de material de almacén"""
    conn = None
    cursor = None
    try:
        data = request.get_json()

        if not data or "id" not in data:
            return jsonify({"success": False, "error": "ID no proporcionado"}), 400

        # Obtener el ID del registro a actualizar
        registro_id = data["id"]

        conn = get_db_connection()
        cursor = conn.cursor()

        # PASO 1: Obtener los valores actuales de la base de datos
        cursor.execute(
            "SELECT * FROM control_material_almacen WHERE id = %s", (registro_id,)
        )
        row = cursor.fetchone()

        if not row:
            return jsonify({"success": False, "error": "Registro no encontrado"}), 404

        # Convertir a dict usando nombres de columna
        columns = [desc[0] for desc in cursor.description]
        valores_actuales = dict(zip(columns, row))

        # PASO 2: Comparar y construir query solo para campos que cambiaron
        campos_actualizables = [
            "forma_material",
            "cliente",
            "codigo_material_original",
            "codigo_material",
            "material_importacion_local",
            "fecha_recibo",
            "fecha_fabricacion",
            "cantidad_actual",
            "numero_lote_material",
            "codigo_material_recibido",
            "numero_parte",
            "cantidad_estandarizada",
            "codigo_material_final",
            "propiedad_material",
            "especificacion",
            "material_importacion_local_final",
            "estado_desecho",
            "ubicacion_salida",
        ]

        sets = []
        params = []
        campos_modificados = []

        for campo in campos_actualizables:
            # Solo procesar campos que fueron enviados explícitamente
            if campo in data:
                valor_nuevo = data[campo]
                valor_actual = valores_actuales.get(campo)

                # Normalizar valores para comparación
                # Manejar campos de fecha vacíos
                if campo in ["fecha_recibo", "fecha_fabricacion"]:
                    if valor_nuevo == "":
                        valor_nuevo = None
                    # Convertir datetime a string para comparación
                    if valor_actual is not None:
                        valor_actual = str(valor_actual)

                # Manejar conversión de estado_desecho (texto a entero)
                if campo == "estado_desecho":
                    if (
                        valor_nuevo == "Activo"
                        or valor_nuevo == "1"
                        or valor_nuevo == 1
                    ):
                        valor_nuevo = 1
                    elif (
                        valor_nuevo == "Inactivo"
                        or valor_nuevo == "Desecho"
                        or valor_nuevo == "0"
                        or valor_nuevo == 0
                    ):
                        valor_nuevo = 0
                    else:
                        valor_nuevo = 1 if valor_nuevo else 0

                # Convertir ambos valores a string para comparación consistente
                valor_nuevo_str = str(valor_nuevo) if valor_nuevo is not None else ""
                valor_actual_str = str(valor_actual) if valor_actual is not None else ""

                # Solo actualizar si los valores son diferentes
                if valor_nuevo_str != valor_actual_str:
                    sets.append(f"{campo} = %s")
                    params.append(valor_nuevo)
                    campos_modificados.append(campo)
                    print(
                        f"✓ Campo MODIFICADO: {campo} = '{valor_actual}' -> '{valor_nuevo}'"
                    )
                else:
                    print(f"⚪ Campo SIN CAMBIOS: {campo} = '{valor_actual}'")
            else:
                print(
                    f"➖ Campo NO ENVIADO (se mantiene): {campo} = '{valores_actuales.get(campo)}'"
                )

        if not sets:
            return jsonify(
                {
                    "success": True,
                    "message": "No hay cambios que guardar",
                    "campos_modificados": [],
                }
            )

        # Agregar ID al final de los parámetros
        params.append(registro_id)

        # Query de actualización solo para campos modificados
        query = f"""
            UPDATE control_material_almacen
            SET {", ".join(sets)}
            WHERE id = %s
        """

        print(f" Query SQL: {query}")
        print(f" Parámetros: {params}")
        print(f"📝 Campos modificados: {campos_modificados}")

        # Ejecutar la actualización
        cursor.execute(query, params)
        conn.commit()

        print(f" Filas afectadas: {cursor.rowcount}")

        if cursor.rowcount > 0:
            print(f"Registro de control de almacén actualizado: ID {registro_id}")

            # Verificar si necesitamos actualizar el inventario consolidado
            if any(
                campo in campos_modificados
                for campo in ["cantidad_actual", "codigo_material"]
            ):
                try:
                    from app.db import actualizar_inventario_consolidado_entrada

                    actualizar_inventario_consolidado_entrada()
                    print("Inventario consolidado actualizado automáticamente")
                except Exception as e:
                    print(f"Error al actualizar inventario consolidado: {str(e)}")

            return jsonify(
                {
                    "success": True,
                    "message": f"Registro actualizado exitosamente. Campos modificados: {', '.join(campos_modificados)}",
                    "campos_modificados": campos_modificados,
                }
            )
        else:
            print(f" No se pudo actualizar el registro con ID: {registro_id}")
            return jsonify(
                {"success": False, "error": "No se pudo actualizar el registro"}
            ), 500

    except Exception as e:
        print(f"Error al actualizar control de almacén: {str(e)}")
        return jsonify(
            {"success": False, "error": f"Error al actualizar: {str(e)}"}
        ), 500

    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass


@app.route("/guardar_cliente_seleccionado", methods=["POST"])
@login_requerido
def guardar_cliente_seleccionado():
    """Guardar la selección de cliente del usuario"""
    try:
        data = request.get_json()
        if not data or "cliente" not in data:
            return jsonify({"success": False, "error": "Cliente no proporcionado"}), 400

        cliente = data["cliente"]
        usuario = session.get("usuario", "default")

        # Guardar la configuración
        if guardar_configuracion_usuario(usuario, "cliente_seleccionado", cliente):
            return jsonify(
                {"success": True, "message": "Cliente guardado exitosamente"}
            )
        else:
            return jsonify({"success": False, "error": "Error al guardar cliente"}), 500

    except Exception as e:
        print(f"Error en guardar_cliente_seleccionado: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500


@app.route("/cargar_cliente_seleccionado", methods=["GET"])
@login_requerido
def cargar_cliente_seleccionado():
    """Cargar la última selección de cliente del usuario"""
    try:
        usuario = session.get("usuario", "default")
        config = cargar_configuracion_usuario(usuario)
        cliente = config.get("cliente_seleccionado", "") if config else ""

        return jsonify({"success": True, "cliente": cliente})

    except Exception as e:
        print(f"Error en cargar_cliente_seleccionado: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500


@app.route("/actualizar_estado_desecho_almacen", methods=["POST"])
@login_requerido
def actualizar_estado_desecho_almacen():
    """Actualizar el estado de desecho de un registro de control de almacén"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {"success": False, "error": "No se proporcionaron datos"}
            ), 400

        registro_id = data.get("id")
        estado_desecho = data.get("estado_desecho", 0)

        if not registro_id:
            return jsonify(
                {"success": False, "error": "ID de registro no proporcionado"}
            ), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Convertir a entero (0 o 1)
        estado_valor = 1 if estado_desecho else 0

        cursor.execute(
            """
            UPDATE control_material_almacen
            SET estado_desecho = %s
            WHERE id = %s
        """,
            (estado_valor, registro_id),
        )

        if cursor.rowcount == 0:
            return jsonify({"success": False, "error": "Registro no encontrado"}), 404

        conn.commit()
        return jsonify(
            {"success": True, "message": "Estado de desecho actualizado correctamente"}
        )

    except Exception as e:
        print(f"Error al actualizar estado de desecho: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500

    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass


@app.route("/obtener_siguiente_secuencial", methods=["GET"])
def obtener_siguiente_secuencial():
    """
    Obtiene el siguiente número secuencial para el código de material recibido.
    Formato corregido: NUMERO_PARTE,YYYYMMDD0001 (donde 0001 incrementa por cada registro del mismo número de parte y fecha)

    Ejemplos:
    - 0CE106AH638,202507080001 (primer registro del día)
    - 0CE106AH638,202507080002 (segundo registro del día)
    - 0CE106AH638,202507080003 (tercer registro del día)
    """
    try:
        # Obtener el código de material del parámetro de la URL
        codigo_material = request.args.get("codigo_material", "")

        if not codigo_material:
            return jsonify(
                {
                    "success": False,
                    "error": "Código de material es requerido",
                    "siguiente_secuencial": 1,
                }
            ), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Primero buscar el número de parte correspondiente al código de material
        query_numero_parte = """
        SELECT numero_parte
        FROM materiales
        WHERE codigo_material = %s
        LIMIT 1
        """

        cursor.execute(query_numero_parte, (codigo_material,))
        resultado_numero_parte = cursor.fetchone()

        if resultado_numero_parte:
            numero_parte = resultado_numero_parte["numero_parte"]
            print(
                f" Número de parte encontrado: '{numero_parte}' para código: '{codigo_material}'"
            )
        else:
            numero_parte = codigo_material  # Fallback al código original
            print(
                f"⚠️ No se encontró número de parte, usando código material: '{numero_parte}'"
            )

        # Obtener la fecha actual en formato YYYYMMDD
        fecha_actual = obtener_fecha_hora_mexico().strftime("%Y%m%d")

        print(
            f" Buscando secuenciales para número de parte: '{numero_parte}' y fecha: {fecha_actual}"
        )

        # Buscar registros específicos para este número de parte y fecha exacta
        # El formato buscado es: NUMERO_PARTE,YYYYMMDD0001 en el campo codigo_material_recibido
        query = """
        SELECT codigo_material_recibido, fecha_registro
        FROM control_material_almacen
        WHERE codigo_material_recibido LIKE %s
        ORDER BY fecha_registro DESC
        """

        # Patrón de búsqueda: NUMERO_PARTE,YYYYMMDD seguido de 4 dígitos (usando número de parte)
        patron_busqueda = f"{numero_parte},{fecha_actual}%"

        cursor.execute(query, (patron_busqueda,))
        resultados = cursor.fetchall()

        print(
            f" Encontrados {len(resultados)} registros para el patrón '{patron_busqueda}'"
        )

        # Buscar el secuencial más alto para este número de parte y fecha específica
        secuencial_mas_alto = 0
        patron_regex = rf"^{re.escape(numero_parte)},{fecha_actual}(\d{{4}})$"

        for resultado in resultados:
            codigo_recibido = resultado["codigo_material_recibido"] or ""

            print(f" Analizando: codigo_material_recibido='{codigo_recibido}'")

            # Buscar patrón exacto: NUMERO_PARTE,YYYYMMDD0001
            match = re.match(patron_regex, codigo_recibido)

            if match:
                secuencial_encontrado = int(match.group(1))
                print(f"✓ Secuencial encontrado: {secuencial_encontrado}")

                if secuencial_encontrado > secuencial_mas_alto:
                    secuencial_mas_alto = secuencial_encontrado
                    print(f" Nuevo secuencial más alto: {secuencial_mas_alto}")
            else:
                print(f" No coincide con patrón esperado: {codigo_recibido}")

        siguiente_secuencial = secuencial_mas_alto + 1

        # Generar el próximo código de material recibido completo usando número de parte
        siguiente_codigo_completo = (
            f"{numero_parte},{fecha_actual}{siguiente_secuencial:04d}"
        )

        print(f" Siguiente secuencial: {siguiente_secuencial}")
        print(f" Próximo código completo: {siguiente_codigo_completo}")

        cursor.close()
        conn.close()

        return jsonify(
            {
                "success": True,
                "siguiente_secuencial": siguiente_secuencial,
                "fecha_actual": fecha_actual,
                "codigo_material": codigo_material,
                "numero_parte": numero_parte,
                "secuencial_mas_alto_encontrado": secuencial_mas_alto,
                "patron_busqueda": patron_busqueda,
                "proximo_codigo_completo": siguiente_codigo_completo,
            }
        )

    except Exception as e:
        print(f" Error al obtener siguiente secuencial: {e}")
        import traceback

        traceback.print_exc()
        return jsonify(
            {
                "success": False,
                "error": str(e),
                "siguiente_secuencial": 1,  # Valor por defecto en caso de error
            }
        ), 500


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
# Reexportamos las funciones de bootstrap para preservar `startup_init.py`.
from app.api.control_produccion.plan_smd import (  # noqa: E402, F401
    crear_tabla_plan_smd,
    crear_tabla_plan_smd_runs,
)


@app.route("/api/work-orders", methods=["GET"])
@login_requerido
def api_work_orders():
    """API para obtener Work Orders con filtros"""
    try:
        # Parámetros de filtro
        q = request.args.get("q", "").strip()
        estados_param = request.args.get("estado", "")
        desde = request.args.get("desde", "")
        hasta = request.args.get("hasta", "")

        # Estados por defecto
        if estados_param:
            estados = [estado.strip() for estado in estados_param.split(",")]
        else:
            estados = ["CREADA", "PLANIFICADA"]

        # Construir query base
        query = """
        SELECT id, codigo_wo, codigo_po, modelo, nombre_modelo, codigo_modelo,
               cantidad_planeada, fecha_operacion, estado, usuario_creacion,
               orden_proceso, modificador, fecha_modificacion
        FROM work_orders
        WHERE 1=1
        """
        params = []

        # Filtros
        if estados:
            placeholders = ",".join(["%s"] * len(estados))
            query += f" AND estado IN ({placeholders})"
            params.extend(estados)

        if q:
            query += " AND (codigo_wo LIKE %s OR codigo_po LIKE %s OR modelo LIKE %s OR codigo_modelo LIKE %s)"
            q_param = f"%{q}%"
            params.extend([q_param, q_param, q_param, q_param])

        if desde:
            query += " AND fecha_operacion >= %s"
            params.append(desde)

        if hasta:
            query += " AND fecha_operacion <= %s"
            params.append(hasta)

        query += " ORDER BY fecha_operacion ASC, codigo_modelo ASC"

        # Ejecutar query
        work_orders = execute_query(query, params, fetch="all")

        # Verificar cuáles WOs ya fueron importadas (existen en plan_main)
        wo_ids = [wo["id"] for wo in work_orders]
        ya_importados = {}

        if wo_ids:
            placeholders = ",".join(["%s"] * len(wo_ids))
            check_query = f"""
            SELECT DISTINCT wo_id, lot_no
            FROM plan_main
            WHERE wo_id IN ({placeholders}) AND wo_id IS NOT NULL
            """
            importados = execute_query(check_query, wo_ids, fetch="all")

            for imp in importados:
                ya_importados[imp["wo_id"]] = imp["lot_no"]

        # Formatear respuesta
        resultado = []
        for wo in work_orders:
            wo_id = wo["id"]
            resultado.append(
                {
                    "id": wo_id,
                    "codigo_wo": wo["codigo_wo"],
                    "codigo_po": wo["codigo_po"] or "",
                    "modelo": wo["modelo"] or "",
                    "nombre_modelo": wo["nombre_modelo"] or "",
                    "codigo_modelo": wo["codigo_modelo"] or "",
                    "cantidad_planeada": wo["cantidad_planeada"] or 0,
                    "fecha_operacion": wo["fecha_operacion"].strftime("%Y-%m-%d")
                    if wo["fecha_operacion"]
                    else "",
                    "estado": wo["estado"] or "",
                    "usuario_creacion": wo["usuario_creacion"] or "",
                    "orden_proceso": wo["orden_proceso"] or "",
                    "modificador": wo["modificador"] or "",
                    "fecha_modificacion": wo["fecha_modificacion"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if wo["fecha_modificacion"]
                    else "",
                    "ya_importado": wo_id in ya_importados,
                    "lot_no_existente": ya_importados.get(wo_id, None),
                }
            )

        return jsonify(resultado)

    except Exception as e:
        print(f" Error en API work-orders: {e}")
        return jsonify({"error": str(e)}), 500


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





@app.route("/control_proceso/control_produccion_smt")
@login_requerido
def control_produccion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de produccion SMT"""
    try:
        # Devolver fragmento AJAX dedicado para evitar cargar una página completa dentro de un contenedor
        return render_template("Control de proceso/control_produccion_smt_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Control de produccion SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# Ruta eliminada - Control de operacion de linea SMT será reemplazado por Control BOM


@app.route("/control-operacion-linea-smt-ajax")
@login_requerido
def control_operacion_linea_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de operación de línea SMT"""
    try:
        fecha_hoy = obtener_fecha_hora_mexico().strftime("%d/%m/%Y")
        return render_template(
            "Control de proceso/control_operacion_linea_smt_ajax.html",
            fecha_hoy=fecha_hoy,
        )
    except Exception as e:
        print(f"Error al cargar template Control de operación de línea SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# Rutas AJAX para todos los módulos de Control de Proceso
@app.route("/control-impresion-identificacion-smt-ajax")
@login_requerido
def control_impresion_identificacion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de impresión de identificación SMT"""
    try:
        return render_template(
            "Control de proceso/control_impresion_identificacion_smt_ajax.html"
        )
    except Exception as e:
        print(
            f"Error al cargar template Control de impresión de identificación SMT AJAX: {e}"
        )
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/control-registro-identificacion-smt-ajax")
@login_requerido
def control_registro_identificacion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de registro de identificación SMT"""
    try:
        return render_template(
            "Control de proceso/control_registro_identificacion_smt_ajax.html"
        )
    except Exception as e:
        print(
            f"Error al cargar template Control de registro de identificación SMT AJAX: {e}"
        )
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/historial-operacion-proceso-ajax")
@login_requerido
def historial_operacion_proceso_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Historial de operación de proceso"""
    try:
        return render_template(
            "Control de proceso/historial_operacion_proceso_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Historial de operación de proceso AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/bom-management-process-ajax")
@login_requerido
def bom_management_process_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de BOM Management Process"""
    try:
        return render_template("Control de proceso/bom_management_process_ajax.html")
    except Exception as e:
        print(f"Error al cargar template BOM Management Process AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/reporte-diario-inspeccion-smt-ajax")
@login_requerido
def reporte_diario_inspeccion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Reporte diario de inspección SMT"""
    try:
        return render_template(
            "Control de proceso/reporte_diario_inspeccion_smt_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Reporte diario de inspección SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/control-diario-inspeccion-smt-ajax")
@login_requerido
def control_diario_inspeccion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control diario de inspección SMT"""
    try:
        return render_template(
            "Control de proceso/control_diario_inspeccion_smt_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Control diario de inspección SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/reporte-diario-inspeccion-proceso-ajax")
@login_requerido
def reporte_diario_inspeccion_proceso_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Reporte diario de inspección de proceso"""
    try:
        return render_template(
            "Control de proceso/reporte_diario_inspeccion_proceso_ajax.html"
        )
    except Exception as e:
        print(
            f"Error al cargar template Reporte diario de inspección de proceso AJAX: {e}"
        )
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/control-unidad-empaque-modelo-ajax")
@login_requerido
def control_unidad_empaque_modelo_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de unidad de empaque modelo"""
    try:
        return render_template(
            "Control de proceso/control_unidad_empaque_modelo_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Control de unidad de empaque modelo AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/packaging-register-management-ajax")
@login_requerido
def packaging_register_management_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Packaging Register Management"""
    try:
        return render_template(
            "Control de proceso/packaging_register_management_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Packaging Register Management AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/search-packaging-history-ajax")
@login_requerido
def search_packaging_history_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Search Packaging History"""
    try:
        return render_template("Control de proceso/search_packaging_history_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Search Packaging History AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/shipping-register-management-ajax")
@login_requerido
def shipping_register_management_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Shipping Register Management"""
    try:
        return render_template(
            "Control de proceso/shipping_register_management_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Shipping Register Management AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/search-shipping-history-ajax")
@login_requerido
def search_shipping_history_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Search Shipping History"""
    try:
        return render_template("Control de proceso/search_shipping_history_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Search Shipping History AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


def _normalizar_numero_embarques_historial(value):
    """Convertir Decimals a int/float legibles para JSON y Excel."""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        try:
            entero = int(value)
            return entero if value == entero else float(value)
        except Exception:
            return float(value)
    return value


def _normalizar_texto_embarques_historial(value):
    """Normalizar valores escalar a texto simple."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _aplicar_filtros_historial_embarques(sql, params, search_columns):
    """Aplicar filtros comunes de historial para los módulos de embarques."""
    search = request.args.get("search", "").strip()
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()

    # Los historiales operativos sólo deben mostrar el periodo vigente.
    # Los movimientos anteriores quedan trazados en el historial de cierres.
    sql += f"""
        AND COALESCE(movement_at, created_at) >= COALESCE(
            (SELECT MAX(closed_at) FROM `{SHIPPING_TABLES['inventory_closures']}`),
            '1000-01-01'
        )
    """

    if fecha_desde:
        sql += " AND DATE(COALESCE(movement_at, created_at)) >= %s"
        params.append(fecha_desde)

    if fecha_hasta:
        sql += " AND DATE(COALESCE(movement_at, created_at)) <= %s"
        params.append(fecha_hasta)

    if search:
        like_value = f"%{search}%"
        sql += " AND (" + " OR ".join(
            [f"COALESCE({column}, '') LIKE %s" for column in search_columns]
        ) + ")"
        params.extend([like_value] * len(search_columns))

    return sql, params


def _obtener_historial_entradas_almacen_embarques(limit=300):
    sql = """
        SELECT
            DATE(COALESCE(movement_at, created_at)) AS fecha,
            DATE_FORMAT(COALESCE(movement_at, created_at), '%%H:%%i:%%s') AS hora,
            entry_folio AS folio,
            part_number,
            quantity AS cantidad,
            previous_quantity,
            new_quantity,
            available_quantity,
            product_model,
            description,
            customer,
            zone_code,
            location_code,
            reference_code,
            batch_no,
            registered_by
        FROM embarques_entrada_material
        WHERE COALESCE(is_fifo_layer_only, 0) = 0
    """
    params = []
    sql, params = _aplicar_filtros_historial_embarques(
        sql,
        params,
        [
            "entry_folio",
            "part_number",
            "product_model",
            "description",
            "customer",
            "zone_code",
            "location_code",
            "reference_code",
            "registered_by",
        ],
    )
    sql += " ORDER BY COALESCE(movement_at, created_at) DESC, id DESC LIMIT %s"
    params.append(limit)

    rows = execute_query(sql, tuple(params), fetch="all") or []
    return [
        {
            "fecha": _normalizar_texto_embarques_historial(row.get("fecha")),
            "hora": _normalizar_texto_embarques_historial(row.get("hora")),
            "folio": _normalizar_texto_embarques_historial(row.get("folio")),
            "part_number": _normalizar_texto_embarques_historial(
                row.get("part_number")
            ),
            "cantidad": _normalizar_numero_embarques_historial(row.get("cantidad")),
            "previous_quantity": _normalizar_numero_embarques_historial(
                row.get("previous_quantity")
            ),
            "new_quantity": _normalizar_numero_embarques_historial(
                row.get("new_quantity")
            ),
            "available_quantity": _normalizar_numero_embarques_historial(
                row.get("available_quantity")
            ),
            "product_model": _normalizar_texto_embarques_historial(
                row.get("product_model")
            ),
            "description": _normalizar_texto_embarques_historial(
                row.get("description")
            ),
            "customer": _normalizar_texto_embarques_historial(row.get("customer")),
            "zone_code": _normalizar_texto_embarques_historial(row.get("zone_code")),
            "location_code": _normalizar_texto_embarques_historial(
                row.get("location_code")
            ),
            "reference_code": _normalizar_texto_embarques_historial(
                row.get("reference_code")
            ),
            "batch_no": _normalizar_texto_embarques_historial(row.get("batch_no")),
            "registered_by": _normalizar_texto_embarques_historial(
                row.get("registered_by")
            ),
        }
        for row in rows
    ]


def _obtener_historial_salidas_almacen_embarques(limit=300):
    sql = """
        SELECT
            id,
            DATE(COALESCE(movement_at, created_at)) AS fecha,
            DATE_FORMAT(COALESCE(movement_at, created_at), '%%H:%%i:%%s') AS hora,
            exit_folio AS folio,
            part_number,
            quantity AS cantidad,
            previous_quantity,
            new_quantity,
            product_model,
            description,
            customer,
            zone_code,
            location_code,
            destination_area,
            departure_code,
            departure_assigned_at,
            departure_assigned_by,
            reason,
            requested_by,
            registered_by
        FROM embarques_salida_material
        WHERE 1=1
    """
    params = []
    sql, params = _aplicar_filtros_historial_embarques(
        sql,
        params,
        [
            "exit_folio",
            "part_number",
            "product_model",
            "description",
            "customer",
            "zone_code",
            "location_code",
            "destination_area",
            "departure_code",
            "departure_assigned_by",
            "reason",
            "requested_by",
            "registered_by",
        ],
    )
    sql += " ORDER BY COALESCE(movement_at, created_at) DESC LIMIT %s"
    params.append(limit)

    rows = execute_query(sql, tuple(params), fetch="all") or []
    return [
        {
            "id": row.get("id"),
            "fecha": _normalizar_texto_embarques_historial(row.get("fecha")),
            "hora": _normalizar_texto_embarques_historial(row.get("hora")),
            "folio": _normalizar_texto_embarques_historial(row.get("folio")),
            "part_number": _normalizar_texto_embarques_historial(
                row.get("part_number")
            ),
            "cantidad": _normalizar_numero_embarques_historial(row.get("cantidad")),
            "previous_quantity": _normalizar_numero_embarques_historial(
                row.get("previous_quantity")
            ),
            "new_quantity": _normalizar_numero_embarques_historial(
                row.get("new_quantity")
            ),
            "product_model": _normalizar_texto_embarques_historial(
                row.get("product_model")
            ),
            "description": _normalizar_texto_embarques_historial(
                row.get("description")
            ),
            "customer": _normalizar_texto_embarques_historial(row.get("customer")),
            "zone_code": _normalizar_texto_embarques_historial(row.get("zone_code")),
            "location_code": _normalizar_texto_embarques_historial(
                row.get("location_code")
            ),
            "destination_area": _normalizar_texto_embarques_historial(
                row.get("destination_area")
            ),
            "departure_code": _normalizar_texto_embarques_historial(
                row.get("departure_code")
            ),
            "departure_assigned_at": _normalizar_texto_embarques_historial(
                row.get("departure_assigned_at")
            ),
            "departure_assigned_by": _normalizar_texto_embarques_historial(
                row.get("departure_assigned_by")
            ),
            "reason": _normalizar_texto_embarques_historial(row.get("reason")),
            "requested_by": _normalizar_texto_embarques_historial(
                row.get("requested_by")
            ),
            "registered_by": _normalizar_texto_embarques_historial(
                row.get("registered_by")
            ),
        }
        for row in rows
    ]


def _obtener_historial_retorno_almacen_embarques(limit=300):
    sql = """
        SELECT
            id,
            DATE(COALESCE(movement_at, created_at)) AS fecha,
            DATE_FORMAT(COALESCE(movement_at, created_at), '%%H:%%i:%%s') AS hora,
            return_folio AS folio,
            part_number,
            return_quantity,
            loss_quantity,
            previous_quantity,
            new_quantity,
            product_model,
            description,
            customer,
            zone_code,
            location_code,
            reason,
            remarks,
            registered_by
        FROM embarques_retorno_material
        WHERE 1=1
    """
    params = []
    sql, params = _aplicar_filtros_historial_embarques(
        sql,
        params,
        [
            "return_folio",
            "part_number",
            "product_model",
            "description",
            "customer",
            "zone_code",
            "location_code",
            "reason",
            "remarks",
            "registered_by",
        ],
    )
    sql += " ORDER BY COALESCE(movement_at, created_at) DESC LIMIT %s"
    params.append(limit)

    rows = execute_query(sql, tuple(params), fetch="all") or []
    return [
        {
            "id": row.get("id"),
            "fecha": _normalizar_texto_embarques_historial(row.get("fecha")),
            "hora": _normalizar_texto_embarques_historial(row.get("hora")),
            "folio": _normalizar_texto_embarques_historial(row.get("folio")),
            "part_number": _normalizar_texto_embarques_historial(
                row.get("part_number")
            ),
            "return_quantity": _normalizar_numero_embarques_historial(
                row.get("return_quantity")
            ),
            "loss_quantity": _normalizar_numero_embarques_historial(
                row.get("loss_quantity")
            ),
            "previous_quantity": _normalizar_numero_embarques_historial(
                row.get("previous_quantity")
            ),
            "new_quantity": _normalizar_numero_embarques_historial(
                row.get("new_quantity")
            ),
            "product_model": _normalizar_texto_embarques_historial(
                row.get("product_model")
            ),
            "description": _normalizar_texto_embarques_historial(
                row.get("description")
            ),
            "customer": _normalizar_texto_embarques_historial(row.get("customer")),
            "zone_code": _normalizar_texto_embarques_historial(row.get("zone_code")),
            "location_code": _normalizar_texto_embarques_historial(
                row.get("location_code")
            ),
            "reason": _normalizar_texto_embarques_historial(row.get("reason")),
            "remarks": _normalizar_texto_embarques_historial(row.get("remarks")),
            "registered_by": _normalizar_texto_embarques_historial(
                row.get("registered_by")
            ),
        }
        for row in rows
    ]


def _obtener_movimientos_editables_almacen_embarques(limit=500):
    limit = min(max(int(limit or 500), 1), 2000)
    tipo = (request.args.get("tipo", "") or "").strip().lower()
    search = (request.args.get("search", "") or "").strip()
    fecha_desde = (request.args.get("fecha_desde", "") or "").strip()
    fecha_hasta = (request.args.get("fecha_hasta", "") or "").strip()

    sql = f"""
        SELECT
            movimiento.movement_type,
            movimiento.movement_label,
            movimiento.record_id,
            DATE(movimiento.movement_timestamp) AS fecha,
            DATE_FORMAT(movimiento.movement_timestamp, '%%H:%%i:%%s') AS hora,
            movimiento.folio,
            movimiento.part_number,
            movimiento.quantity_primary,
            movimiento.quantity_secondary,
            movimiento.product_model,
            movimiento.customer,
            movimiento.zone_code,
            movimiento.location_value,
            movimiento.detail,
            movimiento.departure_code,
            movimiento.registered_by,
            ajuste.adjusted_by AS last_adjusted_by,
            ajuste.adjusted_at AS last_adjusted_at
        FROM (
            SELECT
                'entry' AS movement_type,
                'Entrada' AS movement_label,
                e.id AS record_id,
                COALESCE(e.movement_at, e.created_at) AS movement_timestamp,
                e.entry_folio AS folio,
                e.part_number,
                e.quantity AS quantity_primary,
                NULL AS quantity_secondary,
                e.product_model,
                e.customer,
                e.zone_code,
                e.location_code AS location_value,
                CONCAT_WS(' / ', NULLIF(e.zone_code, ''), NULLIF(e.location_code, '')) AS detail,
                NULL AS departure_code,
                e.registered_by
            FROM `{SHIPPING_TABLES['entries']}` e
            WHERE COALESCE(e.is_fifo_layer_only, 0) = 0

            UNION ALL

            SELECT
                'exit' AS movement_type,
                'Salida' AS movement_label,
                s.id AS record_id,
                COALESCE(s.movement_at, s.created_at) AS movement_timestamp,
                s.exit_folio AS folio,
                s.part_number,
                s.quantity AS quantity_primary,
                NULL AS quantity_secondary,
                s.product_model,
                s.customer,
                s.zone_code,
                s.destination_area AS location_value,
                CONCAT_WS(' / ', NULLIF(s.destination_area, ''), NULLIF(s.reason, '')) AS detail,
                s.departure_code,
                s.registered_by
            FROM `{SHIPPING_TABLES['exits']}` s

            UNION ALL

            SELECT
                'return' AS movement_type,
                'Retorno' AS movement_label,
                r.id AS record_id,
                COALESCE(r.movement_at, r.created_at) AS movement_timestamp,
                r.return_folio AS folio,
                r.part_number,
                r.return_quantity AS quantity_primary,
                r.loss_quantity AS quantity_secondary,
                r.product_model,
                r.customer,
                r.zone_code,
                r.location_code AS location_value,
                CONCAT_WS(' / ', NULLIF(r.reason, ''), NULLIF(r.remarks, '')) AS detail,
                NULL AS departure_code,
                r.registered_by
            FROM `{SHIPPING_TABLES['returns']}` r
        ) movimiento
        LEFT JOIN (
            SELECT
                a.movement_type,
                a.record_id,
                a.adjusted_by,
                a.adjusted_at
            FROM `{SHIPPING_TABLES['movement_adjustments']}` a
            INNER JOIN (
                SELECT movement_type, record_id, MAX(id) AS latest_id
                FROM `{SHIPPING_TABLES['movement_adjustments']}`
                GROUP BY movement_type, record_id
            ) latest
                ON latest.latest_id = a.id
        ) ajuste
            ON ajuste.movement_type = movimiento.movement_type
           AND ajuste.record_id = movimiento.record_id
        WHERE 1 = 1
    """
    params = []

    if tipo in {"entry", "exit", "return"}:
        sql += " AND movimiento.movement_type = %s"
        params.append(tipo)

    if fecha_desde:
        sql += " AND DATE(movimiento.movement_timestamp) >= %s"
        params.append(fecha_desde)

    if fecha_hasta:
        sql += " AND DATE(movimiento.movement_timestamp) <= %s"
        params.append(fecha_hasta)

    if search:
        like_value = f"%{search}%"
        sql += """
            AND (
                COALESCE(movimiento.folio, '') LIKE %s
                OR COALESCE(movimiento.part_number, '') LIKE %s
                OR COALESCE(movimiento.product_model, '') LIKE %s
                OR COALESCE(movimiento.customer, '') LIKE %s
                OR COALESCE(movimiento.zone_code, '') LIKE %s
                OR COALESCE(movimiento.location_value, '') LIKE %s
                OR COALESCE(movimiento.detail, '') LIKE %s
                OR COALESCE(movimiento.departure_code, '') LIKE %s
                OR COALESCE(movimiento.registered_by, '') LIKE %s
            )
        """
        params.extend([like_value] * 9)

    sql += " ORDER BY movimiento.movement_timestamp DESC, movimiento.record_id DESC LIMIT %s"
    params.append(limit)

    rows = execute_query(sql, tuple(params), fetch="all") or []
    return [
        {
            "movement_type": _normalizar_texto_embarques_historial(row.get("movement_type")),
            "movement_label": _normalizar_texto_embarques_historial(row.get("movement_label")),
            "record_id": row.get("record_id"),
            "fecha": _normalizar_texto_embarques_historial(row.get("fecha")),
            "hora": _normalizar_texto_embarques_historial(row.get("hora")),
            "folio": _normalizar_texto_embarques_historial(row.get("folio")),
            "part_number": _normalizar_texto_embarques_historial(row.get("part_number")),
            "quantity_primary": _normalizar_numero_embarques_historial(row.get("quantity_primary")),
            "quantity_secondary": _normalizar_numero_embarques_historial(row.get("quantity_secondary")),
            "product_model": _normalizar_texto_embarques_historial(row.get("product_model")),
            "customer": _normalizar_texto_embarques_historial(row.get("customer")),
            "zone_code": _normalizar_texto_embarques_historial(row.get("zone_code")),
            "location_value": _normalizar_texto_embarques_historial(row.get("location_value")),
            "detail": _normalizar_texto_embarques_historial(row.get("detail")),
            "departure_code": _normalizar_texto_embarques_historial(row.get("departure_code")),
            "registered_by": _normalizar_texto_embarques_historial(row.get("registered_by")),
            "last_adjusted_by": _normalizar_texto_embarques_historial(row.get("last_adjusted_by")),
            "last_adjusted_at": _normalizar_texto_embarques_historial(row.get("last_adjusted_at")),
        }
        for row in rows
    ]


def _obtener_detalle_movimiento_almacen_embarques(movement_type, record_id):
    normalized_type = movement_type.strip().lower()
    record_id = int(record_id)

    if normalized_type == "entry":
        row = execute_query(
            f"""
            SELECT
                id,
                entry_folio AS folio,
                part_number,
                quantity,
                product_model,
                description,
                customer,
                zone_code,
                location_code,
                reference_code,
                batch_no,
                notes,
                registered_by,
                movement_at
            FROM `{SHIPPING_TABLES['entries']}`
            WHERE id = %s
              AND COALESCE(is_fifo_layer_only, 0) = 0
            LIMIT 1
            """,
            (record_id,),
            fetch="one",
        )
        if not row:
            return None
        return {
            "movement_type": "entry",
            "movement_label": "Entrada",
            "record_id": row.get("id"),
            "folio": _normalizar_texto_embarques_historial(row.get("folio")),
            "part_number": _normalizar_texto_embarques_historial(row.get("part_number")),
            "quantity": _normalizar_numero_embarques_historial(row.get("quantity")),
            "product_model": _normalizar_texto_embarques_historial(row.get("product_model")),
            "description": _normalizar_texto_embarques_historial(row.get("description")),
            "customer": _normalizar_texto_embarques_historial(row.get("customer")),
            "zone_code": _normalizar_texto_embarques_historial(row.get("zone_code")),
            "location_code": _normalizar_texto_embarques_historial(row.get("location_code")),
            "reference_code": _normalizar_texto_embarques_historial(row.get("reference_code")),
            "batch_no": _normalizar_texto_embarques_historial(row.get("batch_no")),
            "notes": _normalizar_texto_embarques_historial(row.get("notes")),
            "registered_by": _normalizar_texto_embarques_historial(row.get("registered_by")),
            "movement_at": _normalizar_texto_embarques_historial(row.get("movement_at")),
        }

    if normalized_type == "exit":
        row = execute_query(
            f"""
            SELECT
                id,
                exit_folio AS folio,
                part_number,
                quantity,
                product_model,
                description,
                customer,
                zone_code,
                location_code,
                destination_area,
                departure_code,
                reason,
                requested_by,
                remarks,
                registered_by,
                movement_at
            FROM `{SHIPPING_TABLES['exits']}`
            WHERE id = %s
            LIMIT 1
            """,
            (record_id,),
            fetch="one",
        )
        if not row:
            return None
        return {
            "movement_type": "exit",
            "movement_label": "Salida",
            "record_id": row.get("id"),
            "folio": _normalizar_texto_embarques_historial(row.get("folio")),
            "part_number": _normalizar_texto_embarques_historial(row.get("part_number")),
            "quantity": _normalizar_numero_embarques_historial(row.get("quantity")),
            "product_model": _normalizar_texto_embarques_historial(row.get("product_model")),
            "description": _normalizar_texto_embarques_historial(row.get("description")),
            "customer": _normalizar_texto_embarques_historial(row.get("customer")),
            "zone_code": _normalizar_texto_embarques_historial(row.get("zone_code")),
            "location_code": _normalizar_texto_embarques_historial(row.get("location_code")),
            "destination_area": _normalizar_texto_embarques_historial(row.get("destination_area")),
            "departure_code": _normalizar_texto_embarques_historial(row.get("departure_code")),
            "reason": _normalizar_texto_embarques_historial(row.get("reason")),
            "requested_by": _normalizar_texto_embarques_historial(row.get("requested_by")),
            "remarks": _normalizar_texto_embarques_historial(row.get("remarks")),
            "registered_by": _normalizar_texto_embarques_historial(row.get("registered_by")),
            "movement_at": _normalizar_texto_embarques_historial(row.get("movement_at")),
        }

    if normalized_type == "return":
        row = execute_query(
            f"""
            SELECT
                id,
                return_folio AS folio,
                part_number,
                return_quantity,
                loss_quantity,
                product_model,
                description,
                customer,
                zone_code,
                location_code,
                reason,
                remarks,
                registered_by,
                movement_at
            FROM `{SHIPPING_TABLES['returns']}`
            WHERE id = %s
            LIMIT 1
            """,
            (record_id,),
            fetch="one",
        )
        if not row:
            return None
        return {
            "movement_type": "return",
            "movement_label": "Retorno",
            "record_id": row.get("id"),
            "folio": _normalizar_texto_embarques_historial(row.get("folio")),
            "part_number": _normalizar_texto_embarques_historial(row.get("part_number")),
            "return_quantity": _normalizar_numero_embarques_historial(row.get("return_quantity")),
            "loss_quantity": _normalizar_numero_embarques_historial(row.get("loss_quantity")),
            "product_model": _normalizar_texto_embarques_historial(row.get("product_model")),
            "description": _normalizar_texto_embarques_historial(row.get("description")),
            "customer": _normalizar_texto_embarques_historial(row.get("customer")),
            "zone_code": _normalizar_texto_embarques_historial(row.get("zone_code")),
            "location_code": _normalizar_texto_embarques_historial(row.get("location_code")),
            "reason": _normalizar_texto_embarques_historial(row.get("reason")),
            "remarks": _normalizar_texto_embarques_historial(row.get("remarks")),
            "registered_by": _normalizar_texto_embarques_historial(row.get("registered_by")),
            "movement_at": _normalizar_texto_embarques_historial(row.get("movement_at")),
        }

    return None


def _obtener_inventario_general_almacen_embarques(limit=5000):
    limit = min(max(int(limit or 5000), 1), 20000)
    search = (request.args.get("search", "") or "").strip()
    part_number_key_expr = "CONVERT(%s USING utf8mb4) COLLATE utf8mb4_unicode_ci"

    closure_subquery = f"""
        SELECT
            cierre.part_number,
            {part_number_key_expr % 'cierre.part_number'} AS part_number_key,
            cierre.initial_quantity,
            cierre.closed_at,
            cierre.closure_label
        FROM `{SHIPPING_TABLES['inventory_closures']}` cierre
        INNER JOIN (
            SELECT
                {part_number_key_expr % 'part_number'} AS part_number_key,
                MAX(closed_at) AS latest_closed_at
            FROM `{SHIPPING_TABLES['inventory_closures']}`
            GROUP BY {part_number_key_expr % 'part_number'}
        ) ultimo
            ON ultimo.part_number_key = {part_number_key_expr % 'cierre.part_number'}
           AND ultimo.latest_closed_at = cierre.closed_at
    """

    params = []

    sql = f"""
        SELECT
            i.part_number,
            i.product_model,
            i.customer,
            i.current_quantity,
            cierre.initial_quantity AS closure_initial_quantity,
            cierre.closed_at AS period_start,
            cierre.closure_label,
            COALESCE(entradas.entries_qty, 0) AS entries_qty,
            COALESCE(salidas.exits_qty, 0) AS exits_qty,
            COALESCE(retornos.return_entries_qty, 0) AS return_entries_qty,
            COALESCE(retornos.return_exits_qty, 0) AS return_exits_qty
        FROM `{SHIPPING_TABLES['inventory']}` i
        LEFT JOIN ({closure_subquery}) cierre
            ON cierre.part_number_key = {part_number_key_expr % 'i.part_number'}
        LEFT JOIN (
            SELECT
                {part_number_key_expr % 'e.part_number'} AS part_number_key,
                COALESCE(SUM(e.quantity), 0) AS entries_qty
            FROM `{SHIPPING_TABLES['entries']}` e
            LEFT JOIN ({closure_subquery}) cierre_e
                ON cierre_e.part_number_key = {part_number_key_expr % 'e.part_number'}
            WHERE COALESCE(e.is_fifo_layer_only, 0) = 0
              AND COALESCE(e.movement_at, e.created_at) >= COALESCE(cierre_e.closed_at, '1000-01-01')
            GROUP BY {part_number_key_expr % 'e.part_number'}
        ) entradas
            ON entradas.part_number_key = {part_number_key_expr % 'i.part_number'}
        LEFT JOIN (
            SELECT
                {part_number_key_expr % 's.part_number'} AS part_number_key,
                COALESCE(SUM(s.quantity), 0) AS exits_qty
            FROM `{SHIPPING_TABLES['exits']}` s
            LEFT JOIN ({closure_subquery}) cierre_s
                ON cierre_s.part_number_key = {part_number_key_expr % 's.part_number'}
            WHERE COALESCE(s.movement_at, s.created_at) >= COALESCE(cierre_s.closed_at, '1000-01-01')
            GROUP BY {part_number_key_expr % 's.part_number'}
        ) salidas
            ON salidas.part_number_key = {part_number_key_expr % 'i.part_number'}
        LEFT JOIN (
            SELECT
                {part_number_key_expr % 'r.part_number'} AS part_number_key,
                COALESCE(SUM(r.return_quantity), 0) AS return_entries_qty,
                COALESCE(SUM(r.loss_quantity), 0) AS return_exits_qty
            FROM `{SHIPPING_TABLES['returns']}` r
            LEFT JOIN ({closure_subquery}) cierre_r
                ON cierre_r.part_number_key = {part_number_key_expr % 'r.part_number'}
            WHERE COALESCE(r.movement_at, r.created_at) >= COALESCE(cierre_r.closed_at, '1000-01-01')
            GROUP BY {part_number_key_expr % 'r.part_number'}
        ) retornos
            ON retornos.part_number_key = {part_number_key_expr % 'i.part_number'}
        WHERE 1 = 1
    """

    if search:
        like_value = f"%{search}%"
        sql += """
            AND (
                COALESCE(i.part_number, '') COLLATE utf8mb4_unicode_ci LIKE %s
            )
        """
        params.append(like_value)

    sql += " ORDER BY i.part_number ASC LIMIT %s"
    params.append(limit)

    rows = execute_query(sql, tuple(params), fetch="all") or []
    result_rows = []
    has_closure = False
    latest_period_start = None

    for row in rows:
        current_quantity = _normalizar_numero_embarques_historial(row.get("current_quantity"))
        entries_qty = _normalizar_numero_embarques_historial(row.get("entries_qty"))
        exits_qty = _normalizar_numero_embarques_historial(row.get("exits_qty"))
        return_entries_qty = _normalizar_numero_embarques_historial(row.get("return_entries_qty"))
        return_exits_qty = _normalizar_numero_embarques_historial(row.get("return_exits_qty"))
        closure_initial_quantity = row.get("closure_initial_quantity")
        period_start = _normalizar_texto_embarques_historial(row.get("period_start"))
        closure_label = _normalizar_texto_embarques_historial(row.get("closure_label"))

        if closure_initial_quantity is None:
            initial_quantity = (
                current_quantity
                - entries_qty
                + exits_qty
                - return_entries_qty
                + return_exits_qty
            )
        else:
            initial_quantity = _normalizar_numero_embarques_historial(closure_initial_quantity)
            has_closure = True

        calculated_current_quantity = (
            initial_quantity
            + entries_qty
            - exits_qty
            + return_entries_qty
            - return_exits_qty
        )

        if period_start and (latest_period_start is None or period_start > latest_period_start):
            latest_period_start = period_start

        result_rows.append(
            {
                "part_number": _normalizar_texto_embarques_historial(row.get("part_number")),
                "product_model": _normalizar_texto_embarques_historial(row.get("product_model")),
                "customer": _normalizar_texto_embarques_historial(row.get("customer")),
                "initial_quantity": initial_quantity,
                "entries_qty": entries_qty,
                "exits_qty": exits_qty,
                "return_entries_qty": return_entries_qty,
                "return_exits_qty": return_exits_qty,
                "current_quantity": calculated_current_quantity,
                "period_start": period_start,
                "closure_label": closure_label,
            }
        )

    return {
        "rows": result_rows,
        "summary": {
            "total_items": len(result_rows),
            "has_closure": has_closure,
            "latest_period_start": latest_period_start or "",
        },
    }


CATALOG_FIELD_KEYS = [
    "part_number",
    "product_model",
    "product_status",
    "description",
    "standard_pack",
    "customer",
    "zone_code",
]


def _normalizar_estado_catalogo_embarques(raw_value):
    value = normalize_search(raw_value).lower()
    if value in {"inactivo", "inactive", "baja", "0", "false"}:
        return "inactivo"
    return "activo"


def _normalizar_standard_pack_catalogo_embarques(raw_value):
    parsed = normalize_integer(raw_value)
    if parsed is None or parsed <= 0:
        return 1
    return parsed


def _serializar_catalogo_embarques(row):
    if not row:
        return {}
    return {
        "catalog_id": row.get("catalog_id") or row.get("id"),
        "inventory_id": row.get("inventory_id"),
        "part_number": _normalizar_texto_embarques_historial(row.get("part_number")),
        "product_model": _normalizar_texto_embarques_historial(row.get("product_model")),
        "product_status": _normalizar_texto_embarques_historial(row.get("product_status")),
        "description": _normalizar_texto_embarques_historial(row.get("description")),
        "standard_pack": _normalizar_numero_embarques_historial(row.get("standard_pack")),
        "customer": _normalizar_texto_embarques_historial(row.get("customer")),
        "zone_code": _normalizar_texto_embarques_historial(row.get("zone_code")),
        "current_quantity": _normalizar_numero_embarques_historial(row.get("current_quantity")),
        "entries_count": _normalizar_numero_embarques_historial(row.get("entries_count")),
        "exits_count": _normalizar_numero_embarques_historial(row.get("exits_count")),
        "returns_count": _normalizar_numero_embarques_historial(row.get("returns_count")),
        "departure_count": _normalizar_numero_embarques_historial(row.get("departure_count")),
        "closure_count": _normalizar_numero_embarques_historial(row.get("closure_count")),
    }


def _registrar_auditoria_catalogo_embarques(
    cursor,
    action,
    previous_values,
    new_values,
    changed_fields,
    notes,
):
    previous_values = previous_values or {}
    new_values = new_values or {}
    catalog_id = (
        new_values.get("catalog_id")
        or new_values.get("id")
        or previous_values.get("catalog_id")
        or previous_values.get("id")
    )
    inventory_id = new_values.get("inventory_id") or previous_values.get("inventory_id")
    part_before = previous_values.get("part_number")
    part_after = new_values.get("part_number")
    cursor.execute(
        f"""
        INSERT INTO `{SHIPPING_TABLES['catalog_adjustments']}` (
          catalog_id,
          inventory_id,
          action,
          part_number_before,
          part_number_after,
          previous_values_json,
          new_values_json,
          changed_fields_json,
          notes,
          adjusted_by,
          adjusted_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            catalog_id,
            inventory_id,
            action,
            part_before,
            part_after,
            json.dumps(previous_values, ensure_ascii=False, default=str, separators=(",", ":")),
            json.dumps(new_values, ensure_ascii=False, default=str, separators=(",", ":")),
            json.dumps(changed_fields or [], ensure_ascii=False, separators=(",", ":")),
            normalize_search(notes),
            _obtener_usuario_display_actual(),
            obtener_fecha_hora_mexico(),
        ),
    )


def _obtener_catalogo_almacen_embarques(limit=5000):
    limit = min(max(int(limit or 5000), 1), 20000)
    search = normalize_search(request.args.get("search"))
    status = normalize_search(request.args.get("status")).lower()
    params = []
    part_number_key_expr = "CONVERT(%s USING utf8mb4) COLLATE utf8mb4_unicode_ci"
    latest_closure_subquery = f"""
        SELECT
          {part_number_key_expr % 'part_number'} AS part_number_key,
          MAX(closed_at) AS latest_closed_at
        FROM `{SHIPPING_TABLES['inventory_closures']}`
        GROUP BY {part_number_key_expr % 'part_number'}
    """

    sql = f"""
        SELECT
          c.id AS catalog_id,
          i.id AS inventory_id,
          c.part_number,
          c.product_model,
          c.product_status,
          c.description,
          c.standard_pack,
          c.customer,
          c.zone_code,
          COALESCE(i.current_quantity, 0) AS current_quantity,
          COALESCE(entry_counts.total_rows, 0) AS entries_count,
          COALESCE(exit_counts.total_rows, 0) AS exits_count,
          COALESCE(return_counts.total_rows, 0) AS returns_count,
          COALESCE(departure_counts.total_rows, 0) AS departure_count,
          COALESCE(closure_counts.total_rows, 0) AS closure_count,
          COALESCE(entry_period_counts.total_rows, 0) AS period_entries_count,
          COALESCE(exit_period_counts.total_rows, 0) AS period_exits_count,
          COALESCE(return_period_counts.total_rows, 0) AS period_returns_count,
          COALESCE(departure_period_counts.total_rows, 0) AS period_departure_count,
          c.created_at,
          c.updated_at
        FROM `{SHIPPING_TABLES['catalog']}` c
        LEFT JOIN `{SHIPPING_TABLES['inventory']}` i
          ON i.catalog_id = c.id
        LEFT JOIN (
          SELECT catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['entries']}`
          GROUP BY catalog_id
        ) entry_counts
          ON entry_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['exits']}`
          GROUP BY catalog_id
        ) exit_counts
          ON exit_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['returns']}`
          GROUP BY catalog_id
        ) return_counts
          ON return_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['departure_history']}`
          GROUP BY catalog_id
        ) departure_counts
          ON departure_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT e.catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['entries']}` e
          LEFT JOIN ({latest_closure_subquery}) latest_closure
            ON latest_closure.part_number_key = {part_number_key_expr % 'e.part_number'}
          WHERE e.movement_at >= COALESCE(latest_closure.latest_closed_at, '1000-01-01')
          GROUP BY e.catalog_id
        ) entry_period_counts
          ON entry_period_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT s.catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['exits']}` s
          LEFT JOIN ({latest_closure_subquery}) latest_closure
            ON latest_closure.part_number_key = {part_number_key_expr % 's.part_number'}
          WHERE s.movement_at >= COALESCE(latest_closure.latest_closed_at, '1000-01-01')
          GROUP BY s.catalog_id
        ) exit_period_counts
          ON exit_period_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT r.catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['returns']}` r
          LEFT JOIN ({latest_closure_subquery}) latest_closure
            ON latest_closure.part_number_key = {part_number_key_expr % 'r.part_number'}
          WHERE r.movement_at >= COALESCE(latest_closure.latest_closed_at, '1000-01-01')
          GROUP BY r.catalog_id
        ) return_period_counts
          ON return_period_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT d.catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['departure_history']}` d
          LEFT JOIN ({latest_closure_subquery}) latest_closure
            ON latest_closure.part_number_key = {part_number_key_expr % 'd.part_number'}
          WHERE d.assigned_at >= COALESCE(latest_closure.latest_closed_at, '1000-01-01')
          GROUP BY d.catalog_id
        ) departure_period_counts
          ON departure_period_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT part_number, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['inventory_closures']}`
          GROUP BY part_number
        ) closure_counts
          ON closure_counts.part_number COLLATE utf8mb4_unicode_ci = c.part_number COLLATE utf8mb4_unicode_ci
        WHERE 1 = 1
    """

    if search:
        like_value = f"%{search}%"
        sql += """
          AND (
            COALESCE(c.part_number, '') COLLATE utf8mb4_unicode_ci LIKE %s
            OR COALESCE(c.product_model, '') COLLATE utf8mb4_unicode_ci LIKE %s
            OR COALESCE(c.description, '') COLLATE utf8mb4_unicode_ci LIKE %s
            OR COALESCE(c.customer, '') COLLATE utf8mb4_unicode_ci LIKE %s
          )
        """
        params.extend([like_value, like_value, like_value, like_value])

    if status in {"activo", "inactivo"}:
        sql += " AND c.product_status = %s"
        params.append(status)

    sql += " ORDER BY c.part_number ASC LIMIT %s"
    params.append(limit)

    rows = execute_query(sql, tuple(params), fetch="all") or []
    result_rows = []
    for row in rows:
        current_quantity = _normalizar_numero_embarques_historial(row.get("current_quantity"))
        movement_count = sum(
            _normalizar_numero_embarques_historial(row.get(key))
            for key in (
                "entries_count",
                "exits_count",
                "returns_count",
                "departure_count",
                "closure_count",
            )
        )
        period_movement_count = sum(
            _normalizar_numero_embarques_historial(row.get(key))
            for key in (
                "period_entries_count",
                "period_exits_count",
                "period_returns_count",
                "period_departure_count",
            )
        )
        result_rows.append(
            {
                "catalog_id": row.get("catalog_id"),
                "inventory_id": row.get("inventory_id"),
                "part_number": _normalizar_texto_embarques_historial(row.get("part_number")),
                "product_model": _normalizar_texto_embarques_historial(row.get("product_model")),
                "product_status": _normalizar_texto_embarques_historial(row.get("product_status")),
                "description": _normalizar_texto_embarques_historial(row.get("description")),
                "standard_pack": _normalizar_numero_embarques_historial(row.get("standard_pack")) or 1,
                "customer": _normalizar_texto_embarques_historial(row.get("customer")),
                "zone_code": _normalizar_texto_embarques_historial(row.get("zone_code")),
                "current_quantity": current_quantity,
                "movement_count": movement_count,
                "period_movement_count": period_movement_count,
                "entries_count": _normalizar_numero_embarques_historial(row.get("entries_count")),
                "exits_count": _normalizar_numero_embarques_historial(row.get("exits_count")),
                "returns_count": _normalizar_numero_embarques_historial(row.get("returns_count")),
                "departure_count": _normalizar_numero_embarques_historial(row.get("departure_count")),
                "closure_count": _normalizar_numero_embarques_historial(row.get("closure_count")),
                "delete_mode": (
                    "blocked_stock"
                    if current_quantity != 0
                    else "blocked_movements"
                    if period_movement_count > 0
                    else "soft_delete"
                    if movement_count > 0
                    else "hard_delete"
                ),
                "created_at": _normalizar_texto_embarques_historial(row.get("created_at")),
                "updated_at": _normalizar_texto_embarques_historial(row.get("updated_at")),
            }
        )

    return {"rows": result_rows, "summary": {"total_items": len(result_rows)}}


def _obtener_catalogo_detalle_almacen_embarques(cursor, catalog_id, for_update=False):
    lock_clause = " FOR UPDATE" if for_update else ""
    part_number_key_expr = "CONVERT(%s USING utf8mb4) COLLATE utf8mb4_unicode_ci"
    latest_closure_subquery = f"""
        SELECT
          {part_number_key_expr % 'part_number'} AS part_number_key,
          MAX(closed_at) AS latest_closed_at
        FROM `{SHIPPING_TABLES['inventory_closures']}`
        GROUP BY {part_number_key_expr % 'part_number'}
    """
    cursor.execute(
        f"""
        SELECT
          c.id AS catalog_id,
          i.id AS inventory_id,
          c.part_number,
          c.product_model,
          c.product_status,
          c.description,
          c.standard_pack,
          c.customer,
          c.zone_code,
          COALESCE(i.current_quantity, 0) AS current_quantity,
          COALESCE(entry_counts.total_rows, 0) AS entries_count,
          COALESCE(exit_counts.total_rows, 0) AS exits_count,
          COALESCE(return_counts.total_rows, 0) AS returns_count,
          COALESCE(departure_counts.total_rows, 0) AS departure_count,
          COALESCE(closure_counts.total_rows, 0) AS closure_count,
          COALESCE(entry_period_counts.total_rows, 0) AS period_entries_count,
          COALESCE(exit_period_counts.total_rows, 0) AS period_exits_count,
          COALESCE(return_period_counts.total_rows, 0) AS period_returns_count,
          COALESCE(departure_period_counts.total_rows, 0) AS period_departure_count
        FROM `{SHIPPING_TABLES['catalog']}` c
        LEFT JOIN `{SHIPPING_TABLES['inventory']}` i
          ON i.catalog_id = c.id
        LEFT JOIN (
          SELECT catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['entries']}`
          GROUP BY catalog_id
        ) entry_counts
          ON entry_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['exits']}`
          GROUP BY catalog_id
        ) exit_counts
          ON exit_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['returns']}`
          GROUP BY catalog_id
        ) return_counts
          ON return_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['departure_history']}`
          GROUP BY catalog_id
        ) departure_counts
          ON departure_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT e.catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['entries']}` e
          LEFT JOIN ({latest_closure_subquery}) latest_closure
            ON latest_closure.part_number_key = {part_number_key_expr % 'e.part_number'}
          WHERE e.movement_at >= COALESCE(latest_closure.latest_closed_at, '1000-01-01')
          GROUP BY e.catalog_id
        ) entry_period_counts
          ON entry_period_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT s.catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['exits']}` s
          LEFT JOIN ({latest_closure_subquery}) latest_closure
            ON latest_closure.part_number_key = {part_number_key_expr % 's.part_number'}
          WHERE s.movement_at >= COALESCE(latest_closure.latest_closed_at, '1000-01-01')
          GROUP BY s.catalog_id
        ) exit_period_counts
          ON exit_period_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT r.catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['returns']}` r
          LEFT JOIN ({latest_closure_subquery}) latest_closure
            ON latest_closure.part_number_key = {part_number_key_expr % 'r.part_number'}
          WHERE r.movement_at >= COALESCE(latest_closure.latest_closed_at, '1000-01-01')
          GROUP BY r.catalog_id
        ) return_period_counts
          ON return_period_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT d.catalog_id, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['departure_history']}` d
          LEFT JOIN ({latest_closure_subquery}) latest_closure
            ON latest_closure.part_number_key = {part_number_key_expr % 'd.part_number'}
          WHERE d.assigned_at >= COALESCE(latest_closure.latest_closed_at, '1000-01-01')
          GROUP BY d.catalog_id
        ) departure_period_counts
          ON departure_period_counts.catalog_id = c.id
        LEFT JOIN (
          SELECT part_number, COUNT(*) AS total_rows
          FROM `{SHIPPING_TABLES['inventory_closures']}`
          GROUP BY part_number
        ) closure_counts
          ON closure_counts.part_number COLLATE utf8mb4_unicode_ci = c.part_number COLLATE utf8mb4_unicode_ci
        WHERE c.id = %s
        LIMIT 1{lock_clause}
        """,
        (catalog_id,),
    )
    return cursor.fetchone()


def _validar_part_number_catalogo_unico(cursor, part_number, catalog_id=None, inventory_id=None):
    cursor.execute(
        f"""
        SELECT id
        FROM `{SHIPPING_TABLES['catalog']}`
        WHERE part_number = %s
          AND (%s IS NULL OR id <> %s)
        LIMIT 1
        """,
        (part_number, catalog_id, catalog_id),
    )
    if cursor.fetchone():
        return False, f"El número de parte {part_number} ya existe en el catálogo."

    cursor.execute(
        f"""
        SELECT id
        FROM `{SHIPPING_TABLES['inventory']}`
        WHERE part_number = %s
          AND (%s IS NULL OR id <> %s)
        LIMIT 1
        """,
        (part_number, inventory_id, inventory_id),
    )
    if cursor.fetchone():
        return False, f"El número de parte {part_number} ya existe en inventario actual."

    return True, ""


def _construir_payload_catalogo_embarques(data, current=None):
    part_number = normalize_part_number(data.get("partNumber") or data.get("part_number"))
    if not part_number and current:
        part_number = normalize_part_number(current.get("part_number"))

    return {
        "part_number": part_number,
        "product_model": normalize_search(data.get("productModel") or data.get("product_model")),
        "product_status": _normalizar_estado_catalogo_embarques(
            data.get("productStatus") or data.get("product_status") or "activo"
        ),
        "description": normalize_search(data.get("description")),
        "standard_pack": _normalizar_standard_pack_catalogo_embarques(
            data.get("standardPack") or data.get("standard_pack")
        ),
        "customer": normalize_search(data.get("customer")) or "LG",
        "zone_code": normalize_search(data.get("zoneCode") or data.get("zone_code")) or "pending",
    }


def _crear_catalogo_almacen_embarques(data):
    payload = _construir_payload_catalogo_embarques(data)
    if not payload["part_number"]:
        return {"success": False, "error": "El número de parte es obligatorio."}, 400

    conn = get_pooled_connection()
    if conn is None:
        raise RuntimeError("No fue posible obtener conexión MySQL.")

    cursor = get_dict_cursor(conn)
    try:
        conn.autocommit(False)
        is_unique, error_message = _validar_part_number_catalogo_unico(
            cursor,
            payload["part_number"],
        )
        if not is_unique:
            conn.rollback()
            return {"success": False, "error": error_message}, 409

        cursor.execute(
            f"""
            INSERT INTO `{SHIPPING_TABLES['catalog']}` (
              part_number,
              product_model,
              product_status,
              description,
              standard_pack,
              customer,
              zone_code,
              source_file
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'portal_catalogo_embarques')
            """,
            (
                payload["part_number"],
                payload["product_model"],
                payload["product_status"],
                payload["description"],
                payload["standard_pack"],
                payload["customer"],
                payload["zone_code"],
            ),
        )
        catalog_id = cursor.lastrowid
        cursor.execute(
            f"""
            INSERT INTO `{SHIPPING_TABLES['inventory']}` (
              catalog_id,
              part_number,
              product_model,
              product_status,
              description,
              customer,
              zone_code,
              standard_pack,
              current_quantity,
              catalog_loaded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, %s)
            """,
            (
                catalog_id,
                payload["part_number"],
                payload["product_model"],
                payload["product_status"],
                payload["description"],
                payload["customer"],
                payload["zone_code"],
                payload["standard_pack"],
                obtener_fecha_hora_mexico(),
            ),
        )
        inventory_id = cursor.lastrowid
        new_values = {
            "catalog_id": catalog_id,
            "inventory_id": inventory_id,
            **payload,
            "current_quantity": 0,
        }
        _registrar_auditoria_catalogo_embarques(
            cursor,
            "create",
            {},
            new_values,
            list(payload.keys()),
            data.get("notes") or "Alta desde portal",
        )
        conn.commit()
        return {
            "success": True,
            "message": "Número de parte agregado correctamente.",
            "row": new_values,
        }, 201
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def _actualizar_catalogo_almacen_embarques(catalog_id, data):
    notes = normalize_search(data.get("notes"))
    if not notes:
        return {"success": False, "error": "El motivo del cambio es obligatorio."}, 400

    conn = get_pooled_connection()
    if conn is None:
        raise RuntimeError("No fue posible obtener conexión MySQL.")

    cursor = get_dict_cursor(conn)
    try:
        conn.autocommit(False)
        current = _obtener_catalogo_detalle_almacen_embarques(cursor, catalog_id, True)
        if not current:
            conn.rollback()
            return {"success": False, "error": "Número de parte no encontrado."}, 404

        previous_values = _serializar_catalogo_embarques(current)
        payload = _construir_payload_catalogo_embarques(data, current)
        if not payload["part_number"]:
            conn.rollback()
            return {"success": False, "error": "El número de parte es obligatorio."}, 400

        is_unique, error_message = _validar_part_number_catalogo_unico(
            cursor,
            payload["part_number"],
            catalog_id=current.get("catalog_id"),
            inventory_id=current.get("inventory_id"),
        )
        if not is_unique:
            conn.rollback()
            return {"success": False, "error": error_message}, 409

        changed_fields = []
        for key in CATALOG_FIELD_KEYS:
            previous_value = previous_values.get(key)
            next_value = payload.get(key)
            if key == "standard_pack":
                previous_value = _normalizar_numero_embarques_historial(previous_value) or 1
            if normalize_search(previous_value) != normalize_search(next_value):
                changed_fields.append(key)

        if not changed_fields:
            conn.rollback()
            return {"success": False, "error": "No hay cambios para guardar."}, 400

        cursor.execute(
            f"""
            UPDATE `{SHIPPING_TABLES['catalog']}`
            SET part_number = %s,
                product_model = %s,
                product_status = %s,
                description = %s,
                standard_pack = %s,
                customer = %s,
                zone_code = %s
            WHERE id = %s
            """,
            (
                payload["part_number"],
                payload["product_model"],
                payload["product_status"],
                payload["description"],
                payload["standard_pack"],
                payload["customer"],
                payload["zone_code"],
                current.get("catalog_id"),
            ),
        )

        cursor.execute(
            f"""
            UPDATE `{SHIPPING_TABLES['inventory']}`
            SET part_number = %s,
                product_model = %s,
                product_status = %s,
                description = %s,
                customer = %s,
                zone_code = %s,
                standard_pack = %s
            WHERE catalog_id = %s
            """,
            (
                payload["part_number"],
                payload["product_model"],
                payload["product_status"],
                payload["description"],
                payload["customer"],
                payload["zone_code"],
                payload["standard_pack"],
                current.get("catalog_id"),
            ),
        )

        if "part_number" in changed_fields:
            for table_key in ("entries", "exits", "returns", "departure_history"):
                cursor.execute(
                    f"""
                    UPDATE `{SHIPPING_TABLES[table_key]}`
                    SET part_number = %s
                    WHERE catalog_id = %s
                    """,
                    (payload["part_number"], current.get("catalog_id")),
                )
            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['inventory_closures']}`
                SET part_number = %s
                WHERE part_number = %s
                """,
                (payload["part_number"], previous_values.get("part_number")),
            )
            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['manual_adjustment_items']}`
                SET part_number = %s
                WHERE part_number = %s
                """,
                (payload["part_number"], previous_values.get("part_number")),
            )

        next_values = {
            **previous_values,
            **payload,
            "catalog_id": current.get("catalog_id"),
            "inventory_id": current.get("inventory_id"),
            "current_quantity": previous_values.get("current_quantity"),
        }
        _registrar_auditoria_catalogo_embarques(
            cursor,
            "update",
            previous_values,
            next_values,
            changed_fields,
            notes,
        )
        conn.commit()
        return {
            "success": True,
            "message": "Número de parte actualizado correctamente.",
            "changedFields": changed_fields,
        }, 200
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def _eliminar_catalogo_almacen_embarques(catalog_id, data):
    valid_password, password_error = _validar_password_usuario_actual(data.get("password"))
    if not valid_password:
        return {"success": False, "error": password_error}, 403

    notes = normalize_search(data.get("notes"))
    if not notes:
        return {"success": False, "error": "El comentario de eliminación es obligatorio."}, 400

    conn = get_pooled_connection()
    if conn is None:
        raise RuntimeError("No fue posible obtener conexión MySQL.")

    cursor = get_dict_cursor(conn)
    try:
        conn.autocommit(False)
        current = _obtener_catalogo_detalle_almacen_embarques(cursor, catalog_id, True)
        if not current:
            conn.rollback()
            return {"success": False, "error": "Número de parte no encontrado."}, 404

        previous_values = _serializar_catalogo_embarques(current)
        current_quantity = _normalizar_numero_embarques_historial(current.get("current_quantity"))
        movement_count = sum(
            _normalizar_numero_embarques_historial(current.get(key))
            for key in (
                "entries_count",
                "exits_count",
                "returns_count",
                "departure_count",
                "closure_count",
            )
        )
        period_movement_count = sum(
            _normalizar_numero_embarques_historial(current.get(key))
            for key in (
                "period_entries_count",
                "period_exits_count",
                "period_returns_count",
                "period_departure_count",
            )
        )

        if current_quantity != 0:
            conn.rollback()
            return {
                "success": False,
                "error": (
                    "Este número de parte tiene stock. No se puede eliminar hasta haber "
                    "consumido el total de inventario."
                ),
            }, 409

        if period_movement_count > 0:
            conn.rollback()
            return {
                "success": False,
                "error": (
                    "Este número de parte tiene movimientos registrados. No se puede "
                    "eliminar hasta haber hecho el cierre mensual."
                ),
            }, 409

        if movement_count > 0:
            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['catalog']}`
                SET product_status = 'inactivo'
                WHERE id = %s
                """,
                (current.get("catalog_id"),),
            )
            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['inventory']}`
                SET product_status = 'inactivo'
                WHERE catalog_id = %s
                """,
                (current.get("catalog_id"),),
            )
            new_values = dict(previous_values)
            new_values["product_status"] = "inactivo"
            _registrar_auditoria_catalogo_embarques(
                cursor,
                "soft_delete",
                previous_values,
                new_values,
                ["product_status"],
                notes,
            )
            conn.commit()
            return {
                "success": True,
                "message": "Número de parte eliminado del catálogo activo.",
                "deleteMode": "soft_delete",
            }, 200

        cursor.execute(
            f"DELETE FROM `{SHIPPING_TABLES['inventory']}` WHERE catalog_id = %s",
            (current.get("catalog_id"),),
        )
        cursor.execute(
            f"DELETE FROM `{SHIPPING_TABLES['catalog']}` WHERE id = %s",
            (current.get("catalog_id"),),
        )
        _registrar_auditoria_catalogo_embarques(
            cursor,
            "hard_delete",
            previous_values,
            {},
            ["deleted"],
            notes,
        )
        conn.commit()
        return {
            "success": True,
            "message": "Número de parte eliminado correctamente.",
            "deleteMode": "hard_delete",
        }, 200
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def _obtener_usuario_display_actual():
    return (
        session.get("nombre_completo")
        or session.get("usuario")
        or "Sistema"
    ).strip()


def _validar_password_usuario_actual(raw_password):
    usuario = (session.get("usuario") or "").strip()
    password = str(raw_password or "").strip()

    if not usuario:
        return False, "No se encontro un usuario valido en sesion"
    if not password:
        return False, "Debes confirmar tu contraseña actual"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            raise RuntimeError("No se pudo obtener conexion a la base de datos")

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT password_hash
            FROM usuarios_sistema
            WHERE username = %s
            LIMIT 1
            """,
            (usuario,),
        )
        usuario_row = cursor.fetchone()
        if isinstance(usuario_row, dict):
            password_hash_actual = usuario_row.get("password_hash") or ""
        elif usuario_row:
            password_hash_actual = usuario_row[0] or ""
        else:
            password_hash_actual = ""

        if not password_hash_actual:
            return False, "No fue posible validar tu contraseña actual"
        if password_hash_actual != auth_system.hash_password(password):
            return False, "La contraseña es incorrecta"

        return True, ""
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


MESES_CIERRE_EMBARQUES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


def _parse_datetime_cierre_embarques(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, dt_time.min)

    raw_value = str(value or "").strip()
    if not raw_value:
        return None

    for parser in (
        lambda raw: datetime.fromisoformat(raw.replace("Z", "+00:00")),
        lambda raw: datetime.strptime(raw, "%Y-%m-%d %H:%M:%S"),
        lambda raw: datetime.strptime(raw, "%Y-%m-%d"),
    ):
        try:
            return parser(raw_value).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _parse_month_key_cierre_embarques(value):
    match = re.match(r"^(\d{4})-(\d{2})$", str(value or "").strip())
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    return year, month


def _sumar_meses_cierre_embarques(year, month, delta):
    month_index = (year * 12) + (month - 1) + delta
    return month_index // 12, (month_index % 12) + 1


def _month_key_cierre_embarques(year, month):
    return f"{year:04d}-{month:02d}"


def _month_label_cierre_embarques(year, month):
    return f"{MESES_CIERRE_EMBARQUES[month - 1]} {year}"


def _resolver_periodo_cierre_embarques(batch=None, previous_closed_at=None, reference_at=None):
    """
    El campo closed_at marca el arranque del siguiente periodo operativo.
    El nombre del cierre debe corresponder al periodo cerrado, no al mes de closed_at.
    """
    batch = batch or {}
    closed_at = _parse_datetime_cierre_embarques(batch.get("closed_at")) or _parse_datetime_cierre_embarques(reference_at)
    if closed_at is None:
        closed_at = obtener_fecha_hora_mexico()

    previous_dt = _parse_datetime_cierre_embarques(previous_closed_at)
    raw_month = _parse_month_key_cierre_embarques(batch.get("closure_month"))

    if previous_dt:
        period_year, period_month = previous_dt.year, previous_dt.month
        period_start = previous_dt
    elif raw_month:
        period_year, period_month = raw_month
        if (
            closed_at
            and period_year == closed_at.year
            and period_month == closed_at.month
            and closed_at.day <= 7
        ):
            period_year, period_month = _sumar_meses_cierre_embarques(
                closed_at.year,
                closed_at.month,
                -1,
            )
        period_start = datetime(period_year, period_month, 1)
    else:
        period_year, period_month = closed_at.year, closed_at.month
        if closed_at.day <= 7:
            period_year, period_month = _sumar_meses_cierre_embarques(
                closed_at.year,
                closed_at.month,
                -1,
            )
        period_start = datetime(period_year, period_month, 1)

    period_end_inclusive = closed_at - timedelta(seconds=1) if closed_at else None
    month_label = _month_label_cierre_embarques(period_year, period_month)
    return {
        "closure_month": _month_key_cierre_embarques(period_year, period_month),
        "closure_month_label": month_label,
        "closure_label": f"Cierre {month_label}",
        "period_start": period_start,
        "period_end_exclusive": closed_at,
        "period_end_inclusive": period_end_inclusive,
    }


def _aplicar_metadata_periodo_cierre_embarques(payload, period_info):
    payload = payload or {}
    metadata = payload.setdefault("metadata", {})
    metadata["closureMonth"] = period_info["closure_month"]
    metadata["closureMonthLabel"] = period_info["closure_month_label"]
    metadata["closureLabel"] = period_info["closure_label"]
    return payload


def _obtener_contexto_cierre_inventario_embarques():
    fecha_actual = obtener_fecha_hora_mexico()
    latest_closure = None
    try:
        latest_closure = execute_query(
            f"""
            SELECT closed_at
            FROM `{SHIPPING_TABLES['inventory_closure_batches']}`
            WHERE status = 'confirmed'
            ORDER BY closed_at DESC, id DESC
            LIMIT 1
            """,
            fetch="one",
        )
    except Exception:
        latest_closure = None

    period_info = _resolver_periodo_cierre_embarques(
        {"closed_at": fecha_actual},
        previous_closed_at=(latest_closure or {}).get("closed_at"),
    )
    return {
        "closureDate": fecha_actual.strftime("%Y-%m-%d"),
        "closureDateTime": fecha_actual.strftime("%Y-%m-%d %H:%M:%S"),
        "closureMonth": period_info["closure_month"],
        "closureMonthLabel": period_info["closure_month_label"],
        "closureLabel": period_info["closure_label"],
        "closureUser": _obtener_usuario_display_actual(),
    }


def _normalizar_header_csv_cierre_embarques(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _construir_preview_cierre_inventario_embarques(current_rows, csv_quantities=None):
    preview_rows = []
    differing_parts = []
    negative_difference_parts = []
    matching_rows = 0
    total_rows = len(current_rows)

    csv_quantities = csv_quantities or {}

    for row in current_rows:
        part_number = _normalizar_texto_embarques_historial(row.get("part_number"))
        system_quantity = _normalizar_numero_embarques_historial(
            row.get("current_quantity")
        )
        csv_current_qty = csv_quantities.get(part_number)
        difference_qty = (
            csv_current_qty - system_quantity
            if csv_current_qty is not None
            else None
        )
        applied_initial_qty = (
            max(csv_current_qty, 0) if csv_current_qty is not None else None
        )

        if csv_current_qty is not None:
            if difference_qty == 0:
                matching_rows += 1
            else:
                differing_parts.append(part_number)
                if difference_qty < 0:
                    negative_difference_parts.append(part_number)

        preview_rows.append(
            {
                "part_number": part_number,
                "product_model": _normalizar_texto_embarques_historial(
                    row.get("product_model")
                ),
                "customer": _normalizar_texto_embarques_historial(row.get("customer")),
                "system_quantity": system_quantity,
                "csv_current_qty": csv_current_qty,
                "difference_quantity": difference_qty,
                "applied_initial_quantity": applied_initial_qty,
                "status": (
                    "pendiente"
                    if csv_current_qty is None
                    else "igual"
                    if difference_qty == 0
                    else "diferencia"
                ),
            }
        )

    accuracy_pct = (
        round((matching_rows / total_rows) * 100, 2) if total_rows and csv_quantities else 0
    )
    serializable_rows = [
        {
            "part_number": row["part_number"],
            "system_quantity": row["system_quantity"],
            "csv_current_qty": row["csv_current_qty"],
            "difference_quantity": row["difference_quantity"],
            "applied_initial_quantity": row["applied_initial_quantity"],
        }
        for row in preview_rows
    ]
    rows_hash = hashlib.sha256(
        json.dumps(
            serializable_rows,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "rows": preview_rows,
        "summary": {
            "totalRows": total_rows,
            "matchingRows": matching_rows,
            "differenceRows": len(differing_parts),
            "negativeDifferenceRows": len(negative_difference_parts),
            "accuracyPct": accuracy_pct,
            "differencePartNumbers": differing_parts,
            "negativeDifferencePartNumbers": negative_difference_parts,
            "rowsHash": rows_hash,
        },
    }


def _parsear_csv_cierre_inventario_embarques(file_storage, expected_part_numbers):
    raw_bytes = file_storage.read()
    csv_hash = hashlib.sha256(raw_bytes).hexdigest()

    try:
        decoded = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded = raw_bytes.decode("latin-1")
        except UnicodeDecodeError as exc:
            return {
                "valid": False,
                "errors": [f"No fue posible leer el CSV: {exc}"],
                "csvHash": csv_hash,
                "rows": {},
            }

    reader = csv.reader(io.StringIO(decoded))
    try:
        headers = next(reader)
    except StopIteration:
        return {
            "valid": False,
            "errors": ["El archivo CSV está vacío."],
            "csvHash": csv_hash,
            "rows": {},
        }

    normalized_headers = [_normalizar_header_csv_cierre_embarques(h) for h in headers]
    if set(normalized_headers) != {"part_number", "current_qty"} or len(normalized_headers) != 2:
        return {
            "valid": False,
            "errors": [
                "El CSV debe contener exactamente las columnas part_number y current_qty."
            ],
            "csvHash": csv_hash,
            "rows": {},
        }

    part_idx = normalized_headers.index("part_number")
    qty_idx = normalized_headers.index("current_qty")

    parsed_rows = {}
    errors = []

    for line_number, row in enumerate(reader, start=2):
        if not row or not any(str(cell or "").strip() for cell in row):
            continue

        if len(row) <= max(part_idx, qty_idx):
            errors.append(
                f"Línea {line_number}: faltan columnas requeridas para part_number y current_qty."
            )
            continue

        part_number = _normalizar_texto_embarques_historial(row[part_idx]).upper()
        qty_raw = str(row[qty_idx] or "").strip()

        if not part_number:
            errors.append(f"Línea {line_number}: part_number es obligatorio.")
            continue

        if qty_raw == "":
            errors.append(
                f"Línea {line_number}: current_qty no puede estar vacío. Usa 0 si no hay físico."
            )
            continue

        if not re.fullmatch(r"-?\d+", qty_raw):
            errors.append(
                f"Línea {line_number}: current_qty debe ser un entero para {part_number}."
            )
            continue

        current_qty = int(qty_raw)
        if current_qty < 0:
            errors.append(
                f"Línea {line_number}: current_qty no permite negativos para {part_number}."
            )
            continue

        if part_number in parsed_rows:
            errors.append(f"Línea {line_number}: part_number duplicado {part_number}.")
            continue

        parsed_rows[part_number] = current_qty

    expected_set = set(expected_part_numbers)
    uploaded_set = set(parsed_rows.keys())
    missing_parts = sorted(expected_set - uploaded_set)
    extra_parts = sorted(uploaded_set - expected_set)

    if missing_parts:
        muestra = ", ".join(missing_parts[:8])
        suffix = "..." if len(missing_parts) > 8 else ""
        errors.append(
            f"Faltan {len(missing_parts)} números de parte del catálogo completo. Ejemplo: {muestra}{suffix}"
        )

    if extra_parts:
        muestra = ", ".join(extra_parts[:8])
        suffix = "..." if len(extra_parts) > 8 else ""
        errors.append(
            f"El CSV contiene {len(extra_parts)} números de parte fuera del catálogo actual. Ejemplo: {muestra}{suffix}"
        )

    return {
        "valid": not errors,
        "errors": errors,
        "csvHash": csv_hash,
        "rows": parsed_rows,
    }


MANUAL_SHIPPING_ADJUSTMENT_CONFIG = {
    "entradas": {
        "movement_type": "entry",
        "label": "Entrada",
        "table_key": "entries",
        "folio_column": "entry_folio",
        "folio_prefix": "EMB-ENT-AJ",
        "batch_prefix": "AJ-ENT",
        "quantity_sign": 1,
        "template_filename": "plantilla_ajuste_entradas_embarques",
        "default_notes": "Ajuste manual por lote de entradas",
    },
    "salidas": {
        "movement_type": "exit",
        "label": "Salida",
        "table_key": "exits",
        "folio_column": "exit_folio",
        "folio_prefix": "EMB-SAL-AJ",
        "batch_prefix": "AJ-SAL",
        "quantity_sign": -1,
        "template_filename": "plantilla_ajuste_salidas_embarques",
        "default_notes": "Ajuste manual por lote de salidas",
    },
}


def _obtener_config_ajuste_manual_embarques(module_name):
    config = MANUAL_SHIPPING_ADJUSTMENT_CONFIG.get(
        normalize_search(module_name).lower()
    )
    if not config:
        raise ValueError("Módulo de ajuste no soportado.")
    return config


def _normalizar_fecha_movimiento_ajuste_embarques(raw_value):
    value = normalize_search(raw_value)
    if not value:
        raise ValueError("La fecha del movimiento es obligatoria.")

    normalized = value.replace("T", " ").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(normalized, fmt)
            if fmt == "%Y-%m-%d":
                return parsed.replace(hour=12, minute=0, second=0)
            return parsed.replace(microsecond=0)
        except ValueError:
            continue

    return to_sql_datetime(value)


def _primer_valor_presente(row, keys):
    for key in keys:
        if key in row and row.get(key) is not None:
            value = row.get(key)
            if not isinstance(value, str) or value.strip() != "":
                return value
    return None


def _parsear_archivo_ajuste_manual_embarques(file_storage):
    raw_bytes = file_storage.read()
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    filename = normalize_search(file_storage.filename)
    extension = Path(filename).suffix.lower()
    errors = []
    source_rows = []

    try:
        if extension in {".xlsx", ".xls"}:
            dataframe = pd.read_excel(io.BytesIO(raw_bytes), dtype=str)
            source_rows = dataframe.fillna("").to_dict("records")
        else:
            try:
                decoded = raw_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                decoded = raw_bytes.decode("latin-1")
            reader = csv.DictReader(io.StringIO(decoded))
            source_rows = list(reader)
    except Exception as exc:
        return {
            "valid": False,
            "errors": [f"No fue posible leer el archivo: {exc}"],
            "rows": [],
            "fileHash": file_hash,
        }

    if not source_rows:
        return {
            "valid": False,
            "errors": ["El archivo no contiene registros para validar."],
            "rows": [],
            "fileHash": file_hash,
        }

    parsed_rows = []
    seen_parts = set()

    for index, raw_row in enumerate(source_rows, start=2):
        normalized_row = {
            _normalizar_header_csv_cierre_embarques(key): value
            for key, value in raw_row.items()
        }
        part_number = normalize_part_number(
            _primer_valor_presente(
                normalized_row,
                ["part_number", "no_parte", "numero_parte", "part", "pn"],
            )
        )
        quantity_raw = _primer_valor_presente(
            normalized_row,
            ["quantity", "cantidad", "qty", "current_qty"],
        )
        quantity = normalize_integer(quantity_raw)

        if not part_number and quantity is None:
            continue

        if not part_number:
            errors.append(f"Línea {index}: part_number es obligatorio.")
            continue

        if quantity is None:
            errors.append(f"Línea {index}: quantity es obligatorio para {part_number}.")
            continue

        if quantity <= 0:
            errors.append(
                f"Línea {index}: quantity debe ser mayor a cero para {part_number}."
            )
            continue

        if part_number in seen_parts:
            errors.append(
                f"Línea {index}: part_number duplicado {part_number}. Deja un solo renglón por número de parte."
            )
            continue

        seen_parts.add(part_number)
        parsed_rows.append(
            {
                "rowNumber": index,
                "part_number": part_number,
                "quantity": quantity,
            }
        )

    if not parsed_rows and not errors:
        errors.append("No se encontraron renglones válidos en el archivo.")

    serializable_rows = [
        {
            "part_number": row["part_number"],
            "quantity": row["quantity"],
        }
        for row in parsed_rows
    ]
    rows_hash = hashlib.sha256(
        json.dumps(
            serializable_rows,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "valid": not errors,
        "errors": errors,
        "rows": parsed_rows,
        "fileHash": file_hash,
        "rowsHash": rows_hash,
    }


def _obtener_mapa_inventario_ajuste_manual_embarques():
    rows = execute_query(
        f"""
        SELECT
          id,
          catalog_id,
          part_number,
          current_quantity,
          product_model,
          product_status,
          description,
          customer,
          zone_code,
          standard_pack
        FROM `{SHIPPING_TABLES['inventory']}`
        WHERE part_number IS NOT NULL
          AND TRIM(part_number) <> ''
        ORDER BY part_number ASC
        """,
        fetch="all",
    ) or []
    return {normalize_part_number(row.get("part_number")): row for row in rows}


def _obtener_cierres_impactados_ajuste_manual(part_numbers, movement_at):
    normalized_parts = {normalize_part_number(part) for part in part_numbers if part}
    if not normalized_parts:
        return []

    rows = execute_query(
        f"""
        SELECT
          id,
          closure_batch_id,
          part_number,
          initial_quantity,
          system_quantity,
          difference_quantity,
          raw_current_quantity,
          closed_at,
          closure_label
        FROM `{SHIPPING_TABLES['inventory_closures']}`
        WHERE closed_at > %s
        ORDER BY closed_at ASC, id ASC
        """,
        (movement_at,),
        fetch="all",
    ) or []

    return [
        row
        for row in rows
        if normalize_part_number(row.get("part_number")) in normalized_parts
    ]


def _construir_preview_ajuste_manual_embarques(config, parsed_rows, movement_at):
    inventory_map = _obtener_mapa_inventario_ajuste_manual_embarques()
    impacted_closures = _obtener_cierres_impactados_ajuste_manual(
        [row.get("part_number") for row in parsed_rows],
        movement_at,
    )
    impacted_by_part = {}
    for closure in impacted_closures:
        impacted_by_part.setdefault(
            normalize_part_number(closure.get("part_number")),
            [],
        ).append(closure)

    errors = []
    preview_rows = []
    total_quantity = 0
    sign = int(config["quantity_sign"])

    for row in parsed_rows:
        part_number = normalize_part_number(row.get("part_number"))
        quantity = normalize_integer(row.get("quantity")) or 0
        inventory = inventory_map.get(part_number)

        if not inventory:
            errors.append(
                f"Línea {row.get('rowNumber')}: {part_number} no existe en el catálogo de embarques."
            )
            continue

        previous_quantity = normalize_integer(inventory.get("current_quantity")) or 0
        new_quantity = previous_quantity + (quantity * sign)
        closures_for_part = impacted_by_part.get(part_number, [])
        total_quantity += quantity

        preview_rows.append(
            {
                "rowNumber": row.get("rowNumber"),
                "part_number": part_number,
                "quantity": quantity,
                "current_quantity": previous_quantity,
                "new_quantity": new_quantity,
                "product_model": _normalizar_texto_embarques_historial(
                    inventory.get("product_model")
                ),
                "customer": _normalizar_texto_embarques_historial(
                    inventory.get("customer")
                ),
                "closureImpactCount": len(closures_for_part),
                "status": "impacta_cierre" if closures_for_part else "ok",
            }
        )

    closure_impact = {
        "affected": bool(impacted_closures),
        "affectedRows": len(impacted_closures),
        "affectedClosures": [
            {
                "id": closure.get("id"),
                "closureBatchId": closure.get("closure_batch_id"),
                "partNumber": _normalizar_texto_embarques_historial(
                    closure.get("part_number")
                ),
                "closureLabel": _normalizar_texto_embarques_historial(
                    closure.get("closure_label")
                ),
                "closedAt": _normalizar_texto_embarques_historial(
                    closure.get("closed_at")
                ),
            }
            for closure in impacted_closures
        ],
    }

    serializable_rows = [
        {
            "part_number": row["part_number"],
            "quantity": row["quantity"],
            "movement_type": config["movement_type"],
            "movement_at": movement_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for row in preview_rows
    ]
    rows_hash = hashlib.sha256(
        json.dumps(
            serializable_rows,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "valid": not errors and bool(preview_rows),
        "errors": errors,
        "rows": preview_rows,
        "closureImpact": closure_impact,
        "summary": {
            "totalRows": len(preview_rows),
            "totalQuantity": total_quantity,
            "rowsHash": rows_hash,
            "movementType": config["movement_type"],
            "movementAt": movement_at.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }


def _generar_batch_code_ajuste_manual_embarques(config, rows_hash):
    now = obtener_fecha_hora_mexico()
    suffix = hashlib.sha1(
        f"{rows_hash}:{now.isoformat()}".encode("utf-8")
    ).hexdigest()[:6].upper()
    return f"{config['batch_prefix']}-{now.strftime('%Y%m%d-%H%M%S')}-{suffix}"


def _guardar_preview_ajuste_manual_embarques(
    config,
    movement_at,
    reason,
    file_name,
    file_hash,
    preview_payload,
):
    conn = get_pooled_connection()
    if conn is None:
        raise RuntimeError("No fue posible obtener conexión MySQL para guardar el preview.")

    cursor = get_dict_cursor(conn)
    usuario_actual = _obtener_usuario_display_actual()
    batch_code = _generar_batch_code_ajuste_manual_embarques(
        config,
        preview_payload["summary"]["rowsHash"],
    )
    payload = {
        "metadata": {
            "batchCode": batch_code,
            "movementType": config["movement_type"],
            "movementLabel": config["label"],
            "movementAt": movement_at.strftime("%Y-%m-%d %H:%M:%S"),
            "createdBy": usuario_actual,
            "sourceFileName": file_name,
            "sourceFileHash": file_hash,
            "reason": reason,
        },
        "summary": preview_payload["summary"],
        "rows": preview_payload["rows"],
        "closureImpact": preview_payload["closureImpact"],
    }

    try:
        conn.autocommit(False)
        cursor.execute(
            f"""
            UPDATE `{SHIPPING_TABLES['manual_adjustment_batches']}`
            SET status = 'superseded',
                cancelled_at = NOW()
            WHERE movement_type = %s
              AND created_by = %s
              AND status = 'draft'
            """,
            (config["movement_type"], usuario_actual),
        )
        cursor.execute(
            f"""
            INSERT INTO `{SHIPPING_TABLES['manual_adjustment_batches']}` (
              batch_code,
              movement_type,
              movement_at,
              status,
              reason,
              created_by,
              source_file_name,
              source_file_hash,
              rows_hash,
              payload_json,
              closure_impact_json,
              total_rows,
              total_quantity
            ) VALUES (%s, %s, %s, 'draft', %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                batch_code,
                config["movement_type"],
                movement_at,
                reason,
                usuario_actual,
                file_name,
                file_hash,
                preview_payload["summary"]["rowsHash"],
                json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":")),
                json.dumps(
                    preview_payload["closureImpact"],
                    ensure_ascii=False,
                    default=str,
                    separators=(",", ":"),
                ),
                preview_payload["summary"]["totalRows"],
                preview_payload["summary"]["totalQuantity"],
            ),
        )
        batch_id = cursor.lastrowid
        for row in preview_payload["rows"]:
            cursor.execute(
                f"""
                INSERT INTO `{SHIPPING_TABLES['manual_adjustment_items']}` (
                  batch_id,
                  `row_number`,
                  part_number,
                  quantity,
                  status
                ) VALUES (%s, %s, %s, %s, 'draft')
                """,
                (
                    batch_id,
                    row.get("rowNumber"),
                    row.get("part_number"),
                    row.get("quantity"),
                ),
            )
        conn.commit()
        return batch_id, batch_code
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def _recalcular_cierres_impactados_ajuste_manual(cursor, config, movement_at, item_rows):
    sign = int(config["quantity_sign"])
    updated_closure_ids = []

    for item in item_rows:
        part_number = normalize_part_number(item.get("part_number"))
        quantity = normalize_integer(item.get("quantity")) or 0
        if not part_number or quantity <= 0:
            continue

        cursor.execute(
            f"""
            SELECT
              id,
              system_quantity,
              raw_current_quantity,
              initial_quantity
            FROM `{SHIPPING_TABLES['inventory_closures']}`
            WHERE part_number = %s
              AND closed_at > %s
            ORDER BY closed_at ASC, id ASC
            FOR UPDATE
            """,
            (part_number, movement_at),
        )
        for closure in cursor.fetchall():
            current_system = normalize_integer(closure.get("system_quantity"))
            if current_system is None:
                current_system = normalize_integer(closure.get("initial_quantity")) or 0
            new_system = current_system + (quantity * sign)
            raw_current = normalize_integer(closure.get("raw_current_quantity"))
            if raw_current is None:
                raw_current = normalize_integer(closure.get("initial_quantity")) or 0
            difference = raw_current - new_system
            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['inventory_closures']}`
                SET system_quantity = %s,
                    difference_quantity = %s
                WHERE id = %s
                """,
                (new_system, difference, closure.get("id")),
            )
            updated_closure_ids.append(closure.get("id"))

    return updated_closure_ids


def _confirmar_ajuste_manual_embarques(config, batch_id):
    conn = get_pooled_connection()
    if conn is None:
        raise RuntimeError("No fue posible obtener conexión MySQL para confirmar el lote.")

    cursor = get_dict_cursor(conn)
    usuario_actual = _obtener_usuario_display_actual()
    inserted_records = []
    rebuild_parts = set()

    try:
        conn.autocommit(False)
        cursor.execute(
            f"""
            SELECT *
            FROM `{SHIPPING_TABLES['manual_adjustment_batches']}`
            WHERE id = %s
              AND movement_type = %s
            LIMIT 1
            FOR UPDATE
            """,
            (batch_id, config["movement_type"]),
        )
        batch = cursor.fetchone()
        if not batch:
            conn.rollback()
            return {"success": False, "error": "No se encontró el lote solicitado."}, 404

        if normalize_search(batch.get("status")).lower() != "draft":
            conn.rollback()
            return {
                "success": False,
                "error": "El lote ya no está disponible para confirmar.",
            }, 409

        cursor.execute(
            f"""
            SELECT *
            FROM `{SHIPPING_TABLES['manual_adjustment_items']}`
            WHERE batch_id = %s
            ORDER BY `row_number` ASC, id ASC
            FOR UPDATE
            """,
            (batch_id,),
        )
        item_rows = cursor.fetchall()
        if not item_rows:
            conn.rollback()
            return {"success": False, "error": "El lote no contiene registros."}, 400

        movement_at = to_sql_datetime(batch.get("movement_at"))
        reason = normalize_search(batch.get("reason"))

        for item in item_rows:
            part_number = normalize_part_number(item.get("part_number"))
            quantity = normalize_integer(item.get("quantity")) or 0
            inventory = ensure_inventory_record(cursor, part_number)
            if not inventory:
                conn.rollback()
                return {
                    "success": False,
                    "error": f"{part_number} ya no existe en el catálogo de embarques.",
                }, 404

            folio = generate_movement_folio(config["folio_prefix"])
            catalog_id = inventory.get("catalog_id") or inventory.get("catalog_ref_id")
            inventory_id = inventory.get("id")
            product_model = inventory.get("product_model") or inventory.get("catalog_model")
            description = inventory.get("description") or inventory.get("catalog_description")
            customer = inventory.get("customer") or inventory.get("catalog_customer")
            zone_code = inventory.get("zone_code") or inventory.get("catalog_zone_code")
            notes = f"{config['default_notes']} {batch.get('batch_code')}: {reason}"

            if config["movement_type"] == "entry":
                cursor.execute(
                    f"""
                    INSERT INTO `{SHIPPING_TABLES['entries']}` (
                      entry_folio,
                      inventory_id,
                      catalog_id,
                      part_number,
                      quantity,
                      available_quantity,
                      is_fifo_layer_only,
                      previous_quantity,
                      new_quantity,
                      product_model,
                      description,
                      customer,
                      zone_code,
                      location_code,
                      reference_code,
                      batch_no,
                      notes,
                      registered_by,
                      movement_at
                    ) VALUES (%s, %s, %s, %s, %s, 0, 0, 0, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        folio,
                        inventory_id,
                        catalog_id,
                        part_number,
                        quantity,
                        product_model,
                        description,
                        customer,
                        zone_code,
                        None,
                        f"AJUSTE:{batch.get('batch_code')}",
                        None,
                        notes,
                        usuario_actual,
                        movement_at,
                    ),
                )
            else:
                cursor.execute(
                    f"""
                    INSERT INTO `{SHIPPING_TABLES['exits']}` (
                      exit_folio,
                      inventory_id,
                      catalog_id,
                      part_number,
                      quantity,
                      previous_quantity,
                      new_quantity,
                      product_model,
                      description,
                      customer,
                      zone_code,
                      location_code,
                      fifo_allocation_json,
                      destination_area,
                      departure_code,
                      departure_assigned_at,
                      departure_assigned_by,
                      reason,
                      requested_by,
                      remarks,
                      registered_by,
                      movement_at
                    ) VALUES (%s, %s, %s, %s, %s, 0, 0, %s, %s, %s, %s, %s, NULL, %s, NULL, NULL, NULL, %s, %s, %s, %s, %s)
                    """,
                    (
                        folio,
                        inventory_id,
                        catalog_id,
                        part_number,
                        quantity,
                        product_model,
                        description,
                        customer,
                        zone_code,
                        None,
                        "Embarques",
                        "Ajuste manual de salida",
                        usuario_actual,
                        notes,
                        usuario_actual,
                        movement_at,
                    ),
                )

            inserted_records.append(
                {
                    "item_id": item.get("id"),
                    "part_number": part_number,
                    "quantity": quantity,
                    "folio": folio,
                    "inventory_id": inventory_id,
                    "catalog_id": catalog_id,
                }
            )
            rebuild_parts.add(part_number)

        for part_number in sorted(rebuild_parts):
            rebuild_part_inventory_state(cursor, part_number)

        table_name = SHIPPING_TABLES[config["table_key"]]
        folio_column = config["folio_column"]
        for record in inserted_records:
            cursor.execute(
                f"""
                SELECT previous_quantity, new_quantity
                FROM `{table_name}`
                WHERE `{folio_column}` = %s
                LIMIT 1
                """,
                (record["folio"],),
            )
            movement_row = cursor.fetchone() or {}
            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['manual_adjustment_items']}`
                SET inventory_id = %s,
                    catalog_id = %s,
                    folio = %s,
                    previous_quantity = %s,
                    new_quantity = %s,
                    status = 'applied'
                WHERE id = %s
                """,
                (
                    record.get("inventory_id"),
                    record.get("catalog_id"),
                    record.get("folio"),
                    normalize_integer(movement_row.get("previous_quantity")) or 0,
                    normalize_integer(movement_row.get("new_quantity")) or 0,
                    record.get("item_id"),
                ),
            )

        updated_closure_ids = _recalcular_cierres_impactados_ajuste_manual(
            cursor,
            config,
            movement_at,
            item_rows,
        )

        cursor.execute(
            f"""
            UPDATE `{SHIPPING_TABLES['manual_adjustment_batches']}`
            SET status = 'applied',
                confirmed_by = %s,
                confirmed_at = NOW()
            WHERE id = %s
            """,
            (usuario_actual, batch_id),
        )

        conn.commit()
        return {
            "success": True,
            "batchId": batch_id,
            "batchCode": batch.get("batch_code"),
            "movementType": config["movement_type"],
            "insertedRows": len(inserted_records),
            "updatedClosureRows": len(updated_closure_ids),
            "message": "Lote aplicado correctamente.",
        }, 200
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def _registrar_ajuste_manual_individual_embarques(config, data):
    part_number = normalize_part_number(data.get("partNumber") or data.get("part_number"))
    quantity = normalize_integer(data.get("quantity"))
    reason = normalize_search(data.get("reason"))
    movement_at = _normalizar_fecha_movimiento_ajuste_embarques(data.get("movementAt"))

    if not part_number:
        return {"success": False, "error": "El número de parte es obligatorio."}, 400
    if quantity is None or quantity <= 0:
        return {"success": False, "error": "La cantidad debe ser mayor a cero."}, 400
    if not reason:
        return {"success": False, "error": "El motivo del registro es obligatorio."}, 400

    parsed_rows = [
        {
            "rowNumber": 1,
            "part_number": part_number,
            "quantity": quantity,
        }
    ]
    preview = _construir_preview_ajuste_manual_embarques(
        config,
        parsed_rows,
        movement_at,
    )
    if not preview["valid"]:
        return {
            "success": False,
            "error": "; ".join(preview.get("errors") or ["No fue posible validar el registro."]),
            "preview": preview,
        }, 400

    manual_hash = hashlib.sha256(
        json.dumps(
            {
                "movementType": config["movement_type"],
                "movementAt": movement_at.strftime("%Y-%m-%d %H:%M:%S"),
                "partNumber": part_number,
                "quantity": quantity,
                "reason": reason,
                "createdBy": _obtener_usuario_display_actual(),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    batch_id, _batch_code = _guardar_preview_ajuste_manual_embarques(
        config,
        movement_at,
        reason,
        "registro_manual",
        manual_hash,
        preview,
    )
    return _confirmar_ajuste_manual_embarques(config, batch_id)


def _guardar_borrador_cierre_inventario_embarques(payload, csv_file_name, csv_hash):
    conn = get_pooled_connection()
    if conn is None:
        raise RuntimeError("No fue posible obtener conexión MySQL para guardar el borrador.")

    cursor = get_dict_cursor(conn)
    try:
        conn.autocommit(False)
        cursor.execute(
            f"""
            UPDATE `{SHIPPING_TABLES['inventory_closure_batches']}`
            SET status = 'superseded'
            WHERE status = 'draft'
              AND created_by = %s
              AND closure_month = %s
            """,
            (payload["metadata"]["closureUser"], payload["metadata"]["closureMonth"]),
        )
        cursor.execute(
            f"""
            INSERT INTO `{SHIPPING_TABLES['inventory_closure_batches']}` (
              closure_label,
              closure_month,
              closed_at,
              status,
              created_by,
              csv_file_name,
              csv_hash,
              rows_hash,
              payload_json,
              accuracy_pct,
              total_rows,
              differing_rows
            ) VALUES (%s, %s, %s, 'draft', %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                payload["metadata"]["closureLabel"],
                payload["metadata"]["closureMonth"],
                payload["metadata"]["closureDateTime"],
                payload["metadata"]["closureUser"],
                csv_file_name,
                csv_hash,
                payload["summary"]["rowsHash"],
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                payload["summary"]["accuracyPct"],
                payload["summary"]["totalRows"],
                payload["summary"]["differenceRows"],
            ),
        )
        batch_id = cursor.lastrowid
        conn.commit()
        return batch_id
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def _obtener_historial_cierres_inventario_embarques(limit=20, include_last_draft_for=None):
    rows = execute_query(
        f"""
        SELECT
          id,
          closure_label,
          closure_month,
          status,
          created_by,
          confirmed_by,
          closed_at,
          confirmed_at,
          accuracy_pct,
          total_rows,
          differing_rows,
          csv_hash,
          rows_hash
        FROM `{SHIPPING_TABLES['inventory_closure_batches']}`
        WHERE status = 'confirmed'
        ORDER BY COALESCE(confirmed_at, created_at) DESC, id DESC
        LIMIT %s
        """,
        (limit,),
        fetch="all",
    ) or []

    if include_last_draft_for:
        draft_row = execute_query(
            f"""
            SELECT
              id,
              closure_label,
              closure_month,
              status,
              created_by,
              confirmed_by,
              closed_at,
              confirmed_at,
              accuracy_pct,
              total_rows,
              differing_rows,
              csv_hash,
              rows_hash
            FROM `{SHIPPING_TABLES['inventory_closure_batches']}`
            WHERE status = 'draft'
              AND created_by = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (include_last_draft_for,),
            fetch="one",
        )
        if draft_row:
            rows.insert(0, draft_row)

    history_rows = []
    for row in rows:
        period_info = _resolver_periodo_cierre_embarques(row)
        history_rows.append(
            {
                "id": row.get("id"),
                "closure_label": period_info["closure_label"],
                "closure_month": period_info["closure_month"],
                "status": _normalizar_texto_embarques_historial(row.get("status")),
                "created_by": _normalizar_texto_embarques_historial(row.get("created_by")),
                "confirmed_by": _normalizar_texto_embarques_historial(row.get("confirmed_by")),
                "closed_at": _normalizar_texto_embarques_historial(row.get("closed_at")),
                "confirmed_at": _normalizar_texto_embarques_historial(row.get("confirmed_at")),
                "accuracy_pct": _normalizar_numero_embarques_historial(row.get("accuracy_pct")),
                "total_rows": _normalizar_numero_embarques_historial(row.get("total_rows")),
                "differing_rows": _normalizar_numero_embarques_historial(row.get("differing_rows")),
                "csv_hash": _normalizar_texto_embarques_historial(row.get("csv_hash")),
                "rows_hash": _normalizar_texto_embarques_historial(row.get("rows_hash")),
            }
        )
    return history_rows


def _agregar_timestamp_nombre_archivo(filename):
    stem, extension = os.path.splitext(filename)
    timestamp = obtener_fecha_hora_mexico().strftime("%y%m%d_%H%M%S")
    return f"{stem}_{timestamp}{extension}"


def _exportar_historial_embarques_excel(sheet_name, filename, headers, rows):
    """Generar archivo Excel para cualquiera de los historiales de embarques."""
    from io import BytesIO

    from flask import Response
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    header_fill = PatternFill(
        start_color="1F4E79", end_color="1F4E79", fill_type="solid"
    )
    header_font = Font(color="FFFFFF", bold=True)

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for row_idx, row in enumerate(rows, 2):
        for col_idx, key in enumerate(headers.values(), 1):
            ws.cell(row=row_idx, column=col_idx, value=row.get(key, ""))

    for column_cells in ws.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            cell.alignment = Alignment(vertical="top")
            value_length = len(str(cell.value or ""))
            if value_length > max_length:
                max_length = value_length
        ws.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 28)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    download_filename = _agregar_timestamp_nombre_archivo(filename)

    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'},
    )


def _parse_fecha_control_salida_lineas(value, fallback):
    """Parsear fechas de filtros del modulo Control de salida de lineas."""
    try:
        return datetime.strptime(str(value or "").strip(), "%Y-%m-%d").date()
    except Exception:
        return fallback


def _calcular_estado_control_salida_lineas(produccion, oqc, almacen):
    if produccion == 0 and oqc == 0 and almacen > 0:
        return "Solo almacen"
    if oqc > produccion or almacen > oqc:
        return "Revisar"
    if produccion > 0 and oqc >= produccion and almacen >= oqc:
        return "Completo"
    if oqc < produccion:
        return "Pendiente OQC"
    if almacen < oqc:
        return "Pendiente almacen"
    return "Sin datos"


def _obtener_control_salida_lineas(limit=500):
    """Consultar produccion, liberacion OQC y entradas, acumuladas por parte en el rango."""
    today = date.today()
    default_from = today - timedelta(days=7)
    fecha_desde = _parse_fecha_control_salida_lineas(
        request.args.get("fecha_desde"),
        default_from,
    )
    fecha_hasta = _parse_fecha_control_salida_lineas(
        request.args.get("fecha_hasta"),
        today,
    )
    if fecha_hasta < fecha_desde:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    fecha_inicio_sql = fecha_desde.strftime("%Y-%m-%d")
    fecha_fin_sql = (fecha_hasta + timedelta(days=1)).strftime("%Y-%m-%d")
    part_number = (request.args.get("part_number", "") or "").strip()
    part_like = f"%{part_number}%"
    output_collation = "utf8mb4_0900_ai_ci"

    production_part_expr = (
        "COALESCE(NULLIF(p.part_no, ''), "
        "NULLIF(LEFT(b.serial, GREATEST(CHAR_LENGTH(b.serial) - 12, 1)), ''), "
        "'SIN PARTE')"
    )
    production_model_expr = "COALESCE(NULLIF(p.model_code, ''), '')"
    oqc_part_expr = "COALESCE(NULLIF(pn.part_number, ''), CONCAT('ID-', er.part_number_id))"
    oqc_model_expr = "COALESCE(NULLIF(pn.model, ''), '')"
    entry_part_expr = "COALESCE(NULLIF(e.part_number, ''), 'SIN PARTE')"
    entry_model_expr = "COALESCE(NULLIF(e.product_model, ''), '')"
    production_part_select = f"({production_part_expr}) COLLATE {output_collation}"
    production_model_select = f"({production_model_expr}) COLLATE {output_collation}"
    oqc_part_select = f"({oqc_part_expr}) COLLATE {output_collation}"
    oqc_model_select = f"({oqc_model_expr}) COLLATE {output_collation}"
    entry_part_select = f"({entry_part_expr}) COLLATE {output_collation}"
    entry_model_select = f"({entry_model_expr}) COLLATE {output_collation}"
    empty_text_select = f"'' COLLATE {output_collation}"

    production_where = ["b.last_scan >= %s", "b.last_scan < %s"]
    production_params = [fecha_inicio_sql, fecha_fin_sql]
    oqc_where = [
        "COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME)) >= %s",
        "COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME)) < %s",
        "COALESCE(er.status, '') <> 'cancelled'",
        "COALESCE(er.qc_passed, 1) = 1",
    ]
    oqc_params = [fecha_inicio_sql, fecha_fin_sql]
    entry_where = [
        "COALESCE(e.movement_at, e.created_at) >= %s",
        "COALESCE(e.movement_at, e.created_at) < %s",
        "COALESCE(e.is_fifo_layer_only, 0) = 0",
    ]
    entry_params = [fecha_inicio_sql, fecha_fin_sql]

    if part_number:
        production_where.append(f"{production_part_select} LIKE %s")
        production_params.append(part_like)
        oqc_where.append(f"COALESCE(pn.part_number, '') COLLATE {output_collation} LIKE %s")
        oqc_params.append(part_like)
        entry_where.append(f"e.part_number COLLATE {output_collation} LIKE %s")
        entry_params.append(part_like)

    sql = f"""
        SELECT
            MIN(fuente.fecha) AS fecha_inicio,
            MAX(fuente.fecha) AS fecha_fin,
            fuente.part_number,
            MAX(NULLIF(fuente.product_model, '')) AS product_model,
            SUM(fuente.produced_quantity) AS produced_quantity,
            SUM(fuente.production_boxes) AS production_boxes,
            SUM(fuente.oqc_quantity) AS oqc_quantity,
            SUM(fuente.oqc_records) AS oqc_records,
            SUM(fuente.warehouse_quantity) AS warehouse_quantity,
            SUM(fuente.warehouse_records) AS warehouse_records,
            GROUP_CONCAT(DISTINCT NULLIF(fuente.lineas, '') ORDER BY fuente.lineas SEPARATOR ', ') AS lineas,
            GROUP_CONCAT(DISTINCT NULLIF(fuente.lotes, '') ORDER BY fuente.lotes SEPARATOR ', ') AS lotes,
            GROUP_CONCAT(DISTINCT NULLIF(fuente.oqc_statuses, '') ORDER BY fuente.oqc_statuses SEPARATOR ', ') AS oqc_statuses
        FROM (
            SELECT
                DATE(b.last_scan) AS fecha,
                {production_part_select} AS part_number,
                MAX({production_model_select}) AS product_model,
                COUNT(*) AS produced_quantity,
                COUNT(DISTINCT NULLIF(b.box_code, '')) AS production_boxes,
                0 AS oqc_quantity,
                0 AS oqc_records,
                0 AS warehouse_quantity,
                0 AS warehouse_records,
                (GROUP_CONCAT(DISTINCT NULLIF(p.line, '') ORDER BY p.line SEPARATOR ', ')) COLLATE {output_collation} AS lineas,
                (GROUP_CONCAT(DISTINCT NULLIF(b.lot_no, '') ORDER BY b.lot_no SEPARATOR ', ')) COLLATE {output_collation} AS lotes,
                {empty_text_select} AS oqc_statuses
            FROM box_scans b
            LEFT JOIN plan_main p ON p.lot_no = b.lot_no
            WHERE {" AND ".join(production_where)}
            GROUP BY DATE(b.last_scan), {production_part_select}

            UNION ALL

            SELECT
                DATE(COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME))) AS fecha,
                {oqc_part_select} AS part_number,
                MAX({oqc_model_select}) AS product_model,
                0 AS produced_quantity,
                0 AS production_boxes,
                SUM(er.quantity) AS oqc_quantity,
                COUNT(*) AS oqc_records,
                0 AS warehouse_quantity,
                0 AS warehouse_records,
                {empty_text_select} AS lineas,
                {empty_text_select} AS lotes,
                (GROUP_CONCAT(DISTINCT COALESCE(er.status, 'pending') ORDER BY er.status SEPARATOR ', ')) COLLATE {output_collation} AS oqc_statuses
            FROM exit_records er
            LEFT JOIN part_numbers pn ON pn.id = er.part_number_id
            WHERE {" AND ".join(oqc_where)}
            GROUP BY DATE(COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME))), {oqc_part_select}

            UNION ALL

            SELECT
                DATE(COALESCE(e.movement_at, e.created_at)) AS fecha,
                {entry_part_select} AS part_number,
                MAX({entry_model_select}) AS product_model,
                0 AS produced_quantity,
                0 AS production_boxes,
                0 AS oqc_quantity,
                0 AS oqc_records,
                SUM(e.quantity) AS warehouse_quantity,
                COUNT(*) AS warehouse_records,
                {empty_text_select} AS lineas,
                {empty_text_select} AS lotes,
                {empty_text_select} AS oqc_statuses
            FROM embarques_entrada_material e
            WHERE {" AND ".join(entry_where)}
            GROUP BY DATE(COALESCE(e.movement_at, e.created_at)), {entry_part_select}
        ) fuente
        WHERE COALESCE(fuente.part_number, '') <> ''
        GROUP BY fuente.part_number
        ORDER BY fecha_fin DESC, fuente.part_number
        LIMIT %s
    """
    params = production_params + oqc_params + entry_params + [int(limit)]
    rows = execute_query(sql, tuple(params), fetch="all") or []

    result_rows = []
    summary = {
        "produced_quantity": 0,
        "production_boxes": 0,
        "oqc_quantity": 0,
        "oqc_records": 0,
        "warehouse_quantity": 0,
        "warehouse_records": 0,
        "pending_oqc": 0,
        "pending_warehouse": 0,
    }
    for row in rows:
        part = _normalizar_texto_embarques_historial(row.get("part_number"))
        produced = int(row.get("produced_quantity") or 0)
        production_boxes = int(row.get("production_boxes") or 0)
        oqc = int(row.get("oqc_quantity") or 0)
        oqc_records = int(row.get("oqc_records") or 0)
        warehouse = int(row.get("warehouse_quantity") or 0)
        warehouse_records = int(row.get("warehouse_records") or 0)
        pending_oqc = max(produced - oqc, 0)
        pending_warehouse = max(oqc - warehouse, 0)
        if pending_oqc > 0:
            estado = "Pendiente OQC"
        elif pending_warehouse > 0:
            estado = "Pendiente almacen"
        else:
            estado = _calcular_estado_control_salida_lineas(produced, oqc, warehouse)
        fecha_inicio = _normalizar_texto_embarques_historial(row.get("fecha_inicio"))
        fecha_fin = _normalizar_texto_embarques_historial(row.get("fecha_fin"))
        fecha_periodo = (
            fecha_inicio
            if fecha_inicio == fecha_fin or not fecha_fin
            else f"{fecha_inicio} a {fecha_fin}"
        )

        summary["produced_quantity"] += produced
        summary["production_boxes"] += production_boxes
        summary["oqc_quantity"] += oqc
        summary["oqc_records"] += oqc_records
        summary["warehouse_quantity"] += warehouse
        summary["warehouse_records"] += warehouse_records
        summary["pending_oqc"] += pending_oqc
        summary["pending_warehouse"] += pending_warehouse

        result_rows.append(
            {
                "fecha": fecha_periodo,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "part_number": part,
                "product_model": _normalizar_texto_embarques_historial(row.get("product_model")),
                "lineas": _normalizar_texto_embarques_historial(row.get("lineas")),
                "lotes": _normalizar_texto_embarques_historial(row.get("lotes")),
                "produced_quantity": produced,
                "production_boxes": production_boxes,
                "oqc_quantity": oqc,
                "oqc_records": oqc_records,
                "warehouse_quantity": warehouse,
                "warehouse_records": warehouse_records,
                "pending_oqc": pending_oqc,
                "pending_warehouse": pending_warehouse,
                "produced_cutoff": produced,
                "oqc_cutoff": oqc,
                "warehouse_cutoff": warehouse,
                "oqc_statuses": _normalizar_texto_embarques_historial(row.get("oqc_statuses")),
                "estado": estado,
            }
        )

    return {
        "rows": result_rows,
        "summary": summary,
        "filters": {
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "part_number": part_number,
        },
    }


def _texto_pdf_embarques(value, fallback="-"):
    """Normalizar texto para documentos PDF de embarques."""
    text = str(value if value is not None else "").strip()
    return text or fallback


def _cantidad_pdf_salidas_retorno(row):
    """Obtener la cantidad imprimible de una salida de retorno."""
    for key in ("movement_quantity", "loss_quantity", "quantity", "cantidad"):
        value = row.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0
    return 0


def _formatear_numero_pdf_embarques(value):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "0"
    if numeric_value.is_integer():
        return f"{int(numeric_value):,}"
    return f"{numeric_value:,.2f}".rstrip("0").rstrip(".")


def _tipo_retorno_pdf_embarques(reason):
    text = _texto_pdf_embarques(reason, "Retorno")
    return text.split("/")[0].strip() or "Retorno"


def _normalizar_filas_pdf_salidas_retorno(rows):
    normalized_rows = []
    for raw_row in rows[:1000]:
        if not isinstance(raw_row, dict):
            continue
        quantity = _cantidad_pdf_salidas_retorno(raw_row)
        if quantity <= 0:
            continue
        normalized_rows.append(
            {
                "fecha": _texto_pdf_embarques(raw_row.get("fecha")),
                "hora": _texto_pdf_embarques(raw_row.get("hora")),
                "folio": _texto_pdf_embarques(raw_row.get("folio")),
                "part_number": _texto_pdf_embarques(raw_row.get("part_number")),
                "quantity": quantity,
                "product_model": _texto_pdf_embarques(raw_row.get("product_model")),
                "reason": _tipo_retorno_pdf_embarques(raw_row.get("reason")),
                "registered_by": _texto_pdf_embarques(raw_row.get("registered_by")),
            }
        )

    return sorted(
        normalized_rows,
        key=lambda row: (
            row["part_number"].lower(),
            row["folio"].lower(),
            row["fecha"],
            row["hora"],
        ),
    )


def _pdf_escape_text_embarques(value):
    """Escapar texto para una cadena PDF WinAnsi sin dependencias externas."""
    encoded = _texto_pdf_embarques(value).encode("cp1252", "replace")
    escaped = bytearray()
    for byte in encoded:
        if byte in (40, 41, 92):  # (, ), \
            escaped.append(92)
            escaped.append(byte)
        elif byte in (10, 13, 9):
            escaped.append(32)
        else:
            escaped.append(byte)
    return escaped.decode("latin-1")


def _pdf_color_embarques(hex_color):
    color = hex_color.strip().lstrip("#")
    if len(color) != 6:
        return (0, 0, 0)
    return tuple(int(color[index : index + 2], 16) / 255 for index in (0, 2, 4))


def _pdf_cmd_color_embarques(hex_color, stroke=False):
    r, g, b = _pdf_color_embarques(hex_color)
    operator = "RG" if stroke else "rg"
    return f"{r:.3f} {g:.3f} {b:.3f} {operator}"


def _pdf_text_width_embarques(text, font_size, bold=False):
    factor = 0.56 if bold else 0.50
    return len(str(text)) * font_size * factor


def _pdf_fit_text_embarques(text, font_size, max_width, bold=False):
    text = _texto_pdf_embarques(text)
    if _pdf_text_width_embarques(text, font_size, bold) <= max_width:
        return text

    ellipsis = "..."
    available = max_width - _pdf_text_width_embarques(ellipsis, font_size, bold)
    if available <= 0:
        return ""

    fitted = text
    while fitted and _pdf_text_width_embarques(fitted, font_size, bold) > available:
        fitted = fitted[:-1]
    return f"{fitted}{ellipsis}" if fitted else ellipsis


def _pdf_rect_embarques(x, y, width, height, page_height, fill="#ffffff", stroke="#cfd6e4", line_width=0.5):
    pdf_y = page_height - y - height
    commands = [
        f"q {_pdf_cmd_color_embarques(fill)} {x:.2f} {pdf_y:.2f} {width:.2f} {height:.2f} re f Q",
    ]
    if stroke:
        commands.append(
            f"q {_pdf_cmd_color_embarques(stroke, stroke=True)} {line_width:.2f} w "
            f"{x:.2f} {pdf_y:.2f} {width:.2f} {height:.2f} re S Q"
        )
    return "\n".join(commands)


def _pdf_line_embarques(x1, y1, x2, y2, page_height, stroke="#11213c", line_width=1):
    return (
        f"q {_pdf_cmd_color_embarques(stroke, stroke=True)} {line_width:.2f} w "
        f"{x1:.2f} {page_height - y1:.2f} m {x2:.2f} {page_height - y2:.2f} l S Q"
    )


def _pdf_text_embarques(
    x,
    y,
    text,
    page_height,
    font_size=8,
    font="F1",
    fill="#162033",
    max_width=None,
    align="left",
    bold=False,
):
    safe_text = _texto_pdf_embarques(text)
    if max_width is not None:
        safe_text = _pdf_fit_text_embarques(safe_text, font_size, max_width, bold)
    text_width = _pdf_text_width_embarques(safe_text, font_size, bold)
    if align == "right" and max_width is not None:
        text_x = x + max(max_width - text_width, 0)
    elif align == "center" and max_width is not None:
        text_x = x + max((max_width - text_width) / 2, 0)
    else:
        text_x = x
    pdf_y = page_height - y
    escaped_text = _pdf_escape_text_embarques(safe_text)
    return (
        f"q {_pdf_cmd_color_embarques(fill)} BT /{font} {font_size:.2f} Tf "
        f"1 0 0 1 {text_x:.2f} {pdf_y:.2f} Tm ({escaped_text}) Tj ET Q"
    )


def _pdf_cell_text_embarques(x, y, width, height, text, page_height, font_size=7, font="F1", fill="#162033", align="left", bold=False):
    text_x = x + 4
    text_y = y + (height / 2) + (font_size / 2) - 1.5
    return _pdf_text_embarques(
        text_x,
        text_y,
        text,
        page_height,
        font_size=font_size,
        font=font,
        fill=fill,
        max_width=max(width - 8, 5),
        align=align,
        bold=bold,
    )


def _crear_pdf_embarques(page_streams, page_width=792, page_height=612):
    """Crear un PDF mínimo con fuentes Helvetica estándar."""
    objects = [
        None,
        None,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    pages_id = 2
    font_regular_id = 3
    font_bold_id = 4
    page_ids = []

    def add_object(payload):
        objects.append(payload)
        return len(objects)

    for stream in page_streams:
        stream_bytes = stream.encode("latin-1", "replace")
        content_id = add_object(
            b"<< /Length "
            + str(len(stream_bytes)).encode("ascii")
            + b" >>\nstream\n"
            + stream_bytes
            + b"\nendstream"
        )
        page_id = add_object(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_width} {page_height}] "
                f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        page_ids.append(page_id)

    objects[0] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")

    output = io.BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, payload in enumerate(objects, 1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("ascii"))
        output.write(payload)
        output.write(b"\nendobj\n")

    xref_offset = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    output.seek(0)
    return output


def _generar_pdf_salidas_retorno_embarques(rows):
    """Generar PDF carta horizontal para el formato de salidas de retorno sin dependencias externas."""
    normalized_rows = _normalizar_filas_pdf_salidas_retorno(rows)
    if not normalized_rows:
        raise ValueError("No hay salidas de retorno válidas para generar el PDF.")

    page_width = 792
    page_height = 612
    margin_x = 30
    margin_y = 52
    table_top = margin_y + 122
    row_height = 14
    table_header_height = 17
    footer_reserved = 56
    table_bottom = page_height - margin_y - footer_reserved
    navy = "#11213c"
    gray = "#63708a"
    border = "#cfd6e4"
    row_alt = "#f4f7fb"
    white = "#ffffff"
    black = "#162033"

    columns = [
        ("Fecha", "fecha", 58, "left"),
        ("Hora", "hora", 44, "left"),
        ("Folio", "folio", 162, "left"),
        ("No. parte", "part_number", 95, "left"),
        ("Cantidad", "quantity", 50, "right"),
        ("Modelo", "product_model", 168, "left"),
        ("Tipo", "reason", 60, "left"),
        ("Usuario", "registered_by", 95, "left"),
    ]
    available_width = page_width - (margin_x * 2)
    total_width = sum(column[2] for column in columns)
    if total_width < available_width:
        extra_width = available_width - total_width
        columns[5] = (columns[5][0], columns[5][1], columns[5][2] + extra_width, columns[5][3])

    rows_per_page = max(1, int((table_bottom - table_top - table_header_height) / row_height))
    total_pages = max(1, (len(normalized_rows) + rows_per_page - 1) // rows_per_page)
    total_quantity = sum(row["quantity"] for row in normalized_rows)
    generated_at = obtener_fecha_hora_mexico().strftime("%d/%m/%Y, %I:%M %p").replace("AM", "a.m.").replace("PM", "p.m.")

    page_streams = []
    for page_index in range(total_pages):
        page_rows = normalized_rows[
            page_index * rows_per_page : (page_index + 1) * rows_per_page
        ]
        commands = []

        commands.append(_pdf_text_embarques(margin_x, margin_y, "ALMACÉN DE EMBARQUES", page_height, 8, "F2", gray, bold=True))
        commands.append(_pdf_text_embarques(margin_x, margin_y + 22, "SALIDA DE RETORNO", page_height, 20, "F2", navy, bold=True))
        commands.append(_pdf_text_embarques(page_width - margin_x - 58, margin_y, "GENERADO", page_height, 7, "F2", gray, bold=True))
        commands.append(_pdf_text_embarques(page_width - margin_x - 112, margin_y + 18, generated_at, page_height, 8, "F2", black, bold=True))
        commands.append(
            _pdf_text_embarques(
                page_width - margin_x - 42,
                margin_y + 34,
                f"Pág. {page_index + 1}/{total_pages}",
                page_height,
                7,
                "F2",
                gray,
                bold=True,
            )
        )
        commands.append(_pdf_line_embarques(margin_x, margin_y + 50, page_width - margin_x, margin_y + 50, page_height, navy, 1.5))

        summary_top = margin_y + 64
        summary_width = (available_width - 8) / 2
        for offset, label, value in (
            (0, "REGISTROS", _formatear_numero_pdf_embarques(len(normalized_rows))),
            (summary_width + 8, "CANTIDAD TOTAL", _formatear_numero_pdf_embarques(total_quantity)),
        ):
            x = margin_x + offset
            commands.append(_pdf_rect_embarques(x, summary_top, summary_width, 36, page_height, white, border, 0.6))
            commands.append(_pdf_text_embarques(x + 8, summary_top + 12, label, page_height, 6.5, "F2", gray, bold=True))
            commands.append(_pdf_text_embarques(x + 8, summary_top + 28, value, page_height, 12, "F2", navy, bold=True))

        x = margin_x
        y = table_top
        for label, _key, width, align in columns:
            commands.append(_pdf_rect_embarques(x, y, width, table_header_height, page_height, navy, navy, 0.4))
            commands.append(
                _pdf_cell_text_embarques(
                    x,
                    y,
                    width,
                    table_header_height,
                    label,
                    page_height,
                    6.2,
                    "F2",
                    white,
                    align,
                    True,
                )
            )
            x += width

        y += table_header_height
        for row_index, row in enumerate(page_rows):
            x = margin_x
            row_fill = row_alt if row_index % 2 else white
            for _label, key, width, align in columns:
                commands.append(_pdf_rect_embarques(x, y, width, row_height, page_height, row_fill, border, 0.35))
                value = _formatear_numero_pdf_embarques(row[key]) if key == "quantity" else row[key]
                is_bold = key == "part_number"
                commands.append(
                    _pdf_cell_text_embarques(
                        x,
                        y,
                        width,
                        row_height,
                        value,
                        page_height,
                        5.8,
                        "F2" if is_bold else "F1",
                        black,
                        align,
                        is_bold,
                    )
                )
                x += width
            y += row_height

        footer_y = page_height - margin_y - 30
        signature_width = (available_width - 60) / 3
        for index, label in enumerate(("Entrega", "Recibe", "Validación")):
            x = margin_x + index * (signature_width + 30)
            commands.append(_pdf_line_embarques(x, footer_y, x + signature_width, footer_y, page_height, navy, 0.7))
            commands.append(
                _pdf_text_embarques(
                    x,
                    footer_y + 12,
                    label,
                    page_height,
                    7,
                    "F1",
                    gray,
                    max_width=signature_width,
                    align="center",
                )
            )

        page_streams.append("\n".join(commands))

    return _crear_pdf_embarques(page_streams, page_width=page_width, page_height=page_height)


@app.route("/almacen-embarques-entradas-ajax")
@login_requerido
def almacen_embarques_entradas_ajax():
    """Ruta AJAX para visualizar historial de entradas de almacén de embarques."""
    try:
        return render_template(
            "Control de proceso/almacen_embarques_entradas_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Almacén Embarques Entradas AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/control-salida-lineas-ajax")
@login_requerido
def control_salida_lineas_ajax():
    """Ruta AJAX para consultar salida de lineas contra OQC y almacen de embarques."""
    try:
        return render_template("Control de proceso/control_salida_lineas_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Control de salida de lineas AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/almacen-embarques-salidas-ajax")
@login_requerido
def almacen_embarques_salidas_ajax():
    """Ruta AJAX para visualizar historial de salidas de almacén de embarques."""
    try:
        return render_template(
            "Control de proceso/almacen_embarques_salidas_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Almacén Embarques Salidas AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/almacen-embarques-retorno-ajax")
@login_requerido
def almacen_embarques_retorno_ajax():
    """Ruta AJAX para visualizar historial de retornos de almacén de embarques."""
    try:
        response = make_response(render_template(
            "Control de proceso/almacen_embarques_retorno_ajax.html"
        ))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        print(f"Error al cargar template Almacén Embarques Retorno AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/almacen-embarques-movimientos-ajax")
@login_requerido
def almacen_embarques_movimientos_ajax():
    """Ruta AJAX para visualizar y ajustar movimientos de almacén de embarques."""
    try:
        return render_template(
            "Control de proceso/almacen_embarques_movimientos_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Almacén Embarques Movimientos AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/almacen-embarques-inventario-general-ajax")
@login_requerido
def almacen_embarques_inventario_general_ajax():
    """Ruta AJAX para visualizar inventario general de almacén de embarques."""
    try:
        return render_template(
            "Control de proceso/almacen_embarques_inventario_general_ajax.html"
        )
    except Exception as e:
        print(
            f"Error al cargar template Almacén Embarques Inventario General AJAX: {e}"
        )
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/almacen-embarques-catalogo-ajax")
@login_requerido
def almacen_embarques_catalogo_ajax():
    """Ruta AJAX para administrar catálogo de números de parte de embarques."""
    try:
        response = make_response(render_template(
            "Control de proceso/almacen_embarques_catalogo_ajax.html"
        ))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        print(f"Error al cargar template Almacén Embarques Catálogo AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/api/almacen-embarques/entradas")
@login_requerido
def api_almacen_embarques_entradas():
    """Obtener historial de entradas de almacén de embarques."""
    try:
        return jsonify(_obtener_historial_entradas_almacen_embarques())
    except Exception as e:
        print(f"Error API entradas almacén embarques: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/control-salida-lineas")
@login_requerido
def api_control_salida_lineas():
    """Obtener produccion, liberacion OQC y entradas de almacen por parte/fecha."""
    try:
        payload = _obtener_control_salida_lineas()
        payload["success"] = True
        return jsonify(payload)
    except Exception as e:
        print(f"Error API Control de salida de lineas: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e), "rows": []}), 500


@app.route("/api/control-salida-lineas/export")
@login_requerido
def export_control_salida_lineas():
    """Exportar Control de salida de lineas a Excel."""
    try:
        payload = _obtener_control_salida_lineas(limit=5000)
        return _exportar_historial_embarques_excel(
            "Salida Lineas",
            "control_salida_lineas.xlsx",
            {
                "Periodo": "fecha",
                "No. Parte": "part_number",
                "Produccion": "produced_quantity",
                "Liberacion OQC": "oqc_quantity",
                "Pendiente OQC": "pending_oqc",
                "Entradas Almacen": "warehouse_quantity",
                "Pendientes Almacen": "pending_warehouse",
            },
            payload["rows"],
        )
    except Exception as e:
        print(f"Error exportando Control de salida de lineas: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/entradas/export")
@login_requerido
def export_almacen_embarques_entradas():
    """Exportar historial de entradas de almacén de embarques a Excel."""
    try:
        rows = _obtener_historial_entradas_almacen_embarques(limit=5000)
        return _exportar_historial_embarques_excel(
            "Entradas Embarques",
            "entradas_almacen_embarques.xlsx",
            {
                "Fecha": "fecha",
                "Hora": "hora",
                "Folio": "folio",
                "No. Parte": "part_number",
                "Cantidad": "cantidad",
                "Modelo": "product_model",
                "Cliente": "customer",
                "Zona": "zone_code",
                "Ubicación": "location_code",
                "Usuario": "registered_by",
            },
            rows,
        )
    except Exception as e:
        print(
            f"Error exportando entradas almacén embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": str(e)}), 500


@app.route("/api/almacen-embarques/salidas")
@login_requerido
def api_almacen_embarques_salidas():
    """Obtener historial de salidas de almacén de embarques."""
    try:
        return jsonify(_obtener_historial_salidas_almacen_embarques())
    except Exception as e:
        print(f"Error API salidas almacén embarques: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/almacen-embarques/salidas/export")
@login_requerido
def export_almacen_embarques_salidas():
    """Exportar historial de salidas de almacén de embarques a Excel."""
    try:
        rows = _obtener_historial_salidas_almacen_embarques(limit=5000)
        return _exportar_historial_embarques_excel(
            "Salidas Embarques",
            "salidas_almacen_embarques.xlsx",
            {
                "Fecha": "fecha",
                "Hora": "hora",
                "Folio": "folio",
                "No. Parte": "part_number",
                "Cantidad": "cantidad",
                "Departure": "departure_code",
                "Modelo": "product_model",
                "Cliente": "customer",
                "Destino": "destination_area",
                "Motivo": "reason",
                "Usuario": "registered_by",
            },
            rows,
        )
    except Exception as e:
        print(
            f"Error exportando salidas almacén embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": str(e)}), 500


@app.route("/api/almacen-embarques/<module_name>/ajustes/template")
@login_requerido
def api_almacen_embarques_ajustes_template(module_name):
    """Descargar plantilla CSV para ajustes manuales por lote."""
    try:
        config = _obtener_config_ajuste_manual_embarques(module_name)
        inventory_map = _obtener_mapa_inventario_ajuste_manual_embarques()
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["part_number", "quantity"])
        for part_number in sorted(inventory_map.keys()):
            writer.writerow([part_number, ""])

        filename = (
            f"{config['template_filename']}_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        print(
            f"Error generando plantilla ajustes {module_name}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/<module_name>/ajustes/preview", methods=["POST"])
@login_requerido
def api_almacen_embarques_ajustes_preview(module_name):
    """Validar archivo CSV/XLSX y persistir preview de ajuste manual."""
    try:
        config = _obtener_config_ajuste_manual_embarques(module_name)
        uploaded_file = request.files.get("adjustment_file")
        reason = normalize_search(request.form.get("reason"))
        try:
            movement_at = _normalizar_fecha_movimiento_ajuste_embarques(
                request.form.get("movement_at")
            )
        except ValueError as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

        if not uploaded_file or not uploaded_file.filename:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Debes seleccionar un archivo CSV o Excel.",
                    }
                ),
                400,
            )

        if not reason:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "El motivo del ajuste es obligatorio.",
                    }
                ),
                400,
            )

        init_shipping_material_tables()
        parsed = _parsear_archivo_ajuste_manual_embarques(uploaded_file)
        if not parsed["valid"]:
            return jsonify(
                {
                    "success": True,
                    "valid": False,
                    "errors": parsed.get("errors") or [],
                    "batchId": None,
                }
            )

        preview = _construir_preview_ajuste_manual_embarques(
            config,
            parsed.get("rows") or [],
            movement_at,
        )
        if not preview["valid"]:
            return jsonify(
                {
                    "success": True,
                    "valid": False,
                    "errors": preview.get("errors") or [],
                    "preview": preview,
                    "batchId": None,
                }
            )

        batch_id, batch_code = _guardar_preview_ajuste_manual_embarques(
            config,
            movement_at,
            reason,
            uploaded_file.filename,
            parsed["fileHash"],
            preview,
        )

        return jsonify(
            {
                "success": True,
                "valid": True,
                "batchId": batch_id,
                "batchCode": batch_code,
                "preview": preview,
                "message": "Preview validado correctamente.",
            }
        )
    except Exception as e:
        print(
            f"Error preview ajustes {module_name}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/<module_name>/ajustes/confirm", methods=["POST"])
@login_requerido
def api_almacen_embarques_ajustes_confirm(module_name):
    """Confirmar un lote validado de ajustes manuales."""
    try:
        config = _obtener_config_ajuste_manual_embarques(module_name)
        data = request.get_json(silent=True) or {}
        batch_id = int(data.get("batchId") or 0)
        if batch_id <= 0:
            return jsonify({"success": False, "error": "batchId inválido."}), 400

        payload, status_code = _confirmar_ajuste_manual_embarques(config, batch_id)
        return jsonify(payload), status_code
    except Exception as e:
        print(
            f"Error confirmando ajustes {module_name}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/<module_name>/ajustes/manual", methods=["POST"])
@login_requerido
def api_almacen_embarques_ajustes_manual(module_name):
    """Registrar un ajuste manual unitario con la misma trazabilidad de lotes."""
    try:
        config = _obtener_config_ajuste_manual_embarques(module_name)
        data = request.get_json(silent=True) or {}
        init_shipping_material_tables()
        payload, status_code = _registrar_ajuste_manual_individual_embarques(
            config,
            data,
        )
        return jsonify(payload), status_code
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        print(
            f"Error registrando ajuste manual {module_name}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/<module_name>/ajustes/cancel", methods=["POST"])
@login_requerido
def api_almacen_embarques_ajustes_cancel(module_name):
    """Cancelar un preview draft de ajustes manuales."""
    try:
        config = _obtener_config_ajuste_manual_embarques(module_name)
        data = request.get_json(silent=True) or {}
        batch_id = int(data.get("batchId") or 0)
        if batch_id <= 0:
            return jsonify({"success": False, "error": "batchId inválido."}), 400

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexión MySQL.")

        cursor = get_dict_cursor(conn)
        try:
            conn.autocommit(False)
            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['manual_adjustment_batches']}`
                SET status = 'cancelled',
                    cancelled_at = NOW()
                WHERE id = %s
                  AND movement_type = %s
                  AND status = 'draft'
                """,
                (batch_id, config["movement_type"]),
            )
            if cursor.rowcount <= 0:
                conn.rollback()
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "No se encontró un preview pendiente para cancelar.",
                        }
                    ),
                    404,
                )
            conn.commit()
            return jsonify({"success": True, "message": "Preview cancelado."})
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass
            cursor.close()
            conn.close()
    except Exception as e:
        print(
            f"Error cancelando ajustes {module_name}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/salidas/<int:exit_id>/departure", methods=["POST", "PUT", "PATCH"])
@login_requerido
def assign_almacen_embarques_departure(exit_id):
    """Asignar o reasignar departure a una salida de almacén de embarques."""
    try:
        data = request.get_json(silent=True) or {}
        assigned_by = session.get(
            "nombre_completo", session.get("usuario", "Sistema")
        )
        payload, status_code = assign_exit_departure_value(
            exit_id,
            data.get("departureCode") or data.get("departure"),
            assigned_by,
            departure_quantity=(
                data.get("departureQuantity")
                if data.get("departureQuantity") is not None
                else data.get("quantity")
            ),
            notes=data.get("notes"),
            assigned_at=data.get("assignedAt"),
        )
        return jsonify(payload), status_code
    except Exception as e:
        print(
            f"Error asignando departure a salida {exit_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/departures/history")
@login_requerido
def api_almacen_embarques_departure_history():
    """Consultar historial de asignaciones de departure ligadas a salidas."""
    try:
        payload = get_departure_history_records(
            limit=request.args.get("limit"),
            departure_code=request.args.get("departureCode")
            or request.args.get("departure"),
            exit_id=request.args.get("exitId"),
        )
        return jsonify(payload)
    except Exception as e:
        print(
            f"Error consultando historial de departures: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/retorno")
@login_requerido
def api_almacen_embarques_retorno():
    """Obtener historial de retornos de almacén de embarques."""
    try:
        return jsonify(_obtener_historial_retorno_almacen_embarques())
    except Exception as e:
        print(f"Error API retorno almacén embarques: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/almacen-embarques/retorno/export")
@login_requerido
def export_almacen_embarques_retorno():
    """Exportar historial de retornos de almacén de embarques a Excel."""
    try:
        rows = _obtener_historial_retorno_almacen_embarques(limit=5000)
        movement = (request.args.get("movement", "") or "").strip().lower()

        if movement == "entry":
            rows = [
                row
                for row in rows
                if (row.get("return_quantity") or 0) > 0
                and (row.get("loss_quantity") or 0) <= 0
            ]
            for row in rows:
                row["movement_quantity"] = row.get("return_quantity") or 0
            sheet_name = "Entradas Retorno"
            filename = "entradas_retorno_almacen_embarques.xlsx"
            headers = {
                "Fecha": "fecha",
                "Hora": "hora",
                "Folio": "folio",
                "No. Parte": "part_number",
                "Cantidad entrada": "movement_quantity",
                "Modelo": "product_model",
                "Tipo": "reason",
                "Usuario": "registered_by",
            }
        elif movement == "exit":
            rows = [row for row in rows if (row.get("loss_quantity") or 0) > 0]
            for row in rows:
                row["movement_quantity"] = row.get("loss_quantity") or 0
            sheet_name = "Salidas Retorno"
            filename = "salidas_retorno_almacen_embarques.xlsx"
            headers = {
                "Fecha": "fecha",
                "Hora": "hora",
                "Folio": "folio",
                "No. Parte": "part_number",
                "Cantidad salida": "movement_quantity",
                "Modelo": "product_model",
                "Tipo": "reason",
                "Usuario": "registered_by",
            }
        else:
            sheet_name = "Retorno Embarques"
            filename = "retorno_almacen_embarques.xlsx"
            headers = {
                "Fecha": "fecha",
                "Hora": "hora",
                "Folio": "folio",
                "No. Parte": "part_number",
                "Cantidad retorno": "return_quantity",
                "Cantidad pérdida": "loss_quantity",
                "Modelo": "product_model",
                "Cliente": "customer",
                "Tipo": "reason",
                "Usuario": "registered_by",
            }

        return _exportar_historial_embarques_excel(
            sheet_name,
            filename,
            headers,
            rows,
        )
    except Exception as e:
        print(
            f"Error exportando retorno almacén embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"error": str(e)}), 500


@app.route("/api/almacen-embarques/retorno/print-pdf", methods=["POST"])
@login_requerido
def export_almacen_embarques_retorno_print_pdf():
    """Generar PDF imprimible de salidas de retorno seleccionadas."""
    try:
        data = request.get_json(silent=True) or {}
        rows = data.get("rows") or []
        if not isinstance(rows, list):
            return jsonify({"success": False, "error": "Formato de registros inválido."}), 400

        pdf_output = _generar_pdf_salidas_retorno_embarques(rows)
        filename = f"formato_salidas_retorno_{obtener_fecha_hora_mexico().strftime('%Y%m%d%H%M')}.pdf"
        return send_file(
            pdf_output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        print(
            f"Error generando PDF salidas retorno almacén embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/movimientos")
@login_requerido
def api_almacen_embarques_movimientos():
    """Obtener historial unificado editable de movimientos de embarques."""
    try:
        return jsonify(
            {
                "success": True,
                "rows": _obtener_movimientos_editables_almacen_embarques(),
            }
        )
    except Exception as e:
        print(
            f"Error API movimientos almacén embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/movimientos/export")
@login_requerido
def export_almacen_embarques_movimientos():
    """Exportar historial editable de movimientos de embarques."""
    try:
        rows = _obtener_movimientos_editables_almacen_embarques(limit=5000)
        return _exportar_historial_embarques_excel(
            "Movimientos Embarques",
            "movimientos_almacen_embarques.xlsx",
            {
                "Fecha": "fecha",
                "Hora": "hora",
                "Tipo": "movement_label",
                "Folio": "folio",
                "No. Parte": "part_number",
                "Cantidad": "quantity_primary",
                "Modelo": "product_model",
                "Cliente": "customer",
                "Zona": "zone_code",
                "Ubicacion / Destino": "location_value",
                "Departure": "departure_code",
                "Usuario": "registered_by",
            },
            rows,
        )
    except Exception as e:
        print(
            f"Error exportando movimientos de embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/movimientos/<movement_type>/<int:record_id>")
@login_requerido
def api_almacen_embarques_movimiento_detalle(movement_type, record_id):
    """Obtener detalle actual de un movimiento editable de embarques."""
    try:
        movement = _obtener_detalle_movimiento_almacen_embarques(
            movement_type, record_id
        )
        if not movement:
            return jsonify({"success": False, "error": "Movimiento no encontrado"}), 404
        return jsonify({"success": True, "movement": movement})
    except Exception as e:
        print(
            f"Error obteniendo detalle de movimiento {movement_type}/{record_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route(
    "/api/almacen-embarques/movimientos/<movement_type>/<int:record_id>",
    methods=["PATCH", "PUT", "POST"],
)
@login_requerido
def api_almacen_embarques_movimiento_update(movement_type, record_id):
    """Actualizar un movimiento de embarques y registrar el historial del ajuste."""
    try:
        data = request.get_json(silent=True) or {}
        notes = (data.get("notes") or "").strip()
        if not notes:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "El motivo del ajuste es obligatorio",
                    }
                ),
                400,
            )
        payload, status_code = adjust_shipping_movement_record(
            movement_type,
            record_id,
            data.get("changes") or data,
            session.get("nombre_completo", session.get("usuario", "Sistema")),
            notes=notes,
        )
        return jsonify(payload), status_code
    except Exception as e:
        print(
            f"Error actualizando movimiento {movement_type}/{record_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route(
    "/api/almacen-embarques/movimientos/<movement_type>/<int:record_id>",
    methods=["DELETE"],
)
@login_requerido
def api_almacen_embarques_movimiento_delete(movement_type, record_id):
    """Eliminar un movimiento de embarques con confirmación de contraseña."""
    try:
        data = request.get_json(silent=True) or {}
        password = data.get("password")
        notes = (data.get("notes") or "").strip()
        if not notes:
            return jsonify({"success": False, "error": "El comentario de eliminación es obligatorio"}), 400

        is_valid_password, password_error = _validar_password_usuario_actual(password)
        if not is_valid_password:
            return jsonify({"success": False, "error": password_error}), 400

        payload, status_code = delete_shipping_movement_record(
            movement_type,
            record_id,
            _obtener_usuario_display_actual(),
            notes=notes,
        )
        return jsonify(payload), status_code
    except Exception as e:
        print(
            f"Error eliminando movimiento {movement_type}/{record_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/inventario-general")
@login_requerido
def api_almacen_embarques_inventario_general():
    """Obtener inventario general del periodo para almacén de embarques."""
    try:
        payload = _obtener_inventario_general_almacen_embarques()
        return jsonify({"success": True, **payload})
    except Exception as e:
        print(
            f"Error API inventario general embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/catalogo")
@login_requerido
def api_almacen_embarques_catalogo():
    """Obtener catálogo de números de parte de almacén de embarques."""
    try:
        init_shipping_material_tables()
        payload = _obtener_catalogo_almacen_embarques()
        return jsonify({"success": True, **payload})
    except Exception as e:
        print(f"Error API catálogo embarques: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/catalogo", methods=["POST"])
@login_requerido
def api_almacen_embarques_catalogo_create():
    """Crear un número de parte en catálogo e inventario de embarques."""
    try:
        init_shipping_material_tables()
        data = request.get_json(silent=True) or {}
        payload, status_code = _crear_catalogo_almacen_embarques(data)
        return jsonify(payload), status_code
    except Exception as e:
        print(f"Error creando catálogo embarques: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/catalogo/<int:catalog_id>", methods=["PATCH"])
@login_requerido
def api_almacen_embarques_catalogo_update(catalog_id):
    """Actualizar campos del catálogo de embarques y su snapshot de inventario."""
    try:
        init_shipping_material_tables()
        data = request.get_json(silent=True) or {}
        payload, status_code = _actualizar_catalogo_almacen_embarques(catalog_id, data)
        return jsonify(payload), status_code
    except Exception as e:
        print(
            f"Error actualizando catálogo embarques {catalog_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/catalogo/<int:catalog_id>", methods=["DELETE"])
@login_requerido
def api_almacen_embarques_catalogo_delete(catalog_id):
    """Eliminar o dar de baja lógica a un número de parte del catálogo."""
    try:
        init_shipping_material_tables()
        data = request.get_json(silent=True) or {}
        payload, status_code = _eliminar_catalogo_almacen_embarques(catalog_id, data)
        return jsonify(payload), status_code
    except Exception as e:
        print(
            f"Error eliminando catálogo embarques {catalog_id}: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/catalogo/export")
@login_requerido
def export_almacen_embarques_catalogo():
    """Exportar catálogo de números de parte de embarques."""
    try:
        payload = _obtener_catalogo_almacen_embarques(limit=20000)
        return _exportar_historial_embarques_excel(
            "Catalogo Embarques",
            "catalogo_almacen_embarques.xlsx",
            {
                "No. Parte": "part_number",
                "Modelo": "product_model",
                "Estatus": "product_status",
                "Descripción": "description",
                "Std Pack": "standard_pack",
                "Cliente": "customer",
                "Zona": "zone_code",
                "Cantidad actual": "current_quantity",
            },
            payload.get("rows") or [],
        )
    except Exception as e:
        print(f"Error exportando catálogo embarques: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/inventario-general/export")
@login_requerido
def export_almacen_embarques_inventario_general():
    """Exportar inventario general del periodo de embarques."""
    try:
        payload = _obtener_inventario_general_almacen_embarques(limit=20000)
        return _exportar_historial_embarques_excel(
            "Inventario General Embarques",
            "inventario_general_almacen_embarques.xlsx",
            {
                "No. Parte": "part_number",
                "Modelo": "product_model",
                "Cliente": "customer",
                "Inventario inicial": "initial_quantity",
                "Entradas": "entries_qty",
                "Salidas": "exits_qty",
                "Entradas retorno": "return_entries_qty",
                "Salidas retorno": "return_exits_qty",
                "Cantidad total": "current_quantity",
                "Inicio de periodo": "period_start",
                "Cierre": "closure_label",
            },
            payload.get("rows") or [],
        )
    except Exception as e:
        print(
            f"Error exportando inventario general embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/inventario-general/cierre/bootstrap")
@login_requerido
def api_almacen_embarques_inventario_cierre_bootstrap():
    """Obtener contexto inicial y baseline del cierre de inventario de embarques."""
    try:
        payload = _obtener_inventario_general_almacen_embarques(limit=20000)
        preview = _construir_preview_cierre_inventario_embarques(payload.get("rows") or [])
        return jsonify(
            {
                "success": True,
                "metadata": _obtener_contexto_cierre_inventario_embarques(),
                "preview": preview,
                "history": _obtener_historial_cierres_inventario_embarques(
                    include_last_draft_for=_obtener_usuario_display_actual()
                ),
            }
        )
    except Exception as e:
        print(
            f"Error bootstrap cierre inventario embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/inventario-general/cierre/template")
@login_requerido
def api_almacen_embarques_inventario_cierre_template():
    """Descargar plantilla CSV del catálogo completo para cierre de inventario."""
    try:
        payload = _obtener_inventario_general_almacen_embarques(limit=20000)
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["part_number", "current_qty"])
        for row in payload.get("rows") or []:
            writer.writerow([row.get("part_number") or "", ""])

        content = output.getvalue().encode("utf-8-sig")
        filename = f"plantilla_cierre_inventario_embarques_{datetime.now().strftime('%Y%m%d')}.csv"
        return send_file(
            io.BytesIO(content),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        print(
            f"Error generando plantilla CSV cierre inventario embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/inventario-general/cierre/preview", methods=["POST"])
@login_requerido
def api_almacen_embarques_inventario_cierre_preview():
    """Validar CSV de cierre y generar preview persistente en borrador."""
    try:
        csv_file = request.files.get("closure_file")
        if not csv_file or not csv_file.filename:
            return jsonify(
                {
                    "success": False,
                    "error": "Debes seleccionar un archivo CSV para validar.",
                }
            ), 400

        current_payload = _obtener_inventario_general_almacen_embarques(limit=20000)
        current_rows = current_payload.get("rows") or []
        expected_parts = [row.get("part_number") for row in current_rows if row.get("part_number")]

        parsed_csv = _parsear_csv_cierre_inventario_embarques(csv_file, expected_parts)
        preview = _construir_preview_cierre_inventario_embarques(
            current_rows,
            parsed_csv.get("rows") if parsed_csv.get("rows") else None,
        )
        metadata = _obtener_contexto_cierre_inventario_embarques()

        response_payload = {
            "success": True,
            "valid": parsed_csv["valid"],
            "metadata": metadata,
            "preview": preview,
            "errors": parsed_csv.get("errors") or [],
            "history": _obtener_historial_cierres_inventario_embarques(
                include_last_draft_for=_obtener_usuario_display_actual()
            ),
            "batchId": None,
        }

        if parsed_csv["valid"]:
            draft_payload = {
                "metadata": {
                    **metadata,
                    "csvFileName": csv_file.filename,
                    "csvHash": parsed_csv["csvHash"],
                },
                "summary": preview["summary"],
                "rows": preview["rows"],
            }
            batch_id = _guardar_borrador_cierre_inventario_embarques(
                draft_payload,
                csv_file.filename,
                parsed_csv["csvHash"],
            )
            response_payload["batchId"] = batch_id

        return jsonify(response_payload)
    except Exception as e:
        print(
            f"Error preview cierre inventario embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/inventario-general/cierre/confirm", methods=["POST"])
@login_requerido
def api_almacen_embarques_inventario_cierre_confirm():
    """Confirmar lote de cierre validado y registrarlo como base del siguiente periodo."""
    try:
        data = request.get_json(silent=True) or {}
        batch_id = int(data.get("batchId") or 0)
        if batch_id <= 0:
            return jsonify({"success": False, "error": "batchId inválido."}), 400

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexión MySQL para confirmar el cierre.")

        cursor = get_dict_cursor(conn)
        usuario_actual = _obtener_usuario_display_actual()

        try:
            conn.autocommit(False)
            cursor.execute(
                f"""
                SELECT *
                FROM `{SHIPPING_TABLES['inventory_closure_batches']}`
                WHERE id = %s
                LIMIT 1
                """,
                (batch_id,),
            )
            batch_row = cursor.fetchone()
            if not batch_row:
                return jsonify({"success": False, "error": "No se encontró el borrador del cierre."}), 404

            if (batch_row.get("status") or "").lower() != "draft":
                return jsonify({"success": False, "error": "El lote indicado ya no está disponible para confirmar."}), 409

            cursor.execute(
                f"""
                SELECT id
                FROM `{SHIPPING_TABLES['inventory_closure_batches']}`
                WHERE closure_month = %s
                  AND status = 'confirmed'
                LIMIT 1
                """,
                (batch_row.get("closure_month"),),
            )
            existing_confirmed = cursor.fetchone()
            if existing_confirmed:
                return jsonify({"success": False, "error": "Ya existe un cierre confirmado para ese mes."}), 409

            payload_json = batch_row.get("payload_json") or "{}"
            payload = json.loads(payload_json)
            preview_rows = payload.get("rows") or []
            metadata = payload.get("metadata") or {}

            for row in preview_rows:
                csv_current_qty = row.get("csv_current_qty")
                if csv_current_qty is None:
                    raise ValueError(
                        f"El lote contiene part_numbers sin inventario físico cargado: {row.get('part_number')}"
                    )

                cursor.execute(
                    f"""
                    INSERT INTO `{SHIPPING_TABLES['inventory_closures']}` (
                      closure_batch_id,
                      part_number,
                      initial_quantity,
                      system_quantity,
                      difference_quantity,
                      raw_current_quantity,
                      closed_at,
                      closure_label,
                      closed_by,
                      notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        batch_id,
                        row.get("part_number"),
                        max(int(row.get("applied_initial_quantity") or 0), 0),
                        int(row.get("system_quantity") or 0),
                        int(row.get("difference_quantity") or 0),
                        int(csv_current_qty),
                        metadata.get("closureDateTime"),
                        metadata.get("closureLabel"),
                        usuario_actual,
                        json.dumps(
                            {
                                "status": row.get("status"),
                                "csvHash": metadata.get("csvHash"),
                                "rowsHash": payload.get("summary", {}).get("rowsHash"),
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    ),
                )

            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['inventory_closure_batches']}`
                SET status = 'confirmed',
                    confirmed_by = %s,
                    confirmed_at = %s
                WHERE id = %s
                """,
                (usuario_actual, metadata.get("closureDateTime"), batch_id),
            )

            conn.commit()
            return jsonify(
                {
                    "success": True,
                    "message": "Cierre de inventario confirmado correctamente.",
                    "history": _obtener_historial_cierres_inventario_embarques(
                        include_last_draft_for=_obtener_usuario_display_actual()
                    ),
                }
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass
            cursor.close()
            conn.close()
    except Exception as e:
        print(
            f"Error confirmando cierre inventario embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/inventario-general/cierre/cancel", methods=["POST"])
@login_requerido
def api_almacen_embarques_inventario_cierre_cancel():
    """Cancelar un borrador de preview de cierre para reiniciar el proceso."""
    try:
        data = request.get_json(silent=True) or {}
        batch_id = int(data.get("batchId") or 0)
        if batch_id <= 0:
            return jsonify({"success": False, "error": "batchId inválido."}), 400

        usuario_actual = _obtener_usuario_display_actual()
        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexión MySQL para cancelar el borrador.")

        cursor = get_dict_cursor(conn)
        try:
            conn.autocommit(False)
            cursor.execute(
                f"""
                SELECT id, status, created_by
                FROM `{SHIPPING_TABLES['inventory_closure_batches']}`
                WHERE id = %s
                LIMIT 1
                """,
                (batch_id,),
            )
            batch_row = cursor.fetchone()
            if not batch_row:
                return jsonify({"success": False, "error": "No se encontró el borrador del cierre."}), 404

            if (batch_row.get("status") or "").lower() != "draft":
                return jsonify({"success": False, "error": "Solo se pueden cancelar previews en estado draft."}), 409

            if (
                (batch_row.get("created_by") or "").strip().lower()
                != (usuario_actual or "").strip().lower()
            ):
                return jsonify({"success": False, "error": "Solo el usuario que generó el preview puede cancelarlo."}), 403

            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['inventory_closure_batches']}`
                SET status = 'cancelled'
                WHERE id = %s
                """,
                (batch_id,),
            )
            conn.commit()
            return jsonify(
                {
                    "success": True,
                    "message": "Preview cancelado correctamente.",
                    "history": _obtener_historial_cierres_inventario_embarques(
                        include_last_draft_for=_obtener_usuario_display_actual()
                    ),
                }
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass
            cursor.close()
            conn.close()
    except Exception as e:
        print(
            f"Error cancelando preview de cierre inventario embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/inventario-general/cierre/history/<int:batch_id>")
@login_requerido
def api_almacen_embarques_inventario_cierre_history_detail(batch_id):
    """Consultar detalle completo de un cierre de inventario."""
    try:
        row = execute_query(
            f"""
            SELECT *
            FROM `{SHIPPING_TABLES['inventory_closure_batches']}`
            WHERE id = %s
            LIMIT 1
            """,
            (batch_id,),
            fetch="one",
        )
        if not row:
            return jsonify({"success": False, "error": "No se encontró el cierre solicitado."}), 404

        payload = json.loads(row.get("payload_json") or "{}")
        period_info = _resolver_periodo_cierre_embarques(row)
        payload = _aplicar_metadata_periodo_cierre_embarques(payload, period_info)
        return jsonify(
            {
                "success": True,
                "batch": {
                    "id": row.get("id"),
                    "closure_label": period_info["closure_label"],
                    "closure_month": period_info["closure_month"],
                    "status": row.get("status"),
                    "created_by": row.get("created_by"),
                    "confirmed_by": row.get("confirmed_by"),
                    "closed_at": _normalizar_texto_embarques_historial(row.get("closed_at")),
                    "confirmed_at": _normalizar_texto_embarques_historial(row.get("confirmed_at")),
                    "accuracy_pct": row.get("accuracy_pct"),
                    "csv_hash": row.get("csv_hash"),
                    "rows_hash": row.get("rows_hash"),
                },
                "payload": payload,
            }
        )
    except Exception as e:
        print(
            f"Error consultando detalle de cierre inventario embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/almacen-embarques/inventario-general/cierre/history/<int:batch_id>/export")
@login_requerido
def export_almacen_embarques_inventario_cierre_report(batch_id):
    """Exportar reporte completo del cierre de inventario en Excel."""
    try:
        from io import BytesIO

        from flask import Response
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        batch = execute_query(
            f"""
            SELECT *
            FROM `{SHIPPING_TABLES['inventory_closure_batches']}`
            WHERE id = %s
            LIMIT 1
            """,
            (batch_id,),
            fetch="one",
        )
        if not batch:
            return jsonify({"success": False, "error": "No se encontró el cierre solicitado."}), 404
        if (batch.get("status") or "").lower() != "confirmed":
            return jsonify({"success": False, "error": "Sólo se pueden exportar cierres confirmados."}), 409

        raw_period_end = batch.get("closed_at")
        previous_batch = execute_query(
            f"""
            SELECT id, closed_at
            FROM `{SHIPPING_TABLES['inventory_closure_batches']}`
            WHERE status = 'confirmed'
              AND closed_at < %s
            ORDER BY closed_at DESC, id DESC
            LIMIT 1
            """,
            (raw_period_end,),
            fetch="one",
        )
        period_info = _resolver_periodo_cierre_embarques(
            batch,
            previous_closed_at=(previous_batch or {}).get("closed_at"),
        )
        period_start = (previous_batch or {}).get("closed_at") or period_info["period_start"]
        period_end = period_info["period_end_exclusive"] or raw_period_end
        period_end_inclusive = period_info["period_end_inclusive"]
        previous_batch_id = (previous_batch or {}).get("id")

        def period_filter(column_expr):
            clauses = []
            params = []
            if period_start:
                clauses.append(f"{column_expr} >= %s")
                params.append(period_start)
            if period_end:
                clauses.append(f"{column_expr} < %s")
                params.append(period_end)
            return " AND ".join(clauses) if clauses else "1 = 1", params

        def normalize_excel_value(value):
            if isinstance(value, Decimal):
                try:
                    as_int = int(value)
                    return as_int if value == as_int else float(value)
                except Exception:
                    return float(value)
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(value, date):
                return value.strftime("%Y-%m-%d")
            return value

        def parse_json_summary(raw_value):
            if not raw_value:
                return ""
            try:
                parsed = json.loads(raw_value)
            except Exception:
                return str(raw_value)
            if isinstance(parsed, dict):
                return " | ".join(
                    f"{key}: {normalize_excel_value(value)}"
                    for key, value in parsed.items()
                )
            if isinstance(parsed, list):
                return ", ".join(str(item) for item in parsed)
            return str(parsed)

        def index_quantity(rows, part_key, quantity_key):
            indexed = {}
            for item in rows:
                part_number = _normalizar_texto_embarques_historial(item.get(part_key))
                indexed[part_number] = _normalizar_numero_embarques_historial(
                    item.get(quantity_key)
                ) or 0
            return indexed

        closures = execute_query(
            f"""
            SELECT
              part_number,
              initial_quantity,
              system_quantity,
              difference_quantity,
              raw_current_quantity
            FROM `{SHIPPING_TABLES['inventory_closures']}`
            WHERE closure_batch_id = %s
            ORDER BY part_number ASC
            """,
            (batch_id,),
            fetch="all",
        ) or []

        previous_closures = []
        if previous_batch_id:
            previous_closures = execute_query(
                f"""
                SELECT part_number, initial_quantity
                FROM `{SHIPPING_TABLES['inventory_closures']}`
                WHERE closure_batch_id = %s
                """,
                (previous_batch_id,),
                fetch="all",
            ) or []

        movement_clause, movement_params = period_filter("COALESCE(movement_at, created_at)")
        entries_agg = execute_query(
            f"""
            SELECT part_number, COALESCE(SUM(quantity), 0) AS quantity
            FROM `{SHIPPING_TABLES['entries']}`
            WHERE {movement_clause}
              AND COALESCE(is_fifo_layer_only, 0) = 0
            GROUP BY part_number
            """,
            tuple(movement_params),
            fetch="all",
        ) or []
        exits_agg = execute_query(
            f"""
            SELECT part_number, COALESCE(SUM(quantity), 0) AS quantity
            FROM `{SHIPPING_TABLES['exits']}`
            WHERE {movement_clause}
            GROUP BY part_number
            """,
            tuple(movement_params),
            fetch="all",
        ) or []
        returns_agg = execute_query(
            f"""
            SELECT
              part_number,
              COALESCE(SUM(return_quantity), 0) AS return_quantity,
              COALESCE(SUM(loss_quantity), 0) AS loss_quantity
            FROM `{SHIPPING_TABLES['returns']}`
            WHERE {movement_clause}
            GROUP BY part_number
            """,
            tuple(movement_params),
            fetch="all",
        ) or []

        entries_by_part = index_quantity(entries_agg, "part_number", "quantity")
        exits_by_part = index_quantity(exits_agg, "part_number", "quantity")
        return_entries_by_part = index_quantity(returns_agg, "part_number", "return_quantity")
        return_losses_by_part = index_quantity(returns_agg, "part_number", "loss_quantity")
        previous_initial_by_part = index_quantity(previous_closures, "part_number", "initial_quantity")

        cierre_rows = []
        for row in closures:
            part_number = _normalizar_texto_embarques_historial(row.get("part_number"))
            entries_quantity = entries_by_part.get(part_number, 0)
            exits_quantity = exits_by_part.get(part_number, 0)
            return_entries_quantity = return_entries_by_part.get(part_number, 0)
            return_losses_quantity = return_losses_by_part.get(part_number, 0)
            if previous_batch_id:
                initial_quantity = previous_initial_by_part.get(part_number, 0)
            else:
                # Primer cierre: no hay cierre anterior que defina base.
                # Se infiere la base inicial usando el snapshot del sistema al cierre.
                system_quantity = _normalizar_numero_embarques_historial(row.get("system_quantity"))
                if system_quantity is None:
                    system_quantity = 0
                initial_quantity = (
                    system_quantity
                    - entries_quantity
                    + exits_quantity
                    - return_entries_quantity
                    + return_losses_quantity
                )
            cierre_rows.append(
                {
                    "part_number": part_number,
                    "initial_quantity": initial_quantity,
                    "entries": entries_quantity,
                    "exits": exits_quantity,
                    "return_entries": return_entries_quantity,
                    "return_losses": return_losses_quantity,
                    "physical_quantity": _normalizar_numero_embarques_historial(row.get("raw_current_quantity")),
                    "difference_quantity": _normalizar_numero_embarques_historial(row.get("difference_quantity")),
                }
            )

        entries_rows = execute_query(
            f"""
            SELECT
              COALESCE(movement_at, created_at) AS movement_at,
              'Entrada' AS movement_type,
              entry_folio AS folio,
              part_number,
              quantity,
              '' AS departure_code,
              product_model,
              customer,
              registered_by
            FROM `{SHIPPING_TABLES['entries']}`
            WHERE {movement_clause}
              AND COALESCE(is_fifo_layer_only, 0) = 0
            """,
            tuple(movement_params),
            fetch="all",
        ) or []
        exits_rows = execute_query(
            f"""
            SELECT
              COALESCE(movement_at, created_at) AS movement_at,
              'Salida' AS movement_type,
              exit_folio AS folio,
              part_number,
              quantity,
              departure_code,
              product_model,
              customer,
              registered_by
            FROM `{SHIPPING_TABLES['exits']}`
            WHERE {movement_clause}
            """,
            tuple(movement_params),
            fetch="all",
        ) or []

        entradas_salidas_rows = []
        for item in entries_rows + exits_rows:
            movement_at = item.get("movement_at")
            entradas_salidas_rows.append(
                {
                    "fecha": movement_at.strftime("%Y-%m-%d") if isinstance(movement_at, datetime) else "",
                    "hora": movement_at.strftime("%H:%M:%S") if isinstance(movement_at, datetime) else "",
                    "tipo": item.get("movement_type"),
                    "folio": item.get("folio"),
                    "part_number": item.get("part_number"),
                    "quantity": _normalizar_numero_embarques_historial(item.get("quantity")),
                    "departure_code": item.get("departure_code") or "",
                    "product_model": item.get("product_model") or "",
                    "customer": item.get("customer") or "",
                    "registered_by": item.get("registered_by") or "",
                }
            )
        entradas_salidas_rows.sort(
            key=lambda item: (item.get("fecha") or "", item.get("hora") or "", item.get("folio") or "")
        )

        returns_rows_raw = execute_query(
            f"""
            SELECT
              COALESCE(movement_at, created_at) AS movement_at,
              return_folio,
              part_number,
              return_quantity,
              loss_quantity,
              product_model,
              customer,
              reason,
              registered_by
            FROM `{SHIPPING_TABLES['returns']}`
            WHERE {movement_clause}
            ORDER BY COALESCE(movement_at, created_at) ASC, id ASC
            """,
            tuple(movement_params),
            fetch="all",
        ) or []
        retorno_rows = []
        for item in returns_rows_raw:
            movement_at = item.get("movement_at")
            base = {
                "fecha": movement_at.strftime("%Y-%m-%d") if isinstance(movement_at, datetime) else "",
                "hora": movement_at.strftime("%H:%M:%S") if isinstance(movement_at, datetime) else "",
                "folio": item.get("return_folio"),
                "part_number": item.get("part_number"),
                "product_model": item.get("product_model") or "",
                "customer": item.get("customer") or "",
                "return_type": item.get("reason") or "",
                "registered_by": item.get("registered_by") or "",
            }
            return_quantity = _normalizar_numero_embarques_historial(item.get("return_quantity")) or 0
            loss_quantity = _normalizar_numero_embarques_historial(item.get("loss_quantity")) or 0
            if return_quantity:
                retorno_rows.append({**base, "movement_type": "Entrada retorno", "quantity": return_quantity})
            if loss_quantity:
                retorno_rows.append({**base, "movement_type": "Salida retorno", "quantity": loss_quantity})

        adjustment_clause, adjustment_params = period_filter("adjusted_at")
        adjustment_rows_raw = execute_query(
            f"""
            SELECT
              adjusted_at,
              'Movimiento' AS adjustment_type,
              movement_type,
              adjustment_action,
              folio,
              part_number,
              changed_fields_json,
              previous_values_json,
              new_values_json,
              notes,
              adjusted_by
            FROM `{SHIPPING_TABLES['movement_adjustments']}`
            WHERE {adjustment_clause}
            ORDER BY adjusted_at ASC, id ASC
            """,
            tuple(adjustment_params),
            fetch="all",
        ) or []
        departure_clause, departure_params = period_filter("assigned_at")
        departure_rows_raw = execute_query(
            f"""
            SELECT
              assigned_at,
              'Departure' AS adjustment_type,
              'exit' AS movement_type,
              assignment_action AS adjustment_action,
              exit_folio AS folio,
              part_number,
              previous_departure_code,
              departure_code,
              notes,
              assigned_by
            FROM `{SHIPPING_TABLES['departure_history']}`
            WHERE {departure_clause}
            ORDER BY assigned_at ASC, id ASC
            """,
            tuple(departure_params),
            fetch="all",
        ) or []

        modificaciones_rows = []
        for item in adjustment_rows_raw:
            adjusted_at = item.get("adjusted_at")
            modificaciones_rows.append(
                {
                    "fecha": adjusted_at.strftime("%Y-%m-%d") if isinstance(adjusted_at, datetime) else "",
                    "hora": adjusted_at.strftime("%H:%M:%S") if isinstance(adjusted_at, datetime) else "",
                    "adjustment_type": item.get("adjustment_type"),
                    "movement_type": item.get("movement_type"),
                    "folio": item.get("folio"),
                    "part_number": item.get("part_number"),
                    "action": item.get("adjustment_action"),
                    "changed_fields": parse_json_summary(item.get("changed_fields_json")),
                    "before": parse_json_summary(item.get("previous_values_json")),
                    "after": parse_json_summary(item.get("new_values_json")),
                    "notes": item.get("notes") or "",
                    "user": item.get("adjusted_by") or "",
                }
            )
        for item in departure_rows_raw:
            adjusted_at = item.get("assigned_at")
            modificaciones_rows.append(
                {
                    "fecha": adjusted_at.strftime("%Y-%m-%d") if isinstance(adjusted_at, datetime) else "",
                    "hora": adjusted_at.strftime("%H:%M:%S") if isinstance(adjusted_at, datetime) else "",
                    "adjustment_type": item.get("adjustment_type"),
                    "movement_type": "Salida",
                    "folio": item.get("folio"),
                    "part_number": item.get("part_number"),
                    "action": item.get("adjustment_action"),
                    "changed_fields": "departure_code",
                    "before": item.get("previous_departure_code") or "",
                    "after": item.get("departure_code") or "",
                    "notes": item.get("notes") or "",
                    "user": item.get("assigned_by") or "",
                }
            )
        modificaciones_rows.sort(
            key=lambda item: (item.get("fecha") or "", item.get("hora") or "", item.get("folio") or "")
        )

        wb = Workbook()
        header_fill = PatternFill(start_color="10243F", end_color="10243F", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        title_font = Font(color="10243F", bold=True, size=14)

        def write_sheet(ws, title, headers, rows):
            ws.cell(row=1, column=1, value=title)
            ws.cell(row=1, column=1).font = title_font
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
            if period_start and period_end_inclusive:
                period_text = (
                    f"Periodo: {normalize_excel_value(period_start)} "
                    f"a {normalize_excel_value(period_end_inclusive)}"
                )
            else:
                period_text = f"Periodo: inicio de operación a {normalize_excel_value(period_end)}"
            ws.cell(row=2, column=1, value=period_text)
            ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))

            header_row = 4
            for col_idx, (label, _key) in enumerate(headers, 1):
                cell = ws.cell(row=header_row, column=col_idx, value=label)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            if rows:
                for row_idx, row in enumerate(rows, header_row + 1):
                    for col_idx, (_label, key) in enumerate(headers, 1):
                        cell = ws.cell(row=row_idx, column=col_idx, value=normalize_excel_value(row.get(key, "")))
                        cell.alignment = Alignment(vertical="top", wrap_text=True)
            else:
                ws.cell(row=header_row + 1, column=1, value="Sin registros para el periodo.")
                ws.merge_cells(start_row=header_row + 1, start_column=1, end_row=header_row + 1, end_column=len(headers))

            ws.freeze_panes = "A5"
            ws.auto_filter.ref = f"A4:{ws.cell(row=max(header_row + 1, len(rows) + header_row), column=len(headers)).coordinate}"

            for column_idx in range(1, ws.max_column + 1):
                column_letter = get_column_letter(column_idx)
                max_length = 0
                for cell in ws[column_letter]:
                    value_length = len(str(cell.value or ""))
                    max_length = max(max_length, value_length)
                ws.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 36)

        ws = wb.active
        ws.title = "Cierre"
        write_sheet(
            ws,
            f"Reporte de cierre - {period_info['closure_label']}",
            [
                ("No. parte", "part_number"),
                ("Inventario inicial", "initial_quantity"),
                ("Entradas", "entries"),
                ("Salidas", "exits"),
                ("Entradas de retorno", "return_entries"),
                ("Salidas de retorno", "return_losses"),
                ("Inventario físico", "physical_quantity"),
                ("Diferencia", "difference_quantity"),
            ],
            cierre_rows,
        )

        ws = wb.create_sheet("Entradas y Salidas")
        write_sheet(
            ws,
            "Historial de entradas y salidas",
            [
                ("Fecha", "fecha"),
                ("Hora", "hora"),
                ("Movimiento", "tipo"),
                ("Folio", "folio"),
                ("No. parte", "part_number"),
                ("Cantidad", "quantity"),
                ("Departure", "departure_code"),
                ("Modelo", "product_model"),
                ("Cliente", "customer"),
                ("Usuario", "registered_by"),
            ],
            entradas_salidas_rows,
        )

        ws = wb.create_sheet("Retornos")
        write_sheet(
            ws,
            "Historial de entradas y salidas de retorno",
            [
                ("Fecha", "fecha"),
                ("Hora", "hora"),
                ("Movimiento", "movement_type"),
                ("Folio", "folio"),
                ("No. parte", "part_number"),
                ("Cantidad", "quantity"),
                ("Modelo", "product_model"),
                ("Cliente", "customer"),
                ("Tipo", "return_type"),
                ("Usuario", "registered_by"),
            ],
            retorno_rows,
        )

        ws = wb.create_sheet("Modificaciones")
        write_sheet(
            ws,
            "Historial de modificaciones",
            [
                ("Fecha", "fecha"),
                ("Hora", "hora"),
                ("Tipo ajuste", "adjustment_type"),
                ("Movimiento", "movement_type"),
                ("Folio", "folio"),
                ("No. parte", "part_number"),
                ("Acción", "action"),
                ("Campos", "changed_fields"),
                ("Antes", "before"),
                ("Después", "after"),
                ("Motivo / nota", "notes"),
                ("Usuario", "user"),
            ],
            modificaciones_rows,
        )

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename_label = re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            str(period_info["closure_label"] or f"cierre_{batch_id}"),
        ).strip("_")
        filename = f"reporte_{filename_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return Response(
            output.getvalue(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        print(
            f"Error exportando reporte de cierre inventario embarques: {e}\n{traceback.format_exc()}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/registro-movimiento-identificacion-ajax")
@login_requerido
def registro_movimiento_identificacion_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Registro Movimiento Identificación"""
    try:
        return render_template(
            "Control de proceso/registro_movimiento_identificacion_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Registro Movimiento Identificación AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/control-otras-identificaciones-ajax")
@login_requerido
def control_otras_identificaciones_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control Otras Identificaciones"""
    try:
        return render_template(
            "Control de proceso/control_otras_identificaciones_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Control Otras Identificaciones AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/control-movimiento-ns-producto-ajax")
@login_requerido
def control_movimiento_ns_producto_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control Movimiento NS Producto"""
    try:
        return render_template(
            "Control de proceso/control_movimiento_ns_producto_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Control Movimiento NS Producto AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/model-sn-management-ajax")
@login_requerido
def model_sn_management_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Model SN Management"""
    try:
        return render_template("Control de proceso/model_sn_management_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Model SN Management AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/control-scrap-ajax")
@login_requerido
def control_scrap_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control Scrap"""
    try:
        return render_template("Control de proceso/control_scrap_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Control Scrap AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# Rutas AJAX para módulos de Control de Producción
@app.route("/line-material-status-ajax")
@login_requerido
def line_material_status_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Line Material Status_es"""
    try:
        return render_template(
            "Control de produccion/line_material_status_es_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Line Material Status_es AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# Migracion 2026-05-26: 3 rutas template de Control de SMT (Metal Mask,
# Squeegee, Caja Metal Mask) movidas a sus blueprints en
# app/api/control_produccion/{metal_mask,squeegee,caja_metal_mask}.py


@app.route("/estandares-soldadura-ajax")
@login_requerido
def estandares_soldadura_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Estandares sobre control de soldadura"""
    try:
        return render_template("Control de produccion/estandares_soldadura_ajax.html")
    except Exception as e:
        print(
            f"Error al cargar template Estandares sobre control de soldadura AJAX: {e}"
        )
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/registro-recibo-soldadura-ajax")
@login_requerido
def registro_recibo_soldadura_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Registro de recibo de soldadura"""
    try:
        return render_template(
            "Control de produccion/registro_recibo_soldadura_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Registro de recibo de soldadura AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/control-salida-soldadura-ajax")
@login_requerido
def control_salida_soldadura_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de salida de soldadura"""
    try:
        return render_template(
            "Control de produccion/control_salida_soldadura_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Control de salida de soldadura AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/historial-tension-mask-metal-ajax")
@login_requerido
def historial_tension_mask_metal_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Historial de tension de mask de metal"""
    try:
        return render_template(
            "Control de produccion/historial_tension_mask_metal_ajax.html"
        )
    except Exception as e:
        print(
            f"Error al cargar template Historial de tension de mask de metal AJAX: {e}"
        )
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/control_proceso/inventario_imd_terminado")
@login_requerido
@requiere_permiso_dropdown(
    "LISTA_DE_CONTROL_DE_RESULTADOS", "Control de inventario", "IMD-SMD TERMINADO"
)
def inventario_imd_terminado_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Inventario IMD Terminado"""
    try:
        print(" Iniciando carga de Inventario IMD Terminado AJAX...")
        result = render_template(
            "Control de proceso/inventario_imd_terminado_ajax.html"
        )
        print(
            f" Template Inventario IMD Terminado AJAX renderizado exitosamente, tamaño: {len(result)} caracteres"
        )
        return result
    except Exception as e:
        print(f" Error al cargar template Inventario IMD Terminado AJAX: {e}")
        import traceback

        traceback.print_exc()
        return f"Error al cargar el contenido: {str(e)}", 500


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


@app.route("/historial-aoi")
@login_requerido
def historial_aoi():
    """Servir la página de Historial AOI"""
    try:
        return render_template("Control de resultados/Historial AOI.html")
    except Exception as e:
        print(f"Error al cargar Historial AOI: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/historial-ict-ajax")
@login_requerido
def historial_ict_ajax():
    """Ruta AJAX para cargar el Historial ICT"""
    try:
        return render_template("Control de resultados/history_ict.html")
    except Exception as e:
        print(f"Error al cargar template de Historial ICT: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500

@app.route("/historial-maquina-ict-pass-fail")
@app.route("/historial-maquina-ict-pass-fail-ajax")
@login_requerido
def historial_maquina_ict_pass_fail():
    """Servir la página de Historial maquina ICT % Pass/Fail"""
    try:
        return render_template("Control de resultados/history_ict_Pass_Fail.html")
    except Exception as e:
        print(f"Error al cargar Historial maquina ICT % Pass/Fail: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


def _ict_pass_fail_fecha_jornada_expr(ts_column="ts"):
    return (
        f"CASE WHEN TIME({ts_column}) >= '07:30:00' "
        f"THEN DATE({ts_column}) ELSE DATE(DATE_SUB({ts_column}, INTERVAL 1 DAY)) END"
    )


def _ict_pass_fail_turno_expr(ts_column="ts"):
    return (
        "CASE "
        f"WHEN TIME({ts_column}) >= '07:30:00' AND TIME({ts_column}) < '17:30:00' THEN 'DIA' "
        f"WHEN TIME({ts_column}) >= '17:30:00' AND TIME({ts_column}) < '22:00:00' THEN 'TIEMPO EXTRA' "
        "ELSE 'NOCHE' "
        "END"
    )


def _build_history_ict_pass_fail_summary_query():
    """Construir query para resumen Pass/Fail de ICT por jornada, turno, linea y numero de parte."""
    fecha_desde = (
        request.args.get("fecha_desde", "").strip()
        or request.args.get("fecha", "").strip()
    )
    fecha_hasta = request.args.get("fecha_hasta", "").strip() or fecha_desde
    numero_parte = (
        request.args.get("numero_parte", "").strip()
        or request.args.get("no_parte", "").strip()
    )
    turno = request.args.get("turno", "").strip().upper()
    barcode = (
        request.args.get("barcode", "").strip()
        or request.args.get("barcode_like", "").strip()
    )

    fecha_jornada_expr = _ict_pass_fail_fecha_jornada_expr("ts")
    turno_expr = _ict_pass_fail_turno_expr("ts")

    sql = (
        "SELECT "
        f"{fecha_jornada_expr} AS fecha, "
        "COALESCE(NULLIF(TRIM(linea), ''), 'SIN LINEA') AS linea, "
        "COALESCE(ict, 0) AS ict, "
        f"{turno_expr} AS turno, "
        "COALESCE(NULLIF(TRIM(no_parte), ''), 'SIN NUMERO DE PARTE') AS numero_parte, "
        "COUNT(*) AS total, "
        "SUM(CASE WHEN UPPER(COALESCE(resultado, '')) = 'OK' THEN 1 ELSE 0 END) AS ok_count, "
        "SUM(CASE WHEN UPPER(COALESCE(resultado, '')) = 'NG' THEN 1 ELSE 0 END) AS ng_count "
        "FROM history_ict WHERE 1=1"
    )
    params = []

    if fecha_desde:
        start_date = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
        params.append(datetime.combine(start_date, dt_time(7, 30)))
        sql += " AND ts >= %s"
    if fecha_hasta:
        end_date = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
        params.append(datetime.combine(end_date + timedelta(days=1), dt_time(7, 30)))
        sql += " AND ts < %s"
    if numero_parte:
        sql += " AND no_parte LIKE %s"
        params.append(f"{numero_parte}%")
    if barcode:
        sql += " AND barcode LIKE %s"
        params.append(f"{barcode}%")
    if turno in {"DIA", "TIEMPO EXTRA", "NOCHE"}:
        sql += f" AND {turno_expr}=%s"
        params.append(turno)

    sql += (
        f" GROUP BY {fecha_jornada_expr},"
        " COALESCE(NULLIF(TRIM(linea), ''), 'SIN LINEA'),"
        " COALESCE(ict, 0),"
        f" {turno_expr},"
        " COALESCE(NULLIF(TRIM(no_parte), ''), 'SIN NUMERO DE PARTE')"
        " ORDER BY fecha ASC, linea ASC, ict ASC, FIELD(turno, 'DIA', 'TIEMPO EXTRA', 'NOCHE'), total DESC, numero_parte ASC"
    )

    return sql, tuple(params) if params else None


@app.route("/api/ict/pass-fail")
@login_requerido
def ict_pass_fail_api():
    """Obtener resumen Pass/Fail de ICT con el mismo formato que Vision."""
    try:
        sql, params = _build_history_ict_pass_fail_summary_query()
        rows = execute_query(sql, params, fetch="all") or []

        result = []
        for row in rows:
            total = int(row.get("total") or 0)
            ok_count = int(row.get("ok_count") or 0)
            ng_count = int(row.get("ng_count") or 0)
            porcentaje_ok = round((ok_count / total) * 100, 2) if total else 0
            porcentaje_ng = round((ng_count / total) * 100, 2) if total else 0

            result.append(
                {
                    "fecha": _ict_format_row({"fecha": row.get("fecha")}).get("fecha", ""),
                    "linea": row.get("linea", "") or "",
                    "ict": row.get("ict", "") or "",
                    "turno": row.get("turno", "") or "",
                    "numero_parte": row.get("numero_parte", "") or "",
                    "total": total,
                    "ok_count": ok_count,
                    "ng_count": ng_count,
                    "porcentaje_ok": porcentaje_ok,
                    "porcentaje_ng": porcentaje_ng,
                }
            )

        return jsonify(result)
    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
@app.route("/api/ict/pass-fail/detail")
@login_requerido
def ict_pass_fail_detail_api():
    """Obtener detalle de barcodes para una fila del resumen ICT Pass/Fail."""
    try:
        fecha = request.args.get("fecha", "").strip()
        linea = request.args.get("linea", "").strip()
        ict = request.args.get("ict", "").strip()
        turno = request.args.get("turno", "").strip().upper()
        numero_parte = request.args.get("numero_parte", "").strip()
        barcode = request.args.get("barcode", "").strip()

        try:
            min_intentos = max(
                1, int(request.args.get("min_intentos", "").strip() or 1)
            )
        except ValueError:
            min_intentos = 1

        if not all([fecha, linea, ict, turno, numero_parte]):
            return jsonify({"error": "Faltan filtros para consultar el detalle."}), 400

        if turno not in {"DIA", "TIEMPO EXTRA", "NOCHE"}:
            return jsonify({"error": "Turno invalido para consultar detalle."}), 400

        fecha_jornada = datetime.strptime(fecha, "%Y-%m-%d").date()
        fecha_inicio = datetime.combine(fecha_jornada, dt_time(7, 30))
        fecha_fin = datetime.combine(fecha_jornada + timedelta(days=1), dt_time(7, 30))

        linea_expr = "COALESCE(NULLIF(TRIM(h.linea), ''), 'SIN LINEA')"
        ict_expr = "COALESCE(h.ict, 0)"
        numero_parte_expr = (
            "COALESCE(NULLIF(TRIM(h.no_parte), ''), 'SIN NUMERO DE PARTE')"
        )
        turno_expr = _ict_pass_fail_turno_expr("h.ts")

        sql = (
            "SELECT detalle.barcode, detalle.numero_parte, detalle.linea, "
            "detalle.ict, detalle.turno, detalle.primer_test, detalle.ultimo_test, "
            "detalle.intentos, detalle.ok_count, detalle.ng_count, "
            "detalle.resultado_primer, detalle.resultado_final, "
            "COALESCE(reparacion.defect_count, 0) AS defect_count, "
            "CASE WHEN reparacion.defect_count IS NULL THEN 0 ELSE 1 END AS fue_reparacion, "
            "reparacion.primera_reparacion, "
            "COALESCE(reparacion.defectos, '') AS defectos "
            "FROM ("
            " SELECT h.barcode AS barcode, "
            f" MIN({numero_parte_expr}) AS numero_parte, "
            f" MIN({linea_expr}) AS linea, "
            f" MIN({ict_expr}) AS ict, "
            f" MIN({turno_expr}) AS turno, "
            " MIN(h.ts) AS primer_test, "
            " MAX(h.ts) AS ultimo_test, "
            " COUNT(*) AS intentos, "
            " SUM(CASE WHEN UPPER(COALESCE(h.resultado, '')) = 'OK' THEN 1 ELSE 0 END) AS ok_count, "
            " SUM(CASE WHEN UPPER(COALESCE(h.resultado, '')) = 'NG' THEN 1 ELSE 0 END) AS ng_count, "
            " SUBSTRING_INDEX(GROUP_CONCAT(UPPER(COALESCE(h.resultado, '')) ORDER BY h.ts ASC, h.id ASC SEPARATOR ','), ',', 1) AS resultado_primer, "
            " SUBSTRING_INDEX(GROUP_CONCAT(UPPER(COALESCE(h.resultado, '')) ORDER BY h.ts DESC, h.id DESC SEPARATOR ','), ',', 1) AS resultado_final "
            " FROM history_ict h "
            " WHERE h.ts >= %s AND h.ts < %s "
            f" AND {linea_expr}=%s "
            f" AND {ict_expr}=%s "
            f" AND {turno_expr}=%s "
            f" AND {numero_parte_expr}=%s "
        )
        params = [fecha_inicio, fecha_fin, linea, ict, turno, numero_parte]

        if barcode:
            sql += " AND h.barcode LIKE %s "
            params.append(f"{barcode}%")

        sql += (
            " GROUP BY h.barcode "
            " HAVING COUNT(*) >= %s "
            ") detalle "
            "LEFT JOIN ("
            " SELECT codigo, COUNT(*) AS defect_count, MIN(fecha) AS primera_reparacion, "
            " GROUP_CONCAT(DISTINCT NULLIF(TRIM(defecto), '') ORDER BY defecto SEPARATOR ', ') AS defectos "
            " FROM defect_data GROUP BY codigo"
            ") reparacion ON reparacion.codigo = detalle.barcode "
            "ORDER BY detalle.intentos DESC, detalle.ultimo_test DESC, detalle.barcode ASC"
        )
        params.append(min_intentos)

        rows = execute_query(sql, tuple(params), fetch="all") or []
        formatted_rows = []
        for row in rows:
            formatted = _ict_format_row(row)
            intentos = int(formatted.get("intentos") or 0)
            ok_count = int(formatted.get("ok_count") or 0)
            ng_count = int(formatted.get("ng_count") or 0)
            defect_count = int(formatted.get("defect_count") or 0)
            fue_reparacion = bool(int(formatted.get("fue_reparacion") or 0))
            resultado_primer = (formatted.get("resultado_primer") or "").upper()
            resultado_final = (formatted.get("resultado_final") or "").upper()

            formatted["intentos"] = intentos
            formatted["ok_count"] = ok_count
            formatted["ng_count"] = ng_count
            formatted["defect_count"] = defect_count
            formatted["fue_reparacion"] = fue_reparacion
            formatted["resultado_primer"] = resultado_primer
            formatted["resultado_final"] = resultado_final
            formatted["pass_real"] = resultado_primer == "OK" or (
                fue_reparacion and ok_count > 0
            )
            formatted_rows.append(formatted)

        total_intentos = sum(row["intentos"] for row in formatted_rows)
        ok_total = sum(row["ok_count"] for row in formatted_rows)
        ng_total = sum(row["ng_count"] for row in formatted_rows)
        piezas_unicas = len(formatted_rows)
        piezas_repetidas = sum(1 for row in formatted_rows if row["intentos"] > 1)
        piezas_reparacion = sum(1 for row in formatted_rows if row["fue_reparacion"])
        pass_real = sum(1 for row in formatted_rows if row["pass_real"])
        porcentaje_pass_real = (
            round((pass_real / piezas_unicas) * 100, 2) if piezas_unicas else 0
        )

        return jsonify(
            {
                "summary": {
                    "fecha": fecha,
                    "linea": linea,
                    "ict": ict,
                    "turno": turno,
                    "numero_parte": numero_parte,
                    "total_intentos": total_intentos,
                    "ok_total": ok_total,
                    "ng_total": ng_total,
                    "piezas_unicas": piezas_unicas,
                    "piezas_repetidas": piezas_repetidas,
                    "piezas_reparacion": piezas_reparacion,
                    "pass_real": pass_real,
                    "porcentaje_pass_real": porcentaje_pass_real,
                },
                "rows": formatted_rows,
            }
        )
    except ValueError:
        return jsonify({"error": "Fecha invalida para consultar detalle."}), 400
    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/ict/pass-fail/export")
@login_requerido
def ict_pass_fail_export():
    """Exportar resumen Pass/Fail de ICT a un archivo de Excel."""
    try:
        sql, params = _build_history_ict_pass_fail_summary_query()
        rows = execute_query(sql, params, fetch="all") or []

        from io import BytesIO

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        wb = Workbook()
        ws = wb.active
        ws.title = "ICT Pass Fail"

        header_fill = PatternFill(
            start_color="3f6b6e", end_color="3f6b6e", fill_type="solid"
        )
        cell_fill = PatternFill(
            start_color="a1a09c", end_color="a1a09c", fill_type="solid"
        )
        header_font = Font(bold=True, color="FFFFFF", size=10)
        border = Border(
            left=Side(style="thin", color="000000"),
            right=Side(style="thin", color="000000"),
            top=Side(style="thin", color="000000"),
            bottom=Side(style="thin", color="000000"),
        )

        headers = [
            "Fecha",
            "Linea",
            "ICT",
            "Turno",
            "Numero de parte",
            "Total",
            "OK",
            "NG",
            "% Pass",
            "% Fail",
            "PORCENTAJE",
        ]

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border

        for row_idx, row in enumerate(rows, start=2):
            total = int(row.get("total") or 0)
            ok_count = int(row.get("ok_count") or 0)
            ng_count = int(row.get("ng_count") or 0)
            porcentaje_ok = round((ok_count / total) * 100, 2) if total else 0
            porcentaje_ng = round((ng_count / total) * 100, 2) if total else 0

            values = [
                _ict_format_row({"fecha": row.get("fecha")}).get("fecha", ""),
                row.get("linea", "") or "",
                row.get("ict", "") or "",
                row.get("turno", "") or "",
                row.get("numero_parte", "") or "",
                total,
                ok_count,
                ng_count,
                porcentaje_ok,
                porcentaje_ng,
            ]

            for col_num, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_num, value=value)
                cell.fill = cell_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border

            image_cell = ws.cell(row=row_idx, column=11, value="")
            image_cell.fill = cell_fill
            image_cell.alignment = Alignment(horizontal="center", vertical="center")
            image_cell.border = border

            excel_image = _create_vision_pass_fail_excel_image(
                porcentaje_ok, porcentaje_ng
            )
            ws.add_image(excel_image, f"K{row_idx}")
            ws.row_dimensions[row_idx].height = 24

        column_widths = [14, 20, 10, 18, 28, 14, 12, 12, 14, 14, 58]
        for col_num, width in enumerate(column_widths, start=1):
            column_letter = ws.cell(row=1, column=col_num).column_letter
            ws.column_dimensions[column_letter].width = width

        ws.freeze_panes = "A2"

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = (
            f"historial_ict_pass_fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        return _send_excel_download(output, filename)
    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@app.route("/historial-cambios-parametros-ict-ajax")
@login_requerido
def historial_cambios_parametros_ict_ajax():
    """Ruta AJAX para cargar el Historial de Cambios de Parámetros ICT"""
    try:
        return render_template(
            "Control de resultados/historial_cambios_parametros_ict_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template de Historial Cambios Parámetros ICT: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


def crear_indice_history_ict_audit():
    """Crea indice cubriente para acelerar el modulo de Cambios de Parametros ICT.

    El SQL de _ict_compute_parameter_changes filtra por (ict, ts) y agrupa por
    (no_parte, linea, ict, fuente_archivo). Este indice cubre el WHERE + GROUP BY
    sin tocar la tabla base.
    """
    try:
        execute_query(
            "CREATE INDEX idx_history_ict_audit "
            "ON history_ict (ict, ts, no_parte, linea, fuente_archivo)"
        )
        print("Indice idx_history_ict_audit creado")
    except Exception as e:
        msg = str(e)
        if "1061" in msg or "Duplicate key name" in msg:
            return
        print(f"(info) idx_history_ict_audit no se pudo crear: {e}")


def crear_indice_history_ict_ts_nopart():
    """Indice cubriente para consultas sin filtro por ict (ict_all=1).

    El indice idx_history_ict_audit empieza con (ict, ts, ...). Cuando la query
    omite `AND ict = ?`, MySQL no puede usar el prefijo y cae a un scan completo.
    Este segundo indice arranca en (ts, ...) para cubrir esos casos sin scan.
    """
    try:
        execute_query(
            "CREATE INDEX idx_history_ict_ts_nopart "
            "ON history_ict (ts, no_parte, linea, fuente_archivo)"
        )
        print("Indice idx_history_ict_ts_nopart creado")
    except Exception as e:
        msg = str(e)
        if "1061" in msg or "Duplicate key name" in msg:
            return
        print(f"(info) idx_history_ict_ts_nopart no se pudo crear: {e}")


# Indices history_ict movidos a app/startup_init.py


_ICT_PARAM_JORNADA_START = dt_time(7, 30)

# ----- Progreso de calculo de cambios de parametros ICT -----
# Diccionario en memoria con el progreso de cada request activo, identificado
# por progress_id que envia el frontend. Permite barra de progreso real.
_ICT_PARAM_PROGRESS = {}
_ICT_PARAM_PROGRESS_LOCK = threading.Lock()
_ICT_PARAM_PROGRESS_TTL = 120  # segundos


def _ict_param_progress_set(progress_id, **fields):
    if not progress_id:
        return
    with _ICT_PARAM_PROGRESS_LOCK:
        now = time.monotonic()
        # Evict entradas viejas para evitar crecimiento ilimitado
        stale = [pid for pid, st in _ICT_PARAM_PROGRESS.items()
                 if now - st.get("started", now) > _ICT_PARAM_PROGRESS_TTL]
        for pid in stale:
            _ICT_PARAM_PROGRESS.pop(pid, None)
        state = _ICT_PARAM_PROGRESS.setdefault(progress_id, {"started": now})
        state.update(fields)


def _ict_param_progress_increment(progress_id, by=1):
    if not progress_id:
        return
    with _ICT_PARAM_PROGRESS_LOCK:
        state = _ICT_PARAM_PROGRESS.get(progress_id)
        if state:
            state["done"] = state.get("done", 0) + by


_ICT_PARAM_CHANGE_FIELDS = (
    ("std_value", "STD"),
    ("std_unit", "UNIT (STD)"),
    ("hlim_pct", "HLIM %"),
    ("llim_pct", "LLIM %"),
    ("hp_value", "HP"),
    ("lp_value", "LP"),
    ("ws_value", "WS"),
    ("ds_value", "DS"),
    ("rc_value", "RC"),
    ("p_flag", "P"),
    ("j_flag", "J"),
)


def _ict_param_parse_date(value, field_name):
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{field_name} es requerido.")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} debe tener formato YYYY-MM-DD.") from exc


def _ict_param_parse_time(value, field_name):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"{field_name} debe tener formato HH:MM.")


def _ict_param_as_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, dt_time.min)
    if isinstance(value, str):
        raw = value.strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
    return None


def _ict_param_parse_ict_filter(raw_value):
    raw = (raw_value or "").strip().upper()
    if not raw:
        raise ValueError("ICT es requerido.")

    ict_match = re.search(r"\bICT\s*([0-9]+)\b", raw)
    if ict_match:
        ict_value = int(ict_match.group(1))
    elif raw.isdigit():
        ict_value = int(raw)
    else:
        raise ValueError("ICT debe ser un numero o texto como ICT1.")

    line_match = re.search(r"\b(M|DP|H)\s*([0-9]+)\b", raw)
    line_value = f"{line_match.group(1)}{line_match.group(2)}" if line_match else ""
    return ict_value, line_value


def _ict_param_format_ict(linea, ict):
    linea = str(linea or "").strip()
    ict = str(ict or "").strip()
    if linea and ict:
        return f"{linea} ICT{ict}"
    if ict:
        return f"ICT{ict}"
    return linea


def _ict_param_jornada_label(ts_value):
    ts = _ict_param_as_datetime(ts_value)
    if not ts:
        return ""
    jornada = ts.date() if ts.time() >= _ICT_PARAM_JORNADA_START else ts.date() - timedelta(days=1)
    return jornada.isoformat()


def _ict_param_time_allowed(ts_value, hora_desde, hora_hasta):
    ts = _ict_param_as_datetime(ts_value)
    if not ts:
        return False
    current = ts.time()
    if hora_desde and hora_hasta:
        if hora_desde <= hora_hasta:
            return hora_desde <= current <= hora_hasta
        return current >= hora_desde or current <= hora_hasta
    if hora_desde:
        return current >= hora_desde
    if hora_hasta:
        return current <= hora_hasta
    return True


def _ict_param_compare_token(value):
    if value is None:
        return ("empty", "")
    raw = str(value).strip()
    if raw == "":
        return ("empty", "")
    try:
        return ("num", Decimal(raw.replace(",", "")).normalize())
    except Exception:
        return ("text", raw.upper())


def _ict_param_display_value(value):
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, float):
        return f"{value:g}"
    return str(value).strip()


def _ict_param_component_label(componente, pinref):
    componente = str(componente or "").strip()
    pinref = str(pinref or "").strip()
    if componente and pinref:
        return f"{componente} / {pinref}"
    return componente or pinref


def _ict_param_build_snapshot(param_rows):
    """Snapshot por (componente, pinref) con valores crudos y tokens
    precomputados.

    Estructura: {(comp, pin): {"values": {field: raw}, "tokens": {field: token}}}.
    Precomputar el token (que invoca Decimal.normalize) ahorra ~22k normalizaciones
    por grupo en el bucle de comparacion.
    """
    snapshot = {}
    fields = _ICT_PARAM_CHANGE_FIELDS
    for row in param_rows:
        componente = str(row.get("componente") or "").strip()
        pinref = str(row.get("pinref") or "").strip()
        if not componente and not pinref:
            continue
        values = {}
        tokens = {}
        for field_key, _label in fields:
            v = row.get(field_key)
            values[field_key] = v
            tokens[field_key] = _ict_param_compare_token(v)
        snapshot[(componente, pinref)] = {"values": values, "tokens": tokens}
    return snapshot


def _ict_param_load_snapshot(source_file, barcode, warnings):
    source_file = str(source_file or "").strip()
    barcode = str(barcode or "").strip()
    if not source_file:
        warnings.append("Se omitio un registro sin fuente_archivo.")
        return None
    if not barcode:
        warnings.append(f"Se omitio {source_file}: no tiene barcode representativo.")
        return None

    try:
        lgd_path = resolve_lgd_path(source_file)
        param_rows = get_lgd_parameters_for_barcode(str(lgd_path), barcode)
    except (IctLgdError, OSError) as exc:
        warnings.append(f"No se pudo leer {source_file}: {exc}")
        return None
    except Exception as exc:
        warnings.append(f"No se pudo parsear {source_file}: {exc}")
        return None

    if not param_rows:
        warnings.append(f"Sin parametros para {barcode} en {source_file}.")
        return None
    return _ict_param_build_snapshot(param_rows)


def _ict_compute_parameter_changes(
    fecha_desde,
    fecha_hasta,
    hora_desde,
    hora_hasta,
    ict_filter,
    no_parte_filter="",
    componente_filter="",
    parametro_filter="",
    limit=1000,
    ict_all=False,
    progress_id=None,
):
    _ict_param_progress_set(progress_id, total=0, done=0, phase="iniciando")
    start_date = _ict_param_parse_date(fecha_desde, "fecha_desde")
    end_date = _ict_param_parse_date(fecha_hasta or fecha_desde, "fecha_hasta")
    if end_date < start_date:
        raise ValueError("fecha_hasta no puede ser menor que fecha_desde.")

    if ict_all:
        ict_value = None
        line_filter = ""
    else:
        ict_value, line_filter = _ict_param_parse_ict_filter(ict_filter)
    hora_desde_value = _ict_param_parse_time(hora_desde, "hora_desde")
    hora_hasta_value = _ict_param_parse_time(hora_hasta, "hora_hasta")
    no_parte_filter = (no_parte_filter or "").strip()
    componente_filter = (componente_filter or "").strip().lower()
    parametro_filter = (parametro_filter or "").strip().lower()

    jornada_start = datetime.combine(start_date, _ICT_PARAM_JORNADA_START)
    jornada_end = datetime.combine(end_date + timedelta(days=1), _ICT_PARAM_JORNADA_START)

    sql = (
        "SELECT MIN(barcode) AS barcode, MIN(ts) AS first_ts, "
        "COALESCE(NULLIF(TRIM(no_parte), ''), 'SIN NUMERO DE PARTE') AS no_parte, "
        "COALESCE(NULLIF(TRIM(linea), ''), 'SIN LINEA') AS linea, "
        "ict, fuente_archivo "
        "FROM history_ict "
        "WHERE ts >= %s AND ts < %s "
        "AND fuente_archivo IS NOT NULL AND fuente_archivo <> ''"
    )
    params = [jornada_start, jornada_end]

    if ict_value is not None:
        sql += " AND ict = %s"
        params.append(ict_value)
    if line_filter:
        sql += " AND linea = %s"
        params.append(line_filter)
    if no_parte_filter:
        sql += " AND no_parte LIKE %s"
        params.append(f"{no_parte_filter}%")

    sql += (
        " GROUP BY "
        "COALESCE(NULLIF(TRIM(no_parte), ''), 'SIN NUMERO DE PARTE'), "
        "COALESCE(NULLIF(TRIM(linea), ''), 'SIN LINEA'), "
        "ict, fuente_archivo "
        "ORDER BY no_parte ASC, linea ASC, ict ASC, first_ts ASC"
    )

    _ict_param_progress_set(progress_id, phase="consultando_db")
    source_rows = execute_query(sql, tuple(params), fetch="all") or []
    warnings = []
    warnings_lock = threading.Lock()

    # Modo "pares consecutivos": para cada grupo (linea, ict, no_parte)
    # ordenamos los archivos .lgd por ts y comparamos cada par consecutivo
    # (i, i+1). Esto detecta cambios intermedios (ej. 0->5->0) que un modo
    # primer-vs-ultimo perderia. Cada flip distinto se emite como una fila.
    groups_raw = {}
    for source_row in source_rows:
        ts = _ict_param_as_datetime(source_row.get("first_ts"))
        if not ts or not _ict_param_time_allowed(ts, hora_desde_value, hora_hasta_value):
            continue
        source_file = source_row.get("fuente_archivo") or ""
        if not source_file:
            continue
        gkey = (
            str(source_row.get("linea") or ""),
            str(source_row.get("ict") or ""),
            str(source_row.get("no_parte") or ""),
        )
        groups_raw.setdefault(gkey, []).append({
            "ts": ts,
            "source_file": source_file,
            "barcode": source_row.get("barcode") or "",
        })

    plan = {}  # gkey -> [items ordenados, archivos distintos consecutivos]
    for gkey, items in groups_raw.items():
        items.sort(key=lambda item: item["ts"])
        deduped = []
        for it in items:
            if deduped and deduped[-1]["source_file"] == it["source_file"]:
                continue
            deduped.append(it)
        if len(deduped) >= 2:
            plan[gkey] = deduped

    unique_files = {}
    for items in plan.values():
        for it in items:
            existing = unique_files.get(it["source_file"])
            if existing is None or it["ts"] < existing[0]:
                unique_files[it["source_file"]] = (it["ts"], it["barcode"])

    _ict_param_progress_set(
        progress_id,
        total=len(unique_files),
        done=0,
        phase="parseando_archivos",
    )

    def _parse_one(item):
        source_file, (_ts, barcode) = item
        local_warnings = []
        snapshot = _ict_param_load_snapshot(source_file, barcode, local_warnings)
        _ict_param_progress_increment(progress_id)
        return source_file, snapshot, local_warnings

    snapshot_by_file = {}
    if unique_files:
        max_workers = min(8, len(unique_files))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for source_file, snapshot, local_warnings in executor.map(_parse_one, list(unique_files.items())):
                snapshot_by_file[source_file] = snapshot
                if local_warnings:
                    with warnings_lock:
                        warnings.extend(local_warnings)

    _ict_param_progress_set(progress_id, phase="detectando_cambios")
    files_read = sum(1 for snap in snapshot_by_file.values() if snap is not None)

    # Optimizacion 1: filtrar campos por parametro_filter UNA VEZ por request,
    # no por (par x componente).
    fields_to_check = [
        (k, l) for k, l in _ICT_PARAM_CHANGE_FIELDS
        if not parametro_filter or parametro_filter in l.lower()
    ]

    events = []
    grupos_con_cambios = 0
    if fields_to_check:
        for gkey in sorted(plan):
            items = plan[gkey]
            linea_value, ict_value_g, no_parte_value = gkey
            grupo_tuvo_cambio = False
            # Optimizacion 2: cachear shared_keys del grupo (interseccion de
            # (comp, pin)). Se invalida solo si cambia la identidad del par de
            # snapshots, lo cual rara vez sucede dentro del mismo grupo.
            shared_keys_cache = None

            for previous, current in zip(items, items[1:]):
                prev_snapshot = snapshot_by_file.get(previous["source_file"])
                curr_snapshot = snapshot_by_file.get(current["source_file"])
                if prev_snapshot is None or curr_snapshot is None:
                    continue

                if (
                    shared_keys_cache is None
                    or shared_keys_cache[0] is not prev_snapshot
                    or shared_keys_cache[1] is not curr_snapshot
                ):
                    shared = sorted(
                        set(prev_snapshot.keys()) & set(curr_snapshot.keys()),
                        key=lambda item: (item[0], item[1]),
                    )
                    if componente_filter:
                        shared = [
                            ck for ck in shared
                            if componente_filter in _ict_param_component_label(*ck).lower()
                        ]
                    shared_keys_cache = (prev_snapshot, curr_snapshot, shared)
                shared_keys = shared_keys_cache[2]

                for comp_key in shared_keys:
                    componente_raw, pinref_raw = comp_key
                    prev_cell = prev_snapshot[comp_key]
                    curr_cell = curr_snapshot[comp_key]
                    prev_tokens = prev_cell["tokens"]
                    curr_tokens = curr_cell["tokens"]
                    prev_values = prev_cell["values"]
                    curr_values = curr_cell["values"]
                    component_label = None  # lazy

                    for field_key, field_label in fields_to_check:
                        # Optimizacion 3: comparacion con tokens precomputados,
                        # cero llamadas a Decimal.normalize en este bucle.
                        if prev_tokens[field_key] == curr_tokens[field_key]:
                            continue
                        if component_label is None:
                            component_label = _ict_param_component_label(componente_raw, pinref_raw)

                        grupo_tuvo_cambio = True
                        events.append({
                            "jornada": _ict_param_jornada_label(current["ts"]),
                            "hora_anterior": previous["ts"].strftime("%H:%M:%S"),
                            "hora_cambio": current["ts"].strftime("%H:%M:%S"),
                            "ict": _ict_param_format_ict(linea_value, ict_value_g),
                            "ict_num": ict_value_g,
                            "linea": linea_value,
                            "no_parte": no_parte_value,
                            "std": no_parte_value,
                            "componente": component_label,
                            "componente_raw": componente_raw,
                            "pinref": pinref_raw,
                            "parametro": field_label,
                            "field_key": field_key,
                            "valor_anterior": _ict_param_display_value(prev_values[field_key]),
                            "valor_nuevo": _ict_param_display_value(curr_values[field_key]),
                            "archivo_anterior": previous["source_file"],
                            "archivo_cambio": current["source_file"],
                            "barcode_anterior": previous["barcode"],
                            "barcode_cambio": current["barcode"],
                        })
            if grupo_tuvo_cambio:
                grupos_con_cambios += 1

    events.sort(
        key=lambda row: (row.get("jornada", ""), row.get("hora_cambio", "")),
        reverse=True,
    )
    total_events = len(events)
    limited_events = events[:limit] if limit else events
    file_warning_count = len(warnings)
    if limit and total_events > limit:
        warnings.append(f"Se muestran {limit} de {total_events} cambios. Use filtros para reducir la consulta.")

    _ict_param_progress_set(progress_id, phase="completado")

    return {
        "rows": limited_events,
        "warnings": warnings,
        "meta": {
            "archivos_consultados": len(source_rows),
            "grupos_total": len(groups_raw),
            "grupos_con_cambios": grupos_con_cambios,
            "archivos_unicos": len(unique_files),
            "archivos_leidos": files_read,
            "archivos_faltantes": file_warning_count,
            "eventos": total_events,
            "limite": limit,
            "jornada_inicio": jornada_start.strftime("%Y-%m-%d %H:%M:%S"),
            "jornada_fin": jornada_end.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }


@app.route("/api/ict/param-changes/progress")
@login_requerido
def ict_param_changes_progress():
    """Devuelve el progreso del calculo de cambios de parametros ICT.

    El frontend manda progress_id al iniciar la consulta principal y luego
    pollea este endpoint para alimentar la barra de progreso.
    """
    pid = request.args.get("id", "").strip()
    with _ICT_PARAM_PROGRESS_LOCK:
        state = _ICT_PARAM_PROGRESS.get(pid)
        if not state:
            return jsonify({"total": 0, "done": 0, "phase": "desconocido"})
        return jsonify({
            "total": state.get("total", 0),
            "done": state.get("done", 0),
            "phase": state.get("phase", ""),
        })


@app.route("/api/ict/param-changes")
@login_requerido
def ict_param_changes_api():
    """API para obtener cambios de parametros ICT desde archivos LGD locales."""
    try:
        fecha = request.args.get("fecha", "").strip()
        fecha_desde = request.args.get("fecha_desde", "").strip()
        fecha_hasta = request.args.get("fecha_hasta", "").strip()
        payload = _ict_compute_parameter_changes(
            fecha_desde=fecha_desde or fecha,
            fecha_hasta=fecha_hasta or fecha_desde or fecha,
            hora_desde=request.args.get("hora_desde", "").strip(),
            hora_hasta=request.args.get("hora_hasta", "").strip(),
            ict_filter=request.args.get("ict", "").strip(),
            no_parte_filter=(
                request.args.get("no_parte", "").strip()
                or request.args.get("numero_parte", "").strip()
                or request.args.get("std", "").strip()
            ),
            componente_filter=request.args.get("componente", "").strip(),
            parametro_filter=request.args.get("parametro", "").strip(),
            limit=1000,
            ict_all=request.args.get("ict_all", "").strip() == "1",
            progress_id=request.args.get("progress_id", "").strip() or None,
        )
        return jsonify(payload)
    except ValueError as e:
        return jsonify({"error": str(e), "rows": [], "warnings": [], "meta": {}}), 400
    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/ict/param-changes/export")
@login_requerido
def ict_param_changes_export():
    """Exportar cambios de parametros ICT calculados desde LGD locales."""
    try:
        fecha = request.args.get("fecha", "").strip()
        fecha_desde = request.args.get("fecha_desde", "").strip()
        fecha_hasta = request.args.get("fecha_hasta", "").strip()
        payload = _ict_compute_parameter_changes(
            fecha_desde=fecha_desde or fecha,
            fecha_hasta=fecha_hasta or fecha_desde or fecha,
            hora_desde=request.args.get("hora_desde", "").strip(),
            hora_hasta=request.args.get("hora_hasta", "").strip(),
            ict_filter=request.args.get("ict", "").strip(),
            no_parte_filter=(
                request.args.get("no_parte", "").strip()
                or request.args.get("numero_parte", "").strip()
                or request.args.get("std", "").strip()
            ),
            componente_filter=request.args.get("componente", "").strip(),
            parametro_filter=request.args.get("parametro", "").strip(),
            limit=5000,
            ict_all=request.args.get("ict_all", "").strip() == "1",
            progress_id=request.args.get("progress_id", "").strip() or None,
        )
        rows = payload.get("rows", [])

        from io import BytesIO

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = "Cambios Parametros ICT"

        headers = [
            "Jornada",
            "Hora Anterior",
            "Hora Cambio",
            "ICT",
            "Linea",
            "No Parte",
            "Componente",
            "Parametro",
            "Valor Anterior",
            "Valor Nuevo",
            "Archivo Anterior",
            "Archivo Cambio",
        ]
        header_fill = PatternFill(
            start_color="1F4E79", end_color="1F4E79", fill_type="solid"
        )
        header_font = Font(color="FFFFFF", bold=True)

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        for row_idx, row in enumerate(rows, 2):
            ws.cell(row=row_idx, column=1, value=row.get("jornada", "") or "")
            ws.cell(row=row_idx, column=2, value=row.get("hora_anterior", "") or "")
            ws.cell(row=row_idx, column=3, value=row.get("hora_cambio", "") or "")
            ws.cell(row=row_idx, column=4, value=row.get("ict", "") or "")
            ws.cell(row=row_idx, column=5, value=row.get("linea", "") or "")
            ws.cell(row=row_idx, column=6, value=row.get("no_parte", "") or "")
            ws.cell(row=row_idx, column=7, value=row.get("componente", "") or "")
            ws.cell(row=row_idx, column=8, value=row.get("parametro", "") or "")
            ws.cell(row=row_idx, column=9, value=row.get("valor_anterior", "") or "")
            ws.cell(row=row_idx, column=10, value=row.get("valor_nuevo", "") or "")
            ws.cell(row=row_idx, column=11, value=row.get("archivo_anterior", "") or "")
            ws.cell(row=row_idx, column=12, value=row.get("archivo_cambio", "") or "")

        col_widths = [12, 12, 12, 14, 8, 22, 25, 22, 20, 20, 48, 48]
        for col_idx, width in enumerate(col_widths, 1):
            ws.column_dimensions[
                ws.cell(row=1, column=col_idx).column_letter
            ].width = width
        ws.freeze_panes = "A2"

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = (
            f"cambios_parametros_ict_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        return _send_excel_download(output, filename)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback

        print(f"Error exportando Cambios Parámetros ICT: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/ict/param-changes/detail")
@login_requerido
def ict_param_changes_detail():
    """Localiza el archivo .lgd mas temprano donde aparece valor_nuevo para un
    parametro especifico de un (linea, ict, no_parte). Usa busqueda binaria
    sobre los archivos del rango y un barrido lineal hacia atras para
    parametros que oscilan."""
    try:
        fecha = request.args.get("fecha", "").strip()
        fecha_desde_raw = request.args.get("fecha_desde", "").strip() or fecha
        fecha_hasta_raw = (
            request.args.get("fecha_hasta", "").strip()
            or fecha_desde_raw
            or fecha
        )
        linea = request.args.get("linea", "").strip()
        ict_raw = request.args.get("ict", "").strip()
        no_parte = request.args.get("no_parte", "").strip()
        componente = request.args.get("componente", "")
        pinref = request.args.get("pinref", "")
        field_key = request.args.get("parametro", "").strip()
        valor_nuevo = request.args.get("valor_nuevo", "")

        valid_fields = {fk for fk, _ in _ICT_PARAM_CHANGE_FIELDS}
        if field_key not in valid_fields:
            return jsonify({"error": "Parametro desconocido."}), 400
        if not no_parte:
            return jsonify({"error": "no_parte es requerido."}), 400
        if not ict_raw:
            return jsonify({"error": "ict es requerido."}), 400

        try:
            ict_value = int(ict_raw)
        except ValueError:
            return jsonify({"error": "ict debe ser numerico."}), 400

        start_date = _ict_param_parse_date(fecha_desde_raw, "fecha_desde")
        end_date = _ict_param_parse_date(fecha_hasta_raw, "fecha_hasta")
        if end_date < start_date:
            return jsonify({"error": "fecha_hasta no puede ser menor que fecha_desde."}), 400

        jornada_start = datetime.combine(start_date, _ICT_PARAM_JORNADA_START)
        jornada_end = datetime.combine(end_date + timedelta(days=1), _ICT_PARAM_JORNADA_START)

        sql = (
            "SELECT MIN(barcode) AS barcode, MIN(ts) AS first_ts, fuente_archivo "
            "FROM history_ict "
            "WHERE ts >= %s AND ts < %s "
            "AND ict = %s AND no_parte = %s "
            "AND fuente_archivo IS NOT NULL AND fuente_archivo <> ''"
        )
        params = [jornada_start, jornada_end, ict_value, no_parte]
        if linea:
            sql += " AND linea = %s"
            params.append(linea)
        sql += (
            " GROUP BY fuente_archivo "
            "ORDER BY first_ts ASC"
        )

        rows = execute_query(sql, tuple(params), fetch="all") or []
        files = []
        for row in rows:
            ts = _ict_param_as_datetime(row.get("first_ts"))
            source_file = row.get("fuente_archivo") or ""
            barcode = row.get("barcode") or ""
            if not ts or not source_file:
                continue
            files.append({"ts": ts, "file": source_file, "barcode": barcode})

        if not files:
            return jsonify({"found": False, "reason": "Sin archivos en el rango."})

        target_token = _ict_param_compare_token(valor_nuevo)
        comp_key = (str(componente or ""), str(pinref or ""))
        snap_cache = {}
        warnings_local = []

        def _matches(idx):
            entry = files[idx]
            cache_key = (entry["file"], entry["barcode"])
            snap = snap_cache.get(cache_key)
            if snap is None and cache_key not in snap_cache:
                snap = _ict_param_load_snapshot(
                    entry["file"], entry["barcode"], warnings_local
                )
                snap_cache[cache_key] = snap
            if snap is None:
                return None  # archivo no leible
            cell = snap.get(comp_key)
            if cell is None:
                return False
            # Snapshot ahora tiene la forma {"values": {...}, "tokens": {...}}.
            # Usamos los tokens precomputados para evitar Decimal.normalize aqui.
            return cell["tokens"].get(field_key) == target_token

        last_idx = len(files) - 1
        last_match = _matches(last_idx)
        if last_match is None:
            return jsonify({"found": False, "reason": "No se pudo leer el ultimo archivo."})
        if last_match is False:
            return jsonify({"found": False, "reason": "El valor nuevo no aparece en archivos posteriores."})

        lo, hi = 0, last_idx
        while lo < hi:
            mid = (lo + hi) // 2
            mid_match = _matches(mid)
            if mid_match is True:
                hi = mid
            else:
                # archivo no leible o sin valor_nuevo: buscar mas adelante
                lo = mid + 1

        # Barrido lineal hacia atras para tolerar oscilaciones
        while lo > 0:
            prev_match = _matches(lo - 1)
            if prev_match is True:
                lo -= 1
            else:
                break

        target = files[lo]
        return jsonify({
            "found": True,
            "hora": target["ts"].strftime("%H:%M:%S"),
            "fecha": target["ts"].strftime("%Y-%m-%d"),
            "ts": target["ts"].strftime("%Y-%m-%d %H:%M:%S"),
            "archivo": target["file"],
            "barcode": target["barcode"],
            "archivos_consultados": len(files),
            "archivos_parseados": len(snap_cache),
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/historial-aoi-ajax")
@login_requerido
def historial_aoi_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Historial AOI"""
    try:
        return render_template("Control de resultados/Historial AOI.html")
    except Exception as e:
        print(f"Error al cargar template de Historial AOI: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


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


@app.route("/consultar_especificacion_por_numero_parte")
@login_requerido
def consultar_especificacion_por_numero_parte():
    """Consultar especificación de material por número de parte directamente en BD"""
    try:
        numero_parte = request.args.get("numero_parte", "").strip()

        if not numero_parte:
            return jsonify(
                {"success": False, "error": "Número de parte requerido"}
            ), 400

        print(f" Consultando especificación para número de parte: {numero_parte}")

        # Consultar en la tabla de materiales usando get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Intentar diferentes consultas para encontrar el material
        consultas = [
            "SELECT * FROM materiales WHERE numero_parte = %s",
            "SELECT * FROM materiales WHERE TRIM(numero_parte) = %s",
            "SELECT * FROM materiales WHERE numero_parte LIKE ?",
            "SELECT * FROM materiales WHERE codigo_material = %s",
            "SELECT * FROM materiales WHERE codigo_material_original = %s",
        ]

        material_encontrado = None

        for consulta in consultas:
            if "LIKE" in consulta:
                parametro = f"%{numero_parte}%"
            else:
                parametro = numero_parte

            print(f" Ejecutando consulta: {consulta} con parámetro: {parametro}")

            try:
                cursor.execute(consulta, (parametro,))
                result = cursor.fetchone()

                if result:
                    material_encontrado = result
                    break
            except Exception as consulta_error:
                print(f" Error en consulta: {consulta_error}")
                continue

        if not material_encontrado:
            print(f" No se encontró material con número de parte: {numero_parte}")
            conn.close()
            return jsonify(
                {
                    "success": False,
                    "error": f"No se encontró material con número de parte: {numero_parte}",
                }
            )

        # Convertir resultado a diccionario
        # Obtener nombres de columnas usando MySQL
        cursor.execute("DESCRIBE materiales")
        columns_result = cursor.fetchall()
        column_names = (
            [col["Field"] for col in columns_result] if columns_result else []
        )

        # Crear diccionario con nombres de columnas
        material_dict = {}
        for i, value in enumerate(material_encontrado):
            if i < len(column_names):
                material_dict[column_names[i]] = value

        conn.close()
        print(f"📦 Material completo encontrado: {material_dict}")

        # Buscar especificación en diferentes campos posibles
        campos_especificacion = [
            "especificacion_material",
            "especificacion",
            "descripcion_material",
            "descripcion",
            "nombre_material",
            "descripcion_completa",
        ]

        especificacion_encontrada = None
        campo_usado = None

        for campo in campos_especificacion:
            if (
                campo in material_dict
                and material_dict[campo]
                and str(material_dict[campo]).strip()
            ):
                especificacion_encontrada = str(material_dict[campo]).strip()
                campo_usado = campo
                print(
                    f" Especificación encontrada en campo '{campo}': {especificacion_encontrada}"
                )
                break

        if not especificacion_encontrada:
            # Si no encontramos especificación directa, buscar campos descriptivos largos
            campos_descriptivos = []
            for key, value in material_dict.items():
                if (
                    isinstance(value, str)
                    and len(value) > 15
                    and not any(
                        x in key.lower()
                        for x in ["codigo", "numero", "cantidad", "fecha", "id"]
                    )
                ):
                    campos_descriptivos.append((key, value))

            if campos_descriptivos:
                especificacion_encontrada = campos_descriptivos[0][1]
                campo_usado = campos_descriptivos[0][0]
                print(
                    f"💡 Usando campo descriptivo '{campo_usado}': {especificacion_encontrada}"
                )

        if especificacion_encontrada:
            return jsonify(
                {
                    "success": True,
                    "especificacion": especificacion_encontrada,
                    "campo_origen": campo_usado,
                    "numero_parte": numero_parte,
                    "material_completo": material_dict,
                }
            )
        else:
            print(f" No se encontró especificación para el material")
            print(f" Campos disponibles: {list(material_dict.keys())}")
            return jsonify(
                {
                    "success": False,
                    "error": "No se encontró especificación en el material",
                    "material_disponible": material_dict,
                    "campos_disponibles": list(material_dict.keys()),
                }
            )

    except Exception as e:
        print(f" Error consultando especificación: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500


@app.route("/obtener_reglas_escaneo")
def obtener_reglas_escaneo():
    """Endpoint para obtener las reglas de escaneo desde rules.json"""
    try:
        ruta_rules = os.path.join(os.path.dirname(__file__), "database", "rules.json")
        ruta_rules = os.path.abspath(ruta_rules)

        if os.path.exists(ruta_rules):
            with open(ruta_rules, "r", encoding="utf-8") as f:
                reglas = json.load(f)
            return jsonify(reglas)
        else:
            print(f" Archivo rules.json no encontrado en: {ruta_rules}")
            return jsonify({}), 404

    except Exception as e:
        print(f" Error al cargar reglas de escaneo: {str(e)}")
        return jsonify({"error": str(e)}), 500


# === BUSCAR POR CODIGO MATERIAL RECIBIDO ===
@app.route("/buscar_codigo_recibido")
@login_requerido
def buscar_codigo_recibido():
    codigo = request.args.get("codigo_material_recibido")
    print(f" SERVER: Recibida petición para código: '{codigo}'")
    print(f" SERVER: Usuario en sesión: {session.get('usuario', 'No logueado')}")

    if not codigo:
        print(" SERVER: Código no proporcionado")
        return jsonify({"success": False, "error": "Código no proporcionado"})

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print(f" SERVER: Buscando en BD: {codigo}")
        cursor.execute(
            "SELECT * FROM control_material_almacen WHERE codigo_material_recibido = %s",
            (codigo,),
        )
        row = cursor.fetchone()

        if row:
            print(" SERVER: Registro encontrado en BD")
            # Convertir a dict usando nombres de columna
            columns = [desc[0] for desc in cursor.description]
            registro = dict(zip(columns, row))
            print(f"📦 SERVER: Datos encontrados: {registro}")
            return jsonify({"success": True, "registro": registro})
        else:
            print(" SERVER: Código no encontrado en almacén")
            return jsonify(
                {"success": False, "error": "Código no encontrado en almacén"}
            )

    except Exception as e:
        print(f"💥 SERVER: Error en buscar_codigo_recibido: {str(e)}")
        return jsonify({"success": False, "error": f"Error al buscar: {str(e)}"}), 500

    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass


# === GUARDAR SALIDA DE LOTE ===
@app.route("/guardar_salida_lote", methods=["POST"])
@login_requerido
def guardar_salida_lote():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        codigo_material_recibido = data.get("codigo_material_recibido")
        cantidad_salida = data.get("cantidad_salida")

        if not codigo_material_recibido or not cantidad_salida:
            return jsonify({"success": False, "error": "Faltan datos requeridos"})

        conn = get_db_connection()
        cursor = conn.cursor()

        # Consultar la fila original con propiedad de material
        cursor.execute(
            """
            SELECT cma.cantidad_actual, cma.propiedad_material
            FROM control_material_almacen cma
            WHERE cma.codigo_material_recibido = %s
        """,
            (codigo_material_recibido,),
        )
        row = cursor.fetchone()

        if not row:
            return jsonify(
                {"success": False, "error": "Código no encontrado en almacén"}
            )

        cantidad_actual = float(row[0]) if row[0] else 0
        propiedad_material_real = (
            row[1] if row[1] else data.get("especificacion_material", "")
        )
        cantidad_salida = float(cantidad_salida)

        if cantidad_salida > cantidad_actual:
            return jsonify(
                {
                    "success": False,
                    "error": f"Cantidad de salida ({cantidad_salida}) mayor a la disponible ({cantidad_actual})",
                }
            )

        nueva_cantidad = cantidad_actual - cantidad_salida

        # Actualizar la cantidad en almacen
        cursor.execute(
            "UPDATE control_material SET cantidad_actual = %s WHERE codigo_material_recibido = %s",
            (nueva_cantidad, codigo_material_recibido),
        )

        # Obtener el numero_parte desde control_material_almacen
        cursor.execute(
            """
            SELECT numero_parte, especificacion
            FROM control_material_almacen
            WHERE codigo_material_recibido = %s
            LIMIT 1
        """,
            (codigo_material_recibido,),
        )

        resultado_almacen = cursor.fetchone()
        numero_parte_real = (
            resultado_almacen[0] if resultado_almacen else codigo_material_recibido
        )
        especificacion_real = (
            resultado_almacen[1]
            if resultado_almacen
            else data.get("especificacion_material", "")
        )

        # Registrar la salida en control_material_salida CON numero_parte
        cursor.execute(
            """
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida,
                proceso_salida, cantidad_salida, fecha_salida, especificacion_material
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                codigo_material_recibido,
                numero_parte_real,  # NUEVO: numero_parte desde almacen
                data.get("numero_lote", ""),
                data.get("modelo", ""),
                data.get("depto_salida", ""),
                data.get("proceso_salida", ""),
                cantidad_salida,
                data.get("fecha_salida", ""),
                especificacion_real,  # MEJORADO: especificacion desde almacen
            ),
        )

        conn.commit()
        return jsonify({"success": True, "message": "Salida registrada exitosamente"})

    except Exception as e:
        print(f"Error en guardar_salida_lote: {str(e)}")
        return jsonify({"success": False, "error": f"Error al guardar: {str(e)}"}), 500

    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass


# === CONSULTAR HISTORIAL DE SALIDAS ===
@app.route("/consultar_historial_salidas")
@login_requerido
def consultar_historial_salidas():
    conn = None
    cursor = None
    try:
        # Obtener parámetros de filtro (soportar ambos nombres para compatibilidad)
        fecha_inicio = request.args.get("fecha_inicio") or request.args.get(
            "fecha_desde"
        )
        fecha_fin = request.args.get("fecha_fin") or request.args.get("fecha_hasta")
        numero_lote = request.args.get("numero_lote", "").strip()
        codigo_material = request.args.get("codigo_material", "").strip()

        print(
            f" Filtros recibidos - fecha_desde: {fecha_inicio}, fecha_hasta: {fecha_fin}, codigo_material: {codigo_material}, numero_lote: {numero_lote}"
        )

        # Crear clave de caché simple
        cache_key = f"{fecha_inicio}_{fecha_fin}_{codigo_material}_{numero_lote}"

        conn = get_db_connection()
        cursor = conn.cursor()

        # Construir la consulta SQL optimizada para velocidad y sin duplicados
        query = """
            SELECT DISTINCT
                s.fecha_salida,
                s.proceso_salida,
                s.codigo_material_recibido,
                COALESCE(a.codigo_material, s.codigo_material_recibido) as codigo_material,
                COALESCE(a.numero_parte, '') as numero_parte,
                s.cantidad_salida as disp,
                0 as hist,
                COALESCE(a.codigo_material_original, '') as codigo_material_original,
                s.numero_lote,
                s.modelo as maquina_linea,
                s.depto_salida as departamento,
                COALESCE(s.especificacion_material, a.especificacion, '') as especificacion_material
            FROM control_material_salida s
            LEFT JOIN control_material_almacen a ON s.codigo_material_recibido = a.codigo_material_recibido
            WHERE 1=1
        """

        params = []

        if fecha_inicio:
            query += " AND DATE(s.fecha_salida) >= %s"
            params.append(fecha_inicio)

        if fecha_fin:
            query += " AND DATE(s.fecha_salida) <= %s"
            params.append(fecha_fin)

        if numero_lote:
            query += " AND s.numero_lote LIKE %s"
            params.append(f"%{numero_lote}%")

        if codigo_material:
            query += " AND (s.codigo_material_recibido LIKE %s OR a.codigo_material LIKE %s OR a.codigo_material_original LIKE %s)"
            params.extend(
                [f"%{codigo_material}%", f"%{codigo_material}%", f"%{codigo_material}%"]
            )

        # Optimizar ORDER BY y agregar LIMIT para velocidad máxima
        query += " ORDER BY s.fecha_salida DESC LIMIT 500"

        print(f"✓ SQL Query ULTRA-OPTIMIZADO: {query}")
        print(f" SQL Params: {params}")

        cursor.execute(query, params)
        resultados = cursor.fetchall()

        # Convertir a lista de diccionarios
        datos = []
        for fila in resultados:
            if isinstance(fila, dict):
                # Si ya es un diccionario, usarlo directamente
                registro = fila
            else:
                # Si es una tupla, convertir usando las columnas
                columnas = [desc[0] for desc in cursor.description]
                registro = dict(zip(columnas, fila))
            datos.append(registro)

        # Obtener conteo total de registros (sin LIMIT)
        # Crear una consulta de conteo más simple sin DISTINCT problemático
        count_query = """
            SELECT COUNT(*) as total
            FROM control_material_salida s
            LEFT JOIN control_material_almacen a ON s.codigo_material_recibido = a.codigo_material_recibido
            WHERE 1=1
        """

        # Agregar los mismos filtros que la consulta principal
        count_params = []

        if fecha_inicio:
            count_query += " AND DATE(s.fecha_salida) >= %s"
            count_params.append(fecha_inicio)

        if fecha_fin:
            count_query += " AND DATE(s.fecha_salida) <= %s"
            count_params.append(fecha_fin)

        if numero_lote:
            count_query += " AND s.numero_lote LIKE %s"
            count_params.append(f"%{numero_lote}%")

        if codigo_material:
            count_query += " AND (s.codigo_material_recibido LIKE %s OR a.codigo_material LIKE %s OR a.codigo_material_original LIKE %s)"
            count_params.extend(
                [f"%{codigo_material}%", f"%{codigo_material}%", f"%{codigo_material}%"]
            )

        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()

        # Extraer el valor del conteo
        if isinstance(total_count, dict):
            total_registros = list(total_count.values())[0]
        else:
            total_registros = total_count[0] if total_count else 0

        print(
            f" Consulta completada: {len(datos)} registros mostrados, {total_registros} registros totales"
        )

        # Devolver tanto los datos como el conteo total
        return jsonify(
            {"datos": datos, "total": total_registros, "mostrados": len(datos)}
        )

    except Exception as e:
        print(f"Error al consultar historial de salidas: {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass


# Nuevas funciones para Control de Salida
@app.route("/buscar_material_por_codigo", methods=["GET"])
@login_requerido
def buscar_material_por_codigo():
    """Buscar material en control_material_almacen por código de material recibido y calcular stock disponible real usando MySQL"""
    try:
        codigo_recibido = request.args.get("codigo_recibido", "").strip()

        if not codigo_recibido:
            return jsonify(
                {
                    "success": False,
                    "error": "Código de material recibido no proporcionado",
                }
            ), 400

        # Usar funciones de MySQL en lugar de SQLite
        from .db_mysql import (
            buscar_material_por_codigo_mysql,
            obtener_total_salidas_material,
        )

        material = buscar_material_por_codigo_mysql(codigo_recibido)

        if not material:
            return jsonify(
                {
                    "success": False,
                    "error": "Código de material no encontrado en almacén",
                }
            )

        # Calcular el total de salidas para este código específico usando MySQL
        total_salidas = obtener_total_salidas_material(codigo_recibido)

        # Calcular stock disponible real
        cantidad_original = float(material["cantidad_actual"])
        stock_disponible = cantidad_original - total_salidas

        print(f" STOCK CALCULADO para {codigo_recibido} (MySQL):")
        print(f"   - Cantidad original: {cantidad_original}")
        print(f"   - Total salidas: {total_salidas}")
        print(f"   - Stock disponible: {stock_disponible}")

        # Verificar si hay stock disponible
        if stock_disponible <= 0:
            return jsonify(
                {
                    "success": False,
                    "error": f"Material sin stock disponible. Original: {cantidad_original}, Salidas: {total_salidas}, Disponible: {stock_disponible}",
                }
            )

        # Convertir el resultado a diccionario con stock actualizado
        material_data = {
            "id": material["id"],
            "forma_material": material["forma_material"],
            "cliente": material["cliente"],
            "codigo_material_original": material["codigo_material_original"],
            "codigo_material": material["codigo_material"],
            "material_importacion_local": material["material_importacion_local"],
            "fecha_recibo": material["fecha_recibo"],
            "fecha_fabricacion": material["fecha_fabricacion"],
            "cantidad_actual": stock_disponible,  # ← USAR STOCK CALCULADO EN LUGAR DE CANTIDAD ORIGINAL
            "cantidad_original": cantidad_original,  # ← MANTENER REFERENCIA A LA CANTIDAD ORIGINAL
            "total_salidas": total_salidas,  # ← INFORMACIÓN ADICIONAL
            "numero_lote_material": material["numero_lote_material"],
            "codigo_material_recibido": material["codigo_material_recibido"],
            "numero_parte": material["numero_parte"],
            "cantidad_estandarizada": material["cantidad_estandarizada"],
            "codigo_material_final": material["codigo_material_final"],
            "propiedad_material": material["propiedad_material"],
            "especificacion": material["especificacion"],
            "material_importacion_local_final": material[
                "material_importacion_local_final"
            ],
            "estado_desecho": material["estado_desecho"],
            "ubicacion_salida": material["ubicacion_salida"],
            "fecha_registro": material["fecha_registro"],
            "database_type": "MySQL",  # Indicador de que se está usando MySQL
        }

        return jsonify({"success": True, "material": material_data})

    except Exception as e:
        print(f" ERROR en buscar_material_por_codigo (MySQL): {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500


@app.route("/verificar_stock_rapido", methods=["GET"])
@login_requerido
def verificar_stock_rapido():
    """Verificación ultra rápida de stock para salidas masivas - Solo devuelve stock disponible"""
    try:
        codigo = request.args.get("codigo", "").strip()

        if not codigo:
            return jsonify({"success": False, "error": "Código no proporcionado"}), 400

        # Consulta SQL ultra optimizada - solo lo esencial
        query = """
        SELECT
            codigo_material_recibido,
            numero_parte,
            cantidad_actual,
            numero_lote_material,
            especificacion_material
        FROM control_material_almacen
        WHERE codigo_material_recibido = %s
        LIMIT 1
        """

        result = execute_query(query, (codigo,))

        if not result:
            return jsonify({"success": False, "error": "Material no encontrado"})

        material = result[0]

        # Consulta rápida de salidas totales
        query_salidas = """
        SELECT COALESCE(SUM(cantidad_salida), 0) as total_salidas
        FROM movimientos_inventario
        WHERE codigo_material_recibido = %s AND tipo_movimiento = 'SALIDA'
        """

        salidas_result = execute_query(query_salidas, (codigo,))
        total_salidas = salidas_result[0]["total_salidas"] if salidas_result else 0

        # Calcular stock disponible
        cantidad_original = float(material["cantidad_actual"])
        stock_disponible = cantidad_original - total_salidas

        if stock_disponible <= 0:
            return jsonify(
                {
                    "success": False,
                    "error": "Sin stock disponible",
                    "stock": 0,
                    "original": cantidad_original,
                    "salidas": total_salidas,
                }
            )

        return jsonify(
            {
                "success": True,
                "stock": stock_disponible,
                "numero_parte": material["numero_parte"],
                "numero_lote": material["numero_lote_material"],
                "especificacion": material["especificacion_material"],
                "original": cantidad_original,
                "salidas": total_salidas,
            }
        )

    except Exception as e:
        print(f" ERROR en verificar_stock_rapido: {str(e)}")
        return jsonify({"success": False, "error": f"Error: {str(e)}"}), 500


@app.route("/procesar_salida_material", methods=["POST"])
@login_requerido
def procesar_salida_material():
    """Procesar salida de material con respuesta inmediata y actualización de inventario en background usando MySQL"""
    import threading

    try:
        data = request.get_json()

        # Validar campos requeridos
        required_fields = ["codigo_material_recibido", "cantidad_salida"]
        for field in required_fields:
            if not data.get(field):
                return jsonify(
                    {"success": False, "error": f"Campo requerido: {field}"}
                ), 400

        codigo_recibido = data["codigo_material_recibido"]
        cantidad_salida = float(data["cantidad_salida"])

        if cantidad_salida <= 0:
            return jsonify(
                {"success": False, "error": "La cantidad de salida debe ser mayor a 0"}
            ), 400

        # Usar funciones de MySQL en lugar de SQLite
        from .db_mysql import (
            actualizar_inventario_general_salida_mysql,
            buscar_material_por_codigo_mysql,
            obtener_total_salidas_material,
            registrar_salida_material_mysql,
        )

        # Buscar el material en almacén para obtener información completa
        material = buscar_material_por_codigo_mysql(codigo_recibido)

        if not material:
            return jsonify(
                {"success": False, "error": "Material no encontrado en almacén"}
            ), 400

        cantidad_original = material["cantidad_actual"]
        numero_parte = material["numero_parte"] or ""

        # Calcular el total de salidas existentes para este código específico usando MySQL
        total_salidas_previas = obtener_total_salidas_material(codigo_recibido)

        # Calcular stock disponible real
        stock_disponible = cantidad_original - total_salidas_previas

        print(f" VERIFICACIÓN STOCK PARA SALIDA {codigo_recibido} (MySQL):")
        print(f"   - Cantidad original: {cantidad_original}")
        print(f"   - Salidas previas: {total_salidas_previas}")
        print(f"   - Stock disponible: {stock_disponible}")
        print(f"   - Cantidad solicitada: {cantidad_salida}")

        if stock_disponible <= 0:
            return jsonify(
                {
                    "success": False,
                    "error": f"Sin stock disponible. Original: {cantidad_original}, Salidas previas: {total_salidas_previas}",
                }
            ), 400

        if cantidad_salida > stock_disponible:
            return jsonify(
                {
                    "success": False,
                    "error": f"Cantidad insuficiente. Stock disponible: {stock_disponible}, solicitado: {cantidad_salida}",
                }
            ), 400

        # Preparar datos para registrar la salida usando MySQL
        salida_data = {
            "codigo_material_recibido": codigo_recibido,
            "numero_lote": data.get("numero_lote", ""),
            "modelo": data.get("modelo", ""),
            "depto_salida": data.get("depto_salida", ""),
            "proceso_salida": data.get("proceso_salida", ""),
            "cantidad_salida": cantidad_salida,
            "fecha_salida": data.get("fecha_salida", ""),
        }

        # Solo incluir especificacion_material si se proporciona explícitamente
        if "especificacion_material" in data and data["especificacion_material"]:
            salida_data["especificacion_material"] = data["especificacion_material"]

        # Registrar la salida usando MySQL
        resultado_salida = registrar_salida_material_mysql(salida_data)

        if not resultado_salida.get("success", False):
            error_msg = resultado_salida.get(
                "error", "Error al registrar la salida en la base de datos"
            )
            return jsonify({"success": False, "error": error_msg}), 500

        # Obtener información del proceso determinado
        proceso_destino = resultado_salida.get("proceso_destino", "PRODUCCION")
        especificacion_usada = resultado_salida.get("especificacion_usada", "")

        nueva_cantidad = stock_disponible - cantidad_salida

        #  OPTIMIZACIÓN: Actualizar inventario general en BACKGROUND THREAD
        def actualizar_inventario_background():
            """Función para actualizar inventario en segundo plano usando MySQL"""
            try:
                if numero_parte:
                    print(
                        f" BACKGROUND (MySQL): Actualizando inventario para {numero_parte}"
                    )
                    resultado = actualizar_inventario_general_salida_mysql(
                        numero_parte, cantidad_salida
                    )
                    if resultado:
                        print(
                            f" BACKGROUND (MySQL): Inventario actualizado exitosamente: -{cantidad_salida} para {numero_parte}"
                        )
                    else:
                        print(
                            f" BACKGROUND (MySQL): Error al actualizar inventario para {numero_parte}"
                        )
            except Exception as e:
                print(f" BACKGROUND ERROR (MySQL): {e}")

        # Ejecutar actualización de inventario en hilo separado
        if numero_parte:
            inventario_thread = threading.Thread(
                target=actualizar_inventario_background
            )
            inventario_thread.daemon = True  # Se cierra con la aplicación
            inventario_thread.start()
            print(
                f"🚀 OPTIMIZADO (MySQL): Salida registrada, inventario actualizándose en background"
            )

        #  RESPUESTA INMEDIATA AL USUARIO
        return jsonify(
            {
                "success": True,
                "message": f"Salida registrada exitosamente. Cantidad: {cantidad_salida}",
                "nueva_cantidad_disponible": nueva_cantidad,
                "proceso_destino": proceso_destino,  # Incluir proceso destino determinado
                "especificacion_usada": especificacion_usada,  # Incluir especificación usada
                "optimized": True,  # Indicador de que se está usando optimización
                "numero_parte": numero_parte,  # Para debugging
                "inventario_actualizado_en_background": True,
                "database_type": "MySQL",  # Indicador de que se está usando MySQL
            }
        )

    except Exception as e:
        print(f" ERROR GENERAL en procesar_salida_material (MySQL): {e}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500


@app.route("/forzar_actualizacion_inventario/<numero_parte>", methods=["POST"])
@login_requerido
def forzar_actualizacion_inventario(numero_parte):
    """
    Endpoint para forzar la actualización del inventario general para un número de parte específico
    """
    try:
        print(f" FORZANDO actualización de inventario para: {numero_parte}")

        # Recalcular inventario para este número de parte específico
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener todas las entradas para este número de parte
        cursor.execute(
            """
            SELECT SUM(cantidad_actual) as total_entradas
            FROM control_material_almacen
            WHERE numero_parte = %s
        """,
            (numero_parte,),
        )
        entradas_result = cursor.fetchone()
        total_entradas = (
            entradas_result[0] if entradas_result and entradas_result[0] else 0
        )

        # Obtener todas las salidas para este número de parte
        cursor.execute(
            """
            SELECT SUM(cantidad_salida) as total_salidas
            FROM control_material_salida cms
            JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
            WHERE cma.numero_parte = %s
        """,
            (numero_parte,),
        )
        salidas_result = cursor.fetchone()
        total_salidas = salidas_result[0] if salidas_result and salidas_result[0] else 0

        # Calcular cantidad total actual
        cantidad_total_actual = total_entradas - total_salidas

        # Actualizar o insertar en inventario_general
        cursor.execute(
            """
            INSERT INTO inventario_general
            (numero_parte, cantidad_entradas, cantidad_salidas, cantidad_total, fecha_actualizacion)
            VALUES (%s, %s, %s, %s, NOW()) ON DUPLICATE KEY UPDATE cantidad_entradas = VALUES(cantidad_entradas), cantidad_salidas = VALUES(cantidad_salidas), cantidad_total = VALUES(cantidad_total), fecha_actualizacion = VALUES(fecha_actualizacion)
        """,
            (numero_parte, total_entradas, total_salidas, cantidad_total_actual),
        )

        conn.commit()
        conn.close()

        print(
            f" FORZADO: Inventario actualizado para {numero_parte}: {cantidad_total_actual}"
        )

        return jsonify(
            {
                "success": True,
                "numero_parte": numero_parte,
                "cantidad_total_actualizada": cantidad_total_actual,
                "total_entradas": total_entradas,
                "total_salidas": total_salidas,
            }
        )

    except Exception as e:
        print(f" ERROR al forzar actualización de inventario: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
        print(f"Error al procesar salida de material: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500

    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass


@app.route("/recalcular_inventario_general", methods=["POST"])
@login_requerido
def recalcular_inventario_general_endpoint():
    """Endpoint para recalcular todo el inventario consolidado desde cero"""
    try:
        # Importar función de base de datos
        from .db_mysql import get_connection

        connection = get_connection()
        if not connection:
            return jsonify(
                {"success": False, "error": "Error de conexión a la base de datos"}
            ), 500

        cursor = connection.cursor()

        # 1. Limpiar tabla inventario_consolidado
        cursor.execute("DELETE FROM inventario_consolidado")

        # 2. Recalcular desde control_material_almacen
        query_recalcular = """
            INSERT INTO inventario_consolidado
            (numero_parte, codigo_material, especificacion, propiedad_material,
             cantidad_actual, total_lotes, fecha_ultima_entrada, fecha_primera_entrada,
             total_entradas, total_salidas)
            SELECT
                numero_parte,
                MAX(codigo_material) as codigo_material,
                MAX(especificacion) as especificacion,
                MAX(propiedad_material) as propiedad_material,
                SUM(COALESCE(cantidad_actual, 0)) as cantidad_actual,
                COUNT(DISTINCT numero_lote_material) as total_lotes,
                MAX(fecha_recibo) as fecha_ultima_entrada,
                MIN(fecha_recibo) as fecha_primera_entrada,
                SUM(COALESCE(cantidad_actual, 0)) as total_entradas,
                0 as total_salidas
            FROM control_material_almacen
            WHERE estado_desecho = FALSE
            GROUP BY numero_parte
        """

        cursor.execute(query_recalcular)
        filas_afectadas = cursor.rowcount

        connection.commit()
        cursor.close()
        connection.close()

        print(
            f" Inventario consolidado recalculado: {filas_afectadas} números de parte actualizados"
        )

        return jsonify(
            {
                "success": True,
                "message": f"Inventario consolidado recalculado exitosamente. {filas_afectadas} números de parte actualizados.",
            }
        )

    except Exception as e:
        print(f"Error en endpoint recalcular inventario: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500


@app.route("/obtener_inventario_general", methods=["GET"])
@login_requerido
def obtener_inventario_general_endpoint():
    """Endpoint para obtener el inventario general (para uso futuro)"""
    try:
        from app.db_mysql import obtener_inventario

        inventario = obtener_inventario()
        return jsonify(
            {"success": True, "inventario": inventario, "total_items": len(inventario)}
        )

    except Exception as e:
        print(f"Error al obtener inventario general: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500


@app.route("/verificar_estado_inventario", methods=["GET"])
@login_requerido
def verificar_estado_inventario():
    """Endpoint opcional para verificar si el inventario general está actualizado"""
    try:
        numero_parte = request.args.get("numero_parte")

        if not numero_parte:
            return jsonify(
                {"success": False, "error": "Número de parte requerido"}
            ), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar estado del inventario para este número de parte
        cursor.execute(
            """
            SELECT numero_parte, cantidad_total, fecha_actualizacion
            FROM inventario_general
            WHERE numero_parte = %s
        """,
            (numero_parte,),
        )

        resultado = cursor.fetchone()

        if resultado:
            from datetime import datetime, timedelta

            # Verificar si la actualización es reciente (últimos 30 segundos)
            try:
                fecha_actualizacion = datetime.strptime(
                    resultado["fecha_actualizacion"], "%Y-%m-%d %H:%M:%S"
                )
                tiempo_transcurrido = datetime.now() - fecha_actualizacion
                actualizado_recientemente = tiempo_transcurrido < timedelta(seconds=30)
            except:
                actualizado_recientemente = False

            return jsonify(
                {
                    "success": True,
                    "numero_parte": resultado["numero_parte"],
                    "cantidad_total": resultado["cantidad_total"],
                    "fecha_actualizacion": resultado["fecha_actualizacion"],
                    "actualizado_recientemente": actualizado_recientemente,
                    "mensaje": "Inventario actualizado"
                    if actualizado_recientemente
                    else "Inventario estable",
                }
            )
        else:
            return jsonify(
                {
                    "success": False,
                    "error": f"No se encontró registro de inventario para {numero_parte}",
                }
            ), 404

    except Exception as e:
        print(f"Error al verificar estado de inventario: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500

    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass




@app.route("/test_modelos")
def test_modelos():
    """Página de prueba para verificar la carga de modelos"""
    return render_template("test_modelos.html")


# Ruta para el inventario general (nuevo)
@app.route("/api/inventario/consultar", methods=["POST"])
@login_requerido
def consultar_inventario_general():
    """Endpoint optimizado usando tabla inventario_consolidado para mayor eficiencia"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        filtros = data if data else {}

        # Usar específicamente la conexión MySQL del hosting
        from .config_mysql import get_mysql_connection

        conn = get_mysql_connection()
        using_mysql = True

        if conn is None:
            return jsonify(
                {
                    "success": False,
                    "error": "No se pudo conectar a la base de datos MySQL",
                }
            ), 500

        cursor = conn.cursor()  # Usar cursor normal

        # Verificar que la tabla inventario_consolidado existe en MySQL
        try:
            cursor.execute("SHOW TABLES LIKE 'inventario_consolidado'")

            if not cursor.fetchone():
                return jsonify(
                    {
                        "success": False,
                        "error": "Tabla inventario_consolidado no encontrada en MySQL",
                    }
                ), 500
        except Exception as table_error:
            return jsonify(
                {
                    "success": False,
                    "error": f"Error verificando tablas: {str(table_error)}",
                }
            ), 500

        # Construir consulta optimizada para MySQL
        query = """
            SELECT
                ic.numero_parte,
                ic.codigo_material,
                ic.especificacion,
                ic.propiedad_material,
                ic.cantidad_actual as cantidad_total,
                ic.total_lotes,
                ic.fecha_ultima_entrada as fecha_ultimo_recibo,
                ic.fecha_primera_entrada as fecha_primer_recibo,
                ic.total_entradas,
                ic.total_salidas
            FROM inventario_consolidado ic
            WHERE 1=1
        """

        params = []

        # Aplicar filtros MySQL
        if filtros.get("numeroParte"):
            query += " AND ic.numero_parte LIKE %s"
            params.append(f"%{filtros['numeroParte']}%")

        if filtros.get("propiedad"):
            query += " AND ic.propiedad_material = %s"
            params.append(filtros["propiedad"])

        # Filtrar por cantidad mínima
        if filtros.get("cantidadMinima") and float(filtros["cantidadMinima"]) > 0:
            query += " AND ic.cantidad_actual >= %s"
            params.append(float(filtros["cantidadMinima"]))

        query += " ORDER BY ic.fecha_ultima_entrada DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        inventario = []
        for i, row in enumerate(rows):
            try:
                # Procesar como tupla (orden según la consulta SELECT)
                # SELECT numero_parte, codigo_material, especificacion, propiedad_material,
                #        cantidad_actual, total_lotes, fecha_ultima_entrada, fecha_primera_entrada,
                #        total_entradas, total_salidas
                numero_parte = row[0] if len(row) > 0 else ""
                codigo_material = row[1] if len(row) > 1 else numero_parte
                especificacion = row[2] if len(row) > 2 else ""
                propiedad_material = row[3] if len(row) > 3 else "COMMON USE"
                cantidad_total = (
                    float(row[4]) if len(row) > 4 and row[4] is not None else 0.0
                )
                total_lotes = int(row[5]) if len(row) > 5 and row[5] is not None else 0
                fecha_ultimo_recibo = row[6] if len(row) > 6 else None
                fecha_primer_recibo = row[7] if len(row) > 7 else None
                total_entradas = (
                    float(row[8]) if len(row) > 8 and row[8] is not None else 0.0
                )
                total_salidas = (
                    float(row[9]) if len(row) > 9 and row[9] is not None else 0.0
                )

                # Mostrar registros que tengan entradas (aunque la cantidad total sea 0 o negativa)
                if total_entradas > 0:
                    inventario.append(
                        {
                            "id": i + 1,
                            "numero_parte": numero_parte,
                            "codigo_material": codigo_material,
                            "especificacion": especificacion,
                            "propiedad_material": propiedad_material,
                            "cantidad_total": cantidad_total,
                            "total_entradas": total_entradas,
                            "total_salidas": total_salidas,
                            "total_lotes": total_lotes,
                            "lotes_disponibles": [],  # Se consulta por separado si es necesario
                            "fecha_ultimo_recibo": fecha_ultimo_recibo,
                            "fecha_primer_recibo": fecha_primer_recibo,
                        }
                    )

            except Exception as row_error:
                continue

        return jsonify(
            {
                "success": True,
                "inventario": inventario,
                "total": len(inventario),
                "filtros_aplicados": filtros,
                "modo": "agrupado_por_numero_parte",
            }
        )

    except Exception as e:
        return jsonify(
            {"success": False, "error": f"Error al consultar inventario: {str(e)}"}
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/inventario/historial", methods=["POST"])
@login_requerido
def obtener_historial_numero_parte():
    """Endpoint para obtener el historial completo de entradas y salidas de un número de parte"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        numero_parte = data.get("numero_parte", "").strip()

        if not numero_parte:
            return jsonify(
                {"success": False, "error": "Número de parte requerido"}
            ), 400

        from .db import is_mysql_connection

        using_mysql = is_mysql_connection()

        conn = get_db_connection()
        if conn is None:
            return jsonify(
                {"success": False, "error": "No se pudo conectar a la base de datos"}
            ), 500

        cursor = conn.cursor()

        # Obtener todas las entradas (registros en control_material_almacen)
        if using_mysql:
            entradas_query = """
                SELECT
                    'ENTRADA' as tipo_movimiento,
                    fecha_recibo as fecha_movimiento,
                    numero_lote_material as lote,
                    cantidad_actual as cantidad,
                    codigo_material_recibido,
                    especificacion,
                    propiedad_material,
                    'RECIBO INICIAL' as detalle_movimiento,
                    fecha_registro
                FROM control_material_almacen
                WHERE numero_parte = %s
                ORDER BY fecha_recibo DESC
            """
            cursor.execute(entradas_query, [numero_parte])
        else:
            entradas_query = """
                SELECT
                    'ENTRADA' as tipo_movimiento,
                    fecha_recibo as fecha_movimiento,
                    numero_lote_material as lote,
                    cantidad_actual as cantidad,
                    codigo_material_recibido,
                    especificacion,
                    propiedad_material,
                    'RECIBO INICIAL' as detalle_movimiento,
                    fecha_registro
                FROM control_material_almacen
                WHERE numero_parte = ?
                ORDER BY fecha_recibo DESC
            """
            cursor.execute(entradas_query, [numero_parte])

        entradas_rows = cursor.fetchall()

        # Obtener todas las salidas usando numero_parte directamente
        if using_mysql:
            salidas_query = """
                SELECT
                    'SALIDA' as tipo_movimiento,
                    cms.fecha_salida as fecha_movimiento,
                    cms.numero_lote as lote,
                    cms.cantidad_salida as cantidad,
                    cms.codigo_material_recibido,
                    cms.especificacion_material as especificacion,
                    'N/A' as propiedad_material,
                    CONCAT('SALIDA - ', cms.modelo, ' - ', cms.depto_salida, ' - ', cms.proceso_salida) as detalle_movimiento,
                    cms.fecha_registro
                FROM control_material_salida cms
                WHERE cms.numero_parte = %s
                ORDER BY cms.fecha_salida DESC
            """
            cursor.execute(salidas_query, [numero_parte])
        else:
            salidas_query = """
                SELECT
                    'SALIDA' as tipo_movimiento,
                    cms.fecha_salida as fecha_movimiento,
                    cms.numero_lote as lote,
                    cms.cantidad_salida as cantidad,
                    cms.codigo_material_recibido,
                    cms.especificacion_material as especificacion,
                    'N/A' as propiedad_material,
                    ('SALIDA - ' || cms.modelo || ' - ' || cms.depto_salida || ' - ' || cms.proceso_salida) as detalle_movimiento,
                    cms.fecha_registro
                FROM control_material_salida cms
                WHERE cms.numero_parte = ?
                ORDER BY cms.fecha_salida DESC
            """
            cursor.execute(salidas_query, [numero_parte])

        salidas_rows = cursor.fetchall()

        # Combinar entradas y salidas
        historial = []

        # Procesar entradas
        for row in entradas_rows:
            if hasattr(row, "keys"):
                historial.append(
                    {
                        "tipo_movimiento": row.get("tipo_movimiento", ""),
                        "fecha_movimiento": row.get("fecha_movimiento"),
                        "lote": row.get("lote", ""),
                        "cantidad": float(row.get("cantidad", 0))
                        if row.get("cantidad")
                        else 0.0,
                        "codigo_material_recibido": row.get(
                            "codigo_material_recibido", ""
                        ),
                        "especificacion": row.get("especificacion", ""),
                        "propiedad_material": row.get("propiedad_material", ""),
                        "detalle_movimiento": row.get("detalle_movimiento", ""),
                        "fecha_registro": row.get("fecha_registro"),
                    }
                )
            else:
                historial.append(
                    {
                        "tipo_movimiento": row[0] or "",
                        "fecha_movimiento": row[1],
                        "lote": row[2] or "",
                        "cantidad": float(row[3] or 0),
                        "codigo_material_recibido": row[4] or "",
                        "especificacion": row[5] or "",
                        "propiedad_material": row[6] or "",
                        "detalle_movimiento": row[7] or "",
                        "fecha_registro": row[8],
                    }
                )

        # Procesar salidas
        for row in salidas_rows:
            if hasattr(row, "keys"):
                historial.append(
                    {
                        "tipo_movimiento": row.get("tipo_movimiento", ""),
                        "fecha_movimiento": row.get("fecha_movimiento"),
                        "lote": row.get("lote", ""),
                        "cantidad": -float(row.get("cantidad", 0))
                        if row.get("cantidad")
                        else 0.0,  # Negativo para salidas
                        "codigo_material_recibido": row.get(
                            "codigo_material_recibido", ""
                        ),
                        "especificacion": row.get("especificacion", ""),
                        "propiedad_material": row.get("propiedad_material", ""),
                        "detalle_movimiento": row.get("detalle_movimiento", ""),
                        "fecha_registro": row.get("fecha_registro"),
                    }
                )
            else:
                historial.append(
                    {
                        "tipo_movimiento": row[0] or "",
                        "fecha_movimiento": row[1],
                        "lote": row[2] or "",
                        "cantidad": -float(row[3] or 0),  # Negativo para salidas
                        "codigo_material_recibido": row[4] or "",
                        "especificacion": row[5] or "",
                        "propiedad_material": row[6] or "",
                        "detalle_movimiento": row[7] or "",
                        "fecha_registro": row[8],
                    }
                )

        # Ordenar por fecha de movimiento descendente
        historial.sort(key=lambda x: x["fecha_movimiento"] or "", reverse=True)

        # Calcular balance acumulado
        balance_acumulado = 0
        for movimiento in reversed(
            historial
        ):  # Procesar en orden cronológico para el balance
            balance_acumulado += movimiento["cantidad"]
            movimiento["balance_acumulado"] = balance_acumulado

        # Revertir orden para mostrar más recientes primero
        historial.reverse()

        print(f" Historial obtenido: {len(historial)} movimientos para {numero_parte}")

        return jsonify(
            {
                "success": True,
                "historial": historial,
                "numero_parte": numero_parte,
                "total_movimientos": len(historial),
                "balance_actual": balance_acumulado,
            }
        )

    except Exception as e:
        print(f" Error al obtener historial: {e}")
        import traceback

        traceback.print_exc()
        return jsonify(
            {"success": False, "error": f"Error al obtener historial: {str(e)}"}
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/inventario/historial/<numero_parte>")
@login_requerido
def obtener_historial_numero_parte_get(numero_parte):
    """Endpoint GET para obtener el historial completo de entradas y salidas de un número de parte"""
    conn = None
    cursor = None
    try:
        if not numero_parte:
            return jsonify(
                {"success": False, "error": "Número de parte requerido"}
            ), 400

        print(f" Consultando historial GET para número de parte: {numero_parte}")

        from .db import is_mysql_connection

        using_mysql = is_mysql_connection()

        conn = get_db_connection()
        if conn is None:
            return jsonify(
                {"success": False, "error": "No se pudo conectar a la base de datos"}
            ), 500

        cursor = conn.cursor()

        # Obtener todas las entradas (registros en control_material_almacen)
        if using_mysql:
            entradas_query = """
                SELECT
                    'ENTRADA' as tipo_movimiento,
                    fecha_recibo as fecha_movimiento,
                    numero_lote_material as lote,
                    cantidad_actual as cantidad,
                    codigo_material_recibido,
                    especificacion,
                    propiedad_material,
                    'RECIBO INICIAL' as detalle_movimiento,
                    fecha_registro
                FROM control_material_almacen
                WHERE numero_parte = %s
                ORDER BY fecha_recibo DESC
            """
            cursor.execute(entradas_query, [numero_parte])
        else:
            entradas_query = """
                SELECT
                    'ENTRADA' as tipo_movimiento,
                    fecha_recibo as fecha_movimiento,
                    numero_lote_material as lote,
                    cantidad_actual as cantidad,
                    codigo_material_recibido,
                    especificacion,
                    propiedad_material,
                    'RECIBO INICIAL' as detalle_movimiento,
                    fecha_registro
                FROM control_material_almacen
                WHERE numero_parte = ?
                ORDER BY fecha_recibo DESC
            """
            cursor.execute(entradas_query, [numero_parte])

        entradas_rows = cursor.fetchall()

        # Obtener todas las salidas
        if using_mysql:
            salidas_query = """
                SELECT
                    'SALIDA' as tipo_movimiento,
                    cms.fecha_salida as fecha_movimiento,
                    cms.numero_lote as lote,
                    cms.cantidad_salida as cantidad,
                    cms.codigo_material_recibido,
                    cms.especificacion_material as especificacion,
                    'N/A' as propiedad_material,
                    CONCAT('SALIDA - ', cms.modelo, ' - ', cms.depto_salida, ' - ', cms.proceso_salida) as detalle_movimiento,
                    cms.fecha_registro
                FROM control_material_salida cms
                INNER JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
                WHERE cma.numero_parte = %s
                ORDER BY cms.fecha_salida DESC
            """
            cursor.execute(salidas_query, [numero_parte])
        else:
            salidas_query = """
                SELECT
                    'SALIDA' as tipo_movimiento,
                    cms.fecha_salida as fecha_movimiento,
                    cms.numero_lote as lote,
                    cms.cantidad_salida as cantidad,
                    cms.codigo_material_recibido,
                    cms.especificacion_material as especificacion,
                    'N/A' as propiedad_material,
                    ('SALIDA - ' || cms.modelo || ' - ' || cms.depto_salida || ' - ' || cms.proceso_salida) as detalle_movimiento,
                    cms.fecha_registro
                FROM control_material_salida cms
                INNER JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
                WHERE cma.numero_parte = ?
                ORDER BY cms.fecha_salida DESC
            """
            cursor.execute(salidas_query, [numero_parte])

        salidas_rows = cursor.fetchall()

        # Combinar entradas y salidas
        historial = []

        # Procesar entradas
        for row in entradas_rows:
            if hasattr(row, "keys"):
                historial.append(
                    {
                        "tipo_movimiento": row.get("tipo_movimiento", ""),
                        "fecha_movimiento": row.get("fecha_movimiento"),
                        "lote": row.get("lote", ""),
                        "cantidad": float(row.get("cantidad", 0))
                        if row.get("cantidad")
                        else 0.0,
                        "codigo_material_recibido": row.get(
                            "codigo_material_recibido", ""
                        ),
                        "especificacion": row.get("especificacion", ""),
                        "propiedad_material": row.get("propiedad_material", ""),
                        "detalle_movimiento": row.get("detalle_movimiento", ""),
                        "fecha_registro": row.get("fecha_registro"),
                    }
                )
            else:
                historial.append(
                    {
                        "tipo_movimiento": row[0] or "",
                        "fecha_movimiento": row[1],
                        "lote": row[2] or "",
                        "cantidad": float(row[3] or 0),
                        "codigo_material_recibido": row[4] or "",
                        "especificacion": row[5] or "",
                        "propiedad_material": row[6] or "",
                        "detalle_movimiento": row[7] or "",
                        "fecha_registro": row[8],
                    }
                )

        # Procesar salidas (cantidad negativa para balance)
        for row in salidas_rows:
            if hasattr(row, "keys"):
                historial.append(
                    {
                        "tipo_movimiento": row.get("tipo_movimiento", ""),
                        "fecha_movimiento": row.get("fecha_movimiento"),
                        "lote": row.get("lote", ""),
                        "cantidad": -float(row.get("cantidad", 0))
                        if row.get("cantidad")
                        else 0.0,
                        "codigo_material_recibido": row.get(
                            "codigo_material_recibido", ""
                        ),
                        "especificacion": row.get("especificacion", ""),
                        "propiedad_material": row.get("propiedad_material", ""),
                        "detalle_movimiento": row.get("detalle_movimiento", ""),
                        "fecha_registro": row.get("fecha_registro"),
                    }
                )
            else:
                historial.append(
                    {
                        "tipo_movimiento": row[0] or "",
                        "fecha_movimiento": row[1],
                        "lote": row[2] or "",
                        "cantidad": -float(row[3] or 0),
                        "codigo_material_recibido": row[4] or "",
                        "especificacion": row[5] or "",
                        "propiedad_material": row[6] or "",
                        "detalle_movimiento": row[7] or "",
                        "fecha_registro": row[8],
                    }
                )

        # Ordenar por fecha
        historial.sort(key=lambda x: x["fecha_movimiento"] or "", reverse=True)

        # Calcular balance acumulado
        balance_acumulado = 0
        for mov in reversed(historial):
            balance_acumulado += mov["cantidad"]
            mov["balance_acumulado"] = balance_acumulado

        print(
            f" Historial obtenido: {len(historial)} movimientos, balance: {balance_acumulado}"
        )

        return jsonify(
            {
                "success": True,
                "historial": historial,
                "numero_parte": numero_parte,
                "total_movimientos": len(historial),
                "balance_actual": balance_acumulado,
            }
        )

    except Exception as e:
        print(f" Error al obtener historial GET: {e}")
        import traceback

        traceback.print_exc()
        return jsonify(
            {"success": False, "error": f"Error al obtener historial: {str(e)}"}
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/inventario/lotes", methods=["POST"])
@login_requerido
def obtener_lotes_numero_parte():
    """Endpoint mejorado para obtener todos los lotes disponibles de un número de parte"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        numero_parte = data.get("numero_parte", "").strip()

        if not numero_parte:
            return jsonify(
                {"success": False, "error": "Número de parte requerido"}
            ), 400

        print(f" Consultando lotes para número de parte: {numero_parte}")

        from .db import is_mysql_connection

        using_mysql = is_mysql_connection()

        conn = get_db_connection()
        if conn is None:
            return jsonify(
                {"success": False, "error": "No se pudo conectar a la base de datos"}
            ), 500

        cursor = conn.cursor()

        # Query mejorado para obtener lotes con información completa
        if using_mysql:
            query = """
                SELECT
                    cma.numero_lote_material,
                    cma.cantidad_actual,
                    cma.fecha_recibo,
                    cma.fecha_fabricacion,
                    cma.codigo_material_recibido,
                    cma.especificacion,
                    cma.propiedad_material,
                    cma.ubicacion_salida,
                    COALESCE(salidas.total_salidas, 0) as total_salidas,
                    (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) as cantidad_disponible
                FROM control_material_almacen cma
                LEFT JOIN (
                    SELECT
                        codigo_material_recibido,
                        numero_lote,
                        SUM(cantidad_salida) as total_salidas
                    FROM control_material_salida
                    GROUP BY codigo_material_recibido, numero_lote
                ) salidas ON cma.codigo_material_recibido = salidas.codigo_material_recibido
                          AND cma.numero_lote_material = salidas.numero_lote
                WHERE cma.numero_parte = %s
                  AND cma.cantidad_actual > 0
                  AND (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) > 0
                ORDER BY cma.fecha_recibo DESC
            """
            cursor.execute(query, [numero_parte])
        else:
            query = """
                SELECT
                    cma.numero_lote_material,
                    cma.cantidad_actual,
                    cma.fecha_recibo,
                    cma.fecha_fabricacion,
                    cma.codigo_material_recibido,
                    cma.especificacion,
                    cma.propiedad_material,
                    cma.ubicacion_salida,
                    COALESCE(salidas.total_salidas, 0) as total_salidas,
                    (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) as cantidad_disponible
                FROM control_material_almacen cma
                LEFT JOIN (
                    SELECT
                        codigo_material_recibido,
                        numero_lote,
                        SUM(cantidad_salida) as total_salidas
                    FROM control_material_salida
                    GROUP BY codigo_material_recibido, numero_lote
                ) salidas ON cma.codigo_material_recibido = salidas.codigo_material_recibido
                          AND cma.numero_lote_material = salidas.numero_lote
                WHERE cma.numero_parte = ?
                  AND cma.cantidad_actual > 0
                  AND (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) > 0
                ORDER BY cma.fecha_recibo DESC
            """
            cursor.execute(query, [numero_parte])

        rows = cursor.fetchall()

        print(f" Lotes encontrados: {len(rows) if rows else 0}")

        lotes = []
        for row in rows:
            try:
                if hasattr(row, "keys"):
                    cantidad_disponible = float(row.get("cantidad_disponible", 0))
                    if cantidad_disponible > 0:
                        lotes.append(
                            {
                                "numero_lote": row.get("numero_lote_material", ""),
                                "cantidad_original": float(
                                    row.get("cantidad_actual", 0)
                                ),
                                "total_salidas": float(row.get("total_salidas", 0)),
                                "cantidad_disponible": cantidad_disponible,
                                "fecha_recibo": row.get("fecha_recibo"),
                                "fecha_fabricacion": row.get("fecha_fabricacion"),
                                "codigo_material_recibido": row.get(
                                    "codigo_material_recibido", ""
                                ),
                                "especificacion": row.get("especificacion", ""),
                                "propiedad_material": row.get("propiedad_material", ""),
                                "ubicacion_salida": row.get("ubicacion_salida", ""),
                            }
                        )
                else:
                    cantidad_disponible = float(row[9] if row[9] else 0)
                    if cantidad_disponible > 0:
                        lotes.append(
                            {
                                "numero_lote": row[0] or "",
                                "cantidad_original": float(row[1] if row[1] else 0),
                                "total_salidas": float(row[8] if row[8] else 0),
                                "cantidad_disponible": cantidad_disponible,
                                "fecha_recibo": row[2],
                                "fecha_fabricacion": row[3],
                                "codigo_material_recibido": row[4] or "",
                                "especificacion": row[5] or "",
                                "propiedad_material": row[6] or "",
                                "ubicacion_salida": row[7] or "",
                            }
                        )
            except Exception as row_error:
                print(f" Error procesando lote: {row_error}")
                continue

        print(f" Lotes disponibles: {len(lotes)} para {numero_parte}")

        return jsonify(
            {
                "success": True,
                "lotes": lotes,
                "numero_parte": numero_parte,
                "total_lotes": len(lotes),
            }
        )

    except Exception as e:
        print(f" Error al consultar lotes: {e}")
        import traceback

        traceback.print_exc()
        return jsonify(
            {"success": False, "error": f"Error al consultar lotes: {str(e)}"}
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/inventario/lotes/<numero_parte>")
@login_requerido
def obtener_lotes_numero_parte_get(numero_parte):
    """Endpoint GET para obtener todos los lotes disponibles de un número de parte"""
    conn = None
    cursor = None
    try:
        if not numero_parte:
            return jsonify(
                {"success": False, "error": "Número de parte requerido"}
            ), 400

        print(f" Consultando lotes GET para número de parte: {numero_parte}")

        from .db import is_mysql_connection

        using_mysql = is_mysql_connection()

        conn = get_db_connection()
        if conn is None:
            return jsonify(
                {"success": False, "error": "No se pudo conectar a la base de datos"}
            ), 500

        cursor = conn.cursor()

        # Query optimizada para obtener lotes con balance disponible
        if using_mysql:
            query = """
            SELECT
                    cma.numero_lote_material,
                    cma.cantidad_actual,
                    cma.fecha_recibo,
                    cma.fecha_fabricacion,
                    cma.codigo_material_recibido,
                    cma.especificacion,
                    cma.propiedad_material,
                    cma.ubicacion_salida,
                    COALESCE(salidas.total_salidas, 0) as total_salidas,
                    (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) as cantidad_disponible
                FROM control_material_almacen cma
                LEFT JOIN (
                    SELECT
                        codigo_material_recibido,
                        numero_lote,
                        SUM(cantidad_salida) as total_salidas
                    FROM control_material_salida
                    GROUP BY codigo_material_recibido, numero_lote
                ) salidas ON cma.codigo_material_recibido = salidas.codigo_material_recibido
                          AND cma.numero_lote_material = salidas.numero_lote
                WHERE cma.numero_parte = %s
                  AND cma.cantidad_actual > 0
                  AND (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) > 0
                ORDER BY cma.fecha_recibo DESC
            """
            cursor.execute(query, [numero_parte])
        else:
            query = """
                SELECT
                    cma.numero_lote_material,
                    cma.cantidad_actual,
                    cma.fecha_recibo,
                    cma.fecha_fabricacion,
                    cma.codigo_material_recibido,
                    cma.especificacion,
                    cma.propiedad_material,
                    cma.ubicacion_salida,
                    COALESCE(salidas.total_salidas, 0) as total_salidas,
                    (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) as cantidad_disponible
                FROM control_material_almacen cma
                LEFT JOIN (
                    SELECT
                        codigo_material_recibido,
                        numero_lote,
                        SUM(cantidad_salida) as total_salidas
                    FROM control_material_salida
                    GROUP BY codigo_material_recibido, numero_lote
                ) salidas ON cma.codigo_material_recibido = salidas.codigo_material_recibido
                          AND cma.numero_lote_material = salidas.numero_lote
                WHERE cma.numero_parte = ?
                  AND cma.cantidad_actual > 0
                  AND (cma.cantidad_actual - COALESCE(salidas.total_salidas, 0)) > 0
                ORDER BY cma.fecha_recibo DESC
            """
            cursor.execute(query, [numero_parte])

        rows = cursor.fetchall()

        print(f" Lotes encontrados: {len(rows) if rows else 0}")

        lotes = []
        for row in rows:
            try:
                if hasattr(row, "keys"):
                    cantidad_disponible = float(row.get("cantidad_disponible", 0))
                    if cantidad_disponible > 0:
                        lotes.append(
                            {
                                "numero_lote": row.get("numero_lote_material", ""),
                                "cantidad_original": float(
                                    row.get("cantidad_actual", 0)
                                ),
                                "total_salidas": float(row.get("total_salidas", 0)),
                                "cantidad_disponible": cantidad_disponible,
                                "fecha_recibo": row.get("fecha_recibo"),
                                "fecha_fabricacion": row.get("fecha_fabricacion"),
                                "codigo_material_recibido": row.get(
                                    "codigo_material_recibido", ""
                                ),
                                "especificacion": row.get("especificacion", ""),
                                "propiedad_material": row.get("propiedad_material", ""),
                                "ubicacion_salida": row.get("ubicacion_salida", ""),
                            }
                        )
                else:
                    cantidad_disponible = float(row[9] if row[9] else 0)
                    if cantidad_disponible > 0:
                        lotes.append(
                            {
                                "numero_lote": row[0] or "",
                                "cantidad_original": float(row[1] if row[1] else 0),
                                "total_salidas": float(row[8] if row[8] else 0),
                                "cantidad_disponible": cantidad_disponible,
                                "fecha_recibo": row[2],
                                "fecha_fabricacion": row[3],
                                "codigo_material_recibido": row[4] or "",
                                "especificacion": row[5] or "",
                                "propiedad_material": row[6] or "",
                                "ubicacion_salida": row[7] or "",
                            }
                        )
            except Exception as row_error:
                print(f" Error procesando lote: {row_error}")
                continue

        print(f" Lotes disponibles: {len(lotes)} para {numero_parte}")

        return jsonify(
            {
                "success": True,
                "lotes": lotes,
                "numero_parte": numero_parte,
                "total_lotes": len(lotes),
            }
        )

    except Exception as e:
        print(f" Error al consultar lotes GET: {e}")
        import traceback

        traceback.print_exc()
        return jsonify(
            {"success": False, "error": f"Error al consultar lotes: {str(e)}"}
        ), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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


# ============== CSV VIEWER ROUTES ==============
@app.route("/csv-viewer")
@login_requerido
def csv_viewer():
    """Página principal del visor de CSV"""
    try:
        return render_template("csv-viewer.html")
    except Exception as e:
        print(f"Error al cargar CSV viewer: {e}")
        return f"Error al cargar la página: {str(e)}", 500


# Nueva ruta para historial de cambio de material de SMT
@app.route("/historial-cambio-material-smt")
@login_requerido
def historial_cambio_material_smt():
    """Página del historial de cambio de material de SMT"""
    try:
        return render_template("Control de calidad/historial_cambio_material_smt.html")
    except Exception as e:
        print(f"Error al cargar historial de cambio de material SMT: {e}")
        return f"Error al cargar la página: {str(e)}", 500


@app.route("/historial-cambio-material-smt-ajax")
def historial_cambio_material_smt_ajax():
    if "usuario" not in session:
        return redirect(url_for("login"))
    try:
        return render_template(
            "Control de calidad/historial_cambio_material_smt_ajax.html"
        )
    except Exception as e:
        print(f"Error en historial_cambio_material_smt_ajax: {e}")
        return f"Error interno del servidor: {e}", 500


@app.route("/api/csv_data")
@login_requerido
def get_csv_data():
    """API para obtener datos SMT desde MySQL (no archivos CSV)"""
    try:
        folder = request.args.get("folder", "")
        print(f" Solicitud recibida para carpeta: '{folder}'")

        if not folder:
            print(" No se proporcionó parámetro de carpeta")
            return jsonify(
                {"success": False, "error": "Folder parameter required"}
            ), 400

        # Conectar a MySQL directamente
        import mysql.connector

        mysql_config = {
            "host": os.getenv("MYSQL_HOST"),
            "port": int(os.getenv("MYSQL_PORT", 3306)),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": os.getenv("MYSQL_DATABASE"),
            "charset": "utf8mb4",
        }

        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)

        print(f" Consultando datos SMT desde MySQL para carpeta: {folder}")

        # Query para obtener datos de la tabla MySQL
        query = """
            SELECT
            ScanDate,
            ScanTime,
            SlotNo,
            Result,
            PreviousBarcode,
            Productdate,
            PartName,
            Quantity,
            SEQ,
            Vendor,
            LOTNO,
            Barcode,
            FeederBase,
            archivo,
            linea,
            maquina,
            fecha_subida
        FROM logs_maquina
        WHERE archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s
        ORDER BY ScanDate DESC, ScanTime DESC
        LIMIT 1000
        """

        cursor.execute(query, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        resultados = cursor.fetchall()

        print(f"✓ Encontrados {len(resultados)} registros en MySQL")

        # Convertir datos para JSON
        all_data = []
        for resultado in resultados:
            cleaned_record = {}
            for key, value in resultado.items():
                if hasattr(value, "isoformat"):  # Es una fecha/datetime
                    cleaned_record[key] = value.isoformat()
                elif value is None:
                    cleaned_record[key] = None
                else:
                    cleaned_record[key] = str(value)

            # Mapear nombres para compatibilidad con frontend (usar nombres de la nueva tabla)
            cleaned_record["ScanDate"] = cleaned_record.get("ScanDate", "")
            cleaned_record["ScanTime"] = cleaned_record.get("ScanTime", "")
            cleaned_record["SlotNo"] = cleaned_record.get("SlotNo", "")
            cleaned_record["Result"] = cleaned_record.get("Result", "")
            cleaned_record["PartName"] = cleaned_record.get("PartName", "")
            cleaned_record["SourceFile"] = cleaned_record.get(
                "archivo", ""
            )  # Mapear archivo a SourceFile
            cleaned_record["LOTNO"] = cleaned_record.get("LOTNO", "")
            cleaned_record["Barcode"] = cleaned_record.get("Barcode", "")
            cleaned_record["Quantity"] = cleaned_record.get("Quantity", "")
            cleaned_record["Vendor"] = cleaned_record.get("Vendor", "")
            cleaned_record["FeederBase"] = cleaned_record.get("FeederBase", "")
            cleaned_record["PreviousBarcode"] = cleaned_record.get(
                "PreviousBarcode", ""
            )

            all_data.append(cleaned_record)

        cursor.close()
        conn.close()

        return jsonify(
            {
                "success": True,
                "data": all_data,
                "message": f"Datos MySQL cargados para {folder}: {len(all_data)} registros",
                "files_processed": len(
                    set([d.get("SourceFile", "") for d in all_data])
                ),
                "source": "mysql_logs_maquina",
            }
        )

    except Exception as e:
        print(f" Error obteniendo datos desde MySQL: {e}")
        print(f" Traceback: {traceback.format_exc()}")
        return jsonify(
            {
                "success": False,
                "error": f"Error al consultar base de datos MySQL: {str(e)}",
            }
        ), 500


@app.route("/api/csv_stats")
@login_requerido
def get_csv_stats():
    """API para obtener estadísticas SMT desde MySQL (no archivos CSV)"""
    try:
        folder = request.args.get("folder", "")
        print(f" Solicitud recibida para estadísticas de carpeta: '{folder}'")

        if not folder:
            print(" No se proporcionó parámetro de carpeta")
            return jsonify(
                {"success": False, "error": "Folder parameter required"}
            ), 400

        # Conectar a MySQL directamente
        import mysql.connector

        mysql_config = {
            "host": os.getenv("MYSQL_HOST"),
            "port": int(os.getenv("MYSQL_PORT", 3306)),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": os.getenv("MYSQL_DATABASE"),
            "charset": "utf8mb4",
        }

        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)

        print(f" Consultando estadísticas SMT desde MySQL para carpeta: {folder}")

        # Query para obtener estadísticas de la tabla MySQL
        query = """
            SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT archivo) as total_files,
            COUNT(DISTINCT ScanDate) as total_days,
            COUNT(CASE WHEN Result = 'OK' THEN 1 END) as ok_count,
            COUNT(CASE WHEN Result = 'NG' THEN 1 END) as ng_count,
            MIN(ScanDate) as first_date,
            MAX(ScanDate) as last_date
        FROM logs_maquina
        WHERE archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s
        """

        cursor.execute(query, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        stats = cursor.fetchone()

        # Query para obtener archivos únicos
        files_query = """
        SELECT DISTINCT archivo, COUNT(*) as records
        FROM logs_maquina
        WHERE archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s
        GROUP BY archivo
        ORDER BY archivo
        """

        cursor.execute(files_query, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        files_info = cursor.fetchall()

        cursor.close()
        conn.close()

        print(
            f" Estadísticas obtenidas: {stats['total_records']} registros de {stats['total_files']} archivos"
        )

        return jsonify(
            {
                "success": True,
                "stats": {
                    "total_records": stats["total_records"] or 0,
                    "total_files": stats["total_files"] or 0,
                    "total_days": stats["total_days"] or 0,
                    "ok_count": stats["ok_count"] or 0,
                    "ng_count": stats["ng_count"] or 0,
                    "first_date": stats["first_date"].isoformat()
                    if stats["first_date"]
                    else None,
                    "last_date": stats["last_date"].isoformat()
                    if stats["last_date"]
                    else None,
                },
                "files": [
                    {"name": f["source_file"], "records": f["records"]}
                    for f in files_info
                ],
                "message": f"Estadísticas MySQL para {folder}",
                "source": "mysql",
            }
        )

    except Exception as e:
        print(f" Error obteniendo estadísticas desde MySQL: {e}")
        print(f" Traceback: {traceback.format_exc()}")
        return jsonify(
            {
                "success": False,
                "error": f"Error al consultar estadísticas MySQL: {str(e)}",
            }
        ), 500

        print(f" Encontrados {len(csv_files)} archivos CSV")

        # Leer y combinar todos los archivos CSV
        all_data = []

        for csv_file in csv_files:
            try:
                print(
                    f" Leyendo archivo: {os.path.basename(csv_file)} (tamaño: {os.path.getsize(csv_file)} bytes)"
                )

                # Intentar lectura simple primero
                try:
                    df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
                    print(f" Lectura exitosa con pandas básico: {len(df)} filas")
                except Exception as simple_error:
                    print(f" Error con lectura simple: {str(simple_error)}")

                    # Leer el archivo como texto primero para limpiar formato
                    with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    print(f" Contenido leído: {len(content)} caracteres")

                    # Limpiar saltos de línea incorrectos en el contenido
                    lines = content.strip().split("\n")
                    cleaned_lines = []

                    for line in lines:
                        # Si la línea no termina con una coma y la siguiente no empieza con una fecha,
                        # probablemente es una línea cortada
                        if line and not line.endswith(","):
                            cleaned_lines.append(line)
                        elif line.endswith(","):
                            # Línea que termina en coma, probablemente incompleta
                            if cleaned_lines:
                                cleaned_lines[-1] += line
                            else:
                                cleaned_lines.append(line)

                    print(
                        f"🧹 Líneas limpiadas: {len(cleaned_lines)} de {len(lines)} originales"
                    )

                    # Crear DataFrame desde el contenido limpio
                    from io import StringIO

                    cleaned_content = "\n".join(cleaned_lines)

                    # Leer el archivo CSV con pandas usando el contenido limpio
                    df = pd.read_csv(
                        StringIO(cleaned_content), encoding="utf-8", on_bad_lines="skip"
                    )

                print(f" DataFrame creado: {len(df)} filas, {len(df.columns)} columnas")
                print(f" Columnas: {list(df.columns)}")

                # Verificar que el DataFrame tenga las columnas esperadas
                expected_columns = [
                    "ScanDate",
                    "ScanTime",
                    "SlotNo",
                    "Result",
                    "PartName",
                ]
                missing_columns = [
                    col for col in expected_columns if col not in df.columns
                ]

                if missing_columns:
                    print(f" Columnas faltantes en {csv_file}: {missing_columns}")
                    # Intentar leer de forma más básica
                    df = pd.read_csv(
                        csv_file, encoding="utf-8", on_bad_lines="skip", sep=","
                    )

                # Convertir a diccionarios y agregar nombre del archivo fuente
                file_data = df.to_dict("records")

                # Limpiar valores NaN y convertir a tipos JSON válidos
                cleaned_data = []
                for record in file_data:
                    cleaned_record = {}
                    for key, value in record.items():
                        # Convertir NaN y valores problemáticos a None (null en JSON)
                        if pd.isna(value) or str(value).lower() == "nan":
                            cleaned_record[key] = None
                        elif isinstance(value, (int, float)) and (
                            value != value
                        ):  # Check for NaN
                            cleaned_record[key] = None
                        else:
                            # Convertir a string para asegurar compatibilidad JSON
                            cleaned_record[key] = (
                                str(value) if value is not None else None
                            )

                    cleaned_record["SourceFile"] = os.path.basename(csv_file)
                    cleaned_data.append(cleaned_record)

                print(
                    f" Datos procesados y limpiados: {len(cleaned_data)} registros del archivo {os.path.basename(csv_file)}"
                )
                all_data.extend(cleaned_data)

            except Exception as file_error:
                print(f" Error definitivo leyendo {csv_file}: {str(file_error)}")
                print(f" Tipo de error: {type(file_error).__name__}")
                import traceback

                print(f" Traceback: {traceback.format_exc()}")
                continue

        if not all_data:
            return jsonify(
                {
                    "success": False,
                    "error": "No se pudieron leer datos de los archivos CSV",
                    "files_found": len(csv_files),
                }
            ), 500

        print(
            f" Datos cargados: {len(all_data)} registros de {len(csv_files)} archivos"
        )

        return jsonify(
            {
                "success": True,
                "data": all_data,
                "message": f"Datos cargados para {folder}: {len(all_data)} registros",
                "files_processed": len(csv_files),
                "path": folder_path,
            }
        )

    except Exception as e:
        print(f" Error obteniendo datos CSV: {e}")
        print(f" Traceback: {traceback.format_exc()}")
        return jsonify(
            {
                "success": False,
                "error": f"Error al acceder a los archivos CSV: {str(e)}",
            }
        ), 500


@app.route("/api/filter_data", methods=["POST"])
@login_requerido
def filter_csv_data():
    """API para filtrar datos SMT desde MySQL (no archivos CSV)"""
    try:
        filters = request.get_json()
        folder = filters.get("folder", "")
        part_name = filters.get("partName", "")
        result = filters.get("result", "")
        date_from = filters.get("dateFrom", "")
        date_to = filters.get("dateTo", "")

        if not folder:
            return jsonify(
                {"success": False, "error": "Folder parameter required"}
            ), 400

        print(f" Filtrando datos MySQL para carpeta: {folder}")
        print(
            f" Filtros: partName={part_name}, result={result}, dateFrom={date_from}, dateTo={date_to}"
        )

        # Conectar a MySQL directamente
        import mysql.connector

        mysql_config = {
            "host": os.getenv("MYSQL_HOST"),
            "port": int(os.getenv("MYSQL_PORT", 3306)),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": os.getenv("MYSQL_DATABASE"),
            "charset": "utf8mb4",
        }

        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)

        # Construir query dinámicamente con filtros
        where_conditions = ["source_file LIKE %s"]
        params = [f"%{folder}%"]

        if part_name:
            where_conditions.append("part_name LIKE %s")
            params.append(f"%{part_name}%")

        if result:
            where_conditions.append("result = %s")
            params.append(result.upper())

        if date_from:
            where_conditions.append("ScanDate >= %s")
            params.append(date_from.replace("-", ""))  # Convertir YYYY-MM-DD a YYYYMMDD

        if date_to:
            where_conditions.append("ScanDate <= %s")
            params.append(date_to.replace("-", ""))  # Convertir YYYY-MM-DD a YYYYMMDD

        where_clause = " AND ".join(where_conditions)

        query = f"""
            SELECT
            scan_date,
            scan_time,
            slot_no,
            result,
            previous_barcode,
            product_date,
            part_name,
            quantity,
            seq,
            vendor,
            lot_no,
            barcode,
            feeder_base,
            source_file,
            created_at
        FROM historial_cambio_material_smt
        WHERE {where_clause}
        ORDER BY ScanDate DESC, ScanTime DESC
            LIMIT 5000
        """

        cursor.execute(query, params)
        resultados = cursor.fetchall()

        print(f" Encontrados {len(resultados)} registros con filtros aplicados")

        # Convertir datos para JSON y mapear nombres para compatibilidad
        filtered_data = []
        for resultado in resultados:
            cleaned_record = {}
            for key, value in resultado.items():
                if hasattr(value, "isoformat"):  # Es una fecha/datetime
                    cleaned_record[key] = value.isoformat()
                elif value is None:
                    cleaned_record[key] = None
                else:
                    cleaned_record[key] = str(value)

            # Mapear nombres para compatibilidad con frontend
            cleaned_record["ScanDate"] = cleaned_record.get("ScanDate", "")
            cleaned_record["ScanTime"] = cleaned_record.get("scan_time", "")
            cleaned_record["SlotNo"] = cleaned_record.get("slot_no", "")
            cleaned_record["Result"] = cleaned_record.get("result", "")
            cleaned_record["PartName"] = cleaned_record.get("part_name", "")
            cleaned_record["SourceFile"] = cleaned_record.get("source_file", "")
            cleaned_record["LOTNO"] = cleaned_record.get("lot_no", "")
            cleaned_record["Barcode"] = cleaned_record.get("barcode", "")
            cleaned_record["Quantity"] = cleaned_record.get("quantity", "")
            cleaned_record["Vendor"] = cleaned_record.get("vendor", "")
            cleaned_record["FeederBase"] = cleaned_record.get("feeder_base", "")
            cleaned_record["PreviousBarcode"] = cleaned_record.get(
                "previous_barcode", ""
            )

            filtered_data.append(cleaned_record)

        # Calcular estadísticas de los datos filtrados
        stats = {
            "total_records": len(filtered_data),
            "ok_count": len(
                [d for d in filtered_data if str(d.get("Result", "")).upper() == "OK"]
            ),
            "ng_count": len(
                [d for d in filtered_data if str(d.get("Result", "")).upper() == "NG"]
            ),
        }

        cursor.close()
        conn.close()

        print(f" Datos filtrados desde MySQL: {len(filtered_data)} registros")

        return jsonify(
            {
                "success": True,
                "data": filtered_data,
                "stats": stats,
                "source": "mysql",
                "message": f"Datos filtrados desde MySQL para {folder}",
            }
        )

    except Exception as e:
        print(f" Error filtrando datos desde MySQL: {e}")
        print(f" Traceback: {traceback.format_exc()}")
        return jsonify(
            {"success": False, "error": f"Error al filtrar datos MySQL: {str(e)}"}
        ), 500


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


def cargar_configuracion_usuario(usuario):
    """Cargar configuración específica del usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT configuracion FROM usuarios_sistema
            WHERE username = %s
        """,
            (usuario,),
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result[0]:  # Usar índice en lugar de clave de diccionario
            import json

            return json.loads(result[0])
        else:
            return {}

    except Exception as e:
        print(f"Error cargando configuración del usuario {usuario}: {e}")
        return {}


def guardar_configuracion_usuario(usuario, config, valor=None):
    """Guardar configuración específica del usuario.

    Acepta:
    - guardar_configuracion_usuario(usuario, config_dict)
    - guardar_configuracion_usuario(usuario, clave, valor)
    """
    try:
        import json

        if valor is not None:
            config_actual = cargar_configuracion_usuario(usuario) or {}
            config_actual[str(config)] = valor
            config = config_actual
        elif not isinstance(config, dict):
            raise ValueError("config debe ser un diccionario o una clave con valor")

        conn = get_db_connection()
        cursor = conn.cursor()

        config_json = json.dumps(config)

        cursor.execute(
            """
            UPDATE usuarios_sistema
            SET configuracion = %s
            WHERE username = %s
        """,
            (config_json, usuario),
        )

        success = cursor.rowcount > 0
        conn.commit()
        cursor.close()
        conn.close()

        return success

    except Exception as e:
        print(f"Error guardando configuración del usuario {usuario}: {e}")
        return False


@app.route("/guardar_regla_trazabilidad", methods=["POST"])
def guardar_regla_trazabilidad():
    """Guardar nueva regla de trazabilidad en rules.json"""
    try:
        if "usuario" not in session:
            return jsonify({"error": "Usuario no autenticado"}), 401

        # Obtener los datos de la nueva regla
        nueva_regla = request.get_json()

        if not nueva_regla:
            return jsonify({"error": "No se recibieron datos"}), 400

        # Validar campos requeridos
        campos_requeridos = ["proveedor", "numero_parte", "texto_original"]
        for campo in campos_requeridos:
            if not nueva_regla.get(campo):
                return jsonify({"error": f"Campo requerido faltante: {campo}"}), 400

        # Ruta del archivo rules.json
        rules_file = os.path.join(os.path.dirname(__file__), "database", "rules.json")

        # Cargar reglas existentes
        reglas_existentes = {}
        if os.path.exists(rules_file):
            try:
                with open(rules_file, "r", encoding="utf-8") as f:
                    reglas_existentes = json.load(f)
            except json.JSONDecodeError:
                reglas_existentes = {}

        # Generar clave única para la nueva regla
        proveedor = nueva_regla["proveedor"].upper()
        contador = 1
        clave_base = proveedor
        clave_final = clave_base

        # Si ya existe la clave, agregar número secuencial
        while clave_final in reglas_existentes:
            contador += 1
            clave_final = f"{clave_base}{contador}"

        # Convertir la nueva regla al formato esperado
        texto_original = nueva_regla["texto_original"]
        numero_parte = nueva_regla["numero_parte"]
        numero_lote = nueva_regla.get("numero_lote", "")

        # Calcular posiciones reales
        part_number_start = texto_original.find(numero_parte)
        part_number_length = len(numero_parte)

        if numero_lote and numero_lote.strip():
            lot_number_start = texto_original.find(numero_lote)
            lot_number_length = len(numero_lote)
        else:
            lot_number_start = -1
            lot_number_length = 0

        # Validar que se encontraron las posiciones
        if part_number_start == -1:
            return jsonify(
                {
                    "error": "No se pudo encontrar el número de parte en el texto original"
                }
            ), 400

        if numero_lote and numero_lote.strip() and lot_number_start == -1:
            return jsonify(
                {"error": "No se pudo encontrar el número de lote en el texto original"}
            ), 400

        # Crear patrón de caracteres
        character_pattern = crear_patron_caracteres(
            texto_original,
            part_number_start,
            part_number_length,
            lot_number_start,
            lot_number_length,
        )

        regla_formateada = {
            "character_pattern": character_pattern,
            "partNumberStart": part_number_start,
            "partNumberLength": part_number_length,
            "lotNumberStart": lot_number_start,
            "lotNumberLength": lot_number_length,
        }

        # Agregar la nueva regla con la clave generada
        reglas_existentes[clave_final] = regla_formateada

        # Guardar de vuelta al archivo
        with open(rules_file, "w", encoding="utf-8") as f:
            json.dump(reglas_existentes, f, indent=2, ensure_ascii=False)

        print(
            f" Nueva regla de trazabilidad guardada: {clave_final} - {nueva_regla['proveedor']} - {nueva_regla['numero_parte']}"
        )

        return jsonify(
            {
                "success": True,
                "message": "Regla guardada exitosamente",
                "regla_clave": clave_final,
                "proveedor": nueva_regla["proveedor"],
            }
        )

    except Exception as e:
        print(f" Error guardando regla de trazabilidad: {e}")
        print(f" Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500


# ===================================================================
# 🚀 RUTAS ADICIONALES PARA CONTROL DE SALIDA OPTIMIZADO
# ===================================================================


@app.route("/control_salida/estado", methods=["GET"])
@login_requerido
def control_salida_estado():
    """
     Obtener estado general del módulo Control de Salida

    Retorna:
    - Estadísticas del día
    - Configuración del usuario
    - Estado del sistema
    """
    try:
        usuario = session.get("usuario", "Usuario")
        hoy = time.strftime("%Y-%m-%d")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener estadísticas del día
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_salidas,
                COALESCE(SUM(cantidad_salida), 0) as total_cantidad
            FROM salidas_material
            WHERE DATE(fecha_salida) = %s
        """,
            (hoy,),
        )

        stats = cursor.fetchone()

        conn.close()

        return jsonify(
            {
                "success": True,
                "estado": {
                    "usuario": usuario,
                    "fecha": hoy,
                    "estadisticas": {
                        "salidas_hoy": stats["total_salidas"] if stats else 0,
                        "cantidad_total_hoy": stats["total_cantidad"] if stats else 0,
                    },
                    "configuracion": {
                        "auto_focus": True,
                        "scan_mode": "optimized",
                        "version": "2.0",
                    },
                },
            }
        )

    except Exception as e:
        print(f" Error obteniendo estado Control de Salida: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/control_salida/configuracion", methods=["GET", "POST"])
@login_requerido
def control_salida_configuracion():
    """
    ⚙️ Gestionar configuración del usuario para Control de Salida

    GET: Obtener configuración actual
    POST: Guardar nueva configuración
    """
    try:
        usuario = session.get("usuario", "Usuario")

        if request.method == "GET":
            # Obtener configuración del usuario
            config = cargar_configuracion_usuario(usuario)

            # Configuración por defecto para Control de Salida
            control_salida_config = config.get(
                "control_salida",
                {
                    "registro_automatico": True,
                    "verificacion_requerida": True,
                    "auto_focus": True,
                    "mostrar_ayuda": True,
                    "tiempo_mensaje": 2500,
                },
            )

            return jsonify({"success": True, "configuracion": control_salida_config})

        elif request.method == "POST":
            # Guardar nueva configuración
            data = request.get_json()

            if not data:
                return jsonify(
                    {"success": False, "error": "No se recibieron datos"}
                ), 400

            # Cargar configuración existente
            config = cargar_configuracion_usuario(usuario)
            config["control_salida"] = data

            # Guardar configuración actualizada
            success = guardar_configuracion_usuario(usuario, config)

            return jsonify(
                {
                    "success": success,
                    "message": "Configuración guardada exitosamente"
                    if success
                    else "Error al guardar configuración",
                }
            )

    except Exception as e:
        print(f" Error en configuración Control de Salida: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/control_salida/validar_stock", methods=["POST"])
@login_requerido
def control_salida_validar_stock():
    """
     Validar stock disponible antes de procesar salida

    Útil para validaciones rápidas sin procesar la salida
    """
    try:
        data = request.get_json()
        codigo_recibido = data.get("codigo_recibido")
        cantidad_requerida = float(data.get("cantidad_requerida", 1))

        if not codigo_recibido:
            return jsonify(
                {"success": False, "error": "Código de material requerido"}
            ), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Buscar material por código
        cursor.execute(
            """
            SELECT
                codigo_material_recibido,
                numero_parte,
                especificacion,
                cantidad_actual,
                numero_lote_material
            FROM control_material_almacen
            WHERE codigo_material_recibido = %s OR codigo_material = %s
            ORDER BY fecha_registro DESC
            LIMIT 1
        """,
            (codigo_recibido, codigo_recibido),
        )

        material = cursor.fetchone()
        conn.close()

        if not material:
            return jsonify(
                {
                    "success": False,
                    "disponible": False,
                    "error": "Material no encontrado",
                }
            )

        cantidad_actual = float(material["cantidad_actual"] or 0)
        stock_suficiente = cantidad_actual >= cantidad_requerida

        return jsonify(
            {
                "success": True,
                "disponible": stock_suficiente,
                "material": {
                    "codigo": material["codigo_material_recibido"],
                    "numero_parte": material["numero_parte"],
                    "especificacion": material["especificacion"],
                    "stock_actual": cantidad_actual,
                    "cantidad_requerida": cantidad_requerida,
                    "diferencia": 0,  # diferencia inicial = 0 (campo vacío para entrada manual)
                    "lote": material["numero_lote_material"],
                },
            }
        )

    except Exception as e:
        print(f" Error validando stock: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/control_salida/reporte_diario", methods=["GET"])
@login_requerido
def control_salida_reporte_diario():
    """
    📈 Generar reporte diario de salidas de material

    Parámetros opcionales:
    - fecha: fecha específica (YYYY-MM-DD)
    - formato: 'json' o 'excel'
    """
    try:
        fecha = request.args.get("fecha", time.strftime("%Y-%m-%d"))
        formato = request.args.get("formato", "json")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Consultar salidas del día
        cursor.execute(
            """
            SELECT
                fecha_salida,
                codigo_material_recibido,
                numero_parte,
                cantidad_salida,
                modelo,
                numero_lote,
                proceso_salida,
                departamento
            FROM salidas_material
            WHERE DATE(fecha_salida) = %s
            ORDER BY fecha_salida DESC
        """,
            (fecha,),
        )

        salidas = cursor.fetchall()

        # Estadísticas resumen
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_salidas,
                COALESCE(SUM(cantidad_salida), 0) as cantidad_total,
                COUNT(DISTINCT numero_parte) as partes_diferentes,
                COUNT(DISTINCT modelo) as modelos_diferentes
            FROM salidas_material
            WHERE DATE(fecha_salida) = %s
        """,
            (fecha,),
        )

        estadisticas = cursor.fetchone()
        conn.close()

        if formato == "json":
            return jsonify(
                {
                    "success": True,
                    "fecha": fecha,
                    "estadisticas": {
                        "total_salidas": estadisticas["total_salidas"],
                        "cantidad_total": estadisticas["cantidad_total"],
                        "partes_diferentes": estadisticas["partes_diferentes"],
                        "modelos_diferentes": estadisticas["modelos_diferentes"],
                    },
                    "salidas": [dict(row) for row in salidas],
                }
            )

        # TODO: Implementar exportación a Excel si se requiere
        return jsonify({"success": False, "error": "Formato no soportado aún"}), 400

    except Exception as e:
        print(f" Error generando reporte diario: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


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


# ===================================================================
# 🔧 RUTAS DE MANTENIMIENTO Y DEBUGGING PARA CONTROL DE SALIDA
# ===================================================================


@app.route("/control_salida/debug/test_connection", methods=["GET"])
@login_requerido
def control_salida_test_connection():
    """
    Probar conexión y funcionalidad básica del módulo
    """
    try:
        tests = []

        # Test 1: Conexión a base de datos
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            tests.append({"test": "Database Connection", "status": "OK"})
        except Exception as e:
            tests.append(
                {"test": "Database Connection", "status": "FAIL", "error": str(e)}
            )

        # Test 2: Verificar tablas necesarias
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar tabla salidas_material
            cursor.execute(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'salidas_material'"
            )
            if cursor.fetchone():
                tests.append({"test": "Table salidas_material", "status": "OK"})
            else:
                tests.append({"test": "Table salidas_material", "status": "MISSING"})

            # Verificar tabla control_material_almacen
            cursor.execute(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'control_material_almacen'"
            )
            if cursor.fetchone():
                tests.append({"test": "Table control_material_almacen", "status": "OK"})
            else:
                tests.append(
                    {"test": "Table control_material_almacen", "status": "MISSING"}
                )

            conn.close()
        except Exception as e:
            tests.append(
                {"test": "Table Verification", "status": "FAIL", "error": str(e)}
            )

        # Test 3: Funciones de inventario
        try:
            from .db import actualizar_inventario_general_salida

            tests.append({"test": "Inventory Functions", "status": "OK"})
        except Exception as e:
            tests.append(
                {"test": "Inventory Functions", "status": "FAIL", "error": str(e)}
            )

        return jsonify(
            {
                "success": True,
                "tests": tests,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "overall_status": "OK"
                if all(t["status"] == "OK" for t in tests)
                else "ISSUES",
            }
        )

    except Exception as e:
        print(f" Error en test de conexión: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Rutas de importación AJAX para todas las secciones de material
@app.route("/importar_excel_almacen", methods=["POST"])
def importar_excel_almacen():
    """Importación AJAX para Control de Material de Almacén"""
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
            df = pd.read_excel(
                temp_path, engine="openpyxl" if filename.endswith(".xlsx") else "xlrd"
            )
        except Exception as e:
            try:
                df = pd.read_excel(temp_path)
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

        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()

        registros_insertados = 0
        errores = []

        # Procesar cada fila del DataFrame
        for index, row in df.iterrows():
            try:
                # Insertar en tabla de control de almacén (ajustar según estructura de tu tabla)
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO control_almacen
                    (codigo_material_recibido, codigo_material, numero_parte, numero_lote,
                     propiedad_material, fecha_recibo, cantidad_actual, ubicacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        str(row.get("Codigo Material Recibido", "")),
                        str(row.get("Codigo Material", "")),
                        str(row.get("Numero Parte", "")),
                        str(row.get("Numero Lote", "")),
                        str(row.get("Propiedad Material", "")),
                        str(row.get("Fecha Recibo", "")),
                        str(row.get("Cantidad Recibida", 0)),
                        str(row.get("Ubicacion", "")),
                    ),
                )
                registros_insertados += 1
            except Exception as e:
                errores.append(f"Fila {index + 1}: {str(e)}")

        conn.commit()

        mensaje = (
            f"Importación completada. {registros_insertados} registros insertados."
        )
        if errores:
            mensaje += f" {len(errores)} errores encontrados."

        return jsonify({"success": True, "message": mensaje})

    except Exception as e:
        return jsonify(
            {"success": False, "error": f"Error durante la importación: {str(e)}"}
        ), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.route("/produccion/info")
@login_requerido
def produccion_info():
    try:
        return render_template("CONTROL DE PRODUCCION/info_produccion.html")
    except Exception as e:
        return f"Error al cargar información de producción: {str(e)}", 500


@app.route("/api/wo/exportar", methods=["GET"])
@login_requerido
def exportar_wos_excel():
    """Exportar WOs a Excel"""
    try:
        import io

        from flask import send_file
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        # Obtener parámetros de filtro
        fecha_desde = request.args.get("fecha_desde")
        fecha_hasta = request.args.get("fecha_hasta")

        # Obtener WOs con filtros
        from .po_wo_models import listar_wos

        wos = listar_wos(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)

        # Crear workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Work Orders"

        # Definir encabezados que coincidan con la tabla HTML
        headers = [
            "Código WO",
            "Estado",
            "Fecha Operación",
            "Línea",
            "Código Modelo",
            "Nombre Modelo",
            "Cantidad Planeada",
            "Código PO",
            "Registrado",
            "Modificador",
            "Fecha Modificación",
            "Fecha Creación",
        ]

        # Estilos para encabezados
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="172A46", end_color="172A46", fill_type="solid"
        )
        header_alignment = Alignment(horizontal="center", vertical="center")
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Escribir encabezados
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border

        # Escribir datos
        for row_num, wo in enumerate(wos, 2):
            # Datos que coincidan con las columnas de la tabla HTML
            data = [
                wo.get("codigo_wo", ""),  # Código WO
                wo.get("estado", "CREADA"),  # Estado
                wo.get("fecha_operacion", ""),  # Fecha Operación
                wo.get("linea", "SMT-1"),  # Línea
                wo.get("codigo_modelo", "") or wo.get("modelo", ""),  # Código Modelo
                wo.get("nombre_modelo", ""),  # Nombre Modelo
                wo.get("cantidad_planeada", 0),  # Cantidad Planeada
                wo.get("codigo_po", "SIN-PO"),  # Código PO
                "Sí" if wo.get("registrado") else "No",  # Registrado
                wo.get("modificador", ""),  # Modificador
                wo.get("fecha_modificacion", ""),  # Fecha Modificación
                wo.get("fecha_creacion", ""),  # Fecha Creación
            ]

            for col_num, value in enumerate(data, 1):
                cell = ws.cell(row=row_num, column=col_num, value=value)
                cell.border = border
                cell.alignment = Alignment(horizontal="center", vertical="center")

        # Ajustar ancho de columnas
        column_widths = {
            "A": 15,  # Código WO
            "B": 12,  # Estado
            "C": 15,  # Fecha Operación
            "D": 8,  # Línea
            "E": 15,  # Código Modelo
            "F": 20,  # Nombre Modelo
            "G": 12,  # Cantidad Planeada
            "H": 12,  # Código PO
            "I": 10,  # Registrado
            "J": 15,  # Modificador
            "K": 18,  # Fecha Modificación
            "L": 18,  # Fecha Creación
        }

        for column, width in column_widths.items():
            ws.column_dimensions[column].width = width

        # Guardar en buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        # Generar nombre de archivo
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"work_orders_{timestamp}.xlsx"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        print(f"Error exportando WOs: {e}")
        return jsonify(
            {"success": False, "error": f"Error exportando WOs: {str(e)}"}
        ), 500




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


@app.route("/control-resultado-reparacion-ajax")
@login_requerido
def control_resultado_reparacion_ajax():
    """Template para Control de resultado de reparación"""
    return render_template("Control de calidad/control_resultado_reparacion_ajax.html")


@app.route("/control-item-reparado-ajax")
@login_requerido
def control_item_reparado_ajax():
    """Template para Control de item reparado"""
    return render_template("Control de calidad/control_item_reparado_ajax.html")


@app.route("/historial-cambio-material-maquina-ajax")
@login_requerido
def historial_cambio_material_maquina_ajax():
    """Template para Historial de cambio de material por máquina"""
    return render_template(
        "Control de calidad/historial_cambio_material_maquina_ajax.html"
    )


@app.route("/api/historial-cambio-material-maquina", methods=["GET"])
@login_requerido
def api_historial_cambio_material_maquina():
    """API para obtener historial de cambio de material por máquina"""
    try:
        # Obtener parámetros de filtrado
        equipment = request.args.get("equipment", "")
        slot_no = request.args.get("slot_no", "")
        date_from = request.args.get("date_from", "")
        date_to = request.args.get("date_to", "")
        part_name = request.args.get("part_name", "")

        print(f" API Historial cambio material - Filtros:")
        print(f"  Equipment: {equipment}")
        print(f"  Slot No: {slot_no}")
        print(f"  Date From: {date_from}")
        print(f"  Date To: {date_to}")
        print(f"  Part Name: {part_name}")

        from .db_mysql import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        # Consulta simple y segura
        query = """
            SELECT
                linea,
                maquina,
                ScanDate,
                ScanTime,
                SlotNo,
                Result,
                PreviousBarcode,
                Productdate,
                PartName,
                Quantity,
                SEQ,
                Vendor,
                LOTNO,
                Barcode,
                FeederBase,
                archivo
            FROM historial_cambio_material_smt
            WHERE ScanDate >= %s
            ORDER BY ScanDate DESC, ScanTime DESC
            LIMIT 1000
        """

        # Usar fecha por defecto si no se proporciona
        default_date = "20250801"
        cursor.execute(query, [default_date])
        resultados = cursor.fetchall()

        print(f" Encontrados {len(resultados)} registros en historial cambio material")

        # Formatear datos para la tabla de manera más segura
        formatted_data = []
        for i, row in enumerate(resultados):
            try:
                # Acceso seguro a índices
                linea = row[0] if len(row) > 0 else ""
                maquina = row[1] if len(row) > 1 else ""
                scan_date = row[2] if len(row) > 2 else ""
                scan_time = row[3] if len(row) > 3 else ""
                slot_no = row[4] if len(row) > 4 else ""
                result = row[5] if len(row) > 5 else ""
                previous_barcode = row[6] if len(row) > 6 else ""
                product_date = row[7] if len(row) > 7 else ""
                part_name = row[8] if len(row) > 8 else ""
                quantity = row[9] if len(row) > 9 else 0
                seq = row[10] if len(row) > 10 else ""
                vendor = row[11] if len(row) > 11 else ""
                lot_no = row[12] if len(row) > 12 else ""
                barcode = row[13] if len(row) > 13 else ""
                feeder_base = row[14] if len(row) > 14 else ""
                archivo = row[15] if len(row) > 15 else ""

                # Formatear fecha
                formatted_date = scan_date
                if scan_date and len(str(scan_date)) == 8:
                    date_str = str(scan_date)
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

                formatted_row = {
                    "equipment": linea or "",
                    "slot_no": str(slot_no) if slot_no else "",
                    "regist_date": formatted_date or "",
                    "warehousing": vendor or "",
                    "regist_quantity": quantity or 0,
                    "current_quantity": quantity or 0,
                    "part_name": part_name or "",
                    "machine": maquina or "",
                    "result": result or "",
                    "scan_time": scan_time or "",
                    "barcode": barcode or "",
                    "lot_no": lot_no or "",
                }
                formatted_data.append(formatted_row)

            except Exception as row_error:
                print(f" Error procesando fila {i}: {row_error}")
                continue

        cursor.close()
        conn.close()

        print(f"? Enviando {len(formatted_data)} registros al frontend")

        return jsonify(
            {
                "success": True,
                "data": formatted_data,
                "total": len(formatted_data),
                "message": f"Se encontraron {len(formatted_data)} registros",
            }
        )

    except Exception as e:
        print(f" Error en API historial cambio material: {e}")
        print(f" Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


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


@app.route("/historial-uso-pegamento-soldadura-ajax")
@login_requerido
def historial_uso_pegamento_soldadura_ajax():
    """Template para Historial de uso de pegamento de soldadura"""
    return render_template(
        "Control de calidad/historial_uso_pegamento_soldadura_ajax.html"
    )


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


@app.route("/historial-uso-mask-metal-ajax")
@login_requerido
def historial_uso_mask_metal_ajax():
    """Template para Historial de uso de mask de metal"""
    return render_template("Control de calidad/historial_uso_mask_metal_ajax.html")


@app.route("/historial-uso-squeegee-ajax")
@login_requerido
def historial_uso_squeegee_ajax():
    """Template para Historial de uso de squeegee"""
    return render_template("Control de calidad/historial_uso_squeegee_ajax.html")


@app.route("/process-interlock-history-ajax")
@login_requerido
def process_interlock_history_ajax():
    """Template para Process interlock History"""
    return render_template("Control de calidad/process_interlock_history_ajax.html")


@app.route("/control-master-sample-smt-ajax")
@login_requerido
def control_master_sample_smt_ajax():
    """Template para Control de Master Sample de SMT"""
    return render_template("Control de calidad/control_master_sample_smt_ajax.html")


@app.route("/historial-inspeccion-master-sample-smt-ajax")
@login_requerido
def historial_inspeccion_master_sample_smt_ajax():
    """Template para Historial de inspección de Master Sample de SMT"""
    return render_template(
        "Control de calidad/historial_inspeccion_master_sample_smt_ajax.html"
    )


@app.route("/control-inspeccion-oqc-ajax")
@login_requerido
def control_inspeccion_oqc_ajax():
    """Template para Control de inspección de OQC"""
    return render_template("Control de calidad/control_inspeccion_oqc_ajax.html")


@app.route("/historial-liberacion-lqc-ajax")
@login_requerido
def historial_liberacion_lqc_ajax():
    """Template para Historial de liberacion LQC"""
    return render_template("Control de calidad/historial_liberacion_lqc_ajax.html")


def _lqc_fecha_operativa(now=None):
    from datetime import datetime, timedelta
    now = now or datetime.now()
    corte = now.replace(hour=7, minute=30, second=0, microsecond=0)
    if now >= corte:
        return now.date()
    return (now - timedelta(days=1)).date()


def _lqc_parse_fecha(value, fallback):
    from datetime import datetime
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").date()
    except Exception:
        return fallback


def _lqc_ventana_operativa(fecha_inicio, fecha_fin):
    from datetime import datetime, time, timedelta
    inicio = datetime.combine(fecha_inicio, time(7, 30))
    fin = datetime.combine(fecha_fin + timedelta(days=1), time(7, 30))
    return inicio, fin


@app.route("/api/smt-scanner/lineas")
@login_requerido
def api_smt_scanner_lineas():
    """Resumen de escaneos LQC por linea real usando box_scans + plan_main."""
    try:
        from datetime import datetime, timedelta
        ahora_dt = datetime.now()
        fecha_operativa = _lqc_fecha_operativa(ahora_dt)
        ventana_inicio, ventana_fin = _lqc_ventana_operativa(fecha_operativa, fecha_operativa)
        ventana_fin_consulta = min(ahora_dt, ventana_fin)
        hoy = fecha_operativa.isoformat()
        ahora = ahora_dt.strftime('%Y-%m-%d %H:%M:%S')
        inicio_sql = ventana_inicio.strftime('%Y-%m-%d %H:%M:%S')
        fin_sql = ventana_fin_consulta.strftime('%Y-%m-%d %H:%M:%S')
        lineas_config = ['M1','M2','M3','M4','DP1','DP2','DP3','H1']
        line_expr = "COALESCE(NULLIF(p.line, ''), 'SIN PLAN')"
        slot_expr = """
                    DATE_ADD(
                        STR_TO_DATE(
                            DATE_FORMAT(DATE_SUB(b.last_scan, INTERVAL 30 MINUTE), '%%Y-%%m-%%d %%H:00:00'),
                            '%%Y-%%m-%%d %%H:%%i:%%s'
                        ),
                        INTERVAL 30 MINUTE
                    )
        """

        conn = get_pooled_connection()
        if conn is None:
            return jsonify({"success": True, "lineas": [], "uph_hoy": {}})

        cursor = get_dict_cursor(conn)
        try:
            # Total por linea de la fecha operativa actual; corte 07:30.
            cursor.execute(f"""
                SELECT
                    {line_expr} AS linea,
                    COUNT(*) AS total_hoy
                FROM box_scans b
                LEFT JOIN plan_main p ON p.lot_no = b.lot_no
                WHERE b.last_scan >= %s
                  AND b.last_scan < %s
                GROUP BY linea
            """, (inicio_sql, fin_sql))
            rows = cursor.fetchall()
            counts = {r['linea']: int(r['total_hoy'] or 0) for r in rows}

            # UPH por bloque real de hora; evita mezclar horas iguales de dias distintos.
            cursor.execute(f"""
                SELECT
                    {line_expr} AS linea,
                    DATE_FORMAT({slot_expr}, '%%Y-%%m-%%d %%H:%%i:%%s') AS slot_key,
                    HOUR({slot_expr}) AS hora,
                    COUNT(*) AS total
                FROM box_scans b
                LEFT JOIN plan_main p ON p.lot_no = b.lot_no
                WHERE b.last_scan >= %s
                  AND b.last_scan < %s
                GROUP BY linea, slot_key, hora
                ORDER BY slot_key
            """, (inicio_sql, fin_sql))
            uph_rows = cursor.fetchall()
            uph_hoy = {}
            uph_slots_map = {}
            for r in uph_rows:
                l = r['linea']
                slot_key = r['slot_key']
                if l not in uph_hoy:
                    uph_hoy[l] = {}
                uph_hoy[l][slot_key] = int(r['total'] or 0)
                if slot_key not in uph_slots_map:
                    uph_slots_map[slot_key] = {
                        "key": slot_key,
                        "label": "",
                        "hour": int(r['hora'] or 0),
                    }
            uph_slots = []
            if ventana_fin_consulta >= ventana_inicio:
                start_slot = ventana_inicio
                end_slot = ventana_fin
                current_slot = start_slot
                while current_slot < end_slot:
                    key = current_slot.strftime('%Y-%m-%d %H:%M:%S')
                    slot = uph_slots_map.get(key, {
                        "key": key,
                        "hour": current_slot.hour,
                    })
                    slot["label"] = current_slot.strftime('%H:%M')
                    uph_slots.append(slot)
                    current_slot += timedelta(hours=1)

            ordered_lines = lineas_config[:]
            ordered_lines.extend(
                sorted([line for line in counts.keys() if line not in ordered_lines])
            )
            lineas = [{"linea": l, "total_hoy": counts.get(l, 0)} for l in ordered_lines]
            return jsonify({
                "success": True,
                "fecha_consulta": hoy,
                "actualizado": ahora,
                "ventana_inicio": inicio_sql,
                "ventana_fin": fin_sql,
                "lineas": lineas,
                "uph_hoy": uph_hoy,
                "uph_slots": uph_slots,
            })
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "lineas": [], "uph_hoy": {}}), 500


@app.route("/api/smt-scanner/datos")
@login_requerido
def api_smt_scanner_datos():
    """Registros LQC desde box_scans filtrados por linea real y rango de fechas."""
    try:
        from datetime import datetime
        fecha_default = _lqc_fecha_operativa()
        lineas = [l.strip() for l in request.args.getlist("lineas") if l.strip()]
        fecha_inicio = _lqc_parse_fecha(request.args.get("fecha_inicio"), fecha_default)
        fecha_fin = _lqc_parse_fecha(request.args.get("fecha_fin"), fecha_default)
        if fecha_fin < fecha_inicio:
            fecha_inicio, fecha_fin = fecha_fin, fecha_inicio
        ventana_inicio, ventana_fin = _lqc_ventana_operativa(fecha_inicio, fecha_fin)
        inicio_sql = ventana_inicio.strftime('%Y-%m-%d %H:%M:%S')
        fin_sql = ventana_fin.strftime('%Y-%m-%d %H:%M:%S')
        turno_filtro = request.args.get("turno", "Todos")
        line_expr = "COALESCE(NULLIF(p.line, ''), 'SIN PLAN')"
        fecha_operativa_expr = """
                    CASE
                        WHEN TIME(b.last_scan) >= '07:30:00' THEN DATE(b.last_scan)
                        ELSE DATE_SUB(DATE(b.last_scan), INTERVAL 1 DAY)
                    END
        """
        turno_expr = """
                    CASE
                        WHEN TIME(b.last_scan) >= '07:30:00' AND TIME(b.last_scan) < '17:30:00' THEN 'DIA'
                        WHEN TIME(b.last_scan) >= '17:30:00' AND TIME(b.last_scan) < '22:00:00' THEN 'TIEMPO EXTRA'
                        ELSE 'NOCHE'
                    END
        """

        conn = get_pooled_connection()
        if conn is None:
            return jsonify({"success": True, "records": []})

        cursor = get_dict_cursor(conn)
        try:
            where_conditions = ["b.last_scan >= %s", "b.last_scan < %s"]
            params = [inicio_sql, fin_sql]

            if lineas:
                placeholders = ','.join(['%s'] * len(lineas))
                where_conditions.append(f"{line_expr} IN ({placeholders})")
                params.extend(lineas)

            if turno_filtro != 'Todos':
                where_conditions.append(f"{turno_expr} = %s")
                params.append(turno_filtro)

            where_clause = " AND ".join(where_conditions)
            query = f"""
                SELECT
                    {line_expr} AS linea,
                    {fecha_operativa_expr} AS fecha,
                    COALESCE(NULLIF(p.part_no, ''), LEFT(b.serial, GREATEST(CHAR_LENGTH(b.serial) - 12, 1))) AS part,
                    COALESCE(NULLIF(p.model_code, ''), '') AS model_code,
                    COALESCE(b.lot_no, '') AS lot_no,
                    b.box_code,
                    b.id AS scan_id,
                    b.serial,
                    b.status AS box_status,
                    b.first_scan,
                    b.last_scan,
                    {turno_expr} AS turno
                FROM box_scans b
                LEFT JOIN plan_main p ON p.lot_no = b.lot_no
                WHERE {where_clause}
                ORDER BY b.last_scan DESC, b.id DESC
            """
            cursor.execute(query, params)
            rows = cursor.fetchall()

            historico_por_serial = {}
            seriales = sorted({
                str(r.get('serial') or '').strip()
                for r in rows
                if str(r.get('serial') or '').strip()
            })
            for i in range(0, len(seriales), 1000):
                serial_chunk = seriales[i:i + 1000]
                placeholders = ','.join(['%s'] * len(serial_chunk))
                cursor.execute(f"""
                    SELECT serial
                    FROM box_scans
                    WHERE serial IN ({placeholders})
                    GROUP BY serial
                    HAVING COUNT(*) > 1
                """, serial_chunk)
                for h in cursor.fetchall():
                    serial = str(h.get('serial') or '').strip()
                    if serial:
                        historico_por_serial[serial] = []

            seriales_repetidos = sorted(historico_por_serial.keys())
            for i in range(0, len(seriales_repetidos), 1000):
                serial_chunk = seriales_repetidos[i:i + 1000]
                placeholders = ','.join(['%s'] * len(serial_chunk))
                cursor.execute(f"""
                    SELECT
                        id,
                        serial,
                        CASE
                            WHEN TIME(last_scan) >= '07:30:00' THEN DATE(last_scan)
                            ELSE DATE_SUB(DATE(last_scan), INTERVAL 1 DAY)
                        END AS fecha_operativa,
                        last_scan
                    FROM box_scans
                    WHERE serial IN ({placeholders})
                    ORDER BY serial, last_scan, id
                """, serial_chunk)
                for h in cursor.fetchall():
                    serial = str(h.get('serial') or '').strip()
                    if not serial:
                        continue
                    historico_por_serial[serial].append({
                        "id": h.get('id'),
                        "fecha": str(h.get('fecha_operativa')) if h.get('fecha_operativa') else '',
                        "last_scan": str(h.get('last_scan')).replace('T', ' ') if h.get('last_scan') else '',
                    })

            records = []
            for r in rows:
                serial = r['serial'] or ''
                historico = historico_por_serial.get(serial, [])
                scan_id = r.get('scan_id')
                otros_escaneos = [
                    h for h in historico
                    if scan_id is None or h.get('id') != scan_id
                ]
                fechas_repetidas = []
                scans_repetidos = []
                for h in otros_escaneos:
                    fecha_hist = h.get('fecha') or ''
                    scan_hist = h.get('last_scan') or ''
                    if fecha_hist and fecha_hist not in fechas_repetidas:
                        fechas_repetidas.append(fecha_hist)
                    if scan_hist and scan_hist not in scans_repetidos:
                        scans_repetidos.append(scan_hist)
                es_duplicado_historico = len(otros_escaneos) > 0
                # El primer escaneo cronologico (id mas chico) es el ORIGINAL.
                # Los siguientes son los duplicados reales.
                es_original = False
                if historico:
                    primer_id = min((h.get('id') for h in historico if h.get('id') is not None), default=None)
                    es_original = (primer_id is not None and scan_id == primer_id)
                status = r.get('box_status') or ''
                if es_duplicado_historico and not es_original:
                    status = 'Duplicado'
                records.append({
                    "linea": r['linea'],
                    "fecha": str(r['fecha']) if r['fecha'] else '',
                    "part": r['part'] or '',
                    "model_code": r.get('model_code') or '',
                    "lot_no": r.get('lot_no') or '',
                    "box_code": r.get('box_code') or '',
                    "serial": serial,
                    "status": status,
                    "duplicado_historico": es_duplicado_historico and not es_original,
                    "es_original": es_original,
                    "total_repeticiones": len(historico),
                    "fechas_repetidas": ', '.join(fechas_repetidas),
                    "escaneos_repetidos": ' | '.join(scans_repetidos[:5]),
                    "first_scan": str(r.get('first_scan')).replace('T', ' ') if r.get('first_scan') else '',
                    "last_scan": str(r['last_scan']).replace('T', ' ') if r['last_scan'] else '',
                    "turno": r['turno'],
                })
            return jsonify({"success": True, "records": records, "total": len(records)})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "records": []}), 500


# ======== ENDPOINTS PARA INVENTARIO IMD TERMINADO ========


@app.route("/api/inventario_general", methods=["GET"])
def api_inventario_general():
    """Endpoint para inventario general IMD desde tabla inv_resumen_modelo"""
    try:
        q = request.args.get("q", "", type=str).strip()
        stock = request.args.get("stock", "", type=str).strip()  # "", ">0", "=0"

        where_conditions = []
        params = []

        if q:
            where_conditions.append("(modelo LIKE %s OR nparte LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])

        if stock == ">0":
            where_conditions.append("stock_total > 0")
        elif stock == "=0":
            where_conditions.append("stock_total = 0")

        where_sql = (
            ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        )

        sql = f"""
            SELECT
              modelo,
              nparte,
              stock_total,
              ubicaciones,
              DATE_FORMAT(ultima_entrada, '%Y-%m-%d %H:%i:%s') AS ultima_entrada,
              DATE_FORMAT(ultima_salida,  '%Y-%m-%d %H:%i:%s') AS ultima_salida,
              tipo_inventario
            FROM inv_resumen_modelo
            {where_sql}
            ORDER BY modelo, nparte
            LIMIT 2000
        """

        results = execute_query(sql, params, fetch="all")

        return jsonify({"status": "success", "items": results or []})

    except Exception as e:
        print(f"Error en api_inventario_general: {e}")
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@app.route("/api/ubicacion", methods=["GET"])
def api_ubicacion():
    """Endpoint para ubicaciones IMD desde tabla ubicacionimdinv"""
    try:
        desde = request.args.get("desde", "", type=str).strip()
        hasta = request.args.get("hasta", "", type=str).strip()
        q = request.args.get("q", "", type=str).strip()
        ubic = request.args.get("ubicacion", "", type=str).strip()
        carro = request.args.get("carro", "", type=str).strip()

        where_conditions = []
        params = []

        # Normalizamos fecha: usamos fecha_subida si existe, si no, parseamos 'fecha'
        fecha_expr = "COALESCE(DATE(fecha), STR_TO_DATE(fecha, '%Y-%m-%d'))"

        if desde:
            where_conditions.append(f"{fecha_expr} >= %s")
            params.append(desde)
        if hasta:
            where_conditions.append(f"{fecha_expr} <= %s")
            params.append(hasta)
        if q:
            where_conditions.append(
                "(modelo LIKE %s OR nparte LIKE %s OR ubicacion LIKE %s OR carro LIKE %s)"
            )
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        if ubic:
            where_conditions.append("ubicacion = %s")
            params.append(ubic)
        if carro:
            where_conditions.append("carro = %s")
            params.append(carro)

        where_sql = (
            ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        )

        sql = f"""
            SELECT
              modelo,
              nparte,
              fecha,
              ubicacion,
              cantidad,
              tipo_inventario,
              comentario,
              carro
            FROM ubicacionimdinv
            {where_sql}
            ORDER BY {fecha_expr} DESC, modelo, nparte
            LIMIT 5000
        """

        results = execute_query(sql, params, fetch="all")

        return jsonify({"status": "success", "items": results or []})

    except Exception as e:
        print(f"Error en api_ubicacion: {e}")
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@app.route("/api/movimientos", methods=["GET"])
def api_movimientos():
    """Endpoint para movimientos IMD desde tabla movimientosimd_smd"""
    try:
        desde = request.args.get("desde", "", type=str).strip()
        hasta = request.args.get("hasta", "", type=str).strip()
        q = request.args.get("q", "", type=str).strip()
        tipo = request.args.get(
            "tipo", "", type=str
        ).strip()  # ENTRADA / SALIDA / AJUSTE / ""

        if not desde:
            # Mantener la consulta inicial acotada al dia actual en horario de Mexico.
            desde = obtener_fecha_hora_mexico().strftime("%Y-%m-%d")

        where_conditions = []
        params = []

        # Filtros de fecha simplificados - usar directamente el campo fecha
        if desde:
            where_conditions.append("fecha >= %s")
            params.append(desde)
        if hasta:
            where_conditions.append("fecha <= %s")
            params.append(hasta + " 23:59:59")
        if tipo:
            where_conditions.append("UPPER(tipo) = %s")
            params.append(tipo.upper())
        if q:
            # El modelo no está en la tabla de movimientos; lo deducimos con un subquery
            where_conditions.append(
                "(nparte LIKE %s OR ubicacion LIKE %s OR carro LIKE %s)"
            )
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

        where_sql = (
            ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""
        )

        sql = f"""
            SELECT
              fecha AS fecha_hora,
              UPPER(tipo) AS tipo,
              nparte,
              -- Deducimos el modelo de la última ubicación conocida para esa parte
              (SELECT u.modelo
                 FROM ubicacionimdinv u
                WHERE u.nparte = m.nparte
                ORDER BY u.fecha DESC
                LIMIT 1) AS modelo,
              cantidad,
              ubicacion,
              tipo_inventario,
              comentario,
              carro
            FROM movimientosimd_smd m
            {where_sql}
            ORDER BY fecha DESC
            LIMIT 5000
        """

        results = execute_query(sql, params, fetch="all")

        return jsonify({"status": "success", "items": results or []})

    except Exception as e:
        print(f"Error en api_movimientos: {e}")
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


# ===============================
# SNAPSHOT INVENTARIO - ENDPOINTS
# ===============================


@app.route("/api/snapshot_inventario/fechas", methods=["GET"])
def api_snapshot_inv_fechas():
    """Listar fechas disponibles de snapshots de inventario con hora"""
    try:
        sql = """
            SELECT fecha_snapshot,
                   DATE_FORMAT(DATE_SUB(MIN(created_at), INTERVAL 6 HOUR), '%H:%i') AS hora_snapshot
            FROM snapshot_inventario_general
            GROUP BY fecha_snapshot
            ORDER BY fecha_snapshot DESC
            LIMIT 365
        """
        rows = execute_query(sql, fetch="all")
        fechas = []
        for r in (rows or []):
            fechas.append({
                "fecha": str(r["fecha_snapshot"]),
                "hora": r.get("hora_snapshot") or ""
            })
        return jsonify({"status": "success", "fechas": fechas})
    except Exception as e:
        print(f"Error en api_snapshot_inv_fechas: {e}")
        return jsonify({"status": "error", "message": str(e), "fechas": []}), 500


@app.route("/api/snapshot_inventario/general", methods=["GET"])
def api_snapshot_inv_general():
    """Consultar snapshot de inventario general por fecha"""
    try:
        fecha = request.args.get("fecha", "", type=str).strip()
        if not fecha:
            return jsonify({"status": "error", "message": "Parámetro 'fecha' requerido"}), 400

        q = request.args.get("q", "", type=str).strip()
        where = ["fecha_snapshot = %s"]
        params = [fecha]

        if q:
            where.append("(modelo LIKE %s OR nparte LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])

        where_sql = ' AND '.join(where)
        sql = (
            "SELECT modelo, nparte, stock_total, ubicaciones,"
            " DATE_FORMAT(ultima_entrada, '%%Y-%%m-%%d %%H:%%i:%%s') AS ultima_entrada,"
            " DATE_FORMAT(ultima_salida,  '%%Y-%%m-%%d %%H:%%i:%%s') AS ultima_salida,"
            " tipo_inventario"
            " FROM snapshot_inventario_general"
            f" WHERE {where_sql}"
            " ORDER BY modelo, nparte"
            " LIMIT 2000"
        )
        results = execute_query(sql, params, fetch="all")
        return jsonify({"status": "success", "fecha": fecha, "items": results or []})

    except Exception as e:
        print(f"Error en api_snapshot_inv_general: {e}")
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@app.route("/api/snapshot_inventario/ubicacion", methods=["GET"])
def api_snapshot_inv_ubicacion():
    """Consultar snapshot de ubicación por fecha"""
    try:
        fecha = request.args.get("fecha", "", type=str).strip()
        if not fecha:
            return jsonify({"status": "error", "message": "Parámetro 'fecha' requerido"}), 400

        q = request.args.get("q", "", type=str).strip()
        where = ["fecha_snapshot = %s"]
        params = [fecha]

        if q:
            where.append("(modelo LIKE %s OR nparte LIKE %s OR ubicacion LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

        sql = f"""
            SELECT modelo, nparte, fecha, ubicacion, cantidad,
                   tipo_inventario, comentario, carro
            FROM snapshot_ubicacion
            WHERE {' AND '.join(where)}
            ORDER BY modelo, nparte
            LIMIT 5000
        """
        results = execute_query(sql, params, fetch="all")
        return jsonify({"status": "success", "fecha": fecha, "items": results or []})

    except Exception as e:
        print(f"Error en api_snapshot_inv_ubicacion: {e}")
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@app.route("/api/snapshot_inventario/trigger", methods=["POST"])
@login_requerido
def api_snapshot_inv_trigger():
    """Trigger manual para tomar snapshot de inventario"""
    try:
        data = request.get_json(silent=True) or {}
        fecha_str = data.get("fecha", "").strip() if isinstance(data.get("fecha"), str) else ""

        fecha_override = None
        if fecha_str:
            try:
                fecha_override = date.fromisoformat(fecha_str)
            except ValueError:
                return jsonify({"status": "error", "message": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400

        result = _snapshot_inv_tomar(fecha_override=fecha_override)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        print(f"Error en api_snapshot_inv_trigger: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ===============================
# 🚀 RUTA SIMPLE PARA ANDROID - mysql-proxy.php
# ===============================


@app.route("/mysql-proxy.php", methods=["POST", "GET", "OPTIONS"])
def mysql_proxy_php():
    """
    Ruta simple para acceder al archivo PHP sin login requerido
    Compatible con tu aplicación Android existente
    """
    try:
        import os

        from flask import send_from_directory

        # Manejar preflight CORS
        if request.method == "OPTIONS":
            response = jsonify({"status": "ok"})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type")
            response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            return response

        # Ruta al archivo PHP
        php_dir = os.path.join(os.path.dirname(__file__), "php")
        php_file = "mysql-proxy.php"

        # Verificar que el archivo existe
        php_path = os.path.join(php_dir, php_file)
        if not os.path.exists(php_path):
            return jsonify(
                {"success": False, "error": "Archivo mysql-proxy.php no encontrado"}
            ), 404

        print(f"📍 Redirigiendo a: {php_path}")

        # Servir el archivo PHP directamente
        return send_from_directory(php_dir, php_file)

    except Exception as e:
        print(f" Error sirviendo mysql-proxy.php: {e}")
        response = jsonify({"success": False, "error": f"Error del servidor: {str(e)}"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500


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


@app.route("/api/plan-run/start", methods=["POST"])
def api_plan_run_start():
    """Iniciar un run de producción desde un renglón del plan.
    Body: { plan_id, linea?, lot_prefix? }
    """
    try:
        data = request.get_json(force=True) or {}
        plan_id = int(data.get("plan_id"))
        linea = (data.get("linea") or "").strip()
        lot_prefix = (data.get("lot_prefix") or "I").strip() or "I"
        usuario = session.get(
            "nombre_completo", session.get("usuario", "Sistema")
        ).strip()

        # Obtener datos del plan
        plan_row = execute_query(
            "SELECT * FROM plan_smd WHERE id=%s", (plan_id,), fetch="one"
        )
        if not plan_row:
            return jsonify({"success": False, "error": "Plan no encontrado"}), 404
        if not linea:
            linea = plan_row.get("linea", "")

        # VALIDACION CRITICA: Verificar que no haya otro run activo en la misma linea
        existing_run = execute_query(
            "SELECT id, lot_no, plan_id FROM plan_smd_runs WHERE linea=%s AND status IN ('RUNNING', 'PAUSED') ORDER BY start_time DESC LIMIT 1",
            (linea,),
            fetch="one",
        )
        if existing_run:
            existing_plan = execute_query(
                "SELECT modelo, nparte FROM plan_smd WHERE id=%s",
                (existing_run["plan_id"],),
                fetch="one",
            )
            modelo_info = (
                f" ({existing_plan['modelo']} - {existing_plan['nparte']})"
                if existing_plan
                else ""
            )
            return jsonify(
                {
                    "success": False,
                    "error": f"Ya hay un run activo en la lonea {linea}: {existing_run['lot_no']}{modelo_info}. Debe finalizar el run actual antes de iniciar uno nuevo.",
                }
            ), 409  # 409 Conflict

        # Verificar que este plan especofico no tenga ya un run activo
        plan_run_active = execute_query(
            "SELECT id, lot_no, status FROM plan_smd_runs WHERE plan_id=%s AND status IN ('RUNNING', 'PAUSED') ORDER BY start_time DESC LIMIT 1",
            (plan_id,),
            fetch="one",
        )
        if plan_run_active:
            return jsonify(
                {
                    "success": False,
                    "error": f"Este plan ya tiene un run activo: {plan_run_active['lot_no']} (Status: {plan_run_active['status']}). Debe finalizar el run actual antes de iniciar uno nuevo.",
                }
            ), 409

        # Verificar que el plan no esto ya finalizado
        trazabilidad_actual = execute_query(
            "SELECT estado FROM trazabilidad WHERE lot_no=%s ORDER BY updated_at DESC LIMIT 1",
            (plan_row.get("lote"),),
            fetch="one",
        )
        if trazabilidad_actual and trazabilidad_actual.get("estado") == "FINALIZADO":
            return jsonify(
                {
                    "success": False,
                    "error": f"Este plan ya esto finalizado (LOT: {plan_row.get('lote')}). No se puede reiniciar un plan finalizado.",
                }
            ), 409

        # Usar LOT NO ya definido en el plan; no generar uno nuevo
        lot_no = plan_row.get("lote")
        if not lot_no:
            return jsonify(
                {"success": False, "error": "El plan no tiene LOT asignado"}
            ), 400
        uph = plan_row.get("uph") or 0
        ct = plan_row.get("ct") or 0
        qty_plan = plan_row.get("qty") or 0

        # Preparar baseline AOI al iniciar RUN
        aoi_model = (plan_row.get("nparte") or plan_row.get("modelo") or "").upper()

        def _map_line_no(s: str):
            try:
                ss = (s or "").upper().strip()
                if ss.startswith("SMT "):
                    ss = ss[4:].strip()
                if ss and ss[0].isalpha():
                    return max(1, min(26, ord(ss[0]) - ord("A") + 1))
                if ss.isdigit():
                    return int(ss)
            except Exception:
                pass
            return None

        aoi_line_no = _map_line_no(linea)
        from app.api.control_resultados.aoi import classify_shift, compute_shift_date
        from .auth_system import AuthSystem as _AS

        now_mx = _AS.get_mexico_time()
        current_shift = classify_shift(now_mx)
        current_shift_date = compute_shift_date(now_mx, current_shift).strftime(
            "%Y-%m-%d"
        )
        aoi_baseline = None
        if aoi_model and aoi_line_no:
            baseline_sql = """
                SELECT COALESCE(SUM(piece_w),0) AS total
                FROM aoi_file_log
                WHERE shift_date=%s AND shift=%s AND model=%s AND line_no=%s
            """
            try:
                rowb = (
                    execute_query(
                        baseline_sql,
                        (current_shift_date, current_shift, aoi_model, aoi_line_no),
                        fetch="one",
                    )
                    or {}
                )
                aoi_baseline = int(rowb.get("total") or 0)
            except Exception as e2:
                print(f"?? Error obteniendo baseline AOI: {e2}")
                aoi_baseline = 0

        insert = """
            INSERT INTO plan_smd_runs (plan_id, linea, lot_no, uph, ct, qty_plan, status, created_by,
                                       aoi_model, aoi_line_no, aoi_baseline, aoi_baseline_shift_date, aoi_baseline_shift)
            VALUES (%s,%s,%s,%s,%s,%s,'RUNNING',%s, %s,%s,%s,%s,%s)
        """
        execute_query(
            insert,
            (
                plan_id,
                linea,
                lot_no,
                uph,
                ct,
                qty_plan,
                usuario,
                aoi_model,
                aoi_line_no,
                aoi_baseline,
                current_shift_date,
                current_shift,
            ),
        )

        # Actualizar trazabilidad: INICIADO
        try:
            # Intentar INSERT primero
            try:
                execute_query(
                    """
                    INSERT INTO trazabilidad (lot_no, estado, updated_at)
                    VALUES (%s, 'INICIADO', NOW())
                """,
                    (lot_no,),
                )
            except Exception:
                # Si falla (probablemente duplicado), actualizar el mos reciente
                execute_query(
                    """
                    UPDATE trazabilidad SET estado='INICIADO', updated_at=NOW()
                    WHERE lot_no=%s AND updated_at = (
                        SELECT MAX(updated_at) FROM (SELECT updated_at FROM trazabilidad WHERE lot_no=%s) AS t
                    )
                """,
                    (lot_no, lot_no),
                )
        except Exception as e2:
            print(f"⚠️ Error actualizando trazabilidad (INICIADO): {e2}")

        run = execute_query(
            "SELECT * FROM plan_smd_runs WHERE lot_no=%s", (lot_no,), fetch="one"
        )
        return jsonify({"success": True, "run": run})
    except Exception as e:
        print(f" Error en api_plan_run_start: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/plan-run/end", methods=["POST"])
def api_plan_run_end():
    try:
        data = request.get_json(force=True) or {}
        run_id = int(data.get("run_id"))
        plan_id_req = data.get("plan_id")
        # Validar run existente y opcionalmente que corresponda al plan indicado
        run = execute_query(
            "SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch="one"
        )
        if not run:
            return jsonify({"success": False, "error": "Run no encontrado"}), 404
        if plan_id_req is not None and str(run.get("plan_id")) != str(plan_id_req):
            return jsonify(
                {"success": False, "error": "El run no corresponde al plan indicado"}
            ), 400
        # Cerrar el run si esto RUNNING
        update = "UPDATE plan_smd_runs SET status='ENDED', end_time=NOW() WHERE id=%s AND status='RUNNING'"
        execute_query(update, (run_id,))
        run = execute_query(
            "SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch="one"
        )
        # Calcular y guardar producido final basado en AOI (si hay baseline)
        try:
            if run:
                aoi_model = (run.get("aoi_model") or "").upper()
                aoi_line_no = run.get("aoi_line_no")
                bl = int(run.get("aoi_baseline") or 0)
                bl_date = run.get("aoi_baseline_shift_date")
                bl_shift = (
                    (run.get("aoi_baseline_shift") or "").strip()
                    if run.get("aoi_baseline_shift")
                    else ""
                )
                if aoi_model and aoi_line_no and bl_date and bl_shift:
                    shift_order = {"DIA": 1, "TIEMPO_EXTRA": 2, "NOCHE": 3}
                    agg_sql = """
                        SELECT shift_date, shift, SUM(piece_w) AS total
                        FROM aoi_file_log
                        WHERE model=%s AND line_no=%s AND shift_date >= %s
                        GROUP BY shift_date, shift
                        ORDER BY shift_date ASC
                    """
                    agg_rows = (
                        execute_query(
                            agg_sql, (aoi_model, int(aoi_line_no), bl_date), fetch="all"
                        )
                        or []
                    )
                    total = 0
                    for ar in agg_rows:
                        sd = ar.get("shift_date")
                        sh = (ar.get("shift") or "").strip()
                        t = int(ar.get("total") or 0)
                        if not sd or not sh:
                            continue
                        if str(sd) == str(bl_date) and sh == bl_shift:
                            total += max(0, t - bl)
                        else:
                            if str(sd) == str(bl_date) and shift_order.get(
                                sh, 0
                            ) < shift_order.get(bl_shift, 0):
                                continue
                            total += t
                    try:
                        execute_query(
                            "UPDATE plan_smd_runs SET aoi_produced_final=%s WHERE id=%s",
                            (int(total), run_id),
                        )
                        run = execute_query(
                            "SELECT * FROM plan_smd_runs WHERE id=%s",
                            (run_id,),
                            fetch="one",
                        )
                    except Exception as e3:
                        print(f"?? Error guardando aoi_produced_final: {e3}")
        except Exception as e2:
            print(f"?? Error calculando producido final AOI: {e2}")
        try:
            if run and run.get("lot_no"):
                # Intentar INSERT primero
                try:
                    execute_query(
                        """
                        INSERT INTO trazabilidad (lot_no, estado, updated_at)
                        VALUES (%s, 'FINALIZADO', NOW())
                    """,
                        (run["lot_no"],),
                    )
                except Exception:
                    # Si falla (probablemente duplicado), actualizar el mos reciente
                    execute_query(
                        """
                        UPDATE trazabilidad SET estado='FINALIZADO', updated_at=NOW()
                        WHERE lot_no=%s AND updated_at = (
                            SELECT MAX(updated_at) FROM (SELECT updated_at FROM trazabilidad WHERE lot_no=%s) AS t
                        )
                    """,
                        (run["lot_no"], run["lot_no"]),
                    )
        except Exception as e2:
            print(f"⚠️ Error actualizando trazabilidad (FINALIZADO): {e2}")
        return jsonify({"success": True, "run": run})
    except Exception as e:
        print(f" Error en api_plan_run_end: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/plan-run/pause", methods=["POST"])
def api_plan_run_pause():
    try:
        data = request.get_json(force=True) or {}
        run_id = int(data.get("run_id"))
        update = (
            "UPDATE plan_smd_runs SET status='PAUSED' WHERE id=%s AND status='RUNNING'"
        )
        execute_query(update, (run_id,))
        run = execute_query(
            "SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch="one"
        )
        if run and run.get("lot_no"):
            try:
                # Intentar INSERT primero
                try:
                    execute_query(
                        """
                        INSERT INTO trazabilidad (lot_no, estado, updated_at)
                        VALUES (%s, 'PAUSA', NOW())
                    """,
                        (run["lot_no"],),
                    )
                except Exception:
                    # Si falla (probablemente duplicado), actualizar el mos reciente
                    execute_query(
                        """
                        UPDATE trazabilidad SET estado='PAUSA', updated_at=NOW()
                        WHERE lot_no=%s AND updated_at = (
                            SELECT MAX(updated_at) FROM (SELECT updated_at FROM trazabilidad WHERE lot_no=%s) AS t
                        )
                    """,
                        (run["lot_no"], run["lot_no"]),
                    )
            except Exception as e2:
                print(f"?? Error actualizando trazabilidad (PAUSA): {e2}")
        return jsonify({"success": True, "run": run})
    except Exception as e:
        print(f"? Error en api_plan_run_pause: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/plan-run/resume", methods=["POST"])
def api_plan_run_resume():
    try:
        data = request.get_json(force=True) or {}
        run_id = int(data.get("run_id"))
        run = execute_query(
            "SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch="one"
        )
        if not run:
            return jsonify({"success": False, "error": "Run no encontrado"}), 404
        linea = run.get("linea")
        exists = execute_query(
            "SELECT id FROM plan_smd_runs WHERE linea=%s AND status='RUNNING' AND id<>%s LIMIT 1",
            (linea, run_id),
            fetch="one",
        )
        if exists:
            return jsonify(
                {"success": False, "error": f"Ya existe un plan en progreso en {linea}"}
            ), 400
        execute_query(
            "UPDATE plan_smd_runs SET status='RUNNING' WHERE id=%s AND status='PAUSED'",
            (run_id,),
        )
        if run.get("lot_no"):
            try:
                execute_query(
                    "UPDATE trazabilidad SET estado='INICIADO', updated_at=NOW() WHERE lot_no=%s",
                    (run["lot_no"],),
                )
            except Exception as e2:
                print(f"?? Error actualizando trazabilidad (INICIADO): {e2}")
        run = execute_query(
            "SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch="one"
        )
        return jsonify({"success": True, "run": run})
    except Exception as e:
        print(f"? Error en api_plan_run_resume: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/plan-run/status", methods=["GET"])
def api_plan_run_status():
    """Estado del run por linea o run_id.
    Si está RUNNING, calcula progreso estimado usando UPH y tiempo transcurrido.
    """
    try:
        run_id = request.args.get("run_id")
        linea = request.args.get("linea")

        if run_id:
            row = execute_query(
                "SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch="one"
            )
        elif linea and linea.strip():
            row = execute_query(
                "SELECT * FROM plan_smd_runs WHERE linea=%s AND status='RUNNING' ORDER BY start_time DESC LIMIT 1",
                (linea.strip(),),
                fetch="one",
            )
        else:
            error_msg = "Parometros insuficientes. Se requiere run_id o linea."
            if linea == "":
                error_msg = "Parometro linea esto vacoo"
            return jsonify({"success": False, "error": error_msg}), 400

        if not row:
            return jsonify({"success": True, "running": False})

        # Calcular progreso estimado
        from datetime import datetime

        start = row.get("start_time")
        end = row.get("end_time")
        uph = float(row.get("uph") or 0)
        qty_plan = int(row.get("qty_plan") or 0)
        producido = 0
        if start and not end and uph > 0:
            # elapsed hours
            now = datetime.utcnow()
            # MySQL datetime naive; asumir UTC-agnóstico
            elapsed_hours = max(0.0, (now - start).total_seconds() / 3600.0)
            producido = int(min(qty_plan, uph * elapsed_hours))
        return jsonify(
            {
                "success": True,
                "running": row["status"] == "RUNNING",
                "run": row,
                "producido_est": producido,
            }
        )
    except Exception as e:
        print(f" Error en api_plan_run_status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def crear_tabla_trazabilidad():
    """Crear tabla de trazabilidad (LOTE por WO/LINEA con estados)."""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS trazabilidad (
            id INT AUTO_INCREMENT PRIMARY KEY,
            linea VARCHAR(32) NOT NULL,
            lot_no VARCHAR(32) NOT NULL,
            plan_id INT NULL,
            codigo_wo VARCHAR(32) NULL,
            estado ENUM('PLANEADO','INICIADO','PAUSA','FINALIZADO') DEFAULT 'PLANEADO',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            usuario VARCHAR(64) DEFAULT 'sistema',
            INDEX idx_linea (linea),
            INDEX idx_lot (lot_no),
            INDEX idx_estado (estado)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        execute_query(query)
        print(" Tabla trazabilidad creada/verificada")
    except Exception as e:
        print(f" Error creando tabla trazabilidad: {e}")


# crear_tabla_trazabilidad movido a app/startup_init.py


###############################################
# Metal Mask: poginas y API (integracion)
###############################################


def init_metal_mask_tables():
    """Crea/ajusta tablas usadas por Metal Mask si no existen."""
    try:
        # Tabla principal de masks con nombres de columnas en inglos (usadas por el frontend)
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

        # Asegurar valores del ENUM en caso de historiales previos (migracion suave)
        try:
            execute_query(
                "ALTER TABLE masks MODIFY COLUMN disuse ENUM('Use','Disuse','Uso','Desuso','Scrap') DEFAULT 'Uso'"
            )
            execute_query("UPDATE masks SET disuse='Uso' WHERE disuse='Use'")
            execute_query("UPDATE masks SET disuse='Desuso' WHERE disuse='Disuse'")
            execute_query(
                "ALTER TABLE masks MODIFY COLUMN disuse ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso'"
            )
        except Exception as _:
            # Si falla (p.ej. por no existir la tabla/columna aon), continuar
            pass

        # Tabla de cajas de almacenamiento
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


# init_metal_mask_tables movido a app/startup_init.py


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


# ====== HISTORIAL ICT (FRONT FULL DEFECTS 2) ======
def _append_indexable_text_filter(sql, params, column_name, raw_value, exact_min_length=12):
    """Agregar filtro exacto o por prefijo para evitar LIKE con comodin inicial."""
    value = (raw_value or "").strip()
    if not value:
        return sql

    if len(value) >= exact_min_length:
        sql += f" AND {column_name}=%s"
        params.append(value)
    else:
        sql += f" AND {column_name} LIKE %s"
        params.append(f"{value}%")
    return sql


def _ict_format_row(row):
    """Convertir campos fecha/hora a cadenas serializables."""
    if not row:
        return {}

    formatted = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            formatted[key] = value.isoformat(sep=" ")
        elif isinstance(value, date):
            formatted[key] = value.isoformat()
        elif isinstance(value, dt_time):
            formatted[key] = value.strftime("%H:%M:%S")
        elif isinstance(value, timedelta):
            formatted[key] = str(value)
        else:
            formatted[key] = value
    return formatted


def _ict_find_history_record(barcode, ts=None):
    """Buscar el registro resumen que apunta al archivo LGD local."""
    sql = (
        "SELECT barcode, ts, fuente_archivo, linea, ict "
        "FROM history_ict WHERE barcode=%s"
    )
    params = [barcode]
    if ts:
        sql += " AND ts=%s"
        params.append(ts)
    sql += " ORDER BY ts DESC LIMIT 1"
    return execute_query(sql, tuple(params), fetch="one")


def _ict_load_local_parameters(barcode, ts=None):
    history_row = _ict_find_history_record(barcode, ts)
    if not history_row:
        raise IctLgdNotFoundError("No se encontro el registro ICT solicitado.")

    source_file = (history_row.get("fuente_archivo") or "").strip()
    if not source_file:
        raise IctLgdPathError("El registro no tiene fuente_archivo.")

    lgd_path = resolve_lgd_path(source_file)
    cached_rows = get_lgd_parameters_for_barcode(str(lgd_path), barcode)
    # Copia local porque vamos a setear linea/ict/fuente_archivo. El resultado
    # de get_lgd_parameters_for_barcode comparte memoria con el cache global.
    rows = [dict(row) for row in cached_rows]
    for row in rows:
        row.setdefault("linea", history_row.get("linea"))
        row.setdefault("ict", history_row.get("ict"))
        row.setdefault("fuente_archivo", source_file)
    return rows, source_file


def _vision_format_value(value):
    """Convertir valores de history_vision a cadenas serializables."""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dt_time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    if isinstance(value, str) and re.fullmatch(r"\d{2}:\d{2}:\d{2}\.\d+", value):
        return value.split(".", 1)[0]
    return value


def _vision_parse_datetime(value):
    """Normalizar distintos formatos de fecha/hora a datetime."""
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        try:
            return datetime.fromisoformat(raw_value)
        except ValueError:
            for fmt in (
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S.%f",
                "%Y/%m/%d %H:%M:%S",
            ):
                try:
                    return datetime.strptime(raw_value, fmt)
                except ValueError:
                    continue
    return None


def _vision_parse_date(value):
    """Normalizar valores de fecha a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        try:
            return date.fromisoformat(raw_value)
        except ValueError:
            return None
    return None


def _vision_parse_time(value):
    """Normalizar valores de hora a time."""
    if isinstance(value, dt_time):
        return value
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return dt_time(hour=hours % 24, minute=minutes, second=seconds)
    if isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        try:
            return dt_time.fromisoformat(raw_value)
        except ValueError:
            for fmt in ("%H:%M:%S.%f", "%H:%M:%S"):
                try:
                    return datetime.strptime(raw_value, fmt).time()
                except ValueError:
                    continue
    return None


def _vision_reference_datetime(record):
    """Obtener la fecha/hora mas confiable para resolver la imagen."""
    parsed_value = _vision_parse_datetime(record.get("log_datetime"))
    if parsed_value:
        return parsed_value

    log_date = _vision_parse_date(record.get("log_date"))
    log_time = _vision_parse_time(record.get("log_time"))
    if log_date and log_time:
        return datetime.combine(log_date, log_time)

    for key in ("captured_at_utc", "created_at"):
        parsed_value = _vision_parse_datetime(record.get(key))
        if parsed_value:
            return parsed_value

    return None


def _vision_extract_host_from_source_file(source_file):
    """Extraer el host UNC desde source_file."""
    raw_source = str(source_file or "").strip()
    match = re.match(r"^\\\\([^\\]+)\\", raw_source)
    return match.group(1).strip() if match else ""


def _vision_unique_values(values):
    """Eliminar duplicados preservando el orden original."""
    unique_values = []
    seen_values = set()
    for value in values:
        normalized = str(value or "").strip()
        if not normalized:
            continue
        value_key = normalized.lower()
        if value_key in seen_values:
            continue
        seen_values.add(value_key)
        unique_values.append(normalized)
    return unique_values


def _vision_candidate_share_roots(record):
    """Construir raices UNC candidatas para buscar imagenes."""
    machine_name = str(record.get("machine_name") or "").strip()
    candidate_hosts = _vision_unique_values(
        [
            _vision_extract_host_from_source_file(record.get("source_file")),
            record.get("machine_ip"),
        ]
    )

    roots = []
    seen_roots = set()
    for host in candidate_hosts:
        root_candidates = []
        if machine_name:
            root_candidates.append(Path(rf"\\{host}\Result {machine_name}"))
        root_candidates.append(Path(rf"\\{host}\Result"))

        for candidate_root in root_candidates:
            root_key = os.path.normcase(os.path.normpath(str(candidate_root)))
            if root_key in seen_roots:
                continue
            seen_roots.add(root_key)
            roots.append(candidate_root)

    return roots


def _vision_candidate_hour_directories(root_path, part_code, reference_dt):
    """Construir directorios candidatos por hora, incluyendo borde de hora."""
    if not part_code or not reference_dt:
        return []

    base_hour = reference_dt.replace(minute=0, second=0, microsecond=0)
    candidate_hours = [base_hour]

    previous_delta = (reference_dt - base_hour).total_seconds()
    if previous_delta <= 1.0:
        candidate_hours.append(base_hour - timedelta(hours=1))

    next_hour = base_hour + timedelta(hours=1)
    next_delta = (next_hour - reference_dt).total_seconds()
    if next_delta <= 1.0:
        candidate_hours.append(next_hour)

    ebr_prefix = str(part_code or "").strip().upper()[:11]
    candidate_part_directories = []
    seen_part_directories = set()

    def append_part_directory(path_obj):
        path_key = os.path.normcase(os.path.normpath(str(path_obj)))
        if path_key in seen_part_directories:
            return
        seen_part_directories.add(path_key)
        candidate_part_directories.append(path_obj)

    append_part_directory(root_path / part_code)

    if ebr_prefix and ebr_prefix != str(part_code or "").strip().upper():
        append_part_directory(root_path / ebr_prefix)

    try:
        if root_path.is_dir() and ebr_prefix:
            matching_directories = sorted(
                [
                    child
                    for child in root_path.iterdir()
                    if child.is_dir()
                    and child.name.strip().upper()[:11] == ebr_prefix
                ],
                key=lambda path: path.name.lower(),
            )
            for matching_directory in matching_directories:
                append_part_directory(matching_directory)
    except OSError:
        pass

    directories = []
    seen_directories = set()
    for part_directory in candidate_part_directories:
        for candidate_hour in candidate_hours:
            base_dir = (
                part_directory
                / "Image(Process)"
                / candidate_hour.strftime("%Y")
                / candidate_hour.strftime("%m")
                / candidate_hour.strftime("%d")
                / candidate_hour.strftime("%H")
            )
            dir_key = os.path.normcase(os.path.normpath(str(base_dir)))
            if dir_key in seen_directories:
                continue
            seen_directories.add(dir_key)
            directories.append(base_dir)

    return directories


def _vision_share_name(root_path):
    """Obtener el nombre visible del share UNC."""
    normalized = os.path.normpath(str(root_path)).rstrip("\\/")
    share_name = os.path.basename(normalized)
    if share_name:
        return share_name
    return normalized.split("\\")[-1] if normalized else ""


def _vision_is_safe_path(target_path, allowed_roots):
    """Validar que la ruta final quede contenida dentro de una raiz candidata."""
    normalized_target = os.path.normcase(os.path.normpath(str(target_path)))
    for allowed_root in allowed_roots:
        normalized_root = os.path.normcase(os.path.normpath(str(allowed_root)))
        try:
            if os.path.commonpath([normalized_target, normalized_root]) == normalized_root:
                return True
        except ValueError:
            continue
    return False


def _get_history_vision_record(record_id):
    """Obtener un registro completo de history_vision por id."""
    sql = (
        "SELECT id, source_uid, machine_name, machine_ip, result, log_timestamp, "
        "log_datetime, log_date, log_time, serial_qr, barcode, qr_payload, work_area, "
        "part_code, source_file, captured_at_utc, created_at "
        "FROM history_vision WHERE id=%s LIMIT 1"
    )
    return execute_query(sql, (record_id,), fetch="one")


def _resolve_history_vision_image(record):
    """Resolver la imagen mas cercana a un registro de history_vision."""
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    expected_result = str(record.get("result") or "").strip().upper()
    part_code = str(record.get("part_code") or "").strip()
    part_code_prefix = part_code.upper()[:11]
    reference_dt = _vision_reference_datetime(record)
    share_roots = _vision_candidate_share_roots(record)

    result_payload = {
        "record_id": record.get("id"),
        "resolved_path": "",
        "share_name": "",
        "side_folder": "",
        "delta_seconds": None,
        "searched_paths": [],
        "reference_datetime": _vision_format_value(reference_dt) if reference_dt else "",
        "share_roots": [str(root) for root in share_roots],
    }

    if not part_code:
        result_payload["error"] = "El registro no tiene numero de parte."
        return result_payload

    if expected_result not in {"OK", "NG"}:
        result_payload["error"] = "El resultado del registro no es valido."
        return result_payload

    if not reference_dt:
        result_payload["error"] = "No se pudo determinar la fecha/hora del registro."
        return result_payload

    if not share_roots:
        result_payload["error"] = "No se encontraron rutas compartidas candidatas."
        return result_payload

    filename_part_prefix = part_code_prefix or part_code.upper()
    filename_pattern = re.compile(
        rf"^{re.escape(filename_part_prefix)}(?:[^_]*)_(?P<side>[^_]+)_(?P<stamp>\d{{8}}_\d{{9}})_(?P<result>OK|NG)\.(?P<ext>jpg|jpeg|png|bmp)$",
        re.IGNORECASE,
    )

    best_candidate = None
    searched_paths = []
    seen_search_paths = set()

    for share_root in share_roots:
        for hour_dir in _vision_candidate_hour_directories(
            share_root, part_code, reference_dt
        ):
            hour_dir_str = str(hour_dir)
            hour_dir_key = os.path.normcase(os.path.normpath(hour_dir_str))
            if hour_dir_key not in seen_search_paths:
                seen_search_paths.add(hour_dir_key)
                searched_paths.append(hour_dir_str)

            try:
                if not hour_dir.is_dir():
                    continue
                side_directories = sorted(
                    [child for child in hour_dir.iterdir() if child.is_dir()],
                    key=lambda path: path.name.lower(),
                )
            except OSError:
                continue

            for side_dir in side_directories:
                result_dir = side_dir / expected_result
                result_dir_str = str(result_dir)
                result_dir_key = os.path.normcase(os.path.normpath(result_dir_str))
                if result_dir_key not in seen_search_paths:
                    seen_search_paths.add(result_dir_key)
                    searched_paths.append(result_dir_str)

                try:
                    if not result_dir.is_dir():
                        continue
                    image_candidates = sorted(
                        [child for child in result_dir.iterdir() if child.is_file()],
                        key=lambda path: path.name.lower(),
                    )
                except OSError:
                    continue

                for image_path in image_candidates:
                    if image_path.suffix.lower() not in image_extensions:
                        continue

                    match = filename_pattern.match(image_path.name)
                    if not match or match.group("result").upper() != expected_result:
                        continue

                    try:
                        file_dt = datetime.strptime(
                            match.group("stamp"), "%Y%m%d_%H%M%S%f"
                        )
                    except ValueError:
                        continue

                    delta_seconds = abs((file_dt - reference_dt).total_seconds())
                    candidate = {
                        "path": image_path,
                        "share_name": _vision_share_name(share_root),
                        "side_folder": side_dir.name,
                        "delta_seconds": delta_seconds,
                    }

                    if best_candidate is None or delta_seconds < best_candidate["delta_seconds"]:
                        best_candidate = candidate

    result_payload["searched_paths"] = searched_paths

    if best_candidate and best_candidate["delta_seconds"] <= 1.0:
        result_payload.update(
            {
                "resolved_path": str(best_candidate["path"]),
                "share_name": best_candidate["share_name"],
                "side_folder": best_candidate["side_folder"],
                "delta_seconds": round(best_candidate["delta_seconds"], 3),
            }
        )
        return result_payload

    result_payload["error"] = "No se encontro una imagen dentro del umbral de 1 segundo."
    return result_payload


def _build_history_vision_query():
    """Construir query y parámetros para consultar history_vision."""
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    linea = request.args.get("linea", "").strip()
    resultado = request.args.get("resultado", "").strip()
    numero_parte = request.args.get("numero_parte", "").strip()
    qr = request.args.get("qr", "").strip()
    barcode = request.args.get("barcode", "").strip()

    sql = (
        "SELECT "
        "id, "
        "machine_name AS linea, "
        "log_date AS fecha, "
        "log_time AS hora, "
        "part_code AS numero_parte, "
        "qr_payload AS qr, "
        "barcode, "
        "result AS resultado "
        "FROM history_vision WHERE 1=1"
    )
    params = []

    if fecha_desde:
        sql += " AND log_date >= %s"
        params.append(fecha_desde)
    if fecha_hasta:
        sql += " AND log_date <= %s"
        params.append(fecha_hasta)
    if linea:
        sql += " AND machine_name LIKE %s"
        params.append(f"%{linea}%")
    if resultado:
        sql += " AND result=%s"
        params.append(resultado)
    if numero_parte:
        sql += " AND part_code LIKE %s"
        params.append(f"%{numero_parte}%")
    if qr:
        sql += " AND qr_payload LIKE %s"
        params.append(f"%{qr}%")
    if barcode:
        sql += " AND barcode LIKE %s"
        params.append(f"%{barcode}%")

    sql += " ORDER BY COALESCE(log_datetime, created_at) DESC, id DESC"

    return sql, tuple(params) if params else None


def _build_history_vision_pass_fail_summary_query():
    """Construir query y parámetros para el resumen Pass/Fail de history_vision por línea y número de parte."""
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    numero_parte = request.args.get("numero_parte", "").strip()

    sql = (
        "SELECT "
        "COALESCE(NULLIF(TRIM(machine_name), ''), 'SIN LINEA') AS linea, "
        "COALESCE(NULLIF(TRIM(part_code), ''), 'SIN NUMERO DE PARTE') AS numero_parte, "
        "COUNT(*) AS total, "
        "SUM(CASE WHEN UPPER(COALESCE(result, '')) = 'OK' THEN 1 ELSE 0 END) AS ok_count, "
        "SUM(CASE WHEN UPPER(COALESCE(result, '')) = 'NG' THEN 1 ELSE 0 END) AS ng_count "
        "FROM history_vision WHERE 1=1"
    )
    params = []

    if fecha_desde:
        sql += " AND log_date >= %s"
        params.append(fecha_desde)
    if fecha_hasta:
        sql += " AND log_date <= %s"
        params.append(fecha_hasta)
    if numero_parte:
        sql += " AND part_code LIKE %s"
        params.append(f"%{numero_parte}%")

    sql += (
        " GROUP BY COALESCE(NULLIF(TRIM(machine_name), ''), 'SIN LINEA'),"
        " COALESCE(NULLIF(TRIM(part_code), ''), 'SIN NUMERO DE PARTE')"
        " ORDER BY linea ASC, total DESC, numero_parte ASC"
    )

    return sql, tuple(params) if params else None


VISION_PASS_FAIL_EXCEL_IMAGE_WIDTH = 430
VISION_PASS_FAIL_EXCEL_IMAGE_HEIGHT = 28


def _measure_vision_pass_fail_excel_text(draw, text, font):
    if hasattr(draw, "textbbox"):
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return right - left, bottom - top

    if hasattr(draw, "textsize"):
        return draw.textsize(text, font=font)

    if hasattr(font, "getbbox"):
        left, top, right, bottom = font.getbbox(text)
        return right - left, bottom - top

    if hasattr(font, "getsize"):
        return font.getsize(text)

    return (max(len(text), 1) * 8, 12)


def _load_vision_pass_fail_excel_font(size=12, bold=False):
    from PIL import ImageFont

    windows_font_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    preferred_font_names = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "Calibri Bold.ttf" if bold else "Calibri.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
    ]

    for font_name in preferred_font_names:
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue

    font_candidates = [
        windows_font_dir / ("arialbd.ttf" if bold else "arial.ttf"),
        windows_font_dir / ("calibrib.ttf" if bold else "calibri.ttf"),
        windows_font_dir / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]

    for font_path in font_candidates:
        try:
            if font_path.is_file():
                return ImageFont.truetype(str(font_path), size=size)
        except OSError:
            continue

    return ImageFont.load_default()


def _build_vision_pass_fail_excel_bar_image(porcentaje_ok, porcentaje_ng):
    from io import BytesIO

    from PIL import Image, ImageDraw

    pass_rate = max(0.0, min(100.0, float(porcentaje_ok or 0)))
    fail_rate = max(0.0, min(100.0, float(porcentaje_ng or 0)))

    canvas_width = 430
    canvas_height = 28
    bar_width = 350
    bar_height = 20
    label_gap = 8
    label_width = canvas_width - bar_width - label_gap
    radius = bar_height // 2

    ok_width = int(round((pass_rate / 100.0) * bar_width))
    ok_width = max(0, min(bar_width, ok_width))
    ng_width = max(0, bar_width - ok_width)

    image = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    bar_x = 0
    bar_y = (canvas_height - bar_height) // 2

    # Base dark bar
    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
        radius=radius,
        fill="#1A2740",
    )

    # Draw segments inside a rounded mask for clean edges
    segments = Image.new("RGBA", (bar_width, bar_height), (0, 0, 0, 0))
    segments_draw = ImageDraw.Draw(segments)
    if ok_width > 0:
        segments_draw.rectangle((0, 0, ok_width, bar_height), fill="#4CAF63")
    if ng_width > 0:
        segments_draw.rectangle(
            (bar_width - ng_width, 0, bar_width, bar_height), fill="#E45454"
        )

    mask = Image.new("L", (bar_width, bar_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, bar_width, bar_height), radius=radius, fill=255)
    image.paste(segments, (bar_x, bar_y), mask)

    pass_label = f"{pass_rate:.2f}%"
    fail_label = f"{fail_rate:.2f}%"

    pass_font = _load_vision_pass_fail_excel_font(size=12, bold=True)
    fail_font = _load_vision_pass_fail_excel_font(size=12, bold=True)

    pass_text_width, pass_text_height = _measure_vision_pass_fail_excel_text(
        draw, pass_label, pass_font
    )
    pass_center_x = bar_x + max(ok_width / 2, min(bar_width / 2, 70))
    pass_text_x = int(
        max(
            bar_x + 10,
            min(pass_center_x - pass_text_width / 2, bar_width - pass_text_width - 10),
        )
    )
    pass_text_y = int(bar_y + (bar_height - pass_text_height) / 2 - 1)
    draw.text(
        (pass_text_x, pass_text_y),
        pass_label,
        font=pass_font,
        fill="#FFFFFF",
    )

    _, fail_text_height = _measure_vision_pass_fail_excel_text(
        draw, fail_label, fail_font
    )
    fail_text_x = bar_width + label_gap
    fail_text_y = int(bar_y + (bar_height - fail_text_height) / 2 - 1)
    draw.text(
        (fail_text_x, fail_text_y),
        fail_label,
        font=fail_font,
        fill="#1F1F1F",
    )

    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output


def _vision_pass_fail_text_width(text, char_width=10, spacing=3):
    if not text:
        return 0

    width = 0
    for idx, char in enumerate(text):
        width += _get_vision_pass_fail_char_width(char, char_width)
        if idx < len(text) - 1:
            width += spacing
    return width


def _set_vision_pass_fail_pixel(pixels, width, x, y, color):
    if x < 0 or y < 0:
        return

    idx = ((y * width) + x) * 4
    if idx < 0 or idx + 3 >= len(pixels):
        return

    pixels[idx] = color[0]
    pixels[idx + 1] = color[1]
    pixels[idx + 2] = color[2]
    pixels[idx + 3] = color[3]


def _fill_vision_pass_fail_rounded_rect(
    pixels, canvas_width, x, y, width, height, radius, color
):
    radius = max(0, min(radius, width // 2, height // 2))
    radius_sq = radius * radius

    for local_y in range(height):
        for local_x in range(width):
            if radius == 0:
                inside = True
            elif radius <= local_x < width - radius or radius <= local_y < height - radius:
                inside = True
            else:
                corner_x = radius if local_x < radius else width - radius - 1
                corner_y = radius if local_y < radius else height - radius - 1
                delta_x = local_x - corner_x
                delta_y = local_y - corner_y
                inside = (delta_x * delta_x) + (delta_y * delta_y) <= radius_sq

            if inside:
                _set_vision_pass_fail_pixel(
                    pixels, canvas_width, x + local_x, y + local_y, color
                )


def _draw_vision_pass_fail_disc(pixels, canvas_width, center_x, center_y, radius, color):
    radius_sq = radius * radius
    for local_y in range(-radius, radius + 1):
        for local_x in range(-radius, radius + 1):
            if (local_x * local_x) + (local_y * local_y) <= radius_sq:
                _set_vision_pass_fail_pixel(
                    pixels,
                    canvas_width,
                    center_x + local_x,
                    center_y + local_y,
                    color,
                )


def _draw_vision_pass_fail_line(
    pixels, canvas_width, x1, y1, x2, y2, thickness, color
):
    dx = x2 - x1
    dy = y2 - y1
    steps = max(abs(dx), abs(dy), 1)
    radius = max(1, thickness // 2)

    for step in range(steps + 1):
        point_x = int(round(x1 + (dx * step / steps)))
        point_y = int(round(y1 + (dy * step / steps)))
        _draw_vision_pass_fail_disc(
            pixels, canvas_width, point_x, point_y, radius, color
        )


def _draw_vision_pass_fail_segment(
    pixels,
    canvas_width,
    origin_x,
    origin_y,
    segment_name,
    color,
    char_width=10,
    char_height=14,
    thickness=2,
):
    mid_y = origin_y + (char_height // 2)
    bottom_y = origin_y + char_height - thickness
    right_x = origin_x + char_width - thickness
    horizontal_width = char_width - (thickness * 2)
    vertical_height = (char_height // 2) - thickness - 1
    radius = max(1, thickness // 2)

    if segment_name == "top":
        _fill_vision_pass_fail_rounded_rect(
            pixels,
            canvas_width,
            origin_x + thickness,
            origin_y,
            horizontal_width,
            thickness,
            radius,
            color,
        )
    elif segment_name == "middle":
        _fill_vision_pass_fail_rounded_rect(
            pixels,
            canvas_width,
            origin_x + thickness,
            mid_y - (thickness // 2),
            horizontal_width,
            thickness,
            radius,
            color,
        )
    elif segment_name == "bottom":
        _fill_vision_pass_fail_rounded_rect(
            pixels,
            canvas_width,
            origin_x + thickness,
            bottom_y,
            horizontal_width,
            thickness,
            radius,
            color,
        )
    elif segment_name == "upper_left":
        _fill_vision_pass_fail_rounded_rect(
            pixels,
            canvas_width,
            origin_x,
            origin_y + thickness,
            thickness,
            vertical_height,
            radius,
            color,
        )
    elif segment_name == "upper_right":
        _fill_vision_pass_fail_rounded_rect(
            pixels,
            canvas_width,
            right_x,
            origin_y + thickness,
            thickness,
            vertical_height,
            radius,
            color,
        )
    elif segment_name == "lower_left":
        _fill_vision_pass_fail_rounded_rect(
            pixels,
            canvas_width,
            origin_x,
            mid_y + 1,
            thickness,
            vertical_height,
            radius,
            color,
        )
    elif segment_name == "lower_right":
        _fill_vision_pass_fail_rounded_rect(
            pixels,
            canvas_width,
            right_x,
            mid_y + 1,
            thickness,
            vertical_height,
            radius,
            color,
        )


def _get_vision_pass_fail_segments(char):
    segment_map = {
        "0": (
            "top",
            "upper_left",
            "upper_right",
            "lower_left",
            "lower_right",
            "bottom",
        ),
        "1": ("upper_right", "lower_right"),
        "2": ("top", "upper_right", "middle", "lower_left", "bottom"),
        "3": ("top", "upper_right", "middle", "lower_right", "bottom"),
        "4": ("upper_left", "upper_right", "middle", "lower_right"),
        "5": ("top", "upper_left", "middle", "lower_right", "bottom"),
        "6": (
            "top",
            "upper_left",
            "middle",
            "lower_left",
            "lower_right",
            "bottom",
        ),
        "7": ("top", "upper_right", "lower_right"),
        "8": (
            "top",
            "upper_left",
            "upper_right",
            "middle",
            "lower_left",
            "lower_right",
            "bottom",
        ),
        "9": (
            "top",
            "upper_left",
            "upper_right",
            "middle",
            "lower_right",
            "bottom",
        ),
    }
    return segment_map.get(char, ())


def _get_vision_pass_fail_char_width(char, default_width=10):
    if char == "1":
        return default_width - 2
    if char == ".":
        return 4
    if char == "%":
        return default_width + 2
    if char == " ":
        return max(3, default_width // 2)
    return default_width


def _draw_vision_pass_fail_vector_char(
    pixels,
    canvas_width,
    x,
    y,
    char,
    color,
    char_width=10,
    char_height=14,
    thickness=2,
):
    actual_width = _get_vision_pass_fail_char_width(char, char_width)

    if char.isdigit():
        for segment_name in _get_vision_pass_fail_segments(char):
            _draw_vision_pass_fail_segment(
                pixels,
                canvas_width,
                x,
                y,
                segment_name,
                color,
                char_width=actual_width,
                char_height=char_height,
                thickness=thickness,
            )
        return actual_width

    if char == ".":
        radius = max(1, thickness)
        _draw_vision_pass_fail_disc(
            pixels,
            canvas_width,
            x + radius,
            y + char_height - radius - 1,
            radius,
            color,
        )
        return actual_width

    if char == "%":
        disc_radius = max(1, thickness)
        _draw_vision_pass_fail_disc(
            pixels, canvas_width, x + 2, y + 3, disc_radius, color
        )
        _draw_vision_pass_fail_disc(
            pixels,
            canvas_width,
            x + actual_width - 3,
            y + char_height - 3,
            disc_radius,
            color,
        )
        _draw_vision_pass_fail_line(
            pixels,
            canvas_width,
            x + actual_width - 3,
            y + 1,
            x + 2,
            y + char_height - 2,
            thickness,
            color,
        )
        return actual_width

    return actual_width


def _draw_vision_pass_fail_vector_text(
    pixels,
    canvas_width,
    x,
    y,
    text,
    color,
    char_width=10,
    char_height=14,
    thickness=2,
    spacing=3,
):
    cursor_x = x
    for idx, char in enumerate(text):
        cursor_x += _draw_vision_pass_fail_vector_char(
            pixels,
            canvas_width,
            cursor_x,
            y,
            char,
            color,
            char_width=char_width,
            char_height=char_height,
            thickness=thickness,
        )
        if idx < len(text) - 1:
            cursor_x += spacing


def _build_vision_pass_fail_excel_bar_png_bytes(porcentaje_ok, porcentaje_ng):
    pass_rate = max(0.0, min(100.0, float(porcentaje_ok or 0)))
    fail_rate = max(0.0, min(100.0, float(porcentaje_ng or 0)))

    canvas_width = VISION_PASS_FAIL_EXCEL_IMAGE_WIDTH
    canvas_height = VISION_PASS_FAIL_EXCEL_IMAGE_HEIGHT
    bar_width = 350
    bar_height = 20
    label_gap = 8
    radius = bar_height // 2
    bar_x = 0
    bar_y = (canvas_height - bar_height) // 2

    ok_width = int(round((pass_rate / 100.0) * bar_width))
    ok_width = max(0, min(bar_width, ok_width))
    ng_width = max(0, bar_width - ok_width)

    pixels = bytearray(canvas_width * canvas_height * 4)

    _fill_vision_pass_fail_rounded_rect(
        pixels, canvas_width, bar_x, bar_y, bar_width, bar_height, radius, (26, 39, 64, 255)
    )

    for local_y in range(bar_height):
        for local_x in range(bar_width):
            if radius <= local_x < bar_width - radius or radius <= local_y < bar_height - radius:
                inside = True
            else:
                corner_x = radius if local_x < radius else bar_width - radius - 1
                corner_y = radius if local_y < radius else bar_height - radius - 1
                delta_x = local_x - corner_x
                delta_y = local_y - corner_y
                inside = (delta_x * delta_x) + (delta_y * delta_y) <= radius * radius

            if not inside:
                continue

            if ok_width > 0 and local_x < ok_width:
                color = (76, 175, 99, 255)
            elif ng_width > 0 and local_x >= bar_width - ng_width:
                color = (228, 84, 84, 255)
            else:
                color = (26, 39, 64, 255)

            _set_vision_pass_fail_pixel(
                pixels, canvas_width, bar_x + local_x, bar_y + local_y, color
            )

    pass_label = f"{pass_rate:.2f}%"
    fail_label = f"{fail_rate:.2f}%"

    char_width = 10
    char_height = 14
    thickness = 2
    spacing = 2
    pass_text_width = _vision_pass_fail_text_width(
        pass_label, char_width=char_width, spacing=spacing
    )
    pass_center_x = bar_x + max(ok_width / 2, min(bar_width / 2, 70))
    pass_text_x = int(
        max(
            bar_x + 10,
            min(pass_center_x - pass_text_width / 2, bar_width - pass_text_width - 10),
        )
    )
    pass_text_y = bar_y + max(0, (bar_height - char_height) // 2)
    _draw_vision_pass_fail_vector_text(
        pixels,
        canvas_width,
        pass_text_x,
        pass_text_y,
        pass_label,
        (255, 255, 255, 255),
        char_width=char_width,
        char_height=char_height,
        thickness=thickness,
        spacing=spacing,
    )

    fail_text_x = bar_width + label_gap
    fail_text_y = bar_y + max(0, (bar_height - char_height) // 2)
    _draw_vision_pass_fail_vector_text(
        pixels,
        canvas_width,
        fail_text_x,
        fail_text_y,
        fail_label,
        (31, 31, 31, 255),
        char_width=char_width,
        char_height=char_height,
        thickness=thickness,
        spacing=spacing,
    )

    raw_rows = bytearray()
    stride = canvas_width * 4
    for row_idx in range(canvas_height):
        raw_rows.append(0)
        start = row_idx * stride
        raw_rows.extend(pixels[start : start + stride])

    compressed = zlib.compress(bytes(raw_rows), 9)

    def png_chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    png_bytes = bytearray()
    png_bytes.extend(b"\x89PNG\r\n\x1a\n")
    png_bytes.extend(
        png_chunk(
            b"IHDR",
            struct.pack(
                ">IIBBBBB",
                canvas_width,
                canvas_height,
                8,
                6,
                0,
                0,
                0,
            ),
        )
    )
    png_bytes.extend(png_chunk(b"IDAT", compressed))
    png_bytes.extend(png_chunk(b"IEND", b""))
    return bytes(png_bytes)


def _create_vision_pass_fail_excel_image(porcentaje_ok, porcentaje_ng):
    from openpyxl.drawing.image import Image as XLImage

    try:
        image_buffer = _build_vision_pass_fail_excel_bar_image(
            porcentaje_ok, porcentaje_ng
        )
        excel_image = XLImage(image_buffer)
    except Exception:
        png_bytes = _build_vision_pass_fail_excel_bar_png_bytes(
            porcentaje_ok, porcentaje_ng
        )

        class RawPngExcelImage(XLImage):
            def __init__(self, raw_bytes, width, height):
                self.ref = io.BytesIO(raw_bytes)
                self._raw_bytes = raw_bytes
                self.width = width
                self.height = height
                self.format = "png"

            def _data(self):
                return self._raw_bytes

        excel_image = RawPngExcelImage(
            png_bytes,
            VISION_PASS_FAIL_EXCEL_IMAGE_WIDTH,
            VISION_PASS_FAIL_EXCEL_IMAGE_HEIGHT,
        )

    excel_image.width = VISION_PASS_FAIL_EXCEL_IMAGE_WIDTH
    excel_image.height = VISION_PASS_FAIL_EXCEL_IMAGE_HEIGHT
    return excel_image


def _send_excel_download(output, filename):
    send_kwargs = {
        "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "as_attachment": True,
    }

    try:
        return send_file(output, download_name=filename, **send_kwargs)
    except TypeError:
        output.seek(0)
        return send_file(output, attachment_filename=filename, **send_kwargs)


@app.route("/historial-vision")
@app.route("/historial-vision-ajax")
@login_requerido
def historial_vision():
    """Servir la página de Historial Vision."""
    try:
        return render_template("Control de resultados/history_vision.html")
    except Exception as e:
        print(f"Error al cargar Historial Vision: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/historial-vision-pass-fail")
@app.route("/historial-vision-pass-fail-ajax")
@login_requerido
def historial_vision_pass_fail():
    """Servir la página de Historial Vision % Pass/Fail."""
    try:
        return render_template("Control de resultados/history_vision_pass_fail.html")
    except Exception as e:
        print(f"Error al cargar Historial Vision % Pass/Fail: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/api/vision/data")
@login_requerido
def vision_data_api():
    """Obtener registros recientes del historial de Vision con filtros opcionales."""
    try:
        sql, params = _build_history_vision_query()
        rows = execute_query(sql, params, fetch="all") or []

        result = []
        for row in rows:
            result.append(
                {
                    "id": row.get("id"),
                    "linea": _vision_format_value(row.get("linea", "")) or "",
                    "fecha": _vision_format_value(row.get("fecha", "")) or "",
                    "hora": _vision_format_value(row.get("hora", "")) or "",
                    "numero_parte": _vision_format_value(
                        row.get("numero_parte", "")
                    )
                    or "",
                    "qr": _vision_format_value(row.get("qr", "")) or "",
                    "barcode": _vision_format_value(row.get("barcode", "")) or "",
                    "resultado": _vision_format_value(row.get("resultado", ""))
                    or "",
                }
            )

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/vision/pass-fail-summary")
@login_requerido
def vision_pass_fail_summary_api():
    """Obtener resumen agrupado por línea y número de parte para history_vision."""
    try:
        sql, params = _build_history_vision_pass_fail_summary_query()
        rows = execute_query(sql, params, fetch="all") or []

        result = []
        for row in rows:
            total = int(row.get("total") or 0)
            ok_count = int(row.get("ok_count") or 0)
            ng_count = int(row.get("ng_count") or 0)
            porcentaje_ok = round((ok_count / total) * 100, 2) if total else 0
            porcentaje_ng = round((ng_count / total) * 100, 2) if total else 0

            result.append(
                {
                    "linea": _vision_format_value(row.get("linea", "")) or "",
                    "numero_parte": _vision_format_value(
                        row.get("numero_parte", "")
                    )
                    or "",
                    "total": total,
                    "ok_count": ok_count,
                    "ng_count": ng_count,
                    "porcentaje_ok": porcentaje_ok,
                    "porcentaje_ng": porcentaje_ng,
                }
            )

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/vision/pass-fail-summary/export")
@login_requerido
def export_vision_pass_fail_summary_excel():
    """Exportar resumen Pass/Fail de Vision a un archivo de Excel."""
    try:
        sql, params = _build_history_vision_pass_fail_summary_query()
        rows = execute_query(sql, params, fetch="all") or []

        from io import BytesIO

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        wb = Workbook()
        ws = wb.active
        ws.title = "Vision Pass Fail"

        header_fill = PatternFill(
            start_color="3f6b6e", end_color="3f6b6e", fill_type="solid"
        )
        cell_fill = PatternFill(
            start_color="a1a09c", end_color="a1a09c", fill_type="solid"
        )
        header_font = Font(bold=True, color="FFFFFF", size=10)
        border = Border(
            left=Side(style="thin", color="000000"),
            right=Side(style="thin", color="000000"),
            top=Side(style="thin", color="000000"),
            bottom=Side(style="thin", color="000000"),
        )

        headers = [
            "Linea",
            "Numero de parte",
            "Total",
            "OK",
            "NG",
            "% Pass",
            "% Fail",
            "PORCENTAJE",
        ]

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border

        for row_idx, row in enumerate(rows, start=2):
            total = int(row.get("total") or 0)
            ok_count = int(row.get("ok_count") or 0)
            ng_count = int(row.get("ng_count") or 0)
            porcentaje_ok = round((ok_count / total) * 100, 2) if total else 0
            porcentaje_ng = round((ng_count / total) * 100, 2) if total else 0

            values = [
                _vision_format_value(row.get("linea", "")) or "",
                _vision_format_value(row.get("numero_parte", "")) or "",
                total,
                ok_count,
                ng_count,
                porcentaje_ok,
                porcentaje_ng,
            ]

            for col_num, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_num, value=value)
                cell.fill = cell_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border

            image_cell = ws.cell(row=row_idx, column=8, value="")
            image_cell.fill = cell_fill
            image_cell.alignment = Alignment(horizontal="center", vertical="center")
            image_cell.border = border

            excel_image = _create_vision_pass_fail_excel_image(
                porcentaje_ok, porcentaje_ng
            )
            ws.add_image(excel_image, f"H{row_idx}")
            ws.row_dimensions[row_idx].height = 24

        column_widths = [20, 28, 14, 12, 12, 14, 14, 58]
        for col_num, width in enumerate(column_widths, start=1):
            column_letter = ws.cell(row=1, column=col_num).column_letter
            ws.column_dimensions[column_letter].width = width

        ws.freeze_panes = "A2"

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = (
            f"historial_vision_pass_fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        return _send_excel_download(output, filename)
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/vision/image-info")
@login_requerido
def vision_image_info_api():
    """Resolver metadata de la imagen asociada a un registro de history_vision."""
    record_id = request.args.get("id", "").strip()
    if not re.fullmatch(r"\d+", record_id):
        return jsonify({"error": "ID de registro invalido."}), 400

    try:
        record = _get_history_vision_record(int(record_id))
        if not record:
            return jsonify({"error": "Registro de vision no encontrado."}), 404

        resolution = _resolve_history_vision_image(record)
        response_payload = {
            "record_id": record.get("id"),
            "linea": _vision_format_value(record.get("machine_name", "")) or "",
            "numero_parte": _vision_format_value(record.get("part_code", "")) or "",
            "resultado": _vision_format_value(record.get("result", "")) or "",
            "fecha_hora": resolution.get("reference_datetime") or "",
            "resolved_path": resolution.get("resolved_path", ""),
            "share_name": resolution.get("share_name", ""),
            "side_folder": resolution.get("side_folder", ""),
            "delta_seconds": resolution.get("delta_seconds"),
            "searched_paths": resolution.get("searched_paths", []),
            "source_file": _vision_format_value(record.get("source_file", "")) or "",
            "machine_ip": _vision_format_value(record.get("machine_ip", "")) or "",
            "image_url": "",
        }

        if resolution.get("resolved_path"):
            response_payload["image_url"] = url_for(
                "vision_image_file_api", id=record.get("id")
            )
            return jsonify(response_payload)

        response_payload["error"] = resolution.get(
            "error", "No se encontro imagen para el registro."
        )
        return jsonify(response_payload), 404
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/vision/image-file")
@login_requerido
def vision_image_file_api():
    """Servir la imagen resuelta de un registro de history_vision."""
    record_id = request.args.get("id", "").strip()
    if not re.fullmatch(r"\d+", record_id):
        return jsonify({"error": "ID de registro invalido."}), 400

    try:
        record = _get_history_vision_record(int(record_id))
        if not record:
            return jsonify({"error": "Registro de vision no encontrado."}), 404

        resolution = _resolve_history_vision_image(record)
        resolved_path = resolution.get("resolved_path", "")
        share_roots = [Path(path) for path in resolution.get("share_roots", [])]

        if not resolved_path:
            return (
                jsonify(
                    {
                        "error": resolution.get(
                            "error", "No se encontro imagen para el registro."
                        ),
                        "searched_paths": resolution.get("searched_paths", []),
                    }
                ),
                404,
            )

        resolved_file = Path(resolved_path)
        if not _vision_is_safe_path(resolved_file, share_roots):
            return jsonify({"error": "La ruta resuelta no es segura."}), 403

        if not resolved_file.is_file():
            return (
                jsonify(
                    {
                        "error": "La imagen resuelta ya no esta disponible.",
                        "resolved_path": str(resolved_file),
                    }
                ),
                404,
            )

        mimetype_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".bmp": "image/bmp",
        }
        mimetype = mimetype_map.get(
            resolved_file.suffix.lower(), "application/octet-stream"
        )

        return send_file(
            str(resolved_file),
            mimetype=mimetype,
            as_attachment=False,
            download_name=resolved_file.name,
            conditional=True,
        )
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/vision/export")
@login_requerido
def export_vision_excel():
    """Exportar el historial Vision filtrado a un archivo de Excel."""
    try:
        sql, params = _build_history_vision_query()
        rows = execute_query(sql, params, fetch="all") or []

        from io import BytesIO

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        wb = Workbook()
        ws = wb.active
        ws.title = "Historial Vision"

        header_fill = PatternFill(
            start_color="3f6b6e", end_color="3f6b6e", fill_type="solid"
        )
        cell_fill = PatternFill(
            start_color="a1a09c", end_color="a1a09c", fill_type="solid"
        )
        header_font = Font(bold=True, color="FFFFFF", size=10)
        border = Border(
            left=Side(style="thin", color="000000"),
            right=Side(style="thin", color="000000"),
            top=Side(style="thin", color="000000"),
            bottom=Side(style="thin", color="000000"),
        )

        headers = [
            "Linea",
            "Fecha",
            "Hora",
            "Numero de parte",
            "QR",
            "Barcode",
            "Resultado",
        ]

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border

        for row_idx, row in enumerate(rows, start=2):
            values = [
                _vision_format_value(row.get("linea", "")) or "",
                _vision_format_value(row.get("fecha", "")) or "",
                _vision_format_value(row.get("hora", "")) or "",
                _vision_format_value(row.get("numero_parte", "")) or "",
                _vision_format_value(row.get("qr", "")) or "",
                _vision_format_value(row.get("barcode", "")) or "",
                _vision_format_value(row.get("resultado", "")) or "",
            ]

            for col_num, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_num, value=value)
                cell.fill = cell_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border

        column_widths = [22, 14, 14, 28, 36, 24, 14]
        for col_num, width in enumerate(column_widths, start=1):
            column_letter = ws.cell(row=1, column=col_num).column_letter
            ws.column_dimensions[column_letter].width = width

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = (
            f"historial_vision_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/historial-ict")
@app.route("/ict/front-full-defects2")
@login_requerido
def ict_front_full_defects2():
    """Vista principal del historial ICT con defectos detallados."""
    try:
        return render_template("Control de resultados/history_ict.html")
    except Exception as e:
        print(f"Error al cargar History ICT: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@app.route("/api/ict/data")
@login_requerido
def ict_data_api():
    """Obtener registros del historial ICT con filtros y paginacion.

    Soporta `fecha` (igualdad, retro-compatible) o `fecha_desde`/`fecha_hasta`
    (rango). Si se envian ambos, prevalece el rango.

    Paginacion: `page` (1-based) y `per_page` (default 200, max 1000).
    Cuando se envia `page`, la respuesta es un objeto con metadata; si no se
    envia, se devuelve el array plano (retro-compatible) con LIMIT 500.
    """
    try:
        fecha = request.args.get("fecha", "").strip()
        fecha_desde = request.args.get("fecha_desde", "").strip()
        fecha_hasta = request.args.get("fecha_hasta", "").strip()
        no_parte = request.args.get("no_parte", "").strip()
        linea = request.args.get("linea", "").strip()
        ict_filter = request.args.get("ict", "").strip()
        resultado = request.args.get("resultado", "").strip()
        barcode_like = request.args.get("barcode_like", "").strip()
        page_raw = request.args.get("page", "").strip()
        per_page_raw = request.args.get("per_page", "").strip()
        paginated = bool(page_raw)
        if barcode_like and len(barcode_like) < 6:
            if paginated:
                return jsonify({"rows": [], "total": 0, "page": 1, "per_page": 0, "total_pages": 0})
            return jsonify([])

        where_sql = "WHERE 1=1"
        params = []

        def _add(clause, *vals):
            nonlocal where_sql
            where_sql += " " + clause
            params.extend(vals)

        if fecha_desde or fecha_hasta:
            if fecha_desde:
                _add("AND fecha>=%s", fecha_desde)
            if fecha_hasta:
                _add("AND fecha<=%s", fecha_hasta)
        elif fecha:
            _add("AND fecha=%s", fecha)
        if no_parte:
            _add("AND no_parte LIKE %s", f"{no_parte}%")
        if linea:
            _add("AND linea=%s", linea)
        if ict_filter:
            try:
                _add("AND ict=%s", int(ict_filter))
            except ValueError:
                return jsonify({"error": "ict debe ser numerico"}), 400
        if resultado:
            _add("AND resultado=%s", resultado)
        if barcode_like:
            # Reaplicar la misma logica de _append_indexable_text_filter pero
            # sobre el WHERE acumulado (no sobre el SELECT completo).
            value = barcode_like.strip()
            if len(value) >= 12:
                where_sql += " AND barcode=%s"
                params.append(value)
            else:
                where_sql += " AND barcode LIKE %s"
                params.append(f"{value}%")

        select_cols = (
            "SELECT fecha, TIME(ts) AS hora, linea, ict, resultado, no_parte, barcode, "
            "ts, fuente_archivo, defect_code, defect_valor "
            "FROM history_ict "
        )

        if paginated:
            try:
                page = max(1, int(page_raw))
            except ValueError:
                page = 1
            try:
                per_page = int(per_page_raw) if per_page_raw else 200
            except ValueError:
                per_page = 200
            per_page = max(1, min(per_page, 1000))

            count_sql = "SELECT COUNT(*) AS n FROM history_ict " + where_sql
            count_row = execute_query(count_sql, tuple(params), fetch="one") or {}
            total = int(count_row.get("n", 0))

            offset = (page - 1) * per_page
            data_sql = select_cols + where_sql + " ORDER BY ts DESC LIMIT %s OFFSET %s"
            rows = execute_query(data_sql, tuple(params) + (per_page, offset), fetch="all") or []

            total_pages = (total + per_page - 1) // per_page if per_page else 0
            return jsonify({
                "rows": [_ict_format_row(row) for row in rows],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            })

        # Modo legacy sin paginacion (retro-compatible)
        data_sql = select_cols + where_sql + " ORDER BY ts DESC LIMIT 500"
        rows = execute_query(data_sql, tuple(params), fetch="all") or []
        return jsonify([_ict_format_row(row) for row in rows])
    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/ict/defects")
@login_requerido
def ict_defects_api():
    """Obtener defectos asociados a un barcode espec��fico."""
    barcode = request.args.get("barcode", "").strip()
    ts = request.args.get("ts", "").strip()
    if not barcode:
        return jsonify([])

    try:
        rows, _ = _ict_load_local_parameters(barcode, ts)
        return jsonify([_ict_format_row(row) for row in rows])
    except IctLgdNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except IctLgdPathError as e:
        return jsonify({"error": str(e)}), 400
    except IctLgdError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/ict/export")
@login_requerido
def export_ict_excel():
    """Exportar el historial ICT filtrado a un archivo de Excel."""
    try:
        fecha = request.args.get("fecha", "").strip()
        fecha_desde = request.args.get("fecha_desde", "").strip()
        fecha_hasta = request.args.get("fecha_hasta", "").strip()
        no_parte = request.args.get("no_parte", "").strip()
        linea = request.args.get("linea", "").strip()
        ict_filter = request.args.get("ict", "").strip()
        resultado = request.args.get("resultado", "").strip()
        barcode_like = request.args.get("barcode_like", "").strip()
        if barcode_like and len(barcode_like) < 6:
            return jsonify({"error": "Barcode demasiado corto para exportar"}), 400

        sql = (
            "SELECT fecha, TIME(ts) AS hora, linea, ict, resultado, no_parte, barcode, "
            "fuente_archivo, defect_code, defect_valor "
            "FROM history_ict WHERE 1=1"
        )
        params = []

        if fecha_desde or fecha_hasta:
            if fecha_desde:
                sql += " AND fecha>=%s"
                params.append(fecha_desde)
            if fecha_hasta:
                sql += " AND fecha<=%s"
                params.append(fecha_hasta)
        elif fecha:
            sql += " AND fecha=%s"
            params.append(fecha)
        if no_parte:
            sql += " AND no_parte LIKE %s"
            params.append(f"{no_parte}%")
        if linea:
            sql += " AND linea=%s"
            params.append(linea)
        if ict_filter:
            try:
                sql += " AND ict=%s"
                params.append(int(ict_filter))
            except ValueError:
                return jsonify({"error": "ict debe ser numerico"}), 400
        if resultado:
            sql += " AND resultado=%s"
            params.append(resultado)
        if barcode_like:
            sql = _append_indexable_text_filter(sql, params, "barcode", barcode_like)

        sql += " ORDER BY ts DESC LIMIT 500"
        rows = execute_query(sql, tuple(params), fetch="all") or []

        from io import BytesIO

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        wb = Workbook()
        ws = wb.active
        ws.title = "Historial ICT"

        header_fill = PatternFill(
            start_color="3f6b6e", end_color="3f6b6e", fill_type="solid"
        )
        cell_fill = PatternFill(
            start_color="a1a09c", end_color="a1a09c", fill_type="solid"
        )
        header_font = Font(bold=True, color="FFFFFF", size=10)
        border = Border(
            left=Side(style="thin", color="000000"),
            right=Side(style="thin", color="000000"),
            top=Side(style="thin", color="000000"),
            bottom=Side(style="thin", color="000000"),
        )

        headers = [
            "Fecha",
            "Hora",
            "L��nea",
            "ICT",
            "Resultado",
            "No Parte",
            "Barcode",
            "Fuente",
            "Defect Code",
            "Defect Valor",
        ]

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border

        for row_idx, row in enumerate(rows, start=2):
            formatted = _ict_format_row(row)
            values = [
                formatted.get("fecha", ""),
                formatted.get("hora", ""),
                formatted.get("linea", ""),
                formatted.get("ict", ""),
                formatted.get("resultado", ""),
                formatted.get("no_parte", ""),
                formatted.get("barcode", ""),
                formatted.get("fuente_archivo", ""),
                formatted.get("defect_code", ""),
                formatted.get("defect_valor", ""),
            ]

            for col_num, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_num, value=value)
                cell.fill = cell_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border

        for col in range(1, len(headers) + 1):
            column_letter = ws.cell(row=1, column=col).column_letter
            ws.column_dimensions[column_letter].width = 16

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"historial_ict_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    except IctLgdNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except IctLgdPathError as e:
        return jsonify({"error": str(e)}), 400
    except IctLgdError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/ict/export-defects")
@login_requerido
def export_ict_defects_excel():
    """Exportar detalles de defectos ICT a un archivo de Excel."""
    barcode = request.args.get("barcode", "").strip()
    ts = request.args.get("ts", "").strip()
    resultado_filter = request.args.get("resultado", "").strip()

    if not barcode:
        return jsonify({"error": "Barcode requerido"}), 400

    try:
        rows, _ = _ict_load_local_parameters(barcode, ts)
        if resultado_filter:
            rows = [row for row in rows if row.get("resultado_local") == resultado_filter]

        from io import BytesIO

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        wb = Workbook()
        ws = wb.active
        ws.title = f"Parametros {barcode[:20]}"

        header_fill = PatternFill(
            start_color="3f6b6e", end_color="3f6b6e", fill_type="solid"
        )
        cell_fill = PatternFill(
            start_color="a1a09c", end_color="a1a09c", fill_type="solid"
        )
        header_font = Font(bold=True, color="FFFFFF", size=10)
        border = Border(
            left=Side(style="thin", color="000000"),
            right=Side(style="thin", color="000000"),
            top=Side(style="thin", color="000000"),
            bottom=Side(style="thin", color="000000"),
        )

        headers = [
            "Fecha",
            "Hora",
            "L��nea",
            "ICT",
            "Barcode",
            "Componente",
            "Pinref",
            "ACT",
            "Unit",
            "STD",
            "Unit",
            "MEAS",
            "M",
            "R",
            "HLIM",
            "LLIM",
            "H.P",
            "L.P",
            "WS",
            "DS",
            "RC",
            "P",
            "J",
            "Resultado",
            "Tipo Defecto",
        ]

        for col_num, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border

        for row_idx, row in enumerate(rows, start=2):
            formatted = _ict_format_row(row)
            hlim = formatted.get("hlim_pct", "")
            llim = formatted.get("llim_pct", "")

            row_values = [
                formatted.get("fecha", ""),
                formatted.get("hora", ""),
                formatted.get("linea", ""),
                formatted.get("ict", ""),
                formatted.get("barcode", ""),
                formatted.get("componente", ""),
                formatted.get("pinref", ""),
                formatted.get("act_value", ""),
                formatted.get("act_unit", ""),
                formatted.get("std_value", ""),
                formatted.get("std_unit", ""),
                formatted.get("meas_value", ""),
                formatted.get("m_value", ""),
                formatted.get("r_value", ""),
                f"{hlim}%" if hlim else "",
                f"{llim}%" if llim else "",
                formatted.get("hp_value", ""),
                formatted.get("lp_value", ""),
                formatted.get("ws_value", ""),
                formatted.get("ds_value", ""),
                formatted.get("rc_value", ""),
                formatted.get("p_flag", ""),
                formatted.get("j_flag", ""),
                formatted.get("resultado_local", ""),
                formatted.get("defecto_tipo", ""),
            ]

            for col_num, value in enumerate(row_values, start=1):
                cell = ws.cell(row=row_idx, column=col_num, value=value)
                cell.fill = cell_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border

        for col in range(1, len(headers) + 1):
            column_letter = ws.cell(row=1, column=col).column_letter
            ws.column_dimensions[column_letter].width = 12

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = (
            f"parametros_{barcode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    except IctLgdNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except IctLgdPathError as e:
        return jsonify({"error": str(e)}), 400
    except IctLgdError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/ict/export-compare", methods=["POST"])
@login_requerido
def export_ict_compare_excel():
    """Exportar comparacion de parametros ICT entre varias ejecuciones (auditoria).

    Body JSON: { runs: [{barcode, ts, fecha, hora, linea, resultado}, ...], only_diffs: bool }
    """
    try:
        payload = request.get_json(silent=True) or {}
        runs_input = payload.get("runs") or []
        only_diffs = bool(payload.get("only_diffs", True))

        if len(runs_input) < 2:
            return jsonify({"error": "Se requieren al menos 2 ejecuciones"}), 400

        runs = []
        for idx, rec in enumerate(runs_input, start=1):
            barcode = (rec.get("barcode") or "").strip()
            ts = (rec.get("ts") or "").strip()
            if not barcode:
                continue
            rows, _ = _ict_load_local_parameters(barcode, ts)
            runs.append({
                "run_index": idx,
                "barcode": barcode,
                "ts": ts,
                "fecha": rec.get("fecha") or "",
                "hora": rec.get("hora") or "",
                "linea": rec.get("linea") or "",
                "resultado": rec.get("resultado") or "",
                "defects": [_ict_format_row(row) for row in rows],
            })

        if len(runs) < 2:
            return jsonify({"error": "No se pudieron cargar parametros de las ejecuciones"}), 400

        compare_fields = [
            ("act_value", "ACT", ""),
            ("act_unit", "UNIT", ""),
            ("std_value", "STD", ""),
            ("std_unit", "UNIT", ""),
            ("m_value", "M", ""),
            ("r_value", "R", ""),
            ("hlim_pct", "HLIM %", "%"),
            ("llim_pct", "LLIM %", "%"),
            ("hp_value", "HP", ""),
            ("lp_value", "LP", ""),
            ("ws_value", "WS", ""),
            ("ds_value", "DS", ""),
            ("rc_value", "RC", ""),
            ("p_flag", "P", ""),
            ("j_flag", "J", ""),
        ]

        groups = {}
        for run in runs:
            for d in run["defects"]:
                key = (d.get("componente") or "", d.get("pinref") or "")
                if key not in groups:
                    groups[key] = {"componente": key[0], "pinref": key[1], "by_run": {}}
                groups[key]["by_run"][run["run_index"]] = d

        def _norm(v):
            if v is None:
                return ""
            return str(v).strip()

        from io import BytesIO

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        wb = Workbook()
        ws = wb.active
        ws.title = "Comparacion ICT"

        header_fill = PatternFill(start_color="3f6b6e", end_color="3f6b6e", fill_type="solid")
        cell_fill = PatternFill(start_color="a1a09c", end_color="a1a09c", fill_type="solid")
        diff_fill = PatternFill(start_color="f4b3ad", end_color="f4b3ad", fill_type="solid")
        missing_fill = PatternFill(start_color="d9d9d9", end_color="d9d9d9", fill_type="solid")
        info_fill = PatternFill(start_color="dde6e8", end_color="dde6e8", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        title_font = Font(bold=True, color="000000", size=12)
        info_font = Font(bold=True, color="000000", size=9)
        diff_font = Font(bold=True, color="8b0000", size=10)
        thin = Side(style="thin", color="000000")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        ws.cell(row=1, column=1, value="COMPARACION DE PARAMETROS ICT - AUDITORIA").font = title_font
        ws.cell(row=2, column=1, value=f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        ws.cell(row=2, column=2, value=f"Solo diferencias: {'SI' if only_diffs else 'NO'}")

        info_headers = ["#", "Barcode", "Fecha", "Hora", "Linea", "Resultado"]
        for col_num, h in enumerate(info_headers, start=1):
            c = ws.cell(row=4, column=col_num, value=h)
            c.fill = header_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = border

        for i, run in enumerate(runs, start=5):
            for col_num, value in enumerate([
                f"#{run['run_index']}",
                run["barcode"],
                run["fecha"],
                run["hora"],
                run["linea"],
                run["resultado"],
            ], start=1):
                c = ws.cell(row=i, column=col_num, value=value)
                c.fill = info_fill
                c.font = info_font
                c.alignment = Alignment(horizontal="center", vertical="center")
                c.border = border

        table_start_row = 5 + len(runs) + 2
        table_headers = ["Componente", "Pinref", "Ejecucion"] + [f[1] for f in compare_fields]
        for col_num, h in enumerate(table_headers, start=1):
            c = ws.cell(row=table_start_row, column=col_num, value=h)
            c.fill = header_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = border

        sorted_keys = sorted(groups.keys(), key=lambda k: (k[0] or "", k[1] or ""))

        current_row = table_start_row + 1
        for key in sorted_keys:
            group = groups[key]

            diff_keys = set()
            for f in compare_fields:
                values = set()
                for run in runs:
                    d = group["by_run"].get(run["run_index"])
                    if d:
                        values.add(_norm(d.get(f[0])))
                if len(values) > 1:
                    diff_keys.add(f[0])

            missing_in_some = any(run["run_index"] not in group["by_run"] for run in runs)
            has_any_diff = bool(diff_keys) or missing_in_some

            if only_diffs and not has_any_diff:
                continue

            for run in runs:
                d = group["by_run"].get(run["run_index"])
                run_label = f"#{run['run_index']} - {run['barcode']} {run['fecha']} {run['hora']}"
                row_values = [group["componente"], group["pinref"], run_label]

                for f in compare_fields:
                    if not d:
                        row_values.append("--")
                        continue
                    raw = d.get(f[0])
                    if raw is None or raw == "":
                        row_values.append("")
                    else:
                        suffix = f[2]
                        row_values.append(f"{raw}{suffix}" if suffix else raw)

                for col_num, value in enumerate(row_values, start=1):
                    cell = ws.cell(row=current_row, column=col_num, value=value)
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.border = border

                    if col_num <= 3:
                        cell.fill = cell_fill
                    else:
                        field = compare_fields[col_num - 4]
                        if not d:
                            cell.fill = missing_fill
                        elif field[0] in diff_keys:
                            cell.fill = diff_fill
                            cell.font = diff_font
                        else:
                            cell.fill = cell_fill

                current_row += 1

        widths = [18, 12, 38] + [12] * len(compare_fields)
        for col_idx, width in enumerate(widths, start=1):
            column_letter = ws.cell(row=table_start_row, column=col_idx).column_letter
            ws.column_dimensions[column_letter].width = width

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"comparacion_ict_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    except IctLgdNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except IctLgdPathError as e:
        return jsonify({"error": str(e)}), 400
    except IctLgdError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        import traceback

        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
