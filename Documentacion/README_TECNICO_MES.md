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

- [ARQUITECTURA_SISTEMA_MES.md](./ARQUITECTURA_SISTEMA_MES.md)
- [SETUP_Y_OPERACION_TECNICA.md](./SETUP_Y_OPERACION_TECNICA.md)
- [CATALOGO_MODULOS_Y_RUTAS.md](./CATALOGO_MODULOS_Y_RUTAS.md)
- [MODELO_DE_DATOS_MYSQL.md](./MODELO_DE_DATOS_MYSQL.md)
- [MODULO_BOM_DEEP_DIVE.md](./MODULO_BOM_DEEP_DIVE.md)
- [HALLAZGOS_TECNICOS_Y_RIESGOS.md](./HALLAZGOS_TECNICOS_Y_RIESGOS.md)
- [REFACTOR_BACKEND/README.md](./REFACTOR_BACKEND/README.md)

## Programa activo de refactor backend

El programa activo de refactor backend y su seguimiento por fases vive en:

- [REFACTOR_BACKEND/README.md](./REFACTOR_BACKEND/README.md)

Ese paquete contiene:

- tablero global de avance
- fases del refactor con estado real observado
- decisiones y supuestos cerrados
- bitacora de continuidad entre sesiones

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

- [DOCUMENTACION_API_RUTAS_SISTEMA.md](./DOCUMENTACION_API_RUTAS_SISTEMA.md)
- [GUIA_DESARROLLO_MODULOS_MES.md](./GUIA_DESARROLLO_MODULOS_MES.md)
- [IMPLEMENTACION_CONTROL_MODELOS_AJAX.md](./IMPLEMENTACION_CONTROL_MODELOS_AJAX.md)
- [PROMPT_CONTROL_BOM_AJAX_IMPLEMENTACION.md](./PROMPT_CONTROL_BOM_AJAX_IMPLEMENTACION.md)
- [Implementar AJAX.md](./Implementar AJAX.md)

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
