"""Helpers compartidos para resolucion de BOM revisions y ECOs.

Consumidores:
  - app/routes.py             (rutas de Plan: /api/plan, /api/plan-imd, /api/plan-main/list, ...)
  - app/api/informacion_basica/control_bom.py  (modulo Control BOM)

Antes de 2026-05-25 estas 3 funciones existian duplicadas en ambos archivos
con SQL identico. La duplicacion garantizaba drift al cambiar la query en
un solo lado. Esta consolidacion las mueve a single source-of-truth.

Sin cambios de comportamiento.
"""

from app.db_mysql import execute_query


def _ks_current_bom_revision(part_no):
    """Devuelve la `bom_rev` actual (vigente hoy) para un `part_no` en KS."""
    # Late import para evitar ciclo shared -> routes -> shared.
    # NOTA: usamos la version de app.routes que devuelve `datetime`, no la
    # de app.db_mysql que devuelve `str` (no soportaria .strftime aqui).
    from app.routes import obtener_fecha_hora_mexico
    plant_date = obtener_fecha_hora_mexico().strftime("%Y-%m-%d")
    row = execute_query(
        """
        SELECT bom_rev
        FROM v_ecos_bom_current
        WHERE UPPER(bom_part_no) = UPPER(%s)
          AND status_name = '사용'
          AND (valid_from IS NULL OR valid_from <= %s)
          AND (valid_to IS NULL OR valid_to >= %s)
        GROUP BY bom_rev
        ORDER BY MAX(header_synced_at) DESC, bom_rev DESC
        LIMIT 1
        """,
        (part_no, plant_date, plant_date),
        fetch="one",
    )
    return (row or {}).get("bom_rev") if isinstance(row, dict) else (row[0] if row else None)


def _eco_for_part_revision(part_no, bom_rev):
    """Devuelve el ECO (eco_no, effective_at, status) que aplica a la pareja part_no+bom_rev."""
    return execute_query(
        """
        SELECT ec.eco_no, ec.effective_at, ec.status
        FROM engineering_changes ec
        WHERE (
            UPPER(ec.part_no) = UPPER(%s)
            AND UPPER(ec.bom_revision) = UPPER(%s)
          )
          OR EXISTS (
            SELECT 1
            FROM engineering_change_scope ecs
            WHERE ecs.engineering_change_id = ec.id
              AND UPPER(ecs.part_no) = UPPER(%s)
              AND UPPER(COALESCE(NULLIF(ecs.bom_revision, ''), ec.bom_revision)) = UPPER(%s)
          )
        ORDER BY ec.effective_at DESC, ec.id DESC
        LIMIT 1
        """,
        (part_no, bom_rev, part_no, bom_rev),
        fetch="one",
    )


def _bom_revision_catalog(part_no):
    """Catalogo de todas las revisiones de BOM para un `part_no`, anotadas con ECO y flag de actual."""
    normalized_part = str(part_no or "").strip().upper()
    current_rev = _ks_current_bom_revision(normalized_part)
    rows = execute_query(
        """
        SELECT bom_rev, synced_at
        FROM ks_bom_headers
        WHERE UPPER(part_no) = UPPER(%s)
        ORDER BY synced_at DESC, bom_rev DESC
        """,
        (normalized_part,),
        fetch="all",
    ) or []
    revisions = []
    for row in rows:
        bom_rev = row.get("bom_rev") if isinstance(row, dict) else row[0]
        eco = _eco_for_part_revision(normalized_part, bom_rev) or {}
        effective_at = eco.get("effective_at") if isinstance(eco, dict) else None
        revisions.append(
            {
                "bom_rev": bom_rev,
                "is_current": str(bom_rev or "").upper() == str(current_rev or "").upper(),
                "eco_no": eco.get("eco_no") if isinstance(eco, dict) else None,
                "eco_effective_at": str(effective_at or "") if effective_at else None,
                "eco_status": eco.get("status") if isinstance(eco, dict) else None,
            }
        )
    return revisions


# Alias retrocompatible: routes.py usaba el nombre `_plan_bom_revision_catalog`.
_plan_bom_revision_catalog = _bom_revision_catalog


# ============================================================
# BOM assignment a planes (plan_main / plan_imd)
# Migrado de routes.py + plan_assy.py (2026-05-26).
#
# Consumidores: app/routes.py, app/api/control_produccion/plan_assy.py,
#               app/api/control_produccion/plan_imd.py.
# ============================================================

_PLAN_BOM_ASSIGNMENT_COLUMNS_READY = False


def _ensure_plan_bom_assignment_columns():
    """Keep plan schema compatible with explicit KS BOM revision assignment.

    Agrega 3 columnas (`assigned_bom_rev`, `assigned_bom_rev_by`,
    `assigned_bom_rev_at`) a plan_main y plan_imd si no existen.
    Idempotente: solo corre el primer call por proceso (guard global).
    """
    global _PLAN_BOM_ASSIGNMENT_COLUMNS_READY
    if _PLAN_BOM_ASSIGNMENT_COLUMNS_READY:
        return
    for table_name in ("plan_main", "plan_imd"):
        columns = (
            ("assigned_bom_rev", "assigned_bom_rev VARCHAR(64) NULL"),
            ("assigned_bom_rev_by", "assigned_bom_rev_by VARCHAR(100) NULL"),
            ("assigned_bom_rev_at", "assigned_bom_rev_at DATETIME NULL"),
        )
        for column_name, definition in columns:
            existing = execute_query(
                f"SHOW COLUMNS FROM {table_name} LIKE %s",
                (column_name,),
                fetch="one",
            )
            if not existing:
                execute_query(f"ALTER TABLE {table_name} ADD COLUMN {definition}")
    _PLAN_BOM_ASSIGNMENT_COLUMNS_READY = True


def _plan_has_ks_snapshot(plan_id, modo):
    """True si Verificacion ya congelo un snapshot KS para este plan+modo."""
    snapshot_table = execute_query(
        "SHOW TABLES LIKE 'plan_ks_bom_snapshot'",
        fetch="one",
    )
    if not snapshot_table:
        return False
    row = execute_query(
        """
        SELECT id
        FROM plan_ks_bom_snapshot
        WHERE plan_id = %s AND UPPER(modo) = UPPER(%s)
        LIMIT 1
        """,
        (int(plan_id), modo),
        fetch="one",
    )
    return bool(row)


def _validate_plan_bom_assignment(table_name, lot_no, modo, assigned_bom_rev):
    """Valida un cambio de assigned_bom_rev sobre un plan.

    Reglas:
      - El plan debe existir.
      - Si no hay cambio (rev nueva == rev actual), retorna (rev, None).
      - Si el plan ya inicio (started_at o status RUNNING/EN PROGRESO), rechaza.
      - Si Verificacion ya congelo snapshot KS, rechaza.
      - Si la rev nueva no existe en ks_bom_headers para el part_no, rechaza.

    Devuelve (normalized_rev, error_message_or_None).
    """
    normalized_rev = str(assigned_bom_rev or "").strip().upper() or None
    plan = execute_query(
        f"""
        SELECT id, part_no, status, started_at, assigned_bom_rev
        FROM {table_name}
        WHERE lot_no = %s
        LIMIT 1
        """,
        (lot_no,),
        fetch="one",
    )
    if not plan:
        return None, "Plan no encontrado"

    current_rev = str(plan.get("assigned_bom_rev") or "").strip().upper() or None
    if normalized_rev == current_rev:
        return normalized_rev, None

    status = str(plan.get("status") or "").strip().upper()
    if plan.get("started_at") or status in ("RUNNING", "EN PROGRESO"):
        return None, "No se puede cambiar la revision BOM de un plan iniciado"
    if _plan_has_ks_snapshot(plan.get("id"), modo):
        return None, "No se puede cambiar la revision BOM: Verificacion ya congelo snapshot del plan"

    if normalized_rev:
        exists = execute_query(
            """
            SELECT part_no
            FROM ks_bom_headers
            WHERE UPPER(part_no) = UPPER(%s)
              AND UPPER(bom_rev) = UPPER(%s)
            LIMIT 1
            """,
            (plan.get("part_no"), normalized_rev),
            fetch="one",
        )
        if not exists:
            return None, f"Revision BOM {normalized_rev} no existe en KS para {plan.get('part_no')}"
    return normalized_rev, None
