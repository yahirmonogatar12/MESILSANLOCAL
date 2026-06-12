"""Helpers para mantener el catalogo maestro de modelos.

`ks_part_catalog` nacio como carga inicial desde ERP/K-system, pero las altas
nuevas se hacen desde Control de modelos. Este modulo asegura que esas altas
locales tambien tengan una fila de catalogo sin modificar registros ya
existentes del ERP.
"""

import json
import logging
from typing import Any, Dict, Optional

from app.db_mysql import execute_query

logger = logging.getLogger(__name__)


VALID_BOM_KINDS = {"MASTER", "SMD", "IMD", "OTHER"}

SMD_TO_RAW_FIELDS = {
    "part_no": ("part_no",),
    "model": ("model", "item_name"),
    "main_display": ("main_display", "maindisplay"),
    "c_t": ("c_t", "ct"),
    "uph": ("uph",),
    "hora_dia": ("hora_dia", "horadia"),
    "linea": ("linea",),
    "project": ("project",),
}


def _clean_text(value: Any, max_len: Optional[int] = None, uppercase: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if uppercase:
        text = text.upper()
    if max_len and len(text) > max_len:
        text = text[:max_len]
    return text


def normalize_part_no(value: Any) -> str:
    return _clean_text(value, max_len=128, uppercase=True)


def family_prefix_from_part_no(part_no: str) -> str:
    text = normalize_part_no(part_no)
    return text[:-2] if len(text) > 2 else text


def bom_suffix_from_part_no(part_no: str) -> Optional[str]:
    text = normalize_part_no(part_no)
    if len(text) <= 2:
        return None
    return text[-2:]


def _normalize_bom_kind(value: Any, default: str = "MASTER") -> str:
    text = _clean_text(value, uppercase=True)
    if text in VALID_BOM_KINDS:
        return text
    return default


def _first_non_empty(payload: Dict[str, Any], *keys: str, max_len: Optional[int] = None) -> Optional[str]:
    for key in keys:
        text = _clean_text(payload.get(key), max_len=max_len)
        if text:
            return text
    return None


def infer_bom_kind(source_table: str, payload: Dict[str, Any]) -> str:
    explicit = payload.get("bom_kind") or payload.get("erp_bom_kind")
    if explicit:
        return _normalize_bom_kind(explicit)

    if source_table == "raw_smd":
        probe = " ".join(
            _clean_text(payload.get(k), uppercase=True)
            for k in ("linea", "model", "maindisplay", "process")
        )
        return "IMD" if "IMD" in probe else "SMD"

    return "MASTER"


def ensure_raw_model_for_smd(
    payload: Dict[str, Any],
    *,
    user_name: str = "Sistema",
) -> Dict[str, Any]:
    """Asegura el modelo padre en raw para una configuracion raw_smd.

    raw es el modelo/base local; raw_smd cuelga de ese modelo por part_no. Si
    el padre ya existe, no lo actualiza para no pisar configuraciones hechas en
    Control de modelos o importadas inicialmente desde ERP.
    """
    part_no = normalize_part_no(payload.get("part_no"))
    if not part_no:
        return {"ok": True, "skipped": True, "reason": "part_no vacio"}

    try:
        existing = execute_query(
            """
            SELECT id, part_no
            FROM raw
            WHERE TRIM(UPPER(part_no)) = %s
            LIMIT 1
            """,
            (part_no,),
            fetch="one",
        )
        if existing:
            return {
                "ok": True,
                "part_no": part_no,
                "exists": True,
                "inserted": False,
                "raw_id": existing.get("id"),
            }

        raw_user = (
            _first_non_empty(payload, "Usuario", "usuario", max_len=255)
            or _clean_text(user_name, max_len=255)
            or "Sistema"
        )

        insert_data: Dict[str, Any] = {"part_no": part_no}
        for raw_field, source_fields in SMD_TO_RAW_FIELDS.items():
            if raw_field == "part_no":
                continue
            value = _first_non_empty(payload, *source_fields, max_len=255)
            if value:
                insert_data[raw_field] = value

        insert_data["Usuario"] = raw_user

        columns = list(insert_data.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        columns_sql = ", ".join([f"`{column}`" for column in columns])

        affected = execute_query(
            f"INSERT INTO raw ({columns_sql}) VALUES ({placeholders})",
            tuple(insert_data[column] for column in columns),
        )
        return {
            "ok": True,
            "part_no": part_no,
            "exists": False,
            "inserted": bool(affected),
        }
    except Exception as e:
        logger.error(f"Error asegurando raw para {part_no} desde raw_smd: {e}")
        return {"ok": False, "part_no": part_no, "error": str(e)}


def ensure_ks_part_catalog_for_model(
    payload: Dict[str, Any],
    *,
    source_table: str,
    user_name: str = "Sistema",
) -> Dict[str, Any]:
    """Inserta el modelo en ks_part_catalog si aun no existe.

    No actualiza registros existentes. Esto protege la carga inicial del ERP y
    evita pisar metadatos oficiales si el modelo ya estaba catalogado.
    """
    part_no = normalize_part_no(payload.get("part_no"))
    if not part_no:
        return {"ok": True, "skipped": True, "reason": "part_no vacio"}

    item_name = (
        _clean_text(payload.get("model"), max_len=255)
        or _clean_text(payload.get("item_name"), max_len=255)
        or _clean_text(payload.get("maindisplay"), max_len=255)
        or part_no
    )
    family_prefix = family_prefix_from_part_no(part_no)
    bom_kind = infer_bom_kind(source_table, payload)
    raw_json = json.dumps(
        {
            "source": "CONTROL_MODELOS",
            "source_table": source_table,
            "created_by": _clean_text(user_name, max_len=128),
        },
        ensure_ascii=False,
    )

    try:
        affected = execute_query(
            """
            INSERT IGNORE INTO ks_part_catalog
                (part_no, item_seq, item_name, spec, unit, maker, item_class,
                 root_part_no, family_prefix, bom_suffix, bom_kind, is_active,
                 raw_json, source_updated_at, synced_at)
            VALUES
                (%s, NULL, %s, NULL, NULL, NULL, NULL,
                 %s, %s, %s, %s, 1,
                 %s, NOW(), NOW())
            """,
            (
                part_no,
                item_name,
                part_no,
                family_prefix,
                bom_suffix_from_part_no(part_no),
                bom_kind,
                raw_json,
            ),
        )
        return {
            "ok": True,
            "part_no": part_no,
            "inserted": bool(affected),
            "bom_kind": bom_kind,
        }
    except Exception as e:
        logger.error(f"Error asegurando ks_part_catalog para {part_no}: {e}")
        return {"ok": False, "part_no": part_no, "error": str(e)}
