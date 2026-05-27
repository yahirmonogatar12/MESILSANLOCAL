"""Data backend for the Control BOM Blueprint and ECO KS publication."""

from datetime import datetime, timedelta
import re
import unicodedata

from app.db_mysql import execute_query, get_connection

# === FUNCIONES DE ECOs / CAMBIOS DE INGENIERIA ===

def crear_tablas_ecos():
    """Crear tablas y vista canonica para ECOs aprobados."""
    try:
        for legacy_view in (
            'v_mes_ico_bom_items',
            'v_icos_with_ks_ecn',
            'v_icos_historial_unificado',
        ):
            _eco_drop_view_if_exists(legacy_view)

        execute_query("""
            CREATE TABLE IF NOT EXISTS engineering_changes (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                eco_no VARCHAR(64) NOT NULL,
                part_no VARCHAR(100) NOT NULL,
                bom_revision VARCHAR(64) NOT NULL,
                effective_at DATETIME NOT NULL,
                status ENUM('DRAFT','APPROVED','CANCELLED') NOT NULL DEFAULT 'DRAFT',
                notes TEXT NULL,
                created_by VARCHAR(100) NULL,
                approved_by VARCHAR(100) NULL,
                created_at DATETIME DEFAULT NOW(),
                approved_at DATETIME NULL,
                updated_at DATETIME DEFAULT NOW(),
                UNIQUE KEY uk_engineering_change (eco_no, part_no, bom_revision),
                INDEX idx_eng_part_status_effective (part_no, status, effective_at),
                INDEX idx_eng_status_effective (status, effective_at),
                INDEX idx_eng_eco_no (eco_no)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        _eco_rename_column_if_exists(
            'engineering_changes',
            'ico_no',
            'eco_no',
            'eco_no VARCHAR(64) NOT NULL'
        )
        _eco_rename_index_if_exists('engineering_changes', 'idx_eng_ico_no', 'idx_eng_eco_no')
        _eco_add_index_if_missing('engineering_changes', 'idx_eng_eco_no', '(eco_no)')

        execute_query("""
            CREATE TABLE IF NOT EXISTS engineering_change_bom_items (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                engineering_change_id BIGINT NOT NULL,
                tipo_material VARCHAR(32) NOT NULL DEFAULT 'MAIN',
                posicion_assy VARCHAR(64) NOT NULL,
                location_text TEXT NULL,
                material_code VARCHAR(128) NOT NULL,
                numero_parte VARCHAR(128) NOT NULL,
                qty DECIMAL(10,4) NOT NULL DEFAULT 1,
                ubicacion TEXT NULL,
                proveedor VARCHAR(255) NULL,
                side VARCHAR(50) NULL,
                classification VARCHAR(100) NULL,
                spec TEXT NULL,
                created_at DATETIME DEFAULT NOW(),
                INDEX idx_ec_items_change (engineering_change_id),
                INDEX idx_ec_items_material (material_code),
                INDEX idx_ec_items_position (posicion_assy)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)

        _eco_modify_column_if_needed(
            'engineering_change_bom_items',
            'ubicacion',
            'ubicacion TEXT NULL',
            ('text', 'mediumtext', 'longtext')
        )

        extra_columns = [
            ('location_text', 'location_text TEXT NULL AFTER posicion_assy'),
            ('bom_level', 'bom_level VARCHAR(32) NULL'),
            ('item_seq', 'item_seq VARCHAR(64) NULL'),
            ('item_name', 'item_name VARCHAR(255) NULL'),
            ('item_name_en', 'item_name_en VARCHAR(255) NULL'),
            ('unit', 'unit VARCHAR(32) NULL'),
            ('maker', 'maker VARCHAR(255) NULL'),
            ('process_name', 'process_name VARCHAR(100) NULL'),
            ('item_process', 'item_process VARCHAR(100) NULL'),
            ('item_class', 'item_class VARCHAR(100) NULL'),
            ('valid_from', 'valid_from DATE NULL'),
            ('valid_to', 'valid_to DATE NULL'),
            ('status_name', "status_name VARCHAR(32) NULL DEFAULT '사용'"),
            ('is_alternate', 'is_alternate TINYINT(1) NOT NULL DEFAULT 0'),
            ('alt_item_no', 'alt_item_no VARCHAR(128) NULL'),
            ('alt_item_name', 'alt_item_name VARCHAR(255) NULL'),
            ('alt_spec', 'alt_spec TEXT NULL'),
            ('alt_maker', 'alt_maker VARCHAR(255) NULL'),
            ('child_bom_part_no', 'child_bom_part_no VARCHAR(128) NULL'),
            ('is_sub_bom', 'is_sub_bom TINYINT(1) NOT NULL DEFAULT 0'),
            ('remark', 'remark TEXT NULL'),
            ('item_remark', 'item_remark TEXT NULL'),
        ]
        for column_name, column_definition in extra_columns:
            _eco_add_column_if_missing('engineering_change_bom_items', column_name, column_definition)

        eco_bridge_columns = [
            ('ks_family_prefix', 'ks_family_prefix VARCHAR(128) NULL'),
            ('ks_hist_seq', 'ks_hist_seq BIGINT NULL'),
            ('item_name', 'item_name VARCHAR(255) NULL'),
        ]
        for column_name, column_definition in eco_bridge_columns:
            _eco_add_column_if_missing('engineering_changes', column_name, column_definition)

        execute_query("""
            CREATE TABLE IF NOT EXISTS engineering_change_diff (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                engineering_change_id BIGINT NOT NULL,
                action ENUM('ADD','REMOVE','MODIFY') NOT NULL,
                item_no VARCHAR(128) NULL,
                bom_level VARCHAR(64) NULL,
                ks_row_id BIGINT NULL,
                field_changed VARCHAR(64) NULL,
                old_value TEXT NULL,
                new_value TEXT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ecd_change (engineering_change_id),
                INDEX idx_ecd_action (engineering_change_id, action),
                INDEX idx_ecd_item (engineering_change_id, item_no)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        _eco_add_column_if_missing(
            'engineering_change_diff', 'part_no',
            'part_no VARCHAR(128) NULL AFTER engineering_change_id'
        )
        _eco_add_index_if_missing(
            'engineering_change_diff', 'idx_ecd_part',
            '(engineering_change_id, part_no)'
        )

        execute_query("""
            CREATE TABLE IF NOT EXISTS engineering_change_scope (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                engineering_change_id BIGINT NOT NULL,
                part_no VARCHAR(128) NOT NULL,
                family_prefix VARCHAR(128) NULL,
                bom_revision VARCHAR(64) NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_ecs_change_part (engineering_change_id, part_no),
                INDEX idx_ecs_change (engineering_change_id),
                INDEX idx_ecs_family (family_prefix)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)

        _eco_add_column_if_missing(
            'engineering_changes', 'scope_kind',
            "scope_kind ENUM('SINGLE','FAMILY') NOT NULL DEFAULT 'SINGLE'"
        )
        _eco_add_column_if_missing(
            'engineering_changes', 'family_prefix',
            'family_prefix VARCHAR(128) NULL'
        )
        _eco_add_index_if_missing(
            'engineering_changes',
            'idx_eng_ks_ecn',
            '(ks_family_prefix, ks_hist_seq)'
        )

        execute_query("""
            CREATE OR REPLACE VIEW v_ecos_bom_current AS
            SELECT
                h.part_no AS bom_part_no,
                h.root_part_no AS root_part_no,
                h.family_prefix AS family_prefix,
                h.bom_suffix AS bom_suffix,
                h.bom_kind AS bom_kind,
                h.bom_rev AS bom_rev,
                h.item_seq AS parent_item_seq,
                h.item_name AS parent_item_name,
                h.spec AS parent_spec,
                c.bom_level AS bom_level,
                c.item_seq AS item_seq,
                c.item_no AS item_no,
                c.item_name AS item_name,
                c.item_name_en AS item_name_en,
                c.spec AS spec,
                c.qty AS qty,
                c.unit AS unit,
                c.location_text AS location_text,
                c.maker AS maker,
                c.process_name AS process_name,
                c.item_process AS item_process,
                c.price AS price,
                c.rep_price AS rep_price,
                c.amt AS amt,
                c.pur_price AS pur_price,
                c.pur_amt AS pur_amt,
                c.supplier AS supplier,
                c.currency AS currency,
                c.stock_qty AS stock_qty,
                c.asset_name AS asset_name,
                c.item_class AS item_class,
                c.valid_from AS valid_from,
                c.valid_to AS valid_to,
                c.status_name AS status_name,
                c.is_alternate AS is_alternate,
                c.alt_item_no AS alt_item_no,
                c.alt_item_name AS alt_item_name,
                c.alt_spec AS alt_spec,
                c.alt_maker AS alt_maker,
                c.remark AS remark,
                c.item_remark AS item_remark,
                c.child_bom_part_no AS child_bom_part_no,
                c.is_sub_bom AS is_sub_bom,
                h.synced_at AS header_synced_at,
                c.synced_at AS component_synced_at
            FROM ks_bom_headers h
            JOIN ks_bom_components c
              ON c.parent_part_no = h.part_no
             AND c.bom_rev = h.bom_rev
        """)
        _eco_drop_view_if_exists('v_icos_bom_current')

        execute_query("""
            CREATE OR REPLACE VIEW v_mes_eco_bom_items AS
            SELECT
                ec.id AS engineering_change_id,
                ec.eco_no,
                ec.part_no,
                ec.bom_revision,
                ec.effective_at,
                ec.status,
                ec.updated_at AS source_updated_at,
                i.id AS item_id,
                UPPER(COALESCE(NULLIF(i.tipo_material, ''), 'MAIN')) AS tipo_material,
                i.posicion_assy,
                COALESCE(NULLIF(i.location_text, ''), i.ubicacion, i.posicion_assy) AS location_text,
                COALESCE(NULLIF(i.material_code, ''), i.numero_parte) AS material_code,
                COALESCE(NULLIF(i.numero_parte, ''), i.material_code) AS numero_parte,
                i.qty,
                i.ubicacion,
                i.proveedor,
                i.side,
                i.classification,
                i.spec,
                i.bom_level,
                i.item_seq,
                i.item_name,
                i.item_name_en,
                i.unit,
                i.maker,
                i.process_name,
                i.item_process,
                i.item_class,
                i.valid_from,
                i.valid_to,
                i.status_name,
                i.is_alternate,
                i.alt_item_no,
                i.alt_item_name,
                i.alt_spec,
                i.alt_maker,
                i.child_bom_part_no,
                i.is_sub_bom
            FROM engineering_changes ec
            INNER JOIN engineering_change_bom_items i
                ON i.engineering_change_id = ec.id
            WHERE ec.status = 'APPROVED'
        """)

        execute_query("""
            CREATE OR REPLACE VIEW v_ecos_with_ks_ecn AS
            SELECT
                ec.id              AS eco_id,
                ec.eco_no,
                ec.part_no,
                ec.bom_revision,
                ec.effective_at,
                ec.status,
                ec.created_by,
                ec.approved_by,
                ec.approved_at,
                ec.ks_family_prefix,
                ec.ks_hist_seq,
                ke.family_prefix   AS ecn_family_prefix,
                ke.hist_seq        AS ecn_hist_seq,
                ke.item_no         AS ecn_item_no,
                ke.item_seq        AS ecn_item_seq,
                ke.sb_date         AS ecn_sb_date,
                ke.work_no         AS ecn_work_no,
                ke.chg_remark      AS ecn_chg_remark,
                ke.cause           AS ecn_cause,
                ke.step_result     AS ecn_step_result,
                ke.bom_emp_name    AS ecn_bom_emp_name,
                ke.dev_emp_name    AS ecn_dev_emp_name,
                ke.synced_at       AS ecn_synced_at
            FROM engineering_changes ec
            LEFT JOIN ks_engineering_changes ke
                ON ke.family_prefix = ec.ks_family_prefix COLLATE utf8mb4_0900_ai_ci
               AND ke.hist_seq      = ec.ks_hist_seq
        """)

        execute_query("""
            CREATE OR REPLACE VIEW v_ecos_historial_unificado AS
            SELECT
                CAST(ec.id AS CHAR) COLLATE utf8mb4_0900_ai_ci AS id,
                ec.eco_no               COLLATE utf8mb4_0900_ai_ci AS eco_no,
                ec.part_no              COLLATE utf8mb4_0900_ai_ci AS part_no,
                ec.bom_revision         COLLATE utf8mb4_0900_ai_ci AS bom_revision,
                ec.effective_at         AS effective_at,
                ec.status               COLLATE utf8mb4_0900_ai_ci AS status,
                ec.created_by           COLLATE utf8mb4_0900_ai_ci AS created_by,
                ec.approved_by          COLLATE utf8mb4_0900_ai_ci AS approved_by,
                ec.approved_at          AS approved_at,
                ec.created_at           AS created_at,
                ec.updated_at           AS updated_at,
                'MES'                   COLLATE utf8mb4_0900_ai_ci AS origen,
                CAST(NULL AS UNSIGNED)  AS ks_hist_seq,
                CAST(NULL AS CHAR)      COLLATE utf8mb4_0900_ai_ci AS ks_family_prefix
            FROM engineering_changes ec

            UNION ALL

            SELECT
                CONCAT('ks-', ke.hist_seq) COLLATE utf8mb4_0900_ai_ci AS id,
                CONCAT('KS#', ke.hist_seq) COLLATE utf8mb4_0900_ai_ci AS eco_no,
                COALESCE(ke.item_no, ke.family_prefix) COLLATE utf8mb4_0900_ai_ci AS part_no,
                '-'                     COLLATE utf8mb4_0900_ai_ci AS bom_revision,
                ke.sb_date              AS effective_at,
                'APPROVED'              COLLATE utf8mb4_0900_ai_ci AS status,
                ke.dev_emp_name         COLLATE utf8mb4_0900_ai_ci AS created_by,
                ke.bom_emp_name         COLLATE utf8mb4_0900_ai_ci AS approved_by,
                ke.synced_at            AS approved_at,
                ke.synced_at            AS created_at,
                ke.synced_at            AS updated_at,
                'KS'                    COLLATE utf8mb4_0900_ai_ci AS origen,
                ke.hist_seq             AS ks_hist_seq,
                ke.family_prefix        COLLATE utf8mb4_0900_ai_ci AS ks_family_prefix
            FROM ks_engineering_changes ke
        """)

        print(" Tablas/vista de ECOs listas")
        return True
    except Exception as e:
        print(f" Error creando tablas/vista de ECOs: {e}")
        return False


def _eco_normalize_text(value, default=''):
    text = str(value if value is not None else default).strip()
    return text


def _eco_legacy_position(value):
    return _eco_normalize_text(value)[:64]


def _eco_normalize_upper(value, default=''):
    return _eco_normalize_text(value, default).upper()


def _eco_normalize_datetime(value):
    text = _eco_normalize_text(value)
    if not text:
        return ''
    text = text.replace('T', ' ')
    if len(text) == 16:
        text += ':00'
    return text


def _eco_normalize_date(value, default=''):
    if value is None or value == '':
        return default
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d')
    text = _eco_normalize_text(value)
    if not text:
        return default
    text = text.replace('T', ' ')
    return text.split(' ')[0]


def _eco_effective_valid_from(value, effective_date):
    """Prevent ECO rows from becoming valid before the ECO effective date."""
    item_valid_from = _eco_normalize_date(value)
    eco_valid_from = _eco_normalize_date(effective_date)
    if not eco_valid_from:
        return item_valid_from or None
    if not item_valid_from or item_valid_from < eco_valid_from:
        return eco_valid_from
    return item_valid_from


def _eco_plant_date():
    try:
        return (datetime.utcnow() - timedelta(hours=6)).strftime('%Y-%m-%d')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d')


def _eco_parse_qty(value, default=1.0):
    try:
        if value is None or str(value).strip() == '':
            return default
        qty = float(value)
        return qty if qty > 0 else default
    except Exception:
        return default


def _eco_parse_bool(value):
    text = _eco_normalize_text(value).lower()
    return 1 if text in ('1', 'true', 'yes', 'si', 'sí', 'y', 'x') else 0


def _eco_position_is_valid(posicion):
    text = _eco_normalize_text(posicion).upper()
    if not text:
        return False
    if re.fullmatch(r"\d+", text):
        return True
    return re.search(r"POSICION\s*\d+", text) is not None


def _eco_add_column_if_missing(table_name, column_name, column_definition):
    try:
        existing = execute_query(
            f"SHOW COLUMNS FROM {table_name} LIKE %s",
            (column_name,),
            fetch='one'
        )
        if not existing:
            execute_query(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
    except Exception as e:
        print(f"Error asegurando columna {table_name}.{column_name}: {e}")


def _eco_modify_column_if_needed(table_name, column_name, column_definition, allowed_types):
    try:
        existing = execute_query(
            f"SHOW COLUMNS FROM {table_name} LIKE %s",
            (column_name,),
            fetch='one'
        )
        if not existing:
            return

        column_type = str(
            existing.get('Type')
            or existing.get('type')
            or existing.get('column_type')
            or ''
        ).lower()
        if not any(column_type.startswith(t) for t in allowed_types):
            execute_query(f"ALTER TABLE {table_name} MODIFY COLUMN {column_definition}")
    except Exception as e:
        print(f"Error ajustando columna {table_name}.{column_name}: {e}")


def _eco_add_index_if_missing(table_name, index_name, index_definition):
    try:
        existing = execute_query(
            f"SHOW INDEX FROM {table_name} WHERE Key_name = %s",
            (index_name,),
            fetch='one'
        )
        if not existing:
            execute_query(f"ALTER TABLE {table_name} ADD KEY {index_name} {index_definition}")
    except Exception as e:
        print(f"Error asegurando indice {table_name}.{index_name}: {e}")


def _eco_drop_view_if_exists(view_name):
    try:
        execute_query(f"DROP VIEW IF EXISTS {view_name}")
    except Exception as e:
        print(f"Error eliminando vista legacy {view_name}: {e}")


def _eco_rename_column_if_exists(table_name, old_column, new_column, new_definition):
    try:
        old_existing = execute_query(
            f"SHOW COLUMNS FROM {table_name} LIKE %s",
            (old_column,),
            fetch='one'
        )
        new_existing = execute_query(
            f"SHOW COLUMNS FROM {table_name} LIKE %s",
            (new_column,),
            fetch='one'
        )
        if old_existing and not new_existing:
            execute_query(
                f"ALTER TABLE {table_name} CHANGE COLUMN {old_column} {new_definition}"
            )
        elif old_existing and new_existing:
            execute_query(
                f"""
                UPDATE {table_name}
                SET {new_column} = {old_column}
                WHERE ({new_column} IS NULL OR {new_column} = '')
                  AND {old_column} IS NOT NULL
                """
            )
            execute_query(f"ALTER TABLE {table_name} DROP COLUMN {old_column}")
    except Exception as e:
        print(f"Error migrando columna {table_name}.{old_column} a {new_column}: {e}")


def _eco_rename_index_if_exists(table_name, old_index, new_index):
    try:
        old_existing = execute_query(
            f"SHOW INDEX FROM {table_name} WHERE Key_name = %s",
            (old_index,),
            fetch='one'
        )
        new_existing = execute_query(
            f"SHOW INDEX FROM {table_name} WHERE Key_name = %s",
            (new_index,),
            fetch='one'
        )
        if old_existing and not new_existing:
            execute_query(f"ALTER TABLE {table_name} RENAME INDEX {old_index} TO {new_index}")
        elif old_existing and new_existing:
            execute_query(f"ALTER TABLE {table_name} DROP INDEX {old_index}")
    except Exception as e:
        print(f"Error migrando indice {table_name}.{old_index} a {new_index}: {e}")


def _ks_family_prefix(part_no):
    text = _eco_normalize_upper(part_no)
    return text[:-2] if len(text) > 2 else text


def _ks_part_catalog_lookup(part_no):
    """Buscar metadatos KS para un part_no en ks_part_catalog.

    Devuelve dict con item_name, family_prefix, root_part_no, bom_kind,
    spec, unit, bom_suffix; o None si no existe.
    """
    text = _eco_normalize_upper(part_no)
    if not text:
        return None
    try:
        row = execute_query(
            """
            SELECT item_name, family_prefix, root_part_no, bom_kind,
                   spec, unit, bom_suffix
            FROM ks_part_catalog
            WHERE part_no = %s
            LIMIT 1
            """,
            (text,),
            fetch='one'
        )
        return row or None
    except Exception as e:
        print(f"Error consultando ks_part_catalog para {part_no}: {e}")
        return None


def _ks_parse_suffixes(suffixes):
    """Normaliza una lista o string de sufijos. Acepta 'a,b,c' o ['a','b']."""
    if suffixes is None:
        return []
    if isinstance(suffixes, str):
        parts = re.split(r'[,;\s]+', suffixes)
    else:
        parts = list(suffixes)
    out = []
    seen = set()
    for p in parts:
        text = _eco_normalize_upper(p)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def resolver_familia(family_prefix, suffixes):
    """Resolver una familia + sufijos a una lista de part_no existentes en ks_part_catalog.

    Devuelve: {family, suffixes, parts:[{part_no, item_name, family_prefix, bom_kind}], missing:[suffix...]}
    """
    family = _eco_normalize_upper(family_prefix)
    suf_list = _ks_parse_suffixes(suffixes)
    if not family:
        return {"family": "", "suffixes": suf_list, "parts": [], "missing": suf_list}
    if not suf_list:
        return {"family": family, "suffixes": [], "parts": [], "missing": []}

    found_parts = []
    found_suffixes = set()
    try:
        candidates = [f"{family}{s}" for s in suf_list]
        placeholders = ','.join(['%s'] * len(candidates))
        rows = execute_query(
            f"""
            SELECT part_no, item_name, family_prefix, root_part_no, bom_kind
            FROM ks_part_catalog
            WHERE part_no IN ({placeholders})
            """,
            tuple(candidates),
            fetch='all'
        ) or []
        for row in rows:
            pn = _eco_normalize_upper(row.get('part_no'))
            found_parts.append({
                'part_no': pn,
                'item_name': row.get('item_name'),
                'family_prefix': row.get('family_prefix'),
                'root_part_no': row.get('root_part_no'),
                'bom_kind': row.get('bom_kind'),
            })
            if pn.startswith(family):
                found_suffixes.add(pn[len(family):])
    except Exception as e:
        print(f"Error resolviendo familia {family}: {e}")

    missing = [s for s in suf_list if s not in found_suffixes]
    return {
        "family": family,
        "suffixes": suf_list,
        "parts": found_parts,
        "missing": missing,
    }


def _ks_fetch_bom_items_multi(part_numbers, bom_revision=None):
    """Obtener items de BOM vigente para varios part_no.
    Retorna dict: {part_no: [rows]}.
    """
    result = {}
    for pn in part_numbers:
        rows = _ks_fetch_current_bom_items(pn, bom_revision) or []
        if not rows and bom_revision:
            rows = _ks_fetch_current_bom_items(pn) or []
        result[_eco_normalize_upper(pn)] = rows
    return result


def _ks_process_value(*values):
    for value in values:
        text = _eco_normalize_upper(value)
        if text:
            return text
    return 'MAIN'


def _ks_bom_kind_from_items(items):
    processes = {_ks_process_value(i.get('item_process'), i.get('process_name'), i.get('tipo_material')) for i in items}
    if processes == {'SMD'}:
        return 'SMD'
    if processes == {'IMD'}:
        return 'IMD'
    return 'MASTER'


def _ks_fetch_current_bom_items(part_no, bom_revision=None):
    plant_date = _eco_plant_date()
    if not bom_revision:
        latest = execute_query(
            """
            SELECT bom_rev
            FROM v_ecos_bom_current
            WHERE UPPER(bom_part_no) = UPPER(%s)
              AND (status_name IS NULL OR status_name = '' OR status_name = '사용')
              AND (valid_from IS NULL OR valid_from <= %s)
              AND (valid_to IS NULL OR valid_to >= %s)
            GROUP BY bom_rev
            ORDER BY MAX(header_synced_at) DESC, bom_rev DESC
            LIMIT 1
            """,
            (part_no, plant_date, plant_date),
            fetch='one'
        )
        bom_revision = latest.get('bom_rev') if latest else None
        if not bom_revision:
            return []

    params = [part_no, plant_date, plant_date]
    where = """
        UPPER(bom_part_no) = UPPER(%s)
        AND (status_name IS NULL OR status_name = '' OR status_name = '사용')
        AND (valid_from IS NULL OR valid_from <= %s)
        AND (valid_to IS NULL OR valid_to >= %s)
    """
    where += " AND UPPER(bom_rev) = UPPER(%s)"
    params.append(bom_revision)
    try:
        return execute_query(
            f"""
            SELECT *
            FROM v_ecos_bom_current
            WHERE {where}
            ORDER BY header_synced_at DESC, bom_rev DESC, item_seq
            """,
            tuple(params),
            fetch='all'
        ) or []
    except Exception as e:
        print(f"Error leyendo v_ecos_bom_current para {part_no}: {e}")
        return []


def _eco_revision_sequence(value):
    """Return revision style, numeric sequence and numeric width for known KS formats."""
    text = _eco_normalize_upper(value)
    match = re.fullmatch(r"R(\d+)", text)
    if match:
        return "R", int(match.group(1)), len(match.group(1))
    if re.fullmatch(r"\d+", text):
        return "NUM", int(text), len(text)
    return None, None, None


def _eco_scope_part_numbers(part_numbers):
    if isinstance(part_numbers, str):
        part_numbers = re.split(r"[,;\s]+", part_numbers)
    normalized = [_eco_normalize_upper(part_no) for part_no in (part_numbers or [])]
    return sorted({part_no for part_no in normalized if part_no})


def _eco_revision_rows(part_numbers):
    part_numbers = _eco_scope_part_numbers(part_numbers)
    if not part_numbers:
        return []

    placeholders = ",".join(["%s"] * len(part_numbers))
    params = tuple(part_numbers)
    rows = execute_query(
        f"""
        SELECT part_no, bom_rev AS bom_revision, synced_at AS revision_at, 'KS' AS source
        FROM ks_bom_headers
        WHERE UPPER(part_no) IN ({placeholders})
        ORDER BY synced_at DESC, bom_rev DESC
        """,
        params,
        fetch='all'
    ) or []

    # DRAFT and APPROVED ECOs reserve their revision until they are cancelled/deleted.
    try:
        rows.extend(execute_query(
            f"""
            SELECT part_no, bom_revision, created_at AS revision_at, 'ECO' AS source
            FROM engineering_changes
            WHERE scope_kind = 'SINGLE'
              AND status IN ('DRAFT', 'APPROVED')
              AND UPPER(part_no) IN ({placeholders})
            UNION ALL
            SELECT ecs.part_no,
                   COALESCE(NULLIF(ecs.bom_revision, ''), ec.bom_revision) AS bom_revision,
                   ec.created_at AS revision_at,
                   'ECO_SCOPE' AS source
            FROM engineering_change_scope ecs
            JOIN engineering_changes ec ON ec.id = ecs.engineering_change_id
            WHERE ec.status IN ('DRAFT', 'APPROVED')
              AND UPPER(ecs.part_no) IN ({placeholders})
            """,
            params + params,
            fetch='all'
        ) or [])
    except Exception as e:
        print(f"Error leyendo revisiones ECO reservadas para {part_numbers}: {e}")
    return rows


def siguiente_revision_bom_eco(part_numbers):
    """Compute the next BOM revision for a new ECO across one model or a family scope."""
    part_numbers = _eco_scope_part_numbers(part_numbers)
    if not part_numbers:
        raise ValueError("Se requiere al menos un modelo para calcular la revision BOM")

    rows = _eco_revision_rows(part_numbers)
    parseable = []
    for row in rows:
        style, sequence, width = _eco_revision_sequence(row.get('bom_revision'))
        if style is None:
            continue
        parseable.append({
            'style': style,
            'sequence': sequence,
            'width': width,
            'revision_at': str(row.get('revision_at') or ''),
            'bom_revision': _eco_normalize_upper(row.get('bom_revision')),
        })

    if not parseable:
        return "01"

    latest = max(
        parseable,
        key=lambda row: (row.get('revision_at') or '', row.get('sequence') or 0),
    )
    style = latest['style']
    existing_same_style = [row for row in parseable if row['style'] == style]
    next_sequence = max(row['sequence'] for row in existing_same_style) + 1

    if style == "R":
        return f"R{next_sequence}"

    width = max(2, max(row['width'] for row in existing_same_style))
    return str(next_sequence).zfill(width)


def _eco_get_by_id(eco_id):
    return execute_query(
        "SELECT * FROM engineering_changes WHERE id = %s",
        (eco_id,),
        fetch='one'
    )


def _eco_list_filters(status=None, part_no=None, origen=None, eco_no=None, date_from=None, date_to=None):
    where = ["1=1"]
    params = []
    if status:
        where.append("h.status = %s")
        params.append(_eco_normalize_upper(status))
    if part_no:
        part_filter = _eco_normalize_upper(part_no)
        where.append("""
            (
                UPPER(h.part_no) = %s
                OR UPPER(h.ks_family_prefix) = %s
                OR EXISTS (
                    SELECT 1
                    FROM engineering_change_scope es
                    WHERE h.origen = 'MES'
                      AND CAST(es.engineering_change_id AS CHAR) = h.id
                      AND UPPER(es.part_no) = %s
                )
            )
        """)
        params.extend([part_filter, part_filter, part_filter])
    if origen:
        where.append("h.origen = %s")
        params.append(_eco_normalize_upper(origen))
    if eco_no:
        eco_filter = _eco_normalize_upper(eco_no)
        clean_filter = eco_filter.replace('KS#', '').replace('KS-', '')
        like_filter = f"%{eco_filter}%"
        where.append("""
            (
                UPPER(h.eco_no) LIKE %s
                OR UPPER(h.id) LIKE %s
                OR REPLACE(UPPER(h.eco_no), 'KS#', '') = %s
                OR REPLACE(UPPER(h.id), 'KS-', '') = %s
            )
        """)
        params.extend([like_filter, like_filter, clean_filter, clean_filter])
    if date_from:
        where.append("DATE(h.effective_at) >= %s")
        params.append(_eco_normalize_date(date_from))
    if date_to:
        where.append("DATE(h.effective_at) <= %s")
        params.append(_eco_normalize_date(date_to))
    return where, params


def contar_ecos(status=None, part_no=None, origen=None, eco_no=None, date_from=None, date_to=None):
    """Contar ECOs para paginacion."""
    try:
        crear_tablas_ecos()
        where, params = _eco_list_filters(status, part_no, origen, eco_no, date_from, date_to)
        row = execute_query(
            f"""
            SELECT COUNT(*) AS total
            FROM v_ecos_historial_unificado h
            WHERE {' AND '.join(where)}
            """,
            tuple(params),
            fetch='one'
        ) or {}
        return int(row.get('total') or 0)
    except Exception as e:
        print(f"Error contando ECOs: {e}")
        return 0


def listar_ecos(status=None, part_no=None, limit=100, origen=None, eco_no=None, date_from=None, date_to=None, offset=0):
    """Listar historial unificado de ECOs (MES) + ECN (K-system).

    origen: 'MES' | 'KS' | None (todos)
    """
    try:
        crear_tablas_ecos()
        where, params = _eco_list_filters(status, part_no, origen, eco_no, date_from, date_to)
        limit_clause = ""
        if limit is not None:
            safe_limit = max(1, min(int(limit or 100), 500))
            safe_offset = max(0, int(offset or 0))
            limit_clause = f"LIMIT {safe_limit} OFFSET {safe_offset}"
        query = f"""
            SELECT h.*,
                   COALESCE(c.item_count, 0) AS item_count,
                   COALESCE(s.scope_count, CASE WHEN h.origen = 'MES' THEN 1 ELSE 0 END) AS scope_count,
                   s.scope_parts
            FROM v_ecos_historial_unificado h
            LEFT JOIN (
                SELECT engineering_change_id, COUNT(*) AS item_count
                FROM engineering_change_bom_items
                GROUP BY engineering_change_id
            ) c ON h.origen = 'MES' AND CAST(c.engineering_change_id AS CHAR) = h.id
            LEFT JOIN (
                SELECT engineering_change_id,
                       COUNT(*) AS scope_count,
                       GROUP_CONCAT(part_no ORDER BY part_no SEPARATOR ', ') AS scope_parts
                FROM engineering_change_scope
                GROUP BY engineering_change_id
            ) s ON h.origen = 'MES' AND CAST(s.engineering_change_id AS CHAR) = h.id
            WHERE {' AND '.join(where)}
            ORDER BY COALESCE(h.effective_at, h.updated_at) DESC, h.updated_at DESC
            {limit_clause}
        """
        return execute_query(query, tuple(params), fetch='all') or []
    except Exception as e:
        print(f"Error listando ECOs: {e}")
        return []


def obtener_eco_detalle(eco_id):
    """Obtener ECO con sus items."""
    try:
        crear_tablas_ecos()
        eco = _eco_get_by_id(eco_id)
        if not eco:
            return None
        items = execute_query(
            """
            SELECT * FROM engineering_change_bom_items
            WHERE engineering_change_id = %s
            ORDER BY COALESCE(NULLIF(location_text, ''), posicion_assy), material_code
            """,
            (eco_id,),
            fetch='all'
        ) or []
        eco['items'] = items
        return eco
    except Exception as e:
        print(f"Error obteniendo ECO: {e}")
        return None


def obtener_ecn_ks(hist_seq):
    """Obtener detalle de un ECN sincronizado desde K-system."""
    try:
        row = execute_query(
            """
            SELECT
                family_prefix, hist_seq, item_no, item_seq, sb_date,
                ord1, decide1, ord2, decide2,
                chg_remark, change_context, cause, step_result,
                bom_emp_seq, bom_emp_name, dev_emp_seq, dev_emp_name,
                remark, seongcheolsa, work_no, synced_at
            FROM ks_engineering_changes
            WHERE hist_seq = %s
            LIMIT 1
            """,
            (int(hist_seq),),
            fetch='one'
        )
        return row
    except Exception as e:
        print(f"Error obteniendo ECN KS {hist_seq}: {e}")
        return None


def crear_eco(data, created_by='desconocido'):
    """Crear ECO en borrador y opcionalmente copiar el BOM actual del modelo."""
    crear_tablas_ecos()
    eco_no = _eco_normalize_upper(data.get('eco_no'))
    part_no = _eco_normalize_upper(data.get('part_no'))
    effective_at = _eco_normalize_datetime(data.get('effective_at'))
    notes = _eco_normalize_text(data.get('notes'))
    item_name_input = _eco_normalize_text(data.get('item_name'))
    copy_current_bom = data.get('copy_current_bom', True)

    if not eco_no or not part_no or not effective_at:
        raise ValueError("eco_no, part_no y effective_at son requeridos")
    bom_revision = siguiente_revision_bom_eco([part_no])

    if not item_name_input:
        catalog = _ks_part_catalog_lookup(part_no) or {}
        item_name_input = _eco_normalize_text(catalog.get('item_name'))

    conn = get_connection()
    if conn is None:
        raise RuntimeError("No hay conexion MySQL disponible")

    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass
        cursor.execute(
            """
            INSERT INTO engineering_changes
                (eco_no, part_no, bom_revision, effective_at, status, notes, created_by, item_name)
            VALUES (%s, %s, %s, %s, 'DRAFT', %s, %s, %s)
            """,
            (eco_no, part_no, bom_revision, effective_at, notes, created_by, item_name_input or None)
        )
        eco_id = cursor.lastrowid

        if copy_current_bom:
            current_items = _ks_fetch_current_bom_items(part_no, bom_revision)
            if not current_items:
                current_items = _ks_fetch_current_bom_items(part_no)
            values = []
            for item in current_items:
                material = _eco_normalize_upper(item.get('item_no'))
                numero_parte = material
                location_text = _eco_normalize_text(item.get('location_text'))
                process_value = _ks_process_value(item.get('item_process'), item.get('process_name'))
                values.append((
                    eco_id,
                    process_value,
                    _eco_legacy_position(location_text),
                    location_text,
                    material,
                    numero_parte,
                    _eco_parse_qty(item.get('qty')),
                    location_text,
                    _eco_normalize_text(item.get('supplier') or item.get('maker')),
                    '',
                    _eco_normalize_text(item.get('item_class')),
                    _eco_normalize_text(item.get('spec')),
                    _eco_normalize_text(item.get('bom_level')),
                    _eco_normalize_text(item.get('item_seq')),
                    _eco_normalize_text(item.get('item_name')),
                    _eco_normalize_text(item.get('item_name_en')),
                    _eco_normalize_text(item.get('unit')),
                    _eco_normalize_text(item.get('maker')),
                    _eco_normalize_text(item.get('process_name')),
                    process_value,
                    _eco_normalize_text(item.get('item_class')),
                    _eco_normalize_date(item.get('valid_from'), _eco_normalize_date(effective_at)),
                    _eco_normalize_date(item.get('valid_to')) or None,
                    _eco_normalize_text(item.get('status_name'), '사용') or '사용',
                    _eco_parse_bool(item.get('is_alternate')),
                    _eco_normalize_upper(item.get('alt_item_no')),
                    _eco_normalize_text(item.get('alt_item_name')),
                    _eco_normalize_text(item.get('alt_spec')),
                    _eco_normalize_text(item.get('alt_maker')),
                    _eco_normalize_upper(item.get('child_bom_part_no')),
                    _eco_parse_bool(item.get('is_sub_bom')),
                    _eco_normalize_text(item.get('remark')),
                    _eco_normalize_text(item.get('item_remark')),
                ))
            if values:
                cursor.executemany(
                    """
                    INSERT INTO engineering_change_bom_items
                        (engineering_change_id, tipo_material, posicion_assy, location_text, material_code,
                         numero_parte, qty, ubicacion, proveedor, side, classification, spec,
                         bom_level, item_seq, item_name, item_name_en, unit, maker,
                         process_name, item_process, item_class, valid_from, valid_to,
                         status_name, is_alternate, alt_item_no, alt_item_name, alt_spec,
                         alt_maker, child_bom_part_no, is_sub_bom, remark, item_remark)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    values
                )

        conn.commit()
        return obtener_eco_detalle(eco_id)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


_ECO_DIFF_CRITICAL_FIELDS = (
    'item_no', 'item_name', 'spec', 'qty', 'unit', 'location_text',
    'maker', 'supplier', 'item_class', 'item_process', 'process_name',
    'valid_from', 'valid_to', 'is_alternate', 'alt_item_no',
    'alt_item_name', 'alt_spec', 'alt_maker', 'remark',
)

_ECO_FAMILY_BLANK_MEANS_UNCHANGED_FIELDS = (
    'item_name', 'spec', 'unit', 'location_text', 'maker', 'supplier',
    'item_class', 'item_process', 'process_name', 'valid_from', 'valid_to',
    'is_alternate', 'alt_item_no', 'alt_item_name', 'alt_spec', 'alt_maker',
    'remark',
)


def _eco_single_row_keys_from_values(item_no, bom_level, item_seq=None):
    item_no = _eco_normalize_upper(item_no)
    bom_level = _eco_normalize_text(bom_level)
    item_seq = _eco_normalize_text(item_seq)
    if not item_no and not bom_level:
        return []
    keys = [f"{item_no}|{bom_level}"]
    if item_seq:
        keys.append(f"{item_no}|{bom_level}|{item_seq}")
    return keys


def _eco_single_row_keys(item):
    return _eco_single_row_keys_from_values(
        item.get('item_no') or item.get('material_code') or item.get('numero_parte'),
        item.get('bom_level'),
        item.get('item_seq'),
    )


def _eco_excel_row_ref(item):
    """Referencia estable para la columna oculta __row_id del Excel de ECO.

    La vista canonical v_ecos_bom_current no expone id fisico del componente.
    Cuando no hay id, usamos item_no|bom_level|item_seq para detectar filas
    borradas al subir el Excel modificado.
    """
    rid = item.get('id')
    if rid not in (None, ''):
        return rid
    keys = _eco_single_row_keys(item)
    return keys[-1] if keys else ''


def _eco_diff_normalize(value):
    """Normalizar valor para comparar campos del diff (None/str/numero)."""
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        try:
            return value.strftime('%Y-%m-%d')
        except Exception:
            return str(value)
    text = str(value).strip()
    if text.lower() in ('nan', 'none', 'null'):
        return ''
    return text


def _eco_diff_normalize_qty(value):
    try:
        if value is None or str(value).strip() == '':
            return ''
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return _eco_diff_normalize(value)


def _eco_diff_normalize_bool(value):
    if value is None or str(value).strip() == '':
        return '0'
    return '1' if _eco_parse_bool(value) else '0'


def _eco_diff_field_value(item, field):
    if field == 'qty':
        return _eco_diff_normalize_qty(item.get('qty'))
    if field == 'is_alternate':
        return _eco_diff_normalize_bool(item.get('is_alternate'))
    if field in ('valid_from', 'valid_to'):
        return _eco_diff_normalize(item.get(field))
    return _eco_diff_normalize(item.get(field))


def _eco_family_raw_blank_fields(raw):
    blank_fields = set()
    for field in _ECO_FAMILY_BLANK_MEANS_UNCHANGED_FIELDS:
        if _eco_diff_normalize(raw.get(field)) == '':
            blank_fields.add(field)
    return blank_fields


def _eco_family_origin_values(raw):
    origin = raw.get('__origin_values')
    return origin if isinstance(origin, dict) else {}


def _eco_family_field_matches_origin(row, field, new_val):
    origin = row.get('__origin_values') or {}
    if field not in origin:
        return False
    return _eco_diff_field_value(origin, field) == new_val


def _eco_apply_change_to_item(target, source, field):
    """Aplicar un campo editado del Excel familiar a una fila BOM destino."""
    if not target or not source or not field:
        return
    if field == 'item_no':
        value = _eco_normalize_upper(source.get('material_code') or source.get('numero_parte') or source.get('item_no'))
        target['item_no'] = value
        target['material_code'] = value
        target['numero_parte'] = value
        return
    if field == 'qty':
        target['qty'] = source.get('qty')
        return
    if field == 'location_text':
        value = source.get('location_text') or source.get('ubicacion')
        target['location_text'] = value
        target['ubicacion'] = value
        return
    if field == 'supplier':
        value = source.get('proveedor') or source.get('supplier') or source.get('maker')
        target['supplier'] = value
        target['proveedor'] = value
        return
    if field == 'item_class':
        value = source.get('item_class') or source.get('classification')
        target['item_class'] = value
        target['classification'] = value
        return
    if field == 'item_process':
        value = source.get('item_process') or source.get('tipo_material')
        target['item_process'] = value
        target['tipo_material'] = value
        return
    if field == 'process_name':
        target['process_name'] = source.get('process_name')
        return
    target[field] = source.get(field)


def crear_eco_desde_excel(metadata, excel_rows, created_by='desconocido'):
    """Crear ECO DRAFT desde un Excel modificado de BOM.

    metadata: dict con eco_no, part_no, effective_at, item_name?, notes?
    excel_rows: lista de dicts con keys segun BOM_EXCEL_COLUMNS (sin '__row_id' es addición; con id existente es modificacion).

    Retorna: {success, eco_id, diff:{added,removed,modified}, errors}
    """
    crear_tablas_ecos()
    eco_no = _eco_normalize_upper(metadata.get('eco_no'))
    part_no = _eco_normalize_upper(metadata.get('part_no'))
    effective_at = _eco_normalize_datetime(metadata.get('effective_at'))
    notes = _eco_normalize_text(metadata.get('notes'))
    item_name_input = _eco_normalize_text(metadata.get('item_name'))

    errors = []
    if not eco_no: errors.append("eco_no requerido")
    if not part_no: errors.append("part_no requerido")
    if not effective_at: errors.append("effective_at requerido")
    if not excel_rows: errors.append("El Excel no tiene filas")
    if errors:
        return {"success": False, "errors": errors}
    bom_revision = siguiente_revision_bom_eco([part_no])

    if not item_name_input:
        catalog = _ks_part_catalog_lookup(part_no) or {}
        item_name_input = _eco_normalize_text(catalog.get('item_name'))

    current_items = _ks_fetch_current_bom_items(part_no, bom_revision) or []
    if not current_items:
        current_items = _ks_fetch_current_bom_items(part_no) or []
    current_entries = {}
    current_ref_by_id = {}
    current_ref_by_key = {}
    for row in current_items:
        rid = row.get('id')
        keys = _eco_single_row_keys(row)
        base_ref = None
        if rid not in (None, ''):
            try:
                rid_int = int(rid)
                base_ref = f"id:{rid_int}"
                current_ref_by_id[rid_int] = base_ref
            except (TypeError, ValueError):
                base_ref = None
        if base_ref is None and keys:
            base_ref = f"key:{keys[-1]}"
        if not base_ref:
            continue
        current_entries[base_ref] = row
        for key in keys:
            current_ref_by_key.setdefault(key, base_ref)

    seen_levels = set()
    seen_refs = set()
    parsed_rows = []
    for idx, raw in enumerate(excel_rows, start=1):
        item_no = _eco_normalize_upper(raw.get('item_no'))
        if not item_no:
            errors.append(f"Fila {idx}: item_no vacio")
            continue

        qty_raw = raw.get('qty')
        try:
            qty = float(qty_raw) if qty_raw not in (None, '') else 0
        except (TypeError, ValueError):
            errors.append(f"Fila {idx} ({item_no}): qty no es numero ('{qty_raw}')")
            continue
        if qty <= 0:
            errors.append(f"Fila {idx} ({item_no}): qty debe ser > 0")
            continue

        bom_level = _eco_normalize_text(raw.get('bom_level')) or f"01-{idx:02d}"
        item_seq = _eco_normalize_text(raw.get('item_seq')) or str(idx)
        if bom_level in seen_levels:
            errors.append(f"Fila {idx} ({item_no}): bom_level '{bom_level}' duplicado")
        seen_levels.add(bom_level)

        row_ref_raw = _eco_normalize_text(raw.get('__row_id'))
        if row_ref_raw.lower() in ('nan', 'none', 'null'):
            row_ref_raw = ''
        row_id = None
        row_ref = None
        if row_ref_raw:
            try:
                row_id = int(float(row_ref_raw)) if re.fullmatch(r"\d+(?:\.0+)?", row_ref_raw) else None
            except (TypeError, ValueError):
                row_id = None
            if row_id is not None:
                row_ref = current_ref_by_id.get(row_id)
            if row_ref is None:
                row_ref = current_ref_by_key.get(row_ref_raw)
            if row_ref is None:
                errors.append(f"Fila {idx} ({item_no}): __row_id '{row_ref_raw}' no existe en BOM actual")
        else:
            for key in reversed(_eco_single_row_keys_from_values(item_no, bom_level, item_seq)):
                row_ref = current_ref_by_key.get(key)
                if row_ref:
                    break

        if row_ref is not None:
            if row_ref in seen_refs:
                errors.append(f"Fila {idx} ({item_no}): referencia de BOM duplicada")
            seen_refs.add(row_ref)

        parsed_rows.append({
            '__row_id': row_id,
            '__row_ref': row_ref,
            'item_no': item_no,
            'item_name': _eco_normalize_text(raw.get('item_name')),
            'spec': _eco_normalize_text(raw.get('spec')),
            'qty': qty,
            'unit': _eco_normalize_text(raw.get('unit')) or 'EA',
            'location_text': _eco_normalize_text(raw.get('location_text')),
            'maker': _eco_normalize_text(raw.get('maker')),
            'supplier': _eco_normalize_text(raw.get('supplier')),
            'item_class': _eco_normalize_text(raw.get('item_class')),
            'item_process': _eco_normalize_text(raw.get('item_process')),
            'process_name': _eco_normalize_text(raw.get('process_name')),
            'valid_from': _eco_normalize_date(raw.get('valid_from')) or None,
            'valid_to': _eco_normalize_date(raw.get('valid_to')) or None,
            'is_alternate': _eco_parse_bool(raw.get('is_alternate')),
            'alt_item_no': _eco_normalize_upper(raw.get('alt_item_no')),
            'alt_item_name': _eco_normalize_text(raw.get('alt_item_name')),
            'alt_spec': _eco_normalize_text(raw.get('alt_spec')),
            'alt_maker': _eco_normalize_text(raw.get('alt_maker')),
            'remark': _eco_normalize_text(raw.get('remark')),
            'bom_level': bom_level,
            'item_seq': item_seq,
        })

    if errors:
        return {"success": False, "errors": errors}

    diff_added = []
    diff_removed = []
    diff_modified = []

    for row in parsed_rows:
        if row['__row_ref'] is None:
            diff_added.append(row)
        else:
            original = current_entries.get(row['__row_ref'])
            if original is None:
                continue
            field_diffs = []
            for field in _ECO_DIFF_CRITICAL_FIELDS:
                old_val = _eco_diff_field_value(original, field)
                new_val = _eco_diff_field_value(row, field)
                if old_val != new_val:
                    field_diffs.append({
                        'field': field,
                        'old': old_val,
                        'new': new_val,
                    })
            if field_diffs:
                diff_modified.append({
                    'row_id': row['__row_id'],
                    'item_no': row['item_no'],
                    'bom_level': row['bom_level'],
                    'changes': field_diffs,
                })

    excel_refs = {row['__row_ref'] for row in parsed_rows if row['__row_ref'] is not None}
    for ref, original in current_entries.items():
        if ref not in excel_refs:
            diff_removed.append({
                'row_id': original.get('id'),
                'item_no': _eco_diff_normalize(original.get('item_no')),
                'bom_level': _eco_diff_normalize(original.get('bom_level')),
            })

    if not (diff_added or diff_removed or diff_modified):
        return {"success": False, "errors": ["El Excel no contiene cambios respecto al BOM actual"]}

    conn = get_connection()
    if conn is None:
        return {"success": False, "errors": ["No hay conexion MySQL disponible"]}

    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass

        cursor.execute(
            """
            INSERT INTO engineering_changes
                (eco_no, part_no, bom_revision, effective_at, status, notes, created_by, item_name)
            VALUES (%s, %s, %s, %s, 'DRAFT', %s, %s, %s)
            """,
            (eco_no, part_no, bom_revision, effective_at, notes, created_by, item_name_input or None)
        )
        eco_id = cursor.lastrowid

        item_values = []
        for row in parsed_rows:
            item_values.append((
                eco_id,
                _ks_process_value(row.get('item_process'), 'MAIN'),
                _eco_legacy_position(row['location_text']),
                row['location_text'],
                row['item_no'],
                row['item_no'],
                row['qty'],
                row['location_text'],
                row['supplier'] or row['maker'],
                '',
                row['item_class'],
                row['spec'],
                row['bom_level'],
                row['item_seq'],
                row['item_name'] or row['item_no'],
                '',
                row['unit'],
                row['maker'],
                row['process_name'] or row['item_process'],
                row['item_process'],
                row['item_class'],
                row['valid_from'],
                row['valid_to'],
                '사용',
                row['is_alternate'],
                row['alt_item_no'],
                row['alt_item_name'],
                row['alt_spec'],
                row['alt_maker'],
                '',
                0,
                row.get('remark'),
                None,
            ))
        if item_values:
            cursor.executemany(
                """
                INSERT INTO engineering_change_bom_items
                    (engineering_change_id, tipo_material, posicion_assy, location_text, material_code,
                     numero_parte, qty, ubicacion, proveedor, side, classification, spec,
                     bom_level, item_seq, item_name, item_name_en, unit, maker,
                     process_name, item_process, item_class, valid_from, valid_to,
                     status_name, is_alternate, alt_item_no, alt_item_name, alt_spec,
                     alt_maker, child_bom_part_no, is_sub_bom, remark, item_remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                item_values
            )

        diff_rows = []
        for r in diff_added:
            diff_rows.append((eco_id, 'ADD', r['item_no'], r['bom_level'], None, None, None, None))
        for r in diff_removed:
            diff_rows.append((eco_id, 'REMOVE', r['item_no'], r['bom_level'], r['row_id'], None, None, None))
        for r in diff_modified:
            for change in r['changes']:
                diff_rows.append((
                    eco_id, 'MODIFY', r['item_no'], r['bom_level'], r['row_id'],
                    change['field'], change['old'] or None, change['new'] or None,
                ))
        if diff_rows:
            cursor.executemany(
                """
                INSERT INTO engineering_change_diff
                    (engineering_change_id, action, item_no, bom_level, ks_row_id,
                     field_changed, old_value, new_value)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                diff_rows
            )

        conn.commit()
        return {
            "success": True,
            "eco_id": eco_id,
            "bom_revision": bom_revision,
            "diff": {
                "added": len(diff_added),
                "removed": len(diff_removed),
                "modified": len(diff_modified),
                "modified_fields": sum(len(r['changes']) for r in diff_modified),
            },
            "errors": [],
        }
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"Error creando ECO desde Excel: {e}")
        return {"success": False, "errors": [str(e)]}
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def obtener_diff_eco(eco_id):
    """Obtener el diff persistido de un ECO."""
    try:
        rows = execute_query(
            """
            SELECT id, part_no, action, item_no, bom_level, ks_row_id,
                   field_changed, old_value, new_value, created_at
            FROM engineering_change_diff
            WHERE engineering_change_id = %s
            ORDER BY FIELD(action, 'ADD', 'MODIFY', 'REMOVE'), part_no, bom_level, item_no, field_changed
            """,
            (int(eco_id),),
            fetch='all'
        ) or []
        return rows
    except Exception as e:
        print(f"Error obteniendo diff ECO {eco_id}: {e}")
        return []


def obtener_scope_eco(eco_id):
    """Obtener la lista de part_no afectados por un ECO de familia."""
    try:
        rows = execute_query(
            """
            SELECT part_no, family_prefix, bom_revision
            FROM engineering_change_scope
            WHERE engineering_change_id = %s
            ORDER BY part_no
            """,
            (int(eco_id),),
            fetch='all'
        ) or []
        return rows
    except Exception as e:
        print(f"Error obteniendo scope ECO {eco_id}: {e}")
        return []


def crear_eco_familia_desde_excel(metadata, excel_rows, scope_parts, created_by='desconocido'):
    """Crear ECO de familia desde Excel multi-modelo.

    metadata: eco_no, family_prefix, effective_at, item_name?, notes?
    excel_rows: lista de dicts con __row_key, modelos_afectados, item_no, bom_level y demas campos.
    scope_parts: lista de part_no del scope (resuelta antes).

    Retorna: {success, eco_id, diff, errors}
    """
    crear_tablas_ecos()
    eco_no = _eco_normalize_upper(metadata.get('eco_no'))
    family_prefix = _eco_normalize_upper(metadata.get('family_prefix'))
    effective_at = _eco_normalize_datetime(metadata.get('effective_at'))
    notes = _eco_normalize_text(metadata.get('notes'))
    item_name_input = _eco_normalize_text(metadata.get('item_name'))
    scope_parts = [_eco_normalize_upper(p) for p in scope_parts if p]

    errors = []
    if not eco_no: errors.append("eco_no requerido")
    if not family_prefix: errors.append("family_prefix requerido")
    if not effective_at: errors.append("effective_at requerido")
    if not scope_parts: errors.append("scope_parts vacio")
    if not excel_rows: errors.append("El Excel no tiene filas")
    if errors:
        return {"success": False, "errors": errors}
    bom_revision = siguiente_revision_bom_eco(scope_parts)

    # Construir BOM vigente por modelo
    bom_by_part = _ks_fetch_bom_items_multi(scope_parts, bom_revision)
    bom_by_part_key = {}  # {part_no: {row_key: row}}
    for pn, rows in bom_by_part.items():
        idx = {}
        for r in rows:
            key = f"{(r.get('item_no') or '').upper()}|{(r.get('bom_level') or '').strip()}"
            if key.strip('|'):
                idx[key] = r
        bom_by_part_key[pn] = idx

    # Parsear filas del Excel
    parsed_rows = []
    seen_keys = set()
    for idx, raw in enumerate(excel_rows, start=1):
        item_no = _eco_normalize_upper(raw.get('item_no'))
        if not item_no:
            errors.append(f"Fila {idx}: item_no vacio")
            continue

        qty_raw = raw.get('qty')
        try:
            qty = float(qty_raw) if qty_raw not in (None, '') else 0
        except (TypeError, ValueError):
            errors.append(f"Fila {idx} ({item_no}): qty no es numero ('{qty_raw}')")
            continue
        if qty <= 0:
            errors.append(f"Fila {idx} ({item_no}): qty debe ser > 0")
            continue

        modelos_raw = _eco_normalize_text(raw.get('modelos_afectados'))
        modelos = _ks_parse_suffixes(modelos_raw) if modelos_raw else []
        modelos = [m for m in modelos if m in scope_parts]
        if not modelos:
            # Si no especifica, asumir todos los del scope
            modelos = list(scope_parts)

        row_key_raw = _eco_normalize_text(raw.get('__row_key'))
        bom_level = _eco_normalize_text(raw.get('bom_level'))
        if not bom_level and row_key_raw and '|' in row_key_raw:
            bom_level = row_key_raw.split('|', 1)[1]
        if not bom_level:
            errors.append(f"Fila {idx} ({item_no}): bom_level vacio")
            continue

        # Para filas nuevas en ECO de familia permitimos __row_key vacio y lo generamos.
        # La llave canonical siempre debe ser ITEM_NO|BOM_LEVEL para diff estable.
        row_key = f"{item_no}|{bom_level}"
        if row_key in seen_keys:
            errors.append(f"Fila {idx}: __row_key '{row_key}' duplicado")
            continue
        seen_keys.add(row_key)

        parsed_rows.append({
            '__row_key': row_key,
            '__row_key_raw': row_key_raw,
            '__blank_fields': _eco_family_raw_blank_fields(raw),
            '__origin_values': _eco_family_origin_values(raw),
            'item_no': item_no,
            'item_name': _eco_normalize_text(raw.get('item_name')),
            'spec': _eco_normalize_text(raw.get('spec')),
            'qty': qty,
            'unit': _eco_normalize_text(raw.get('unit')) or 'EA',
            'location_text': _eco_normalize_text(raw.get('location_text')),
            'maker': _eco_normalize_text(raw.get('maker')),
            'supplier': _eco_normalize_text(raw.get('supplier')),
            'item_class': _eco_normalize_text(raw.get('item_class')),
            'item_process': _eco_normalize_text(raw.get('item_process')),
            'process_name': _eco_normalize_text(raw.get('process_name')),
            'valid_from': _eco_normalize_date(raw.get('valid_from')) or None,
            'valid_to': _eco_normalize_date(raw.get('valid_to')) or None,
            'is_alternate': _eco_parse_bool(raw.get('is_alternate')),
            'alt_item_no': _eco_normalize_upper(raw.get('alt_item_no')),
            'alt_item_name': _eco_normalize_text(raw.get('alt_item_name')),
            'alt_spec': _eco_normalize_text(raw.get('alt_spec')),
            'alt_maker': _eco_normalize_text(raw.get('alt_maker')),
            'remark': _eco_normalize_text(raw.get('remark')),
            'bom_level': bom_level,
            'item_seq': _eco_normalize_text(raw.get('item_seq')) or str(idx),
            'modelos_afectados': modelos,
        })

    if errors:
        return {"success": False, "errors": errors}

    # Calcular diff por modelo
    diff_added = []  # [{part_no, row, ...}]
    diff_removed = []
    diff_modified = []

    excel_keys_by_part = {pn: set() for pn in scope_parts}
    for row in parsed_rows:
        for pn in row['modelos_afectados']:
            excel_keys_by_part.setdefault(pn, set()).add(row['__row_key'])

    for row in parsed_rows:
        key = row['__row_key']
        is_new_row_intent = not _eco_normalize_text(row.get('__row_key_raw'))
        for pn in row['modelos_afectados']:
            current = bom_by_part_key.get(pn, {}).get(key)
            if current is None:
                # El usuario quiere aplicar este item a un modelo donde no existe
                # ADD: aceptable. Lo importante es que no hagamos MODIFY sobre algo inexistente.
                diff_added.append({
                    'part_no': pn,
                    'row': row,
                })
            else:
                if is_new_row_intent:
                    errors.append(
                        f"Fila nueva '{row['item_no']}' en modelo {pn} ya existe con bom_level {row['bom_level']}. "
                        "Para añadir, use un bom_level nuevo; para modificar, conserve __row_key original."
                    )
                    continue
                field_diffs = []
                blank_fields = row.get('__blank_fields') or set()
                for field in _ECO_DIFF_CRITICAL_FIELDS:
                    if field in blank_fields:
                        continue
                    old_val = _eco_diff_field_value(current, field)
                    new_val = _eco_diff_field_value(row, field)
                    if old_val == new_val:
                        continue
                    if _eco_family_field_matches_origin(row, field, new_val):
                        continue
                    field_diffs.append({
                        'field': field,
                        'old': old_val,
                        'new': new_val,
                    })
                if field_diffs:
                    diff_modified.append({
                        'part_no': pn,
                        'row_id': current.get('id'),
                        'item_no': row['item_no'],
                        'bom_level': row['bom_level'],
                        'changes': field_diffs,
                        'row': row,
                    })

    # REMOVE: items en BOM vigente que no aparecen en el Excel (por modelo)
    for pn, idx in bom_by_part_key.items():
        excel_keys_for_part = excel_keys_by_part.get(pn, set())
        for key, original in idx.items():
            if key not in excel_keys_for_part:
                diff_removed.append({
                    'part_no': pn,
                    'row_id': original.get('id'),
                    'item_no': original.get('item_no'),
                    'bom_level': original.get('bom_level'),
                })

    if errors:
        return {"success": False, "errors": errors}

    if not (diff_added or diff_removed or diff_modified):
        return {"success": False, "errors": ["El Excel no contiene cambios respecto al BOM actual"]}

    # Bloquear si una fila MODIFY apunta a un modelo donde el item no existe
    # (Eso se detectaria como ADD; pero si el usuario listo el modelo en modelos_afectados
    #  con la intencion de modificar, debe existir. Verificamos: si una row con cambios criticos
    #  termino como ADD en un modelo donde NO existia, lo permitimos solo si TODOS los campos
    #  son nuevos. Aqui aceptamos ADD libremente; el bloqueo lo dejamos a si el usuario manda
    #  un modelo no presente en scope_parts -> ya filtrado arriba.)

    # Tomar metadatos del catalog para usar el primer part_no como representante
    representative_part = scope_parts[0]
    if not item_name_input:
        catalog = _ks_part_catalog_lookup(representative_part) or {}
        item_name_input = _eco_normalize_text(catalog.get('item_name'))

    conn = get_connection()
    if conn is None:
        return {"success": False, "errors": ["No hay conexion MySQL disponible"]}

    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass

        cursor.execute(
            """
            INSERT INTO engineering_changes
                (eco_no, part_no, bom_revision, effective_at, status, notes,
                 created_by, item_name, scope_kind, family_prefix)
            VALUES (%s, %s, %s, %s, 'DRAFT', %s, %s, %s, 'FAMILY', %s)
            """,
            (eco_no, representative_part, bom_revision, effective_at, notes,
             created_by, item_name_input or None, family_prefix)
        )
        eco_id = cursor.lastrowid

        scope_values = [(eco_id, pn, family_prefix, bom_revision) for pn in scope_parts]
        cursor.executemany(
            """
            INSERT INTO engineering_change_scope
                (engineering_change_id, part_no, family_prefix, bom_revision)
            VALUES (%s, %s, %s, %s)
            """,
            scope_values
        )

        # Items del ECO: guardamos UN registro por fila del Excel (no replicamos por modelo).
        # El detalle "a qué modelo aplica cada cambio" vive en engineering_change_diff.
        item_values = []
        for row in parsed_rows:
            item_values.append((
                eco_id,
                _ks_process_value(row.get('item_process'), 'MAIN'),
                _eco_legacy_position(row['location_text']),
                row['location_text'],
                row['item_no'],
                row['item_no'],
                row['qty'],
                row['location_text'],
                row['supplier'] or row['maker'],
                '',
                row['item_class'],
                row['spec'],
                row['bom_level'],
                row['item_seq'],
                row['item_name'] or row['item_no'],
                '',
                row['unit'],
                row['maker'],
                row['process_name'] or row['item_process'],
                row['item_process'],
                row['item_class'],
                row['valid_from'],
                row['valid_to'],
                '사용',
                row['is_alternate'],
                row['alt_item_no'],
                row['alt_item_name'],
                row['alt_spec'],
                row['alt_maker'],
                '',
                0,
                row.get('remark'),
                None,
            ))
        if item_values:
            cursor.executemany(
                """
                INSERT INTO engineering_change_bom_items
                    (engineering_change_id, tipo_material, posicion_assy, location_text, material_code,
                     numero_parte, qty, ubicacion, proveedor, side, classification, spec,
                     bom_level, item_seq, item_name, item_name_en, unit, maker,
                     process_name, item_process, item_class, valid_from, valid_to,
                     status_name, is_alternate, alt_item_no, alt_item_name, alt_spec,
                     alt_maker, child_bom_part_no, is_sub_bom, remark, item_remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                item_values
            )

        diff_rows = []
        for d in diff_added:
            diff_rows.append((eco_id, d['part_no'], 'ADD', d['row']['item_no'], d['row']['bom_level'], None, None, None, None))
        for d in diff_removed:
            diff_rows.append((eco_id, d['part_no'], 'REMOVE', d['item_no'], d['bom_level'], d['row_id'], None, None, None))
        for d in diff_modified:
            for change in d['changes']:
                diff_rows.append((
                    eco_id, d['part_no'], 'MODIFY', d['item_no'], d['bom_level'], d['row_id'],
                    change['field'], change['old'] or None, change['new'] or None,
                ))
        if diff_rows:
            cursor.executemany(
                """
                INSERT INTO engineering_change_diff
                    (engineering_change_id, part_no, action, item_no, bom_level,
                     ks_row_id, field_changed, old_value, new_value)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                diff_rows
            )

        conn.commit()

        # Resumen por modelo
        per_part = {}
        for d in diff_added:
            per_part.setdefault(d['part_no'], {'added': 0, 'modified': 0, 'removed': 0})['added'] += 1
        for d in diff_modified:
            per_part.setdefault(d['part_no'], {'added': 0, 'modified': 0, 'removed': 0})['modified'] += 1
        for d in diff_removed:
            per_part.setdefault(d['part_no'], {'added': 0, 'modified': 0, 'removed': 0})['removed'] += 1

        return {
            "success": True,
            "eco_id": eco_id,
            "bom_revision": bom_revision,
            "scope_kind": "FAMILY",
            "scope_parts": scope_parts,
            "diff": {
                "added": len(diff_added),
                "removed": len(diff_removed),
                "modified": len(diff_modified),
                "modified_fields": sum(len(d['changes']) for d in diff_modified),
                "per_part": per_part,
            },
            "errors": [],
        }
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"Error creando ECO familia: {e}")
        return {"success": False, "errors": [str(e)]}
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def importar_items_eco_desde_dataframe(eco_id, df):
    """Reemplazar items de un ECO DRAFT desde Excel."""
    crear_tablas_ecos()
    eco = _eco_get_by_id(eco_id)
    if not eco:
        raise ValueError("ECO no encontrado")
    if eco.get('status') != 'DRAFT':
        raise ValueError("Solo se pueden importar items en ECOs DRAFT")

    columnas_disponibles = df.columns.tolist()

    def normalizar_columna(nombre):
        texto = str(nombre or '')
        texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
        texto = texto.strip().lower()
        texto = re.sub(r'[^a-z0-9]+', ' ', texto)
        return ' '.join(texto.split())

    columnas_normalizadas = {col: normalizar_columna(col) for col in columnas_disponibles}

    def buscar_columna(variaciones_exactas=None, variaciones_contiene=None):
        variaciones_exactas = variaciones_exactas or []
        variaciones_contiene = variaciones_contiene or []
        for var in variaciones_exactas:
            var_norm = normalizar_columna(var)
            for col, col_norm in columnas_normalizadas.items():
                if col_norm == var_norm:
                    return col
        for var in variaciones_contiene:
            var_norm = normalizar_columna(var)
            for col, col_norm in columnas_normalizadas.items():
                if var_norm and var_norm in col_norm:
                    return col
        return None

    col_numero_parte = buscar_columna(
        ['numero de parte', 'numero_parte', 'part number', 'material'],
        ['numero parte', 'part number']
    )
    col_material = buscar_columna(
        ['codigo de material', 'codigo_material', 'material code'],
        ['codigo material', 'material code']
    )
    col_posicion = buscar_columna(
        ['posicion assy', 'posicion_assy', 'posicion', 'position'],
        ['posicion', 'position']
    )
    col_qty = buscar_columna(['cantidad total', 'cantidad', 'qty'], ['cantidad', 'qty'])
    col_tipo = buscar_columna(['tipo de material', 'tipo_material', 'material type'], ['tipo de material', 'material type'])
    col_ubicacion = buscar_columna(['ubicacion', 'location'], ['ubicacion', 'location'])
    col_proveedor = buscar_columna(['proveedor', 'vendor', 'vender', 'supplier'], ['proveedor', 'vendor', 'supplier'])
    col_side = buscar_columna(['side', 'lado'], ['side', 'lado'])
    col_classification = buscar_columna(['classification', 'clasificacion', 'categoria'], ['classification', 'clasificacion', 'categoria'])
    col_spec = buscar_columna(['especificacion', 'especificacion material', 'description', 'descripcion'], ['especificacion', 'description', 'descripcion'])
    col_bom_level = buscar_columna(['bom_level', 'bom level', 'nivel bom'], ['bom level', 'nivel'])
    col_item_seq = buscar_columna(['item_seq', 'item seq', 'secuencia'], ['item seq', 'secuencia'])
    col_item_name = buscar_columna(['item_name', 'item name', 'nombre item', 'descripcion material'], ['item name', 'nombre item'])
    col_item_name_en = buscar_columna(['item_name_en', 'item name en', 'nombre ingles'], ['name en', 'ingles'])
    col_unit = buscar_columna(['unit', 'unidad'], ['unit', 'unidad'])
    col_maker = buscar_columna(['maker', 'fabricante'], ['maker', 'fabricante'])
    col_process_name = buscar_columna(['process_name', 'process name', 'proceso'], ['process name', 'proceso'])
    col_item_process = buscar_columna(['item_process', 'item process', 'tipo proceso'], ['item process', 'tipo proceso'])
    col_item_class = buscar_columna(['item_class', 'item class', 'classification'], ['item class', 'classification'])
    col_valid_from = buscar_columna(['valid_from', 'valid from', 'fecha efectiva', 'effective date'], ['valid from', 'fecha efectiva', 'effective'])
    col_valid_to = buscar_columna(['valid_to', 'valid to', 'fecha fin'], ['valid to', 'fecha fin'])
    col_status_name = buscar_columna(['status_name', 'status name', 'estado'], ['status name', 'estado'])
    col_is_alternate = buscar_columna(['is_alternate', 'is alternate', 'alterno'], ['is alternate', 'alterno'])
    col_alt_item_no = buscar_columna(['alt_item_no', 'alternate item no', 'material alterno', 'material sustituto'], ['alt item', 'alternate', 'sustituto'])
    col_alt_item_name = buscar_columna(['alt_item_name', 'alternate item name', 'nombre alterno'], ['alt name', 'alterno nombre'])
    col_alt_spec = buscar_columna(['alt_spec', 'alternate spec', 'spec alterno'], ['alt spec', 'spec alterno'])
    col_alt_maker = buscar_columna(['alt_maker', 'alternate maker', 'maker alterno'], ['alt maker', 'maker alterno'])
    col_child_bom_part_no = buscar_columna(['child_bom_part_no', 'child bom part no', 'sub bom'], ['child bom', 'sub bom'])
    col_is_sub_bom = buscar_columna(['is_sub_bom', 'is sub bom'], ['is sub bom'])
    col_remark = buscar_columna(['remark', 'remarks', 'comentario', 'observacion'], ['remark', 'comentario', 'observacion'])
    col_item_remark = buscar_columna(['item_remark', 'item remark', 'comentario item'], ['item remark', 'comentario item'])

    if not col_numero_parte and not col_material:
        raise ValueError("El Excel debe incluir Numero de Parte o Codigo de Material")

    values = []
    omitidos = 0
    for _, row in df.iterrows():
        numero_parte = _eco_normalize_upper(row.get(col_numero_parte) if col_numero_parte else '')
        material = _eco_normalize_upper(row.get(col_material) if col_material else '')
        if not numero_parte and not material:
            omitidos += 1
            continue
        if not material:
            material = numero_parte
        if not numero_parte:
            numero_parte = material
        location_text = _eco_normalize_text(row.get(col_posicion) if col_posicion else '')
        if not location_text:
            location_text = _eco_normalize_text(row.get(col_ubicacion) if col_ubicacion else '')
        item_process = _ks_process_value(
            row.get(col_item_process) if col_item_process else '',
            row.get(col_tipo) if col_tipo else ''
        )
        process_name = _eco_normalize_text(row.get(col_process_name) if col_process_name else item_process)
        values.append((
            eco_id,
            item_process,
            _eco_legacy_position(location_text),
            location_text,
            material,
            numero_parte,
            _eco_parse_qty(row.get(col_qty) if col_qty else 1),
            location_text,
            _eco_normalize_text(row.get(col_proveedor) if col_proveedor else ''),
            _eco_normalize_text(row.get(col_side) if col_side else ''),
            _eco_normalize_text(row.get(col_classification) if col_classification else ''),
            _eco_normalize_text(row.get(col_spec) if col_spec else ''),
            _eco_normalize_text(row.get(col_bom_level) if col_bom_level else ''),
            _eco_normalize_text(row.get(col_item_seq) if col_item_seq else ''),
            _eco_normalize_text(row.get(col_item_name) if col_item_name else ''),
            _eco_normalize_text(row.get(col_item_name_en) if col_item_name_en else ''),
            _eco_normalize_text(row.get(col_unit) if col_unit else 'EA') or 'EA',
            _eco_normalize_text(row.get(col_maker) if col_maker else ''),
            process_name,
            item_process,
            _eco_normalize_text(row.get(col_item_class) if col_item_class else row.get(col_classification) if col_classification else ''),
            _eco_normalize_date(row.get(col_valid_from) if col_valid_from else eco.get('effective_at')),
            _eco_normalize_date(row.get(col_valid_to) if col_valid_to else '') or None,
            _eco_normalize_text(row.get(col_status_name) if col_status_name else '사용') or '사용',
            _eco_parse_bool(row.get(col_is_alternate) if col_is_alternate else 0),
            _eco_normalize_upper(row.get(col_alt_item_no) if col_alt_item_no else ''),
            _eco_normalize_text(row.get(col_alt_item_name) if col_alt_item_name else ''),
            _eco_normalize_text(row.get(col_alt_spec) if col_alt_spec else ''),
            _eco_normalize_text(row.get(col_alt_maker) if col_alt_maker else ''),
            _eco_normalize_upper(row.get(col_child_bom_part_no) if col_child_bom_part_no else ''),
            _eco_parse_bool(row.get(col_is_sub_bom) if col_is_sub_bom else 0),
            _eco_normalize_text(row.get(col_remark) if col_remark else ''),
            _eco_normalize_text(row.get(col_item_remark) if col_item_remark else ''),
        ))

    if not values:
        raise ValueError("No se encontraron filas validas para importar")

    conn = get_connection()
    if conn is None:
        raise RuntimeError("No hay conexion MySQL disponible")
    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass
        cursor.execute("DELETE FROM engineering_change_bom_items WHERE engineering_change_id = %s", (eco_id,))
        cursor.executemany(
            """
            INSERT INTO engineering_change_bom_items
                (engineering_change_id, tipo_material, posicion_assy, location_text, material_code,
                 numero_parte, qty, ubicacion, proveedor, side, classification, spec,
                 bom_level, item_seq, item_name, item_name_en, unit, maker,
                 process_name, item_process, item_class, valid_from, valid_to,
                 status_name, is_alternate, alt_item_no, alt_item_name, alt_spec,
                 alt_maker, child_bom_part_no, is_sub_bom, remark, item_remark)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            values
        )
        conn.commit()
        return {"insertados": len(values), "omitidos": omitidos}
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def validar_eco_para_aprobacion(eco_id):
    """Validar que un ECO DRAFT pueda aprobarse."""
    eco = obtener_eco_detalle(eco_id)
    errors = []
    if not eco:
        return ["ECO no encontrado"]
    if eco.get('status') != 'DRAFT':
        errors.append("Solo se pueden aprobar ECOs DRAFT")
    for field in ('eco_no', 'part_no', 'bom_revision', 'effective_at'):
        if not eco.get(field):
            errors.append(f"Campo requerido faltante: {field}")
    items = eco.get('items') or []
    if not items:
        errors.append("El ECO no tiene items de BOM")
    for idx, item in enumerate(items, start=1):
        material = item.get('material_code') or item.get('numero_parte')
        if not material:
            errors.append(f"Item {idx}: material_code/numero_parte requerido")
        if _eco_parse_qty(item.get('qty'), 0) <= 0:
            errors.append(f"Item {idx}: qty debe ser mayor a 0")
    errors.extend(_validar_revision_bom_no_publicada(eco_id, eco))
    return errors


def _validar_revision_bom_no_publicada(eco_id, eco):
    """Every ECO must publish a new KS revision for each model it affects."""
    bom_rev = _eco_normalize_upper((eco or {}).get('bom_revision'))
    if not bom_rev:
        return []

    if _eco_normalize_upper((eco or {}).get('scope_kind')) == 'FAMILY':
        scope = obtener_scope_eco(eco_id) or []
        part_numbers = [_eco_normalize_upper(row.get('part_no')) for row in scope]
    else:
        part_numbers = [_eco_normalize_upper((eco or {}).get('part_no'))]
    part_numbers = sorted({part_no for part_no in part_numbers if part_no})
    if not part_numbers:
        return []

    placeholders = ','.join(['%s'] * len(part_numbers))
    existing = execute_query(
        f"""
        SELECT part_no
        FROM ks_bom_headers
        WHERE UPPER(bom_rev) = UPPER(%s)
          AND UPPER(part_no) IN ({placeholders})
        ORDER BY part_no
        LIMIT 10
        """,
        tuple([bom_rev] + part_numbers),
        fetch='all'
    ) or []
    if not existing:
        return []
    examples = ', '.join(
        _eco_normalize_upper(row.get('part_no')) for row in existing if row.get('part_no')
    )
    return [
        (
            f"Revision BOM {bom_rev} ya existe en KS"
            + (f" para {examples}" if examples else "")
        )
    ]


def _eco_item_key(item_no, bom_level):
    return f"{_eco_normalize_upper(item_no)}|{_eco_normalize_text(bom_level)}"


def _eco_component_tuple(part_no, bom_rev, item, effective_date, eco, idx):
    item_no = _eco_normalize_upper(item.get('material_code') or item.get('numero_parte') or item.get('item_no'))
    item_process = _ks_process_value(item.get('item_process'), item.get('tipo_material'), item.get('process_name'))
    process_name = _eco_normalize_text(item.get('process_name')) or item_process
    location_text = _eco_normalize_text(item.get('location_text') or item.get('ubicacion') or item.get('posicion_assy'))
    return (
        part_no,
        bom_rev,
        _eco_normalize_text(item.get('bom_level')) or f"01-{idx:02d}",
        _eco_normalize_text(item.get('item_seq')) or str(idx),
        item_no,
        _eco_normalize_text(item.get('item_name')) or item_no,
        _eco_normalize_text(item.get('item_name_en')),
        _eco_normalize_text(item.get('spec')),
        _eco_parse_qty(item.get('qty')),
        _eco_normalize_text(item.get('unit'), 'EA') or 'EA',
        location_text,
        _eco_normalize_text(item.get('maker') or item.get('proveedor') or item.get('supplier')),
        process_name,
        item_process,
        _eco_normalize_text(item.get('proveedor') or item.get('supplier')),
        _eco_normalize_text(item.get('item_class') or item.get('classification')),
        _eco_effective_valid_from(item.get('valid_from'), effective_date),
        _eco_normalize_date(item.get('valid_to')) or None,
        '사용',
        _eco_parse_bool(item.get('is_alternate')),
        _eco_normalize_upper(item.get('alt_item_no')),
        _eco_normalize_text(item.get('alt_item_name')),
        _eco_normalize_text(item.get('alt_spec')),
        _eco_normalize_text(item.get('alt_maker')),
        _eco_normalize_upper(item.get('child_bom_part_no')),
        _eco_parse_bool(item.get('is_sub_bom')),
        _eco_normalize_text(item.get('remark')) or f"ECO {eco.get('eco_no')}",
        _eco_normalize_text(item.get('item_remark')) or _eco_normalize_text(eco.get('notes')),
    )


def _aprobar_eco_familia(eco_id, approved_by, eco):
    """Aprobar un ECO de familia publicando una revision completa por modelo."""
    items = eco.get('items') or []
    effective_date = _eco_normalize_date(eco.get('effective_at'), _eco_plant_date())
    bom_rev = _eco_normalize_upper(eco.get('bom_revision'))
    family_prefix = _eco_normalize_upper(eco.get('family_prefix'))

    scope = obtener_scope_eco(eco_id)
    if not scope:
        return {"success": False, "errors": ["El ECO de familia no tiene scope definido"]}

    # Indexar items del ECO por __row_key = item_no|bom_level
    items_by_key = {}
    for it in items:
        key = _eco_item_key(it.get('material_code') or it.get('numero_parte') or it.get('item_no'), it.get('bom_level'))
        if key.strip('|'):
            items_by_key[key] = it

    # Cargar diff completo agrupado por part_no
    diff_rows = execute_query(
        """
        SELECT part_no, action, item_no, bom_level, ks_row_id,
               field_changed, old_value, new_value
        FROM engineering_change_diff
        WHERE engineering_change_id = %s
        """,
        (int(eco_id),),
        fetch='all'
    ) or []
    diff_by_part = {}
    for r in diff_rows:
        pn = _eco_normalize_upper(r.get('part_no'))
        diff_by_part.setdefault(pn, []).append(r)

    conn = get_connection()
    if conn is None:
        return {"success": False, "errors": ["No hay conexion MySQL disponible"]}
    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass

        applied_summary = {}
        insert_sql = """
            INSERT INTO ks_bom_components
                (parent_part_no, bom_rev, bom_level, item_seq, item_no,
                 item_name, item_name_en, spec, qty, unit, location_text,
                 maker, process_name, item_process, supplier, item_class,
                 valid_from, valid_to, status_name, is_alternate,
                 alt_item_no, alt_item_name, alt_spec, alt_maker,
                 child_bom_part_no, is_sub_bom, remark, item_remark, synced_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                 %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        current_by_part = _ks_fetch_bom_items_multi([entry.get('part_no') for entry in scope], None)

        for entry in scope:
            part_no = _eco_normalize_upper(entry.get('part_no'))
            if not part_no:
                continue

            catalog = _ks_part_catalog_lookup(part_no) or {}
            cat_item_name = _eco_normalize_text(catalog.get('item_name')) if catalog else ''
            cat_spec = _eco_normalize_text(catalog.get('spec')) if catalog else ''
            cat_unit = _eco_normalize_text(catalog.get('unit')) if catalog else ''
            cat_family = _eco_normalize_text(catalog.get('family_prefix')) if catalog else ''
            cat_root = _eco_normalize_text(catalog.get('root_part_no')) if catalog else ''
            cat_kind = _eco_normalize_upper(catalog.get('bom_kind')) if catalog else ''
            cat_suffix = _eco_normalize_text(catalog.get('bom_suffix')) if catalog else ''

            target_rows = {}
            for current in current_by_part.get(part_no, []):
                key = _eco_item_key(current.get('item_no'), current.get('bom_level'))
                if key.strip('|'):
                    target_rows[key] = dict(current)

            part_diffs = diff_by_part.get(part_no, [])
            adds = [d for d in part_diffs if d.get('action') == 'ADD']
            removes = [d for d in part_diffs if d.get('action') == 'REMOVE']
            modifies = [d for d in part_diffs if d.get('action') == 'MODIFY']

            for d in removes:
                target_rows.pop(_eco_item_key(d.get('item_no'), d.get('bom_level')), None)

            modify_by_key = {}
            for d in modifies:
                new_key = _eco_item_key(d.get('item_no'), d.get('bom_level'))
                old_key = new_key
                if d.get('field_changed') == 'item_no' and d.get('old_value'):
                    old_key = _eco_item_key(d.get('old_value'), d.get('bom_level'))
                base_row = target_rows.get(old_key) or target_rows.get(new_key) or {}
                if old_key != new_key:
                    base_row = target_rows.pop(old_key, base_row)
                info = modify_by_key.setdefault(new_key, {
                    'base': dict(base_row),
                    'fields': set(),
                })
                if base_row and not info.get('base'):
                    info['base'] = dict(base_row)
                if d.get('field_changed'):
                    info['fields'].add(d.get('field_changed'))

            for key, info in modify_by_key.items():
                src = items_by_key.get(key)
                if src:
                    merged = info.get('base') or dict(target_rows.get(key, {}))
                    for field in info.get('fields') or []:
                        _eco_apply_change_to_item(merged, src, field)
                    target_rows[key] = merged

            for d in adds:
                key = _eco_item_key(d.get('item_no'), d.get('bom_level'))
                src = items_by_key.get(key)
                if src:
                    target_rows[key] = dict(src)

            cursor.execute(
                "DELETE FROM ks_bom_components WHERE parent_part_no = %s AND bom_rev = %s",
                (part_no, bom_rev)
            )

            ordered_items = sorted(
                target_rows.values(),
                key=lambda row: (
                    _eco_normalize_text(row.get('item_seq')).zfill(12),
                    _eco_normalize_text(row.get('bom_level')),
                    _eco_normalize_upper(row.get('material_code') or row.get('numero_parte') or row.get('item_no')),
                )
            )
            component_values = [
                _eco_component_tuple(part_no, bom_rev, item, effective_date, eco, idx)
                for idx, item in enumerate(ordered_items, start=1)
            ]
            if component_values:
                cursor.executemany(insert_sql, component_values)

            comp_count = len(component_values)
            cursor.execute(
                """
                INSERT INTO ks_bom_headers
                    (part_no, item_seq, item_name, spec, unit, bom_rev, root_part_no,
                     family_prefix, bom_suffix, bom_kind, component_count,
                     source_updated_at, synced_at)
                VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """,
                (
                    part_no,
                    cat_item_name or part_no,
                    cat_spec or None,
                    cat_unit or None,
                    bom_rev,
                    cat_root or part_no,
                    cat_family or family_prefix or _ks_family_prefix(part_no),
                    cat_suffix or None,
                    cat_kind or _ks_bom_kind_from_items(items),
                    comp_count,
                )
            )

            applied_summary[part_no] = {
                'added': len(adds),
                'modified': len(modify_by_key),
                'removed': len(removes),
                'total_components': comp_count,
            }

        cursor.execute(
            """
            UPDATE engineering_changes
            SET status = 'APPROVED',
                approved_by = %s,
                approved_at = NOW(),
                updated_at = NOW()
            WHERE id = %s AND status = 'DRAFT'
            """,
            (approved_by, eco_id)
        )

        conn.commit()
        return {
            "success": True,
            "errors": [],
            "scope_kind": "FAMILY",
            "applied": applied_summary,
        }
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"Error aprobando ECO familia {eco_id}: {e}")
        return {"success": False, "errors": [str(e)]}
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def aprobar_eco(eco_id, approved_by='desconocido'):
    """Aprobar un ECO DRAFT y publicar la revision en tablas KS."""
    errors = validar_eco_para_aprobacion(eco_id)
    if errors:
        return {"success": False, "errors": errors}
    eco = obtener_eco_detalle(eco_id)

    if _eco_normalize_upper(eco.get('scope_kind')) == 'FAMILY':
        return _aprobar_eco_familia(eco_id, approved_by, eco)

    items = eco.get('items') or []
    effective_date = _eco_normalize_date(eco.get('effective_at'), _eco_plant_date())
    part_no = _eco_normalize_upper(eco.get('part_no'))
    bom_rev = _eco_normalize_upper(eco.get('bom_revision'))

    catalog = _ks_part_catalog_lookup(part_no) or {}
    catalog_item_name = _eco_normalize_text(catalog.get('item_name')) if catalog else ''
    catalog_spec = _eco_normalize_text(catalog.get('spec')) if catalog else ''
    catalog_unit = _eco_normalize_text(catalog.get('unit')) if catalog else ''
    catalog_family = _eco_normalize_text(catalog.get('family_prefix')) if catalog else ''
    catalog_root = _eco_normalize_text(catalog.get('root_part_no')) if catalog else ''
    catalog_kind = _eco_normalize_upper(catalog.get('bom_kind')) if catalog else ''
    catalog_suffix = _eco_normalize_text(catalog.get('bom_suffix')) if catalog else ''

    header_item_name = (
        _eco_normalize_text(eco.get('item_name'))
        or catalog_item_name
        or part_no
    )
    header_spec = catalog_spec or None
    header_unit = catalog_unit or None
    header_family = catalog_family or _ks_family_prefix(part_no)
    header_root = catalog_root or part_no
    header_suffix = catalog_suffix or None
    header_bom_kind = catalog_kind or _ks_bom_kind_from_items(items)

    conn = get_connection()
    if conn is None:
        return {"success": False, "errors": ["No hay conexion MySQL disponible"]}

    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass

        cursor.execute(
            """
            INSERT INTO ks_bom_headers
                (part_no, item_seq, item_name, spec, unit, bom_rev, root_part_no,
                 family_prefix, bom_suffix, bom_kind, component_count,
                 source_updated_at, synced_at)
            VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """,
            (
                part_no,
                header_item_name,
                header_spec,
                header_unit,
                bom_rev,
                header_root,
                header_family,
                header_suffix,
                header_bom_kind,
                len(items),
            )
        )

        cursor.execute(
            "DELETE FROM ks_bom_components WHERE parent_part_no = %s AND bom_rev = %s",
            (part_no, bom_rev)
        )

        component_values = []
        for idx, item in enumerate(items, start=1):
            item_no = _eco_normalize_upper(item.get('material_code') or item.get('numero_parte'))
            if not item_no:
                continue
            item_process = _ks_process_value(item.get('item_process'), item.get('tipo_material'))
            process_name = _eco_normalize_text(item.get('process_name')) or item_process
            location_text = _eco_normalize_text(item.get('location_text') or item.get('ubicacion') or item.get('posicion_assy'))
            component_values.append((
                part_no,
                bom_rev,
                _eco_normalize_text(item.get('bom_level')) or f"01-{idx:02d}",
                _eco_normalize_text(item.get('item_seq')) or str(idx),
                item_no,
                _eco_normalize_text(item.get('item_name')) or item_no,
                _eco_normalize_text(item.get('item_name_en')),
                _eco_normalize_text(item.get('spec')),
                _eco_parse_qty(item.get('qty')),
                _eco_normalize_text(item.get('unit'), 'EA') or 'EA',
                location_text,
                _eco_normalize_text(item.get('maker') or item.get('proveedor')),
                process_name,
                item_process,
                _eco_normalize_text(item.get('proveedor')),
                _eco_normalize_text(item.get('item_class') or item.get('classification')),
                _eco_effective_valid_from(item.get('valid_from'), effective_date),
                _eco_normalize_date(item.get('valid_to')) or None,
                '사용',
                _eco_parse_bool(item.get('is_alternate')),
                _eco_normalize_upper(item.get('alt_item_no')),
                _eco_normalize_text(item.get('alt_item_name')),
                _eco_normalize_text(item.get('alt_spec')),
                _eco_normalize_text(item.get('alt_maker')),
                _eco_normalize_upper(item.get('child_bom_part_no')),
                _eco_parse_bool(item.get('is_sub_bom')),
                f"ECO {eco.get('eco_no')}",
                _eco_normalize_text(eco.get('notes')),
            ))

        if component_values:
            cursor.executemany(
                """
                INSERT INTO ks_bom_components
                    (parent_part_no, bom_rev, bom_level, item_seq, item_no,
                     item_name, item_name_en, spec, qty, unit, location_text,
                     maker, process_name, item_process, supplier, item_class,
                     valid_from, valid_to, status_name, is_alternate,
                     alt_item_no, alt_item_name, alt_spec, alt_maker,
                     child_bom_part_no, is_sub_bom, remark, item_remark, synced_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                component_values
            )

        ks_family_prefix = _ks_family_prefix(part_no) or None
        ks_hist_seq = eco.get('ks_hist_seq')
        try:
            ks_hist_seq = int(ks_hist_seq) if ks_hist_seq not in (None, '', 0) else None
        except (TypeError, ValueError):
            ks_hist_seq = None

        if ks_hist_seq is None and ks_family_prefix:
            item_numbers = [
                _eco_normalize_upper(item.get('material_code') or item.get('numero_parte'))
                for item in items
            ]
            item_numbers = [x for x in item_numbers if x]
            if item_numbers:
                placeholders = ','.join(['%s'] * len(item_numbers))
                cursor.execute(
                    f"""
                    SELECT hist_seq
                    FROM ks_engineering_changes
                    WHERE family_prefix = %s
                      AND UPPER(item_no) IN ({placeholders})
                    ORDER BY sb_date DESC, hist_seq DESC
                    LIMIT 2
                    """,
                    (ks_family_prefix, *item_numbers)
                )
                rows = cursor.fetchall() or []
                if len(rows) == 1:
                    ks_hist_seq = rows[0][0] if isinstance(rows[0], (list, tuple)) else rows[0].get('hist_seq')

        cursor.execute(
            """
            UPDATE engineering_changes
            SET status = 'APPROVED',
                approved_by = %s,
                approved_at = NOW(),
                ks_family_prefix = %s,
                ks_hist_seq = %s,
                updated_at = NOW()
            WHERE id = %s AND status = 'DRAFT'
            """,
            (approved_by, ks_family_prefix, ks_hist_seq, eco_id)
        )

        conn.commit()
        return {"success": True, "errors": [], "published_items": len(component_values)}
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return {"success": False, "errors": [str(e)]}
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def cancelar_eco(eco_id, cancelled_by='desconocido'):
    """Cancelar un ECO DRAFT. Los ECOs aprobados son inmutables."""
    eco = _eco_get_by_id(eco_id)
    if not eco:
        return {"success": False, "error": "ECO no encontrado"}
    if eco.get('status') == 'APPROVED':
        return {"success": False, "error": "Un ECO aprobado es inmutable"}
    result = execute_query(
        """
        UPDATE engineering_changes
        SET status = 'CANCELLED',
            notes = CONCAT(COALESCE(notes, ''), %s),
            updated_at = NOW()
        WHERE id = %s AND status = 'DRAFT'
        """,
        (f"\nCancelado por {cancelled_by}", eco_id)
    )
    return {"success": bool(result)}


def eliminar_eco(eco_id):
    """Eliminar fisicamente un ECO que no este aprobado."""
    eco = _eco_get_by_id(eco_id)
    if not eco:
        return {"success": False, "error": "ECO no encontrado"}
    if eco.get('status') == 'APPROVED':
        return {"success": False, "error": "Un ECO aprobado es inmutable; no se puede borrar"}

    execute_query(
        "DELETE FROM engineering_change_bom_items WHERE engineering_change_id = %s",
        (eco_id,)
    )
    result = execute_query(
        "DELETE FROM engineering_changes WHERE id = %s AND status <> 'APPROVED'",
        (eco_id,)
    )
    return {"success": bool(result)}


# === FUNCIONES DE BOM ===

def obtener_bom_por_modelo(modelo):
    """Obtener BOM por modelo desde la vista canonica KS/ECOs."""
    return listar_bom_por_modelo(modelo)

def guardar_bom_item(data):
    """La edicion directa de bom quedo deshabilitada; usar Crear ECO."""
    print("guardar_bom_item bloqueado: use Crear ECO para publicar en KS")
    return False

def obtener_modelos_bom():
    """Obtener lista de modelos en BOM"""
    try:
        plant_date = _eco_plant_date()
        query = """
            SELECT DISTINCT bom_part_no AS modelo
            FROM v_ecos_bom_current
            WHERE (status_name IS NULL OR status_name = '' OR status_name = '사용')
              AND (valid_from IS NULL OR valid_from <= %s)
              AND (valid_to IS NULL OR valid_to >= %s)
            ORDER BY bom_part_no
        """
        result = execute_query(query, (plant_date, plant_date), fetch='all') or []
        return [{'modelo': row['modelo']} for row in result]
    except Exception as e:
        print(f"Error obteniendo modelos BOM desde v_ecos_bom_current: {e}")
        return []


def _map_ks_bom_row(row):
    process_value = _ks_process_value(row.get('item_process'), row.get('process_name'))
    return {
        'id': row.get('id') or row.get('item_seq'),
        'modelo': row.get('bom_part_no'),
        'codigoMaterial': row.get('item_no'),
        'numeroParte': row.get('item_no'),
        'side': '',
        'tipoMaterial': process_value,
        'classification': row.get('item_class'),
        'especificacionMaterial': row.get('spec'),
        'vender': row.get('maker'),
        'cantidadTotal': row.get('qty'),
        'cantidadOriginal': row.get('qty'),
        'ubicacion': row.get('location_text'),
        'posicionAssy': row.get('location_text'),
        'materialSustituto': row.get('alt_item_no'),
        'materialOriginal': None,
        'registrador': 'KS',
        'fechaRegistro': row.get('component_synced_at') or row.get('header_synced_at'),
        'bomRevision': row.get('bom_rev'),
    }


def listar_bom_por_modelo(modelo, classification=None, bom_revision=None):
    """Listar BOM desde v_ecos_bom_current con shape legacy para la pantalla."""
    try:
        selected_revision = str(bom_revision or '').strip()
        plant_date = _eco_plant_date()
        where = [
            "(status_name IS NULL OR status_name = '' OR status_name = '사용')",
        ]
        params = []

        # La consulta normal muestra el BOM vigente por fecha. Cuando Control BOM
        # pide una revision explicita debe poder inspeccionar revisiones pasadas o futuras.
        if not selected_revision:
            where.extend([
                "(valid_from IS NULL OR valid_from <= %s)",
                "(valid_to IS NULL OR valid_to >= %s)",
            ])
            params.extend([plant_date, plant_date])

        if modelo and modelo != 'todos':
            where.append("UPPER(bom_part_no) = UPPER(%s)")
            params.append(modelo)
            if not selected_revision:
                latest = execute_query(
                    """
                    SELECT bom_rev
                    FROM v_ecos_bom_current
                    WHERE UPPER(bom_part_no) = UPPER(%s)
                      AND (status_name IS NULL OR status_name = '' OR status_name = '사용')
                      AND (valid_from IS NULL OR valid_from <= %s)
                      AND (valid_to IS NULL OR valid_to >= %s)
                    GROUP BY bom_rev
                    ORDER BY MAX(header_synced_at) DESC, bom_rev DESC
                    LIMIT 1
                    """,
                    (modelo, plant_date, plant_date),
                    fetch='one'
                )
                if latest and latest.get('bom_rev'):
                    where.append("UPPER(bom_rev) = UPPER(%s)")
                    params.append(latest.get('bom_rev'))

        if selected_revision:
            where.append("UPPER(bom_rev) = UPPER(%s)")
            params.append(selected_revision)

        if classification and classification != 'TODOS':
            where.append("""
                (
                    UPPER(COALESCE(NULLIF(item_process, ''), NULLIF(process_name, ''), 'MAIN')) = UPPER(%s)
                    OR UPPER(COALESCE(item_class, '')) = UPPER(%s)
                )
            """)
            params.extend([classification, classification])

        query = f"""
            SELECT *
            FROM v_ecos_bom_current
            WHERE {' AND '.join(where)}
            ORDER BY bom_part_no, header_synced_at DESC, bom_rev DESC, item_seq, item_no
        """
        result = execute_query(query, tuple(params), fetch='all') or []
        print(
            " Query BOM KS: "
            f"modelo={modelo}, classification={classification}, bom_revision={selected_revision or 'vigente'}, "
            f"resultados={len(result)}"
        )
        return [_map_ks_bom_row(row) for row in result]
    except Exception as e:
        print(f"Error listando BOM por modelo: {e}")
        return []

def insertar_bom_desde_dataframe(df, registrador):
    """Reject direct imports into the obsolete legacy `bom` table."""
    raise ValueError("La tabla legacy bom esta obsoleta. Use Control BOM -> Crear ECO -> Importar Excel y aprobar.")

