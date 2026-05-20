# 🔍 Auditoría y Verificación Exhaustiva de Rutas Huérfanas (v2)

Este documento audita y verifica **una por una** todas las rutas del sistema usando **8 estrategias de detección**:

1. `url_for()` con nombre de función (todos los archivos)
2. Token de función referenciado en cualquier archivo
3. Coincidencia exacta del path (sin parámetros dinámicos)
4. Multi-segmento: todos los segmentos estáticos en la misma línea
5. Regex dinámico para template literals y concatenaciones JS
6. Segmentos parciales (primer + último segmento en misma línea)
7. Referencias internas en routes.py (redirect, url_for)
8. Grupo CRUD: hermanos del mismo prefijo confirmados en uso

## Resumen del Análisis Exhaustivo
- **Rutas analizadas en routes.py**: 346
- **Rutas Confirmadas En Uso**: 346
- **Rutas Confirmadas Huérfanas (Sin uso)**: 0

## 🚫 Rutas 100% Confirmadas Sin Uso (Huérfanas)
Las siguientes rutas no fueron detectadas por ninguna de las 8 estrategias de búsqueda. **Pueden ser removidas de manera segura del archivo `routes.py`**.

| Línea | Ruta | Métodos | Función |
| :--- | :--- | :--- | :--- |

## ✅ Rutas Confirmadas En Uso
Cada ruta incluye la **estrategia** que confirmó su uso y la **evidencia** específica.

### `/api/health` (GET)
- **Función**: `api_health` (Línea 218)
- **Evidencia**: Función 'api_health' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/smt-simple` (GET)
- **Función**: `smt_simple` (Línea 252)
- **Evidencia**: Función 'smt_simple' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/` (GET)
- **Función**: `index` (Línea 585)
- **Evidencia**: Función 'index' referenciada en README.md

### `/login` (GET, POST)
- **Función**: `login` (Línea 590)
- **Evidencia**: url_for en app\routes.py

### `/inicio` (GET)
- **Función**: `inicio` (Línea 733)
- **Evidencia**: url_for en app\routes.py

### `/api/mi-perfil` (GET, POST)
- **Función**: `api_mi_perfil` (Línea 739)
- **Evidencia**: Función 'api_mi_perfil' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/calendario` (GET)
- **Función**: `calendario` (Línea 1035)
- **Evidencia**: Función 'calendario' referenciada en .playwright-cli\page-2026-04-28T13-38-05-123Z.yml

### `/defect-management` (GET)
- **Función**: `defect_management` (Línea 1042)
- **Evidencia**: Función 'defect_management' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/favicon.eco` (GET)
- **Función**: `favicon` (Línea 1055)
- **Evidencia**: Función 'favicon' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/sistemas` (GET)
- **Función**: `sistemas` (Línea 1065)
- **Evidencia**: Función 'sistemas' referenciada en .history\app\templates\MaterialTemplate_20260427162900.html

### `/soporte` (GET)
- **Función**: `soporte` (Línea 1072)
- **Evidencia**: Función 'soporte' referenciada en README.md

### `/documentacion` (GET)
- **Función**: `documentacion` (Línea 1083)
- **Evidencia**: Función 'documentacion' referenciada en app\templates\Control de proceso\control_unidad_empaque_modelo_ajax.html

### `/ILSAN-ELECTRONICS` (GET)
- **Función**: `material` (Línea 1094)
- **Evidencia**: url_for en app\routes.py

### `/dashboard` (GET)
- **Función**: `dashboard` (Línea 1139)
- **Evidencia**: Función 'dashboard' referenciada en .history\app\static\js\control-cuchillas-corte_20260226101507.js

### `/logout` (GET)
- **Función**: `logout` (Línea 1173)
- **Evidencia**: Función 'logout' referenciada en DESIGN_GUIDE.md

### `/front-plan/static/<path:filename>` (GET)
- **Función**: `front_plan_static` (Línea 1201)
- **Evidencia**: Función 'front_plan_static' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/plan-main` (GET)
- **Función**: `view_plan_main` (Línea 1210)
- **Evidencia**: Función 'view_plan_main' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control-main` (GET)
- **Función**: `view_control_main` (Línea 1217)
- **Evidencia**: Función 'view_control_main' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/plan-main-assy-ajax` (GET)
- **Función**: `plan_main_assy_ajax` (Línea 1225)
- **Evidencia**: Función 'plan_main_assy_ajax' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/plan-main-imd-ajax` (GET)
- **Función**: `plan_main_imd_ajax` (Línea 1234)
- **Evidencia**: Función 'plan_main_imd_ajax' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/plan-main-smt-ajax` (GET)
- **Función**: `plan_main_smt_ajax` (Línea 1243)
- **Evidencia**: Función 'plan_main_smt_ajax' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control-operacion-linea-main-ajax` (GET)
- **Función**: `ctrl_operacion_linea_main_ajax` (Línea 1252)
- **Evidencia**: Función 'ctrl_operacion_linea_main_ajax' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan` (GET)
- **Función**: `api_plan_list` (Línea 3545)
- **Evidencia**: Función 'api_plan_list' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan/input-main/scan-lots` (GET)
- **Función**: `api_plan_input_main_scan_lots` (Línea 3610)
- **Evidencia**: Función 'api_plan_input_main_scan_lots' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan/input-main/assign-lot` (POST)
- **Función**: `api_plan_input_main_assign_lot` (Línea 3746)
- **Evidencia**: Función 'api_plan_input_main_assign_lot' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan/input-main/create-plan` (POST)
- **Función**: `api_plan_input_main_create_plan` (Línea 3963)
- **Evidencia**: Función 'api_plan_input_main_create_plan' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan` (POST)
- **Función**: `api_plan_create` (Línea 4119)
- **Evidencia**: Función 'api_plan_create' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan/update` (POST)
- **Función**: `api_plan_update` (Línea 4258)
- **Evidencia**: Función 'api_plan_update' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/raw/search` (GET)
- **Función**: `api_raw_search` (Línea 4313)
- **Evidencia**: Función 'api_raw_search' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan/status` (POST)
- **Función**: `api_plan_status` (Línea 4367)
- **Evidencia**: Función 'api_plan_status' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan/save-sequences` (POST)
- **Función**: `api_plan_save_sequences` (Línea 4515)
- **Evidencia**: Función 'api_plan_save_sequences' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan/pending` (GET)
- **Función**: `api_plan_pending` (Línea 4565)
- **Evidencia**: Función 'api_plan_pending' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan/reschedule` (POST)
- **Función**: `api_plan_reschedule` (Línea 4631)
- **Evidencia**: Función 'api_plan_reschedule' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan/export-excel` (POST)
- **Función**: `api_plan_export_excel` (Línea 4786)
- **Evidencia**: Función 'api_plan_export_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-imd` (GET)
- **Función**: `api_plan_imd_list` (Línea 4875)
- **Evidencia**: Función 'api_plan_imd_list' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-imd` (POST)
- **Función**: `api_plan_imd_create` (Línea 4942)
- **Evidencia**: Función 'api_plan_imd_create' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-imd/batch-update` (POST)
- **Función**: `api_plan_imd_batch_update` (Línea 5022)
- **Evidencia**: Función 'api_plan_imd_batch_update' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-imd/update` (POST)
- **Función**: `api_plan_imd_update` (Línea 5064)
- **Evidencia**: Función 'api_plan_imd_update' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-imd/save-sequences` (POST)
- **Función**: `api_plan_imd_save_sequences` (Línea 5113)
- **Evidencia**: Función 'api_plan_imd_save_sequences' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-imd/pending` (GET)
- **Función**: `api_plan_imd_pending` (Línea 5164)
- **Evidencia**: Función 'api_plan_imd_pending' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-imd/pending-reschedule` (GET)
- **Función**: `api_plan_imd_pending_reschedule` (Línea 5218)
- **Evidencia**: Función 'api_plan_imd_pending_reschedule' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-imd/reschedule` (POST)
- **Función**: `api_plan_imd_reschedule` (Línea 5268)
- **Evidencia**: Función 'api_plan_imd_reschedule' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-imd/export-excel` (POST)
- **Función**: `api_plan_imd_export_excel` (Línea 5377)
- **Evidencia**: Función 'api_plan_imd_export_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-imd/import-excel` (POST)
- **Función**: `api_plan_imd_import_excel` (Línea 5462)
- **Evidencia**: Función 'api_plan_imd_import_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smt` (GET)
- **Función**: `api_plan_smt_list` (Línea 5721)
- **Evidencia**: Función 'api_plan_smt_list' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smt` (POST)
- **Función**: `api_plan_smt_create` (Línea 5788)
- **Evidencia**: Función 'api_plan_smt_create' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smt/batch-update` (POST)
- **Función**: `api_plan_smt_batch_update` (Línea 5866)
- **Evidencia**: Función 'api_plan_smt_batch_update' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smt/update` (POST)
- **Función**: `api_plan_smt_update` (Línea 5900)
- **Evidencia**: Función 'api_plan_smt_update' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smt/save-sequences` (POST)
- **Función**: `api_plan_smt_save_sequences` (Línea 5942)
- **Evidencia**: Función 'api_plan_smt_save_sequences' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smt/pending` (GET)
- **Función**: `api_plan_smt_pending` (Línea 5993)
- **Evidencia**: Función 'api_plan_smt_pending' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smt/reschedule` (POST)
- **Función**: `api_plan_smt_reschedule` (Línea 6043)
- **Evidencia**: Función 'api_plan_smt_reschedule' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smt/export-excel` (POST)
- **Función**: `api_plan_smt_export_excel` (Línea 6145)
- **Evidencia**: Función 'api_plan_smt_export_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smt/import-excel` (POST)
- **Función**: `api_plan_smt_import_excel` (Línea 6222)
- **Evidencia**: Función 'api_plan_smt_import_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-main/list` (GET)
- **Función**: `api_plan_main_list` (Línea 6425)
- **Evidencia**: Función 'api_plan_main_list' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/work-orders/import` (POST)
- **Función**: `api_work_orders_import` (Línea 6493)
- **Evidencia**: Función 'api_work_orders_import' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/cargar_template` (POST)
- **Función**: `cargar_template` (Línea 6657)
- **Evidencia**: Función 'cargar_template' referenciada en .history\app\templates\MaterialTemplate_20260427162900.html

### `/importar_excel_bom` (POST)
- **Función**: `importar_excel_bom` (Línea 6682)
- **Evidencia**: Función 'importar_excel_bom' referenciada en README.md

### `/listar_modelos_bom` (GET)
- **Función**: `listar_modelos_bom` (Línea 6720)
- **Evidencia**: Función 'listar_modelos_bom' referenciada en README.md

### `/listar_bom` (POST)
- **Función**: `listar_bom` (Línea 6736)
- **Evidencia**: Función 'listar_bom' referenciada en README.md

### `/consultar_bom` (GET)
- **Función**: `consultar_bom` (Línea 6755)
- **Evidencia**: Función 'consultar_bom' referenciada en README.md

### `/api/ecos` (GET)
- **Función**: `api_ecos_list` (Línea 6809)
- **Evidencia**: Path exacto '/api/ecos' en app\routes.py

### `/api/ecos/export` (GET)
- **Función**: `api_ecos_export` (Línea 6867)
- **Evidencia**: Path exacto '/api/ecos/export' en app\routes.py

### `/api/ecos/<int:eco_id>` (GET)
- **Función**: `api_ecos_detail` (Línea 6958)
- **Evidencia**: Path exacto '/api/ecos' en app\routes.py

### `/api/ecn-ks/<int:hist_seq>` (GET)
- **Función**: `api_ecn_ks_detail` (Línea 6975)
- **Evidencia**: Path exacto '/api/ecn-ks' en app\routes.py

### `/api/ecos` (POST)
- **Función**: `api_ecos_create` (Línea 6991)
- **Evidencia**: Path exacto '/api/ecos' en app\routes.py

### `/api/bom/download-excel` (GET)
- **Función**: `api_bom_download_excel` (Línea 7039)
- **Evidencia**: Path exacto '/api/bom/download-excel' en app\routes.py

### `/api/bom/resolve-family` (GET)
- **Función**: `api_bom_resolve_family` (Línea 7103)
- **Evidencia**: Path exacto '/api/bom/resolve-family' en app\routes.py

### `/api/bom/download-excel-family` (GET)
- **Función**: `api_bom_download_excel_family` (Línea 7221)
- **Evidencia**: Path exacto '/api/bom/download-excel-family' en app\routes.py

### `/api/ecos/from-excel` (POST)
- **Función**: `api_ecos_from_excel` (Línea 7254)
- **Evidencia**: Path exacto '/api/ecos/from-excel' en app\routes.py

### `/api/ecos/from-excel-family` (POST)
- **Función**: `api_ecos_from_excel_family` (Línea 7332)
- **Evidencia**: Path exacto '/api/ecos/from-excel-family' en app\routes.py

### `/api/ecos/<int:eco_id>/scope` (GET)
- **Función**: `api_ecos_scope` (Línea 7442)
- **Evidencia**: MANUAL: Confirmado en uso por el usuario

### `/api/ecos/<int:eco_id>/diff` (GET)
- **Función**: `api_ecos_diff` (Línea 7455)
- **Evidencia**: Multi-segmento ['/api/ecos/', '/diff'] en app\routes.py: '@app.route("/api/ecos/<int:eco_id>/diff", methods=["GET"])'

### `/api/ecos/<int:eco_id>/items/import` (POST)
- **Función**: `api_ecos_import_items` (Línea 7498)
- **Evidencia**: Multi-segmento ['/api/ecos/', '/items/import'] en app\routes.py: '@app.route("/api/ecos/<int:eco_id>/items/import", methods=["POST"])'

### `/api/ecos/<int:eco_id>/approve` (POST)
- **Función**: `api_ecos_approve` (Línea 7521)
- **Evidencia**: Multi-segmento ['/api/ecos/', '/approve'] en app\routes.py: '@app.route("/api/ecos/<int:eco_id>/approve", methods=["POST"])'

### `/api/ecos/<int:eco_id>/cancel` (POST)
- **Función**: `api_ecos_cancel` (Línea 7541)
- **Evidencia**: MANUAL: Confirmado en uso por el usuario

### `/api/ecos/<int:eco_id>` (DELETE)
- **Función**: `api_ecos_delete` (Línea 7558)
- **Evidencia**: Path exacto '/api/ecos' en app\routes.py

### `/buscar_material_por_numero_parte` (GET)
- **Función**: `buscar_material_por_numero_parte` (Línea 7574)
- **Evidencia**: Función 'buscar_material_por_numero_parte' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/exportar_excel_bom` (GET)
- **Función**: `exportar_excel_bom` (Línea 7716)
- **Evidencia**: Función 'exportar_excel_bom' referenciada en README.md

### `/api/bom/update` (POST)
- **Función**: `api_bom_update` (Línea 7763)
- **Evidencia**: Función 'api_bom_update' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/bom/update-posiciones-assy` (POST)
- **Función**: `api_bom_update_posiciones_assy` (Línea 7852)
- **Evidencia**: Función 'api_bom_update_posiciones_assy' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/guardar_entrada_aereo` (POST)
- **Función**: `guardar_entrada_aereo` (Línea 7927)
- **Evidencia**: Función 'guardar_entrada_aereo' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/listar_entradas_aereo` (GET)
- **Función**: `listar_entradas_aereo` (Línea 7955)
- **Evidencia**: Función 'listar_entradas_aereo' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/guardar_material` (POST)
- **Función**: `guardar_material_route` (Línea 7966)
- **Evidencia**: Función 'guardar_material_route' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/listar_materiales` (GET)
- **Función**: `listar_materiales` (Línea 8007)
- **Evidencia**: Función 'listar_materiales' referenciada en README.md

### `/api/inventario/lotes_detalle` (POST)
- **Función**: `consultar_lotes_detalle` (Línea 8022)
- **Evidencia**: Función 'consultar_lotes_detalle' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/importar_excel` (POST)
- **Función**: `importar_excel` (Línea 8168)
- **Evidencia**: Función 'importar_excel' referenciada en README.md

### `/actualizar_campo_material` (POST)
- **Función**: `actualizar_campo_material` (Línea 8483)
- **Evidencia**: Función 'actualizar_campo_material' referenciada en README.md

### `/actualizar_material_completo` (POST)
- **Función**: `actualizar_material_completo_route` (Línea 8545)
- **Evidencia**: Función 'actualizar_material_completo_route' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/exportar_excel` (GET)
- **Función**: `exportar_excel` (Línea 8584)
- **Evidencia**: Función 'exportar_excel' referenciada en .kiro\steering\api-conventions.md

### `/obtener_codigos_material` (GET)
- **Función**: `obtener_codigos_material` (Línea 8683)
- **Evidencia**: Función 'obtener_codigos_material' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control_calidad` (GET)
- **Función**: `control_calidad` (Línea 8837)
- **Evidencia**: Función 'control_calidad' referenciada en .history\app\templates\MaterialTemplate_20260427162900.html

### `/guardar_control_almacen` (POST)
- **Función**: `guardar_control_almacen` (Línea 8843)
- **Evidencia**: Función 'guardar_control_almacen' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/obtener_secuencial_lote_interno` (POST)
- **Función**: `obtener_secuencial_lote_interno` (Línea 8876)
- **Evidencia**: Función 'obtener_secuencial_lote_interno' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/consultar_control_almacen` (GET)
- **Función**: `consultar_control_almacen` (Línea 8939)
- **Evidencia**: Función 'consultar_control_almacen' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/actualizar_control_almacen` (POST)
- **Función**: `actualizar_control_almacen` (Línea 9020)
- **Evidencia**: Función 'actualizar_control_almacen' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/guardar_cliente_seleccionado` (POST)
- **Función**: `guardar_cliente_seleccionado` (Línea 9206)
- **Evidencia**: Función 'guardar_cliente_seleccionado' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/cargar_cliente_seleccionado` (GET)
- **Función**: `cargar_cliente_seleccionado` (Línea 9231)
- **Evidencia**: Función 'cargar_cliente_seleccionado' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/actualizar_estado_desecho_almacen` (POST)
- **Función**: `actualizar_estado_desecho_almacen` (Línea 9247)
- **Evidencia**: Función 'actualizar_estado_desecho_almacen' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/obtener_siguiente_secuencial` (GET)
- **Función**: `obtener_siguiente_secuencial` (Línea 9308)
- **Evidencia**: Función 'obtener_siguiente_secuencial' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/informacion_basica/control_de_material` (GET)
- **Función**: `control_de_material_ajax` (Línea 9445)
- **Evidencia**: Función 'control_de_material_ajax' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/informacion_basica/control_de_bom` (GET)
- **Función**: `control_de_bom_ajax` (Línea 9456)
- **Evidencia**: Función 'control_de_bom_ajax' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/listas/informacion_basica` (GET)
- **Función**: `lista_informacion_basica` (Línea 9474)
- **Evidencia**: Función 'lista_informacion_basica' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/listas/control_material` (GET)
- **Función**: `lista_control_material` (Línea 9485)
- **Evidencia**: Función 'lista_control_material' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/listas/control_produccion` (GET)
- **Función**: `lista_control_produccion` (Línea 9496)
- **Evidencia**: Función 'lista_control_produccion' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control_produccion/control_embarque` (GET)
- **Función**: `control_embarque` (Línea 9507)
- **Evidencia**: Función 'control_embarque' referenciada en .history\app\templates\MaterialTemplate_20260427162900.html

### `/Control de embarque` (GET)
- **Función**: `control_embarque_ajax` (Línea 9518)
- **Evidencia**: Función 'control_embarque_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control_produccion/crear_plan` (GET)
- **Función**: `crear_plan_produccion` (Línea 9529)
- **Evidencia**: Función 'crear_plan_produccion' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control_produccion/plan_smt` (GET)
- **Función**: `plan_smt_ajax` (Línea 9546)
- **Evidencia**: Función 'plan_smt_ajax' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/work-orders` (GET)
- **Función**: `api_work_orders` (Línea 9597)
- **Evidencia**: Función 'api_work_orders' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/inventario/modelo/<codigo_modelo>` (GET)
- **Función**: `api_inventario_modelo` (Línea 9701)
- **Evidencia**: Función 'api_inventario_modelo' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smd` (POST)
- **Función**: `api_plan_smd_guardar` (Línea 9745)
- **Evidencia**: Función 'api_plan_smd_guardar' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/generar-plan-smd` (POST)
- **Función**: `api_generar_plan_smd` (Línea 9804)
- **Evidencia**: Función 'api_generar_plan_smd' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control_proceso/control_produccion_smt` (GET)
- **Función**: `control_produccion_smt_ajax` (Línea 10062)
- **Evidencia**: Función 'control_produccion_smt_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-bom-ajax` (GET)
- **Función**: `control_bom_ajax` (Línea 10077)
- **Evidencia**: Función 'control_bom_ajax' referenciada en graphify-out\.graphify_detect.json

### `/crear-plan-micom-ajax` (GET)
- **Función**: `crear_plan_micom_ajax` (Línea 10100)
- **Evidencia**: Función 'crear_plan_micom_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-operacion-linea-smt-ajax` (GET)
- **Función**: `control_operacion_linea_smt_ajax` (Línea 10111)
- **Evidencia**: Función 'control_operacion_linea_smt_ajax' referenciada en app\static\js\control-operacion-smt-ajax.js

### `/control-impresion-identificacion-smt-ajax` (GET)
- **Función**: `control_impresion_identificacion_smt_ajax` (Línea 10127)
- **Evidencia**: Función 'control_impresion_identificacion_smt_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-registro-identificacion-smt-ajax` (GET)
- **Función**: `control_registro_identificacion_smt_ajax` (Línea 10142)
- **Evidencia**: Función 'control_registro_identificacion_smt_ajax' referenciada en graphify-out\.graphify_detect.json

### `/historial-operacion-proceso-ajax` (GET)
- **Función**: `historial_operacion_proceso_ajax` (Línea 10157)
- **Evidencia**: Función 'historial_operacion_proceso_ajax' referenciada en graphify-out\.graphify_detect.json

### `/bom-management-process-ajax` (GET)
- **Función**: `bom_management_process_ajax` (Línea 10170)
- **Evidencia**: Función 'bom_management_process_ajax' referenciada en graphify-out\.graphify_detect.json

### `/reporte-diario-inspeccion-smt-ajax` (GET)
- **Función**: `reporte_diario_inspeccion_smt_ajax` (Línea 10181)
- **Evidencia**: Función 'reporte_diario_inspeccion_smt_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-diario-inspeccion-smt-ajax` (GET)
- **Función**: `control_diario_inspeccion_smt_ajax` (Línea 10194)
- **Evidencia**: Función 'control_diario_inspeccion_smt_ajax' referenciada en graphify-out\.graphify_detect.json

### `/reporte-diario-inspeccion-proceso-ajax` (GET)
- **Función**: `reporte_diario_inspeccion_proceso_ajax` (Línea 10207)
- **Evidencia**: Función 'reporte_diario_inspeccion_proceso_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-unidad-empaque-modelo-ajax` (GET)
- **Función**: `control_unidad_empaque_modelo_ajax` (Línea 10222)
- **Evidencia**: Función 'control_unidad_empaque_modelo_ajax' referenciada en graphify-out\.graphify_detect.json

### `/packaging-register-management-ajax` (GET)
- **Función**: `packaging_register_management_ajax` (Línea 10235)
- **Evidencia**: Función 'packaging_register_management_ajax' referenciada en graphify-out\.graphify_detect.json

### `/search-packaging-history-ajax` (GET)
- **Función**: `search_packaging_history_ajax` (Línea 10248)
- **Evidencia**: Función 'search_packaging_history_ajax' referenciada en graphify-out\.graphify_detect.json

### `/shipping-register-management-ajax` (GET)
- **Función**: `shipping_register_management_ajax` (Línea 10259)
- **Evidencia**: Función 'shipping_register_management_ajax' referenciada en graphify-out\.graphify_detect.json

### `/search-shipping-history-ajax` (GET)
- **Función**: `search_shipping_history_ajax` (Línea 10272)
- **Evidencia**: Función 'search_shipping_history_ajax' referenciada en graphify-out\.graphify_detect.json

### `/almacen-embarques-entradas-ajax` (GET)
- **Función**: `almacen_embarques_entradas_ajax` (Línea 13985)
- **Evidencia**: Función 'almacen_embarques_entradas_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-salida-lineas-ajax` (GET)
- **Función**: `control_salida_lineas_ajax` (Línea 13998)
- **Evidencia**: Path exacto '/control-salida-lineas-ajax' en app\routes.py

### `/almacen-embarques-salidas-ajax` (GET)
- **Función**: `almacen_embarques_salidas_ajax` (Línea 14009)
- **Evidencia**: Función 'almacen_embarques_salidas_ajax' referenciada en graphify-out\.graphify_detect.json

### `/almacen-embarques-retorno-ajax` (GET)
- **Función**: `almacen_embarques_retorno_ajax` (Línea 14022)
- **Evidencia**: Función 'almacen_embarques_retorno_ajax' referenciada en graphify-out\.graphify_detect.json

### `/almacen-embarques-movimientos-ajax` (GET)
- **Función**: `almacen_embarques_movimientos_ajax` (Línea 14039)
- **Evidencia**: Función 'almacen_embarques_movimientos_ajax' referenciada en graphify-out\.graphify_detect.json

### `/almacen-embarques-inventario-general-ajax` (GET)
- **Función**: `almacen_embarques_inventario_general_ajax` (Línea 14052)
- **Evidencia**: Función 'almacen_embarques_inventario_general_ajax' referenciada en graphify-out\.graphify_detect.json

### `/almacen-embarques-catalogo-ajax` (GET)
- **Función**: `almacen_embarques_catalogo_ajax` (Línea 14067)
- **Evidencia**: Función 'almacen_embarques_catalogo_ajax' referenciada en graphify-out\.graphify_detect.json

### `/api/almacen-embarques/entradas` (GET)
- **Función**: `api_almacen_embarques_entradas` (Línea 14084)
- **Evidencia**: Función 'api_almacen_embarques_entradas' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/control-salida-lineas` (GET)
- **Función**: `api_control_salida_lineas` (Línea 14095)
- **Evidencia**: Path exacto '/api/control-salida-lineas' en app\routes.py

### `/api/control-salida-lineas/export` (GET)
- **Función**: `export_control_salida_lineas` (Línea 14108)
- **Evidencia**: Path exacto '/api/control-salida-lineas/export' en app\routes.py

### `/api/almacen-embarques/entradas/export` (GET)
- **Función**: `export_almacen_embarques_entradas` (Línea 14133)
- **Evidencia**: Función 'export_almacen_embarques_entradas' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/salidas` (GET)
- **Función**: `api_almacen_embarques_salidas` (Línea 14163)
- **Evidencia**: Función 'api_almacen_embarques_salidas' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/salidas/export` (GET)
- **Función**: `export_almacen_embarques_salidas` (Línea 14174)
- **Evidencia**: Función 'export_almacen_embarques_salidas' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/<module_name>/ajustes/template` (GET)
- **Función**: `api_almacen_embarques_ajustes_template` (Línea 14205)
- **Evidencia**: Función 'api_almacen_embarques_ajustes_template' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/<module_name>/ajustes/preview` (POST)
- **Función**: `api_almacen_embarques_ajustes_preview` (Línea 14234)
- **Evidencia**: Función 'api_almacen_embarques_ajustes_preview' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/<module_name>/ajustes/confirm` (POST)
- **Función**: `api_almacen_embarques_ajustes_confirm` (Línea 14325)
- **Evidencia**: Función 'api_almacen_embarques_ajustes_confirm' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/<module_name>/ajustes/manual` (POST)
- **Función**: `api_almacen_embarques_ajustes_manual` (Línea 14345)
- **Evidencia**: Función 'api_almacen_embarques_ajustes_manual' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/<module_name>/ajustes/cancel` (POST)
- **Función**: `api_almacen_embarques_ajustes_cancel` (Línea 14367)
- **Evidencia**: Función 'api_almacen_embarques_ajustes_cancel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/salidas/<int:exit_id>/departure` (POST, PUT, PATCH)
- **Función**: `assign_almacen_embarques_departure` (Línea 14426)
- **Evidencia**: Función 'assign_almacen_embarques_departure' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/departures/history` (GET)
- **Función**: `api_almacen_embarques_departure_history` (Línea 14455)
- **Evidencia**: Función 'api_almacen_embarques_departure_history' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/retorno` (GET)
- **Función**: `api_almacen_embarques_retorno` (Línea 14474)
- **Evidencia**: Función 'api_almacen_embarques_retorno' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/retorno/export` (GET)
- **Función**: `export_almacen_embarques_retorno` (Línea 14485)
- **Evidencia**: Función 'export_almacen_embarques_retorno' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/retorno/print-pdf` (POST)
- **Función**: `export_almacen_embarques_retorno_print_pdf` (Línea 14560)
- **Evidencia**: Función 'export_almacen_embarques_retorno_print_pdf' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/movimientos` (GET)
- **Función**: `api_almacen_embarques_movimientos` (Línea 14587)
- **Evidencia**: Función 'api_almacen_embarques_movimientos' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/movimientos/export` (GET)
- **Función**: `export_almacen_embarques_movimientos` (Línea 14605)
- **Evidencia**: Función 'export_almacen_embarques_movimientos' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/movimientos/<movement_type>/<int:record_id>` (GET)
- **Función**: `api_almacen_embarques_movimiento_detalle` (Línea 14637)
- **Evidencia**: Función 'api_almacen_embarques_movimiento_detalle' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/inventario-general` (GET)
- **Función**: `api_almacen_embarques_inventario_general` (Línea 14722)
- **Evidencia**: Función 'api_almacen_embarques_inventario_general' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/catalogo` (GET)
- **Función**: `api_almacen_embarques_catalogo` (Línea 14736)
- **Evidencia**: Función 'api_almacen_embarques_catalogo' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/catalogo` (POST)
- **Función**: `api_almacen_embarques_catalogo_create` (Línea 14749)
- **Evidencia**: Función 'api_almacen_embarques_catalogo_create' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/catalogo/<int:catalog_id>` (PATCH)
- **Función**: `api_almacen_embarques_catalogo_update` (Línea 14763)
- **Evidencia**: Función 'api_almacen_embarques_catalogo_update' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/catalogo/<int:catalog_id>` (DELETE)
- **Función**: `api_almacen_embarques_catalogo_delete` (Línea 14779)
- **Evidencia**: Función 'api_almacen_embarques_catalogo_delete' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/catalogo/export` (GET)
- **Función**: `export_almacen_embarques_catalogo` (Línea 14795)
- **Evidencia**: Función 'export_almacen_embarques_catalogo' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/inventario-general/export` (GET)
- **Función**: `export_almacen_embarques_inventario_general` (Línea 14821)
- **Evidencia**: Función 'export_almacen_embarques_inventario_general' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/inventario-general/cierre/bootstrap` (GET)
- **Función**: `api_almacen_embarques_inventario_cierre_bootstrap` (Línea 14852)
- **Evidencia**: Función 'api_almacen_embarques_inventario_cierre_bootstrap' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/inventario-general/cierre/template` (GET)
- **Función**: `api_almacen_embarques_inventario_cierre_template` (Línea 14876)
- **Evidencia**: Función 'api_almacen_embarques_inventario_cierre_template' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/inventario-general/cierre/preview` (POST)
- **Función**: `api_almacen_embarques_inventario_cierre_preview` (Línea 14903)
- **Evidencia**: Función 'api_almacen_embarques_inventario_cierre_preview' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/inventario-general/cierre/confirm` (POST)
- **Función**: `api_almacen_embarques_inventario_cierre_confirm` (Línea 14965)
- **Evidencia**: Función 'api_almacen_embarques_inventario_cierre_confirm' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/inventario-general/cierre/cancel` (POST)
- **Función**: `api_almacen_embarques_inventario_cierre_cancel` (Línea 15101)
- **Evidencia**: Función 'api_almacen_embarques_inventario_cierre_cancel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/inventario-general/cierre/history/<int:batch_id>` (GET)
- **Función**: `api_almacen_embarques_inventario_cierre_history_detail` (Línea 15176)
- **Evidencia**: Función 'api_almacen_embarques_inventario_cierre_history_detail' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/almacen-embarques/inventario-general/cierre/history/<int:batch_id>/export` (GET)
- **Función**: `export_almacen_embarques_inventario_cierre_report` (Línea 15223)
- **Evidencia**: Función 'export_almacen_embarques_inventario_cierre_report' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/registro-movimiento-identificacion-ajax` (GET)
- **Función**: `registro_movimiento_identificacion_ajax` (Línea 15754)
- **Evidencia**: Función 'registro_movimiento_identificacion_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-otras-identificaciones-ajax` (GET)
- **Función**: `control_otras_identificaciones_ajax` (Línea 15767)
- **Evidencia**: Función 'control_otras_identificaciones_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-movimiento-ns-producto-ajax` (GET)
- **Función**: `control_movimiento_ns_producto_ajax` (Línea 15780)
- **Evidencia**: Función 'control_movimiento_ns_producto_ajax' referenciada en graphify-out\.graphify_detect.json

### `/model-sn-management-ajax` (GET)
- **Función**: `model_sn_management_ajax` (Línea 15793)
- **Evidencia**: Función 'model_sn_management_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-scrap-ajax` (GET)
- **Función**: `control_scrap_ajax` (Línea 15804)
- **Evidencia**: Función 'control_scrap_ajax' referenciada en graphify-out\.graphify_detect.json

### `/line-material-status-ajax` (GET)
- **Función**: `line_material_status_ajax` (Línea 15816)
- **Evidencia**: Función 'line_material_status_ajax' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control-mask-metal-ajax` (GET)
- **Función**: `control_mask_metal_ajax` (Línea 15829)
- **Evidencia**: Función 'control_mask_metal_ajax' referenciada en .kiro\steering\modules-metal-mask.md

### `/control-squeegee-ajax` (GET)
- **Función**: `control_squeegee_ajax` (Línea 15840)
- **Evidencia**: Función 'control_squeegee_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-caja-mask-metal-ajax` (GET)
- **Función**: `control_caja_mask_metal_ajax` (Línea 15851)
- **Evidencia**: Función 'control_caja_mask_metal_ajax' referenciada en graphify-out\.graphify_detect.json

### `/estandares-soldadura-ajax` (GET)
- **Función**: `estandares_soldadura_ajax` (Línea 15864)
- **Evidencia**: Función 'estandares_soldadura_ajax' referenciada en graphify-out\.graphify_detect.json

### `/registro-recibo-soldadura-ajax` (GET)
- **Función**: `registro_recibo_soldadura_ajax` (Línea 15877)
- **Evidencia**: Función 'registro_recibo_soldadura_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-salida-soldadura-ajax` (GET)
- **Función**: `control_salida_soldadura_ajax` (Línea 15890)
- **Evidencia**: Función 'control_salida_soldadura_ajax' referenciada en graphify-out\.graphify_detect.json

### `/historial-tension-mask-metal-ajax` (GET)
- **Función**: `historial_tension_mask_metal_ajax` (Línea 15903)
- **Evidencia**: Función 'historial_tension_mask_metal_ajax' referenciada en graphify-out\.graphify_detect.json

### `/listas/control_proceso` (GET)
- **Función**: `lista_control_proceso` (Línea 15942)
- **Evidencia**: Función 'lista_control_proceso' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/listas/control_calidad` (GET)
- **Función**: `lista_control_calidad` (Línea 15953)
- **Evidencia**: Función 'lista_control_calidad' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/listas/control_resultados` (GET)
- **Función**: `lista_control_resultados` (Línea 15964)
- **Evidencia**: Función 'lista_control_resultados' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-aoi` (GET)
- **Función**: `historial_aoi` (Línea 15975)
- **Evidencia**: Función 'historial_aoi' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-ict-ajax` (GET)
- **Función**: `historial_ict_ajax` (Línea 15986)
- **Evidencia**: Función 'historial_ict_ajax' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-maquina-ict-pass-fail` (GET)
- **Función**: `historial_maquina_ict_pass_fail` (Línea 15996)
- **Evidencia**: Función 'historial_maquina_ict_pass_fail' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-maquina-ict-pass-fail-ajax` (GET)
- **Función**: `historial_maquina_ict_pass_fail` (Línea 15997)
- **Evidencia**: Función 'historial_maquina_ict_pass_fail' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/pass-fail` (GET)
- **Función**: `ict_pass_fail_api` (Línea 16089)
- **Evidencia**: Función 'ict_pass_fail_api' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/pass-fail/detail` (GET)
- **Función**: `ict_pass_fail_detail_api` (Línea 16127)
- **Evidencia**: Función 'ict_pass_fail_detail_api' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/pass-fail/export` (GET)
- **Función**: `ict_pass_fail_export` (Línea 16274)
- **Evidencia**: Función 'ict_pass_fail_export' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-cambios-parametros-ict-ajax` (GET)
- **Función**: `historial_cambios_parametros_ict_ajax` (Línea 16383)
- **Evidencia**: Función 'historial_cambios_parametros_ict_ajax' referenciada en .history\app\templates\Control de resultados\plan_20260429115351.md

### `/api/ict/param-changes/progress` (GET)
- **Función**: `ict_param_changes_progress` (Línea 16912)
- **Evidencia**: Función 'ict_param_changes_progress' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/param-changes` (GET)
- **Función**: `ict_param_changes_api` (Línea 16932)
- **Evidencia**: Función 'ict_param_changes_api' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/param-changes/export` (GET)
- **Función**: `ict_param_changes_export` (Línea 16966)
- **Evidencia**: Función 'ict_param_changes_export' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/param-changes/detail` (GET)
- **Función**: `ict_param_changes_detail` (Línea 17065)
- **Evidencia**: Función 'ict_param_changes_detail' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-aoi-ajax` (GET)
- **Función**: `historial_aoi_ajax` (Línea 17205)
- **Evidencia**: Función 'historial_aoi_ajax' referenciada en app\templates\Control de resultados\Historial AOI.html

### `/listas/control_reporte` (GET)
- **Función**: `lista_control_reporte` (Línea 17216)
- **Evidencia**: Función 'lista_control_reporte' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/listas/configuracion_programa` (GET)
- **Función**: `lista_configuracion_programa` (Línea 17227)
- **Evidencia**: Función 'lista_configuracion_programa' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/material/info` (GET)
- **Función**: `material_info` (Línea 17238)
- **Evidencia**: Función 'material_info' referenciada en app\db_mysql.py

### `/consultar_especificacion_por_numero_parte` (GET)
- **Función**: `consultar_especificacion_por_numero_parte` (Línea 17249)
- **Evidencia**: Función 'consultar_especificacion_por_numero_parte' referenciada en .history\app\templates\MaterialTemplate_20260427162900.html

### `/material/control_calidad` (GET)
- **Función**: `material_control_calidad` (Línea 17398)
- **Evidencia**: Función 'material_control_calidad' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/material/historial_inventario` (GET)
- **Función**: `material_historial_inventario` (Línea 17409)
- **Evidencia**: Función 'material_historial_inventario' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/material/registro_material` (GET)
- **Función**: `material_registro_material` (Línea 17420)
- **Evidencia**: Función 'material_registro_material' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/material/estatus_material` (GET)
- **Función**: `material_estatus_material` (Línea 17431)
- **Evidencia**: Función 'material_estatus_material' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/estatus_material/consultar` (POST)
- **Función**: `consultar_estatus_material` (Línea 17442)
- **Evidencia**: Función 'consultar_estatus_material' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/obtener_reglas_escaneo` (GET)
- **Función**: `obtener_reglas_escaneo` (Línea 17543)
- **Evidencia**: Función 'obtener_reglas_escaneo' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/buscar_codigo_recibido` (GET)
- **Función**: `buscar_codigo_recibido` (Línea 17564)
- **Evidencia**: Función 'buscar_codigo_recibido' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/guardar_salida_lote` (POST)
- **Función**: `guardar_salida_lote` (Línea 17619)
- **Evidencia**: Función 'guardar_salida_lote' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/consultar_historial_salidas` (GET)
- **Función**: `consultar_historial_salidas` (Línea 17736)
- **Evidencia**: Función 'consultar_historial_salidas' referenciada en .history\app\templates\MaterialTemplate_20260427162900.html

### `/buscar_material_por_codigo` (GET)
- **Función**: `buscar_material_por_codigo` (Línea 17887)
- **Evidencia**: Función 'buscar_material_por_codigo' referenciada en .history\app\templates\MaterialTemplate_20260427162900.html

### `/verificar_stock_rapido` (GET)
- **Función**: `verificar_stock_rapido` (Línea 17975)
- **Evidencia**: Función 'verificar_stock_rapido' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/procesar_salida_material` (POST)
- **Función**: `procesar_salida_material` (Línea 18047)
- **Evidencia**: Función 'procesar_salida_material' referenciada en .history\app\templates\MaterialTemplate_20260427162900.html

### `/forzar_actualizacion_inventario/<numero_parte>` (POST)
- **Función**: `forzar_actualizacion_inventario` (Línea 18202)
- **Evidencia**: Función 'forzar_actualizacion_inventario' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/recalcular_inventario_general` (POST)
- **Función**: `recalcular_inventario_general_endpoint` (Línea 18291)
- **Evidencia**: Función 'recalcular_inventario_general_endpoint' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/obtener_inventario_general` (GET)
- **Función**: `obtener_inventario_general_endpoint` (Línea 18355)
- **Evidencia**: Función 'obtener_inventario_general_endpoint' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/verificar_estado_inventario` (GET)
- **Función**: `verificar_estado_inventario` (Línea 18372)
- **Evidencia**: Función 'verificar_estado_inventario' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/test_modelos` (GET)
- **Función**: `test_modelos` (Línea 18451)
- **Evidencia**: Función 'test_modelos' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/inventario/consultar` (POST)
- **Función**: `consultar_inventario_general` (Línea 18458)
- **Evidencia**: Función 'consultar_inventario_general' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/inventario/historial` (POST)
- **Función**: `obtener_historial_numero_parte` (Línea 18608)
- **Evidencia**: Función 'obtener_historial_numero_parte' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/inventario/historial/<numero_parte>` (GET)
- **Función**: `obtener_historial_numero_parte_get` (Línea 18825)
- **Evidencia**: Función 'obtener_historial_numero_parte_get' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/inventario/lotes` (POST)
- **Función**: `obtener_lotes_numero_parte` (Línea 19040)
- **Evidencia**: Función 'obtener_lotes_numero_parte' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/inventario/lotes/<numero_parte>` (GET)
- **Función**: `obtener_lotes_numero_parte_get` (Línea 19204)
- **Evidencia**: Función 'obtener_lotes_numero_parte_get' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/templates/LISTAS/<filename>` (GET)
- **Función**: `serve_list_template` (Línea 19365)
- **Evidencia**: Función 'serve_list_template' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/verificar_permiso_dropdown` (POST)
- **Función**: `verificar_permiso_dropdown` (Línea 19404)
- **Evidencia**: Función 'verificar_permiso_dropdown' referenciada en app\user_admin.py

### `/obtener_permisos_usuario_actual` (GET)
- **Función**: `obtener_permisos_usuario_actual` (Línea 19457)
- **Evidencia**: Función 'obtener_permisos_usuario_actual' referenciada en app\user_admin.py

### `/csv-viewer` (GET)
- **Función**: `csv_viewer` (Línea 19506)
- **Evidencia**: Función 'csv_viewer' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-cambio-material-smt` (GET)
- **Función**: `historial_cambio_material_smt` (Línea 19518)
- **Evidencia**: Función 'historial_cambio_material_smt' referenciada en .kiro\steering\database.md

### `/historial-cambio-material-smt-ajax` (GET)
- **Función**: `historial_cambio_material_smt_ajax` (Línea 19529)
- **Evidencia**: Función 'historial_cambio_material_smt_ajax' referenciada en app\smt_routes_clean.py

### `/api/csv_data` (GET)
- **Función**: `get_csv_data` (Línea 19542)
- **Evidencia**: Función 'get_csv_data' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/csv_stats` (GET)
- **Función**: `get_csv_stats` (Línea 19662)
- **Evidencia**: Función 'get_csv_stats' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/filter_data` (POST)
- **Función**: `filter_csv_data` (Línea 19911)
- **Evidencia**: Función 'filter_csv_data' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/guardar_regla_trazabilidad` (POST)
- **Función**: `guardar_regla_trazabilidad` (Línea 20170)
- **Evidencia**: Función 'guardar_regla_trazabilidad' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control_salida/estado` (GET)
- **Función**: `control_salida_estado` (Línea 20289)
- **Evidencia**: Función 'control_salida_estado' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control_salida/configuracion` (GET, POST)
- **Función**: `control_salida_configuracion` (Línea 20347)
- **Evidencia**: Función 'control_salida_configuracion' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control_salida/validar_stock` (POST)
- **Función**: `control_salida_validar_stock` (Línea 20407)
- **Evidencia**: Función 'control_salida_validar_stock' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control_salida/reporte_diario` (GET)
- **Función**: `control_salida_reporte_diario` (Línea 20481)
- **Evidencia**: Función 'control_salida_reporte_diario' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/importar_excel_plan_produccion` (POST)
- **Función**: `importar_excel_plan_produccion` (Línea 20559)
- **Evidencia**: Función 'importar_excel_plan_produccion' referenciada en app\static\js\crear-plan-produccion.js

### `/control_salida/debug/test_connection` (GET)
- **Función**: `control_salida_test_connection` (Línea 20923)
- **Evidencia**: Función 'control_salida_test_connection' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/importar_excel_almacen` (POST)
- **Función**: `importar_excel_almacen` (Línea 21002)
- **Evidencia**: Función 'importar_excel_almacen' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/produccion/info` (GET)
- **Función**: `produccion_info` (Línea 21115)
- **Evidencia**: Función 'produccion_info' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/material/recibo_pago` (GET)
- **Función**: `material_recibo_pago` (Línea 21129)
- **Evidencia**: Función 'material_recibo_pago' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/material/material_sustituto` (GET)
- **Función**: `material_material_sustituto` (Línea 21140)
- **Evidencia**: Función 'material_material_sustituto' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/material/consultar_peps` (GET)
- **Función**: `material_consultar_peps` (Línea 21151)
- **Evidencia**: Función 'material_consultar_peps' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/material/longterm_inventory` (GET)
- **Función**: `material_longterm_inventory` (Línea 21162)
- **Evidencia**: Función 'material_longterm_inventory' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/material/ajuste_numero` (GET)
- **Función**: `material_ajuste_numero` (Línea 21175)
- **Evidencia**: Función 'material_ajuste_numero' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/importar_excel_salida` (POST)
- **Función**: `importar_excel_salida` (Línea 21186)
- **Evidencia**: Función 'importar_excel_salida' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/importar_excel_retorno` (POST)
- **Función**: `importar_excel_retorno` (Línea 21298)
- **Evidencia**: Función 'importar_excel_retorno' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/importar_excel_registro` (POST)
- **Función**: `importar_excel_registro` (Línea 21409)
- **Evidencia**: Función 'importar_excel_registro' referenciada en app\templates\Control de material\Registro de material real.html

### `/importar_excel_estatus_inventario` (POST)
- **Función**: `importar_excel_estatus_inventario` (Línea 21520)
- **Evidencia**: Función 'importar_excel_estatus_inventario' referenciada en app\templates\Control de material\Estatus de material.html

### `/importar_excel_estatus_recibido` (POST)
- **Función**: `importar_excel_estatus_recibido` (Línea 21631)
- **Evidencia**: Función 'importar_excel_estatus_recibido' referenciada en app\templates\Control de material\Estatus de material.html

### `/importar_excel_historial` (POST)
- **Función**: `importar_excel_historial` (Línea 21743)
- **Evidencia**: Función 'importar_excel_historial' referenciada en app\templates\Control de material\Historial de inventario real.html

### `/api/wo/exportar` (GET)
- **Función**: `exportar_wos_excel` (Línea 21859)
- **Evidencia**: Función 'exportar_wos_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smd/import` (POST)
- **Función**: `api_plan_smd_import` (Línea 21988)
- **Evidencia**: Función 'api_plan_smd_import' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/inventario` (GET)
- **Función**: `api_inventario` (Línea 22140)
- **Evidencia**: Función 'api_inventario' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-micom/generar` (POST)
- **Función**: `api_plan_micom_generar` (Línea 22195)
- **Evidencia**: Función 'api_plan_micom_generar' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control-resultado-reparacion-ajax` (GET)
- **Función**: `control_resultado_reparacion_ajax` (Línea 22267)
- **Evidencia**: Función 'control_resultado_reparacion_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-item-reparado-ajax` (GET)
- **Función**: `control_item_reparado_ajax` (Línea 22274)
- **Evidencia**: Función 'control_item_reparado_ajax' referenciada en graphify-out\.graphify_detect.json

### `/historial-cambio-material-maquina-ajax` (GET)
- **Función**: `historial_cambio_material_maquina_ajax` (Línea 22281)
- **Evidencia**: Función 'historial_cambio_material_maquina_ajax' referenciada en app\templates\Control de calidad\historial_cambio_material_maquina_ajax.html

### `/api/historial-cambio-material-maquina` (GET)
- **Función**: `api_historial_cambio_material_maquina` (Línea 22290)
- **Evidencia**: Función 'api_historial_cambio_material_maquina' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/historial_smt_latest` (GET)
- **Función**: `api_historial_smt_latest` (Línea 22417)
- **Evidencia**: Función 'api_historial_smt_latest' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/historial_smt_latest_v2` (GET)
- **Función**: `api_historial_smt_latest_v2` (Línea 22521)
- **Evidencia**: Función 'api_historial_smt_latest_v2' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/masks/info` (GET)
- **Función**: `api_masks_info` (Línea 22620)
- **Evidencia**: Función 'api_masks_info' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-uso-pegamento-soldadura-ajax` (GET)
- **Función**: `historial_uso_pegamento_soldadura_ajax` (Línea 22692)
- **Evidencia**: Función 'historial_uso_pegamento_soldadura_ajax' referenciada en graphify-out\.graphify_detect.json

### `/api/metal-mask/history` (POST)
- **Función**: `api_save_metal_mask_history` (Línea 22704)
- **Evidencia**: Función 'api_save_metal_mask_history' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/metal-mask/history` (GET)
- **Función**: `api_get_metal_mask_history` (Línea 22801)
- **Evidencia**: Función 'api_get_metal_mask_history' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/metal-mask/update-used-count` (POST)
- **Función**: `api_update_metal_mask_used_count` (Línea 22895)
- **Evidencia**: Función 'api_update_metal_mask_used_count' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-uso-mask-metal-ajax` (GET)
- **Función**: `historial_uso_mask_metal_ajax` (Línea 23057)
- **Evidencia**: Función 'historial_uso_mask_metal_ajax' referenciada en graphify-out\.graphify_detect.json

### `/historial-uso-squeegee-ajax` (GET)
- **Función**: `historial_uso_squeegee_ajax` (Línea 23064)
- **Evidencia**: Función 'historial_uso_squeegee_ajax' referenciada en graphify-out\.graphify_detect.json

### `/process-interlock-history-ajax` (GET)
- **Función**: `process_interlock_history_ajax` (Línea 23071)
- **Evidencia**: Función 'process_interlock_history_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-master-sample-smt-ajax` (GET)
- **Función**: `control_master_sample_smt_ajax` (Línea 23078)
- **Evidencia**: Función 'control_master_sample_smt_ajax' referenciada en graphify-out\.graphify_detect.json

### `/historial-inspeccion-master-sample-smt-ajax` (GET)
- **Función**: `historial_inspeccion_master_sample_smt_ajax` (Línea 23085)
- **Evidencia**: Función 'historial_inspeccion_master_sample_smt_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-inspeccion-oqc-ajax` (GET)
- **Función**: `control_inspeccion_oqc_ajax` (Línea 23094)
- **Evidencia**: Función 'control_inspeccion_oqc_ajax' referenciada en graphify-out\.graphify_detect.json

### `/historial-liberacion-lqc-ajax` (GET)
- **Función**: `historial_liberacion_lqc_ajax` (Línea 23101)
- **Evidencia**: Función 'historial_liberacion_lqc_ajax' referenciada en graphify-out\.graphify_detect.json

### `/api/smt-scanner/lineas` (GET)
- **Función**: `api_smt_scanner_lineas` (Línea 23132)
- **Evidencia**: Función 'api_smt_scanner_lineas' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/smt-scanner/datos` (GET)
- **Función**: `api_smt_scanner_datos` (Línea 23244)
- **Evidencia**: Función 'api_smt_scanner_datos' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/ajuste-numero-parte-ajax` (GET)
- **Función**: `ajuste_numero_parte_ajax` (Línea 23423)
- **Evidencia**: Función 'ajuste_numero_parte_ajax' referenciada en graphify-out\.graphify_detect.json

### `/consultar-peps-ajax` (GET)
- **Función**: `consultar_peps_ajax` (Línea 23430)
- **Evidencia**: Función 'consultar_peps_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-entrada-salida-material-ajax` (GET)
- **Función**: `control_entrada_salida_material_ajax` (Línea 23437)
- **Evidencia**: Función 'control_entrada_salida_material_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-recibo-refacciones-ajax` (GET)
- **Función**: `control_recibo_refacciones_ajax` (Línea 23446)
- **Evidencia**: Función 'control_recibo_refacciones_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-salida-refacciones-ajax` (GET)
- **Función**: `control_salida_refacciones_ajax` (Línea 23453)
- **Evidencia**: Función 'control_salida_refacciones_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-total-material-ajax` (GET)
- **Función**: `control_total_material_ajax` (Línea 23460)
- **Evidencia**: Función 'control_total_material_ajax' referenciada en graphify-out\.graphify_detect.json

### `/estandares-refacciones-ajax` (GET)
- **Función**: `estandares_refacciones_ajax` (Línea 23467)
- **Evidencia**: Función 'estandares_refacciones_ajax' referenciada en graphify-out\.graphify_detect.json

### `/estatus-inventario-refacciones-ajax` (GET)
- **Función**: `estatus_inventario_refacciones_ajax` (Línea 23474)
- **Evidencia**: Función 'estatus_inventario_refacciones_ajax' referenciada en graphify-out\.graphify_detect.json

### `/estatus-material-ajax` (GET)
- **Función**: `estatus_material_ajax` (Línea 23483)
- **Evidencia**: Función 'estatus_material_ajax' referenciada en graphify-out\.graphify_detect.json

### `/estatus-material-msl-ajax` (GET)
- **Función**: `estatus_material_msl_ajax` (Línea 23490)
- **Evidencia**: Función 'estatus_material_msl_ajax' referenciada en graphify-out\.graphify_detect.json

### `/historial-inventario-real-ajax` (GET)
- **Función**: `historial_inventario_real_ajax` (Línea 23497)
- **Evidencia**: Función 'historial_inventario_real_ajax' referenciada en graphify-out\.graphify_detect.json

### `/inventario-rollos-smd-ajax` (GET)
- **Función**: `inventario_rollos_smd_ajax` (Línea 23504)
- **Evidencia**: Función 'inventario_rollos_smd_ajax' referenciada en graphify-out\.graphify_detect.json

### `/longterm-inventory-ajax` (GET)
- **Función**: `longterm_inventory_ajax` (Línea 23511)
- **Evidencia**: Función 'longterm_inventory_ajax' referenciada en graphify-out\.graphify_detect.json

### `/material-sustituto-ajax` (GET)
- **Función**: `material_sustituto_ajax` (Línea 23518)
- **Evidencia**: Función 'material_sustituto_ajax' referenciada en graphify-out\.graphify_detect.json

### `/recibo-pago-material-ajax` (GET)
- **Función**: `recibo_pago_material_ajax` (Línea 23525)
- **Evidencia**: Función 'recibo_pago_material_ajax' referenciada en graphify-out\.graphify_detect.json

### `/registro-material-real-ajax` (GET)
- **Función**: `registro_material_real_ajax` (Línea 23532)
- **Evidencia**: Función 'registro_material_real_ajax' referenciada en graphify-out\.graphify_detect.json

### `/api/inventario_general` (GET)
- **Función**: `api_inventario_general` (Línea 23542)
- **Evidencia**: Función 'api_inventario_general' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ubicacion` (GET)
- **Función**: `api_ubicacion` (Línea 23589)
- **Evidencia**: Función 'api_ubicacion' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/movimientos` (GET)
- **Función**: `api_movimientos` (Línea 23652)
- **Evidencia**: Función 'api_movimientos' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/snapshot_inventario/fechas` (GET)
- **Función**: `api_snapshot_inv_fechas` (Línea 23727)
- **Evidencia**: Función 'api_snapshot_inv_fechas' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/snapshot_inventario/general` (GET)
- **Función**: `api_snapshot_inv_general` (Línea 23752)
- **Evidencia**: Función 'api_snapshot_inv_general' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/snapshot_inventario/ubicacion` (GET)
- **Función**: `api_snapshot_inv_ubicacion` (Línea 23787)
- **Evidencia**: Función 'api_snapshot_inv_ubicacion' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/snapshot_inventario/trigger` (POST)
- **Función**: `api_snapshot_inv_trigger` (Línea 23819)
- **Evidencia**: Función 'api_snapshot_inv_trigger' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/mysql-proxy.php` (POST, GET, OPTIONS)
- **Función**: `mysql_proxy_php` (Línea 23846)
- **Evidencia**: Función 'mysql_proxy_php' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/mysql` (POST, GET, OPTIONS)
- **Función**: `api_mysql_simple` (Línea 23888)
- **Evidencia**: Función 'api_mysql_simple' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/status` (GET)
- **Función**: `api_status` (Línea 23954)
- **Evidencia**: Función 'api_status' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/plan-smd-diario` (GET)
- **Función**: `plan_smd_diario` (Línea 23987)
- **Evidencia**: Función 'plan_smd_diario' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control-operacion-linea-smt` (GET)
- **Función**: `control_operacion_linea_smt` (Línea 23993)
- **Evidencia**: Función 'control_operacion_linea_smt' referenciada en app\templates\LISTAS\LISTA_CONTROL_DE_PROCESO.html

### `/api/plan-smd-diario` (GET)
- **Función**: `api_plan_smd_diario` (Línea 23999)
- **Evidencia**: Función 'api_plan_smd_diario' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/visor-mysql` (GET)
- **Función**: `visor_mysql` (Línea 24086)
- **Evidencia**: Función 'visor_mysql' referenciada en .history\app\templates\visor_mysql_20260119114201.html

### `/control-modelos-visor-ajax` (GET)
- **Función**: `control_modelos_visor_ajax` (Línea 24096)
- **Evidencia**: Función 'control_modelos_visor_ajax' referenciada en graphify-out\.graphify_detect.json

### `/control-modelos-smt-ajax` (GET)
- **Función**: `control_modelos_smt_ajax` (Línea 24120)
- **Evidencia**: Función 'control_modelos_smt_ajax' referenciada en graphify-out\.graphify_detect.json

### `/api/mysql/columns` (GET)
- **Función**: `api_mysql_columns` (Línea 24136)
- **Evidencia**: Función 'api_mysql_columns' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/mysql/data` (GET)
- **Función**: `api_mysql_data` (Línea 24163)
- **Evidencia**: Función 'api_mysql_data' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/mysql/update` (POST)
- **Función**: `api_mysql_update` (Línea 24264)
- **Evidencia**: Función 'api_mysql_update' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/mysql/create` (POST)
- **Función**: `api_mysql_create` (Línea 24424)
- **Evidencia**: Función 'api_mysql_create' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/mysql/usuario-actual` (GET)
- **Función**: `api_mysql_usuario_actual` (Línea 24517)
- **Evidencia**: Función 'api_mysql_usuario_actual' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/mysql/delete` (POST)
- **Función**: `api_mysql_delete` (Línea 24537)
- **Evidencia**: Función 'api_mysql_delete' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-smd/list` (GET)
- **Función**: `api_plan_smd_list` (Línea 24675)
- **Evidencia**: Función 'api_plan_smd_list' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-run/start` (POST)
- **Función**: `api_plan_run_start` (Línea 24893)
- **Evidencia**: Función 'api_plan_run_start' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-run/end` (POST)
- **Función**: `api_plan_run_end` (Línea 25081)
- **Evidencia**: Función 'api_plan_run_end' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-run/pause` (POST)
- **Función**: `api_plan_run_pause` (Línea 25189)
- **Evidencia**: Función 'api_plan_run_pause' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-run/resume` (POST)
- **Función**: `api_plan_run_resume` (Línea 25231)
- **Evidencia**: Función 'api_plan_run_resume' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/plan-run/status` (GET)
- **Función**: `api_plan_run_status` (Línea 25272)
- **Evidencia**: Función 'api_plan_run_status' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control/metal-mask` (GET)
- **Función**: `pagina_control_metal_mask` (Línea 25428)
- **Evidencia**: Función 'pagina_control_metal_mask' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/control/metal-mask/caja` (GET)
- **Función**: `pagina_control_caja_metal_mask` (Línea 25438)
- **Evidencia**: Función 'pagina_control_caja_metal_mask' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/masks` (GET)
- **Función**: `api_list_masks` (Línea 25451)
- **Evidencia**: Función 'api_list_masks' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/masks` (POST)
- **Función**: `api_create_mask` (Línea 25491)
- **Evidencia**: Función 'api_create_mask' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/masks/<int:mask_id>` (PUT)
- **Función**: `api_update_mask` (Línea 25537)
- **Evidencia**: Función 'api_update_mask' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/storage` (GET)
- **Función**: `api_get_storage` (Línea 25583)
- **Evidencia**: Función 'api_get_storage' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/storage` (POST)
- **Función**: `api_add_storage` (Línea 25635)
- **Evidencia**: Función 'api_add_storage' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/storage/<int:storage_id>` (PUT)
- **Función**: `api_update_storage` (Línea 25676)
- **Evidencia**: Función 'api_update_storage' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/bom-smt-data` (GET)
- **Función**: `api_bom_smt_data` (Línea 25716)
- **Evidencia**: Función 'api_bom_smt_data' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-vision` (GET)
- **Función**: `historial_vision` (Línea 27084)
- **Evidencia**: Función 'historial_vision' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-vision-ajax` (GET)
- **Función**: `historial_vision` (Línea 27085)
- **Evidencia**: Función 'historial_vision' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-vision-pass-fail` (GET)
- **Función**: `historial_vision_pass_fail` (Línea 27096)
- **Evidencia**: Función 'historial_vision_pass_fail' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-vision-pass-fail-ajax` (GET)
- **Función**: `historial_vision_pass_fail` (Línea 27097)
- **Evidencia**: Función 'historial_vision_pass_fail' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/vision/data` (GET)
- **Función**: `vision_data_api` (Línea 27108)
- **Evidencia**: Función 'vision_data_api' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/vision/pass-fail-summary` (GET)
- **Función**: `vision_pass_fail_summary_api` (Línea 27140)
- **Evidencia**: Función 'vision_pass_fail_summary_api' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/vision/pass-fail-summary/export` (GET)
- **Función**: `export_vision_pass_fail_summary_excel` (Línea 27176)
- **Evidencia**: Función 'export_vision_pass_fail_summary_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/vision/image-info` (GET)
- **Función**: `vision_image_info_api` (Línea 27278)
- **Evidencia**: Función 'vision_image_info_api' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/vision/image-file` (GET)
- **Función**: `vision_image_file_api` (Línea 27322)
- **Evidencia**: Función 'vision_image_file_api' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/vision/export` (GET)
- **Función**: `export_vision_excel` (Línea 27388)
- **Evidencia**: Función 'export_vision_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/historial-ict` (GET)
- **Función**: `ict_front_full_defects2` (Línea 27475)
- **Evidencia**: Función 'ict_front_full_defects2' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/ict/front-full-defects2` (GET)
- **Función**: `ict_front_full_defects2` (Línea 27476)
- **Evidencia**: Función 'ict_front_full_defects2' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/data` (GET)
- **Función**: `ict_data_api` (Línea 27487)
- **Evidencia**: Función 'ict_data_api' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/defects` (GET)
- **Función**: `ict_defects_api` (Línea 27597)
- **Evidencia**: Función 'ict_defects_api' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/export` (GET)
- **Función**: `export_ict_excel` (Línea 27621)
- **Evidencia**: Función 'export_ict_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/export-defects` (GET)
- **Función**: `export_ict_defects_excel` (Línea 27766)
- **Evidencia**: Función 'export_ict_defects_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

### `/api/ict/export-compare` (POST)
- **Función**: `export_ict_compare_excel` (Línea 27908)
- **Evidencia**: Función 'export_ict_compare_excel' referenciada en graphify-out\db-relations-corpus\graphify-out\graph.html

