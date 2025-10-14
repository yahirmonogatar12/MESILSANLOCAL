# INSTRUCCIONES PARA IMPLEMENTAR MÓDULOS AJAX

## PASO 1: PREPARACIÓN DE LA LISTA (YA COMPLETADO)
- Los botones en `LISTA_CONTROL_DE_PROCESO.html` ya están preparados con el patrón AJAX
- Los contenedores ya están agregados en `MaterialTemplate.html`
- La función `hideAllMaterialContainers` ya incluye todos los contenedores

## PASO 2: AGREGAR FUNCIONES JAVASCRIPT
1. Abrir `app/static/js/scriptMain.js`
2. Copiar las funciones del archivo `control-proceso-ajax-functions-template.js`
3. Pegarlas al final del archivo (antes del cierre del DOMContentLoaded)

## PASO 3: AGREGAR RUTAS EN FLASK
1. Abrir `app/routes.py`
2. Copiar las rutas del archivo `control-proceso-routes-template.py`
3. Agregarlas en la sección correspondiente de rutas

## PASO 4: CREAR TEMPLATES HTML
Para cada módulo, crear un archivo HTML en `app/templates/Control de proceso/`:

### Nomenclatura de archivos:
- `control_impresion_identificacion_smt_ajax.html`
- `control_registro_identificacion_smt_ajax.html`
- `historial_operacion_proceso_ajax.html`
- `bom_management_process_ajax.html`
- `reporte_diario_inspeccion_smt_ajax.html`
- `control_diario_inspeccion_smt_ajax.html`
- `reporte_diario_inspeccion_proceso_ajax.html`
- `control_unidad_empaque_modelo_ajax.html`
- `packaging_register_management_ajax.html`
- `search_packaging_history_ajax.html`
- `shipping_register_management_ajax.html`
- `search_shipping_history_ajax.html`
- `return_warehousing_register_ajax.html`
- `return_warehousing_history_ajax.html`
- `registro_movimiento_identificacion_ajax.html`
- `control_otras_identificaciones_ajax.html`
- `control_movimiento_ns_producto_ajax.html`
- `model_sn_management_ajax.html`
- `control_scrap_ajax.html`

### Usar el template de ejemplo:
1. Copiar el contenido de `template-ajax-ejemplo.html`
2. Reemplazar:
   - `[NOMBRE DEL MÓDULO]` con el nombre del módulo
   - `[sufijo-unico]` con el sufijo único (ejemplo: `impresion-identificacion-smt`)
   - `[nombre-contenedor]` con el nombre del contenedor
   - `[nombre-modulo]` con el nombre en minúsculas y guiones
   - `[NombreModulo]` con el nombre en CamelCase para JavaScript
   - `[Título del Módulo]` con el título visible

## PASO 5: VERIFICACIÓN
1. Reiniciar el servidor Flask
2. Navegar a Control de Proceso
3. Hacer clic en cada botón para verificar que carga correctamente
4. Verificar en la consola del navegador que no hay errores

## MAPEO DE NOMBRES

| Botón | Contenedor | Sufijo | Función JS |
|-------|------------|--------|------------|
| Control de impresion de identificacion de SMT | control-impresion-identificacion-smt-unique-container | impresion-identificacion-smt | mostrarControlImpresionIdentificacionSMT |
| Control de registro de identificacion de SMT | control-registro-identificacion-smt-unique-container | registro-identificacion-smt | mostrarControlRegistroIdentificacionSMT |
| Historial de operacion por proceso | historial-operacion-proceso-unique-container | historial-operacion-proceso | mostrarHistorialOperacionProceso |
| BOM Management By Process | bom-management-process-unique-container | bom-management-process | mostrarBOMManagementProcess |
| Reporte diario de inspeccion de SMT | reporte-diario-inspeccion-smt-unique-container | reporte-diario-inspeccion-smt | mostrarReporteDiarioInspeccionSMT |
| Control diario de inspeccion de SMT | control-diario-inspeccion-smt-unique-container | control-diario-inspeccion-smt | mostrarControlDiarioInspeccionSMT |
| Reporte diario de inspeccion por proceso | reporte-diario-inspeccion-proceso-unique-container | reporte-diario-inspeccion-proceso | mostrarReporteDiarioInspeccionProceso |
| Control de unidad de empaque por modelo | control-unidad-empaque-modelo-unique-container | control-unidad-empaque-modelo | mostrarControlUnidadEmpaqueModelo |
| Packaging Register Management | packaging-register-management-unique-container | packaging-register-management | mostrarPackagingRegisterManagement |
| Search Packaging History | search-packaging-history-unique-container | search-packaging-history | mostrarSearchPackagingHistory |
| Shipping Register Management | shipping-register-management-unique-container | shipping-register-management | mostrarShippingRegisterManagement |
| Search Shipping History | search-shipping-history-unique-container | search-shipping-history | mostrarSearchShippingHistory |
| Return Warehousing Register | return-warehousing-register-unique-container | return-warehousing-register | mostrarReturnWarehousingRegister |
| Return Warehousing History | return-warehousing-history-unique-container | return-warehousing-history | mostrarReturnWarehousingHistory |
| Registro de movimiento de identificacion | registro-movimiento-identificacion-unique-container | registro-movimiento-identificacion | mostrarRegistroMovimientoIdentificacion |
| Control de otras identificaciones | control-otras-identificaciones-unique-container | control-otras-identificaciones | mostrarControlOtrasIdentificaciones |
| Control de movimiento de N/S de producto | control-movimiento-ns-producto-unique-container | control-movimiento-ns-producto | mostrarControlMovimientoNSProducto |
| Model S/N Management | model-sn-management-unique-container | model-sn-management | mostrarModelSNManagement |
| Control de Scrap | control-scrap-unique-container | control-scrap | mostrarControlScrap |

## NOTAS IMPORTANTES
- Cada módulo debe tener IDs únicos usando el sufijo correspondiente
- Los estilos CSS deben estar encapsulados con clases específicas del módulo
- Las funciones JavaScript deben estar en el scope global (window.)
- Siempre incluir la auto-inicialización en el template
- Mantener la estructura de carpetas consistente
