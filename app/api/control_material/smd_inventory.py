"""SMD Rolls Inventory API - inventario automatico de rollos SMD.

Integra con el sistema existente de movimientos y mounters.

Rutas:
  GET  /smd/inventario                                          -> render HTML
  GET  /api/smd/inventario/rollos                               -> JSON list
  GET  /api/smd/inventario/rollo/<id>                           -> JSON detalle + historial
  POST /api/smd/inventario/rollo/<id>/marcar_agotado            -> stored proc
  POST /api/smd/inventario/rollo/<id>/asignar_mounter           -> JSON update
  GET  /api/smd/inventario/stats                                -> JSON stats
  POST /api/smd/inventario/sincronizar                          -> JSON sync con almacen

Migrado desde `app/smd_inventory_api.py` (2026-05-22).

NOTA WF_003: este modulo conserva `get_db_connection()` con `mysql.connector`
directo en lugar de `execute_query()` porque usa:
  - `cursor.callproc('sp_marcar_rollo_agotado', ...)` (stored procedure)
  - `cursor.lastrowid` (obtener ID del INSERT)
  - Transacciones multi-query con commit explicito (sincronizar_inventario)
Que `execute_query()` no soporta. Cuando se generalice ese helper estos
endpoints podran migrar tambien.
"""

import logging
import os
from datetime import datetime

import mysql.connector
from flask import Blueprint, jsonify, render_template, request


logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
    "charset": "utf8mb4",
}


bp = Blueprint("smd_inventory_api", __name__)


def get_db_connection():
    """Crear conexion directa a la base de datos.

    Ver nota WF_003 en docstring del modulo.
    """
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        raise


@bp.route("/smd/inventario", methods=["GET"])
def ver_inventario_rollos():
    """Pagina HTML para visualizar el inventario de rollos SMD"""
    return render_template("Control de material/inventario_rollos_smd.html")


@bp.route("/api/smd/inventario/rollos", methods=["GET"])
def get_inventario_rollos():
    """API para obtener el inventario actual de rollos SMD con filtros"""
    try:
        estado = request.args.get("estado", "")
        numero_parte = request.args.get("numero_parte", "")
        linea = request.args.get("linea", "")
        maquina = request.args.get("maquina", "")
        fecha_desde = request.args.get("fecha_desde", "")
        fecha_hasta = request.args.get("fecha_hasta", "")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        filters = []
        params = []

        if estado:
            filters.append("estado = %s")
            params.append(estado)

        if numero_parte:
            filters.append("numero_parte LIKE %s")
            params.append(f"%{numero_parte}%")

        if linea:
            filters.append("linea_asignada LIKE %s")
            params.append(f"%{linea}%")

        if maquina:
            filters.append("maquina_asignada LIKE %s")
            params.append(f"%{maquina}%")

        if fecha_desde:
            filters.append("fecha_entrada >= %s")
            params.append(fecha_desde)

        if fecha_hasta:
            filters.append("fecha_entrada <= %s")
            params.append(fecha_hasta + " 23:59:59")

        where_clause = "WHERE " + " AND ".join(filters) if filters else ""

        query = f"""
            SELECT *,
                   TIMESTAMPDIFF(HOUR, fecha_entrada, COALESCE(fecha_ultimo_uso, NOW())) as horas_en_smd,
                   CASE
                       WHEN cantidad_actual = 0 THEN 'AGOTADO'
                       WHEN linea_asignada IS NOT NULL THEN 'ASIGNADO'
                       WHEN estado = 'ACTIVO' THEN 'DISPONIBLE'
                       ELSE estado
                   END as estado_detallado
            FROM InventarioRollosSMD
            {where_clause}
            ORDER BY fecha_entrada DESC
        """

        cursor.execute(query, params)
        rollos = cursor.fetchall()

        for rollo in rollos:
            for key, value in rollo.items():
                if isinstance(value, datetime):
                    rollo[key] = value.strftime("%Y-%m-%d %H:%M:%S") if value else None

        cursor.execute("""
            SELECT
                COUNT(*) as total_rollos,
                COUNT(CASE WHEN estado = 'ACTIVO' THEN 1 END) as activos,
                COUNT(CASE WHEN estado = 'EN_USO' THEN 1 END) as en_uso,
                COUNT(CASE WHEN estado = 'AGOTADO' THEN 1 END) as agotados,
                COUNT(CASE WHEN linea_asignada IS NOT NULL THEN 1 END) as asignados,
                SUM(cantidad_actual) as cantidad_total_disponible
            FROM InventarioRollosSMD
            WHERE estado != 'RETIRADO'
        """)

        stats = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "data": rollos,
            "stats": stats,
            "total": len(rollos),
            "message": f"Encontrados {len(rollos)} rollos"
        })

    except Exception as e:
        logger.error(f"Error en get_inventario_rollos: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "data": [],
            "stats": {}
        }), 500


@bp.route("/api/smd/inventario/rollo/<int:rollo_id>", methods=["GET"])
def get_detalle_rollo(rollo_id):
    """Obtener detalle completo de un rollo especifico con su historial"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *,
                   TIMESTAMPDIFF(HOUR, fecha_entrada, COALESCE(fecha_ultimo_uso, NOW())) as horas_en_smd
            FROM InventarioRollosSMD
            WHERE id = %s
        """, (rollo_id,))

        rollo = cursor.fetchone()

        if not rollo:
            return jsonify({"success": False, "error": "Rollo no encontrado"}), 404

        cursor.execute("""
            SELECT *
            FROM HistorialMovimientosRollosSMD
            WHERE rollo_id = %s
            ORDER BY fecha_movimiento DESC
        """, (rollo_id,))

        historial = cursor.fetchall()

        if isinstance(rollo.get("fecha_entrada"), datetime):
            for key, value in rollo.items():
                if isinstance(value, datetime):
                    rollo[key] = value.strftime("%Y-%m-%d %H:%M:%S") if value else None

        for registro in historial:
            for key, value in registro.items():
                if isinstance(value, datetime):
                    registro[key] = value.strftime("%Y-%m-%d %H:%M:%S") if value else None

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "rollo": rollo,
            "historial": historial
        })

    except Exception as e:
        logger.error(f"Error en get_detalle_rollo: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/smd/inventario/rollo/<int:rollo_id>/marcar_agotado", methods=["POST"])
def marcar_rollo_agotado(rollo_id):
    """Marcar un rollo como agotado manualmente"""
    try:
        data = request.get_json() or {}
        observaciones = data.get("observaciones", "Marcado como agotado manualmente")
        usuario = data.get("usuario", "USUARIO_WEB")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Llamar al procedimiento almacenado
        cursor.callproc("sp_marcar_rollo_agotado", (rollo_id, observaciones))

        # Actualizar el usuario en el historial
        cursor.execute("""
            UPDATE HistorialMovimientosRollosSMD
            SET usuario = %s
            WHERE rollo_id = %s
            AND tipo_movimiento = 'AGOTAMIENTO'
            ORDER BY fecha_movimiento DESC
            LIMIT 1
        """, (usuario, rollo_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Rollo marcado como agotado correctamente"
        })

    except Exception as e:
        logger.error(f"Error en marcar_rollo_agotado: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/smd/inventario/rollo/<int:rollo_id>/asignar_mounter", methods=["POST"])
def asignar_rollo_mounter(rollo_id):
    """Asignar un rollo manualmente a una mounter especifica"""
    try:
        data = request.get_json() or {}
        linea = data.get("linea", "")
        maquina = data.get("maquina", "")
        slot = data.get("slot", "")
        usuario = data.get("usuario", "USUARIO_WEB")

        if not all([linea, maquina, slot]):
            return jsonify({
                "success": False,
                "error": "Linea, maquina y slot son requeridos"
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM InventarioRollosSMD
            WHERE id = %s AND estado IN ('ACTIVO', 'EN_USO')
        """, (rollo_id,))

        rollo = cursor.fetchone()

        if not rollo:
            return jsonify({
                "success": False,
                "error": "Rollo no encontrado o no disponible"
            }), 404

        cursor.execute("""
            UPDATE InventarioRollosSMD
            SET
                linea_asignada = %s,
                maquina_asignada = %s,
                slot_asignado = %s,
                fecha_asignacion = CURRENT_TIMESTAMP,
                estado = 'EN_USO',
                actualizado_en = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (linea, maquina, slot, rollo_id))

        cursor.execute("""
            INSERT INTO HistorialMovimientosRollosSMD (
                rollo_id,
                tipo_movimiento,
                descripcion,
                cantidad_antes,
                cantidad_despues,
                linea,
                maquina,
                slot,
                usuario
            ) VALUES (%s, 'ASIGNACION', %s, %s, %s, %s, %s, %s, %s)
        """, (
            rollo_id,
            f"Asignacion manual a {linea}/{maquina} slot {slot}",
            rollo["cantidad_actual"],
            rollo["cantidad_actual"],
            linea,
            maquina,
            slot,
            usuario
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Rollo asignado a {linea}/{maquina} slot {slot} correctamente"
        })

    except Exception as e:
        logger.error(f"Error en asignar_rollo_mounter: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/smd/inventario/stats", methods=["GET"])
def get_inventario_stats():
    """Obtener estadisticas generales del inventario SMD"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                COUNT(*) as total_rollos,
                COUNT(CASE WHEN estado = 'ACTIVO' THEN 1 END) as activos,
                COUNT(CASE WHEN estado = 'EN_USO' THEN 1 END) as en_uso,
                COUNT(CASE WHEN estado = 'AGOTADO' THEN 1 END) as agotados,
                COUNT(CASE WHEN linea_asignada IS NOT NULL THEN 1 END) as asignados,
                SUM(cantidad_actual) as cantidad_total_disponible,
                COUNT(DISTINCT numero_parte) as partes_unicas
            FROM InventarioRollosSMD
            WHERE estado != 'RETIRADO'
        """)

        stats_principales = cursor.fetchone()

        cursor.execute("""
            SELECT
                numero_parte,
                COUNT(*) as cantidad_rollos,
                SUM(cantidad_actual) as cantidad_total,
                AVG(cantidad_actual) as promedio_por_rollo
            FROM InventarioRollosSMD
            WHERE estado != 'RETIRADO'
            GROUP BY numero_parte
            ORDER BY cantidad_rollos DESC
            LIMIT 5
        """)

        top_partes = cursor.fetchall()

        cursor.execute("""
            SELECT
                COUNT(*) as movimientos_24h,
                COUNT(CASE WHEN tipo_movimiento = 'ENTRADA' THEN 1 END) as entradas_24h,
                COUNT(CASE WHEN tipo_movimiento = 'ASIGNACION' THEN 1 END) as asignaciones_24h,
                COUNT(CASE WHEN tipo_movimiento = 'AGOTAMIENTO' THEN 1 END) as agotamientos_24h
            FROM HistorialMovimientosRollosSMD
            WHERE fecha_movimiento >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)

        actividad_24h = cursor.fetchone()

        cursor.execute("""
            SELECT
                CONCAT(COALESCE(linea_asignada, 'Sin asignar'), ' / ', COALESCE(maquina_asignada, 'Sin asignar')) as ubicacion,
                COUNT(*) as cantidad_rollos
            FROM InventarioRollosSMD
            WHERE estado IN ('ACTIVO', 'EN_USO')
            GROUP BY linea_asignada, maquina_asignada
            ORDER BY cantidad_rollos DESC
            LIMIT 10
        """)

        por_ubicacion = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "stats": {
                "principales": stats_principales,
                "top_partes": top_partes,
                "actividad_24h": actividad_24h,
                "por_ubicacion": por_ubicacion
            }
        })

    except Exception as e:
        logger.error(f"Error en get_inventario_stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/smd/inventario/sincronizar", methods=["POST"])
def sincronizar_inventario():
    """Sincronizar inventario SMD con movimientos recientes del almacen"""
    try:
        data = request.get_json() or {}
        horas_atras = data.get("horas_atras", 24)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM movimientosimd_smd
            WHERE tipo = 'SALIDA'
            AND ubicacion LIKE '%SMD%'
            AND fecha >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            AND id NOT IN (
                SELECT movimiento_origen_id
                FROM InventarioRollosSMD
                WHERE movimiento_origen_id IS NOT NULL
            )
        """, (horas_atras,))

        movimientos_pendientes = cursor.fetchall()

        rollos_creados = 0

        for mov in movimientos_pendientes:
            cursor.execute("""
                SELECT COUNT(*) as cuenta
                FROM InventarioRollosSMD
                WHERE numero_parte = %s AND estado = 'ACTIVO'
            """, (mov["nparte"],))

            existe_activo = cursor.fetchone()["cuenta"]

            if existe_activo == 0:
                cursor.execute("""
                    INSERT INTO InventarioRollosSMD (
                        numero_parte,
                        codigo_barras,
                        cantidad_inicial,
                        cantidad_actual,
                        area_smd,
                        origen_almacen,
                        movimiento_origen_id,
                        observaciones
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    mov["nparte"],
                    f"SMD_{mov['nparte']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    mov["cantidad"],
                    mov["cantidad"],
                    "SMD_PRODUCTION",
                    mov["ubicacion"],
                    mov["id"],
                    f"Sincronizacion automatica desde movimiento ID {mov['id']}. Carro: {mov.get('carro', 'N/A')}"
                ))

                rollo_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO HistorialMovimientosRollosSMD (
                        rollo_id,
                        tipo_movimiento,
                        descripcion,
                        cantidad_antes,
                        cantidad_despues,
                        usuario
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    rollo_id,
                    "ENTRADA",
                    f"Sincronizacion desde almacen: {mov['ubicacion']}",
                    0,
                    mov["cantidad"],
                    "SINCRONIZACION_AUTO"
                ))

                rollos_creados += 1

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Sincronizacion completada: {rollos_creados} rollos creados",
            "rollos_creados": rollos_creados,
            "movimientos_procesados": len(movimientos_pendientes)
        })

    except Exception as e:
        logger.error(f"Error en sincronizar_inventario: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
