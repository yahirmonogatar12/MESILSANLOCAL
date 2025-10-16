# ILSAN MES (MESILSANLOCAL)

Sistema MES basado en Flask para gestión de materiales, BOM, inventarios, planeación de producción y módulos SMT, con soporte de impresión local Zebra.

## Requisitos

- Python 3.11 (ver `runtime.txt`)
- MySQL 8.x (acceso a instancia con base y usuario)
- Windows (opcional) para el servicio local de impresión Zebra

## Variables de entorno

Crear un archivo `.env` en la raíz de `MESILSANLOCAL/` con:

- MYSQL_HOST=...
- MYSQL_PORT=3306
- MYSQL_DATABASE=...
- MYSQL_USER=...
- MYSQL_PASSWORD=...
- SECRET_KEY=alguna_clave_secreta

Notas:
- También se acepta `MYSQL_USERNAME` como alternativa a `MYSQL_USER`.
- En entornos serverless (Vercel) las variables se inyectan vía configuración del proveedor.

## Instalación

1) Crear y activar un entorno virtual (opcional pero recomendado).
2) Instalar dependencias:
   - Repositorio: `MESILSANLOCAL/requirements.txt`

## Ejecutar en local

1. **Configurar variables de entorno:**
   - Copia `.env.example` a `.env` en la carpeta `MESILSANLOCAL`.
   - Completa los valores de MySQL y `SECRET_KEY`.

2. **Método recomendado (runner local):**
   - Ejecuta `run.py` en la carpeta `MESILSANLOCAL`.
   - Este archivo registra todas las rutas/blueprints necesarios y expone endpoints de health/debug.

3. **Entrypoint alternativo (Vercel):**
   - `api/index.py` expone la app para despliegue serverless.

La app por defecto inicia en `http://127.0.0.1:5000/` (o 0.0.0.0:5000):
- `/login` — página de inicio de sesión.
- `/inicio` — hub/landing page (después de autenticar) con todas las aplicaciones disponibles.
- `/ILSAN-ELECTRONICS` — módulo MES principal (material, inventarios, BOM, producción).

## Servicio de Impresión Zebra (opcional)

Carpeta: `ZebraPrintService/`.

Hay dos enfoques:

- Servicio integrado (Windows Service que levanta Flask): `zebra_flask_integrado.py`
  - Expone:
    - `GET /` (status)
    - `POST /print` (ZPL en JSON: `{ "zpl_content": "^XA...^XZ" }`)
    - `GET /printers` (lista impresoras)
  - Puerto por defecto: 5003.

- Servicio Windows que gestiona un proceso Flask externo: `print_service_windows.py`
  - Controla `print_service.py` y mantiene el servicio en ejecución.

Scripts .bat para instalar/desinstalar el servicio:
- `instalar_servicio.bat`, `desinstalar_servicio.bat`, `start_service_auto.bat`, etc.

Asegúrate de tener instalados los paquetes necesarios en Windows:
- `flask`, `flask-cors`, `pywin32`

## Hub de aplicaciones (Landing Page)

Después de autenticarse, todos los usuarios son redirigidos a `/inicio`, un hub centralizado que muestra las aplicaciones disponibles según su rol y permisos.

**Ubicación:**
- Endpoint: `/inicio` en `app/routes.py` (línea ~300)
- Template: `app/templates/landing.html`

**Características:**
- **Filtrado por permisos**: Cada app card se muestra solo si el usuario tiene el permiso correspondiente.
  - Material Management: requiere permiso `'material'`
  - Control de Defectos: requiere permiso `'calidad'`
  - Portal IT: requiere permiso `'admin'`
  - Admin Panel: requiere permiso `'admin'`
  
- **Diseño responsivo**: Cards en grid auto-fit para desktop, stack vertical en móvil.
- **Animaciones**: Fade-in en cascada (0.1s-0.4s) para cada card.
- **Badges**: "NUEVO" para recién agregadas, "PROXIMAMENTE" para en desarrollo.
- **Navbar personalizada**: Muestra nombre del usuario, ícono de avatar, botón logout.

**Apps disponibles en el hub:**
1. **Material Management** → enlace a `/ILSAN-ELECTRONICS`
2. **Control de Defectos** → enlace a `/defect-management` (en desarrollo)
3. **Portal IT** → enlace a `/tickets` (en desarrollo)
4. **Admin Panel** → enlace a `/admin/panel`

**Cómo agregar una nueva aplicación al hub:**

1. Crear la blueprint o módulo (ej. `app/defect_api.py`)
2. Crear endpoint raíz (ej. `/defect-management`)
3. Agregar permiso en `auth_system.py` si es necesario (ej. `'calidad'`)
4. Agregar usuario-permiso en BD si aplica
5. Actualizar `landing.html` con un nuevo card (copiar estructura de un card existente y cambiar icono/enlace)
6. Actualizar endpoint `/inicio` en `routes.py` para incluir la app en el contexto (opcional, si necesita datos dinámicos)

**Flujo de autenticación actualizado:**
```
/login → POST (valida credenciales) → /inicio (hub) → [MES|Defects|IT|Admin] → Módulo específico
```

## Mapa de módulos y endpoints principales

Los endpoints clave viven principalmente en `app/routes.py` y blueprints adicionales.

### Autenticación y sesión
- `GET /login` (render login)
- `POST /login` (autenticación)
- `GET /logout` (cierre de sesión)
- `GET /` → redirige a `/login` (en rutas) o devuelve health JSON (en run)

### Materiales e inventario
- `POST /guardar_material` — alta/actualización de materiales
- `GET /listar_materiales` — listado formateado para frontend
- `POST /api/inventario/lotes_detalle` — detalle de lotes por número de parte (MySQL)
- `POST /importar_excel` — importación de catálogo de materiales desde Excel
- `POST /actualizar_campo_material` — actualización puntual (p.ej. prohibidoSacar)
- `POST /actualizar_material_completo` — actualización completa por código original

### BOM (Bill of Materials)
- `POST /importar_excel_bom` — importación de BOM desde Excel
- `GET /listar_modelos_bom` — modelos únicos
- `POST /listar_bom` — listar por modelo o todos
- `GET /consultar_bom` — filtros GET por modelo/número de parte
- `GET /exportar_excel_bom` — exportación a Excel

### Planeación de producción (plan_main)
- `GET /api/plan` — listar planes (filtros start/end)
- `POST /api/plan` — crear plan
- `POST /api/plan/update` — actualizar campos del plan
- `POST /api/plan/status` — cambiar estado (PLAN/EN PROGRESO/PAUSADO/TERMINADO/CANCELADO)
- `POST /api/plan/save-sequences` — guardar secuencias/grupos
- `GET /api/plan/pending` — planes con pendiente > 0
- `POST /api/plan/reschedule` — reprogramar por lote
- `POST /api/plan/export-excel` — exportar vista de plan
- `GET /api/plan-main/list` — lista condensada para UI

### Integración RAW/PO/WO
- `GET /api/raw/search` — completa CT/UPH/model/project desde tabla `raw`
- `POST /api/work-orders/import` — importa WOs existentes a `plan_main`

### SMT CSV Historial (Blueprint smt_api)
- `GET /api/smt/historial/data` — consulta con filtros
- `GET /api/smt/historial/export` — exportación
- `POST /api/smt/historial/upload` — subir CSV
- `GET /api/smt/folders` — carpetas/líneas disponibles
- `GET /api/smt/stats` — estadísticas

## Arquitectura (resumen)

- Flask app principal en `app/routes.py` (crea `app` y registra módulos).
- Autenticación/permisos en `app/auth_system.py` (roles, permisos por botón, auditoría).
- Capa de datos MySQL en `app/config_mysql.py` (con `execute_query`) y `app/db_mysql.py` (inicialización de tablas y lógica de negocio para materiales/inventario/BOM/plan).
- Entrypoints:
  - Local: `run.py`
  - Serverless: `api/index.py` (ver `vercel.json`)

## Troubleshooting rápido

- Si no conecta a MySQL, verifica variables de entorno con `GET /debug/env` (solo en `api/index.py`).
- Errores de importación de Excel: asegúrate de tener `pandas`, `openpyxl`, `xlrd` instalados.
- Impresión Zebra: valida que Windows detecte la impresora y que el servicio exponga `GET /printers` con el nombre correcto.

## Licencia

Uso interno. Ajusta según políticas de tu organización.
