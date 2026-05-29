# Análisis de Mejoras — Repositorio MES ILSAN

> Documento de **solo diagnóstico**. No se modificó código. Cada hallazgo incluye
> referencia a archivo/línea, impacto y propuesta. Priorizado por severidad.
> Fecha del análisis: 2026-05-29.

## Contexto

- App Flask (~78 archivos `.py`, 108 templates HTML, 49 JS, 42 CSS).
- ~83k líneas solo en `.py`/`.js`. Despliegue por GitHub Actions → Azure App Service.
- Refactor en curso: `routes.py` se está partiendo en blueprints bajo `app/api/<seccion>/` (bien encaminado).
- Backend MySQL con pool de conexiones casero; fallback SQLite legacy.

---

## 1. Seguridad (prioridad ALTA)

### 1.1 Hashing de contraseñas con SHA-256 sin sal
[app/auth_system.py:679-681](app/auth_system.py#L679-L681), comparación en [app/auth_system.py:721](app/auth_system.py#L721)

```python
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
...
if usuario['password_hash'] == self.hash_password(password):
```

- **Problema:** SHA-256 es un hash rápido y aquí va **sin sal**, vulnerable a rainbow tables y fuerza bruta masiva. La comparación con `==` no es de tiempo constante (fuga de timing). Lo más revelador: `werkzeug.security.generate_password_hash`/`check_password_hash` **ya están importados** en [app/auth_system.py:17](app/auth_system.py#L17) pero **no se usan**.
- **Propuesta:** migrar a `generate_password_hash` (pbkdf2/scrypt con sal) y `check_password_hash`. Plan de migración: rehashear en el próximo login exitoso (detectar formato viejo, validar con SHA-256, regrabar con el nuevo). No rompe usuarios existentes.

### 1.2 Credencial por defecto `admin / admin123`
[app/auth_system.py:649-656](app/auth_system.py#L649-L656)

- Se siembra un admin con password `admin123` en el arranque. Si nunca se cambió en producción, es acceso total.
- **Propuesta:** forzar cambio de contraseña en primer login, o exigir que el password inicial venga de variable de entorno; documentar el procedimiento.

### 1.3 `SECRET_KEY` con fallback hardcodeado
[app/routes.py:56-58](app/routes.py#L56-L58)

```python
app.secret_key = os.getenv("SECRET_KEY", "fallback_key_for_development_only")
```

- Si `SECRET_KEY` no está en el entorno, se usa una clave conocida y pública (está en el repo) para **firmar las cookies de sesión** → falsificación de sesiones.
- **Propuesta:** fallar al arrancar si `SECRET_KEY` no está definida en producción (p. ej. permitir el fallback solo si `FLASK_ENV=development`).

### 1.4 Cookies de sesión sin flags de seguridad
No se encontró ninguna config de `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE` ni `PERMANENT_SESSION_LIFETIME` en todo `app/`.

- **Problema:** sin `SECURE` la cookie viaja por HTTP plano; sin `SAMESITE` se amplía la superficie de CSRF. La app corre detrás de HTTPS en Azure, así que `SECURE=True` debería ser seguro de activar.
- **Propuesta:** `app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", PERMANENT_SESSION_LIFETIME=...)`.

### 1.5 SQL dinámico con f-strings — auditar lista blanca (riesgo BAJO hoy)
Ejemplos: [app/api/control_material/material_admin.py:280](app/api/control_material/material_admin.py#L280), [app/api/informacion_basica/control_modelos_smt.py:170](app/api/informacion_basica/control_modelos_smt.py#L170), [app/api/pda/shipping.py:928](app/api/pda/shipping.py#L928).

- **Estado actual: aceptable.** Los **valores** van siempre por placeholders `%s`; lo interpolado en el f-string son **identificadores** (columnas/expresiones) que provienen de diccionarios internos del servidor, no de input del usuario (ver patrón seguro en [material_admin.py:257-266](app/api/control_material/material_admin.py#L257-L266)).
- **Propuesta:** documentar la invariante "los f-strings solo interpolan identificadores de una lista blanca del servidor" y añadir una verificación en revisión de código, para que un cambio futuro no meta input de usuario por ahí.

---

## 2. Arquitectura y capa de datos (prioridad ALTA/MEDIA)

### 2.1 Capa de acceso a datos fragmentada y con código muerto
Existen **cinco** puntos de entrada a MySQL:

| Archivo | Estado | Evidencia |
|---|---|---|
| [app/config_mysql.py](app/config_mysql.py) | **Activo** — pool real + `execute_query` | importado por `db_mysql`, `db`, `po_wo_models`, etc. |
| [app/db_mysql.py](app/db_mysql.py) | **Activo** — reexporta `execute_query` de config_mysql ([:5](app/db_mysql.py#L5)) | usado por `app.api.shared` |
| [app/db.py](app/db.py) | **Activo** — wrapper de compatibilidad SQLite/MySQL | |
| [app/config_mysql_hybrid.py](app/config_mysql_hybrid.py) | **CÓDIGO MUERTO** | sin imports en código; solo lo cita un `.md` |
| [app/mysql_http_client.py](app/mysql_http_client.py) | **CÓDIGO MUERTO** | solo lo referencia `config_mysql_hybrid` (que también es muerto) |

- **Propuesta:** eliminar `config_mysql_hybrid.py` y `mysql_http_client.py` (confirmar antes con `git grep`). Documentar que `config_mysql.py` es el único dueño del pool y que el resto solo reexporta.

### 2.2 Tragado silencioso de errores en `execute_query`
[app/config_mysql.py:226-245](app/config_mysql.py#L226-L245)

```python
except Exception as e:
    ...
    print(f"Error ejecutando consulta MySQL: {e}")
    if fetch == 'one': return None
    elif fetch == 'all': return []
    else: return 0
```

- **Problema:** un `INSERT/UPDATE/DELETE` que falla devuelve `0` (igual que "0 filas afectadas"); un `SELECT` que falla devuelve `[]` (igual que "sin resultados"). El llamador **no puede distinguir fallo de vacío**. Esto puede ocultar pérdida de datos. (Hay un caso relacionado, una transacción reportando éxito tras un error parcial, justo el tipo de bug que pediste vigilar en otros módulos.)
- **Propuesta:** propagar la excepción (o devolver un sentinel/`raise`) y dejar que cada endpoint decida. Como mínimo, registrar con nivel `error` y stack, no `print`.

### 2.3 `convert_sqlite_to_mysql` hace reemplazos de texto frágiles
[app/config_mysql.py:247-272](app/config_mysql.py#L247-L272)

- `mysql_query.replace('TEXT', 'TEXT')` es un no-op; `replace('REAL', 'DECIMAL(10,2)')` y `replace('CURRENT_TIMESTAMP', 'NOW()')` son reemplazos de **substring ciegos**: pueden corromper queries donde esos textos aparezcan dentro de literales de cadena, nombres de columna o comentarios (p. ej. una columna `AREAL` o un valor `'CURRENT_TIMESTAMP'`).
- **Propuesta:** como ya todo es MySQL (el fallback SQLite es legacy), evaluar **eliminar la conversión** y escribir SQL MySQL directo. Si se conserva, acotarla con regex de límites de palabra.

### 2.4 Pool size inconsistente entre config y `.env.example`
- [config_mysql.py:44](app/config_mysql.py#L44) usa default `MYSQL_POOL_SIZE=3`; [.env.example:13](.env.example#L13) sugiere `50`; [run.py:15](run.py#L15) sirve con `threads=8`.
- Con 8 hilos y pool de 3, bajo carga se crean/cierran conexiones fuera del pool constantemente (churn). No es un bug, pero desperdicia el pool.
- **Propuesta:** alinear el default con el número de hilos (`>= threads`) y documentar la relación pool↔threads.

### 2.5 Lógica de arranque duplicada
`_env_flag` y `should_run_startup_init` están **copiados** en [app_factory.py:10-24](app_factory.py#L10-L24) y [routes.py:61-80](app/routes.py#L61-L80).
- **Propuesta:** moverlos a un único `app/api/shared/env.py` e importarlos.

---

## 3. Calidad de código y mantenibilidad (prioridad MEDIA)

### 3.1 Archivos monstruo
Top por líneas: [almacen_embarques.py — 5293](app/api/control_proceso/almacen_embarques.py), [shipping_material.py — 4286](app/api/pda/shipping_material.py), [scriptMain.js — 3600](app/static/js/scriptMain.js), [almacen_embarques_history.js — 3104](app/static/js/almacen_embarques_history.js), [control_bom.js — 3027](app/static/js/control_bom.js).
- **Problema:** difíciles de revisar, probar y navegar; alto riesgo en cada cambio.
- **Propuesta:** partir por responsabilidad (queries / lógica de negocio / endpoints). El refactor de blueprints ya marca el camino; aplicar el mismo criterio dentro de los módulos grandes.

### 3.2 Decorador `login_requerido` reproducido como proxy en 13 archivos
13 definiciones ([conteo](app/api/__init__.py)) — la mayoría son **proxies** idénticos que reenvían a `app.routes.login_requerido` para evitar import circular (ver [plan_assy.py:59-66](app/api/control_produccion/plan_assy.py#L59-L66)).
- **No es hueco de seguridad** (todos terminan en el mismo decorador real), pero es boilerplate repetido y el proxy re-envuelve `f` en **cada request** (overhead menor).
- `app.api.shared` **ya expone** `login_requerido` de forma lazy ([shared/__init__.py:43-53](app/api/shared/__init__.py#L43-L53)).
- **Propuesta:** reemplazar los 13 proxies por `from app.api.shared import login_requerido` (y `requiere_permiso_dropdown`). Elimina ~13 bloques duplicados.

### 3.3 `print()` como logging (460+ ocurrencias)
[búsqueda](app/db_mysql.py) — 460+ `print(...)` en 15+ archivos, incluido un `print` en el **hot path** de auth en cada request ([routes.py:272](app/routes.py#L272)).
- **Problema:** sin niveles, sin timestamps estructurados, ruido en stdout de producción, y el print por-request añade I/O.
- **Propuesta:** migrar a `logging` con niveles (`INFO`/`WARNING`/`ERROR`) y un handler único. Quitar los prints por-request.

### 3.4 Ausencia total de pruebas
`git ls-files` no encuentra **ningún** archivo de test (`test_*`, `tests/`, `conftest`, `pytest`). El CI solo hace `compileall` + un smoke test de imports/rutas ([workflow:40-59](.github/workflows/main_ilsan-mes.yml#L40-L59)).
- **Problema:** ~83k LOC de lógica de negocio (inventarios, embarques, calidad) sin red de seguridad. Cada refactor —como el de blueprints en curso— se valida solo "a mano".
- **Propuesta:** empezar por tests de las funciones puras de negocio (p. ej. `_ict_pass_fail_real_counts`, cálculos de inventario consolidado) y de los helpers compartidos; luego tests de endpoints con `app.test_client()`. Añadir `pytest` al CI.

### 3.5 73 marcadores TODO/FIXME/HACK
en archivos `.py`. Útiles como backlog, pero conviene convertirlos en issues rastreables en vez de dejarlos enterrados en el código.

---

## 4. Higiene del repositorio (prioridad MEDIA/BAJA)

### 4.1 Binarios y datos operativos versionados
- [app/database/ISEMM_MES.db](app/database/ISEMM_MES.db) — base SQLite **commiteada** (el fallback legacy). Engorda el repo y puede contener datos.
- `app/static/Thumbs.db` y `app/static/icons/Thumbs.db` — artefactos de Windows (basura).
- [backups/](backups/) — 12 dumps CSV/JSON de operación (cierres de embarques, movimientos) versionados. Son datos de runtime, no fuente.
- **Propuesta:** sacarlos de git (`git rm --cached`), añadir a `.gitignore` (`*.db`, `Thumbs.db`, `backups/`). Si el `.db` se necesita como semilla, versionar un esquema/seed, no la base con datos.

### 4.2 Tres configuraciones de despliegue, una sola activa
Coexisten [Dockerfile](Dockerfile), [vercel.json](vercel.json) y [runtime.txt](runtime.txt), pero el CI despliega a **Azure App Service** ([workflow](.github/workflows/main_ilsan-mes.yml)).
- **Propuesta:** confirmar cuál es el target real y eliminar los configs huérfanos (probablemente `vercel.json` y `Dockerfile`) para evitar confusión sobre cómo/ dónde corre la app.

### 4.3 `aplication.py` de una sola línea
[aplication.py](aplication.py) = `from run import app`. Nombre con typo ("aplication"), probablemente requerido por el entry point de Azure.
- **Propuesta:** si Azure lo exige, dejar un comentario explicando por qué existe; si no, eliminarlo.

---

## 5. Observabilidad y operación (prioridad BAJA)

- **Sin healthcheck informativo:** la ruta `/` devuelve `"ok"` ([app_factory.py:62-65](app_factory.py#L62-L65)) pero no verifica BD. Un `/health` que pruebe el pool daría señal real a Azure.
- **Logs de config con credenciales parciales:** [config_mysql.py:39](app/config_mysql.py#L39) imprime host/db/user al cargar. Aceptable, pero conviene asegurarse de no escalar a imprimir password en ningún punto.
- **Emojis/caracteres no-ASCII en prints** dentro de rutas de arranque pueden romper en consolas sin UTF-8 (el CI ya tuvo que forzar `PYTHONIOENCODING=utf-8`).

---

## 6. Tabla de priorización

| # | Hallazgo | Severidad | Esfuerzo | Riesgo de no actuar |
|---|---|:---:|:---:|---|
| 1.1 | SHA-256 sin sal para passwords | 🔴 Alta | Medio | Compromiso de credenciales |
| 1.2 | Admin por defecto `admin123` | 🔴 Alta | Bajo | Acceso total no autorizado |
| 1.3 | `SECRET_KEY` con fallback público | 🔴 Alta | Bajo | Falsificación de sesiones |
| 1.4 | Cookies sin `Secure`/`SameSite` | 🟠 Media-Alta | Bajo | Robo de sesión / CSRF |
| 2.2 | `execute_query` traga errores | 🟠 Media-Alta | Medio | Pérdida silenciosa de datos |
| 2.1 | Capa DB fragmentada + código muerto | 🟠 Media | Bajo | Confusión, mantenimiento |
| 3.4 | Cero pruebas automatizadas | 🟠 Media | Alto | Regresiones en refactors |
| 2.3 | `convert_sqlite_to_mysql` frágil | 🟡 Media-Baja | Bajo | Corrupción de queries raros |
| 3.3 | `print()` en vez de logging | 🟡 Baja | Medio | Operación a ciegas |
| 3.1 | Archivos de 3k-5k líneas | 🟡 Baja | Alto | Velocidad/calidad de cambios |
| 3.2 | 13 proxies `login_requerido` | 🟡 Baja | Bajo | Boilerplate, overhead menor |
| 4.1 | `.db`/`backups`/`Thumbs.db` en git | 🟡 Baja | Bajo | Repo pesado, fuga de datos |
| 4.2 | 3 configs de deploy | 🟢 Muy baja | Bajo | Confusión |

---

## 7. Lo que ya está BIEN (no tocar)

- El refactor `routes.py` → blueprints está bien estructurado y documentado ([app/api/__init__.py](app/api/__init__.py)).
- El patrón de filtros con lista blanca de identificadores + `%s` para valores ([material_admin.py:257-282](app/api/control_material/material_admin.py#L257-L282)) es la forma correcta.
- El pool de conexiones con `ping`/reciclado ([config_mysql.py:94-128](app/config_mysql.py#L94-L128)) es razonable.
- El smoke test del CI, aunque mínimo, atrapa errores de import y de registro de rutas.
- La protección contra fuerza bruta con bloqueo por intentos fallidos ([auth_system.py:683-728](app/auth_system.py#L683-L728)) existe — buena base.

---

### Nota de alcance
Este informe es estático (lectura de código + grep + estructura). No se ejecutó la app
ni se probó contra la BD. Los hallazgos de seguridad 1.1–1.3 deberían atenderse antes
que cualquier otra cosa. Ningún archivo de código fue modificado.
