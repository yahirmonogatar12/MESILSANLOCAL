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
from app.api.control_material.costing_core.resolver import recalculate_lot_cost
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
    # SINCRONIZACION = espeja el Excel: agrega, actualiza y borra renglones.
    modo = sanitizar_texto(value, 20).upper()
    return modo if modo in ("INICIAL", "SINCRONIZACION") else "ACTUALIZACION"


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
    select_columns = ", ".join(("id", "estado", *_LINE_IDENTITY_COLUMNS))

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


def _lineas_por_parte(cursor, tipo, lineas, claves_archivo):
    """Renglones del mismo tipo y parte en OTRAS transacciones.

    Son los candidatos a "cambio de numero de transaccion": el archivo ya no
    menciona la transaccion vieja, asi que _existing_lines nunca la traeria.
    ponytail: raw_part_num no esta indexado, es un scan; con decenas de miles de
    renglones habria que agregar KEY (tipo, raw_part_num).
    """
    partes = sorted({(l.get("raw_part_num") or l.get("numero_parte") or "") for l in lineas})
    partes = [parte for parte in partes if parte]
    if not partes:
        return []
    rows_by_id = {}
    select_columns = ", ".join(("id", "estado", *_LINE_IDENTITY_COLUMNS))
    for chunk in _chunks(partes):
        placeholders = ", ".join(["%s"] * len(chunk))
        cursor.execute(
            f"""
            SELECT {select_columns}
            FROM lista_compras_lineas
            WHERE tipo = %s AND raw_part_num IN ({placeholders})
            """,
            [tipo, *chunk],
        )
        for row in cursor.fetchall() or []:
            if _transaction_key(row["numero_transaccion"]) in claves_archivo:
                continue  # esa transaccion si viene en el archivo: ya se compara aparte
            rows_by_id[row["id"]] = row
    return list(rows_by_id.values())


def _line_key(row):
    """Clave de negocio de un renglón: transacción + parte del Excel."""
    return (
        _transaction_key(row.get("numero_transaccion")),
        _text_key(row.get("raw_part_num") or row.get("numero_parte")),
    )


def _lineas_con_lote(cursor, line_ids):
    """Ids de línea que tienen algún lote APLICADO (no se tocan ni se borran)."""
    con_lote = set()
    for chunk in _chunks(sorted(line_ids)):
        placeholders = ", ".join(["%s"] * len(chunk))
        cursor.execute(
            f"""
            SELECT DISTINCT transaccion_linea_id
            FROM lista_compras_lot_links
            WHERE estado = 'APLICADO' AND transaccion_linea_id IN ({placeholders})
            """,
            chunk,
        )
        con_lote.update(row["transaccion_linea_id"] for row in (cursor.fetchall() or []))
    return con_lote


def _sync_plan(cursor, tipo, lineas):
    """Compara el Excel contra la BD y arma el plan de sincronización.

    Sólo se comparan las transacciones que trae el archivo: un Excel semanal no
    puede borrar transacciones que ni siquiera menciona. Bloquea los renglones
    con lote aplicado y protege el histórico CERRADO de la carga inicial.
    """
    existing_rows = _existing_lines(cursor, tipo, lineas)
    db_por_clave = {}
    for row in existing_rows:
        db_por_clave.setdefault(_line_key(row), []).append(row)
    excel_por_clave = {}
    for line in lineas:
        excel_por_clave.setdefault(_line_key(line), []).append(line)

    plan = {
        "nuevas": [],
        "modificadas": [],  # (row_id, linea)
        "renombradas": [],  # (row_id, linea, transaccion_anterior)
        "faltantes": [],
        "sin_cambio": 0,
        "bloqueadas": [],  # tienen lote aplicado
        "protegidas": [],  # histórico CERRADO
        "ambiguas": [],  # la misma parte repetida: no se puede parear 1 a 1
    }
    candidatos = {}  # row_id -> row, para consultar lotes de una sola vez

    for clave, filas_excel in excel_por_clave.items():
        filas_db = db_por_clave.get(clave) or []
        if not filas_db:
            plan["nuevas"].extend(filas_excel)
            continue
        if len(filas_excel) > 1 or len(filas_db) > 1:
            plan["ambiguas"].append({"transaccion": filas_db[0]["numero_transaccion"],
                                     "parte": filas_db[0].get("raw_part_num")})
            continue
        fila_db, linea = filas_db[0], filas_excel[0]
        if _line_signature(fila_db) == _line_signature(linea):
            plan["sin_cambio"] += 1
            continue
        candidatos[fila_db["id"]] = ("modificadas", fila_db, linea)

    faltantes_db = [
        fila_db
        for clave, filas_db in db_por_clave.items()
        if clave not in excel_por_clave
        for fila_db in filas_db
    ]
    claves_archivo = {clave[0] for clave in excel_por_clave}
    _detectar_renombres(
        plan, faltantes_db, _lineas_por_parte(cursor, tipo, plan["nuevas"], claves_archivo)
    )
    for fila_db in faltantes_db:
        candidatos[fila_db["id"]] = ("faltantes", fila_db, None)

    con_lote = _lineas_con_lote(cursor, candidatos) if candidatos else set()
    for row_id, (destino, fila_db, linea) in candidatos.items():
        if row_id in con_lote:
            plan["bloqueadas"].append({**_resumen_fila(fila_db), "motivo": "lote aplicado"})
            continue
        if fila_db.get("estado") == "CERRADA":
            plan["protegidas"].append({**_resumen_fila(fila_db), "motivo": "histórico (carga inicial)"})
            continue
        if destino == "modificadas":
            plan["modificadas"].append((row_id, linea))
        else:
            plan["faltantes"].append(fila_db)
    return plan


def _detectar_renombres(plan, faltantes_db, otros_candidatos=()):
    """Cambio de numero de transaccion: mismo renglon, otro numero.

    Un renglon que desaparece y otro identico que aparece con distinto numero de
    transaccion es la misma compra recapturada. En vez de borrar e insertar, la
    linea conserva su id y sus lotes vinculados viajan con ella (se actualiza el
    numero en los links), asi que el material no se desaplica ni hay que volver
    a asignarlo. Solo cuando el pareo es 1 a 1: con duplicados no se adivina.
    """
    def sin_transaccion(row):
        return _line_signature(row)[1:]

    pendientes = {}
    for fila_db in (*faltantes_db, *otros_candidatos):
        pendientes.setdefault(sin_transaccion(fila_db), []).append(fila_db)
    entrantes = {}
    for linea in plan["nuevas"]:
        entrantes.setdefault(sin_transaccion(linea), []).append(linea)

    for firma, filas_db in pendientes.items():
        candidatas = entrantes.get(firma) or []
        if len(filas_db) != 1 or len(candidatas) != 1:
            continue
        fila_db, linea = filas_db[0], candidatas[0]
        plan["renombradas"].append((fila_db["id"], linea, fila_db["numero_transaccion"]))
        if fila_db in faltantes_db:
            faltantes_db.remove(fila_db)
        plan["nuevas"].remove(linea)


def _rename_lineas(cursor, carga_id, renombradas):
    """Mueve el renglon (y sus lotes vinculados) al nuevo numero de transaccion."""
    for row_id, linea, _anterior in renombradas:
        cursor.execute(
            "UPDATE lista_compras_lineas SET numero_transaccion = %s, carga_id = %s WHERE id = %s",
            (linea["numero_transaccion"], carga_id, row_id),
        )
        cursor.execute(
            "UPDATE lista_compras_lot_links SET numero_transaccion = %s WHERE transaccion_linea_id = %s",
            (linea["numero_transaccion"], row_id),
        )


def _resumen_fila(row):
    return {
        "id": row.get("id"),
        "numero_transaccion": row.get("numero_transaccion"),
        "numero_parte": row.get("raw_part_num"),
        "cantidad": row.get("cantidad"),
        "costo_total": row.get("costo_total"),
    }


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
    sync = None
    if not db_error:
        try:
            if modo == "SINCRONIZACION":
                plan = _sync_plan(cursor, tipo, lineas)
                sample_lines = plan["nuevas"]
                lineas_nuevas = len(plan["nuevas"])
                lineas_existentes = plan["sin_cambio"]
                nuevas = len({_transaction_key(l["numero_transaccion"]) for l in plan["nuevas"]})
                existentes = len(transaction_keys) - nuevas
                sync = {
                    "modificadas": len(plan["modificadas"]),
                    "renombradas": len(plan["renombradas"]),
                    "renombradas_muestra": [
                        {
                            "anterior": anterior,
                            "nueva": linea["numero_transaccion"],
                            "numero_parte": linea.get("raw_part_num"),
                        }
                        for _id, linea, anterior in plan["renombradas"][:20]
                    ],
                    "faltantes": len(plan["faltantes"]),
                    "sin_cambio": plan["sin_cambio"],
                    "bloqueadas": plan["bloqueadas"][:20],
                    "protegidas": plan["protegidas"][:20],
                    "ambiguas": plan["ambiguas"][:20],
                    "faltantes_muestra": [
                        row_to_json(_resumen_fila(row)) for row in plan["faltantes"][:20]
                    ],
                }
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
            "sync": sync,
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

        plan = None
        if modo == "INICIAL":
            lineas_a_insertar = lineas
            estado_lineas = "CERRADA"
        elif modo == "SINCRONIZACION":
            # Espeja el Excel dentro de las transacciones que trae el archivo.
            plan = _sync_plan(cursor, tipo, lineas)
            lineas_a_insertar = plan["nuevas"]
            estado_lineas = "ABIERTA"
            if not (plan["nuevas"] or plan["modificadas"] or plan["faltantes"] or plan["renombradas"]):
                return (
                    {
                        "success": True,
                        "carga_id": None,
                        "tipo": tipo,
                        "modo": modo,
                        "total_lineas": 0,
                        "agregadas": 0,
                        "modificadas": 0,
                        "borradas": 0,
                        "bloqueadas": len(plan["bloqueadas"]),
                        "protegidas": len(plan["protegidas"]),
                        "message": "El Excel ya coincide con lo registrado.",
                    },
                    200,
                )
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
        # En SINCRONIZACION la carga documenta todo lo tocado, no sólo lo insertado.
        lineas_afectadas = (
            lineas_a_insertar
            + [linea for _, linea in plan["modificadas"]]
            + [linea for _id, linea, _anterior in plan["renombradas"]]
            if plan
            else lineas_a_insertar
        )
        transacciones = {
            _transaction_key(l["numero_transaccion"]) for l in lineas_afectadas
        }
        total_monto = sum((l.get("costo_total") or Decimal("0")) for l in lineas_afectadas)

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
                len(lineas_afectadas),
                str(total_monto),
                usuario,
                fecha,
            ),
        )
        carga_id = cursor.lastrowid

        if lineas_a_insertar:
            _insert_lineas(cursor, carga_id, tipo, lineas_a_insertar, estado_lineas)
        if plan:
            _update_lineas(cursor, carga_id, plan["modificadas"])
            _rename_lineas(cursor, carga_id, plan["renombradas"])
            _delete_lineas(cursor, [row["id"] for row in plan["faltantes"]])
        conn.commit()
        respuesta = {
            "success": True,
            "carga_id": carga_id,
            "tipo": tipo,
            "modo": modo,
            "total_lineas": len(lineas_a_insertar),
            "total_transacciones": len(transacciones),
            "estado_lineas": estado_lineas,
        }
        if plan:
            respuesta.update(
                {
                    "agregadas": len(plan["nuevas"]),
                    "modificadas": len(plan["modificadas"]),
                    "renombradas": len(plan["renombradas"]),
                    "borradas": len(plan["faltantes"]),
                    "bloqueadas": len(plan["bloqueadas"]),
                    "protegidas": len(plan["protegidas"]),
                    "ambiguas": len(plan["ambiguas"]),
                }
            )
        return respuesta, 201
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


_SYNC_UPDATE_COLUMNS = (
    "anio", "mes", "fecha_compra", "wk", "raw_part_num", "numero_parte",
    "numero_parte_sistema", "descripcion", "spec", "cantidad", "moneda",
    "costo_unitario", "costo_total", "fecha_factura", "proveedor", "factura",
    "modelo", "categoria", "comentario", "estado_match", "mensaje_match",
)


def _sync_valor(linea, columna):
    valor = linea.get(columna)
    if columna in ("cantidad", "costo_unitario", "costo_total"):
        return None if valor is None else str(valor)
    if columna == "moneda":
        return valor or "USD"
    if columna == "estado_match":
        return valor or "SIN_ALIAS"
    return valor


def _update_lineas(cursor, carga_id, modificadas):
    """Reescribe los datos del renglón y lo reapunta a la carga que lo cambió."""
    if not modificadas:
        return
    sets = ", ".join(f"{columna} = %s" for columna in _SYNC_UPDATE_COLUMNS)
    cursor.executemany(
        f"UPDATE lista_compras_lineas SET carga_id = %s, {sets} WHERE id = %s",
        [
            (
                carga_id,
                *[_sync_valor(linea, columna) for columna in _SYNC_UPDATE_COLUMNS],
                row_id,
            )
            for row_id, linea in modificadas
        ],
    )


def _delete_lineas(cursor, ids):
    """Borra renglones y sus links DESAPLICADOS (los APLICADOS ya se filtraron)."""
    for chunk in _chunks(sorted(ids)):
        placeholders = ", ".join(["%s"] * len(chunk))
        cursor.execute(
            f"DELETE FROM lista_compras_lot_links WHERE transaccion_linea_id IN ({placeholders})",
            chunk,
        )
        cursor.execute(
            f"DELETE FROM lista_compras_lineas WHERE id IN ({placeholders})", chunk
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


def _recalcular_estado_lineas(cursor, numero, tipo):
    """Deja cada linea en APLICADA (llena) o ABIERTA (con pendiente).

    Las CERRADAS son historico de la carga inicial y no vuelven al almacen por
    desaplicar un lote, asi que quedan intactas.
    """
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
        WHERE l.numero_transaccion = %s AND l.tipo = %s AND l.estado <> 'CERRADA'
        """,
        (numero, tipo),
    )


def _transaccion_valida(cursor, numero_transaccion, tipo):
    """(numero, tipo, error) normalizados; error ya viene como (payload, status)."""
    numero = sanitizar_texto(numero_transaccion, 255)
    tipo_normalizado = _normalizar_tipo(tipo)
    if not numero or not tipo_normalizado:
        return None, None, (
            {"success": False, "error": "numero_transaccion y tipo (LG u OVEN) son requeridos."},
            400,
        )
    cursor.execute(
        "SELECT id FROM lista_compras_lineas WHERE numero_transaccion = %s AND tipo = %s LIMIT 1",
        (numero, tipo_normalizado),
    )
    if not cursor.fetchone():
        return None, None, ({"success": False, "error": "Transaccion no encontrada."}, 404)
    return numero, tipo_normalizado, None


def unapply_transaccion(numero_transaccion, tipo, data=None):
    """Desaplica lotes de una transaccion (espejo de unapply_invoice).

    Los vinculos los crea otro proyecto en la entrada de almacen; aqui solo se
    revierten: el lote deja de costearse desde esta compra y la linea vuelve a
    quedar abierta por la cantidad liberada.
    """
    data = data or {}
    conn, cursor, error = _db()
    if error:
        return error
    try:
        cursor.execute("START TRANSACTION")
        numero, tipo_normalizado, error = _transaccion_valida(cursor, numero_transaccion, tipo)
        if error:
            conn.rollback()
            return error

        motivo = sanitizar_texto(data.get("motivo_desaplicado") or data.get("motivo"), 255)
        link_ids = [
            int(value)
            for value in (data.get("link_ids") if isinstance(data.get("link_ids"), list) else [])
            if str(value).isdigit()
        ]
        codigo = sanitizar_texto(data.get("codigo_material_recibido"), 255)
        where = ["numero_transaccion = %s", "tipo = %s", "estado = 'APLICADO'"]
        params = [numero, tipo_normalizado]
        if link_ids:
            where.append(f"id IN ({', '.join(['%s'] * len(link_ids))})")
            params.extend(link_ids)
        if codigo:
            where.append("codigo_material_recibido = %s")
            params.append(codigo)

        cursor.execute(
            f"""
            SELECT id, codigo_material_recibido
            FROM lista_compras_lot_links
            WHERE {' AND '.join(where)}
            ORDER BY fecha_aplicacion ASC, id ASC
            FOR UPDATE
            """,
            params,
        )
        links = cursor.fetchall() or []
        if not links:
            conn.rollback()
            return {"success": True, "links_desaplicados": 0, "message": "No hay lotes aplicados que desaplicar."}, 200

        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()
        cursor.execute(
            f"""
            UPDATE lista_compras_lot_links
            SET estado = 'DESAPLICADO',
                fecha_desaplicado = %s,
                usuario_desaplicado = %s,
                motivo_desaplicado = %s
            WHERE id IN ({', '.join(['%s'] * len(links))})
            """,
            [fecha, usuario, motivo or None, *[link["id"] for link in links]],
        )
        _recalcular_estado_lineas(cursor, numero, tipo_normalizado)
        recalculados = sum(
            1
            for codigo_lote in {link["codigo_material_recibido"] for link in links}
            if recalculate_lot_cost(cursor, codigo_lote, usuario)
        )
        conn.commit()
        return {
            "success": True,
            "numero_transaccion": numero,
            "tipo": tipo_normalizado,
            "links_desaplicados": len(links),
            "lotes_recalculados": recalculados,
        }, 200
    except Exception as exc:
        conn.rollback()
        logger.exception("Error desaplicando compras %s/%s: %s", tipo, numero_transaccion, exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def reapply_transaccion(numero_transaccion, tipo, data=None):
    """Reaplica los lotes desaplicados de una transaccion.

    Un lote solo puede tener una compra activa (uk_lcll_activo), asi que los
    lotes que ya fueron aplicados a otra transaccion se omiten y se reportan.
    """
    data = data or {}
    conn, cursor, error = _db()
    if error:
        return error
    try:
        cursor.execute("START TRANSACTION")
        numero, tipo_normalizado, error = _transaccion_valida(cursor, numero_transaccion, tipo)
        if error:
            conn.rollback()
            return error

        link_ids = [
            int(value)
            for value in (data.get("link_ids") if isinstance(data.get("link_ids"), list) else [])
            if str(value).isdigit()
        ]
        where = ["numero_transaccion = %s", "tipo = %s", "estado = 'DESAPLICADO'"]
        params = [numero, tipo_normalizado]
        if link_ids:
            where.append(f"id IN ({', '.join(['%s'] * len(link_ids))})")
            params.extend(link_ids)

        cursor.execute(
            f"""
            SELECT id, codigo_material_recibido
            FROM lista_compras_lot_links
            WHERE {' AND '.join(where)}
            ORDER BY fecha_aplicacion ASC, id ASC
            FOR UPDATE
            """,
            params,
        )
        links = cursor.fetchall() or []
        reaplicados, omitidos = [], []
        usuario = _usuario_actual()
        for link in links:
            cursor.execute(
                """
                SELECT id FROM lista_compras_lot_links
                WHERE codigo_material_recibido = %s AND estado = 'APLICADO'
                LIMIT 1
                """,
                (link["codigo_material_recibido"],),
            )
            if cursor.fetchone():
                omitidos.append(link["codigo_material_recibido"])
                continue
            cursor.execute(
                """
                UPDATE lista_compras_lot_links
                SET estado = 'APLICADO',
                    fecha_desaplicado = NULL,
                    usuario_desaplicado = NULL,
                    motivo_desaplicado = NULL
                WHERE id = %s AND estado = 'DESAPLICADO'
                """,
                (link["id"],),
            )
            reaplicados.append(link["codigo_material_recibido"])

        if reaplicados:
            _recalcular_estado_lineas(cursor, numero, tipo_normalizado)
            for codigo_lote in set(reaplicados):
                recalculate_lot_cost(cursor, codigo_lote, usuario)
        conn.commit()
        return {
            "success": True,
            "numero_transaccion": numero,
            "tipo": tipo_normalizado,
            "links_reaplicados": len(reaplicados),
            "omitidos": omitidos[:50],
        }, 200
    except Exception as exc:
        conn.rollback()
        logger.exception("Error reaplicando compras %s/%s: %s", tipo, numero_transaccion, exc)
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
    """Borra una carga solo si sus lineas NO tienen lotes APLICADOS.

    Un link APLICADO es un lote ya costeado desde esta compra; borrarla rompería
    la trazabilidad del costo. Para corregir una transacción primero hay que
    desaplicar el lote, borrar/re-subir, y luego reaplicarlo. Los DESAPLICADO son
    histórico inerte y se limpian junto con la carga (espejo de delete_invoice).
    """
    conn, cursor, error = _db()
    if error:
        return error
    try:
        cursor.execute("START TRANSACTION")
        cursor.execute(
            "SELECT archivo_ruta FROM lista_compras_cargas WHERE id = %s LIMIT 1 FOR UPDATE",
            (carga_id,),
        )
        carga = cursor.fetchone()
        if not carga:
            conn.rollback()
            return {"success": False, "error": "Carga no encontrada."}, 404

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM lista_compras_lot_links ll
            INNER JOIN lista_compras_lineas l ON l.id = ll.transaccion_linea_id
            WHERE l.carga_id = %s AND ll.estado = 'APLICADO'
            """,
            (carga_id,),
        )
        links_activos = int((cursor.fetchone() or {}).get("total") or 0)
        if links_activos:
            conn.rollback()
            return (
                {
                    "success": False,
                    "error": (
                        "No se puede eliminar: la carga tiene "
                        f"{links_activos} lote(s) APLICADOS a sus transacciones. "
                        "Desaplica primero y reaplica despues."
                    ),
                    "links": links_activos,
                },
                409,
            )

        cursor.execute(
            """
            DELETE ll FROM lista_compras_lot_links ll
            INNER JOIN lista_compras_lineas l ON l.id = ll.transaccion_linea_id
            WHERE l.carga_id = %s
            """,
            (carga_id,),
        )
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
