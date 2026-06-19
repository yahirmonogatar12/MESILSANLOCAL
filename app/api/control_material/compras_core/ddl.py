"""DDL idempotente para Lista de compras y costeo por transaccion.

Reusa los helpers de invoice_core/ddl (mismo patron SHOW COLUMNS/INDEX). Aqui:
- 2 tablas nuevas (cargas + lineas) para el registro de compras.
- columna numero_transaccion en control_material_almacen (la entrada de almacen
  puede referenciar una transaccion de compra para fijar el costo del lote).
- amplia el ENUM fuente_costo de inventario_lote_costos con 'LISTA_COMPRAS'.
"""

from app.db_mysql import execute_query
from app.api.control_material.invoice_core.ddl import (
    _ddl_fetch_one,
    _ensure_column,
    _ensure_index,
)


def _ensure_transaccion_column():
    """numero_transaccion en control_material_almacen (entrada -> costo por compra)."""
    _ensure_column(
        "control_material_almacen",
        "numero_transaccion",
        "numero_transaccion VARCHAR(255) NULL",
    )
    _ensure_index(
        "control_material_almacen",
        "idx_cma_transaccion",
        "KEY idx_cma_transaccion (numero_transaccion)",
    )


def _ensure_fuente_costo_lista_compras():
    """Agrega 'LISTA_COMPRAS' al ENUM fuente_costo si aun no esta.

    Se hace condicional leyendo INFORMATION_SCHEMA para que el ALTER de la tabla
    compartida solo corra una vez (idempotente). Orden: INVOICE y LISTA_COMPRAS
    son costos reales (es_estimado=0); CONTROL_MATERIAL/SIN_COSTO estimados.
    """
    row = _ddl_fetch_one(
        """
        SELECT COLUMN_TYPE
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'inventario_lote_costos'
          AND COLUMN_NAME = 'fuente_costo'
        """
    )
    column_type = (row or {}).get("COLUMN_TYPE") or ""
    if "LISTA_COMPRAS" in column_type:
        return
    execute_query(
        """
        ALTER TABLE inventario_lote_costos
        MODIFY COLUMN fuente_costo
        ENUM('INVOICE','LISTA_COMPRAS','CONTROL_MATERIAL','SIN_COSTO')
        NOT NULL DEFAULT 'SIN_COSTO'
        """
    )


def init_lista_compras_tables():
    """Crea/actualiza tablas y columnas de Lista de compras."""
    _ensure_transaccion_column()
    _ensure_fuente_costo_lista_compras()

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lista_compras_cargas (
            id BIGINT NOT NULL AUTO_INCREMENT,
            tipo VARCHAR(20) NOT NULL DEFAULT '',
            modo ENUM('INICIAL','ACTUALIZACION') NOT NULL DEFAULT 'ACTUALIZACION',
            archivo_nombre VARCHAR(255) NULL,
            archivo_ruta VARCHAR(512) NULL,
            archivo_size BIGINT NULL,
            archivo_mime VARCHAR(120) NULL,
            archivo_hash_sha256 VARCHAR(64) NOT NULL,
            total_transacciones INT NOT NULL DEFAULT 0,
            total_lineas INT NOT NULL DEFAULT 0,
            total_monto DECIMAL(18,4) NOT NULL DEFAULT 0,
            usuario_carga VARCHAR(255) NOT NULL DEFAULT 'SISTEMA',
            fecha_carga DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uk_compras_file_hash (archivo_hash_sha256),
            KEY idx_compras_cargas_tipo (tipo),
            KEY idx_compras_cargas_fecha (fecha_carga)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    _ensure_column(
        "lista_compras_cargas",
        "modo",
        "modo ENUM('INICIAL','ACTUALIZACION') NOT NULL DEFAULT 'ACTUALIZACION'",
    )

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lista_compras_lineas (
            id BIGINT NOT NULL AUTO_INCREMENT,
            carga_id BIGINT NOT NULL,
            tipo VARCHAR(20) NOT NULL DEFAULT '',
            numero_transaccion VARCHAR(255) NOT NULL,
            estado ENUM('ABIERTA','CERRADA','APLICADA') NOT NULL DEFAULT 'ABIERTA',
            anio INT NULL,
            mes VARCHAR(20) NULL,
            fecha_compra DATE NULL,
            wk VARCHAR(20) NULL,
            raw_part_num VARCHAR(512) NULL,
            numero_parte VARCHAR(512) NOT NULL,
            numero_parte_sistema VARCHAR(512) NOT NULL,
            descripcion VARCHAR(1024) NULL,
            spec VARCHAR(512) NULL,
            cantidad DECIMAL(18,4) NOT NULL DEFAULT 0,
            moneda VARCHAR(10) NOT NULL DEFAULT 'USD',
            costo_unitario DECIMAL(12,4) NULL,
            costo_total DECIMAL(18,4) NULL,
            fecha_factura DATE NULL,
            proveedor VARCHAR(255) NULL,
            factura VARCHAR(255) NULL,
            modelo VARCHAR(255) NULL,
            categoria VARCHAR(50) NULL,
            comentario VARCHAR(512) NULL,
            estado_match ENUM('DIRECTO','SIN_ALIAS') NOT NULL DEFAULT 'SIN_ALIAS',
            mensaje_match VARCHAR(255) NULL,
            PRIMARY KEY (id),
            KEY idx_lcl_carga (carga_id),
            KEY idx_lcl_transaccion (numero_transaccion),
            KEY idx_lcl_tipo (tipo),
            KEY idx_lcl_estado (tipo, estado),
            KEY idx_lcl_trans_parte (numero_transaccion, numero_parte_sistema(120))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    # estado por parte: ABIERTA aparece en el selector y se va llenando con cada
    # entrada; APLICADA = llegó al tope (cantidad comprada) y sale del selector;
    # CERRADA = histórico (carga inicial), oculto, solo para costear.
    _ensure_column(
        "lista_compras_lineas",
        "estado",
        "estado ENUM('ABIERTA','CERRADA','APLICADA') NOT NULL DEFAULT 'ABIERTA'",
    )
    # Si la columna ya existía con el enum viejo (sin APLICADA), amplíalo.
    estado_row = _ddl_fetch_one(
        """
        SELECT COLUMN_TYPE FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'lista_compras_lineas'
          AND COLUMN_NAME = 'estado'
        """
    )
    if "APLICADA" not in ((estado_row or {}).get("COLUMN_TYPE") or ""):
        execute_query(
            "ALTER TABLE lista_compras_lineas MODIFY COLUMN estado "
            "ENUM('ABIERTA','CERRADA','APLICADA') NOT NULL DEFAULT 'ABIERTA'"
        )
    _ensure_index(
        "lista_compras_lineas",
        "idx_lcl_estado",
        "KEY idx_lcl_estado (tipo, estado)",
    )

    # Vínculo lote ↔ línea de transacción (espejo de material_invoice_lot_links).
    # Cada lote recibido se aplica contra una parte de la transacción y acumula
    # hasta el tope. activo_key (único) garantiza 1 transacción activa por lote.
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lista_compras_lot_links (
            id BIGINT NOT NULL AUTO_INCREMENT,
            transaccion_linea_id BIGINT NOT NULL,
            numero_transaccion VARCHAR(255) NOT NULL,
            tipo VARCHAR(20) NOT NULL DEFAULT '',
            codigo_material_recibido VARCHAR(255) NOT NULL,
            numero_parte_sistema VARCHAR(512) NOT NULL,
            cantidad_aplicada DECIMAL(18,4) NOT NULL DEFAULT 0,
            costo_unitario DECIMAL(12,4) NULL,
            moneda VARCHAR(10) NOT NULL DEFAULT 'USD',
            usuario_aplicacion VARCHAR(255) NOT NULL DEFAULT 'SISTEMA',
            fecha_aplicacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            estado ENUM('APLICADO','DESAPLICADO') NOT NULL DEFAULT 'APLICADO',
            fecha_desaplicado DATETIME NULL,
            usuario_desaplicado VARCHAR(255) NULL,
            activo_key VARCHAR(255) GENERATED ALWAYS AS (
                CASE WHEN estado = 'APLICADO' THEN codigo_material_recibido ELSE NULL END
            ) STORED,
            PRIMARY KEY (id),
            UNIQUE KEY uk_lcll_activo (activo_key),
            KEY idx_lcll_linea (transaccion_linea_id),
            KEY idx_lcll_transaccion (numero_transaccion),
            KEY idx_lcll_codigo (codigo_material_recibido)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
