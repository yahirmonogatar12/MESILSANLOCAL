"""Casos de uso de valorizacion de inventario."""

import logging

from flask import session

from app.api.control_material.costing_core.resolver import (
    fetch_lot_row,
    resolve_control_material_cost,
    upsert_inventory_cost,
)
from app.api.control_material.invoice_core.constants import ERROR_INTERNO, MONEDA_DEFAULT
from app.api.control_material.invoice_core.normalizers import normalizar_pallet_no, row_to_json
from app.api.shared import conexion_o_error, dict_cursor, sanitizar_texto

logger = logging.getLogger(__name__)


def _usuario_actual():
    return session.get("usuario") or "SISTEMA"


def _db():
    conn, error_response = conexion_o_error()
    if error_response:
        return None, None, ({"success": False, "error": "Base de datos no disponible"}, 503)
    return conn, dict_cursor(conn), None


def _int_param(args, form, name, default, min_value, max_value):
    try:
        value = int(args.get(name, form.get(name, default)))
    except (TypeError, ValueError):
        value = default
    return min(max(value, min_value), max_value)


def valuation_filters(args):
    params = []
    where = ["1=1"]

    numero_parte = sanitizar_texto(args.get("numero_parte"), 120)
    codigo = sanitizar_texto(args.get("codigo_material_recibido"), 120)
    pallet = sanitizar_texto(args.get("pallet_no"), 50)
    fuente = sanitizar_texto(args.get("fuente_costo"), 40).upper()
    include_zero = str(args.get("include_zero_stock") or "").lower() in ("1", "true", "yes", "si", "on")

    if not include_zero:
        where.append("COALESCE(il.stock_actual, cma.cantidad_actual, 0) > 0")
    if numero_parte:
        where.append("COALESCE(il.numero_parte, cma.numero_parte) LIKE %s")
        params.append(f"%{numero_parte}%")
    if codigo:
        where.append("COALESCE(il.codigo_material_recibido, cma.codigo_material_recibido) LIKE %s")
        params.append(f"%{codigo}%")
    if pallet:
        where.append("COALESCE(ilc.pallet_no, cma.pallet_no) = %s")
        params.append(normalizar_pallet_no(pallet))
    if fuente in {"INVOICE", "CONTROL_MATERIAL", "SIN_COSTO"}:
        where.append("COALESCE(ilc.fuente_costo, 'SIN_COSTO') = %s")
        params.append(fuente)

    return where, params


def valuation_base_sql(where):
    return f"""
        SELECT
          il.codigo_material_recibido AS codigo_material_recibido,
          COALESCE(il.numero_parte, cma.numero_parte) AS numero_parte_sistema,
          COALESCE(il.numero_lote, cma.numero_lote_material) AS numero_lote,
          COALESCE(il.total_entrada, cma.cantidad_actual, 0) AS cantidad_lote,
          COALESCE(il.stock_actual, 0) AS stock_actual,
          COALESCE(il.unidad_medida, cma.unidad_medida, 'EA') AS unidad_medida,
          COALESCE(ilc.pallet_no_original, cma.pallet_no_original) AS pallet_no_original,
          COALESCE(ilc.pallet_no, cma.pallet_no) AS pallet_no,
          COALESCE(ilc.vendedor, cma.vendedor) AS vendedor,
          cma.numero_invoice,
          COALESCE(ilc.costo_unitario, 0) AS costo_unitario,
          COALESCE(ilc.moneda, %s) AS moneda,
          COALESCE(ilc.fuente_costo, 'SIN_COSTO') AS fuente_costo,
          COALESCE(ilc.es_estimado, 1) AS es_estimado,
          ilc.invoice_id,
          ilc.invoice_line_id,
          ilc.packing_line_id,
          ilc.link_id,
          ilc.fecha_actualizacion,
          (COALESCE(il.stock_actual, 0) * COALESCE(ilc.costo_unitario, 0)) AS valor_total
        FROM inventario_lotes il
        LEFT JOIN control_material_almacen cma
          ON cma.codigo_material_recibido = il.codigo_material_recibido
        LEFT JOIN inventario_lote_costos ilc
          ON ilc.codigo_material_recibido = il.codigo_material_recibido
        WHERE {' AND '.join(where)}
          AND (cma.cancelado = 0 OR cma.cancelado IS NULL)
    """


def list_valuation(args):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        limit = min(max(int(args.get("limit", 500)), 1), 5000)
        offset = max(int(args.get("offset", 0)), 0)
        where, params = valuation_filters(args)
        base = valuation_base_sql(where)
        count_params = [MONEDA_DEFAULT] + params
        cursor.execute(f"SELECT COUNT(*) AS total FROM ({base}) t", count_params)
        total = int((cursor.fetchone() or {}).get("total") or 0)
        cursor.execute(
            base + " ORDER BY numero_parte_sistema, codigo_material_recibido LIMIT %s OFFSET %s",
            count_params + [limit, offset],
        )
        records = [row_to_json(r) for r in (cursor.fetchall() or [])]
        return {"success": True, "records": records, "total": total, "limit": limit, "offset": offset}, 200
    except Exception as exc:
        logger.exception("Error listando valorizacion: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def valuation_summary(args):
    conn, cursor, error = _db()
    if error:
        return error
    try:
        where, params = valuation_filters(args)
        base = valuation_base_sql(where)
        cursor.execute(
            f"""
            SELECT
              fuente_costo,
              moneda,
              COUNT(*) AS lotes,
              SUM(stock_actual) AS stock_total,
              SUM(valor_total) AS valor_total
            FROM ({base}) t
            GROUP BY fuente_costo, moneda
            ORDER BY fuente_costo, moneda
            """,
            [MONEDA_DEFAULT] + params,
        )
        return {"success": True, "records": [row_to_json(r) for r in (cursor.fetchall() or [])]}, 200
    except Exception as exc:
        logger.exception("Error summary valorizacion: %s", exc)
        return {"success": False, "error": ERROR_INTERNO}, 500
    finally:
        cursor.close()
        conn.close()


def _latest_material_cost_sql():
    return """
        SELECT mc.numero_parte, mc.vendedor, mc.costo_unitario_material, mc.moneda
        FROM material_costos mc
        JOIN (
          SELECT numero_parte, vendedor, MAX(id) AS max_id
          FROM material_costos
          GROUP BY numero_parte, vendedor
        ) latest_cost_id
          ON latest_cost_id.max_id = mc.id
    """


def _backfill_cost_joins_sql():
    latest_cost = _latest_material_cost_sql()
    return """
        LEFT JOIN ({latest_cost}) vendor_cost
          ON vendor_cost.numero_parte = il.numero_parte
         AND vendor_cost.vendedor = NULLIF(TRIM(COALESCE(cma.vendedor, '')), '')
        LEFT JOIN (
          SELECT single_cost.*
          FROM ({latest_cost}) single_cost
          JOIN (
            SELECT numero_parte, COUNT(*) AS vendor_count
            FROM ({latest_cost}) counted_costs
            GROUP BY numero_parte
          ) vendor_counts
            ON vendor_counts.numero_parte = single_cost.numero_parte
           AND vendor_counts.vendor_count = 1
        ) unique_part_cost
          ON unique_part_cost.numero_parte = il.numero_parte
         AND NULLIF(TRIM(COALESCE(cma.vendedor, '')), '') IS NULL
    """.format(latest_cost=latest_cost)


def _backfill_has_control_cost_sql():
    return """
        (
          (
            NULLIF(TRIM(COALESCE(cma.vendedor, '')), '') IS NOT NULL
            AND vendor_cost.numero_parte IS NOT NULL
          )
          OR
          (
            NULLIF(TRIM(COALESCE(cma.vendedor, '')), '') IS NULL
            AND unique_part_cost.numero_parte IS NOT NULL
          )
        )
    """


def _backfill_cost_amount_sql():
    return "COALESCE(vendor_cost.costo_unitario_material, unique_part_cost.costo_unitario_material, 0)"


def _backfill_cost_currency_sql():
    return "COALESCE(vendor_cost.moneda, unique_part_cost.moneda, %s)"


def _backfill_summary(cursor):
    cursor.execute(
        f"""
        SELECT
          COUNT(*) AS total_lotes,
          SUM(CASE WHEN COALESCE(ilc.fuente_costo, '') = 'CONTROL_MATERIAL' THEN 1 ELSE 0 END) AS ya_tenian_costo,
          SUM(CASE WHEN COALESCE(ilc.fuente_costo, '') = 'INVOICE' THEN 1 ELSE 0 END) AS no_sobrescritos_invoice,
          SUM(
            CASE
              WHEN COALESCE(ilc.fuente_costo, '') NOT IN ('INVOICE', 'LISTA_COMPRAS', 'CONTROL_MATERIAL')
               AND {_backfill_has_control_cost_sql()}
              THEN 1 ELSE 0
            END
          ) AS asignados_control_material,
          SUM(
            CASE
              WHEN COALESCE(ilc.fuente_costo, '') NOT IN ('INVOICE', 'LISTA_COMPRAS', 'CONTROL_MATERIAL')
               AND NOT {_backfill_has_control_cost_sql()}
              THEN 1 ELSE 0
            END
          ) AS quedaron_sin_costo
        FROM inventario_lotes il
        LEFT JOIN control_material_almacen cma
          ON cma.codigo_material_recibido = il.codigo_material_recibido
        LEFT JOIN inventario_lote_costos ilc
          ON ilc.codigo_material_recibido = il.codigo_material_recibido
        {_backfill_cost_joins_sql()}
        WHERE il.stock_actual > 0
          AND (cma.cancelado = 0 OR cma.cancelado IS NULL)
        """
    )
    row = cursor.fetchone() or {}
    return {
        "total_lotes": int(row.get("total_lotes") or 0),
        "ya_tenian_costo": int(row.get("ya_tenian_costo") or 0),
        "asignados_control_material": int(row.get("asignados_control_material") or 0),
        "quedaron_sin_costo": int(row.get("quedaron_sin_costo") or 0),
        "no_sobrescritos_invoice": int(row.get("no_sobrescritos_invoice") or 0),
    }


def _backfill_candidate_rows(cursor, limit):
    cursor.execute(
        f"""
        SELECT
          il.codigo_material_recibido,
          COALESCE(il.numero_parte, cma.numero_parte) AS numero_parte_sistema,
          COALESCE(ilc.fuente_costo, '') AS fuente_costo,
          COALESCE(ilc.costo_unitario, 0) AS costo_unitario
        FROM inventario_lotes il
        LEFT JOIN control_material_almacen cma
          ON cma.codigo_material_recibido = il.codigo_material_recibido
        LEFT JOIN inventario_lote_costos ilc
          ON ilc.codigo_material_recibido = il.codigo_material_recibido
        {_backfill_cost_joins_sql()}
        WHERE il.stock_actual > 0
          AND (cma.cancelado = 0 OR cma.cancelado IS NULL)
          AND COALESCE(ilc.fuente_costo, '') NOT IN ('INVOICE', 'LISTA_COMPRAS', 'CONTROL_MATERIAL')
          AND {_backfill_has_control_cost_sql()}
        ORDER BY cma.fecha_recibo ASC, cma.id ASC, il.codigo_material_recibido ASC
        LIMIT %s
        """,
        (limit,),
    )
    return cursor.fetchall() or []


def _backfill_preview_rows(cursor, limit):
    cursor.execute(
        f"""
        SELECT
          il.codigo_material_recibido,
          COALESCE(il.numero_parte, cma.numero_parte) AS numero_parte_sistema,
          COALESCE(il.numero_lote, cma.numero_lote_material) AS numero_lote,
          COALESCE(il.stock_actual, 0) AS stock_actual,
          COALESCE(il.unidad_medida, cma.unidad_medida, 'EA') AS unidad_medida,
          cma.pallet_no,
          cma.vendedor,
          cma.numero_invoice,
          {_backfill_cost_amount_sql()} AS costo_unitario,
          {_backfill_cost_currency_sql()} AS moneda,
          (COALESCE(il.stock_actual, 0) * {_backfill_cost_amount_sql()}) AS valor_total
        FROM inventario_lotes il
        LEFT JOIN control_material_almacen cma
          ON cma.codigo_material_recibido = il.codigo_material_recibido
        LEFT JOIN inventario_lote_costos ilc
          ON ilc.codigo_material_recibido = il.codigo_material_recibido
        {_backfill_cost_joins_sql()}
        WHERE il.stock_actual > 0
          AND (cma.cancelado = 0 OR cma.cancelado IS NULL)
          AND COALESCE(ilc.fuente_costo, '') NOT IN ('INVOICE', 'LISTA_COMPRAS', 'CONTROL_MATERIAL')
          AND {_backfill_has_control_cost_sql()}
        ORDER BY cma.fecha_recibo ASC, cma.id ASC, il.codigo_material_recibido ASC
        LIMIT %s
        """,
        (MONEDA_DEFAULT, limit),
    )
    return [row_to_json(row) for row in (cursor.fetchall() or [])]


def backfill_valuation(args, form):
    dry_run = str(args.get("dry_run", form.get("dry_run", "1"))).lower() in ("1", "true", "yes", "si", "on")
    batch_size = _int_param(args, form, "batch_size", 500, 1, 5000)
    preview_limit = _int_param(args, form, "preview_limit", 1000, 1, 5000)
    conn, cursor, error = _db()
    if error:
        return error
    result = {
        "dry_run": dry_run,
        "batch_size": batch_size,
        "preview_limit": preview_limit,
        "procesados_lotes": 0,
        "asignables_control_material": 0,
        "pendientes_aplicables": 0,
    }
    try:
        summary_before = _backfill_summary(cursor)
        result.update(summary_before)
        result["asignables_control_material"] = summary_before["asignados_control_material"]
        result["pendientes_aplicables"] = summary_before["asignados_control_material"]
        if dry_run:
            preview_records = _backfill_preview_rows(cursor, preview_limit)
            result["preview_records"] = preview_records
            result["preview_total"] = summary_before["asignados_control_material"]
            result["preview_truncated"] = len(preview_records) < summary_before["asignados_control_material"]
            return {"success": True, **result}, 200

        cursor.execute("START TRANSACTION")
        rows = _backfill_candidate_rows(cursor, batch_size)
        usuario = _usuario_actual()
        result["asignados_control_material"] = 0
        result["procesados_lotes"] = len(rows)
        for row in rows:
            lot = fetch_lot_row(cursor, row["codigo_material_recibido"], for_update=not dry_run)
            if not lot:
                continue
            cost = resolve_control_material_cost(
                cursor,
                lot["numero_parte_sistema"],
                lot.get("vendedor"),
            )
            if cost:
                result["asignados_control_material"] += 1
                upsert_inventory_cost(cursor, lot, cost, usuario)
        summary_after = _backfill_summary(cursor)
        result.update({
            "total_lotes": summary_after["total_lotes"],
            "ya_tenian_costo": summary_after["ya_tenian_costo"],
            "quedaron_sin_costo": summary_after["quedaron_sin_costo"],
            "no_sobrescritos_invoice": summary_after["no_sobrescritos_invoice"],
            "pendientes_aplicables": summary_after["asignados_control_material"],
        })
        conn.commit()
        return {"success": True, **result}, 200
    except Exception as exc:
        if not dry_run:
            conn.rollback()
        logger.exception("Error backfill valorizacion: %s", exc)
        return {"success": False, "error": ERROR_INTERNO, **result}, 500
    finally:
        cursor.close()
        conn.close()
