import os
import re
import threading
from collections import OrderedDict, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional


ICT_BASE_DIR = os.environ.get(
    "ICT_ODATA_BASE_DIR",
    r"\\192.168.1.144\lg-pws\TDATA\ICT\ODATA",
)
_CACHE_MAX = 256
_PARSE_CACHE = OrderedDict()
_PARSE_CACHE_LOCK = threading.RLock()

NUM_HYPHEN_RE = re.compile(r"(\d+)\s*-\s*(\d+)")
FLOAT_RE = re.compile(r"[-+]?\d+\.\d+")
INT_RE = re.compile(r"[-+]?\d+")
FAIL_TOKENS = re.compile(
    r"\b(LOWLIMIT|HIGHLIMIT|HIGHTLIMIT|OPENNG|SHORTNG|OVERLIMIT|UNDERLIMIT|[A-Z]+NG)\b",
    re.IGNORECASE,
)


class IctLgdError(Exception):
    """Base error for ICT LGD local-file access."""


class IctLgdPathError(IctLgdError):
    """Raised when a relative source path is unsafe."""


class IctLgdNotFoundError(IctLgdError):
    """Raised when the source LGD file does not exist."""


def normalize_defecto(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    value = token.upper()
    return "HIGHLIMIT" if value == "HIGHTLIMIT" else value


def is_valid_defecto(token: Optional[str]) -> bool:
    if not token:
        return False
    value = token.upper()
    if value in {
        "LOWLIMIT",
        "HIGHLIMIT",
        "HIGHTLIMIT",
        "OPENNG",
        "SHORTNG",
        "OVERLIMIT",
        "UNDERLIMIT",
    }:
        return True
    return value.endswith("NG")


def to_float(value):
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def to_int(value):
    try:
        return int(float(str(value).replace(",", "")))
    except Exception:
        return None


def extrae_linea_ict(linea_raw: str):
    if not linea_raw:
        return "UNKNOWN", 0
    raw = str(linea_raw)
    direct = re.findall(r"[Mm]+\s*(\d+)\s*-\s*(\d+)", raw)
    if direct:
        a, b = direct[-1]
        return f"M{a}", int(b)
    any_match = NUM_HYPHEN_RE.findall(raw)
    if any_match:
        a, b = any_match[-1]
        return f"M{a}", int(b)
    return "UNKNOWN", 0


def primeros_veredictos_ok_ng(tokens):
    veredictos = []
    first_index = None
    for index, token in enumerate(tokens):
        value = token.strip().upper()
        if value in ("OK", "NG"):
            if first_index is None:
                first_index = index
            veredictos.append(value)
            if len(veredictos) == 2:
                break
    first = veredictos[0] if veredictos else None
    second = veredictos[1] if len(veredictos) > 1 else None
    return first, second, first_index


def parse_ws_ds_rc(after_tokens):
    numbers = []
    for token in after_tokens:
        value = token.strip()
        if value and (FLOAT_RE.fullmatch(value) or INT_RE.fullmatch(value)):
            numbers.append(value)

    if not numbers:
        return None, None, None, None, None

    rest = numbers[2:] if len(numbers) > 2 else []

    ints = []
    for value in rest:
        if INT_RE.fullmatch(value):
            parsed = to_int(value)
            if parsed is not None:
                ints.append(parsed)
    hp_candidates = [value for value in ints if abs(value) > 0]
    hp_value = lp_value = None
    if len(hp_candidates) >= 2:
        hp_value, lp_value = hp_candidates[0], hp_candidates[1]
    elif len(ints) >= 2:
        hp_value, lp_value = ints[-2], ints[-1]

    floats = []
    for value in rest:
        if "." in value:
            parsed = to_float(value)
            if parsed is not None:
                floats.append(parsed)
    ws_value = floats[0] if len(floats) > 0 else None
    ds_value = floats[1] if len(floats) > 1 else None
    rc_value = floats[2] if len(floats) > 2 else None

    return hp_value, lp_value, ws_value, ds_value, rc_value


def rel_path_from_base(abs_path: str, base_dir: str = ICT_BASE_DIR) -> str:
    try:
        return os.path.relpath(abs_path, base_dir).replace("/", "\\")
    except Exception:
        return os.path.basename(abs_path)


def resolve_lgd_path(source_file: str, base_dir: str = ICT_BASE_DIR) -> Path:
    source = str(source_file or "").strip().replace("/", "\\")
    if not source:
        raise IctLgdPathError("Fuente de archivo vacia.")

    source_path = Path(source)
    if source_path.is_absolute():
        raise IctLgdPathError("La fuente ICT debe ser relativa.")

    parts = [part for part in source.split("\\") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise IctLgdPathError("La fuente ICT contiene una ruta no permitida.")
    if not parts[-1].lower().endswith(".lgd"):
        raise IctLgdPathError("La fuente ICT no es un archivo .lgd.")

    base = Path(base_dir)
    candidate = base.joinpath(*parts)
    try:
        base_resolved = base.resolve(strict=False)
        candidate_resolved = candidate.resolve(strict=False)
        if base_resolved != candidate_resolved and base_resolved not in candidate_resolved.parents:
            raise IctLgdPathError("La fuente ICT sale del directorio permitido.")
    except IctLgdPathError:
        raise
    except Exception:
        # Fallback for UNC resolution issues; the traversal checks above still apply.
        pass

    if not candidate.exists() or not candidate.is_file():
        raise IctLgdNotFoundError(f"No se encontro el archivo ICT: {source}")
    return candidate


def _row_key(row):
    return (
        str(row.get("componente") or ""),
        str(row.get("pinref") or ""),
        str(row.get("resultado_local") or ""),
    )


def _parse_file_uncached(abs_path: str, base_dir: str = ICT_BASE_DIR):
    per_bc = defaultdict(lambda: {
        "linea": None,
        "ict": None,
        "ts": None,
        "no_parte": None,
        "any_ng": False,
        "def_comps": set(),
        "def_vals": set(),
    })
    defects_rows = []
    all_components_by_bc = defaultdict(dict)
    parameters_by_bc = defaultdict(list)
    rel_src = rel_path_from_base(abs_path, base_dir)

    with open(abs_path, "r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue

            barcode = parts[1].strip()
            if not barcode:
                continue

            linea, ict = extrae_linea_ict(parts[2].strip())
            ts = None
            ts_raw = parts[3].strip()
            if ts_raw:
                try:
                    ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    try:
                        ts = datetime.fromisoformat(ts_raw)
                    except Exception:
                        ts = None

            tail = parts[4:] if len(parts) > 4 else []
            v1, v2, idx_v1 = primeros_veredictos_ok_ng(tail)
            linea_indica_ng = bool(v1 is not None and (v1 != "OK" or v2 == "NG"))

            componente = parts[4].strip() if len(parts) > 4 else ""
            pinref = parts[5].strip() if len(parts) > 5 else None
            act_value = to_float(parts[6]) if len(parts) > 6 else None
            act_unit = parts[7].strip() if len(parts) > 7 else None
            std_value = to_float(parts[8]) if len(parts) > 8 else None
            std_unit = parts[9].strip() if len(parts) > 9 else None
            meas_value = to_float(parts[10]) if len(parts) > 10 else None
            m_value = to_int(parts[12]) if len(parts) > 12 else None
            r_value = to_int(parts[13]) if len(parts) > 13 else None
            hlim_pct = to_float(parts[14]) if len(parts) > 14 else None
            llim_pct = to_float(parts[16]) if len(parts) > 16 else None

            defecto_tipo = None
            fail_match = FAIL_TOKENS.search(line)
            if fail_match:
                defecto_tipo = normalize_defecto(fail_match.group(1))
            defecto_valido = is_valid_defecto(defecto_tipo)
            linea_es_ng = defecto_valido

            p_flag = j_flag = None
            hp_value = lp_value = ws_value = ds_value = rc_value = None
            if idx_v1 is not None:
                after = tail[idx_v1 + (1 if v2 is None else 2):]
                num_found = []
                for token in after:
                    value = token.strip()
                    if re.fullmatch(r"[-+]?\d+(\.\d+)?", value):
                        num_found.append(value)
                        if len(num_found) == 2:
                            break
                if num_found:
                    p_flag = to_int(num_found[0])
                if len(num_found) > 1:
                    j_flag = to_int(num_found[1])
                hp_value, lp_value, ws_value, ds_value, rc_value = parse_ws_ds_rc(after)

            rec = per_bc[barcode]
            if rec["linea"] is None:
                rec["linea"] = linea
            if rec["ict"] in (None, 0):
                rec["ict"] = ict
            if rec["ts"] is None and ts:
                rec["ts"] = ts
            if rec["no_parte"] is None:
                rec["no_parte"] = barcode[:11]
            if linea_indica_ng:
                rec["any_ng"] = True

            row = {
                "barcode": barcode,
                "ts": ts,
                "fecha": ts.date() if ts else None,
                "hora": ts.time() if ts else None,
                "linea": linea,
                "ict": ict,
                "componente": componente,
                "pinref": pinref,
                "act_value": act_value,
                "act_unit": act_unit,
                "std_value": std_value,
                "std_unit": std_unit,
                "meas_value": meas_value,
                "m_value": m_value,
                "r_value": r_value,
                "hlim_pct": hlim_pct,
                "llim_pct": llim_pct,
                "hp_value": hp_value,
                "lp_value": lp_value,
                "ws_value": ws_value,
                "ds_value": ds_value,
                "rc_value": rc_value,
                "p_flag": p_flag,
                "j_flag": j_flag,
                "resultado_local": "NG" if linea_es_ng else "OK",
                "defecto_tipo": defecto_tipo if linea_es_ng else None,
                "fuente_archivo": rel_src,
            }

            if componente and componente not in all_components_by_bc[barcode]:
                all_components_by_bc[barcode][componente] = dict(row)

            parameters_by_bc[barcode].append(row)

            if linea_es_ng:
                rec["def_comps"].add(componente)
                rec["def_vals"].add(defecto_tipo)
                defects_rows.append(dict(row))

    summary = {}
    for barcode, info in per_bc.items():
        final = "NG" if info["any_ng"] else "OK"
        summary[barcode] = {
            "no_parte": info["no_parte"] or barcode[:11],
            "linea": info["linea"] or "UNKNOWN",
            "ict": int(info["ict"] or 0),
            "ts": info["ts"],
            "resultado": final,
            "defect_code": ",".join(sorted(info["def_comps"])) if final == "NG" else "",
            "defect_valor": ",".join(sorted(info["def_vals"])) if final == "NG" else "",
        }

    for barcode in parameters_by_bc:
        parameters_by_bc[barcode].sort(key=_row_key)

    return {
        "summary": summary,
        "defects_rows": defects_rows,
        "all_components_by_bc": all_components_by_bc,
        "parameters_by_bc": parameters_by_bc,
        "source_file": rel_src,
    }


def _cache_key(abs_path: str):
    stat = os.stat(abs_path)
    return str(Path(abs_path)), stat.st_mtime_ns, stat.st_size


def parse_lgd_payload(abs_path: str, base_dir: str = ICT_BASE_DIR):
    key = _cache_key(abs_path)

    with _PARSE_CACHE_LOCK:
        cached = _PARSE_CACHE.get(key)
        if cached is not None:
            _PARSE_CACHE.move_to_end(key)
            return cached

    payload = _parse_file_uncached(abs_path, base_dir)

    with _PARSE_CACHE_LOCK:
        same_path = key[0]
        for old_key in list(_PARSE_CACHE.keys()):
            if old_key[0] == same_path:
                _PARSE_CACHE.pop(old_key, None)
        _PARSE_CACHE[key] = payload
        while len(_PARSE_CACHE) > _CACHE_MAX:
            _PARSE_CACHE.popitem(last=False)

    return payload


def parse_lgd_file(abs_path: str, base_dir: str = ICT_BASE_DIR):
    payload = parse_lgd_payload(abs_path, base_dir)
    return payload["summary"], payload["defects_rows"], payload["all_components_by_bc"]


def get_lgd_parameters_for_barcode(abs_path: str, barcode: str, base_dir: str = ICT_BASE_DIR):
    """Devuelve las filas de parametros del barcode.

    IMPORTANTE: las rows pertenecen al cache. NO las mutes aqui. Si necesitas
    modificar, copia con `dict(row)` en el sitio del consumidor.
    """
    payload = parse_lgd_payload(abs_path, base_dir)
    return payload["parameters_by_bc"].get(barcode, [])
