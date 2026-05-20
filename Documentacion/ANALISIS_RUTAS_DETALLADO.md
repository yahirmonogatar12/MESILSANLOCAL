# 🔍 Análisis Detallado de Rutas (routes.py)

Este reporte analiza de forma automatizada todas las rutas declaradas en `app/routes.py`, identificando cuáles están activas y referenciadas en el frontend/backend, y cuáles podrían estar huérfanas.

## Resumen Estadístico
- **Total de Rutas Declaradas**: 346
- **Rutas Referenciadas (Activas)**: 260 (75.1%)
- **Rutas No Referenciadas (Huérfanas / Candidatas a Depuración)**: 86 (24.9%)

## ⚠️ Rutas No Referenciadas (Sin Uso Encontrado)
Estas rutas están declaradas en `app/routes.py` pero no se encontró ninguna llamada o enlace en los archivos de plantillas HTML, scripts JavaScript, ni en otras APIs en Python. **Se recomienda auditarlas para posible eliminación.**

| Línea | Ruta | Métodos | Función |
| :--- | :--- | :--- | :--- |
| 218 | `/api/health` | `GET` | `api_health` |
| 252 | `/smt-simple` | `GET` | `smt_simple` |
| 1055 | `/favicon.eco` | `GET` | `favicon` |
| 1065 | `/sistemas` | `GET` | `sistemas` |
| 1083 | `/documentacion` | `GET` | `documentacion` |
| 5022 | `/api/plan-imd/batch-update` | `POST` | `api_plan_imd_batch_update` |
| 5866 | `/api/plan-smt/batch-update` | `POST` | `api_plan_smt_batch_update` |
| 6755 | `/consultar_bom` | `GET` | `consultar_bom` |
| 7455 | `/api/ecos/<int:eco_id>/diff` | `GET` | `api_ecos_diff` |
| 7498 | `/api/ecos/<int:eco_id>/items/import` | `POST` | `api_ecos_import_items` |
| 7521 | `/api/ecos/<int:eco_id>/approve` | `POST` | `api_ecos_approve` |
| 7541 | `/api/ecos/<int:eco_id>/cancel` | `POST` | `api_ecos_cancel` |
| 7927 | `/guardar_entrada_aereo` | `POST` | `guardar_entrada_aereo` |
| 7955 | `/listar_entradas_aereo` | `GET` | `listar_entradas_aereo` |
| 8683 | `/obtener_codigos_material` | `GET` | `obtener_codigos_material` |
| 8843 | `/guardar_control_almacen` | `POST` | `guardar_control_almacen` |
| 8876 | `/obtener_secuencial_lote_interno` | `POST` | `obtener_secuencial_lote_interno` |
| 8939 | `/consultar_control_almacen` | `GET` | `consultar_control_almacen` |
| 9020 | `/actualizar_control_almacen` | `POST` | `actualizar_control_almacen` |
| 9206 | `/guardar_cliente_seleccionado` | `POST` | `guardar_cliente_seleccionado` |
| 9231 | `/cargar_cliente_seleccionado` | `GET` | `cargar_cliente_seleccionado` |
| 9247 | `/actualizar_estado_desecho_almacen` | `POST` | `actualizar_estado_desecho_almacen` |
| 9308 | `/obtener_siguiente_secuencial` | `GET` | `obtener_siguiente_secuencial` |
| 9804 | `/api/generar-plan-smd` | `POST` | `api_generar_plan_smd` |
| 14205 | `/api/almacen-embarques/<module_name>/ajustes/template` | `GET` | `api_almacen_embarques_ajustes_template` |
| 14234 | `/api/almacen-embarques/<module_name>/ajustes/preview` | `POST` | `api_almacen_embarques_ajustes_preview` |
| 14325 | `/api/almacen-embarques/<module_name>/ajustes/confirm` | `POST` | `api_almacen_embarques_ajustes_confirm` |
| 14345 | `/api/almacen-embarques/<module_name>/ajustes/manual` | `POST` | `api_almacen_embarques_ajustes_manual` |
| 14367 | `/api/almacen-embarques/<module_name>/ajustes/cancel` | `POST` | `api_almacen_embarques_ajustes_cancel` |
| 14426 | `/api/almacen-embarques/salidas/<int:exit_id>/departure` | `POST, PUT, PATCH` | `assign_almacen_embarques_departure` |
| 14455 | `/api/almacen-embarques/departures/history` | `GET` | `api_almacen_embarques_departure_history` |
| 15223 | `/api/almacen-embarques/inventario-general/cierre/history/<int:batch_id>/export` | `GET` | `export_almacen_embarques_inventario_cierre_report` |
| 17065 | `/api/ict/param-changes/detail` | `GET` | `ict_param_changes_detail` |
| 17249 | `/consultar_especificacion_por_numero_parte` | `GET` | `consultar_especificacion_por_numero_parte` |
| 17398 | `/material/control_calidad` | `GET` | `material_control_calidad` |
| 17543 | `/obtener_reglas_escaneo` | `GET` | `obtener_reglas_escaneo` |
| 17564 | `/buscar_codigo_recibido` | `GET` | `buscar_codigo_recibido` |
| 17619 | `/guardar_salida_lote` | `POST` | `guardar_salida_lote` |
| 17736 | `/consultar_historial_salidas` | `GET` | `consultar_historial_salidas` |
| 17975 | `/verificar_stock_rapido` | `GET` | `verificar_stock_rapido` |
| 18047 | `/procesar_salida_material` | `POST` | `procesar_salida_material` |
| 18202 | `/forzar_actualizacion_inventario/<numero_parte>` | `POST` | `forzar_actualizacion_inventario` |
| 18291 | `/recalcular_inventario_general` | `POST` | `recalcular_inventario_general_endpoint` |
| 18355 | `/obtener_inventario_general` | `GET` | `obtener_inventario_general_endpoint` |
| 18372 | `/verificar_estado_inventario` | `GET` | `verificar_estado_inventario` |
| 18451 | `/test_modelos` | `GET` | `test_modelos` |
| 19506 | `/csv-viewer` | `GET` | `csv_viewer` |
| 19662 | `/api/csv_stats` | `GET` | `get_csv_stats` |
| 19911 | `/api/filter_data` | `POST` | `filter_csv_data` |
| 20170 | `/guardar_regla_trazabilidad` | `POST` | `guardar_regla_trazabilidad` |
| 20289 | `/control_salida/estado` | `GET` | `control_salida_estado` |
| 20347 | `/control_salida/configuracion` | `GET, POST` | `control_salida_configuracion` |
| 20407 | `/control_salida/validar_stock` | `POST` | `control_salida_validar_stock` |
| 20481 | `/control_salida/reporte_diario` | `GET` | `control_salida_reporte_diario` |
| 20923 | `/control_salida/debug/test_connection` | `GET` | `control_salida_test_connection` |
| 21002 | `/importar_excel_almacen` | `POST` | `importar_excel_almacen` |
| 21162 | `/material/longterm_inventory` | `GET` | `material_longterm_inventory` |
| 21186 | `/importar_excel_salida` | `POST` | `importar_excel_salida` |
| 21298 | `/importar_excel_retorno` | `POST` | `importar_excel_retorno` |
| 23423 | `/ajuste-numero-parte-ajax` | `GET` | `ajuste_numero_parte_ajax` |
| 23430 | `/consultar-peps-ajax` | `GET` | `consultar_peps_ajax` |
| 23437 | `/control-entrada-salida-material-ajax` | `GET` | `control_entrada_salida_material_ajax` |
| 23446 | `/control-recibo-refacciones-ajax` | `GET` | `control_recibo_refacciones_ajax` |
| 23453 | `/control-salida-refacciones-ajax` | `GET` | `control_salida_refacciones_ajax` |
| 23460 | `/control-total-material-ajax` | `GET` | `control_total_material_ajax` |
| 23467 | `/estandares-refacciones-ajax` | `GET` | `estandares_refacciones_ajax` |
| 23474 | `/estatus-inventario-refacciones-ajax` | `GET` | `estatus_inventario_refacciones_ajax` |
| 23483 | `/estatus-material-ajax` | `GET` | `estatus_material_ajax` |
| 23490 | `/estatus-material-msl-ajax` | `GET` | `estatus_material_msl_ajax` |
| 23497 | `/historial-inventario-real-ajax` | `GET` | `historial_inventario_real_ajax` |
| 23504 | `/inventario-rollos-smd-ajax` | `GET` | `inventario_rollos_smd_ajax` |
| 23511 | `/longterm-inventory-ajax` | `GET` | `longterm_inventory_ajax` |
| 23518 | `/material-sustituto-ajax` | `GET` | `material_sustituto_ajax` |
| 23525 | `/recibo-pago-material-ajax` | `GET` | `recibo_pago_material_ajax` |
| 23532 | `/registro-material-real-ajax` | `GET` | `registro_material_real_ajax` |
| 23819 | `/api/snapshot_inventario/trigger` | `POST` | `api_snapshot_inv_trigger` |
| 23846 | `/mysql-proxy.php` | `POST, GET, OPTIONS` | `mysql_proxy_php` |
| 23954 | `/api/status` | `GET` | `api_status` |
| 24517 | `/api/mysql/usuario-actual` | `GET` | `api_mysql_usuario_actual` |
| 25189 | `/api/plan-run/pause` | `POST` | `api_plan_run_pause` |
| 25231 | `/api/plan-run/resume` | `POST` | `api_plan_run_resume` |
| 25272 | `/api/plan-run/status` | `GET` | `api_plan_run_status` |
| 25428 | `/control/metal-mask` | `GET` | `pagina_control_metal_mask` |
| 25438 | `/control/metal-mask/caja` | `GET` | `pagina_control_caja_metal_mask` |
| 27322 | `/api/vision/image-file` | `GET` | `vision_image_file_api` |
| 27476 | `/ict/front-full-defects2` | `GET` | `ict_front_full_defects2` |

##  Rutas Referenciadas (En Uso)
Estas rutas son llamadas activamente desde el frontend (AJAX, enlaces, formularios) o desde otros módulos del backend.

### `/` (GET)
- **Función**: `index` (Línea 585 en `routes.py`)
- **Referencias encontradas**:
  - `app\db_mysql.py` (Línea/s: 147, 151, 155, 157, 418)
  - `app\models_po_wo.py` (Línea/s: 16, 56, 61)
  - `app\shipping_material_api.py` (Línea/s: 2838, 2857)
  - `app\smt_routes_clean.py` (Línea/s: 130)
  - `app\smt_routes_fixed.py` (Línea/s: 186)
  - `app\tickets_portal.py` (Línea/s: 445, 448)
  - `app\user_admin.py` (Línea/s: 1476)
  - `app\py\Backend metal mask.py` (Línea/s: 89, 90)
  - `app\py\control_modelos_smt.py` (Línea/s: 117, 146, 266)
  - `app\services\ict_lgd_parser.py` (Línea/s: 94, 95, 98, 99, 105)

### `/login` (GET, POST)
- **Función**: `login` (Línea 590 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\landing.html` (Línea/s: 1507)
  - `app\templates\MaterialTemplate.html` (Línea/s: 2003, 2035, 2754, 2879)
  - `app\admin_api.py` (Línea/s: 19, 33, 41, 73, 115)
  - `app\Almacen_api.py` (Línea/s: 14, 72, 92, 104, 700)
  - `app\auth_system.py` (Línea/s: 1002, 1041, 1083, 1093)
  - `app\shipping_api.py` (Línea/s: 475, 477, 479, 1245, 1273)
  - `app\tickets_portal.py` (Línea/s: 30, 54, 67, 99, 243)
  - `app\user_admin.py` (Línea/s: 120, 163, 184, 203, 268)

### `/inicio` (GET)
- **Función**: `inicio` (Línea 733 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\calendario.html` (Línea/s: 93)
  - `app\templates\landing.html` (Línea/s: 1532)
  - `app\templates\login.html` (Línea/s: 5, 39)
  - `app\templates\portal_tickets.html` (Línea/s: 442)
  - `app\Almacen_api.py` (Línea/s: 155, 159, 160, 197, 273)
  - `app\auth_system.py` (Línea/s: 193, 1045, 1046, 1052, 1069)
  - `app\tickets_portal.py` (Línea/s: 353)
  - `app\user_admin.py` (Línea/s: 1231, 1247, 1249, 1429, 1445)

### `/api/mi-perfil` (GET, POST)
- **Función**: `api_mi_perfil` (Línea 739 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\landing.html` (Línea/s: 1886, 2040)

### `/calendario` (GET)
- **Función**: `calendario` (Línea 1035 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\landing.html` (Línea/s: 1564)

### `/defect-management` (GET)
- **Función**: `defect_management` (Línea 1042 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\landing.html` (Línea/s: 1547)

### `/soporte` (GET)
- **Función**: `soporte` (Línea 1072 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\landing.html` (Línea/s: 1563)

### `/ILSAN-ELECTRONICS` (GET)
- **Función**: `material` (Línea 1094 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\landing.html` (Línea/s: 1539)
  - `app\templates\admin\auditoria.html` (Línea/s: 589)
  - `app\templates\admin\panel_usuarios.html` (Línea/s: 187)
  - `app\Almacen_api.py` (Línea/s: 19, 22, 30, 35, 37)
  - `app\auth_system.py` (Línea/s: 279, 280, 281, 282, 283)
  - `app\db.py` (Línea/s: 24, 25, 109, 111, 113)
  - `app\db_mysql.py` (Línea/s: 56, 57, 58, 124, 125)
  - `app\shipping_api.py` (Línea/s: 58, 64, 70, 82, 112)
  - `app\shipping_material_api.py` (Línea/s: 21, 22, 23, 37, 38)
  - `app\smd_inventory_api.py` (Línea/s: 43)
  - `app\smt_csv_handler.py` (Línea/s: 59, 143, 204, 271)
  - `app\smt_routes_clean.py` (Línea/s: 4, 38, 117, 200, 209)
  - `app\smt_routes_date_fixed.py` (Línea/s: 73, 146, 152, 160)
  - `app\smt_routes_fixed.py` (Línea/s: 4, 5, 45, 54, 63)
  - `app\smt_routes_simple.py` (Línea/s: 54, 96, 101, 109)
  - `app\startup_init.py` (Línea/s: 49, 63, 64, 65)
  - `app\database\ISEMM_MES.py` (Línea/s: 16, 18, 20, 23)

### `/dashboard` (GET)
- **Función**: `dashboard` (Línea 1139 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-cuchillas-corte.js` (Línea/s: 759)
  - `app\user_admin.py` (Línea/s: 1344, 1503)

### `/logout` (GET)
- **Función**: `logout` (Línea 1173 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\landing.html` (Línea/s: 1499, 2018)
  - `app\templates\MaterialTemplate.html` (Línea/s: 3424)
  - `app\templates\admin\auditoria.html` (Línea/s: 1100)
  - `app\templates\admin\panel_usuarios.html` (Línea/s: 825)
  - `app\shipping_api.py` (Línea/s: 600, 602, 604)

### `/front-plan/static/<path:filename>` (GET)
- **Función**: `front_plan_static` (Línea 1201 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\index-functions.js` (Línea/s: 3)

### `/plan-main` (GET)
- **Función**: `view_plan_main` (Línea 1210 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de proceso\Control de operacion de linea Main.html` (Línea/s: 37, 72, 73)
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 49, 54, 59)
  - `app\static\js\plan-main-loader.js` (Línea/s: 28, 72, 253, 270)
  - `app\static\js\scriptMain.js` (Línea/s: 1149, 1305, 1374)

### `/control-main` (GET)
- **Función**: `view_control_main` (Línea 1217 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 64)

### `/plan-main-assy-ajax` (GET)
- **Función**: `plan_main_assy_ajax` (Línea 1225 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 49)
  - `app\static\js\scriptMain.js` (Línea/s: 1149)

### `/plan-main-imd-ajax` (GET)
- **Función**: `plan_main_imd_ajax` (Línea 1234 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 54)
  - `app\static\js\scriptMain.js` (Línea/s: 1305)

### `/plan-main-smt-ajax` (GET)
- **Función**: `plan_main_smt_ajax` (Línea 1243 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 59)
  - `app\static\js\scriptMain.js` (Línea/s: 1374)

### `/control-operacion-linea-main-ajax` (GET)
- **Función**: `ctrl_operacion_linea_main_ajax` (Línea 1252 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 64)
  - `app\static\js\scriptMain.js` (Línea/s: 1096)

### `/api/plan` (GET)
- **Función**: `api_plan_list` (Línea 3545 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de proceso\Control de operacion de linea SMT.html` (Línea/s: 754)
  - `app\templates\Control de produccion\crear_plan_micom_ajax.html` (Línea/s: 402, 403, 406)
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 337, 382, 431, 1291, 1362)
  - `app\static\js\plan-main-loader.js` (Línea/s: 28, 72, 253, 270, 871)
  - `app\static\js\plan-smd-module.js` (Línea/s: 15)
  - `app\static\js\plan.js` (Línea/s: 456, 764, 934, 996, 1178)
  - `app\static\js\plan_imd.js` (Línea/s: 56, 292, 394, 428, 591)
  - `app\static\js\plan_smt.js` (Línea/s: 58, 293, 395, 429, 592)

### `/api/plan/input-main/scan-lots` (GET)
- **Función**: `api_plan_input_main_scan_lots` (Línea 3610 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan.js` (Línea/s: 1814)

### `/api/plan/input-main/assign-lot` (POST)
- **Función**: `api_plan_input_main_assign_lot` (Línea 3746 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan.js` (Línea/s: 1926)

### `/api/plan/input-main/create-plan` (POST)
- **Función**: `api_plan_input_main_create_plan` (Línea 3963 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan.js` (Línea/s: 1976)

### `/api/plan` (POST)
- **Función**: `api_plan_create` (Línea 4119 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de proceso\Control de operacion de linea SMT.html` (Línea/s: 754)
  - `app\templates\Control de produccion\crear_plan_micom_ajax.html` (Línea/s: 402, 403, 406)
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 337, 382, 431, 1291, 1362)
  - `app\static\js\plan-main-loader.js` (Línea/s: 28, 72, 253, 270, 871)
  - `app\static\js\plan-smd-module.js` (Línea/s: 15)
  - `app\static\js\plan.js` (Línea/s: 456, 764, 934, 996, 1178)
  - `app\static\js\plan_imd.js` (Línea/s: 56, 292, 394, 428, 591)
  - `app\static\js\plan_smt.js` (Línea/s: 58, 293, 395, 429, 592)

### `/api/plan/update` (POST)
- **Función**: `api_plan_update` (Línea 4258 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan.js` (Línea/s: 934, 996)

### `/api/raw/search` (GET)
- **Función**: `api_raw_search` (Línea 4313 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan.js` (Línea/s: 893)

### `/api/plan/status` (POST)
- **Función**: `api_plan_status` (Línea 4367 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan-main-loader.js` (Línea/s: 871)

### `/api/plan/save-sequences` (POST)
- **Función**: `api_plan_save_sequences` (Línea 4515 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan.js` (Línea/s: 4944)

### `/api/plan/pending` (GET)
- **Función**: `api_plan_pending` (Línea 4565 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan.js` (Línea/s: 2065)

### `/api/plan/reschedule` (POST)
- **Función**: `api_plan_reschedule` (Línea 4631 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan.js` (Línea/s: 2158)

### `/api/plan/export-excel` (POST)
- **Función**: `api_plan_export_excel` (Línea 4786 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan.js` (Línea/s: 4765)

### `/api/plan-imd` (GET)
- **Función**: `api_plan_imd_list` (Línea 4875 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_imd.js` (Línea/s: 56, 292, 394, 428, 591)

### `/api/plan-imd` (POST)
- **Función**: `api_plan_imd_create` (Línea 4942 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_imd.js` (Línea/s: 56, 292, 394, 428, 591)

### `/api/plan-imd/update` (POST)
- **Función**: `api_plan_imd_update` (Línea 5064 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_imd.js` (Línea/s: 394, 428)

### `/api/plan-imd/save-sequences` (POST)
- **Función**: `api_plan_imd_save_sequences` (Línea 5113 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_imd.js` (Línea/s: 292)

### `/api/plan-imd/pending` (GET)
- **Función**: `api_plan_imd_pending` (Línea 5164 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_imd.js` (Línea/s: 909)

### `/api/plan-imd/pending-reschedule` (GET)
- **Función**: `api_plan_imd_pending_reschedule` (Línea 5218 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_imd.js` (Línea/s: 909)

### `/api/plan-imd/reschedule` (POST)
- **Función**: `api_plan_imd_reschedule` (Línea 5268 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_imd.js` (Línea/s: 962)

### `/api/plan-imd/export-excel` (POST)
- **Función**: `api_plan_imd_export_excel` (Línea 5377 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_imd.js` (Línea/s: 631)

### `/api/plan-imd/import-excel` (POST)
- **Función**: `api_plan_imd_import_excel` (Línea 5462 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_imd.js` (Línea/s: 680)

### `/api/plan-smt` (GET)
- **Función**: `api_plan_smt_list` (Línea 5721 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_smt.js` (Línea/s: 58, 293, 395, 429, 592)

### `/api/plan-smt` (POST)
- **Función**: `api_plan_smt_create` (Línea 5788 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_smt.js` (Línea/s: 58, 293, 395, 429, 592)

### `/api/plan-smt/update` (POST)
- **Función**: `api_plan_smt_update` (Línea 5900 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_smt.js` (Línea/s: 395, 429)

### `/api/plan-smt/save-sequences` (POST)
- **Función**: `api_plan_smt_save_sequences` (Línea 5942 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_smt.js` (Línea/s: 293)

### `/api/plan-smt/pending` (GET)
- **Función**: `api_plan_smt_pending` (Línea 5993 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_smt.js` (Línea/s: 906)

### `/api/plan-smt/reschedule` (POST)
- **Función**: `api_plan_smt_reschedule` (Línea 6043 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_smt.js` (Línea/s: 959)

### `/api/plan-smt/export-excel` (POST)
- **Función**: `api_plan_smt_export_excel` (Línea 6145 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_smt.js` (Línea/s: 632)

### `/api/plan-smt/import-excel` (POST)
- **Función**: `api_plan_smt_import_excel` (Línea 6222 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan_smt.js` (Línea/s: 681)

### `/api/plan-main/list` (GET)
- **Función**: `api_plan_main_list` (Línea 6425 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan-main-loader.js` (Línea/s: 72, 253, 270)

### `/api/work-orders/import` (POST)
- **Función**: `api_work_orders_import` (Línea 6493 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan.js` (Línea/s: 1620, 1720)

### `/cargar_template` (POST)
- **Función**: `cargar_template` (Línea 6657 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1306)

### `/importar_excel_bom` (POST)
- **Función**: `importar_excel_bom` (Línea 6682 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 1681)

### `/listar_modelos_bom` (GET)
- **Función**: `listar_modelos_bom` (Línea 6720 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 3444, 3445)
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 1759, 1865)
  - `app\static\js\control-embarque.js` (Línea/s: 312, 313, 513, 514)
  - `app\db_mysql.py` (Línea/s: 4195)

### `/listar_bom` (POST)
- **Función**: `listar_bom` (Línea 6736 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 1379)
  - `app\db_mysql.py` (Línea/s: 3411, 3462)

### `/api/ecos` (GET)
- **Función**: `api_ecos_list` (Línea 6809 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 778, 786, 812, 889, 1093)

### `/api/ecos/export` (GET)
- **Función**: `api_ecos_export` (Línea 6867 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 1093)

### `/api/ecos/<int:eco_id>` (GET)
- **Función**: `api_ecos_detail` (Línea 6958 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 778, 786, 812, 889, 1093)

### `/api/ecn-ks/<int:hist_seq>` (GET)
- **Función**: `api_ecn_ks_detail` (Línea 6975 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 1011)

### `/api/ecos` (POST)
- **Función**: `api_ecos_create` (Línea 6991 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 778, 786, 812, 889, 1093)

### `/api/bom/download-excel` (GET)
- **Función**: `api_bom_download_excel` (Línea 7039 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 708, 725)

### `/api/bom/resolve-family` (GET)
- **Función**: `api_bom_resolve_family` (Línea 7103 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 669)

### `/api/bom/download-excel-family` (GET)
- **Función**: `api_bom_download_excel_family` (Línea 7221 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 708)

### `/api/ecos/from-excel` (POST)
- **Función**: `api_ecos_from_excel` (Línea 7254 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 778, 786)

### `/api/ecos/from-excel-family` (POST)
- **Función**: `api_ecos_from_excel_family` (Línea 7332 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 778)

### `/api/ecos/<int:eco_id>/scope` (GET)
- **Función**: `api_ecos_scope` (Línea 7442 en `routes.py`)
- **Referencias encontradas**:
  - `Confirmación del usuario / Integración externa` (Línea/s: 1)

### `/api/ecos/<int:eco_id>` (DELETE)
- **Función**: `api_ecos_delete` (Línea 7558 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 778, 786, 812, 889, 1093)

### `/buscar_material_por_numero_parte` (GET)
- **Función**: `buscar_material_por_numero_parte` (Línea 7574 en `routes.py`)
- **Referencias encontradas**:
  - `app\db_mysql.py` (Línea/s: 3987)

### `/exportar_excel_bom` (GET)
- **Función**: `exportar_excel_bom` (Línea 7716 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 1548)

### `/api/bom/update` (POST)
- **Función**: `api_bom_update` (Línea 7763 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 2482, 2768)

### `/api/bom/update-posiciones-assy` (POST)
- **Función**: `api_bom_update_posiciones_assy` (Línea 7852 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 2768)

### `/guardar_material` (POST)
- **Función**: `guardar_material_route` (Línea 7966 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\material-edit-drawer.js` (Línea/s: 984)

### `/listar_materiales` (GET)
- **Función**: `listar_materiales` (Línea 8007 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_MATERIAL.html` (Línea/s: 347)

### `/api/inventario/lotes_detalle` (POST)
- **Función**: `consultar_lotes_detalle` (Línea 8022 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\Registro_de_material_real.js` (Línea/s: 610)

### `/importar_excel` (POST)
- **Función**: `importar_excel` (Línea 8168 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de material\Estatus de material.html` (Línea/s: 126, 165)
  - `app\templates\Control de material\Historial de inventario real.html` (Línea/s: 1206)
  - `app\templates\Control de material\Registro de material real.html` (Línea/s: 278)
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 1681)
  - `app\templates\INFORMACION BASICA\CONTROL_DE_MATERIAL.html` (Línea/s: 443)
  - `app\static\js\crear-plan-produccion.js` (Línea/s: 1210)

### `/actualizar_campo_material` (POST)
- **Función**: `actualizar_campo_material` (Línea 8483 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_MATERIAL.html` (Línea/s: 474)

### `/actualizar_material_completo` (POST)
- **Función**: `actualizar_material_completo_route` (Línea 8545 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\material-edit-drawer.js` (Línea/s: 614)

### `/exportar_excel` (GET)
- **Función**: `exportar_excel` (Línea 8584 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html` (Línea/s: 1548)
  - `app\templates\INFORMACION BASICA\CONTROL_DE_MATERIAL.html` (Línea/s: 382)

### `/control_calidad` (GET)
- **Función**: `control_calidad` (Línea 8837 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1574, 3332)
  - `app\db.py` (Línea/s: 158, 159)

### `/informacion_basica/control_de_material` (GET)
- **Función**: `control_de_material_ajax` (Línea 9445 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2445)

### `/informacion_basica/control_de_bom` (GET)
- **Función**: `control_de_bom_ajax` (Línea 9456 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2538)
  - `app\templates\LISTAS\LISTA_INFORMACIONBASICA.html` (Línea/s: 92, 97)

### `/listas/informacion_basica` (GET)
- **Función**: `lista_informacion_basica` (Línea 9474 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1550, 3280)

### `/listas/control_material` (GET)
- **Función**: `lista_control_material` (Línea 9485 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1556, 3122)

### `/listas/control_produccion` (GET)
- **Función**: `lista_control_produccion` (Línea 9496 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1562, 3318)

### `/control_produccion/control_embarque` (GET)
- **Función**: `control_embarque` (Línea 9507 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2615)
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 15)

### `/Control de embarque` (GET)
- **Función**: `control_embarque_ajax` (Línea 9518 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2720)

### `/control_produccion/crear_plan` (GET)
- **Función**: `crear_plan_produccion` (Línea 9529 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2648)
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 20, 25)

### `/control_produccion/plan_smt` (GET)
- **Función**: `plan_smt_ajax` (Línea 9546 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2681)

### `/api/work-orders` (GET)
- **Función**: `api_work_orders` (Línea 9597 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan-smd-module.js` (Línea/s: 13)
  - `app\static\js\plan.js` (Línea/s: 876, 1445, 1620, 1720)

### `/api/inventario/modelo/<codigo_modelo>` (GET)
- **Función**: `api_inventario_modelo` (Línea 9701 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\plan-smd-module.js` (Línea/s: 14)

### `/api/plan-smd` (POST)
- **Función**: `api_plan_smd_guardar` (Línea 9745 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de proceso\Control de operacion de linea SMT.html` (Línea/s: 754)
  - `app\templates\Control de produccion\crear_plan_micom_ajax.html` (Línea/s: 402, 403)
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 337, 382, 431, 1362, 2943)
  - `app\static\js\plan-smd-module.js` (Línea/s: 15)

### `/control_proceso/control_produccion_smt` (GET)
- **Función**: `control_produccion_smt_ajax` (Línea 10062 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 15)
  - `app\static\js\scriptMain.js` (Línea/s: 2678)

### `/control-bom-ajax` (GET)
- **Función**: `control_bom_ajax` (Línea 10077 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\scriptMain.js` (Línea/s: 2963)

### `/crear-plan-micom-ajax` (GET)
- **Función**: `crear_plan_micom_ajax` (Línea 10100 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 25)
  - `app\static\js\scriptMain.js` (Línea/s: 2814)

### `/control-operacion-linea-smt-ajax` (GET)
- **Función**: `control_operacion_linea_smt_ajax` (Línea 10111 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 20)
  - `app\static\js\scriptMain.js` (Línea/s: 1009)

### `/control-impresion-identificacion-smt-ajax` (GET)
- **Función**: `control_impresion_identificacion_smt_ajax` (Línea 10127 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 30)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 8)
  - `app\static\js\scriptMain.js` (Línea/s: 1450)

### `/control-registro-identificacion-smt-ajax` (GET)
- **Función**: `control_registro_identificacion_smt_ajax` (Línea 10142 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 35)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 17)
  - `app\static\js\scriptMain.js` (Línea/s: 1511)

### `/historial-operacion-proceso-ajax` (GET)
- **Función**: `historial_operacion_proceso_ajax` (Línea 10157 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 69)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 26)
  - `app\static\js\scriptMain.js` (Línea/s: 1572)

### `/bom-management-process-ajax` (GET)
- **Función**: `bom_management_process_ajax` (Línea 10170 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 74)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 35)
  - `app\static\js\scriptMain.js` (Línea/s: 1633)

### `/reporte-diario-inspeccion-smt-ajax` (GET)
- **Función**: `reporte_diario_inspeccion_smt_ajax` (Línea 10181 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 94)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 44)
  - `app\static\js\scriptMain.js` (Línea/s: 1693)

### `/control-diario-inspeccion-smt-ajax` (GET)
- **Función**: `control_diario_inspeccion_smt_ajax` (Línea 10194 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 99)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 53)
  - `app\static\js\scriptMain.js` (Línea/s: 1754)

### `/reporte-diario-inspeccion-proceso-ajax` (GET)
- **Función**: `reporte_diario_inspeccion_proceso_ajax` (Línea 10207 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 104, 109)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 62)
  - `app\static\js\scriptMain.js` (Línea/s: 1815)

### `/control-unidad-empaque-modelo-ajax` (GET)
- **Función**: `control_unidad_empaque_modelo_ajax` (Línea 10222 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 123)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 71)
  - `app\static\js\scriptMain.js` (Línea/s: 1876)

### `/packaging-register-management-ajax` (GET)
- **Función**: `packaging_register_management_ajax` (Línea 10235 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 128)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 80)
  - `app\static\js\scriptMain.js` (Línea/s: 1937)

### `/search-packaging-history-ajax` (GET)
- **Función**: `search_packaging_history_ajax` (Línea 10248 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 133)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 89)
  - `app\static\js\scriptMain.js` (Línea/s: 1998)

### `/shipping-register-management-ajax` (GET)
- **Función**: `shipping_register_management_ajax` (Línea 10259 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 138)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 98)
  - `app\static\js\scriptMain.js` (Línea/s: 2058)

### `/search-shipping-history-ajax` (GET)
- **Función**: `search_shipping_history_ajax` (Línea 10272 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 143)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 107)
  - `app\static\js\scriptMain.js` (Línea/s: 2119)

### `/almacen-embarques-entradas-ajax` (GET)
- **Función**: `almacen_embarques_entradas_ajax` (Línea 13985 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 157)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 116)
  - `app\static\js\scriptMain.js` (Línea/s: 2197)

### `/control-salida-lineas-ajax` (GET)
- **Función**: `control_salida_lineas_ajax` (Línea 13998 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 79)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 170)
  - `app\static\js\scriptMain.js` (Línea/s: 2251)

### `/almacen-embarques-salidas-ajax` (GET)
- **Función**: `almacen_embarques_salidas_ajax` (Línea 14009 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 162)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 125)
  - `app\static\js\scriptMain.js` (Línea/s: 2206)

### `/almacen-embarques-retorno-ajax` (GET)
- **Función**: `almacen_embarques_retorno_ajax` (Línea 14022 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 167)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 134)
  - `app\static\js\scriptMain.js` (Línea/s: 2215)

### `/almacen-embarques-movimientos-ajax` (GET)
- **Función**: `almacen_embarques_movimientos_ajax` (Línea 14039 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 172)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 143)
  - `app\static\js\scriptMain.js` (Línea/s: 2224)

### `/almacen-embarques-inventario-general-ajax` (GET)
- **Función**: `almacen_embarques_inventario_general_ajax` (Línea 14052 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 177)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 152)
  - `app\static\js\scriptMain.js` (Línea/s: 2233)

### `/almacen-embarques-catalogo-ajax` (GET)
- **Función**: `almacen_embarques_catalogo_ajax` (Línea 14067 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 182)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 161)
  - `app\static\js\scriptMain.js` (Línea/s: 2242)

### `/api/almacen-embarques/entradas` (GET)
- **Función**: `api_almacen_embarques_entradas` (Línea 14084 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_history.js` (Línea/s: 3038, 3039)

### `/api/control-salida-lineas` (GET)
- **Función**: `api_control_salida_lineas` (Línea 14095 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control_salida_lineas.js` (Línea/s: 352, 388)

### `/api/control-salida-lineas/export` (GET)
- **Función**: `export_control_salida_lineas` (Línea 14108 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control_salida_lineas.js` (Línea/s: 388)

### `/api/almacen-embarques/entradas/export` (GET)
- **Función**: `export_almacen_embarques_entradas` (Línea 14133 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_history.js` (Línea/s: 3039)

### `/api/almacen-embarques/salidas` (GET)
- **Función**: `api_almacen_embarques_salidas` (Línea 14163 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_history.js` (Línea/s: 2717, 3052, 3053)

### `/api/almacen-embarques/salidas/export` (GET)
- **Función**: `export_almacen_embarques_salidas` (Línea 14174 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_history.js` (Línea/s: 3053)

### `/api/almacen-embarques/retorno` (GET)
- **Función**: `api_almacen_embarques_retorno` (Línea 14474 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_history.js` (Línea/s: 1963, 2365, 2450, 2559, 3066)

### `/api/almacen-embarques/retorno/export` (GET)
- **Función**: `export_almacen_embarques_retorno` (Línea 14485 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_history.js` (Línea/s: 2559, 3067)

### `/api/almacen-embarques/retorno/print-pdf` (POST)
- **Función**: `export_almacen_embarques_retorno_print_pdf` (Línea 14560 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_history.js` (Línea/s: 2365)

### `/api/almacen-embarques/movimientos` (GET)
- **Función**: `api_almacen_embarques_movimientos` (Línea 14587 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 2395, 2452, 2658, 2659)

### `/api/almacen-embarques/movimientos/export` (GET)
- **Función**: `export_almacen_embarques_movimientos` (Línea 14605 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 2659)

### `/api/almacen-embarques/movimientos/<movement_type>/<int:record_id>` (GET)
- **Función**: `api_almacen_embarques_movimiento_detalle` (Línea 14637 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 2395, 2452, 2658, 2659)

### `/api/almacen-embarques/inventario-general` (GET)
- **Función**: `api_almacen_embarques_inventario_general` (Línea 14722 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1230, 1268, 1306, 1360, 1411)

### `/api/almacen-embarques/catalogo` (GET)
- **Función**: `api_almacen_embarques_catalogo` (Línea 14736 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1720, 1721, 1854, 2701, 2702)

### `/api/almacen-embarques/catalogo` (POST)
- **Función**: `api_almacen_embarques_catalogo_create` (Línea 14749 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1720, 1721, 1854, 2701, 2702)

### `/api/almacen-embarques/catalogo/<int:catalog_id>` (PATCH)
- **Función**: `api_almacen_embarques_catalogo_update` (Línea 14763 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1720, 1721, 1854, 2701, 2702)

### `/api/almacen-embarques/catalogo/<int:catalog_id>` (DELETE)
- **Función**: `api_almacen_embarques_catalogo_delete` (Línea 14779 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1720, 1721, 1854, 2701, 2702)

### `/api/almacen-embarques/catalogo/export` (GET)
- **Función**: `export_almacen_embarques_catalogo` (Línea 14795 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 2702)

### `/api/almacen-embarques/inventario-general/export` (GET)
- **Función**: `export_almacen_embarques_inventario_general` (Línea 14821 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 2671)

### `/api/almacen-embarques/inventario-general/cierre/bootstrap` (GET)
- **Función**: `api_almacen_embarques_inventario_cierre_bootstrap` (Línea 14852 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1230)

### `/api/almacen-embarques/inventario-general/cierre/template` (GET)
- **Función**: `api_almacen_embarques_inventario_cierre_template` (Línea 14876 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1495)

### `/api/almacen-embarques/inventario-general/cierre/preview` (POST)
- **Función**: `api_almacen_embarques_inventario_cierre_preview` (Línea 14903 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1268)

### `/api/almacen-embarques/inventario-general/cierre/confirm` (POST)
- **Función**: `api_almacen_embarques_inventario_cierre_confirm` (Línea 14965 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1360)

### `/api/almacen-embarques/inventario-general/cierre/cancel` (POST)
- **Función**: `api_almacen_embarques_inventario_cierre_cancel` (Línea 15101 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1306)

### `/api/almacen-embarques/inventario-general/cierre/history/<int:batch_id>` (GET)
- **Función**: `api_almacen_embarques_inventario_cierre_history_detail` (Línea 15176 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\almacen_embarques_admin.js` (Línea/s: 1411, 1516)

### `/registro-movimiento-identificacion-ajax` (GET)
- **Función**: `registro_movimiento_identificacion_ajax` (Línea 15754 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 196)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 179)
  - `app\static\js\scriptMain.js` (Línea/s: 2301)

### `/control-otras-identificaciones-ajax` (GET)
- **Función**: `control_otras_identificaciones_ajax` (Línea 15767 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 201)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 188)
  - `app\static\js\scriptMain.js` (Línea/s: 2362)

### `/control-movimiento-ns-producto-ajax` (GET)
- **Función**: `control_movimiento_ns_producto_ajax` (Línea 15780 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 215)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 197)
  - `app\static\js\scriptMain.js` (Línea/s: 2423)

### `/model-sn-management-ajax` (GET)
- **Función**: `model_sn_management_ajax` (Línea 15793 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 220)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 206)
  - `app\static\js\scriptMain.js` (Línea/s: 2485)

### `/control-scrap-ajax` (GET)
- **Función**: `control_scrap_ajax` (Línea 15804 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 234)
  - `app\static\js\control-proceso-ajax-functions-template.js` (Línea/s: 215)
  - `app\static\js\scriptMain.js` (Línea/s: 2543)

### `/line-material-status-ajax` (GET)
- **Función**: `line_material_status_ajax` (Línea 15816 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 106)
  - `app\static\js\scriptMain.js` (Línea/s: 3078)

### `/control-mask-metal-ajax` (GET)
- **Función**: `control_mask_metal_ajax` (Línea 15829 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 53)
  - `app\static\js\scriptMain.js` (Línea/s: 3186)

### `/control-squeegee-ajax` (GET)
- **Función**: `control_squeegee_ajax` (Línea 15840 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 58)
  - `app\static\js\scriptMain.js` (Línea/s: 3273)

### `/control-caja-mask-metal-ajax` (GET)
- **Función**: `control_caja_mask_metal_ajax` (Línea 15851 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 63)
  - `app\static\js\scriptMain.js` (Línea/s: 3358)

### `/estandares-soldadura-ajax` (GET)
- **Función**: `estandares_soldadura_ajax` (Línea 15864 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 77)
  - `app\static\js\scriptMain.js` (Línea/s: 3449)

### `/registro-recibo-soldadura-ajax` (GET)
- **Función**: `registro_recibo_soldadura_ajax` (Línea 15877 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 82)
  - `app\static\js\scriptMain.js` (Línea/s: 3539)

### `/control-salida-soldadura-ajax` (GET)
- **Función**: `control_salida_soldadura_ajax` (Línea 15890 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 87)
  - `app\static\js\scriptMain.js` (Línea/s: 3630)

### `/historial-tension-mask-metal-ajax` (GET)
- **Función**: `historial_tension_mask_metal_ajax` (Línea 15903 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html` (Línea/s: 92)
  - `app\static\js\scriptMain.js` (Línea/s: 3721)

### `/listas/control_proceso` (GET)
- **Función**: `lista_control_proceso` (Línea 15942 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1568, 3190)

### `/listas/control_calidad` (GET)
- **Función**: `lista_control_calidad` (Línea 15953 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1574, 3332)

### `/listas/control_resultados` (GET)
- **Función**: `lista_control_resultados` (Línea 15964 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1580, 3234, 3347)

### `/historial-aoi` (GET)
- **Función**: `historial_aoi` (Línea 15975 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 49)
  - `app\static\js\scriptMain.js` (Línea/s: 4376)

### `/historial-ict-ajax` (GET)
- **Función**: `historial_ict_ajax` (Línea 15986 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 75)
  - `app\static\js\scriptMain.js` (Línea/s: 4480)

### `/historial-maquina-ict-pass-fail` (GET)
- **Función**: `historial_maquina_ict_pass_fail` (Línea 15996 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 81)
  - `app\static\js\scriptMain.js` (Línea/s: 4703)

### `/historial-maquina-ict-pass-fail-ajax` (GET)
- **Función**: `historial_maquina_ict_pass_fail` (Línea 15997 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 81)

### `/api/ict/pass-fail` (GET)
- **Función**: `ict_pass_fail_api` (Línea 16089 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\ict-Pass-Fail.js` (Línea/s: 177, 492, 518)

### `/api/ict/pass-fail/detail` (GET)
- **Función**: `ict_pass_fail_detail_api` (Línea 16127 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\ict-Pass-Fail.js` (Línea/s: 492)

### `/api/ict/pass-fail/export` (GET)
- **Función**: `ict_pass_fail_export` (Línea 16274 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\ict-Pass-Fail.js` (Línea/s: 518)

### `/historial-cambios-parametros-ict-ajax` (GET)
- **Función**: `historial_cambios_parametros_ict_ajax` (Línea 16383 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 87)
  - `app\static\js\scriptMain.js` (Línea/s: 4928)

### `/api/ict/param-changes/progress` (GET)
- **Función**: `ict_param_changes_progress` (Línea 16912 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\historial_cambios_parametros_ict.js` (Línea/s: 116)

### `/api/ict/param-changes` (GET)
- **Función**: `ict_param_changes_api` (Línea 16932 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\historial_cambios_parametros_ict.js` (Línea/s: 116, 250, 315)

### `/api/ict/param-changes/export` (GET)
- **Función**: `ict_param_changes_export` (Línea 16966 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\historial_cambios_parametros_ict.js` (Línea/s: 315)

### `/historial-aoi-ajax` (GET)
- **Función**: `historial_aoi_ajax` (Línea 17205 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 49)
  - `app\static\js\scriptMain.js` (Línea/s: 4376)

### `/listas/control_reporte` (GET)
- **Función**: `lista_control_reporte` (Línea 17216 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1586, 3357)

### `/listas/configuracion_programa` (GET)
- **Función**: `lista_configuracion_programa` (Línea 17227 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1592, 3366)

### `/material/info` (GET)
- **Función**: `material_info` (Línea 17238 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2601)
  - `app\db_mysql.py` (Línea/s: 4126, 4128, 4149)

### `/material/historial_inventario` (GET)
- **Función**: `material_historial_inventario` (Línea 17409 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 3039)

### `/material/registro_material` (GET)
- **Función**: `material_registro_material` (Línea 17420 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 3024)

### `/material/estatus_material` (GET)
- **Función**: `material_estatus_material` (Línea 17431 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2963)
  - `app\static\js\scriptMain.js` (Línea/s: 579)

### `/api/estatus_material/consultar` (POST)
- **Función**: `consultar_estatus_material` (Línea 17442 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\Estatus de material.js` (Línea/s: 23)

### `/buscar_material_por_codigo` (GET)
- **Función**: `buscar_material_por_codigo` (Línea 17887 en `routes.py`)
- **Referencias encontradas**:
  - `app\db_mysql.py` (Línea/s: 3822)

### `/api/inventario/consultar` (POST)
- **Función**: `consultar_inventario_general` (Línea 18458 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\Registro_de_material_real.js` (Línea/s: 63)
  - `app\static\js\Registro_de_material_real_new.js` (Línea/s: 36)

### `/api/inventario/historial` (POST)
- **Función**: `obtener_historial_numero_parte` (Línea 18608 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\Registro_de_material_real.js` (Línea/s: 550)
  - `app\static\js\Registro_de_material_real_new.js` (Línea/s: 145)

### `/api/inventario/historial/<numero_parte>` (GET)
- **Función**: `obtener_historial_numero_parte_get` (Línea 18825 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\Registro_de_material_real.js` (Línea/s: 550)
  - `app\static\js\Registro_de_material_real_new.js` (Línea/s: 145)

### `/api/inventario/lotes` (POST)
- **Función**: `obtener_lotes_numero_parte` (Línea 19040 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\Registro_de_material_real.js` (Línea/s: 610)
  - `app\static\js\Registro_de_material_real_new.js` (Línea/s: 169)

### `/api/inventario/lotes/<numero_parte>` (GET)
- **Función**: `obtener_lotes_numero_parte_get` (Línea 19204 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\Registro_de_material_real.js` (Línea/s: 610)
  - `app\static\js\Registro_de_material_real_new.js` (Línea/s: 169)

### `/templates/LISTAS/<filename>` (GET)
- **Función**: `serve_list_template` (Línea 19365 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 1281, 1285, 1289, 1293, 1297)

### `/verificar_permiso_dropdown` (POST)
- **Función**: `verificar_permiso_dropdown` (Línea 19404 en `routes.py`)
- **Referencias encontradas**:
  - `app\user_admin.py` (Línea/s: 1163, 1165)

### `/obtener_permisos_usuario_actual` (GET)
- **Función**: `obtener_permisos_usuario_actual` (Línea 19457 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\permisos-dropdowns.js` (Línea/s: 59, 70)
  - `app\user_admin.py` (Línea/s: 1188, 1190)

### `/historial-cambio-material-smt` (GET)
- **Función**: `historial_cambio_material_smt` (Línea 19518 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 3095)
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 34)
  - `app\smt_csv_handler.py` (Línea/s: 59, 143, 204, 271)
  - `app\smt_routes_clean.py` (Línea/s: 38, 117, 200, 209, 249)
  - `app\smt_routes_date_fixed.py` (Línea/s: 73, 146, 152, 160)
  - `app\smt_routes_fixed.py` (Línea/s: 5, 45, 54, 63, 92)
  - `app\smt_routes_simple.py` (Línea/s: 54, 96, 101, 109)

### `/historial-cambio-material-smt-ajax` (GET)
- **Función**: `historial_cambio_material_smt_ajax` (Línea 19529 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 3095)
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 34)
  - `app\smt_routes_clean.py` (Línea/s: 38)
  - `app\smt_routes_fixed.py` (Línea/s: 92, 97)

### `/api/csv_data` (GET)
- **Función**: `get_csv_data` (Línea 19542 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\historial_cambio_material_smt.js` (Línea/s: 48)

### `/importar_excel_plan_produccion` (POST)
- **Función**: `importar_excel_plan_produccion` (Línea 20559 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\crear-plan-produccion.js` (Línea/s: 1210)

### `/produccion/info` (GET)
- **Función**: `produccion_info` (Línea 21115 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 3156)

### `/material/recibo_pago` (GET)
- **Función**: `material_recibo_pago` (Línea 21129 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2920)

### `/material/material_sustituto` (GET)
- **Función**: `material_material_sustituto` (Línea 21140 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2978)

### `/material/consultar_peps` (GET)
- **Función**: `material_consultar_peps` (Línea 21151 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2993)

### `/material/ajuste_numero` (GET)
- **Función**: `material_ajuste_numero` (Línea 21175 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 3069)

### `/importar_excel_registro` (POST)
- **Función**: `importar_excel_registro` (Línea 21409 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de material\Registro de material real.html` (Línea/s: 278)

### `/importar_excel_estatus_inventario` (POST)
- **Función**: `importar_excel_estatus_inventario` (Línea 21520 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de material\Estatus de material.html` (Línea/s: 126)

### `/importar_excel_estatus_recibido` (POST)
- **Función**: `importar_excel_estatus_recibido` (Línea 21631 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de material\Estatus de material.html` (Línea/s: 165)

### `/importar_excel_historial` (POST)
- **Función**: `importar_excel_historial` (Línea 21743 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de material\Historial de inventario real.html` (Línea/s: 1206)

### `/api/wo/exportar` (GET)
- **Función**: `exportar_wos_excel` (Línea 21859 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\crear-plan-produccion.js` (Línea/s: 832)

### `/api/plan-smd/import` (POST)
- **Función**: `api_plan_smd_import` (Línea 21988 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de produccion\crear_plan_micom_ajax.html` (Línea/s: 403)

### `/api/inventario` (GET)
- **Función**: `api_inventario` (Línea 22140 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de produccion\crear_plan_micom_ajax.html` (Línea/s: 404)
  - `app\static\js\inventario-imd-terminado-module.js` (Línea/s: 476, 749)
  - `app\static\js\plan-smd-module.js` (Línea/s: 14)
  - `app\static\js\Registro_de_material_real.js` (Línea/s: 63, 550, 610)
  - `app\static\js\Registro_de_material_real_new.js` (Línea/s: 36, 145, 169)

### `/api/plan-micom/generar` (POST)
- **Función**: `api_plan_micom_generar` (Línea 22195 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de produccion\crear_plan_micom_ajax.html` (Línea/s: 406)

### `/control-resultado-reparacion-ajax` (GET)
- **Función**: `control_resultado_reparacion_ajax` (Línea 22267 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 15)
  - `app\static\js\scriptMain.js` (Línea/s: 3784)

### `/control-item-reparado-ajax` (GET)
- **Función**: `control_item_reparado_ajax` (Línea 22274 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 20)
  - `app\static\js\scriptMain.js` (Línea/s: 3835)

### `/historial-cambio-material-maquina-ajax` (GET)
- **Función**: `historial_cambio_material_maquina_ajax` (Línea 22281 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 39)
  - `app\static\js\scriptMain.js` (Línea/s: 3883)

### `/api/historial-cambio-material-maquina` (GET)
- **Función**: `api_historial_cambio_material_maquina` (Línea 22290 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de calidad\historial_cambio_material_maquina_ajax.html` (Línea/s: 390)
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1770, 2018)

### `/api/historial_smt_latest` (GET)
- **Función**: `api_historial_smt_latest` (Línea 22417 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1791)

### `/api/historial_smt_latest_v2` (GET)
- **Función**: `api_historial_smt_latest_v2` (Línea 22521 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1791)

### `/api/masks/info` (GET)
- **Función**: `api_masks_info` (Línea 22620 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1560)

### `/historial-uso-pegamento-soldadura-ajax` (GET)
- **Función**: `historial_uso_pegamento_soldadura_ajax` (Línea 22692 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 53)
  - `app\static\js\scriptMain.js` (Línea/s: 3937)

### `/api/metal-mask/history` (POST)
- **Función**: `api_save_metal_mask_history` (Línea 22704 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de calidad\historial_uso_mask_metal_ajax.html` (Línea/s: 288)
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1648, 2638, 2685)

### `/api/metal-mask/history` (GET)
- **Función**: `api_get_metal_mask_history` (Línea 22801 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de calidad\historial_uso_mask_metal_ajax.html` (Línea/s: 288)
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1648, 2638, 2685)

### `/api/metal-mask/update-used-count` (POST)
- **Función**: `api_update_metal_mask_used_count` (Línea 22895 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 2534)

### `/historial-uso-mask-metal-ajax` (GET)
- **Función**: `historial_uso_mask_metal_ajax` (Línea 23057 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 58)
  - `app\static\js\scriptMain.js` (Línea/s: 3991)

### `/historial-uso-squeegee-ajax` (GET)
- **Función**: `historial_uso_squeegee_ajax` (Línea 23064 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 63)
  - `app\static\js\scriptMain.js` (Línea/s: 4042)

### `/process-interlock-history-ajax` (GET)
- **Función**: `process_interlock_history_ajax` (Línea 23071 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 77)
  - `app\static\js\scriptMain.js` (Línea/s: 4090)

### `/control-master-sample-smt-ajax` (GET)
- **Función**: `control_master_sample_smt_ajax` (Línea 23078 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 91)
  - `app\static\js\scriptMain.js` (Línea/s: 4139)

### `/historial-inspeccion-master-sample-smt-ajax` (GET)
- **Función**: `historial_inspeccion_master_sample_smt_ajax` (Línea 23085 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 96)
  - `app\static\js\scriptMain.js` (Línea/s: 4190)

### `/control-inspeccion-oqc-ajax` (GET)
- **Función**: `control_inspeccion_oqc_ajax` (Línea 23094 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 110)
  - `app\static\js\scriptMain.js` (Línea/s: 4244)

### `/historial-liberacion-lqc-ajax` (GET)
- **Función**: `historial_liberacion_lqc_ajax` (Línea 23101 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html` (Línea/s: 115)
  - `app\static\js\scriptMain.js` (Línea/s: 4291)

### `/api/smt-scanner/lineas` (GET)
- **Función**: `api_smt_scanner_lineas` (Línea 23132 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de calidad\historial_liberacion_lqc_ajax.html` (Línea/s: 442)

### `/api/smt-scanner/datos` (GET)
- **Función**: `api_smt_scanner_datos` (Línea 23244 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de calidad\historial_liberacion_lqc_ajax.html` (Línea/s: 472)

### `/api/inventario_general` (GET)
- **Función**: `api_inventario_general` (Línea 23542 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\inventario-imd-terminado-module.js` (Línea/s: 476, 749)

### `/api/ubicacion` (GET)
- **Función**: `api_ubicacion` (Línea 23589 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\inventario-imd-terminado-module.js` (Línea/s: 393, 737)

### `/api/movimientos` (GET)
- **Función**: `api_movimientos` (Línea 23652 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\inventario-imd-terminado-module.js` (Línea/s: 420, 743)

### `/api/snapshot_inventario/fechas` (GET)
- **Función**: `api_snapshot_inv_fechas` (Línea 23727 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\inventario-imd-terminado-module.js` (Línea/s: 549)

### `/api/snapshot_inventario/general` (GET)
- **Función**: `api_snapshot_inv_general` (Línea 23752 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\inventario-imd-terminado-module.js` (Línea/s: 589)

### `/api/snapshot_inventario/ubicacion` (GET)
- **Función**: `api_snapshot_inv_ubicacion` (Línea 23787 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\inventario-imd-terminado-module.js` (Línea/s: 590)

### `/api/mysql` (POST, GET, OPTIONS)
- **Función**: `api_mysql_simple` (Línea 23888 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\visor_mysql.js` (Línea/s: 115, 136, 886, 890, 989)

### `/plan-smd-diario` (GET)
- **Función**: `plan_smd_diario` (Línea 23987 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de proceso\Control de operacion de linea SMT.html` (Línea/s: 754)
  - `app\static\js\scriptMain.js` (Línea/s: 5023)

### `/control-operacion-linea-smt` (GET)
- **Función**: `control_operacion_linea_smt` (Línea 23993 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html` (Línea/s: 20)
  - `app\static\js\scriptMain.js` (Línea/s: 1009)

### `/api/plan-smd-diario` (GET)
- **Función**: `api_plan_smd_diario` (Línea 23999 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\Control de proceso\Control de operacion de linea SMT.html` (Línea/s: 754)

### `/visor-mysql` (GET)
- **Función**: `visor_mysql` (Línea 24086 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\MaterialTemplate.html` (Línea/s: 2586)

### `/control-modelos-visor-ajax` (GET)
- **Función**: `control_modelos_visor_ajax` (Línea 24096 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_INFORMACIONBASICA.html` (Línea/s: 87)
  - `app\static\js\scriptMain.js` (Línea/s: 5119)

### `/control-modelos-smt-ajax` (GET)
- **Función**: `control_modelos_smt_ajax` (Línea 24120 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_INFORMACIONBASICA.html` (Línea/s: 82)
  - `app\static\js\scriptMain.js` (Línea/s: 5194)

### `/api/mysql/columns` (GET)
- **Función**: `api_mysql_columns` (Línea 24136 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\visor_mysql.js` (Línea/s: 115)

### `/api/mysql/data` (GET)
- **Función**: `api_mysql_data` (Línea 24163 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\visor_mysql.js` (Línea/s: 136)

### `/api/mysql/update` (POST)
- **Función**: `api_mysql_update` (Línea 24264 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\visor_mysql.js` (Línea/s: 890)

### `/api/mysql/create` (POST)
- **Función**: `api_mysql_create` (Línea 24424 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\visor_mysql.js` (Línea/s: 886)

### `/api/mysql/delete` (POST)
- **Función**: `api_mysql_delete` (Línea 24537 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\visor_mysql.js` (Línea/s: 989)

### `/api/plan-smd/list` (GET)
- **Función**: `api_plan_smd_list` (Línea 24675 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 337, 382, 431, 1362, 2943)

### `/api/plan-run/start` (POST)
- **Función**: `api_plan_run_start` (Línea 24893 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1291)

### `/api/plan-run/end` (POST)
- **Función**: `api_plan_run_end` (Línea 25081 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1374)

### `/api/masks` (GET)
- **Función**: `api_list_masks` (Línea 25451 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1560)
  - `app\static\js\MetalMask.js` (Línea/s: 51, 59, 64, 138)
  - `app\py\Backend metal mask.py` (Línea/s: 105, 135, 279)

### `/api/masks` (POST)
- **Función**: `api_create_mask` (Línea 25491 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1560)
  - `app\static\js\MetalMask.js` (Línea/s: 51, 59, 64, 138)
  - `app\py\Backend metal mask.py` (Línea/s: 105, 135, 279)

### `/api/masks/<int:mask_id>` (PUT)
- **Función**: `api_update_mask` (Línea 25537 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 1560)
  - `app\static\js\MetalMask.js` (Línea/s: 51, 59, 64, 138)
  - `app\py\Backend metal mask.py` (Línea/s: 105, 135, 279)

### `/api/storage` (GET)
- **Función**: `api_get_storage` (Línea 25583 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\Caja-metalmask.js` (Línea/s: 51, 52, 77)
  - `app\static\js\MetalMask.js` (Línea/s: 56, 58, 62, 68, 98)
  - `app\py\Backend metal mask.py` (Línea/s: 162, 202, 242)

### `/api/storage` (POST)
- **Función**: `api_add_storage` (Línea 25635 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\Caja-metalmask.js` (Línea/s: 51, 52, 77)
  - `app\static\js\MetalMask.js` (Línea/s: 56, 58, 62, 68, 98)
  - `app\py\Backend metal mask.py` (Línea/s: 162, 202, 242)

### `/api/storage/<int:storage_id>` (PUT)
- **Función**: `api_update_storage` (Línea 25676 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\Caja-metalmask.js` (Línea/s: 51, 52, 77)
  - `app\static\js\MetalMask.js` (Línea/s: 56, 58, 62, 68, 98)
  - `app\py\Backend metal mask.py` (Línea/s: 162, 202, 242)

### `/api/bom-smt-data` (GET)
- **Función**: `api_bom_smt_data` (Línea 25716 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\control-operacion-smt-ajax.js` (Línea/s: 2307)

### `/historial-vision` (GET)
- **Función**: `historial_vision` (Línea 27084 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 92, 97)
  - `app\static\js\scriptMain.js` (Línea/s: 4588, 4821)

### `/historial-vision-ajax` (GET)
- **Función**: `historial_vision` (Línea 27085 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 92)
  - `app\static\js\scriptMain.js` (Línea/s: 4588)

### `/historial-vision-pass-fail` (GET)
- **Función**: `historial_vision_pass_fail` (Línea 27096 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 97)
  - `app\static\js\scriptMain.js` (Línea/s: 4821)

### `/historial-vision-pass-fail-ajax` (GET)
- **Función**: `historial_vision_pass_fail` (Línea 27097 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 97)
  - `app\static\js\scriptMain.js` (Línea/s: 4821)

### `/api/vision/data` (GET)
- **Función**: `vision_data_api` (Línea 27108 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\history_vision.js` (Línea/s: 276)

### `/api/vision/pass-fail-summary` (GET)
- **Función**: `vision_pass_fail_summary_api` (Línea 27140 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\history_vision_pass_fail.js` (Línea/s: 174, 275)

### `/api/vision/pass-fail-summary/export` (GET)
- **Función**: `export_vision_pass_fail_summary_excel` (Línea 27176 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\history_vision_pass_fail.js` (Línea/s: 275)

### `/api/vision/image-info` (GET)
- **Función**: `vision_image_info_api` (Línea 27278 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\history_vision.js` (Línea/s: 611)

### `/api/vision/export` (GET)
- **Función**: `export_vision_excel` (Línea 27388 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\history_vision.js` (Línea/s: 358)

### `/historial-ict` (GET)
- **Función**: `ict_front_full_defects2` (Línea 27475 en `routes.py`)
- **Referencias encontradas**:
  - `app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html` (Línea/s: 75)
  - `app\static\js\scriptMain.js` (Línea/s: 4480)

### `/api/ict/data` (GET)
- **Función**: `ict_data_api` (Línea 27487 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\ict.js` (Línea/s: 191)

### `/api/ict/defects` (GET)
- **Función**: `ict_defects_api` (Línea 27597 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\ict.js` (Línea/s: 437, 557)

### `/api/ict/export` (GET)
- **Función**: `export_ict_excel` (Línea 27621 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\ict.js` (Línea/s: 716, 747, 756)

### `/api/ict/export-defects` (GET)
- **Función**: `export_ict_defects_excel` (Línea 27766 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\ict.js` (Línea/s: 756)

### `/api/ict/export-compare` (POST)
- **Función**: `export_ict_compare_excel` (Línea 27908 en `routes.py`)
- **Referencias encontradas**:
  - `app\static\js\ict.js` (Línea/s: 716)

