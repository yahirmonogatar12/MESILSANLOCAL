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
    "departure_history": "embarques_departure_historial",
    "movement_adjustments": "embarques_movimiento_ajustes_historial",
    "inventory_closures": "embarques_inventario_cierres",
    "inventory_closure_batches": "embarques_inventario_cierre_lotes",
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


def normalize_departure_code(raw_value):
    value = normalize_search(raw_value)
    return value.upper() if value else ""


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


def get_split_folio_base(exit_folio):
    folio = normalize_search(exit_folio)
    if not folio:
        return ""
    return re.sub(r"-S\d*$", "", folio)


def generate_split_exit_folio(cursor, source_exit_folio):
    base_folio = get_split_folio_base(source_exit_folio)
    if not base_folio:
        return f"{generate_movement_folio('EMB-SAL')}-S"

    cursor.execute(
        f"""
        SELECT exit_folio
        FROM `{SHIPPING_TABLES['exits']}`
        WHERE exit_folio = %s OR exit_folio LIKE %s
        ORDER BY id ASC
        """,
        (f"{base_folio}-S", f"{base_folio}-S%"),
    )
    existing_folios = {normalize_search(row.get("exit_folio")) for row in cursor.fetchall()}
    if f"{base_folio}-S" not in existing_folios:
        return f"{base_folio}-S"

    suffix = 2
    while f"{base_folio}-S{suffix}" in existing_folios:
        suffix += 1
    return f"{base_folio}-S{suffix}"


def parse_fifo_allocations(raw_value):
    if not raw_value:
        return []

    if isinstance(raw_value, list):
        return raw_value

    try:
        parsed = json.loads(raw_value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []

    return parsed if isinstance(parsed, list) else []


def split_fifo_allocations(allocations, assigned_quantity):
    requested_quantity = normalize_integer(assigned_quantity) or 0
    assigned_allocations = []
    remainder_allocations = []
    remaining_to_assign = requested_quantity

    for allocation in allocations:
        allocation_data = dict(allocation)
        previous_available = normalize_integer(allocation_data.get("previousAvailable")) or 0
        consumed_quantity = normalize_integer(allocation_data.get("consumedQuantity")) or 0

        if consumed_quantity <= 0:
            continue

        assigned_from_layer = min(consumed_quantity, max(remaining_to_assign, 0))
        if assigned_from_layer > 0:
            assigned_allocations.append(
                {
                    **allocation_data,
                    "consumedQuantity": assigned_from_layer,
                    "previousAvailable": previous_available,
                    "nextAvailable": previous_available - assigned_from_layer,
                }
            )
            remaining_to_assign -= assigned_from_layer

        remaining_on_layer = consumed_quantity - assigned_from_layer
        if remaining_on_layer > 0:
            remainder_previous_available = previous_available - assigned_from_layer
            remainder_allocations.append(
                {
                    **allocation_data,
                    "consumedQuantity": remaining_on_layer,
                    "previousAvailable": remainder_previous_available,
                    "nextAvailable": remainder_previous_available - remaining_on_layer,
                }
            )

    return assigned_allocations, remainder_allocations


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
              split_from_exit_id BIGINT UNSIGNED NULL,
              split_root_exit_id BIGINT UNSIGNED NULL,
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
              departure_code VARCHAR(120) NULL,
              departure_assigned_at DATETIME NULL,
              departure_assigned_by VARCHAR(120) NULL,
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
            CREATE TABLE IF NOT EXISTS `{SHIPPING_TABLES['departure_history']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              exit_id BIGINT UNSIGNED NOT NULL,
              exit_folio VARCHAR(40) NOT NULL,
              inventory_id BIGINT UNSIGNED NOT NULL,
              catalog_id BIGINT UNSIGNED NOT NULL,
              part_number VARCHAR(64) NOT NULL,
              quantity INT NOT NULL,
              departure_code VARCHAR(120) NOT NULL,
              previous_departure_code VARCHAR(120) NULL,
              assignment_action VARCHAR(20) NOT NULL DEFAULT 'assigned',
              product_model VARCHAR(180) NULL,
              customer VARCHAR(120) NULL,
              destination_area VARCHAR(120) NULL,
              reason VARCHAR(120) NULL,
              assigned_by VARCHAR(120) NULL,
              assigned_at DATETIME NOT NULL,
              notes TEXT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              KEY idx_departure_history_exit_id (exit_id),
              KEY idx_departure_history_departure (departure_code),
              KEY idx_departure_history_part_number (part_number),
              KEY idx_departure_history_assigned_at (assigned_at),
              CONSTRAINT fk_departure_history_exit
                FOREIGN KEY (exit_id) REFERENCES `{SHIPPING_TABLES['exits']}` (id)
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

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{SHIPPING_TABLES['movement_adjustments']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              movement_type VARCHAR(20) NOT NULL,
              record_id BIGINT UNSIGNED NOT NULL,
              folio VARCHAR(40) NULL,
              part_number VARCHAR(64) NOT NULL,
              adjustment_action VARCHAR(20) NOT NULL DEFAULT 'update',
              previous_values_json LONGTEXT NOT NULL,
              new_values_json LONGTEXT NOT NULL,
              changed_fields_json LONGTEXT NOT NULL,
              notes TEXT NULL,
              adjusted_by VARCHAR(120) NULL,
              adjusted_at DATETIME NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              KEY idx_adjustments_type_record (movement_type, record_id),
              KEY idx_adjustments_part_number (part_number),
              KEY idx_adjustments_adjusted_at (adjusted_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{SHIPPING_TABLES['inventory_closures']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              part_number VARCHAR(64) NOT NULL,
              initial_quantity INT NOT NULL DEFAULT 0,
              closed_at DATETIME NOT NULL,
              closure_label VARCHAR(120) NULL,
              closed_by VARCHAR(120) NULL,
              notes TEXT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              KEY idx_inventory_closures_part_closed_at (part_number, closed_at),
              KEY idx_inventory_closures_closed_at (closed_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS `{SHIPPING_TABLES['inventory_closure_batches']}` (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              closure_label VARCHAR(120) NOT NULL,
              closure_month CHAR(7) NOT NULL,
              closed_at DATETIME NOT NULL,
              status VARCHAR(20) NOT NULL DEFAULT 'draft',
              created_by VARCHAR(120) NULL,
              confirmed_by VARCHAR(120) NULL,
              csv_file_name VARCHAR(255) NULL,
              csv_hash CHAR(64) NULL,
              rows_hash CHAR(64) NULL,
              payload_json LONGTEXT NULL,
              accuracy_pct DECIMAL(6,2) NOT NULL DEFAULT 0.00,
              total_rows INT NOT NULL DEFAULT 0,
              differing_rows INT NOT NULL DEFAULT 0,
              notes TEXT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              confirmed_at DATETIME NULL,
              PRIMARY KEY (id),
              KEY idx_inventory_closure_batches_month (closure_month),
              KEY idx_inventory_closure_batches_status (status),
              KEY idx_inventory_closure_batches_closed_at (closed_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        remove_deprecated_location_defaults(cursor)
        ensure_column(
            cursor,
            SHIPPING_TABLES["exits"],
            "split_from_exit_id",
            "BIGINT UNSIGNED NULL AFTER `exit_folio`",
        )
        ensure_column(
            cursor,
            SHIPPING_TABLES["exits"],
            "split_root_exit_id",
            "BIGINT UNSIGNED NULL AFTER `split_from_exit_id`",
        )
        ensure_column(
            cursor,
            SHIPPING_TABLES["exits"],
            "departure_code",
            "VARCHAR(120) NULL AFTER `destination_area`",
        )
        ensure_column(
            cursor,
            SHIPPING_TABLES["exits"],
            "departure_assigned_at",
            "DATETIME NULL AFTER `departure_code`",
        )
        ensure_column(
            cursor,
            SHIPPING_TABLES["exits"],
            "departure_assigned_by",
            "VARCHAR(120) NULL AFTER `departure_assigned_at`",
        )
        ensure_column(
            cursor,
            SHIPPING_TABLES["movement_adjustments"],
            "notes",
            "TEXT NULL AFTER `changed_fields_json`",
        )
        ensure_column(
            cursor,
            SHIPPING_TABLES["inventory_closures"],
            "closure_batch_id",
            "BIGINT UNSIGNED NULL AFTER `id`",
        )
        ensure_column(
            cursor,
            SHIPPING_TABLES["inventory_closures"],
            "system_quantity",
            "INT NULL AFTER `initial_quantity`",
        )
        ensure_column(
            cursor,
            SHIPPING_TABLES["inventory_closures"],
            "difference_quantity",
            "INT NULL AFTER `system_quantity`",
        )
        ensure_column(
            cursor,
            SHIPPING_TABLES["inventory_closures"],
            "raw_current_quantity",
            "INT NULL AFTER `difference_quantity`",
        )
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


def fetch_exit_record_for_update(cursor, exit_id):
    cursor.execute(
        f"""
        SELECT
          id,
          exit_folio,
          split_from_exit_id,
          split_root_exit_id,
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
          departure_code,
          departure_assigned_at,
          departure_assigned_by,
          reason,
          requested_by,
          remarks,
          registered_by,
          movement_at
        FROM `{SHIPPING_TABLES['exits']}`
        WHERE id = %s
        LIMIT 1
        FOR UPDATE
        """,
        (exit_id,),
    )
    return cursor.fetchone()


def insert_departure_history_record(
    cursor,
    exit_row,
    departure_code,
    assigned_by,
    assigned_at,
    notes=None,
):
    previous_departure_code = normalize_departure_code(exit_row.get("departure_code")) or None
    action = "reassigned" if previous_departure_code else "assigned"

    cursor.execute(
        f"""
        INSERT INTO `{SHIPPING_TABLES['departure_history']}` (
          exit_id,
          exit_folio,
          inventory_id,
          catalog_id,
          part_number,
          quantity,
          departure_code,
          previous_departure_code,
          assignment_action,
          product_model,
          customer,
          destination_area,
          reason,
          assigned_by,
          assigned_at,
          notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            exit_row["id"],
            exit_row.get("exit_folio"),
            exit_row.get("inventory_id"),
            exit_row.get("catalog_id"),
            exit_row.get("part_number"),
            normalize_integer(exit_row.get("quantity")) or 0,
            departure_code,
            previous_departure_code,
            action,
            exit_row.get("product_model"),
            exit_row.get("customer"),
            exit_row.get("destination_area"),
            exit_row.get("reason"),
            normalize_search(assigned_by) or "Sistema",
            assigned_at,
            normalize_search(notes) or None,
        ),
    )


def create_split_exit_record(cursor, source_exit_row, split_quantity, split_allocations):
    split_folio = generate_split_exit_folio(cursor, source_exit_row.get("exit_folio"))
    split_root_exit_id = (
        normalize_integer(source_exit_row.get("split_root_exit_id"))
        or normalize_integer(source_exit_row.get("id"))
        or None
    )
    source_new_quantity = normalize_integer(source_exit_row.get("new_quantity")) or 0
    split_quantity_value = normalize_integer(split_quantity) or 0
    split_previous_quantity = source_new_quantity + split_quantity_value
    first_split_allocation = split_allocations[0] if split_allocations else {}

    cursor.execute(
        f"""
        INSERT INTO `{SHIPPING_TABLES['exits']}` (
          exit_folio,
          split_from_exit_id,
          split_root_exit_id,
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
          departure_code,
          departure_assigned_at,
          departure_assigned_by,
          reason,
          requested_by,
          remarks,
          registered_by,
          movement_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            split_folio,
            source_exit_row.get("id"),
            split_root_exit_id,
            source_exit_row.get("inventory_id"),
            source_exit_row.get("catalog_id"),
            source_exit_row.get("part_number"),
            split_quantity_value,
            split_previous_quantity,
            source_new_quantity,
            source_exit_row.get("product_model"),
            source_exit_row.get("description"),
            source_exit_row.get("customer"),
            first_split_allocation.get("zoneCode") or source_exit_row.get("zone_code"),
            first_split_allocation.get("locationCode")
            or source_exit_row.get("location_code"),
            json.dumps(split_allocations) if split_allocations else None,
            source_exit_row.get("destination_area"),
            None,
            None,
            None,
            source_exit_row.get("reason"),
            source_exit_row.get("requested_by"),
            source_exit_row.get("remarks"),
            source_exit_row.get("registered_by"),
            source_exit_row.get("movement_at"),
        ),
    )
    return {
        "id": cursor.lastrowid,
        "folio": split_folio,
        "quantity": split_quantity_value,
    }


def assign_exit_departure_value(
    exit_id,
    departure_code,
    assigned_by,
    departure_quantity=None,
    notes=None,
    assigned_at=None,
):
    normalized_departure = normalize_departure_code(departure_code)
    if not normalized_departure:
        return {
            "success": False,
            "error": "Se requiere un departure valido",
        }, 400

    conn = None
    cursor = None

    try:
        conn = get_transaction_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        exit_row = fetch_exit_record_for_update(cursor, exit_id)
        if not exit_row:
            conn.rollback()
            return {
                "success": False,
                "error": "La salida solicitada no existe",
            }, 404

        row_quantity = normalize_integer(exit_row.get("quantity")) or 0
        assigned_quantity = normalize_integer(departure_quantity)
        if assigned_quantity is None:
            assigned_quantity = row_quantity
        if assigned_quantity <= 0:
            conn.rollback()
            return {
                "success": False,
                "error": "La cantidad a asignar al departure debe ser mayor a cero",
            }, 400
        if assigned_quantity > row_quantity:
            conn.rollback()
            return {
                "success": False,
                "error": "La cantidad del departure no puede ser mayor a la cantidad del registro",
                "availableQuantity": row_quantity,
            }, 400

        current_departure = normalize_departure_code(exit_row.get("departure_code"))
        if current_departure and current_departure != normalized_departure:
            conn.rollback()
            return {
                "success": False,
                "error": "La salida ya tiene un departure asignado",
            }, 409
        if current_departure == normalized_departure:
            if assigned_quantity != row_quantity:
                conn.rollback()
                return {
                    "success": False,
                    "error": "La salida ya tiene un departure asignado; usa el registro restante para otra asignacion",
                }, 409
            conn.rollback()
            return {
                "success": True,
                "id": exit_row["id"],
                "folio": exit_row.get("exit_folio"),
                "departureCode": normalized_departure,
                "assignedQuantity": row_quantity,
                "unchanged": True,
                "message": "El departure ya estaba asignado",
            }, 200

        assignment_timestamp = to_sql_datetime(assigned_at)
        normalized_assigned_by = normalize_search(assigned_by) or "Sistema"
        fifo_allocations = parse_fifo_allocations(exit_row.get("fifo_allocation_json"))
        assigned_allocations, remaining_allocations = split_fifo_allocations(
            fifo_allocations,
            assigned_quantity,
        )
        split_record = None
        quantity_to_keep = assigned_quantity
        remaining_quantity = row_quantity - assigned_quantity
        previous_quantity = normalize_integer(exit_row.get("previous_quantity")) or 0
        assigned_new_quantity = previous_quantity - quantity_to_keep

        if remaining_quantity > 0:
            split_record = create_split_exit_record(
                cursor,
                exit_row,
                remaining_quantity,
                remaining_allocations,
            )

        cursor.execute(
            f"""
            UPDATE `{SHIPPING_TABLES['exits']}`
            SET quantity = %s,
                new_quantity = %s,
                fifo_allocation_json = %s,
                departure_code = %s,
                departure_assigned_at = %s,
                departure_assigned_by = %s
            WHERE id = %s
            """,
            (
                quantity_to_keep,
                assigned_new_quantity,
                json.dumps(assigned_allocations) if assigned_allocations else None,
                normalized_departure,
                assignment_timestamp,
                normalized_assigned_by,
                exit_row["id"],
            ),
        )

        assigned_exit_row = {
            **exit_row,
            "quantity": quantity_to_keep,
            "new_quantity": assigned_new_quantity,
            "fifo_allocation_json": json.dumps(assigned_allocations)
            if assigned_allocations
            else None,
        }
        insert_departure_history_record(
            cursor,
            assigned_exit_row,
            normalized_departure,
            normalized_assigned_by,
            assignment_timestamp,
            notes=notes,
        )

        conn.commit()
        return {
            "success": True,
            "id": exit_row["id"],
            "folio": exit_row.get("exit_folio"),
            "departureCode": normalized_departure,
            "assignedQuantity": quantity_to_keep,
            "remainingQuantity": remaining_quantity,
            "splitCreated": bool(split_record),
            "splitExitId": split_record.get("id") if split_record else None,
            "splitFolio": split_record.get("folio") if split_record else None,
            "assignedAt": serialize_datetime(assignment_timestamp),
            "assignedBy": normalized_assigned_by,
            "message": (
                "Departure asignado y salida dividida correctamente"
                if split_record
                else "Departure asignado correctamente"
            ),
        }, 200
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_departure_history_records(limit=300, departure_code=None, exit_id=None):
    limit_value = min(max(normalize_integer(limit) or 300, 1), 2000)
    where_clauses = ["1 = 1"]
    params = []

    normalized_departure = normalize_departure_code(departure_code)
    if normalized_departure:
        where_clauses.append("departure_code = %s")
        params.append(normalized_departure)

    normalized_exit_id = normalize_integer(exit_id)
    if normalized_exit_id:
        where_clauses.append("exit_id = %s")
        params.append(normalized_exit_id)

    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute(
            f"""
            SELECT
              id,
              exit_id,
              exit_folio,
              part_number,
              quantity,
              departure_code,
              previous_departure_code,
              assignment_action,
              product_model,
              customer,
              destination_area,
              reason,
              assigned_by,
              assigned_at,
              notes,
              created_at
            FROM `{SHIPPING_TABLES['departure_history']}`
            WHERE {" AND ".join(where_clauses)}
            ORDER BY assigned_at DESC, id DESC
            LIMIT %s
            """,
            tuple(params + [limit_value]),
        )
        rows = [serialize_row(row) for row in cursor.fetchall()]
        return {"success": True, "history": rows, "total": len(rows)}
    finally:
        cursor.close()
        conn.close()


def normalize_movement_type(raw_value):
    normalized = normalize_search(raw_value).lower()
    mapping = {
        "entrada": "entry",
        "entradas": "entry",
        "entry": "entry",
        "salida": "exit",
        "salidas": "exit",
        "exit": "exit",
        "retorno": "return",
        "retornos": "return",
        "return": "return",
    }
    return mapping.get(normalized, normalized)


def json_dumps_safe(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def normalize_optional_text(raw_value):
    value = normalize_search(raw_value)
    return value or None


def generate_return_layer_folio(return_row):
    return_id = normalize_integer(return_row.get("id"))
    if return_id:
        return f"EMB-LYR-{return_id}"
    return generate_movement_folio("EMB-LYR")


def fetch_entry_record_for_update(cursor, entry_id):
    cursor.execute(
        f"""
        SELECT
          id,
          entry_folio,
          inventory_id,
          catalog_id,
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
        WHERE id = %s
          AND COALESCE(is_fifo_layer_only, 0) = 0
        LIMIT 1
        FOR UPDATE
        """,
        (entry_id,),
    )
    return cursor.fetchone()


def fetch_return_record_for_update(cursor, return_id):
    cursor.execute(
        f"""
        SELECT
          id,
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
          movement_at,
          created_at
        FROM `{SHIPPING_TABLES['returns']}`
        WHERE id = %s
        LIMIT 1
        FOR UPDATE
        """,
        (return_id,),
    )
    return cursor.fetchone()


def build_movement_adjustment_snapshot(movement_type, row):
    normalized_type = normalize_movement_type(movement_type)
    if normalized_type == "entry":
        snapshot = {
            "id": row.get("id"),
            "folio": row.get("entry_folio"),
            "part_number": row.get("part_number"),
            "quantity": normalize_integer(row.get("quantity")) or 0,
            "available_quantity": normalize_integer(row.get("available_quantity")) or 0,
            "product_model": normalize_optional_text(row.get("product_model")),
            "description": normalize_optional_text(row.get("description")),
            "customer": normalize_optional_text(row.get("customer")),
            "zone_code": normalize_optional_text(row.get("zone_code")),
            "location_code": normalize_optional_text(row.get("location_code")),
            "reference_code": normalize_optional_text(row.get("reference_code")),
            "batch_no": normalize_optional_text(row.get("batch_no")),
            "notes": normalize_optional_text(row.get("notes")),
            "registered_by": normalize_optional_text(row.get("registered_by")),
            "movement_at": serialize_datetime(row.get("movement_at")),
        }
        return serialize_row(snapshot)

    if normalized_type == "exit":
        snapshot = {
            "id": row.get("id"),
            "folio": row.get("exit_folio"),
            "part_number": row.get("part_number"),
            "quantity": normalize_integer(row.get("quantity")) or 0,
            "previous_quantity": normalize_integer(row.get("previous_quantity")) or 0,
            "new_quantity": normalize_integer(row.get("new_quantity")) or 0,
            "product_model": normalize_optional_text(row.get("product_model")),
            "description": normalize_optional_text(row.get("description")),
            "customer": normalize_optional_text(row.get("customer")),
            "zone_code": normalize_optional_text(row.get("zone_code")),
            "location_code": normalize_optional_text(row.get("location_code")),
            "destination_area": normalize_optional_text(row.get("destination_area")),
            "departure_code": normalize_optional_text(row.get("departure_code")),
            "reason": normalize_optional_text(row.get("reason")),
            "requested_by": normalize_optional_text(row.get("requested_by")),
            "remarks": normalize_optional_text(row.get("remarks")),
            "registered_by": normalize_optional_text(row.get("registered_by")),
            "movement_at": serialize_datetime(row.get("movement_at")),
        }
        return serialize_row(snapshot)

    snapshot = {
        "id": row.get("id"),
        "folio": row.get("return_folio"),
        "part_number": row.get("part_number"),
        "return_quantity": normalize_integer(row.get("return_quantity")) or 0,
        "loss_quantity": normalize_integer(row.get("loss_quantity")) or 0,
        "previous_quantity": normalize_integer(row.get("previous_quantity")) or 0,
        "new_quantity": normalize_integer(row.get("new_quantity")) or 0,
        "product_model": normalize_optional_text(row.get("product_model")),
        "description": normalize_optional_text(row.get("description")),
        "customer": normalize_optional_text(row.get("customer")),
        "zone_code": normalize_optional_text(row.get("zone_code")),
        "location_code": normalize_optional_text(row.get("location_code")),
        "reason": normalize_optional_text(row.get("reason")),
        "remarks": normalize_optional_text(row.get("remarks")),
        "registered_by": normalize_optional_text(row.get("registered_by")),
        "movement_at": serialize_datetime(row.get("movement_at")),
    }
    return serialize_row(snapshot)


def insert_movement_adjustment_record(
    cursor,
    movement_type,
    record_id,
    folio,
    part_number,
    previous_values,
    new_values,
    changed_fields,
    adjusted_by,
    adjusted_at,
    notes=None,
    adjustment_action="update",
):
    cursor.execute(
        f"""
        INSERT INTO `{SHIPPING_TABLES['movement_adjustments']}` (
          movement_type,
          record_id,
          folio,
          part_number,
          adjustment_action,
          previous_values_json,
          new_values_json,
          changed_fields_json,
          notes,
          adjusted_by,
          adjusted_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            movement_type,
            record_id,
            folio,
            part_number,
            normalize_optional_text(adjustment_action) or "update",
            json_dumps_safe(previous_values),
            json_dumps_safe(new_values),
            json_dumps_safe(changed_fields),
            normalize_optional_text(notes),
            normalize_optional_text(adjusted_by) or "Sistema",
            adjusted_at,
        ),
    )


def load_rebuild_movements_for_part(cursor, part_number):
    normalized_part = normalize_part_number(part_number)
    if not normalized_part:
        return []

    movements = []

    cursor.execute(
        f"""
        SELECT
          id,
          entry_folio AS folio,
          quantity,
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
        WHERE part_number = %s
          AND COALESCE(is_fifo_layer_only, 0) = 0
        """,
        (normalized_part,),
    )
    for row in cursor.fetchall():
        movements.append(
            {
                **row,
                "movement_type": "entry",
                "sort_at": row.get("movement_at") or row.get("created_at"),
                "sort_order": 1,
            }
        )

    cursor.execute(
        f"""
        SELECT
          id,
          return_folio AS folio,
          return_quantity,
          loss_quantity,
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
        WHERE part_number = %s
        """,
        (normalized_part,),
    )
    for row in cursor.fetchall():
        movements.append(
            {
                **row,
                "movement_type": "return",
                "sort_at": row.get("movement_at") or row.get("created_at"),
                "sort_order": 2,
            }
        )

    cursor.execute(
        f"""
        SELECT
          id,
          exit_folio AS folio,
          quantity,
          product_model,
          description,
          customer,
          zone_code,
          location_code,
          destination_area,
          departure_code,
          reason,
          requested_by,
          remarks,
          registered_by,
          movement_at,
          created_at
        FROM `{SHIPPING_TABLES['exits']}`
        WHERE part_number = %s
        """,
        (normalized_part,),
    )
    for row in cursor.fetchall():
        movements.append(
            {
                **row,
                "movement_type": "exit",
                "sort_at": row.get("movement_at") or row.get("created_at"),
                "sort_order": 3,
            }
        )

    movements.sort(
        key=lambda row: (
            row.get("sort_at") or datetime.min,
            row.get("sort_order") or 9,
            normalize_integer(row.get("id")) or 0,
        )
    )
    return movements


def rebuild_part_inventory_state(cursor, part_number):
    normalized_part = normalize_part_number(part_number)
    if not normalized_part:
        return None

    inventory = ensure_inventory_record(cursor, normalized_part)
    if not inventory:
        return None

    cursor.execute(
        f"""
        DELETE FROM `{SHIPPING_TABLES['entries']}`
        WHERE part_number = %s
          AND COALESCE(is_fifo_layer_only, 0) = 1
        """,
        (normalized_part,),
    )

    movements = load_rebuild_movements_for_part(cursor, normalized_part)
    layer_queue = []
    tracked_available = {}
    current_quantity = 0
    last_entry_at = None
    last_exit_at = None
    last_return_at = None

    for movement in movements:
        movement_type = movement.get("movement_type")
        movement_at = movement.get("movement_at") or movement.get("created_at") or to_sql_datetime()

        if movement_type == "entry":
            quantity = normalize_integer(movement.get("quantity")) or 0
            previous_quantity = current_quantity
            new_quantity = previous_quantity + quantity
            available_quantity = resolve_available_layer_quantity(previous_quantity, quantity)

            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['entries']}`
                SET previous_quantity = %s,
                    new_quantity = %s,
                    available_quantity = %s
                WHERE id = %s
                """,
                (
                    previous_quantity,
                    new_quantity,
                    available_quantity,
                    movement["id"],
                ),
            )

            tracked_available[movement["id"]] = available_quantity
            if available_quantity > 0:
                layer_queue.append(
                    {
                        "entry_id": movement["id"],
                        "entry_folio": movement.get("folio"),
                        "available_quantity": available_quantity,
                        "zone_code": movement.get("zone_code"),
                        "location_code": movement.get("location_code"),
                        "movement_at": movement_at,
                    }
                )

            current_quantity = new_quantity
            last_entry_at = movement_at
            continue

        if movement_type == "return":
            return_quantity = normalize_integer(movement.get("return_quantity")) or 0
            loss_quantity = normalize_integer(movement.get("loss_quantity")) or 0
            net_quantity = return_quantity - loss_quantity
            previous_quantity = current_quantity
            new_quantity = previous_quantity + net_quantity

            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['returns']}`
                SET previous_quantity = %s,
                    new_quantity = %s
                WHERE id = %s
                """,
                (
                    previous_quantity,
                    new_quantity,
                    movement["id"],
                ),
            )

            available_quantity = resolve_available_layer_quantity(
                previous_quantity,
                net_quantity,
            )
            if net_quantity > 0 and available_quantity > 0:
                hidden_folio = generate_return_layer_folio(movement)
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
                        hidden_folio,
                        inventory["id"],
                        inventory.get("catalog_id") or inventory.get("catalog_ref_id"),
                        normalized_part,
                        available_quantity,
                        available_quantity,
                        available_quantity,
                        movement.get("product_model")
                        or inventory.get("product_model")
                        or inventory.get("catalog_model"),
                        movement.get("description")
                        or inventory.get("description")
                        or inventory.get("catalog_description"),
                        movement.get("customer")
                        or inventory.get("customer")
                        or inventory.get("catalog_customer"),
                        movement.get("zone_code")
                        or inventory.get("zone_code")
                        or inventory.get("catalog_zone_code"),
                        movement.get("location_code"),
                        f"RETORNO:{movement.get('folio')}",
                        None,
                        movement.get("remarks") or "Capa FIFO generada por retorno",
                        movement.get("registered_by") or "Sistema",
                        movement_at,
                    ),
                )
                hidden_entry_id = cursor.lastrowid
                tracked_available[hidden_entry_id] = available_quantity
                layer_queue.append(
                    {
                        "entry_id": hidden_entry_id,
                        "entry_folio": hidden_folio,
                        "available_quantity": available_quantity,
                        "zone_code": movement.get("zone_code")
                        or inventory.get("zone_code")
                        or inventory.get("catalog_zone_code"),
                        "location_code": movement.get("location_code"),
                        "movement_at": movement_at,
                    }
                )

            current_quantity = new_quantity
            last_return_at = movement_at
            continue

        quantity = normalize_integer(movement.get("quantity")) or 0
        previous_quantity = current_quantity
        remaining_quantity = quantity
        allocations = []

        for layer in layer_queue:
            available_quantity = normalize_integer(layer.get("available_quantity")) or 0
            if remaining_quantity <= 0:
                break
            if available_quantity <= 0:
                continue

            consumed_quantity = min(available_quantity, remaining_quantity)
            allocations.append(
                {
                    "entryId": layer["entry_id"],
                    "entryFolio": layer.get("entry_folio"),
                    "consumedQuantity": consumed_quantity,
                    "previousAvailable": available_quantity,
                    "nextAvailable": available_quantity - consumed_quantity,
                    "zoneCode": layer.get("zone_code"),
                    "locationCode": layer.get("location_code"),
                    "movementAt": serialize_datetime(layer.get("movement_at")),
                }
            )
            layer["available_quantity"] = available_quantity - consumed_quantity
            tracked_available[layer["entry_id"]] = layer["available_quantity"]
            remaining_quantity -= consumed_quantity

        new_quantity = previous_quantity - quantity
        first_allocation = allocations[0] if allocations else {}
        cursor.execute(
            f"""
            UPDATE `{SHIPPING_TABLES['exits']}`
            SET previous_quantity = %s,
                new_quantity = %s,
                fifo_allocation_json = %s,
                zone_code = %s,
                location_code = %s
            WHERE id = %s
            """,
            (
                previous_quantity,
                new_quantity,
                json_dumps_safe(allocations) if allocations else None,
                first_allocation.get("zoneCode") or movement.get("zone_code"),
                first_allocation.get("locationCode") or movement.get("location_code"),
                movement["id"],
            ),
        )

        current_quantity = new_quantity
        last_exit_at = movement_at

    for entry_id, available_quantity in tracked_available.items():
        cursor.execute(
            f"""
            UPDATE `{SHIPPING_TABLES['entries']}`
            SET available_quantity = %s
            WHERE id = %s
            """,
            (
                normalize_integer(available_quantity) or 0,
                entry_id,
            ),
        )

    update_inventory_snapshot(
        cursor,
        inventory["id"],
        {
            "current_quantity": current_quantity,
            "last_entry_at": last_entry_at,
            "last_exit_at": last_exit_at,
            "last_return_at": last_return_at,
        },
    )

    return {
        "partNumber": normalized_part,
        "currentQuantity": current_quantity,
    }


def fetch_all_embarques_parts(cursor):
    cursor.execute(
        f"""
        SELECT DISTINCT part_number
        FROM `{SHIPPING_TABLES['inventory']}`
        WHERE part_number IS NOT NULL
          AND TRIM(part_number) <> ''
        ORDER BY part_number ASC
        """
    )
    return [normalize_part_number(row.get("part_number")) for row in cursor.fetchall()]


def adjust_shipping_movement_record(
    movement_type,
    record_id,
    changes,
    adjusted_by,
    notes=None,
):
    normalized_type = normalize_movement_type(movement_type)
    if normalized_type not in {"entry", "exit", "return"}:
        return {
            "success": False,
            "error": "Tipo de movimiento no soportado",
        }, 400

    record_id_value = normalize_integer(record_id)
    if not record_id_value:
        return {
            "success": False,
            "error": "Registro de movimiento invalido",
        }, 400

    conn = None
    cursor = None

    try:
        conn = get_transaction_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        if normalized_type == "entry":
            current_row = fetch_entry_record_for_update(cursor, record_id_value)
            table_name = SHIPPING_TABLES["entries"]
            folio_field = "entry_folio"
            allowed_text_fields = {
                "product_model",
                "description",
                "customer",
                "zone_code",
                "location_code",
                "reference_code",
                "batch_no",
                "notes",
                "registered_by",
            }
            quantity_field = "quantity"
        elif normalized_type == "exit":
            current_row = fetch_exit_record_for_update(cursor, record_id_value)
            table_name = SHIPPING_TABLES["exits"]
            folio_field = "exit_folio"
            allowed_text_fields = {
                "product_model",
                "description",
                "customer",
                "zone_code",
                "location_code",
                "destination_area",
                "reason",
                "requested_by",
                "remarks",
                "registered_by",
            }
            quantity_field = "quantity"
        else:
            current_row = fetch_return_record_for_update(cursor, record_id_value)
            table_name = SHIPPING_TABLES["returns"]
            folio_field = "return_folio"
            allowed_text_fields = {
                "product_model",
                "description",
                "customer",
                "zone_code",
                "location_code",
                "reason",
                "remarks",
                "registered_by",
            }
            quantity_field = None

        if not current_row:
            conn.rollback()
            return {
                "success": False,
                "error": "El movimiento solicitado no existe",
            }, 404

        old_snapshot = build_movement_adjustment_snapshot(normalized_type, current_row)
        updated_row = {**current_row}
        update_payload = {}
        rebuild_parts = {normalize_part_number(current_row.get("part_number"))}

        if "part_number" in changes:
            next_part_number = normalize_part_number(changes.get("part_number"))
            if not next_part_number:
                conn.rollback()
                return {
                    "success": False,
                    "error": "Se requiere un numero de parte valido",
                }, 400

            if next_part_number != normalize_part_number(current_row.get("part_number")):
                next_inventory = ensure_inventory_record(cursor, next_part_number)
                if not next_inventory:
                    conn.rollback()
                    return {
                        "success": False,
                        "error": "El numero de parte no existe en el catalogo de embarques",
                    }, 404

                update_payload["part_number"] = next_part_number
                update_payload["inventory_id"] = next_inventory["id"]
                update_payload["catalog_id"] = (
                    next_inventory.get("catalog_id") or next_inventory.get("catalog_ref_id")
                )
                updated_row["part_number"] = next_part_number
                updated_row["inventory_id"] = next_inventory["id"]
                updated_row["catalog_id"] = (
                    next_inventory.get("catalog_id") or next_inventory.get("catalog_ref_id")
                )
                rebuild_parts.add(next_part_number)

        if "movement_at" in changes:
            raw_movement_at = normalize_search(changes.get("movement_at"))
            if not raw_movement_at:
                conn.rollback()
                return {
                    "success": False,
                    "error": "La fecha del movimiento es obligatoria",
                }, 400

            current_movement_at = to_sql_datetime(current_row.get("movement_at"))
            try:
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_movement_at):
                    next_date = datetime.strptime(raw_movement_at, "%Y-%m-%d")
                    next_movement_at = current_movement_at.replace(
                        year=next_date.year,
                        month=next_date.month,
                        day=next_date.day,
                    )
                else:
                    next_movement_at = to_sql_datetime(raw_movement_at)
            except ValueError:
                conn.rollback()
                return {
                    "success": False,
                    "error": "La fecha del movimiento no es valida",
                }, 400

            update_payload["movement_at"] = next_movement_at
            updated_row["movement_at"] = next_movement_at

        if normalized_type in {"entry", "exit"} and quantity_field in changes:
            next_quantity = normalize_integer(changes.get(quantity_field))
            if next_quantity is None or next_quantity <= 0:
                conn.rollback()
                return {
                    "success": False,
                    "error": "La cantidad debe ser un entero mayor a cero",
                }, 400
            update_payload[quantity_field] = next_quantity
            updated_row[quantity_field] = next_quantity

        if normalized_type == "return":
            next_return_quantity = (
                normalize_integer(changes.get("return_quantity"))
                if "return_quantity" in changes
                else normalize_integer(current_row.get("return_quantity"))
            ) or 0
            next_loss_quantity = (
                normalize_integer(changes.get("loss_quantity"))
                if "loss_quantity" in changes
                else normalize_integer(current_row.get("loss_quantity"))
            ) or 0

            if next_return_quantity <= 0:
                conn.rollback()
                return {
                    "success": False,
                    "error": "La cantidad de retorno debe ser mayor a cero",
                }, 400

            if next_loss_quantity < 0 or next_loss_quantity > next_return_quantity:
                conn.rollback()
                return {
                    "success": False,
                    "error": "La merma no puede ser mayor que la cantidad retornada",
                }, 400

            if "return_quantity" in changes:
                update_payload["return_quantity"] = next_return_quantity
                updated_row["return_quantity"] = next_return_quantity
            if "loss_quantity" in changes:
                update_payload["loss_quantity"] = next_loss_quantity
                updated_row["loss_quantity"] = next_loss_quantity

        for field_name in allowed_text_fields:
            if field_name not in changes:
                continue
            next_value = normalize_optional_text(changes.get(field_name))
            update_payload[field_name] = next_value
            updated_row[field_name] = next_value

        if normalized_type == "exit" and "departure_code" in changes:
            next_departure = normalize_departure_code(changes.get("departure_code")) or None
            update_payload["departure_code"] = next_departure
            update_payload["departure_assigned_at"] = to_sql_datetime()
            update_payload["departure_assigned_by"] = normalize_optional_text(adjusted_by) or "Sistema"
            updated_row["departure_code"] = next_departure
            updated_row["departure_assigned_at"] = update_payload["departure_assigned_at"]
            updated_row["departure_assigned_by"] = update_payload["departure_assigned_by"]

        new_snapshot = build_movement_adjustment_snapshot(normalized_type, updated_row)
        changed_fields = {
            field_name: {
                "previous": old_snapshot.get(field_name),
                "new": new_snapshot.get(field_name),
            }
            for field_name in new_snapshot.keys()
            if old_snapshot.get(field_name) != new_snapshot.get(field_name)
        }

        if not changed_fields:
            conn.rollback()
            return {
                "success": False,
                "error": "No se detectaron cambios para guardar",
            }, 400

        assignments = ", ".join([f"`{field_name}` = %s" for field_name in update_payload.keys()])
        params = list(update_payload.values()) + [record_id_value]
        cursor.execute(
            f"""
            UPDATE `{table_name}`
            SET {assignments}
            WHERE id = %s
            """,
            tuple(params),
        )

        adjusted_at = to_sql_datetime()
        insert_movement_adjustment_record(
            cursor,
            normalized_type,
            record_id_value,
            new_snapshot.get("folio"),
            new_snapshot.get("part_number"),
            old_snapshot,
            new_snapshot,
            changed_fields,
            adjusted_by,
            adjusted_at,
            notes=notes,
        )

        for rebuild_part in sorted({part for part in rebuild_parts if part}):
            rebuild_part_inventory_state(cursor, rebuild_part)

        conn.commit()
        return {
            "success": True,
            "movementType": normalized_type,
            "recordId": record_id_value,
            "folio": new_snapshot.get("folio"),
            "partNumber": new_snapshot.get("part_number"),
            "changedFields": changed_fields,
            "adjustedAt": serialize_datetime(adjusted_at),
            "adjustedBy": normalize_optional_text(adjusted_by) or "Sistema",
            "message": "Movimiento actualizado correctamente",
        }, 200
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def delete_shipping_movement_record(
    movement_type,
    record_id,
    adjusted_by,
    notes=None,
):
    normalized_type = normalize_movement_type(movement_type)
    if normalized_type not in {"entry", "exit", "return"}:
        return {
            "success": False,
            "error": "Tipo de movimiento no soportado",
        }, 400

    record_id_value = normalize_integer(record_id)
    if not record_id_value:
        return {
            "success": False,
            "error": "Registro de movimiento invalido",
        }, 400

    conn = None
    cursor = None

    try:
        conn = get_transaction_connection()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        if normalized_type == "entry":
            current_row = fetch_entry_record_for_update(cursor, record_id_value)
            table_name = SHIPPING_TABLES["entries"]
            folio_field = "entry_folio"
        elif normalized_type == "exit":
            current_row = fetch_exit_record_for_update(cursor, record_id_value)
            table_name = SHIPPING_TABLES["exits"]
            folio_field = "exit_folio"
        else:
            current_row = fetch_return_record_for_update(cursor, record_id_value)
            table_name = SHIPPING_TABLES["returns"]
            folio_field = "return_folio"

        if not current_row:
            conn.rollback()
            return {
                "success": False,
                "error": "El movimiento solicitado no existe",
            }, 404

        old_snapshot = build_movement_adjustment_snapshot(normalized_type, current_row)
        normalized_part = normalize_part_number(current_row.get("part_number"))
        deleted_folio = normalize_optional_text(current_row.get(folio_field))

        if normalized_type == "exit":
            cursor.execute(
                f"""
                DELETE FROM `{SHIPPING_TABLES['departure_history']}`
                WHERE exit_id = %s
                """,
                (record_id_value,),
            )
            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['exits']}`
                SET split_from_exit_id = NULL
                WHERE split_from_exit_id = %s
                """,
                (record_id_value,),
            )
            cursor.execute(
                f"""
                UPDATE `{SHIPPING_TABLES['exits']}`
                SET split_root_exit_id = NULL
                WHERE split_root_exit_id = %s
                """,
                (record_id_value,),
            )

        cursor.execute(
            f"""
            DELETE FROM `{table_name}`
            WHERE id = %s
            """,
            (record_id_value,),
        )

        if cursor.rowcount <= 0:
            conn.rollback()
            return {
                "success": False,
                "error": "No fue posible eliminar el movimiento solicitado",
            }, 500

        adjusted_at = to_sql_datetime()
        insert_movement_adjustment_record(
            cursor,
            normalized_type,
            record_id_value,
            deleted_folio,
            normalized_part,
            old_snapshot,
            {},
            {"deleted": True},
            adjusted_by,
            adjusted_at,
            notes=notes,
            adjustment_action="delete",
        )

        if normalized_part:
            rebuild_part_inventory_state(cursor, normalized_part)

        conn.commit()
        return {
            "success": True,
            "movementType": normalized_type,
            "recordId": record_id_value,
            "folio": deleted_folio,
            "partNumber": normalized_part,
            "adjustedAt": serialize_datetime(adjusted_at),
            "adjustedBy": normalize_optional_text(adjusted_by) or "Sistema",
            "message": "Movimiento eliminado correctamente",
        }, 200
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
            "departure_code",
            "departure_assigned_by",
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
              departure_code,
              departure_assigned_at,
              departure_assigned_by,
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
        departure_code = normalize_departure_code(
            data.get("departureCode") or data.get("departure")
        )

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
              departure_code,
              departure_assigned_at,
              departure_assigned_by,
              reason,
              requested_by,
              remarks,
              registered_by,
              movement_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                departure_code or None,
                movement_at if departure_code else None,
                (
                    normalize_search(data.get("registeredBy"))
                    or normalize_search(data.get("userName"))
                    or "Usuario local"
                )
                if departure_code
                else None,
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
        if departure_code:
            insert_departure_history_record(
                cursor,
                {
                    "id": record_id,
                    "exit_folio": exit_folio,
                    "inventory_id": inventory["id"],
                    "catalog_id": inventory.get("catalog_id")
                    or inventory.get("catalog_ref_id"),
                    "part_number": inventory["part_number"],
                    "quantity": quantity,
                    "product_model": inventory.get("product_model")
                    or inventory.get("catalog_model"),
                    "customer": inventory.get("customer")
                    or inventory.get("catalog_customer"),
                    "destination_area": normalize_search(data.get("destinationArea"))
                    or normalize_search(data.get("department"))
                    or "Embarques",
                    "departure_code": None,
                    "reason": normalize_search(data.get("reason"))
                    or normalize_search(data.get("process"))
                    or "Salida de producto terminado",
                },
                departure_code,
                normalize_search(data.get("registeredBy"))
                or normalize_search(data.get("userName"))
                or "Usuario local",
                movement_at,
                notes=normalize_search(data.get("remarks")) or None,
            )
        conn.commit()
        return jsonify(
            {
                "success": True,
                "id": record_id,
                "folio": exit_folio,
                "departureCode": departure_code or None,
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


@shipping_material_api.route("/exits/<int:exit_id>/departure", methods=["POST", "PUT", "PATCH"])
@manejo_errores
def assign_exit_departure():
    data = request.get_json(silent=True) or {}
    payload, status_code = assign_exit_departure_value(
        exit_id,
        data.get("departureCode") or data.get("departure"),
        data.get("assignedBy") or data.get("registeredBy") or "Sistema",
        departure_quantity=(
            data.get("departureQuantity")
            if data.get("departureQuantity") is not None
            else data.get("quantity")
        ),
        notes=data.get("notes"),
        assigned_at=data.get("assignedAt"),
    )
    return jsonify(payload), status_code


@shipping_material_api.route("/departures/history", methods=["GET"])
@manejo_errores
def list_departure_history():
    payload = get_departure_history_records(
        limit=request.args.get("limit"),
        departure_code=request.args.get("departureCode") or request.args.get("departure"),
        exit_id=request.args.get("exitId"),
    )
    return jsonify(payload)


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
