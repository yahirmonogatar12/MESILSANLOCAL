# ILSAN MES (MESILSANLOCAL)

Sistema MES basado en Flask para gestión de materiales, BOM, inventarios, planeación de producción y módulos SMT, con soporte de impresión local Zebra.

## Documentación Técnica y Manual Maestro

Para ver la documentación completa y detallada del sistema, consulta el **[Manual Técnico Completo](Documentacion/MANUAL_TECNICO_COMPLETO.md)**, el cual incluye:
- Arquitectura general del sistema.
- Flujos de procesos visuales (diagramas Mermaid) para autenticación, control de almacenes, ingeniería BOM/ECO, líneas SMT/SMD y terminales móviles PDA Zebra.
- Detalle de la estructura del repositorio con enlaces clickables.
- Catálogo de APIs y comportamiento de seguridad.
- Esquema de base de datos relacional y catálogo de tablas.

Otros documentos de referencia:
- Índice técnico v2: [README_TECNICO_MES.md](Documentacion/README_TECNICO_MES.md)
- Guía de Desarrollo de Módulos: [GUIA_DESARROLLO_MODULOS_MES.md](Documentacion/GUIA_DESARROLLO_MODULOS_MES.md)
- Hallazgos y Riesgos de Seguridad: [ANALISIS_MEJORAS_REPO.md](Documentacion/ANALISIS_MEJORAS_REPO.md)

## Requisitos

- Python 3.11 (ver `runtime.txt`)
- MySQL 8.x (acceso a instancia con base y usuario)

## Variables de entorno

Crear un archivo `.env` en la raíz de `MESILSANLOCAL/` con:

- MYSQL_HOST=...
- MYSQL_PORT=3306
- MYSQL_DATABASE=...
- MYSQL_USER=...
- MYSQL_PASSWORD=...
- SECRET_KEY=alguna_clave_secreta
- MES_FORCE_STARTUP_INIT=0 (opcional, para evitar inicialización forzada de tablas en cada arranque)

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
   - Este archivo registra todas las rutas/blueprints necesarios y expone el endpoint de health.

La app por defecto inicia en `http://127.0.0.1:5000/` (o 0.0.0.0:5000):
- `/login` — página de inicio de sesión.
- `/inicio` — hub/landing page (después de autenticar) con todas las aplicaciones disponibles.
- `/ILSAN-ELECTRONICS` — módulo MES principal (material, inventarios, BOM, producción).

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
- Entrypoint: `run.py` (server local con waitress).

## Troubleshooting rápido

- Si no conecta a MySQL, revisa las variables de entorno (`MYSQL_*`) en `.env` y el log de arranque (`app.config_mysql` imprime host/puerto/db/user).
- Errores de importación de Excel: asegúrate de tener `pandas`, `openpyxl`, `xlrd` instalados.

## Licencia

Uso interno. Ajusta según políticas de tu organización.
