"""Endpoints HTTP del modulo Part Planning LG (import del plan diario de LG).

Etapa 1 (2026-07-12): recibir, validar y guardar el plan diario de LG desde
el Excel oficial (hoja "LG"). No calcula LGEMM/ISEMM/pendiente (Etapa 2).

Rutas render:
  GET  /part-planning-ajax                        -> render fragment AJAX

Rutas API:
  POST /api/part-planning/import/preview          -> analizar Excel sin guardar
  POST /api/part-planning/import/confirm          -> guardar plan (transaccional)
  POST /api/part-planning/inventory/import        -> inventario semanal (hoja Part 10)
  POST /api/part-planning/schedule                -> capturar/editar renglon S
  GET  /api/part-planning/plan                    -> plan pivotado P/S/I (parte x fechas)
  GET  /api/part-planning/imports                 -> historial de importaciones

Etapa 2 (2026-07-13): renglones P/S/I. P = lg_plan_daily; S = lg_schedule_daily
(importado de Part 10 y/o capturado en MES); I = proyeccion calculada con la
formula del Excel: I(t) = I(t-1) - P(t) + S(t), I0 = LGEMM+ISEMM+SVC+DIF+
PENDIENTE+REWORK (escalares semanales en lg_part_inventory, hoja "Part 10").

Formato del Excel (verificado contra el archivo real):
  Hoja "LG"; fila 3 = fechas (datetime completos; fallback strings "07-Jul");
  columna B desde fila 4 = numeros de parte; celdas = cantidades o None.

Flujo preview -> confirm: el navegador reenvia el mismo archivo en el confirm
junto con el SHA-256 que devolvio el preview; si el hash no coincide se
rechaza (patron Lista de compras: sin token ni temporales en servidor).
"""

import hashlib
import io
import json
import logging
import math
import os
import re
from datetime import date, datetime, timedelta

import openpyxl
from flask import Blueprint, jsonify, render_template, request, session

from app.db_mysql import execute_query
from app.config_mysql import get_pooled_connection
from app.api.pda.shipping_material import get_dict_cursor
from app.api.shared import login_requerido, requiere_permiso_dropdown

logger = logging.getLogger(__name__)

bp = Blueprint("control_produccion_part_planning", __name__)

PP_PERMISO_PAGINA = "LISTA_CONTROLDEPRODUCCION"
PP_PERMISO_SECCION = "Control de plan de produccion"
PP_PERMISO_BOTON = "Part Planning LG"
# Modulo hermano "Proyeccion" (renglones P/S/I, inventario semanal y schedule)
PROY_PERMISO_BOTON = "Proyeccion"
# Modulo hermano "Plan Proyectado" (generador de lotes tipo hoja LOTE N)
PPY_PERMISO_BOTON = "Plan Proyectado"
PPY_HORAS_TURNO = 9.0  # horas productivas sin tiempo extra (plan-assy-helpers.js)
PPY_FAMILIA_LEN = 9  # ponytail: familia = prefijo del part_no (EBR807574xx); catalogo si hay excepciones
PPY_MARGEN = 1.10  # siempre se planea 10% mas del faltante
PPY_TURNOS = ("DIA", "TIEMPO EXTRA", "NOCHE")
PPY_HORIZONTE_DIAS = 14  # dias hacia adelante para adelantar faltantes futuros
PPY_LINEAS_DEFAULT = "M1,M2,M3"
PPY_PACK_DEFAULT = 20  # std pack asumido en la propuesta de schedule para partes sin registro

PP_SHEET_NAME = "LG"
# Campos de inventario por parte (editables en Proyeccion; suman al I inicial)
PP_INV_FIELDS = ("lgemm", "isemm", "svc", "dif", "pendiente", "rework", "smt", "imd")
PP_MAX_FILE_BYTES = 20 * 1024 * 1024
PP_BATCH_SIZE = 1000
PP_EXTENSIONES = (".xlsx", ".xlsm")
PP_MODOS = ("upsert", "only_positive", "only_new")
PP_MAX_RANGO_DIAS = 120


# =============================
# DDL (llamado desde app/startup_init.py)
# =============================

def init_part_planning_tables():
    """Crea las tablas del modulo Part Planning LG (idempotente)."""
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lg_plan_daily (
            id BIGINT NOT NULL AUTO_INCREMENT,
            part_no VARCHAR(100) NOT NULL,
            plan_date DATE NOT NULL,
            plan_qty INT NOT NULL DEFAULT 0,
            import_id BIGINT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uk_lgpd_part_date (part_no, plan_date),
            KEY idx_lgpd_plan_date (plan_date),
            KEY idx_lgpd_part_no (part_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lg_plan_imports (
            id BIGINT NOT NULL AUTO_INCREMENT,
            original_filename VARCHAR(255) NULL,
            sheet_name VARCHAR(50) NOT NULL DEFAULT 'LG',
            plan_year INT NULL,
            date_from DATE NULL,
            date_to DATE NULL,
            parts_count INT NOT NULL DEFAULT 0,
            dates_count INT NOT NULL DEFAULT 0,
            records_count INT NOT NULL DEFAULT 0,
            zero_records_count INT NOT NULL DEFAULT 0,
            warning_count INT NOT NULL DEFAULT 0,
            import_mode VARCHAR(20) NOT NULL DEFAULT 'upsert',
            file_sha256 VARCHAR(64) NULL,
            imported_by VARCHAR(255) NOT NULL DEFAULT 'SISTEMA',
            imported_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(20) NOT NULL DEFAULT 'COMPLETADO',
            PRIMARY KEY (id),
            KEY idx_lgpi_imported_at (imported_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lg_plan_import_changes (
            id BIGINT NOT NULL AUTO_INCREMENT,
            import_id BIGINT NOT NULL,
            part_no VARCHAR(100) NOT NULL,
            plan_date DATE NOT NULL,
            old_qty INT NULL,
            new_qty INT NOT NULL,
            change_type VARCHAR(10) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_lgpc_import (import_id),
            KEY idx_lgpc_part_date (part_no, plan_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    # Etapa 2: inventario semanal por parte (hoja "Part 10": LGEMM/ISEMM/...)
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lg_part_inventory (
            id BIGINT NOT NULL AUTO_INCREMENT,
            part_no VARCHAR(100) NOT NULL,
            board VARCHAR(100) NULL,
            line VARCHAR(20) NULL,
            lgemm INT NOT NULL DEFAULT 0,
            isemm INT NOT NULL DEFAULT 0,
            svc INT NOT NULL DEFAULT 0,
            dif INT NOT NULL DEFAULT 0,
            pendiente INT NOT NULL DEFAULT 0,
            rework INT NOT NULL DEFAULT 0,
            smt INT NOT NULL DEFAULT 0,
            imd INT NOT NULL DEFAULT 0,
            ref_date DATE NULL,
            import_id BIGINT NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uk_lgpi_part (part_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    # Columnas smt/imd agregadas despues del primer despliegue (ALTER condicional)
    for col_prev, col in (("rework", "smt"), ("smt", "imd")):
        existe = execute_query(
            "SELECT COUNT(*) AS c FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'lg_part_inventory' "
            "AND COLUMN_NAME = %s",
            (col,),
            fetch="one",
        )
        if not existe["c"]:
            execute_query(
                f"ALTER TABLE lg_part_inventory "
                f"ADD COLUMN {col} INT NOT NULL DEFAULT 0 AFTER {col_prev}"
            )

    # Etapa 2: schedule diario (renglon S) capturado en MES o importado de Part 10
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lg_schedule_daily (
            id BIGINT NOT NULL AUTO_INCREMENT,
            part_no VARCHAR(100) NOT NULL,
            sched_date DATE NOT NULL,
            sched_qty INT NOT NULL DEFAULT 0,
            updated_by VARCHAR(255) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uk_lgsd_part_date (part_no, sched_date),
            KEY idx_lgsd_date (sched_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    # Plan Proyectado: lotes propuestos/confirmados tipo hoja "LOTE N"
    # (lot_no NULL hasta confirmar; time/falta/%/familia se calculan al vuelo)
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lg_lote_plan (
            id BIGINT NOT NULL AUTO_INCREMENT,
            plan_date DATE NOT NULL,
            lot_no VARCHAR(20) NULL,
            part_no VARCHAR(100) NOT NULL,
            model VARCHAR(100) NULL,
            main_sub VARCHAR(20) NULL,
            linea VARCHAR(10) NULL,
            turno VARCHAR(15) NOT NULL DEFAULT 'DIA',
            faltante INT NOT NULL DEFAULT 0,
            qty_plan INT NOT NULL DEFAULT 0,
            uph INT NULL,
            estandar_pack INT NULL,
            fisico INT NULL,
            status VARCHAR(12) NOT NULL DEFAULT 'PENDIENTE',
            comentario VARCHAR(255) NULL,
            created_by VARCHAR(80) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR(80) NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            confirmed_by VARCHAR(80) NULL,
            confirmed_at DATETIME NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uk_llp_lot (lot_no),
            KEY idx_llp_plan_date (plan_date),
            KEY idx_llp_part (part_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    # Config del Plan Proyectado (lineas activas configurables)
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lg_pp_config (
            clave VARCHAR(50) NOT NULL,
            valor VARCHAR(255) NULL,
            PRIMARY KEY (clave)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    execute_query(
        "INSERT IGNORE INTO lg_pp_config (clave, valor) VALUES ('lineas_activas', %s)",
        (PPY_LINEAS_DEFAULT,),
    )
    # Lineas permitidas por parte/familia: columna en raw (se configura una
    # vez por familia; aplica a todos los sufijos del mismo prefijo).
    existe = execute_query(
        "SELECT COUNT(*) AS c FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'raw' "
        "AND COLUMN_NAME = 'lineas_permitidas'",
        fetch="one",
    )
    if not existe["c"]:
        execute_query(
            "ALTER TABLE raw ADD COLUMN lineas_permitidas VARCHAR(100) NULL "
            "AFTER estandar_pack"
        )


# =============================
# Parser del Excel (compartido por preview y confirm)
# =============================

def _pp_normalizar_parte(valor):
    """Normaliza el numero de parte de la celda (col B)."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def _pp_detectar_anio(original_filename, override_year):
    """Anio para fechas string ("07-Jul"): override > filename > anio actual."""
    if override_year:
        return int(override_year)
    m = re.search(r"(20\d{2})", original_filename or "")
    if m:
        return int(m.group(1))
    return date.today().year


def _pp_parse_fecha_celda(valor, anio_fallback):
    """Convierte una celda de la fila 3 a date, o None si no es fecha."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        texto = valor.strip()
        for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(texto, fmt).date()
            except ValueError:
                pass
        for fmt in ("%d-%b", "%d/%m"):
            try:
                parcial = datetime.strptime(texto, fmt)
                return date(anio_fallback, parcial.month, parcial.day)
            except ValueError:
                pass
    return None


def _parse_lg_workbook(file_bytes, original_filename="", override_year=None):
    """Parsea el Excel del plan LG.

    Retorna (parsed_dict, None) si el archivo es utilizable, o
    (None, (payload_error, http_status)) si hay error bloqueante.
    """
    def error(msg, status=400):
        return None, ({"success": False, "errors": [msg], "warnings": []}, status)

    ext = os.path.splitext(original_filename or "")[1].lower()
    if ext not in PP_EXTENSIONES:
        return error("Formato no permitido. Solo se aceptan archivos .xlsx o .xlsm.")
    if not file_bytes:
        return error("El archivo esta vacio.")
    if len(file_bytes) > PP_MAX_FILE_BYTES:
        return error("El archivo supera el tamano maximo permitido (20 MB).")

    try:
        wb = openpyxl.load_workbook(
            io.BytesIO(file_bytes), read_only=True, data_only=True
        )
    except Exception as e:
        logger.warning("part_planning: archivo Excel ilegible: %s", e)
        return error("El archivo esta corrupto o no es un Excel valido.")

    try:
        if PP_SHEET_NAME not in wb.sheetnames:
            return error(
                f"No se encontro la hoja '{PP_SHEET_NAME}' en el archivo. "
                f"Hojas disponibles: {', '.join(wb.sheetnames[:10])}"
            )
        ws = wb[PP_SHEET_NAME]

        anio_fallback = _pp_detectar_anio(original_filename, override_year)
        warnings = []

        filas = ws.iter_rows(values_only=True)
        fila_fechas = None
        for idx, fila in enumerate(filas, start=1):
            if idx == 3:
                fila_fechas = fila
                break
        if fila_fechas is None:
            return error("El archivo no tiene fila de fechas (fila 3).")

        # Mapa indice de columna (0-based en la tupla) -> fecha. Desde col C.
        col_fechas = {}
        for ci in range(2, len(fila_fechas)):
            fecha = _pp_parse_fecha_celda(fila_fechas[ci], anio_fallback)
            if fecha is not None:
                col_fechas[ci] = fecha
        if not col_fechas:
            return error("No se encontraron fechas validas en la fila 3.")

        # Filas de datos: parte en col B (indice 1), cantidades en col_fechas.
        records = {}
        partes_vistas = set()
        partes_duplicadas = set()
        celdas_no_numericas = 0
        for fila in filas:  # continua despues de la fila 3
            if len(fila) < 2:
                continue
            part_no = _pp_normalizar_parte(fila[1])
            if not part_no:
                continue
            if part_no in partes_vistas:
                partes_duplicadas.add(part_no)
            partes_vistas.add(part_no)
            for ci, fecha in col_fechas.items():
                valor = fila[ci] if ci < len(fila) else None
                if valor is None or valor == "":
                    qty = 0
                elif isinstance(valor, (int, float)):
                    qty = int(round(valor))
                else:
                    celdas_no_numericas += 1
                    continue
                if qty < 0:
                    warnings.append(
                        f"Cantidad negativa en {part_no} / {fecha.isoformat()}: "
                        f"{qty} se ajusto a 0."
                    )
                    qty = 0
                clave = (part_no, fecha)
                # Duplicados de parte se consolidan sumando.
                records[clave] = records.get(clave, 0) + qty

        if not partes_vistas:
            return error(
                "No se encontraron numeros de parte en la columna B (desde la fila 4)."
            )
        if not records:
            return error("El archivo no contiene registros de plan.")

        if celdas_no_numericas:
            warnings.append(
                f"{celdas_no_numericas} celdas con texto no numerico fueron ignoradas."
            )

        fechas = sorted(set(col_fechas.values()))
        records_count = sum(1 for q in records.values() if q > 0)
        parsed = {
            "plan_year": fechas[0].year,
            "date_from": fechas[0],
            "date_to": fechas[-1],
            "dates": fechas,
            "records": records,
            "parts": sorted(partes_vistas),
            "parts_count": len(partes_vistas),
            "dates_count": len(fechas),
            "records_count": records_count,
            "zero_records_count": len(records) - records_count,
            "duplicated_parts": sorted(partes_duplicadas),
            "warnings": warnings,
            "errors": [],
        }
        return parsed, None
    finally:
        wb.close()


def _pp_compute_warnings(parsed):
    """Advertencias que requieren BD (no bloquean). Muta parsed["warnings"]."""
    warnings = parsed["warnings"]

    dups = parsed["duplicated_parts"]
    if dups:
        listado = ", ".join(dups[:10]) + ("..." if len(dups) > 10 else "")
        warnings.append(
            f"{len(dups)} numeros de parte repetidos se consolidaron sumando: {listado}"
        )

    try:
        rows = execute_query(
            "SELECT DISTINCT TRIM(part_no) AS part_no FROM raw", fetch="all"
        ) or []
        raw_parts = {r["part_no"] for r in rows if r.get("part_no")}
        faltantes = [p for p in parsed["parts"] if p not in raw_parts]
        if faltantes:
            listado = ", ".join(faltantes[:10]) + ("..." if len(faltantes) > 10 else "")
            warnings.append(
                f"{len(faltantes)} numeros de parte no existen en RAW: {listado}"
            )
    except Exception as e:
        logger.warning("part_planning: no se pudo consultar RAW: %s", e)

    hoy = date.today()
    pasadas = [f for f in parsed["dates"] if f < hoy]
    if pasadas:
        warnings.append(
            f"{len(pasadas)} fechas del plan ya pasaron "
            f"({pasadas[0].isoformat()} a {pasadas[-1].isoformat()})."
        )

    try:
        row = execute_query(
            """
            SELECT COUNT(*) AS c, MIN(plan_date) AS f1, MAX(plan_date) AS f2
            FROM lg_plan_daily
            WHERE plan_date BETWEEN %s AND %s
            """,
            (parsed["date_from"], parsed["date_to"]),
            fetch="one",
        )
        if row and int(row.get("c") or 0) > 0:
            warnings.append(
                f"Ya existen {row['c']} registros de plan entre {row['f1']} y "
                f"{row['f2']}; seran afectados segun el modo de importacion."
            )
    except Exception as e:
        logger.warning("part_planning: no se pudo consultar plan existente: %s", e)


def _pp_summary(parsed):
    return {
        "plan_year": parsed["plan_year"],
        "date_from": parsed["date_from"].isoformat(),
        "date_to": parsed["date_to"].isoformat(),
        "parts_count": parsed["parts_count"],
        "dates_count": parsed["dates_count"],
        "records_count": parsed["records_count"],
        "zero_records_count": parsed["zero_records_count"],
        "duplicates_count": len(parsed["duplicated_parts"]),
    }


def _pp_filas_segun_modo(parsed, modo, include_zero):
    """Lista de (part_no, plan_date, qty) a escribir segun el modo."""
    solo_positivos = modo == "only_positive" or not include_zero
    return [
        (part, fecha, qty)
        for (part, fecha), qty in parsed["records"].items()
        if qty > 0 or not solo_positivos
    ]


# =============================
# Parser hoja "Part 10" (inventario semanal LGEMM/ISEMM + schedule)
# =============================

# La hoja cambia de nombre por dia ("Part 10", "Part 14", ...): se busca por patron.
PP_INV_SHEET_RE = re.compile(r"^part\s*\d+\s*$", re.IGNORECASE)


def _pp_buscar_hoja_inventario(sheetnames):
    for nombre in sheetnames:
        if PP_INV_SHEET_RE.match(nombre.strip()):
            return nombre
    return None


def _parse_part10_workbook(file_bytes, original_filename=""):
    """Parsea la hoja 'Part 10': escalares de inventario por parte + renglon S.

    Estructura (verificada contra el archivo real): fila de encabezado con
    'PART NUMBER' en col C; LGEMM..REWORK en cols E-J; linea en col M; tipo de
    renglon (P/S/I) en col N; fechas datetime en el mismo encabezado desde
    col Q. Cada parte ocupa un bloque de 3 renglones P/S/I.

    Retorna (parsed, None) o (None, (payload_error, http_status)).
    """
    def error(msg, status=400):
        return None, ({"success": False, "errors": [msg], "warnings": []}, status)

    ext = os.path.splitext(original_filename or "")[1].lower()
    if ext not in PP_EXTENSIONES:
        return error("Formato no permitido. Solo se aceptan archivos .xlsx o .xlsm.")
    if not file_bytes:
        return error("El archivo esta vacio.")
    if len(file_bytes) > PP_MAX_FILE_BYTES:
        return error("El archivo supera el tamano maximo permitido (20 MB).")

    try:
        wb = openpyxl.load_workbook(
            io.BytesIO(file_bytes), read_only=True, data_only=True
        )
    except Exception as e:
        logger.warning("part_planning: archivo Excel ilegible: %s", e)
        return error("El archivo esta corrupto o no es un Excel valido.")

    try:
        hoja_inv = _pp_buscar_hoja_inventario(wb.sheetnames)
        if not hoja_inv:
            return error("No se encontro una hoja 'Part N' (ej. Part 10, Part 14) en el archivo.")
        ws = wb[hoja_inv]

        warnings = []
        filas = ws.iter_rows(values_only=True)

        # Encabezado: fila con 'PART NUMBER' en col C (indice 2).
        col_fechas = {}
        encontrado = False
        for fila in filas:
            valor = fila[2] if len(fila) > 2 else None
            if isinstance(valor, str) and valor.strip().upper() == "PART NUMBER":
                for ci in range(3, len(fila)):
                    f = _pp_parse_fecha_celda(fila[ci], date.today().year)
                    if f is not None:
                        col_fechas[ci] = f
                encontrado = True
                break
        if not encontrado:
            return error(
                f"No se encontro el encabezado 'PART NUMBER' en la hoja '{hoja_inv}'."
            )
        if not col_fechas:
            return error(f"No se encontraron fechas en el encabezado de '{hoja_inv}'.")

        def escalar(v):
            return int(round(v)) if isinstance(v, (int, float)) else 0

        inventory = {}
        schedules = {}
        parte_actual = None
        for fila in filas:  # continua despues del encabezado
            tipo = str(fila[13]).strip().upper() if len(fila) > 13 and fila[13] else ""
            if tipo == "P":
                part = _pp_normalizar_parte(fila[2] if len(fila) > 2 else None)
                if not part:
                    parte_actual = None
                    continue
                if part in inventory:
                    warnings.append(f"Parte repetida en {hoja_inv}: {part} (se toma la primera).")
                    parte_actual = None
                    continue
                parte_actual = part
                inventory[part] = {
                    "board": (str(fila[3]).strip()[:100] if len(fila) > 3 and fila[3] else None),
                    "line": (str(fila[12]).strip()[:20] if len(fila) > 12 and fila[12] else None),
                    "lgemm": escalar(fila[4] if len(fila) > 4 else None),
                    "isemm": escalar(fila[5] if len(fila) > 5 else None),
                    "svc": escalar(fila[6] if len(fila) > 6 else None),
                    "dif": escalar(fila[7] if len(fila) > 7 else None),
                    "pendiente": escalar(fila[8] if len(fila) > 8 else None),
                    "rework": escalar(fila[9] if len(fila) > 9 else None),
                    "smt": escalar(fila[10] if len(fila) > 10 else None),
                    "imd": escalar(fila[11] if len(fila) > 11 else None),
                }
            elif tipo == "S" and parte_actual:
                for ci, fecha in col_fechas.items():
                    v = fila[ci] if ci < len(fila) else None
                    if isinstance(v, (int, float)) and v > 0:
                        clave = (parte_actual, fecha)
                        schedules[clave] = schedules.get(clave, 0) + int(round(v))

        if not inventory:
            return error(f"No se encontraron partes en la hoja '{hoja_inv}'.")

        fechas = sorted(col_fechas.values())
        return {
            "sheet_name": hoja_inv,
            "ref_date": fechas[0],
            "date_to": fechas[-1],
            "dates_count": len(fechas),
            "inventory": inventory,
            "schedules": schedules,
            "warnings": warnings,
        }, None
    finally:
        wb.close()


# =============================
# RUTAS RENDER
# =============================

@bp.route("/part-planning-ajax")
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PP_PERMISO_BOTON)
def part_planning_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de Part Planning LG."""
    try:
        return render_template("Control de produccion/part_planning_ajax.html")
    except Exception as e:
        logger.error("Error al cargar Part Planning LG: %s", e)
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/proyeccion-ajax")
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PROY_PERMISO_BOTON)
def proyeccion_ajax():
    """Ruta AJAX para el modulo Proyeccion (renglones P/S/I)."""
    try:
        return render_template("Control de produccion/proyeccion_ajax.html")
    except Exception as e:
        logger.error("Error al cargar Proyeccion: %s", e)
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/plan-proyectado-ajax")
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def plan_proyectado_ajax():
    """Ruta AJAX para el modulo Plan Proyectado (generador de lotes)."""
    try:
        return render_template("Control de produccion/plan_proyectado_ajax.html")
    except Exception as e:
        logger.error("Error al cargar Plan Proyectado: %s", e)
        return f"Error al cargar el contenido: {str(e)}", 500


# =============================
# RUTAS API
# =============================

@bp.route("/api/part-planning/import/preview", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PP_PERMISO_BOTON)
def api_pp_import_preview():
    """Analiza el Excel del plan LG sin guardar nada."""
    try:
        archivo = request.files.get("file")
        if archivo is None or not archivo.filename:
            return jsonify({"success": False, "errors": ["No se recibio archivo."]}), 400
        file_bytes = archivo.read()
        override_year = request.form.get("plan_year", type=int)

        parsed, err = _parse_lg_workbook(file_bytes, archivo.filename, override_year)
        if err is not None:
            payload, status = err
            return jsonify(payload), status

        _pp_compute_warnings(parsed)

        sample = sorted(
            (
                (part, fecha, qty)
                for (part, fecha), qty in parsed["records"].items()
                if qty > 0
            ),
            key=lambda x: (x[0], x[1]),
        )[:100]

        return jsonify(
            {
                "success": True,
                "file_sha256": hashlib.sha256(file_bytes).hexdigest(),
                "file": {
                    "name": archivo.filename,
                    "sheet": PP_SHEET_NAME,
                    "size_bytes": len(file_bytes),
                },
                "summary": _pp_summary(parsed),
                "errors": [],
                "warnings": parsed["warnings"],
                "sample_rows": [
                    {"part_no": p, "plan_date": f.isoformat(), "plan_qty": q}
                    for p, f, q in sample
                ],
            }
        )
    except Exception as e:
        logger.error("Error en api_pp_import_preview: %s", e, exc_info=True)
        return jsonify({"success": False, "errors": [f"Error interno: {e}"]}), 500


@bp.route("/api/part-planning/import/confirm", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PP_PERMISO_BOTON)
def api_pp_import_confirm():
    """Guarda el plan LG (transaccional) con auditoria de cambios."""
    conn = None
    cursor = None
    try:
        archivo = request.files.get("file")
        if archivo is None or not archivo.filename:
            return jsonify({"success": False, "errors": ["No se recibio archivo."]}), 400
        file_bytes = archivo.read()

        hash_esperado = (request.form.get("file_sha256") or "").strip().lower()
        if not hash_esperado:
            return (
                jsonify(
                    {
                        "success": False,
                        "errors": ["file_sha256 requerido. Analiza el archivo primero."],
                    }
                ),
                400,
            )
        hash_real = hashlib.sha256(file_bytes).hexdigest()
        if hash_real != hash_esperado:
            return (
                jsonify(
                    {
                        "success": False,
                        "errors": [
                            "El archivo cambio desde la vista previa. "
                            "Vuelve a analizarlo antes de confirmar."
                        ],
                    }
                ),
                400,
            )

        modo = (request.form.get("import_mode") or "upsert").strip()
        if modo not in PP_MODOS:
            return jsonify({"success": False, "errors": [f"Modo invalido: {modo}"]}), 400
        include_zero = (request.form.get("include_zero") or "1").strip().lower() in (
            "1", "true", "on", "si",
        )
        override_year = request.form.get("plan_year", type=int)

        parsed, err = _parse_lg_workbook(file_bytes, archivo.filename, override_year)
        if err is not None:
            payload, status = err
            return jsonify(payload), status
        _pp_compute_warnings(parsed)

        filas = _pp_filas_segun_modo(parsed, modo, include_zero)
        usuario = session.get("usuario") or "SISTEMA"

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)

        # Snapshot de lo existente en el rango para el diff de auditoria.
        cursor.execute(
            "SELECT part_no, plan_date, plan_qty FROM lg_plan_daily "
            "WHERE plan_date BETWEEN %s AND %s",
            (parsed["date_from"], parsed["date_to"]),
        )
        existentes = {
            (r["part_no"], r["plan_date"]): int(r["plan_qty"])
            for r in cursor.fetchall()
        }

        cambios = []  # (part_no, plan_date, old_qty, new_qty, change_type)
        a_escribir = []
        inserted = updated = unchanged = 0
        for part, fecha, qty in filas:
            old = existentes.get((part, fecha))
            if old is None:
                inserted += 1
                cambios.append((part, fecha, None, qty, "INSERT"))
                a_escribir.append((part, fecha, qty))
            elif modo == "only_new":
                unchanged += 1
            elif old != qty:
                updated += 1
                cambios.append((part, fecha, old, qty, "UPDATE"))
                a_escribir.append((part, fecha, qty))
            else:
                unchanged += 1

        cursor.execute(
            """
            INSERT INTO lg_plan_imports
                (original_filename, sheet_name, plan_year, date_from, date_to,
                 parts_count, dates_count, records_count, zero_records_count,
                 warning_count, import_mode, file_sha256, imported_by, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'COMPLETADO')
            """,
            (
                archivo.filename[:255],
                PP_SHEET_NAME,
                parsed["plan_year"],
                parsed["date_from"],
                parsed["date_to"],
                parsed["parts_count"],
                parsed["dates_count"],
                parsed["records_count"],
                parsed["zero_records_count"],
                len(parsed["warnings"]),
                modo,
                hash_real,
                usuario,
            ),
        )
        import_id = cursor.lastrowid

        sql_upsert = (
            "INSERT INTO lg_plan_daily (part_no, plan_date, plan_qty, import_id) "
            "VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE plan_qty = VALUES(plan_qty), "
            "import_id = VALUES(import_id)"
        )
        datos = [(p, f, q, import_id) for p, f, q in a_escribir]
        for i in range(0, len(datos), PP_BATCH_SIZE):
            cursor.executemany(sql_upsert, datos[i : i + PP_BATCH_SIZE])

        sql_cambio = (
            "INSERT INTO lg_plan_import_changes "
            "(import_id, part_no, plan_date, old_qty, new_qty, change_type) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        datos_cambios = [(import_id, p, f, o, n, t) for p, f, o, n, t in cambios]
        for i in range(0, len(datos_cambios), PP_BATCH_SIZE):
            cursor.executemany(sql_cambio, datos_cambios[i : i + PP_BATCH_SIZE])

        conn.commit()

        return jsonify(
            {
                "success": True,
                "import_id": import_id,
                "inserted": inserted,
                "updated": updated,
                "unchanged": unchanged,
                "date_from": parsed["date_from"].isoformat(),
                "date_to": parsed["date_to"].isoformat(),
                "warnings": parsed["warnings"],
            }
        )
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error("Error en api_pp_import_confirm: %s", e, exc_info=True)
        return jsonify({"success": False, "errors": [f"Error interno: {e}"]}), 500
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.autocommit(True)
                conn.close()
            except Exception:
                pass


@bp.route("/api/part-planning/inventory/import", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PROY_PERMISO_BOTON)
def api_pp_inventory_import():
    """Importa inventario semanal (LGEMM/ISEMM/...) + schedules de la hoja Part 10."""
    conn = None
    cursor = None
    try:
        archivo = request.files.get("file")
        if archivo is None or not archivo.filename:
            return jsonify({"success": False, "errors": ["No se recibio archivo."]}), 400
        file_bytes = archivo.read()

        parsed, err = _parse_part10_workbook(file_bytes, archivo.filename)
        if err is not None:
            payload, status = err
            return jsonify(payload), status

        usuario = session.get("usuario") or "SISTEMA"
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        # ref_date = lunes actual (igual que la captura manual): el inventario
        # importado ya incluye lo producido antes; arrancar la proyeccion en la
        # primera fecha de la hoja restaria plan y sumaria schedules pasados dos veces.
        hoy = date.today()
        ref_lunes = hoy - timedelta(days=hoy.weekday())

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)

        cursor.execute(
            """
            INSERT INTO lg_plan_imports
                (original_filename, sheet_name, plan_year, date_from, date_to,
                 parts_count, dates_count, records_count, zero_records_count,
                 warning_count, import_mode, file_sha256, imported_by, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, %s, 'inventory', %s, %s, 'COMPLETADO')
            """,
            (
                archivo.filename[:255],
                parsed["sheet_name"],
                parsed["ref_date"].year,
                parsed["ref_date"],
                parsed["date_to"],
                len(parsed["inventory"]),
                parsed["dates_count"],
                len(parsed["schedules"]),
                len(parsed["warnings"]),
                file_hash,
                usuario,
            ),
        )
        import_id = cursor.lastrowid

        sql_inv = (
            "INSERT INTO lg_part_inventory "
            "(part_no, board, line, lgemm, isemm, svc, dif, pendiente, rework, "
            " smt, imd, ref_date, import_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE board=VALUES(board), line=VALUES(line), "
            "lgemm=VALUES(lgemm), isemm=VALUES(isemm), svc=VALUES(svc), "
            "dif=VALUES(dif), pendiente=VALUES(pendiente), rework=VALUES(rework), "
            "smt=VALUES(smt), imd=VALUES(imd), "
            "ref_date=VALUES(ref_date), import_id=VALUES(import_id)"
        )
        datos_inv = [
            (p, d["board"], d["line"], d["lgemm"], d["isemm"], d["svc"],
             d["dif"], d["pendiente"], d["rework"], d["smt"], d["imd"],
             ref_lunes, import_id)
            for p, d in parsed["inventory"].items()
        ]
        for i in range(0, len(datos_inv), PP_BATCH_SIZE):
            cursor.executemany(sql_inv, datos_inv[i : i + PP_BATCH_SIZE])

        sql_sched = (
            "INSERT INTO lg_schedule_daily (part_no, sched_date, sched_qty, updated_by) "
            "VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE sched_qty=VALUES(sched_qty), "
            "updated_by=VALUES(updated_by)"
        )
        datos_sched = [
            (p, f, q, usuario) for (p, f), q in parsed["schedules"].items()
        ]
        for i in range(0, len(datos_sched), PP_BATCH_SIZE):
            cursor.executemany(sql_sched, datos_sched[i : i + PP_BATCH_SIZE])

        conn.commit()

        return jsonify(
            {
                "success": True,
                "import_id": import_id,
                "parts": len(parsed["inventory"]),
                "schedules": len(parsed["schedules"]),
                "ref_date": ref_lunes.isoformat(),
                "date_to": parsed["date_to"].isoformat(),
                "warnings": parsed["warnings"],
            }
        )
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error("Error en api_pp_inventory_import: %s", e, exc_info=True)
        return jsonify({"success": False, "errors": [f"Error interno: {e}"]}), 500
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.autocommit(True)
                conn.close()
            except Exception:
                pass


@bp.route("/api/part-planning/schedule/sync-excel", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PROY_PERMISO_BOTON)
def api_pp_schedule_sync_excel():
    """TEMPORAL: sincroniza SOLO el schedule (renglon S) desde la hoja Part N.

    Reemplaza por parte: para cada parte que trae el Excel, borra su schedule
    actual en el rango de fechas del archivo y lo repone con el del Excel. Las
    partes que no estan en el Excel no se tocan. No modifica el inventario.
    """
    conn = None
    cursor = None
    try:
        archivo = request.files.get("file")
        if archivo is None or not archivo.filename:
            return jsonify({"success": False, "errors": ["No se recibio archivo."]}), 400
        file_bytes = archivo.read()

        parsed, err = _parse_part10_workbook(file_bytes, archivo.filename)
        if err is not None:
            payload, status = err
            return jsonify(payload), status

        usuario = session.get("usuario") or "SISTEMA"
        # Schedules agrupados por parte; rango de fechas real del archivo
        por_parte = {}
        for (p, f), q in parsed["schedules"].items():
            por_parte.setdefault(p, []).append((f, int(q)))
        rango_desde = parsed["ref_date"]
        rango_hasta = parsed["date_to"]

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)

        partes = list(por_parte)
        borradas = 0
        for i in range(0, len(partes), PP_BATCH_SIZE):
            lote = partes[i : i + PP_BATCH_SIZE]
            placeholders = ", ".join(["%s"] * len(lote))
            cursor.execute(
                "DELETE FROM lg_schedule_daily "
                f"WHERE part_no IN ({placeholders}) AND sched_date BETWEEN %s AND %s",
                tuple(lote) + (rango_desde, rango_hasta),
            )
            borradas += cursor.rowcount or 0

        datos = [
            (p, f, q, usuario)
            for p, celdas in por_parte.items()
            for (f, q) in celdas
            if q > 0
        ]
        for i in range(0, len(datos), PP_BATCH_SIZE):
            cursor.executemany(
                "INSERT INTO lg_schedule_daily (part_no, sched_date, sched_qty, updated_by) "
                "VALUES (%s, %s, %s, %s)",
                datos[i : i + PP_BATCH_SIZE],
            )
        conn.commit()

        return jsonify(
            {
                "success": True,
                "sheet_name": parsed["sheet_name"],
                "parts": len(partes),
                "schedules": len(datos),
                "replaced": borradas,
                "date_from": rango_desde.isoformat(),
                "date_to": rango_hasta.isoformat(),
            }
        )
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error("Error en api_pp_schedule_sync_excel: %s", e, exc_info=True)
        return jsonify({"success": False, "errors": [f"Error interno: {e}"]}), 500
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.autocommit(True)
                conn.close()
            except Exception:
                pass


@bp.route("/api/part-planning/schedule", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PROY_PERMISO_BOTON)
def api_pp_schedule_save():
    """Captura/edita el schedule (renglon S) de una parte en una fecha."""
    try:
        data = request.get_json(silent=True) or {}
        part_no = (data.get("part_no") or "").strip()
        fecha_txt = (data.get("sched_date") or "").strip()
        if not part_no or not fecha_txt:
            return jsonify({"success": False, "error": "part_no y sched_date requeridos"}), 400
        try:
            fecha = datetime.strptime(fecha_txt, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "sched_date invalida"}), 400

        qty_raw = data.get("sched_qty")
        usuario = session.get("usuario") or "SISTEMA"

        if qty_raw is None or str(qty_raw).strip() == "" or int(qty_raw) <= 0:
            execute_query(
                "DELETE FROM lg_schedule_daily WHERE part_no = %s AND sched_date = %s",
                (part_no, fecha),
            )
            return jsonify({"success": True, "part_no": part_no,
                            "sched_date": fecha.isoformat(), "sched_qty": None})

        qty = int(qty_raw)
        execute_query(
            "INSERT INTO lg_schedule_daily (part_no, sched_date, sched_qty, updated_by) "
            "VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE sched_qty=VALUES(sched_qty), updated_by=VALUES(updated_by)",
            (part_no, fecha, qty, usuario),
        )
        return jsonify({"success": True, "part_no": part_no,
                        "sched_date": fecha.isoformat(), "sched_qty": qty})
    except Exception as e:
        logger.error("Error en api_pp_schedule_save: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def _ppy_simular_schedule(fecha_ini, fecha_fin):
    """Propuesta de schedule dia a dia para cubrir faltantes del rango.

    Mismo motor que Plan Proyectado (+10%, caja cerrada, familias, lineas
    permitidas, 9 h por linea activa menos lotes confirmados). Se simula en
    orden cronologico: lo propuesto un dia sube la I de los dias siguientes,
    y lo que no cupo reaparece como faltante al dia siguiente.
    No escribe nada. Retorna (propuestas, partes_omitidas).
    """
    lineas_activas = _ppy_config_lineas()
    proy = _ppy_proyeccion_rango(fecha_ini, fecha_fin)
    partes = list(proy)
    datos_raw = _ppy_datos_raw(partes)
    perm_parte, perm_familia = _ppy_lineas_permitidas_map()

    info = {}
    for p in partes:
        r = datos_raw.get(p) or {}
        pack = r.get("estandar_pack")
        info[p] = {
            "pack": int(pack) if pack else None,
            "uph": _ppy_parse_uph(r.get("uph")),
            "model": r.get("model"),
            "main_sub": r.get("sub_assy"),
            "line": proy[p]["line"],
            "permitidas": perm_parte.get(p) or perm_familia.get(_ppy_familia(p)),
        }

    horas_conf = {}
    rows = execute_query(
        "SELECT plan_date, linea, qty_plan, uph FROM lg_lote_plan "
        "WHERE plan_date BETWEEN %s AND %s AND status = 'CONFIRMADO'",
        (fecha_ini, fecha_fin),
        fetch="all",
    ) or []
    for r in rows:
        f = r["plan_date"].date() if isinstance(r["plan_date"], datetime) else r["plan_date"]
        l = (r.get("linea") or "").upper()
        if r.get("uph"):
            horas_conf[(f, l)] = horas_conf.get((f, l), 0.0) + int(r["qty_plan"] or 0) / int(r["uph"])

    propuestas = []
    acum = {p: 0 for p in partes}
    omitidas = set()
    d = fecha_ini
    while d <= fecha_fin:
        candidatos = []
        for p in partes:
            base = proy[p]["proj"].get(d)
            if base is None:
                continue
            i_d = base + acum[p]
            if i_d < 0:
                candidatos.append(
                    {"part_no": p, "falt_total": -i_d, "falt_hoy": -i_d,
                     "primera_falta": d, **info[p]}
                )
        if candidatos:
            horas_rest = {
                l: PPY_HORAS_TURNO - horas_conf.get((d, l), 0.0) for l in lineas_activas
            }
            lotes, fuera = _ppy_armar_lotes(
                candidatos, lineas_activas, horas_rest, estricto=False
            )
            for l in lotes:
                propuestas.append(
                    {"part_no": l["part_no"], "sched_date": d.isoformat(), "qty": l["qty"]}
                )
                acum[l["part_no"]] += l["qty"]
            for f in fuera:
                omitidas.add(f["part_no"] + " (" + f["motivo"] + ")")
        d += timedelta(days=1)
    return propuestas, sorted(omitidas)


@bp.route("/api/part-planning/schedule/proponer", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PROY_PERMISO_BOTON)
def api_pp_schedule_proponer():
    """Calcula la propuesta de schedule del rango visible (sin guardar)."""
    try:
        data = request.get_json(silent=True) or {}
        hoy = date.today()
        date_from = _ppy_parse_fecha(data.get("date_from")) or hoy
        date_to = _ppy_parse_fecha(data.get("date_to")) or (date_from + timedelta(days=6))
        if date_to < date_from:
            date_from, date_to = date_to, date_from
        date_from = max(date_from, hoy)  # no se propone produccion en el pasado
        if date_to < date_from:
            return jsonify({"success": False, "error": "El rango ya paso; no hay dias por proponer."}), 400
        if (date_to - date_from).days > PP_MAX_RANGO_DIAS:
            return jsonify({"success": False, "error": f"Rango maximo {PP_MAX_RANGO_DIAS} dias"}), 400

        propuestas, omitidas = _ppy_simular_schedule(date_from, date_to)
        # Schedule actual de las celdas propuestas (para el modal de revision)
        if propuestas:
            partes_prop = list({p["part_no"] for p in propuestas})
            placeholders = ", ".join(["%s"] * len(partes_prop))
            rows = execute_query(
                "SELECT part_no, sched_date, sched_qty FROM lg_schedule_daily "
                f"WHERE sched_date BETWEEN %s AND %s AND part_no IN ({placeholders})",
                tuple([date_from, date_to] + partes_prop),
                fetch="all",
            ) or []
            actual = {}
            for r in rows:
                f = r["sched_date"].date() if isinstance(r["sched_date"], datetime) else r["sched_date"]
                actual[(r["part_no"], f.isoformat())] = int(r["sched_qty"])
            for p in propuestas:
                p["sched_actual"] = actual.get((p["part_no"], p["sched_date"]))
        return jsonify(
            {
                "success": True,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "proposals": propuestas,
                "total_qty": sum(p["qty"] for p in propuestas),
                "partes": len({p["part_no"] for p in propuestas}),
                "omitidas": omitidas[:20],
                "omitidas_count": len(omitidas),
            }
        )
    except Exception as e:
        logger.error("Error en api_pp_schedule_proponer: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/part-planning/schedule/proponer/aplicar", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PROY_PERMISO_BOTON)
def api_pp_schedule_aplicar():
    """Aplica la propuesta: SUMA cada cantidad al schedule existente."""
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        items = data.get("proposals") or []
        if not items or not isinstance(items, list):
            return jsonify({"success": False, "error": "Sin propuestas que aplicar"}), 400
        if len(items) > 5000:
            return jsonify({"success": False, "error": "Demasiadas propuestas"}), 400

        usuario = session.get("usuario") or "SISTEMA"
        filas = []
        for it in items:
            p = (it.get("part_no") or "").strip()
            f = _ppy_parse_fecha(it.get("sched_date"))
            try:
                q = int(it.get("qty"))
            except (TypeError, ValueError):
                q = 0
            if not p or not f or q <= 0:
                return jsonify({"success": False, "error": "Propuesta invalida"}), 400
            filas.append((p, f, q, usuario))

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)
        for i in range(0, len(filas), PP_BATCH_SIZE):
            cursor.executemany(
                "INSERT INTO lg_schedule_daily (part_no, sched_date, sched_qty, updated_by) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE sched_qty = sched_qty + VALUES(sched_qty), "
                "updated_by = VALUES(updated_by)",
                filas[i : i + PP_BATCH_SIZE],
            )
        conn.commit()
        return jsonify({"success": True, "aplicadas": len(filas)})
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error("Error en api_pp_schedule_aplicar: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.autocommit(True)
                conn.close()
            except Exception:
                pass


@bp.route("/api/part-planning/inventory/field", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PROY_PERMISO_BOTON)
def api_pp_inventory_field():
    """Captura/edita un campo de inventario (LGEMM, ISEMM, SVC, ...) de una parte.

    Al editar manualmente, la fecha de referencia del calculo de I pasa al
    lunes de la semana actual (el inventario capturado es de esta semana).
    """
    try:
        data = request.get_json(silent=True) or {}
        part_no = (data.get("part_no") or "").strip()
        campo = (data.get("field") or "").strip().lower()
        if not part_no:
            return jsonify({"success": False, "error": "part_no requerido"}), 400
        if campo not in PP_INV_FIELDS:
            return jsonify({"success": False, "error": f"Campo invalido: {campo}"}), 400

        valor_raw = data.get("value")
        try:
            valor = int(valor_raw) if valor_raw not in (None, "") else 0
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Valor invalido"}), 400

        hoy = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())
        # campo esta validado contra PP_INV_FIELDS (whitelist)
        execute_query(
            f"INSERT INTO lg_part_inventory (part_no, {campo}, ref_date) "
            "VALUES (%s, %s, %s) "
            f"ON DUPLICATE KEY UPDATE {campo}=VALUES({campo}), ref_date=VALUES(ref_date)",
            (part_no, valor, lunes),
        )
        return jsonify(
            {
                "success": True,
                "part_no": part_no,
                "field": campo,
                "value": valor,
                "ref_date": lunes.isoformat(),
            }
        )
    except Exception as e:
        logger.error("Error en api_pp_inventory_field: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/part-planning/plan", methods=["GET"])
@login_requerido
def api_pp_plan():
    """Plan importado pivotado: filas = partes, columnas = fechas del rango."""
    try:
        hoy = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())
        try:
            date_from = datetime.strptime(
                request.args.get("date_from") or lunes.isoformat(), "%Y-%m-%d"
            ).date()
            date_to = datetime.strptime(
                request.args.get("date_to")
                or (lunes + timedelta(days=6)).isoformat(),
                "%Y-%m-%d",
            ).date()
        except ValueError:
            return jsonify({"success": False, "error": "Fechas invalidas"}), 400
        if date_to < date_from:
            date_from, date_to = date_to, date_from
        if (date_to - date_from).days > PP_MAX_RANGO_DIAS:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Rango maximo {PP_MAX_RANGO_DIAS} dias",
                    }
                ),
                400,
            )

        part = (request.args.get("part") or "").strip()
        page = max(request.args.get("page", type=int) or 1, 1)
        page_size = min(max(request.args.get("page_size", type=int) or 50, 1), 200)
        # Solo faltantes: partes cuya proyeccion I cae en negativo en el rango.
        # Se calcula sobre todas las partes del rango y se pagina en Python.
        only_shortage = (request.args.get("only_shortage") or "").strip().lower() in (
            "1", "true", "on",
        )

        where = "WHERE plan_date BETWEEN %s AND %s"
        params = [date_from, date_to]
        if part:
            where += " AND part_no LIKE %s"
            params.append(f"%{part}%")

        total_row = execute_query(
            f"SELECT COUNT(DISTINCT part_no) AS c FROM lg_plan_daily {where}",
            tuple(params),
            fetch="one",
        )
        total_parts = int((total_row or {}).get("c") or 0)

        if only_shortage:
            partes = execute_query(
                f"SELECT DISTINCT part_no FROM lg_plan_daily {where} ORDER BY part_no",
                tuple(params),
                fetch="all",
            ) or []
        else:
            partes = execute_query(
                f"SELECT DISTINCT part_no FROM lg_plan_daily {where} "
                "ORDER BY part_no LIMIT %s OFFSET %s",
                tuple(params + [page_size, (page - 1) * page_size]),
                fetch="all",
            ) or []
        parte_list = [r["part_no"] for r in partes]

        filas = []
        if parte_list:
            placeholders = ", ".join(["%s"] * len(parte_list))
            datos = execute_query(
                "SELECT part_no, plan_date, plan_qty FROM lg_plan_daily "
                f"WHERE plan_date BETWEEN %s AND %s AND part_no IN ({placeholders}) "
                "ORDER BY part_no, plan_date",
                tuple([date_from, date_to] + parte_list),
                fetch="all",
            ) or []
            por_parte = {p: {} for p in parte_list}
            for r in datos:
                fecha = r["plan_date"]
                if isinstance(fecha, datetime):
                    fecha = fecha.date()
                por_parte[r["part_no"]][fecha.isoformat()] = int(r["plan_qty"])

            def _a_date(v):
                return v.date() if isinstance(v, datetime) else v

            # Demanda total de LG por parte desde hoy (todo el plan importado,
            # independiente del rango visible) — "cuanto ocupa LG".
            req_rows = execute_query(
                "SELECT part_no, SUM(plan_qty) AS req FROM lg_plan_daily "
                f"WHERE plan_date >= %s AND part_no IN ({placeholders}) "
                "GROUP BY part_no",
                tuple([date.today()] + parte_list),
                fetch="all",
            ) or []
            req_por_parte = {r["part_no"]: int(r["req"] or 0) for r in req_rows}

            # Inventario semanal (escalares Part 10) por parte
            inv_rows = execute_query(
                f"SELECT * FROM lg_part_inventory WHERE part_no IN ({placeholders})",
                tuple(parte_list),
                fetch="all",
            ) or []
            inv_por_parte = {}
            for r in inv_rows:
                ref = _a_date(r.get("ref_date"))
                escalares = {k: int(r.get(k) or 0) for k in PP_INV_FIELDS}
                inv_por_parte[r["part_no"]] = {
                    "board": r.get("board"),
                    "line": r.get("line"),
                    **escalares,
                    "i0": sum(escalares.values()),
                    "ref_date": ref.isoformat() if ref else None,
                    "_ref": ref,
                }

            # Schedule (renglon S) en el rango consultado
            sched_rows = execute_query(
                "SELECT part_no, sched_date, sched_qty FROM lg_schedule_daily "
                f"WHERE sched_date BETWEEN %s AND %s AND part_no IN ({placeholders})",
                tuple([date_from, date_to] + parte_list),
                fetch="all",
            ) or []
            sched_por_parte = {p: {} for p in parte_list}
            for r in sched_rows:
                f = _a_date(r["sched_date"])
                sched_por_parte[r["part_no"]][f.isoformat()] = int(r["sched_qty"])

            # Arrastre de I: acumulados de P y S entre ref_date y date_from-1
            prev_plan = {}
            prev_sched = {}
            refs = [d["_ref"] for d in inv_por_parte.values() if d["_ref"]]
            if refs and min(refs) < date_from:
                min_ref = min(refs)
                for tabla, col_f, col_q, destino in (
                    ("lg_plan_daily", "plan_date", "plan_qty", prev_plan),
                    ("lg_schedule_daily", "sched_date", "sched_qty", prev_sched),
                ):
                    rows_prev = execute_query(
                        f"SELECT part_no, {col_f} AS f, {col_q} AS q FROM {tabla} "
                        f"WHERE {col_f} >= %s AND {col_f} < %s "
                        f"AND part_no IN ({placeholders})",
                        tuple([min_ref, date_from] + parte_list),
                        fetch="all",
                    ) or []
                    for r in rows_prev:
                        inv = inv_por_parte.get(r["part_no"])
                        if inv and inv["_ref"] and _a_date(r["f"]) >= inv["_ref"]:
                            destino[r["part_no"]] = destino.get(r["part_no"], 0) + int(r["q"])

            fechas_rango = [
                date_from + timedelta(days=i)
                for i in range((date_to - date_from).days + 1)
            ]
            for p in parte_list:
                qty = por_parte[p]
                sched = sched_por_parte.get(p, {})
                inv = inv_por_parte.get(p)
                # Proyeccion I (formula del Excel): I(t) = I(t-1) - P(t) + S(t),
                # I0 = LGEMM+ISEMM+SVC+DIF+PENDIENTE+REWORK desde ref_date.
                proj = {}
                if inv and inv["_ref"]:
                    carry = inv["i0"] - prev_plan.get(p, 0) + prev_sched.get(p, 0)
                    for f in fechas_rango:
                        iso = f.isoformat()
                        if f < inv["_ref"]:
                            proj[iso] = None
                        else:
                            carry = carry - qty.get(iso, 0) + sched.get(iso, 0)
                            proj[iso] = carry
                filas.append(
                    {
                        "part_no": p,
                        "total": sum(qty.values()),
                        "qty": qty,
                        "req_lg": req_por_parte.get(p, 0),
                        "sched": sched,
                        "sched_total": sum(sched.values()),
                        "inv": ({k: v for k, v in inv.items() if k != "_ref"} if inv else None),
                        "proj": proj,
                    }
                )

            if only_shortage:
                # Solo faltantes accionables: dias de HOY en adelante (un
                # negativo de un dia pasado ya no se puede producir).
                hoy_iso = date.today().isoformat()
                filas = [
                    f for f in filas
                    if any(
                        v is not None and v < 0 and iso >= hoy_iso
                        for iso, v in f["proj"].items()
                    )
                ]
                total_parts = len(filas)
                filas = filas[(page - 1) * page_size : page * page_size]

        num_dias = (date_to - date_from).days + 1
        fechas = [
            (date_from + timedelta(days=i)).isoformat() for i in range(num_dias)
        ]

        return jsonify(
            {
                "success": True,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "dates": fechas,
                "rows": filas,
                "total_parts": total_parts,
                "page": page,
                "page_size": page_size,
            }
        )
    except Exception as e:
        logger.error("Error en api_pp_plan: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/part-planning/imports", methods=["GET"])
@login_requerido
def api_pp_imports():
    """Historial de importaciones del plan LG."""
    try:
        limit = min(max(request.args.get("limit", type=int) or 20, 1), 100)
        rows = execute_query(
            "SELECT * FROM lg_plan_imports ORDER BY imported_at DESC LIMIT %s",
            (limit,),
            fetch="all",
        ) or []
        for r in rows:
            for k, v in r.items():
                if isinstance(v, (datetime, date)):
                    r[k] = v.isoformat(sep=" ") if isinstance(v, datetime) else v.isoformat()
        return jsonify({"success": True, "imports": rows})
    except Exception as e:
        logger.error("Error en api_pp_imports: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# =============================
# PLAN PROYECTADO (generador de lotes tipo hoja "LOTE N" del Excel)
#
# Reglas (confirmadas con el usuario):
#   - faltante = |I proyectado negativo| a la fecha (formula de Proyeccion)
#   - se planea faltante + 10%, redondeado ARRIBA a caja cerrada (estandar_pack)
#   - familias juntas (prefijo del part_no) y por linea
#   - por linea la suma de horas (qty/UPH) debe caber en 9 h sin tiempo extra
#   - los lotes quedan PENDIENTE sin numero; al confirmar se numeran
#     I<YYYYMMDD>-#### (consecutivo global del dia) y su qty se SUMA al
#     renglon S (lg_schedule_daily) de Proyeccion
# =============================


def _ppy_familia(part_no):
    return (part_no or "")[:PPY_FAMILIA_LEN]


def _ppy_qty_pack(faltante, pack):
    """Cantidad a planear: faltante + 10%, redondeada arriba a caja cerrada."""
    try:
        pack = int(pack) if pack and int(pack) > 0 else 1
    except (TypeError, ValueError):
        pack = 1
    # round() evita que el float de *1.10 suba de mas (100*1.1 = 110.0000...01)
    objetivo = round(faltante * PPY_MARGEN, 6)
    return int(math.ceil(objetivo / pack)) * pack


def _ppy_parse_uph(valor):
    """UPH de raw es varchar: parseo defensivo, None si no es numero positivo."""
    try:
        n = int(float(str(valor).strip()))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _ppy_parse_fecha(texto):
    try:
        return datetime.strptime((texto or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _ppy_config_lineas():
    """Lineas activas configurables (CSV en lg_pp_config)."""
    try:
        row = execute_query(
            "SELECT valor FROM lg_pp_config WHERE clave = 'lineas_activas'",
            fetch="one",
        )
    except Exception:
        row = None
    texto = (row or {}).get("valor") or PPY_LINEAS_DEFAULT
    lineas = []
    for l in texto.split(","):
        l = l.strip().upper()[:10]
        if l and l not in lineas:
            lineas.append(l)
    return lineas or [x.strip() for x in PPY_LINEAS_DEFAULT.split(",")]


def _ppy_lineas_permitidas_map():
    """Lineas permitidas desde raw.lineas_permitidas (CSV, ej. 'M1,M2,M4').

    Se configura una sola vez por familia: basta capturarla en cualquier
    parte de la familia y aplica a todos los sufijos (EBR807574xx).
    Retorna ({part_no: [lineas]}, {familia: [lineas]}).
    """
    try:
        rows = execute_query(
            "SELECT TRIM(part_no) AS part_no, lineas_permitidas FROM raw "
            "WHERE lineas_permitidas IS NOT NULL AND TRIM(lineas_permitidas) <> ''",
            fetch="all",
        ) or []
    except Exception:
        return {}, {}
    por_parte = {}
    por_familia = {}
    for r in rows:
        lineas = [l.strip().upper() for l in (r["lineas_permitidas"] or "").split(",") if l.strip()]
        if not lineas:
            continue
        por_parte[r["part_no"]] = lineas
        por_familia.setdefault(_ppy_familia(r["part_no"]), lineas)
    return por_parte, por_familia


def _ppy_proyeccion_rango(fecha_ini, fecha_fin):
    """I proyectado por parte para cada dia de [fecha_ini, fecha_fin].

    Misma formula que Proyeccion: I(t) = I(t-1) - P(t) + S(t) desde ref_date.
    Como I ya incluye los S confirmados/capturados, regenerar no duplica.
    Retorna {part_no: {"line": str|None, "proj": {date: int}}}.
    """
    inv_rows = execute_query("SELECT * FROM lg_part_inventory", fetch="all") or []
    base = {}
    refs = {}
    for r in inv_rows:
        ref = r.get("ref_date")
        if isinstance(ref, datetime):
            ref = ref.date()
        i0 = sum(int(r.get(k) or 0) for k in PP_INV_FIELDS)
        base[r["part_no"]] = {"line": r.get("line"), "i0": i0}
        if ref and ref <= fecha_fin:
            refs[r["part_no"]] = ref

    movs = {}  # (part, date) -> delta (-P + S)
    if refs:
        min_ref = min(refs.values())
        for tabla, col_f, col_q, signo in (
            ("lg_plan_daily", "plan_date", "plan_qty", -1),
            ("lg_schedule_daily", "sched_date", "sched_qty", 1),
        ):
            rows = execute_query(
                f"SELECT part_no, {col_f} AS f, {col_q} AS q FROM {tabla} "
                f"WHERE {col_f} BETWEEN %s AND %s",
                (min_ref, fecha_fin),
                fetch="all",
            ) or []
            for r in rows:
                ref = refs.get(r["part_no"])
                if not ref:
                    continue
                f = r["f"].date() if isinstance(r["f"], datetime) else r["f"]
                if f >= ref:
                    clave = (r["part_no"], f)
                    movs[clave] = movs.get(clave, 0) + signo * int(r["q"] or 0)

    resultado = {}
    for p, d in base.items():
        ref = refs.get(p)
        proj = {}
        carry = d["i0"]
        if ref:
            f = ref
            while f <= fecha_fin:
                carry += movs.get((p, f), 0)
                if f >= fecha_ini:
                    proj[f] = carry
                f += timedelta(days=1)
        else:
            f = fecha_ini
            while f <= fecha_fin:
                proj[f] = carry
                f += timedelta(days=1)
        resultado[p] = {"line": d["line"], "proj": proj}
    return resultado


def _ppy_armar_lotes(candidatos, lineas_activas, horas_rest, estricto=True):
    """Ajusta los candidatos a las horas disponibles por linea (9 h sin TE).

    candidatos: [{part_no, falt_total, falt_hoy, primera_falta(date), line,
                  uph, pack, model, main_sub}]
    horas_rest: {linea: horas disponibles} (se muta al asignar).

    Orden: familias con la falta mas proxima primero (los faltantes de HOY van
    antes que los adelantos); familia junta y de preferencia en la misma linea.
    Si un lote no cabe completo se planea parcial a caja cerrada ("lo que se
    pueda meter"). Retorna (lotes, fuera).

    estricto=True (Plan Proyectado): sin UPH o sin pack la parte no se genera.
    estricto=False (propuesta de schedule): pack faltante se asume
    PPY_PACK_DEFAULT y sin UPH la parte entra sin presupuesto de horas.
    """
    familias = {}
    for c in candidatos:
        familias.setdefault(_ppy_familia(c["part_no"]), []).append(c)
    orden = sorted(
        familias.values(),
        key=lambda g: (min(c["primera_falta"] for c in g),
                       -max(c["falt_total"] for c in g)),
    )

    lotes = []
    fuera = []
    for grupo in orden:
        grupo.sort(key=lambda c: (c["primera_falta"], -c["falt_total"], c["part_no"]))
        linea_familia = None
        for c in grupo:
            pack = c["pack"] if c["pack"] and c["pack"] > 0 else None
            if estricto:
                # Sin UPH no hay presupuesto de horas y sin pack no hay caja
                # cerrada: la parte no se genera (visible en no_incluidos).
                faltan = []
                if not c["uph"]:
                    faltan.append("UPH")
                if not pack:
                    faltan.append("pack")
                if faltan:
                    fuera.append({"part_no": c["part_no"],
                                  "qty": _ppy_qty_pack(c["falt_total"], pack),
                                  "motivo": "sin " + " ni ".join(faltan) + " en raw"})
                    continue
            elif not pack:
                pack = PPY_PACK_DEFAULT

            qty_obj = _ppy_qty_pack(c["falt_total"], pack)
            adelanto = c["falt_hoy"] <= 0

            if not c["uph"]:
                # Solo en modo laxo: entra completo sin consumir horas
                lotes.append({**c, "qty": qty_obj,
                              "linea": linea_familia or c.get("line"),
                              "comentario": None})
                continue

            # Linea: la de la familia > la preferida de la parte > la mas
            # libre, siempre dentro de las permitidas (raw.lineas_permitidas)
            permitidas = c.get("permitidas")

            def _permitida(l):
                return permitidas is None or l in permitidas

            opciones = []
            for cand in (linea_familia, (c.get("line") or "").upper() or None):
                if cand in horas_rest and _permitida(cand) and cand not in opciones:
                    opciones.append(cand)
            opciones += sorted(
                (l for l in horas_rest if l not in opciones and _permitida(l)),
                key=lambda l: -horas_rest[l],
            )
            if not opciones:
                fuera.append({"part_no": c["part_no"], "qty": qty_obj,
                              "motivo": "sus lineas (" + ",".join(permitidas or []) +
                                        ") no estan activas"})
                continue
            elegido = None
            qty = 0
            for l in opciones:
                cap = int(max(horas_rest[l], 0.0) * c["uph"]) // pack * pack
                if cap >= pack:
                    elegido = l
                    qty = min(qty_obj, cap)
                    break
            if elegido is None:
                fuera.append({"part_no": c["part_no"], "qty": qty_obj,
                              "motivo": "sin horas disponibles" +
                                        (" en sus lineas (" + ",".join(permitidas) + ")"
                                         if permitidas else "")})
                continue

            horas_rest[elegido] = horas_rest[elegido] - qty / c["uph"]
            if linea_familia is None:
                linea_familia = elegido
            notas = []
            if adelanto:
                notas.append(f"Adelanto: falta el {c['primera_falta'].strftime('%d/%m')}")
            if qty < qty_obj:
                notas.append("parcial por horas")
            lotes.append({**c, "qty": qty, "linea": elegido,
                          "comentario": " | ".join(notas) or None})
    return lotes, fuera


def _ppy_datos_raw(parte_list):
    """model/sub_assy/uph/estandar_pack desde raw, indexado por part_no TRIM."""
    if not parte_list:
        return {}
    placeholders = ", ".join(["%s"] * len(parte_list))
    rows = execute_query(
        "SELECT TRIM(part_no) AS part_no, model, sub_assy, uph, estandar_pack "
        f"FROM raw WHERE TRIM(part_no) IN ({placeholders})",
        tuple(parte_list),
        fetch="all",
    ) or []
    return {r["part_no"]: r for r in rows}


_PPY_ORDEN_SQL = (
    "ORDER BY COALESCE(NULLIF(linea, ''), 'ZZZ'), "
    f"LEFT(part_no, {PPY_FAMILIA_LEN}), part_no, id"
)


def _ppy_listado(fecha):
    """Lotes del dia + resumen de horas por linea (para GET y respuestas)."""
    rows = execute_query(
        "SELECT * FROM lg_lote_plan WHERE plan_date = %s "
        "AND status IN ('PENDIENTE', 'CONFIRMADO') " + _PPY_ORDEN_SQL,
        (fecha,),
        fetch="all",
    ) or []
    lotes = []
    lineas = {}
    for r in rows:
        uph = r.get("uph")
        qty = int(r.get("qty_plan") or 0)
        horas = round(qty / uph, 2) if uph else None
        fisico = r.get("fisico")
        pack = r.get("estandar_pack")
        lotes.append(
            {
                "id": r["id"],
                "lot_no": r.get("lot_no"),
                "part_no": r["part_no"],
                "familia": _ppy_familia(r["part_no"]),
                "model": r.get("model"),
                "main_sub": r.get("main_sub"),
                "linea": r.get("linea"),
                "turno": r.get("turno"),
                "faltante": int(r.get("faltante") or 0),
                "qty_plan": qty,
                "uph": uph,
                "estandar_pack": pack,
                "time_horas": horas,
                "fisico": fisico,
                "falta": (int(fisico) - qty) if fisico is not None else None,
                "pct": (round(int(fisico) * 100.0 / qty, 1) if fisico is not None and qty else None),
                "status": r.get("status"),
                "comentario": r.get("comentario"),
                "warn_pack": bool(pack and int(pack) > 1 and qty % int(pack) != 0),
                "warn_uph": uph is None,
            }
        )
        clave = r.get("linea") or "SIN LINEA"
        acum = lineas.setdefault(clave, {"linea": clave, "horas": 0.0, "lotes": 0})
        acum["lotes"] += 1
        if horas:
            acum["horas"] = round(acum["horas"] + horas, 2)
    resumen = []
    for clave in sorted(lineas, key=lambda x: (x == "SIN LINEA", x)):
        d = lineas[clave]
        d["horas_max"] = PPY_HORAS_TURNO
        # "SIN LINEA" agrupa lo no acomodado: su suma de horas no es un exceso.
        d["excede"] = clave != "SIN LINEA" and d["horas"] > PPY_HORAS_TURNO
        resumen.append(d)
    return {"fecha": fecha.isoformat(), "lotes": lotes, "lineas": resumen}


@bp.route("/api/plan-proyectado", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def api_ppy_listado():
    try:
        fecha = _ppy_parse_fecha(request.args.get("fecha")) or date.today()
        return jsonify(
            {"success": True, "lineas_activas": _ppy_config_lineas(), **_ppy_listado(fecha)}
        )
    except Exception as e:
        logger.error("Error en api_ppy_listado: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/plan-proyectado/config", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def api_ppy_config():
    """Guarda las lineas activas (CSV, ej. 'M1,M2,M3') para el generador."""
    try:
        data = request.get_json(silent=True) or {}
        texto = (data.get("lineas") or "").strip().upper()
        lineas = []
        for l in texto.split(","):
            l = l.strip()
            if not l:
                continue
            if not re.match(r"^[A-Z0-9\-]{1,10}$", l):
                return jsonify({"success": False, "error": f"Linea invalida: {l}"}), 400
            if l not in lineas:
                lineas.append(l)
        if not lineas:
            return jsonify({"success": False, "error": "Captura al menos una linea"}), 400
        execute_query(
            "INSERT INTO lg_pp_config (clave, valor) VALUES ('lineas_activas', %s) "
            "ON DUPLICATE KEY UPDATE valor = VALUES(valor)",
            (",".join(lineas),),
        )
        return jsonify({"success": True, "lineas_activas": lineas})
    except Exception as e:
        logger.error("Error en api_ppy_config: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/plan-proyectado/generate", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def api_ppy_generate():
    """Genera la propuesta del dia: borra PENDIENTEs de la fecha y los recrea.

    Cubre los faltantes de HOY y adelanta faltantes de los proximos
    PPY_HORIZONTE_DIAS dias hasta llenar las horas de las lineas activas.
    """
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        fecha = _ppy_parse_fecha(data.get("fecha")) or date.today()
        usuario = session.get("usuario") or "SISTEMA"

        lineas_activas = _ppy_config_lineas()
        horas_rest = {l: PPY_HORAS_TURNO for l in lineas_activas}
        # Los lotes ya confirmados del dia consumen horas de su linea
        confirmados = execute_query(
            "SELECT part_no, linea, qty_plan, uph FROM lg_lote_plan "
            "WHERE plan_date = %s AND status = 'CONFIRMADO'",
            (fecha,),
            fetch="all",
        ) or []
        partes_confirmadas = set()
        for r in confirmados:
            partes_confirmadas.add(r["part_no"])
            l = (r.get("linea") or "").upper()
            if l in horas_rest and r.get("uph"):
                horas_rest[l] -= int(r["qty_plan"] or 0) / int(r["uph"])

        proy = _ppy_proyeccion_rango(fecha, fecha + timedelta(days=PPY_HORIZONTE_DIAS))
        candidatos = []
        for p, d in proy.items():
            if p in partes_confirmadas or not d["proj"]:
                continue
            min_i = min(d["proj"].values())
            if min_i >= 0:
                continue
            i_hoy = d["proj"].get(fecha, 0)
            candidatos.append(
                {
                    "part_no": p,
                    "falt_total": -min_i,
                    "falt_hoy": max(0, -i_hoy),
                    "primera_falta": min(f for f, v in d["proj"].items() if v < 0),
                    "line": d["line"],
                }
            )

        datos_raw = _ppy_datos_raw([c["part_no"] for c in candidatos])
        perm_parte, perm_familia = _ppy_lineas_permitidas_map()
        for c in candidatos:
            raw_info = datos_raw.get(c["part_no"]) or {}
            pack = raw_info.get("estandar_pack")
            c["pack"] = int(pack) if pack else None
            c["uph"] = _ppy_parse_uph(raw_info.get("uph"))
            c["model"] = raw_info.get("model")
            c["main_sub"] = raw_info.get("sub_assy")
            c["permitidas"] = (perm_parte.get(c["part_no"])
                               or perm_familia.get(_ppy_familia(c["part_no"])))

        lotes, fuera = _ppy_armar_lotes(candidatos, lineas_activas, horas_rest)
        nuevos = [
            (
                fecha,
                l["part_no"],
                l.get("model"),
                l.get("main_sub"),
                (l.get("linea") or None),
                "DIA",
                l["falt_total"],
                l["qty"],
                l.get("uph"),
                l.get("pack"),
                l.get("comentario"),
                usuario,
            )
            for l in lotes
        ]

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)
        cursor.execute(
            "DELETE FROM lg_lote_plan WHERE plan_date = %s AND status = 'PENDIENTE'",
            (fecha,),
        )
        if nuevos:
            for i in range(0, len(nuevos), PP_BATCH_SIZE):
                cursor.executemany(
                    "INSERT INTO lg_lote_plan (plan_date, part_no, model, main_sub, "
                    "linea, turno, faltante, qty_plan, uph, estandar_pack, comentario, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    nuevos[i : i + PP_BATCH_SIZE],
                )
        conn.commit()

        return jsonify(
            {
                "success": True,
                "generados": len(nuevos),
                "no_incluidos": fuera,
                "lineas_activas": lineas_activas,
                **_ppy_listado(fecha),
            }
        )
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error("Error en api_ppy_generate: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.autocommit(True)
                conn.close()
            except Exception:
                pass


@bp.route("/api/plan-proyectado/generate-faltantes", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def api_ppy_generate_faltantes():
    """Crea lotes PENDIENTES desde los faltantes del dia SIN asignar linea.

    La linea se asigna despues (manual o con "Acomodar con IA"). Cantidad =
    faltante +10% a caja cerrada (pack asumido PPY_PACK_DEFAULT si no hay).
    Reemplaza los PENDIENTES del dia; no toca los CONFIRMADOS.
    """
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        fecha = _ppy_parse_fecha(data.get("fecha")) or date.today()
        usuario = session.get("usuario") or "SISTEMA"

        confirmadas = execute_query(
            "SELECT DISTINCT part_no FROM lg_lote_plan "
            "WHERE plan_date = %s AND status = 'CONFIRMADO'",
            (fecha,),
            fetch="all",
        ) or []
        partes_confirmadas = {r["part_no"] for r in confirmadas}

        proy = _ppy_proyeccion_rango(fecha, fecha + timedelta(days=PPY_HORIZONTE_DIAS))
        faltantes = {}  # part_no -> faltante total (peor I del rango)
        for p, d in proy.items():
            if p in partes_confirmadas or not d["proj"]:
                continue
            min_i = min(d["proj"].values())
            if min_i < 0:
                faltantes[p] = -min_i

        datos_raw = _ppy_datos_raw(list(faltantes))
        nuevos = []
        for p, falt in faltantes.items():
            raw_info = datos_raw.get(p) or {}
            pack_raw = raw_info.get("estandar_pack")
            pack = int(pack_raw) if pack_raw else PPY_PACK_DEFAULT
            nuevos.append(
                (
                    fecha, p, raw_info.get("model"), raw_info.get("sub_assy"),
                    None,  # sin linea: se acomoda despues
                    "DIA", falt, _ppy_qty_pack(falt, pack),
                    _ppy_parse_uph(raw_info.get("uph")),
                    (int(pack_raw) if pack_raw else None),
                    None, usuario,
                )
            )

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)
        cursor.execute(
            "DELETE FROM lg_lote_plan WHERE plan_date = %s AND status = 'PENDIENTE'",
            (fecha,),
        )
        if nuevos:
            for i in range(0, len(nuevos), PP_BATCH_SIZE):
                cursor.executemany(
                    "INSERT INTO lg_lote_plan (plan_date, part_no, model, main_sub, "
                    "linea, turno, faltante, qty_plan, uph, estandar_pack, comentario, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    nuevos[i : i + PP_BATCH_SIZE],
                )
        conn.commit()
        return jsonify(
            {"success": True, "generados": len(nuevos),
             "lineas_activas": _ppy_config_lineas(), **_ppy_listado(fecha)}
        )
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error("Error en api_ppy_generate_faltantes: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.autocommit(True)
                conn.close()
            except Exception:
                pass


@bp.route("/api/plan-proyectado/generate-schedule", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def api_ppy_generate_schedule():
    """Crea un lote PENDIENTE por cada Schedule (renglon S) del dia SIN linea.

    El Schedule capturado/importado en Proyeccion ES el plan del dia: cada
    celda S de la fecha se vuelve un lote con su cantidad EXACTA. La linea se
    asigna despues (manual o con "Acomodar con IA"). Reemplaza los PENDIENTES;
    no toca los CONFIRMADOS.
    """
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        fecha = _ppy_parse_fecha(data.get("fecha")) or date.today()
        usuario = session.get("usuario") or "SISTEMA"

        confirmadas = execute_query(
            "SELECT DISTINCT part_no FROM lg_lote_plan "
            "WHERE plan_date = %s AND status = 'CONFIRMADO'",
            (fecha,), fetch="all",
        ) or []
        partes_confirmadas = {r["part_no"] for r in confirmadas}

        sched = execute_query(
            "SELECT part_no, sched_qty FROM lg_schedule_daily "
            "WHERE sched_date = %s AND sched_qty > 0 ORDER BY part_no",
            (fecha,), fetch="all",
        ) or []
        sched = [r for r in sched if r["part_no"] not in partes_confirmadas]

        datos_raw = _ppy_datos_raw([r["part_no"] for r in sched])
        nuevos = []
        for r in sched:
            p = r["part_no"]
            qty = int(r["sched_qty"] or 0)
            raw_info = datos_raw.get(p) or {}
            pack_raw = raw_info.get("estandar_pack")
            nuevos.append(
                (
                    fecha, p, raw_info.get("model"), raw_info.get("sub_assy"),
                    None,  # sin linea: se acomoda despues
                    "DIA",
                    qty,  # faltante = cantidad del schedule (referencia)
                    qty,  # qty_plan = cantidad EXACTA del schedule
                    _ppy_parse_uph(raw_info.get("uph")),
                    (int(pack_raw) if pack_raw else None),
                    "Desde schedule", usuario,
                )
            )

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)
        cursor.execute(
            "DELETE FROM lg_lote_plan WHERE plan_date = %s AND status = 'PENDIENTE'",
            (fecha,),
        )
        if nuevos:
            for i in range(0, len(nuevos), PP_BATCH_SIZE):
                cursor.executemany(
                    "INSERT INTO lg_lote_plan (plan_date, part_no, model, main_sub, "
                    "linea, turno, faltante, qty_plan, uph, estandar_pack, comentario, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    nuevos[i : i + PP_BATCH_SIZE],
                )
        conn.commit()
        return jsonify(
            {"success": True, "generados": len(nuevos),
             "lineas_activas": _ppy_config_lineas(), **_ppy_listado(fecha)}
        )
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error("Error en api_ppy_generate_schedule: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.autocommit(True)
                conn.close()
            except Exception:
                pass


def _ppy_acomodo_heuristico(pend, lineas_activas, horas_rest):
    """Fallback local: asigna linea a los lotes sin linea por horas + familia.

    Reutiliza _ppy_armar_lotes (linea mas libre, familia junta, lineas
    permitidas). No cambia cantidades, solo linea. Retorna {id: linea}.
    """
    candidatos = []
    for l in pend:
        candidatos.append({
            "part_no": l["part_no"], "falt_total": int(l["qty_plan"] or 0),
            "falt_hoy": int(l["qty_plan"] or 0), "primera_falta": date.today(),
            "line": None, "uph": l.get("uph"),
            "pack": (int(l["estandar_pack"]) if l.get("estandar_pack") else None),
            "model": l.get("model"), "main_sub": l.get("main_sub"),
            "permitidas": l.get("permitidas"), "_id": l["id"],
        })
    lotes, _ = _ppy_armar_lotes(candidatos, lineas_activas, dict(horas_rest), estricto=False)
    # _ppy_armar_lotes conserva las claves extra via {**c}, incluido _id
    return {l["_id"]: l.get("linea") for l in lotes if l.get("linea")}


@bp.route("/api/plan-proyectado/acomodar-ia", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def api_ppy_acomodar_ia():
    """Asigna linea a los lotes PENDIENTES sin linea usando la IA (OpenAI).

    Respeta lineas permitidas (raw) y 9 h por linea activa (menos lo ya usado
    por lotes con linea). Si la IA falla o no hay API key, cae a la heuristica
    local. No cambia cantidades: solo asigna linea.
    """
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        fecha = _ppy_parse_fecha(data.get("fecha")) or date.today()
        usuario = session.get("usuario") or "SISTEMA"
        lineas_activas = _ppy_config_lineas()

        rows = execute_query(
            "SELECT id, part_no, model, main_sub, linea, qty_plan, uph, estandar_pack "
            "FROM lg_lote_plan WHERE plan_date = %s AND status = 'PENDIENTE'",
            (fecha,),
            fetch="all",
        ) or []
        perm_parte, perm_familia = _ppy_lineas_permitidas_map()
        for r in rows:
            r["permitidas"] = (perm_parte.get(r["part_no"])
                               or perm_familia.get(_ppy_familia(r["part_no"])))

        sin_linea = [r for r in rows if not (r.get("linea") or "").strip()]
        if not sin_linea:
            return jsonify({"success": True, "asignados": 0, "metodo": "nada",
                            "lineas_activas": lineas_activas, **_ppy_listado(fecha)})

        # Horas ya ocupadas por lotes con linea (y confirmados)
        horas_rest = {l: PPY_HORAS_TURNO for l in lineas_activas}
        confirmados = execute_query(
            "SELECT linea, qty_plan, uph FROM lg_lote_plan "
            "WHERE plan_date = %s AND status = 'CONFIRMADO'",
            (fecha,), fetch="all",
        ) or []
        for r in list(rows) + confirmados:
            l = (r.get("linea") or "").upper()
            if l in horas_rest and r.get("uph"):
                horas_rest[l] -= int(r["qty_plan"] or 0) / int(r["uph"])

        asignaciones = {}
        ia_ok = False
        try:
            asignaciones = _ppy_acomodo_ia_llm(sin_linea, lineas_activas, horas_rest)
            ia_ok = True
        except Exception as e:
            logger.warning("acomodar-ia: IA no disponible, uso heuristica: %r", e)

        # Validar cada asignacion de la IA: linea activa, permitida, y que
        # NO exceda las horas disponibles de la linea (la IA puede equivocarse).
        by_id = {r["id"]: r for r in sin_linea}
        horas_libre = dict(horas_rest)
        validas = {}
        for lote_id, l in asignaciones.items():
            r = by_id.get(lote_id)
            if not r:
                continue
            l = str(l).strip().upper()
            if l not in lineas_activas:
                continue
            if r["permitidas"] and l not in r["permitidas"]:
                continue
            h = (int(r["qty_plan"] or 0) / int(r["uph"])) if r.get("uph") else 0.0
            if h > horas_libre.get(l, 0.0) + 1e-6:
                continue  # excederia la linea: se descarta, va a heuristica
            horas_libre[l] = horas_libre.get(l, 0.0) - h
            validas[lote_id] = l

        if ia_ok and validas:
            metodo = "ia"
        else:
            metodo = "heuristica"

        # Solo si la IA fallo por completo (0 asignaciones validas), la
        # heuristica local intenta acomodar todo. Si la IA acomodo bien, lo
        # que dejo fuera es porque no cabe: NO se fuerza.
        if not validas:
            heur = _ppy_acomodo_heuristico(sin_linea, lineas_activas, horas_rest)
            validas.update(heur)

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)
        for lote_id, linea in validas.items():
            cursor.execute(
                "UPDATE lg_lote_plan SET linea = %s, updated_by = %s "
                "WHERE id = %s AND status = 'PENDIENTE'",
                (linea, usuario, lote_id),
            )
        conn.commit()

        return jsonify(
            {"success": True, "asignados": len(validas),
             "sin_asignar": len(sin_linea) - len(validas), "metodo": metodo,
             "lineas_activas": lineas_activas, **_ppy_listado(fecha)}
        )
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error("Error en api_ppy_acomodar_ia: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.autocommit(True)
                conn.close()
            except Exception:
                pass


def _ppy_acomodo_ia_llm(sin_linea, lineas_activas, horas_rest):
    """Pide a la IA la mejor linea por lote. Retorna {id: linea}.

    Lanza excepcion si la IA no esta disponible (sin API key) o falla; el
    caller cae a la heuristica local.
    """
    from app.api.portal.ai_openai import complete_json

    # Solo se le manda a la IA lo que puede caber: lotes con UPH (horas
    # calculables), ordenados por familia, hasta ~el total de horas
    # disponibles + un margen. El resto no cabe igual y se queda sin linea:
    # asi el prompt no crece con faltantes que no se van a acomodar.
    horas_totales = sum(max(horas_rest.get(l, 0.0), 0.0) for l in lineas_activas)
    candidatos = sorted(
        (r for r in sin_linea if r.get("uph")),
        key=lambda r: (_ppy_familia(r["part_no"]), r["part_no"]),
    )
    lotes_payload = []
    acum_horas = 0.0
    for r in candidatos:
        h = round(int(r["qty_plan"] or 0) / int(r["uph"]), 2)
        lotes_payload.append({
            "id": r["id"],
            "familia": _ppy_familia(r["part_no"]),
            "horas": h,
            "lineas": r["permitidas"] or lineas_activas,
        })
        acum_horas += h
        if acum_horas >= horas_totales * 1.2:  # margen para que la IA elija
            break
    if not lotes_payload:
        return {}

    system = (
        "Eres un planificador de produccion. Asignas lotes a lineas de ensamble "
        "balanceando la carga. Reglas ESTRICTAS:\n"
        "1. Cada lote va SOLO a una de sus 'lineas' permitidas.\n"
        "2. La suma de 'horas' de los lotes de una linea no debe exceder sus "
        "'horas_disponibles'. Si no cabe todo, deja lotes sin asignar; no "
        "inventes lineas ni excedas horas.\n"
        "3. Manten juntos en la MISMA linea los lotes de la misma 'familia'.\n"
        "4. Balancea las horas entre lineas.\n"
        "Responde SOLO JSON {\"asignaciones\":[{\"id\":<int>,\"linea\":\"<LINEA>\"}]}, "
        "omitiendo los lotes que no acomodes."
    )
    user = "Acomoda estos lotes y responde en JSON.\n" + json.dumps({
        "horas_disponibles": {l: round(max(horas_rest.get(l, 0.0), 0.0), 2) for l in lineas_activas},
        "lotes": lotes_payload,
    }, ensure_ascii=False)

    resultado = complete_json(system=system, user=user, username="plan_proyectado")
    salida = {}
    for a in (resultado.get("asignaciones") or []):
        try:
            salida[int(a["id"])] = str(a["linea"]).strip().upper()
        except (KeyError, TypeError, ValueError):
            continue
    return salida


@bp.route("/api/plan-proyectado/add", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def api_ppy_add():
    """Alta manual de un lote PENDIENTE (enriquece desde raw e inventario)."""
    try:
        data = request.get_json(silent=True) or {}
        fecha = _ppy_parse_fecha(data.get("fecha")) or date.today()
        part_no = (data.get("part_no") or "").strip()
        if not part_no:
            return jsonify({"success": False, "error": "part_no requerido"}), 400
        try:
            qty = int(data.get("qty"))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Cantidad invalida"}), 400
        if qty <= 0:
            return jsonify({"success": False, "error": "Cantidad invalida"}), 400

        usuario = session.get("usuario") or "SISTEMA"
        raw_info = (_ppy_datos_raw([part_no])).get(part_no) or {}
        linea = (data.get("linea") or "").strip() or None
        if not linea:
            inv = execute_query(
                "SELECT line FROM lg_part_inventory WHERE part_no = %s",
                (part_no,),
                fetch="one",
            )
            linea = (inv or {}).get("line") or None
        pack = raw_info.get("estandar_pack")
        execute_query(
            "INSERT INTO lg_lote_plan (plan_date, part_no, model, main_sub, linea, "
            "turno, faltante, qty_plan, uph, estandar_pack, created_by) "
            "VALUES (%s, %s, %s, %s, %s, 'DIA', 0, %s, %s, %s, %s)",
            (
                fecha,
                part_no,
                raw_info.get("model"),
                raw_info.get("sub_assy"),
                linea,
                qty,
                _ppy_parse_uph(raw_info.get("uph")),
                (int(pack) if pack else None),
                usuario,
            ),
        )
        return jsonify({"success": True, **_ppy_listado(fecha)})
    except Exception as e:
        logger.error("Error en api_ppy_add: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/plan-proyectado/update", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def api_ppy_update():
    """Edita un campo del lote. PENDIENTE: qty/linea/turno/comentario/fisico;
    CONFIRMADO: solo fisico y comentario (la qty confirmada ya sumo al S)."""
    try:
        data = request.get_json(silent=True) or {}
        lote_id = data.get("id")
        campo = (data.get("field") or "").strip().lower()
        valor = data.get("value")
        if not lote_id or campo not in ("qty_plan", "linea", "turno", "comentario", "fisico"):
            return jsonify({"success": False, "error": "Campo invalido"}), 400

        row = execute_query(
            "SELECT * FROM lg_lote_plan WHERE id = %s", (lote_id,), fetch="one"
        )
        if not row:
            return jsonify({"success": False, "error": "Lote no encontrado"}), 404
        if row["status"] == "CANCELADO":
            return jsonify({"success": False, "error": "Lote cancelado"}), 400
        if row["status"] == "CONFIRMADO" and campo not in ("fisico", "comentario"):
            return (
                jsonify({"success": False, "error": "Lote confirmado: solo FISICO y comentario son editables"}),
                400,
            )

        if campo == "qty_plan":
            try:
                valor = int(valor)
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Cantidad invalida"}), 400
            if valor <= 0:
                return jsonify({"success": False, "error": "Cantidad invalida"}), 400
        elif campo == "fisico":
            if valor in (None, ""):
                valor = None
            else:
                try:
                    valor = int(valor)
                except (TypeError, ValueError):
                    return jsonify({"success": False, "error": "Valor invalido"}), 400
                if valor < 0:
                    return jsonify({"success": False, "error": "Valor invalido"}), 400
        elif campo == "turno":
            valor = (str(valor) or "").strip().upper()
            if valor not in PPY_TURNOS:
                return jsonify({"success": False, "error": "Turno invalido"}), 400
        else:
            valor = (str(valor or "").strip()[:255]) or None
            if campo == "linea" and valor:
                valor = valor.upper()[:10]

        usuario = session.get("usuario") or "SISTEMA"
        # campo validado contra whitelist arriba
        execute_query(
            f"UPDATE lg_lote_plan SET {campo} = %s, updated_by = %s WHERE id = %s",
            (valor, usuario, lote_id),
        )
        fecha = row["plan_date"]
        if isinstance(fecha, datetime):
            fecha = fecha.date()
        return jsonify({"success": True, **_ppy_listado(fecha)})
    except Exception as e:
        logger.error("Error en api_ppy_update: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/plan-proyectado/delete", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def api_ppy_delete():
    """PENDIENTE se borra; CONFIRMADO se cancela y su qty se resta del S."""
    try:
        data = request.get_json(silent=True) or {}
        lote_id = data.get("id")
        row = execute_query(
            "SELECT * FROM lg_lote_plan WHERE id = %s", (lote_id,), fetch="one"
        )
        if not row:
            return jsonify({"success": False, "error": "Lote no encontrado"}), 404
        fecha = row["plan_date"]
        if isinstance(fecha, datetime):
            fecha = fecha.date()

        if row["status"] == "PENDIENTE":
            execute_query("DELETE FROM lg_lote_plan WHERE id = %s", (lote_id,))
        elif row["status"] == "CONFIRMADO":
            usuario = session.get("usuario") or "SISTEMA"
            execute_query(
                "UPDATE lg_lote_plan SET status = 'CANCELADO', updated_by = %s "
                "WHERE id = %s",
                (usuario, lote_id),
            )
            execute_query(
                "UPDATE lg_schedule_daily SET sched_qty = GREATEST(sched_qty - %s, 0), "
                "updated_by = %s WHERE part_no = %s AND sched_date = %s",
                (int(row["qty_plan"] or 0), usuario, row["part_no"], fecha),
            )
            execute_query(
                "DELETE FROM lg_schedule_daily WHERE part_no = %s AND sched_date = %s "
                "AND sched_qty = 0",
                (row["part_no"], fecha),
            )
        return jsonify({"success": True, **_ppy_listado(fecha)})
    except Exception as e:
        logger.error("Error en api_ppy_delete: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/plan-proyectado/confirm", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(PP_PERMISO_PAGINA, PP_PERMISO_SECCION, PPY_PERMISO_BOTON)
def api_ppy_confirm():
    """Numera los PENDIENTEs del dia (I<YYYYMMDD>-####) y suma su qty al S.

    Bloquea si alguna linea excede las 9 h sin tiempo extra ("debe cumplirse
    en sus horas"): el usuario ajusta cantidades y reintenta.
    """
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        fecha = _ppy_parse_fecha(data.get("fecha")) or date.today()
        usuario = session.get("usuario") or "SISTEMA"

        listado = _ppy_listado(fecha)
        excedidas = [l for l in listado["lineas"] if l["excede"]]
        if excedidas:
            detalle = ", ".join(f"{l['linea']}: {l['horas']} h" for l in excedidas)
            return (
                jsonify({"success": False,
                         "error": f"Lineas exceden {PPY_HORAS_TURNO:g} h sin tiempo extra: {detalle}. Ajusta cantidades antes de confirmar."}),
                400,
            )

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)

        cursor.execute(
            "SELECT * FROM lg_lote_plan WHERE plan_date = %s AND status = 'PENDIENTE' "
            + _PPY_ORDEN_SQL + " FOR UPDATE",
            (fecha,),
        )
        pendientes = cursor.fetchall() or []
        if not pendientes:
            conn.rollback()
            return jsonify({"success": False, "error": "No hay lotes pendientes para esa fecha."}), 400

        prefijo = f"I{fecha.strftime('%Y%m%d')}"
        cursor.execute(
            "SELECT lot_no FROM lg_lote_plan WHERE lot_no LIKE %s "
            "ORDER BY lot_no DESC LIMIT 1 FOR UPDATE",
            (f"{prefijo}-%",),
        )
        ultimo = cursor.fetchone()
        consecutivo = 0
        if ultimo and ultimo.get("lot_no"):
            try:
                consecutivo = int(str(ultimo["lot_no"]).split("-")[-1])
            except ValueError:
                consecutivo = 0

        sumas_s = {}
        for r in pendientes:
            consecutivo += 1
            cursor.execute(
                "UPDATE lg_lote_plan SET lot_no = %s, status = 'CONFIRMADO', "
                "confirmed_by = %s, confirmed_at = NOW() WHERE id = %s",
                (f"{prefijo}-{consecutivo:04d}", usuario, r["id"]),
            )
            sumas_s[r["part_no"]] = sumas_s.get(r["part_no"], 0) + int(r["qty_plan"] or 0)

        cursor.executemany(
            "INSERT INTO lg_schedule_daily (part_no, sched_date, sched_qty, updated_by) "
            "VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE sched_qty = sched_qty + VALUES(sched_qty), "
            "updated_by = VALUES(updated_by)",
            [(p, fecha, q, usuario) for p, q in sumas_s.items()],
        )
        conn.commit()

        return jsonify({"success": True, "confirmados": len(pendientes), **_ppy_listado(fecha)})
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error("Error en api_ppy_confirm: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.autocommit(True)
                conn.close()
            except Exception:
                pass
