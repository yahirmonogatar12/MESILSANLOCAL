"""Compara dos reportes de LG y reporta el atraso y el material sin consumir.

Sirve para PPN (tarjetas) y para el Prod Plan de OVEN. Misma cuenta que hace el
import en Part Planning, pero sin tocar la BD: para revisar un dia a mano. La
logica vive en app/api/control_produccion/ppn.py.

Uso:
    python tools/ppn_delta.py "PPN 29.07.26.xlsx" "PPN 30.07.26 (1).xlsx"
    python tools/ppn_delta.py "Prod Plan JULIO 29 2026.xlsx" "Prod Plan JULIO 30 2026.xlsx"
"""
import os
import sys

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.api.control_produccion import ppn  # noqa: E402


def leer(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        hoja, fuente = ppn.hoja_reporte(wb)
        if hoja is None:
            raise SystemExit(f"{path}: no es PPN ni Prod Plan ({wb.sheetnames[:5]})")
        fecha0, wos = ppn.LECTORES[fuente](wb[hoja])
        return fecha0, wos, fuente
    finally:
        wb.close()


def main(p_ayer, p_hoy):
    dia, ayer, fuente = leer(p_ayer)
    _, hoy, fuente_hoy = leer(p_hoy)
    if fuente != fuente_hoy:
        raise SystemExit(f"No se comparan entre si: {fuente} vs {fuente_hoy}")
    print(f"fuente: {fuente}")
    renglones, partes = ppn.sobrante(ppn.baseline(dia, ayer), hoy)
    prog = sum(r[1] for r in renglones)
    real = sum(r[2] for r in renglones)
    print(f"{dia}: {len(renglones)} W/O programados | plan {prog} | construido {real} | "
          f"atraso {prog - real} ({100 * (prog - real) / max(prog, 1):.0f}%)")

    print("\nW/O con mayor desviacion")
    for wo, p, r in sorted(renglones, key=lambda x: -(x[1] - x[2]))[:10]:
        print(f"  {wo:9} {ayer[wo]['modelo']:24} plan={p:5} real={r:5} atraso={p - r:5}")

    print(f"\nPartes ILSAN entregadas y NO consumidas (total {sum(partes.values())} pzas)")
    print("  siguen en piso de LG: no se deben volver a planear")
    for p, q in sorted(partes.items(), key=lambda x: -x[1])[:20]:
        print(f"  {p:14} {q:6}")

    sin_bom = sorted({w["modelo"] for w in hoy.values() if w["sin_bom"]})
    if sin_bom:
        print(f"\nModelos sin BOM en el PPN (demanda no explotada): {sin_bom}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
