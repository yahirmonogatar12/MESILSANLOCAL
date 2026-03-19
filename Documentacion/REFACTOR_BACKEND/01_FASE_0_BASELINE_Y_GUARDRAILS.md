# Fase 0 - Baseline y Guardrails

## Objetivo de la fase

Documentar el comportamiento actual del backend, definir una linea base de validacion y establecer guardrails minimos para ejecutar el refactor sin romper login, permisos, materiales, BOM ni planeacion.

## Estado actual observado

- Ya existe documentacion tecnica util en `Documentacion/README_TECNICO_MES.md`, `Documentacion/ARQUITECTURA_SISTEMA_MES.md` y `Documentacion/HALLAZGOS_TECNICOS_Y_RIESGOS.md`.
- No se detecto una carpeta `tests/` ni archivos `test_*.py` o `*_test.py`.
- No existe un baseline de rendimiento formal con endpoints, tiempos esperados y condiciones de prueba.
- El backend depende de MySQL remoto, por lo que cualquier medicion debe registrar entorno y latencia base.
- El archivo principal `app/routes.py` concentra suficiente funcionalidad como para volver inseguro cualquier refactor sin smoke tests previos.

## Archivos y modulos involucrados

- `Documentacion/README_TECNICO_MES.md`
- `Documentacion/ARQUITECTURA_SISTEMA_MES.md`
- `Documentacion/HALLAZGOS_TECNICOS_Y_RIESGOS.md`
- `app/routes.py`
- `app/auth_system.py`
- `run.py`
- `api/index.py`

## Problemas que resuelve

- Evita refactors a ciegas.
- Reduce regresiones silenciosas en login, permisos y rutas sensibles.
- Da un punto de comparacion para tiempos de respuesta y rutas criticas.
- Permite decidir prioridades usando hechos del sistema actual, no intuicion.

## Entregables concretos

- Matriz de endpoints criticos para smoke tests.
- Lista canonica de flujos obligatorios a validar antes y despues de cada fase.
- Plantilla de baseline de rendimiento para endpoints backend.
- Lista de guardrails de refactor y criterios de rollback documental.

## Checklist ejecutable

- [ ] Definir smoke tests minimos para `GET /login`, `POST /login`, `GET /inicio`, `GET /obtener_permisos_usuario_actual`, endpoints clave de materiales, BOM y planeacion.
- [ ] Registrar precondiciones de entorno para correr las pruebas localmente.
- [ ] Documentar que datos semilla o usuarios de prueba se requieren.
- [ ] Definir como registrar tiempos base de endpoints backend sin incluir frontend.
- [ ] Enlazar riesgos activos desde `Documentacion/HALLAZGOS_TECNICOS_Y_RIESGOS.md`.
- [ ] Establecer criterio de "no avanzar de fase" si no existe validacion minima ejecutable.

## Criterios de salida

- Existe una matriz minima de smoke tests con comandos y resultado esperado.
- Existe una linea base inicial de endpoints y tiempos observados.
- Los riesgos criticos del refactor estan enlazados y priorizados.
- Otra persona puede ejecutar la validacion minima sin tener que inferir pasos.

## Riesgos y bloqueos

- Falta de ambiente reproducible local.
- Dependencia de MySQL remoto para pruebas funcionales.
- Ausencia de datos de prueba aislados.
- Posibles diferencias entre `run.py` y `api/index.py` al validar rutas.

## Validacion requerida

- Revision manual de consistencia entre este documento y `00_ESTADO_GLOBAL.md`.
- Confirmar que la lista de smoke tests cubra auth, permisos, materiales, BOM y planeacion.
- Confirmar que cada prueba tenga entrada, salida esperada y criterio de exito.

## Progreso de la fase

- Estado: `En progreso`
- Avance: `20`
- Ultima actualizacion: `2026-03-11`
- Siguiente accion: documentar la matriz inicial de smoke tests y el formato de captura de tiempos base.

## Notas de continuidad

- No mezclar pruebas frontend AJAX en esta fase; el alcance es backend puro.
- Si se agrega cualquier prueba automatizada durante el programa, este documento debe convertirse en la referencia de minima cobertura requerida.
