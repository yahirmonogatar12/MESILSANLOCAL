# Documentacion Tecnica MES ILSAN (v2)

Este indice centraliza la documentacion tecnica actualizada del sistema MES ILSAN, alineada al estado real del codigo en `MESILSANLOCAL`.

## Alcance

- Arquitectura de ejecucion local y serverless.
- Setup tecnico y operacion.
- Catalogo funcional por dominios con rutas/endpoints clave.
- Modelo de datos MySQL y estrategia de migracion observada.
- Deep dive del modulo BOM (incluyendo `CONTROL_DE_BOM`).
- Hallazgos tecnicos, riesgos y priorizacion de remediacion.

## Mapa del paquete documental

- [MANUAL_TECNICO_COMPLETO.md](./MANUAL_TECNICO_COMPLETO.md) — Manual maestro que consolida la arquitectura, flujos visuales, estructura del repositorio, catálogo de APIs y esquema de base de datos.
- [ANALISIS_MEJORAS_REPO.md](./ANALISIS_MEJORAS_REPO.md) — Diagnóstico detallado de mejoras de seguridad y arquitectura (anteriormente Hallazgos Técnicos y Riesgos).
- [SISTEMA_AUTENTICACION_ROLES.md](./SISTEMA_AUTENTICACION_ROLES.md) — Documentación detallada del control de acceso basado en roles (RBAC).
- [GUIA_DESARROLLO_MODULOS_MES.md](./GUIA_DESARROLLO_MODULOS_MES.md) — Guía y checklist para desarrollo e integración de nuevos módulos.

## Programa activo de refactor backend

El programa activo de refactor backend y su seguimiento por fases vive en:

- [PLAN_REFACTORIZAR_ROUTES.md](./PLAN_REFACTORIZAR_ROUTES.md) — Seguimiento de la migración de routes.py a blueprints.
- [PLAN_REFACTOR_CONTENEDOR_UNICO.md](./PLAN_REFACTOR_CONTENEDOR_UNICO.md) — Plan de refactor estructural para un contenedor universal único.

## Quick start tecnico

1. Instalar dependencias:
   - `pip install -r requirements.txt`
2. Configurar entorno:
   - Copiar `.env.example` a `.env` y completar variables MySQL + `SECRET_KEY`.
3. Arrancar en local:
   - `python run.py`
4. Verificar endpoints basicos:
   - `GET /` (health en `run.py`)
   - `GET /inicio` (hub)
   - `GET /ILSAN-ELECTRONICS` (contenedor principal MES)
5. Si se despliega en Vercel:
   - Confirmar variables en proyecto Vercel.
   - `vercel.json` enruta todo a `api/index.py`.

## Documentos legacy relevantes (vigentes como referencia)

Los siguientes documentos previos no se eliminan. Siguen siendo utiles para contexto historico o decisiones previas:

- [Implementar AJAX.md](./Implementar AJAX.md)
- [INSTRUCCIONES-IMPLEMENTACION-AJAX.md](./INSTRUCCIONES-IMPLEMENTACION-AJAX.md)

## Convenciones usadas en esta documentacion

- Estado de rutas y proteccion basado en analisis estatico de decoradores en:
  - `app/routes.py`
  - `app/api_po_wo.py`
  - `app/aoi_api.py`
  - `app/api_raw_modelos.py`
  - `app/smd_inventory_api.py`
  - `app/smt_routes_clean.py`
  - `app/smt_routes_date_fixed.py`
  - `app/user_admin.py`
  - `app/admin_api.py`
  - `app/py/control_modelos_smt.py`
- Referencias `archivo:linea` apuntan al codigo actual analizado.
- La documentacion describe comportamiento observado, no la intencion historica.
