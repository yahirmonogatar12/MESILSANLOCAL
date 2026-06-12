"""Exportaciones de invoices de material."""

import logging

from app.api.control_material.invoice_core.constants import ERROR_INTERNO
from app.api.control_material.invoice_core.normalizers import row_to_json
from app.api.control_material.invoice_core.repository import fetch_invoice
from app.api.shared import conexion_o_error, dict_cursor, excel_response

logger = logging.getLogger(__name__)


def export_invoice(invoice_id):
    conn, error_response = conexion_o_error()
    if error_response:
        return {"success": False, "error": "Base de datos no disponible"}, 503
    cursor = dict_cursor(conn)
    try:
        invoice = fetch_invoice(cursor, invoice_id)
        if not invoice:
            return {"success": False, "error": "Invoice no encontrada."}, 404
        cursor.execute(
            """
            SELECT line_no, raw_part_num, numero_parte_sistema, descripcion,
                   cantidad, uom, costo_unitario, costo_total, estado_match, mensaje_match
            FROM material_invoice_lines
            WHERE invoice_id = %s
            ORDER BY line_no, id
            """,
            (invoice_id,),
        )
        rows = [row_to_json(r) for r in (cursor.fetchall() or [])]
        headers = [
            "Linea", "Parte raw", "Parte sistema", "Descripcion", "Cantidad",
            "UOM", "Costo unitario", "Costo total", "Estado", "Mensaje",
        ]
        keys = [
            "line_no", "raw_part_num", "numero_parte_sistema", "descripcion",
            "cantidad", "uom", "costo_unitario", "costo_total", "estado_match",
            "mensaje_match",
        ]
        widths = [10, 24, 24, 38, 14, 10, 16, 16, 18, 35]
        response = excel_response(
            rows,
            headers,
            keys,
            widths,
            sheet="Invoice",
            filename=f"invoice_{invoice['numero_invoice']}",
            freeze="A2",
        )
        return response, 200
    except Exception as exc:
        logger.exception("Error exportando invoice %s: %s", invoice_id, exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()
