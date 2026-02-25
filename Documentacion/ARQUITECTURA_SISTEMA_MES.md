# Arquitectura del Sistema MES

## 1. Entry points y bootstrap

## 1.1 Local (`run.py`)

Archivo: `run.py`

Secuencia de arranque:

1. Carga `.env` con `dotenv`.
2. Importa `app` desde `app/routes.py` (esto ejecuta inicializacion de DB y registro de varias rutas/blueprints).
3. Registra blueprints/rutas adicionales:
   - `register_smt_routes(app)` desde `app/smt_routes_clean.py`
   - `registrar_rutas_po_wo(app)` desde `app/api_po_wo.py`
   - `app.register_blueprint(aoi_api)` desde `app/aoi_api.py`
   - `app.register_blueprint(control_modelos_bp)` desde `app/py/control_modelos_smt.py`
   - `api_raw` condicional (si no existe ya)
4. Agrega `GET /` (endpoint `health`) que retorna `"ok", 200`.

## 1.2 Serverless (`api/index.py`)

Archivo: `api/index.py`

Flujo equivalente a `run.py`, con diferencias:

- `GET /` retorna JSON (`status`, `message`).
- Expone `GET /debug/env` para revisar variables en despliegue.
- Comentario explicito: Vercel toma la variable `app` directamente.

## 1.3 Vercel routing (`vercel.json`)

Archivo: `vercel.json`

- Build python sobre `api/index.py`.
- Regla catch-all:
  - `src: "/(.*)"`
  - `dest: "api/index.py"`

Resultado: todo request HTTP entra por `api/index.py` en entorno Vercel.

## 2. Registro de blueprints y rutas

## 2.1 Registro base en `app/routes.py`

Archivo: `app/routes.py`

- Crea `app = Flask(__name__)`.
- `register_smd_inventory_routes(app)` (`app/smd_inventory_api.py`).
- Registra `api_raw` si no existe (`app/api_raw_modelos.py`).
- Registra `smt_bp` (`app/smt_routes_date_fixed.py`).
- Registra admin:
  - `app.register_blueprint(user_admin_bp, url_prefix='/admin')`
  - `app.register_blueprint(admin_bp)` (ya trae `url_prefix='/admin'` en su blueprint).

Nota: `registrar_rutas_po_wo(app)` esta comentado en `app/routes.py` para evitar conflicto con `run.py`.

## 2.2 Registro adicional en `run.py` y `api/index.py`

- SMT historial extendido (`smt_routes_clean`).
- API PO/WO (`api_po_wo`).
- API AOI (`aoi_api`).
- Control modelos SMT (`control_modelos_bp`).

## 2.3 Duplicidades detectadas por composicion de entrypoints

Con `run.py`/`api/index.py` activos sobre `app/routes.py`:

- `GET /` existe 2 veces:
  - `index` en `app/routes.py` (`/` -> redirect a `/inicio`)
  - `health` en `run.py` o `api/index.py`
- `GET /api/historial_smt_data` existe 2 veces:
  - `smt.get_historial_smt_data` (`app/smt_routes_date_fixed.py`)
  - `smt_api.api_historial_smt_data` (`app/smt_routes_clean.py`)

Esto introduce ambiguedad en resolucion de rutas y mantenimiento.

## 3. Arquitectura por capas

## 3.1 Capa UI / Presentacion

- Shell principal: `app/templates/MaterialTemplate.html`.
- JS global de orquestacion: `app/static/js/scriptMain.js`.
- Carga dinamica AJAX de fragmentos HTML:
  - Listas: `/listas/...`
  - Modulos: `/informacion_basica/...`, `/material/...`, `/control_proceso/...`

Patron dominante:

1. Click en sidebar/nav.
2. `window.cargarContenidoDinamico(containerId, templatePath)`.
3. `fetch(templatePath)` (cookies de sesion incluidas).
4. Inyeccion HTML en contenedor y ejecucion de scripts embebidos.

## 3.2 Capa HTTP (rutas Flask)

- Monolito principal: `app/routes.py` (272 decoradores `@app.route` detectados).
- Blueprints de dominio:
  - `app/user_admin.py`
  - `app/admin_api.py`
  - `app/api_po_wo.py`
  - `app/aoi_api.py`
  - `app/api_raw_modelos.py`
  - `app/smd_inventory_api.py`
  - `app/smt_routes_clean.py`
  - `app/smt_routes_date_fixed.py`
  - `app/py/control_modelos_smt.py`

## 3.3 Capa autenticacion/permisos

- `app/auth_system.py`:
  - login con hash SHA-256.
  - sesiones activas y auditoria.
  - decoradores:
    - `login_requerido_avanzado`
    - `requiere_permiso(modulo, accion)`
- `app/routes.py` define tambien `login_requerido` simple (basado en `session['usuario']`).

## 3.4 Capa datos/config

- Conectividad y pooling: `app/config_mysql.py`.
  - pool manual con `_MAX_POOL_SIZE = 3`.
- Operaciones DB y migraciones: `app/db_mysql.py`.
- Capa de compatibilidad MySQL/SQLite: `app/db.py`.
- Migraciones adicionales por dominio:
  - `app/po_wo_models.py`
  - funciones de creacion en `app/routes.py` (plan_smt, plan_smd, plan_smd_runs, trazabilidad, masks/storage).

## 4. Flujo request-response (diagrama textual)

### 4.1 Flujo HTML dinamico (modulo)

```text
Browser (MaterialTemplate)
  -> fetch('/informacion_basica/control_de_bom')
Flask route (app/routes.py::control_de_bom_ajax)
  -> db_mysql.obtener_modelos_bom()
  -> render_template('INFORMACION BASICA/CONTROL_DE_BOM.html', modelos=...)
Browser
  -> inject HTML + init listeners (event delegation)
```

### 4.2 Flujo API de datos (BOM)

```text
Browser (CONTROL_DE_BOM.html)
  -> fetch('/listar_bom', POST JSON {modelo, classification?})
Flask route (app/routes.py::listar_bom)
  -> db_mysql.listar_bom_por_modelo(modelo, classification)
MySQL (tabla bom)
  -> rows
Flask -> JSON mapeado a claves frontend
Browser -> render tabla y cache local
```

## 5. Diferencias Local vs Vercel

## 5.1 Local (`run.py`)

- Respuesta de health:
  - `GET /` -> texto `"ok"`.
- Ideal para desarrollo interactivo con `debug=True`.

## 5.2 Vercel (`api/index.py`)

- `GET /` -> JSON de estado.
- `GET /debug/env` disponible (util en troubleshooting de variables).
- Cold start puede amplificar costo de inicializacion por side-effects al importar `app/routes.py`.

## 5.3 Side-effects de import relevantes

Al importar `app/routes.py` se ejecutan operaciones de inicializacion:

- `init_db()` y migraciones en `db_mysql`.
- `auth_system.init_database()`.
- `crear_tabla_plan_smt_v2()`.
- `crear_tabla_plan_smd()`.
- `crear_tabla_plan_smd_runs()`.
- `crear_tabla_trazabilidad()`.
- `init_metal_mask_tables()`.

Adicionalmente `app/po_wo_models.py` ejecuta en import:

- `crear_tablas_po_wo()`
- `migrar_tabla_embarques()`
- `migrar_tabla_work_orders()`
- `migrar_tabla_plan_main()`

## 6. Observaciones de diseno

- Arquitectura actual: monolito Flask con UI server-rendered + AJAX heavy.
- Puntos de acoplamiento alto:
  - `MaterialTemplate.html` + `scriptMain.js` + scripts inline de cada modulo.
  - migraciones ejecutadas en runtime/import en multiples archivos.
- Riesgos principales de arquitectura:
  - rutas duplicadas por doble registro de blueprints.
  - superficie de endpoints abiertos en modulos API sin decorador de autenticacion.
  - mezcla de estilos SQL (MySQL vs SQLite) en partes legacy.

