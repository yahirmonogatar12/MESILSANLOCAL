"""Helpers compartidos para generacion de lot_no en planes ASSY/IMD/SMT.

Consumidores:
  - app/routes.py                                       (rutas SCAN/operacion sobre plan_main)
  - app/api/control_produccion/plan_assy.py             (rutas /api/plan/*)
  - app/api/control_produccion/plan_imd.py              (rutas /api/plan-imd/*)
  - app/api/control_produccion/plan_smt.py              (rutas /api/plan-smt/*)

Antes de 2026-05-26 estas 2 funciones existian duplicadas en plan_assy.py,
plan_smt.py y routes.py con codigo identico. Esta consolidacion las mueve a
single source-of-truth.

Sin cambios de comportamiento.
"""

from datetime import datetime

from app.db_mysql import execute_query


def _fp_safe_date(s):
    """Parsear string ISO-8601 (primeros 10 chars) a date, None si invalido."""
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _fp_generate_lot_no(fecha):
    """Generar lot_no unico para plan ASSY: ASSYLINE-YYMMDD-NNN.

    Cuenta los lot_no existentes con el mismo prefijo en plan_main y
    devuelve el siguiente correlativo.
    """
    try:
        fecha_str = fecha.strftime("%y%m%d")
        prefix = f"ASSYLINE-{fecha_str}"
        row = execute_query(
            "SELECT COUNT(*) AS c FROM plan_main WHERE lot_no LIKE %s",
            (f"{prefix}%",),
            fetch="one",
        )
        count = 0
        if row:
            if isinstance(row, dict):
                count = (
                    list(row.values())[0]
                    if len(row.values()) == 1
                    else (row.get("c") or row.get("COUNT(*)") or 0)
                )
            else:
                count = row[0]
        return f"{prefix}-{int(count) + 1:03d}"
    except Exception:
        return f"ASSYLINE-{fecha.strftime('%y%m%d')}-001"
