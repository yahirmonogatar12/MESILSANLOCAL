"""Cliente servidor-a-servidor para el Control de FPA autoritativo en MICOM."""

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlparse

import requests


class FpaMicomError(RuntimeError):
    def __init__(self, message, status_code=503, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


def _base_url():
    return os.getenv("MICOM_API_URL", "http://127.0.0.1:3012").rstrip("/")


def _secret():
    value = os.getenv("MICOM_INTEGRATION_SECRET", "").strip()
    if not value:
        raise FpaMicomError(
            "MICOM_INTEGRATION_SECRET no está configurado en MES.",
            status_code=503,
        )
    return value.encode("utf-8")


def request_micom(method, path, *, actor, payload=None, params=None, idempotency_key=None, stream=False):
    method = method.upper()
    body = b"" if payload is None else json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    timestamp = str(int(time.time() * 1000))
    body_hash = hashlib.sha256(body).hexdigest()
    normalized_path = urlparse(path).path
    actor_name = str(actor or "MES")[:100]
    canonical = f"{timestamp}\n{method}\n{normalized_path}\n{actor_name}\n{body_hash}".encode("utf-8")
    signature = hmac.new(_secret(), canonical, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-MES-Timestamp": timestamp,
        "X-MES-Body-SHA256": body_hash,
        "X-MES-Signature": signature,
        "X-MES-User": actor_name,
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    try:
        response = requests.request(
            method,
            f"{_base_url()}{path}",
            data=body if body else None,
            params=params,
            headers=headers,
            timeout=(4, 35),
            stream=stream,
        )
    except requests.RequestException as exc:
        raise FpaMicomError(f"MICOM no está disponible: {exc}") from exc

    if stream and response.ok:
        return response
    try:
        data = response.json()
    except ValueError:
        data = {"error": response.text[:300] or "Respuesta inválida de MICOM"}
    if not response.ok:
        raise FpaMicomError(
            data.get("error") or data.get("message") or f"Error MICOM {response.status_code}",
            status_code=response.status_code,
            payload=data,
        )
    return data
