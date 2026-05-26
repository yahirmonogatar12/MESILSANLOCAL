# 🔍 Verificación Exhaustiva de Rutas Huérfanas (v3)

Auditoría **una por una** de las 346 rutas del sistema usando 5 estrategias de detección calibradas:

1. **url_for()** — Referencia directa con nombre de función
2. **Path estático** — Coincidencia exacta del path en archivos frontend
3. **Multi-segmento** — Segmentos estáticos de ruta dinámica en misma línea con contexto de URL
4. **Función Python** — Nombre de función referenciado en otro archivo .py
5. **Template literal** — Regex para interpolaciones JS tipo `${variable}`

---

## Resumen

| Métrica | Valor |
| :--- | :--- |
| Rutas analizadas | 346 |
| Rutas en uso confirmadas | 268 (77.5%) |
| Rutas huérfanas confirmadas | 78 (22.5%) |

---

## 🚫 Rutas Huérfanas (Sin uso detectado)

Estas rutas **no fueron encontradas** por ninguna de las 5 estrategias de detección en los 187 archivos frontend ni en los 34 archivos Python del proyecto.

| # | Línea | Ruta | Métodos | Función |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 218 | `/api/health` | `GET` | `api_health` |
| 2 | 252 | `/smt-simple` | `GET` | `smt_simple` |
| 3 | 1055 | `/favicon.eco` | `GET` | `favicon` |
| 4 | 1065 | `/sistemas` | `GET` | `sistemas` |
| 5 | 1083 | `/documentacion` | `GET` | `documentacion` |
| 6 | 5022 | `/api/plan-imd/batch-update` | `POST` | `api_plan_imd_batch_update` |
| 7 | 5866 | `/api/plan-smt/batch-update` | `POST` | `api_plan_smt_batch_update` |
| 8 | 6755 | `/consultar_bom` | `GET` | `consultar_bom` |
| 9 | 7498 | `/api/ecos/<int:eco_id>/items/import` | `POST` | `api_ecos_import_items` |
| 10 | 7574 | `/buscar_material_por_numero_parte` | `GET` | `buscar_material_por_numero_parte` |
| 11 | 7927 | `/guardar_entrada_aereo` | `POST` | `guardar_entrada_aereo` |
| 12 | 7955 | `/listar_entradas_aereo` | `GET` | `listar_entradas_aereo` |
| 13 | 8683 | `/obtener_codigos_material` | `GET` | `obtener_codigos_material` |
| 14 | 8843 | `/guardar_control_almacen` | `POST` | `guardar_control_almacen` |
| 15 | 8876 | `/obtener_secuencial_lote_interno` | `POST` | `obtener_secuencial_lote_interno` |
| 16 | 8939 | `/consultar_control_almacen` | `GET` | `consultar_control_almacen` |
| 17 | 9020 | `/actualizar_control_almacen` | `POST` | `actualizar_control_almacen` |
| 18 | 9206 | `/guardar_cliente_seleccionado` | `POST` | `guardar_cliente_seleccionado` |
| 19 | 9231 | `/cargar_cliente_seleccionado` | `GET` | `cargar_cliente_seleccionado` |
| 20 | 9247 | `/actualizar_estado_desecho_almacen` | `POST` | `actualizar_estado_desecho_almacen` |
| 21 | 9308 | `/obtener_siguiente_secuencial` | `GET` | `obtener_siguiente_secuencial` |
| 22 | 9804 | `/api/generar-plan-smd` | `POST` | `api_generar_plan_smd` |
| 23 | 14455 | `/api/almacen-embarques/departures/history` | `GET` | `api_almacen_embarques_departure_history` |
| 24 | 17065 | `/api/ict/param-changes/detail` | `GET` | `ict_param_changes_detail` |
| 25 | 17249 | `/consultar_especificacion_por_numero_parte` | `GET` | `consultar_especificacion_por_numero_parte` |
| 26 | 17398 | `/material/control_calidad` | `GET` | `material_control_calidad` |
| 27 | 17543 | `/obtener_reglas_escaneo` | `GET` | `obtener_reglas_escaneo` |
| 28 | 17564 | `/buscar_codigo_recibido` | `GET` | `buscar_codigo_recibido` |
| 29 | 17619 | `/guardar_salida_lote` | `POST` | `guardar_salida_lote` |
| 30 | 17736 | `/consultar_historial_salidas` | `GET` | `consultar_historial_salidas` |
| 31 | 17887 | `/buscar_material_por_codigo` | `GET` | `buscar_material_por_codigo` |
| 32 | 17975 | `/verificar_stock_rapido` | `GET` | `verificar_stock_rapido` |
| 33 | 18047 | `/procesar_salida_material` | `POST` | `procesar_salida_material` |
| 34 | 18202 | `/forzar_actualizacion_inventario/<numero_parte>` | `POST` | `forzar_actualizacion_inventario` |
| 35 | 18291 | `/recalcular_inventario_general` | `POST` | `recalcular_inventario_general_endpoint` |
| 36 | 18355 | `/obtener_inventario_general` | `GET` | `obtener_inventario_general_endpoint` |
| 37 | 18372 | `/verificar_estado_inventario` | `GET` | `verificar_estado_inventario` |
| 38 | 18451 | `/test_modelos` | `GET` | `test_modelos` |
| 39 | 19506 | `/csv-viewer` | `GET` | `csv_viewer` |
| 40 | 19662 | `/api/csv_stats` | `GET` | `get_csv_stats` |
| 41 | 19911 | `/api/filter_data` | `POST` | `filter_csv_data` |
| 42 | 20170 | `/guardar_regla_trazabilidad` | `POST` | `guardar_regla_trazabilidad` |
| 43 | 20289 | `/control_salida/estado` | `GET` | `control_salida_estado` |
| 44 | 20347 | `/control_salida/configuracion` | `GET, POST` | `control_salida_configuracion` |
| 45 | 20407 | `/control_salida/validar_stock` | `POST` | `control_salida_validar_stock` |
| 46 | 20481 | `/control_salida/reporte_diario` | `GET` | `control_salida_reporte_diario` |
| 47 | 20923 | `/control_salida/debug/test_connection` | `GET` | `control_salida_test_connection` |
| 48 | 21002 | `/importar_excel_almacen` | `POST` | `importar_excel_almacen` |
| 49 | 21162 | `/material/longterm_inventory` | `GET` | `material_longterm_inventory` |
| 50 | 21186 | `/importar_excel_salida` | `POST` | `importar_excel_salida` |
| 51 | 21298 | `/importar_excel_retorno` | `POST` | `importar_excel_retorno` |
| 52 | 23423 | `/ajuste-numero-parte-ajax` | `GET` | `ajuste_numero_parte_ajax` |
| 53 | 23430 | `/consultar-peps-ajax` | `GET` | `consultar_peps_ajax` |
| 54 | 23437 | `/control-entrada-salida-material-ajax` | `GET` | `control_entrada_salida_material_ajax` |
| 55 | 23446 | `/control-recibo-refacciones-ajax` | `GET` | `control_recibo_refacciones_ajax` |
| 56 | 23453 | `/control-salida-refacciones-ajax` | `GET` | `control_salida_refacciones_ajax` |
| 57 | 23460 | `/control-total-material-ajax` | `GET` | `control_total_material_ajax` |
| 58 | 23467 | `/estandares-refacciones-ajax` | `GET` | `estandares_refacciones_ajax` |
| 59 | 23474 | `/estatus-inventario-refacciones-ajax` | `GET` | `estatus_inventario_refacciones_ajax` |
| 60 | 23483 | `/estatus-material-ajax` | `GET` | `estatus_material_ajax` |
| 61 | 23490 | `/estatus-material-msl-ajax` | `GET` | `estatus_material_msl_ajax` |
| 62 | 23497 | `/historial-inventario-real-ajax` | `GET` | `historial_inventario_real_ajax` |
| 63 | 23504 | `/inventario-rollos-smd-ajax` | `GET` | `inventario_rollos_smd_ajax` |
| 64 | 23511 | `/longterm-inventory-ajax` | `GET` | `longterm_inventory_ajax` |
| 65 | 23518 | `/material-sustituto-ajax` | `GET` | `material_sustituto_ajax` |
| 66 | 23525 | `/recibo-pago-material-ajax` | `GET` | `recibo_pago_material_ajax` |
| 67 | 23532 | `/registro-material-real-ajax` | `GET` | `registro_material_real_ajax` |
| 68 | 23819 | `/api/snapshot_inventario/trigger` | `POST` | `api_snapshot_inv_trigger` |
| 69 | 23846 | `/mysql-proxy.php` | `POST, GET, OPTIONS` | `mysql_proxy_php` |
| 70 | 23954 | `/api/status` | `GET` | `api_status` |
| 71 | 24517 | `/api/mysql/usuario-actual` | `GET` | `api_mysql_usuario_actual` |
| 72 | 25189 | `/api/plan-run/pause` | `POST` | `api_plan_run_pause` |
| 73 | 25231 | `/api/plan-run/resume` | `POST` | `api_plan_run_resume` |
| 74 | 25272 | `/api/plan-run/status` | `GET` | `api_plan_run_status` |
| 75 | 25428 | `/control/metal-mask` | `GET` | `pagina_control_metal_mask` |
| 76 | 25438 | `/control/metal-mask/caja` | `GET` | `pagina_control_caja_metal_mask` |
| 77 | 27322 | `/api/vision/image-file` | `GET` | `vision_image_file_api` |
| 78 | 27476 | `/ict/front-full-defects2` | `GET` | `ict_front_full_defects2` |

---

## ✅ Rutas En Uso (con evidencia)

### `/` (GET)
- **Función**: `index` (Línea 585)
- **Evidencia**: Función 'index' en app\db_mysql.py

### `/login` (GET, POST)
- **Función**: `login` (Línea 590)
- **Evidencia**: url_for('login') en app\templates\landing.html

### `/inicio` (GET)
- **Función**: `inicio` (Línea 733)
- **Evidencia**: url_for('inicio') en app\templates\login.html

### `/api/mi-perfil` (GET, POST)
- **Función**: `api_mi_perfil` (Línea 739)
- **Evidencia**: Path exacto '/api/mi-perfil' en app\templates\landing.html

### `/calendario` (GET)
- **Función**: `calendario` (Línea 1035)
- **Evidencia**: Path exacto '/calendario' en app\templates\landing.html

### `/defect-management` (GET)
- **Función**: `defect_management` (Línea 1042)
- **Evidencia**: Path exacto '/defect-management' en app\templates\landing.html

### `/soporte` (GET)
- **Función**: `soporte` (Línea 1072)
- **Evidencia**: Path exacto '/soporte' en app\templates\landing.html

### `/ILSAN-ELECTRONICS` (GET)
- **Función**: `material` (Línea 1094)
- **Evidencia**: url_for interno en routes.py L703

### `/dashboard` (GET)
- **Función**: `dashboard` (Línea 1139)
- **Evidencia**: Path exacto '/dashboard' en app\static\js\control-cuchillas-corte.js

### `/logout` (GET)
- **Función**: `logout` (Línea 1173)
- **Evidencia**: Path exacto '/logout' en app\templates\landing.html

### `/front-plan/static/<path:filename>` (GET)
- **Función**: `front_plan_static` (Línea 1201)
- **Evidencia**: Path limpio '/front-plan/static' en app\static\js\index-functions.js

### `/plan-main` (GET)
- **Función**: `view_plan_main` (Línea 1210)
- **Evidencia**: Path exacto '/plan-main' en app\templates\Control de proceso\Control de operacion de linea Main.html

### `/control-main` (GET)
- **Función**: `view_control_main` (Línea 1217)
- **Evidencia**: Path exacto '/control-main' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/plan-main-assy-ajax` (GET)
- **Función**: `plan_main_assy_ajax` (Línea 1225)
- **Evidencia**: Path exacto '/plan-main-assy-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/plan-main-imd-ajax` (GET)
- **Función**: `plan_main_imd_ajax` (Línea 1234)
- **Evidencia**: Path exacto '/plan-main-imd-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/plan-main-smt-ajax` (GET)
- **Función**: `plan_main_smt_ajax` (Línea 1243)
- **Evidencia**: Path exacto '/plan-main-smt-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/control-operacion-linea-main-ajax` (GET)
- **Función**: `ctrl_operacion_linea_main_ajax` (Línea 1252)
- **Evidencia**: Path exacto '/control-operacion-linea-main-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/api/plan` (GET)
- **Función**: `api_plan_list` (Línea 3545)
- **Evidencia**: Path exacto '/api/plan' en app\templates\Control de proceso\Control de operacion de linea SMT.html

### `/api/plan/input-main/scan-lots` (GET)
- **Función**: `api_plan_input_main_scan_lots` (Línea 3610)
- **Evidencia**: Path exacto '/api/plan/input-main/scan-lots' en app\static\js\plan.js

### `/api/plan/input-main/assign-lot` (POST)
- **Función**: `api_plan_input_main_assign_lot` (Línea 3746)
- **Evidencia**: Path exacto '/api/plan/input-main/assign-lot' en app\static\js\plan.js

### `/api/plan/input-main/create-plan` (POST)
- **Función**: `api_plan_input_main_create_plan` (Línea 3963)
- **Evidencia**: Path exacto '/api/plan/input-main/create-plan' en app\static\js\plan.js

### `/api/plan` (POST)
- **Función**: `api_plan_create` (Línea 4119)
- **Evidencia**: Path exacto '/api/plan' en app\templates\Control de proceso\Control de operacion de linea SMT.html

### `/api/plan/update` (POST)
- **Función**: `api_plan_update` (Línea 4258)
- **Evidencia**: Path exacto '/api/plan/update' en app\static\js\plan.js

### `/api/raw/search` (GET)
- **Función**: `api_raw_search` (Línea 4313)
- **Evidencia**: Path exacto '/api/raw/search' en app\static\js\plan.js

### `/api/plan/status` (POST)
- **Función**: `api_plan_status` (Línea 4367)
- **Evidencia**: Path exacto '/api/plan/status' en app\static\js\plan-main-loader.js

### `/api/plan/save-sequences` (POST)
- **Función**: `api_plan_save_sequences` (Línea 4515)
- **Evidencia**: Path exacto '/api/plan/save-sequences' en app\static\js\plan.js

### `/api/plan/pending` (GET)
- **Función**: `api_plan_pending` (Línea 4565)
- **Evidencia**: Path exacto '/api/plan/pending' en app\static\js\plan.js

### `/api/plan/reschedule` (POST)
- **Función**: `api_plan_reschedule` (Línea 4631)
- **Evidencia**: Path exacto '/api/plan/reschedule' en app\static\js\plan.js

### `/api/plan/export-excel` (POST)
- **Función**: `api_plan_export_excel` (Línea 4786)
- **Evidencia**: Path exacto '/api/plan/export-excel' en app\static\js\plan.js

### `/api/plan-imd` (GET)
- **Función**: `api_plan_imd_list` (Línea 4875)
- **Evidencia**: Path exacto '/api/plan-imd' en app\static\js\plan_imd.js

### `/api/plan-imd` (POST)
- **Función**: `api_plan_imd_create` (Línea 4942)
- **Evidencia**: Path exacto '/api/plan-imd' en app\static\js\plan_imd.js

### `/api/plan-imd/update` (POST)
- **Función**: `api_plan_imd_update` (Línea 5064)
- **Evidencia**: Path exacto '/api/plan-imd/update' en app\static\js\plan_imd.js

### `/api/plan-imd/save-sequences` (POST)
- **Función**: `api_plan_imd_save_sequences` (Línea 5113)
- **Evidencia**: Path exacto '/api/plan-imd/save-sequences' en app\static\js\plan_imd.js

### `/api/plan-imd/pending` (GET)
- **Función**: `api_plan_imd_pending` (Línea 5164)
- **Evidencia**: Path exacto '/api/plan-imd/pending' en app\static\js\plan_imd.js

### `/api/plan-imd/pending-reschedule` (GET)
- **Función**: `api_plan_imd_pending_reschedule` (Línea 5218)
- **Evidencia**: Path exacto '/api/plan-imd/pending-reschedule' en app\static\js\plan_imd.js

### `/api/plan-imd/reschedule` (POST)
- **Función**: `api_plan_imd_reschedule` (Línea 5268)
- **Evidencia**: Path exacto '/api/plan-imd/reschedule' en app\static\js\plan_imd.js

### `/api/plan-imd/export-excel` (POST)
- **Función**: `api_plan_imd_export_excel` (Línea 5377)
- **Evidencia**: Path exacto '/api/plan-imd/export-excel' en app\static\js\plan_imd.js

### `/api/plan-imd/import-excel` (POST)
- **Función**: `api_plan_imd_import_excel` (Línea 5462)
- **Evidencia**: Path exacto '/api/plan-imd/import-excel' en app\static\js\plan_imd.js

### `/api/plan-smt` (GET)
- **Función**: `api_plan_smt_list` (Línea 5721)
- **Evidencia**: Path exacto '/api/plan-smt' en app\static\js\plan_smt.js

### `/api/plan-smt` (POST)
- **Función**: `api_plan_smt_create` (Línea 5788)
- **Evidencia**: Path exacto '/api/plan-smt' en app\static\js\plan_smt.js

### `/api/plan-smt/update` (POST)
- **Función**: `api_plan_smt_update` (Línea 5900)
- **Evidencia**: Path exacto '/api/plan-smt/update' en app\static\js\plan_smt.js

### `/api/plan-smt/save-sequences` (POST)
- **Función**: `api_plan_smt_save_sequences` (Línea 5942)
- **Evidencia**: Path exacto '/api/plan-smt/save-sequences' en app\static\js\plan_smt.js

### `/api/plan-smt/pending` (GET)
- **Función**: `api_plan_smt_pending` (Línea 5993)
- **Evidencia**: Path exacto '/api/plan-smt/pending' en app\static\js\plan_smt.js

### `/api/plan-smt/reschedule` (POST)
- **Función**: `api_plan_smt_reschedule` (Línea 6043)
- **Evidencia**: Path exacto '/api/plan-smt/reschedule' en app\static\js\plan_smt.js

### `/api/plan-smt/export-excel` (POST)
- **Función**: `api_plan_smt_export_excel` (Línea 6145)
- **Evidencia**: Path exacto '/api/plan-smt/export-excel' en app\static\js\plan_smt.js

### `/api/plan-smt/import-excel` (POST)
- **Función**: `api_plan_smt_import_excel` (Línea 6222)
- **Evidencia**: Path exacto '/api/plan-smt/import-excel' en app\static\js\plan_smt.js

### `/api/plan-main/list` (GET)
- **Función**: `api_plan_main_list` (Línea 6425)
- **Evidencia**: Path exacto '/api/plan-main/list' en app\static\js\plan-main-loader.js

### `/api/work-orders/import` (POST)
- **Función**: `api_work_orders_import` (Línea 6493)
- **Evidencia**: Path exacto '/api/work-orders/import' en app\static\js\plan.js

### `/cargar_template` (POST)
- **Función**: `cargar_template` (Línea 6657)
- **Evidencia**: Path exacto '/cargar_template' en app\templates\MainTemplate.html

### `/importar_excel_bom` (POST)
- **Función**: `importar_excel_bom` (Línea 6682)
- **Evidencia**: Path exacto '/importar_excel_bom' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/listar_modelos_bom` (GET)
- **Función**: `listar_modelos_bom` (Línea 6720)
- **Evidencia**: Path exacto '/listar_modelos_bom' en app\templates\MainTemplate.html

### `/listar_bom` (POST)
- **Función**: `listar_bom` (Línea 6736)
- **Evidencia**: Path exacto '/listar_bom' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/ecos` (GET)
- **Función**: `api_ecos_list` (Línea 6809)
- **Evidencia**: Path exacto '/api/ecos' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/ecos/export` (GET)
- **Función**: `api_ecos_export` (Línea 6867)
- **Evidencia**: Path exacto '/api/ecos/export' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/ecos/<int:eco_id>` (GET)
- **Función**: `api_ecos_detail` (Línea 6958)
- **Evidencia**: Path limpio '/api/ecos' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/ecn-ks/<int:hist_seq>` (GET)
- **Función**: `api_ecn_ks_detail` (Línea 6975)
- **Evidencia**: Path limpio '/api/ecn-ks' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/ecos` (POST)
- **Función**: `api_ecos_create` (Línea 6991)
- **Evidencia**: Path exacto '/api/ecos' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/bom/download-excel` (GET)
- **Función**: `api_bom_download_excel` (Línea 7039)
- **Evidencia**: Path exacto '/api/bom/download-excel' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/bom/resolve-family` (GET)
- **Función**: `api_bom_resolve_family` (Línea 7103)
- **Evidencia**: Path exacto '/api/bom/resolve-family' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/bom/download-excel-family` (GET)
- **Función**: `api_bom_download_excel_family` (Línea 7221)
- **Evidencia**: Path exacto '/api/bom/download-excel-family' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/ecos/from-excel` (POST)
- **Función**: `api_ecos_from_excel` (Línea 7254)
- **Evidencia**: Path exacto '/api/ecos/from-excel' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/ecos/from-excel-family` (POST)
- **Función**: `api_ecos_from_excel_family` (Línea 7332)
- **Evidencia**: Path exacto '/api/ecos/from-excel-family' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/ecos/<int:eco_id>/scope` (GET)
- **Función**: `api_ecos_scope` (Línea 7442)
- **Evidencia**: Confirmado en uso por el usuario

### `/api/ecos/<int:eco_id>/diff` (GET)
- **Función**: `api_ecos_diff` (Línea 7455)
- **Evidencia**: Multi-segmento ['/api/ecos/', '/diff'] en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html: 'const response = await fetch(`/api/ecos/${ecoId}/diff`);'

### `/api/ecos/<int:eco_id>/approve` (POST)
- **Función**: `api_ecos_approve` (Línea 7521)
- **Evidencia**: Multi-segmento ['/api/ecos/', '/approve'] en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html: 'const response = await fetch(`/api/ecos/${ecoActualId}/approve`, { method: 'POST' });'

### `/api/ecos/<int:eco_id>/cancel` (POST)
- **Función**: `api_ecos_cancel` (Línea 7541)
- **Evidencia**: Confirmado en uso por el usuario

### `/api/ecos/<int:eco_id>` (DELETE)
- **Función**: `api_ecos_delete` (Línea 7558)
- **Evidencia**: Path limpio '/api/ecos' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/exportar_excel_bom` (GET)
- **Función**: `exportar_excel_bom` (Línea 7716)
- **Evidencia**: Path exacto '/exportar_excel_bom' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/bom/update` (POST)
- **Función**: `api_bom_update` (Línea 7763)
- **Evidencia**: Path exacto '/api/bom/update' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/api/bom/update-posiciones-assy` (POST)
- **Función**: `api_bom_update_posiciones_assy` (Línea 7852)
- **Evidencia**: Path exacto '/api/bom/update-posiciones-assy' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/guardar_material` (POST)
- **Función**: `guardar_material_route` (Línea 7966)
- **Evidencia**: Path exacto '/guardar_material' en app\static\js\material-edit-drawer.js

### `/listar_materiales` (GET)
- **Función**: `listar_materiales` (Línea 8007)
- **Evidencia**: Path exacto '/listar_materiales' en app\templates\INFORMACION BASICA\CONTROL_DE_MATERIAL.html

### `/api/inventario/lotes_detalle` (POST)
- **Función**: `consultar_lotes_detalle` (Línea 8022)
- **Evidencia**: Path exacto '/api/inventario/lotes_detalle' en app\static\js\Registro_de_material_real.js

### `/importar_excel` (POST)
- **Función**: `importar_excel` (Línea 8168)
- **Evidencia**: Path exacto '/importar_excel' en app\templates\Control de material\Estatus de material.html

### `/actualizar_campo_material` (POST)
- **Función**: `actualizar_campo_material` (Línea 8483)
- **Evidencia**: Path exacto '/actualizar_campo_material' en app\templates\INFORMACION BASICA\CONTROL_DE_MATERIAL.html

### `/actualizar_material_completo` (POST)
- **Función**: `actualizar_material_completo_route` (Línea 8545)
- **Evidencia**: Path exacto '/actualizar_material_completo' en app\static\js\material-edit-drawer.js

### `/exportar_excel` (GET)
- **Función**: `exportar_excel` (Línea 8584)
- **Evidencia**: Path exacto '/exportar_excel' en app\templates\INFORMACION BASICA\CONTROL_DE_BOM.html

### `/control_calidad` (GET)
- **Función**: `control_calidad` (Línea 8837)
- **Evidencia**: Path exacto '/control_calidad' en app\templates\MainTemplate.html

### `/informacion_basica/control_de_material` (GET)
- **Función**: `control_de_material_ajax` (Línea 9445)
- **Evidencia**: Path exacto '/informacion_basica/control_de_material' en app\templates\MainTemplate.html

### `/informacion_basica/control_de_bom` (GET)
- **Función**: `control_de_bom_ajax` (Línea 9456)
- **Evidencia**: Path exacto '/informacion_basica/control_de_bom' en app\templates\MainTemplate.html

### `/listas/informacion_basica` (GET)
- **Función**: `lista_informacion_basica` (Línea 9474)
- **Evidencia**: Path exacto '/listas/informacion_basica' en app\templates\MainTemplate.html

### `/listas/control_material` (GET)
- **Función**: `lista_control_material` (Línea 9485)
- **Evidencia**: Path exacto '/listas/control_material' en app\templates\MainTemplate.html

### `/listas/control_produccion` (GET)
- **Función**: `lista_control_produccion` (Línea 9496)
- **Evidencia**: Path exacto '/listas/control_produccion' en app\templates\MainTemplate.html

### `/control_produccion/control_embarque` (GET)
- **Función**: `control_embarque` (Línea 9507)
- **Evidencia**: Path exacto '/control_produccion/control_embarque' en app\templates\MainTemplate.html

### `/Control de embarque` (GET)
- **Función**: `control_embarque_ajax` (Línea 9518)
- **Evidencia**: Path exacto '/Control de embarque' en app\templates\MainTemplate.html

### `/control_produccion/crear_plan` (GET)
- **Función**: `crear_plan_produccion` (Línea 9529)
- **Evidencia**: Path exacto '/control_produccion/crear_plan' en app\templates\MainTemplate.html

### `/control_produccion/plan_smt` (GET)
- **Función**: `plan_smt_ajax` (Línea 9546)
- **Evidencia**: Path exacto '/control_produccion/plan_smt' en app\templates\MainTemplate.html

### `/api/work-orders` (GET)
- **Función**: `api_work_orders` (Línea 9597)
- **Evidencia**: Path exacto '/api/work-orders' en app\static\js\plan-smd-module.js

### `/api/inventario/modelo/<codigo_modelo>` (GET)
- **Función**: `api_inventario_modelo` (Línea 9701)
- **Evidencia**: Path limpio '/api/inventario/modelo' en app\static\js\plan-smd-module.js

### `/api/plan-smd` (POST)
- **Función**: `api_plan_smd_guardar` (Línea 9745)
- **Evidencia**: Path exacto '/api/plan-smd' en app\templates\Control de proceso\Control de operacion de linea SMT.html

### `/control_proceso/control_produccion_smt` (GET)
- **Función**: `control_produccion_smt_ajax` (Línea 10062)
- **Evidencia**: Path exacto '/control_proceso/control_produccion_smt' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/control-bom-ajax` (GET)
- **Función**: `control_bom_ajax` (Línea 10077)
- **Evidencia**: Path exacto '/control-bom-ajax' en app\static\js\scriptMain.js

### `/crear-plan-micom-ajax` (GET)
- **Función**: `crear_plan_micom_ajax` (Línea 10100)
- **Evidencia**: Path exacto '/crear-plan-micom-ajax' en app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html

### `/control-operacion-linea-smt-ajax` (GET)
- **Función**: `control_operacion_linea_smt_ajax` (Línea 10111)
- **Evidencia**: Path exacto '/control-operacion-linea-smt-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/control-impresion-identificacion-smt-ajax` (GET)
- **Función**: `control_impresion_identificacion_smt_ajax` (Línea 10127)
- **Evidencia**: Path exacto '/control-impresion-identificacion-smt-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/control-registro-identificacion-smt-ajax` (GET)
- **Función**: `control_registro_identificacion_smt_ajax` (Línea 10142)
- **Evidencia**: Path exacto '/control-registro-identificacion-smt-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/historial-operacion-proceso-ajax` (GET)
- **Función**: `historial_operacion_proceso_ajax` (Línea 10157)
- **Evidencia**: Path exacto '/historial-operacion-proceso-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/bom-management-process-ajax` (GET)
- **Función**: `bom_management_process_ajax` (Línea 10170)
- **Evidencia**: Path exacto '/bom-management-process-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/reporte-diario-inspeccion-smt-ajax` (GET)
- **Función**: `reporte_diario_inspeccion_smt_ajax` (Línea 10181)
- **Evidencia**: Path exacto '/reporte-diario-inspeccion-smt-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/control-diario-inspeccion-smt-ajax` (GET)
- **Función**: `control_diario_inspeccion_smt_ajax` (Línea 10194)
- **Evidencia**: Path exacto '/control-diario-inspeccion-smt-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/reporte-diario-inspeccion-proceso-ajax` (GET)
- **Función**: `reporte_diario_inspeccion_proceso_ajax` (Línea 10207)
- **Evidencia**: Path exacto '/reporte-diario-inspeccion-proceso-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/control-unidad-empaque-modelo-ajax` (GET)
- **Función**: `control_unidad_empaque_modelo_ajax` (Línea 10222)
- **Evidencia**: Path exacto '/control-unidad-empaque-modelo-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/packaging-register-management-ajax` (GET)
- **Función**: `packaging_register_management_ajax` (Línea 10235)
- **Evidencia**: Path exacto '/packaging-register-management-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/search-packaging-history-ajax` (GET)
- **Función**: `search_packaging_history_ajax` (Línea 10248)
- **Evidencia**: Path exacto '/search-packaging-history-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/shipping-register-management-ajax` (GET)
- **Función**: `shipping_register_management_ajax` (Línea 10259)
- **Evidencia**: Path exacto '/shipping-register-management-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/search-shipping-history-ajax` (GET)
- **Función**: `search_shipping_history_ajax` (Línea 10272)
- **Evidencia**: Path exacto '/search-shipping-history-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/almacen-embarques-entradas-ajax` (GET)
- **Función**: `almacen_embarques_entradas_ajax` (Línea 13985)
- **Evidencia**: Path exacto '/almacen-embarques-entradas-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/control-salida-lineas-ajax` (GET)
- **Función**: `control_salida_lineas_ajax` (Línea 13998)
- **Evidencia**: Path exacto '/control-salida-lineas-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/almacen-embarques-salidas-ajax` (GET)
- **Función**: `almacen_embarques_salidas_ajax` (Línea 14009)
- **Evidencia**: Path exacto '/almacen-embarques-salidas-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/almacen-embarques-retorno-ajax` (GET)
- **Función**: `almacen_embarques_retorno_ajax` (Línea 14022)
- **Evidencia**: Path exacto '/almacen-embarques-retorno-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/almacen-embarques-movimientos-ajax` (GET)
- **Función**: `almacen_embarques_movimientos_ajax` (Línea 14039)
- **Evidencia**: Path exacto '/almacen-embarques-movimientos-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/almacen-embarques-inventario-general-ajax` (GET)
- **Función**: `almacen_embarques_inventario_general_ajax` (Línea 14052)
- **Evidencia**: Path exacto '/almacen-embarques-inventario-general-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/almacen-embarques-catalogo-ajax` (GET)
- **Función**: `almacen_embarques_catalogo_ajax` (Línea 14067)
- **Evidencia**: Path exacto '/almacen-embarques-catalogo-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/api/almacen-embarques/entradas` (GET)
- **Función**: `api_almacen_embarques_entradas` (Línea 14084)
- **Evidencia**: Path exacto '/api/almacen-embarques/entradas' en app\static\js\almacen_embarques_history.js

### `/api/control-salida-lineas` (GET)
- **Función**: `api_control_salida_lineas` (Línea 14095)
- **Evidencia**: Path exacto '/api/control-salida-lineas' en app\static\js\control_salida_lineas.js

### `/api/control-salida-lineas/export` (GET)
- **Función**: `export_control_salida_lineas` (Línea 14108)
- **Evidencia**: Path exacto '/api/control-salida-lineas/export' en app\static\js\control_salida_lineas.js

### `/api/almacen-embarques/entradas/export` (GET)
- **Función**: `export_almacen_embarques_entradas` (Línea 14133)
- **Evidencia**: Path exacto '/api/almacen-embarques/entradas/export' en app\static\js\almacen_embarques_history.js

### `/api/almacen-embarques/salidas` (GET)
- **Función**: `api_almacen_embarques_salidas` (Línea 14163)
- **Evidencia**: Path exacto '/api/almacen-embarques/salidas' en app\static\js\almacen_embarques_history.js

### `/api/almacen-embarques/salidas/export` (GET)
- **Función**: `export_almacen_embarques_salidas` (Línea 14174)
- **Evidencia**: Path exacto '/api/almacen-embarques/salidas/export' en app\static\js\almacen_embarques_history.js

### `/api/almacen-embarques/<module_name>/ajustes/template` (GET)
- **Función**: `api_almacen_embarques_ajustes_template` (Línea 14205)
- **Evidencia**: Multi-segmento ['/api/almacen-embarques/', '/ajustes/template'] en app\static\js\almacen_embarques_history.js: 'window.open(`/api/almacen-embarques/${config.adjustmentModule}/ajustes/template`, "_blank");'

### `/api/almacen-embarques/<module_name>/ajustes/preview` (POST)
- **Función**: `api_almacen_embarques_ajustes_preview` (Línea 14234)
- **Evidencia**: Multi-segmento ['/api/almacen-embarques/', '/ajustes/preview'] en app\static\js\almacen_embarques_history.js: 'const response = await fetch(`/api/almacen-embarques/${config.adjustmentModule}/ajustes/preview`, {'

### `/api/almacen-embarques/<module_name>/ajustes/confirm` (POST)
- **Función**: `api_almacen_embarques_ajustes_confirm` (Línea 14325)
- **Evidencia**: Multi-segmento ['/api/almacen-embarques/', '/ajustes/confirm'] en app\static\js\almacen_embarques_history.js: 'const response = await fetch(`/api/almacen-embarques/${config.adjustmentModule}/ajustes/confirm`, {'

### `/api/almacen-embarques/<module_name>/ajustes/manual` (POST)
- **Función**: `api_almacen_embarques_ajustes_manual` (Línea 14345)
- **Evidencia**: Multi-segmento ['/api/almacen-embarques/', '/ajustes/manual'] en app\static\js\almacen_embarques_history.js: 'const response = await fetch(`/api/almacen-embarques/${config.adjustmentModule}/ajustes/manual`, {'

### `/api/almacen-embarques/<module_name>/ajustes/cancel` (POST)
- **Función**: `api_almacen_embarques_ajustes_cancel` (Línea 14367)
- **Evidencia**: Multi-segmento ['/api/almacen-embarques/', '/ajustes/cancel'] en app\static\js\almacen_embarques_history.js: 'await fetch(`/api/almacen-embarques/${config.adjustmentModule}/ajustes/cancel`, {'

### `/api/almacen-embarques/salidas/<int:exit_id>/departure` (POST, PUT, PATCH)
- **Función**: `assign_almacen_embarques_departure` (Línea 14426)
- **Evidencia**: Multi-segmento ['/api/almacen-embarques/salidas/', '/departure'] en app\static\js\almacen_embarques_history.js: 'const response = await fetch(`/api/almacen-embarques/salidas/${assignmentPayload.exitId}/departure`, {'

### `/api/almacen-embarques/retorno` (GET)
- **Función**: `api_almacen_embarques_retorno` (Línea 14474)
- **Evidencia**: Path exacto '/api/almacen-embarques/retorno' en app\static\js\almacen_embarques_history.js

### `/api/almacen-embarques/retorno/export` (GET)
- **Función**: `export_almacen_embarques_retorno` (Línea 14485)
- **Evidencia**: Path exacto '/api/almacen-embarques/retorno/export' en app\static\js\almacen_embarques_history.js

### `/api/almacen-embarques/retorno/print-pdf` (POST)
- **Función**: `export_almacen_embarques_retorno_print_pdf` (Línea 14560)
- **Evidencia**: Path exacto '/api/almacen-embarques/retorno/print-pdf' en app\static\js\almacen_embarques_history.js

### `/api/almacen-embarques/movimientos` (GET)
- **Función**: `api_almacen_embarques_movimientos` (Línea 14587)
- **Evidencia**: Path exacto '/api/almacen-embarques/movimientos' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/movimientos/export` (GET)
- **Función**: `export_almacen_embarques_movimientos` (Línea 14605)
- **Evidencia**: Path exacto '/api/almacen-embarques/movimientos/export' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/movimientos/<movement_type>/<int:record_id>` (GET)
- **Función**: `api_almacen_embarques_movimiento_detalle` (Línea 14637)
- **Evidencia**: Path limpio '/api/almacen-embarques/movimientos' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/inventario-general` (GET)
- **Función**: `api_almacen_embarques_inventario_general` (Línea 14722)
- **Evidencia**: Path exacto '/api/almacen-embarques/inventario-general' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/catalogo` (GET)
- **Función**: `api_almacen_embarques_catalogo` (Línea 14736)
- **Evidencia**: Path exacto '/api/almacen-embarques/catalogo' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/catalogo` (POST)
- **Función**: `api_almacen_embarques_catalogo_create` (Línea 14749)
- **Evidencia**: Path exacto '/api/almacen-embarques/catalogo' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/catalogo/<int:catalog_id>` (PATCH)
- **Función**: `api_almacen_embarques_catalogo_update` (Línea 14763)
- **Evidencia**: Path limpio '/api/almacen-embarques/catalogo' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/catalogo/<int:catalog_id>` (DELETE)
- **Función**: `api_almacen_embarques_catalogo_delete` (Línea 14779)
- **Evidencia**: Path limpio '/api/almacen-embarques/catalogo' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/catalogo/export` (GET)
- **Función**: `export_almacen_embarques_catalogo` (Línea 14795)
- **Evidencia**: Path exacto '/api/almacen-embarques/catalogo/export' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/inventario-general/export` (GET)
- **Función**: `export_almacen_embarques_inventario_general` (Línea 14821)
- **Evidencia**: Path exacto '/api/almacen-embarques/inventario-general/export' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/inventario-general/cierre/bootstrap` (GET)
- **Función**: `api_almacen_embarques_inventario_cierre_bootstrap` (Línea 14852)
- **Evidencia**: Path exacto '/api/almacen-embarques/inventario-general/cierre/bootstrap' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/inventario-general/cierre/template` (GET)
- **Función**: `api_almacen_embarques_inventario_cierre_template` (Línea 14876)
- **Evidencia**: Path exacto '/api/almacen-embarques/inventario-general/cierre/template' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/inventario-general/cierre/preview` (POST)
- **Función**: `api_almacen_embarques_inventario_cierre_preview` (Línea 14903)
- **Evidencia**: Path exacto '/api/almacen-embarques/inventario-general/cierre/preview' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/inventario-general/cierre/confirm` (POST)
- **Función**: `api_almacen_embarques_inventario_cierre_confirm` (Línea 14965)
- **Evidencia**: Path exacto '/api/almacen-embarques/inventario-general/cierre/confirm' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/inventario-general/cierre/cancel` (POST)
- **Función**: `api_almacen_embarques_inventario_cierre_cancel` (Línea 15101)
- **Evidencia**: Path exacto '/api/almacen-embarques/inventario-general/cierre/cancel' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/inventario-general/cierre/history/<int:batch_id>` (GET)
- **Función**: `api_almacen_embarques_inventario_cierre_history_detail` (Línea 15176)
- **Evidencia**: Path limpio '/api/almacen-embarques/inventario-general/cierre/history' en app\static\js\almacen_embarques_admin.js

### `/api/almacen-embarques/inventario-general/cierre/history/<int:batch_id>/export` (GET)
- **Función**: `export_almacen_embarques_inventario_cierre_report` (Línea 15223)
- **Evidencia**: Multi-segmento ['/api/almacen-embarques/inventario-general/cierre/history/', '/export'] en app\static\js\almacen_embarques_admin.js: '`/api/almacen-embarques/inventario-general/cierre/history/${encodeURIComponent(reportButton.dataset.batchId)}/export`,'

### `/registro-movimiento-identificacion-ajax` (GET)
- **Función**: `registro_movimiento_identificacion_ajax` (Línea 15754)
- **Evidencia**: Path exacto '/registro-movimiento-identificacion-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/control-otras-identificaciones-ajax` (GET)
- **Función**: `control_otras_identificaciones_ajax` (Línea 15767)
- **Evidencia**: Path exacto '/control-otras-identificaciones-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/control-movimiento-ns-producto-ajax` (GET)
- **Función**: `control_movimiento_ns_producto_ajax` (Línea 15780)
- **Evidencia**: Path exacto '/control-movimiento-ns-producto-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/model-sn-management-ajax` (GET)
- **Función**: `model_sn_management_ajax` (Línea 15793)
- **Evidencia**: Path exacto '/model-sn-management-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/control-scrap-ajax` (GET)
- **Función**: `control_scrap_ajax` (Línea 15804)
- **Evidencia**: Path exacto '/control-scrap-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/line-material-status-ajax` (GET)
- **Función**: `line_material_status_ajax` (Línea 15816)
- **Evidencia**: Path exacto '/line-material-status-ajax' en app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html

### `/control-mask-metal-ajax` (GET)
- **Función**: `control_mask_metal_ajax` (Línea 15829)
- **Evidencia**: Path exacto '/control-mask-metal-ajax' en app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html

### `/control-squeegee-ajax` (GET)
- **Función**: `control_squeegee_ajax` (Línea 15840)
- **Evidencia**: Path exacto '/control-squeegee-ajax' en app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html

### `/control-caja-mask-metal-ajax` (GET)
- **Función**: `control_caja_mask_metal_ajax` (Línea 15851)
- **Evidencia**: Path exacto '/control-caja-mask-metal-ajax' en app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html

### `/estandares-soldadura-ajax` (GET)
- **Función**: `estandares_soldadura_ajax` (Línea 15864)
- **Evidencia**: Path exacto '/estandares-soldadura-ajax' en app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html

### `/registro-recibo-soldadura-ajax` (GET)
- **Función**: `registro_recibo_soldadura_ajax` (Línea 15877)
- **Evidencia**: Path exacto '/registro-recibo-soldadura-ajax' en app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html

### `/control-salida-soldadura-ajax` (GET)
- **Función**: `control_salida_soldadura_ajax` (Línea 15890)
- **Evidencia**: Path exacto '/control-salida-soldadura-ajax' en app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html

### `/historial-tension-mask-metal-ajax` (GET)
- **Función**: `historial_tension_mask_metal_ajax` (Línea 15903)
- **Evidencia**: Path exacto '/historial-tension-mask-metal-ajax' en app\templates\LISTAS\LISTA_CONTROLDEPRODUCCION.html

### `/listas/control_proceso` (GET)
- **Función**: `lista_control_proceso` (Línea 15942)
- **Evidencia**: Path exacto '/listas/control_proceso' en app\templates\MainTemplate.html

### `/listas/control_calidad` (GET)
- **Función**: `lista_control_calidad` (Línea 15953)
- **Evidencia**: Path exacto '/listas/control_calidad' en app\templates\MainTemplate.html

### `/listas/control_resultados` (GET)
- **Función**: `lista_control_resultados` (Línea 15964)
- **Evidencia**: Path exacto '/listas/control_resultados' en app\templates\MainTemplate.html

### `/historial-aoi` (GET)
- **Función**: `historial_aoi` (Línea 15975)
- **Evidencia**: Path exacto '/historial-aoi' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/historial-ict-ajax` (GET)
- **Función**: `historial_ict_ajax` (Línea 15986)
- **Evidencia**: Path exacto '/historial-ict-ajax' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/historial-maquina-ict-pass-fail` (GET)
- **Función**: `historial_maquina_ict_pass_fail` (Línea 15996)
- **Evidencia**: Path exacto '/historial-maquina-ict-pass-fail' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/historial-maquina-ict-pass-fail-ajax` (GET)
- **Función**: `historial_maquina_ict_pass_fail` (Línea 15997)
- **Evidencia**: Path exacto '/historial-maquina-ict-pass-fail-ajax' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/api/ict/pass-fail` (GET)
- **Función**: `ict_pass_fail_api` (Línea 16089)
- **Evidencia**: Path exacto '/api/ict/pass-fail' en app\static\js\ict-Pass-Fail.js

### `/api/ict/pass-fail/detail` (GET)
- **Función**: `ict_pass_fail_detail_api` (Línea 16127)
- **Evidencia**: Path exacto '/api/ict/pass-fail/detail' en app\static\js\ict-Pass-Fail.js

### `/api/ict/pass-fail/export` (GET)
- **Función**: `ict_pass_fail_export` (Línea 16274)
- **Evidencia**: Path exacto '/api/ict/pass-fail/export' en app\static\js\ict-Pass-Fail.js

### `/historial-cambios-parametros-ict-ajax` (GET)
- **Función**: `historial_cambios_parametros_ict_ajax` (Línea 16383)
- **Evidencia**: Path exacto '/historial-cambios-parametros-ict-ajax' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/api/ict/param-changes/progress` (GET)
- **Función**: `ict_param_changes_progress` (Línea 16912)
- **Evidencia**: Path exacto '/api/ict/param-changes/progress' en app\static\js\historial_cambios_parametros_ict.js

### `/api/ict/param-changes` (GET)
- **Función**: `ict_param_changes_api` (Línea 16932)
- **Evidencia**: Path exacto '/api/ict/param-changes' en app\static\js\historial_cambios_parametros_ict.js

### `/api/ict/param-changes/export` (GET)
- **Función**: `ict_param_changes_export` (Línea 16966)
- **Evidencia**: Path exacto '/api/ict/param-changes/export' en app\static\js\historial_cambios_parametros_ict.js

### `/historial-aoi-ajax` (GET)
- **Función**: `historial_aoi_ajax` (Línea 17205)
- **Evidencia**: Path exacto '/historial-aoi-ajax' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/listas/control_reporte` (GET)
- **Función**: `lista_control_reporte` (Línea 17216)
- **Evidencia**: Path exacto '/listas/control_reporte' en app\templates\MainTemplate.html

### `/listas/configuracion_programa` (GET)
- **Función**: `lista_configuracion_programa` (Línea 17227)
- **Evidencia**: Path exacto '/listas/configuracion_programa' en app\templates\MainTemplate.html

### `/material/info` (GET)
- **Función**: `material_info` (Línea 17238)
- **Evidencia**: Path exacto '/material/info' en app\templates\MainTemplate.html

### `/material/historial_inventario` (GET)
- **Función**: `material_historial_inventario` (Línea 17409)
- **Evidencia**: Path exacto '/material/historial_inventario' en app\templates\MainTemplate.html

### `/material/registro_material` (GET)
- **Función**: `material_registro_material` (Línea 17420)
- **Evidencia**: Path exacto '/material/registro_material' en app\templates\MainTemplate.html

### `/material/estatus_material` (GET)
- **Función**: `material_estatus_material` (Línea 17431)
- **Evidencia**: Path exacto '/material/estatus_material' en app\templates\MainTemplate.html

### `/api/estatus_material/consultar` (POST)
- **Función**: `consultar_estatus_material` (Línea 17442)
- **Evidencia**: Path exacto '/api/estatus_material/consultar' en app\static\js\Estatus de material.js

### `/api/inventario/consultar` (POST)
- **Función**: `consultar_inventario_general` (Línea 18458)
- **Evidencia**: Path exacto '/api/inventario/consultar' en app\static\js\Registro_de_material_real.js

### `/api/inventario/historial` (POST)
- **Función**: `obtener_historial_numero_parte` (Línea 18608)
- **Evidencia**: Path exacto '/api/inventario/historial' en app\static\js\Registro_de_material_real.js

### `/api/inventario/historial/<numero_parte>` (GET)
- **Función**: `obtener_historial_numero_parte_get` (Línea 18825)
- **Evidencia**: Path limpio '/api/inventario/historial' en app\static\js\Registro_de_material_real.js

### `/api/inventario/lotes` (POST)
- **Función**: `obtener_lotes_numero_parte` (Línea 19040)
- **Evidencia**: Path exacto '/api/inventario/lotes' en app\static\js\Registro_de_material_real.js

### `/api/inventario/lotes/<numero_parte>` (GET)
- **Función**: `obtener_lotes_numero_parte_get` (Línea 19204)
- **Evidencia**: Path limpio '/api/inventario/lotes' en app\static\js\Registro_de_material_real.js

### `/templates/LISTAS/<filename>` (GET)
- **Función**: `serve_list_template` (Línea 19365)
- **Evidencia**: Path limpio '/templates/LISTAS' en app\templates\MainTemplate.html

### `/verificar_permiso_dropdown` (POST)
- **Función**: `verificar_permiso_dropdown` (Línea 19404)
- **Evidencia**: Función 'verificar_permiso_dropdown' en app\user_admin.py

### `/obtener_permisos_usuario_actual` (GET)
- **Función**: `obtener_permisos_usuario_actual` (Línea 19457)
- **Evidencia**: Path exacto '/obtener_permisos_usuario_actual' en app\static\js\permisos-dropdowns.js

### `/historial-cambio-material-smt` (GET)
- **Función**: `historial_cambio_material_smt` (Línea 19518)
- **Evidencia**: Path exacto '/historial-cambio-material-smt' en app\templates\MainTemplate.html

### `/historial-cambio-material-smt-ajax` (GET)
- **Función**: `historial_cambio_material_smt_ajax` (Línea 19529)
- **Evidencia**: Path exacto '/historial-cambio-material-smt-ajax' en app\templates\MainTemplate.html

### `/api/csv_data` (GET)
- **Función**: `get_csv_data` (Línea 19542)
- **Evidencia**: Path exacto '/api/csv_data' en app\static\js\historial_cambio_material_smt.js

### `/importar_excel_plan_produccion` (POST)
- **Función**: `importar_excel_plan_produccion` (Línea 20559)
- **Evidencia**: Path exacto '/importar_excel_plan_produccion' en app\static\js\crear-plan-produccion.js

### `/produccion/info` (GET)
- **Función**: `produccion_info` (Línea 21115)
- **Evidencia**: Path exacto '/produccion/info' en app\templates\MainTemplate.html

### `/material/recibo_pago` (GET)
- **Función**: `material_recibo_pago` (Línea 21129)
- **Evidencia**: Path exacto '/material/recibo_pago' en app\templates\MainTemplate.html

### `/material/material_sustituto` (GET)
- **Función**: `material_material_sustituto` (Línea 21140)
- **Evidencia**: Path exacto '/material/material_sustituto' en app\templates\MainTemplate.html

### `/material/consultar_peps` (GET)
- **Función**: `material_consultar_peps` (Línea 21151)
- **Evidencia**: Path exacto '/material/consultar_peps' en app\templates\MainTemplate.html

### `/material/ajuste_numero` (GET)
- **Función**: `material_ajuste_numero` (Línea 21175)
- **Evidencia**: Path exacto '/material/ajuste_numero' en app\templates\MainTemplate.html

### `/importar_excel_registro` (POST)
- **Función**: `importar_excel_registro` (Línea 21409)
- **Evidencia**: Path exacto '/importar_excel_registro' en app\templates\Control de material\Registro de material real.html

### `/importar_excel_estatus_inventario` (POST)
- **Función**: `importar_excel_estatus_inventario` (Línea 21520)
- **Evidencia**: Path exacto '/importar_excel_estatus_inventario' en app\templates\Control de material\Estatus de material.html

### `/importar_excel_estatus_recibido` (POST)
- **Función**: `importar_excel_estatus_recibido` (Línea 21631)
- **Evidencia**: Path exacto '/importar_excel_estatus_recibido' en app\templates\Control de material\Estatus de material.html

### `/importar_excel_historial` (POST)
- **Función**: `importar_excel_historial` (Línea 21743)
- **Evidencia**: Path exacto '/importar_excel_historial' en app\templates\Control de material\Historial de inventario real.html

### `/api/wo/exportar` (GET)
- **Función**: `exportar_wos_excel` (Línea 21859)
- **Evidencia**: Path exacto '/api/wo/exportar' en app\static\js\crear-plan-produccion.js

### `/api/plan-smd/import` (POST)
- **Función**: `api_plan_smd_import` (Línea 21988)
- **Evidencia**: Path exacto '/api/plan-smd/import' en app\templates\Control de produccion\crear_plan_micom_ajax.html

### `/api/inventario` (GET)
- **Función**: `api_inventario` (Línea 22140)
- **Evidencia**: Path exacto '/api/inventario' en app\templates\Control de produccion\crear_plan_micom_ajax.html

### `/api/plan-micom/generar` (POST)
- **Función**: `api_plan_micom_generar` (Línea 22195)
- **Evidencia**: Path exacto '/api/plan-micom/generar' en app\templates\Control de produccion\crear_plan_micom_ajax.html

### `/control-resultado-reparacion-ajax` (GET)
- **Función**: `control_resultado_reparacion_ajax` (Línea 22267)
- **Evidencia**: Path exacto '/control-resultado-reparacion-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/control-item-reparado-ajax` (GET)
- **Función**: `control_item_reparado_ajax` (Línea 22274)
- **Evidencia**: Path exacto '/control-item-reparado-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/historial-cambio-material-maquina-ajax` (GET)
- **Función**: `historial_cambio_material_maquina_ajax` (Línea 22281)
- **Evidencia**: Path exacto '/historial-cambio-material-maquina-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/api/historial-cambio-material-maquina` (GET)
- **Función**: `api_historial_cambio_material_maquina` (Línea 22290)
- **Evidencia**: Path exacto '/api/historial-cambio-material-maquina' en app\templates\Control de calidad\historial_cambio_material_maquina_ajax.html

### `/api/historial_smt_latest` (GET)
- **Función**: `api_historial_smt_latest` (Línea 22417)
- **Evidencia**: Path exacto '/api/historial_smt_latest' en app\static\js\control-operacion-smt-ajax.js

### `/api/historial_smt_latest_v2` (GET)
- **Función**: `api_historial_smt_latest_v2` (Línea 22521)
- **Evidencia**: Path exacto '/api/historial_smt_latest_v2' en app\static\js\control-operacion-smt-ajax.js

### `/api/masks/info` (GET)
- **Función**: `api_masks_info` (Línea 22620)
- **Evidencia**: Path exacto '/api/masks/info' en app\static\js\control-operacion-smt-ajax.js

### `/historial-uso-pegamento-soldadura-ajax` (GET)
- **Función**: `historial_uso_pegamento_soldadura_ajax` (Línea 22692)
- **Evidencia**: Path exacto '/historial-uso-pegamento-soldadura-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/api/metal-mask/history` (POST)
- **Función**: `api_save_metal_mask_history` (Línea 22704)
- **Evidencia**: Path exacto '/api/metal-mask/history' en app\templates\Control de calidad\historial_uso_mask_metal_ajax.html

### `/api/metal-mask/history` (GET)
- **Función**: `api_get_metal_mask_history` (Línea 22801)
- **Evidencia**: Path exacto '/api/metal-mask/history' en app\templates\Control de calidad\historial_uso_mask_metal_ajax.html

### `/api/metal-mask/update-used-count` (POST)
- **Función**: `api_update_metal_mask_used_count` (Línea 22895)
- **Evidencia**: Path exacto '/api/metal-mask/update-used-count' en app\static\js\control-operacion-smt-ajax.js

### `/historial-uso-mask-metal-ajax` (GET)
- **Función**: `historial_uso_mask_metal_ajax` (Línea 23057)
- **Evidencia**: Path exacto '/historial-uso-mask-metal-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/historial-uso-squeegee-ajax` (GET)
- **Función**: `historial_uso_squeegee_ajax` (Línea 23064)
- **Evidencia**: Path exacto '/historial-uso-squeegee-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/process-interlock-history-ajax` (GET)
- **Función**: `process_interlock_history_ajax` (Línea 23071)
- **Evidencia**: Path exacto '/process-interlock-history-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/control-master-sample-smt-ajax` (GET)
- **Función**: `control_master_sample_smt_ajax` (Línea 23078)
- **Evidencia**: Path exacto '/control-master-sample-smt-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/historial-inspeccion-master-sample-smt-ajax` (GET)
- **Función**: `historial_inspeccion_master_sample_smt_ajax` (Línea 23085)
- **Evidencia**: Path exacto '/historial-inspeccion-master-sample-smt-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/control-inspeccion-oqc-ajax` (GET)
- **Función**: `control_inspeccion_oqc_ajax` (Línea 23094)
- **Evidencia**: Path exacto '/control-inspeccion-oqc-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/historial-liberacion-lqc-ajax` (GET)
- **Función**: `historial_liberacion_lqc_ajax` (Línea 23101)
- **Evidencia**: Path exacto '/historial-liberacion-lqc-ajax' en app\templates\LISTAS\LISTA_CONTROL_DE_CALIDAD.html

### `/api/smt-scanner/lineas` (GET)
- **Función**: `api_smt_scanner_lineas` (Línea 23132)
- **Evidencia**: Path exacto '/api/smt-scanner/lineas' en app\templates\Control de calidad\historial_liberacion_lqc_ajax.html

### `/api/smt-scanner/datos` (GET)
- **Función**: `api_smt_scanner_datos` (Línea 23244)
- **Evidencia**: Path exacto '/api/smt-scanner/datos' en app\templates\Control de calidad\historial_liberacion_lqc_ajax.html

### `/api/inventario_general` (GET)
- **Función**: `api_inventario_general` (Línea 23542)
- **Evidencia**: Path exacto '/api/inventario_general' en app\static\js\inventario-imd-terminado-module.js

### `/api/ubicacion` (GET)
- **Función**: `api_ubicacion` (Línea 23589)
- **Evidencia**: Path exacto '/api/ubicacion' en app\static\js\inventario-imd-terminado-module.js

### `/api/movimientos` (GET)
- **Función**: `api_movimientos` (Línea 23652)
- **Evidencia**: Path exacto '/api/movimientos' en app\static\js\inventario-imd-terminado-module.js

### `/api/snapshot_inventario/fechas` (GET)
- **Función**: `api_snapshot_inv_fechas` (Línea 23727)
- **Evidencia**: Path exacto '/api/snapshot_inventario/fechas' en app\static\js\inventario-imd-terminado-module.js

### `/api/snapshot_inventario/general` (GET)
- **Función**: `api_snapshot_inv_general` (Línea 23752)
- **Evidencia**: Path exacto '/api/snapshot_inventario/general' en app\static\js\inventario-imd-terminado-module.js

### `/api/snapshot_inventario/ubicacion` (GET)
- **Función**: `api_snapshot_inv_ubicacion` (Línea 23787)
- **Evidencia**: Path exacto '/api/snapshot_inventario/ubicacion' en app\static\js\inventario-imd-terminado-module.js

### `/api/mysql` (POST, GET, OPTIONS)
- **Función**: `api_mysql_simple` (Línea 23888)
- **Evidencia**: Path exacto '/api/mysql' en app\static\js\visor_mysql.js

### `/plan-smd-diario` (GET)
- **Función**: `plan_smd_diario` (Línea 23987)
- **Evidencia**: Path exacto '/plan-smd-diario' en app\templates\Control de proceso\Control de operacion de linea SMT.html

### `/control-operacion-linea-smt` (GET)
- **Función**: `control_operacion_linea_smt` (Línea 23993)
- **Evidencia**: Path exacto '/control-operacion-linea-smt' en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/api/plan-smd-diario` (GET)
- **Función**: `api_plan_smd_diario` (Línea 23999)
- **Evidencia**: Path exacto '/api/plan-smd-diario' en app\templates\Control de proceso\Control de operacion de linea SMT.html

### `/visor-mysql` (GET)
- **Función**: `visor_mysql` (Línea 24086)
- **Evidencia**: Path exacto '/visor-mysql' en app\templates\MainTemplate.html

### `/control-modelos-visor-ajax` (GET)
- **Función**: `control_modelos_visor_ajax` (Línea 24096)
- **Evidencia**: Path exacto '/control-modelos-visor-ajax' en app\templates\LISTAS\LISTA_INFORMACIONBASICA.html

### `/control-modelos-smt-ajax` (GET)
- **Función**: `control_modelos_smt_ajax` (Línea 24120)
- **Evidencia**: Path exacto '/control-modelos-smt-ajax' en app\templates\LISTAS\LISTA_INFORMACIONBASICA.html

### `/api/mysql/columns` (GET)
- **Función**: `api_mysql_columns` (Línea 24136)
- **Evidencia**: Path exacto '/api/mysql/columns' en app\static\js\visor_mysql.js

### `/api/mysql/data` (GET)
- **Función**: `api_mysql_data` (Línea 24163)
- **Evidencia**: Path exacto '/api/mysql/data' en app\static\js\visor_mysql.js

### `/api/mysql/update` (POST)
- **Función**: `api_mysql_update` (Línea 24264)
- **Evidencia**: Path exacto '/api/mysql/update' en app\static\js\visor_mysql.js

### `/api/mysql/create` (POST)
- **Función**: `api_mysql_create` (Línea 24424)
- **Evidencia**: Path exacto '/api/mysql/create' en app\static\js\visor_mysql.js

### `/api/mysql/delete` (POST)
- **Función**: `api_mysql_delete` (Línea 24537)
- **Evidencia**: Path exacto '/api/mysql/delete' en app\static\js\visor_mysql.js

### `/api/plan-smd/list` (GET)
- **Función**: `api_plan_smd_list` (Línea 24675)
- **Evidencia**: Path exacto '/api/plan-smd/list' en app\static\js\control-operacion-smt-ajax.js

### `/api/plan-run/start` (POST)
- **Función**: `api_plan_run_start` (Línea 24893)
- **Evidencia**: Path exacto '/api/plan-run/start' en app\static\js\control-operacion-smt-ajax.js

### `/api/plan-run/end` (POST)
- **Función**: `api_plan_run_end` (Línea 25081)
- **Evidencia**: Path exacto '/api/plan-run/end' en app\static\js\control-operacion-smt-ajax.js

### `/api/masks` (GET)
- **Función**: `api_list_masks` (Línea 25451)
- **Evidencia**: Path exacto '/api/masks' en app\static\js\control-operacion-smt-ajax.js

### `/api/masks` (POST)
- **Función**: `api_create_mask` (Línea 25491)
- **Evidencia**: Path exacto '/api/masks' en app\static\js\control-operacion-smt-ajax.js

### `/api/masks/<int:mask_id>` (PUT)
- **Función**: `api_update_mask` (Línea 25537)
- **Evidencia**: Path limpio '/api/masks' en app\static\js\control-operacion-smt-ajax.js

### `/api/storage` (GET)
- **Función**: `api_get_storage` (Línea 25583)
- **Evidencia**: Path exacto '/api/storage' en app\static\js\Caja-metalmask.js

### `/api/storage` (POST)
- **Función**: `api_add_storage` (Línea 25635)
- **Evidencia**: Path exacto '/api/storage' en app\static\js\Caja-metalmask.js

### `/api/storage/<int:storage_id>` (PUT)
- **Función**: `api_update_storage` (Línea 25676)
- **Evidencia**: Path limpio '/api/storage' en app\static\js\Caja-metalmask.js

### `/api/bom-smt-data` (GET)
- **Función**: `api_bom_smt_data` (Línea 25716)
- **Evidencia**: Path exacto '/api/bom-smt-data' en app\static\js\control-operacion-smt-ajax.js

### `/historial-vision` (GET)
- **Función**: `historial_vision` (Línea 27084)
- **Evidencia**: Path exacto '/historial-vision' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/historial-vision-ajax` (GET)
- **Función**: `historial_vision` (Línea 27085)
- **Evidencia**: Path exacto '/historial-vision-ajax' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/historial-vision-pass-fail` (GET)
- **Función**: `historial_vision_pass_fail` (Línea 27096)
- **Evidencia**: Path exacto '/historial-vision-pass-fail' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/historial-vision-pass-fail-ajax` (GET)
- **Función**: `historial_vision_pass_fail` (Línea 27097)
- **Evidencia**: Path exacto '/historial-vision-pass-fail-ajax' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/api/vision/data` (GET)
- **Función**: `vision_data_api` (Línea 27108)
- **Evidencia**: Path exacto '/api/vision/data' en app\static\js\history_vision.js

### `/api/vision/pass-fail-summary` (GET)
- **Función**: `vision_pass_fail_summary_api` (Línea 27140)
- **Evidencia**: Path exacto '/api/vision/pass-fail-summary' en app\static\js\history_vision_pass_fail.js

### `/api/vision/pass-fail-summary/export` (GET)
- **Función**: `export_vision_pass_fail_summary_excel` (Línea 27176)
- **Evidencia**: Path exacto '/api/vision/pass-fail-summary/export' en app\static\js\history_vision_pass_fail.js

### `/api/vision/image-info` (GET)
- **Función**: `vision_image_info_api` (Línea 27278)
- **Evidencia**: Path exacto '/api/vision/image-info' en app\static\js\history_vision.js

### `/api/vision/export` (GET)
- **Función**: `export_vision_excel` (Línea 27388)
- **Evidencia**: Path exacto '/api/vision/export' en app\static\js\history_vision.js

### `/historial-ict` (GET)
- **Función**: `ict_front_full_defects2` (Línea 27475)
- **Evidencia**: Path exacto '/historial-ict' en app\templates\LISTAS\LISTA_DE_CONTROL_DE_RESULTADOS.html

### `/api/ict/data` (GET)
- **Función**: `ict_data_api` (Línea 27487)
- **Evidencia**: Path exacto '/api/ict/data' en app\static\js\ict.js

### `/api/ict/defects` (GET)
- **Función**: `ict_defects_api` (Línea 27597)
- **Evidencia**: Path exacto '/api/ict/defects' en app\static\js\ict.js

### `/api/ict/export` (GET)
- **Función**: `export_ict_excel` (Línea 27621)
- **Evidencia**: Path exacto '/api/ict/export' en app\static\js\ict.js

### `/api/ict/export-defects` (GET)
- **Función**: `export_ict_defects_excel` (Línea 27766)
- **Evidencia**: Path exacto '/api/ict/export-defects' en app\static\js\ict.js

### `/api/ict/export-compare` (POST)
- **Función**: `export_ict_compare_excel` (Línea 27908)
- **Evidencia**: Path exacto '/api/ict/export-compare' en app\static\js\ict.js

