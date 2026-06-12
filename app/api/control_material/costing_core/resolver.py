"""Resolucion y persistencia del costo vigente por lote."""

from decimal import Decimal

from app.api.shared import sanitizar_texto
from app.api.control_material.invoice_core.constants import MONEDA_DEFAULT
from app.api.control_material.invoice_core.normalizers import (
    decimal_or_zero,
    normalizar_numero_parte,
)

def fetch_lot_row(cursor, codigo, for_update=False):
    suffix = " FOR UPDATE" if for_update else ""
    cursor.execute(
        f"""
        SELECT
          COALESCE(il.codigo_material_recibido, cma.codigo_material_recibido) AS codigo_material_recibido,
          COALESCE(il.numero_parte, cma.numero_parte) AS numero_parte_sistema,
          COALESCE(il.numero_lote, cma.numero_lote_material) AS numero_lote,
          COALESCE(il.total_entrada, cma.cantidad_actual, 0) AS cantidad_lote,
          COALESCE(il.stock_actual, cma.cantidad_actual, 0) AS stock_actual,
          cma.numero_invoice,
          cma.pallet_no_original,
          cma.pallet_no,
          cma.vendedor,
          cma.fecha_recibo
        FROM control_material_almacen cma
        LEFT JOIN inventario_lotes il
          ON il.codigo_material_recibido = cma.codigo_material_recibido
        WHERE cma.codigo_material_recibido = %s
        LIMIT 1{suffix}
        """,
        (codigo,),
    )
    return cursor.fetchone()


def resolve_control_material_cost(cursor, numero_parte, vendedor=None):
    numero_parte = normalizar_numero_parte(numero_parte)
    vendedor = sanitizar_texto(vendedor, 100)
    if not numero_parte:
        return None
    if vendedor:
        cursor.execute(
            """
            SELECT costo_unitario_material, moneda
            FROM material_costos
            WHERE numero_parte = %s AND vendedor = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (numero_parte, vendedor),
        )
        row = cursor.fetchone()
        if row:
            return {
                "costo_unitario": Decimal(str(row["costo_unitario_material"])),
                "moneda": row.get("moneda") or MONEDA_DEFAULT,
                "fuente_costo": "CONTROL_MATERIAL",
                "es_estimado": 1,
            }
        return None

    cursor.execute(
        """
        SELECT mc.vendedor, mc.costo_unitario_material, mc.moneda
        FROM material_costos mc
        JOIN (
            SELECT vendedor, MAX(id) AS max_id
            FROM material_costos
            WHERE numero_parte = %s
            GROUP BY vendedor
        ) ult ON ult.max_id = mc.id
        """,
        (numero_parte,),
    )
    rows = cursor.fetchall() or []
    if len(rows) == 1:
        row = rows[0]
        return {
            "costo_unitario": Decimal(str(row["costo_unitario_material"])),
            "moneda": row.get("moneda") or MONEDA_DEFAULT,
            "fuente_costo": "CONTROL_MATERIAL",
            "es_estimado": 1,
        }
    return None


def upsert_inventory_cost(cursor, lot, cost_info, usuario, invoice_refs=None):
    invoice_refs = invoice_refs or {}
    cursor.execute(
        """
        INSERT INTO inventario_lote_costos (
            codigo_material_recibido, numero_parte_sistema, numero_lote,
            pallet_no_original, pallet_no, vendedor, cantidad_lote, stock_actual,
            costo_unitario, moneda, fuente_costo, es_estimado,
            invoice_id, invoice_line_id, packing_line_id, link_id,
            usuario_registro, fecha_registro, fecha_actualizacion
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        )
        ON DUPLICATE KEY UPDATE
            numero_parte_sistema = VALUES(numero_parte_sistema),
            numero_lote = VALUES(numero_lote),
            pallet_no_original = VALUES(pallet_no_original),
            pallet_no = VALUES(pallet_no),
            vendedor = VALUES(vendedor),
            cantidad_lote = VALUES(cantidad_lote),
            stock_actual = VALUES(stock_actual),
            costo_unitario = VALUES(costo_unitario),
            moneda = VALUES(moneda),
            fuente_costo = VALUES(fuente_costo),
            es_estimado = VALUES(es_estimado),
            invoice_id = VALUES(invoice_id),
            invoice_line_id = VALUES(invoice_line_id),
            packing_line_id = VALUES(packing_line_id),
            link_id = VALUES(link_id),
            fecha_actualizacion = NOW()
        """,
        (
            lot["codigo_material_recibido"],
            lot["numero_parte_sistema"],
            lot.get("numero_lote"),
            lot.get("pallet_no_original"),
            lot.get("pallet_no"),
            lot.get("vendedor"),
            str(decimal_or_zero(lot.get("cantidad_lote"))),
            str(decimal_or_zero(lot.get("stock_actual"))),
            str(cost_info["costo_unitario"]),
            cost_info["moneda"],
            cost_info["fuente_costo"],
            int(cost_info["es_estimado"]),
            invoice_refs.get("invoice_id"),
            invoice_refs.get("invoice_line_id"),
            invoice_refs.get("packing_line_id"),
            invoice_refs.get("link_id"),
            usuario,
        ),
    )


def recalculate_lot_cost(cursor, codigo, usuario):
    lot = fetch_lot_row(cursor, codigo, for_update=True)
    if not lot:
        return False

    cursor.execute(
        """
        SELECT ll.*, il.costo_unitario, il.moneda
        FROM material_invoice_lot_links ll
        JOIN material_invoice_lines il ON il.id = ll.invoice_line_id
        WHERE ll.codigo_material_recibido = %s
          AND ll.estado = 'APLICADO'
        ORDER BY ll.fecha_aplicacion DESC, ll.id DESC
        LIMIT 1
        """,
        (codigo,),
    )
    active = cursor.fetchone()
    if active:
        upsert_inventory_cost(
            cursor,
            lot,
            {
                "costo_unitario": Decimal(str(active["costo_unitario"])),
                "moneda": active.get("moneda") or MONEDA_DEFAULT,
                "fuente_costo": "INVOICE",
                "es_estimado": 0,
            },
            usuario,
            {
                "invoice_id": active["invoice_id"],
                "invoice_line_id": active["invoice_line_id"],
                "packing_line_id": active.get("packing_line_id"),
                "link_id": active["id"],
            },
        )
        return True

    fallback = resolve_control_material_cost(
        cursor, lot["numero_parte_sistema"], lot.get("vendedor")
    )
    if not fallback:
        fallback = {
            "costo_unitario": Decimal("0.0000"),
            "moneda": MONEDA_DEFAULT,
            "fuente_costo": "SIN_COSTO",
            "es_estimado": 1,
        }
    upsert_inventory_cost(cursor, lot, fallback, usuario)
    return True

# Compatibilidad con nombres previos al refactor.
_fetch_lot_row = fetch_lot_row
_resolve_control_material_cost = resolve_control_material_cost
_upsert_inventory_cost = upsert_inventory_cost
_recalculate_lot_cost = recalculate_lot_cost
