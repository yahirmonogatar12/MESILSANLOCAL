"""Papeleria de los ECOs: archivos HTML, PPT/PPTX y PDF adjuntos a cada ECO MES.

Los archivos van a disco (storage/eco_files/<eco_id>/<uuid>.<ext>) y la BD
solo guarda metadatos. El nombre en disco no depende del nombre subido, asi
que no hay path traversal posible.
"""

import os
import shutil
import uuid

from app.db_mysql import execute_query

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
STORAGE_ROOT = os.path.join(_PROJECT_ROOT, "storage", "eco_files")

# Extension -> mimetype con que se sirve.
TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # PPT antiguo (binario): se acepta pero el navegador no lo puede dibujar,
    # solo se descarga.
    ".ppt": "application/vnd.ms-powerpoint",
    ".pdf": "application/pdf",
}
EXTENSIONES_HTML = {".html", ".htm"}
MAX_BYTES = 50 * 1024 * 1024


def crear_tabla_eco_files():
    execute_query("""
        CREATE TABLE IF NOT EXISTS engineering_change_files (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            engineering_change_id BIGINT NOT NULL,
            nombre_original VARCHAR(255) NOT NULL,
            extension VARCHAR(10) NOT NULL,
            archivo_ruta VARCHAR(255) NOT NULL,
            size_bytes BIGINT NOT NULL DEFAULT 0,
            created_by VARCHAR(100) NULL,
            created_at DATETIME DEFAULT NOW(),
            INDEX idx_ecf_eco (engineering_change_id)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """)


def listar(eco_id):
    return execute_query(
        """
        SELECT id, engineering_change_id, nombre_original, extension, size_bytes, created_by, created_at
        FROM engineering_change_files
        WHERE engineering_change_id = %s
        ORDER BY id
        """,
        (eco_id,),
        fetch="all",
    ) or []


def ultimo_eco_con_papeleria(part_no):
    """ECO mas reciente (no cancelado) del numero de parte que tenga archivos.

    Cuenta el ECO del part_no y los ECO de familia que lo incluyen en su
    scope. Se salta los ECO sin archivos: si el ultimo no actualizo el
    dibujo, el vigente sigue siendo el del ECO anterior.
    """
    return execute_query(
        """
        SELECT ec.id, ec.eco_no, ec.part_no, ec.status, ec.effective_at
        FROM engineering_changes ec
        WHERE ec.status <> 'CANCELLED'
          AND EXISTS (SELECT 1 FROM engineering_change_files f WHERE f.engineering_change_id = ec.id)
          AND (
                ec.part_no = %s
             OR EXISTS (
                    SELECT 1 FROM engineering_change_scope s
                    WHERE s.engineering_change_id = ec.id AND s.part_no = %s
                )
          )
        ORDER BY ec.effective_at DESC, ec.id DESC
        LIMIT 1
        """,
        (part_no, part_no),
        fetch="one",
    )


def obtener(eco_id, file_id):
    return execute_query(
        "SELECT * FROM engineering_change_files WHERE id = %s AND engineering_change_id = %s",
        (file_id, eco_id),
        fetch="one",
    )


def ruta_absoluta(row):
    full = os.path.abspath(os.path.join(STORAGE_ROOT, row["archivo_ruta"]))
    # Defensa en profundidad: nunca servir algo fuera del root.
    return full if full.startswith(STORAGE_ROOT + os.sep) else None


def guardar(eco_id, filename, data, usuario):
    """Escribe el archivo y su registro. Devuelve un mensaje de error o None."""
    nombre = os.path.basename((filename or "").replace("\\", "/")).strip()[:255]
    extension = os.path.splitext(nombre)[1].lower()
    if extension not in TIPOS:
        return "Solo se permiten archivos HTML, PPT/PPTX o PDF."
    if not data:
        return "El archivo esta vacio."
    if len(data) > MAX_BYTES:
        return f"El archivo excede {MAX_BYTES // (1024 * 1024)} MB."

    ruta = os.path.join(str(int(eco_id)), f"{uuid.uuid4().hex}{extension}")
    full = os.path.join(STORAGE_ROOT, ruta)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as fh:
        fh.write(data)
    try:
        execute_query(
            """
            INSERT INTO engineering_change_files
                (engineering_change_id, nombre_original, extension, archivo_ruta, size_bytes, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (eco_id, nombre, extension, ruta, len(data), usuario),
        )
    except Exception:
        os.remove(full)
        raise
    return None


def eliminar(row):
    execute_query("DELETE FROM engineering_change_files WHERE id = %s", (row["id"],))
    full = ruta_absoluta(row)
    if full and os.path.isfile(full):
        os.remove(full)


def eliminar_de_eco(eco_id):
    """Borra toda la papeleria de un ECO (al borrar el ECO)."""
    execute_query("DELETE FROM engineering_change_files WHERE engineering_change_id = %s", (eco_id,))
    shutil.rmtree(os.path.join(STORAGE_ROOT, str(int(eco_id))), ignore_errors=True)
