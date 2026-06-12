"""CRUD de materiales (Informacion Basica) sobre la tabla `materiales`.

Reconstruccion 2026-06-12 del modulo eliminado (ver app/routes.py:609-612).

Alcance: el modulo web gestiona SOLO estas columnas de `materiales`:
  numero_parte, propiedad_material, clasificacion, especificacion_material,
  unidad_empaque, unidad_medida, vendedor, fecha_registro, usuario_registro.
Las ~45 columnas restantes (codigo_material, ubicaciones, MSL, IQC, etc.)
quedan con sus DEFAULT y se siguen gestionando en la app de escritorio
Flutter `Control_de_material_de_almacen`, que comparte esta misma tabla.

Costos: tabla nueva `material_costos`, costo POR VENDEDOR con moneda e
historial (cada cambio es un INSERT; el vigente por (numero_parte, vendedor)
es la fila con MAX(id)). `materiales.vendedor` guarda los vendedores
comma-separated (join ", " / split ",") igual que la app de escritorio.

WF_001: opcion en LISTA_INFORMACIONBASICA / Control de material.
WF_002: template AJAX en INFORMACION BASICA/CONTROL_DE_MATERIAL.html.
WF_003: blueprint dueno de render y APIs JSON + export Excel.
WF_004: CSS persistente en MainTemplate.html y asegurado desde JS.
WF_005: nada de handlers inline; texto escapado en el JS del modulo.
"""

import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

from app.api.shared import (
    conexion_o_error,
    dict_cursor,
    excel_response,
    formatear_fecha_hora,
    login_requerido,
    obtener_fecha_hora_mexico,
    requiere_permiso_dropdown,
    sanitizar_texto,
)
from app.api.control_material.invoice_core.normalizers import normalizar_numero_parte
from app.api.control_material.invoice_core.service import _parse_alias_workbook
from app.db_mysql import execute_query

logger = logging.getLogger(__name__)

bp = Blueprint("informacion_basica_control_material", __name__)

PERMISO_MODULO = (
    "LISTA_INFORMACIONBASICA",
    "Control de material",
    "Control de material",
)

MONEDAS_VALIDAS = {"USD", "MXN", "KRW"}
MONEDA_DEFAULT = "USD"

# Mensaje generico para errores 500: no se filtra str(exc) al frontend
# (evita exponer SQL, nombres de tabla o rutas internas). El detalle queda
# en el log via logger.exception.
ERROR_INTERNO = "Error interno del servidor."

# Maximo representable por costo_unitario_material DECIMAL(12,4). Validar antes
# de insertar evita que MySQL aborte con "Out of range value".
MAX_COSTO = Decimal("99999999.9999")

# Limite de la columna materiales.vendedor (varchar(100)). El string unido
# ", ".join(vendedores) debe caber para no truncar la lista que lee Flutter.
VENDEDOR_COLUMN_MAX = 100


def crear_tabla_material_costos():
    """Crea `material_costos` si no existe (historial de costo por vendedor).

    Sin FOREIGN KEY a `materiales`: la app de escritorio inserta/borra
    materiales fuera del web; un FK romperia esos flujos. La limpieza de
    costos al borrar un material la hace el endpoint DELETE de este modulo.
    El indice idx_mcost_parte_vendedor (numero_parte(191), vendedor, id) cubre
    el lookup del costo vigente (MAX(id) por par); el prefijo (191) es por el
    limite de 3072 bytes del indice en utf8mb4. Si el historial llega a millones
    de filas, validar el plan de _costos_vigentes con EXPLAIN.

    Tambien asegura las columnas auxiliares del web sobre `materiales`
    (soft-delete y auditoria de edicion); ver _asegurar_columnas_materiales.
    """
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS material_costos (
            id INT NOT NULL AUTO_INCREMENT,
            numero_parte VARCHAR(512) NOT NULL,
            vendedor VARCHAR(100) NOT NULL,
            costo_unitario_material DECIMAL(12,4) NOT NULL DEFAULT 0.0000,
            moneda VARCHAR(10) NOT NULL DEFAULT 'USD',
            usuario_registro VARCHAR(255) NOT NULL DEFAULT 'SISTEMA',
            fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_mcost_parte_vendedor (numero_parte(191), vendedor, id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    _crear_tabla_material_part_aliases()
    _asegurar_columnas_materiales()


def _crear_tabla_material_part_aliases():
    """Asegura el catalogo de equivalencias invoice/packing -> sistema.

    El DDL/migracion vive en invoice_core.ddl (unico dueño); aqui solo se
    delega para que el modulo funcione aunque init_material_invoice_tables()
    no haya corrido aun. Import diferido para no acoplar el arranque.
    """
    from app.api.control_material.invoice_core.ddl import (
        ensure_material_part_aliases_table,
    )
    ensure_material_part_aliases_table()


def _asegurar_columnas_materiales():
    """Agrega columnas auxiliares del web a `materiales` si no existen.

    - activo: soft-delete (el web nunca borra fisico; UPDATE activo=0).
    - usuario_modificacion / fecha_modificacion: auditoria de edicion.

    La app de escritorio Flutter ignora estas columnas (no rompe nada). El
    DEFAULT 1 en `activo` deja los 752 materiales existentes como activos.
    Patron idempotente SHOW COLUMNS + ALTER (igual que bom_revisions.py).
    """
    columnas = (
        ("activo", "activo TINYINT NOT NULL DEFAULT 1"),
        ("usuario_modificacion", "usuario_modificacion VARCHAR(255) NULL"),
        ("fecha_modificacion", "fecha_modificacion DATETIME NULL"),
    )
    for nombre, definicion in columnas:
        existing = execute_query(
            "SHOW COLUMNS FROM materiales LIKE %s", (nombre,), fetch="one"
        )
        if not existing:
            execute_query(f"ALTER TABLE materiales ADD COLUMN {definicion}")


# ===================== Helpers internos =====================

def _usuario_actual():
    return session.get("usuario") or "SISTEMA"


def _decimal_str(value):
    """Serializa un DECIMAL(12,4) como string de 4 decimales (sin perder
    precision en float). None -> None."""
    if value is None:
        return None
    try:
        return f"{Decimal(str(value)):.4f}"
    except (InvalidOperation, ValueError):
        return str(value)


def _parse_costo(value):
    """Convierte el costo de entrada a Decimal(>=0) con 4 decimales.
    Devuelve (Decimal, error|None)."""
    if value is None or str(value).strip() == "":
        return Decimal("0.0000"), None
    try:
        dec = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None, "El costo debe ser un numero valido."
    if dec < 0:
        return None, "El costo no puede ser negativo."
    # Validar el maximo ANTES de quantize: para valores con demasiados digitos
    # quantize() lanzaria InvalidOperation (excede la precision del contexto).
    if dec > MAX_COSTO:
        return None, "El costo excede el maximo permitido (99,999,999.9999)."
    try:
        dec = dec.quantize(Decimal("0.0001"))
    except InvalidOperation:
        return None, "El costo debe tener un formato valido."
    return dec, None


def _split_vendedores(vendedor_str):
    """materiales.vendedor (comma-separated) -> lista de vendedores."""
    if not vendedor_str:
        return []
    return [v.strip() for v in str(vendedor_str).split(",") if v.strip()]


def _parse_vendedores(payload):
    """Valida la lista de vendedores+costo del payload del formulario.

    Entrada: payload["vendedores"] = [{vendedor, costo, moneda}, ...].
    Devuelve (vendedor_str, costos, errors) donde:
      vendedor_str -> ", ".join de los nombres (para materiales.vendedor)
      costos       -> [{"vendedor", "costo": Decimal, "moneda"}]
    """
    raw = payload.get("vendedores")
    if not isinstance(raw, list):
        raw = []

    costos = []
    nombres = []
    errors = []
    vistos = set()

    for item in raw:
        if not isinstance(item, dict):
            continue
        vendedor = sanitizar_texto(item.get("vendedor"), 100)
        if not vendedor:
            continue
        if "," in vendedor:
            errors.append(
                f"El vendedor '{vendedor}' no puede contener comas."
            )
            continue
        clave = vendedor.lower()
        if clave in vistos:
            errors.append(f"El vendedor '{vendedor}' esta duplicado.")
            continue
        vistos.add(clave)

        costo, costo_error = _parse_costo(item.get("costo"))
        if costo_error:
            errors.append(f"{vendedor}: {costo_error}")
            continue

        moneda = sanitizar_texto(item.get("moneda"), 10).upper() or MONEDA_DEFAULT
        if moneda not in MONEDAS_VALIDAS:
            errors.append(
                f"{vendedor}: la moneda debe ser una de {', '.join(sorted(MONEDAS_VALIDAS))}."
            )
            continue

        nombres.append(vendedor)
        costos.append({"vendedor": vendedor, "costo": costo, "moneda": moneda})

    vendedor_str = ", ".join(nombres)
    if len(vendedor_str) > VENDEDOR_COLUMN_MAX:
        errors.append(
            "La lista de vendedores excede el limite de "
            f"{VENDEDOR_COLUMN_MAX} caracteres."
        )

    return vendedor_str, costos, errors


def _costos_vigentes(cursor, numeros_parte=None):
    """Costo vigente (MAX(id)) por (numero_parte, vendedor).

    Devuelve dict numero_parte -> {vendedor_lower: {vendedor, costo, moneda,
    usuario_registro, fecha_registro}}.
    """
    # El filtro va DENTRO del subquery: restringe el GROUP BY al subconjunto
    # de materiales listados en vez de agregar todo el historial. Aprovecha el
    # indice idx_mcost_parte_vendedor (numero_parte(191), vendedor, id).
    params = []
    where_sub = ""
    if numeros_parte:
        placeholders = ", ".join(["%s"] * len(numeros_parte))
        where_sub = f"WHERE numero_parte IN ({placeholders})"
        params = list(numeros_parte)

    sql = f"""
        SELECT mc.numero_parte, mc.vendedor, mc.costo_unitario_material,
               mc.moneda, mc.usuario_registro, mc.fecha_registro
        FROM material_costos mc
        JOIN (
            SELECT numero_parte, vendedor, MAX(id) AS max_id
            FROM material_costos
            {where_sub}
            GROUP BY numero_parte, vendedor
        ) ult ON ult.max_id = mc.id
    """

    cursor.execute(sql, params)
    resultado = {}
    for row in cursor.fetchall() or []:
        np = row["numero_parte"]
        resultado.setdefault(np, {})[row["vendedor"].lower()] = {
            "vendedor": row["vendedor"],
            "costo": _decimal_str(row["costo_unitario_material"]),
            "moneda": row["moneda"],
            "usuario_registro": row.get("usuario_registro") or "",
            "fecha_registro": formatear_fecha_hora(row.get("fecha_registro")),
        }
    return resultado


def _costos_para_material(vigentes_np, vendedores):
    """Filtra los costos vigentes a los vendedores actuales del material,
    en el mismo orden en que aparecen en materiales.vendedor."""
    costos = []
    for vendedor in vendedores:
        info = (vigentes_np or {}).get(vendedor.lower())
        if info:
            costos.append(info)
        else:
            costos.append(
                {
                    "vendedor": vendedor,
                    "costo": None,
                    "moneda": "",
                    "usuario_registro": "",
                    "fecha_registro": "",
                }
            )
    return costos


def _aliases_por_material(cursor, numeros_parte):
    """Aliases activos por parte sistema: todos y solo globales."""
    if not numeros_parte:
        return {}, {}
    placeholders = ", ".join(["%s"] * len(numeros_parte))
    cursor.execute(
        f"""
        SELECT numero_parte_original, numero_parte_sistema, tipo
        FROM material_part_aliases
        WHERE activo = 1
          AND numero_parte_sistema IN ({placeholders})
        ORDER BY numero_parte_original ASC, tipo ASC, id DESC
        """,
        list(numeros_parte),
    )
    todos = {}
    globales = {}
    for row in cursor.fetchall() or []:
        numero_parte = row["numero_parte_sistema"]
        alias = row["numero_parte_original"]
        tipo = row.get("tipo") or ""
        todos.setdefault(numero_parte, []).append(
            f"{alias} ({tipo})" if tipo else alias
        )
        if not tipo:
            globales.setdefault(numero_parte, []).append(alias)
    return todos, globales


def _parse_numeros_parte_original(value):
    """Numeros originales globales separados por coma, punto y coma, tab o saltos."""
    raw_items = value if isinstance(value, list) else re.split(r"[,;\n\r\t]+", str(value or ""))
    aliases = []
    vistos = set()
    for raw in raw_items:
        alias = normalizar_numero_parte(raw)
        if not alias or alias in vistos:
            continue
        vistos.add(alias)
        aliases.append(alias)
    return aliases


def _sync_numeros_parte_original(cursor, numero_parte, originales, usuario, fecha):
    """Sincroniza numeros originales globales sin tocar registros por tipo."""
    cursor.execute(
        """
        SELECT numero_parte_original
        FROM material_part_aliases
        WHERE numero_parte_sistema = %s
          AND activo = 1
          AND COALESCE(tipo, '') = ''
        """,
        (numero_parte,),
    )
    actuales = {row["numero_parte_original"] for row in (cursor.fetchall() or [])}
    deseados = set(originales or [])

    for original in actuales - deseados:
        cursor.execute(
            """
            UPDATE material_part_aliases
            SET activo = 0
            WHERE numero_parte_original = %s
              AND numero_parte_sistema = %s
              AND COALESCE(tipo, '') = ''
            """,
            (original, numero_parte),
        )

    for original in sorted(deseados):
        cursor.execute(
            """
            INSERT INTO material_part_aliases (
                numero_parte_original, numero_parte_sistema, tipo,
                usuario_registro, fecha_registro, activo
            ) VALUES (%s, %s, '', %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                numero_parte_sistema = VALUES(numero_parte_sistema),
                usuario_registro = VALUES(usuario_registro),
                fecha_registro = VALUES(fecha_registro),
                activo = 1
            """,
            (original, numero_parte, usuario, fecha),
        )


def _materiales_existentes(cursor, numeros_parte):
    numeros = sorted({normalizar_numero_parte(numero) for numero in numeros_parte if numero})
    existentes = set()
    for idx in range(0, len(numeros), 500):
        bloque = numeros[idx:idx + 500]
        placeholders = ", ".join(["%s"] * len(bloque))
        cursor.execute(
            f"""
            SELECT numero_parte
            FROM materiales
            WHERE activo = 1
              AND numero_parte IN ({placeholders})
            """,
            tuple(bloque),
        )
        existentes.update(row["numero_parte"] for row in (cursor.fetchall() or []))
    return existentes


def _upsert_numero_parte_original(cursor, original, sistema, tipo, usuario, fecha):
    cursor.execute(
        """
        INSERT INTO material_part_aliases (
            numero_parte_original, numero_parte_sistema, tipo,
            usuario_registro, fecha_registro, activo
        ) VALUES (%s, %s, %s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE
            numero_parte_sistema = VALUES(numero_parte_sistema),
            usuario_registro = VALUES(usuario_registro),
            fecha_registro = VALUES(fecha_registro),
            activo = 1
        """,
        (original, sistema, tipo or "", usuario, fecha),
    )


def _analizar_numeros_parte_original(cursor, records, skipped_excel, tipo_default, conflicts=None):
    conflicts = conflicts or []
    materiales_existentes = _materiales_existentes(
        cursor,
        (record["numero_parte_sistema"] for record in records),
    )
    originales = sorted({record["numero_parte_original"] for record in records})
    existentes = {}
    for idx in range(0, len(originales), 500):
        bloque = originales[idx:idx + 500]
        placeholders = ", ".join(["%s"] * len(bloque))
        cursor.execute(
            f"""
            SELECT numero_parte_original, numero_parte_sistema,
                   COALESCE(tipo, '') AS tipo, activo
            FROM material_part_aliases
            WHERE numero_parte_original IN ({placeholders})
            """,
            tuple(bloque),
        )
        for row in cursor.fetchall() or []:
            existentes[(row["numero_parte_original"], row.get("tipo") or "")] = row

    conflict_rows = []
    for conflict in conflicts:
        sistemas = conflict.get("sistemas") or []
        filas = [str(row_no) for row_no in (conflict.get("filas") or []) if row_no]
        detalle = conflict.get("detalle") or "Mismo numero original + tipo apunta a varios sistemas"
        if filas:
            detalle = f"{detalle}. Filas: {', '.join(filas)}"
        conflict_rows.append(
            {
                "numero_parte_original": conflict.get("numero_parte_original") or "",
                "numero_parte_sistema": " / ".join(sistemas),
                "tipo": conflict.get("tipo") or "",
                "estatus": "CONFLICTO",
                "detalle": detalle,
            }
        )

    rows = []
    counts = {
        "nuevos": 0,
        "actualizados": 0,
        "sin_cambio": 0,
        "reactivados": 0,
        "omitidos_sistema": 0,
        "conflictos": len(conflicts),
    }
    importables_records = []
    omitidos_sistema = []

    for record in records:
        original = record["numero_parte_original"]
        sistema = record["numero_parte_sistema"]
        tipo = record.get("tipo") or tipo_default or ""
        existente = existentes.get((original, tipo))
        estatus = "NUEVO"
        detalle = "Se creara equivalencia"
        importable = sistema in materiales_existentes

        if not importable:
            estatus = "OMITIDO"
            detalle = "La parte sistema no existe activa en materiales"
            counts["omitidos_sistema"] += 1
            omitidos_sistema.append(
                {
                    "numero_parte_original": original,
                    "numero_parte_sistema": sistema,
                    "tipo": tipo,
                    "motivo": "PARTE_SISTEMA_NO_EXISTE",
                }
            )
        elif not existente:
            counts["nuevos"] += 1
        elif int(existente.get("activo") or 0) == 0:
            estatus = "REACTIVAR"
            detalle = "Se reactivara equivalencia"
            if (existente.get("numero_parte_sistema") or "") != sistema:
                detalle = f"Se reactivara y cambiara desde {existente.get('numero_parte_sistema') or ''}"
            counts["reactivados"] += 1
        elif (existente.get("numero_parte_sistema") or "") == sistema:
            estatus = "SIN_CAMBIO"
            detalle = "La equivalencia ya existe activa"
            counts["sin_cambio"] += 1
        else:
            estatus = "ACTUALIZAR"
            detalle = f"Cambiara desde {existente.get('numero_parte_sistema') or ''}"
            counts["actualizados"] += 1

        if importable:
            importables_records.append({**record, "tipo": tipo})

        rows.append(
            {
                "numero_parte_original": original,
                "numero_parte_sistema": sistema,
                "tipo": tipo,
                "estatus": estatus,
                "detalle": detalle,
            }
        )

    rows = conflict_rows + rows
    importables = len(importables_records)
    total_omitidos = skipped_excel + counts["omitidos_sistema"] + counts["conflictos"]
    return {
        "total_detectados": len(records) + counts["conflictos"],
        "importables": importables,
        "omitidos": total_omitidos,
        "omitidos_excel": skipped_excel,
        "omitidos_sistema": counts["omitidos_sistema"],
        "omitidos_conflicto": counts["conflictos"],
        "nuevos": counts["nuevos"],
        "actualizados": counts["actualizados"],
        "sin_cambio": counts["sin_cambio"],
        "reactivados": counts["reactivados"],
        "conflictos": counts["conflictos"],
        "conflictos_preview": conflicts[:50],
        "preview": rows[:100],
        "preview_total": len(rows),
        "omitidos_sistema_preview": omitidos_sistema[:50],
        "_importables_records": importables_records,
    }


def _leer_excel_numeros_originales(files):
    uploaded = files.get("file") or files.get("archivo")
    if not uploaded:
        return None, None, None, None, (jsonify({"success": False, "error": "Archivo requerido."}), 400)

    filename = secure_filename(uploaded.filename or "numeros_originales.xlsx")
    file_bytes = uploaded.read()
    if not file_bytes:
        return None, None, None, None, (jsonify({"success": False, "error": "El archivo esta vacio."}), 400)

    try:
        records, skipped_excel, conflicts = _parse_alias_workbook(file_bytes, include_conflicts=True)
    except Exception as exc:
        logger.exception("Error leyendo numeros originales desde %s: %s", filename, exc)
        return None, None, None, None, (
            jsonify({"success": False, "error": "No se pudo leer el Excel de numeros originales."}),
            400,
        )

    if not records and not conflicts:
        return None, None, None, None, (
            jsonify(
                {
                    "success": False,
                    "error": "No se detectaron columnas de numero de parte original y parte sistema.",
                }
            ),
            400,
        )

    return filename, records, skipped_excel, conflicts, None


def _insertar_costos(cursor, numero_parte, costos, usuario, fecha):
    """Inserta una fila por cada vendedor con costo (siempre, para alta)."""
    for c in costos:
        cursor.execute(
            """
            INSERT INTO material_costos
                (numero_parte, vendedor, costo_unitario_material, moneda,
                 usuario_registro, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (numero_parte, c["vendedor"], str(c["costo"]), c["moneda"], usuario, fecha),
        )


def _insertar_costos_si_cambiaron(cursor, numero_parte, costos, vigentes_np, usuario, fecha):
    """Inserta solo si (costo, moneda) cambio o el vendedor no tenia costo.
    Preserva la semantica de historial sin filas redundantes."""
    for c in costos:
        actual = (vigentes_np or {}).get(c["vendedor"].lower())
        nuevo_costo = f"{c['costo']:.4f}"
        if actual and actual.get("costo") == nuevo_costo and actual.get("moneda") == c["moneda"]:
            continue
        cursor.execute(
            """
            INSERT INTO material_costos
                (numero_parte, vendedor, costo_unitario_material, moneda,
                 usuario_registro, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (numero_parte, c["vendedor"], str(c["costo"]), c["moneda"], usuario, fecha),
        )


def _material_to_json(row, vigentes_np, aliases_np=None, aliases_global_np=None):
    vendedores = _split_vendedores(row.get("vendedor"))
    aliases = aliases_np or []
    aliases_globales = aliases_global_np or []
    return {
        "numero_parte": row.get("numero_parte") or "",
        "numeros_parte_original": aliases,
        "numeros_parte_original_text": ", ".join(aliases),
        "numeros_parte_original_global": aliases_globales,
        "numeros_parte_original_global_text": ", ".join(aliases_globales),
        "propiedad_material": row.get("propiedad_material") or "",
        "clasificacion": row.get("clasificacion") or "",
        "especificacion_material": row.get("especificacion_material") or "",
        "unidad_empaque": row.get("unidad_empaque") or "",
        "unidad_medida": row.get("unidad_medida") or "",
        "vendedor": row.get("vendedor") or "",
        "vendedores": vendedores,
        "costos": _costos_para_material(vigentes_np, vendedores),
        "fecha_registro": formatear_fecha_hora(row.get("fecha_registro")),
        "usuario_registro": row.get("usuario_registro") or "",
        "fecha_modificacion": formatear_fecha_hora(row.get("fecha_modificacion")),
        "usuario_modificacion": row.get("usuario_modificacion") or "",
    }


def _fetch_material(cursor, numero_parte):
    """Lee un material ACTIVO por numero_parte (soft-delete: activo=1)."""
    cursor.execute(
        """
        SELECT numero_parte, propiedad_material, clasificacion,
               especificacion_material, unidad_empaque, unidad_medida,
               vendedor, fecha_registro, usuario_registro,
               usuario_modificacion, fecha_modificacion
        FROM materiales
        WHERE numero_parte = %s AND activo = 1
        LIMIT 1
        """,
        (numero_parte,),
    )
    return cursor.fetchone()


def _payload_material():
    data = request.get_json(silent=True) or {}
    numero_parte = sanitizar_texto(data.get("numero_parte"), 512)
    numeros_originales = _parse_numeros_parte_original(
        data.get("numeros_parte_original", data.get("aliases_invoice"))
    )
    propiedad = sanitizar_texto(data.get("propiedad_material"), 512)
    clasificacion = sanitizar_texto(data.get("clasificacion"), 512)
    especificacion = sanitizar_texto(data.get("especificacion_material"), 512)
    unidad_empaque = sanitizar_texto(data.get("unidad_empaque"), 50)
    unidad_medida = sanitizar_texto(data.get("unidad_medida"), 10) or "EA"

    errors = []
    if not numero_parte:
        errors.append("El numero de parte es requerido.")
    if not especificacion:
        errors.append("La especificacion del material es requerida.")

    vendedor_str, costos, vend_errors = _parse_vendedores(data)
    errors.extend(vend_errors)

    payload = {
        "numero_parte": numero_parte,
        "numeros_parte_original": numeros_originales,
        "propiedad_material": propiedad,
        "clasificacion": clasificacion,
        "especificacion_material": especificacion,
        "unidad_empaque": unidad_empaque,
        "unidad_medida": unidad_medida,
        "vendedor": vendedor_str,
        "costos": costos,
    }
    return payload, errors


# ===================== Render del fragmento =====================

@bp.route("/informacion_basica/control_de_material")
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def control_material_ajax():
    """Render AJAX del modulo Control de material (Informacion Basica)."""
    return render_template("INFORMACION BASICA/CONTROL_DE_MATERIAL.html")


# ===================== Filtros y listado =====================

def _build_filters():
    q = sanitizar_texto(request.args.get("q"), 120)
    clasificacion = sanitizar_texto(request.args.get("clasificacion"), 255)
    # Soft-delete: el web solo lista materiales activos.
    where = ["activo = 1"]
    params = []
    if q:
        where.append(
            """
            (
                numero_parte LIKE %s OR
                especificacion_material LIKE %s OR
                propiedad_material LIKE %s OR
                clasificacion LIKE %s OR
                vendedor LIKE %s OR
                numero_parte IN (
                    SELECT numero_parte_sistema
                    FROM material_part_aliases
                    WHERE activo = 1
                      AND numero_parte_original LIKE %s
                )
            )
            """
        )
        like = f"%{q}%"
        params.extend([like, like, like, like, like, like])
    if clasificacion:
        where.append("clasificacion = %s")
        params.append(clasificacion)
    return " AND ".join(where), params


def _query_materiales(cursor):
    where_sql, params = _build_filters()
    cursor.execute(
        f"""
        SELECT numero_parte, propiedad_material, clasificacion,
               especificacion_material, unidad_empaque, unidad_medida,
               vendedor, fecha_registro, usuario_registro,
               usuario_modificacion, fecha_modificacion
        FROM materiales
        WHERE {where_sql}
        ORDER BY numero_parte ASC
        LIMIT 2000
        """,
        params,
    )
    rows = cursor.fetchall() or []
    numeros = [r["numero_parte"] for r in rows]
    vigentes = _costos_vigentes(cursor, numeros) if numeros else {}
    aliases, aliases_globales = _aliases_por_material(cursor, numeros) if numeros else ({}, {})
    return [
        _material_to_json(
            r,
            vigentes.get(r["numero_parte"]),
            aliases.get(r["numero_parte"]),
            aliases_globales.get(r["numero_parte"]),
        )
        for r in rows
    ]


@bp.route("/api/informacion_basica/control_material/materiales", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def list_materiales():
    """Listar materiales con filtros simples (q, clasificacion)."""
    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        rows = _query_materiales(cursor)
        return jsonify({"success": True, "records": rows, "total": len(rows)})
    except Exception as exc:
        logger.exception("Error listando materiales: %s", exc)
        return jsonify({"success": False, "error": ERROR_INTERNO, "records": []}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/informacion_basica/control_material/materiales/detalle", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def detalle_material():
    """Detalle de un material por numero_parte (query param: puede traer '/')."""
    numero_parte = sanitizar_texto(request.args.get("numero_parte"), 512)
    if not numero_parte:
        return jsonify({"success": False, "error": "numero_parte requerido"}), 400
    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        row = _fetch_material(cursor, numero_parte)
        if not row:
            return jsonify({"success": False, "error": "Material no encontrado"}), 404
        vigentes = _costos_vigentes(cursor, [numero_parte])
        aliases, aliases_globales = _aliases_por_material(cursor, [numero_parte])
        return jsonify(
            {
                "success": True,
                "record": _material_to_json(
                    row,
                    vigentes.get(numero_parte),
                    aliases.get(numero_parte),
                    aliases_globales.get(numero_parte),
                ),
            }
        )
    except Exception as exc:
        logger.exception("Error obteniendo material %s: %s", numero_parte, exc)
        return jsonify({"success": False, "error": ERROR_INTERNO}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/informacion_basica/control_material/costos/historial", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def historial_costos():
    """Historial completo de costos de un material (opcional: por vendedor)."""
    numero_parte = sanitizar_texto(request.args.get("numero_parte"), 512)
    vendedor = sanitizar_texto(request.args.get("vendedor"), 100)
    if not numero_parte:
        return jsonify({"success": False, "error": "numero_parte requerido"}), 400
    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        sql = """
            SELECT vendedor, costo_unitario_material, moneda,
                   usuario_registro, fecha_registro
            FROM material_costos
            WHERE numero_parte = %s
        """
        params = [numero_parte]
        if vendedor:
            sql += " AND vendedor = %s"
            params.append(vendedor)
        sql += " ORDER BY id DESC"
        cursor.execute(sql, params)
        records = [
            {
                "vendedor": r["vendedor"],
                "costo": _decimal_str(r["costo_unitario_material"]),
                "moneda": r["moneda"],
                "usuario_registro": r.get("usuario_registro") or "",
                "fecha_registro": formatear_fecha_hora(r.get("fecha_registro")),
            }
            for r in (cursor.fetchall() or [])
        ]
        return jsonify({"success": True, "records": records, "total": len(records)})
    except Exception as exc:
        logger.exception("Error en historial de costos %s: %s", numero_parte, exc)
        return jsonify({"success": False, "error": ERROR_INTERNO}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/informacion_basica/control_material/catalogos", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def catalogos():
    """Valores distinct para datalists del formulario + monedas."""
    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        def _distinct(columna):
            # Solo materiales activos: los dados de baja no deben aparecer en
            # los datalists/filtros (consistente con el listado).
            cursor.execute(
                f"""
                SELECT DISTINCT {columna} AS v FROM materiales
                WHERE activo = 1
                  AND {columna} IS NOT NULL AND {columna} <> ''
                ORDER BY {columna} ASC LIMIT 500
                """
            )
            return [r["v"] for r in (cursor.fetchall() or [])]

        return jsonify(
            {
                "success": True,
                "clasificaciones": _distinct("clasificacion"),
                "propiedades": _distinct("propiedad_material"),
                "unidades_empaque": _distinct("unidad_empaque"),
                "unidades_medida": _distinct("unidad_medida"),
                "monedas": sorted(MONEDAS_VALIDAS),
            }
        )
    except Exception as exc:
        logger.exception("Error obteniendo catalogos: %s", exc)
        return jsonify({"success": False, "error": ERROR_INTERNO}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/informacion_basica/control_material/numeros-originales/import", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def import_numeros_parte_original():
    """Carga masiva de equivalencias numero original -> numero sistema.

    Pertenece al modulo de Informacion Basica / Control de material porque
    estas equivalencias son catalogo maestro, no datos propios de una invoice.
    """
    filename, records, skipped_excel, conflicts, error = _leer_excel_numeros_originales(request.files)
    if error:
        return error

    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()
        tipo_default = sanitizar_texto(request.form.get("tipo") or request.form.get("proveedor"), 255)
        cursor.execute("START TRANSACTION")
        analysis = _analizar_numeros_parte_original(cursor, records, skipped_excel, tipo_default, conflicts)
        importados = 0
        for record in analysis["_importables_records"]:
            _upsert_numero_parte_original(
                cursor,
                record["numero_parte_original"],
                record["numero_parte_sistema"],
                record.get("tipo") or "",
                usuario,
                fecha,
            )
            importados += 1
        conn.commit()
        analysis.pop("_importables_records", None)
        analysis["success"] = True
        analysis["archivo"] = filename
        analysis["importados"] = importados
        return jsonify(analysis)
    except Exception as exc:
        conn.rollback()
        logger.exception("Error importando numeros originales: %s", exc)
        return jsonify({"success": False, "error": ERROR_INTERNO}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/informacion_basica/control_material/numeros-originales/preview", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def preview_numeros_parte_original():
    """Previsualiza la carga masiva sin escribir equivalencias."""
    filename, records, skipped_excel, conflicts, error = _leer_excel_numeros_originales(request.files)
    if error:
        return error

    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        tipo_default = sanitizar_texto(request.form.get("tipo") or request.form.get("proveedor"), 255)
        analysis = _analizar_numeros_parte_original(cursor, records, skipped_excel, tipo_default, conflicts)
        analysis.pop("_importables_records", None)
        analysis["success"] = True
        analysis["archivo"] = filename
        return jsonify(analysis)
    except Exception as exc:
        logger.exception("Error generando preview de numeros originales: %s", exc)
        return jsonify({"success": False, "error": ERROR_INTERNO}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/informacion_basica/control_material/export", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def export_materiales():
    """Exportar el listado filtrado a Excel (una fila por material+vendedor)."""
    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        materiales = _query_materiales(cursor)
        items = []
        for m in materiales:
            costos = m["costos"] or [None]
            for c in costos:
                items.append(
                    {
                        "numero_parte": m["numero_parte"],
                        "numero_parte_original": m["numeros_parte_original_text"],
                        "propiedad_material": m["propiedad_material"],
                        "clasificacion": m["clasificacion"],
                        "especificacion_material": m["especificacion_material"],
                        "unidad_empaque": m["unidad_empaque"],
                        "unidad_medida": m["unidad_medida"],
                        "vendedor": (c["vendedor"] if c else ""),
                        "costo": (c["costo"] if c and c["costo"] is not None else ""),
                        "moneda": (c["moneda"] if c else ""),
                        "fecha_registro": m["fecha_registro"],
                        "usuario_registro": m["usuario_registro"],
                    }
                )
        headers = [
            "Numero de parte", "Numero de parte original", "Propiedad", "Clasificacion", "Especificacion",
            "Unidad empaque", "Unidad medida", "Vendedor", "Costo", "Moneda",
            "Fecha registro", "Usuario",
        ]
        keys = [
            "numero_parte", "numero_parte_original", "propiedad_material", "clasificacion",
            "especificacion_material", "unidad_empaque", "unidad_medida",
            "vendedor", "costo", "moneda", "fecha_registro", "usuario_registro",
        ]
        widths = [22, 26, 20, 18, 34, 14, 12, 18, 12, 8, 18, 16]
        filename = f"control_material_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return excel_response(
            items, headers, keys, widths,
            sheet="Control de material", filename=filename,
        )
    except Exception as exc:
        logger.exception("Error exportando materiales: %s", exc)
        return jsonify({"success": False, "error": ERROR_INTERNO}), 500
    finally:
        cursor.close()
        conn.close()


# ===================== Alta / Edicion / Borrado =====================

@bp.route("/api/informacion_basica/control_material/materiales", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def create_material():
    """Crear un material (solo las 9 columnas del alcance) + costos."""
    payload, errors = _payload_material()
    if errors:
        return jsonify({"success": False, "error": " ".join(errors)}), 400

    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        # numero_parte es PK: puede existir ACTIVO (409) o soft-deleted
        # (activo=0 -> se reactiva con los datos nuevos en vez de fallar).
        cursor.execute(
            "SELECT activo FROM materiales WHERE numero_parte = %s LIMIT 1",
            (payload["numero_parte"],),
        )
        existente = cursor.fetchone()
        if existente and int(existente.get("activo") or 0) == 1:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Ya existe un material con numero de parte '{payload['numero_parte']}'.",
                        "field": "numero_parte",
                    }
                ),
                409,
            )

        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()
        if existente:
            # Reactivar un material soft-deleted: se reusa el registro y se
            # marca la reactivacion como modificacion (auditoria).
            cursor.execute(
                """
                UPDATE materiales
                SET propiedad_material = %s,
                    clasificacion = %s,
                    especificacion_material = %s,
                    unidad_empaque = %s,
                    unidad_medida = %s,
                    vendedor = %s,
                    activo = 1,
                    usuario_modificacion = %s,
                    fecha_modificacion = %s
                WHERE numero_parte = %s
                """,
                (
                    payload["propiedad_material"],
                    payload["clasificacion"],
                    payload["especificacion_material"],
                    payload["unidad_empaque"],
                    payload["unidad_medida"],
                    payload["vendedor"],
                    usuario,
                    fecha,
                    payload["numero_parte"],
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO materiales
                    (numero_parte, propiedad_material, clasificacion,
                     especificacion_material, unidad_empaque, unidad_medida,
                     vendedor, fecha_registro, usuario_registro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payload["numero_parte"],
                    payload["propiedad_material"],
                    payload["clasificacion"],
                    payload["especificacion_material"],
                    payload["unidad_empaque"],
                    payload["unidad_medida"],
                    payload["vendedor"],
                    fecha,
                    usuario,
                ),
            )
        _insertar_costos(cursor, payload["numero_parte"], payload["costos"], usuario, fecha)
        _sync_numeros_parte_original(cursor, payload["numero_parte"], payload["numeros_parte_original"], usuario, fecha)
        conn.commit()

        row = _fetch_material(cursor, payload["numero_parte"])
        vigentes = _costos_vigentes(cursor, [payload["numero_parte"]])
        aliases, aliases_globales = _aliases_por_material(cursor, [payload["numero_parte"]])
        return (
            jsonify(
                {
                    "success": True,
                    "record": _material_to_json(
                        row,
                        vigentes.get(payload["numero_parte"]),
                        aliases.get(payload["numero_parte"]),
                        aliases_globales.get(payload["numero_parte"]),
                    ),
                }
            ),
            201,
        )
    except Exception as exc:
        conn.rollback()
        logger.exception("Error creando material: %s", exc)
        return jsonify({"success": False, "error": ERROR_INTERNO}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/informacion_basica/control_material/materiales", methods=["PUT"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def update_material():
    """Actualizar un material existente. Solo toca las 6 columnas editables
    + vendedor; NO modifica fecha/usuario de registro ni columnas fuera de
    alcance (codigo_material, MSL, IQC, ubicaciones, etc.)."""
    payload, errors = _payload_material()
    if errors:
        return jsonify({"success": False, "error": " ".join(errors)}), 400

    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        if not _fetch_material(cursor, payload["numero_parte"]):
            return jsonify({"success": False, "error": "Material no encontrado"}), 404

        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()
        cursor.execute(
            """
            UPDATE materiales
            SET propiedad_material = %s,
                clasificacion = %s,
                especificacion_material = %s,
                unidad_empaque = %s,
                unidad_medida = %s,
                vendedor = %s,
                usuario_modificacion = %s,
                fecha_modificacion = %s
            WHERE numero_parte = %s
            """,
            (
                payload["propiedad_material"],
                payload["clasificacion"],
                payload["especificacion_material"],
                payload["unidad_empaque"],
                payload["unidad_medida"],
                payload["vendedor"],
                usuario,
                fecha,
                payload["numero_parte"],
            ),
        )

        vigentes = _costos_vigentes(cursor, [payload["numero_parte"]])
        _insertar_costos_si_cambiaron(
            cursor, payload["numero_parte"], payload["costos"],
            vigentes.get(payload["numero_parte"]), usuario, fecha,
        )
        _sync_numeros_parte_original(cursor, payload["numero_parte"], payload["numeros_parte_original"], usuario, fecha)
        conn.commit()

        row = _fetch_material(cursor, payload["numero_parte"])
        vigentes = _costos_vigentes(cursor, [payload["numero_parte"]])
        aliases, aliases_globales = _aliases_por_material(cursor, [payload["numero_parte"]])
        return jsonify(
            {
                "success": True,
                "record": _material_to_json(
                    row,
                    vigentes.get(payload["numero_parte"]),
                    aliases.get(payload["numero_parte"]),
                    aliases_globales.get(payload["numero_parte"]),
                ),
            }
        )
    except Exception as exc:
        conn.rollback()
        logger.exception("Error actualizando material: %s", exc)
        return jsonify({"success": False, "error": ERROR_INTERNO}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/informacion_basica/control_material/materiales", methods=["DELETE"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def delete_material():
    """Soft-delete: marca el material como inactivo (activo=0).

    NO borra fisicamente para no dejar huerfanos en inventario/BOM/salidas
    que referencian numero_parte. El historial de costos se conserva (el
    material puede reactivarse re-dandolo de alta con el mismo numero_parte).
    """
    data = request.get_json(silent=True) or {}
    numero_parte = sanitizar_texto(data.get("numero_parte"), 512)
    if not numero_parte:
        return jsonify({"success": False, "error": "numero_parte requerido"}), 400

    conn, error_response = conexion_o_error()
    if error_response:
        return error_response
    cursor = dict_cursor(conn)
    try:
        if not _fetch_material(cursor, numero_parte):
            return jsonify({"success": False, "error": "Material no encontrado"}), 404
        usuario = _usuario_actual()
        fecha = obtener_fecha_hora_mexico()
        cursor.execute(
            """
            UPDATE materiales
            SET activo = 0,
                usuario_modificacion = %s,
                fecha_modificacion = %s
            WHERE numero_parte = %s
            """,
            (usuario, fecha, numero_parte),
        )
        conn.commit()
        return jsonify({"success": True})
    except Exception as exc:
        conn.rollback()
        logger.exception("Error eliminando material %s: %s", numero_parte, exc)
        return jsonify({"success": False, "error": ERROR_INTERNO}), 500
    finally:
        cursor.close()
        conn.close()
