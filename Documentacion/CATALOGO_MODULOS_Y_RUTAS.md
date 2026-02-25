# Catalogo Tecnico de Modulos y Rutas

Este catalogo resume endpoints clave por dominio funcional, con entradas/salidas esperadas y archivo fuente.

## Metodologia

- Inventario de rutas levantado desde:
  - `app/routes.py`
  - `app/api_po_wo.py`
  - `app/aoi_api.py`
  - `app/api_raw_modelos.py`
  - `app/smd_inventory_api.py`
  - `app/smt_routes_clean.py`
  - `app/smt_routes_date_fixed.py`
  - `app/user_admin.py`
  - `app/admin_api.py`
  - `app/py/control_modelos_smt.py`
- Proteccion evaluada por presencia de decoradores de autenticacion/permisos.

## 1. Autenticacion y Hub

| Endpoint | Metodo | Entrada esperada | Salida esperada | Proteccion | Fuente |
|---|---|---|---|---|---|
| `/login` | `GET/POST` | Form `username`, `password` en POST | Redirect o JSON (`success`, `redirect`) | Publica | `app/routes.py:349` |
| `/inicio` | `GET` | Sesion opcional | Landing/hub apps | Publica | `app/routes.py:478` |
| `/ILSAN-ELECTRONICS` | `GET` | Sesion activa | `MaterialTemplate.html` | `@login_requerido` | `app/routes.py:528` |
| `/logout` | `GET` | Sesion activa/opcional | Limpieza sesion + redirect | Publica | `app/routes.py:607` |
| `/obtener_permisos_usuario_actual` | `GET` | Sesion | JSON permisos dropdown | `@login_requerido` | `app/routes.py:7608` |
| `/verificar_permiso_dropdown` | `POST` | JSON `{pagina,seccion,boton}` | JSON `{tiene_permiso,...}` | Publica (usa `session['username']`) | `app/routes.py:7537` |

## 2. Informacion Basica

| Endpoint | Metodo | Entrada esperada | Salida esperada | Proteccion | Fuente |
|---|---|---|---|---|---|
| `/listas/informacion_basica` | `GET` | N/A | HTML sidebar lista | `@login_requerido` | `app/routes.py:4283` |
| `/informacion_basica/control_de_material` | `GET` | N/A | HTML fragment modulo | `@login_requerido` | `app/routes.py:4260` |
| `/informacion_basica/control_de_bom` | `GET` | N/A | HTML fragment BOM + modelos | `@login_requerido` | `app/routes.py:4270` |
| `/cargar_template` | `POST` | JSON `{template_path}` | HTML renderizado | `@login_requerido` | `app/routes.py:2504` |
| `/control-modelos/` | `GET` | N/A | HTML control modelos SMT | Abierta | `app/py/control_modelos_smt.py:265` |
| `/control-modelos/api/rows` | `POST` | JSON fila | JSON `{ok}` | Abierta | `app/py/control_modelos_smt.py:319` |
| `/control-modelos/api/data` | `GET` | Query `q,page,size` | JSON tabla paginada | Abierta | `app/py/control_modelos_smt.py:337` |

## 3. Material e Inventario

| Endpoint | Metodo | Entrada esperada | Salida esperada | Proteccion | Fuente |
|---|---|---|---|---|---|
| `/guardar_material` | `POST` | JSON datos material | JSON `{success}` | Abierta | `app/routes.py:3015` |
| `/listar_materiales` | `GET` | N/A | JSON lista materiales | Abierta | `app/routes.py:3053` |
| `/importar_excel` | `POST` | archivo Excel | JSON resultado importacion | Abierta | `app/routes.py:3200` |
| `/actualizar_campo_material` | `POST` | JSON `{codigoMaterial,campo,valor}` | JSON resultado | Abierta | `app/routes.py:3405` |
| `/actualizar_material_completo` | `POST` | JSON `{codigo_material_original,nuevos_datos}` | JSON resultado | `@login_requerido` | `app/routes.py:3455` |
| `/api/inventario/consultar` | `POST` | filtros numero parte/codigo | JSON consolidado | `@login_requerido` | `app/routes.py:6669` |
| `/api/inventario/lotes` | `POST` | JSON filtros/paginacion | JSON lotes | `@login_requerido` | `app/routes.py:7195` |
| `/api/inventario/lotes/<numero_parte>` | `GET` | path numero_parte | JSON detalle lotes | `@login_requerido` | `app/routes.py:7349` |
| `/procesar_salida_material` | `POST` | JSON salida material | JSON transaccion salida | `@login_requerido` | `app/routes.py:5953` |
| `/api/smd/inventario/rollos` | `GET` | query filtros | JSON `{success,data,stats}` | Abierta | `app/smd_inventory_api.py:45` |
| `/api/smd/inventario/rollo/<id>/marcar_agotado` | `POST` | JSON observaciones/usuario | JSON `{success,message}` | Abierta | `app/smd_inventory_api.py:212` |

## 4. BOM

| Endpoint | Metodo | Entrada esperada | Salida esperada | Proteccion | Fuente |
|---|---|---|---|---|---|
| `/listar_modelos_bom` | `GET` | N/A | JSON modelos `[{modelo}]` | `@login_requerido` | `app/routes.py:2565` |
| `/listar_bom` | `POST` | JSON `{modelo, classification?}` | JSON filas BOM mapeadas | `@login_requerido` | `app/routes.py:2579` |
| `/importar_excel_bom` | `POST` | archivo Excel | JSON resumen import | `@login_requerido` | `app/routes.py:2528` |
| `/exportar_excel_bom` | `GET` | query `modelo`, `classification?` | archivo `.xlsx` | `@login_requerido` | `app/routes.py:2789` |
| `/api/bom/update` | `POST` | JSON registro editado | JSON `{success,message}` | `@login_requerido` | `app/routes.py:2831` |
| `/api/bom/update-posiciones-assy` | `POST` | JSON `{cambios:[...]}` | JSON `{success,actualizados}` | Abierta | `app/routes.py:2912` |
| `/api/bom-smt-data` | `GET` | query `linea`,`model_code` | JSON BOM SMT | `@login_requerido` | `app/routes.py:12581` |
| `/control-bom-ajax` | `GET` | N/A | HTML BOM (legacy) | `@login_requerido` | `app/routes.py:4810` |

## 5. Planeacion (MAIN / IMD / SMT / SMD)

| Endpoint | Metodo | Entrada esperada | Salida esperada | Proteccion | Fuente |
|---|---|---|---|---|---|
| `/api/plan` | `GET/POST` | filtros o payload plan_main | JSON planes/alta | `@login_requerido` | `app/routes.py:712`, `app/routes.py:770` |
| `/api/plan/update` | `POST` | JSON cambios plan_main | JSON resultado | `@login_requerido` | `app/routes.py:867` |
| `/api/plan-imd` | `GET/POST` | filtros o payload plan_imd | JSON planes IMD | `@login_requerido` | `app/routes.py:1339`, `app/routes.py:1397` |
| `/api/plan-smt` | `GET/POST` | filtros o payload plan_smt | JSON planes SMT | `@login_requerido` | `app/routes.py:1893`, `app/routes.py:1951` |
| `/api/plan-main/list` | `GET` | filtros minimos | JSON lista compacta | `@login_requerido` | `app/routes.py:2319` |
| `/api/plan-smd` | `POST` | arreglo renglones SMD | JSON `{renglones_guardados}` | `@login_requerido` | `app/routes.py:4523` |
| `/api/generar-plan-smd` | `POST` | JSON opciones agente | JSON resumen generado | `@login_requerido` | `app/routes.py:4576` |
| `/api/plan-smd/import` | `POST` | CSV o JSON renglones | JSON `{inserted,updated,errors}` | `@login_requerido` | `app/routes.py:9722` |
| `/api/plan-smd/list` | `GET` | query (`q`,`linea`,`solo_pendientes`,`plan_id`) | JSON `{rows,count}` | Abierta | `app/routes.py:11755` |
| `/api/plan-run/start` | `POST` | JSON `{plan_id,linea?,lot_prefix?}` | JSON run iniciado | Abierta | `app/routes.py:11930` |
| `/api/plan-run/end` | `POST` | JSON `{run_id,plan_id?}` | JSON run finalizado | Abierta | `app/routes.py:12063` |
| `/api/plan-run/status` | `GET` | query `run_id` o `linea` | JSON estado + progreso | Abierta | `app/routes.py:12197` |
| `/api/plan-smd-diario` | `GET` | query `date`,`shift?` | JSON cruce PLAN vs AOI | Abierta | `app/routes.py:11162` |

## 6. PO / WO

| Endpoint | Metodo | Entrada esperada | Salida esperada | Proteccion | Fuente |
|---|---|---|---|---|---|
| `/api/work_orders` | `POST` | JSON WO nueva | JSON `{ok,codigo_wo}` | Abierta | `app/api_po_wo.py:106` |
| `/api/work_orders` | `GET` | query filtros | JSON listado WO | Abierta | `app/api_po_wo.py:226` |
| `/api/wo/listar` | `GET` | query filtros | JSON lista WO | Abierta | `app/api_po_wo.py:284` |
| `/api/wo/<codigo>/estado` | `PUT` | JSON nuevo estado | JSON resultado | Abierta | `app/api_po_wo.py:363` |
| `/api/po/listar` | `GET` | query filtros PO | JSON listado PO | Abierta | `app/api_po_wo.py:596` |
| `/api/po/crear` | `POST` | JSON PO | JSON `{success,message}` | Abierta | `app/api_po_wo.py:685` |
| `/api/work-orders/import` | `POST` | filtros/criterios import | JSON `{imported,plans,...}` | `@login_requerido` | `app/routes.py:2374` |
| `/api/work-orders` | `GET` | query `q`,`estado`... | JSON WOs para planeacion | `@login_requerido` | `app/routes.py:4395` |
| `/api/wo/exportar` | `GET` | query filtros | Excel descarga | `@login_requerido` | `app/routes.py:9607` |

## 7. SMT Historial

| Endpoint | Metodo | Entrada esperada | Salida esperada | Proteccion | Fuente |
|---|---|---|---|---|---|
| `/api/historial_smt_data` | `GET` | query filtros fecha/folder | JSON historial SMT | Abierta (duplicada) | `app/smt_routes_date_fixed.py:42`, `app/smt_routes_clean.py:43` |
| `/api/smt/historial/data` | `GET` | query `folder` y filtros | JSON `{success,data,stats}` | Abierta | `app/smt_routes_clean.py:231` |
| `/api/smt/filtros/opciones` | `GET` | N/A | JSON lineas/maquinas | Abierta | `app/smt_routes_clean.py:188` |
| `/smt/historial` | `GET` | N/A | HTML historial SMT AJAX | Abierta | `app/smt_routes_clean.py:32` |
| `/api/historial_smt_latest` | `GET` | query varios | JSON latest v1 | `@login_requerido` | `app/routes.py:10098` |
| `/api/historial_smt_latest_v2` | `GET` | query varios | JSON latest v2 | `@login_requerido` | `app/routes.py:10204` |

## 8. AOI

| Endpoint | Metodo | Entrada esperada | Salida esperada | Proteccion | Fuente |
|---|---|---|---|---|---|
| `/api/shift-now` | `GET` | N/A | JSON turno actual | Abierta | `app/aoi_api.py` |
| `/api/realtime` | `GET` | N/A | JSON tabla en tiempo real | Abierta | `app/aoi_api.py` |
| `/api/day` | `GET` | query `date` | JSON filas por dia logico | Abierta | `app/aoi_api.py` |
| `/historial-aoi` | `GET` | N/A | HTML vista historial AOI | `@login_requerido` | `app/routes.py:5165` |
| `/historial-aoi-ajax` | `GET` | N/A | HTML fragment AOI | `@login_requerido` | `app/routes.py:5185` |

## 9. Metal Mask

| Endpoint | Metodo | Entrada esperada | Salida esperada | Proteccion | Fuente |
|---|---|---|---|---|---|
| `/control/metal-mask` | `GET` | N/A | HTML modulo masks | `@login_requerido` | `app/routes.py:12332` |
| `/control/metal-mask/caja` | `GET` | N/A | HTML modulo cajas | `@login_requerido` | `app/routes.py:12342` |
| `/api/masks` | `GET/POST` | query paginacion o JSON nueva mascara | JSON data o alta | `@login_requerido` | `app/routes.py:12353`, `app/routes.py:12393` |
| `/api/masks/<mask_id>` | `PUT` | JSON edicion mascara | JSON resultado | `@login_requerido` | `app/routes.py:12427` |
| `/api/storage` | `GET/POST` | query filtros o JSON alta caja | JSON data/alta | `@login_requerido` | `app/routes.py:12473`, `app/routes.py:12514` |
| `/api/storage/<storage_id>` | `PUT` | JSON edicion caja | JSON resultado | `@login_requerido` | `app/routes.py:12546` |
| `/api/metal-mask/history` | `POST/GET` | JSON registro uso o query filtros | JSON historial/alta | `@login_requerido` | `app/routes.py:10361`, `app/routes.py:10449` |

## 10. Admin / Usuarios / Permisos

| Endpoint | Metodo | Entrada esperada | Salida esperada | Proteccion | Fuente |
|---|---|---|---|---|---|
| `/admin/panel` | `GET` | N/A | HTML panel usuarios | `login_requerido_avanzado` + `requiere_permiso` | `app/user_admin.py:64` |
| `/admin/listar_usuarios` | `GET` | N/A | JSON usuarios + roles | `login_requerido_avanzado` + `requiere_permiso` | `app/user_admin.py:91` |
| `/admin/guardar_usuario` | `POST` | JSON usuario | JSON resultado | `login_requerido_avanzado` + `requiere_permiso` | `app/user_admin.py:193` |
| `/admin/listar_roles` | `GET` | N/A | JSON roles | `login_requerido_avanzado` | `app/user_admin.py:556` |
| `/admin/crear_rol` | `POST` | JSON rol/permisos | JSON resultado | `login_requerido_avanzado` | `app/user_admin.py:1620` |
| `/admin/permisos-dropdowns` | `GET` | N/A | HTML gestion permisos dropdown | Abierta | `app/admin_api.py:8` |
| `/admin/api/roles` | `GET` | N/A | JSON roles | Abierta | `app/admin_api.py:13` |
| `/admin/api/toggle-permission` | `POST` | JSON `role`,`permission_key`,`action` | JSON `{success,message}` | Abierta | `app/admin_api.py:120` |

## 11. Matriz de proteccion (con/sin login)

Resumen por archivo (analisis estatico de decoradores):

| Archivo | Total rutas | Protegidas | Abiertas |
|---|---:|---:|---:|
| `app/routes.py` | 272 | 223 | 49 |
| `app/user_admin.py` | 30 | 29 | 1 |
| `app/api_po_wo.py` | 10 | 0 | 10 |
| `app/aoi_api.py` | 3 | 0 | 3 |
| `app/api_raw_modelos.py` | 2 | 0 | 2 |
| `app/smd_inventory_api.py` | 7 | 0 | 7 |
| `app/smt_routes_clean.py` | 4 | 0 | 4 |
| `app/smt_routes_date_fixed.py` | 2 | 0 | 2 |
| `app/admin_api.py` | 7 | 0 | 7 |
| `app/py/control_modelos_smt.py` | 5 | 0 | 5 |

Totales consolidados:

- Rutas detectadas: 342
- Rutas protegidas: 252
- Rutas abiertas: 90

## 12. Rutas abiertas sensibles (muestra)

Ejemplos de endpoints abiertos con impacto funcional:

- `/api/bom/update-posiciones-assy` (edicion masiva BOM).
- `/guardar_material`, `/importar_excel`, `/actualizar_campo_material` (alta/modificacion materiales).
- `/api/mysql`, `/api/mysql/update`, `/api/mysql/create` (consultas/edicion tablas).
- `/api/plan-run/start|end|pause|resume|status` (control de ejecucion en linea).
- `/api/plan-smd/list`, `/api/plan-smd-diario` (datos operativos planeacion).

Detalle y priorizacion en:

- [HALLAZGOS_TECNICOS_Y_RIESGOS.md](./HALLAZGOS_TECNICOS_Y_RIESGOS.md)

