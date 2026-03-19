# Fase 4 - Planificacion, Produccion y SMT

## Objetivo de la fase

Reordenar planeacion, produccion, PO/WO y SMT en limites funcionales coherentes, escogiendo una implementacion SMT canonica y reduciendo la dispersion actual entre modulos.

## Estado actual observado

- `app/routes.py` contiene muchos endpoints de planificacion y produccion.
- `app/api_po_wo.py` agrega otra parte del dominio PO/WO y tambien registra blueprint.
- Existen cinco archivos SMT competidores: `app/smt_routes.py`, `app/smt_routes_clean.py`, `app/smt_routes_date_fixed.py`, `app/smt_routes_fixed.py`, `app/smt_routes_simple.py`.
- La composicion actual puede registrar SMT desde mas de un punto segun entrypoint.
- Hay rutas de planeacion diaria, corridas, historial y datos AOI repartidas entre varios archivos.

## Archivos y modulos involucrados

- `app/routes.py`
- `app/api_po_wo.py`
- `app/po_wo_models.py`
- `app/models_po_wo.py`
- `app/smt_routes.py`
- `app/smt_routes_clean.py`
- `app/smt_routes_date_fixed.py`
- `app/smt_routes_fixed.py`
- `app/smt_routes_simple.py`
- `app/aoi_api.py`

## Problemas que resuelve

- Evita tener varias fuentes de verdad para SMT.
- Reduce el riesgo de rutas duplicadas y handlers ambiguos.
- Permite separar planeacion, ejecucion de corridas y reportes operativos.
- Facilita medir regresiones por subdominio productivo.

## Entregables concretos

- Decision documentada sobre la implementacion SMT canonica.
- Mapa de subdominios: PO/WO, plan, plan-imd, plan-smt, plan-smd, corridas y AOI.
- Orden de extraccion por riesgo y dependencia.
- Lista de endpoints que requieren pruebas de regresion obligatoria.

## Checklist ejecutable

- [ ] Catalogar endpoints de planificacion y produccion que siguen en `app/routes.py`.
- [ ] Delimitar que responsabilidad se queda en `app/api_po_wo.py` y cual debe migrarse.
- [ ] Escoger la implementacion SMT canonica y documentar que archivos quedan legacy.
- [ ] Listar rutas con colision o solapamiento funcional.
- [ ] Definir orden de extraccion para plan, corridas y reportes.
- [ ] Marcar endpoints con dependencia cruzada a AOI o historial como alto riesgo.

## Criterios de salida

- Existe una implementacion SMT canonica elegida y justificada.
- El dominio de planeacion queda dividido por subdominios claros.
- Hay una lista de endpoints criticos con validacion obligatoria.
- Estan identificados los modulos legacy que no deben seguir creciendo.

## Riesgos y bloqueos

- SMT tiene variantes con diferencias historicas no documentadas completamente.
- Planeacion y corridas pueden depender de tablas y estados compartidos.
- Cambios de ownership pueden romper reportes o historial si se mezcla AOI/SMT.
- Sin baseline previo es dificil distinguir regresion funcional de deuda preexistente.

## Validacion requerida

- Confirmar que la decision SMT canonica cubra los casos usados en local y despliegue.
- Confirmar que el mapa de subdominios refleje el codigo actual, no una arquitectura deseada abstracta.
- Confirmar que los endpoints marcados de alto riesgo tengan coverage en la Fase 0.

## Progreso de la fase

- Estado: `No iniciado`
- Avance: `5`
- Ultima actualizacion: `2026-03-11`
- Siguiente accion: documentar comparativo minimo entre las cinco variantes SMT y escoger la canonica.

## Notas de continuidad

- Esta fase no debe avanzar hasta cerrar la composicion de app en Fase 1.
- Si se detecta una colision nueva de rutas durante el trabajo, registrar primero en Fase 1 y despues aqui.
