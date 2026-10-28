"""Helpers compartidos entre los 2 modulos Vision.

Consumido por:
  - app/api/control_resultados/historial_vision.py             (4 APIs)
  - app/api/control_resultados/historial_vision_pass_fail.py   (2 APIs)

Contenido:
  - Parsers de fecha/hora (_vision_format_value, _vision_parse_*).
  - Resolucion de imagenes en shares de red (_vision_candidate_share_roots,
    _vision_candidate_hour_directories, _vision_share_name,
    _vision_is_safe_path, _resolve_history_vision_image, _get_history_vision_record).
    La IP de la PC sale de DeviceHub (_vision_devicehub_ip), el share se monta con
    VISION_SHARE_USER/PASSWORD del .env (_vision_share_available) y un shlog duplicado
    toma la foto de su gemelo SHT (_get_history_vision_sht_twin).
  - Builders de query SQL (_build_history_vision_query,
    _build_history_vision_pass_fail_summary_query).

Migrado desde app/routes.py el 2026-05-27. routes.py reexporta todo para
compatibilidad.

NOTA anti-circular: importa execute_query directo de app.db_mysql.
"""

import json
import logging
import os
import re
import subprocess
import time
from datetime import date, datetime, timedelta
from datetime import time as dt_time
from pathlib import Path

from flask import request

from app.db_mysql import execute_query

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parsers de fecha/hora
# ---------------------------------------------------------------------------


def _vision_format_value(value):
    """Convertir valores de history_vision a cadenas serializables."""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dt_time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    if isinstance(value, str) and re.fullmatch(r"\d{2}:\d{2}:\d{2}\.\d+", value):
        return value.split(".", 1)[0]
    return value


def _vision_parse_datetime(value):
    """Normalizar distintos formatos de fecha/hora a datetime."""
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        try:
            return datetime.fromisoformat(raw_value)
        except ValueError:
            for fmt in (
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S.%f",
                "%Y/%m/%d %H:%M:%S",
            ):
                try:
                    return datetime.strptime(raw_value, fmt)
                except ValueError:
                    continue
    return None


def _vision_parse_date(value):
    """Normalizar valores de fecha a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        try:
            return date.fromisoformat(raw_value)
        except ValueError:
            return None
    return None


def _vision_parse_time(value):
    """Normalizar valores de hora a time."""
    if isinstance(value, dt_time):
        return value
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return dt_time(hour=hours % 24, minute=minutes, second=seconds)
    if isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        try:
            return dt_time.fromisoformat(raw_value)
        except ValueError:
            for fmt in ("%H:%M:%S.%f", "%H:%M:%S"):
                try:
                    return datetime.strptime(raw_value, fmt).time()
                except ValueError:
                    continue
    return None


def _vision_reference_datetime(record):
    """Obtener la fecha/hora mas confiable para resolver la imagen."""
    parsed_value = _vision_parse_datetime(record.get("log_datetime"))
    if parsed_value:
        return parsed_value

    log_date = _vision_parse_date(record.get("log_date"))
    log_time = _vision_parse_time(record.get("log_time"))
    if log_date and log_time:
        return datetime.combine(log_date, log_time)

    for key in ("captured_at_utc", "created_at"):
        parsed_value = _vision_parse_datetime(record.get(key))
        if parsed_value:
            return parsed_value

    return None


def _vision_record_source(record):
    """'SHT' si el registro vino del .txt de resultados de la vision, 'shlog' si del log.

    Importa para la imagen: en el SHT log_datetime es el inicio de la inspeccion y es
    exactamente el sello de la foto (al milisegundo); en el .shlog es el fin (csZone.Run),
    0.2-0.4 s despues de la foto.
    """
    source_file = str(record.get("source_file") or "").strip().lower()
    return "SHT" if source_file.endswith(".txt") else "shlog"


# ---------------------------------------------------------------------------
# Resolucion de imagenes en shares de red
# ---------------------------------------------------------------------------


def _vision_extract_host_from_source_file(source_file):
    """Extraer el host UNC desde source_file."""
    raw_source = str(source_file or "").strip()
    match = re.match(r"^\\\\([^\\]+)\\", raw_source)
    return match.group(1).strip() if match else ""


def _vision_unique_values(values):
    """Eliminar duplicados preservando el orden original."""
    unique_values = []
    seen_values = set()
    for value in values:
        normalized = str(value or "").strip()
        if not normalized:
            continue
        value_key = normalized.lower()
        if value_key in seen_values:
            continue
        seen_values.add(value_key)
        unique_values.append(normalized)
    return unique_values


# La red da IPs por DHCP sin reserva y cada registro guarda la IP del dia de su captura:
# M2 paso de .156 a .110 el 2026-10-23 y sus fotos anteriores ya no se encontraban. La IP
# vigente la reporta el agente de DeviceHub de cada PC; las de vision son VISION-<linea>.
_VISION_DEVICEHUB_TTL_SECONDS = 30
_vision_devicehub_cache = {}  # machine_name -> (consultado_en, ip o None)


def _vision_devicehub_ip(machine_name):
    """IP actual de la PC de vision de la linea segun DeviceHub; None si no se sabe."""
    machine_name = str(machine_name or "").strip()
    if not machine_name:
        return None
    cached = _vision_devicehub_cache.get(machine_name)
    if cached and time.time() - cached[0] < _VISION_DEVICEHUB_TTL_SECONDS:
        return cached[1]

    ip = None
    try:
        row = execute_query(
            "SELECT current_ip FROM devicehub.machines "
            "WHERE machine_code=%s AND retired_at IS NULL AND current_ip IS NOT NULL "
            "ORDER BY last_seen DESC LIMIT 1",
            (f"VISION-{machine_name}",),
            fetch="one",
        )
        ip = (row or {}).get("current_ip") or None
    except Exception:
        # Sin DeviceHub se busca con la IP guardada en el registro, como antes.
        logger.warning("No se pudo consultar DeviceHub para %s", machine_name, exc_info=True)
    _vision_devicehub_cache[machine_name] = (time.time(), ip)
    return ip


def _vision_current_source_file(record):
    """source_file con el host cambiado por la IP vigente de la PC (DeviceHub), si se conoce."""
    path = str(record.get("source_file") or "").strip()
    current_ip = _vision_devicehub_ip(record.get("machine_name"))
    if not current_ip or not path.startswith("\\\\"):
        return path
    rest = path[2:].split("\\", 1)
    return rf"\\{current_ip}\{rest[1]}" if len(rest) > 1 else path


# El MES no tenia credenciales del share: solo entraba mientras otro proceso de Windows
# tuviera abierta una sesion a esa PC, y al caerse la sesion "no se encontraba la foto".
_VISION_SHARE_RETRY_SECONDS = 60
_vision_share_retry_at = {}  # share -> no reintentar net use antes de este momento


def _vision_share_available(root_path):
    """True si la carpeta del share responde; si no, la monta con las credenciales del .env."""
    return os.path.isdir(str(root_path)) or _vision_mount_share(root_path)


def _vision_mount_share(root_path):
    """net use con VISION_SHARE_USER / VISION_SHARE_PASSWORD del .env (a lo mas cada 60 s
    por share); True si despues la carpeta responde."""
    root = str(root_path)
    user = os.getenv("VISION_SHARE_USER", "").strip()
    key = root.lower()
    if os.name != "nt" or not user or time.time() < _vision_share_retry_at.get(key, 0):
        return False
    _vision_share_retry_at[key] = time.time() + _VISION_SHARE_RETRY_SECONDS
    try:
        # ponytail: la contraseña va en la linea de comandos de net use un instante, igual que el watcher
        result = subprocess.run(
            ["net", "use", root, os.getenv("VISION_SHARE_PASSWORD", ""), f"/user:{user}", "/persistent:no"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("net use %s fallo: %s", root, exc)
        return False
    if result.returncode != 0:
        logger.warning("net use %s fallo: %s", root, (result.stderr or result.stdout).strip())
    return os.path.isdir(root)


def _vision_candidate_share_roots(record):
    """Construir raices UNC candidatas para buscar imagenes."""
    machine_name = str(record.get("machine_name") or "").strip()
    current_ip = _vision_devicehub_ip(machine_name)
    # Con la IP vigente no se busca en la guardada: ya no es de esa PC (o es de otra).
    candidate_hosts = [current_ip] if current_ip else _vision_unique_values(
        [
            _vision_extract_host_from_source_file(record.get("source_file")),
            record.get("machine_ip"),
        ]
    )

    roots = []
    seen_roots = set()
    for host in candidate_hosts:
        root_candidates = []
        if machine_name:
            root_candidates.append(Path(rf"\\{host}\Result {machine_name}"))
        root_candidates.append(Path(rf"\\{host}\Result"))

        for candidate_root in root_candidates:
            root_key = os.path.normcase(os.path.normpath(str(candidate_root)))
            if root_key in seen_roots:
                continue
            seen_roots.add(root_key)
            roots.append(candidate_root)

    return roots


def _vision_candidate_hour_directories(root_path, part_code, reference_dt):
    """Construir directorios candidatos por hora, incluyendo borde de hora."""
    if not part_code or not reference_dt:
        return []

    base_hour = reference_dt.replace(minute=0, second=0, microsecond=0)
    candidate_hours = [base_hour]

    previous_delta = (reference_dt - base_hour).total_seconds()
    if previous_delta <= _VISION_SHLOG_BEFORE_SECONDS:  # la foto del shlog puede ser de la hora anterior
        candidate_hours.append(base_hour - timedelta(hours=1))

    next_hour = base_hour + timedelta(hours=1)
    next_delta = (next_hour - reference_dt).total_seconds()
    if next_delta <= 1.0:
        candidate_hours.append(next_hour)

    ebr_prefix = str(part_code or "").strip().upper()[:11]
    candidate_part_directories = []
    seen_part_directories = set()

    def append_part_directory(path_obj):
        path_key = os.path.normcase(os.path.normpath(str(path_obj)))
        if path_key in seen_part_directories:
            return
        seen_part_directories.add(path_key)
        candidate_part_directories.append(path_obj)

    append_part_directory(root_path / part_code)

    if ebr_prefix and ebr_prefix != str(part_code or "").strip().upper():
        append_part_directory(root_path / ebr_prefix)

    try:
        if root_path.is_dir() and ebr_prefix:
            matching_directories = sorted(
                [
                    child
                    for child in root_path.iterdir()
                    if child.is_dir()
                    and child.name.strip().upper()[:11] == ebr_prefix
                ],
                key=lambda path: path.name.lower(),
            )
            for matching_directory in matching_directories:
                append_part_directory(matching_directory)
    except OSError:
        pass

    directories = []
    seen_directories = set()
    for part_directory in candidate_part_directories:
        for candidate_hour in candidate_hours:
            base_dir = (
                part_directory
                / "Image(Process)"
                / candidate_hour.strftime("%Y")
                / candidate_hour.strftime("%m")
                / candidate_hour.strftime("%d")
                / candidate_hour.strftime("%H")
            )
            dir_key = os.path.normcase(os.path.normpath(str(base_dir)))
            if dir_key in seen_directories:
                continue
            seen_directories.add(dir_key)
            directories.append(base_dir)

    return directories


def _vision_share_name(root_path):
    """Obtener el nombre visible del share UNC."""
    normalized = os.path.normpath(str(root_path)).rstrip("\\/")
    share_name = os.path.basename(normalized)
    if share_name:
        return share_name
    return normalized.split("\\")[-1] if normalized else ""


def _vision_is_safe_path(target_path, allowed_roots):
    """Validar que la ruta final quede contenida dentro de una raiz candidata."""
    normalized_target = os.path.normcase(os.path.normpath(str(target_path)))
    for allowed_root in allowed_roots:
        normalized_root = os.path.normcase(os.path.normpath(str(allowed_root)))
        try:
            if os.path.commonpath([normalized_target, normalized_root]) == normalized_root:
                return True
        except ValueError:
            continue
    return False


_VISION_RECORD_COLUMNS = (
    "id, source_uid, machine_name, machine_ip, result, log_timestamp, "
    "log_datetime, log_date, log_time, serial_qr, barcode, qr_payload, work_area, "
    "part_code, source_file, captured_at_utc, created_at"
)


def _get_history_vision_record(record_id):
    """Obtener un registro completo de history_vision por id."""
    sql = f"SELECT {_VISION_RECORD_COLUMNS} FROM history_vision WHERE id=%s LIMIT 1"
    return execute_query(sql, (record_id,), fetch="one")


_VISION_TWIN_WINDOW = timedelta(minutes=10)


def _get_history_vision_sht_twin(record):
    """Registro SHT de la misma pieza (mismo QR o barcode y resultado) cerca de un registro shlog.

    El watcher a veces escribe la pieza dos veces: del .txt SHT y del .shlog con la hora
    corrida 9-200 s (fuera de su ventana de +-3 s contra el SHT). La foto es la del SHT,
    sellada con la hora exacta del SHT. Medido 2026-10-27: 13 de 15 shlog en M4, 24 de 72 en M3.
    """
    qr = str(record.get("serial_qr") or "").strip()
    barcode = str(record.get("barcode") or "").strip()
    reference_dt = _vision_reference_datetime(record)
    if not reference_dt or not (qr or barcode):
        return None
    # None en vez de '': "serial_qr = NULL" nunca empata con las filas sin codigo.
    sql = (
        f"SELECT {_VISION_RECORD_COLUMNS} FROM history_vision "
        "WHERE result=%s AND log_datetime BETWEEN %s AND %s AND machine_name=%s "
        "AND source_file LIKE %s AND (serial_qr=%s OR barcode=%s) "
        # El QR de la pieza manda: el .shlog a veces le pega el barcode de la vecina.
        "ORDER BY (serial_qr <=> %s) DESC, ABS(TIMESTAMPDIFF(MICROSECOND, log_datetime, %s)) "
        "LIMIT 1"
    )
    params = (
        record.get("result"), reference_dt - _VISION_TWIN_WINDOW, reference_dt + _VISION_TWIN_WINDOW,
        record.get("machine_name"), "%.txt", qr or None, barcode or None, qr or None, reference_dt,
    )
    return execute_query(sql, params, fetch="one")


# Tolerancias de la busqueda de imagen (segundos).
_VISION_EXACT_SECONDS = 0.01  # SHT: el sello de la foto es log_datetime al milisegundo
_VISION_NEAREST_SECONDS = 1.0  # shlog: la foto es 0.2-0.4 s anterior al fin de la inspeccion (OK)
# shlog NG: la inspeccion tarda mas; M2 2026-10-27 tenia la foto 1.01-1.14 s antes del fin.
# La foto nunca es posterior al fin, asi que solo hacia atras; misma ventana del watcher (+-3 s).
_VISION_SHLOG_BEFORE_SECONDS = 3.0


def _vision_record_codes(record):
    """QR y barcode de la pieza, normalizados, para compararlos con el nombre de la foto."""
    return {
        str(value).strip().upper()
        for value in (record.get("qr_payload"), record.get("serial_qr"), record.get("barcode"))
        if str(value or "").strip()
    }


def _vision_pick_image_candidate(candidates, source):
    """Elegir la foto segun de donde viene el registro (source_file).
    Devuelve (candidato, tipo_de_coincidencia) o (None, "").

    - SHT (.txt): log_datetime ES el sello de la foto, al milisegundo -> hora exacta. Si el
      nombre trae codigo debe ser el de la pieza (el del SHT es exacto: distinto = otra pieza).
    - shlog: log_datetime es el fin de la inspeccion, 0.2-0.4 s despues de la foto, y sus
      codigos vienen del escaner de mano (pueden ser de la pieza vecina) -> la foto mas
      cercana en hora, sin mirar el codigo.
    """
    if source == "SHT":
        exact = [
            c for c in candidates
            if c["delta_seconds"] <= _VISION_EXACT_SECONDS and c["code_consistent"]
        ]
        if not exact:
            return None, ""
        best = min(exact, key=lambda c: c["delta_seconds"])
        return best, "exacta (hora y codigo)" if best["code_match"] else "exacta (hora)"

    nearest = [
        c for c in candidates
        if c["delta_seconds"] <= _VISION_NEAREST_SECONDS
        or 0 <= c["photo_before_seconds"] <= _VISION_SHLOG_BEFORE_SECONDS
    ]
    if not nearest:
        return None, ""
    return min(nearest, key=lambda c: c["delta_seconds"]), "por hora mas cercana"


def _resolve_history_vision_image(record):
    """Resolver la imagen de un registro de history_vision segun su fuente (SHT o shlog)."""
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    expected_result = str(record.get("result") or "").strip().upper()
    part_code = str(record.get("part_code") or "").strip()
    part_code_prefix = part_code.upper()[:11]
    reference_dt = _vision_reference_datetime(record)
    share_roots = _vision_candidate_share_roots(record)
    source = _vision_record_source(record)
    record_codes = _vision_record_codes(record)

    result_payload = {
        "record_id": record.get("id"),
        "resolved_path": "",
        "share_name": "",
        "side_folder": "",
        "delta_seconds": None,
        "searched_paths": [],
        "reference_datetime": _vision_format_value(reference_dt) if reference_dt else "",
        "share_roots": [str(root) for root in share_roots],
        "fuente": source,
        "match_type": "",
    }

    if not part_code:
        result_payload["error"] = "El registro no tiene numero de parte."
        return result_payload

    if expected_result not in {"OK", "NG"}:
        result_payload["error"] = "El resultado del registro no es valido."
        return result_payload

    if not reference_dt:
        result_payload["error"] = "No se pudo determinar la fecha/hora del registro."
        return result_payload

    if not share_roots:
        result_payload["error"] = "No se encontraron rutas compartidas candidatas."
        return result_payload

    # is_dir() de un share sin acceso da False igual que una carpeta que no existe: sin
    # esta revision, una sesion de red caida se reportaba como "no se encontro la foto".
    # Solo si ninguna responde se monta: "\\IP\Result" no existe en todas las PCs (error 67).
    share_roots = (
        [root for root in share_roots if os.path.isdir(str(root))]
        or [root for root in share_roots if _vision_mount_share(root)]
    )
    if not share_roots:
        result_payload["error"] = (
            "Sin acceso a la carpeta de la vision ("
            + ", ".join(result_payload["share_roots"])
            + "). Revise la red de la PC o VISION_SHARE_USER / VISION_SHARE_PASSWORD en el .env."
        )
        result_payload["share_inaccessible"] = True
        return result_payload

    filename_part_prefix = part_code_prefix or part_code.upper()
    # <Modelo>_<Zona>_[<ultimo codigo leido>_]<AAAAMMDD>_<HHMMSSmmm>_<OK|NG>.jpg
    # Las recetas que leen QR/DataMatrix meten ese codigo en el nombre; las que no, no.
    filename_pattern = re.compile(
        rf"^{re.escape(filename_part_prefix)}(?:[^_]*)_(?P<side>[^_]+)_(?:(?P<code>[^_]*)_)?"
        rf"(?P<stamp>\d{{8}}_\d{{9}})_(?P<result>OK|NG)\.(?P<ext>jpg|jpeg|png|bmp)$",
        re.IGNORECASE,
    )

    candidates = []
    searched_paths = []
    seen_search_paths = set()

    for share_root in share_roots:
        for hour_dir in _vision_candidate_hour_directories(
            share_root, part_code, reference_dt
        ):
            hour_dir_str = str(hour_dir)
            hour_dir_key = os.path.normcase(os.path.normpath(hour_dir_str))
            if hour_dir_key not in seen_search_paths:
                seen_search_paths.add(hour_dir_key)
                searched_paths.append(hour_dir_str)

            try:
                if not hour_dir.is_dir():
                    continue
                side_directories = sorted(
                    [child for child in hour_dir.iterdir() if child.is_dir()],
                    key=lambda path: path.name.lower(),
                )
            except OSError:
                continue

            for side_dir in side_directories:
                result_dir = side_dir / expected_result
                result_dir_str = str(result_dir)
                result_dir_key = os.path.normcase(os.path.normpath(result_dir_str))
                if result_dir_key not in seen_search_paths:
                    seen_search_paths.add(result_dir_key)
                    searched_paths.append(result_dir_str)

                try:
                    if not result_dir.is_dir():
                        continue
                    image_candidates = sorted(
                        [child for child in result_dir.iterdir() if child.is_file()],
                        key=lambda path: path.name.lower(),
                    )
                except OSError:
                    continue

                for image_path in image_candidates:
                    if image_path.suffix.lower() not in image_extensions:
                        continue

                    match = filename_pattern.match(image_path.name)
                    if not match or match.group("result").upper() != expected_result:
                        continue

                    try:
                        file_dt = datetime.strptime(
                            match.group("stamp"), "%Y%m%d_%H%M%S%f"
                        )
                    except ValueError:
                        continue

                    file_code = (match.group("code") or "").strip().upper()
                    code_match = bool(file_code) and file_code in record_codes
                    candidates.append({
                        "path": image_path,
                        "share_name": _vision_share_name(share_root),
                        "side_folder": side_dir.name,
                        "delta_seconds": abs((file_dt - reference_dt).total_seconds()),
                        "photo_before_seconds": (reference_dt - file_dt).total_seconds(),
                        "code_match": code_match,
                        # Un codigo distinto en el nombre es otra pieza (aunque la hora sea cercana).
                        "code_consistent": code_match or not file_code or not record_codes,
                    })

    result_payload["searched_paths"] = searched_paths

    best_candidate, match_type = _vision_pick_image_candidate(candidates, source)
    if best_candidate:
        result_payload.update(
            {
                "resolved_path": str(best_candidate["path"]),
                "share_name": best_candidate["share_name"],
                "side_folder": best_candidate["side_folder"],
                "delta_seconds": round(best_candidate["delta_seconds"], 3),
                "match_type": match_type,
            }
        )
        return result_payload

    if source == "SHT":
        result_payload["error"] = "No se encontro la foto con la misma hora (registro SHT)."
        return result_payload

    twin_payload = _resolve_from_sht_twin(record, result_payload)
    if twin_payload:
        return twin_payload
    result_payload["error"] = (
        "No se encontro una foto cercana (1 s, o hasta 3 s antes) ni un registro SHT de la "
        "misma pieza (registro shlog)."
    )
    return result_payload


def _resolve_from_sht_twin(record, result_payload):
    """Foto de un registro shlog tomada de su gemelo SHT (misma pieza); None si no hay."""
    try:
        twin = _get_history_vision_sht_twin(record)
    except Exception:
        logger.warning("No se pudo buscar el registro SHT gemelo de %s", record.get("id"), exc_info=True)
        return None
    if not twin:
        return None
    twin_payload = _resolve_history_vision_image(twin)  # SHT: no vuelve a buscar gemelo
    if not twin_payload.get("resolved_path"):
        return None
    twin_payload.update({
        "record_id": result_payload["record_id"],
        "reference_datetime": result_payload["reference_datetime"],
        "fuente": result_payload["fuente"],
        "searched_paths": result_payload["searched_paths"] + twin_payload["searched_paths"],
        "match_type": f"misma pieza en el registro SHT {twin.get('id')} (QR/barcode)",
        "twin_record_id": twin.get("id"),
    })
    return twin_payload


# ---------------------------------------------------------------------------
# Detalle de NG (history_vision_defects, lo llena el watcher de Vision desde el SHT)
# ---------------------------------------------------------------------------

_VISION_DEFECTS_RECHECK_SECONDS = 300
_vision_defects_state = {"available": False, "checked_at": None}

# Fallas de una pieza NG como arreglo JSON (una entrada por posicion / sub-prueba); la app
# las separa en Componente / Tipo de falla / Valor. Subconsulta por fila sobre
# idx_source_uid, solo en las NG.
_VISION_FALLAS_SQL = (
    "(CASE WHEN result = 'NG' THEN ("
    "SELECT JSON_ARRAYAGG(JSON_OBJECT("
    "'test_name', d.test_name, 'position', d.position, 'sub_test', d.sub_test, "
    "'value_text', d.value_text, 'value_num', d.value_num)) "
    "FROM history_vision_defects d WHERE d.source_uid = history_vision.source_uid"
    ") END)"
)


def _vision_defect_columns(test_name, position, sub_test, value_text, value_num):
    """Una falla en las columnas del historial / Excel:
    tipo "Conector", componente "CON101", tipo de falla "Maker_Axis", valor 75.46 (numero)
    y unidad "%".

    Lecturas de codigo NG no tienen posicion (componente vacio) ni sub-prueba: el tipo de
    falla es el motivo ("no leyo la etiqueta").
    Valores sin un solo numero (color "95,89,24") quedan como texto.
    """
    value_text = str(value_text or "")
    if value_num is not None:
        valor = round(float(value_num), 2)
        unidad = "%" if "%" in value_text else ""
    else:
        valor = value_text
        unidad = ""
    tipo = str(sub_test or "")
    if not tipo:
        # Lectura de codigo: "no leyo la etiqueta" o "etiqueta no corresponde al modelo: <codigo>".
        # El tipo queda corto (para agrupar en graficas) y el codigo leido va en el valor.
        motivo, _, codigo = value_text.partition(": ")
        tipo, valor = motivo, codigo
    return {
        "tipo": str(test_name or ""),
        "componente": str(position or ""),
        "tipo_falla": tipo,
        "valor": valor,
        "unidad": unidad,
    }


def _vision_parse_fallas(raw):
    """Columna `fallas` (arreglo JSON de la subconsulta) -> lista de columnas por falla."""
    if not raw:
        return []
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    try:
        items = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return []
    return [
        _vision_defect_columns(
            item.get("test_name"), item.get("position"), item.get("sub_test"),
            item.get("value_text"), item.get("value_num"),
        )
        for item in (items or [])
        if isinstance(item, dict)
    ]


def _vision_defects_table_available():
    """True si existe history_vision_defects. La crea el watcher de Vision con el primer NG
    del SHT; mientras no exista, el historial funciona igual pero sin detalle de falla."""
    if _vision_defects_state["available"]:
        return True
    now = time.monotonic()
    checked_at = _vision_defects_state["checked_at"]
    if checked_at is not None and now - checked_at < _VISION_DEFECTS_RECHECK_SECONDS:
        return False
    _vision_defects_state["checked_at"] = now
    row = execute_query(
        "SELECT COUNT(*) AS n FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = %s",
        ("history_vision_defects",),
        fetch="one",
    ) or {}
    _vision_defects_state["available"] = bool(row.get("n"))
    return _vision_defects_state["available"]


def _get_history_vision_defects(source_uid):
    """Posiciones que fallaron en una pieza NG del SHT (vacio si vino del .shlog)."""
    if not source_uid or not _vision_defects_table_available():
        return []
    sql = (
        "SELECT test_name, position, sub_test, value_text, value_num "
        "FROM history_vision_defects WHERE source_uid=%s ORDER BY id LIMIT 50"
    )
    return execute_query(sql, (source_uid,), fetch="all") or []


# ---------------------------------------------------------------------------
# Parametros completos de una pieza SHT: se leen del .txt de resultados al momento
# (no se guardan en la base). Una fila por pieza, TAB: [NAME-ZONE] [DATE] [JUDGE] [ID] y
# bloques de 6 por prueba: [NAME] [JUDGE] [LOWER] [UPPER] [VALUE] [TESTED].
# ---------------------------------------------------------------------------

# Posiciones dentro del [VALUE] de un grupo: "CON1:OK,CON4:NG>FALTANTE:NG>77.8". Las
# plantillas meten comas en su valor ("posicion:-214.5,-19.9"): solo se corta antes de algo
# con forma "nombre:OK" / "nombre:NG".
_VISION_SHT_ITEM_SPLIT_RE = re.compile(r",\s*(?=[^,:>]+:(?:OK|NG)\b)")
_VISION_SHT_CODE_TOOL_RE = re.compile(r"Barcode|QR|DataMatrix", re.IGNORECASE)
_VISION_SHT_TERMS = {
    "갯수": "cantidad",
    "일치율": "coincidencia",
    "위치": "posicion",
    "각도": "angulo",
    "크기": "escala",
    "←": "<-",
}


def _vision_sht_translate(text):
    """Textos coreanos de las plantillas (Maker_Axis, Direction-Marker...) al espanol."""
    for korean, spanish in _VISION_SHT_TERMS.items():
        text = text.replace(korean, spanish)
    return text


def _vision_sht_stamp(record):
    """[DATE] de la fila SHT de la pieza: es log_datetime al milisegundo."""
    reference = _vision_reference_datetime(record)
    if not reference:
        return ""
    return reference.strftime("%Y-%m-%d %H:%M:%S.") + f"{reference.microsecond // 1000:03d}"


def _read_sht_row(path, stamp):
    """Columnas de la fila de la pieza (por su [DATE] exacto), o None si no esta.

    open() de Python comparte lectura y escritura: no bloquea a la maquina, que sigue
    agregando filas. Algunas recetas guardan el coreano en CP949 y no en UTF-8.
    """
    needle = f"\t{stamp}\t".encode("ascii")
    with open(path, "rb") as handle:
        for raw in handle:
            if needle not in raw:
                continue
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError:
                line = raw.decode("cp949", errors="replace")
            columns = line.rstrip("\r\n").split("\t")
            if len(columns) >= 4 and columns[1].strip() == stamp:
                return columns
    return None


def _vision_sht_positions(value):
    """[VALUE] de un grupo -> [{posicion, resultado, detalle}]. La maquina solo guarda el
    detalle medido de lo que fallo; de las posiciones OK solo dice "OK"."""
    value = value.strip()
    if not value:
        return []
    if value in ("OK", "NG"):  # grupo de una sola posicion
        return [{"posicion": "", "resultado": value, "detalle": ""}]

    positions = []
    for item in _VISION_SHT_ITEM_SPLIT_RE.split(value):
        item = item.strip()
        head, _, rest = item.partition(":")
        if rest == "OK":
            positions.append({"posicion": head, "resultado": "OK", "detalle": ""})
        elif rest.startswith("NG>"):
            failure = rest[3:]
            detail = _vision_sht_translate(failure).replace(":NG>", " > ")
            previous = positions[-1] if positions else None
            if previous and previous["resultado"] == "NG" and previous["detalle"] and ":NG>" not in failure:
                # Otra sub-prueba de la misma posicion: "CON202:NG>FALTANTE:NG>43.5, INVERTIDO:NG>48.9"
                previous["detalle"] += f"; {head} > {detail}"
            else:
                positions.append({"posicion": head, "resultado": "NG", "detalle": detail})
        else:
            positions.append({"posicion": "", "resultado": "", "detalle": _vision_sht_translate(item)})
    return positions


def _parse_sht_parameters(columns):
    """Fila SHT -> todas las pruebas de la pieza con sus posiciones, y un resumen."""
    tests = []
    total_positions = 0
    total_ng = 0
    for i in range(4, len(columns) - 5, 6):
        name, judge, lower, upper, value, tested = (c.strip() for c in columns[i:i + 6])
        executed = tested.upper() != "UNTESTED"
        # Lecturas de codigo sueltas: [VALUE] es el codigo leido (vacio = no leyo la etiqueta).
        is_code = bool(_VISION_SHT_CODE_TOOL_RE.search(name)) and value not in ("OK", "NG") \
            and not re.search(r":(OK|NG)", value)
        positions = [] if is_code or not executed else _vision_sht_positions(value)
        tests.append({
            "prueba": name,
            "resultado": judge.upper(),
            "ejecutada": executed,
            "limite_inferior": lower,
            "limite_superior": upper,
            "es_lectura": is_code,
            "lectura": value if is_code else "",
            "posiciones": positions,
        })
        if executed:
            total_positions += len(positions)
            ng_positions = sum(1 for p in positions if p["resultado"] == "NG")
            total_ng += ng_positions or (1 if judge.upper() == "NG" else 0)
    return {
        "fecha": columns[1].strip(),
        "resultado": columns[2].strip().upper(),
        "pruebas": tests,
        "resumen": {"pruebas": len(tests), "posiciones": total_positions, "ng": total_ng},
    }


# ---------------------------------------------------------------------------
# Builders de query SQL
# ---------------------------------------------------------------------------


def _vision_date_filter_sql(fecha_desde, fecha_hasta):
    """Filtro de fechas de history_vision que usa idx_result_datetime (result, log_datetime).

    Filtrar por log_date (sin indice) recorria la tabla completa: 1.8M filas, ~1 s por
    consulta y creciendo. Con result IN ('OK','NG') + rango de log_datetime MySQL lee solo
    ese rango del indice (~20 ms). Es equivalente: log_date = DATE(log_datetime) en toda la
    tabla y el watcher de Vision solo escribe OK/NG.
    """
    if not fecha_desde and not fecha_hasta:
        return "", []

    sql = " AND result IN ('OK','NG')"
    params = []
    if fecha_desde:
        sql += " AND log_datetime >= %s"
        params.append(fecha_desde)
    if fecha_hasta:
        try:
            next_day = (date.fromisoformat(fecha_hasta) + timedelta(days=1)).isoformat()
        except ValueError:
            next_day = None
        if next_day:
            sql += " AND log_datetime < %s"
            params.append(next_day)
        else:  # fecha rara: se respeta tal cual, aunque sea lento
            sql += " AND log_date <= %s"
            params.append(fecha_hasta)
    return sql, params


def _build_history_vision_where():
    """WHERE compartido por listado, conteo y exportacion de registros Vision."""
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    linea = request.args.get("linea", "").strip()
    resultado = request.args.get("resultado", "").strip()
    numero_parte = request.args.get("numero_parte", "").strip()
    qr = request.args.get("qr", "").strip()
    barcode = request.args.get("barcode", "").strip()

    sql = " FROM history_vision WHERE 1=1"
    params = []

    date_sql, date_params = _vision_date_filter_sql(fecha_desde, fecha_hasta)
    sql += date_sql
    params.extend(date_params)
    if linea:
        sql += " AND machine_name LIKE %s"
        params.append(f"%{linea}%")
    if resultado:
        sql += " AND result=%s"
        params.append(resultado)
    if numero_parte:
        sql += " AND part_code LIKE %s"
        params.append(f"%{numero_parte}%")
    if qr:
        sql += " AND qr_payload LIKE %s"
        params.append(f"%{qr}%")
    if barcode:
        sql += " AND barcode LIKE %s"
        params.append(f"%{barcode}%")

    column_filter_sql = {
        "linea": "machine_name LIKE %s",
        "fecha": "CAST(log_date AS CHAR) LIKE %s",
        "hora": "CAST(log_time AS CHAR) LIKE %s",
        "numero_parte": "part_code LIKE %s",
        "qr": "qr_payload LIKE %s",
        "barcode": "barcode LIKE %s",
        "resultado": "result LIKE %s",
    }
    if _vision_defects_table_available():
        # Semi-join contra la tabla de fallas (chica): piezas con alguna falla que coincida.
        column_filter_sql["tipo"] = (
            "source_uid IN (SELECT d.source_uid FROM history_vision_defects d "
            "WHERE d.test_name LIKE %s)"
        )
        column_filter_sql["componente"] = (
            "source_uid IN (SELECT d.source_uid FROM history_vision_defects d "
            "WHERE d.position LIKE %s)"
        )
        column_filter_sql["tipo_falla"] = (
            "source_uid IN (SELECT d.source_uid FROM history_vision_defects d "
            "WHERE IF(d.sub_test <> '', d.sub_test, d.value_text) LIKE %s)"
        )
    for key, clause in column_filter_sql.items():
        value = request.args.get(f"cf_{key}", "").strip()
        if value:
            sql += f" AND {clause}"
            params.append(f"%{value}%")

    return sql, params


def _build_history_vision_query(limit=None, offset=0):
    """Query de registros; sin ``limit`` devuelve todo para exportacion/compatibilidad."""
    where_sql, params = _build_history_vision_where()
    fallas_sql = _VISION_FALLAS_SQL if _vision_defects_table_available() else "NULL"
    sql = (
        "SELECT "
        "id, "
        "machine_name AS linea, "
        "log_date AS fecha, "
        "log_time AS hora, "
        "part_code AS numero_parte, "
        "qr_payload AS qr, "
        "barcode, "
        "result AS resultado, "
        f"{fallas_sql} AS fallas"
        + where_sql
        + " ORDER BY COALESCE(log_datetime, created_at) DESC, id DESC"
    )
    if limit is not None:
        sql += " LIMIT %s OFFSET %s"
        params.extend([max(1, int(limit)), max(0, int(offset))])

    return sql, tuple(params)


def _build_history_vision_count_query():
    """Conteo total de registros Vision con los mismos filtros del listado."""
    where_sql, params = _build_history_vision_where()
    return "SELECT COUNT(*) AS n" + where_sql, tuple(params)


def _build_history_vision_pass_fail_summary_query():
    """Construir query y parametros para el resumen Pass/Fail por linea y numero de parte."""
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    numero_parte = request.args.get("numero_parte", "").strip()

    sql = (
        "SELECT "
        "COALESCE(NULLIF(TRIM(machine_name), ''), 'SIN LINEA') AS linea, "
        "COALESCE(NULLIF(TRIM(part_code), ''), 'SIN NUMERO DE PARTE') AS numero_parte, "
        "COUNT(*) AS total, "
        "SUM(CASE WHEN UPPER(COALESCE(result, '')) = 'OK' THEN 1 ELSE 0 END) AS ok_count, "
        "SUM(CASE WHEN UPPER(COALESCE(result, '')) = 'NG' THEN 1 ELSE 0 END) AS ng_count "
        "FROM history_vision WHERE 1=1"
    )
    params = []

    date_sql, date_params = _vision_date_filter_sql(fecha_desde, fecha_hasta)
    sql += date_sql
    params.extend(date_params)
    if numero_parte:
        sql += " AND part_code LIKE %s"
        params.append(f"%{numero_parte}%")

    sql += (
        " GROUP BY COALESCE(NULLIF(TRIM(machine_name), ''), 'SIN LINEA'),"
        " COALESCE(NULLIF(TRIM(part_code), ''), 'SIN NUMERO DE PARTE')"
        " ORDER BY linea ASC, total DESC, numero_parte ASC"
    )

    return sql, tuple(params) if params else None


# ---------------------------------------------------------------------------
# Paros reales de Vision (history_vision_ng_stops) + relacion con ajustes
# ---------------------------------------------------------------------------

VISION_STOP_START_SQL = "COALESCE(s.sequence_error_datetime, s.stop_datetime)"


def _build_vision_stops_where():
    """WHERE compartido por listado, conteo y exportacion de paros de Vision."""
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    linea = request.args.get("linea", "").strip()
    estado = request.args.get("estado", "").strip()  # open | confirmed | failed_recovery
    sql = f" FROM history_vision_ng_stops s WHERE {VISION_STOP_START_SQL} IS NOT NULL"
    params = []
    if fecha_desde:
        sql += f" AND {VISION_STOP_START_SQL} >= %s"
        params.append(fecha_desde)
    if fecha_hasta:
        sql += f" AND {VISION_STOP_START_SQL} < DATE_ADD(%s, INTERVAL 1 DAY)"
        params.append(fecha_hasta)
    if linea:
        sql += " AND s.machine_name = %s"
        params.append(linea)
    if estado in {"open", "confirmed", "failed_recovery"}:
        sql += " AND s.recovery_status = %s"
        params.append(estado)
    else:
        sql += " AND s.recovery_status IN ('open', 'confirmed')"

    column_filters = {
        key: request.args.get(f"cf_{key}", "").strip()
        for key in (
            "linea", "numero_parte", "sequence_error_datetime", "stop_datetime",
            "stable_run_datetime", "paro_real", "run_attempt_count", "tecnico_ajuste",
        )
    }
    simple_filter_sql = {
        "linea": "s.machine_name LIKE %s",
        "numero_parte": "s.part_code LIKE %s",
        "sequence_error_datetime": f"CAST({VISION_STOP_START_SQL} AS CHAR) LIKE %s",
        "stop_datetime": "CAST(s.stop_datetime AS CHAR) LIKE %s",
        "stable_run_datetime": "CAST(s.stable_run_datetime AS CHAR) LIKE %s",
        "paro_real": (
            "TIME_FORMAT(SEC_TO_TIME(COALESCE(s.real_stop_seconds, "
            f"TIMESTAMPDIFF(MICROSECOND, {VISION_STOP_START_SQL}, NOW())/1e6)), "
            "'%%H:%%i:%%s.%%f') LIKE %s"
        ),
        "run_attempt_count": "CAST(s.run_attempt_count AS CHAR) LIKE %s",
    }
    for key, clause in simple_filter_sql.items():
        if column_filters[key]:
            sql += f" AND {clause}"
            params.append(f"%{column_filters[key]}%")

    if column_filters["tecnico_ajuste"]:
        tecnico_expr = (
            "COALESCE(NULLIF(TRIM(a.usuario), ''), NULLIF(TRIM(a.username), ''), "
            "NULLIF(TRIM(o.display_name), ''), NULLIF(TRIM(o.badge_code), ''), "
            "CASE WHEN JSON_VALID(e.details_json) THEN NULLIF(NULLIF(TRIM(JSON_UNQUOTE("
            "JSON_EXTRACT(e.details_json, '$.DisplayName'))), ''), 'null') END, "
            "CASE WHEN JSON_VALID(e.details_json) THEN NULLIF(NULLIF(TRIM(JSON_UNQUOTE("
            "JSON_EXTRACT(e.details_json, '$.BadgeCode'))), ''), 'null') END, '')"
        )
        sql += (
            " AND EXISTS (SELECT 1 FROM historial_estaciones_qa a "
            "LEFT JOIN station_events_QA e ON e.id = a.session_id "
            "AND e.event_type = 'WindowClosed' "
            "LEFT JOIN operators_QA o ON o.id = e.operator_id "
            "WHERE a.estado = 'Ajuste' AND a.estacion LIKE 'VISION-%%' "
            f"AND a.linea = s.machine_name AND a.fin_local >= {VISION_STOP_START_SQL} "
            "AND a.inicio_local <= COALESCE(s.stable_run_datetime, NOW()) "
            f"AND CONCAT_WS(' ', {tecnico_expr}, CAST(a.inicio_local AS CHAR), "
            "CAST(a.fin_local AS CHAR)) LIKE %s)"
        )
        params.append(f"%{column_filters['tecnico_ajuste']}%")

    return sql, params


def _build_vision_stops_query(limit=None, offset=0):
    """Query de paros; sin ``limit`` devuelve todo para exportacion/compatibilidad."""
    where_sql, params = _build_vision_stops_where()
    sql = (
        f"SELECT s.source_uid, s.machine_name AS linea, "
        f"{VISION_STOP_START_SQL} AS sequence_error_datetime, "
        "s.stop_datetime, s.stable_run_datetime, "
        "s.real_stop_seconds, "
        "COALESCE(s.real_stop_seconds, "
        f"         TIMESTAMPDIFF(MICROSECOND, {VISION_STOP_START_SQL}, NOW())/1e6) AS real_stop_prov, "
        "s.run_attempt_count, "
        "s.recovery_status, s.part_code, s.ng_datetime"
        + where_sql
        + f" ORDER BY {VISION_STOP_START_SQL} DESC"
    )
    if limit is not None:
        sql += " LIMIT %s OFFSET %s"
        params.extend([max(1, int(limit)), max(0, int(offset))])
    return sql, tuple(params)


def _build_vision_stops_count_query():
    """Conteo y tiempo total con exactamente los mismos filtros del listado."""
    where_sql, params = _build_vision_stops_where()
    aggregate_sql = (
        "SELECT COUNT(*) AS n, "
        "COALESCE(SUM(COALESCE(s.real_stop_seconds, "
        f"TIMESTAMPDIFF(MICROSECOND, {VISION_STOP_START_SQL}, NOW())/1e6)), 0) "
        "AS total_stop_seconds"
    )
    return aggregate_sql + where_sql, tuple(params)


def _fetch_ajustes_for_stops(rows):
    """Un solo query en lote para los ajustes de Vision que solapan los paros de la pagina,
    agrupados por paro en Python. Para paros open el solape usa NOW() como fin provisional."""
    if not rows:
        return {}
    lineas = sorted({r.get("linea") for r in rows if r.get("linea")})
    if not lineas:
        return {}

    now = datetime.now()
    stops_dt = [
        r.get("sequence_error_datetime")
        for r in rows
        if r.get("sequence_error_datetime")
    ]
    fines = [r.get("stable_run_datetime") or now for r in rows]
    if not stops_dt:
        return {}
    min_stop = min(stops_dt)
    max_fin = max(fines)

    placeholders = ", ".join(["%s"] * len(lineas))
    sql = (
        "SELECT a.linea, a.session_id, "
        "COALESCE(NULLIF(TRIM(a.usuario), ''), NULLIF(TRIM(a.username), ''), "
        "         NULLIF(TRIM(o.display_name), ''), NULLIF(TRIM(o.badge_code), ''), "
        "         CASE WHEN JSON_VALID(e.details_json) "
        "              THEN NULLIF(NULLIF(TRIM(JSON_UNQUOTE(JSON_EXTRACT(e.details_json, '$.DisplayName'))), ''), 'null') END, "
        "         CASE WHEN JSON_VALID(e.details_json) "
        "              THEN NULLIF(NULLIF(TRIM(JSON_UNQUOTE(JSON_EXTRACT(e.details_json, '$.BadgeCode'))), ''), 'null') END) AS tecnico, "
        "a.inicio_local, a.fin_local "
        "FROM historial_estaciones_qa a "
        "LEFT JOIN station_events_QA e ON e.id = a.session_id AND e.event_type = 'WindowClosed' "
        "LEFT JOIN operators_QA o ON o.id = e.operator_id "
        "WHERE a.estado = 'Ajuste' AND a.estacion LIKE 'VISION-%%' "
        f"AND a.linea IN ({placeholders}) "
        "AND a.fin_local >= %s AND a.inicio_local <= %s"
    )
    params = tuple(lineas) + (min_stop, max_fin)
    ajustes = execute_query(sql, params, fetch="all") or []

    # Empareja cada ajuste con el intervalo real [ERROR inicial, RUN estable].
    by_uid = {}
    for r in rows:
        stop_start = r.get("sequence_error_datetime")
        if stop_start is None:
            continue
        fin = r.get("stable_run_datetime") or now
        for a in ajustes:
            if a.get("linea") != r.get("linea"):
                continue
            if a.get("fin_local") is None or a.get("inicio_local") is None:
                continue
            if a["fin_local"] >= stop_start and a["inicio_local"] <= fin:
                by_uid.setdefault(r["source_uid"], []).append({
                    "session_id": a.get("session_id"),
                    "tecnico": _vision_format_value(a.get("tecnico")) or "",
                    "inicio_local": _vision_format_value(a.get("inicio_local")) or "",
                    "fin_local": _vision_format_value(a.get("fin_local")) or "",
                })
    return by_uid
