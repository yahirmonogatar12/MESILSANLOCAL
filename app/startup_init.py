"""
Inicializaciones de base de datos y workers para arranque del servidor.

Se ejecuta solo cuando MES_SKIP_STARTUP_INIT no esta activo.
Para forzar una sola corrida (despues de un cambio de schema):
    set MES_SKIP_STARTUP_INIT=0
    set MES_FORCE_STARTUP_INIT=1
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
        # Workers siguen siendo necesarios aunque las tablas ya existan
        _start_workers_only()
        return

    t0 = time.time()

    def log(msg):
        print(f"[startup {round(time.time() - t0, 2)}s] {msg}")

    # Importes diferidos para evitar ciclos al importar app.routes
    from . import routes as _routes
    from .db import init_db
    from .auth_system import AuthSystem
    from .shipping_api import init_shipping_tables
    from .shipping_material_api import init_shipping_material_tables

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
    _routes.crear_tablas_cuchillas_corte()
    log("Bootstrap de cuchillas de corte completado")

    log("Iniciando bootstrap de snapshot inventario")
    _routes.crear_tablas_snapshot_inventario()
    log("Bootstrap de snapshot inventario completado")

    log("Iniciando crear_tabla_plan_smt_v2()")
    _routes.crear_tabla_plan_smt_v2()
    log("crear_tabla_plan_smt_v2() completado")

    log("Iniciando crear_tabla_plan_smd()")
    _routes.crear_tabla_plan_smd()
    log("crear_tabla_plan_smd() completado")

    log("Asegurando indice idx_history_ict_audit")
    _routes.crear_indice_history_ict_audit()
    log("Asegurando indice idx_history_ict_ts_nopart")
    _routes.crear_indice_history_ict_ts_nopart()

    log("Iniciando crear_tabla_plan_smd_runs()")
    _routes.crear_tabla_plan_smd_runs()
    log("crear_tabla_plan_smd_runs() completado")

    log("Iniciando crear_tabla_trazabilidad()")
    _routes.crear_tabla_trazabilidad()
    log("crear_tabla_trazabilidad() completado")

    log("Iniciando init_metal_mask_tables()")
    _routes.init_metal_mask_tables()
    log("init_metal_mask_tables() completado")

    _start_workers_only()


def _start_workers_only():
    """Arranca los workers en background. Independiente de init de tablas."""
    from . import routes as _routes
    try:
        _routes.iniciar_cuchillas_hourly_sync_worker()
    except Exception as e:
        print(f"[startup-init] Error iniciando cuchillas worker: {e}")
    try:
        _routes.iniciar_snapshot_inv_worker()
    except Exception as e:
        print(f"[startup-init] Error iniciando snapshot worker: {e}")
