"""Solicitud de Retrabajo: el MES define el retrabajo y cada area recibe su parte.

No hay tabla de tareas: la parte de cada area se deriva de la solicitud.
  EMBARQUES       origen EMBARQUES          -> retrabajo_salidas_embarques (MES, Salidas almacen embarques)
  MICOM           programacion              -> fpa_requests (cola FPA existente de MICOM)
  IMPRESION       np_destino != np_origen   -> qr_history del lote plan_smt routing RETRABAJO
  CP_RETRABAJO    etiquetas o programacion  -> retrabajo_escaneos (Control_produccion)
  CP_REPARACION   componente ASSY           -> retrabajo_escaneos (Control_produccion)
  SMD_REPARACION  componente SMD            -> retrabajo_escaneos (Control_inventario_SMD)

Las salidas de Embarques viven en tablas propias; no tocan inventario de
Embarques ni cajas OQC (la conexion se hara despues).
"""

import logging
import re

from flask import Blueprint, jsonify, render_template, request, session

from app.api.shared import (
    auth_system,
    conexion_o_error,
    dict_cursor,
    excel_response_ict,
    execute_query,
    formatear_fecha_hora,
    login_requerido,
    obtener_fecha_hora_mexico,
    requiere_permiso_dropdown,
    sanitizar_texto,
)
from app.services.fpa_micom_client import FpaMicomError, request_micom

logger = logging.getLogger(__name__)

bp = Blueprint("retrabajo", __name__)

PERMISO_MODULO = ("LISTA_CONTROLDEPRODUCCION", "Retrabajo", "Solicitud de retrabajo")
PERMISO_EMBARQUES = (
    "LISTA_CONTROL_DE_PROCESO",
    "Almacén de Embarques",
    "Salidas almacen embarques",
)

PART_RE = re.compile(r"^[A-Z]{3}\d{8}$")
ORIGENES = ("EMBARQUES", "SMD", "PRODUCCION")
TIPOS_MATERIAL = ("ASSY", "IMD_SMD")
# IMD tambien lo repara Control Inventario SMD (etapa SMD_REPARACION).
TIPOS_COMPONENTE = ("ASSY", "SMD", "IMD")
MAX_CANTIDAD = 999  # tope de micomQuantity en la cola FPA de MICOM
ERROR_INTERNO = "Error interno del servidor."


def crear_tablas_retrabajo():
    """Crea las tablas de retrabajo y agrega tracking.QR_Anterior si falta."""
    tablas = (
        """
        CREATE TABLE IF NOT EXISTS retrabajo_solicitudes (
            id INT NOT NULL AUTO_INCREMENT,
            folio VARCHAR(30) NULL,
            idempotency_key VARCHAR(64) NOT NULL,
            np_origen VARCHAR(64) NOT NULL,
            np_destino VARCHAR(64) NOT NULL,
            cantidad INT NOT NULL,
            tipo_material ENUM('ASSY','IMD_SMD') NOT NULL,
            cambio_etiquetas TINYINT NOT NULL DEFAULT 0,
            lote_impresion VARCHAR(50) NULL,
            comentarios TEXT NULL,
            status ENUM('ACTIVA','CANCELADA') NOT NULL DEFAULT 'ACTIVA',
            solicitado_por VARCHAR(100) NOT NULL,
            cancelado_por VARCHAR(100) NULL,
            cancelado_at DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_rtb_folio (folio),
            UNIQUE KEY uq_rtb_idempotency (idempotency_key),
            KEY idx_rtb_status (status, id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS retrabajo_origenes (
            id INT NOT NULL AUTO_INCREMENT,
            solicitud_id INT NOT NULL,
            origen ENUM('EMBARQUES','SMD','PRODUCCION') NOT NULL,
            cantidad INT NOT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uq_rtb_origen (solicitud_id, origen)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS retrabajo_programaciones (
            id INT NOT NULL AUTO_INCREMENT,
            solicitud_id INT NOT NULL,
            ic_location VARCHAR(128) NOT NULL,
            micom_part_no VARCHAR(128) NOT NULL,
            programming_label VARCHAR(255) NOT NULL,
            fpa_request_id BIGINT NULL,
            PRIMARY KEY (id),
            KEY idx_rtb_prog_solicitud (solicitud_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS retrabajo_componentes (
            id INT NOT NULL AUTO_INCREMENT,
            solicitud_id INT NOT NULL,
            tipo ENUM('ASSY','SMD','IMD') NOT NULL,
            ubicacion VARCHAR(100) NOT NULL,
            np_anterior VARCHAR(64) NULL,
            np_nuevo VARCHAR(64) NULL,
            PRIMARY KEY (id),
            KEY idx_rtb_comp_solicitud (solicitud_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS retrabajo_salidas_embarques (
            id INT NOT NULL AUTO_INCREMENT,
            folio VARCHAR(30) NULL,
            solicitud_id INT NOT NULL,
            part_number VARCHAR(64) NOT NULL,
            cantidad INT NOT NULL,
            registrado_por VARCHAR(100) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_rtb_salida_folio (folio),
            KEY idx_rtb_salida_solicitud (solicitud_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS retrabajo_salidas_embarques_cajas (
            id INT NOT NULL AUTO_INCREMENT,
            salida_id INT NOT NULL,
            box_code VARCHAR(100) NOT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uq_rtb_caja (box_code),
            KEY idx_rtb_caja_salida (salida_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        # Los QR van en utf8mb4_bin igual que tracking.QR.
        """
        CREATE TABLE IF NOT EXISTS retrabajo_escaneos (
            id BIGINT NOT NULL AUTO_INCREMENT,
            capture_id CHAR(36) NOT NULL,
            solicitud_id INT NOT NULL,
            etapa ENUM('CP_RETRABAJO','CP_REPARACION','SMD_REPARACION') NOT NULL,
            pcb_key VARCHAR(255) COLLATE utf8mb4_bin NOT NULL,
            qr_smd_anterior VARCHAR(255) COLLATE utf8mb4_bin NULL,
            qr_smd_nuevo VARCHAR(255) COLLATE utf8mb4_bin NULL,
            qr_assy_anterior VARCHAR(255) NULL,
            qr_assy_nuevo VARCHAR(255) NULL,
            usuario VARCHAR(100) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_rtb_capture (capture_id),
            UNIQUE KEY uq_rtb_pcb (solicitud_id, etapa, pcb_key),
            UNIQUE KEY uq_rtb_qr_smd_nuevo (qr_smd_nuevo),
            UNIQUE KEY uq_rtb_qr_assy_nuevo (qr_assy_nuevo),
            KEY idx_rtb_qr_smd_anterior (qr_smd_anterior),
            KEY idx_rtb_qr_assy_anterior (qr_assy_anterior)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
    )
    for ddl in tablas:
        execute_query(ddl)
    tipo = execute_query("SHOW COLUMNS FROM retrabajo_componentes LIKE %s", ("tipo",), fetch="one")
    if tipo and "IMD" not in str(tipo.get("Type", "")):
        execute_query("ALTER TABLE retrabajo_componentes MODIFY tipo ENUM('ASSY','SMD','IMD') NOT NULL")
    # Mismo patron que tracking.Barcode_Anterior (Control_produccion).
    if not execute_query("SHOW COLUMNS FROM tracking LIKE %s", ("QR_Anterior",), fetch="one"):
        execute_query(
            "ALTER TABLE tracking ADD COLUMN QR_Anterior VARCHAR(255) "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL, "
            "ADD INDEX idx_tracking_qr_anterior (QR_Anterior)"
        )


# ===================== Reglas puras =====================

def _entero(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def opcion_programacion(row):
    """Puerto de parseProgramming (Control_produccion pcbReprogrammingRules.js)."""
    micom = re.sub(r"_\((IC[^)]*)\)$", "", str(row.get("item_no") or "").strip(), flags=re.I)
    spec = str(row.get("spec") or "").strip()
    location = str(row.get("location_text") or "").strip()
    if len(micom) < 4 or not location:
        return None
    checksum = re.sub(r"[^0-9a-fA-F]", "", spec)[-4:].upper()
    label = f"{micom[:-3]} {micom[-3:]}" + (f"({checksum})" if checksum else "")
    return {"ic_location": location, "micom_part_no": micom, "programming_label": label}


def validar_solicitud(data):
    """Normaliza el payload de alta. Devuelve (payload, errores)."""
    errors = []
    np_origen = sanitizar_texto(data.get("np_origen"), 64).upper()
    np_destino = sanitizar_texto(data.get("np_destino"), 64).upper()
    tipo_material = sanitizar_texto(data.get("tipo_material"), 10).upper()
    for etiqueta, valor in (("NP origen", np_origen), ("NP destino", np_destino)):
        if not PART_RE.match(valor):
            errors.append(f"{etiqueta} inválido (formato EBR########).")
    if tipo_material not in TIPOS_MATERIAL:
        errors.append("Tipo de material debe ser ASSY o IMD_SMD.")

    origenes = []
    for item in data.get("origenes") or []:
        origen = sanitizar_texto((item or {}).get("origen"), 20).upper()
        cantidad = _entero((item or {}).get("cantidad"))
        if origen not in ORIGENES:
            errors.append(f"Origen inválido: {origen or '(vacío)'}.")
        elif any(o["origen"] == origen for o in origenes):
            errors.append(f"Origen repetido: {origen}.")
        elif cantidad is None or cantidad < 1:
            errors.append(f"Cantidad inválida para {origen}.")
        else:
            origenes.append({"origen": origen, "cantidad": cantidad})
    if not origenes:
        errors.append("Indique al menos un origen del material con cantidad.")
    cantidad = sum(o["cantidad"] for o in origenes)
    if origenes and cantidad > MAX_CANTIDAD:
        errors.append(f"La cantidad total no puede pasar de {MAX_CANTIDAD}.")

    programaciones = []
    for item in data.get("programaciones") or []:
        ic_location = sanitizar_texto((item or {}).get("ic_location"), 128)
        label = sanitizar_texto((item or {}).get("programming_label"), 255)
        if not ic_location or not label:
            errors.append("Programación incompleta.")
        elif not any(p["ic_location"] == ic_location for p in programaciones):
            programaciones.append({"ic_location": ic_location, "programming_label": label})

    componentes = []
    for item in data.get("componentes") or []:
        tipo = sanitizar_texto((item or {}).get("tipo"), 10).upper()
        ubicacion = sanitizar_texto((item or {}).get("ubicacion"), 100).upper()
        if tipo not in TIPOS_COMPONENTE:
            errors.append("El tipo de componente debe ser ASSY, SMD o IMD.")
        elif not ubicacion:
            errors.append("Cada componente necesita su ubicación.")
        else:
            componentes.append({
                "tipo": tipo,
                "ubicacion": ubicacion,
                "np_anterior": sanitizar_texto((item or {}).get("np_anterior"), 64).upper() or None,
                "np_nuevo": sanitizar_texto((item or {}).get("np_nuevo"), 64).upper() or None,
            })

    cambio_etiquetas = bool(np_origen and np_destino and np_origen != np_destino)
    if not (cambio_etiquetas or programaciones or componentes):
        errors.append("El retrabajo debe llevar cambio de número de parte, programación o componentes.")

    return {
        "np_origen": np_origen,
        "np_destino": np_destino,
        "tipo_material": tipo_material,
        "cantidad": cantidad,
        "cambio_etiquetas": cambio_etiquetas,
        "origenes": origenes,
        "programaciones": programaciones,
        "componentes": componentes,
        "comentarios": sanitizar_texto(data.get("comentarios"), 2000) or None,
    }, errors


def validar_salida_embarques(solicitud, data, surtido):
    """Valida una salida de Embarques a retrabajo. Devuelve (payload, error)."""
    if not solicitud:
        return None, "Orden de retrabajo no encontrada."
    if solicitud.get("status") != "ACTIVA":
        return None, "La orden de retrabajo está cancelada."
    solicitado = int(solicitud.get("emb_solicitado") or 0)
    if solicitado <= 0:
        return None, "La orden no tiene material de Embarques."
    part_number = sanitizar_texto(data.get("partNumber"), 64).upper()
    if part_number != solicitud.get("np_origen"):
        return None, f"El número de parte debe ser {solicitud.get('np_origen')}."
    cantidad = _entero(data.get("cantidad"))
    pendiente = solicitado - int(surtido or 0)
    if cantidad is None or cantidad < 1:
        return None, "Cantidad inválida."
    if cantidad > pendiente:
        return None, f"La cantidad rebasa lo pendiente para Embarques ({max(pendiente, 0)})."
    cajas = []
    for raw in data.get("boxCodes") or []:
        caja = sanitizar_texto(raw, 100)
        if not caja:
            continue
        if caja.upper() in (c.upper() for c in cajas):
            return None, f"Caja repetida: {caja}."
        cajas.append(caja)
    if not cajas:
        return None, "Escanee al menos una caja."
    return {"part_number": part_number, "cantidad": cantidad, "cajas": cajas}, None


def _estado(hecho, total, iniciado=None):
    if total and hecho >= total:
        return "COMPLETADA"
    return "EN_PROCESO" if (iniciado if iniciado is not None else hecho) > 0 else "PENDIENTE"


def calcular_areas(row):
    """Areas involucradas y su avance a partir de una fila de _SELECT_RESUMEN."""
    n = lambda key: int(row.get(key) or 0)  # noqa: E731
    cantidad = n("cantidad")
    areas = []

    def add(clave, nombre, hecho, total, iniciado=None):
        areas.append({
            "area": clave, "nombre": nombre, "hecho": hecho, "total": total,
            "estado": _estado(hecho, total, iniciado),
        })

    if n("emb_solicitado"):
        add("EMBARQUES", "Embarques", n("emb_surtido"), n("emb_solicitado"))
    if n("prog_total"):
        add("MICOM", "MICOM", n("prog_completas"), n("prog_total"), n("prog_iniciadas"))
    if n("cambio_etiquetas"):
        add("IMPRESION", "Impresión", n("impresas"), cantidad)
    if n("cambio_etiquetas") or n("prog_total"):
        nombre = "Reprogramación" if n("prog_total") else "Cambio de etiquetas"
        add("CP_RETRABAJO", nombre, n("esc_cp_retrabajo"), cantidad)
    if n("comp_assy"):
        add("CP_REPARACION", "Reparación ASSY", n("esc_cp_reparacion"), cantidad)
    if n("comp_smd"):
        add("SMD_REPARACION", "Reparación SMD/IMD", n("esc_smd_reparacion"), cantidad)

    if row.get("status") == "CANCELADA":
        estado = "CANCELADA"
    elif areas and all(a["estado"] == "COMPLETADA" for a in areas):
        estado = "COMPLETADA"
    elif any(a["estado"] != "PENDIENTE" for a in areas):
        estado = "EN_PROCESO"
    else:
        estado = "PENDIENTE"
    return areas, estado


# ===================== Consultas =====================
# Lecturas con execute_query (WF_003); conexion propia solo donde hay transaccion.

FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _rows(sql, params=None):
    return execute_query(sql, params or None, fetch="all") or []


def _cursor_rows(cursor):
    """Las mismas lecturas, dentro de la transaccion abierta en `cursor`."""
    def run(sql, params=None):
        cursor.execute(sql, params)
        return list(cursor.fetchall() or [])
    return run


_SELECT_RESUMEN = """
    SELECT s.*,
      (SELECT GROUP_CONCAT(CONCAT(o.origen, ' ', o.cantidad)
                           ORDER BY FIELD(o.origen, 'EMBARQUES', 'SMD', 'PRODUCCION') SEPARATOR ', ')
        FROM retrabajo_origenes o WHERE o.solicitud_id = s.id) AS origenes_txt,
      (SELECT COALESCE(SUM(o.cantidad), 0) FROM retrabajo_origenes o
        WHERE o.solicitud_id = s.id AND o.origen = 'EMBARQUES') AS emb_solicitado,
      (SELECT COALESCE(SUM(se.cantidad), 0) FROM retrabajo_salidas_embarques se
        WHERE se.solicitud_id = s.id) AS emb_surtido,
      (SELECT COUNT(*) FROM retrabajo_programaciones p WHERE p.solicitud_id = s.id) AS prog_total,
      (SELECT COUNT(*) FROM retrabajo_programaciones p JOIN fpa_requests f ON f.id = p.fpa_request_id
        WHERE p.solicitud_id = s.id AND f.status = 'COMPLETADA') AS prog_completas,
      (SELECT COUNT(*) FROM retrabajo_programaciones p JOIN fpa_requests f ON f.id = p.fpa_request_id
        WHERE p.solicitud_id = s.id AND f.status IN ('PARCIAL', 'COMPLETADA')) AS prog_iniciadas,
      (SELECT COALESCE(SUM(h.cantidad_impresa), 0) FROM qr_history h
        WHERE h.lote = s.lote_impresion AND h.es_reimpresion = 0
          AND h.impresora_utilizada <> 'Pendiente de impresión') AS impresas,
      (SELECT COUNT(*) FROM retrabajo_componentes c WHERE c.solicitud_id = s.id AND c.tipo = 'ASSY') AS comp_assy,
      (SELECT COUNT(*) FROM retrabajo_componentes c WHERE c.solicitud_id = s.id AND c.tipo IN ('SMD', 'IMD')) AS comp_smd,
      (SELECT COUNT(*) FROM retrabajo_escaneos e WHERE e.solicitud_id = s.id AND e.etapa = 'CP_RETRABAJO') AS esc_cp_retrabajo,
      (SELECT COUNT(*) FROM retrabajo_escaneos e WHERE e.solicitud_id = s.id AND e.etapa = 'CP_REPARACION') AS esc_cp_reparacion,
      (SELECT COUNT(*) FROM retrabajo_escaneos e WHERE e.solicitud_id = s.id AND e.etapa = 'SMD_REPARACION') AS esc_smd_reparacion
    FROM retrabajo_solicitudes s
"""

ESTADOS_TXT = {
    "PENDIENTE": "Pendiente",
    "EN_PROCESO": "En proceso",
    "COMPLETADA": "Completada",
    "CANCELADA": "Cancelada",
}


def _resumen_json(row):
    areas, estado = calcular_areas(row)
    return {
        "id": int(row["id"]),
        "folio": row.get("folio") or "",
        "np_origen": row.get("np_origen") or "",
        "np_destino": row.get("np_destino") or "",
        "cantidad": int(row.get("cantidad") or 0),
        "tipo_material": row.get("tipo_material") or "",
        "cambio_etiquetas": bool(row.get("cambio_etiquetas")),
        "lote_impresion": row.get("lote_impresion") or "",
        "comentarios": row.get("comentarios") or "",
        "origenes_txt": row.get("origenes_txt") or "",
        "status": row.get("status") or "",
        "estado": estado,
        "areas": areas,
        "emb_solicitado": int(row.get("emb_solicitado") or 0),
        "emb_surtido": int(row.get("emb_surtido") or 0),
        "solicitado_por": row.get("solicitado_por") or "",
        "cancelado_por": row.get("cancelado_por") or "",
        "cancelado_at": formatear_fecha_hora(row.get("cancelado_at")),
        "created_at": formatear_fecha_hora(row.get("created_at")),
    }


def _filtros_lista(args):
    """WHERE de la lista y del Excel. `codigo` busca en todo el historial (ignora fechas)."""
    codigo = sanitizar_texto(args.get("codigo"), 255)
    if codigo:
        return """
            WHERE s.folio = %s OR s.np_origen = %s OR s.np_destino = %s
               OR s.id IN (SELECT solicitud_id FROM retrabajo_escaneos
                           WHERE qr_smd_anterior = %s OR qr_smd_nuevo = %s
                              OR qr_assy_anterior = %s OR qr_assy_nuevo = %s)
               OR s.id IN (SELECT se.solicitud_id FROM retrabajo_salidas_embarques se
                           JOIN retrabajo_salidas_embarques_cajas c ON c.salida_id = se.id
                           WHERE c.box_code = %s)
        """, [codigo.upper()] * 3 + [codigo] * 4 + [codigo]
    where, params = [], []
    desde = sanitizar_texto(args.get("desde"), 10)
    hasta = sanitizar_texto(args.get("hasta"), 10)
    if FECHA_RE.match(desde):
        where.append("s.created_at >= %s")
        params.append(desde)
    if FECHA_RE.match(hasta):
        where.append("s.created_at < DATE_ADD(%s, INTERVAL 1 DAY)")
        params.append(hasta)
    return (" WHERE " + " AND ".join(where)) if where else "", params


def _listar(args, limit):
    where, params = _filtros_lista(args)
    estado = sanitizar_texto(args.get("estado"), 20).upper()
    # ponytail: el estado se calcula en Python sobre las ultimas `limit`; paginar si crece.
    rows = _rows(f"{_SELECT_RESUMEN} {where} ORDER BY s.id DESC LIMIT {int(limit)}", params)
    records = [_resumen_json(r) for r in rows]
    return [r for r in records if r["estado"] == estado] if estado else records


def _fetch_resumen(solicitud_id, rows=_rows):
    found = rows(_SELECT_RESUMEN + " WHERE s.id = %s", (solicitud_id,))
    return found[0] if found else None


def _detalle(solicitud_id):
    row = _fetch_resumen(solicitud_id)
    if not row:
        return None
    record = _resumen_json(row)
    record["origenes"] = [
        {"origen": r["origen"], "cantidad": int(r["cantidad"])}
        for r in _rows(
            "SELECT origen, cantidad FROM retrabajo_origenes WHERE solicitud_id = %s "
            "ORDER BY FIELD(origen, 'EMBARQUES', 'SMD', 'PRODUCCION')",
            (solicitud_id,),
        )
    ]
    record["componentes"] = _rows(
        "SELECT tipo, ubicacion, np_anterior, np_nuevo FROM retrabajo_componentes "
        "WHERE solicitud_id = %s ORDER BY id",
        (solicitud_id,),
    )
    record["programaciones"] = _rows(
        """
        SELECT p.ic_location, p.micom_part_no, p.programming_label, p.fpa_request_id,
               f.folio AS fpa_folio, f.status AS fpa_status
        FROM retrabajo_programaciones p
        LEFT JOIN fpa_requests f ON f.id = p.fpa_request_id
        WHERE p.solicitud_id = %s ORDER BY p.id
        """,
        (solicitud_id,),
    )
    record["salidas_embarques"] = _salidas_embarques(solicitud_id)
    record["escaneos"] = [
        {**r, "created_at": formatear_fecha_hora(r.get("created_at"))}
        for r in _rows(
            """
            SELECT etapa, qr_smd_anterior, qr_smd_nuevo, qr_assy_anterior, qr_assy_nuevo,
                   usuario, created_at
            FROM retrabajo_escaneos WHERE solicitud_id = %s ORDER BY id DESC
            """,
            (solicitud_id,),
        )
    ]
    return record


def _salidas_embarques(solicitud_id):
    rows = _rows(
        """
        SELECT se.id, se.folio, se.part_number, se.cantidad, se.registrado_por, se.created_at,
               GROUP_CONCAT(c.box_code ORDER BY c.id SEPARATOR ', ') AS cajas
        FROM retrabajo_salidas_embarques se
        LEFT JOIN retrabajo_salidas_embarques_cajas c ON c.salida_id = se.id
        WHERE se.solicitud_id = %s
        GROUP BY se.id ORDER BY se.id DESC
        """,
        (solicitud_id,),
    )
    return [
        {
            "folio": r.get("folio") or "",
            "part_number": r.get("part_number") or "",
            "cantidad": int(r.get("cantidad") or 0),
            "registrado_por": r.get("registrado_por") or "",
            "created_at": formatear_fecha_hora(r.get("created_at")),
            "cajas": [c for c in (r.get("cajas") or "").split(", ") if c],
        }
        for r in rows
    ]


def _opciones_programacion(part_no):
    select = (
        "SELECT bom_part_no, item_no, spec, location_text FROM v_ecos_bom_latest "
        "WHERE item_name = 'MICOM ASSY'"
    )
    rows = _rows(f"{select} AND bom_part_no = %s ORDER BY location_text, item_no", (part_no,))
    if not rows:
        rows = _rows(
            f"{select} AND root_part_no = %s ORDER BY bom_part_no, location_text, item_no",
            (part_no,),
        )
    opciones = {}
    for row in rows:
        opcion = opcion_programacion(row)
        if opcion:
            opciones.setdefault((opcion["ic_location"], opcion["programming_label"]), opcion)
    return list(opciones.values())


def _crear_lote_impresion(cursor, folio, np_destino, cantidad, fecha):
    """Fila plan_smt que Modulo IMPRESION muestra como lote pendiente de retrabajo.

    Lote SMT-YYMMDD-8NNN: el generador de lotes del MES solo cuenta sufijos de
    1-3 digitos y el 'sin plan' de IMPRESION usa 9NNN. working_date NULL la
    deja fuera de las vistas de plan del MES. Requiere el GET_LOCK del caller.
    """
    prefix = f"SMT-{fecha.strftime('%y%m%d')}"
    cursor.execute(
        "SELECT MAX(CAST(SUBSTRING_INDEX(lot_no, '-', -1) AS UNSIGNED)) AS max_seq "
        "FROM plan_smt WHERE lot_no REGEXP %s",
        (f"^{prefix}-8[0-9]{{3}}$",),
    )
    max_seq = int((cursor.fetchone() or {}).get("max_seq") or 7999)
    if max_seq >= 8999:
        raise ValueError("Se agotaron los lotes de retrabajo del día.")
    lote = f"{prefix}-{max_seq + 1}"
    cursor.execute("SELECT model FROM raw_smd WHERE part_no = %s LIMIT 1", (np_destino,))
    model = (cursor.fetchone() or {}).get("model") or np_destino
    cursor.execute(
        """
        INSERT INTO plan_smt
            (lot_no, wo_code, working_date, line, shift, model_code, part_no, process,
             plan_count, status, routing)
        VALUES (%s, %s, NULL, 'RETRABAJO', 'DIA', %s, %s, 'SMT', %s, 'PLAN', 'RETRABAJO')
        """,
        (lote, folio, model, np_destino, cantidad),
    )
    return lote


def _usuario():
    return session.get("usuario") or "SISTEMA"


def _error(message, status=400):
    return jsonify({"success": False, "error": message}), status


def _es_duplicado(exc):
    args = getattr(exc, "args", ()) or ()
    return (args[0] if args else None) == 1062 or "Duplicate entry" in str(exc)


# ===================== Rutas =====================

@bp.route("/control_produccion/retrabajo")
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def retrabajo_ajax():
    try:
        return render_template("Control de produccion/retrabajo_ajax.html")
    except Exception as exc:
        logger.exception("Error al cargar Solicitud de retrabajo: %s", exc)
        return "Error al cargar el contenido.", 500


@bp.route("/api/retrabajo/programacion", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def programacion_opciones():
    part_no = sanitizar_texto(request.args.get("part_no"), 64).upper()
    if not PART_RE.match(part_no):
        return _error("Número de parte inválido.")
    try:
        return jsonify({"success": True, "records": _opciones_programacion(part_no)})
    except Exception as exc:
        logger.exception("Error consultando programacion de %s: %s", part_no, exc)
        return _error(ERROR_INTERNO, 500)


@bp.route("/api/retrabajo", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def listar_solicitudes():
    try:
        return jsonify({"success": True, "records": _listar(request.args, 500)})
    except Exception as exc:
        logger.exception("Error listando retrabajos: %s", exc)
        return _error(ERROR_INTERNO, 500)


@bp.route("/api/retrabajo/export", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def exportar_solicitudes():
    """Mismos filtros que la lista, con el estilo Excel de los historiales ICT."""
    try:
        items = [
            {
                **r,
                "material": "ASSY" if r["tipo_material"] == "ASSY" else "IMD-SMD",
                "areas_txt": ", ".join(f"{a['nombre']} {a['hecho']}/{a['total']}" for a in r["areas"]),
                "estado_txt": ESTADOS_TXT.get(r["estado"], r["estado"]),
            }
            for r in _listar(request.args, 5000)
        ]
        headers = ["Folio", "NP origen", "NP destino", "Cantidad", "Material", "Origen",
                   "Áreas", "Estado", "Solicitó", "Fecha", "Comentarios"]
        keys = ["folio", "np_origen", "np_destino", "cantidad", "material", "origenes_txt",
                "areas_txt", "estado_txt", "solicitado_por", "created_at", "comentarios"]
        widths = [18, 14, 14, 10, 10, 28, 70, 12, 16, 20, 40]
        filename = f"retrabajo_{obtener_fecha_hora_mexico().strftime('%Y%m%d_%H%M%S')}"
        return excel_response_ict(items, headers, keys, widths, sheet="Retrabajo",
                                  filename=filename, freeze="A2")
    except Exception as exc:
        logger.exception("Error exportando retrabajos: %s", exc)
        return _error(ERROR_INTERNO, 500)


@bp.route("/api/retrabajo/<int:solicitud_id>", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def detalle_solicitud(solicitud_id):
    try:
        record = _detalle(solicitud_id)
        if not record:
            return _error("Solicitud no encontrada.", 404)
        return jsonify({"success": True, "record": record})
    except Exception as exc:
        logger.exception("Error obteniendo retrabajo %s: %s", solicitud_id, exc)
        return _error(ERROR_INTERNO, 500)


@bp.route("/api/retrabajo", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def crear_solicitud():
    key = sanitizar_texto(request.headers.get("Idempotency-Key"), 64)
    if not key:
        return _error("Idempotency-Key es requerido.")
    payload, errors = validar_solicitud(request.get_json(silent=True) or {})
    if errors:
        return _error(" ".join(errors))

    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    lock_name = None
    try:
        cursor.execute("SELECT id FROM retrabajo_solicitudes WHERE idempotency_key = %s", (key,))
        existing = cursor.fetchone()
        if existing:
            return jsonify({"success": True, "record": _detalle(existing["id"]), "replayed": True})

        cursor.execute(
            "SELECT part_no FROM raw WHERE part_no IN (%s, %s)",
            (payload["np_origen"], payload["np_destino"]),
        )
        conocidos = {str(r["part_no"]).upper() for r in cursor.fetchall() or []}
        faltantes = {payload["np_origen"], payload["np_destino"]} - conocidos
        if faltantes:
            return _error(f"Número de parte no registrado: {', '.join(sorted(faltantes))}.")

        programaciones = []
        if payload["programaciones"]:
            opciones = {
                (o["ic_location"], o["programming_label"]): o
                for o in _opciones_programacion(payload["np_destino"])
            }
            for item in payload["programaciones"]:
                opcion = opciones.get((item["ic_location"], item["programming_label"]))
                if not opcion:
                    return _error(
                        f"La programación {item['programming_label']} ({item['ic_location']}) "
                        f"no corresponde al BOM vigente de {payload['np_destino']}.",
                        409,
                    )
                programaciones.append(opcion)

        ahora = obtener_fecha_hora_mexico()
        if payload["cambio_etiquetas"]:
            lock_name = f"retrabajo_lote_{ahora.strftime('%y%m%d')}"
            cursor.execute("SELECT GET_LOCK(%s, 10) AS ok", (lock_name,))
            if int((cursor.fetchone() or {}).get("ok") or 0) != 1:
                lock_name = None
                return _error("No se pudo reservar el lote de impresión, intente de nuevo.", 503)

        cursor.execute("START TRANSACTION")
        cursor.execute(
            """
            INSERT INTO retrabajo_solicitudes
                (idempotency_key, np_origen, np_destino, cantidad, tipo_material,
                 cambio_etiquetas, comentarios, solicitado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                key, payload["np_origen"], payload["np_destino"], payload["cantidad"],
                payload["tipo_material"], 1 if payload["cambio_etiquetas"] else 0,
                payload["comentarios"], _usuario(),
            ),
        )
        solicitud_id = cursor.lastrowid
        folio = f"RT-{ahora.strftime('%Y%m%d')}-{solicitud_id}"
        lote = (
            _crear_lote_impresion(cursor, folio, payload["np_destino"], payload["cantidad"], ahora)
            if payload["cambio_etiquetas"] else None
        )
        cursor.execute(
            "UPDATE retrabajo_solicitudes SET folio = %s, lote_impresion = %s WHERE id = %s",
            (folio, lote, solicitud_id),
        )
        for origen in payload["origenes"]:
            cursor.execute(
                "INSERT INTO retrabajo_origenes (solicitud_id, origen, cantidad) VALUES (%s, %s, %s)",
                (solicitud_id, origen["origen"], origen["cantidad"]),
            )
        for comp in payload["componentes"]:
            cursor.execute(
                """
                INSERT INTO retrabajo_componentes (solicitud_id, tipo, ubicacion, np_anterior, np_nuevo)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (solicitud_id, comp["tipo"], comp["ubicacion"], comp["np_anterior"], comp["np_nuevo"]),
            )
        for prog in programaciones:
            # Los reintentos con la misma Idempotency-Key reusan la FPA ya creada.
            response = request_micom(
                "POST",
                "/api/fpa/requests",
                actor=_usuario(),
                payload={
                    "fpaPartNumber": f"RETRABAJO {payload['np_destino']}",
                    "pgmMicom": prog["programming_label"],
                    "micomQuantity": payload["cantidad"],
                },
                idempotency_key=f"{key}-{prog['ic_location']}"[:100],
            )
            cursor.execute(
                """
                INSERT INTO retrabajo_programaciones
                    (solicitud_id, ic_location, micom_part_no, programming_label, fpa_request_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    solicitud_id, prog["ic_location"], prog["micom_part_no"],
                    prog["programming_label"], (response.get("data") or {}).get("id"),
                ),
            )
        conn.commit()
        record = _detalle(solicitud_id)
        auth_system.registrar_auditoria(
            _usuario(), "Solicitud de retrabajo", "CREAR",
            descripcion=f"Retrabajo {folio}", datos_despues=record,
        )
        return jsonify({"success": True, "record": record}), 201
    except FpaMicomError as exc:
        conn.rollback()
        return _error(f"No se pudo solicitar etiquetas a MICOM: {exc}", 503)
    except ValueError as exc:
        conn.rollback()
        return _error(str(exc), 409)
    except Exception as exc:
        conn.rollback()
        if _es_duplicado(exc):
            return _error("La solicitud ya fue registrada; actualice la lista.", 409)
        logger.exception("Error creando retrabajo: %s", exc)
        return _error(ERROR_INTERNO, 500)
    finally:
        if lock_name:
            cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
        cursor.close()
        conn.close()


@bp.route("/api/retrabajo/<int:solicitud_id>/cancelar", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def cancelar_solicitud(solicitud_id):
    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        cursor.execute("START TRANSACTION")
        cursor.execute(
            "SELECT id, folio, status, lote_impresion FROM retrabajo_solicitudes WHERE id = %s FOR UPDATE",
            (solicitud_id,),
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return _error("Solicitud no encontrada.", 404)
        if row["status"] != "ACTIVA":
            conn.rollback()
            return _error("La solicitud ya está cancelada.", 409)
        cursor.execute(
            "UPDATE retrabajo_solicitudes SET status = 'CANCELADA', cancelado_por = %s, "
            "cancelado_at = %s WHERE id = %s",
            (_usuario(), obtener_fecha_hora_mexico(), solicitud_id),
        )
        if row.get("lote_impresion"):
            cursor.execute(
                "UPDATE plan_smt SET status = 'CANCELADO' WHERE lot_no = %s AND routing = 'RETRABAJO'",
                (row["lote_impresion"],),
            )
        conn.commit()

        # MICOM no puede bajar de lo ya consumido; si no responde se avisa.
        avisos = []
        cursor.execute(
            """
            SELECT p.fpa_request_id, COALESCE(i.consumed_quantity, 0) AS consumido
            FROM retrabajo_programaciones p
            LEFT JOIN fpa_request_items i ON i.request_id = p.fpa_request_id AND i.label_type = 'MICOM'
            WHERE p.solicitud_id = %s AND p.fpa_request_id IS NOT NULL
            """,
            (solicitud_id,),
        )
        for prog in cursor.fetchall() or []:
            try:
                request_micom(
                    "PATCH",
                    f"/api/fpa/requests/{prog['fpa_request_id']}/quantities",
                    actor=_usuario(),
                    payload={
                        "micomQuantity": int(prog["consumido"] or 0),
                        "reason": f"Retrabajo {row['folio']} cancelado",
                    },
                )
            except FpaMicomError as exc:
                avisos.append(f"FPA {prog['fpa_request_id']}: {exc}")

        auth_system.registrar_auditoria(
            _usuario(), "Solicitud de retrabajo", "CANCELAR", descripcion=f"Retrabajo {row['folio']}",
        )
        return jsonify({"success": True, "record": _detalle(solicitud_id), "avisos": avisos})
    except Exception as exc:
        conn.rollback()
        logger.exception("Error cancelando retrabajo %s: %s", solicitud_id, exc)
        return _error(ERROR_INTERNO, 500)
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/retrabajo/embarques/pendientes", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_EMBARQUES)
def embarques_pendientes():
    try:
        rows = _rows(
            f"""
            SELECT * FROM ({_SELECT_RESUMEN} WHERE s.status = 'ACTIVA') t
            WHERE t.emb_solicitado > t.emb_surtido ORDER BY t.id
            """
        )
        return jsonify({"success": True, "records": [_resumen_json(r) for r in rows]})
    except Exception as exc:
        logger.exception("Error listando pendientes de Embarques: %s", exc)
        return _error(ERROR_INTERNO, 500)


@bp.route("/api/retrabajo/embarques/salidas", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_EMBARQUES)
def embarques_salidas():
    solicitud_id = _entero(request.args.get("solicitud_id"))
    if not solicitud_id:
        return _error("solicitud_id es requerido.")
    try:
        return jsonify({"success": True, "records": _salidas_embarques(solicitud_id)})
    except Exception as exc:
        logger.exception("Error listando salidas de retrabajo %s: %s", solicitud_id, exc)
        return _error(ERROR_INTERNO, 500)


@bp.route("/api/retrabajo/<int:solicitud_id>/salida-embarques", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_EMBARQUES)
def registrar_salida_embarques(solicitud_id):
    data = request.get_json(silent=True) or {}
    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        cursor.execute("START TRANSACTION")
        cursor.execute("SELECT id FROM retrabajo_solicitudes WHERE id = %s FOR UPDATE", (solicitud_id,))
        solicitud = _fetch_resumen(solicitud_id, _cursor_rows(cursor)) if cursor.fetchone() else None
        salida, error = validar_salida_embarques(
            solicitud, data, (solicitud or {}).get("emb_surtido")
        )
        if error:
            conn.rollback()
            return _error(error, 404 if not solicitud else 409)
        cursor.execute(
            """
            INSERT INTO retrabajo_salidas_embarques (solicitud_id, part_number, cantidad, registrado_por)
            VALUES (%s, %s, %s, %s)
            """,
            (solicitud_id, salida["part_number"], salida["cantidad"], _usuario()),
        )
        salida_id = cursor.lastrowid
        folio = f"RTS-{obtener_fecha_hora_mexico().strftime('%Y%m%d')}-{salida_id}"
        cursor.execute("UPDATE retrabajo_salidas_embarques SET folio = %s WHERE id = %s", (folio, salida_id))
        for caja in salida["cajas"]:
            cursor.execute(
                "INSERT INTO retrabajo_salidas_embarques_cajas (salida_id, box_code) VALUES (%s, %s)",
                (salida_id, caja),
            )
        conn.commit()
        auth_system.registrar_auditoria(
            _usuario(), "Salida retrabajo Embarques", "SALIDA",
            descripcion=f"{folio} para {solicitud['folio']}", datos_despues={**salida, "folio": folio},
        )
        return jsonify({
            "success": True,
            "folio": folio,
            "record": _resumen_json(_fetch_resumen(solicitud_id, _cursor_rows(cursor))),
        }), 201
    except Exception as exc:
        conn.rollback()
        if _es_duplicado(exc):
            return _error("Una de las cajas ya salió a retrabajo.", 409)
        logger.exception("Error registrando salida de retrabajo %s: %s", solicitud_id, exc)
        return _error(ERROR_INTERNO, 500)
    finally:
        cursor.close()
        conn.close()
