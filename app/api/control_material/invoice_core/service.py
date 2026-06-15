"""Casos de uso transaccionales para invoices de material."""

import hashlib
import logging
import os
import re
import unicodedata
from decimal import Decimal
from io import BytesIO

from flask import session
from werkzeug.utils import secure_filename

from app.api.control_material.costing_core.resolver import (
    fetch_lot_row,
    recalculate_lot_cost,
    upsert_inventory_cost,
)
from app.api.control_material.invoice_core.constants import (
    ERROR_INTERNO,
    ESTADOS_INVOICE,
    MONEDA_DEFAULT,
)
from app.api.control_material.invoice_core.matcher import (
    assign_packing_lines,
    invoice_has_differences,
    validate_system_parts,
)
from app.api.control_material.invoice_core.normalizers import (
    decimal_or_zero,
    normalizar_numero_parte,
    normalizar_pallet_no,
    raw_text,
    row_to_json,
)
from app.api.control_material.invoice_core.parser import parse_invoice_workbook
from app.api.control_material.invoice_core.repository import (
    candidate_lots_for_packing,
    fetch_invoice,
    packing_available_locked,
    recalculate_invoice_state,
    recalculate_packing_state,
)
from app.api.control_material.invoice_core.storage import (
    absolute_path,
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


def _usuario_actual():
    return session.get("usuario") or "SISTEMA"


def _db():
    conn, error_response = conexion_o_error()
    if error_response:
        return None, None, ({"success": False, "error": "Base de datos no disponible"}, 503)
    return conn, dict_cursor(conn), None


def list_invoices(args):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        q = sanitizar_texto(args.get("q"), 120)
        estado = sanitizar_texto(args.get("estado"), 40).upper()
        params = []
        where = ["1=1"]
        if q:
            where.append("(mi.numero_invoice LIKE %s OR COALESCE(mi.tipo, '') LIKE %s OR mi.archivo_nombre LIKE %s)")
            like = f"%{q}%"
            params.extend([like, like, like])
        if estado in ESTADOS_INVOICE:
            where.append("mi.estado = %s")
            params.append(estado)

        cursor.execute(
            f"""
            SELECT mi.*,
                   COALESCE(active_links.links_activos, 0) AS links_activos
            FROM material_invoices mi
            LEFT JOIN (
                SELECT invoice_id, COUNT(*) AS links_activos
                FROM material_invoice_lot_links
                WHERE estado = 'APLICADO'
                GROUP BY invoice_id
            ) active_links ON active_links.invoice_id = mi.id
            WHERE {' AND '.join(where)}
            ORDER BY mi.fecha_carga DESC, mi.id DESC
            LIMIT 300
            """,
            params,
        )
        records = [row_to_json(r) for r in (cursor.fetchall() or [])]
        return {"success": True, "records": records, "total": len(records)}, 200
    except Exception as exc:
        logger.exception("Error listando invoices: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def preview_invoice(files, form):
    """Parsea el Excel y devuelve lo que se cargaria, sin tocar la BD de invoices.

    Valida las partes contra materiales (UOM y existencia) y detecta si la
    invoice ya esta cargada (por numero o por hash), para mostrarlo en el modal.
    """
    uploaded = files.get("file") or files.get("archivo")
    if not uploaded:
        return {"success": False, "error": "Archivo requerido."}, 400

    filename = secure_filename(uploaded.filename or "invoice.xlsx")
    file_bytes = uploaded.read()
    if not file_bytes:
        return {"success": False, "error": "El archivo esta vacio."}, 400

    try:
        parsed = parse_invoice_workbook(file_bytes, filename)
    except Exception as exc:
        logger.exception("Error leyendo invoice (preview) desde %s: %s", filename, exc)
        return {"success": False, "error": "No se pudo leer el Excel de la invoice."}, 400

    numero_invoice = sanitizar_texto(
        form.get("numero_invoice") or parsed.get("numero_invoice_sugerido"),
        255,
    )
    if not parsed["invoice_lines"]:
        detail = " ".join(parsed.get("warnings") or [])
        message = "No se detectaron lineas de invoice en la hoja INVOICE(CONVERTED)."
        return {"success": False, "error": f"{message} {detail}".strip()}, 400

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    conn, cursor, error = _db()
    if error:
        return error
    try:
        # Valida partes contra materiales (UOM + existencia) sin persistir.
        validate_system_parts(cursor, parsed["invoice_lines"], "numero_parte_sistema", "DIRECTO")

        # Detecta duplicado por numero o por hash de archivo.
        duplicado = None
        cursor.execute("SELECT id FROM material_invoices WHERE numero_invoice = %s LIMIT 1", (numero_invoice,))
        row = cursor.fetchone()
        if row:
            duplicado = {"motivo": "NUMERO_INVOICE", "invoice_id": row["id"]}
        else:
            cursor.execute("SELECT id FROM material_invoices WHERE archivo_hash_sha256 = %s LIMIT 1", (file_hash,))
            row = cursor.fetchone()
            if row:
                duplicado = {"motivo": "ARCHIVO_HASH", "invoice_id": row["id"]}

        total_monto = sum((r.get("costo_total") or Decimal("0.0000")) for r in parsed["invoice_lines"])
        sin_parte = sum(1 for r in parsed["invoice_lines"] if r.get("estado_match") == "SIN_ALIAS")
        lines = [
            {
                "line_no": r.get("line_no"),
                "pallet_no": next(
                    (p.get("pallet_no") for p in parsed["packing_lines"] if p.get("line_no") == r.get("line_no")),
                    "",
                ),
                "raw_part_num": r.get("raw_part_num"),
                "numero_parte_sistema": r.get("numero_parte_sistema"),
                "descripcion": r.get("descripcion"),
                "cantidad": str(r.get("cantidad")),
                "uom": r.get("uom") or "",
                "costo_unitario": str(r.get("costo_unitario")),
                "costo_total": str(r.get("costo_total")),
                "estado_match": r.get("estado_match"),
            }
            for r in parsed["invoice_lines"]
        ]
        return (
            {
                "success": True,
                "numero_invoice": numero_invoice,
                "fuente_hoja": parsed.get("fuente_hoja"),
                "total_lineas": len(parsed["invoice_lines"]),
                "total_packing": len(parsed["packing_lines"]),
                "total_monto": str(total_monto),
                "partes_sin_sistema": sin_parte,
                "duplicado": duplicado,
                "warnings": parsed.get("warnings") or [],
                "lines": lines,
            },
            200,
        )
    except Exception as exc:
        logger.exception("Error en preview de invoice: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def upload_invoice(files, form):
    uploaded = files.get("file") or files.get("archivo")
    if not uploaded:
        return {"success": False, "error": "Archivo requerido."}, 400

    filename = secure_filename(uploaded.filename or "invoice.xlsx")
    file_bytes = uploaded.read()
    if not file_bytes:
        return {"success": False, "error": "El archivo esta vacio."}, 400

    try:
        parsed = parse_invoice_workbook(file_bytes, filename)
    except Exception as exc:
        logger.exception("Error leyendo invoice desde %s: %s", filename, exc)
        return {"success": False, "error": "No se pudo leer el Excel de la invoice."}, 400
    numero_invoice = sanitizar_texto(
        form.get("numero_invoice") or parsed.get("numero_invoice_sugerido"),
        255,
    )
    tipo = sanitizar_texto(form.get("tipo") or form.get("proveedor"), 255)
    if not numero_invoice:
        return {"success": False, "error": "numero_invoice requerido."}, 400
    if not parsed["invoice_lines"]:
        detail = " ".join(parsed.get("warnings") or [])
        message = "No se detectaron lineas de invoice en la hoja INVOICE(CONVERTED)."
        return {"success": False, "error": f"{message} {detail}".strip()}, 400

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    conn, cursor, error = _db()
    if error:
        return error
    archivo_ruta = None
    try:
        cursor.execute("SELECT id FROM material_invoices WHERE numero_invoice = %s LIMIT 1", (numero_invoice,))
        existing = cursor.fetchone()
        if existing:
            return (
                {
                    "success": False,
                    "duplicado": True,
                    "motivo": "NUMERO_INVOICE",
                    "invoice_id": existing["id"],
                    "message": "Esta invoice ya fue cargada.",
                },
                409,
            )

        cursor.execute("SELECT id FROM material_invoices WHERE archivo_hash_sha256 = %s LIMIT 1", (file_hash,))
        existing = cursor.fetchone()
        if existing:
            return (
                {
                    "success": False,
                    "duplicado": True,
                    "motivo": "ARCHIVO_HASH",
                    "invoice_id": existing["id"],
                    "message": "Este archivo parece ya cargado.",
                },
                409,
            )

        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()

        # Guarda el Excel original renombrado por numero de invoice y ordenado
        # por fecha (AAAA/MM). Se escribe antes del INSERT; si la transaccion
        # falla, el except borra el archivo huerfano.
        archivo_ruta = build_relative_path(numero_invoice, file_hash, fecha)
        _, archivo_size = save_file(file_bytes, archivo_ruta)

        cursor.execute("START TRANSACTION")
        # El Excel ya trae el numero de parte en sistema (Part Sys); solo se
        # valida su existencia en materiales (ya no se usa la tabla de aliases).
        # invoice_lines usa estado 'DIRECTO'; packing_lines usa 'MATCH' (ENUMs distintos).
        validate_system_parts(cursor, parsed["invoice_lines"], "numero_parte_sistema", "DIRECTO")
        validate_system_parts(cursor, parsed["packing_lines"], "numero_parte_sistema", "MATCH")

        total_monto = sum((r.get("costo_total") or Decimal("0.0000")) for r in parsed["invoice_lines"])
        cursor.execute(
            """
            INSERT INTO material_invoices (
                numero_invoice, tipo, archivo_nombre, archivo_ruta,
                archivo_size, archivo_mime, archivo_hash_sha256,
                estado, moneda, total_lineas, total_packing, total_monto,
                usuario_carga, fecha_carga
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'BORRADOR', %s, %s, %s, %s, %s, %s)
            """,
            (
                numero_invoice,
                tipo or None,
                filename,
                archivo_ruta,
                archivo_size,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                file_hash,
                MONEDA_DEFAULT,
                len(parsed["invoice_lines"]),
                len(parsed["packing_lines"]),
                str(total_monto),
                usuario,
                fecha,
            ),
        )
        invoice_id = cursor.lastrowid

        _insert_invoice_lines(cursor, invoice_id, parsed["invoice_lines"])
        _insert_packing_lines(cursor, invoice_id, parsed["packing_lines"])

        assign_packing_lines(cursor, invoice_id)
        estado = "CON_DIFERENCIAS" if invoice_has_differences(cursor, invoice_id) else "VALIDADA"
        cursor.execute(
            """
            UPDATE material_invoices
            SET estado = %s, usuario_validacion = %s, fecha_validacion = %s
            WHERE id = %s
            """,
            (estado, usuario, fecha, invoice_id),
        )
        conn.commit()
        return (
            {
                "success": True,
                "invoice_id": invoice_id,
                "estado": estado,
                "lineas": len(parsed["invoice_lines"]),
                "packing": len(parsed["packing_lines"]),
            },
            201,
        )
    except Exception as exc:
        conn.rollback()
        if archivo_ruta:
            delete_file(archivo_ruta)
        logger.exception("Error cargando invoice: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def _insert_invoice_lines(cursor, invoice_id, invoice_lines):
    if not invoice_lines:
        return
    # executemany en lote: el driver colapsa las filas en un INSERT multi-fila,
    # reduciendo los round-trips y acortando la ventana de la transaccion.
    params = [
        (
            invoice_id,
            line["line_no"],
            line.get("maker"),
            line.get("origin"),
            line.get("raw_part_num"),
            line["numero_parte_invoice"],
            line["numero_parte_sistema"],
            line.get("descripcion"),
            str(line["cantidad"]),
            line.get("uom"),
            str(line["costo_unitario"]),
            str(line["costo_total"]),
            line.get("moneda") or MONEDA_DEFAULT,
            line.get("raw_qty"),
            line.get("raw_unit_cost"),
            line.get("raw_total_cost"),
            line.get("estado_match") or "PENDIENTE",
            line.get("mensaje_match"),
        )
        for line in invoice_lines
    ]
    cursor.executemany(
        """
        INSERT INTO material_invoice_lines (
            invoice_id, line_no, maker, origin, raw_part_num,
            numero_parte_invoice, numero_parte_sistema, descripcion,
            cantidad, uom, costo_unitario, costo_total, moneda,
            raw_qty, raw_unit_cost, raw_total_cost, estado_match, mensaje_match
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        params,
    )


def _insert_packing_lines(cursor, invoice_id, packing_lines):
    if not packing_lines:
        return
    params = [
        (
            invoice_id,
            packing["line_no"],
            packing.get("packing_no"),
            packing.get("raw_part_num"),
            packing["numero_parte_packing"],
            packing["numero_parte_sistema"],
            packing.get("descripcion"),
            str(packing["cantidad_packing"]),
            packing.get("raw_qty"),
            packing.get("pallet_no_original"),
            packing.get("pallet_no"),
            str(packing["kg"]) if packing.get("kg") is not None else None,
            str(packing["cbm"]) if packing.get("cbm") is not None else None,
            packing.get("estado_match") or "PENDIENTE",
            packing.get("mensaje_match"),
        )
        for packing in packing_lines
    ]
    cursor.executemany(
        """
        INSERT INTO material_invoice_packing_lines (
            invoice_id, line_no, packing_no, raw_part_num,
            numero_parte_packing, numero_parte_sistema, descripcion,
            cantidad_packing, raw_qty, pallet_no_original, pallet_no,
            kg, cbm, estado_match, mensaje_match
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        params,
    )


def get_invoice_detail(invoice_id):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        invoice = fetch_invoice(cursor, invoice_id)
        if not invoice:
            return {"success": False, "error": "Invoice no encontrada."}, 404
        cursor.execute("SELECT * FROM material_invoice_lines WHERE invoice_id = %s ORDER BY line_no, id", (invoice_id,))
        lines = [row_to_json(r) for r in (cursor.fetchall() or [])]
        cursor.execute(
            """
            SELECT
              mipl.*,
              COALESCE(entradas.entradas_recibidas, 0) AS entradas_recibidas,
              COALESCE(entradas.cantidad_recibida, 0) AS cantidad_recibida,
              GREATEST(mipl.cantidad_packing - COALESCE(entradas.cantidad_recibida, 0), 0) AS cantidad_pendiente_entrada,
              COALESCE(aplicado.links_activos, 0) AS links_activos,
              COALESCE(aplicado.cantidad_aplicada_activa, 0) AS cantidad_aplicada_activa
            FROM material_invoice_packing_lines mipl
            LEFT JOIN (
                SELECT
                  cma.numero_invoice,
                  cma.pallet_no,
                  COALESCE(il.numero_parte, cma.numero_parte) AS numero_parte_sistema,
                  COUNT(DISTINCT cma.codigo_material_recibido) AS entradas_recibidas,
                  SUM(COALESCE(il.total_entrada, cma.cantidad_actual, 0)) AS cantidad_recibida
                FROM control_material_almacen cma
                LEFT JOIN inventario_lotes il
                  ON il.codigo_material_recibido = cma.codigo_material_recibido
                WHERE cma.numero_invoice = %s
                  AND (cma.cancelado = 0 OR cma.cancelado IS NULL)
                GROUP BY cma.numero_invoice, cma.pallet_no, COALESCE(il.numero_parte, cma.numero_parte)
            ) entradas
              ON entradas.numero_invoice = %s
             AND entradas.pallet_no = mipl.pallet_no
             AND entradas.numero_parte_sistema = mipl.numero_parte_sistema
            LEFT JOIN (
                SELECT
                  packing_line_id,
                  COUNT(*) AS links_activos,
                  SUM(cantidad_aplicada) AS cantidad_aplicada_activa
                FROM material_invoice_lot_links
                WHERE invoice_id = %s
                  AND estado = 'APLICADO'
                GROUP BY packing_line_id
            ) aplicado
              ON aplicado.packing_line_id = mipl.id
            WHERE mipl.invoice_id = %s
            ORDER BY
              CASE
                WHEN mipl.pallet_no REGEXP '^[0-9]+$' THEN CAST(mipl.pallet_no AS UNSIGNED)
                ELSE 999999
              END,
              mipl.pallet_no,
              mipl.line_no,
              mipl.id
            """,
            (invoice["numero_invoice"], invoice["numero_invoice"], invoice_id, invoice_id),
        )
        packing = [row_to_json(r) for r in (cursor.fetchall() or [])]
        cursor.execute(
            """
            SELECT *
            FROM material_invoice_lot_links
            WHERE invoice_id = %s
            ORDER BY fecha_aplicacion DESC, id DESC
            LIMIT 500
            """,
            (invoice_id,),
        )
        links = [row_to_json(r) for r in (cursor.fetchall() or [])]
        return {"success": True, "invoice": row_to_json(invoice), "lines": lines, "packing": packing, "links": links}, 200
    except Exception as exc:
        logger.exception("Error detalle invoice %s: %s", invoice_id, exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def get_invoice_candidates(invoice_id, args):
    packing_line_id = args.get("packing_line_id")
    conn, cursor, error = _db()
    if error:
        return error
    try:
        invoice = fetch_invoice(cursor, invoice_id)
        if not invoice:
            return {"success": False, "error": "Invoice no encontrada."}, 404

        params = [invoice["numero_invoice"]]
        where = ["cma.numero_invoice = %s", "(cma.cancelado = 0 OR cma.cancelado IS NULL)"]
        if packing_line_id:
            cursor.execute(
                "SELECT * FROM material_invoice_packing_lines WHERE id = %s AND invoice_id = %s",
                (packing_line_id, invoice_id),
            )
            packing = cursor.fetchone()
            if not packing:
                return {"success": False, "error": "Packing line no encontrada."}, 404
            where.append("cma.pallet_no = %s")
            where.append("cma.numero_parte = %s")
            params.extend([packing.get("pallet_no"), packing.get("numero_parte_sistema")])

        cursor.execute(
            f"""
            SELECT
              cma.codigo_material_recibido,
              cma.numero_parte,
              cma.numero_lote_material,
              cma.numero_invoice,
              cma.pallet_no_original,
              cma.pallet_no,
              cma.vendedor,
              cma.cantidad_actual,
              il.stock_actual,
              active.id AS active_link_id
            FROM control_material_almacen cma
            LEFT JOIN inventario_lotes il ON il.codigo_material_recibido = cma.codigo_material_recibido
            LEFT JOIN material_invoice_lot_links active
              ON active.codigo_material_recibido = cma.codigo_material_recibido
             AND active.estado = 'APLICADO'
            WHERE {' AND '.join(where)}
            ORDER BY cma.fecha_recibo ASC, cma.id ASC
            LIMIT 500
            """,
            params,
        )
        return {"success": True, "records": [row_to_json(r) for r in (cursor.fetchall() or [])]}, 200
    except Exception as exc:
        logger.exception("Error candidatos invoice %s: %s", invoice_id, exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def apply_invoice(invoice_id, data):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()
        cursor.execute("START TRANSACTION")
        invoice = fetch_invoice(cursor, invoice_id, for_update=True)
        if not invoice:
            conn.rollback()
            return {"success": False, "error": "Invoice no encontrada."}, 404
        if invoice.get("estado") == "CANCELADA":
            conn.rollback()
            return {"success": False, "error": "No se puede aplicar una invoice cancelada."}, 400

        applied, skipped = _apply_items_or_auto(cursor, invoice, data, usuario, fecha)
        estado = recalculate_invoice_state(cursor, invoice_id)
        conn.commit()
        return {
            "success": True,
            "estado": estado,
            "aplicados": len(applied),
            "omitidos": len(skipped),
            "applied": applied,
            "skipped": skipped[:50],
        }, 200
    except Exception as exc:
        conn.rollback()
        logger.exception("Error aplicando invoice %s: %s", invoice_id, exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def _apply_items_or_auto(cursor, invoice, data, usuario, fecha):
    items = data.get("items") if isinstance(data.get("items"), list) else None
    if not items:
        return _auto_apply_invoice(cursor, invoice, usuario, fecha)

    applied = []
    skipped = []
    for item in items:
        result = _apply_one_locked(cursor, invoice, item, usuario, fecha)
        (applied if result.get("success") else skipped).append(result)
    return applied, skipped


def _apply_one_locked(cursor, invoice, item, usuario, fecha):
    codigo = sanitizar_texto(item.get("codigo_material_recibido"), 255)
    packing_line_id = item.get("packing_line_id")
    if not codigo or not packing_line_id:
        return {"success": False, "codigo_material_recibido": codigo, "error": "codigo_material_recibido y packing_line_id son requeridos."}

    packing, _total_packing, available = packing_available_locked(cursor, packing_line_id)
    if not packing or int(packing["invoice_id"]) != int(invoice["id"]):
        return {"success": False, "codigo_material_recibido": codigo, "error": "Packing line no pertenece a la invoice."}
    if not packing.get("invoice_line_id") and not item.get("invoice_line_id"):
        return {"success": False, "codigo_material_recibido": codigo, "error": "Packing line no esta conciliada con invoice line."}

    invoice_line_id = item.get("invoice_line_id") or packing["invoice_line_id"]
    cursor.execute(
        """
        SELECT *
        FROM material_invoice_lines
        WHERE id = %s AND invoice_id = %s
        LIMIT 1
        FOR UPDATE
        """,
        (invoice_line_id, invoice["id"]),
    )
    line = cursor.fetchone()
    if not line:
        return {"success": False, "codigo_material_recibido": codigo, "error": "Invoice line no encontrada."}

    cursor.execute(
        """
        SELECT id, invoice_id
        FROM material_invoice_lot_links
        WHERE codigo_material_recibido = %s AND estado = 'APLICADO'
        FOR UPDATE
        """,
        (codigo,),
    )
    if cursor.fetchone():
        return {
            "success": False,
            "codigo_material_recibido": codigo,
            "error": "El lote ya tiene una invoice aplicada. Desaplica primero o usa reaplicacion explicita.",
        }

    lot = fetch_lot_row(cursor, codigo, for_update=True)
    if not lot:
        return {"success": False, "codigo_material_recibido": codigo, "error": "Lote no encontrado en control_material_almacen."}

    lot_pallet = normalizar_pallet_no(lot.get("pallet_no") or lot.get("pallet_no_original"))
    if lot.get("numero_invoice") != invoice.get("numero_invoice"):
        return {"success": False, "codigo_material_recibido": codigo, "error": "El numero_invoice del lote no coincide."}
    if lot_pallet != (packing.get("pallet_no") or ""):
        return {"success": False, "codigo_material_recibido": codigo, "error": "El pallet del lote no coincide."}
    if normalizar_numero_parte(lot.get("numero_parte_sistema")) != normalizar_numero_parte(packing.get("numero_parte_sistema")):
        return {"success": False, "codigo_material_recibido": codigo, "error": "La parte del lote no coincide."}

    cantidad = decimal_or_zero(item.get("cantidad_aplicada"))
    if cantidad <= 0:
        cantidad = decimal_or_zero(lot.get("cantidad_lote"))
    if cantidad <= 0:
        return {"success": False, "codigo_material_recibido": codigo, "error": "Cantidad aplicada invalida."}
    if cantidad > available:
        return {
            "success": False,
            "codigo_material_recibido": codigo,
            "error": "La cantidad del lote excede la cantidad packing disponible.",
            "cantidad_disponible": str(available),
        }

    cursor.execute(
        """
        INSERT INTO material_invoice_lot_links (
            invoice_id, invoice_line_id, packing_line_id, codigo_material_recibido,
            numero_parte_sistema, cantidad_aplicada, costo_unitario, moneda,
            usuario_aplicacion, fecha_aplicacion, usuario_registro, fecha_registro, estado
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'APLICADO')
        """,
        (
            invoice["id"],
            invoice_line_id,
            packing_line_id,
            codigo,
            line["numero_parte_sistema"],
            str(cantidad),
            str(line["costo_unitario"]),
            line.get("moneda") or MONEDA_DEFAULT,
            usuario,
            fecha,
            usuario,
            fecha,
        ),
    )
    link_id = cursor.lastrowid
    upsert_inventory_cost(
        cursor,
        lot,
        {
            "costo_unitario": Decimal(str(line["costo_unitario"])),
            "moneda": line.get("moneda") or MONEDA_DEFAULT,
            "fuente_costo": "INVOICE",
            "es_estimado": 0,
        },
        usuario,
        {
            "invoice_id": invoice["id"],
            "invoice_line_id": invoice_line_id,
            "packing_line_id": packing_line_id,
            "link_id": link_id,
        },
    )
    recalculate_packing_state(cursor, packing_line_id)
    return {"success": True, "codigo_material_recibido": codigo, "link_id": link_id, "cantidad_aplicada": str(cantidad)}


def _auto_apply_invoice(cursor, invoice, usuario, fecha):
    cursor.execute(
        """
        SELECT *
        FROM material_invoice_packing_lines
        WHERE invoice_id = %s
          AND invoice_line_id IS NOT NULL
          AND estado_match NOT IN ('SIN_ALIAS','SIN_LINEA','DIFERENCIA')
        ORDER BY pallet_no, line_no, id
        """,
        (invoice["id"],),
    )
    applied = []
    skipped = []
    for packing in cursor.fetchall() or []:
        for codigo in candidate_lots_for_packing(cursor, invoice, packing):
            result = _apply_one_locked(
                cursor,
                invoice,
                {
                    "codigo_material_recibido": codigo,
                    "packing_line_id": packing["id"],
                    "invoice_line_id": packing["invoice_line_id"],
                },
                usuario,
                fecha,
            )
            (applied if result.get("success") else skipped).append(result)
    return applied, skipped


def unapply_invoice(invoice_id, data):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()
        cursor.execute("START TRANSACTION")
        invoice = fetch_invoice(cursor, invoice_id, for_update=True)
        if not invoice:
            conn.rollback()
            return {"success": False, "error": "Invoice no encontrada."}, 404
        if invoice.get("estado") == "CANCELADA":
            conn.rollback()
            return {"success": False, "error": "No se puede desaplicar una invoice cancelada."}, 400

        result = _unapply_links_locked(cursor, invoice_id, data, usuario, fecha)
        estado = recalculate_invoice_state(cursor, invoice_id)
        conn.commit()
        result.update({"success": True, "estado": estado})
        return result, 200
    except Exception as exc:
        conn.rollback()
        logger.exception("Error desaplicando invoice %s: %s", invoice_id, exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def _unapply_links_locked(cursor, invoice_id, data, usuario, fecha):
    motivo = sanitizar_texto(data.get("motivo_desaplicado") or data.get("motivo"), 255)
    link_ids = data.get("link_ids") if isinstance(data.get("link_ids"), list) else []
    codigo = sanitizar_texto(data.get("codigo_material_recibido"), 255)

    params = [invoice_id]
    where = ["invoice_id = %s", "estado = 'APLICADO'"]
    if link_ids:
        placeholders = ", ".join(["%s"] * len(link_ids))
        where.append(f"id IN ({placeholders})")
        params.extend(link_ids)
    if codigo:
        where.append("codigo_material_recibido = %s")
        params.append(codigo)

    cursor.execute(
        f"""
        SELECT *
        FROM material_invoice_lot_links
        WHERE {' AND '.join(where)}
        ORDER BY fecha_aplicacion ASC, id ASC
        FOR UPDATE
        """,
        params,
    )
    links = cursor.fetchall() or []
    affected_codes = []
    packing_ids = set()
    for link in links:
        cursor.execute(
            """
            UPDATE material_invoice_lot_links
            SET estado = 'DESAPLICADO',
                fecha_desaplicado = %s,
                usuario_desaplicado = %s,
                motivo_desaplicado = %s
            WHERE id = %s AND estado = 'APLICADO'
            """,
            (fecha, usuario, motivo or None, link["id"]),
        )
        affected_codes.append((link["codigo_material_recibido"], link["fecha_aplicacion"], link["id"]))
        if link.get("packing_line_id"):
            packing_ids.add(link["packing_line_id"])

    recalculated = 0
    skipped_later = 0
    for codigo_lote, old_fecha, old_id in affected_codes:
        cursor.execute(
            """
            SELECT id
            FROM material_invoice_lot_links
            WHERE codigo_material_recibido = %s
              AND estado = 'APLICADO'
              AND (
                fecha_aplicacion > %s
                OR (fecha_aplicacion = %s AND id > %s)
              )
            ORDER BY fecha_aplicacion DESC, id DESC
            LIMIT 1
            """,
            (codigo_lote, old_fecha, old_fecha, old_id),
        )
        if cursor.fetchone():
            skipped_later += 1
            continue
        if recalculate_lot_cost(cursor, codigo_lote, usuario):
            recalculated += 1

    for packing_id in packing_ids:
        recalculate_packing_state(cursor, packing_id)

    return {
        "links_desaplicados": len(links),
        "lotes_recalculados": recalculated,
        "lotes_omitidos_por_reaplicacion_posterior": skipped_later,
    }


def reapply_invoice(invoice_id, data):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()
        cursor.execute("START TRANSACTION")
        invoice = fetch_invoice(cursor, invoice_id, for_update=True)
        if not invoice:
            conn.rollback()
            return {"success": False, "error": "Invoice no encontrada."}, 404
        if invoice.get("estado") == "CANCELADA":
            conn.rollback()
            return {"success": False, "error": "No se puede reaplicar una invoice cancelada."}, 400

        unapply_result = _unapply_links_locked(
            cursor,
            invoice_id,
            {"motivo": data.get("motivo") or "Reaplicacion explicita"},
            usuario,
            fecha,
        )
        applied, skipped = _apply_items_or_auto(cursor, invoice, data, usuario, fecha)
        estado = recalculate_invoice_state(cursor, invoice_id)
        conn.commit()
        return {
            "success": True,
            "estado": estado,
            "unapply": unapply_result,
            "aplicados": len(applied),
            "omitidos": len(skipped),
            "applied": applied,
            "skipped": skipped[:50],
        }, 200
    except Exception as exc:
        conn.rollback()
        logger.exception("Error reaplicando invoice %s: %s", invoice_id, exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def resolve_invoice_file(invoice_id):
    """Localiza el Excel original de una invoice en disco.

    Devuelve (info, status). info trae ruta absoluta y nombre de descarga.
    """
    conn, cursor, error = _db()
    if error:
        return error
    try:
        cursor.execute(
            """
            SELECT numero_invoice, archivo_nombre, archivo_ruta, archivo_mime
            FROM material_invoices
            WHERE id = %s
            LIMIT 1
            """,
            (invoice_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {"success": False, "error": "Invoice no encontrada."}, 404
        if not row.get("archivo_ruta"):
            return {"success": False, "error": "Esta invoice no tiene archivo guardado."}, 404

        full = absolute_path(row["archivo_ruta"])
        if not full or not os.path.isfile(full):
            return {"success": False, "error": "El archivo no existe en el servidor."}, 404

        download_name = row.get("archivo_nombre") or f"{row['numero_invoice']}.xlsx"
        if not download_name.lower().endswith((".xlsx", ".xlsm")):
            download_name = f"{download_name}.xlsx"
        return (
            {
                "success": True,
                "path": full,
                "download_name": download_name,
                "mimetype": row.get("archivo_mime")
                or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
            200,
        )
    except Exception as exc:
        logger.exception("Error resolviendo archivo de invoice %s: %s", invoice_id, exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def delete_invoice(invoice_id):
    """Borra una invoice solo si NO tiene ningun link de lote.

    Cualquier link (APLICADO o DESAPLICADO) bloquea el borrado, porque
    representa lotes costeados desde esta invoice y eliminarla romperia la
    trazabilidad de costos del inventario. Borra lineas, packing, el registro
    y el Excel guardado en disco.
    """
    conn, cursor, error = _db()
    if error:
        return error
    archivo_ruta = None
    try:
        cursor.execute("START TRANSACTION")
        cursor.execute(
            "SELECT id, numero_invoice, archivo_ruta FROM material_invoices WHERE id = %s LIMIT 1 FOR UPDATE",
            (invoice_id,),
        )
        invoice = cursor.fetchone()
        if not invoice:
            conn.rollback()
            return {"success": False, "error": "Invoice no encontrada."}, 404

        cursor.execute(
            "SELECT COUNT(*) AS total FROM material_invoice_lot_links WHERE invoice_id = %s",
            (invoice_id,),
        )
        total_links = (cursor.fetchone() or {}).get("total") or 0
        if total_links:
            conn.rollback()
            return (
                {
                    "success": False,
                    "error": (
                        "No se puede eliminar: la invoice tiene "
                        f"{total_links} link(s) de lote. Desaplica y limpia los links primero."
                    ),
                    "links": total_links,
                },
                409,
            )

        archivo_ruta = invoice.get("archivo_ruta")
        cursor.execute("DELETE FROM material_invoice_packing_lines WHERE invoice_id = %s", (invoice_id,))
        cursor.execute("DELETE FROM material_invoice_lines WHERE invoice_id = %s", (invoice_id,))
        cursor.execute("DELETE FROM material_invoices WHERE id = %s", (invoice_id,))
        conn.commit()

        # Borra el Excel solo despues del commit (si falla, no es critico).
        if archivo_ruta:
            delete_file(archivo_ruta)
        return {"success": True, "invoice_id": invoice_id, "numero_invoice": invoice.get("numero_invoice")}, 200
    except Exception as exc:
        conn.rollback()
        logger.exception("Error eliminando invoice %s: %s", invoice_id, exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()
