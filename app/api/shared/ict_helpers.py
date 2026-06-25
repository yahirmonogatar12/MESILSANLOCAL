"""Helpers compartidos entre los 3 modulos ICT (Control de resultados).

Consumido por:
  - app/api/control_resultados/historial_ict.py             (defects + 5 APIs)
  - app/api/control_resultados/historial_ict_pass_fail.py   (3 APIs Pass/Fail)
  - app/api/control_resultados/historial_cambios_parametros_ict.py  (4 APIs)

Migrado desde app/routes.py el 2026-05-27. routes.py reexporta los 4
helpers para no romper cualquier consumidor legacy que aun no se haya
identificado (patron usado tambien en el refactor de Almacen de Embarques).
"""

from datetime import date, datetime, timedelta
from datetime import time as dt_time

# Import directo de db_mysql (no de app.api.shared) para evitar ciclo:
# routes.py reexporta estos helpers, y app.api.shared.__init__ importa de
# routes. Importar app.api.shared aqui haria circular.
from app.db_mysql import execute_query
from app.services.ict_lgd_parser import (
    IctLgdNotFoundError,
    IctLgdPathError,
    get_lgd_parameters_for_barcode,
    resolve_lgd_path,
)


def _to_time(value):
    """Normaliza a datetime.time. El driver devuelve TIME como timedelta."""
    if isinstance(value, timedelta):
        return (datetime.min + value).time()
    return value


def _append_indexable_text_filter(sql, params, column_name, raw_value, exact_min_length=12):
    """Agregar filtro exacto o por prefijo para evitar LIKE con comodin inicial."""
    value = (raw_value or "").strip()
    if not value:
        return sql

    if len(value) >= exact_min_length:
        sql += f" AND {column_name}=%s"
        params.append(value)
    else:
        sql += f" AND {column_name} LIKE %s"
        params.append(f"{value}%")
    return sql


def _ict_load_operator_sessions(fecha_desde, fecha_hasta):
    """Sesiones ICT del rango [fecha_desde, fecha_hasta], indexadas por (fecha, linea, ict).

    estacion = 'ICT-<ict>-<linea>'; el numero de ICT es el 2do segmento.
    Acepta date o datetime; se carga una vez y se resuelve en memoria con
    _ict_resolve_operator (evita subqueries correlacionadas por fila).
    """
    d_desde = fecha_desde.date() if isinstance(fecha_desde, datetime) else fecha_desde
    d_hasta = fecha_hasta.date() if isinstance(fecha_hasta, datetime) else fecha_hasta
    sql = (
        "SELECT s.fecha, s.linea, "
        "CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(s.estacion,'-',2),'-',-1) AS UNSIGNED) AS ict, "
        "s.usuario, s.hora_entrada, s.hora_salida, s.estado, s.duracion_seg, u.cargo "
        "FROM historial_estaciones_qa s "
        "LEFT JOIN usuarios_sistema u ON u.username = s.username "
        "WHERE s.tipo='ICT' AND s.fecha >= %s AND s.fecha <= %s AND s.usuario IS NOT NULL"
    )
    rows = execute_query(sql, (d_desde, d_hasta), fetch="all") or []
    sessions = {}
    for r in rows:
        key = (str(r.get("fecha")), str(r.get("linea") or ""), str(r.get("ict") or ""))
        sessions.setdefault(key, []).append(r)
    return sessions


def _ict_resolve_operator(sessions, ts, linea, ict_num):
    """Operador cuya sesion cubre el datetime `ts` para (linea, ict). '' si ninguna.

    Si varias sesiones lo cubren, gana la de mayor hora_entrada. Sesiones
    abiertas (hora_salida NULL) cubren todo lo posterior a su entrada.
    """
    if not ts:
        return ""
    key = (ts.date().isoformat(), str(linea or ""), str(ict_num or ""))
    candidates = sessions.get(key)
    if not candidates:
        return ""
    current = ts.time()
    best = None  # (hora_entrada, usuario) de la sesion mas reciente que cubre ts
    for s in candidates:
        entrada = _to_time(s.get("hora_entrada"))
        salida = _to_time(s.get("hora_salida"))
        if entrada is None or current < entrada:
            continue
        if salida is not None and current > salida:
            continue
        if best is None or entrada > best[0]:
            best = (entrada, s.get("usuario") or "")
    return best[1] if best else ""


_ICT_TECNICO_CARGOS = ("TECNICO QA",)


def _ict_resolve_adjuster(sessions, ts, linea, ict_num):
    """Quien ajusto la ICT para un cambio detectado en `ts`. '' si nadie aplica.

    Solo un tecnico puede ajustar. El cambio se hace durante la sesion del
    tecnico, pero la pieza con el valor nuevo puede pasar despues (ya con otro
    operador en la maquina). Por eso se toma el ULTIMO tecnico (cargo TECNICO
    QA) cuya hora_entrada <= ts, sin exigir que su sesion cubra ts.
    ponytail: solo mira sesiones del mismo dia calendario que ts; un ajuste
    cruzando medianoche es raro. Ampliar a ts.date()-1 si aparece el caso.
    """
    if not ts:
        return ""
    key = (ts.date().isoformat(), str(linea or ""), str(ict_num or ""))
    candidates = sessions.get(key)
    if not candidates:
        return ""
    current = ts.time()
    best = None  # (hora_entrada, usuario) del ultimo tecnico con entrada <= ts
    for s in candidates:
        if str(s.get("cargo") or "").upper() not in _ICT_TECNICO_CARGOS:
            continue
        entrada = _to_time(s.get("hora_entrada"))
        if entrada is None or entrada > current:
            continue
        if best is None or entrada > best[0]:
            best = (entrada, s.get("usuario") or "")
    return best[1] if best else ""


def _ict_session_bounds(s):
    """(inicio, fin) como datetime de una sesion. fin=None si sigue abierta."""
    fecha = s.get("fecha")
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    entrada = _to_time(s.get("hora_entrada"))
    salida = _to_time(s.get("hora_salida"))
    if fecha is None or entrada is None:
        return None, None
    inicio = datetime.combine(fecha, entrada)
    fin = datetime.combine(fecha, salida) if salida is not None else None
    return inicio, fin


def _ict_sessions_in_range(sessions, primer_test, ultimo_test, linea, ict_num):
    """Sesiones (linea, ict) cuyo tiempo solapa [primer_test, ultimo_test].

    Mira las fechas calendario que toca el rango (cubre jornada nocturna que
    cruza medianoche). Una sesion abierta (fin=None) solapa si empezo antes
    del fin del rango.
    """
    if not primer_test or not ultimo_test:
        return []
    fechas = {primer_test.date().isoformat(), ultimo_test.date().isoformat()}
    out = []
    for fkey in fechas:
        for s in sessions.get((fkey, str(linea or ""), str(ict_num or "")), []):
            inicio, fin = _ict_session_bounds(s)
            if inicio is None:
                continue
            # solape: inicio <= ultimo_test  AND  (fin is None OR fin >= primer_test)
            if inicio <= ultimo_test and (fin is None or fin >= primer_test):
                out.append(s)
    return out


def _ict_operadores_y_ajustes(sessions, primer_test, ultimo_test, linea, ict_num):
    """Para una fila Pass/Fail: operadores que estuvieron y ajustes por tecnico.

    Devuelve dict:
      operadores: [nombres unicos] de sesiones NO-Ajuste que solaparon.
      ajuste_total_seg: suma de duracion_seg de sesiones estado='Ajuste'.
      ajustes: [{"tecnico": nombre, "segundos": n}] por tecnico (sumado).
    """
    solapan = _ict_sessions_in_range(sessions, primer_test, ultimo_test, linea, ict_num)
    operadores = []
    vistos = set()
    ajuste_por_tecnico = {}
    for s in solapan:
        usuario = (s.get("usuario") or "").strip()
        if str(s.get("estado") or "") == "Ajuste":
            seg = int(s.get("duracion_seg") or 0)
            ajuste_por_tecnico[usuario] = ajuste_por_tecnico.get(usuario, 0) + seg
        else:
            if usuario and usuario not in vistos:
                vistos.add(usuario)
                operadores.append(usuario)
    ajustes = [
        {"tecnico": t, "segundos": seg}
        for t, seg in sorted(ajuste_por_tecnico.items(), key=lambda kv: -kv[1])
    ]
    return {
        "operadores": operadores,
        "ajuste_total_seg": sum(a["segundos"] for a in ajustes),
        "ajustes": ajustes,
    }


def _ict_attach_operator(rows):
    """Anota cada fila de history_ict con su `operador` (in-place) y la devuelve.

    Requiere que cada fila traiga `ts` (datetime), `linea` e `ict`. Carga las
    sesiones del rango de fechas presente en `rows` una sola vez.
    """
    fechas = [r["ts"] for r in rows if r.get("ts")]
    if not fechas:
        for r in rows:
            r["operador"] = ""
        return rows
    sessions = _ict_load_operator_sessions(min(fechas), max(fechas))
    for r in rows:
        r["operador"] = _ict_resolve_operator(
            sessions, r.get("ts"), r.get("linea"), r.get("ict")
        )
    return rows


def _ict_format_row(row):
    """Convertir campos fecha/hora a cadenas serializables."""
    if not row:
        return {}

    formatted = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            formatted[key] = value.isoformat(sep=" ")
        elif isinstance(value, date):
            formatted[key] = value.isoformat()
        elif isinstance(value, dt_time):
            formatted[key] = value.strftime("%H:%M:%S")
        elif isinstance(value, timedelta):
            formatted[key] = str(value)
        else:
            formatted[key] = value
    return formatted


def _ict_find_history_record(barcode, ts=None):
    """Buscar el registro resumen que apunta al archivo LGD local."""
    sql = (
        "SELECT barcode, ts, fuente_archivo, linea, ict "
        "FROM history_ict WHERE barcode=%s"
    )
    params = [barcode]
    if ts:
        sql += " AND ts=%s"
        params.append(ts)
    sql += " ORDER BY ts DESC LIMIT 1"
    return execute_query(sql, tuple(params), fetch="one")


def _ict_load_local_parameters(barcode, ts=None):
    """Cargar parametros ICT desde el LGD local (usado por defects y export)."""
    history_row = _ict_find_history_record(barcode, ts)
    if not history_row:
        raise IctLgdNotFoundError("No se encontro el registro ICT solicitado.")

    source_file = (history_row.get("fuente_archivo") or "").strip()
    if not source_file:
        raise IctLgdPathError("El registro no tiene fuente_archivo.")

    lgd_path = resolve_lgd_path(source_file)
    cached_rows = get_lgd_parameters_for_barcode(str(lgd_path), barcode)
    # Copia local porque seteamos linea/ict/fuente_archivo. El resultado de
    # get_lgd_parameters_for_barcode comparte memoria con el cache global.
    rows = [dict(row) for row in cached_rows]
    for row in rows:
        row.setdefault("linea", history_row.get("linea"))
        row.setdefault("ict", history_row.get("ict"))
        row.setdefault("fuente_archivo", source_file)
    return rows, source_file
