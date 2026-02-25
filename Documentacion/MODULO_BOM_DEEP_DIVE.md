# Modulo BOM Deep Dive

Analisis end-to-end del modulo BOM centrado en `CONTROL_DE_BOM` y su integracion con el shell principal.

## 1. Archivos involucrados

Frontend:

- `app/templates/INFORMACION BASICA/CONTROL_DE_BOM.html`
- `app/templates/MaterialTemplate.html`
- `app/static/js/scriptMain.js` (flujo BOM legacy adicional)

Backend:

- `app/routes.py`
- `app/db_mysql.py`

## 2. Integracion con contenedor principal

## 2.1 Flujo principal actual (Informacion Basica)

`MaterialTemplate.html`:

1. `window.mostrarControlBOMInfo()` oculta contenedores y prepara area target (`app/templates/MaterialTemplate.html:2320`).
2. Llama `cargarContenidoDinamico('control-bom-info-container', '/informacion_basica/control_de_bom')` (`app/templates/MaterialTemplate.html:2387`).
3. Tras cargar HTML, ejecuta `window.initializeControlBOMEventListeners()` si existe (`app/templates/MaterialTemplate.html:2390`).

Backend:

- `/informacion_basica/control_de_bom` renderiza template BOM con `modelos` precargados (`app/routes.py:4270`).

## 2.2 Flujo legacy paralelo

- `scriptMain.js` mantiene `window.mostrarControlBOM()` y carga `/control-bom-ajax` (`app/static/js/scriptMain.js:2428`).
- Ruta legacy `/control-bom-ajax` intenta usar `mysql.connection` (`app/routes.py:4810`), pero no hay objeto `mysql` definido en `routes.py`.

Implicacion: existen 2 caminos BOM, uno vigente y otro legacy/fragil.

## 3. Flujo frontend dentro de `CONTROL_DE_BOM.html`

## 3.1 Inicializacion y eventos

- Funciones globales + event delegation en `document.body` (`app/templates/INFORMACION BASICA/CONTROL_DE_BOM.html:120`).
- Guarda flag `document.body.dataset.controlBOMListenersAttached` para evitar doble attach.
- Auto-init por script inline al final del fragmento (`.../CONTROL_DE_BOM.html:1735+`).

## 3.2 Consulta BOM

Ruta frontend:

1. Usuario selecciona modelo (`#bomModeloSearch`).
2. `consultarBOMOriginal()` valida modelo y llama `cargarDatosBOMEnTabla(modelo)` (`.../CONTROL_DE_BOM.html:874`).
3. `fetch('/listar_bom', POST)` con `{ modelo, classification? }` (`.../CONTROL_DE_BOM.html:280`).
4. Render tabla + cache local `bomDataCache`.

## 3.3 Importar Excel BOM

Frontend:

- `importarExcelBOM()` toma archivo y hace `fetch('/importar_excel_bom', POST multipart)` (`.../CONTROL_DE_BOM.html:499`, `:586`).

Backend:

- `/importar_excel_bom` lee Excel con `pandas` y delega a `insertar_bom_desde_dataframe` (`app/routes.py:2528`).

DB logic:

- mapeo flexible de columnas por variantes de nombre.
- preprocesa filas y usa `executemany` por lotes (`app/db_mysql.py:1081`, `:1184`).

## 3.4 Exportar Excel BOM

Frontend:

- `exportarExcelBOM()` construye URL con `modelo` y `classification` (`.../CONTROL_DE_BOM.html:432`, `:453`).

Backend:

- `/exportar_excel_bom` genera temporal `.xlsx` y devuelve `send_file` (`app/routes.py:2789`).

## 3.5 Edicion puntual

Frontend:

- Doble click en fila -> `openBOMEditPanel(bomData)` (`.../CONTROL_DE_BOM.html:213`, `:1069`).
- Guardado via `saveBOMEdit()` -> `POST /api/bom/update` (`.../CONTROL_DE_BOM.html:1352`, `:1385`).

Backend:

- `/api/bom/update` arma `UPDATE bom SET ... WHERE codigo_material AND modelo` (`app/routes.py:2831`).

## 3.6 Actualizacion masiva `posicion_assy`

Frontend:

- Modal dinamico `createModalRegistroPosicion()` (`.../CONTROL_DE_BOM.html:1427`).
- `guardarPosicionesAssy()` construye arreglo `cambios` y envia `POST /api/bom/update-posiciones-assy` (`.../CONTROL_DE_BOM.html:1626`, `:1667`).

Backend:

- `/api/bom/update-posiciones-assy` usa una transaccion + `executemany` (`app/routes.py:2912`).
- Actualiza por `(codigo_material, modelo)`.

## 4. Endpoints BOM y contratos funcionales

| Endpoint | Metodo | Payload entrada | Salida |
|---|---|---|---|
| `/listar_modelos_bom` | `GET` | N/A | `[{modelo: "..."}, ...]` |
| `/listar_bom` | `POST` | `{ modelo: "...", classification?: "IMD|SMD|MAIN|TODOS" }` | array filas mapeadas |
| `/importar_excel_bom` | `POST` | `multipart/form-data` (`file`) | `{success,message}` |
| `/exportar_excel_bom` | `GET` | query `modelo`, `classification?` | archivo Excel |
| `/api/bom/update` | `POST` | JSON fila editable | `{success,message}` |
| `/api/bom/update-posiciones-assy` | `POST` | `{cambios:[{codigoMaterial,modelo,posicionAssy}]}` | `{success,actualizados}` |

## 5. Mapeo DB <-> frontend en BOM

`db_mysql.listar_bom_por_modelo()` transforma columnas DB a claves JS (`app/db_mysql.py:1051`):

- `codigo_material` -> `codigoMaterial`
- `numero_parte` -> `numeroParte`
- `tipo_material` -> `tipoMaterial`
- `especificacion_material` -> `especificacionMaterial`
- `cantidad_total` -> `cantidadTotal`
- `cantidad_original` -> `cantidadOriginal`
- `posicion_assy` -> `posicionAssy`

## 6. Limitaciones tecnicas detectadas

## 6.1 Seguridad/acceso

- `/api/bom/update-posiciones-assy` no tiene `@login_requerido` (`app/routes.py:2912`).

## 6.2 Integracion frontend

- En success de guardado masivo, se intenta leer `#modeloDropdown` (`.../CONTROL_DE_BOM.html:1694`), pero el input principal del modulo es `#bomModeloSearch` (`.../CONTROL_DE_BOM.html:11`).
- Existe boton de prueba visible (`TEST CARGAR MODELOS`) inyectado en runtime (`.../CONTROL_DE_BOM.html:909`).

## 6.3 Duplicidad de caminos BOM

- Camino actual: `/informacion_basica/control_de_bom` (estable).
- Camino legacy: `/control-bom-ajax` (dependencia `mysql.connection` no definida).

## 6.4 Mantenibilidad

- Logica BOM distribuida entre:
  - script inline del template BOM
  - loader generico de `MaterialTemplate.html`
  - flujo adicional en `scriptMain.js`

## 7. Mejoras recomendadas (pendientes)

1. Proteger `POST /api/bom/update-posiciones-assy` con `@login_requerido`.
2. Eliminar o desactivar ruta legacy `/control-bom-ajax` y flujo antiguo en `scriptMain.js`.
3. Corregir recarga post-guardado masivo para usar `#bomModeloSearch`.
4. Remover codigo de testing temporal del template BOM.
5. Extraer script inline BOM a JS modular dedicado para reducir duplicidad.

