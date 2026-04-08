import json
import os
import random
import re
from datetime import datetime

import pandas as pd
from flask import Blueprint, jsonify, request

from .shipping_api import (
    MYSQL_AVAILABLE,
    MySQLdb,
    get_db_connection,
    manejo_errores,
)


SHIPPING_TABLES = {
    "catalog": "embarques_catalogo_partes",
    "inventory": "embarques_inventario_actual",
    "entries": "embarques_entrada_material",
    "exits": "embarques_salida_material",
    "returns": "embarques_retorno_material",
}

shipping_material_api = Blueprint(
    "shipping_material_api",
    __name__,
    url_prefix="/api/shipping/material",
)


def normalize_search(raw_value):
    return str(raw_value or "").strip()


def normalize_part_number(raw_value):
    return normalize_search(raw_value).upper()


def normalize_header(value):
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return normalized.strip("_")


def normalize_integer(raw_value):
    if raw_value is None:
        return None

    if isinstance(raw_value, bool):
        return int(raw_value)

    if isinstance(raw_value, int):
        return raw_value

    if isinstance(raw_value, float):
        return int(raw_value)

    parsed = re.sub(r"[,\s]", "", str(raw_value).strip())
    if not parsed:
        return None

    try:
        return int(float(parsed))
    except ValueError:
        return None


def to_sql_datetime(raw_value=None):
    if raw_value:
        if isinstance(raw_value, datetime):
            return raw_value.replace(microsecond=0)

        normalized = str(raw_value).strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).replace(
                tzinfo=None,
                microsecond=0,
            )
        except ValueError:
            pass

    return datetime.now().replace(microsecond=0)


def serialize_datetime(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


def serialize_row(row):
    serialized = {}
    for key, value in row.items():
        serialized[key] = serialize_datetime(value)
    return serialized


def generate_movement_folio(prefix):
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    random_part = random.randint(100, 999)
    return f"{prefix}-{timestamp}-{random_part}"


def build_search_clause(search, columns):
    search_text = normalize_search(search)
    if not search_text:
        return "", []

    wildcard = f"%{search_text}%"
    clause = " OR ".join(
        [f"COALESCE(CAST({column} AS CHAR), '') LIKE %s" for column in columns]
    )
    return f" AND ({clause})", [wildcard] * len(columns)


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cursor.fetchone() is not None


def ensure_column(cursor, table_name, column_name, definition):
    if column_exists(cursor, table_name, column_name):
        return

    cursor.execute(
        f"""
        ALTER TABLE `{table_name}`
        ADD COLUMN `{column_name}` {definition}
        """
    )


def remove_deprecated_location_defaults(cursor):
    if column_exists(cursor, SHIPPING_TABLES["catalog"], "default_location"):
        cursor.execute(
            f"ALTER TABLE `{SHIPPING_TABLES['catalog']}` DROP COLUMN `default_location`"
        )

    if column_exists(cursor, SHIPPING_TABLES["inventory"], "location_code"):
        cursor.execute(
            f"ALTER TABLE `{SHIPPING_TABLES['inventory']}` DROP COLUMN `location_code`"
        )

    ensure_column(
        cursor,
        SHIPPING_TABLES["entries"],
        "available_quantity",
        "INT NOT NULL DEFAULT 0 AFTER `quantity`",
    )
    ensure_column(
        cursor,
        SHIPPING_TABLES["entries"],
        "is_fifo_layer_only",
        "TINYINT(1) NOT NULL DEFAULT 0 AFTER `available_quantity`",
    )
    ensure_column(
        cursor,
        SHIPPING_TABLES["exits"],
        "fifo_allocation_json",
        "LONGTEXT NULL AFTER `location_code`",
    )

    cursor.execute(
        f"""
        UPDATE `{SHIPPING_TABLES['entries']}`
        SET available_quantity = quantity
        WHERE available_quantity IS NULL
           OR (available_quantity = 0 AND quantity > 0)
        """
    )


def init_shipping_material_tables():
    if not MYSQL_AVAILABLE:
        print("MySQL no disponible, no se pueden crear tablas compartidas de embarques")
        return False

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{SHIPPING_TABLES['catalog']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              part_number VARCHAR(64) NOT NULL,
              product_model VARCHAR(180) NULL,
              product_status VARCHAR(40) NOT NULL DEFAULT 'activo',
              description VARCHAR(255) NULL,
              standard_pack INT UNSIGNED NOT NULL DEFAULT 1,
              customer VARCHAR(120) NULL,
              zone_code VARCHAR(60) NULL,
              source_file VARCHAR(255) NULL,
              source_row INT UNSIGNED NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_catalog_part_number (part_number),
              KEY idx_catalog_model (product_model),
              KEY idx_catalog_customer (customer),
              KEY idx_catalog_status (product_status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{SHIPPING_TABLES['inventory']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              catalog_id BIGINT UNSIGNED NOT NULL,
              part_number VARCHAR(64) NOT NULL,
              product_model VARCHAR(180) NULL,
              product_status VARCHAR(40) NOT NULL DEFAULT 'activo',
              description VARCHAR(255) NULL,
              customer VARCHAR(120) NULL,
              zone_code VARCHAR(60) NULL,
              standard_pack INT UNSIGNED NOT NULL DEFAULT 1,
              current_quantity INT NOT NULL DEFAULT 0,
              last_entry_at DATETIME NULL,
              last_exit_at DATETIME NULL,
              last_return_at DATETIME NULL,
              catalog_loaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_inventory_catalog_id (catalog_id),
              UNIQUE KEY uq_inventory_part_number (part_number),
              KEY idx_inventory_customer (customer),
              KEY idx_inventory_model (product_model),
              KEY idx_inventory_status (product_status),
              CONSTRAINT fk_inventory_catalog
                FOREIGN KEY (catalog_id) REFERENCES `{SHIPPING_TABLES['catalog']}` (id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{SHIPPING_TABLES['entries']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              entry_folio VARCHAR(40) NOT NULL,
              inventory_id BIGINT UNSIGNED NOT NULL,
              catalog_id BIGINT UNSIGNED NOT NULL,
              part_number VARCHAR(64) NOT NULL,
              quantity INT NOT NULL,
              available_quantity INT NOT NULL DEFAULT 0,
              is_fifo_layer_only TINYINT(1) NOT NULL DEFAULT 0,
              previous_quantity INT NOT NULL DEFAULT 0,
              new_quantity INT NOT NULL DEFAULT 0,
              product_model VARCHAR(180) NULL,
              description VARCHAR(255) NULL,
              customer VARCHAR(120) NULL,
              zone_code VARCHAR(60) NULL,
              location_code VARCHAR(60) NULL,
              reference_code VARCHAR(80) NULL,
              batch_no VARCHAR(80) NULL,
              notes TEXT NULL,
              registered_by VARCHAR(120) NULL,
              movement_at DATETIME NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_entries_folio (entry_folio),
              KEY idx_entries_part_number (part_number),
              KEY idx_entries_movement_at (movement_at),
              CONSTRAINT fk_entries_inventory
                FOREIGN KEY (inventory_id) REFERENCES `{SHIPPING_TABLES['inventory']}` (id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
              CONSTRAINT fk_entries_catalog
                FOREIGN KEY (catalog_id) REFERENCES `{SHIPPING_TABLES['catalog']}` (id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{SHIPPING_TABLES['exits']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              exit_folio VARCHAR(40) NOT NULL,
              inventory_id BIGINT UNSIGNED NOT NULL,
              catalog_id BIGINT UNSIGNED NOT NULL,
              part_number VARCHAR(64) NOT NULL,
              quantity INT NOT NULL,
              previous_quantity INT NOT NULL DEFAULT 0,
              new_quantity INT NOT NULL DEFAULT 0,
              product_model VARCHAR(180) NULL,
              description VARCHAR(255) NULL,
              customer VARCHAR(120) NULL,
              zone_code VARCHAR(60) NULL,
              location_code VARCHAR(60) NULL,
              fifo_allocation_json LONGTEXT NULL,
              destination_area VARCHAR(120) NULL,
              reason VARCHAR(120) NULL,
              requested_by VARCHAR(120) NULL,
              remarks TEXT NULL,
              registered_by VARCHAR(120) NULL,
              movement_at DATETIME NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_exits_folio (exit_folio),
              KEY idx_exits_part_number (part_number),
              KEY idx_exits_movement_at (movement_at),
              CONSTRAINT fk_exits_inventory
                FOREIGN KEY (inventory_id) REFERENCES `{SHIPPING_TABLES['inventory']}` (id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
              CONSTRAINT fk_exits_catalog
                FOREIGN KEY (catalog_id) REFERENCES `{SHIPPING_TABLES['catalog']}` (id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{SHIPPING_TABLES['returns']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              return_folio VARCHAR(40) NOT NULL,
              inventory_id BIGINT UNSIGNED NOT NULL,
              catalog_id BIGINT UNSIGNED NOT NULL,
              part_number VARCHAR(64) NOT NULL,
              return_quantity INT NOT NULL,
              loss_quantity INT NOT NULL DEFAULT 0,
              previous_quantity INT NOT NULL DEFAULT 0,
              new_quantity INT NOT NULL DEFAULT 0,
              product_model VARCHAR(180) NULL,
              description VARCHAR(255) NULL,
              customer VARCHAR(120) NULL,
              zone_code VARCHAR(60) NULL,
              location_code VARCHAR(60) NULL,
              reason VARCHAR(120) NULL,
              remarks TEXT NULL,
              registered_by VARCHAR(120) NULL,
              movement_at DATETIME NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_returns_folio (return_folio),
              KEY idx_returns_part_number (part_number),
              KEY idx_returns_movement_at (movement_at),
              CONSTRAINT fk_returns_inventory
                FOREIGN KEY (inventory_id) REFERENCES `{SHIPPING_TABLES['inventory']}` (id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
              CONSTRAINT fk_returns_catalog
                FOREIGN KEY (catalog_id) REFERENCES `{SHIPPING_TABLES['catalog']}` (id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        remove_deprecated_location_defaults(cursor)
        conn.commit()
        print("Tablas compartidas de embarques creadas/verificadas correctamente")
        return True
    except Exception as exc:
        if conn:
            conn.rollback()
        print(f"Error creando tablas compartidas de embarques: {exc}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def ensure_inventory_record(cursor, part_number):
    normalized_part_number = normalize_part_number(part_number)
    if not normalized_part_number:
        return None

    cursor.execute(
        f"""
        SELECT
          i.*,
          c.id AS catalog_ref_id,
          c.product_model AS catalog_model,
          c.product_status AS catalog_status,
          c.description AS catalog_description,
          c.standard_pack AS catalog_standard_pack,
          c.customer AS catalog_customer,
          c.zone_code AS catalog_zone_code
        FROM `{SHIPPING_TABLES['inventory']}` i
        INNER JOIN `{SHIPPING_TABLES['catalog']}` c
          ON c.id = i.catalog_id
        WHERE i.part_number = %s
        LIMIT 1
        """,
        (normalized_part_number,),
    )
    inventory = cursor.fetchone()
    if inventory:
        return inventory

    cursor.execute(
        f"""
        SELECT *
        FROM `{SHIPPING_TABLES['catalog']}`
        WHERE part_number = %s
        LIMIT 1
        """,
        (normalized_part_number,),
    )
    catalog = cursor.fetchone()
    if not catalog:
        return None

    cursor.execute(
        f"""
        INSERT INTO `{SHIPPING_TABLES['inventory']}` (
          catalog_id,
          part_number,
          product_model,
          product_status,
          description,
          customer,
          zone_code,
          standard_pack,
          current_quantity,
          catalog_loaded_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, NOW())
        """,
        (
            catalog["id"],
            catalog["part_number"],
            catalog.get("product_model"),
            catalog.get("product_status") or "activo",
            catalog.get("description"),
            catalog.get("customer"),
            catalog.get("zone_code"),
            normalize_integer(catalog.get("standard_pack")) or 1,
        ),
    )

    cursor.execute(
        f"""
        SELECT
          i.*,
          c.id AS catalog_ref_id,
          c.product_model AS catalog_model,
          c.product_status AS catalog_status,
          c.description AS catalog_description,
          c.standard_pack AS catalog_standard_pack,
          c.customer AS catalog_customer,
          c.zone_code AS catalog_zone_code
        FROM `{SHIPPING_TABLES['inventory']}` i
        INNER JOIN `{SHIPPING_TABLES['catalog']}` c
          ON c.id = i.catalog_id
        WHERE i.part_number = %s
        LIMIT 1
        """,
        (normalized_part_number,),
    )
    return cursor.fetchone()


def update_inventory_snapshot(cursor, inventory_id, patch):
    assignments = []
    params = []

    for column, value in patch.items():
        if value is None:
            continue
        assignments.append(f"`{column}` = %s")
        params.append(value)

    if not assignments:
        return

    params.append(inventory_id)
    cursor.execute(
        f"""
        UPDATE `{SHIPPING_TABLES['inventory']}`
        SET {", ".join(assignments)}
        WHERE id = %s
        """,
        tuple(params),
    )


def load_fifo_layers(cursor, part_number):
    cursor.execute(
        f"""
        SELECT
          id,
          entry_folio,
          available_quantity,
          movement_at,
          zone_code,
          location_code
        FROM `{SHIPPING_TABLES['entries']}`
        WHERE part_number = %s
          AND available_quantity > 0
        ORDER BY movement_at ASC, id ASC
        FOR UPDATE
        """,
        (part_number,),
    )
    return cursor.fetchall()


def build_fifo_allocations(layers, requested_quantity):
    remaining = requested_quantity
    allocations = []

    for layer in layers:
        if remaining <= 0:
            break

        available_quantity = normalize_integer(layer.get("available_quantity")) or 0
        if available_quantity <= 0:
            continue

        consumed_quantity = min(available_quantity, remaining)
        allocations.append(
            {
                "entryId": layer["id"],
                "entryFolio": layer.get("entry_folio"),
                "consumedQuantity": consumed_quantity,
                "previousAvailable": available_quantity,
                "nextAvailable": available_quantity - consumed_quantity,
                "zoneCode": layer.get("zone_code"),
                "locationCode": layer.get("location_code"),
                "movementAt": serialize_datetime(layer.get("movement_at")),
            }
        )
        remaining -= consumed_quantity

    total_available = sum(
        normalize_integer(layer.get("available_quantity")) or 0 for layer in layers
    )

    return {
        "allocations": allocations,
        "remaining": remaining,
        "totalAvailable": total_available,
    }


def resolve_available_layer_quantity(previous_quantity, incoming_quantity):
    previous = normalize_integer(previous_quantity) or 0
    incoming = normalize_integer(incoming_quantity) or 0

    if incoming <= 0:
        return 0

    if previous >= 0:
        return incoming

    return max(previous + incoming, 0)


def apply_fifo_allocations(cursor, allocations):
    for allocation in allocations:
        cursor.execute(
            f"""
            UPDATE `{SHIPPING_TABLES['entries']}`
            SET available_quantity = %s
            WHERE id = %s
            """,
            (
                allocation["nextAvailable"],
                allocation["entryId"],
            ),
        )


def create_hidden_return_layer(cursor, inventory, return_folio, payload):
    net_quantity = normalize_integer(payload.get("netQuantity")) or 0
    available_quantity = normalize_integer(payload.get("availableQuantity")) or 0

    if net_quantity <= 0 or available_quantity <= 0:
        return

    layer_folio = generate_movement_folio("EMB-LYR")
    cursor.execute(
        f"""
        INSERT INTO `{SHIPPING_TABLES['entries']}` (
          entry_folio,
          inventory_id,
          catalog_id,
          part_number,
          quantity,
          available_quantity,
          is_fifo_layer_only,
          previous_quantity,
          new_quantity,
          product_model,
          description,
          customer,
          zone_code,
          location_code,
          reference_code,
          batch_no,
          notes,
          registered_by,
          movement_at
        ) VALUES (%s, %s, %s, %s, %s, %s, 1, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            layer_folio,
            inventory["id"],
            inventory.get("catalog_id") or inventory.get("catalog_ref_id"),
            inventory["part_number"],
            available_quantity,
            available_quantity,
            available_quantity,
            inventory.get("product_model") or inventory.get("catalog_model"),
            inventory.get("description") or inventory.get("catalog_description"),
            inventory.get("customer") or inventory.get("catalog_customer"),
            normalize_search(payload.get("zoneCode"))
            or inventory.get("zone_code")
            or inventory.get("catalog_zone_code"),
            normalize_search(payload.get("locationCode")) or None,
            f"RETORNO:{return_folio}",
            None,
            normalize_search(payload.get("notes")) or "Capa FIFO generada por retorno",
            normalize_search(payload.get("registeredBy")) or "Usuario local",
            payload.get("movementAt"),
        ),
    )


def merge_catalog_record(base_record, next_record):
    return {
        **base_record,
        "productModel": base_record.get("productModel") or next_record.get("productModel"),
        "productStatus": base_record.get("productStatus") or next_record.get("productStatus"),
        "description": base_record.get("description") or next_record.get("description"),
        "standardPack": base_record.get("standardPack") or next_record.get("standardPack"),
        "customer": base_record.get("customer") or next_record.get("customer"),
        "zoneCode": base_record.get("zoneCode") or next_record.get("zoneCode"),
    }


def resolve_catalog_source_path(source_path=None):
    if source_path:
        return source_path if os.path.isabs(source_path) else os.path.abspath(source_path)

    env_source_path = os.getenv("SHIPPING_CATALOG_PATH")
    if env_source_path:
        return (
            env_source_path
            if os.path.isabs(env_source_path)
            else os.path.abspath(env_source_path)
        )

    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "raw_shipping.xlsx")
    )


def parse_standard_pack(raw_value):
    parsed = normalize_integer(raw_value)
    if parsed is None or parsed <= 0:
        return 1
    return parsed


def pick_column(row, candidates):
    for candidate in candidates:
        value = row.get(candidate)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def parse_catalog_rows(source_path):
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"No se encontro el archivo de catalogo: {source_path}")

    dataframe = pd.read_excel(source_path, dtype=str).fillna("")
    if dataframe.empty:
        raise ValueError("El archivo Excel no contiene registros para importar")

    normalized_headers = [normalize_header(column) for column in dataframe.columns]
    dataframe.columns = normalized_headers

    records_by_part = {}
    source_rows = 0
    duplicate_rows = 0

    for row_index, row_data in dataframe.iterrows():
        row = {key: str(value).strip() for key, value in row_data.to_dict().items()}
        part_number = normalize_part_number(
            pick_column(row, ["part_no", "part_number", "numero_parte"])
        )
        if not part_number:
            continue

        source_rows += 1
        parsed_record = {
            "partNumber": part_number,
            "zoneCode": pick_column(row, ["zone", "zona"]),
            "productModel": pick_column(row, ["model", "modelo"]),
            "productStatus": pick_column(row, ["status", "estatus"]) or "activo",
            "description": pick_column(row, ["description", "descripcion"]),
            "standardPack": parse_standard_pack(
                pick_column(row, ["std_pack", "standard_pack", "std"])
            ),
            "customer": pick_column(row, ["customer", "cliente"]),
            "sourceRow": row_index + 2,
        }

        if part_number in records_by_part:
            duplicate_rows += 1
            records_by_part[part_number] = merge_catalog_record(
                records_by_part[part_number],
                parsed_record,
            )
        else:
            records_by_part[part_number] = parsed_record

    return {
        "sourceRows": source_rows,
        "duplicateRows": duplicate_rows,
        "records": list(records_by_part.values()),
    }


def reset_shipping_data(cursor):
    cursor.execute(f"DELETE FROM `{SHIPPING_TABLES['returns']}`")
    cursor.execute(f"DELETE FROM `{SHIPPING_TABLES['exits']}`")
    cursor.execute(f"DELETE FROM `{SHIPPING_TABLES['entries']}`")
    cursor.execute(f"DELETE FROM `{SHIPPING_TABLES['inventory']}`")
    cursor.execute(f"DELETE FROM `{SHIPPING_TABLES['catalog']}`")


def upsert_catalog(cursor, record, source_file):
    cursor.execute(
        f"""
        INSERT INTO `{SHIPPING_TABLES['catalog']}` (
          part_number,
          product_model,
          product_status,
          description,
          standard_pack,
          customer,
          zone_code,
          source_file,
          source_row
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          id = LAST_INSERT_ID(id),
          product_model = VALUES(product_model),
          product_status = VALUES(product_status),
          description = VALUES(description),
          standard_pack = VALUES(standard_pack),
          customer = VALUES(customer),
          zone_code = VALUES(zone_code),
          source_file = VALUES(source_file),
          source_row = VALUES(source_row),
          updated_at = CURRENT_TIMESTAMP
        """,
        (
            record["partNumber"],
            record.get("productModel") or None,
            record.get("productStatus") or "activo",
            record.get("description") or None,
            record.get("standardPack") or 1,
            record.get("customer") or None,
            record.get("zoneCode") or None,
            source_file,
            record.get("sourceRow"),
        ),
    )
    return cursor.lastrowid


def upsert_inventory(cursor, catalog_id, record):
    cursor.execute(
        f"""
        INSERT INTO `{SHIPPING_TABLES['inventory']}` (
          catalog_id,
          part_number,
          product_model,
          product_status,
          description,
          customer,
          zone_code,
          standard_pack,
          current_quantity,
          catalog_loaded_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, NOW())
        ON DUPLICATE KEY UPDATE
          catalog_id = VALUES(catalog_id),
          product_model = VALUES(product_model),
          product_status = VALUES(product_status),
          description = VALUES(description),
          customer = VALUES(customer),
          zone_code = VALUES(zone_code),
          standard_pack = VALUES(standard_pack),
          updated_at = CURRENT_TIMESTAMP
        """,
        (
            catalog_id,
            record["partNumber"],
            record.get("productModel") or None,
            record.get("productStatus") or "activo",
            record.get("description") or None,
            record.get("customer") or None,
            record.get("zoneCode") or None,
            record.get("standardPack") or 1,
        ),
    )


def get_transaction_connection():
    conn = get_db_connection()
    conn.autocommit(False)
    return conn


@shipping_material_api.route("/catalog/import", methods=["POST"])
@manejo_errores
def import_catalog():
    data = request.get_json(silent=True) or {}
    source_path = resolve_catalog_source_path(
        normalize_search(data.get("sourcePath")) or None
    )
    reset = bool(data.get("reset"))

    conn = None
    cursor = None

    try:
        init_shipping_material_tables()
        parsed = parse_catalog_rows(source_path)
        source_file = os.path.basename(source_path)
        conn = get_transaction_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        if reset:
            reset_shipping_data(cursor)

        for record in parsed["records"]:
            catalog_id = upsert_catalog(cursor, record, source_file)
            upsert_inventory(cursor, catalog_id, record)

        conn.commit()
        return jsonify(
            {
                "success": True,
                "message": "Catalogo de embarques importado correctamente",
                "sourcePath": source_path,
                "sourceRows": parsed["sourceRows"],
                "duplicateRows": parsed["duplicateRows"],
                "importedParts": len(parsed["records"]),
                "resetApplied": reset,
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


@shipping_material_api.route("/entries", methods=["GET"])
@manejo_errores
def list_entries():
    limit = normalize_integer(request.args.get("limit")) or 100
    limit = min(max(limit, 1), 500)
    search = request.args.get("q")
    search_clause, search_params = build_search_clause(
        search,
        [
            "entry_folio",
            "part_number",
            "product_model",
            "description",
            "customer",
            "location_code",
            "reference_code",
            "batch_no",
        ],
    )

    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute(
            f"""
            SELECT
              id,
              entry_folio,
              part_number,
              quantity,
              available_quantity,
              previous_quantity,
              new_quantity,
              product_model,
              description,
              customer,
              zone_code,
              location_code,
              reference_code,
              batch_no,
              notes,
              registered_by,
              movement_at,
              created_at
            FROM `{SHIPPING_TABLES['entries']}`
            WHERE is_fifo_layer_only = 0
            {search_clause}
            ORDER BY movement_at DESC, id DESC
            LIMIT %s
            """,
            tuple(search_params + [limit]),
        )
        rows = [serialize_row(row) for row in cursor.fetchall()]
        return jsonify({"success": True, "entries": rows, "total": len(rows)})
    finally:
        cursor.close()
        conn.close()


@shipping_material_api.route("/entries", methods=["POST"])
@manejo_errores
def create_entry():
    data = request.get_json(silent=True) or {}
    quantity = normalize_integer(data.get("quantity"))
    part_number = normalize_part_number(
        data.get("partNumber") or data.get("box_id") or data.get("part_number")
    )
    location_code = normalize_search(
        data.get("location")
        or data.get("warehouseZone")
        or data.get("warehouse_zone")
    )

    if not part_number or quantity is None or quantity <= 0:
        return jsonify(
            {
                "success": False,
                "error": "Se requiere numero de parte y una cantidad valida",
            }
        ), 400

    conn = None
    cursor = None

    try:
        conn = get_transaction_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        inventory = ensure_inventory_record(cursor, part_number)
        if not inventory:
            conn.rollback()
            return jsonify(
                {
                    "success": False,
                    "error": "El numero de parte no existe en el catalogo de embarques",
                }
            ), 404

        previous_quantity = normalize_integer(inventory.get("current_quantity")) or 0
        new_quantity = previous_quantity + quantity
        available_quantity = resolve_available_layer_quantity(
            previous_quantity,
            quantity,
        )
        movement_at = to_sql_datetime(
            data.get("receivedAt") or data.get("scanned_at")
        )

        update_inventory_snapshot(
            cursor,
            inventory["id"],
            {
                "current_quantity": new_quantity,
                "zone_code": inventory.get("zone_code")
                or inventory.get("catalog_zone_code"),
                "last_entry_at": movement_at,
            },
        )

        entry_folio = generate_movement_folio("EMB-ENT")
        cursor.execute(
            f"""
            INSERT INTO `{SHIPPING_TABLES['entries']}` (
              entry_folio,
              inventory_id,
              catalog_id,
              part_number,
              quantity,
              available_quantity,
              is_fifo_layer_only,
              previous_quantity,
              new_quantity,
              product_model,
              description,
              customer,
              zone_code,
              location_code,
              reference_code,
              batch_no,
              notes,
              registered_by,
              movement_at
            ) VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                entry_folio,
                inventory["id"],
                inventory.get("catalog_id") or inventory.get("catalog_ref_id"),
                inventory["part_number"],
                quantity,
                available_quantity,
                previous_quantity,
                new_quantity,
                inventory.get("product_model") or inventory.get("catalog_model"),
                inventory.get("description") or inventory.get("catalog_description"),
                inventory.get("customer") or inventory.get("catalog_customer"),
                inventory.get("zone_code") or inventory.get("catalog_zone_code"),
                location_code,
                normalize_search(data.get("referenceCode"))
                or normalize_search(data.get("materialCode"))
                or normalize_search(data.get("raw_code"))
                or None,
                normalize_search(data.get("batchNo"))
                or normalize_search(data.get("lotNumber"))
                or normalize_search(data.get("lot_number"))
                or None,
                normalize_search(data.get("notes"))
                or normalize_search(data.get("specification"))
                or None,
                normalize_search(data.get("registeredBy"))
                or normalize_search(data.get("scanned_by"))
                or "Usuario local",
                movement_at,
            ),
        )

        record_id = cursor.lastrowid
        conn.commit()
        return jsonify(
            {
                "success": True,
                "id": record_id,
                "folio": entry_folio,
                "currentQuantity": new_quantity,
                "message": "Entrada registrada",
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


@shipping_material_api.route("/exits", methods=["GET"])
@manejo_errores
def list_exits():
    limit = normalize_integer(request.args.get("limit")) or 100
    limit = min(max(limit, 1), 500)
    search = request.args.get("q")
    search_clause, search_params = build_search_clause(
        search,
        [
            "exit_folio",
            "part_number",
            "product_model",
            "description",
            "customer",
            "zone_code",
            "location_code",
            "destination_area",
            "reason",
            "requested_by",
        ],
    )

    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute(
            f"""
            SELECT
              id,
              exit_folio,
              part_number,
              quantity,
              previous_quantity,
              new_quantity,
              product_model,
              description,
              customer,
              zone_code,
              location_code,
              fifo_allocation_json,
              destination_area,
              reason,
              requested_by,
              remarks,
              registered_by,
              movement_at,
              created_at
            FROM `{SHIPPING_TABLES['exits']}`
            WHERE 1 = 1
            {search_clause}
            ORDER BY movement_at DESC, id DESC
            LIMIT %s
            """,
            tuple(search_params + [limit]),
        )
        rows = [serialize_row(row) for row in cursor.fetchall()]
        return jsonify({"success": True, "exits": rows, "total": len(rows)})
    finally:
        cursor.close()
        conn.close()


@shipping_material_api.route("/exits", methods=["POST"])
@manejo_errores
def create_exit():
    data = request.get_json(silent=True) or {}
    quantity = normalize_integer(data.get("quantity"))
    part_number = normalize_part_number(
        data.get("partNumber")
        or data.get("warehousingCode")
        or data.get("part_number")
    )

    if not part_number or quantity is None or quantity <= 0:
        return jsonify(
            {
                "success": False,
                "error": "Se requiere numero de parte y una cantidad valida",
            }
        ), 400

    conn = None
    cursor = None

    try:
        conn = get_transaction_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        inventory = ensure_inventory_record(cursor, part_number)
        if not inventory:
            conn.rollback()
            return jsonify(
                {
                    "success": False,
                    "error": "El numero de parte no existe en el catalogo de embarques",
                }
            ), 404

        previous_quantity = normalize_integer(inventory.get("current_quantity")) or 0
        fifo_layers = load_fifo_layers(cursor, inventory["part_number"])
        fifo_plan = build_fifo_allocations(fifo_layers, quantity)

        new_quantity = previous_quantity - quantity
        movement_at = to_sql_datetime(data.get("exitedAt"))
        exit_folio = generate_movement_folio("EMB-SAL")
        first_allocation = fifo_plan["allocations"][0] if fifo_plan["allocations"] else {}

        update_inventory_snapshot(
            cursor,
            inventory["id"],
            {
                "current_quantity": new_quantity,
                "last_exit_at": movement_at,
            },
        )
        apply_fifo_allocations(cursor, fifo_plan["allocations"])

        cursor.execute(
            f"""
            INSERT INTO `{SHIPPING_TABLES['exits']}` (
              exit_folio,
              inventory_id,
              catalog_id,
              part_number,
              quantity,
              previous_quantity,
              new_quantity,
              product_model,
              description,
              customer,
              zone_code,
              location_code,
              fifo_allocation_json,
              destination_area,
              reason,
              requested_by,
              remarks,
              registered_by,
              movement_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                exit_folio,
                inventory["id"],
                inventory.get("catalog_id") or inventory.get("catalog_ref_id"),
                inventory["part_number"],
                quantity,
                previous_quantity,
                new_quantity,
                inventory.get("product_model") or inventory.get("catalog_model"),
                inventory.get("description") or inventory.get("catalog_description"),
                inventory.get("customer") or inventory.get("catalog_customer"),
                first_allocation.get("zoneCode")
                or inventory.get("zone_code")
                or inventory.get("catalog_zone_code"),
                first_allocation.get("locationCode"),
                json.dumps(fifo_plan["allocations"]),
                normalize_search(data.get("destinationArea"))
                or normalize_search(data.get("department"))
                or "Embarques",
                normalize_search(data.get("reason"))
                or normalize_search(data.get("process"))
                or "Salida de producto terminado",
                normalize_search(data.get("requestedBy"))
                or normalize_search(data.get("model"))
                or None,
                normalize_search(data.get("remarks")) or None,
                normalize_search(data.get("registeredBy"))
                or normalize_search(data.get("userName"))
                or "Usuario local",
                movement_at,
            ),
        )

        record_id = cursor.lastrowid
        conn.commit()
        return jsonify(
            {
                "success": True,
                "id": record_id,
                "folio": exit_folio,
                "currentQuantity": new_quantity,
                "message": "Salida registrada",
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


@shipping_material_api.route("/returns", methods=["GET"])
@manejo_errores
def list_returns():
    limit = normalize_integer(request.args.get("limit")) or 100
    limit = min(max(limit, 1), 500)
    search = request.args.get("q")
    search_clause, search_params = build_search_clause(
        search,
        [
            "return_folio",
            "part_number",
            "product_model",
            "description",
            "customer",
            "reason",
            "remarks",
        ],
    )

    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute(
            f"""
            SELECT
              id,
              return_folio,
              part_number,
              return_quantity,
              loss_quantity,
              previous_quantity,
              new_quantity,
              product_model,
              description,
              customer,
              zone_code,
              location_code,
              reason,
              remarks,
              registered_by,
              movement_at,
              created_at
            FROM `{SHIPPING_TABLES['returns']}`
            WHERE 1 = 1
            {search_clause}
            ORDER BY movement_at DESC, id DESC
            LIMIT %s
            """,
            tuple(search_params + [limit]),
        )
        rows = [serialize_row(row) for row in cursor.fetchall()]
        return jsonify({"success": True, "returns": rows, "total": len(rows)})
    finally:
        cursor.close()
        conn.close()


@shipping_material_api.route("/returns", methods=["POST"])
@manejo_errores
def create_return():
    data = request.get_json(silent=True) or {}
    return_quantity = normalize_integer(data.get("returnQty"))
    loss_quantity = normalize_integer(data.get("lossQty")) or 0
    part_number = normalize_part_number(
        data.get("partNumber")
        or data.get("warehousingCode")
        or data.get("part_number")
    )

    if not part_number or return_quantity is None or return_quantity <= 0:
        return jsonify(
            {
                "success": False,
                "error": "Se requiere numero de parte y una cantidad de retorno valida",
            }
        ), 400

    if loss_quantity < 0 or loss_quantity > return_quantity:
        return jsonify(
            {
                "success": False,
                "error": "La merma no puede ser mayor que la cantidad retornada",
            }
        ), 400

    conn = None
    cursor = None

    try:
        conn = get_transaction_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        inventory = ensure_inventory_record(cursor, part_number)
        if not inventory:
            conn.rollback()
            return jsonify(
                {
                    "success": False,
                    "error": "El numero de parte no existe en el catalogo de embarques",
                }
            ), 404

        previous_quantity = normalize_integer(inventory.get("current_quantity")) or 0
        net_quantity = return_quantity - loss_quantity
        new_quantity = previous_quantity + net_quantity
        available_quantity = resolve_available_layer_quantity(
            previous_quantity,
            net_quantity,
        )
        movement_at = to_sql_datetime(data.get("returnedAt"))
        return_folio = generate_movement_folio("EMB-RET")

        update_inventory_snapshot(
            cursor,
            inventory["id"],
            {
                "current_quantity": new_quantity,
                "last_return_at": movement_at,
            },
        )

        cursor.execute(
            f"""
            INSERT INTO `{SHIPPING_TABLES['returns']}` (
              return_folio,
              inventory_id,
              catalog_id,
              part_number,
              return_quantity,
              loss_quantity,
              previous_quantity,
              new_quantity,
              product_model,
              description,
              customer,
              zone_code,
              location_code,
              reason,
              remarks,
              registered_by,
              movement_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                return_folio,
                inventory["id"],
                inventory.get("catalog_id") or inventory.get("catalog_ref_id"),
                inventory["part_number"],
                return_quantity,
                loss_quantity,
                previous_quantity,
                new_quantity,
                inventory.get("product_model") or inventory.get("catalog_model"),
                inventory.get("description") or inventory.get("catalog_description"),
                inventory.get("customer") or inventory.get("catalog_customer"),
                inventory.get("zone_code") or inventory.get("catalog_zone_code"),
                normalize_search(data.get("location")) or None,
                normalize_search(data.get("reason")) or "Retorno a embarques",
                normalize_search(data.get("remarks")) or None,
                normalize_search(data.get("registeredBy"))
                or normalize_search(data.get("userName"))
                or "Usuario local",
                movement_at,
            ),
        )
        record_id = cursor.lastrowid

        create_hidden_return_layer(
            cursor,
            inventory,
            return_folio,
            {
                "netQuantity": net_quantity,
                "availableQuantity": available_quantity,
                "zoneCode": data.get("zone"),
                "locationCode": data.get("location"),
                "notes": data.get("remarks"),
                "registeredBy": normalize_search(data.get("registeredBy"))
                or normalize_search(data.get("userName"))
                or "Usuario local",
                "movementAt": movement_at,
            },
        )

        conn.commit()
        return jsonify(
            {
                "success": True,
                "id": record_id,
                "folio": return_folio,
                "currentQuantity": new_quantity,
                "netQuantity": net_quantity,
                "message": "Retorno registrado",
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


@shipping_material_api.route("/inventory", methods=["GET"])
@manejo_errores
def get_inventory():
    part_number = normalize_search(request.args.get("partNumber"))
    model = normalize_search(request.args.get("model"))
    customer = normalize_search(request.args.get("customer"))
    limit = normalize_integer(request.args.get("limit")) or 200
    limit = min(max(limit, 1), 500)

    where = []
    params = []

    if part_number:
        where.append("part_number LIKE %s")
        params.append(f"%{part_number.upper()}%")

    if model:
        where.append("COALESCE(product_model, '') LIKE %s")
        params.append(f"%{model}%")

    if customer:
        where.append("COALESCE(customer, '') LIKE %s")
        params.append(f"%{customer}%")

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute(
            f"""
            SELECT
              part_number,
              product_model,
              description,
              customer,
              zone_code,
              standard_pack,
              product_status,
              current_quantity
            FROM `{SHIPPING_TABLES['inventory']}`
            {where_clause}
            ORDER BY part_number ASC
            LIMIT %s
            """,
            tuple(params + [limit]),
        )
        rows = [serialize_row(row) for row in cursor.fetchall()]
        return jsonify({"success": True, "inventory": rows, "total": len(rows)})
    finally:
        cursor.close()
        conn.close()


@shipping_material_api.route("/stats/today", methods=["GET"])
@manejo_errores
def get_today_stats():
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
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute(
            f"""
            SELECT COUNT(*) AS total_entries
            FROM `{SHIPPING_TABLES['entries']}`
            WHERE is_fifo_layer_only = 0
              AND DATE(movement_at) = %s
            """,
            (target_date,),
        )
        entry_stats = cursor.fetchone() or {}

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total_exits
            FROM `{SHIPPING_TABLES['exits']}`
            WHERE DATE(movement_at) = %s
            """,
            (target_date,),
        )
        exit_stats = cursor.fetchone() or {}

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total_returns
            FROM `{SHIPPING_TABLES['returns']}`
            WHERE DATE(movement_at) = %s
            """,
            (target_date,),
        )
        return_stats = cursor.fetchone() or {}

        cursor.execute(
            f"""
            SELECT
              COUNT(*) AS inventory_items,
              COALESCE(SUM(current_quantity), 0) AS inventory_quantity
            FROM `{SHIPPING_TABLES['inventory']}`
            """
        )
        inventory_stats = cursor.fetchone() or {}

        entries = normalize_integer(entry_stats.get("total_entries")) or 0
        exits = normalize_integer(exit_stats.get("total_exits")) or 0
        returns = normalize_integer(return_stats.get("total_returns")) or 0
        inventory_items = normalize_integer(inventory_stats.get("inventory_items")) or 0
        inventory_quantity = normalize_integer(
            inventory_stats.get("inventory_quantity")
        ) or 0

        return jsonify(
            {
                "success": True,
                "date": target_date.strftime("%Y-%m-%d"),
                "entries": entries,
                "exits": exits,
                "returns": returns,
                "inventory_items": inventory_items,
                "inventory_quantity": inventory_quantity,
                "total": entries + exits + returns,
            }
        )
    finally:
        cursor.close()
        conn.close()


def register_shipping_material_routes(app):
    try:
        if "shipping_material_api" not in app.blueprints:
            app.register_blueprint(shipping_material_api)
            print("Shipping Material API registrada en /api/shipping/material")
        return True
    except Exception as exc:
        print(f"Error registrando Shipping Material API: {exc}")
        return False
