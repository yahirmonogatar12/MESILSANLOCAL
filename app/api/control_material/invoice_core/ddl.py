"""DDL idempotente para invoices, packing, links y valorizacion."""

from app.db_mysql import execute_query

def _ddl_fetch_one(sql, params=None):
    return execute_query(sql, params, fetch="one")


def _ensure_column(table, name, definition):
    exists = _ddl_fetch_one(f"SHOW COLUMNS FROM {table} LIKE %s", (name,))
    if not exists:
        execute_query(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _ensure_index(table, key_name, definition):
    exists = _ddl_fetch_one(f"SHOW INDEX FROM {table} WHERE Key_name = %s", (key_name,))
    if not exists:
        execute_query(f"ALTER TABLE {table} ADD {definition}")


def _index_columns(table, key_name):
    rows = execute_query(
        f"SHOW INDEX FROM {table} WHERE Key_name = %s",
        (key_name,),
        fetch="all",
    ) or []
    ordered = sorted(rows, key=lambda row: int(row.get("Seq_in_index") or 0))
    return [row.get("Column_name") for row in ordered]


def _drop_index_if_exists(table, key_name):
    exists = _ddl_fetch_one(f"SHOW INDEX FROM {table} WHERE Key_name = %s", (key_name,))
    if exists:
        execute_query(f"ALTER TABLE {table} DROP INDEX {key_name}")

def _ensure_control_material_columns():
    """Asegura columnas e índices usados por invoice/pallet en control_material_almacen."""
    columnas = (
        ("pallet_no_original", "pallet_no_original VARCHAR(50) NULL"),
        ("pallet_no", "pallet_no VARCHAR(50) NULL"),
        ("vendedor", "vendedor VARCHAR(100) NULL"),
    )

    for name, definition in columnas:
        _ensure_column("control_material_almacen", name, definition)

    _ensure_index(
        "control_material_almacen",
        "idx_cma_invoice_pallet",
        "KEY idx_cma_invoice_pallet (numero_invoice, pallet_no)",
    )

    _ensure_index(
        "control_material_almacen",
        "idx_cma_parte_vendedor_fecha",
        "KEY idx_cma_parte_vendedor_fecha (numero_parte(191), vendedor, fecha_recibo)",
    )

def init_material_invoice_tables():
    """Crea/actualiza tablas para invoice, packing, links y valorizacion."""
    _ensure_control_material_columns()

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS material_invoices (
            id BIGINT NOT NULL AUTO_INCREMENT,
            numero_invoice VARCHAR(255) NOT NULL,
            tipo VARCHAR(255) NULL,
            archivo_nombre VARCHAR(255) NULL,
            archivo_ruta VARCHAR(512) NULL,
            archivo_size BIGINT NULL,
            archivo_mime VARCHAR(120) NULL,
            archivo_hash_sha256 VARCHAR(64) NOT NULL,
            estado ENUM(
                'BORRADOR',
                'VALIDADA',
                'CON_DIFERENCIAS',
                'PARCIALMENTE_APLICADA',
                'APLICADA',
                'CANCELADA'
            ) NOT NULL DEFAULT 'BORRADOR',
            moneda VARCHAR(10) NOT NULL DEFAULT 'USD',
            total_lineas INT NOT NULL DEFAULT 0,
            total_packing INT NOT NULL DEFAULT 0,
            total_monto DECIMAL(18,4) NOT NULL DEFAULT 0,
            observaciones TEXT NULL,
            usuario_carga VARCHAR(255) NOT NULL DEFAULT 'SISTEMA',
            fecha_carga DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            usuario_validacion VARCHAR(255) NULL,
            fecha_validacion DATETIME NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uk_invoice_numero (numero_invoice),
            UNIQUE KEY uk_invoice_file_hash (archivo_hash_sha256),
            KEY idx_material_invoices_estado (estado),
            KEY idx_material_invoices_fecha (fecha_carga)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    invoice_columns = (
        ("tipo", "tipo VARCHAR(255) NULL"),
        ("archivo_ruta", "archivo_ruta VARCHAR(512) NULL"),
        ("archivo_size", "archivo_size BIGINT NULL"),
        ("archivo_mime", "archivo_mime VARCHAR(120) NULL"),
        ("archivo_hash_sha256", "archivo_hash_sha256 VARCHAR(64) NOT NULL"),
        ("usuario_validacion", "usuario_validacion VARCHAR(255) NULL"),
        ("fecha_validacion", "fecha_validacion DATETIME NULL"),
    )
    for name, definition in invoice_columns:
        _ensure_column("material_invoices", name, definition)
    invoice_proveedor_col = _ddl_fetch_one("SHOW COLUMNS FROM material_invoices LIKE %s", ("proveedor",))
    if invoice_proveedor_col:
        execute_query(
            """
            UPDATE material_invoices
            SET tipo = proveedor
            WHERE (tipo IS NULL OR tipo = '')
              AND proveedor IS NOT NULL
              AND proveedor <> ''
            """
        )
        execute_query("ALTER TABLE material_invoices DROP COLUMN proveedor")
    _ensure_index("material_invoices", "uk_invoice_numero", "UNIQUE KEY uk_invoice_numero (numero_invoice)")
    _ensure_index("material_invoices", "uk_invoice_file_hash", "UNIQUE KEY uk_invoice_file_hash (archivo_hash_sha256)")

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS material_invoice_lines (
            id BIGINT NOT NULL AUTO_INCREMENT,
            invoice_id BIGINT NOT NULL,
            line_no INT NOT NULL DEFAULT 0,
            maker VARCHAR(255) NULL,
            origin VARCHAR(255) NULL,
            raw_part_num VARCHAR(512) NULL,
            numero_parte_invoice VARCHAR(512) NOT NULL,
            numero_parte_sistema VARCHAR(512) NOT NULL,
            descripcion VARCHAR(1024) NULL,
            cantidad DECIMAL(18,4) NOT NULL DEFAULT 0,
            uom VARCHAR(50) NULL,
            costo_unitario DECIMAL(12,4) NOT NULL DEFAULT 0,
            costo_total DECIMAL(18,4) NOT NULL DEFAULT 0,
            moneda VARCHAR(10) NOT NULL DEFAULT 'USD',
            raw_qty VARCHAR(100) NULL,
            raw_unit_cost VARCHAR(100) NULL,
            raw_total_cost VARCHAR(100) NULL,
            estado_match ENUM('PENDIENTE','DIRECTO','ALIAS','SIN_ALIAS','DIFERENCIA') NOT NULL DEFAULT 'PENDIENTE',
            mensaje_match VARCHAR(255) NULL,
            PRIMARY KEY (id),
            KEY idx_mil_invoice (invoice_id),
            KEY idx_mil_parte_sistema (numero_parte_sistema(191))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    for name, definition in (
        ("raw_part_num", "raw_part_num VARCHAR(512) NULL"),
        ("raw_qty", "raw_qty VARCHAR(100) NULL"),
        ("raw_unit_cost", "raw_unit_cost VARCHAR(100) NULL"),
        ("raw_total_cost", "raw_total_cost VARCHAR(100) NULL"),
    ):
        _ensure_column("material_invoice_lines", name, definition)

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS material_invoice_packing_lines (
            id BIGINT NOT NULL AUTO_INCREMENT,
            invoice_id BIGINT NOT NULL,
            invoice_line_id BIGINT NULL,
            line_no INT NOT NULL DEFAULT 0,
            packing_no VARCHAR(100) NULL,
            raw_part_num VARCHAR(512) NULL,
            numero_parte_packing VARCHAR(512) NOT NULL,
            numero_parte_sistema VARCHAR(512) NOT NULL,
            descripcion VARCHAR(1024) NULL,
            cantidad_packing DECIMAL(18,4) NOT NULL DEFAULT 0,
            raw_qty VARCHAR(100) NULL,
            pallet_no_original VARCHAR(50) NULL,
            pallet_no VARCHAR(50) NULL,
            kg DECIMAL(18,4) NULL,
            cbm DECIMAL(18,4) NULL,
            estado_match ENUM('PENDIENTE','MATCH','SIN_ALIAS','SIN_LINEA','DIFERENCIA','APLICADA_PARCIAL','APLICADA') NOT NULL DEFAULT 'PENDIENTE',
            mensaje_match VARCHAR(255) NULL,
            PRIMARY KEY (id),
            KEY idx_mipl_invoice (invoice_id),
            KEY idx_mipl_line (invoice_line_id),
            KEY idx_mipl_pallet_part (pallet_no, numero_parte_sistema(191))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    for name, definition in (
        ("pallet_no_original", "pallet_no_original VARCHAR(50) NULL"),
        ("pallet_no", "pallet_no VARCHAR(50) NULL"),
        ("estado_match", "estado_match ENUM('PENDIENTE','MATCH','SIN_ALIAS','SIN_LINEA','DIFERENCIA','APLICADA_PARCIAL','APLICADA') NOT NULL DEFAULT 'PENDIENTE'"),
    ):
        _ensure_column("material_invoice_packing_lines", name, definition)


    execute_query(
        """
        CREATE TABLE IF NOT EXISTS material_invoice_lot_links (
            id BIGINT NOT NULL AUTO_INCREMENT,
            invoice_id BIGINT NOT NULL,
            invoice_line_id BIGINT NOT NULL,
            packing_line_id BIGINT NULL,
            codigo_material_recibido VARCHAR(255) NOT NULL,
            numero_parte_sistema VARCHAR(512) NOT NULL,
            cantidad_aplicada DECIMAL(18,4) NOT NULL DEFAULT 0,
            costo_unitario DECIMAL(12,4) NOT NULL DEFAULT 0,
            moneda VARCHAR(10) NOT NULL DEFAULT 'USD',
            usuario_aplicacion VARCHAR(255) NOT NULL DEFAULT 'SISTEMA',
            fecha_aplicacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            usuario_registro VARCHAR(255) NOT NULL DEFAULT 'SISTEMA',
            fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            estado ENUM('APLICADO','DESAPLICADO') NOT NULL DEFAULT 'APLICADO',
            fecha_desaplicado DATETIME NULL,
            usuario_desaplicado VARCHAR(255) NULL,
            motivo_desaplicado VARCHAR(255) NULL,
            activo_key VARCHAR(255) GENERATED ALWAYS AS (
                CASE
                    WHEN estado = 'APLICADO' THEN codigo_material_recibido
                    ELSE NULL
                END
            ) STORED,
            PRIMARY KEY (id),
            UNIQUE KEY uk_lote_link_activo (activo_key),
            KEY idx_invoice_lot_invoice (invoice_id),
            KEY idx_invoice_lot_codigo (codigo_material_recibido),
            KEY idx_invoice_lot_packing (packing_line_id),
            KEY idx_invoice_lot_estado_fecha (estado, fecha_aplicacion, id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    for name, definition in (
        ("fecha_aplicacion", "fecha_aplicacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ("usuario_aplicacion", "usuario_aplicacion VARCHAR(255) NOT NULL DEFAULT 'SISTEMA'"),
        ("motivo_desaplicado", "motivo_desaplicado VARCHAR(255) NULL"),
    ):
        _ensure_column("material_invoice_lot_links", name, definition)
    if not _ddl_fetch_one("SHOW COLUMNS FROM material_invoice_lot_links LIKE %s", ("activo_key",)):
        execute_query(
            """
            ALTER TABLE material_invoice_lot_links
            ADD COLUMN activo_key VARCHAR(255)
            GENERATED ALWAYS AS (
                CASE
                    WHEN estado = 'APLICADO' THEN codigo_material_recibido
                    ELSE NULL
                END
            ) STORED
            """
        )
    _ensure_index("material_invoice_lot_links", "uk_lote_link_activo", "UNIQUE KEY uk_lote_link_activo (activo_key)")

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS inventario_lote_costos (
            id BIGINT NOT NULL AUTO_INCREMENT,
            codigo_material_recibido VARCHAR(255) NOT NULL,
            numero_parte_sistema VARCHAR(512) NOT NULL,
            numero_lote VARCHAR(255) NULL,
            pallet_no_original VARCHAR(50) NULL,
            pallet_no VARCHAR(50) NULL,
            vendedor VARCHAR(100) NULL,
            cantidad_lote DECIMAL(18,4) NOT NULL DEFAULT 0,
            stock_actual DECIMAL(18,4) NOT NULL DEFAULT 0,
            costo_unitario DECIMAL(12,4) NOT NULL DEFAULT 0,
            moneda VARCHAR(10) NOT NULL DEFAULT 'USD',
            fuente_costo ENUM('INVOICE','CONTROL_MATERIAL','SIN_COSTO') NOT NULL DEFAULT 'SIN_COSTO',
            es_estimado TINYINT NOT NULL DEFAULT 1,
            invoice_id BIGINT NULL,
            invoice_line_id BIGINT NULL,
            packing_line_id BIGINT NULL,
            link_id BIGINT NULL,
            usuario_registro VARCHAR(255) NOT NULL DEFAULT 'SISTEMA',
            fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uk_ilc_codigo (codigo_material_recibido),
            KEY idx_ilc_parte (numero_parte_sistema(191)),
            KEY idx_ilc_pallet (pallet_no),
            KEY idx_ilc_fuente (fuente_costo),
            KEY idx_ilc_invoice (invoice_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    for name, definition in (
        ("pallet_no_original", "pallet_no_original VARCHAR(50) NULL"),
        ("pallet_no", "pallet_no VARCHAR(50) NULL"),
        ("link_id", "link_id BIGINT NULL"),
    ):
        _ensure_column("inventario_lote_costos", name, definition)

