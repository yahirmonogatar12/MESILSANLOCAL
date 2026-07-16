"""Herramientas del asistente IA para el pipeline de Plan de produccion LG.

Da al asistente MES la capacidad de, conversando, importar el plan LG y su
inventario (mismo Excel), decir que falta, y generar/acomodar los lotes del
dia respetando las 9 h por linea. Reutiliza la logica de
`app.api.control_produccion.part_planning` (no la duplica).

Seguridad: las acciones que ESCRIBEN (importar, generar, acomodar) usan
confirmacion de dos pasos. La tool de "preparar" calcula y devuelve un token
firmado con lo que se hara; la de "ejecutar" solo procede si recibe ese token
valido y no expirado. Asi el LLM nunca escribe sin que el usuario haya visto y
confirmado el resumen.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import date, timedelta
from typing import Any

from app.db_mysql import execute_query
from app.config_mysql import get_pooled_connection
from app.api.pda.shipping_material import get_dict_cursor

from app.api.control_produccion import part_planning as pp

logger = logging.getLogger(__name__)

# Permisos separados: consultar/proponer el renglon S pertenece a Proyeccion;
# crear lotes pertenece a Plan Proyectado.
PLAN_PERMISO = (pp.PP_PERMISO_PAGINA, pp.PP_PERMISO_SECCION, pp.PPY_PERMISO_BOTON)
PROJECTION_PERMISO = (
    pp.PP_PERMISO_PAGINA,
    pp.PP_PERMISO_SECCION,
    pp.PROY_PERMISO_BOTON,
)
_TOKEN_TTL = 900  # 15 min: la confirmacion caduca

TOOL_NAMES = frozenset({
    "plan_estado_faltantes",
    "plan_importar_preparar",
    "plan_importar_ejecutar",
    "plan_generar_preparar",
    "plan_generar_ejecutar",
    "plan_part_sincronizar_preparar",
    "plan_part_sincronizar_ejecutar",
    "plan_propuesta_preparar",
    "plan_propuesta_aplicar",
})


# ============================================================
# Token de confirmacion (dos pasos)
# ============================================================

def _secret() -> bytes:
    key = os.getenv("AI_SAFETY_HMAC_KEY") or os.getenv("SECRET_KEY") or "mes-plan-fallback"
    return key.encode("utf-8")


def _make_token(action: str, payload: dict[str, Any]) -> str:
    body = {"a": action, "p": payload, "t": int(time.time())}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    sig = hmac.new(_secret(), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return raw + "||" + sig


def _read_token(token: str, expected_action: str) -> dict[str, Any]:
    try:
        raw, sig = str(token).rsplit("||", 1)
    except ValueError:
        raise ValueError("Token de confirmacion invalido")
    good = hmac.new(_secret(), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, good):
        raise ValueError("Token de confirmacion alterado o invalido")
    body = json.loads(raw)
    if body.get("a") != expected_action:
        raise ValueError("El token no corresponde a esta accion")
    if int(time.time()) - int(body.get("t", 0)) > _TOKEN_TTL:
        raise ValueError("La confirmacion expiro; vuelve a preparar la accion")
    return body.get("p") or {}


def _parse_fecha(texto: str | None) -> date:
    return pp._ppy_parse_fecha(texto) or date.today()


# ============================================================
# Nucleo reutilizable (misma logica que los endpoints)
# ============================================================

def _importar_plan_e_inventario(file_bytes: bytes, filename: str, usuario: str) -> dict[str, Any]:
    """Importa hoja LG (plan) + hoja Part N (inventario y schedules) en una
    transaccion. Devuelve resumen. Reusa parsers de part_planning."""
    plan, err = pp._parse_lg_workbook(file_bytes, filename)
    if err is not None:
        raise ValueError(err[0]["errors"][0])
    inv, err2 = pp._parse_part10_workbook(file_bytes, filename)
    inv_ok = err2 is None

    ref_lunes = pp._pp_ref_lunes(filename)
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    conn = get_pooled_connection()
    if conn is None:
        raise RuntimeError("No fue posible obtener conexion MySQL.")
    cursor = get_dict_cursor(conn)
    try:
        conn.autocommit(False)
        # --- Plan (hoja LG): upsert por parte+fecha ---
        cursor.execute(
            "INSERT INTO lg_plan_imports (original_filename, sheet_name, plan_year, "
            "date_from, date_to, parts_count, dates_count, records_count, "
            "zero_records_count, warning_count, import_mode, file_sha256, imported_by, status) "
            "VALUES (%s, 'LG', %s, %s, %s, %s, %s, %s, 0, 0, 'ai_upsert', %s, %s, 'COMPLETADO')",
            (filename[:255], plan["plan_year"], plan["date_from"], plan["date_to"],
             plan["parts_count"], plan["dates_count"], plan["records_count"],
             file_hash, usuario),
        )
        import_id = cursor.lastrowid
        filas_plan = [
            (p, f, q, import_id)
            for (p, f), q in plan["records"].items()
        ]
        for i in range(0, len(filas_plan), pp.PP_BATCH_SIZE):
            cursor.executemany(
                "INSERT INTO lg_plan_daily (part_no, plan_date, plan_qty, import_id) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE plan_qty=VALUES(plan_qty), import_id=VALUES(import_id)",
                filas_plan[i : i + pp.PP_BATCH_SIZE],
            )

        # --- Inventario + schedules (hoja Part N), si vino ---
        parts_inv = 0
        sched_n = 0
        if inv_ok:
            sql_inv = (
                "INSERT INTO lg_part_inventory "
                "(part_no, board, line, lgemm, isemm, svc, dif, pendiente, rework, "
                " smt, imd, ref_date, import_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE board=VALUES(board), line=VALUES(line), "
                "lgemm=VALUES(lgemm), isemm=VALUES(isemm), svc=VALUES(svc), "
                "dif=VALUES(dif), pendiente=VALUES(pendiente), rework=VALUES(rework), "
                "smt=VALUES(smt), imd=VALUES(imd), ref_date=VALUES(ref_date), "
                "import_id=VALUES(import_id)"
            )
            datos_inv = [
                (p, d["board"], d["line"], d["lgemm"], d["isemm"], d["svc"],
                 d["dif"], d["pendiente"], d["rework"], d["smt"], d["imd"],
                 ref_lunes, import_id)
                for p, d in inv["inventory"].items()
            ]
            for i in range(0, len(datos_inv), pp.PP_BATCH_SIZE):
                cursor.executemany(sql_inv, datos_inv[i : i + pp.PP_BATCH_SIZE])
            parts_inv = len(datos_inv)

            datos_sched = [(p, f, int(q), usuario) for (p, f), q in inv["schedules"].items()]
            for i in range(0, len(datos_sched), pp.PP_BATCH_SIZE):
                cursor.executemany(
                    "INSERT INTO lg_schedule_daily (part_no, sched_date, sched_qty, updated_by) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE sched_qty=VALUES(sched_qty), updated_by=VALUES(updated_by)",
                    datos_sched[i : i + pp.PP_BATCH_SIZE],
                )
            sched_n = len(datos_sched)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.autocommit(True)
        conn.close()

    return {
        "import_id": import_id,
        "plan_partes": plan["parts_count"],
        "plan_fechas": plan["dates_count"],
        "plan_registros": plan["records_count"],
        "rango": f"{plan['date_from'].isoformat()} a {plan['date_to'].isoformat()}",
        "inventario_hoja": inv.get("sheet_name") if inv_ok else None,
        "inventario_partes": parts_inv,
        "schedules": sched_n,
        "inventario_encontrado": inv_ok,
    }


def _faltantes(fecha: date) -> dict[str, Any]:
    """Resumen de faltantes accionables (hoy en adelante) a la fecha."""
    # El anticipo se cuenta en dias de produccion y D1 llega mas lejos que main.
    proy = pp._ppy_proyeccion_rango(
        fecha, pp._ppy_sumar_dias_produccion(fecha, pp.PPY_ANTICIPACION_MAX)
    )
    hoy = date.today()
    excluidas = pp._ppy_partes_excluidas()
    partes = []
    for p, d in proy.items():
        if not d["proj"] or p.upper() in excluidas:
            continue  # las que no producimos aqui no son faltante nuestro
        futuros = {f: v for f, v in d["proj"].items() if f >= hoy}
        if not futuros:
            continue
        min_i = min(futuros.values())
        if min_i < 0:
            partes.append({"part_no": p, "faltante": -min_i,
                           "primera_falta": min(f for f, v in futuros.items() if v < 0).isoformat()})
    partes.sort(key=lambda x: -x["faltante"])
    return {
        "fecha": fecha.isoformat(),
        "partes_con_faltante": len(partes),
        "piezas_faltantes": sum(x["faltante"] for x in partes),
        "top": partes[:15],
    }


# ============================================================
# Definiciones de tools (schema OpenAI)
# ============================================================

def _has_plan(username: str) -> bool:
    from app.api.shared.permisos import puede_boton
    return bool(username and puede_boton(username, *PLAN_PERMISO))


def _has_projection(username: str) -> bool:
    from app.api.shared.permisos import puede_boton
    return bool(username and puede_boton(username, *PROJECTION_PERMISO))


def _has(username: str) -> bool:
    """Compatibilidad: el asistente muestra funciones de plan con cualquiera de ambos permisos."""
    return _has_plan(username) or _has_projection(username)


def tool_schemas(username: str) -> list[dict[str, Any]]:
    """Tools visibles al modelo; las de ejecutar quedan solo del lado servidor."""
    tools: list[dict[str, Any]] = []
    if _has_plan(username):
        tools.extend(
            [
                {
                    "type": "function",
                    "name": "plan_estado_faltantes",
                    "description": (
                        "SOLO LECTURA. Resume faltantes para cubrir el plan LG a una fecha."
                    ),
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "fecha": {
                                "type": ["string", "null"],
                                "description": "Fecha AAAA-MM-DD; null significa hoy",
                            },
                        },
                        "required": ["fecha"],
                        "additionalProperties": False,
                    },
                },
                {
                    "type": "function",
                    "name": "plan_importar_preparar",
                    "description": (
                        "Analiza el ultimo Excel de plan adjunto y prepara su importacion. "
                        "No modifica el MES; muestra el resumen y pide confirmacion posterior."
                    ),
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                },
                {
                    "type": "function",
                    "name": "plan_generar_preparar",
                    "description": (
                        "Prepara la creacion de lotes del dia desde faltantes o schedule. "
                        "No escribe; muestra el resumen y pide confirmacion posterior."
                    ),
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "fecha": {"type": ["string", "null"]},
                            "modo": {"type": "string", "enum": ["faltantes", "schedule"]},
                        },
                        "required": ["fecha", "modo"],
                        "additionalProperties": False,
                    },
                },
            ]
        )
    if _has_projection(username):
        tools.append(
            {
                "type": "function",
                "name": "plan_part_sincronizar_preparar",
                "description": (
                    "Analiza el ultimo Excel adjunto y prepara la sincronizacion del "
                    "renglon S de su hoja Part N usando exactamente la operacion del "
                    "boton Sincronizar Part. Reemplaza schedule por parte y rango; no "
                    "modifica inventario ni plan LG. Requiere confirmacion posterior."
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "alcance": {
                            "type": "string",
                            "enum": ["main", "todos"],
                            "description": (
                                "main sincroniza solo M1-M4; todos reproduce el "
                                "alcance completo del boton"
                            ),
                        },
                    },
                    "required": ["alcance"],
                    "additionalProperties": False,
                },
            }
        )
        tools.append(
            {
                "type": "function",
                "name": "plan_propuesta_preparar",
                "description": (
                    "Genera una propuesta deterministica y revisable de schedule usando plan LG, "
                    "inventario, RAW (CT/UPH/empaque), lineas permitidas y capacidad. No modifica "
                    "schedule ni lotes. Usala cuando pidan 'haz una propuesta del plan'."
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fecha_inicio": {
                            "type": ["string", "null"],
                            "description": "AAAA-MM-DD; null significa hoy",
                        },
                        "fecha_fin": {
                            "type": ["string", "null"],
                            "description": "AAAA-MM-DD; null significa seis dias despues",
                        },
                        "objetivo": {
                            "type": ["string", "null"],
                            "description": (
                                "Nota de prioridad/restriccion para registrar y mostrar al planeador; "
                                "la V1 no altera reglas duras con texto libre"
                            ),
                        },
                        "proceso_actual": {
                            "type": ["string", "null"],
                            "description": (
                                "Obligatorio cuando el rango incluye hoy: indica en que "
                                "proceso/lote van las lineas antes de replanear. Para fechas "
                                "futuras debe ser null."
                            ),
                        },
                    },
                    "required": [
                        "fecha_inicio", "fecha_fin", "objetivo", "proceso_actual"
                    ],
                    "additionalProperties": False,
                },
            }
        )
    return tools


# ============================================================
# Ejecutores (los llama execute_tool del asistente)
# ============================================================

def execute(name: str, arguments: dict[str, Any], *, username: str, file_lookup) -> dict[str, Any]:
    """Ejecuta una tool del plan. `file_lookup(file_ref)` devuelve (bytes, filename)
    o (None, None). Retorna dict serializable para el LLM."""
    projection_tools = {
        "plan_part_sincronizar_preparar",
        "plan_part_sincronizar_ejecutar",
        "plan_propuesta_preparar",
        "plan_propuesta_aplicar",
    }
    if name in projection_tools:
        if not _has_projection(username):
            raise PermissionError("No tienes permiso de Proyeccion para esta accion")
    elif not _has_plan(username):
        raise PermissionError("No tienes permiso para las acciones del Plan de produccion")

    if name == "plan_estado_faltantes":
        return _faltantes(_parse_fecha(arguments.get("fecha")))

    if name == "plan_part_sincronizar_preparar":
        file_bytes, filename = file_lookup(arguments.get("file_ref"))
        if not file_bytes:
            raise ValueError(
                "No encuentro un Excel subido. Pide al usuario que adjunte el "
                "archivo que contiene la hoja Part N."
            )
        resumen = pp._pp_sincronizar_schedule_excel(
            file_bytes,
            filename or "plan.xlsm",
            username,
            aplicar=False,
            alcance=arguments.get("alcance") or "todos",
        )
        token = _make_token(
            "sincronizar_part_schedule",
            {
                "sha": hashlib.sha256(file_bytes).hexdigest(),
                "alcance": arguments.get("alcance") or "todos",
            },
        )
        return {
            "resumen": resumen,
            "confirm_token": token,
            "instruccion": (
                "Explica que solo se sincronizara el renglon S de Part N, muestra "
                "hoja, alcance, partes, schedules, exclusiones por alcance y rango, "
                "aclara que plan LG e inventario no cambian, y pide confirmacion en "
                "un mensaje posterior."
            ),
        }

    if name == "plan_part_sincronizar_ejecutar":
        payload = _read_token(
            arguments.get("confirm_token"), "sincronizar_part_schedule"
        )
        file_bytes, filename = file_lookup(None)
        if not file_bytes:
            raise ValueError("El archivo ya no esta disponible; vuelve a adjuntarlo.")
        if payload.get("sha") != hashlib.sha256(file_bytes).hexdigest():
            raise ValueError(
                "El archivo cambio desde la vista previa; vuelve a preparar la sincronizacion."
            )
        return pp._pp_sincronizar_schedule_excel(
            file_bytes,
            filename or "plan.xlsm",
            username,
            aplicar=True,
            alcance=payload.get("alcance") or "todos",
        )

    if name == "plan_propuesta_preparar":
        hoy = date.today()
        fecha_inicio = _parse_fecha(arguments.get("fecha_inicio"))
        fecha_fin = pp._ppy_parse_fecha(arguments.get("fecha_fin")) or (
            fecha_inicio + timedelta(days=6)
        )
        if fecha_fin < fecha_inicio:
            fecha_inicio, fecha_fin = fecha_fin, fecha_inicio
        fecha_inicio = max(fecha_inicio, hoy)
        if fecha_fin < fecha_inicio:
            raise ValueError("El rango solicitado ya paso")
        if (fecha_fin - fecha_inicio).days > pp.PP_MAX_RANGO_DIAS:
            raise ValueError(f"Rango maximo {pp.PP_MAX_RANGO_DIAS} dias")
        proceso_actual = str(arguments.get("proceso_actual") or "").strip()
        if fecha_inicio <= hoy <= fecha_fin and not proceso_actual:
            raise ValueError(
                "Antes de replanear hoy, pregunta en que proceso o lote van "
                "las lineas y envia la respuesta en proceso_actual."
            )
        objetivo = str(arguments.get("objetivo") or "").strip()
        if proceso_actual:
            contexto = "Proceso actual reportado por Planning: " + proceso_actual
            objetivo = (objetivo + "\n" + contexto).strip()
        propuesta = pp._ppy_crear_propuesta(
            fecha_inicio,
            fecha_fin,
            username,
            source="AI",
            objective=objetivo or None,
        )
        pp._ppy_mark_proposal_pending(propuesta["proposal_id"], username)
        token = _make_token(
            "aplicar_propuesta",
            {
                "proposal_id": propuesta["proposal_id"],
                "version": propuesta["version"],
                "username": username,
            },
        )
        muestra = [
            {
                "fecha": item["fecha"],
                "linea": item["linea"],
                "turno": item["turno"],
                "numero_parte": item["numero_parte"],
                "cantidad": item["cantidad"],
                "ct": item["ct"],
                "uph": item["uph"],
                "horas_requeridas": item["horas_requeridas"],
                "inventario_antes": item["inventario_antes"],
                "inventario_despues": item["inventario_despues"],
                "fecha_shortage": item["fecha_shortage"],
                "excepciones": item["excepciones"],
            }
            for item in propuesta["proposals"][:12]
        ]
        return {
            "proposal_id": propuesta["proposal_id"],
            "version": propuesta["version"],
            "engine_version": propuesta["engine_version"],
            "date_from": propuesta["date_from"],
            "date_to": propuesta["date_to"],
            "items": len(propuesta["proposals"]),
            "partes": propuesta["partes"],
            "total_qty": propuesta["total_qty"],
            "line_summary": propuesta["line_summary"],
            "omitted_count": propuesta["omitidas_count"],
            "exceptions": propuesta["exceptions"][:20],
            "sample": muestra,
            "proceso_actual": proceso_actual or None,
            "confirm_token": token,
            "instruccion": (
                "Explica que es una propuesta calculada por el motor, resume capacidad y "
                "excepciones, y pide confirmacion en un mensaje posterior para aplicarla."
            ),
        }

    if name == "plan_propuesta_aplicar":
        payload = _read_token(arguments.get("confirm_token"), "aplicar_propuesta")
        if payload.get("username") != username:
            raise PermissionError("La confirmacion pertenece a otro usuario")
        return pp._ppy_aplicar_propuesta(
            str(payload.get("proposal_id") or ""),
            username,
            version=payload.get("version") or 1,
            items=None,
        )

    if name == "plan_importar_preparar":
        file_bytes, filename = file_lookup(arguments.get("file_ref"))
        if not file_bytes:
            raise ValueError("No encuentro un Excel subido. Pide al usuario que adjunte el archivo del plan.")
        plan, err = pp._parse_lg_workbook(file_bytes, filename or "plan.xlsm")
        if err is not None:
            raise ValueError(err[0]["errors"][0])
        inv, err2 = pp._parse_part10_workbook(file_bytes, filename or "plan.xlsm")
        resumen = {
            "archivo": filename,
            "plan_partes": plan["parts_count"],
            "plan_fechas": plan["dates_count"],
            "rango": f"{plan['date_from'].isoformat()} a {plan['date_to'].isoformat()}",
            "inventario_encontrado": err2 is None,
            "inventario_hoja": inv.get("sheet_name") if err2 is None else None,
            "inventario_partes": len(inv["inventory"]) if err2 is None else 0,
        }
        # El token liga el hash del archivo: confirmar importa exactamente lo previsualizado
        token = _make_token("importar", {"sha": hashlib.sha256(file_bytes).hexdigest()})
        instruccion = "Muestra el resumen y pide al usuario confirmar la importacion."
        # Importar un archivo mas viejo que el ultimo revierte en silencio lo
        # que el mas nuevo actualizo (el upsert por parte+fecha gana el ultimo).
        viejo = pp._pp_import_mas_reciente(
            pp._pp_fecha_archivo(filename), plan["date_from"], plan["date_to"])
        if viejo:
            resumen["aviso_retroceso"] = (
                f"Este archivo es del {pp._pp_fecha_archivo(filename)} pero ya se "
                f"importo uno mas nuevo ({viejo['archivo']}, del "
                f"{viejo['fecha_archivo']}). Confirmar REVIERTE el plan de las "
                f"fechas que se solapan a la version vieja."
            )
            instruccion += (" ADVIERTE del retroceso: ya se importo un archivo mas "
                            "nuevo y confirmar pisaria ese plan con datos viejos. "
                            "Pide confirmacion explicita.")
        if err2 is not None:
            # El Cal diario solo trae el plan de LG; el inventario vive en la
            # hoja Part N del xlsm semanal. Importar el Cal actualiza la demanda
            # y deja el inventario como este, que es lo correcto: la foto es del
            # lunes. Hay que decirlo para que nadie asuma que se actualizo.
            resumen["nota_inventario"] = (
                "Este archivo no trae hoja de inventario (Part N): solo se "
                "actualiza el plan de LG. El inventario sigue siendo el de la "
                "ultima importacion del xlsm semanal."
            )
            instruccion += (" Avisa que el inventario NO se actualiza con este "
                            "archivo y que se usara el ya cargado.")
        return {"resumen": resumen, "confirm_token": token,
                "instruccion": instruccion}

    if name == "plan_importar_ejecutar":
        payload = _read_token(arguments.get("confirm_token"), "importar")
        file_bytes, filename = file_lookup(None)  # ultimo Excel subido
        if not file_bytes:
            raise ValueError("El archivo ya no esta disponible; vuelve a adjuntarlo.")
        if payload.get("sha") != hashlib.sha256(file_bytes).hexdigest():
            raise ValueError("El archivo cambio desde la vista previa; vuelve a preparar la importacion.")
        return _importar_plan_e_inventario(file_bytes, filename or "plan.xlsm", username)

    if name == "plan_generar_preparar":
        fecha = _parse_fecha(arguments.get("fecha"))
        modo = (arguments.get("modo") or "faltantes").strip().lower()
        if modo not in ("faltantes", "schedule"):
            raise ValueError("modo debe ser 'faltantes' o 'schedule'")
        if modo == "schedule":
            n = execute_query(
                "SELECT COUNT(*) AS c FROM lg_schedule_daily WHERE sched_date=%s AND sched_qty>0",
                (fecha,), fetch="one")
            cuantos = int((n or {}).get("c") or 0)
            detalle = f"{cuantos} lotes (uno por cada schedule del dia, cantidad exacta)"
        else:
            f = _faltantes(fecha)
            cuantos = f["partes_con_faltante"]
            detalle = f"{cuantos} lotes de faltantes (+10%, caja cerrada), {f['piezas_faltantes']} pzs"
        token = _make_token("generar", {"fecha": fecha.isoformat(), "modo": modo})
        return {
            "fecha": fecha.isoformat(), "modo": modo, "lotes_estimados": cuantos,
            "detalle": detalle, "lineas_activas": pp._ppy_config_lineas(),
            "confirm_token": token,
            "instruccion": "Muestra el detalle y pide confirmar antes de generar.",
        }

    if name == "plan_generar_ejecutar":
        payload = _read_token(arguments.get("confirm_token"), "generar")
        fecha = _parse_fecha(payload.get("fecha"))
        modo = payload.get("modo") or "faltantes"
        acomodar = arguments.get("acomodar")
        acomodar = True if acomodar is None else bool(acomodar)
        return _generar_y_acomodar(fecha, modo, acomodar, username)

    raise ValueError(f"Tool del plan no reconocida: {name}")


def _generar_y_acomodar(fecha: date, modo: str, acomodar: bool, username: str) -> dict[str, Any]:
    """Genera lotes (faltantes/schedule) y opcionalmente acomoda con IA.

    Reutiliza los endpoints internos via test_request_context para no duplicar
    la logica transaccional ni la de acomodo IA (ya probada)."""
    if modo == "faltantes":
        # /generate hace el ciclo completo: elige linea (manda assy_line),
        # reparte las lineas en los bloques de 9 h y recorta lo que no cabe.
        # NO usar /generate-faltantes: crea los lotes sin linea y delega en el
        # acomodo, que ignora assy_line (mandaba todo a D1, la primera
        # alfabetica) y no recorta cantidades (dejaba D1 en 11.4 h).
        res = _call_endpoint("/api/plan-proyectado/generate",
                             {"fecha": fecha.isoformat()}, username)
        return {
            "generados": res.get("generados", 0),
            "modo": modo,
            "fecha": fecha.isoformat(),
            "no_incluidos": res.get("no_incluidos") or [],
            "lineas": [
                {"linea": l["linea"], "horas": l["horas"], "excede": l["excede"]}
                for l in (res.get("lineas") or [])
            ],
        }

    # modo schedule: el renglon S ya trae la cantidad exacta, pero los
    # registros legacy pueden venir sin linea; ahi si aplica el acomodo.
    ruta = "/api/plan-proyectado/generate-schedule"
    res_gen = _call_endpoint(ruta, {"fecha": fecha.isoformat()}, username)
    salida = {"generados": res_gen.get("generados", 0), "modo": modo,
              "fecha": fecha.isoformat()}
    if acomodar and res_gen.get("generados"):
        res_ac = _call_endpoint("/api/plan-proyectado/acomodar-ia",
                                {"fecha": fecha.isoformat()}, username)
        salida["acomodo_metodo"] = res_ac.get("metodo")
        salida["asignados"] = res_ac.get("asignados")
        salida["sin_asignar"] = res_ac.get("sin_asignar")
        salida["lineas"] = [
            {"linea": l["linea"], "horas": l["horas"], "excede": l["excede"]}
            for l in (res_ac.get("lineas") or [])
        ]
    return salida


def _call_endpoint(ruta: str, body: dict[str, Any], username: str) -> dict[str, Any]:
    """Invoca un endpoint interno del plan con la sesion del usuario actual."""
    from flask import current_app

    client = current_app.test_client()
    with client.session_transaction() as sess:
        sess["usuario"] = username
    resp = client.post(ruta, json=body)
    data = resp.get_json() or {}
    if not data.get("success"):
        raise RuntimeError(data.get("error") or f"Fallo {ruta}")
    return data
