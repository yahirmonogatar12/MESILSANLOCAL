"""Casos de uso para Lista de compras (carga, consulta, borrado).

Espejo reducido de invoice_core/service.py: sin packing/pallets/apply. El costeo
por transaccion lo aplica el backend Node en la entrada de almacen; aqui solo se
registran las compras y sus precios. Reusa storage, matcher y normalizadores.
"""

import hashlib
import logging
import threading
import time
import unicodedata
from collections import Counter, OrderedDict
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

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
DB_IN_CHUNK_SIZE = 500
PARSE_CACHE_MAX_ITEMS = 2
PARSE_CACHE_TTL_SECONDS = 10 * 60

_parse_cache = OrderedDict()
_parse_cache_lock = threading.Lock()

# Campos que identifican una compra. Se excluyen descripcion/spec/comentario para
# que un cambio meramente descriptivo no vuelva a insertar una compra existente.
_LINE_IDENTITY_COLUMNS = (
    "numero_transaccion",
    "raw_part_num",
    "fecha_compra",
    "cantidad",
    "costo_unitario",
    "costo_total",
    "fecha_factura",
    "proveedor",
    "factura",
    "modelo",
    "categoria",
)


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


def _normalizar_modo(value):
    # INICIAL = histórico (entra CERRADO, no aparece en almacén). ACTUALIZACION =
    # solo agrega transacciones nuevas, ABIERTAS (aparecen en almacén).
    modo = sanitizar_texto(value, 20).upper()
    return "INICIAL" if modo == "INICIAL" else "ACTUALIZACION"


def _tiene_carga_inicial(cursor, tipo):
    cursor.execute(
        "SELECT id FROM lista_compras_cargas WHERE tipo = %s AND modo = 'INICIAL' LIMIT 1",
        (tipo,),
    )
    return cursor.fetchone() is not None


def _text_key(value):
    """Clave comparable como utf8mb4_unicode_ci: sin acentos, caso ni espacios extra."""
    text = "" if value is None else str(value)
    text = text.replace("\u00a0", " ").strip()
    text = " ".join(text.split())
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return text.casefold()


def _transaction_key(value):
    return _text_key(value)


def _date_key(value):
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value or "")[:10]


def _decimal_key(value):
    if value in (None, ""):
        return None
    try:
        normalized = Decimal(str(value)).normalize()
        return format(normalized, "f")
    except Exception:
        return str(value).strip()


def _line_signature(line):
    """Firma estable de una línea, compatible entre openpyxl y MySQL."""
    return (
        _transaction_key(line.get("numero_transaccion")),
        _text_key(line.get("raw_part_num") or line.get("numero_parte")),
        _date_key(line.get("fecha_compra")),
        _decimal_key(line.get("cantidad")),
        _decimal_key(line.get("costo_unitario")),
        _decimal_key(line.get("costo_total")),
        _date_key(line.get("fecha_factura")),
        _text_key(line.get("proveedor")),
        _text_key(line.get("factura")),
        _text_key(line.get("modelo")),
        _text_key(line.get("categoria")),
    )


def _chunks(values, size=DB_IN_CHUNK_SIZE):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _existing_lines(cursor, tipo, lineas):
    """Lee líneas candidatas por bloques y evita repetir filas por collation/chunks."""
    numeros = sorted({l.get("numero_transaccion") or "" for l in lineas})
    nonblank = [numero for numero in numeros if numero]
    rows_by_id = {}
    select_columns = ", ".join(("id", *_LINE_IDENTITY_COLUMNS))

    for chunk in _chunks(nonblank):
        placeholders = ", ".join(["%s"] * len(chunk))
        cursor.execute(
            f"""
            SELECT {select_columns}
            FROM lista_compras_lineas
            WHERE tipo = %s AND numero_transaccion IN ({placeholders})
            """,
            [tipo, *chunk],
        )
        for row in cursor.fetchall() or []:
            rows_by_id[row["id"]] = row

    if "" in numeros:
        cursor.execute(
            f"""
            SELECT {select_columns}
            FROM lista_compras_lineas
            WHERE tipo = %s AND numero_transaccion = ''
            """,
            (tipo,),
        )
        for row in cursor.fetchall() or []:
            rows_by_id[row["id"]] = row

    return list(rows_by_id.values())


def _filter_new_lines(cursor, tipo, lineas):
    """Quita sólo líneas ya cargadas; permite nuevas partes en una transacción vieja."""
    existing_rows = _existing_lines(cursor, tipo, lineas)
    existing_counts = Counter(_line_signature(row) for row in existing_rows)
    existing_transaction_keys = {
        _transaction_key(row.get("numero_transaccion")) for row in existing_rows
    }
    new_lines = []
    matched_lines = 0

    # Counter conserva multiplicidad: si BD tiene una copia y el nuevo Excel dos,
    # sólo la copia adicional se considera nueva.
    for line in lineas:
        signature = _line_signature(line)
        if existing_counts[signature] > 0:
            existing_counts[signature] -= 1
            matched_lines += 1
        else:
            new_lines.append(line)

    return new_lines, matched_lines, existing_transaction_keys


def _parse_cached(file_bytes, filename):
    """Evita parsear dos veces el mismo Excel entre preview y confirmación."""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    now = time.monotonic()
    with _parse_cache_lock:
        cached = _parse_cache.get(file_hash)
        if cached and now - cached[0] <= PARSE_CACHE_TTL_SECONDS:
            _parse_cache.move_to_end(file_hash)
            return deepcopy(cached[1]), file_hash
        if cached:
            del _parse_cache[file_hash]

    parsed = parse_compras_workbook(file_bytes, filename)
    with _parse_cache_lock:
        _parse_cache[file_hash] = (now, parsed)
        _parse_cache.move_to_end(file_hash)
        while len(_parse_cache) > PARSE_CACHE_MAX_ITEMS:
            _parse_cache.popitem(last=False)
    return deepcopy(parsed), file_hash


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
    modo = _normalizar_modo(form.get("modo"))
    try:
        parsed, _ = _parse_cached(file_bytes, filename)
    except Exception as exc:
        logger.exception("Error leyendo compras desde %s: %s", filename, exc)
        return {"success": False, "error": "No se pudo leer el Excel de compras."}, 400

    lineas = parsed["lineas"]
    if not lineas:
        detail = " ".join(parsed.get("warnings") or [])
        return {"success": False, "error": f"No se detectaron renglones. {detail}".strip()}, 400

    transaction_keys = {_transaction_key(l["numero_transaccion"]) for l in lineas}
    total_monto = sum((l.get("costo_total") or Decimal("0")) for l in lineas)
    sample_lines = lineas

    # Cuántas transacciones son nuevas vs ya existen (para que el usuario sepa
    # qué se agregará). En INICIAL todo entra cerrado; en ACTUALIZACION solo las
    # nuevas se insertan (abiertas).
    conn, cursor, db_error = _db()
    nuevas = len(transaction_keys)
    existentes = 0
    lineas_nuevas = len(lineas)
    lineas_existentes = 0
    bloqueado_inicial = False
    if not db_error:
        try:
            if modo == "ACTUALIZACION":
                nuevas_lineas, lineas_existentes, _ = _filter_new_lines(
                    cursor, tipo, lineas
                )
                sample_lines = nuevas_lineas
                lineas_nuevas = len(nuevas_lineas)
                new_transaction_keys = {
                    _transaction_key(line["numero_transaccion"])
                    for line in nuevas_lineas
                }
                nuevas = len(new_transaction_keys)
                existentes = len(transaction_keys - new_transaction_keys)
            if modo == "INICIAL":
                bloqueado_inicial = _tiene_carga_inicial(cursor, tipo)
        finally:
            cursor.close()
            conn.close()

    return (
        {
            "success": True,
            "tipo": tipo,
            "modo": modo,
            "total_lineas": len(lineas),
            "total_transacciones": len(transaction_keys),
            "transacciones_nuevas": nuevas,
            "transacciones_existentes": existentes,
            "lineas_nuevas": lineas_nuevas,
            "lineas_existentes": lineas_existentes,
            "bloqueado_inicial": bloqueado_inicial,
            "total_monto": json_value(total_monto),
            "warnings": parsed.get("warnings") or [],
            # En ACTUALIZACION la tabla de preview sólo enseña lo que se insertará.
            "sample": [row_to_json(line) for line in sample_lines[:50]],
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
    modo = _normalizar_modo(form.get("modo"))
    try:
        parsed, file_hash = _parse_cached(file_bytes, filename)
    except Exception as exc:
        logger.exception("Error leyendo compras desde %s: %s", filename, exc)
        return {"success": False, "error": "No se pudo leer el Excel de compras."}, 400

    lineas = parsed["lineas"]
    if not lineas:
        detail = " ".join(parsed.get("warnings") or [])
        return {"success": False, "error": f"No se detectaron renglones. {detail}".strip()}, 400

    conn, cursor, error = _db()
    if error:
        return error
    archivo_ruta = None
    try:
        if modo == "INICIAL":
            # Solo una carga inicial por tipo: fija el histórico como CERRADO.
            if _tiene_carga_inicial(cursor, tipo):
                return (
                    {
                        "success": False,
                        "bloqueado_inicial": True,
                        "message": f"Ya existe una carga inicial para {tipo}. Usa 'Actualizar'.",
                    },
                    409,
                )
            # En INICIAL el mismo archivo no debe re-cargarse (de-dup por hash).
            cursor.execute(
                "SELECT id FROM lista_compras_cargas WHERE archivo_hash_sha256 = %s LIMIT 1",
                (file_hash,),
            )
            dup = cursor.fetchone()
            if dup:
                return (
                    {
                        "success": False,
                        "duplicado": True,
                        "carga_id": dup["id"],
                        "message": "Este archivo ya fue cargado.",
                    },
                    409,
                )

        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()

        # Resuelve numero_parte_sistema contra materiales (prefijo-match). El
        # Excel puede traer Part Sys; si no, usa Part No. Marca DIRECTO/SIN_ALIAS.
        validate_system_parts(cursor, lineas, "numero_parte_sistema", "DIRECTO")

        if modo == "INICIAL":
            lineas_a_insertar = lineas
            estado_lineas = "CERRADA"
        else:
            # ACTUALIZACION: de-dup por firma de línea, no por transacción. Así
            # una transacción vieja puede recibir una parte/renglón nuevo.
            lineas_a_insertar, lineas_existentes, existing_transaction_keys = (
                _filter_new_lines(cursor, tipo, lineas)
            )
            estado_lineas = "ABIERTA"
            if not lineas_a_insertar:
                return (
                    {
                        "success": True,
                        "carga_id": None,
                        "tipo": tipo,
                        "modo": modo,
                        "total_lineas": 0,
                        "total_transacciones": 0,
                        "transacciones_existentes": len(existing_transaction_keys),
                        "lineas_existentes": lineas_existentes,
                        "message": "Sin renglones nuevos que agregar.",
                    },
                    200,
                )

        # Guarda el Excel original (reusa el storage de invoices: AAAA/MM/slug__hash8).
        # En ACTUALIZACION el hash puede repetirse entre cargas: se renombra por fecha.
        slug = f"compras_{tipo}_{modo}_{filename}"
        archivo_ruta = build_relative_path(slug, file_hash, fecha)
        _, archivo_size = save_file(file_bytes, archivo_ruta)

        cursor.execute("START TRANSACTION")
        transacciones = {
            _transaction_key(l["numero_transaccion"]) for l in lineas_a_insertar
        }
        total_monto = sum((l.get("costo_total") or Decimal("0")) for l in lineas_a_insertar)

        cursor.execute(
            """
            INSERT INTO lista_compras_cargas (
                tipo, modo, archivo_nombre, archivo_ruta, archivo_size, archivo_mime,
                archivo_hash_sha256, total_transacciones, total_lineas, total_monto,
                usuario_carga, fecha_carga
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tipo,
                modo,
                filename,
                archivo_ruta,
                archivo_size,
                EXCEL_MIME,
                # En ACTUALIZACION el mismo Excel puede re-subirse: el hash deja de
                # ser único, así que se sufija con un uuid corto para no chocar con
                # el UNIQUE. En INICIAL se guarda el hash real (de-dup por archivo).
                file_hash if modo == "INICIAL" else f"{file_hash[:31]}-{uuid4().hex}",
                len(transacciones),
                len(lineas_a_insertar),
                str(total_monto),
                usuario,
                fecha,
            ),
        )
        carga_id = cursor.lastrowid

        _insert_lineas(cursor, carga_id, tipo, lineas_a_insertar, estado_lineas)
        conn.commit()
        return (
            {
                "success": True,
                "carga_id": carga_id,
                "tipo": tipo,
                "modo": modo,
                "total_lineas": len(lineas_a_insertar),
                "total_transacciones": len(transacciones),
                "estado_lineas": estado_lineas,
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


def _insert_lineas(cursor, carga_id, tipo, lineas, estado="ABIERTA"):
    params = [
        (
            carga_id,
            tipo,
            l["numero_transaccion"],
            estado,
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
            carga_id, tipo, numero_transaccion, estado, anio, mes, fecha_compra, wk,
            raw_part_num, numero_parte, numero_parte_sistema, descripcion, spec,
            cantidad, moneda, costo_unitario, costo_total, fecha_factura,
            proveedor, factura, modelo, categoria, comentario, estado_match, mensaje_match
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        estado = sanitizar_texto(args.get("estado"), 10).upper()
        if estado in ("ABIERTA", "CERRADA", "APLICADA"):
            where.append("estado = %s")
            params.append(estado)
        if fecha_inicio:
            where.append("fecha_compra >= %s")
            params.append(fecha_inicio)
        if fecha_fin:
            where.append("fecha_compra <= %s")
            params.append(fecha_fin)

        cursor.execute(
            f"""
            SELECT numero_transaccion,
                   tipo,
                   CASE
                     WHEN SUM(estado = 'ABIERTA') > 0 THEN 'ABIERTA'
                     WHEN SUM(estado = 'APLICADA') > 0 THEN 'APLICADA'
                     ELSE 'CERRADA'
                   END AS estado,
                   MAX(proveedor) AS proveedor,
                   MIN(fecha_compra) AS fecha_compra,
                   COUNT(*) AS num_lineas,
                   COUNT(DISTINCT numero_parte_sistema) AS num_partes,
                   SUM(COALESCE(costo_total, 0)) AS total_monto
            FROM lista_compras_lineas
            WHERE {' AND '.join(where)}
            GROUP BY tipo, numero_transaccion
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


def get_transaccion_detail(numero_transaccion, tipo=None):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        numero = sanitizar_texto(numero_transaccion, 255)
        tipo_normalizado = _normalizar_tipo(tipo) if tipo else None
        if tipo and not tipo_normalizado:
            return {"success": False, "error": "tipo invalido (LG u OVEN)."}, 400
        where_tipo = " AND l.tipo = %s" if tipo_normalizado else ""
        params = [numero]
        if tipo_normalizado:
            params.append(tipo_normalizado)
        # Incluye cuánto se ha recibido (aplicado) vs comprado, y el estado por
        # parte (ABIERTA pendiente / APLICADA llena / CERRADA histórico).
        cursor.execute(
            f"""
            SELECT l.*,
                   COALESCE(ll.aplicado, 0) AS aplicado,
                   GREATEST(l.cantidad - COALESCE(ll.aplicado, 0), 0) AS pendiente
            FROM lista_compras_lineas l
            LEFT JOIN (
                SELECT transaccion_linea_id, SUM(cantidad_aplicada) AS aplicado
                FROM lista_compras_lot_links
                WHERE estado = 'APLICADO'
                GROUP BY transaccion_linea_id
            ) ll ON ll.transaccion_linea_id = l.id
            WHERE l.numero_transaccion = %s
              {where_tipo}
            ORDER BY l.id ASC
            """,
            params,
        )
        lineas = [row_to_json(r) for r in (cursor.fetchall() or [])]
        if not lineas:
            return {"success": False, "error": "Transaccion no encontrada."}, 404

        tipos = {line.get("tipo") for line in lineas}
        if not tipo_normalizado and len(tipos) > 1:
            return {
                "success": False,
                "error": "La transaccion existe en LG y OVEN; especifica el tipo.",
            }, 409
        resolved_tipo = tipo_normalizado or next(iter(tipos))

        cursor.execute(
            """
            SELECT ll.*, l.raw_part_num, l.descripcion
            FROM lista_compras_lot_links ll
            INNER JOIN lista_compras_lineas l ON l.id = ll.transaccion_linea_id
            WHERE l.numero_transaccion = %s AND l.tipo = %s
            ORDER BY ll.fecha_aplicacion DESC, ll.id DESC
            LIMIT 500
            """,
            (numero, resolved_tipo),
        )
        links = [row_to_json(r) for r in (cursor.fetchall() or [])]
        estados = {line.get("estado") for line in lineas}
        estado = (
            "ABIERTA"
            if "ABIERTA" in estados
            else "APLICADA"
            if "APLICADA" in estados
            else "CERRADA"
        )
        transaccion = {
            "numero_transaccion": numero,
            "tipo": resolved_tipo,
            "estado": estado,
            "cerrada": estado == "CERRADA",
        }
        return {
            "success": True,
            "numero_transaccion": numero,
            "tipo": resolved_tipo,
            "transaccion": transaccion,
            "lineas": lineas,
            "links": links,
        }, 200
    except Exception as exc:
        logger.exception("Error obteniendo transaccion: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def set_transaccion_closed(numero_transaccion, tipo, cerrado):
    """Cierra o reabre una transacción sin alterar sus vínculos de lote."""
    conn, cursor, error = _db()
    if error:
        return error
    try:
        numero = sanitizar_texto(numero_transaccion, 255)
        tipo_normalizado = _normalizar_tipo(tipo)
        if not numero or not tipo_normalizado:
            return {
                "success": False,
                "error": "numero_transaccion y tipo (LG u OVEN) son requeridos.",
            }, 400

        cursor.execute(
            """
            SELECT id FROM lista_compras_lineas
            WHERE numero_transaccion = %s AND tipo = %s
            LIMIT 1
            """,
            (numero, tipo_normalizado),
        )
        if not cursor.fetchone():
            return {"success": False, "error": "Transaccion no encontrada."}, 404

        if cerrado:
            cursor.execute(
                """
                UPDATE lista_compras_lineas
                SET estado = 'CERRADA'
                WHERE numero_transaccion = %s AND tipo = %s
                """,
                (numero, tipo_normalizado),
            )
            estado = "CERRADA"
        else:
            # Al reabrir, las líneas completas recuperan APLICADA y las que aún
            # tienen pendiente vuelven a ABIERTA.
            cursor.execute(
                """
                UPDATE lista_compras_lineas l
                LEFT JOIN (
                    SELECT transaccion_linea_id, SUM(cantidad_aplicada) AS aplicado
                    FROM lista_compras_lot_links
                    WHERE estado = 'APLICADO'
                    GROUP BY transaccion_linea_id
                ) links ON links.transaccion_linea_id = l.id
                SET l.estado = CASE
                    WHEN COALESCE(links.aplicado, 0) >= l.cantidad THEN 'APLICADA'
                    ELSE 'ABIERTA'
                END
                WHERE l.numero_transaccion = %s AND l.tipo = %s
                """,
                (numero, tipo_normalizado),
            )
            estado = "ABIERTA"
        conn.commit()
        return {
            "success": True,
            "numero_transaccion": numero,
            "tipo": tipo_normalizado,
            "cerrada": bool(cerrado),
            "estado": estado,
        }, 200
    except Exception as exc:
        conn.rollback()
        logger.exception("Error cerrando transaccion %s/%s: %s", tipo, numero_transaccion, exc)
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


def estado_carga_inicial(args):
    """Indica, por tipo, si ya se hizo la carga inicial (para bloquear el botón)."""
    conn, cursor, error = _db()
    if error:
        return error
    try:
        cursor.execute(
            """
            SELECT tipo, COUNT(*) AS cargas
            FROM lista_compras_cargas
            WHERE modo = 'INICIAL'
            GROUP BY tipo
            """
        )
        hechas = {row["tipo"] for row in (cursor.fetchall() or [])}
        return (
            {
                "success": True,
                "inicial_hecha": {t: (t in hechas) for t in TIPOS_VALIDOS},
            },
            200,
        )
    except Exception as exc:
        logger.exception("Error consultando estado carga inicial: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()
