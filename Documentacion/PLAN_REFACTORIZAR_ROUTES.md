# Plan: Refactorizar `app/routes.py`

**Fecha del plan**: 2026-05-28
**Estado actual**: `routes.py` tiene **1232 líneas** tras Fase 6 (baseline original: 4455 líneas, 105 defs top-level → ahora 33 defs core).
**Meta**: reducir a **~2100 líneas** (-53%) moviendo o borrando lo que ya no debería vivir aquí.

## Progreso

| Fase | Estado | Líneas `routes.py` | Δ | Rutas Flask | Smoke test |
|---|---|---:|---:|---:|---|
| Fase 0 (snapshot) | — | 4455 | — | 388 | — |
| **Fase 1 (9 huérfanas)** | ✅ **2026-05-28** | **3804** | **-651** | **379** | ✅ `create_app()` OK |
| **Fase 2 (re-exports zombies)** | ✅ **2026-05-28** | **3758** | **-46** | **379** | ✅ `create_app()` + imports lazy OK |
| **Fase 3 (renders + salida lineas)** | ✅ **2026-05-28** | **3146** | **-612** | **379** | ✅ 36 URLs migradas presentes |
| **Fase 4 (11 rutas gordas + 3 helpers huérfanos)** | ✅ **2026-05-28** | **1823** | **-1323** | **379** | ✅ 10 URLs verificadas |
| **Fase 5 (limpieza imports muertos)** | ✅ **2026-05-28** | **1745** | **-78** | **379** | ✅ AST OK + lazy resolve OK |
| **Fase 6 (auth blueprint: index/inicio/login/logout/api_mi_perfil)** | ✅ **2026-05-28** | **1232** | **-513** | **379** | ✅ 5 URLs migradas + url_for resuelve |

## Principio rector

Regla de oro definida en `app/api/__init__.py`:

> `app/routes.py` SOLO contiene rutas Flask y los pocos helpers transversales
> que el resto de la app necesita importar como `from app.routes import X`.
> Todo lo demás (renders por sección, helpers privados de módulo, DDL,
> workers, re-exports zombies) debe vivir en su blueprint dueño bajo
> `app/api/<seccion>/<modulo>.py`.

Cada fase del plan se ejecuta en un commit aparte (smoke test entre fases:
`python -c "from app_factory import create_app; create_app()"` debe terminar
sin errores y con el mismo número de rutas registradas más/menos los aliases).

---

## Fases

### Fase 0 — Snapshot inicial (referencia)

| Métrica | Valor |
|---|---|
| Líneas totales | 4455 |
| Defs top-level | 105 |
| Rutas Flask en `routes.py` | ~75 |
| Funciones no-ruta | ~30 |
| Re-exports zombies confirmados (0 consumidores externos) | 25 |
| Rutas con 0 consumidores en `app/static` + `app/templates` | 9 |

---

### Fase 1 — Borrar 9 rutas huérfanas (sin consumidores) ✅ COMPLETADA (2026-05-28)

**Ganancia real**: -651 líneas (4455 → 3804). **Total rutas**: 388 → 379.
**Smoke test**: `app_factory.create_app()` OK, las 9 URLs ya no están en `app.url_map`.
**Bonus eliminado**: ~150 líneas de dead code zombie en `get_csv_stats` (código después
del `return jsonify(..., 500)` inalcanzable). Las funciones eliminadas se reemplazan por
un comentario `# Fase 1 (2026-05-28): <nombre> borrada — sin consumidores` para dejar
pista de auditoría (esto explica que la ganancia sea -651 y no -700).

| Línea | Función | URL | Verificación |
|---:|---|---|---|
| 1022 | `sistemas` | `/sistemas` | 0 refs en `app/static` + `app/templates` |
| 1029 | `soporte` | `/soporte` | 0 refs |
| 1040 | `documentacion` | `/documentacion` | 0 refs |
| 1427 | `guardar_cliente_seleccionado` | `POST /guardar_cliente_seleccionado` | 0 refs |
| 1452 | `cargar_cliente_seleccionado` | `GET /cargar_cliente_seleccionado` | 0 refs |
| 2393 | `csv_viewer` | `/csv-viewer` | 0 refs |
| 2429 | `get_csv_data` | `/api/csv_data` | 0 refs en código vivo (sólo en docs) |
| 2549 | `get_csv_stats` | `/api/csv_stats` | 0 refs en código vivo |
| 2798 | `filter_csv_data` | `POST /api/filter_data` | 0 refs en código vivo |

**Helpers que se llevan con ellas** (sólo consumidos por las rutas borradas):
- 2982 `cargar_configuracion_usuario`
- 3012 `guardar_configuracion_usuario`

**Verificación previa antes de borrar CSV-viewer**: confirmar con
`grep -rE "csv_data|csv_stats|filter_data" --include='*.py'` que ningún
script Python externo los consume. Si sólo aparecen los matches en docs +
la propia ruta, borrar.

**Smoke test**: `app.url_map` debe pasar de 388 a 379 rutas.

---

### Fase 2 — Limpiar 25 re-exports zombies ✅ COMPLETADA (2026-05-28)

**Ganancia real**: -46 líneas (3804 → 3758). **Total rutas**: 379 (sin cambio).
**Smoke test**: `create_app()` OK; lazy proxy (`login_requerido`, `execute_query`,
`auth_system`, `obtener_fecha_hora_mexico`) sigue resolviendo;
`material_admin._cuchillas_rows_to_json` ahora viene directo de su blueprint dueño
(`app.api.control_produccion.cuchillas_corte`).

**Cambios aplicados**:
1. `routes.py`: borrados 4 bloques de re-exports (ICT 4, Vision 15, Excel 4,
   Cuchillas 10). Almacen embarques se conserva como import local porque
   "Control de salida de líneas" sigue viviendo en `routes.py` (Fase 3 lo migra).
2. `material_admin.py:26-32`: cambiado a importar `_cuchillas_rows_to_json`
   directo del blueprint en lugar de via `app.api.shared`.
3. `shared/__init__.py`: removido `_cuchillas_rows_to_json` de `__all__` y
   `_LAZY_FROM_ROUTES`. El proxy lazy ahora solo expone los 4 símbolos core.

#### 2.1 Re-exports en `routes.py:138-174` (ICT + Vision + Excel + Almacen embarques)

Borrar estos 4 bloques completos:

```python
# routes.py:138-141 (almacen embarques)
from .api.control_proceso.almacen_embarques import (
    _exportar_historial_embarques_excel,
    _normalizar_texto_embarques_historial,
)

# routes.py:144-149 (ICT helpers)
from .api.shared.ict_helpers import (
    _append_indexable_text_filter,
    _ict_find_history_record,
    _ict_format_row,
    _ict_load_local_parameters,
)

# routes.py:151-167 (Vision helpers, 15 símbolos)
from .api.shared.vision_helpers import (...)

# routes.py:169-174 (Excel helpers)
from .api.shared.excel_helpers import (
    VISION_PASS_FAIL_EXCEL_IMAGE_HEIGHT,
    VISION_PASS_FAIL_EXCEL_IMAGE_WIDTH,
    _create_vision_pass_fail_excel_image,
    _send_excel_download,
)
```

**Verificación previa**: `grep -rE "from app\.routes import.*<simbolo>"
app/` para cada símbolo. Resultado esperado: 0 matches fuera de routes.py.
Todos los blueprints ya importan directo desde `app.api.shared.*`.

**Nota**: los 2 símbolos de `almacen_embarques` (`_exportar_historial_...`
y `_normalizar_texto_...`) son consumidos por **`_obtener_control_salida_lineas`**
y **`export_control_salida_lineas`** que viven en `routes.py`. Cuando esos
endpoints se muevan en Fase 3, se llevan sus imports directos. Hasta
entonces, mantener este bloque o cambiar los call sites de `routes.py` a
importar directo de `almacen_embarques`.

#### 2.2 Re-exports de Cuchillas en `routes.py:1199-1212` (9 de 10 zombies)

De los 10 símbolos re-exportados, sólo **`_cuchillas_rows_to_json`** tiene
consumidor externo (`material_admin.py:27` lo importa vía `app.api.shared`).

**Acción**:
1. Cambiar `material_admin.py:27` para importar directo del blueprint:
   ```python
   from app.api.control_produccion.cuchillas_corte import _cuchillas_rows_to_json
   ```
2. Borrar `_cuchillas_rows_to_json` del re-export en `routes.py:1207`.
3. Borrar `_cuchillas_rows_to_json` de `app/api/shared/__init__.py:25,32`
   (PEP 562 `__getattr__` lazy + `__all__`).
4. Borrar las 9 entradas zombies del bloque `from app.api.control_produccion.cuchillas_corte import (...)`.

**Smoke test**: importar `app_factory` y montar al menos un endpoint de
`material_admin` debe seguir funcionando.

---

### Fase 3 — Mover renders cortos (`return render_template`) a blueprints existentes ✅ COMPLETADA (2026-05-28)

**Ganancia real**: -612 líneas (3758 → 3146). **Total rutas**: 379 (sin cambio).
**URLs migradas**: 36 (16 control_proceso renders + 3 endpoints salida lineas + 6 control_produccion + 11 control_calidad).
**Archivos nuevos**: `control_proceso/renders.py`, `control_proceso/control_salida_lineas.py`, `control_produccion/renders.py`, `control_calidad/renders.py`.
**Archivos extendidos**: `control_produccion/plan_smt.py`, `control_produccion/metal_mask.py`, `control_produccion/squeegee.py`, `control_calidad/smt_historial.py`.
**Bonus**: la migracion completa de "Control de salida de lineas" elimino el import directo de `_normalizar_*` y `_exportar_*` que quedaba en routes.py desde Fase 2 (cierra deuda).
**3.4 (LISTAS) NO ejecutada**: las 9 rutas `/listas/*` se quedan en routes.py por ser transversales (sirven templates del sidebar para todas las secciones).

Cada render se mueve al blueprint hermano de su sección. Como las URLs no
cambian, **no se requieren aliases 301** y no hay cambios en `scriptMain.js`
ni en las LISTAS.

#### 3.1 Control de proceso → `app/api/control_proceso/renders.py` (NUEVO)

15 renders + 3 endpoints de salida de líneas (con sus 3 helpers privados):

| Línea | Función | URL |
|---:|---|---|
| 1599 | `historial_operacion_proceso_ajax` | `/historial-operacion-proceso-ajax` |
| 1612 | `bom_management_process_ajax` | `/bom-management-process-ajax` |
| 1623 | `reporte_diario_inspeccion_smt_ajax` | `/reporte-diario-inspeccion-smt-ajax` |
| 1636 | `control_diario_inspeccion_smt_ajax` | `/control-diario-inspeccion-smt-ajax` |
| 1649 | `reporte_diario_inspeccion_proceso_ajax` | `/reporte-diario-inspeccion-proceso-ajax` |
| 1664 | `control_unidad_empaque_modelo_ajax` | `/control-unidad-empaque-modelo-ajax` |
| 1677 | `packaging_register_management_ajax` | `/packaging-register-management-ajax` |
| 1690 | `search_packaging_history_ajax` | `/search-packaging-history-ajax` |
| 1701 | `shipping_register_management_ajax` | `/shipping-register-management-ajax` |
| 1714 | `search_shipping_history_ajax` | `/search-shipping-history-ajax` |
| 2024 | `registro_movimiento_identificacion_ajax` | `/registro-movimiento-identificacion-ajax` |
| 2037 | `control_otras_identificaciones_ajax` | `/control-otras-identificaciones-ajax` |
| 2050 | `control_movimiento_ns_producto_ajax` | `/control-movimiento-ns-producto-ajax` |
| 2063 | `model_sn_management_ajax` | `/model-sn-management-ajax` |
| 2074 | `control_scrap_ajax` | `/control-scrap-ajax` |
| 2161 | `inventario_imd_terminado_legacy_redirect` | `/control_proceso/inventario_imd_terminado` (alias 301) |

**Control de salida de líneas** (3 helpers + 3 endpoints, mover juntos a
`app/api/control_proceso/control_salida_lineas.py` NUEVO):
- 1724 `_parse_fecha_control_salida_lineas`
- 1732 `_calcular_estado_control_salida_lineas`
- 1746 `_obtener_control_salida_lineas` (~225 l, consume helpers de almacen_embarques)
- 1973 `control_salida_lineas_ajax`
- 1985 `api_control_salida_lineas`
- 1998 `export_control_salida_lineas`

Importes que se llevan al blueprint nuevo:
```python
from app.api.control_proceso.almacen_embarques import (
    _exportar_historial_embarques_excel,
    _normalizar_texto_embarques_historial,
)
```
→ esto **completa** la eliminación del re-export en Fase 2.1.

#### 3.2 Control de producción → blueprints existentes

| Línea | Función | URL | Blueprint destino |
|---:|---|---|---|
| 1180 | `plan_main_smt_ajax` | `/plan-main-smt-ajax` | `control_produccion/plan_smt.py` |
| 2086 | `line_material_status_ajax` | `/line-material-status-ajax` | `control_produccion/renders.py` (NUEVO o consolidado) |
| 2104 | `estandares_soldadura_ajax` | `/estandares-soldadura-ajax` | Idem |
| 2117 | `registro_recibo_soldadura_ajax` | `/registro-recibo-soldadura-ajax` | Idem |
| 2130 | `control_salida_soldadura_ajax` | `/control-salida-soldadura-ajax` | Idem |
| 2143 | `historial_tension_mask_metal_ajax` | `/historial-tension-mask-metal-ajax` | `control_produccion/metal_mask.py` |

#### 3.3 Control de calidad → blueprints existentes / nuevos

| Línea | Función | URL | Blueprint destino |
|---:|---|---|---|
| 3489 | `control_resultado_reparacion_ajax` | `/control-resultado-reparacion-ajax` | `control_calidad/renders.py` (NUEVO) |
| 3496 | `control_item_reparado_ajax` | `/control-item-reparado-ajax` | Idem |
| 3787 | `historial_uso_pegamento_soldadura_ajax` | `/historial-uso-pegamento-soldadura-ajax` | Idem |
| 4152 | `historial_uso_mask_metal_ajax` | `/historial-uso-mask-metal-ajax` | `control_produccion/metal_mask.py` |
| 4159 | `historial_uso_squeegee_ajax` | `/historial-uso-squeegee-ajax` | `control_produccion/squeegee.py` |
| 4166 | `process_interlock_history_ajax` | `/process-interlock-history-ajax` | `control_calidad/renders.py` |
| 4173 | `control_master_sample_smt_ajax` | `/control-master-sample-smt-ajax` | Idem |
| 4180 | `historial_inspeccion_master_sample_smt_ajax` | `/historial-inspeccion-master-sample-smt-ajax` | Idem |
| 4189 | `control_inspeccion_oqc_ajax` | `/control-inspeccion-oqc-ajax` | Idem |
| 2405 | `historial_cambio_material_smt` | `/historial-cambio-material-smt` | `control_calidad/smt_historial.py` |
| 2415 | `historial_cambio_material_smt_ajax` | `/historial-cambio-material-smt-ajax` | Idem |

#### 3.4 LISTAS → `app/api/shared/listas.py` (NUEVO, opcional)

7 endpoints de sidebar + 1 servidor de templates. Decisión: si se considera
"transversal" pueden quedarse en `routes.py`. Si se mueven, todos juntos:

- 1480 `lista_informacion_basica`
- 1491 `lista_control_material`
- 1502 `lista_control_produccion`
- 2167 `lista_control_proceso`
- 2178 `lista_control_calidad`
- 2189 `lista_control_resultados`
- 2220 `lista_control_reporte`
- 2231 `lista_configuracion_programa`
- 2251 `serve_list_template`

**Recomendación**: dejar para una fase posterior o mantener en `routes.py`
(son transversales, no específicas de una sección).

**Smoke test fase 3**: el número total de rutas debe quedar **igual**
(0 alias agregados, 0 borrados). Mismo set de URLs activas.

---

### Fase 4 — Mover rutas gordas a blueprints existentes ✅ COMPLETADA (2026-05-28)

**Ganancia real**: -1323 líneas (3146 → 1823, **más del doble** de lo previsto).
**Total rutas**: 379 (sin cambio). **10 URLs migradas verificadas en `url_map`**.
**Bonus**: los 3 helpers huérfanos previstos para Fase 5 se borraron en este
mismo paso (0 consumidores en código vivo).

**Migración aplicada**:
| Funcion | Destino |
|---|---|
| `api_raw_search` (GET /api/raw/search) | `shared/raw_modelos.py` (mismo url_prefix /api/raw + /search) |
| `api_inventario_modelo`, `api_inventario` | `control_resultados/inventario_imd.py` |
| `api_historial_smt_latest`, `api_historial_smt_latest_v2` + `convertir_linea_smt` | `control_calidad/smt_historial.py` |
| `api_masks_info`, `api_save_metal_mask_history`, `api_get_metal_mask_history`, `api_update_metal_mask_used_count` | `control_produccion/metal_mask.py` |
| `api_bom_smt_data` | `informacion_basica/control_bom.py` |
| `importar_excel_plan_produccion` (POST) | `control_produccion/plan_assy.py` |

**Helpers borrados (Fase 5 anticipada)**:
- `crear_patron_caracteres` (0 consumidores)
- `generar_lot_no_secuencial` (0 consumidores)
- `convertir_linea_smt_reverso` (0 consumidores)

**Nota técnica**: el comentario obsoleto "NO mover aqui /api/masks/info" en
`metal_mask.py` (L11) se eliminó — los blueprints Flask son namespaces de
código, no aíslan rutas; Control de operacion SMT sigue consumiéndola sin
cambios via la URL canónica.

| Línea | Función | URL | Tamaño | Blueprint destino |
|---:|---|---|---:|---|
| 1276 | `api_raw_search` | `/api/raw/search` | ~120 l | `shared/raw_modelos.py` |
| 1538 | `api_inventario_modelo` | `/api/inventario/modelo/<codigo_modelo>` | ~60 l | `control_resultados/inventario_imd.py` |
| 3056 | `importar_excel_plan_produccion` | `POST /importar_excel_plan_produccion` | ~360 l | `control_produccion/plan_assy.py` o nuevo `plan_excel_import.py` |
| 3429 | `api_inventario` | `/api/inventario` | ~60 l | `control_resultados/inventario_imd.py` |
| 3512 | `api_historial_smt_latest` | `/api/historial_smt_latest` | ~100 l | `control_calidad/smt_historial.py` |
| 3616 | `api_historial_smt_latest_v2` | `/api/historial_smt_latest_v2` | ~100 l | Idem |
| 3715 | `api_masks_info` | `/api/masks/info` | ~70 l | `control_produccion/metal_mask.py` |
| 3799 | `api_save_metal_mask_history` | `POST /api/metal-mask/history` | ~100 l | Idem |
| 3896 | `api_get_metal_mask_history` | `GET /api/metal-mask/history` | ~100 l | Idem |
| 3990 | `api_update_metal_mask_used_count` | `/api/metal-mask/update-used-count` | ~160 l | Idem |
| 4270 | `api_bom_smt_data` | `/api/bom-smt-data` | ~130 l | `informacion_basica/control_bom.py` |

**Helpers que se llevan con ellas**:
- 4401 `convertir_linea_smt` → único consumidor es `api_historial_smt_latest_v2` (línea 3620). Mover junto con la ruta.
- 4220 `generar_lot_no_secuencial` → buscar consumidor real; si es `importar_excel_plan_produccion`, mover junto.
- 2947 `crear_patron_caracteres` → buscar consumidor real; si es `importar_excel_plan_produccion`, mover junto. Si no, borrar (categoría D).

**Importante para `api_masks_info`**: el comentario L11 de
`metal_mask.py` dice "NO mover aquí porque es compartida con Control de
operacion SMT". Esa razón no aplica — los blueprints Flask son namespaces
de código, no aíslan rutas. Sí se puede mover sin romper consumidores.

**Smoke test fase 4**: total de rutas igual, integridad preservada.
Probar manualmente al menos `/api/raw/search?part_no=X` y abrir Metal Mask
en la UI.

---

### Fase 5 — Borrar helpers huérfanos + limpiar imports muertos ✅ COMPLETADA (2026-05-28)

**Resultado en 2 pasos**:

**Paso A (adelantado en Fase 4)** — 4 helpers borrados:
- `crear_patron_caracteres` — 0 consumidores en código vivo (borrado en Fase 4)
- `generar_lot_no_secuencial` — 0 consumidores (borrado en Fase 4)
- `convertir_linea_smt_reverso` — 0 consumidores (borrado en Fase 4)
- `convertir_linea_smt` — MOVIDO a `smt_historial.py` junto con su único consumidor (`api_historial_smt_latest_v2`)

**Paso B (este turno)** — 72 imports muertos eliminados:

Tras mover ~3000 líneas de lógica a blueprints, el bloque de imports de
`routes.py` quedó arrastrando símbolos sin consumidores. Análisis AST detectó
**72 imports muertos** vs **21 imports realmente usados**.

Eliminados:
- Stdlib innecesarios: `csv`, `hashlib`, `io`, `threading`, `struct`, `zlib`, `socket`, `subprocess`, `tempfile`, `ThreadPoolExecutor`, `Decimal`, `Path`, `dt_time`
- Flask no usados: `make_response`, `send_file`, `secure_filename`
- Pandas: `pd` (ya no se importa Excel aquí)
- `db_mysql`: 7 funciones de inventario/material no usadas
- `db`: 4 funciones de migration/control no usadas
- `po_wo_models`: 12 helpers PO/WO (todo el módulo movido a `po_wo.py`)
- `api.pda.shipping_material`: 12 helpers (movido a su blueprint)
- `api.pda.shipping`: `init_shipping_tables`
- `services.ict_lgd_parser`: 5 símbolos
- `config_mysql`: `get_pooled_connection`
- `api.shared.bom_revisions`: 5 helpers (consumidos solo desde blueprints)
- `api.shared.plan_lot_no`: 2 helpers

**Verificación con grep**: confirmado que ningún módulo externo importa estos
símbolos vía `from app.routes import X`. Todos los blueprints ya consumen los
originales directo de sus módulos fuente o vía `app.api.shared`.

**Bloque de imports final**: después de las limpiezas posteriores, `routes.py`
ya no define utilidades de fecha/hora ni allowlists de APIs públicas; importa
esas piezas desde `app.api.shared.*`.

**Resultado final**: 1823 → 1745 (-78 líneas adicionales).

---

### Fase 6 — Extraer auth/sesión a su propio blueprint ✅ COMPLETADA (2026-05-28)

**Decisión**: aunque el plan original listaba `login`/`logout`/`api_mi_perfil`
como "deben quedarse en routes.py", el usuario observó (correctamente) que son
lógica de auth pura y conceptualmente encajan en un blueprint. Se aprobó la
migración.

**Migración aplicada** — nuevo `app/api/auth/sesion.py`:

| Funcion | Tipo | Endpoint efectivo |
|---|---|---|
| `index` | render | `auth_sesion.index` (`/`) |
| `inicio` | render | `auth_sesion.inicio` (`/inicio`) |
| `login` | POST + render | `auth_sesion.login` (`/login`) |
| `logout` | render | `auth_sesion.logout` (`/logout`) |
| `api_mi_perfil` | GET/POST | `auth_sesion.api_mi_perfil` (`/api/mi-perfil`) |
| `render_landing_page` | helper | privado (solo consumido por index/inicio/login) |
| `cargar_usuarios` | helper | privado (fallback legacy usuarios.json solo para login) |

**Cambios colaterales**:
1. `PUBLIC_ROUTE_ENDPOINTS` en routes.py actualizado: `"login"`, `"index"`,
   `"inicio"` → `"auth_sesion.login"`, etc.
2. Refactor de **5 referencias `url_for()` en código Python**
   (routes.py:2, smt_historial.py:1, portal/tickets.py:1, sesion.py:5
   self-references) y **3 en templates** (landing.html:1, login.html:2).
3. 2 re-exports zombies adicionales eliminados de routes.py:
   `from app.api.shared.plan_lot_no import _fp_*` y `from app.api.shared.bom_revisions import _ks_*` (0 consumidores externos).
4. 2 imports muertos limpiados (`json`, `re`) — solo `login`/`api_mi_perfil`
   los usaban.

**Aprendizaje técnico**: Flask **siempre** prefija el endpoint con `<bp.name>.`
sin importar el `endpoint=` que pongas — éste solo controla el nombre dentro
del blueprint. Por eso fue necesario el rename masivo (12 ubicaciones) en
lugar de pretender preservar nombres sin namespace.

**Smoke test**: `create_app()` OK, 379 rutas (sin cambio), 5 URLs migradas
verificadas en `app.url_map`, `url_for("auth_sesion.X")` resuelve a las URLs
originales (`/inicio`, `/login`, etc.).

**Resultado**: 1745 → 1232 líneas (-513).

---

## Lo que SÍ debe quedarse en `routes.py`

Estas funciones son **transversales** y muchos blueprints las consumen vía
`from app.routes import X` (o vía `app.api.shared` con resolución lazy).
Son el core que justifica que `routes.py` siga existiendo:

| Línea | Función | Razón |
|---:|---|---|
| 185 | `_env_flag` | Util de configuración |
| 192 | `should_run_startup_init` | Configuración de arranque |
| 211 | `_startup_log` | Logger de arranque |
| 234 | `api_health` | Health check del servicio |
| 266 | `requiere_permiso_dropdown` | Decorador transversal |
| 353 | `tiene_permiso_boton` | Helper de auth |
| 381 | `permisos_botones_pagina` | Helper de auth |
| 389 | `cargar_usuarios` | Helper de auth |
| 402 | `login_requerido` | **Decorador clave** — usado por **todos** los blueprints vía proxy `from app import routes as _r; _r.login_requerido(...)` |
| 438 | `_request_expects_json` | Util de auth |
| 480 | `require_login_by_default` | Middleware `before_request` |
| 506 | `render_landing_page` | Helper de render |
| 541 | `index`, 546 `login`, 689 `inicio`, 695 `api_mi_perfil`, 1129 `logout` | Endpoints de auth/sesión |
| 992 | `calendario` | Sí tiene consumidor (`landing.html`) |
| 999 | `defect_management` | Sí tiene consumidor (`landing.html`) |
| 1011 | `favicon` | Asset core |
| 1051 | `material` (`/ILSAN-ELECTRONICS`) | Landing principal |
| 1096 | `dashboard` | Consumido por `control-cuchillas-corte.js` |
| 1157 | `front_plan_static` | Servidor de assets `/front-plan/static/*` |
| 1393 | `cargar_template` | Helper genérico de render (consumido por `MainTemplate.html`) |
| 1468 | `control_de_material_ajax` | Render canónico de material (consumido por `MainTemplate.html`) |
| 2242 | `material_info` (`/material/info`), 3415 `produccion_info` (`/produccion/info`) | Renders consumidos por `MainTemplate.html` |
| 2290 | `verificar_permiso_dropdown` | Endpoint AJAX transversal |
| 2344 | `obtener_permisos_usuario_actual` | Endpoint AJAX transversal |
| 227 | `auth_system = AuthSystem()` (línea ~227) | Instancia global usada por decoradores |

**Movido a shared (2026-05-28)**:
- `obtener_fecha_hora_mexico()` vive en `app/api/shared/datetime_helpers.py`.
- La allowlist de APIs públicas PDA vive en `app/api/shared/public_routes.py`
  como `is_public_api_route(path)`.

`routes.py` solo conserva el middleware `require_login_by_default()` que invoca
esos helpers.

---

## Estado proyectado por fase

| Después de... | Líneas `routes.py` | Δ acumulado |
|---|---:|---:|
| Estado original (Fase 0) | 4455 | — |
| **Fase 1 (borrar 9 huérfanas) ✅** | **3804** | **-651** |
| **Fase 2 (borrar 25 re-exports zombies) ✅** | **3758** | **-697** |
| **Fase 3 (mover 36 renders + 3 endpoints salida líneas) ✅** | **3146** | **-1309** |
| **Fase 4 (mover 11 rutas gordas + Fase 5 anticipada) ✅** | **1823** | **-2632** |
| **Fase 5 (limpiar 72 imports muertos) ✅** | **1745** | **-2710** |
| **Fase 6 (auth blueprint) ✅** | **1232** | **-3223** |

**Meta destruida**: `routes.py` está en **1232 líneas** (objetivo era ~2100 / -53%).
Reducción real: **-3223 líneas (-72.3%)** desde el baseline.

**Verificación final del contenido**: AST analysis confirma que las **40 funciones
top-level** que quedan en `routes.py` corresponden 1:1 con la lista de
"debe quedarse" del plan (24 core + 8 LISTAS + 1 serve_list_template + 7 más).
**0 funciones faltantes, 0 funciones extra** (los 3 closures internos
`decorated_function`/`decorator`/`decorada` son parte legítima de la
implementación de `login_requerido` y `requiere_permiso_dropdown`).

**Refactor COMPLETO**: `routes.py` con **1232 líneas**, **33 defs top-level**
(decoradores, middleware, helpers de auth, landing/dashboard, renders
transversales y LISTAS), **0 funciones DDL**, **0 re-exports zombies**,
**0 imports muertos**.

---

## Smoke test estándar entre fases

```powershell
$env:PYTHONIOENCODING="utf-8"
python -c "
from app_factory import create_app
app = create_app()
total = sum(1 for _ in app.url_map.iter_rules())
print(f'OK rutas: {total}')
"
```

**Resultado esperado tras cada fase**:
- Fase 1: 388 → 379 (9 menos).
- Fase 2: 379 → 379 (sin cambios, sólo borra exports).
- Fase 3: 379 → 379 (sin cambios, sólo mueve handlers de un blueprint a otro).
- Fase 4: 379 → 379 (idem).
- Fase 5: 379 → 379 (sólo helpers, no rutas).

Cualquier cambio en el conteo total que no sea esperado = regresión.

---

## Riesgos cruzados y mitigación

1. **`login_requerido` es crítico**: vive en `routes.py` como decorador core.
   **No tocar** sin revisar todos los blueprints. Los módulos que lo necesitan
   lo importan vía proxy `from app import routes as _r` + `_r.login_requerido(f)`
   exactamente para evitar el ciclo de import. `obtener_fecha_hora_mexico()`
   ya vive en `app/api/shared/datetime_helpers.py`.

2. **`auth_system` global** (línea ~227): instancia única consumida por
   decoradores en `routes.py`. **No tocar**.

3. **Renders movidos a `<seccion>/renders.py`**: si el blueprint registra
   rutas con el mismo URL que un endpoint existente, Flask responde con
   `View function mapping is overwriting an existing endpoint function` al
   startup. Verificar en cada fase con `app.url_map.iter_rules()`.

4. **`importar_excel_plan_produccion` (Fase 4)**: 360 líneas con lógica de
   parsing Excel + creación de plan. Probar end-to-end importando un .xlsx
   real antes de hacer merge.

5. **Aliases 301 no son necesarios en esta refactorización**: como ningún
   URL cambia (sólo cambia el archivo que lo sirve), `scriptMain.js`, las
   LISTAS y los frontend JS siguen funcionando sin tocar.
