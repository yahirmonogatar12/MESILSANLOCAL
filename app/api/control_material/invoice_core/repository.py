"""Repositorio de invoices: lecturas y actualizaciones puntuales."""

from decimal import Decimal

from app.api.control_material.invoice_core.constants import MONEDA_DEFAULT
from app.api.control_material.invoice_core.matcher import invoice_has_differences

def fetch_invoice(cursor, invoice_id, for_update=False):
    suffix = " FOR UPDATE" if for_update else ""
    cursor.execute(
        f"""
        SELECT *
        FROM material_invoices
        WHERE id = %s
        LIMIT 1{suffix}
        """,
        (invoice_id,),
    )
    return cursor.fetchone()


def recalculate_packing_state(cursor, packing_line_id):
    if not packing_line_id:
        return
    cursor.execute(
        """
        SELECT cantidad_packing
        FROM material_invoice_packing_lines
        WHERE id = %s
        """,
        (packing_line_id,),
    )
    packing = cursor.fetchone()
    if not packing:
        return
    cursor.execute(
        """
        SELECT cantidad_aplicada
        FROM material_invoice_lot_links
        WHERE packing_line_id = %s AND estado = 'APLICADO'
        """,
        (packing_line_id,),
    )
    used = sum(Decimal(str(row["cantidad_aplicada"])) for row in (cursor.fetchall() or []))
    total = Decimal(str(packing["cantidad_packing"] or 0))
    if total > 0 and used >= total:
        estado = "APLICADA"
    elif used > 0:
        estado = "APLICADA_PARCIAL"
    else:
        estado = "MATCH"
    cursor.execute(
        """
        UPDATE material_invoice_packing_lines
        SET estado_match = %s
        WHERE id = %s
          AND estado_match NOT IN ('SIN_ALIAS','SIN_LINEA','DIFERENCIA')
        """,
        (estado, packing_line_id),
    )


def recalculate_invoice_state(cursor, invoice_id):
    invoice = fetch_invoice(cursor, invoice_id, for_update=True)
    if not invoice or invoice.get("estado") == "CANCELADA":
        return None
    cursor.execute(
        """
        SELECT
          COALESCE((SELECT SUM(cantidad_packing) FROM material_invoice_packing_lines WHERE invoice_id = %s), 0) AS total_packing,
          COALESCE((SELECT SUM(cantidad_aplicada) FROM material_invoice_lot_links WHERE invoice_id = %s AND estado = 'APLICADO'), 0) AS total_aplicado,
          (SELECT COUNT(*) FROM material_invoice_lot_links WHERE invoice_id = %s AND estado = 'APLICADO') AS links_activos
        """,
        (invoice_id, invoice_id, invoice_id),
    )
    totals = cursor.fetchone() or {}
    total_packing = Decimal(str(totals.get("total_packing") or 0))
    total_aplicado = Decimal(str(totals.get("total_aplicado") or 0))
    links_activos = int(totals.get("links_activos") or 0)

    if total_packing > 0 and total_aplicado >= total_packing:
        estado = "APLICADA"
    elif links_activos > 0 or total_aplicado > 0:
        estado = "PARCIALMENTE_APLICADA"
    else:
        estado = "CON_DIFERENCIAS" if invoice_has_differences(cursor, invoice_id) else "VALIDADA"

    cursor.execute(
        "UPDATE material_invoices SET estado = %s WHERE id = %s",
        (estado, invoice_id),
    )
    return estado


# ===================== Render =====================

def packing_available_locked(cursor, packing_line_id):
    cursor.execute(
        """
        SELECT *
        FROM material_invoice_packing_lines
        WHERE id = %s
        LIMIT 1
        FOR UPDATE
        """,
        (packing_line_id,),
    )
    packing = cursor.fetchone()
    if not packing:
        return None, Decimal("0.0000"), Decimal("0.0000")
    cursor.execute(
        """
        SELECT id, cantidad_aplicada
        FROM material_invoice_lot_links
        WHERE packing_line_id = %s AND estado = 'APLICADO'
        FOR UPDATE
        """,
        (packing_line_id,),
    )
    used = sum(Decimal(str(row["cantidad_aplicada"])) for row in (cursor.fetchall() or []))
    total = Decimal(str(packing.get("cantidad_packing") or 0))
    return packing, total, total - used

def candidate_lots_for_packing(cursor, invoice, packing):
    # El packing trae la parte BASE (resuelta por validate_system_parts), pero en
    # almacen cma.numero_parte puede traer version/lote (EAX66946005-1.0). Se
    # acepta igualdad con la base o que empiece por "base-" (con sufijo). No se
    # usa el primer segmento a ciegas para no romper partes que legitimamente
    # llevan guion (en ese caso packing.numero_parte_sistema ya es el codigo
    # completo y la igualdad exacta funciona). El pallet debe coincidir: los
    # lotes con pallet distinto se reportan aparte (mismatched_pallet_lots).
    base = packing.get("numero_parte_sistema") or ""
    cursor.execute(
        """
        SELECT cma.codigo_material_recibido
        FROM control_material_almacen cma
        LEFT JOIN material_invoice_lot_links active
          ON active.codigo_material_recibido = cma.codigo_material_recibido
         AND active.estado = 'APLICADO'
        WHERE cma.numero_invoice = %s
          AND cma.pallet_no = %s
          AND (cma.numero_parte = %s OR cma.numero_parte LIKE %s)
          AND active.id IS NULL
          AND (cma.cancelado = 0 OR cma.cancelado IS NULL)
        ORDER BY cma.fecha_recibo ASC, cma.id ASC
        """,
        (invoice["numero_invoice"], packing.get("pallet_no"), base, f"{base}-%"),
    )
    return [row["codigo_material_recibido"] for row in (cursor.fetchall() or [])]


def mismatched_pallet_lots_for_packing(cursor, invoice, packing):
    """Lotes de la misma invoice+parte cuyo PALLET no coincide con el packing.

    Son lotes que llegaron pero en un pallet distinto (o sin pallet). NO se
    auto-aplican: se reportan como diferencia para revision manual, porque
    aplicar a ciegas mezclaria el costo entre pallets. Devuelve filas con
    codigo y el pallet real del lote para mostrarlo en el reporte.
    """
    base = packing.get("numero_parte_sistema") or ""
    pallet = packing.get("pallet_no")
    cursor.execute(
        """
        SELECT cma.codigo_material_recibido, cma.pallet_no AS pallet_lote
        FROM control_material_almacen cma
        LEFT JOIN material_invoice_lot_links active
          ON active.codigo_material_recibido = cma.codigo_material_recibido
         AND active.estado = 'APLICADO'
        WHERE cma.numero_invoice = %s
          AND (cma.numero_parte = %s OR cma.numero_parte LIKE %s)
          AND active.id IS NULL
          AND (cma.cancelado = 0 OR cma.cancelado IS NULL)
          AND (cma.pallet_no IS NULL OR cma.pallet_no = '' OR cma.pallet_no <> %s)
        ORDER BY cma.fecha_recibo ASC, cma.id ASC
        """,
        (invoice["numero_invoice"], base, f"{base}-%", pallet),
    )
    return cursor.fetchall() or []


# Compatibilidad con nombres previos al refactor.
_fetch_invoice = fetch_invoice
_recalculate_packing_state = recalculate_packing_state
_recalculate_invoice_state = recalculate_invoice_state
_packing_available_locked = packing_available_locked
_candidate_lots_for_packing = candidate_lots_for_packing
_mismatched_pallet_lots_for_packing = mismatched_pallet_lots_for_packing
