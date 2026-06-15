"""Conciliacion de partes, aliases e invoice/packing lines."""

from app.api.control_material.invoice_core.normalizers import (
    normalizar_numero_parte,
    prefijos_por_guion,
)


def validate_system_parts(cursor, records, part_key="numero_parte_sistema", estado_ok="DIRECTO"):
    """Valida numero_parte_sistema (ya resuelto en el Excel) contra materiales.

    No usa la tabla de aliases: la hoja INVOICE(CONVERTED) ya trae Part Sys.
    Marca si la parte existe o no en el sistema (para detectar diferencias) y,
    cuando existe, toma la unidad de medida (UOM) desde materiales para mantener
    consistencia con el sistema en vez de depender del Excel.

    El usuario apila el codigo como parte-version-lote separados por guiones, ej.
    EAX66946005-1.0-202601090001, mientras que en `materiales` la parte se da de
    alta como la base (EAX66946005). Por eso, si el codigo completo no existe, se
    prueban sus prefijos por guion del mas largo al mas corto y se usa el primero
    que exista como numero_parte_sistema (para que cuadre con almacen y costos).

    `estado_ok` es el estado a usar cuando la parte existe, porque el ENUM de
    estado_match difiere entre tablas: invoice_lines usa 'DIRECTO', packing_lines
    usa 'MATCH'. Las inexistentes quedan en 'SIN_ALIAS' (valido en ambas).
    """
    # Se consultan todos los prefijos por guion de cada codigo (parte completa,
    # luego sin lote, luego sin version, ...) para resolver la parte base real.
    candidatos = set()
    for r in records:
        candidatos.update(prefijos_por_guion(r.get(part_key)))
    candidatos.discard("")
    parts = sorted(candidatos)

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
        prefijos = prefijos_por_guion(record.get(part_key))
        # Primer prefijo (mas largo) que exista en materiales gana.
        match = next((p for p in prefijos if p in uom_por_parte), None)

        if not raw_part:
            record["estado_match"] = "SIN_ALIAS"
            record["mensaje_match"] = "Sin numero de parte"
        elif match:
            record["numero_parte_sistema"] = match
            record["estado_match"] = estado_ok
            record["mensaje_match"] = (
                "Parte encontrada" if match == raw_part
                else "Parte encontrada por base (sin version/lote)"
            )
            # UOM desde materiales (consistencia con el sistema).
            if "uom" in record:
                record["uom"] = uom_por_parte[match] or record.get("uom") or ""
        else:
            # Sin match: se conserva la base (primer segmento) como referencia.
            record["numero_parte_sistema"] = prefijos[-1] if prefijos else raw_part
            record["estado_match"] = "SIN_ALIAS"
            record["mensaje_match"] = "La parte no existe en materiales"


def assign_packing_lines(cursor, invoice_id):
    cursor.execute(
        """
        SELECT id, line_no, numero_parte_sistema, estado_match
        FROM material_invoice_lines
        WHERE invoice_id = %s
        """,
        (invoice_id,),
    )
    by_part = {}
    # line_no -> invoice_line_id (la hoja CONVERTED genera pares 1:1 por line_no).
    by_line_no = {}
    for row in cursor.fetchall() or []:
        by_part.setdefault(row["numero_parte_sistema"], []).append(row["id"])
        by_line_no[row["line_no"]] = row["id"]

    cursor.execute(
        """
        SELECT id, line_no, numero_parte_sistema, estado_match
        FROM material_invoice_packing_lines
        WHERE invoice_id = %s
        """,
        (invoice_id,),
    )
    for row in cursor.fetchall() or []:
        if row["estado_match"] == "SIN_ALIAS":
            continue
        matches = by_part.get(row["numero_parte_sistema"], [])
        invoice_line_id = None
        if len(matches) == 1:
            invoice_line_id = matches[0]
        elif len(matches) > 1:
            # Varias invoice lines comparten la misma parte (p.ej. la base
            # colapsa varias versiones/tarimas). Se desambigua por line_no:
            # en CONVERTED el packing y su invoice line comparten line_no.
            candidato = by_line_no.get(row["line_no"])
            if candidato in matches:
                invoice_line_id = candidato

        if invoice_line_id is not None:
            cursor.execute(
                """
                UPDATE material_invoice_packing_lines
                SET invoice_line_id = %s, estado_match = 'MATCH', mensaje_match = 'Packing conciliado con invoice line'
                WHERE id = %s
                """,
                (invoice_line_id, row["id"]),
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
