# -*- coding: utf-8 -*-
"""
Plan SMD Routes - Rutas para el plan de producción SMD y ejecuciones (runs)
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
from ..database.db_mysql import execute_query

plan_smd_bp = Blueprint('plan_smd', __name__)

# ============================================================================
# DECORADOR DE AUTENTICACIÓN
# ============================================================================

def login_requerido(f):
    """Decorador para verificar que el usuario está autenticado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return jsonify({'error': 'No autorizado', 'redirect': '/login'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# INICIALIZACIÓN DE TABLAS
# ============================================================================

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
            execute_query("ALTER TABLE plan_smd_runs MODIFY status ENUM('RUNNING','PAUSED','ENDED') DEFAULT 'RUNNING'")
        except Exception as e:
            print(f"  (info) Status PAUSED: {str(e)[:60]}")
        # Columnas adicionales para baseline y conteo AOI
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_model VARCHAR(64) NULL")
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
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_baseline_shift_date DATE NULL")
        except Exception as e:
            print(f"  (info) aoi_baseline_shift_date: {str(e)[:60]}")
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_baseline_shift VARCHAR(16) NULL")
        except Exception as e:
            print(f"  (info) aoi_baseline_shift: {str(e)[:60]}")
        try:
            execute_query("ALTER TABLE plan_smd_runs ADD COLUMN aoi_produced_final INT NULL")
        except Exception as e:
            print(f"  (info) aoi_produced_final: {str(e)[:60]}")
        print("✅ Tabla plan_smd_runs creada/verificada")
    except Exception as e:
        print(f"⚠️ Error creando tabla plan_smd_runs (continuando): {str(e)[:100]}")


def crear_tabla_trazabilidad():
    """Crear tabla de trazabilidad (LOTE por WO/LINEA con estados)."""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS trazabilidad (
            id INT AUTO_INCREMENT PRIMARY KEY,
            linea VARCHAR(32) NOT NULL,
            lot_no VARCHAR(32) NOT NULL,
            plan_id INT NULL,
            codigo_wo VARCHAR(32) NULL,
            estado ENUM('PLANEADO','INICIADO','PAUSA','FINALIZADO') DEFAULT 'PLANEADO',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            usuario VARCHAR(64) DEFAULT 'sistema',
            INDEX idx_linea (linea),
            INDEX idx_lot (lot_no),
            INDEX idx_estado (estado)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        execute_query(query)
        print("✅ Tabla trazabilidad creada/verificada")
    except Exception as e:
        print(f"❌ Error creando tabla trazabilidad: {e}")


# ============================================================================
# API: LISTAR PLAN SMD
# ============================================================================

@plan_smd_bp.route('/api/plan-smd/list', methods=['GET'])
def api_plan_smd_list():
    """Listar renglones de plan_smd con filtros simples.

    Params opcionales: 
    - q (busca en modelo, nparte, lote)
    - linea, desde, hasta 
    - solo_pendientes: muestra planes del dia actual + planeados/iniciados de fechas anteriores
    - plan_id: consulta especifica de un plan
    """
    try:
        q = (request.args.get('q') or '').strip()
        linea = (request.args.get('linea') or '').strip()
        desde = (request.args.get('desde') or '').strip()
        hasta = (request.args.get('hasta') or '').strip()
        solo_pendientes = request.args.get('solo_pendientes') == 'true'
        plan_id = (request.args.get('plan_id') or '').strip()

        sql = [
            "SELECT p.id, p.linea, p.lote, p.nparte, p.modelo, p.tipo, p.turno, p.ct, p.uph, p.qty, p.fisico, p.falta, p.pct, p.comentarios, p.fecha_creacion, COALESCE(t.estado,'PLANEADO') AS estatus,",
            "r.status AS run_status, r.id AS run_id, r.start_time AS run_start_time, r.end_time AS run_end_time,",
            "r.aoi_model, r.aoi_line_no, r.aoi_baseline, r.aoi_baseline_shift_date, r.aoi_baseline_shift, r.aoi_produced_final",
            "FROM plan_smd p", 
            "LEFT JOIN (SELECT lot_no, MAX(updated_at) AS mx FROM trazabilidad GROUP BY lot_no) tm ON tm.lot_no = p.lote",
            "LEFT JOIN trazabilidad t ON t.lot_no = tm.lot_no AND t.updated_at = tm.mx",
            "LEFT JOIN (SELECT plan_id, status, id, start_time, end_time, aoi_model, aoi_line_no, aoi_baseline, aoi_baseline_shift_date, aoi_baseline_shift, aoi_produced_final, ROW_NUMBER() OVER (PARTITION BY plan_id ORDER BY start_time DESC) as rn FROM plan_smd_runs) r ON r.plan_id = p.id AND r.rn = 1",
            "WHERE 1=1"
        ]
        params = []
        
        # Si se especifica un plan_id específico, solo buscar ese plan (ignorar todos los demás filtros)
        if plan_id:
            sql.append("AND p.id = %s")
            params.append(plan_id)
        else:
            # Lógica para "Mostrar Pendientes": 
            # - Planes del día actual (cualquier estado)
            # - Planes PLANEADOS de fechas anteriores (trabajo no iniciado)
            # - Planes INICIADOS de fechas anteriores (trabajo en progreso)
            if solo_pendientes:
                # Obtener fecha actual
                fecha_actual = datetime.now().strftime('%Y-%m-%d')
                
                # Condición: (planes del día actual de cualquier estado) OR (planes PLANEADOS/INICIADOS de fechas anteriores)
                sql.append("AND ((fecha_creacion >= %s AND fecha_creacion <= %s) OR (fecha_creacion < %s AND (COALESCE(t.estado,'PLANEADO') IN ('PLANEADO', 'INICIADO') OR r.status = 'RUNNING') AND (r.status IS NULL OR r.status != 'ENDED')))")
                params.extend([fecha_actual, fecha_actual + ' 23:59:59', fecha_actual])
            else:
                # Aplicar filtros de fecha normales cuando no es solo_pendientes
                if desde:
                    sql.append("AND fecha_creacion >= %s")
                    params.append(desde)
                if hasta:
                    sql.append("AND fecha_creacion <= %s")
                    # Incluir todo el día hasta 23:59:59
                    params.append(hasta + ' 23:59:59')
            
            if q:
                sql.append("AND (modelo LIKE %s OR nparte LIKE %s OR lote LIKE %s)")
                params.extend([f"%{q}%", f"%{q}%", f"%{q}%"]) 
            if linea:
                sql.append("AND p.linea = %s")
                params.append(linea)
                print(f"Filtro de linea aplicado en API: '{linea}'")
            
        sql.append("ORDER BY fecha_creacion DESC, id DESC")

        rows = execute_query(" ".join(sql), tuple(params) if params else None, fetch='all') or []

        # Enriquecer con producido estimado desde runs
        try:
            if rows:
                lotes = [r.get('lote') for r in rows if r.get('lote')]
                if lotes:
                    placeholders = ','.join(['%s'] * len(lotes))
                    run_sql = f"""
                        SELECT lot_no, status, uph, qty_plan, start_time, end_time
                        FROM plan_smd_runs
                        WHERE lot_no IN ({placeholders})
                        ORDER BY start_time DESC
                    """
                    run_rows = execute_query(run_sql, tuple(lotes), fetch='all') or []
                    latest = {}
                    for rr in run_rows:
                        ln = rr.get('lot_no')
                        if ln and ln not in latest:
                            latest[ln] = rr
                    now = datetime.now()
                    for r in rows:
                        lot = r.get('lote')
                        producido = 0
                        if lot and lot in latest:
                            rr = latest[lot]
                            try:
                                uph = float(rr.get('uph') or 0)
                            except Exception:
                                uph = 0.0
                            st = rr.get('start_time')
                            et = rr.get('end_time')
                            if uph and st:
                                elapsed_h = ((et or now) - st).total_seconds() / 3600.0
                                producido = int(min(int(r.get('qty') or 0), max(0.0, uph * elapsed_h)))
                        r['producido'] = producido
                        qty_val = int(r.get('qty') or 0)
                        r['falta'] = max(0, qty_val - producido)
                        r['pct'] = int(min(100, round((producido / qty_val)*100))) if qty_val else 0
        except Exception as e:
            print(f"⚠️ Error enriqueciendo producido en api_plan_smd_list: {e}")

        # OVERRIDE: Producido por AOI usando baseline del run (si existe)
        try:
            if rows:
                shift_order = {'DIA': 1, 'TIEMPO_EXTRA': 2, 'NOCHE': 3}
                for r in rows:
                    qty_val = int(r.get('qty') or 0)
                    if r.get('run_id') and r.get('id') is not None:
                        aoi_model = (r.get('aoi_model') or '').upper()
                        aoi_line_no = r.get('aoi_line_no')
                        bl = r.get('aoi_baseline')
                        bl_date = r.get('aoi_baseline_shift_date')
                        bl_shift = (r.get('aoi_baseline_shift') or '').strip() if r.get('aoi_baseline_shift') else ''
                        final_val = r.get('aoi_produced_final')
                        if final_val is not None:
                            producido = int(final_val or 0)
                            r['producido'] = producido
                            r['falta'] = max(0, qty_val - producido)
                            r['pct'] = int(min(100, round((producido / qty_val) * 100))) if qty_val else 0
                        elif aoi_model and aoi_line_no and bl is not None and bl_date and bl_shift:
                            agg_sql = """
                                SELECT shift_date, shift, SUM(piece_w) AS total
                                FROM aoi_file_log
                                WHERE model=%s AND line_no=%s AND shift_date >= %s
                                GROUP BY shift_date, shift
                                ORDER BY shift_date ASC
                            """
                            agg_rows = execute_query(agg_sql, (aoi_model, int(aoi_line_no), bl_date), fetch='all') or []
                            total = 0
                            for ar in agg_rows:
                                sd = ar.get('shift_date')
                                sh = (ar.get('shift') or '').strip()
                                t = int(ar.get('total') or 0)
                                if not sd or not sh:
                                    continue
                                if str(sd) == str(bl_date) and sh == bl_shift:
                                    total += max(0, t - int(bl or 0))
                                else:
                                    if str(sd) == str(bl_date) and shift_order.get(sh, 0) < shift_order.get(bl_shift, 0):
                                        continue
                                    total += t
                            r['producido'] = int(min(qty_val, max(0, total)))
                            r['falta'] = max(0, qty_val - r['producido'])
                            r['pct'] = int(min(100, round((r['producido'] / qty_val) * 100))) if qty_val else 0
        except Exception as e:
            print(f"⚠️ Error override producido AOI en api_plan_smd_list: {e}")

        return jsonify({'success': True, 'rows': rows, 'count': len(rows)})
    except Exception as e:
        print(f"❌ Error en api_plan_smd_list: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def generar_lot_no_secuencial(q, like, prefix, fecha):
    """Genera un número de lote secuencial basado en la consulta"""
    last = execute_query(q, (like,), fetch='one')
    if last and last.get('lot_no'):
        try:
            seq = int(last['lot_no'].split('-')[-1]) + 1
        except Exception:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{fecha}-{seq:04d}"


def _map_line_no(s: str):
    """Convierte nombre de línea a número"""
    try:
        ss = (s or '').upper().strip()
        if ss.startswith('SMT '):
            ss = ss[4:].strip()
        if ss and ss[0].isalpha():
            return max(1, min(26, ord(ss[0]) - ord('A') + 1))
        if ss.isdigit():
            return int(ss)
    except Exception:
        pass
    return None


# ============================================================================
# API: INICIAR RUN
# ============================================================================

@plan_smd_bp.route('/api/plan-run/start', methods=['POST'])
def api_plan_run_start():
    """Iniciar un run de producción desde un renglón del plan.
    Body: { plan_id, linea?, lot_prefix? }
    """
    try:
        data = request.get_json(force=True) or {}
        plan_id = int(data.get('plan_id'))
        linea = (data.get('linea') or '').strip()
        lot_prefix = (data.get('lot_prefix') or 'I').strip() or 'I'
        usuario = session.get('nombre_completo', session.get('usuario', 'Sistema')).strip()

        # Obtener datos del plan
        plan_row = execute_query("SELECT * FROM plan_smd WHERE id=%s", (plan_id,), fetch='one')
        if not plan_row:
            return jsonify({'success': False, 'error': 'Plan no encontrado'}), 404
        if not linea:
            linea = plan_row.get('linea', '')

        # VALIDACIÓN CRÍTICA: Verificar que no haya otro run activo en la misma línea
        existing_run = execute_query(
            "SELECT id, lot_no, plan_id FROM plan_smd_runs WHERE linea=%s AND status IN ('RUNNING', 'PAUSED') ORDER BY start_time DESC LIMIT 1", 
            (linea,), 
            fetch='one'
        )
        if existing_run:
            existing_plan = execute_query("SELECT modelo, nparte FROM plan_smd WHERE id=%s", (existing_run['plan_id'],), fetch='one')
            modelo_info = f" ({existing_plan['modelo']} - {existing_plan['nparte']})" if existing_plan else ""
            return jsonify({
                'success': False, 
                'error': f'Ya hay un run activo en la línea {linea}: {existing_run["lot_no"]}{modelo_info}. Debe finalizar el run actual antes de iniciar uno nuevo.'
            }), 409  # 409 Conflict

        # Verificar que este plan específico no tenga ya un run activo
        plan_run_active = execute_query(
            "SELECT id, lot_no, status FROM plan_smd_runs WHERE plan_id=%s AND status IN ('RUNNING', 'PAUSED') ORDER BY start_time DESC LIMIT 1", 
            (plan_id,), 
            fetch='one'
        )
        if plan_run_active:
            return jsonify({
                'success': False, 
                'error': f'Este plan ya tiene un run activo: {plan_run_active["lot_no"]} (Status: {plan_run_active["status"]}). Debe finalizar el run actual antes de iniciar uno nuevo.'
            }), 409

        # Verificar que el plan no esté ya finalizado
        trazabilidad_actual = execute_query(
            "SELECT estado FROM trazabilidad WHERE lot_no=%s ORDER BY updated_at DESC LIMIT 1", 
            (plan_row.get('lote'),), 
            fetch='one'
        )
        if trazabilidad_actual and trazabilidad_actual.get('estado') == 'FINALIZADO':
            return jsonify({
                'success': False, 
                'error': f'Este plan ya está finalizado (LOT: {plan_row.get("lote")}). No se puede reiniciar un plan finalizado.'
            }), 409

        # Usar LOT NO ya definido en el plan; no generar uno nuevo
        lot_no = plan_row.get('lote')
        if not lot_no:
            return jsonify({'success': False, 'error': 'El plan no tiene LOT asignado'}), 400
        uph = plan_row.get('uph') or 0
        ct = plan_row.get('ct') or 0
        qty_plan = plan_row.get('qty') or 0

        # Preparar baseline AOI al iniciar RUN
        aoi_model = (plan_row.get('nparte') or plan_row.get('modelo') or '').upper()
        aoi_line_no = _map_line_no(linea)
        
        from ..api.aoi_api import classify_shift, compute_shift_date
        from ..core.auth_system import AuthSystem as _AS
        now_mx = _AS.get_mexico_time()
        current_shift = classify_shift(now_mx)
        current_shift_date = compute_shift_date(now_mx, current_shift).strftime('%Y-%m-%d')
        aoi_baseline = None
        if aoi_model and aoi_line_no:
            baseline_sql = """
                SELECT COALESCE(SUM(piece_w),0) AS total
                FROM aoi_file_log
                WHERE shift_date=%s AND shift=%s AND model=%s AND line_no=%s
            """
            try:
                rowb = execute_query(baseline_sql, (current_shift_date, current_shift, aoi_model, aoi_line_no), fetch='one') or {}
                aoi_baseline = int(rowb.get('total') or 0)
            except Exception as e2:
                print(f"⚠️ Error obteniendo baseline AOI: {e2}")
                aoi_baseline = 0

        insert = """
            INSERT INTO plan_smd_runs (plan_id, linea, lot_no, uph, ct, qty_plan, status, created_by,
                                       aoi_model, aoi_line_no, aoi_baseline, aoi_baseline_shift_date, aoi_baseline_shift)
            VALUES (%s,%s,%s,%s,%s,%s,'RUNNING',%s, %s,%s,%s,%s,%s)
        """
        execute_query(insert, (plan_id, linea, lot_no, uph, ct, qty_plan, usuario,
                               aoi_model, aoi_line_no, aoi_baseline, current_shift_date, current_shift))

        # Actualizar trazabilidad: INICIADO
        try:
            # Intentar INSERT primero
            try:
                execute_query("""
                    INSERT INTO trazabilidad (lot_no, estado, updated_at) 
                    VALUES (%s, 'INICIADO', NOW())
                """, (lot_no,))
            except Exception:
                # Si falla (probablemente duplicado), actualizar el más reciente
                execute_query("""
                    UPDATE trazabilidad SET estado='INICIADO', updated_at=NOW() 
                    WHERE lot_no=%s AND updated_at = (
                        SELECT MAX(updated_at) FROM (SELECT updated_at FROM trazabilidad WHERE lot_no=%s) AS t
                    )
                """, (lot_no, lot_no))
        except Exception as e2:
            print(f"⚠️ Error actualizando trazabilidad (INICIADO): {e2}")

        run = execute_query("SELECT * FROM plan_smd_runs WHERE lot_no=%s", (lot_no,), fetch='one')
        return jsonify({'success': True, 'run': run})
    except Exception as e:
        print(f"❌ Error en api_plan_run_start: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API: FINALIZAR RUN
# ============================================================================

@plan_smd_bp.route('/api/plan-run/end', methods=['POST'])
def api_plan_run_end():
    """Finalizar un run de producción"""
    try:
        data = request.get_json(force=True) or {}
        run_id = int(data.get('run_id'))
        plan_id_req = data.get('plan_id')
        
        # Validar run existente y opcionalmente que corresponda al plan indicado
        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        if not run:
            return jsonify({'success': False, 'error': 'Run no encontrado'}), 404
        if plan_id_req is not None and str(run.get('plan_id')) != str(plan_id_req):
            return jsonify({'success': False, 'error': 'El run no corresponde al plan indicado'}), 400
        
        # Cerrar el run si está RUNNING
        update = "UPDATE plan_smd_runs SET status='ENDED', end_time=NOW() WHERE id=%s AND status='RUNNING'"
        execute_query(update, (run_id,))
        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        
        # Calcular y guardar producido final basado en AOI (si hay baseline)
        try:
            if run:
                aoi_model = (run.get('aoi_model') or '').upper()
                aoi_line_no = run.get('aoi_line_no')
                bl = int(run.get('aoi_baseline') or 0)
                bl_date = run.get('aoi_baseline_shift_date')
                bl_shift = (run.get('aoi_baseline_shift') or '').strip() if run.get('aoi_baseline_shift') else ''
                if aoi_model and aoi_line_no and bl_date and bl_shift:
                    shift_order = {'DIA': 1, 'TIEMPO_EXTRA': 2, 'NOCHE': 3}
                    agg_sql = """
                        SELECT shift_date, shift, SUM(piece_w) AS total
                        FROM aoi_file_log
                        WHERE model=%s AND line_no=%s AND shift_date >= %s
                        GROUP BY shift_date, shift
                        ORDER BY shift_date ASC
                    """
                    agg_rows = execute_query(agg_sql, (aoi_model, int(aoi_line_no), bl_date), fetch='all') or []
                    total = 0
                    for ar in agg_rows:
                        sd = ar.get('shift_date')
                        sh = (ar.get('shift') or '').strip()
                        t = int(ar.get('total') or 0)
                        if not sd or not sh:
                            continue
                        if str(sd) == str(bl_date) and sh == bl_shift:
                            total += max(0, t - bl)
                        else:
                            if str(sd) == str(bl_date) and shift_order.get(sh, 0) < shift_order.get(bl_shift, 0):
                                continue
                            total += t
                    try:
                        execute_query("UPDATE plan_smd_runs SET aoi_produced_final=%s WHERE id=%s", (int(total), run_id))
                        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
                    except Exception as e3:
                        print(f"⚠️ Error guardando aoi_produced_final: {e3}")
        except Exception as e2:
            print(f"⚠️ Error calculando producido final AOI: {e2}")
        
        try:
            if run and run.get('lot_no'):
                # Intentar INSERT primero
                try:
                    execute_query("""
                        INSERT INTO trazabilidad (lot_no, estado, updated_at) 
                        VALUES (%s, 'FINALIZADO', NOW())
                    """, (run['lot_no'],))
                except Exception:
                    # Si falla (probablemente duplicado), actualizar el más reciente
                    execute_query("""
                        UPDATE trazabilidad SET estado='FINALIZADO', updated_at=NOW() 
                        WHERE lot_no=%s AND updated_at = (
                            SELECT MAX(updated_at) FROM (SELECT updated_at FROM trazabilidad WHERE lot_no=%s) AS t
                        )
                    """, (run['lot_no'], run['lot_no']))
        except Exception as e2:
            print(f"⚠️ Error actualizando trazabilidad (FINALIZADO): {e2}")
        
        return jsonify({'success': True, 'run': run})
    except Exception as e:
        print(f"❌ Error en api_plan_run_end: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API: PAUSAR RUN
# ============================================================================

@plan_smd_bp.route('/api/plan-run/pause', methods=['POST'])
def api_plan_run_pause():
    """Pausar un run de producción"""
    try:
        data = request.get_json(force=True) or {}
        run_id = int(data.get('run_id'))
        update = "UPDATE plan_smd_runs SET status='PAUSED' WHERE id=%s AND status='RUNNING'"
        execute_query(update, (run_id,))
        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        if run and run.get('lot_no'):
            try:
                # Intentar INSERT primero
                try:
                    execute_query("""
                        INSERT INTO trazabilidad (lot_no, estado, updated_at) 
                        VALUES (%s, 'PAUSA', NOW())
                    """, (run['lot_no'],))
                except Exception:
                    # Si falla (probablemente duplicado), actualizar el más reciente
                    execute_query("""
                        UPDATE trazabilidad SET estado='PAUSA', updated_at=NOW() 
                        WHERE lot_no=%s AND updated_at = (
                            SELECT MAX(updated_at) FROM (SELECT updated_at FROM trazabilidad WHERE lot_no=%s) AS t
                        )
                    """, (run['lot_no'], run['lot_no']))
            except Exception as e2:
                print(f"⚠️ Error actualizando trazabilidad (PAUSA): {e2}")
        return jsonify({'success': True, 'run': run})
    except Exception as e:
        print(f"❌ Error en api_plan_run_pause: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API: REANUDAR RUN
# ============================================================================

@plan_smd_bp.route('/api/plan-run/resume', methods=['POST'])
def api_plan_run_resume():
    """Reanudar un run pausado"""
    try:
        data = request.get_json(force=True) or {}
        run_id = int(data.get('run_id'))
        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        if not run:
            return jsonify({'success': False, 'error': 'Run no encontrado'}), 404
        linea = run.get('linea')
        exists = execute_query("SELECT id FROM plan_smd_runs WHERE linea=%s AND status='RUNNING' AND id<>%s LIMIT 1", (linea, run_id), fetch='one')
        if exists:
            return jsonify({'success': False, 'error': f'Ya existe un plan en progreso en {linea}'}), 400
        execute_query("UPDATE plan_smd_runs SET status='RUNNING' WHERE id=%s AND status='PAUSED'", (run_id,))
        if run.get('lot_no'):
            try:
                execute_query("UPDATE trazabilidad SET estado='INICIADO', updated_at=NOW() WHERE lot_no=%s", (run['lot_no'],))
            except Exception as e2:
                print(f"⚠️ Error actualizando trazabilidad (INICIADO): {e2}")
        run = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        return jsonify({'success': True, 'run': run})
    except Exception as e:
        print(f"❌ Error en api_plan_run_resume: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API: ESTADO DEL RUN
# ============================================================================

@plan_smd_bp.route('/api/plan-run/status', methods=['GET'])
def api_plan_run_status():
    """Estado del run por línea o run_id.
    Si está RUNNING, calcula progreso estimado usando UPH y tiempo transcurrido.
    """
    try:
        run_id = request.args.get('run_id')
        linea = request.args.get('linea')
        
        if run_id:
            row = execute_query("SELECT * FROM plan_smd_runs WHERE id=%s", (run_id,), fetch='one')
        elif linea and linea.strip():
            row = execute_query("SELECT * FROM plan_smd_runs WHERE linea=%s AND status='RUNNING' ORDER BY start_time DESC LIMIT 1", (linea.strip(),), fetch='one')
        else:
            error_msg = 'Parámetros insuficientes. Se requiere run_id o linea.'
            if linea == '':
                error_msg = 'Parámetro linea está vacío'
            return jsonify({'success': False, 'error': error_msg}), 400

        if not row:
            return jsonify({'success': True, 'running': False})

        # Calcular progreso estimado
        start = row.get('start_time')
        end = row.get('end_time')
        uph = float(row.get('uph') or 0)
        qty_plan = int(row.get('qty_plan') or 0)
        producido = 0
        if start and not end and uph > 0:
            # elapsed hours
            now = datetime.utcnow()
            # MySQL datetime naive; asumir UTC-agnóstico
            elapsed_hours = max(0.0, (now - start).total_seconds() / 3600.0)
            producido = int(min(qty_plan, uph * elapsed_hours))
        return jsonify({'success': True, 'running': row['status']=='RUNNING', 'run': row, 'producido_est': producido})
    except Exception as e:
        print(f"❌ Error en api_plan_run_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
