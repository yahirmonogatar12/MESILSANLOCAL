# Programa de Refactor Backend

Esta carpeta es la fuente de verdad del refactor backend de MES ILSAN. Su objetivo es conservar el contexto operativo entre sesiones y dejar claro que fase esta activa, que falta, que bloquea y cual es la siguiente accion concreta.

## Objetivo del programa

- Reducir el acoplamiento del backend Flask actual.
- Sacar responsabilidades del monolito `app/routes.py`.
- Unificar composicion de app, auth, permisos y acceso a datos.
- Ejecutar el refactor por fases sin perder trazabilidad.

## Indice

- [00_ESTADO_GLOBAL.md](./00_ESTADO_GLOBAL.md)
- [01_FASE_0_BASELINE_Y_GUARDRAILS.md](./01_FASE_0_BASELINE_Y_GUARDRAILS.md)
- [02_FASE_1_BOOTSTRAP_Y_COMPOSICION.md](./02_FASE_1_BOOTSTRAP_Y_COMPOSICION.md)
- [03_FASE_2_AUTH_ADMIN_Y_SESION.md](./03_FASE_2_AUTH_ADMIN_Y_SESION.md)
- [04_FASE_3_MATERIAL_BOM_E_INVENTARIO.md](./04_FASE_3_MATERIAL_BOM_E_INVENTARIO.md)
- [05_FASE_4_PLANIFICACION_PRODUCCION_Y_SMT.md](./05_FASE_4_PLANIFICACION_PRODUCCION_Y_SMT.md)
- [06_FASE_5_CAPA_DE_DATOS_Y_DEPRECACION.md](./06_FASE_5_CAPA_DE_DATOS_Y_DEPRECACION.md)
- [90_DECISIONES_Y_SUPUESTOS.md](./90_DECISIONES_Y_SUPUESTOS.md)
- [99_BITACORA.md](./99_BITACORA.md)

## Como se actualiza el tablero

1. Actualizar primero [00_ESTADO_GLOBAL.md](./00_ESTADO_GLOBAL.md).
2. Actualizar despues el archivo de la fase tocada.
3. Registrar la sesion en [99_BITACORA.md](./99_BITACORA.md).
4. Si hubo una decision arquitectonica o un supuesto nuevo, registrarlo en [90_DECISIONES_Y_SUPUESTOS.md](./90_DECISIONES_Y_SUPUESTOS.md).

## Convenciones

- Estados permitidos: `No iniciado`, `En progreso`, `Bloqueado`, `Completado`.
- Fecha canonica: `YYYY-MM-DD`.
- Progreso: porcentaje entero de `0` a `100`.
- Siempre capturar `Siguiente accion` concreta.
- El orden de verdad es:
  1. [00_ESTADO_GLOBAL.md](./00_ESTADO_GLOBAL.md)
  2. archivo de fase
  3. [90_DECISIONES_Y_SUPUESTOS.md](./90_DECISIONES_Y_SUPUESTOS.md)
  4. [99_BITACORA.md](./99_BITACORA.md)

## Estado inicial sembrado

- Fecha base: `2026-03-11`
- Alcance: backend puro
- Granularidad: 6 fases macro
- Estado general: refactor documentado, no iniciado como programa de ejecucion formal

## Documentacion vigente relacionada

- [../README_TECNICO_MES.md](../README_TECNICO_MES.md)
- [../ARQUITECTURA_SISTEMA_MES.md](../ARQUITECTURA_SISTEMA_MES.md)
- [../CATALOGO_MODULOS_Y_RUTAS.md](../CATALOGO_MODULOS_Y_RUTAS.md)
- [../MODELO_DE_DATOS_MYSQL.md](../MODELO_DE_DATOS_MYSQL.md)
- [../HALLAZGOS_TECNICOS_Y_RIESGOS.md](../HALLAZGOS_TECNICOS_Y_RIESGOS.md)

## Regla de uso

Esta carpeta documenta el estado real observado del repo. No debe describir un backend idealizado ni asumir que una fase ya se completo por existir directorios vacios o experimentos parciales.
