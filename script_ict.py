#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor ODATA ICT:
- Escaneo inicial (últimos 3 meses) + monitoreo en tiempo real de \\...\\ODATA\\YYYYMMDD
- Parser .lgd con regla de veredictos (primeros 1–2 OK/NG por línea)
- Guarda:
   * Tabla padre: history_ict (resumen por barcode con defect_code/defect_valor de NG validos)
   * Parametros detallados permanecen en archivos .lgd locales.
- processed_files.log cacheado en memoria (rápido) + log de ejecución.
- Re-escaneo periódico para robustez.
"""

import os
import re
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import json
import json
from collections import defaultdict
from typing import Optional

import pymysql
from pymysql.constants import CLIENT
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.services.ict_lgd_parser import parse_lgd_file

# ====== Zona horaria (tzdata recomendada) ======
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

def get_mty_tz():
    if ZoneInfo is None:
        return None
    for key in ("America/Monterrey", "America/Mexico_City", "Mexico/General"):
        try:
            return ZoneInfo(key)
        except Exception:
            continue
    return None

TZ_MTY = get_mty_tz()

# ================== CONFIG ==================
BASE_DIR = r"\\192.168.1.144\lg-pws\TDATA\ICT\ODATA"
MESES_RETRO = 3
RESCAN_EVERY_SEC = 10 * 60  # re-escaneo incremental cada 10 minutos

SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "history_ict_monitor.log"
PROCESADOS_FILE = SCRIPT_DIR / "processed_files.log"
FULL_SCAN_STATE_FILE = SCRIPT_DIR / "full_scan_state.json"
FORCE_INITIAL_FULL_RESCAN = os.environ.get("ICT_FULL_RESCAN", "0") == "1"
MAX_WORKERS = min(4, max(2, (os.cpu_count() or 4) // 4))
BULK_CHUNK_SIZE = 500

DB_CFG = {
    "host": "up-de-fra1-mysql-1.db.run-on-seenode.com",
    "port": 11550,
    "user": "db_rrpq0erbdujn",
    "password": "5fUNbSRcPP3LN9K2I33Pr0ge",
    "database": "db_rrpq0erbdujn",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
    "client_flag": CLIENT.LOCAL_FILES,
}

# ================== LOGGING ==================
logger = logging.getLogger("history_ict")
logger.setLevel(logging.INFO)
rot = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8")
rot.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(rot)
console = logging.StreamHandler(sys.stdout)
console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(console)

# ================== UTILS ==================
NUM_HYPHEN_RE = re.compile(r"(\d+)\s*-\s*(\d+)")

# Solo defectos válidos (excluye OPEN/SHORT/JUMP)
FAIL_TOKENS = re.compile(
    r"\b(LOWLIMIT|HIGHLIMIT|HIGHTLIMIT|OPENNG|SHORTNG|OVERLIMIT|UNDERLIMIT|[A-Z]+NG)\b",
    re.IGNORECASE
)

def normalize_defecto(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    t = token.upper()
    if t == "HIGHTLIMIT":
        t = "HIGHLIMIT"
    return t

def is_valid_defecto(token: Optional[str]) -> bool:
    if not token:
        return False
    t = token.upper()
    if t in {"LOWLIMIT", "HIGHLIMIT", "HIGHTLIMIT", "OPENNG", "SHORTNG", "OVERLIMIT", "UNDERLIMIT"}:
        return True
    return t.endswith("NG")

def get_conn():
    return pymysql.connect(**DB_CFG)

def obtener_conexion_mysql(max_attempts: int = 3, delay: float = 2.0):
    """Devuelve una conexión a MySQL con reintentos básicos."""
    last_exc = None
    for intento in range(1, max_attempts + 1):
        try:
            conn = get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SET SESSION local_infile = 1")
            except Exception as e:
                logger.debug("No se pudo habilitar local_infile en la sesión: %s", e)
            return conn
        except pymysql.MySQLError as exc:
            last_exc = exc
        except Exception as exc:
            last_exc = exc
        logger.warning("Fallo conectando a MySQL (intento %d/%d): %s", intento, max_attempts, last_exc)
        if intento < max_attempts:
            time.sleep(delay)
    logger.error("No se pudo establecer conexión MySQL tras %d intentos: %s", max_attempts, last_exc)
    return None

def tz_monterrey(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    if TZ_MTY is None:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ_MTY).astimezone(TZ_MTY).replace(tzinfo=None)
    return dt.astimezone(TZ_MTY).replace(tzinfo=None)

def rel_path_from_base(abs_path: str) -> str:
    try:
        rp = os.path.relpath(abs_path, BASE_DIR)
    except Exception:
        rp = os.path.basename(abs_path)
    return rp.replace("/", "\\")

def extrae_linea_ict(linea_raw: str):
    """Soporta 'ISMM1-1', 'IMM2-2', 'M3-1' con/sin espacios. Retorna ('Mx', y) del último x-y."""
    if not linea_raw:
        return "UNKNOWN", 0
    s = str(linea_raw)
    m_direct = re.findall(r"[Mm]+\s*(\d+)\s*-\s*(\d+)", s)
    if m_direct:
        a, b = m_direct[-1]
        return f"M{a}", int(b)
    m_any = NUM_HYPHEN_RE.findall(s)
    if m_any:
        a, b = m_any[-1]
        return f"M{a}", int(b)
    logger.warning("No pude extraer linea/ict de '%s'", s)
    return "UNKNOWN", 0

def to_float(x):
    try:
        return float(str(x).replace(",", ""))
    except Exception:
        return None

def to_int(x):
    try:
        return int(float(str(x).replace(",", "")))
    except Exception:
        return None

def primeros_veredictos_ok_ng(tokens):
    """Devuelve (v1, v2, idx_v1) con los primeros 1–2 veredictos en {'OK','NG'} dentro de tokens."""
    veredictos = []
    idx_primero = None
    for i, t in enumerate(tokens):
        u = t.strip().upper()
        if u in ("OK", "NG"):
            if idx_primero is None:
                idx_primero = i
            veredictos.append(u)
            if len(veredictos) == 2:
                break
    v1 = veredictos[0] if veredictos else None
    v2 = veredictos[1] if len(veredictos) > 1 else None
    return v1, v2, idx_primero

# ======= Alcance por fecha (días específicos) =======
DIAS_ESPECIFICOS = ["20250825", "20250908"]  # Días específicos a procesar

def yyyymmdd_from_path(path: str) -> Optional[datetime]:
    p = Path(path)
    for part in p.parts[::-1]:
        if len(part) == 8 and part.isdigit():
            try:
                return datetime.strptime(part, "%Y%m%d")
            except Exception:
                pass
    return None

def in_scope_last_months(path: str, months: int = MESES_RETRO) -> bool:
    day = yyyymmdd_from_path(path)
    if not day:
        return False
    
    # Verificar si es uno de los días específicos
    day_str = day.strftime("%Y%m%d")
    if day_str in DIAS_ESPECIFICOS:
        return True
    
    # Fallback al comportamiento original (últimos meses)
    cutoff = datetime.now() - timedelta(days=30 * months)
    return day >= cutoff

# ======= processed_files.log en memoria (rápido) =======
PROCESADOS_SET = set()
PROCESADOS_LOCK = threading.Lock()
FUENTES_MYSQL = set()
FUENTES_LOCK = threading.Lock()
FUENTES_LAST_REFRESH = 0.0
FUENTES_REFRESH_EVERY_SEC = max(RESCAN_EVERY_SEC, 5 * 60)

def cargar_estado_full_scan():
    if not FULL_SCAN_STATE_FILE.exists():
        return {"last_day": None}
    try:
        data = json.loads(FULL_SCAN_STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"last_day": None}
        return {"last_day": data.get("last_day")}
    except Exception:
        logger.warning("No se pudo leer estado de escaneo, iniciando desde principio")
        return {"last_day": None}

def guardar_estado_full_scan(day_str: str):
    try:
        FULL_SCAN_STATE_FILE.write_text(json.dumps({"last_day": day_str}), encoding="utf-8")
    except Exception as e:
        logger.warning("No se pudo guardar estado de escaneo: %s", e)

def limpiar_estado_full_scan():
    try:
        if FULL_SCAN_STATE_FILE.exists():
            FULL_SCAN_STATE_FILE.unlink()
    except Exception:
        pass

def chunked(rows, size):
    for i in range(0, len(rows), size):
        yield rows[i:i+size]

def infer_last_completed_day() -> Optional[str]:
    best = None
    with PROCESADOS_LOCK:
        for sig in PROCESADOS_SET:
            rel = sig.split("|", 1)[0]
            for part in rel.split("\\"):
                if len(part) == 8 and part.isdigit():
                    if best is None or part > best:
                        best = part
                    break
    return best

def bulk_upsert_history_ict(cur, rows):
    if not rows:
        return 0
    placeholders = "(" + ",".join(["%s"] * 11) + ")"
    base_sql = """
    INSERT INTO history_ict
      (fecha, hora, linea, ict, resultado, no_parte, barcode, ts, fuente_archivo, defect_code, defect_valor)
    VALUES {values_clause}
    ON DUPLICATE KEY UPDATE
      resultado=VALUES(resultado),
      linea=VALUES(linea),
      ict=VALUES(ict),
      fuente_archivo=VALUES(fuente_archivo),
      defect_code=VALUES(defect_code),
      defect_valor=VALUES(defect_valor),
      updated_at=NOW()
    """
    for chunk in chunked(rows, BULK_CHUNK_SIZE):
        values_clause = ",".join([placeholders] * len(chunk))
        flat = []
        for row in chunk:
            flat.extend(row)
        cur.execute(base_sql.format(values_clause=values_clause), flat)
    return len(rows)

def _firma_archivo(abs_path: str):
    try:
        st = os.stat(abs_path)
        return f"{rel_path_from_base(abs_path)}|{st.st_size}|{int(st.st_mtime)}"
    except FileNotFoundError:
        return None
    except OSError as exc:
        logger.warning("No se pudo obtener stat de %s (%s); se reintentará más tarde", abs_path, exc)
        return None

def cargar_log_procesados():
    with PROCESADOS_LOCK:
        PROCESADOS_SET.clear()
        if not PROCESADOS_FILE.exists():
            PROCESADOS_FILE.touch()
            return
        with open(PROCESADOS_FILE, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                sig = line.strip()
                if sig:
                    PROCESADOS_SET.add(sig)

def ya_procesado(abs_path: str) -> bool:
    sig = _firma_archivo(abs_path)
    if not sig:
        return False

    rel_src = rel_path_from_base(abs_path)
    with PROCESADOS_LOCK:
        if sig not in PROCESADOS_SET:
            return False
    with FUENTES_LOCK:
        fuentes_copy = set(FUENTES_MYSQL)
    if fuentes_copy and rel_src not in fuentes_copy:
        logger.warning(
            "Archivo marcado como procesado pero ausente en MySQL, forzando reproceso: %s",
            rel_src
        )
        with PROCESADOS_LOCK:
            PROCESADOS_SET.discard(sig)
        return False

    return True

def marca_procesado(abs_path: str):
    try:
        sig = _firma_archivo(abs_path)
        if not sig:
            return
        with PROCESADOS_LOCK:
            if sig in PROCESADOS_SET:
                return
            PROCESADOS_SET.add(sig)
        with open(PROCESADOS_FILE, "a", encoding="utf-8") as fh:
            fh.write(sig + "\n")
    except Exception as e:
        logger.warning("No se pudo marcar procesado %s: %s", abs_path, e)

def actualizar_cache_fuentes_mysql(force: bool = False):
    """Sincroniza un cache local de fuente_archivo presentes en MySQL para los últimos MESES_RETRO meses."""
    global FUENTES_MYSQL, FUENTES_LAST_REFRESH
    now = time.time()
    if not force and now - FUENTES_LAST_REFRESH < FUENTES_REFRESH_EVERY_SEC:
        return
    conn = obtener_conexion_mysql()
    if conn is None:
        return
    try:
        cutoff_date = (datetime.now() - timedelta(days=30 * MESES_RETRO)).date()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT fuente_archivo
            FROM history_ict
            WHERE fuente_archivo IS NOT NULL
              AND fuente_archivo <> ''
              AND fecha >= %s
            """,
            (cutoff_date,)
        )
        tmp = {row["fuente_archivo"] for row in cur}
        with FUENTES_LOCK:
            FUENTES_MYSQL.clear()
            FUENTES_MYSQL.update(tmp)
        FUENTES_LAST_REFRESH = now
        logger.info("Cache MySQL sincronizado: %d fuentes activas desde %s", len(tmp), cutoff_date)
    except Exception:
        logger.exception("No se pudo actualizar cache de fuentes desde MySQL")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

# ======= Parseo WS/Ds/R-C =======
FLOAT_RE = re.compile(r"[-+]?\d+\.\d+(e[-+]?\d+)?$", re.IGNORECASE)
INT_RE = re.compile(r"[-+]?\d+$")

def parse_ws_ds_rc(after_tokens):
    """Extrae NodoA/NodoB (HP/LP) y los valores WS/Ds/RC tras los veredictos."""
    numbers = []
    for token in after_tokens:
        s = token.strip()
        if not s:
            continue
        if FLOAT_RE.fullmatch(s) or INT_RE.fullmatch(s):
            numbers.append(s)

    if not numbers:
        return None, None, None, None, None

    rest = numbers[2:] if len(numbers) > 2 else []  # omitir p_flag y j_flag

    ints = []
    for s in rest:
        if INT_RE.fullmatch(s):
            try:
                ints.append(int(float(s)))
            except Exception:
                continue
    hp_candidates = [val for val in ints if abs(val) > 0]
    nodo_a = nodo_b = None
    if len(hp_candidates) >= 2:
        nodo_a, nodo_b = hp_candidates[0], hp_candidates[1]
    elif len(ints) >= 2:
        nodo_a, nodo_b = ints[-2], ints[-1]

    floats = []
    for s in rest:
        if '.' in s:
            try:
                floats.append(float(s))
            except Exception:
                continue
    ws = floats[0] if len(floats) > 0 else None
    ds = floats[1] if len(floats) > 1 else None
    rc = floats[2] if len(floats) > 2 else None

    return nodo_a, nodo_b, ws, ds, rc
# ================== INSERCIÓN ==================
def parse_file(abs_path: str):
    """Parsea .lgd usando el helper compartido sin efectos secundarios."""
    try:
        return parse_lgd_file(abs_path, base_dir=BASE_DIR)
    except Exception:
        logger.exception("Error leyendo %s", abs_path)
        return {}, [], {}


def insertar_mysql(abs_path: str, summary_by_bc: dict, defects_rows: list, all_components_by_bc: dict):
    global FUENTES_MYSQL
    if not summary_by_bc:
        logger.info("Sin datos que insertar: %s", abs_path)
        return

    rel_src = rel_path_from_base(abs_path)
    st = os.stat(abs_path)
    mtime_dt = datetime.fromtimestamp(st.st_mtime)
    mtime_local = tz_monterrey(mtime_dt) or mtime_dt

    conn = obtener_conexion_mysql()
    if conn is None:
        logger.error("Saltando inserción por falta de conexión MySQL: %s", rel_src)
        return
    try:
        cur = conn.cursor()

        parent_rows = []
        for bc, info in summary_by_bc.items():
            ts = info.get("ts") or mtime_local
            fecha, hora = ts.date(), ts.time()
            parent_rows.append((
                fecha, hora,
                info.get("linea", "UNKNOWN"),
                int(info.get("ict") or 0),
                info.get("resultado", "NG"),
                info.get("no_parte") or bc[:11],
                bc, ts, rel_src,
                info.get("defect_code") or None,
                info.get("defect_valor") or None
            ))

        n_parent = bulk_upsert_history_ict(cur, parent_rows)
        conn.commit()
        with FUENTES_LOCK:
            FUENTES_MYSQL.add(rel_src)
        logger.info(
            "history_ict: %d filas; parametros detallados permanecen en archivo local %s",
            n_parent, rel_src
        )
        marca_procesado(abs_path)
    except Exception:
        conn.rollback()
        logger.exception("Error insertando %s", rel_src)
    finally:
        conn.close()

# ================== WORKFLOW ==================
def procesar_archivo(abs_path: str, force: bool = False):
    if not abs_path.lower().endswith(".lgd"):
        return
    if not in_scope_last_months(abs_path):
        return
    already = ya_procesado(abs_path)
    rel_log = rel_path_from_base(abs_path)
    if already and not force:
        logger.info("Saltado (ya procesado): %s", rel_log)
        return
    if already and force:
        logger.info("Reprocesando forzado: %s", rel_log)
    else:
        logger.info("Procesando: %s", rel_log)
    summary, defects, all_comp = parse_file(abs_path)
    if not summary:
        logger.info("Archivo sin barcodes/resultados: %s", rel_log)
        return
    insertar_mysql(abs_path, summary, defects, all_comp)

def _procesar_paths_concurrentes(paths, force: bool = False):
    if not paths:
        return
    if MAX_WORKERS <= 1 or len(paths) < MAX_WORKERS:
        for p in paths:
            procesar_archivo(p, force=force)
        return
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(procesar_archivo, p, force): p for p in paths}
        for fut in as_completed(future_map):
            path = future_map[fut]
            try:
                fut.result()
            except Exception:
                logger.exception("Error procesando %s", path)

def escaneo_inicial():
    base = Path(BASE_DIR)
    if not base.exists():
        logger.error("BASE_DIR no existe: %s", BASE_DIR)
        return

    estado = cargar_estado_full_scan()
    last_day = estado.get("last_day")
    if FORCE_INITIAL_FULL_RESCAN:
        logger.info("Escaneo forzado: ignorando estado previo de carpetas procesadas")
        limpiar_estado_full_scan()
        last_day = None
    elif last_day:
        logger.info("Último día completado previamente: %s", last_day)
        logger.info("Saltando escaneo inicial. Solo monitoreando cambios nuevos desde ahora.")
        return  # No volver a escanear, solo monitorear en tiempo real
    else:
        inferred = infer_last_completed_day()
        if inferred:
            last_day = inferred
            guardar_estado_full_scan(inferred)
            logger.info("Estado inferido desde processed_files.log: %s", inferred)
            logger.info("Saltando escaneo inicial. Solo monitoreando cambios nuevos desde ahora.")
            return  # No volver a escanear, solo monitorear en tiempo real

    dirs = []
    for d in base.iterdir():
        if d.is_dir() and in_scope_last_months(str(d)):
            day = yyyymmdd_from_path(str(d))
            if day:
                dirs.append((day, d))

    dirs.sort()  # más antiguo primero

    for day, d in dirs:
        day_str = day.strftime("%Y%m%d")
        if not FORCE_INITIAL_FULL_RESCAN and last_day and day_str <= last_day:
            logger.info("Saltando carpeta %s (%s) (ya completada)", d.name, day.date())
            continue

        logger.info("Escaneando carpeta %s (%s)…", d.name, day.date())
        archivos = sorted([p for p in d.iterdir() if p.is_file() and p.suffix.lower() == ".lgd"])
        logger.info("  %d archivos .lgd detectados", len(archivos))
        try:
            _procesar_paths_concurrentes([str(p) for p in archivos], force=FORCE_INITIAL_FULL_RESCAN)
            guardar_estado_full_scan(day_str)
            last_day = day_str
        except Exception:
            logger.exception("Error procesando carpeta %s", d)

def escaneo_incremental():
    base = Path(BASE_DIR)
    if not base.exists():
        return
    dirs = []
    for d in base.iterdir():
        if d.is_dir() and in_scope_last_months(str(d)):
            day = yyyymmdd_from_path(str(d))
            if day:
                dirs.append((day, d))
    dirs.sort(reverse=True)
    for _, d in dirs:
        for f in d.iterdir():
            if f.is_file() and f.suffix.lower() == ".lgd":
                procesar_archivo(str(f))

class Handler(FileSystemEventHandler):
    def _should_process(self, path: str) -> bool:
        return path.lower().endswith(".lgd") and in_scope_last_months(path)

    def on_created(self, ev):
        if ev.is_directory:
            return
        if not self._should_process(ev.src_path):
            return
        time.sleep(0.5)
        procesar_archivo(ev.src_path)

    def on_moved(self, ev):
        if ev.is_directory:
            return
        dst = getattr(ev, "dest_path", ev.src_path)
        if not self._should_process(dst):
            return
        time.sleep(0.5)
        procesar_archivo(dst)

def main():
    logger.info("===== history_ict monitor iniciado =====")
    logger.info("BASE_DIR: %s", BASE_DIR)

    cargar_log_procesados()
    actualizar_cache_fuentes_mysql(force=True)
    escaneo_inicial()

    obs = Observer()
    obs.schedule(Handler(), BASE_DIR, recursive=True)
    obs.start()
    logger.info("Monitoreo en tiempo real activo…")

    last_rescan = time.time()
    try:
        while True:
            time.sleep(3)
            now = time.time()
            if now - last_rescan >= RESCAN_EVERY_SEC:
                actualizar_cache_fuentes_mysql()
                logger.info("Re-escaneo incremental del rango de %d meses...", MESES_RETRO)
                escaneo_incremental()
                last_rescan = now
    except KeyboardInterrupt:
        logger.info("Deteniendo monitor…")
        obs.stop()
    obs.join()
    logger.info("Monitor detenido.")

if __name__ == "__main__":
    main()


