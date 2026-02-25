# 📚 Documentación Completa del Sistema MES ILSAN

## Índice
1. [Arquitectura General](#arquitectura-general)
2. [Punto de Entrada (run.py)](#punto-de-entrada-runpy)
3. [Rutas Principales (routes.py)](#rutas-principales-routespy)
4. [API SMT Routes (smt_routes_clean.py)](#api-smt-routes-smt_routes_cleanpy)
5. [API PO/WO (api_po_wo.py)](#api-powo-api_po_wopy)
6. [API AOI (aoi_api.py)](#api-aoi-aoi_apipy)
7. [API RAW Modelos (api_raw_modelos.py)](#api-raw-modelos-api_raw_modelospy)
8. [Control Modelos SMT (control_modelos_smt.py)](#control-modelos-smt-control_modelos_smtpy)
9. [API Inventario SMD (smd_inventory_api.py)](#api-inventario-smd-smd_inventory_apipy)
10. [API Admin Permisos (admin_api.py)](#api-admin-permisos-admin_apipy)
11. [Blueprints Adicionales](#blueprints-adicionales)

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              run.py                                      │
│                      (Punto de Entrada Principal)                        │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   routes.py     │  │ smt_routes_     │  │  api_po_wo.py   │
│ (App Flask +    │  │  clean.py       │  │ (PO/WO API)     │
│  Rutas Ppales)  │  │ (SMT API)       │  │                 │
└────────┬────────┘  └─────────────────┘  └─────────────────┘
         │
         ├──────────────────────────────────────────┐
         │                                          │
         ▼                                          ▼
┌─────────────────────────────────────┐  ┌─────────────────────────────┐
│        Blueprints Registrados        │  │    Módulos de Soporte       │
│  • aoi_api (AOI)                    │  │  • db.py                    │
│  • control_modelos_bp               │  │  • db_mysql.py              │
│  • api_raw                          │  │  • auth_system.py           │
│  • user_admin_bp                    │  │  • po_wo_models.py          │
│  • admin_bp                         │  │  • config_mysql.py          │
│  • smt_bp                           │  │                             │
│  • smd_inventory_api                │  │                             │
└─────────────────────────────────────┘  └─────────────────────────────┘
```

---

## Punto de Entrada (run.py)

### Descripción
Archivo principal que inicializa y ejecuta la aplicación Flask.

### Funciones Principales
| Función | Descripción |
|---------|-------------|
| `load_dotenv()` | Carga variables de entorno desde `.env` |
| `register_smt_routes(app)` | Registra rutas SMT |
| `registrar_rutas_po_wo(app)` | Registra rutas PO/WO |
| `app.register_blueprint()` | Registra blueprints adicionales |

### Blueprints Registrados
- `smt_api` - Rutas SMT
- `api_po_wo` - API de PO/WO  
- `aoi_api` - API de AOI
- `control_modelos_bp` - Control de modelos SMT
- `api_raw` - API de modelos RAW

### Configuración del Servidor
```python
app.run(host='0.0.0.0', port=5000, use_reloader=True, reloader_type='stat')
```

---

## Rutas Principales (routes.py)

### Descripción
Archivo principal con +12,000 líneas que contiene la instancia Flask y la mayoría de rutas del sistema.

### Importaciones Principales
- Flask y extensiones
- Sistema de autenticación (`AuthSystem`)
- Módulos de base de datos (`db.py`, `db_mysql.py`)
- Modelos PO/WO

---

###  RUTAS DE AUTENTICACIÓN

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/` | GET | Redirección a inicio | No |
| `/login` | GET, POST | Página de login | No |
| `/logout` | GET | Cerrar sesión | No |
| `/inicio` | GET | Landing page / Hub | No |

---

###  RUTAS DE PÁGINAS PRINCIPALES

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/ILSAN-ELECTRONICS` | GET | Página principal MaterialTemplate |  |
| `/dashboard` | GET | Alias para MaterialTemplate |  |
| `/calendario` | GET | Calendario de producción |  |
| `/defect-management` | GET | Gestión de defectos (en desarrollo) |  |
| `/sistemas` | GET | Redirección al hub |  |
| `/soporte` | GET | Página de soporte técnico |  |
| `/documentacion` | GET | Página de documentación |  |
| `/Prueba` | GET | Control de salida (prueba) |  |
| `/DESARROLLO` | GET | Control de salida (desarrollo) |  |

---

###  RUTAS FRONT PLAN

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/front-plan/static/<path:filename>` | GET | Assets de FRONT PLAN | No |
| `/plan-main` | GET | Página de planeación |  |
| `/control-main` | GET | Panel de control de operación |  |
| `/plan-main-assy-ajax` | GET | AJAX para plan main |  |
| `/control-operacion-linea-main-ajax` | GET | AJAX para control operación |  |

---

###  API PLAN (Plan de Producción)

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/api/plan` | GET | Listar planes |  |
| `/api/plan` | POST | Crear plan |  |
| `/api/plan/update` | POST | Actualizar plan |  |
| `/api/plan/status` | POST | Actualizar estado |  |
| `/api/plan/save-sequences` | POST | Guardar secuencias |  |
| `/api/plan/pending` | GET | Planes pendientes |  |
| `/api/plan/reschedule` | POST | Reprogramar planes |  |
| `/api/plan/export-excel` | POST | Exportar a Excel |  |
| `/api/plan-main/list` | GET | Listar plan main |  |
| `/api/raw/search` | GET | Buscar en tabla RAW |  |

---

### 📦 API BOM (Bill of Materials)

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/importar_excel_bom` | POST | Importar BOM desde Excel |  |
| `/listar_modelos_bom` | GET | Listar modelos BOM |  |
| `/listar_bom` | POST | Listar registros BOM |  |
| `/consultar_bom` | GET | Consultar BOM con filtros |  |
| `/exportar_excel_bom` | GET | Exportar BOM a Excel |  |
| `/api/bom/update` | POST | Actualizar registro BOM |  |
| `/api/bom/update-posiciones-assy` | POST | Actualizar posiciones ASSY | No |
| `/api/bom-smt-data` | GET | Datos BOM para SMT |  |

---

### 📦 API MATERIALES

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/guardar_material` | POST | Guardar material | No |
| `/listar_materiales` | GET | Listar materiales | No |
| `/importar_excel` | POST | Importar materiales desde Excel | No |
| `/actualizar_campo_material` | POST | Actualizar campo específico | No |
| `/actualizar_material_completo` | POST | Actualizar material completo |  |
| `/exportar_excel` | GET | Exportar materiales a Excel |  |
| `/obtener_codigos_material` | GET | Obtener códigos para dropdown | No |
| `/buscar_material_por_numero_parte` | GET | Buscar por número de parte |  |
| `/buscar_material_por_codigo` | GET | Buscar por código |  |

---

### 🏭 RUTAS CONTROL DE ALMACÉN

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/control_almacen` | GET | Página de control de almacén |  |
| `/guardar_control_almacen` | POST | Guardar registro |  |
| `/consultar_control_almacen` | GET | Consultar registros |  |
| `/actualizar_control_almacen` | POST | Actualizar registro |  |
| `/obtener_secuencial_lote_interno` | POST | Obtener siguiente secuencial |  |
| `/obtener_siguiente_secuencial` | GET | Siguiente secuencial código | No |
| `/actualizar_estado_desecho_almacen` | POST | Actualizar estado desecho |  |

---

### 📤 RUTAS CONTROL DE SALIDA

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/control_salida` | GET | Página de control de salida |  |
| `/buscar_codigo_recibido` | GET | Buscar código recibido |  |
| `/guardar_salida_lote` | POST | Guardar salida de lote |  |
| `/consultar_historial_salidas` | GET | Historial de salidas |  |
| `/procesar_salida_material` | POST | Procesar salida |  |
| `/verificar_stock_rapido` | GET | Verificar stock |  |
| `/control_salida/estado` | GET | Estado del módulo |  |
| `/control_salida/configuracion` | GET, POST | Configuración |  |
| `/control_salida/validar_stock` | POST | Validar stock |  |
| `/control_salida/reporte_diario` | GET | Reporte diario |  |

---

###  API INVENTARIO

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/api/inventario/consultar` | POST | Consultar inventario general |  |
| `/api/inventario/historial` | POST | Historial por número de parte |  |
| `/api/inventario/historial/<numero_parte>` | GET | Historial (GET) |  |
| `/api/inventario/lotes` | POST | Lotes por número de parte |  |
| `/api/inventario/lotes/<numero_parte>` | GET | Lotes (GET) |  |
| `/api/inventario/lotes_detalle` | POST | Detalle de lotes |  |
| `/api/inventario/modelo/<codigo_modelo>` | GET | Inventario por modelo |  |
| `/api/inventario` | GET | API inventario general |  |
| `/api/inventario_general` | GET | Inventario general IMD | No |
| `/obtener_inventario_general` | GET | Obtener inventario |  |
| `/verificar_estado_inventario` | GET | Verificar estado |  |
| `/recalcular_inventario_general` | POST | Recalcular inventario |  |
| `/forzar_actualizacion_inventario/<numero_parte>` | POST | Forzar actualización |  |

---

### 🏭 API PLAN SMD

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/api/plan-smd` | POST | Guardar plan SMD |  |
| `/api/plan-smd/list` | GET | Listar planes SMD | No |
| `/api/plan-smd/import` | POST | Importar plan SMD |  |
| `/api/plan-smd-diario` | GET | Plan SMD diario | No |
| `/api/generar-plan-smd` | POST | Generar plan SMD (Agente) |  |
| `/plan-smd-diario` | GET | Página plan SMD diario | No |

---

### 📋 API WORK ORDERS

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/api/work-orders` | GET | Listar Work Orders |  |
| `/api/work-orders/import` | POST | Importar Work Orders |  |

---

### 🔧 API PLAN-RUN (Ciclos de Producción)

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/api/plan-run/start` | POST | Iniciar ciclo | No |
| `/api/plan-run/end` | POST | Finalizar ciclo | No |
| `/api/plan-run/pause` | POST | Pausar ciclo | No |
| `/api/plan-run/resume` | POST | Reanudar ciclo | No |
| `/api/plan-run/status` | GET | Estado del ciclo | No |

---

### 🖨️ IMPRESIÓN ZEBRA

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/imprimir_zebra` | POST | Imprimir etiqueta Zebra |  |
| `/imprimir_etiqueta_qr` | POST | Imprimir etiqueta QR |  |

---

### 🎭 METAL MASK API

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/control/metal-mask` | GET | Página control Metal Mask |  |
| `/control/metal-mask/caja` | GET | Página control caja Metal Mask |  |
| `/api/masks` | GET | Listar masks |  |
| `/api/masks` | POST | Crear mask |  |
| `/api/masks/<int:mask_id>` | PUT | Actualizar mask |  |
| `/api/masks/info` | GET | Info de mask |  |
| `/api/metal-mask/history` | GET | Historial Metal Mask |  |
| `/api/metal-mask/history` | POST | Guardar historial |  |
| `/api/metal-mask/update-used-count` | POST | Actualizar contador uso |  |
| `/api/metal-mask/test` | GET | Test Metal Mask | No |

---

### 📦 API STORAGE (Almacenamiento)

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/api/storage` | GET | Obtener storage boxes |  |
| `/api/storage` | POST | Agregar storage box |  |
| `/api/storage/<int:storage_id>` | PUT | Actualizar storage |  |

---

###  HISTORIAL SMT

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/historial-cambio-material-smt` | GET | Página historial SMT |  |
| `/historial-cambio-material-smt-ajax` | GET | AJAX historial SMT | No |
| `/api/historial-cambio-material-maquina` | GET | API historial máquina |  |
| `/api/historial_smt_latest` | GET | Último por línea/máquina/slot |  |
| `/api/historial_smt_latest_v2` | GET | Versión 2 con agrupación |  |
| `/api/test-historial-smt` | GET | Test historial SMT |  |
| `/api/test-historial-smt-v2` | GET | Test historial SMT v2 |  |
| `/api/crear-datos-prueba-smt` | POST | Crear datos de prueba |  |

---

###  HISTORIAL ICT

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/historial-ict` | GET | Página historial ICT |  |
| `/ict/front-full-defects2` | GET | Vista defectos ICT |  |
| `/api/ict/data` | GET | Datos ICT |  |
| `/api/ict/defects` | GET | Defectos por barcode |  |
| `/api/ict/export` | GET | Exportar ICT a Excel |  |
| `/api/ict/export-defects` | GET | Exportar defectos a Excel |  |

---

### 🗄️ VISOR MySQL

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/visor-mysql` | GET | Visor MySQL | No |
| `/api/mysql/columns` | GET | Columnas de tabla | No |
| `/api/mysql/data` | GET | Datos de tabla | No |
| `/api/mysql/update` | POST | Actualizar registro | No |
| `/api/mysql/create` | POST | Crear registro | No |
| `/api/mysql/delete` | POST | Eliminar registro |  |
| `/api/mysql/usuario-actual` | GET | Usuario actual |  |
| `/api/mysql` | GET, POST | Proxy MySQL | No |
| `/mysql-proxy.php` | GET, POST | Proxy PHP (Android) | No |

---

### 📡 API STATUS

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/api/status` | GET | Estado del servidor | No |
| `/api/ubicacion` | GET | API ubicación | No |
| `/api/movimientos` | GET | API movimientos | No |

---

###  PERMISOS

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/verificar_permiso_dropdown` | POST | Verificar permiso dropdown | No |
| `/obtener_permisos_usuario_actual` | GET | Permisos del usuario |  |
| `/test-permisos` | GET | Test de permisos |  |
| `/test-frontend-permisos` | GET | Test frontend permisos |  |
| `/test-ajax-manager` | GET | Test AJAX manager |  |

---

###  RUTAS AJAX (Control de Material)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/ajuste-numero-parte-ajax` | GET | Ajuste número de parte |
| `/consultar-peps-ajax` | GET | Consultar PEPS |
| `/control-almacen-ajax` | GET | Control de almacén |
| `/control-entrada-salida-material-ajax` | GET | Entrada/salida material |
| `/control-recibo-refacciones-ajax` | GET | Recibo refacciones |
| `/control-retorno-ajax` | GET | Control retorno |
| `/control-salida-ajax` | GET | Control salida |
| `/control-salida-refacciones-ajax` | GET | Salida refacciones |
| `/control-total-material-ajax` | GET | Total material |
| `/estandares-refacciones-ajax` | GET | Estándares refacciones |
| `/estatus-inventario-refacciones-ajax` | GET | Estatus inventario |
| `/estatus-material-ajax` | GET | Estatus material |
| `/estatus-material-msl-ajax` | GET | Estatus MSL |
| `/historial-inventario-real-ajax` | GET | Historial inventario |
| `/historial-material-ajax` | GET | Historial material |
| `/inventario-rollos-smd-ajax` | GET | Inventario rollos SMD |
| `/longterm-inventory-ajax` | GET | Inventario largo plazo |
| `/material-sustituto-ajax` | GET | Material sustituto |
| `/recibo-pago-material-ajax` | GET | Recibo pago material |
| `/registro-material-real-ajax` | GET | Registro material |

---

###  RUTAS AJAX (Control de Proceso)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/control-bom-ajax` | GET | Control BOM |
| `/crear-plan-micom-ajax` | GET | Crear plan MICOM |
| `/control-operacion-linea-smt-ajax` | GET | Control operación SMT |
| `/control-impresion-identificacion-smt-ajax` | GET | Control impresión |
| `/control-registro-identificacion-smt-ajax` | GET | Registro identificación |
| `/historial-operacion-proceso-ajax` | GET | Historial operación |
| `/bom-management-process-ajax` | GET | BOM management |
| `/reporte-diario-inspeccion-smt-ajax` | GET | Reporte inspección SMT |
| `/control-diario-inspeccion-smt-ajax` | GET | Control diario |
| `/reporte-diario-inspeccion-proceso-ajax` | GET | Reporte proceso |

---

###  RUTAS AJAX (Control de Producción)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/line-material-status-ajax` | GET | Estado material línea |
| `/control-mask-metal-ajax` | GET | Control mask metal |
| `/control-squeegee-ajax` | GET | Control squeegee |
| `/control-caja-mask-metal-ajax` | GET | Control caja mask |
| `/estandares-soldadura-ajax` | GET | Estándares soldadura |
| `/registro-recibo-soldadura-ajax` | GET | Registro soldadura |
| `/control-salida-soldadura-ajax` | GET | Salida soldadura |
| `/historial-tension-mask-metal-ajax` | GET | Historial tensión |
| `/historial-uso-pegamento-soldadura-ajax` | GET | Historial pegamento |
| `/historial-uso-mask-metal-ajax` | GET | Historial uso mask |
| `/historial-uso-squeegee-ajax` | GET | Historial squeegee |
| `/process-interlock-history-ajax` | GET | Historial interlock |
| `/control-master-sample-smt-ajax` | GET | Master sample SMT |
| `/historial-inspeccion-master-sample-smt-ajax` | GET | Inspección master |
| `/control-inspeccion-oqc-ajax` | GET | Inspección OQC |

---

###  RUTAS AJAX (Calidad y Empaque)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/control-resultado-reparacion-ajax` | GET | Resultado reparación |
| `/control-item-reparado-ajax` | GET | Item reparado |
| `/control-unidad-empaque-modelo-ajax` | GET | Unidad empaque |
| `/packaging-register-management-ajax` | GET | Registro empaque |
| `/search-packaging-history-ajax` | GET | Historial empaque |
| `/shipping-register-management-ajax` | GET | Registro embarque |
| `/search-shipping-history-ajax` | GET | Historial embarque |
| `/return-warehousing-register-ajax` | GET | Retorno almacén |
| `/return-warehousing-history-ajax` | GET | Historial retorno |

---

###  RUTAS AJAX (Identificación y Scrap)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/registro-movimiento-identificacion-ajax` | GET | Registro movimiento |
| `/control-otras-identificaciones-ajax` | GET | Otras identificaciones |
| `/control-movimiento-ns-producto-ajax` | GET | Movimiento NS |
| `/model-sn-management-ajax` | GET | Gestión SN |
| `/control-scrap-ajax` | GET | Control scrap |

---

###  RUTAS LISTAS

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/listas/informacion_basica` | GET | Lista información básica |
| `/listas/control_material` | GET | Lista control material |
| `/listas/control_produccion` | GET | Lista control producción |
| `/listas/control_proceso` | GET | Lista control proceso |
| `/listas/control_calidad` | GET | Lista control calidad |
| `/listas/control_resultados` | GET | Lista control resultados |
| `/listas/control_reporte` | GET | Lista control reporte |
| `/listas/configuracion_programa` | GET | Lista configuración |

---

###  CSV VIEWER

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/csv-viewer` | GET | Visor CSV |  |
| `/api/csv_data` | GET | Datos CSV |  |
| `/api/csv_stats` | GET | Estadísticas CSV |  |
| `/api/filter_data` | POST | Filtrar datos CSV |  |

---

## API SMT Routes (smt_routes_clean.py)

### Blueprint: `smt_api`

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/smt/historial` | GET | Página HTML historial SMT |
| `/api/historial_smt_data` | GET | API datos historial SMT |
| `/api/smt/filtros/opciones` | GET | Opciones de filtros |
| `/smt/debug` | GET | Debug SMT |
| `/api/smt/historial/data` | GET | Datos historial (compatibilidad) |

### Parámetros de Filtro `/api/historial_smt_data`
- `folder` - Carpeta/archivo
- `part_name` - Nombre de parte
- `result` - Resultado (OK/NG)
- `date_from` - Fecha desde
- `date_to` - Fecha hasta
- `linea` - Línea de producción
- `maquina` - Máquina

---

## API PO/WO (api_po_wo.py)

### Blueprint: `api_po_wo` (prefix: `/api`)

### Work Orders (WO)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/api/work_orders` | POST | Crear nueva WO |
| `/api/work_orders` | GET | Listar WOs |
| `/api/generar_codigo_wo` | GET | Generar código WO |
| `/api/wo/listar` | GET | Listar WOs (alternativa) |
| `/api/wo/<codigo>/estado` | PUT | Actualizar estado WO |
| `/api/wo/actualizar-po` | POST | Actualizar PO de WO |
| `/api/wo/actualizar` | POST | Actualizar WO completa |
| `/api/wo/eliminar` | DELETE | Eliminar WO |

### Purchase Orders (PO)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/api/po/listar` | GET | Listar POs |
| `/api/po/crear` | POST | Crear nueva PO |

### Parámetros de Filtro WO
- `estado` - Estado de la WO
- `codigo_wo` - Código WO específico
- `modelo` - Modelo
- `fecha_desde` - Fecha desde
- `fecha_hasta` - Fecha hasta
- `incluir_planificadas` - Incluir WO planificadas

### Estados Válidos WO
- `CREADA`
- `PLANIFICADA`
- `EN_PRODUCCION`
- `CERRADA`

---

## API AOI (aoi_api.py)

### Blueprint: `aoi_api`

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/api/shift-now` | GET | Turno actual |
| `/api/realtime` | GET | Datos en tiempo real |
| `/api/day` | GET | Datos por día |

### Turnos
| Turno | Horario |
|-------|---------|
| DÍA | 07:40 - 17:39 |
| TIEMPO_EXTRA | 17:40 - 22:49 |
| NOCHE | 22:50 - 07:30 |

---

## API RAW Modelos (api_raw_modelos.py)

### Blueprint: `api_raw` (prefix: `/api/raw`)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/api/raw/modelos` | GET | Listar modelos desde tabla RAW |
| `/api/raw/ct_uph` | GET | Obtener CT y UPH por part_no |

### Parámetros `/api/raw/ct_uph`
- `part_no` (requerido) - Número de parte
- `linea` (opcional) - Línea de producción

---

## Control Modelos SMT (control_modelos_smt.py)

### Blueprint: `control_modelos_bp` (prefix: `/control-modelos`)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/control-modelos/` | GET | Página principal control modelos |
| `/control-modelos/api/rows` | POST | Crear nuevo registro |
| `/control-modelos/api/rows/<rowhash>` | PUT | Actualizar registro |
| `/control-modelos/api/rows/<rowhash>` | DELETE | Eliminar registro |
| `/control-modelos/api/data` | GET | Obtener datos actualizados |

### Funciones Principales
- `init_control_modelos_table()` - Inicializa tabla
- `get_current_user()` - Obtiene usuario de sesión
- `ensure_usuario_column()` - Asegura columna usuario
- `compute_rowhash()` - Calcula hash de fila

---

## API Inventario SMD (smd_inventory_api.py)

### Blueprint: `smd_inventory_api`

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/smd/inventario` | GET | Página inventario rollos SMD |
| `/api/smd/inventario/rollos` | GET | API inventario rollos |
| `/api/smd/inventario/rollo/<int:rollo_id>` | GET | Detalle de rollo |
| `/api/smd/inventario/rollo/<int:rollo_id>/marcar_agotado` | POST | Marcar rollo agotado |
| `/api/smd/inventario/rollo/<int:rollo_id>/asignar_mounter` | POST | Asignar a mounter |
| `/api/smd/inventario/stats` | GET | Estadísticas inventario |
| `/api/smd/inventario/sincronizar` | POST | Sincronizar inventario |

### Parámetros de Filtro `/api/smd/inventario/rollos`
- `estado` - Estado del rollo
- `numero_parte` - Número de parte
- `linea` - Línea asignada
- `maquina` - Máquina asignada
- `fecha_desde` - Fecha desde
- `fecha_hasta` - Fecha hasta

### Estados de Rollo
- `ACTIVO`
- `EN_USO`
- `AGOTADO`
- `RETIRADO`

---

## API Admin Permisos (admin_api.py)

### Blueprint: `admin_bp` (prefix: `/admin`)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/admin/permisos-dropdowns` | GET | Página gestión permisos |
| `/admin/api/roles` | GET | Obtener roles |
| `/admin/api/dropdowns` | GET | Obtener dropdowns |
| `/admin/api/role-permissions/<role_name>` | GET | Permisos de un rol |
| `/admin/api/toggle-permission` | POST | Alternar permiso |
| `/admin/api/enable-all-permissions` | POST | Habilitar todos los permisos |
| `/admin/api/disable-all-permissions` | POST | Deshabilitar todos los permisos |

---

## Blueprints Adicionales

### user_admin_bp (prefix: `/admin`)
Blueprint para administración de usuarios.

### smt_bp (smt_routes_date_fixed.py)
Blueprint para rutas SMT con corrección de fechas.

---

## Decoradores Personalizados

### `@login_requerido`
Verifica que el usuario esté autenticado en la sesión.

### `@requiere_permiso_dropdown(pagina, seccion, boton)`
Verifica permisos específicos de dropdowns para el usuario actual.

### `@manejo_errores` (api_po_wo.py)
Decorator para manejo centralizado de errores en API.

---

## Funciones Utilitarias

### Zona Horaria México
```python
def obtener_fecha_hora_mexico():
    """Obtener fecha y hora actual en zona horaria de México (GMT-6)"""
```

### Conversión de Líneas SMT
```python
def convertir_linea_smt(linea_nombre):
    # SMT A = 1line, SMT B = 2line, SMT C = 3line, SMT D = 4line

def convertir_linea_smt_reverso(linea_bd):
    # 1line = SMT A, 2line = SMT B, 3line = SMT C, 4line = SMT D
```

---

## Tablas de Base de Datos Principales

| Tabla | Descripción |
|-------|-------------|
| `usuarios_sistema` | Usuarios del sistema |
| `roles` | Roles de usuario |
| `usuario_roles` | Relación usuario-rol |
| `permisos_botones` | Permisos de botones/dropdowns |
| `rol_permisos_botones` | Relación rol-permiso |
| `work_orders` | Órdenes de trabajo |
| `embarques` | Purchase Orders |
| `bom` | Bill of Materials |
| `materiales` | Inventario de materiales |
| `historial_cambio_material_smt` | Historial SMT |
| `history_ict` | Historial ICT |
| `history_ict_defects` | Defectos ICT |
| `aoi_file_log` | Log de archivos AOI |
| `raw` | Datos RAW de modelos |
| `raw_smd` | Datos SMD |
| `plan_main` | Plan de producción principal |
| `plan_smd` | Plan SMD |
| `plan_smd_runs` | Ciclos de producción |
| `metal_masks` | Metal masks |
| `storage_boxes` | Cajas de almacenamiento |
| `InventarioRollosSMD` | Inventario rollos SMD |
| `HistorialMovimientosRollosSMD` | Historial movimientos |

---

## Configuración de Base de Datos

```python
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT')),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE'),
    'charset': 'utf8mb4'
}
```

---

## Variables de Entorno Requeridas

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta Flask |
| `MYSQL_HOST` | Host MySQL |
| `MYSQL_PORT` | Puerto MySQL |
| `MYSQL_USER` | Usuario MySQL |
| `MYSQL_PASSWORD` | Contraseña MySQL |
| `MYSQL_DATABASE` | Nombre de base de datos |

---

## Resumen Estadístico

| Categoría | Cantidad Aproximada |
|-----------|---------------------|
| **Rutas Totales** | ~250+ |
| **APIs REST** | ~80+ |
| **Rutas AJAX** | ~60+ |
| **Blueprints** | 8 |
| **Tablas BD** | ~20+ |
| **Líneas de Código (routes.py)** | ~12,968 |

---

*Documento generado el 27 de noviembre de 2025*
*Sistema MES ILSAN - Versión Documentada*
