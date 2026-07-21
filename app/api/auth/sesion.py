"""Endpoints de sesion del portal corporativo (login / logout / perfil / landing).

Migrado desde `app/routes.py` el 2026-05-28 (Fase 6). Sin cambios funcionales.

Rutas (con `endpoint=` explicito que fija el nombre LOCAL del endpoint; el
endpoint real queda prefijado por el blueprint, p.ej. `auth_sesion.login`):

  GET   /                  -> index            (redirect a inicio)
  GET   /inicio            -> inicio           (landing page)
  POST  /login             -> login            (procesa credenciales)
  GET   /logout            -> logout           (cierra sesion)
  GET   /api/mi-perfil     -> api_mi_perfil    (datos del usuario logueado)
  POST  /api/mi-perfil     -> api_mi_perfil    (actualiza perfil + password)

Helpers privados que vinieron juntos:
  - `render_landing_page()`   — render compartido por index/inicio/login

Convenciones (OJO con url_for):
  - Blueprint name: "auth_sesion". `endpoint="login"` NO quita el prefijo: el
    endpoint real es `auth_sesion.login` (Flask siempre antepone el nombre del
    blueprint). Por eso TODAS las referencias usan la forma PREFIJADA:
    `url_for("auth_sesion.login")`, `url_for("auth_sesion.inicio")`, etc. en
    routes.py, templates (landing.html, login.html) y otros modulos.
  - `PUBLIC_ROUTE_ENDPOINTS` en routes.py lista los nombres prefijados:
    "auth_sesion.index", "auth_sesion.inicio", "auth_sesion.login" (mas
    "favicon", que es ruta a nivel de app, sin blueprint).
"""

import os
import re

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth_system import auth_system
from app.db import get_db_connection

import logging
logger = logging.getLogger(__name__)


bp = Blueprint("auth_sesion", __name__)


# Nota: el login usa SOLO el sistema de BD. El fallback legacy a usuarios.json
# (funcion cargar_usuarios) se elimino el 2026-05-29: el archivo no existia y
# ese path comparaba contrasenas en texto plano.


@bp.after_request
def disable_session_page_cache(response):
    """Impedir que navegador/proxy reutilice una landing sin sesion."""
    if request.endpoint in {
        "auth_sesion.index",
        "auth_sesion.inicio",
        "auth_sesion.login",
    }:
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, private"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.vary.add("Cookie")
    return response


# ---------------------------------------------------------------------------
# Helper compartido: render de la landing page (con o sin sesion)
# ---------------------------------------------------------------------------


def render_landing_page(login_error=None, login_username=None):
    """Renderiza la landing page con o sin sesion activa."""
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
            "name": "Mas Herramientas",
            "description": "Expansion futura",
            "long_description": "Nuevas aplicaciones seran agregadas pronto.",
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


# ---------------------------------------------------------------------------
# Endpoints de sesion
# ---------------------------------------------------------------------------


@bp.route("/", endpoint="index")
def index():
    return redirect(url_for("auth_sesion.inicio"))


@bp.route("/inicio", endpoint="inicio")
def inicio():
    """Landing page / Hub de aplicaciones."""
    return render_landing_page()


@bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "GET":
        return redirect(url_for("auth_sesion.inicio"))

    is_ajax = request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")

    user = request.form.get("username", "").strip()
    pw = request.form.get("password", "")
    logger.info(f" Intento de login: {user}")

    # PRIORIDAD 1: Intentar con el nuevo sistema de BD
    resultado_auth = auth_system.verificar_usuario(user, pw)

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
        logger.info(f" Login exitoso con sistema BD: {user}")
        # Eliminar cualquier contenido anonimo o firmado con una configuracion
        # anterior antes de construir la nueva sesion autenticada.
        session.clear()
        session["usuario"] = user

        info_usuario = auth_system.obtener_informacion_usuario(user)
        if info_usuario:
            session["nombre_completo"] = info_usuario["nombre_completo"]
            session["email"] = info_usuario["email"]
            session["departamento"] = info_usuario["departamento"]
            logger.info(f" Informacion completa cargada para {user}:")
            logger.info(f"  - Nombre completo: {info_usuario['nombre_completo']}")
            logger.info(f"  - Email: {info_usuario['email']}")
            logger.info(f"  - Departamento: {info_usuario['departamento']}")
        else:
            session["nombre_completo"] = user
            logger.error(
                f" No se pudo cargar informacion completa para {user}, usando username como fallback"
            )

        auth_system.registrar_auditoria(
            usuario=user,
            modulo="sistema",
            accion="login",
            descripcion="Inicio de sesion exitoso",
            resultado="EXITOSO",
        )

        permisos_resultado = auth_system.obtener_permisos_usuario(user)
        if isinstance(permisos_resultado, tuple):
            permisos, rol_id = permisos_resultado
        else:
            permisos = permisos_resultado
            rol_id = None

        session["permisos"] = permisos
        session["roles"] = auth_system.obtener_roles_usuario(user)
        session["rol_principal"] = session["roles"][0] if session["roles"] else None
        session.modified = True
        logger.info(f" Permisos establecidos en sesion para {user}: {permisos}")

        logger.info(f" Login exitoso para {user}, redirigiendo al hub de aplicaciones")
        redirect_url = url_for("auth_sesion.inicio")
        if is_ajax:
            return jsonify({"success": True, "redirect": redirect_url})
        return redirect(redirect_url)

    logger.error(f" Login fallo: {user} ({auth_message})")
    auth_system.registrar_auditoria(
        usuario=user,
        modulo="sistema",
        accion="login_failed",
        descripcion="Intento de login fallido - credenciales incorrectas",
        resultado="ERROR",
    )

    error_message = "Usuario o contrasena incorrectos. Por favor, intente de nuevo"

    if is_ajax:
        return jsonify({"success": False, "message": error_message}), 401

    return render_landing_page(login_error=error_message, login_username=user)


@bp.route("/logout", endpoint="logout")
def logout():
    usuario = session.get("usuario", "unknown")

    if usuario != "unknown":
        auth_system.registrar_auditoria(
            usuario=usuario,
            modulo="sistema",
            accion="logout",
            descripcion="Cierre de sesion",
            resultado="EXITOSO",
        )
        logger.info(f" Logout exitoso: {usuario}")

    session.clear()
    return redirect(url_for("auth_sesion.inicio"))


@bp.route("/api/mi-perfil", methods=["GET", "POST"], endpoint="api_mi_perfil")
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
        logger.error(f"Error actualizando perfil de {usuario}: {exc}")
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
