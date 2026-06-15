"""Almacenamiento en disco de los Excel originales de invoices.

Guarda cada archivo cargado renombrado por numero de invoice y ordenado por
fecha (AAAA/MM), de modo que se puedan consultar/descargar despues. La logica
de BD vive en service.py; aqui solo se resuelven rutas y se escribe/lee disco.
"""

import os
import re
import unicodedata

# Raiz del proyecto: <repo>/MESILSANLOCAL (este archivo esta en
# app/api/control_material/invoice_core/storage.py -> subir 5 niveles).
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_DEFAULT_STORAGE_DIR = os.path.join(_PROJECT_ROOT, "storage", "invoices")


def storage_root():
    """Carpeta base de los Excel de invoices (configurable por env)."""
    return os.path.abspath(
        os.environ.get("MES_INVOICE_STORAGE_DIR") or _DEFAULT_STORAGE_DIR
    )


def _safe_slug(value, fallback="invoice"):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._-")
    return text or fallback


def build_relative_path(numero_invoice, file_hash, fecha):
    """Ruta relativa AAAA/MM/<numero>__<hash8>.xlsx (estable y unica)."""
    year = fecha.strftime("%Y")
    month = fecha.strftime("%m")
    slug = _safe_slug(numero_invoice)
    short_hash = (file_hash or "")[:8] or "nohash"
    return os.path.join(year, month, f"{slug}__{short_hash}.xlsx")


def absolute_path(relative_path):
    if not relative_path:
        return None
    # Normaliza separadores guardados en BD (pudieron escribirse en otra OS).
    relative_path = relative_path.replace("\\", os.sep).replace("/", os.sep)
    full = os.path.abspath(os.path.join(storage_root(), relative_path))
    # Evita traversal fuera del root.
    if os.path.commonpath([full, storage_root()]) != storage_root():
        return None
    return full


def save_file(file_bytes, relative_path):
    """Escribe el archivo en disco; devuelve (ruta_absoluta, size)."""
    full = absolute_path(relative_path)
    if not full:
        raise ValueError("Ruta de almacenamiento invalida.")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as handle:
        handle.write(file_bytes)
    return full, len(file_bytes)


def delete_file(relative_path):
    """Borra el archivo si existe (best-effort, para rollback)."""
    full = absolute_path(relative_path)
    if full and os.path.isfile(full):
        try:
            os.remove(full)
        except OSError:
            pass
