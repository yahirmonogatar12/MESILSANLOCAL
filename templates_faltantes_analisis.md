# Análisis de Templates AJAX Faltantes

## Rutas AJAX Implementadas vs Templates Existentes

### Control de Proceso (24 rutas)
1. `/control-bom-ajax` → `control_bom_ajax.html` ✅ EXISTE
2. `/control-operacion-linea-smt-ajax` → `control_operacion_linea_smt_ajax.html` ✅ EXISTE
3. `/control-impresion-identificacion-smt-ajax` → `control_impresion_identificacion_smt_ajax.html` ✅ EXISTE
4. `/control-registro-identificacion-smt-ajax` → `control_registro_identificacion_smt_ajax.html` ✅ EXISTE
5. `/historial-operacion-proceso-ajax` → `historial_operacion_proceso_ajax.html` ✅ EXISTE
6. `/bom-management-process-ajax` → `bom_management_process_ajax.html` ✅ EXISTE
7. `/reporte-diario-inspeccion-smt-ajax` → `reporte_diario_inspeccion_smt_ajax.html` ✅ EXISTE
8. `/control-diario-inspeccion-smt-ajax` → `control_diario_inspeccion_smt_ajax.html` ✅ EXISTE
9. `/reporte-diario-inspeccion-proceso-ajax` → `reporte_diario_inspeccion_proceso_ajax.html` ✅ EXISTE
10. `/control-unidad-empaque-modelo-ajax` → `control_unidad_empaque_modelo_ajax.html` ✅ EXISTE
11. `/packaging-register-management-ajax` → `packaging_register_management_ajax.html` ✅ EXISTE
12. `/search-packaging-history-ajax` → `search_packaging_history_ajax.html` ✅ EXISTE
13. `/shipping-register-management-ajax` → `shipping_register_management_ajax.html` ✅ EXISTE
14. `/search-shipping-history-ajax` → `search_shipping_history_ajax.html` ✅ EXISTE
15. `/return-warehousing-register-ajax` → `return_warehousing_register_ajax.html` ✅ EXISTE
16. `/return-warehousing-history-ajax` → `return_warehousing_history_ajax.html` ✅ EXISTE
17. `/registro-movimiento-identificacion-ajax` → `registro_movimiento_identificacion_ajax.html` ✅ EXISTE
18. `/control-otras-identificaciones-ajax` → `control_otras_identificaciones_ajax.html` ✅ EXISTE
19. `/control-movimiento-ns-producto-ajax` → `control_movimiento_ns_producto_ajax.html` ✅ EXISTE
20. `/model-sn-management-ajax` → `model_sn_management_ajax.html` ✅ EXISTE
21. `/control-scrap-ajax` → `control_scrap_ajax.html` ✅ EXISTE

### Control de Producción (9 rutas)
22. `/crear-plan-micom-ajax` → `crear_plan_micom_ajax.html` ✅ EXISTE
23. `/line-material-status-ajax` → `line_material_status_es_ajax.html` ✅ EXISTE
24. `/control-mask-metal-ajax` → `control_mask_metal_ajax.html` ✅ EXISTE
25. `/control-squeegee-ajax` → `control_squeegee_ajax.html` ✅ EXISTE
26. `/control-caja-mask-metal-ajax` → `control_caja_mask_metal_ajax.html` ✅ EXISTE
27. `/estandares-soldadura-ajax` → `estandares_soldadura_ajax.html` ✅ EXISTE
28. `/registro-recibo-soldadura-ajax` → `registro_recibo_soldadura_ajax.html` ✅ EXISTE
29. `/control-salida-soldadura-ajax` → `control_salida_soldadura_ajax.html` ✅ EXISTE
30. `/historial-tension-mask-metal-ajax` → `historial_tension_mask_metal_ajax.html` ✅ EXISTE

### Control de Calidad (10 rutas) - ❌ FALTAN TODOS
31. `/historial-cambio-material-smt-ajax` → ❌ FALTA
32. `/control-resultado-reparacion-ajax` → ❌ FALTA
33. `/control-item-reparado-ajax` → ❌ FALTA
34. `/historial-cambio-material-maquina-ajax` → ❌ FALTA
35. `/historial-uso-pegamento-soldadura-ajax` → ❌ FALTA
36. `/historial-uso-mask-metal-ajax` → ❌ FALTA
37. `/historial-uso-squeegee-ajax` → ❌ FALTA
38. `/process-interlock-history-ajax` → ❌ FALTA
39. `/control-master-sample-smt-ajax` → ❌ FALTA
40. `/historial-inspeccion-master-sample-smt-ajax` → ❌ FALTA
41. `/control-inspeccion-oqc-ajax` → ❌ FALTA

## RESUMEN
- ✅ Templates existentes: 30
- ❌ Templates faltantes: 11 (todos de Control de Calidad)
- 📁 Directorio faltante: `Control de calidad/` en templates

## ACCIÓN REQUERIDA
Crear 11 templates AJAX para Control de Calidad en el directorio:
`app/templates/Control de calidad/`