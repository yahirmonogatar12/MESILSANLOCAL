# Historial Cambios Parametros ICT - Backend

> Version: 3.0  
> Fecha: 2026-05-07  
> Template documentado: `app/templates/Control de resultados/historial_cambios_parametros_ict_ajax.html`  
> JS asociado: `app/static/js/historial_cambios_parametros_ict.js`  
> Backend principal: `app/routes.py`

---

## Resumen

El modulo **Historial Cambios Parametros ICT** detecta cambios entre **pares consecutivos** de archivos `.lgd` ordenados por hora dentro de cada combinacion `(linea, ict, no_parte)`. Cada flip distinto se emite como una fila independiente: si un parametro va `0 → 5 → 0` durante el dia se generan dos filas (una por cada transicion) cada una con su hora exacta.

Flujo:

1. Consulta `history_ict` por la jornada para obtener todos los archivos `.lgd`.
2. Agrupa por `(linea, ict, no_parte)` y ordena cronologicamente.
3. Deduplica archivos consecutivos identicos en el mismo grupo (paranoia defensiva).
4. Parsea cada `.lgd` distinto **una sola vez** en paralelo (8 workers).
5. Compara pares consecutivos `(items[i], items[i+1])` y emite un evento por cada parametro que cambio.
6. La UI muestra cada flip como una fila clickeable; al click abre un modal con archivo, hora y barcode/PCB del flip — **sin llamar al backend**: los datos ya vienen en el row.

Todos los endpoints estan protegidos con `@login_requerido`.

---

## Archivos Involucrados

| Archivo | Responsabilidad |
|---|---|
| `app/templates/Control de resultados/historial_cambios_parametros_ict_ajax.html` | Estructura visual, filtros, tabla, modal de detalle. |
| `app/static/js/historial_cambios_parametros_ict.js` | Lee filtros, llama APIs, pollea progreso, renderiza filas, abre modal. |
| `app/routes.py` | Rutas Flask, query a MySQL, calculo de cambios, exportacion Excel. |
| `app/services/ict_lgd_parser.py` | Resuelve y parsea archivos `.lgd`. |
| `script_ict.py` | Proceso externo que alimenta `history_ict`. |

---

## Rutas del Modulo

### 1. Vista AJAX

```python
@app.route("/historial-cambios-parametros-ict-ajax")
```

Renderiza el HTML del modulo.

### 2. API de datos (pares consecutivos)

```http
GET /api/ict/param-changes
```

Devuelve los cambios calculados como JSON. Cada flip es una fila.

### 3. API de progreso

```http
GET /api/ict/param-changes/progress?id=<progress_id>
```

Devuelve el avance de la consulta principal.

### 4. API de detalle on-demand (busqueda binaria, opcional)

```http
GET /api/ict/param-changes/detail
```

Endpoint conservado pero **el JS actual no lo usa**: el modal pinta los datos del flip directamente desde la fila (`archivo_cambio`, `barcode_cambio`, `hora_cambio`). Sigue disponible para uso por otras herramientas o debug.

### 5. Exportacion Excel

```http
GET /api/ict/param-changes/export
```

Mismo calculo que la API de datos pero genera un `.xlsx` con `limit=5000`.

---

## Parametros Recibidos - API Principal

| Parametro HTTP | Uso backend | Notas |
|---|---|---|
| `fecha` | Fecha simple | Fallback si no llegan `fecha_desde` y `fecha_hasta`. |
| `fecha_desde` | Inicio de jornada | Requerido. Formato `YYYY-MM-DD`. |
| `fecha_hasta` | Fin de jornada | Si falta, usa `fecha_desde`. |
| `hora_desde` | Filtro horario opcional | Formato `HH:MM` o `HH:MM:SS`. |
| `hora_hasta` | Filtro horario opcional | Soporta rangos cruzando medianoche. |
| `ict` | ICT especifica | Acepta texto como `ICT1 M1` o numero. |
| `ict_all` | Todas las ICT | Si vale `1`, no exige ICT especifica. |
| `no_parte`, `numero_parte`, `std` | Filtro por numero de parte | Usa prefijo: `no_parte LIKE '<valor>%'`. |
| `componente` | Filtro post-deteccion | Comparacion parcial sobre la etiqueta `"comp / pin"`. |
| `parametro` | Filtro post-deteccion | Comparacion parcial sobre el label del campo. |
| `progress_id` | ID de progreso | Generado por el JS. |

---

## Concepto de Jornada

Inicio a las **07:30:00**. Para una fecha `2026-05-07`, el rango consultado es:

```text
2026-05-07 07:30:00 <= ts < 2026-05-08 07:30:00
```

Si un registro tiene hora menor a `07:30`, se etiqueta como jornada del dia anterior.

---

## Algoritmo (pares consecutivos)

```
groups_raw = {}                         # (linea, ict, no_parte) -> [{ts, file, barcode}]
for source_row in source_rows:
    if not _ict_param_time_allowed(...): continue
    if not source_file: continue
    groups_raw[gkey].append(...)

plan = {}                               # gkey -> [items distintos consecutivos]
for gkey, items in groups_raw.items():
    items.sort(by ts)
    deduped = []
    for it in items:
        if deduped and deduped[-1].file == it.file: continue
        deduped.append(it)
    if len(deduped) >= 2:
        plan[gkey] = deduped

unique_files = union(plan)              # cada .lgd se parsea UNA sola vez
parse en paralelo (max 8 workers)

for gkey, items in plan.items():
    for previous, current in zip(items, items[1:]):
        diff snapshot[previous.file] vs snapshot[current.file]
        por cada (componente, pinref) compartido y campo en _ICT_PARAM_CHANGE_FIELDS:
            if compare_token(prev) != compare_token(curr):
                emitir fila con hora_anterior, hora_cambio,
                archivo_anterior, archivo_cambio,
                barcode_anterior, barcode_cambio
```

**Por que no se pierde el caso `0 → 5 → 0`**: el bucle compara `(A,B)` y luego `(B,C)`. Si `A.STD = 0`, `B.STD = 5`, `C.STD = 0`, el primer par produce fila `0→5` y el segundo produce fila `5→0`. La cronologia completa queda visible.

**Velocidad**: cada `.lgd` se parsea **una sola vez** (`unique_files` deduplica entre grupos). El cache global del parser (64 archivos) reutiliza entre requests sucesivos. En jornadas tipicas (5-20 archivos por grupo) el parseo es rapido.

---

## Parametros Comparados

| Campo interno | Etiqueta |
|---|---|
| `std_value` | `STD` |
| `std_unit` | `UNIT (STD)` |
| `hlim_pct` | `HLIM %` |
| `llim_pct` | `LLIM %` |
| `hp_value` | `HP` |
| `lp_value` | `LP` |
| `ws_value` | `WS` |
| `ds_value` | `DS` |
| `rc_value` | `RC` |
| `p_flag` | `P` |
| `j_flag` | `J` |

Snapshot indexado por `(componente, pinref)`. Solo se comparan claves compartidas por ambos snapshots del par.

Comparacion de valores (`_ict_param_compare_token`):

- Vacios → `("empty", "")`
- Numeros → `("num", Decimal.normalize)` — `1.0`, `1.00` y `1` son equivalentes.
- Texto → `("text", upper)` — case-insensitive.

---

## Respuesta JSON - API Principal

```json
{
  "rows": [
    {
      "jornada": "2026-05-07",
      "hora_anterior": "10:25:00",
      "hora_cambio":   "11:14:33",
      "ict": "M1 ICT1",
      "ict_num": 1,
      "linea": "M1",
      "no_parte": "EBR30299369",
      "std": "EBR30299369",
      "componente": "R101 / 1",
      "componente_raw": "R101",
      "pinref": "1",
      "parametro": "STD",
      "field_key": "std_value",
      "valor_anterior": "1000",
      "valor_nuevo":    "1200",
      "archivo_anterior": "20260507\\archivo_007.lgd",
      "archivo_cambio":   "20260507\\archivo_008.lgd",
      "barcode_anterior": "EBR302993690012",
      "barcode_cambio":   "EBR302993690013"
    }
  ],
  "warnings": [],
  "meta": {
    "archivos_consultados": 120,
    "grupos_total": 12,
    "grupos_con_cambios": 7,
    "archivos_unicos": 78,
    "archivos_leidos": 78,
    "archivos_faltantes": 0,
    "eventos": 14,
    "limite": 1000,
    "jornada_inicio": "2026-05-07 07:30:00",
    "jornada_fin": "2026-05-08 07:30:00"
  }
}
```

Limites:

- API de datos: `limit=1000`.
- Exportacion Excel: `limit=5000`.

---

## Progreso de Consulta

Sistema en memoria con lock + TTL 120s. Fases:

| Fase backend | Texto frontend |
|---|---|
| `iniciando` | Iniciando |
| `consultando_db` | Consultando base de datos |
| `parseando_archivos` | Comparando datos (total = `archivos_unicos`) |
| `detectando_cambios` | Detectando cambios |
| `completado` | Completado |

---

## Exportacion Excel

Hoja: `Cambios Parametros ICT`. Columnas:

1. Jornada
2. Hora Anterior
3. Hora Cambio
4. ICT
5. Linea
6. No Parte
7. Componente
8. Parametro
9. Valor Anterior
10. Valor Nuevo
11. Archivo Anterior
12. Archivo Cambio

Nombre del archivo: `cambios_parametros_ict_YYYYMMDD_HHMMSS.xlsx`.

---

## Manejo de Errores y Advertencias

Errores HTTP 400 (validacion):

- Fecha faltante o invalida.
- `fecha_hasta` < `fecha_desde`.
- ICT faltante (sin `ict_all=1`) o invalida.
- Hora invalida.

Errores HTTP 500: traceback en el JSON.

Warnings (no detienen la consulta):

- Registro sin `fuente_archivo`.
- Archivo `.lgd` inexistente o no legible.
- Sin parametros para el barcode.
- Resultado truncado por `limite`.

---

## Frontend - Relacion con Backend

Tabla (11 columnas):

```
# | Jornada | Hora Anterior | Hora Cambio | ICT | No Parte | Componente |
Parametro | Valor Anterior | Valor Nuevo | Detalle
```

Cada `<tr>` lleva atributos `data-*` con todo lo necesario para el modal:

- `data-jornada`, `data-linea`, `data-ict`, `data-noparte`
- `data-componente`, `data-componente-raw`, `data-pinref`
- `data-parametro`, `data-field`
- `data-valor-anterior`, `data-valor-nuevo`
- `data-hora-anterior`, `data-hora-cambio`
- `data-archivo-anterior`, `data-archivo-cambio`
- `data-barcode-anterior`, `data-barcode-cambio`

Click en cualquier fila → modal `cp-modal-detalle` que muestra **inmediatamente** archivo, hora y barcode/PCB del flip (anterior y del cambio). **No hace fetch** — toda la informacion del flip ya viene en la respuesta principal de `/api/ict/param-changes`.

---

## Puntos de Cuidado

- El modulo depende de que `history_ict.fuente_archivo` apunte a un `.lgd` relativo valido bajo `ICT_ODATA_BASE_DIR`.
- **Cruce de jornada**: un cambio entre el ultimo `.lgd` de la jornada anterior y el primero de la actual no se detecta. La jornada es 07:30 → 07:30.
- **Pines no compartidos**: si un par consecutivo cambia los pines presentes (uno se agrega o se elimina), esas diferencias no se reportan (solo se comparan `(componente, pinref)` presentes en ambos snapshots).
- **Cambios `0 → 5 → 0`**: emiten dos filas separadas (`0→5` y `5→0`), cada una con su hora exacta. Esto era una limitacion del modo primer-vs-ultimo y se corrigio en v3.0.
- **`MIN(barcode)`** sigue siendo representativo: si el archivo trae multiples barcodes con parametros distintos, solo se lee uno.
- **Cache del parser**: 64 archivos (en `app/services/ict_lgd_parser.py`).
- **Jornadas con muchos archivos por grupo**: cada `.lgd` distinto se parsea una sola vez. Para 100+ archivos por grupo el coste sigue siendo lineal en `archivos_unicos`, no cuadratico.
- **Progreso**: vive en memoria del proceso. En multi-worker el polling debe caer en el mismo worker.
