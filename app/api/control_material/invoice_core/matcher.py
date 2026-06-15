"""Conciliacion de partes, aliases e invoice/packing lines."""

from app.api.control_material.invoice_core.normalizers import normalizar_numero_parte


def validate_system_parts(cursor, records, part_key="numero_parte_sistema", estado_ok="DIRECTO"):
    """Valida numero_parte_sistema (ya resuelto en el Excel) contra materiales.

    No usa la tabla de aliases: la hoja INVOICE(CONVERTED) ya trae Part Sys.
    Marca si la parte existe o no en el sistema (para detectar diferencias) y,
    cuando existe, toma la unidad de medida (UOM) desde materiales para mantener
    consistencia con el sistema en vez de depender del Excel.

    `estado_ok` es el estado a usar cuando la parte existe, porque el ENUM de
    estado_match difiere entre tablas: invoice_lines usa 'DIRECTO', packing_lines
    usa 'MATCH'. Las inexistentes quedan en 'SIN_ALIAS' (valido en ambas).
    """
    parts = sorted({normalizar_numero_parte(r.get(part_key)) for r in records if r.get(part_key)})
    uom_por_parte = {}
    if parts:
        placeholders = ", ".join(["%s"] * len(parts))
        cursor.execute(
            f"""
            SELECT numero_parte, unidad_medida
            FROM materiales
            WHERE numero_parte IN ({placeholders})
            """,
            parts,
        )
        for row in cursor.fetchall() or []:
            uom_por_parte[normalizar_numero_parte(row["numero_parte"])] = row.get("unidad_medida")

    for record in records:
        raw_part = normalizar_numero_parte(record.get(part_key))
        if not raw_part:
            record["estado_match"] = "SIN_ALIAS"
            record["mensaje_match"] = "Sin numero de parte"
        elif raw_part in uom_por_parte:
            record["numero_parte_sistema"] = raw_part
            record["estado_match"] = estado_ok
            record["mensaje_match"] = "Parte encontrada"
            # UOM desde materiales (consistencia con el sistema).
            if "uom" in record:
                record["uom"] = uom_por_parte[raw_part] or record.get("uom") or ""
        else:
            record["numero_parte_sistema"] = raw_part
            record["estado_match"] = "SIN_ALIAS"
            record["mensaje_match"] = "La parte no existe en materiales"


def assign_packing_lines(cursor, invoice_id):
    cursor.execute(
        """
        SELECT id, numero_parte_sistema, estado_match
        FROM material_invoice_lines
        WHERE invoice_id = %s
        """,
        (invoice_id,),
    )
    by_part = {}
    for row in cursor.fetchall() or []:
        by_part.setdefault(row["numero_parte_sistema"], []).append(row["id"])

    cursor.execute(
        """
        SELECT id, numero_parte_sistema, estado_match
        FROM material_invoice_packing_lines
        WHERE invoice_id = %s
        """,
        (invoice_id,),
    )
    for row in cursor.fetchall() or []:
        if row["estado_match"] == "SIN_ALIAS":
            continue
        matches = by_part.get(row["numero_parte_sistema"], [])
        if len(matches) == 1:
            cursor.execute(
                """
                UPDATE material_invoice_packing_lines
                SET invoice_line_id = %s, estado_match = 'MATCH', mensaje_match = 'Packing conciliado con invoice line'
                WHERE id = %s
                """,
                (matches[0], row["id"]),
            )
        elif not matches:
            cursor.execute(
                """
                UPDATE material_invoice_packing_lines
                SET invoice_line_id = NULL, estado_match = 'SIN_LINEA', mensaje_match = 'No hay linea de invoice para la parte'
                WHERE id = %s
                """,
                (row["id"],),
            )
        else:
            cursor.execute(
                """
                UPDATE material_invoice_packing_lines
                SET invoice_line_id = NULL, estado_match = 'DIFERENCIA', mensaje_match = 'Multiples lineas de invoice para la parte'
                WHERE id = %s
                """,
                (row["id"],),
            )


def invoice_has_differences(cursor, invoice_id):
    cursor.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM material_invoice_lines
           WHERE invoice_id = %s AND estado_match IN ('SIN_ALIAS','DIFERENCIA')) AS diff_lines,
          (SELECT COUNT(*) FROM material_invoice_packing_lines
           WHERE invoice_id = %s AND estado_match IN ('SIN_ALIAS','SIN_LINEA','DIFERENCIA')) AS diff_packing
        """,
        (invoice_id, invoice_id),
    )
    row = cursor.fetchone() or {}
    return bool(row.get("diff_lines") or row.get("diff_packing"))

# Compatibilidad con nombres previos al refactor.
_assign_packing_lines = assign_packing_lines
_invoice_has_differences = invoice_has_differences
