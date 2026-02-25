# Setup y Operacion Tecnica

## 1. Requisitos base

- Python `3.11` (ver `runtime.txt`).
- MySQL `8.x` accesible desde entorno de ejecucion.
- `pip` y entorno virtual recomendado.

## 2. Dependencias (requirements)

Archivo fuente: `requirements.txt`.

Paquetes clave:

- Web:
  - `Flask==2.3.3`
  - `Werkzeug==2.3.7`
  - `Jinja2==3.1.2`
- DB:
  - `pymysql>=1.0.0` (base principal y compatible serverless)
  - `mysql-connector-python==8.0.33` (usado en algunos blueprints)
  - `cryptography>=41.0.0`
- Procesamiento:
  - `pandas>=2.0.0`
  - `openpyxl>=3.1.0`
  - `xlrd>=2.0.0`
- Deploy/runtime:
  - `gunicorn==21.2.0`
  - `python-dotenv>=1.0.0`

## 3. Variables de entorno

Archivo fuente: `.env.example`.

Variables requeridas:

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MYSQL_USER` (alternativa soportada: `MYSQL_USERNAME`)
- `MYSQL_PASSWORD`
- `SECRET_KEY`

Opcional:

- `TZ` (ejemplo: `America/Mexico_City`)

## 4. Arranque local

## 4.1 Preparacion

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Completar `.env` con credenciales reales.

## 4.2 Ejecucion

```bash
python run.py
```

Verificaciones rapidas:

- `GET /` -> health local (`ok`).
- `GET /inicio` -> hub.
- `GET /ILSAN-ELECTRONICS` -> shell principal MES.

## 5. Arranque serverless (Vercel)

Archivos relevantes:

- `api/index.py`
- `vercel.json`

Puntos importantes:

- Todo trafico se enruta a `api/index.py`.
- Se deben definir variables `MYSQL_*` y `SECRET_KEY` en la configuracion del proyecto.
- Endpoint util de debug en Vercel:
  - `GET /debug/env` (no usar en produccion publica sin restriccion).

## 6. Conectividad MySQL y pooling

## 6.1 Pool principal (`app/config_mysql.py`)

- Pool manual de conexiones reutilizables.
- Parametros destacados:
  - `_MAX_POOL_SIZE = 3`
  - `connect_timeout/read_timeout/write_timeout = 60`
- `execute_query()` aplica conversion basica de SQL SQLite->MySQL para algunos patrones.

## 6.2 Modulos que no usan el pool central

Estos modulos crean conexion directa via `mysql.connector` o `pymysql.connect`, fuera de `config_mysql`:

- `app/smd_inventory_api.py`
- `app/smt_routes_clean.py`
- `app/smt_routes_date_fixed.py`
- `app/aoi_api.py`

Impacto:

- Mayor dispersion de configuracion DB.
- Dificultad para unificar retries, tracing y limites de conexiones.

## 7. Operacion diaria recomendada

Checklist operativo:

1. Validar conectividad MySQL antes de levantar trafico real.
2. Revisar logs de inicializacion por errores de DDL/migracion.
3. Verificar rutas criticas de negocio:
   - BOM (`/listar_modelos_bom`, `/listar_bom`)
   - Material (`/listar_materiales`, `/api/inventario/consultar`)
   - Planeacion (`/api/plan`, `/api/plan-smd/list`)
4. Confirmar sesion y permisos en UI:
   - login
   - acceso a `/ILSAN-ELECTRONICS`
   - endpoints admin bajo `/admin/*`.

## 8. Troubleshooting tecnico

## 8.1 Error de conexion DB

- Revisar `.env`.
- Confirmar firewall/whitelist del host MySQL.
- Probar endpoint de estado que implique query simple (`/api/status` en entorno controlado).

## 8.2 Errores de importacion Excel

- Confirmar `pandas`, `openpyxl`, `xlrd`.
- Revisar formato de columnas esperado por cada endpoint de importacion.

## 8.3 Inicio con errores de codificacion consola (Windows)

Si Python/terminal usa `cp1252`, algunos logs con caracteres no ASCII pueden fallar.

- Mitigacion temporal:
  - `set PYTHONIOENCODING=utf-8`

## 8.4 Diferencias de comportamiento local vs Vercel

- Verificar que en Vercel esten registradas las mismas rutas adicionales que en local (`api/index.py`).
- Confirmar variables de entorno con `/debug/env` solo en debugging controlado.

