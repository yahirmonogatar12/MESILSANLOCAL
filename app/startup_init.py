"""
Inicializaciones de base de datos y workers para arranque del servidor.

Se ejecuta solo cuando MES_SKIP_STARTUP_INIT no esta activo.
Para forzar una sola corrida (despues de un cambio de schema):
    set MES_SKIP_STARTUP_INIT=0
    set MES_FORCE_STARTUP_INIT=1

Patron de imports (2026-05-28): cada DDL / worker se importa DIRECTO desde
su blueprint dueño en `app.api.<seccion>.<modulo>`. Antes este modulo
importaba `from . import routes as _routes` y consumia las funciones via
`_routes.X()`, lo que mantenia a `routes.py` como cuello de botella
gravitacional aunque las funciones ya vivieran en sus blueprints.
"""

import os
import time


def _env_flag(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on", "si")


def should_run_startup_init():
    if _env_flag("MES_FORCE_STARTUP_INIT", False):
        return True
    if _env_flag("MES_SKIP_STARTUP_INIT", False):
        return False
    if _env_flag("MES_USE_RELOADER", False):
        return os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    return True


def run_startup_init():
    """Ejecuta todas las inicializaciones diferidas de la app."""
    if not should_run_startup_init():
        print("[startup-init] Saltando inicializaciones (MES_SKIP_STARTUP_INIT=1)")
        # Workers siguen siendo necesarios aunque las tablas ya existan.
        _start_workers_only()
        return

    t0 = time.time()

    def log(msg):
        print(f"[startup {round(time.time() - t0, 2)}s] {msg}")

    # Importes diferidos para evitar ciclos al cargar routes en paralelo.
    from .db import init_db
    from .auth_system import AuthSystem
    from .api.pda.shipping import init_shipping_tables
    from .api.pda.shipping_material import init_shipping_material_tables
    from .api.control_produccion.cuchillas_corte import crear_tablas_cuchillas_corte
    from .api.shared.snapshot_inventario import crear_tablas_snapshot_inventario
    from .api.control_produccion.plan_smt import crear_tabla_plan_smt_v2
    from .api.control_produccion.plan_smd import (
        crear_tabla_plan_smd,
        crear_tabla_plan_smd_runs,
    )
    from .api.control_resultados.historial_cambios_parametros_ict import (
        crear_indice_history_ict_audit,
        crear_indice_history_ict_ts_nopart,
    )
    from .api.control_produccion.trazabilidad import crear_tabla_trazabilidad
    from .api.control_produccion.metal_mask import init_metal_mask_tables

    log("Iniciando init_db()")
    init_db()
    log("init_db() completado")

    log("Iniciando auth_system.init_database()")
    AuthSystem().init_database()
    log("auth_system.init_database() completado")

    log("Iniciando init_shipping_tables()")
    init_shipping_tables()
    log("init_shipping_tables() completado")

    log("Iniciando init_shipping_material_tables()")
    init_shipping_material_tables()
    log("init_shipping_material_tables() completado")

    log("Iniciando bootstrap de cuchillas de corte")
    crear_tablas_cuchillas_corte()
    log("Bootstrap de cuchillas de corte completado")

    log("Iniciando bootstrap de snapshot inventario")
    crear_tablas_snapshot_inventario()
    log("Bootstrap de snapshot inventario completado")

    log("Iniciando crear_tabla_plan_smt_v2()")
    crear_tabla_plan_smt_v2()
    log("crear_tabla_plan_smt_v2() completado")

    log("Iniciando crear_tabla_plan_smd()")
    crear_tabla_plan_smd()
    log("crear_tabla_plan_smd() completado")

    log("Asegurando indice idx_history_ict_audit")
    crear_indice_history_ict_audit()
    log("Asegurando indice idx_history_ict_ts_nopart")
    crear_indice_history_ict_ts_nopart()

    log("Iniciando crear_tabla_plan_smd_runs()")
    crear_tabla_plan_smd_runs()
    log("crear_tabla_plan_smd_runs() completado")

    log("Iniciando crear_tabla_trazabilidad()")
    crear_tabla_trazabilidad()
    log("crear_tabla_trazabilidad() completado")

    log("Iniciando init_metal_mask_tables()")
    init_metal_mask_tables()
    log("init_metal_mask_tables() completado")

    _start_workers_only()


def _start_workers_only():
    """Arranca los workers en background. Independiente de init de tablas."""
    try:
        from .api.control_produccion.cuchillas_corte import (
            iniciar_cuchillas_hourly_sync_worker,
        )
        iniciar_cuchillas_hourly_sync_worker()
    except Exception as e:
        print(f"[startup-init] Error iniciando cuchillas worker: {e}")
    try:
        from .api.shared.snapshot_inventario import iniciar_snapshot_inv_worker
        iniciar_snapshot_inv_worker()
    except Exception as e:
        print(f"[startup-init] Error iniciando snapshot worker: {e}")
