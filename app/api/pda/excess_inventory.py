"""QA Excess Inventory API for the mobile scanner app.

Rutas con url_prefix `/api/shipping/excess`:
  POST /api/shipping/excess/pieces
  GET  /api/shipping/excess/pieces
  GET  /api/shipping/excess/stats/today

La autenticacion se reutiliza desde `/api/shipping/auth/*`; estos endpoints
son publicos respecto a la sesion web del portal, igual que las apps PDA.
"""

import csv
import re
from collections import Counter
from pathlib import Path
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.api.pda.shipping import (
    MYSQL_AVAILABLE,
    MySQLdb,
    get_db_connection,
    manejo_errores,
)
from app.api.pda.shipping_material import (
    SHIPPING_TABLES,
    build_search_clause,
    get_dict_cursor,
    normalize_integer,
    normalize_part_number,
    normalize_search,
    serialize_row,
    to_sql_datetime,
)

import logging

logger = logging.getLogger(__name__)


EXCESS_TABLES = {
    "pieces": "qa_exceso_inventario_piezas",
    "movements": "qa_exceso_movimientos",
    "closures": "qa_exceso_inventario_cierres",
    "closure_batches": "qa_exceso_inventario_cierre_lotes",
}

bp = Blueprint("excess_inventory_api", __name__, url_prefix="/api/shipping/excess")


def normalize_scan_code(raw_value):
    return normalize_search(raw_value).upper()


def resolve_part_number_from_scan_code(raw_value, catalog_part_numbers):
    scan_code = normalize_scan_code(raw_value)
    if not scan_code:
        return ""

    normalized_catalog = [
        normalize_part_number(part_number)
        for part_number in catalog_part_numbers
        if normalize_part_number(part_number)
    ]
    for part_number in sorted(normalized_catalog, key=len, reverse=True):
        if scan_code.startswith(part_number):
            return part_number

    match = re.search(r"[A-Z]{2,5}\d{6,12}", scan_code)
    candidate = normalize_part_number(match.group(0)) if match else ""
    return candidate if candidate in set(normalized_catalog) else ""


def resolve_catalog_snapshot(cursor, part_number):
    cursor.execute(
        f"""
        SELECT
          c.id AS catalog_id,
          c.part_number,
          c.product_model,
          c.description,
          c.customer,
          c.zone_code,
          i.id AS shipping_inventory_id
        FROM `{SHIPPING_TABLES['catalog']}` c
        LEFT JOIN `{SHIPPING_TABLES['inventory']}` i
          ON i.catalog_id = c.id
        WHERE c.part_number = %s
        LIMIT 1
        """,
        (part_number,),
    )
    return cursor.fetchone()


def fetch_shipping_catalog_snapshots(cursor):
    cursor.execute(
        f"""
        SELECT
          c.id AS catalog_id,
          c.part_number,
          c.product_model,
          c.description,
          c.customer,
          c.zone_code,
          i.id AS shipping_inventory_id
        FROM `{SHIPPING_TABLES['catalog']}` c
        LEFT JOIN `{SHIPPING_TABLES['inventory']}` i
          ON i.catalog_id = c.id
        WHERE COALESCE(c.part_number, '') <> ''
        """
    )
    snapshots = {}
    for row in cursor.fetchall():
        part_number = normalize_part_number(row.get("part_number"))
        if part_number and part_number not in snapshots:
            snapshots[part_number] = row
    return snapshots


def parse_excess_baseline_csv(csv_path, catalog_part_numbers):
    path = Path(csv_path)
    rows = []
    errors = []
    duplicate_counts = Counter()

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [normalize_search(name).upper() for name in (reader.fieldnames or [])]
        if fieldnames != ["BARCODE"]:
            return [], [f"El CSV baseline debe contener exactamente la columna BARCODE: {path}"]

        for line_number, row in enumerate(reader, start=2):
            raw_scan_code = normalize_scan_code(row.get("BARCODE"))
            if not raw_scan_code:
                continue

            duplicate_counts[raw_scan_code] += 1
            scan_code = (
                raw_scan_code
                if duplicate_counts[raw_scan_code] == 1
                else f"{raw_scan_code}#BASELINE{duplicate_counts[raw_scan_code]:04d}"
            )

            part_number = resolve_part_number_from_scan_code(raw_scan_code, catalog_part_numbers)
            if not part_number:
                errors.append(
                    f"Linea {line_number}: no se pudo relacionar {raw_scan_code} con el catalogo de embarques."
                )
                continue
            rows.append(
                {
                    "scan_code": scan_code,
                    "raw_code": raw_scan_code,
                    "part_number": part_number,
                }
            )

    return rows, errors


def import_excess_baseline_csv(
    cursor,
    csv_path,
    scanned_at="2026-05-31 23:59:00",
    registered_by="Carga inicial",
    device_id="baseline-cierre-mayo",
):
    catalog_snapshots = fetch_shipping_catalog_snapshots(cursor)
    parsed_rows, errors = parse_excess_baseline_csv(csv_path, catalog_snapshots.keys())
    if errors:
        return {"success": False, "errors": errors, "inserted": 0, "skipped": 0}

    inserted = 0
    skipped = 0
    movement_inserted = 0
    by_part = Counter()

    for parsed in parsed_rows:
        scan_code = parsed["scan_code"]
        raw_code = parsed.get("raw_code") or scan_code
        part_number = parsed["part_number"]
        catalog = catalog_snapshots.get(part_number) or {}
        by_part[part_number] += 1

        cursor.execute(
            f"""
            SELECT id
            FROM `{EXCESS_TABLES['pieces']}`
            WHERE scan_code = %s
            LIMIT 1
            """,
            (scan_code,),
        )
        existing = cursor.fetchone()
        if existing:
            piece_id = existing.get("id")
            skipped += 1
        else:
            cursor.execute(
                f"""
                INSERT INTO `{EXCESS_TABLES['pieces']}` (
                  scan_code,
                  raw_code,
                  part_number,
                  quantity,
                  catalog_id,
                  shipping_inventory_id,
                  source_return_id,
                  product_model,
                  description,
                  customer,
                  zone_code,
                  status,
                  registered_by_user_id,
                  registered_by,
                  device_id,
                  notes,
                  scanned_at
                ) VALUES (%s, %s, %s, 1, %s, %s, NULL, %s, %s, %s, %s, 'active', NULL, %s, %s, %s, %s)
                """,
                (
                    scan_code,
                    raw_code,
                    part_number,
                    catalog.get("catalog_id"),
                    catalog.get("shipping_inventory_id"),
                    catalog.get("product_model"),
                    catalog.get("description"),
                    catalog.get("customer"),
                    catalog.get("zone_code"),
                    registered_by,
                    device_id,
                    f"Baseline importado desde {Path(csv_path).name}",
                    scanned_at,
                ),
            )
            piece_id = cursor.lastrowid
            inserted += 1

        cursor.execute(
            f"""
            SELECT id
            FROM `{EXCESS_TABLES['movements']}`
            WHERE piece_id = %s
              AND movement_type = 'entry'
            LIMIT 1
            """,
            (piece_id,),
        )
        if not cursor.fetchone():
            cursor.execute(
                f"""
                INSERT INTO `{EXCESS_TABLES['movements']}` (
                  piece_id,
                  scan_code,
                  movement_type,
                  part_number,
                  quantity,
                  registered_by_user_id,
                  registered_by,
                  device_id,
                  notes,
                  movement_at
                ) VALUES (%s, %s, 'entry', %s, 1, NULL, %s, %s, %s, %s)
                """,
                (
                    piece_id,
                    scan_code,
                    part_number,
                    registered_by,
                    device_id,
                    f"Baseline importado desde {Path(csv_path).name}",
                    scanned_at,
                ),
            )
            movement_inserted += 1

    return {
        "success": True,
        "source": str(csv_path),
        "total": len(parsed_rows),
        "inserted": inserted,
        "skipped": skipped,
        "movementInserted": movement_inserted,
        "byPart": dict(sorted(by_part.items())),
    }


def resolve_latest_excess_return(cursor, part_number):
    cursor.execute(
        f"""
        SELECT id, return_folio
        FROM `{SHIPPING_TABLES['returns']}`
        WHERE part_number = %s
          AND COALESCE(reason, '') LIKE %s
        ORDER BY movement_at DESC, id DESC
        LIMIT 1
        """,
        (part_number, "%Exceso%"),
    )
    return cursor.fetchone()


def resolve_registered_by_user_id(cursor, registered_by_id, *identity_values):
    if registered_by_id:
        cursor.execute(
            """
            SELECT id
            FROM usuarios_sistema
            WHERE id = %s
              AND activo = 1
            LIMIT 1
            """,
            (registered_by_id,),
        )
        row = cursor.fetchone()
        if row:
            return row.get("id")

    identities = [
        normalize_search(value)
        for value in identity_values
        if normalize_search(value)
    ]
    if not identities:
        return None

    placeholders = ", ".join(["%s"] * len(identities))
    cursor.execute(
        f"""
        SELECT id
        FROM usuarios_sistema
        WHERE activo = 1
          AND (
            username IN ({placeholders})
            OR nombre_completo IN ({placeholders})
          )
        ORDER BY id ASC
        LIMIT 1
        """,
        tuple(identities + identities),
    )
    row = cursor.fetchone()
    return row.get("id") if row else None


@bp.route("/pieces", methods=["POST"])
@manejo_errores
def create_excess_piece():
    data = request.get_json(silent=True) or {}
    scan_code = normalize_scan_code(
        data.get("scanCode")
        or data.get("pieceCode")
        or data.get("rawCode")
        or data.get("referenceCode")
    )
    raw_code = normalize_search(data.get("rawCode") or scan_code)
    part_number = normalize_part_number(
        data.get("partNumber")
        or data.get("part_number")
        or data.get("warehousingCode")
    )
    quantity = normalize_integer(data.get("quantity")) or 1
    registered_by = normalize_search(data.get("registeredBy")) or "Usuario local"
    registered_by_id = normalize_integer(
        data.get("registeredById")
        or data.get("registered_by_user_id")
        or data.get("userId")
    )
    registered_by_username = normalize_search(
        data.get("registeredByUsername")
        or data.get("username")
        or data.get("userName")
    )
    device_id = normalize_search(data.get("deviceId")) or None
    notes = normalize_search(data.get("notes")) or None
    scanned_at = to_sql_datetime(data.get("scannedAt"))

    if not scan_code:
        return jsonify({"success": False, "error": "Se requiere codigo escaneado"}), 400

    if not part_number:
        return jsonify({"success": False, "error": "Se requiere numero de parte"}), 400

    if quantity != 1:
        return jsonify(
            {
                "success": False,
                "error": "El inventario de exceso QA se registra pieza por pieza",
            }
        ), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        conn.autocommit(False)
        cursor = get_dict_cursor(conn)

        cursor.execute(
            f"""
            SELECT id, status, part_number, scanned_at, registered_by
            FROM `{EXCESS_TABLES['pieces']}`
            WHERE scan_code = %s
            LIMIT 1
            """,
            (scan_code,),
        )
        existing = cursor.fetchone()
        if existing:
            conn.rollback()
            return jsonify(
                {
                    "success": False,
                    "error": "La pieza ya fue registrada en inventario de exceso",
                    "piece": serialize_row(existing),
                }
            ), 409

        catalog = resolve_catalog_snapshot(cursor, part_number)
        if not catalog:
            conn.rollback()
            return jsonify(
                {
                    "success": False,
                    "error": "El numero de parte no existe en el catalogo de embarques",
                }
            ), 404

        related_return = resolve_latest_excess_return(cursor, part_number)
        registered_by_id = resolve_registered_by_user_id(
            cursor,
            registered_by_id,
            registered_by_username,
            registered_by,
        )

        cursor.execute(
            f"""
            INSERT INTO `{EXCESS_TABLES['pieces']}` (
              scan_code,
              raw_code,
              part_number,
              quantity,
              catalog_id,
              shipping_inventory_id,
              source_return_id,
              product_model,
              description,
              customer,
              zone_code,
              status,
              registered_by_user_id,
              registered_by,
              device_id,
              notes,
              scanned_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s, %s)
            """,
            (
                scan_code,
                raw_code,
                part_number,
                1,
                catalog.get("catalog_id"),
                catalog.get("shipping_inventory_id"),
                (related_return or {}).get("id"),
                catalog.get("product_model"),
                catalog.get("description"),
                catalog.get("customer"),
                catalog.get("zone_code"),
                registered_by_id,
                registered_by,
                device_id,
                notes,
                scanned_at,
            ),
        )
        piece_id = cursor.lastrowid

        cursor.execute(
            f"""
            INSERT INTO `{EXCESS_TABLES['movements']}` (
              piece_id,
              scan_code,
              movement_type,
              part_number,
              quantity,
              registered_by_user_id,
              registered_by,
              device_id,
              notes,
              movement_at
            ) VALUES (%s, %s, 'entry', %s, 1, %s, %s, %s, %s, %s)
            """,
            (
                piece_id,
                scan_code,
                part_number,
                registered_by_id,
                registered_by,
                device_id,
                notes,
                scanned_at,
            ),
        )

        conn.commit()
        return jsonify(
            {
                "success": True,
                "id": piece_id,
                "scanCode": scan_code,
                "partNumber": part_number,
                "quantity": 1,
                "sourceReturnId": (related_return or {}).get("id"),
                "sourceReturnFolio": (related_return or {}).get("return_folio"),
                "message": "Pieza registrada en inventario de exceso",
            }
        ), 201
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route("/pieces", methods=["GET"])
@manejo_errores
def list_excess_pieces():
    limit = normalize_integer(request.args.get("limit")) or 100
    limit = min(max(limit, 1), 500)
    search = request.args.get("q") or request.args.get("search")
    part_number = normalize_part_number(request.args.get("partNumber"))
    status = normalize_search(request.args.get("status"))
    from_date = normalize_search(request.args.get("fromDate"))
    to_date = normalize_search(request.args.get("toDate"))

    search_clause, search_params = build_search_clause(
        search,
        [
            "p.scan_code",
            "p.raw_code",
            "p.part_number",
            "p.product_model",
            "p.description",
            "p.customer",
            "p.registered_by",
            "p.notes",
        ],
    )

    where = ["1 = 1"]
    params = []
    if part_number:
        where.append("p.part_number = %s")
        params.append(part_number)
    if status:
        where.append("p.status = %s")
        params.append(status)
    if from_date:
        where.append("DATE(p.scanned_at) >= %s")
        params.append(from_date)
    if to_date:
        where.append("DATE(p.scanned_at) <= %s")
        params.append(to_date)

    conn = get_db_connection()
    cursor = get_dict_cursor(conn)

    try:
        cursor.execute(
            f"""
            SELECT
              p.id,
              p.scan_code,
              p.raw_code,
              p.part_number,
              p.quantity,
              p.product_model,
              p.description,
              p.customer,
              p.zone_code,
              p.status,
              p.registered_by,
              p.device_id,
              p.notes,
              p.scanned_at,
              p.created_at,
              r.return_folio AS source_return_folio
            FROM `{EXCESS_TABLES['pieces']}` p
            LEFT JOIN `{SHIPPING_TABLES['returns']}` r
              ON r.id = p.source_return_id
            WHERE {' AND '.join(where)}
            {search_clause}
            ORDER BY p.scanned_at DESC, p.id DESC
            LIMIT %s
            """,
            tuple(params + search_params + [limit]),
        )
        rows = [serialize_row(row) for row in cursor.fetchall()]
        return jsonify({"success": True, "pieces": rows, "total": len(rows)})
    finally:
        cursor.close()
        conn.close()


@bp.route("/stats/today", methods=["GET"])
@manejo_errores
def get_today_excess_stats():
    date_param = normalize_search(request.args.get("date"))
    try:
        target_date = (
            datetime.strptime(date_param, "%Y-%m-%d").date()
            if date_param
            else datetime.now().date()
        )
    except ValueError:
        target_date = datetime.now().date()

    conn = get_db_connection()
    cursor = get_dict_cursor(conn)

    try:
        cursor.execute(
            f"""
            SELECT
              COUNT(*) AS total,
              COALESCE(SUM(quantity), 0) AS quantity
            FROM `{EXCESS_TABLES['pieces']}`
            WHERE DATE(scanned_at) = %s
              AND status = 'active'
            """,
            (target_date,),
        )
        today = cursor.fetchone() or {}

        cursor.execute(
            f"""
            SELECT
              COUNT(*) AS inventory_items,
              COALESCE(SUM(quantity), 0) AS inventory_quantity
            FROM `{EXCESS_TABLES['pieces']}`
            WHERE status = 'active'
            """
        )
        inventory = cursor.fetchone() or {}

        return jsonify(
            {
                "success": True,
                "date": target_date.strftime("%Y-%m-%d"),
                "total": int(today.get("total") or 0),
                "quantity": int(today.get("quantity") or 0),
                "inventoryItems": int(inventory.get("inventory_items") or 0),
                "inventoryQuantity": int(inventory.get("inventory_quantity") or 0),
            }
        )
    finally:
        cursor.close()
        conn.close()


def init_excess_inventory_tables():
    if not MYSQL_AVAILABLE:
        logger.warning("MySQL no disponible, no se pueden crear tablas de exceso QA")
        return False

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{EXCESS_TABLES['pieces']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              scan_code VARCHAR(160) NOT NULL,
              raw_code TEXT NULL,
              part_number VARCHAR(64) NOT NULL,
              quantity INT NOT NULL DEFAULT 1,
              catalog_id BIGINT UNSIGNED NULL,
              shipping_inventory_id BIGINT UNSIGNED NULL,
              source_return_id BIGINT UNSIGNED NULL,
              product_model VARCHAR(180) NULL,
              description VARCHAR(255) NULL,
              customer VARCHAR(120) NULL,
              zone_code VARCHAR(60) NULL,
              status ENUM('active', 'cancelled') NOT NULL DEFAULT 'active',
              registered_by_user_id INT NULL,
              registered_by VARCHAR(120) NULL,
              device_id VARCHAR(80) NULL,
              notes TEXT NULL,
              scanned_at DATETIME NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_excess_piece_scan_code (scan_code),
              KEY idx_excess_piece_part_number (part_number),
              KEY idx_excess_piece_status (status),
              KEY idx_excess_piece_scanned_at (scanned_at),
              KEY idx_excess_piece_registered_by (registered_by_user_id),
              KEY idx_excess_piece_source_return (source_return_id),
              CONSTRAINT fk_excess_piece_catalog
                FOREIGN KEY (catalog_id) REFERENCES `{SHIPPING_TABLES['catalog']}` (id)
                ON UPDATE CASCADE
                ON DELETE SET NULL,
              CONSTRAINT fk_excess_piece_shipping_inventory
                FOREIGN KEY (shipping_inventory_id) REFERENCES `{SHIPPING_TABLES['inventory']}` (id)
                ON UPDATE CASCADE
                ON DELETE SET NULL,
              CONSTRAINT fk_excess_piece_source_return
                FOREIGN KEY (source_return_id) REFERENCES `{SHIPPING_TABLES['returns']}` (id)
                ON UPDATE CASCADE
                ON DELETE SET NULL,
              CONSTRAINT fk_excess_piece_user
                FOREIGN KEY (registered_by_user_id) REFERENCES usuarios_sistema (id)
                ON UPDATE CASCADE
                ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{EXCESS_TABLES['movements']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              piece_id BIGINT UNSIGNED NOT NULL,
              scan_code VARCHAR(160) NOT NULL,
              movement_type ENUM('entry', 'cancel') NOT NULL DEFAULT 'entry',
              part_number VARCHAR(64) NOT NULL,
              quantity INT NOT NULL DEFAULT 1,
              registered_by_user_id INT NULL,
              registered_by VARCHAR(120) NULL,
              device_id VARCHAR(80) NULL,
              notes TEXT NULL,
              movement_at DATETIME NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              KEY idx_excess_mov_piece (piece_id),
              KEY idx_excess_mov_scan_code (scan_code),
              KEY idx_excess_mov_part_number (part_number),
              KEY idx_excess_mov_movement_at (movement_at),
              CONSTRAINT fk_excess_mov_piece
                FOREIGN KEY (piece_id) REFERENCES `{EXCESS_TABLES['pieces']}` (id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
              CONSTRAINT fk_excess_mov_user
                FOREIGN KEY (registered_by_user_id) REFERENCES usuarios_sistema (id)
                ON UPDATE CASCADE
                ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{EXCESS_TABLES['closure_batches']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              closure_label VARCHAR(120) NOT NULL,
              closure_month CHAR(7) NOT NULL,
              closed_at DATETIME NULL,
              created_by VARCHAR(120) NULL,
              confirmed_by VARCHAR(120) NULL,
              status ENUM('pending', 'confirmed', 'cancelled') NOT NULL DEFAULT 'pending',
              source_filename VARCHAR(255) NULL,
              file_hash VARCHAR(64) NULL,
              rows_hash VARCHAR(64) NULL,
              payload_json LONGTEXT NULL,
              summary_json LONGTEXT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              confirmed_at DATETIME NULL,
              PRIMARY KEY (id),
              KEY idx_excess_closure_batch_status (status),
              KEY idx_excess_closure_batch_month (closure_month),
              KEY idx_excess_closure_batch_closed_at (closed_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{EXCESS_TABLES['closures']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              closure_batch_id BIGINT UNSIGNED NULL,
              closure_label VARCHAR(120) NULL,
              part_number VARCHAR(64) NOT NULL,
              product_model VARCHAR(180) NULL,
              customer VARCHAR(120) NULL,
              system_quantity INT NOT NULL DEFAULT 0,
              physical_quantity INT NOT NULL DEFAULT 0,
              difference_quantity INT NOT NULL DEFAULT 0,
              initial_quantity INT NOT NULL DEFAULT 0,
              closed_at DATETIME NOT NULL,
              closed_by VARCHAR(120) NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              KEY idx_excess_closure_part_closed_at (part_number, closed_at),
              KEY idx_excess_closure_batch (closure_batch_id),
              CONSTRAINT fk_excess_closure_batch
                FOREIGN KEY (closure_batch_id) REFERENCES `{EXCESS_TABLES['closure_batches']}` (id)
                ON UPDATE CASCADE
                ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        conn.commit()
        logger.info("Tablas de inventario de exceso QA creadas/verificadas")
        return True
    except Exception as exc:
        logger.error(f"Error creando tablas de exceso QA: {exc}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
