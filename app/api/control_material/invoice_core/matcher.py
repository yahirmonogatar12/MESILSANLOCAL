"""Conciliacion de partes, aliases e invoice/packing lines."""

from app.api.control_material.invoice_core.normalizers import normalizar_numero_parte

def resolve_aliases(cursor, records, tipo=None, part_key="numero_parte_sistema"):
    parts = sorted({normalizar_numero_parte(r.get(part_key)) for r in records if r.get(part_key)})
    if not parts:
        return

    placeholders = ", ".join(["%s"] * len(parts))
    tipo = tipo or ""
    alias_params = parts + [tipo, tipo]
    cursor.execute(
        f"""
        SELECT numero_parte_original, numero_parte_sistema, tipo
        FROM material_part_aliases
        WHERE activo = 1
          AND numero_parte_original IN ({placeholders})
          AND (tipo IS NULL OR tipo = '' OR tipo = %s)
        ORDER BY
          CASE
            WHEN tipo = %s THEN 0
            WHEN tipo IS NULL OR tipo = '' THEN 1
            ELSE 2
          END,
          id DESC
        """,
        alias_params,
    )
    aliases = {}
    for row in cursor.fetchall() or []:
        aliases.setdefault(normalizar_numero_parte(row["numero_parte_original"]), row["numero_parte_sistema"])

    cursor.execute(
        f"""
        SELECT numero_parte
        FROM materiales
        WHERE numero_parte IN ({placeholders})
        """,
        parts,
    )
    direct = {normalizar_numero_parte(row["numero_parte"]): row["numero_parte"] for row in cursor.fetchall() or []}

    for record in records:
        raw_part = normalizar_numero_parte(record.get(part_key))
        if not raw_part:
            record["estado_match"] = "SIN_ALIAS"
            record["mensaje_match"] = "Sin numero de parte"
            continue
        if raw_part in aliases:
            record["numero_parte_sistema"] = aliases[raw_part]
            record["estado_match"] = "ALIAS" if "cantidad" in record else "MATCH"
            record["mensaje_match"] = "Alias aplicado"
        elif raw_part in direct:
            record["numero_parte_sistema"] = direct[raw_part]
            record["estado_match"] = "DIRECTO" if "cantidad" in record else "MATCH"
            record["mensaje_match"] = "Parte encontrada"
        else:
            record["numero_parte_sistema"] = raw_part
            record["estado_match"] = "SIN_ALIAS"
            record["mensaje_match"] = "No existe alias/material en sistema"


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
_resolve_aliases = resolve_aliases
_assign_packing_lines = assign_packing_lines
_invoice_has_differences = invoice_has_differences
