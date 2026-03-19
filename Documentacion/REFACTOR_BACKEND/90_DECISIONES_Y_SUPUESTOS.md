# Decisiones y Supuestos

Registro de decisiones cerradas y supuestos operativos del programa de refactor backend.

## Decisiones cerradas

| Fecha | Decision | Justificacion |
| --- | --- | --- |
| 2026-03-11 | El alcance del programa es backend puro | El problema principal es el monolito Flask, auth, rutas y acceso a datos; frontend AJAX se trata solo como dependencia. |
| 2026-03-11 | El seguimiento vive en `Documentacion/REFACTOR_BACKEND/` | Ya existe `Documentacion/` como raiz documental del repo y evita dispersar contexto. |
| 2026-03-11 | La granularidad del programa es de 6 fases macro | Da control suficiente sin crear demasiados documentos ni microfases dificiles de mantener. |
| 2026-03-11 | `app_factory.py` es la composicion destino del backend | Ya existe una base de `create_app()` y es el punto correcto para converger bootstrap local y serverless. |
| 2026-03-11 | La llave canonica de sesion es `session['usuario']` | El proyecto ha sufrido inconsistencia historica con `username`; se necesita una sola convencion. |
| 2026-03-11 | El orden de verdad documental inicia en `00_ESTADO_GLOBAL.md` | Evita divergencias cuando varias fases cambian dentro de una misma sesion. |

## Supuestos activos

| Fecha | Supuesto | Impacto |
| --- | --- | --- |
| 2026-03-11 | El backend seguira usando Flask durante este programa | El refactor es estructural, no una migracion de framework. |
| 2026-03-11 | MySQL remoto seguira siendo la base operativa durante las primeras fases | Las mediciones y guardrails deben contemplar latencia de red. |
| 2026-03-11 | Las carpetas `app/routes`, `app/services`, `app/core` y `app/database` son destino parcial, no estado consolidado | No se debe asumir modularizacion real solo por existencia de directorios. |
| 2026-03-11 | No se ejecutara una reescritura total en una sola fase | El programa se mueve por entregables incrementales y validables. |

## Regla de actualizacion

- Agregar una nueva fila cuando una decision arquitectonica quede cerrada.
- No editar filas historicas para reescribir el pasado; agregar una nueva decision que sustituya a la anterior si cambia el criterio.
- Referenciar la fecha exacta del cambio.
