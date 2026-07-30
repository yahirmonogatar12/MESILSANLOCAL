"""PPN de LG: demanda pendiente por parte y consumo REAL del dia que paso.

Sin dependencias de Flask ni de BD: solo openpyxl. Lo usan part_planning.py
(import) y tools/ppn_delta.py (CLI).

Cada renglon del PPN es un W/O con su modelo, las partes que ILSAN le surte
(columnas I..Q, mismo layout que la hoja BOM del Cal_*.xlsx) y la cantidad
PENDIENTE repartida por dia (columnas BC..CH). Explotar esos buckets por esas
partes reproduce la hoja diaria del Cal (46/49 partes exactas el 30/07): el Cal
es el PPN explotado, asi que el PPN sirve igual para alimentar lg_plan_daily.

POR QUE IMPORTA EL CONSUMO REAL
Los buckets del PPN ya vienen NETOS de lo construido (W/O Result), asi que la
demanda futura se autocorrige sola. Lo que no se corrige es el pasado: el
renglon de AYER en lg_plan_daily sigue con lo PLANEADO, no con lo que LG metio.
Y la proyeccion arrastra I(t) = I(t-1) - P(t) + S(t) desde ref_date, o sea que
descuenta ese plan viejo completo. Si LG se atraso, ese material sigue en su
piso y ademas el PPN de hoy lo reprograma hacia adelante: se descuenta dos veces
y aparece un faltante fantasma que la IA vuelve a planear.

    sobrante(parte) = programado_ayer - construido_ayer

construido_ayer sale de comparar el W/O Result de dos snapshots del PPN.
"""
import datetime as dt
import io
import re
from collections import defaultdict

import openpyxl

PPN_SHEET_RE = re.compile(r"^\s*ppn\b", re.IGNORECASE)

C_WO, C_MODELO = 4, 7
C_PARTES = range(8, 17)   # I..Q: MAIN, HARNESS x3, DISPLAY, PCB DISPLAY, SUB ENS, PCB SUB, LED
C_PSTART = 31             # Planned Start Time
C_PLAN, C_RESULT = 49, 51  # W/O Plan Qty, W/O Result
C_DIA0, C_DIAN = 54, 86   # BC..CH: pendiente repartido por dia
NO_PARTE = ("NO USA", "N/A", "-", "")


def hoja_ppn(wb):
    """Nombre de la hoja PPN del workbook, o None si no es un PPN."""
    for nombre in wb.sheetnames:
        if PPN_SHEET_RE.match(nombre):
            return nombre
    return None


def leer_ppn(ws):
    """-> (fecha0, {wo: {modelo, partes, sin_bom, plan, result, dias{fecha: qty}}}).

    Lanza ValueError si el layout no es el esperado (columnas movidas).
    """
    filas = list(ws.iter_rows(values_only=True))
    if len(filas) < 3:
        raise ValueError("La hoja PPN no tiene renglones de W/O.")
    etiquetas = filas[0][C_DIA0:C_DIAN]
    inicios = [r[C_PSTART] for r in filas[2:]
               if len(r) > C_PSTART and isinstance(r[C_PSTART], dt.datetime)]
    if not inicios:
        raise ValueError("La hoja PPN no trae 'Planned Start Time' (columna AF).")
    fecha0 = min(inicios).date()
    fechas = [fecha0 + dt.timedelta(days=i) for i in range(len(etiquetas))]
    # Las etiquetas de esas columnas son el dia del mes: si no cuadran con
    # fecha0, el layout cambio y explotar los buckets pondria la demanda en
    # fechas equivocadas.
    try:
        dias_hoja = [int(e) for e in etiquetas]
    except (TypeError, ValueError):
        raise ValueError("Las columnas de dias del PPN (BC..CH) no traen dia del mes.")
    if dias_hoja != [f.day for f in fechas]:
        raise ValueError(
            f"Los dias del PPN no empiezan en {fecha0}: encabezados {dias_hoja[:5]}."
        )

    wos = {}
    for r in filas[2:]:
        if not r or r[0] is None or len(r) <= C_RESULT:
            continue
        crudas = [str(r[i]).strip() for i in C_PARTES if isinstance(r[i], str)]
        wos[str(r[C_WO])] = {
            "modelo": str(r[C_MODELO] or "").strip(),
            # "#N/A" = modelo sin BOM en el PPN; se reporta, no se explota.
            "partes": {p for p in crudas if p.upper() not in NO_PARTE and not p.startswith("#")},
            "sin_bom": any(p.startswith("#") for p in crudas),
            "plan": int(r[C_PLAN] or 0),
            "result": int(r[C_RESULT] or 0),
            "dias": {f: int(r[C_DIA0 + i])
                     for i, f in enumerate(fechas)
                     if C_DIA0 + i < len(r) and r[C_DIA0 + i]},
        }
    if not wos:
        raise ValueError("La hoja PPN no tiene renglones de W/O.")
    return fecha0, wos


def leer_bytes(file_bytes):
    """(fecha0, wos) del Excel en memoria, o None si no trae hoja PPN."""
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    try:
        hoja = hoja_ppn(wb)
        return leer_ppn(wb[hoja]) if hoja else None
    finally:
        wb.close()


def demanda(wos):
    """Demanda pendiente por (parte, fecha), ya neta de lo que LG construyo."""
    d = defaultdict(int)
    for w in wos.values():
        for fecha, qty in w["dias"].items():
            for p in w["partes"]:
                d[(p, fecha)] += qty
    return d


def baseline(fecha, wos):
    """Snapshot minimo que hay que guardar para poder comparar mañana."""
    return {
        wo: {
            "partes": w["partes"],
            "prog": w["dias"].get(fecha, 0),  # lo programado para SU propio dia
            "plan": w["plan"],
            "result": w["result"],
        }
        for wo, w in wos.items()
    }


def sobrante(base, wos_hoy):
    """Material entregado y no consumido el dia del snapshot `base`.

    -> (renglones [(wo, prog, real)], {parte: pzas sin consumir})
    """
    renglones, partes = [], defaultdict(int)
    for wo, b in base.items():
        prog = b["prog"]
        if not prog:
            continue
        if wo in wos_hoy:
            hecho = wos_hoy[wo]["result"] - b["result"]
        else:
            hecho = b["plan"] - b["result"]  # desaparecio del reporte = cerrado
        # Tope: de ese W/O no pudo consumir mas de lo que tenia programado ese
        # dia; lo demas es produccion de otros dias del mismo W/O.
        real = max(0, min(hecho, prog))
        renglones.append((wo, prog, real))
        for p in b["partes"]:
            partes[p] += prog - real
    return renglones, {p: q for p, q in partes.items() if q > 0}
