"""Endpoints HTTP del modulo Plan SMD + Agente Generador.

Migrado desde `app/routes.py` (2026-05-25). Sin cambios funcionales.

Rutas:
  POST   /api/plan-smd          -> guardar renglones del plan SMD
  POST   /api/plan-smd/import   -> importar plan SMD desde CSV/JSON
  POST   /api/generar-plan-smd  -> AGENTE GENERADOR (faltantes por codigo_modelo)
  GET    /api/plan-smd/list     -> listar runs/ciclos de produccion

Bootstrap `crear_tabla_plan_smd` y `crear_tabla_plan_smd_runs` se reexportan
desde `app/routes.py` para preservar consumidores legacy (`startup_init.py`).
"""

import io
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request, session

from app.db_mysql import execute_query


def login_requerido(f):
    """Proxy del decorador real definido en `app.routes`."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import routes as _r
        return _r.login_requerido(f)(*args, **kwargs)

    return decorated_function


def obtener_fecha_hora_mexico():
    """Proxy del helper definido en `app.routes`."""
    from app import routes as _r
    return _r.obtener_fecha_hora_mexico()


bp = Blueprint("control_produccion_plan_smd", __name__)


def crear_tabla_plan_smd():
    """Crear tabla plan_smd si no existe"""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS plan_smd (
            id INT AUTO_INCREMENT PRIMARY KEY,
            linea VARCHAR(32) NOT NULL,
            lote VARCHAR(32) NOT NULL COMMENT 'Código WO para trazabilidad',
            nparte VARCHAR(64) NOT NULL,
            modelo VARCHAR(64) NOT NULL,
            tipo VARCHAR(32) NOT NULL DEFAULT 'Main',
            turno VARCHAR(32) NOT NULL,
            ct VARCHAR(32) DEFAULT '',
            uph VARCHAR(32) DEFAULT '',
            qty INT NOT NULL DEFAULT 0,
            fisico INT NOT NULL DEFAULT 0,
            falta INT NOT NULL DEFAULT 0,
            pct INT NOT NULL DEFAULT 0,
            comentarios TEXT NULL,
            fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            usuario_creacion VARCHAR(64) DEFAULT 'sistema',
            INDEX idx_lote (lote),
            INDEX idx_modelo (modelo),
            INDEX idx_nparte (nparte)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        execute_query(query)
        print(" Tabla plan_smd creada/verificada")
    except Exception as e:
        print(f" Error creando tabla plan_smd: {e}")


# crear_tabla_plan_smd movido a app/startup_init.py

@bp.route("/api/plan-smd", methods=["POST"])
@login_requerido
def api_plan_smd_guardar():
    """API para guardar renglones del plan SMD"""
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({"error": "Se esperaba un arreglo de renglones"}), 400

        usuario = session.get("usuario", "sistema")
        renglones_guardados = 0

        for renglon in data:
            # Validar campos requeridos
            if not all(
                k in renglon
                for k in ["linea", "lote", "nparte", "modelo", "tipo", "turno", "qty"]
            ):
                continue

            query = """
            INSERT INTO plan_smd (linea, lote, nparte, modelo, tipo, turno, ct, uph,
                                 qty, fisico, falta, pct, comentarios, usuario_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            params = (
                renglon["linea"],
                renglon["lote"],
                renglon["nparte"],
                renglon["modelo"],
                renglon["tipo"],
                renglon["turno"],
                renglon.get("ct", ""),
                renglon.get("uph", ""),
                renglon["qty"],
                renglon.get("fisico", 0),
                renglon.get("falta", renglon["qty"]),
                renglon.get("pct", 0),
                renglon.get("comentarios", ""),
                usuario,
            )

            execute_query(query, params)
            renglones_guardados += 1

        return jsonify(
            {
                "success": True,
                "renglones_guardados": renglones_guardados,
                "message": f"Se guardaron {renglones_guardados} renglones del plan SMD",
            }
        )

    except Exception as e:
        print(f" Error guardando plan SMD: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route("/api/generar-plan-smd", methods=["POST"])
@login_requerido
def api_generar_plan_smd():
    """🤖 AGENTE GENERADOR DE PLAN SMD - Sólo faltantes por codigo_modelo"""
    try:
        # Parámetros de entrada
        data = request.get_json() or {}

        # Parámetros con defaults
        q = data.get("q", "")
        estados = data.get("estados", ["CREADA", "PLANIFICADA"])
        desde = data.get("desde", "")
        hasta = data.get("hasta", "")
        linea_default = data.get("linea_default", "SMT A")
        turno_default = data.get("turno_default", "DIA")
        tipo_default = data.get("tipo_default", "Main")
        limite_wo = data.get("limite_wo", None)
        dry_run = data.get("dry_run", False)

        print(f"🤖 AGENTE PLAN SMD iniciado - DRY_RUN: {dry_run}")

        # Variables de seguimiento
        wo_procesadas = 0
        renglones_generados = 0
        qty_total_plan = 0
        faltante_total_plan = 0
        inventario_acumulado_considerado = 0
        lotes = []
        omitidas_sin_faltante = []
        incidencias = []
        renglones_plan = []

        # 1. TRAER WORK ORDERS
        try:
            fecha_actual = obtener_fecha_hora_mexico().strftime("%Y%m%d")

            # Construir filtros para work orders
            filtros = {
                "q": q,
                "estado": ",".join(estados),
                "desde": desde,
                "hasta": hasta,
            }

            # Simular llamada a API interna
            query_wo = """
            SELECT id, codigo_wo, codigo_po, modelo, nombre_modelo, codigo_modelo,
                   cantidad_planeada, fecha_operacion, estado
            FROM work_orders
            WHERE estado IN ({})
            """.format(",".join(["%s"] * len(estados)))

            params_wo = estados[:]

            if q:
                query_wo += " AND (codigo_wo LIKE %s OR codigo_po LIKE %s OR modelo LIKE %s OR codigo_modelo LIKE %s)"
                q_param = f"%{q}%"
                params_wo.extend([q_param, q_param, q_param, q_param])

            if desde:
                query_wo += " AND fecha_operacion >= %s"
                params_wo.append(desde)

            if hasta:
                query_wo += " AND fecha_operacion <= %s"
                params_wo.append(hasta)

            query_wo += " ORDER BY fecha_operacion ASC, codigo_modelo ASC"

            if limite_wo:
                query_wo += f" LIMIT {int(limite_wo)}"

            work_orders = execute_query(query_wo, params_wo, fetch="all")
            print(f"📋 Encontradas {len(work_orders)} work orders")

        except Exception as e:
            incidencias.append(
                {
                    "wo": "SISTEMA",
                    "tipo": "error_consulta_wo",
                    "detalle": f"Error consultando work orders: {str(e)}",
                }
            )
            work_orders = []

        # 2. PROCESAR CADA WO
        lote_counter = 1

        for wo in work_orders:
            wo_procesadas += 1
            codigo_wo = wo["codigo_wo"]
            codigo_modelo = wo["codigo_modelo"]
            cantidad_planeada = wo["cantidad_planeada"]

            # Validaciones
            if not codigo_modelo or not codigo_modelo.strip():
                incidencias.append(
                    {
                        "wo": codigo_wo,
                        "tipo": "sin_codigo_modelo",
                        "detalle": "La WO no tiene codigo_modelo",
                    }
                )
                continue

            if not cantidad_planeada or cantidad_planeada <= 0:
                incidencias.append(
                    {
                        "wo": codigo_wo,
                        "tipo": "cantidad_invalida",
                        "detalle": f"Cantidad planeada inválida: {cantidad_planeada}",
                    }
                )
                continue

            # 3. CONSULTAR INVENTARIO POR CODIGO_MODELO
            try:
                query_inv = """
                SELECT SUM(stock_total) as inventario_total
                FROM inv_resumen_modelo
                WHERE nparte = %s
                """

                resultado_inv = execute_query(query_inv, (codigo_modelo,), fetch="one")
                inventario_total = (
                    resultado_inv["inventario_total"]
                    if resultado_inv and resultado_inv["inventario_total"]
                    else 0
                )
                inventario_acumulado_considerado += inventario_total

                print(
                    f"📦 WO {codigo_wo} | Modelo: {codigo_modelo} | Planeado: {cantidad_planeada} | Inventario: {inventario_total}"
                )

            except Exception as e:
                incidencias.append(
                    {
                        "wo": codigo_wo,
                        "tipo": "inventario_endpoint_error",
                        "detalle": f"Error consultando inventario: {str(e)}",
                    }
                )
                inventario_total = 0

            # 4. CALCULAR FALTANTE
            faltante = max(0, cantidad_planeada - inventario_total)

            if faltante <= 0:
                omitidas_sin_faltante.append(codigo_wo)
                print(
                    f"⏭️ WO {codigo_wo} omitida - Sin faltante (inventario suficiente)"
                )
                continue

            # 5. GENERAR RENGLÓN DEL PLAN
            lote = f"P{fecha_actual}-{lote_counter:03d}"
            lotes.append(lote)
            lote_counter += 1

            renglon = {
                "linea": linea_default,
                "lote": lote,
                "nparte": codigo_modelo,  #  Usamos codigo_modelo
                "modelo": codigo_modelo,  #  Usamos codigo_modelo
                "tipo": tipo_default,
                "turno": turno_default,
                "ct": "",
                "uph": "",
                "qty": faltante,
                "fisico": int(inventario_total),  #  Usar el inventario real consultado
                "falta": faltante,
                "pct": int((inventario_total / cantidad_planeada) * 100)
                if cantidad_planeada > 0
                else 0,  #  Calcular porcentaje real
                "comentarios": f"Inventario: {int(inventario_total)} | Requerido: {int(cantidad_planeada)} | Faltante: {faltante}",
            }

            renglones_plan.append(renglon)
            renglones_generados += 1
            qty_total_plan += faltante
            faltante_total_plan += faltante

            print(
                f" Renglón generado - Lote: {lote} | Modelo: {codigo_modelo} | QTY: {faltante}"
            )

        # 6. GUARDAR SI NO ES DRY_RUN
        if not dry_run and renglones_plan:
            try:
                usuario = session.get("usuario", "sistema")
                renglones_guardados = 0

                for renglon in renglones_plan:
                    query_insert = """
                    INSERT INTO plan_smd (linea, lote, nparte, modelo, tipo, turno, ct, uph,
                                         qty, fisico, falta, pct, comentarios, usuario_creacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    params_insert = (
                        renglon["linea"],
                        renglon["lote"],
                        renglon["nparte"],
                        renglon["modelo"],
                        renglon["tipo"],
                        renglon["turno"],
                        renglon["ct"],
                        renglon["uph"],
                        renglon["qty"],
                        renglon["fisico"],
                        renglon["falta"],
                        renglon["pct"],
                        renglon["comentarios"],
                        usuario,
                    )

                    execute_query(query_insert, params_insert)
                    renglones_guardados += 1

                print(f" Plan guardado: {renglones_guardados} renglones")

            except Exception as e:
                incidencias.append(
                    {
                        "wo": "SISTEMA",
                        "tipo": "error_guardado",
                        "detalle": f"Error guardando plan: {str(e)}",
                    }
                )

        # 7. RESUMEN FINAL
        resumen = {
            "wo_procesadas": wo_procesadas,
            "renglones_generados": renglones_generados,
            "qty_total_plan": qty_total_plan,
            "faltante_total_plan": faltante_total_plan,
            "inventario_acumulado_considerado": inventario_acumulado_considerado,
            "lotes": lotes,
            "omitidas_sin_faltante": omitidas_sin_faltante,
            "incidencias": incidencias,
            "dry_run": dry_run,
            "plan_generado": renglones_plan
            if dry_run
            else f"{len(renglones_plan)} renglones guardados",
        }

        print(
            f"🎯 AGENTE COMPLETADO - Generados: {renglones_generados} | Total QTY: {qty_total_plan}"
        )

        return jsonify(resumen)

    except Exception as e:
        print(f" Error en Agente PLAN SMD: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-smd/import", methods=["POST"])
@login_requerido
def api_plan_smd_import():
    """API para importar plan SMD desde CSV o JSON"""
    try:
        usuario = session.get("usuario", "sistema")

        # Verificar si es archivo o JSON
        if "file" in request.files:
            # Importar desde archivo CSV
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "No se seleccionó archivo"}), 400

            if not file.filename.lower().endswith(".csv"):
                return jsonify({"error": "Solo se permiten archivos CSV"}), 400

            # Leer CSV
            import csv
            import io

            content = file.read().decode("utf-8")
            csv_reader = csv.DictReader(io.StringIO(content))
            data = list(csv_reader)

        else:
            # Importar desde JSON
            data = request.get_json()
            if not data or not isinstance(data, list):
                return jsonify({"error": "Se esperaba un arreglo JSON"}), 400

        # Validar y procesar datos
        inserted = 0
        updated = 0
        errors = []

        for i, row in enumerate(data):
            try:
                # Validar campos requeridos
                if not all(k in row for k in ["linea", "lote", "modelo"]):
                    errors.append(
                        f"Fila {i + 1}: Faltan campos requeridos (linea, lote, modelo)"
                    )
                    continue

                # Normalizar datos
                linea = str(row.get("linea", "")).strip().upper()
                lote = str(row.get("lote", "")).strip()
                nparte = str(row.get("nparte", "")).strip()
                modelo = str(row.get("modelo", "")).strip().upper()
                tipo = str(row.get("tipo", "")).strip()
                turno = str(row.get("turno", "")).strip().upper()
                ct = str(row.get("ct", "")).strip()
                uph = str(row.get("uph", "")).strip()
                qty = float(row.get("qty", 0)) if row.get("qty") else 0
                fisico = float(row.get("fisico", 0)) if row.get("fisico") else 0
                comentarios = str(row.get("comentarios", "")).strip()
                usuario_creacion = str(row.get("usuario_creacion", usuario)).strip()

                # Validaciones
                if qty < 0:
                    errors.append(f"Fila {i + 1}: qty debe ser >= 0")
                    continue

                if fisico < 0:
                    errors.append(f"Fila {i + 1}: fisico debe ser >= 0")
                    continue

                # Calcular falta y pct
                falta = max(qty - fisico, 0)
                pct = round((qty - falta) * 100 / qty) if qty > 0 else 0

                # Verificar si ya existe (upsert por lote, modelo)
                check_query = """
                SELECT id FROM plan_smd
                WHERE lote = %s AND modelo = %s
                """
                existing = execute_query(check_query, (lote, modelo), fetch="one")

                if existing:
                    # Actualizar registro existente
                    update_query = """
                    UPDATE plan_smd SET
                        linea = %s, nparte = %s, tipo = %s, turno = %s, ct = %s, uph = %s,
                        qty = %s, fisico = %s, falta = %s, pct = %s, comentarios = %s
                    WHERE id = %s
                    """
                    execute_query(
                        update_query,
                        (
                            linea,
                            nparte,
                            tipo,
                            turno,
                            ct,
                            uph,
                            qty,
                            fisico,
                            falta,
                            pct,
                            comentarios,
                            existing["id"],
                        ),
                    )
                    updated += 1
                else:
                    # Insertar nuevo registro
                    insert_query = """
                    INSERT INTO plan_smd (linea, lote, nparte, modelo, tipo, turno, ct, uph,
                                         qty, fisico, falta, pct, comentarios, usuario_creacion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    execute_query(
                        insert_query,
                        (
                            linea,
                            lote,
                            nparte,
                            modelo,
                            tipo,
                            turno,
                            ct,
                            uph,
                            qty,
                            fisico,
                            falta,
                            pct,
                            comentarios,
                            usuario_creacion,
                        ),
                    )
                    inserted += 1

            except Exception as e:
                errors.append(f"Fila {i + 1}: {str(e)}")
                continue

        return jsonify(
            {
                "success": True,
                "inserted": inserted,
                "updated": updated,
                "errors": errors,
                "message": f"Importación completada: {inserted} insertados, {updated} actualizados",
            }
        )

    except Exception as e:
        print(f" Error importando plan SMD: {e}")
        return jsonify({"error": str(e)}), 500

def crear_tabla_plan_smd_runs():
    """Crear tabla de ejecuciones del plan SMD (ciclos de producción)."""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS plan_smd_runs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            plan_id INT,
            linea VARCHAR(32) NOT NULL,
            lot_no VARCHAR(32) NOT NULL,
            uph DECIMAL(20,6) DEFAULT 0,
            ct DECIMAL(20,6) DEFAULT 0,
            qty_plan INT DEFAULT 0,
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME NULL,
            status ENUM('RUNNING','ENDED') DEFAULT 'RUNNING',
            created_by VARCHAR(64) DEFAULT 'sistema',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_linea (linea),
            INDEX idx_lot (lot_no),
            INDEX idx_plan (plan_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        execute_query(query)
        # Asegurar estado PAUSED disponible
        try:
            execute_query(
                "ALTER TABLE plan_smd_runs MODIFY status ENUM('RUNNING','PAUSED','ENDED') DEFAULT 'RUNNING'"
            )
        except Exception as e:
            print(f"  (info) Status PAUSED: {str(e)[:60]}")
        # Columnas adicionales para baseline y conteo AOI
        try:
            execute_query(
                "ALTER TABLE plan_smd_runs ADD COLUMN aoi_model VARCHAR(64) NULL"
            )
        except Exception as e:
            print(f"  (info) aoi_model: {str(e)[:60]}")
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_line_no INT NULL")
        except Exception as e:
            print(f"  (info) aoi_line_no: {str(e)[:60]}")
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_baseline INT NULL")
        except Exception as e:
            print(f"  (info) aoi_baseline: {str(e)[:60]}")
        try:
            execute_query(
                "ALTER TABLE plan_smd_runs ADD COLUMN aoi_baseline_shift_date DATE NULL"
            )
        except Exception as e:
            print(f"  (info) aoi_baseline_shift_date: {str(e)[:60]}")
        try:
            execute_query(
                "ALTER TABLE plan_smd_runs ADD COLUMN aoi_baseline_shift VARCHAR(16) NULL"
            )
        except Exception as e:
            print(f"  (info) aoi_baseline_shift: {str(e)[:60]}")
        try:
            execute_query(
                "ALTER TABLE plan_smd_runs ADD COLUMN aoi_produced_final INT NULL"
            )
        except Exception as e:
            print(f"  (info) aoi_produced_final: {str(e)[:60]}")
        print(" Tabla plan_smd_runs creada/verificada")
    except Exception as e:
        print(f"⚠️  Error creando tabla plan_smd_runs (continuando): {str(e)[:100]}")


# crear_tabla_plan_smd_runs movido a app/startup_init.py


@bp.route("/api/plan-smd/list", methods=["GET"])
def api_plan_smd_list():
    """Listar renglones de plan_smd con filtros simples.

    Params opcionales:
    - q (busca en modelo, nparte, lote)
    - linea, desde, hasta
    - solo_pendientes: muestra planes del dia actual + planeados/iniciados de fechas anteriores
    - plan_id: consulta especifica de un plan
    """
    try:
        q = (request.args.get("q") or "").strip()
        linea = (request.args.get("linea") or "").strip()
        desde = (request.args.get("desde") or "").strip()
        hasta = (request.args.get("hasta") or "").strip()
        solo_pendientes = request.args.get("solo_pendientes") == "true"
        plan_id = (request.args.get("plan_id") or "").strip()

        sql = [
            "SELECT p.id, p.linea, p.lote, p.nparte, p.modelo, p.tipo, p.turno, p.ct, p.uph, p.qty, p.fisico, p.falta, p.pct, p.comentarios, p.fecha_creacion, COALESCE(t.estado,'PLANEADO') AS estatus,",
            "r.status AS run_status, r.id AS run_id, r.start_time AS run_start_time, r.end_time AS run_end_time,",
            "r.aoi_model, r.aoi_line_no, r.aoi_baseline, r.aoi_baseline_shift_date, r.aoi_baseline_shift, r.aoi_produced_final",
            "FROM plan_smd p",
            "LEFT JOIN (SELECT lot_no, MAX(updated_at) AS mx FROM trazabilidad GROUP BY lot_no) tm ON tm.lot_no = p.lote",
            "LEFT JOIN trazabilidad t ON t.lot_no = tm.lot_no AND t.updated_at = tm.mx",
            "LEFT JOIN (SELECT plan_id, status, id, start_time, end_time, aoi_model, aoi_line_no, aoi_baseline, aoi_baseline_shift_date, aoi_baseline_shift, aoi_produced_final, ROW_NUMBER() OVER (PARTITION BY plan_id ORDER BY start_time DESC) as rn FROM plan_smd_runs) r ON r.plan_id = p.id AND r.rn = 1",
            "WHERE 1=1",
        ]
        params = []

        # Si se especifica un plan_id especifico, solo buscar ese plan (ignorar todos los demas filtros)
        if plan_id:
            sql.append("AND p.id = %s")
            params.append(plan_id)
        else:
            # Logica para "Mostrar Pendientes":
            # - Planes del dia actual (cualquier estado)
            # - Planes PLANEADOS de fechas anteriores (trabajo no iniciado)
            # - Planes INICIADOS de fechas anteriores (trabajo en progreso)
            if solo_pendientes:
                # Obtener fecha actual
                from datetime import datetime

                fecha_actual = datetime.now().strftime("%Y-%m-%d")

                # Condicion: (planes del dia actual de cualquier estado) OR (planes PLANEADOS/INICIADOS de fechas anteriores)
                sql.append(
                    "AND ((fecha_creacion >= %s AND fecha_creacion <= %s) OR (fecha_creacion < %s AND (COALESCE(t.estado,'PLANEADO') IN ('PLANEADO', 'INICIADO') OR r.status = 'RUNNING') AND (r.status IS NULL OR r.status != 'ENDED')))"
                )
                params.extend([fecha_actual, fecha_actual + " 23:59:59", fecha_actual])
            else:
                # Aplicar filtros de fecha normales cuando no es solo_pendientes
                if desde:
                    sql.append("AND fecha_creacion >= %s")
                    params.append(desde)
                if hasta:
                    sql.append("AND fecha_creacion <= %s")
                    # Incluir todo el dia hasta 23:59:59
                    params.append(hasta + " 23:59:59")

            if q:
                sql.append("AND (modelo LIKE %s OR nparte LIKE %s OR lote LIKE %s)")
                params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
            if linea:
                sql.append("AND p.linea = %s")
                params.append(linea)
                print(f"Filtro de linea aplicado en API: '{linea}'")

        sql.append("ORDER BY fecha_creacion DESC, id DESC")

        rows = (
            execute_query(" ".join(sql), tuple(params) if params else None, fetch="all")
            or []
        )

        # Enriquecer con producido estimado desde runs
        try:
            if rows:
                lotes = [r.get("lote") for r in rows if r.get("lote")]
                if lotes:
                    placeholders = ",".join(["%s"] * len(lotes))
                    run_sql = f"""
                        SELECT lot_no, status, uph, qty_plan, start_time, end_time
                        FROM plan_smd_runs
                        WHERE lot_no IN ({placeholders})
                        ORDER BY start_time DESC
                    """
                    run_rows = execute_query(run_sql, tuple(lotes), fetch="all") or []
                    latest = {}
                    for rr in run_rows:
                        ln = rr.get("lot_no")
                        if ln and ln not in latest:
                            latest[ln] = rr
                    from datetime import datetime

                    now = datetime.now()
                    for r in rows:
                        lot = r.get("lote")
                        producido = 0
                        if lot and lot in latest:
                            rr = latest[lot]
                            try:
                                uph = float(rr.get("uph") or 0)
                            except Exception:
                                uph = 0.0
                            st = rr.get("start_time")
                            et = rr.get("end_time")
                            if uph and st:
                                elapsed_h = ((et or now) - st).total_seconds() / 3600.0
                                producido = int(
                                    min(
                                        int(r.get("qty") or 0),
                                        max(0.0, uph * elapsed_h),
                                    )
                                )
                        r["producido"] = producido
                        qty_val = int(r.get("qty") or 0)
                        r["falta"] = max(0, qty_val - producido)
                        r["pct"] = (
                            int(min(100, round((producido / qty_val) * 100)))
                            if qty_val
                            else 0
                        )
        except Exception as e:
            print(f"?? Error enriqueciendo producido en api_plan_smd_list: {e}")

        # OVERRIDE: Producido por AOI usando baseline del run (si existe)
        try:
            if rows:
                shift_order = {"DIA": 1, "TIEMPO_EXTRA": 2, "NOCHE": 3}
                for r in rows:
                    qty_val = int(r.get("qty") or 0)
                    if r.get("run_id") and r.get("id") is not None:
                        aoi_model = (r.get("aoi_model") or "").upper()
                        aoi_line_no = r.get("aoi_line_no")
                        bl = r.get("aoi_baseline")
                        bl_date = r.get("aoi_baseline_shift_date")
                        bl_shift = (
                            (r.get("aoi_baseline_shift") or "").strip()
                            if r.get("aoi_baseline_shift")
                            else ""
                        )
                        final_val = r.get("aoi_produced_final")
                        if final_val is not None:
                            producido = int(final_val or 0)
                            r["producido"] = producido
                            r["falta"] = max(0, qty_val - producido)
                            r["pct"] = (
                                int(min(100, round((producido / qty_val) * 100)))
                                if qty_val
                                else 0
                            )
                        elif (
                            aoi_model
                            and aoi_line_no
                            and bl is not None
                            and bl_date
                            and bl_shift
                        ):
                            agg_sql = """
                                SELECT shift_date, shift, SUM(piece_w) AS total
                                FROM aoi_file_log
                                WHERE model=%s AND line_no=%s AND shift_date >= %s
                                GROUP BY shift_date, shift
                                ORDER BY shift_date ASC
                            """
                            agg_rows = (
                                execute_query(
                                    agg_sql,
                                    (aoi_model, int(aoi_line_no), bl_date),
                                    fetch="all",
                                )
                                or []
                            )
                            total = 0
                            for ar in agg_rows:
                                sd = ar.get("shift_date")
                                sh = (ar.get("shift") or "").strip()
                                t = int(ar.get("total") or 0)
                                if not sd or not sh:
                                    continue
                                if str(sd) == str(bl_date) and sh == bl_shift:
                                    total += max(0, t - int(bl or 0))
                                else:
                                    if str(sd) == str(bl_date) and shift_order.get(
                                        sh, 0
                                    ) < shift_order.get(bl_shift, 0):
                                        continue
                                    total += t
                            r["producido"] = int(min(qty_val, max(0, total)))
                            r["falta"] = max(0, qty_val - r["producido"])
                            r["pct"] = (
                                int(min(100, round((r["producido"] / qty_val) * 100)))
                                if qty_val
                                else 0
                            )
        except Exception as e:
            print(f"?? Error override producido AOI en api_plan_smd_list: {e}")

        return jsonify({"success": True, "rows": rows, "count": len(rows)})
    except Exception as e:
        print(f"? Error en api_plan_smd_list: {e}")
        return jsonify({"success": False, "error": str(e)})

