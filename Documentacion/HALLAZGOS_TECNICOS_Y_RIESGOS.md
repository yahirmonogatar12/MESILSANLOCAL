# Hallazgos Tecnicos y Riesgos

Documento de riesgos tecnicos detectados en el estado actual del codigo.

## 1. Hallazgos de severidad Alta

## 1.1 Endpoints sensibles sin proteccion de sesion

Ejemplos relevantes:

- `POST /api/bom/update-posiciones-assy` (`app/routes.py:2912`)
- `POST /guardar_material` (`app/routes.py:3015`)
- `POST /importar_excel` (`app/routes.py:3200`)
- `POST /actualizar_campo_material` (`app/routes.py:3405`)
- `POST /api/plan-run/start|end|pause|resume` (`app/routes.py:11930`, `:12063`, `:12141`, `:12173`)
- `GET /api/plan-run/status` (`app/routes.py:12197`)
- `GET /api/plan-smd/list` (`app/routes.py:11755`)

Impacto:

- Escritura/alteracion de datos productivos sin control central de autenticacion.
- Mayor superficie para abuso interno/externo si hay exposicion de red.

Recomendacion:

1. Aplicar `@login_requerido` o `@auth_system.login_requerido_avanzado` en endpoints de mutacion.
2. Definir politica por blueprint (default deny).
3. Agregar pruebas automatizadas de proteccion por ruta critica.

## 1.2 API SQL abierta y con CORS amplio

Endpoints:

- `/api/mysql` (`app/routes.py:11045`)
- `/api/mysql/columns` (`app/routes.py:11288`)
- `/api/mysql/data` (`app/routes.py:11314`)
- `/api/mysql/update` (`app/routes.py:11399`)
- `/api/mysql/create` (`app/routes.py:11533`)
- `/api/mysql/delete` (`app/routes.py:11633`) (este si protegido)

Notas:

- `/api/mysql` permite SQL GET/POST (restringe `SELECT/SHOW`, pero sigue abierto).
- Se adiciona `Access-Control-Allow-Origin: *` en rutas proxy/API simple.

Impacto:

- Exposicion de metadatos y datos tabulares sin control uniforme.
- Riesgo de exfiltracion y abuso de consultas costosas.

Recomendacion:

1. Cerrar acceso anonimo.
2. Mover a red interna o exigir token firmado.
3. Limitar tablas permitidas y rate limit por cliente.

## 1.3 Duplicidad de rutas por registro multiple de blueprints

Caso confirmado:

- `/api/historial_smt_data` registrado por:
  - `smt.get_historial_smt_data` (`app/smt_routes_date_fixed.py`)
  - `smt_api.api_historial_smt_data` (`app/smt_routes_clean.py`)

Tambien `/` se define en `app/routes.py` y en `run.py`/`api/index.py`.

Impacto:

- Ambiguedad de handler efectivo.
- Dificultad para debugging y trazabilidad funcional.

Recomendacion:

1. Mantener una sola implementacion por endpoint.
2. Definir estrategia unica de registro por entorno.
3. Validar colisiones en CI (script que inspeccione `app.url_map`).

## 2. Hallazgos de severidad Media

## 2.1 Inconsistencia de sesion (`usuario` vs `username`)

Ejemplos:

- `session['usuario']` en login y decoradores (`app/routes.py:375`, `app/routes.py:268`).
- `session['username']` en filtros/permisos (`app/routes.py:214`, `app/routes.py:7537`).
- `session.get('username')` en admin (`app/user_admin.py:1439`).

Impacto:

- Falsos negativos de autenticacion/autorizacion.
- comportamiento inconsistente entre modulos.

Recomendacion:

1. Estandarizar key canonica (`usuario`).
2. Proveer helper unico `get_current_user()`.
3. Refactor gradual con tests de regresion.

## 2.2 SQL dialect mismatch (MySQL vs SQLite) en rutas de import

Se detecta `INSERT OR REPLACE` en rutas que operan con MySQL:

- `control_almacen`, `control_salida`, `control_retorno`, `registro_material_real`,
  `estatus_inventario`, `material_recibido`, `historial_inventario` en `app/routes.py:8994+`.

En `admin_api.py` se detecta `INSERT OR IGNORE` (`app/admin_api.py:225`).

Impacto:

- Errores en runtime o comportamiento no determinista segun backend real.

Recomendacion:

1. Normalizar a SQL MySQL (`INSERT ... ON DUPLICATE KEY UPDATE` o `INSERT IGNORE` segun caso).
2. Revisar constraints unique por tabla para definir upsert correcto.

## 2.3 Duplicidad/solapamiento de logica frontend

Solapamientos:

- `MaterialTemplate.html` contiene orquestacion AJAX extensa.
- `app/static/js/scriptMain.js` reimplementa flujos equivalentes.
- Modulos inline (ej. `CONTROL_DE_BOM.html`) agregan otra capa de logica.

Impacto:

- Mayor probabilidad de regresiones por cambios no sincronizados.

Recomendacion:

1. Declarar un unico owner por flujo (shell vs modulo).
2. Migrar scripts inline a archivos JS modulares.
3. Mantener API de eventos clara (`init`/`cleanup`) por modulo.

## 2.4 Ruta legacy/deprecada BOM fragil

- `/control-bom-ajax` usa `mysql.connection.cursor()` (`app/routes.py:4816`), pero no existe `mysql` definido en `routes.py`.

Impacto:

- Falla en runtime si se activa flujo legacy.

Recomendacion:

1. Retirar ruta legacy o adaptarla a `get_db_connection()`.
2. Eliminar invocaciones legacy desde `scriptMain.js`.

## 2.5 Inicializacion de schema con side-effects de import

- Creacion/migracion de tablas en import de `app/routes.py` y `app/po_wo_models.py`.

Impacto:

- Tiempo de arranque variable.
- Riesgo de alterar schema en cold start serverless.

Recomendacion:

1. Mover migraciones a job explicito de despliegue.
2. Mantener inicializacion read-only al importar modulo app.

## 3. Hallazgos de severidad Baja

## 3.1 Endpoints de test/debug abiertos

Ejemplos:

- `/test_modelos` (`app/routes.py:6663`)
- `/api/status` (`app/routes.py:11115`)
- `/debug/env` en `api/index.py` (si se despliega sin control)

Recomendacion:

- Restringir por entorno (`DEBUG`), IP o auth.

## 3.2 Logging sensible de configuracion

- `config_mysql.py` imprime host/db/user al importar.

Recomendacion:

- Enmascarar o eliminar logs de credenciales/infra en produccion.

## 4. Priorizacion de remediacion

## 4.1 Alta prioridad (inmediato)

1. Cerrar rutas de mutacion abiertas.
2. Restringir API SQL/proxy abierta.
3. Resolver colisiones de rutas duplicadas.

## 4.2 Prioridad media (siguiente iteracion)

1. Unificar clave de sesion (`usuario`).
2. Corregir SQL dialect mismatch (`INSERT OR REPLACE/IGNORE`).
3. Desactivar BOM legacy (`/control-bom-ajax`) y flujo duplicado.

## 4.3 Prioridad baja (hardening continuo)

1. Reducir logs sensibles.
2. Encapsular test/debug endpoints por entorno.
3. Preparar plan de migraciones versionadas (Alembic o equivalente).

