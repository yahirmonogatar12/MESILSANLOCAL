"""Casos de uso para Lista de compras (carga, consulta, borrado).

Espejo reducido de invoice_core/service.py: sin packing/pallets/apply. El costeo
por transaccion lo aplica el backend Node en la entrada de almacen; aqui solo se
registran las compras y sus precios. Reusa storage, matcher y normalizadores.
"""

import hashlib
import logging
from decimal import Decimal

from flask import session
from werkzeug.utils import secure_filename

from app.api.control_material.compras_core.parser import parse_compras_workbook
from app.api.control_material.invoice_core.matcher import validate_system_parts
from app.api.control_material.invoice_core.normalizers import json_value, row_to_json
from app.api.control_material.invoice_core.storage import (
    build_relative_path,
    delete_file,
    save_file,
)
from app.api.shared import (
    conexion_o_error,
    dict_cursor,
    obtener_fecha_hora_mexico,
    sanitizar_texto,
)

logger = logging.getLogger(__name__)

ERROR_INTERNO = "Error interno del servidor."
TIPOS_VALIDOS = ("LG", "OVEN")
EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _usuario_actual():
    return session.get("usuario") or "SISTEMA"


def _db():
    conn, error_response = conexion_o_error()
    if error_response:
        return None, None, ({"success": False, "error": "Base de datos no disponible"}, 503)
    return conn, dict_cursor(conn), None


def _normalizar_tipo(value):
    tipo = sanitizar_texto(value, 20).upper()
    return tipo if tipo in TIPOS_VALIDOS else None


def _leer_archivo(files):
    uploaded = files.get("file") or files.get("archivo")
    if not uploaded:
        return None, None, ({"success": False, "error": "Archivo requerido."}, 400)
    filename = secure_filename(uploaded.filename or "compras.xlsx")
    file_bytes = uploaded.read()
    if not file_bytes:
        return None, None, ({"success": False, "error": "El archivo esta vacio."}, 400)
    return filename, file_bytes, None


def preview_compras(files, form):
    filename, file_bytes, error = _leer_archivo(files)
    if error:
        return error
    tipo = _normalizar_tipo(form.get("tipo"))
    if not tipo:
        return {"success": False, "error": "tipo requerido (LG u OVEN)."}, 400
    try:
        parsed = parse_compras_workbook(file_bytes, filename)
    except Exception as exc:
        logger.exception("Error leyendo compras desde %s: %s", filename, exc)
        return {"success": False, "error": "No se pudo leer el Excel de compras."}, 400

    lineas = parsed["lineas"]
    if not lineas:
        detail = " ".join(parsed.get("warnings") or [])
        return {"success": False, "error": f"No se detectaron renglones. {detail}".strip()}, 400

    transacciones = {l["numero_transaccion"] for l in lineas}
    total_monto = sum((l.get("costo_total") or Decimal("0")) for l in lineas)
    sample = [row_to_json(l) for l in lineas[:50]]
    return (
        {
            "success": True,
            "tipo": tipo,
            "total_lineas": len(lineas),
            "total_transacciones": len(transacciones),
            "total_monto": json_value(total_monto),
            "warnings": parsed.get("warnings") or [],
            "sample": sample,
        },
        200,
    )


def upload_compras(files, form):
    filename, file_bytes, error = _leer_archivo(files)
    if error:
        return error
    tipo = _normalizar_tipo(form.get("tipo"))
    if not tipo:
        return {"success": False, "error": "tipo requerido (LG u OVEN)."}, 400
    try:
        parsed = parse_compras_workbook(file_bytes, filename)
    except Exception as exc:
        logger.exception("Error leyendo compras desde %s: %s", filename, exc)
        return {"success": False, "error": "No se pudo leer el Excel de compras."}, 400

    lineas = parsed["lineas"]
    if not lineas:
        detail = " ".join(parsed.get("warnings") or [])
        return {"success": False, "error": f"No se detectaron renglones. {detail}".strip()}, 400

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    conn, cursor, error = _db()
    if error:
        return error
    archivo_ruta = None
    try:
        cursor.execute(
            "SELECT id FROM lista_compras_cargas WHERE archivo_hash_sha256 = %s LIMIT 1",
            (file_hash,),
        )
        existing = cursor.fetchone()
        if existing:
            return (
                {
                    "success": False,
                    "duplicado": True,
                    "carga_id": existing["id"],
                    "message": "Este archivo parece ya cargado.",
                },
                409,
            )

        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()

        # Guarda el Excel original (reusa el storage de invoices: AAAA/MM/slug__hash8).
        archivo_ruta = build_relative_path(f"compras_{tipo}_{filename}", file_hash, fecha)
        _, archivo_size = save_file(file_bytes, archivo_ruta)

        cursor.execute("START TRANSACTION")
        # Resuelve numero_parte_sistema contra materiales (prefijo-match). El
        # Excel puede traer Part Sys; si no, usa Part No. Marca DIRECTO/SIN_ALIAS.
        validate_system_parts(cursor, lineas, "numero_parte_sistema", "DIRECTO")

        transacciones = {l["numero_transaccion"] for l in lineas}
        total_monto = sum((l.get("costo_total") or Decimal("0")) for l in lineas)

        cursor.execute(
            """
            INSERT INTO lista_compras_cargas (
                tipo, archivo_nombre, archivo_ruta, archivo_size, archivo_mime,
                archivo_hash_sha256, total_transacciones, total_lineas, total_monto,
                usuario_carga, fecha_carga
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tipo,
                filename,
                archivo_ruta,
                archivo_size,
                EXCEL_MIME,
                file_hash,
                len(transacciones),
                len(lineas),
                str(total_monto),
                usuario,
                fecha,
            ),
        )
        carga_id = cursor.lastrowid

        _insert_lineas(cursor, carga_id, tipo, lineas)
        conn.commit()
        return (
            {
                "success": True,
                "carga_id": carga_id,
                "tipo": tipo,
                "total_lineas": len(lineas),
                "total_transacciones": len(transacciones),
            },
            201,
        )
    except Exception as exc:
        conn.rollback()
        if archivo_ruta:
            delete_file(archivo_ruta)
        logger.exception("Error cargando compras: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def _insert_lineas(cursor, carga_id, tipo, lineas):
    params = [
        (
            carga_id,
            tipo,
            l["numero_transaccion"],
            l.get("anio"),
            l.get("mes"),
            l.get("fecha_compra"),
            l.get("wk"),
            l.get("raw_part_num"),
            l["numero_parte"],
            l["numero_parte_sistema"],
            l.get("descripcion"),
            l.get("spec"),
            str(l["cantidad"]),
            l.get("moneda") or "USD",
            str(l["costo_unitario"]) if l.get("costo_unitario") is not None else None,
            str(l["costo_total"]) if l.get("costo_total") is not None else None,
            l.get("fecha_factura"),
            l.get("proveedor"),
            l.get("factura"),
            l.get("modelo"),
            l.get("categoria"),
            l.get("comentario"),
            l.get("estado_match") or "SIN_ALIAS",
            l.get("mensaje_match"),
        )
        for l in lineas
    ]
    cursor.executemany(
        """
        INSERT INTO lista_compras_lineas (
            carga_id, tipo, numero_transaccion, anio, mes, fecha_compra, wk,
            raw_part_num, numero_parte, numero_parte_sistema, descripcion, spec,
            cantidad, moneda, costo_unitario, costo_total, fecha_factura,
            proveedor, factura, modelo, categoria, comentario, estado_match, mensaje_match
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        params,
    )


def list_transacciones(args):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        q = sanitizar_texto(args.get("q"), 120)
        tipo = _normalizar_tipo(args.get("tipo"))
        fecha_inicio = sanitizar_texto(args.get("fecha_inicio"), 10)
        fecha_fin = sanitizar_texto(args.get("fecha_fin"), 10)
        where = ["1=1"]
        params = []
        if q:
            like = f"%{q}%"
            where.append(
                "(numero_transaccion LIKE %s OR numero_parte_sistema LIKE %s "
                "OR COALESCE(proveedor,'') LIKE %s OR COALESCE(descripcion,'') LIKE %s)"
            )
            params.extend([like, like, like, like])
        if tipo:
            where.append("tipo = %s")
            params.append(tipo)
        if fecha_inicio:
            where.append("fecha_compra >= %s")
            params.append(fecha_inicio)
        if fecha_fin:
            where.append("fecha_compra <= %s")
            params.append(fecha_fin)

        cursor.execute(
            f"""
            SELECT numero_transaccion,
                   MAX(tipo) AS tipo,
                   MAX(proveedor) AS proveedor,
                   MIN(fecha_compra) AS fecha_compra,
                   COUNT(*) AS num_lineas,
                   COUNT(DISTINCT numero_parte_sistema) AS num_partes,
                   SUM(COALESCE(costo_total, 0)) AS total_monto
            FROM lista_compras_lineas
            WHERE {' AND '.join(where)}
            GROUP BY numero_transaccion
            ORDER BY MIN(fecha_compra) DESC, numero_transaccion DESC
            LIMIT 500
            """,
            params,
        )
        records = [row_to_json(r) for r in (cursor.fetchall() or [])]
        return {"success": True, "records": records, "total": len(records)}, 200
    except Exception as exc:
        logger.exception("Error listando transacciones: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def get_transaccion_detail(numero_transaccion):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        numero = sanitizar_texto(numero_transaccion, 255)
        cursor.execute(
            """
            SELECT *
            FROM lista_compras_lineas
            WHERE numero_transaccion = %s
            ORDER BY id ASC
            """,
            (numero,),
        )
        lineas = [row_to_json(r) for r in (cursor.fetchall() or [])]
        if not lineas:
            return {"success": False, "error": "Transaccion no encontrada."}, 404
        return {"success": True, "numero_transaccion": numero, "lineas": lineas}, 200
    except Exception as exc:
        logger.exception("Error obteniendo transaccion: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def list_cargas(args):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        tipo = _normalizar_tipo(args.get("tipo"))
        where = ["1=1"]
        params = []
        if tipo:
            where.append("tipo = %s")
            params.append(tipo)
        cursor.execute(
            f"""
            SELECT id, tipo, archivo_nombre, total_transacciones, total_lineas,
                   total_monto, usuario_carga, fecha_carga
            FROM lista_compras_cargas
            WHERE {' AND '.join(where)}
            ORDER BY fecha_carga DESC, id DESC
            LIMIT 300
            """,
            params,
        )
        records = [row_to_json(r) for r in (cursor.fetchall() or [])]
        return {"success": True, "records": records, "total": len(records)}, 200
    except Exception as exc:
        logger.exception("Error listando cargas: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def delete_carga(carga_id):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        cursor.execute(
            "SELECT archivo_ruta FROM lista_compras_cargas WHERE id = %s LIMIT 1",
            (carga_id,),
        )
        carga = cursor.fetchone()
        if not carga:
            return {"success": False, "error": "Carga no encontrada."}, 404
        cursor.execute("START TRANSACTION")
        cursor.execute("DELETE FROM lista_compras_lineas WHERE carga_id = %s", (carga_id,))
        cursor.execute("DELETE FROM lista_compras_cargas WHERE id = %s", (carga_id,))
        conn.commit()
        if carga.get("archivo_ruta"):
            delete_file(carga["archivo_ruta"])
        return {"success": True}, 200
    except Exception as exc:
        conn.rollback()
        logger.exception("Error borrando carga: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def resolve_compras_file(carga_id):
    """Devuelve (ruta_relativa, nombre) o (None, None) para descarga."""
    conn, cursor, error = _db()
    if error:
        return None, None
    try:
        cursor.execute(
            "SELECT archivo_ruta, archivo_nombre FROM lista_compras_cargas WHERE id = %s LIMIT 1",
            (carga_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None, None
        return row.get("archivo_ruta"), row.get("archivo_nombre")
    finally:
        cursor.close()
        conn.close()
