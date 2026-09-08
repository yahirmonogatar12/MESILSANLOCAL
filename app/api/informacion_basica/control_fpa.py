"""Módulo MES para solicitar y auditar etiquetas FPA impresas por MICOM."""

from functools import wraps
import uuid

from flask import Blueprint, Response, jsonify, render_template, request, session, stream_with_context

from app.api.shared import auth_system, login_requerido
from app.auth_system import FPA_ADJUST_PERMISSION, FPA_REQUEST_PERMISSION, FPA_VIEW_PERMISSION
from app.services.fpa_micom_client import FpaMicomError, request_micom


bp = Blueprint("control_fpa_api", __name__)


def _has_permission(permission):
    username = session.get("usuario")
    if not username:
        return False
    if auth_system.obtener_rol_principal_usuario(username) == "superadmin":
        return True
    return auth_system.verificar_permiso_boton(
        username, permission["pagina"], permission["seccion"], permission["boton"]
    )


def _requires(permission):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if not _has_permission(permission):
                return jsonify({"success": False, "error": "No tienes permiso para esta acción."}), 403
            return function(*args, **kwargs)
        return wrapped
    return decorator


def _proxy_error(error):
    return jsonify({**error.payload, "success": False, "error": str(error)}), error.status_code


@bp.get("/informacion_basica/control_fpa")
@login_requerido
@_requires(FPA_VIEW_PERMISSION)
def control_fpa_view():
    return render_template(
        "INFORMACION BASICA/control_fpa.html",
        can_request=_has_permission(FPA_REQUEST_PERMISSION),
        can_adjust=_has_permission(FPA_ADJUST_PERMISSION),
    )


@bp.get("/api/control-fpa/requests")
@login_requerido
@_requires(FPA_VIEW_PERMISSION)
def list_requests():
    try:
        return jsonify(request_micom(
            "GET", "/api/fpa/requests", actor=session.get("usuario"), params=request.args.to_dict()
        ))
    except FpaMicomError as error:
        return _proxy_error(error)


@bp.get("/api/control-fpa/requests/<int:request_id>")
@login_requerido
@_requires(FPA_VIEW_PERMISSION)
def request_detail(request_id):
    try:
        return jsonify(request_micom(
            "GET", f"/api/fpa/requests/{request_id}", actor=session.get("usuario")
        ))
    except FpaMicomError as error:
        return _proxy_error(error)


@bp.post("/api/control-fpa/requests")
@login_requerido
@_requires(FPA_REQUEST_PERMISSION)
def create_request():
    data = request.get_json(silent=True) or {}
    data.pop("requester", None)
    data.pop("requesterUserId", None)
    try:
        response = request_micom(
            "POST",
            "/api/fpa/requests",
            actor=session.get("usuario"),
            payload=data,
            idempotency_key=request.headers.get("Idempotency-Key") or str(uuid.uuid4()),
        )
        auth_system.registrar_auditoria(
            session.get("usuario"), "Control de FPA", "SOLICITAR",
            descripcion=f"Solicitud {response.get('data', {}).get('folio', '')}",
            datos_despues=response.get("data"),
        )
        return jsonify(response), 201
    except FpaMicomError as error:
        return _proxy_error(error)


@bp.patch("/api/control-fpa/requests/<int:request_id>/quantities")
@login_requerido
@_requires(FPA_ADJUST_PERMISSION)
def adjust_quantities(request_id):
    data = request.get_json(silent=True) or {}
    try:
        response = request_micom(
            "PATCH", f"/api/fpa/requests/{request_id}/quantities",
            actor=session.get("usuario"), payload=data,
        )
        auth_system.registrar_auditoria(
            session.get("usuario"), "Control de FPA", "AJUSTAR_CANTIDAD",
            descripcion=f"Ajuste de solicitud FPA {request_id}: {data.get('reason', '')}",
            datos_despues=response.get("data"),
        )
        return jsonify(response)
    except FpaMicomError as error:
        return _proxy_error(error)


@bp.get("/api/control-fpa/export")
@login_requerido
@_requires(FPA_VIEW_PERMISSION)
def export_history():
    try:
        upstream = request_micom(
            "GET", "/api/fpa/requests/export", actor=session.get("usuario"),
            params=request.args.to_dict(), stream=True
        )
        headers = {}
        for key in ("Content-Type", "Content-Disposition"):
            if upstream.headers.get(key):
                headers[key] = upstream.headers[key]
        return Response(
            stream_with_context(upstream.iter_content(chunk_size=65536)),
            status=upstream.status_code,
            headers=headers,
        )
    except FpaMicomError as error:
        return _proxy_error(error)
