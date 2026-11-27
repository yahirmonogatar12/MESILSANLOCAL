"""Relee el costo unitario de invoices que se cargaron con costo 0.

Desde la V-60 (oct 2026) la hoja INVOICE (CONVERTED) llama PRECIO a la columna
del costo unitario y el parser solo reconocia COSTO/COSTOS, asi que esas
invoices quedaron con costo unitario 0 (el TOTAL si se leyo). El parser ya
acepta PRECIO; este script vuelve a leer el Excel guardado de cada invoice y
pone el costo en:
  - material_invoice_lines: lineas en 0 que coinciden en No., parte y cantidad
  - material_invoice_lot_links de esas lineas que quedaron en 0
  - inventario_lote_costos cuyo costo vigente sale de esas lineas (INVOICE) en 0
El TOTAL de las lineas no se toca. Sin --aplicar solo muestra lo que cambiaria.

Uso, en el servidor (donde estan los Excel guardados):
    python tools/reparar_costo_invoice.py IM20260906-V60 IM20261021-V70
    python tools/reparar_costo_invoice.py IM20260906-V60 IM20261021-V70 --aplicar
"""
import argparse
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.api.control_material.invoice_core.parser import parse_invoice_workbook  # noqa: E402
from app.api.control_material.invoice_core.storage import absolute_path  # noqa: E402
from app.api.shared.db_helpers import dict_cursor  # noqa: E402
from app.config_mysql import get_mysql_connection  # noqa: E402


def cambios(excel_lines, db_lines):
    """(cambios, distintas, incoherentes) entre lo que lee el parser y la BD.

    Solo cambia lineas en 0 cuya No., parte raw y cantidad coinciden con el
    Excel; si alguien edito o borro una linea, se reporta y no se toca.
    """
    por_no = {int(row["line_no"]): row for row in db_lines}
    nuevos, distintas, incoherentes = [], [], []
    for linea in excel_lines:
        actual = por_no.get(linea["line_no"])
        if (
            not actual
            or (actual["raw_part_num"] or "") != linea["raw_part_num"]
            or Decimal(str(actual["cantidad"])) != linea["cantidad"]
        ):
            distintas.append(linea["line_no"])
            continue
        unit = linea["costo_unitario"]
        if unit <= 0 or Decimal(str(actual["costo_unitario"])) > 0:
            continue
        total = Decimal(str(actual["costo_total"] or 0))
        if total and abs(unit * linea["cantidad"] - total) > max(Decimal("0.05"), total / 200):
            incoherentes.append(
                f"No. {linea['line_no']} {linea['raw_part_num']}: precio {unit} x {linea['cantidad']} "
                f"= {(unit * linea['cantidad']).quantize(Decimal('0.01'))}, total {total}"
            )
        nuevos.append((actual["id"], unit, linea["raw_unit_cost"]))
    return nuevos, distintas, incoherentes


def _contar(cursor, sql, invoice_id, ids):
    marcas = ", ".join(["%s"] * len(ids))
    cursor.execute(sql.format(marcas=marcas), [invoice_id, *ids])
    return int((cursor.fetchone() or {}).get("total") or 0)


def reparar(cursor, numero, aplicar):
    cursor.execute(
        "SELECT id, ambito, archivo_nombre, archivo_ruta FROM material_invoices WHERE numero_invoice = %s",
        (numero,),
    )
    invoices = cursor.fetchall()
    if len(invoices) != 1:
        print(f"{numero}: {len(invoices)} invoices con ese numero, se omite")
        return
    invoice = invoices[0]
    ruta = absolute_path(invoice["archivo_ruta"])
    if not ruta or not os.path.exists(ruta):
        print(f"{numero}: no se encontro el Excel guardado ({invoice['archivo_ruta']})")
        return
    with open(ruta, "rb") as archivo:
        parsed = parse_invoice_workbook(archivo.read(), invoice["archivo_nombre"], invoice["ambito"])
    cursor.execute(
        "SELECT id, line_no, raw_part_num, cantidad, costo_unitario, costo_total "
        "FROM material_invoice_lines WHERE invoice_id = %s",
        (invoice["id"],),
    )
    nuevos, distintas, incoherentes = cambios(parsed["invoice_lines"], cursor.fetchall())
    print(f"\n{numero} (id {invoice['id']}): {len(parsed['invoice_lines'])} lineas en el Excel")
    print(f"  lineas con costo nuevo: {len(nuevos)}")
    if distintas:
        print(f"  no coinciden con la BD (se dejan igual): No. {', '.join(map(str, distintas))}")
    for texto in incoherentes:
        print(f"  aviso, PRECIO x QTY no da el TOTAL: {texto}")
    if not nuevos:
        return
    ids = [line_id for line_id, _, _ in nuevos]
    links = _contar(
        cursor,
        "SELECT COUNT(*) AS total FROM material_invoice_lot_links "
        "WHERE invoice_id = %s AND invoice_line_id IN ({marcas}) AND costo_unitario = 0",
        invoice["id"],
        ids,
    )
    lotes = _contar(
        cursor,
        "SELECT COUNT(*) AS total FROM inventario_lote_costos WHERE invoice_id = %s "
        "AND invoice_line_id IN ({marcas}) AND fuente_costo = 'INVOICE' AND costo_unitario = 0",
        invoice["id"],
        ids,
    )
    print(f"  links de lotes a corregir: {links}")
    print(f"  costos de lote a corregir: {lotes}")
    if not aplicar:
        return
    cursor.executemany(
        "UPDATE material_invoice_lines SET costo_unitario = %s, raw_unit_cost = %s "
        "WHERE id = %s AND costo_unitario = 0",
        [(str(unit), raw, line_id) for line_id, unit, raw in nuevos],
    )
    marcas = ", ".join(["%s"] * len(ids))
    cursor.execute(
        f"""
        UPDATE material_invoice_lot_links ll
        JOIN material_invoice_lines il ON il.id = ll.invoice_line_id
        SET ll.costo_unitario = il.costo_unitario
        WHERE ll.invoice_id = %s AND il.id IN ({marcas}) AND ll.costo_unitario = 0
        """,
        [invoice["id"], *ids],
    )
    cursor.execute(
        f"""
        UPDATE inventario_lote_costos ilc
        JOIN material_invoice_lines il ON il.id = ilc.invoice_line_id
        SET ilc.costo_unitario = il.costo_unitario, ilc.fecha_actualizacion = NOW()
        WHERE ilc.invoice_id = %s AND il.id IN ({marcas})
          AND ilc.fuente_costo = 'INVOICE' AND ilc.costo_unitario = 0
        """,
        [invoice["id"], *ids],
    )
    print("  aplicado")


def main():
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("invoices", nargs="+", help="numeros de invoice, ej. IM20261021-V70")
    args.add_argument("--aplicar", action="store_true", help="escribe los cambios (sin esto solo muestra)")
    opciones = args.parse_args()
    conn = get_mysql_connection()
    if conn is None:
        raise SystemExit("Base de datos no disponible")
    cursor = dict_cursor(conn)
    try:
        cursor.execute("START TRANSACTION")
        for numero in opciones.invoices:
            reparar(cursor, numero, opciones.aplicar)
        if opciones.aplicar:
            conn.commit()
            print("\nCambios guardados.")
        else:
            conn.rollback()
            print("\nSolo revision: no se escribio nada. Agrega --aplicar para guardar.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
