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
import logging
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

PP_INV_SHEET = "Part 10"


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
        if PP_INV_SHEET not in wb.sheetnames:
            return error(f"No se encontro la hoja '{PP_INV_SHEET}' en el archivo.")
        ws = wb[PP_INV_SHEET]

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
                f"No se encontro el encabezado 'PART NUMBER' en la hoja '{PP_INV_SHEET}'."
            )
        if not col_fechas:
            return error(f"No se encontraron fechas en el encabezado de '{PP_INV_SHEET}'.")

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
                    warnings.append(f"Parte repetida en {PP_INV_SHEET}: {part} (se toma la primera).")
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
            return error(f"No se encontraron partes en la hoja '{PP_INV_SHEET}'.")

        fechas = sorted(col_fechas.values())
        return {
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
                PP_INV_SHEET,
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
             parsed["ref_date"], import_id)
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
                "ref_date": parsed["ref_date"].isoformat(),
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
                filas = [
                    f for f in filas
                    if any(v is not None and v < 0 for v in f["proj"].values())
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
