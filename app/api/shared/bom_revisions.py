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
