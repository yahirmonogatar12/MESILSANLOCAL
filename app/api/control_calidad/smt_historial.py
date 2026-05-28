"""Endpoints HTTP para historial de cambio de material SMT (version optimizada).

Consumido por 'Historial de cambio de material de SMT' en
LISTA_CONTROL_DE_CALIDAD.

Rutas:
  GET /smt/historial                  -> render HTML
  GET /api/historial_smt_data         -> JSON con filtros optimizados
  GET /api/smt/filtros/opciones       -> lineas y maquinas disponibles
  GET /api/smt/historial/data         -> JSON variante de compatibilidad

Migrado desde `app/smt_routes_clean.py` (2026-05-22). Mismo blueprint name
('smt_api') y mismas rutas; el frontend no requiere cambios.

NOTA: la ruta /api/historial_smt_data tambien la define
`smt_historial_simple.py` (migrado desde smt_routes_date_fixed.py).
Por orden de registro Flask, smt_historial_simple SE REGISTRA PRIMERO
(durante import de routes.py) y por tanto SU implementacion es la que
responde a esa URL. La version de aqui es codigo muerto pero se conserva
intencionalmente — mantener el comportamiento legacy hasta decidir
unificacion.

NOTA WF_003: conserva `get_db_connection()` directo con mysql.connector.
Migrar a execute_query es trivial aqui (no usa lastrowid ni transacciones),
queda pendiente para una pasada futura.
"""

import logging
import os
import traceback

import mysql.connector
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.api.shared import login_requerido
from app.db_mysql import get_connection


logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE'),
    'charset': 'utf8mb4'
}


bp = Blueprint('smt_api', __name__)


def get_db_connection():
    """Crear conexion a la base de datos"""
    return mysql.connector.connect(**DB_CONFIG)


@bp.route('/smt/historial', methods=['GET'])
def smt_historial():
    """Pagina HTML para visualizar historial SMT con filtros optimizados"""
    try:
        return render_template('Control de calidad/historial_cambio_material_smt_ajax.html')
    except Exception as e:
        logger.error(f"Error en /smt/historial: {e}")
        return f"Error cargando template: {e}", 500


@bp.route('/api/historial_smt_data', methods=['GET'])
def api_historial_smt_data():
    """API optimizada para cargar datos SMT con filtros.

    Filtros optimizados para cargar solo datos del dia actual por defecto.
    NOTA: en runtime, esta funcion NO responde — smt_historial_simple.py
    registra primero la misma ruta y gana en el routing de Flask.
    """
    try:
        folder = request.args.get('folder', '')
        part_name = request.args.get('part_name', '')
        result = request.args.get('result', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        linea = request.args.get('linea', '')
        maquina = request.args.get('maquina', '')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        filters = []
        params = []

        if date_from or date_to:
            if date_from:
                date_from_formatted = date_from.replace('-', '')
                filters.append('ScanDate >= %s')
                params.append(date_from_formatted)
            if date_to:
                date_to_formatted = date_to.replace('-', '')
                filters.append('ScanDate <= %s')
                params.append(date_to_formatted)
        elif not filters:
            from datetime import datetime, timedelta
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            filters.append('ScanDate >= %s')
            params.append(thirty_days_ago)

        if linea:
            filters.append('linea = %s')
            params.append(linea)

        if maquina:
            filters.append('maquina = %s')
            params.append(maquina)

        if folder:
            filters.append('(archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s)')
            params.extend([f"%{folder}%", f"%{folder}%", f"%{folder}%"])

        if part_name:
            filters.append('PartName LIKE %s')
            params.append(f"%{part_name}%")

        if result:
            filters.append('Result = %s')
            params.append(result)

        where_clause = 'WHERE ' + ' AND '.join(filters) if filters else ''

        query = f"""
            SELECT
                ScanDate, ScanTime, SlotNo, Result,
                LOTNO, Barcode, archivo, linea, maquina,
                PartName, Quantity, SEQ, Vendor,
                PreviousBarcode, Productdate, FeederBase
            FROM historial_cambio_material_smt
            {where_clause}
            ORDER BY id DESC
            LIMIT 1000
        """

        cursor.execute(query, params)
        results = cursor.fetchall()

        data = []
        for i, row in enumerate(results, 1):
            data.append({
                'index': i,
                'scan_date': row['ScanDate'],
                'scan_time': row['ScanTime'],
                'slotno': row['SlotNo'],
                'result': row['Result'],
                'lotno': row['LOTNO'],
                'serial': row['Barcode'],
                'barcode': row['Barcode'],
                'source_file': row['archivo'],
                'linea': row['linea'],
                'maquina': row['maquina'],
                'part_name': row['PartName'],
                'quantity': row['Quantity'],
                'seq': row['SEQ'],
                'vendor': row['Vendor'],
                'previousbarcode': row.get('PreviousBarcode', '') or '',
                'productdate': row.get('Productdate', row['ScanDate']) or row['ScanDate'],
                'feederbase': row.get('FeederBase', '') or '',
                'l_position': '',
                'm_position': ''
            })

        total_records = len(data)
        ok_count = sum(1 for row in data if row['result'] == 'OK')
        ng_count = sum(1 for row in data if row['result'] == 'NG')

        stats = {
            'total': total_records,
            'ok': ok_count,
            'ng': ng_count
        }

        response_data = {
            'success': True,
            'data': data,
            'stats': stats,
            'total': total_records,
            'message': f'Encontrados {total_records} registros'
        }

        cursor.close()
        conn.close()

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error en /api/historial_smt_data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'stats': {'total': 0, 'ok': 0, 'ng': 0},
            'total': 0
        }), 500


@bp.route('/api/smt/filtros/opciones', methods=['GET'])
def get_filtros_opciones():
    """Obtener opciones disponibles para los filtros (lineas, maquinas)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT DISTINCT linea
            FROM historial_cambio_material_smt
            WHERE linea IS NOT NULL AND linea != ''
            ORDER BY linea
        """)
        lineas = [row['linea'] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT maquina
            FROM historial_cambio_material_smt
            WHERE maquina IS NOT NULL AND maquina != ''
            ORDER BY maquina
        """)
        maquinas = [row['maquina'] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'lineas': lineas,
            'maquinas': maquinas
        })

    except Exception as e:
        logger.error(f"Error en filtros opciones: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/smt/historial/data', methods=['GET'])
def get_smt_historial_data():
    """API endpoint para obtener datos del historial SMT (compatibilidad)"""
    try:
        folder = request.args.get('folder', '')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if folder:
            cursor.execute("""
                SELECT
                    ScanDate, ScanTime, SlotNo, Result,
                    LOTNO, Barcode, archivo, linea, maquina,
                    PartName, Quantity, SEQ, Vendor,
                    PreviousBarcode, Productdate, FeederBase
                FROM historial_cambio_material_smt
                WHERE (archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s)
                ORDER BY ScanDate DESC, ScanTime DESC
                LIMIT 1000
            """, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        else:
            cursor.execute("""
                SELECT
                    ScanDate, ScanTime, SlotNo, Result,
                    LOTNO, Barcode, archivo, linea, maquina,
                    PartName, Quantity, SEQ, Vendor,
                    PreviousBarcode, Productdate, FeederBase
                FROM historial_cambio_material_smt
                ORDER BY ScanDate DESC, ScanTime DESC
                LIMIT 1000
            """)

        results = cursor.fetchall()

        data = []
        for row in results:
            data.append({
                'scan_date': row['ScanDate'],
                'scan_time': row['ScanTime'],
                'slot_no': row['SlotNo'],
                'result': row['Result'],
                'lot_no': row['LOTNO'],
                'barcode': row['Barcode'],
                'source_file': row['archivo'],
                'linea': row['linea'],
                'maquina': row['maquina'],
                'part_name': row['PartName'],
                'quantity': row['Quantity'],
                'seq': row['SEQ'],
                'vendor': row['Vendor'],
                'previousbarcode': row.get('PreviousBarcode', '') or '',
                'productdate': row.get('Productdate', row['ScanDate']) or row['ScanDate'],
                'feederbase': row.get('FeederBase', '') or ''
            })

        total_records = len(data)
        ok_count = sum(1 for row in data if row['result'] == 'OK')
        ng_count = sum(1 for row in data if row['result'] == 'NG')

        stats = {
            'total': total_records,
            'ok': ok_count,
            'ng': ng_count
        }

        return jsonify({
            'success': True,
            'data': data,
            'stats': stats,
            'total': total_records
        })

    except Exception as e:
        logger.error(f"Error en /api/smt/historial/data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'stats': {'total': 0, 'ok': 0, 'ng': 0},
            'total': 0
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


# ---------------------------------------------------------------------------
# Fase 3.3 (2026-05-28): rutas legacy /historial-cambio-material-smt[-ajax]
# migradas desde routes.py. Renderizan el mismo template que /smt/historial
# (definido arriba); las URLs distintas se preservan porque la sidebar
# LISTA_CONTROL_DE_CALIDAD las usa.
# ---------------------------------------------------------------------------


@bp.route("/historial-cambio-material-smt")
@login_requerido
def historial_cambio_material_smt():
    """Página del historial de cambio de material de SMT"""
    try:
        return render_template("Control de calidad/historial_cambio_material_smt.html")
    except Exception as e:
        print(f"Error al cargar historial de cambio de material SMT: {e}")
        return f"Error al cargar la página: {str(e)}", 500


@bp.route("/historial-cambio-material-smt-ajax")
def historial_cambio_material_smt_ajax():
    if "usuario" not in session:
        return redirect(url_for("auth_sesion.login"))
    try:
        return render_template(
            "Control de calidad/historial_cambio_material_smt_ajax.html"
        )
    except Exception as e:
        print(f"Error en historial_cambio_material_smt_ajax: {e}")
        return f"Error interno del servidor: {e}", 500


# ---------------------------------------------------------------------------
# Fase 4 (2026-05-28): 2 endpoints "latest" migrados desde routes.py.
# Consumidos por el panel "Control de Operacion SMT" para hacer match contra
# BOM con el ultimo material escaneado por (linea, maquina, SlotNo).
# `convertir_linea_smt` se trae junto porque solo lo usa la variante v2.
# ---------------------------------------------------------------------------


def convertir_linea_smt(linea_nombre):
    """Convierte nombres de linea SMT a formato de BD (SMT A -> 1line, etc.)"""
    conversion = {
        "SMT A": "1line",
        "SMT B": "2line",
        "SMT C": "3line",
        "SMT D": "4line",
    }
    return conversion.get(linea_nombre, linea_nombre)


@bp.route("/api/historial_smt_latest", methods=["GET"])
@login_requerido
def api_historial_smt_latest():
    """Devuelve el ultimo escaneo por (linea, maquina, SlotNo) desde la tabla
    historial_cambio_material_smt. Pensado para el panel de Control de Operacion SMT
    que requiere el ultimo material escaneado para hacer match con el BOM.

    Parametros:
      - linea: opcional. Ej: 'SMT B'. Si se omite, devuelve para todas las lineas.
    """
    try:
        linea = request.args.get("linea", "").strip()

        conn = get_connection()
        cursor = conn.cursor()

        where_sub = ""
        params = []
        if linea:
            where_sub = "WHERE linea = %s"
            params.append(linea)

        # Seleccionar el ultimo registro por grupo usando fecha_subida
        query = f"""
            SELECT h.id, h.linea, h.maquina, h.archivo, h.ScanDate, h.ScanTime,
                   h.SlotNo, h.Result, h.PreviousBarcode, h.Productdate,
                   h.PartName, h.Quantity, h.SEQ, h.Vendor, h.LOTNO,
                   h.Barcode, h.FeederBase, h.fecha_subida,
                   CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                        WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                        ELSE 'UNKNOWN' END AS side_norm
            FROM historial_cambio_material_smt h
            INNER JOIN (
                SELECT linea, maquina, SlotNo,
                       CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                            WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                            ELSE 'UNKNOWN' END AS side_norm,
                       MAX(fecha_subida) AS max_fecha
                FROM historial_cambio_material_smt
                {where_sub}
                GROUP BY linea, maquina, SlotNo, side_norm
            ) m
            ON h.linea = m.linea AND h.maquina = m.maquina
               AND h.SlotNo = m.SlotNo AND h.fecha_subida = m.max_fecha
               AND (
                    (CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                          WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                          ELSE 'UNKNOWN' END) = m.side_norm
               )
            {("WHERE h.linea = %s" if linea else "")}
            ORDER BY h.linea, h.maquina, h.SlotNo, side_norm
        """

        if linea:
            cursor.execute(query, params + params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()

        data = []
        for r in rows:
            linea_v = r[1] if len(r) > 1 else ""
            maquina_v = r[2] if len(r) > 2 else ""
            scan_date = r[4] if len(r) > 4 else ""
            scan_time = r[5] if len(r) > 5 else ""
            slot_no = r[6] if len(r) > 6 else ""
            part_name = r[10] if len(r) > 10 else ""
            quantity = r[11] if len(r) > 11 else 0
            vendor = r[13] if len(r) > 13 else ""
            feeder_base = r[16] if len(r) > 16 else ""

            formatted = {
                "linea": linea_v,
                "maquina": maquina_v,
                "Equipment": maquina_v,
                "SlotNo": slot_no,
                "FeederBase": feeder_base,
                "RegistDate": scan_date,
                "fecha_formateada": scan_date,
                "PartName": part_name,
                "Quantity": quantity,
                "Vendor": vendor,
                "ScanDate": scan_date,
                "ScanTime": scan_time,
            }
            data.append(formatted)

        cursor.close()
        conn.close()

        return jsonify({"success": True, "data": data, "total": len(data)})
    except Exception as e:
        print(f"Error en api_historial_smt_latest: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


# Variante robusta con lado FRONT/REAR agrupado explicitamente
@bp.route("/api/historial_smt_latest_v2", methods=["GET"])
@login_requerido
def api_historial_smt_latest_v2():
    try:
        linea_input = request.args.get("linea", "").strip()
        linea = convertir_linea_smt(linea_input)

        conn = get_connection()
        cursor = conn.cursor()

        where_sub = ""
        params = []
        if linea:
            where_sub = "WHERE linea = %s"
            params.append(linea)

        query = f"""
            SELECT h.id, h.linea, h.maquina, h.archivo, h.ScanDate, h.ScanTime,
                   h.SlotNo, h.Result, h.PreviousBarcode, h.Productdate,
                   h.PartName, h.Quantity, h.SEQ, h.Vendor, h.LOTNO,
                   h.Barcode, h.FeederBase, h.fecha_subida,
                   CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                        WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                        ELSE 'UNKNOWN' END AS side_norm
            FROM historial_cambio_material_smt h
            INNER JOIN (
                SELECT linea, maquina, SlotNo,
                       (CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                             WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                             ELSE 'UNKNOWN' END) AS side_norm,
                       MAX(fecha_subida) AS max_fecha
                FROM historial_cambio_material_smt
                {where_sub}
                GROUP BY linea, maquina, SlotNo,
                         (CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                               WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                               ELSE 'UNKNOWN' END)
            ) m
              ON h.linea = m.linea AND h.maquina = m.maquina
             AND h.SlotNo = m.SlotNo AND h.fecha_subida = m.max_fecha
             AND (
                 (CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                       WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                       ELSE 'UNKNOWN' END) = m.side_norm
             )
            {("WHERE h.linea = %s" if linea else "")}
            ORDER BY h.linea, h.maquina, h.SlotNo, m.side_norm
        """

        if linea:
            cursor.execute(query, params + params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()
        data = []
        for r in rows:
            linea_v = r[1] if len(r) > 1 else ""
            maquina_v = r[2] if len(r) > 2 else ""
            scan_date = r[4] if len(r) > 4 else ""
            scan_time = r[5] if len(r) > 5 else ""
            slot_no = r[6] if len(r) > 6 else ""
            part_name = r[10] if len(r) > 10 else ""
            quantity = r[11] if len(r) > 11 else 0
            vendor = r[13] if len(r) > 13 else ""
            feeder_base = r[16] if len(r) > 16 else ""

            formatted = {
                "linea": linea_v,
                "maquina": maquina_v,
                "Equipment": maquina_v,
                "SlotNo": slot_no,
                "FeederBase": feeder_base,
                "RegistDate": scan_date,
                "fecha_formateada": scan_date,
                "PartName": part_name,
                "Quantity": quantity,
                "Vendor": vendor,
                "ScanDate": scan_date,
                "ScanTime": scan_time,
            }
            data.append(formatted)

        cursor.close()
        conn.close()

        return jsonify({"success": True, "data": data, "total": len(data)})
    except Exception as e:
        print("Error en api_historial_smt_latest_v2:", e)
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500
