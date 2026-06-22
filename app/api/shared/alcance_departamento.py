"""Alcance por departamento para administradores delegados.

Helper compartido por los modulos de Administracion de usuario y Gestion de
roles acotados por departamento. Un superadmin no tiene restriccion; el resto
solo administra su propio departamento (`session['departamento']`).
"""

from flask import session


def alcance_actual():
    """Alcance del usuario en sesion.

    Retorna (es_superadmin: bool, departamento: str|None).
    Para superadmin el departamento es None y significa "todos".
    """
    from app.api.shared import auth_system  # lazy: evita ciclos de import

    username = session.get("usuario")
    roles = auth_system.obtener_roles_usuario(username) or []
    if "superadmin" in roles:
        return True, None
    return False, (session.get("departamento") or "").strip()
