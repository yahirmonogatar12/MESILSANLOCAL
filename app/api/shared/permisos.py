"""Fachada del backend de permisos por boton (dropdowns).

Punto de entrada unico para acceder a los permisos de cada boton. ENVUELVE
los metodos existentes de `auth_system` (no los reemplaza): la logica de
dominio, la cache TTL y las queries siguen viviendo en `app/auth_system.py`;
aqui solo se centraliza el acceso, el decorador y la normalizacion de datos.

Antes esto estaba disperso: el decorador `requiere_permiso_dropdown` en
`app/routes.py` (con proxies duplicados en 7 blueprints), el lookup
reimplementado en varios sitios con `isinstance(item, dict)` defensivo, y los
filtros Jinja con su propia copia. Esta fachada unifica todo.

El acceso a `auth_system` es LAZY (dentro de las funciones) para evitar ciclos
de import: `app.api.shared` reexporta el singleton `auth_system` desde
`app.routes`, y los blueprints se importan despues de que `routes` esta cargado.
"""

import logging
from functools import wraps

from flask import jsonify, request, session

logger = logging.getLogger(__name__)


def _auth():
    """Devuelve el singleton AuthSystem (import lazy, evita ciclos)."""
    from app.api.shared import auth_system
    return auth_system


def _normalizar_boton(item):
    """Unico punto que tolera la mezcla dict/string del backend.

    Devuelve SIEMPRE {"boton": str|None, "descripcion": str|None}.
    """
    if isinstance(item, dict):
        return {"boton": item.get("boton"), "descripcion": item.get("descripcion")}
    return {"boton": item, "descripcion": None}


def permisos_botones(username, pagina=None):
    """Permisos de botones del usuario, normalizados.

    Forma: {pagina: {seccion: [{"boton","descripcion"}, ...]}}.
    Delega en auth_system y normaliza cada item a dict.
    """
    raw = _auth().obtener_permisos_botones_usuario(username, pagina) or {}
    normalizado = {}
    for pag, secciones in raw.items():
        normalizado[pag] = {}
        for seccion, botones in (secciones or {}).items():
            normalizado[pag][seccion] = [_normalizar_boton(it) for it in (botones or [])]
    return normalizado


def puede_boton(username, pagina, seccion, boton):
    """True si el usuario puede usar ese boton en esa pagina/seccion.

    Delega en auth_system.verificar_permiso_boton (incluye bypass superadmin).
    """
    return bool(_auth().verificar_permiso_boton(username, pagina, seccion, boton))


def puede_boton_por_nombre(username, boton):
    """True si el usuario tiene el boton (por NOMBRE) en cualquier pagina/seccion.

    Semantica del filtro Jinja `tiene_permiso_boton` (solo conoce el nombre del
    boton). Incluye bypass de superadmin.
    """
    try:
        if _auth().obtener_rol_principal_usuario(username) == "superadmin":
            return True
        for secciones in permisos_botones(username).values():
            for botones in secciones.values():
                for item in botones:  # ya normalizados a dict
                    if item.get("boton") == boton:
                        return True
        return False
    except Exception as e:
        logger.error("Error verificando permiso de boton '%s': %s", boton, e)
        return False


def invalidar_cache(username=None):
    """Invalida la cache de permisos de botones (delega en auth_system)."""
    return _auth().invalidar_cache_permisos_botones(username)


def requiere_permiso_dropdown(pagina, seccion, boton):
    """Decorador canonico para gatear endpoints por permiso de boton.

    Comportamiento (preservado del original en app.routes):
      - 401 JSON si no hay sesion.
      - bypass para superadmin.
      - 403 JSON para peticiones AJAX/JSON, o bloque HTML 403 para navegacion
        directa (carga de fragmentos).
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "usuario" not in session:
                return jsonify(
                    {"error": "Usuario no autenticado", "redirect": "/login"}
                ), 401

            try:
                username = session["usuario"]
                logger.info(
                    " Verificando permisos para usuario: %s, pagina: %s, seccion: %s, boton: %s",
                    username, pagina, seccion, boton,
                )

                auth = _auth()
                rol_nombre = auth.obtener_rol_principal_usuario(username)
                if not rol_nombre:
                    logger.info(" Usuario sin roles asignados")
                    return jsonify({"error": "Usuario sin roles asignados"}), 403

                logger.info(" Rol del usuario: %s", rol_nombre)
                if rol_nombre == "superadmin":
                    logger.info(" Superadmin: permiso concedido")
                    return f(*args, **kwargs)

                tiene_permiso = auth.verificar_permiso_boton(
                    username, pagina, seccion, boton
                )
                logger.info(" Tiene permiso: %s", tiene_permiso)

                if not tiene_permiso:
                    logger.info(" Sin permisos para: %s > %s > %s", pagina, seccion, boton)
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

                logger.info(" Permisos verificados correctamente, ejecutando funcion...")
                return f(*args, **kwargs)

            except Exception as e:
                logger.exception(" Error verificando permisos: %s", e)
                return jsonify({"error": "Error interno del servidor"}), 500

        return decorated_function

    return decorator
