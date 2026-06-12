"""Exportacion Excel de valorizacion de inventario."""

import logging

from app.api.control_material.invoice_core.constants import ERROR_INTERNO, MONEDA_DEFAULT
from app.api.control_material.invoice_core.normalizers import row_to_json
from app.api.control_material.valuation_core.service import valuation_base_sql, valuation_filters
from app.api.shared import conexion_o_error, dict_cursor, excel_response

logger = logging.getLogger(__name__)


def export_valuation(args):
    conn, error_response = conexion_o_error()
    if error_response:
        return {"success": False, "error": "Base de datos no disponible"}, 503
    cursor = dict_cursor(conn)
    try:
        where, params = valuation_filters(args)
        base = valuation_base_sql(where)
        cursor.execute(
            base + " ORDER BY numero_parte_sistema, codigo_material_recibido LIMIT 20000",
            [MONEDA_DEFAULT] + params,
        )
        rows = [row_to_json(r) for r in (cursor.fetchall() or [])]
        headers = [
            "Codigo recibido", "Numero de parte", "Lote", "Pallet", "Vendedor",
            "Stock", "Unidad", "Costo unitario", "Moneda", "Valor total",
            "Fuente costo", "Estimado", "Invoice", "Actualizado",
        ]
        keys = [
            "codigo_material_recibido", "numero_parte_sistema", "numero_lote",
            "pallet_no", "vendedor", "stock_actual", "unidad_medida",
            "costo_unitario", "moneda", "valor_total", "fuente_costo",
            "es_estimado", "numero_invoice", "fecha_actualizacion",
        ]
        widths = [24, 24, 20, 12, 18, 12, 10, 16, 10, 16, 18, 10, 20, 20]
        response = excel_response(
            rows,
            headers,
            keys,
            widths,
            sheet="Valorizacion",
            filename="inventory_valuation",
            freeze="A2",
        )
        return response, 200
    except Exception as exc:
        logger.exception("Error exportando valorizacion: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()
