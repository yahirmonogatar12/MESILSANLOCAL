# Objetivo del agente

Orquestar de forma autónoma el ciclo **PO → WO** entre dos frontends (Control de Embarque y Plan de Producción) y un backend Flask, garantizando validación, persistencia, estados, idempotencia y retroalimentación visual al usuario.

---

# 1) Suposiciones del entorno

- **Backend**: Flask + SQLAlchemy + (MySQL/MariaDB o SQLite). JSON over HTTP.
- **Frontends**: los HTML provistos (Control de Embarque y Crear plan de producción) con JS vanilla y `fetch`.
- **Auth**: simple (sin token) o Bearer si se habilita; el agente puede incluir cabeceras.
- **Formato de códigos**: `PO-YYMMDD-####` y `WO-YYMMDD-####`.

---

# 2) Modelos de datos (contratos)

## 2.1 Tabla `embarques` (PO)

- `id` INT PK AI
- `codigo_po` VARCHAR(32) **UNIQUE**, **NOT NULL**
- `cliente` VARCHAR(64)
- `fecha_registro` DATE
- `estado` ENUM('PLAN','PREPARACION','EMBARCADO','EN\_TRANSITO','ENTREGADO') DEFAULT 'PLAN'
- `modificado` DATETIME DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP

## 2.2 Tabla `work_orders` (WO)

- `id` INT PK AI
- `codigo_wo` VARCHAR(32) **UNIQUE**, **NOT NULL**
- `codigo_po` VARCHAR(32) **FK** → `embarques.codigo_po` **NOT NULL**
- `modelo` VARCHAR(64)
- `cantidad_planeada` INT **> 0**
- `fecha_operacion` DATE
- `modificador` VARCHAR(64)
- `fecha_modificacion` DATETIME DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP

---

# 3) Endpoints REST (Flask)

## 3.1 `POST /api/embarques`

**Request**

```
{
  "codigo_po": "PO-250807-0001",
  "cliente": "LG_REFRIS",
  "fecha_registro": "2025-08-07",
  "estado": "PLAN"
}
```

**Responses**

- 201 `{ "ok": true, "id": 123 }`
- 409 `{ "ok": false, "code": "DUPLICATE_PO" }`
- 400 `{ "ok": false, "code": "VALIDATION_ERROR", "field": "codigo_po" }`

## 3.2 `GET /api/embarques`

Query params: `estado` (opcional), `codigo_po` (opcional) **Response**

```
[
  {"codigo_po":"PO-250807-0001","cliente":"LG_REFRIS","fecha_registro":"2025-08-07","estado":"PLAN"}
]
```

## 3.3 `POST /api/work_orders`

**Request**

```
{
  "codigo_wo": "WO-250807-0001",
  "codigo_po": "PO-250807-0001",
  "modelo": "NFM961M0032",
  "cantidad_planeada": 60,
  "fecha_operacion": "2025-08-08",
  "modificador": "AGENTE"
}
```

**Responses**

- 201 `{ "ok": true, "id": 987 }`
- 404 `{ "ok": false, "code": "PO_NOT_FOUND" }`
- 409 `{ "ok": false, "code": "DUPLICATE_WO" }`
- 400 `{ "ok": false, "code": "VALIDATION_ERROR", "field": "cantidad_planeada" }`

## 3.4 `GET /api/work_orders`

Query params: `po` (opcional)

## 3.5 (Opcional) Cambios de estado

- `PUT /api/embarques/{codigo_po}/estado` body `{ "estado": "PREPARACION" }`
- `PUT /api/work_orders/{codigo_wo}/estado` body `{ "estado": "PLANIFICADA" }`

---

# 4) Validaciones mínimas (agente + backend)

- `codigo_po`/`codigo_wo`: no vacíos; patrón `/^(PO|WO)-\d{6}-\d{4}$/`
- `fecha_*`: formato `YYYY-MM-DD`
- `cantidad_planeada`: entero > 0
- Antes de crear WO, confirmar existencia de la `codigo_po`

---

# 5) Idempotencia y reintentos

- **Antes de POST**: comprobar existencia con `GET` por código. Si existe, **considerar éxito lógico** y reutilizar.
- **409**: tratar como éxito lógico; recuperar recurso con `GET`.
- **5xx**: reintentos con backoff: 0.2s → 0.5s → 1s (máx 3).
- **Time-out**: abortar acción y notificar con opción de reintentar.

---

# 6) Estados y transiciones

## 6.1 PO

`PLAN` → `PREPARACION` → `EMBARCADO` → `EN_TRANSITO` → `ENTREGADO`

- Prohibir retrocesos; cambios sólo vía endpoint de estado.

## 6.2 WO

`CREADA` → `PLANIFICADA` → `EN_PRODUCCION` → `CERRADA`

---

# 7) Flujos operativos del agente

## 7.1 Crear PO desde Control de Embarque

1. Leer inputs de UI (cliente, fecha, etc.).
2. Generar `codigo_po` único `PO-${YYMMDD}-${secuencia4}`; verificar colisión con `GET /api/embarques?codigo_po=...`.
3. Enviar `POST /api/embarques`.
4. **Si 201**: refrescar tabla llamando `GET /api/embarques` y re-render.
5. **Si 409**: obtener registro con `GET` y mostrarlo como existente.
6. Mostrar notificación (éxito o ya-existente) en UI.

## 7.2 Poblar POs en Plan de Producción

1. `GET /api/embarques?estado=PLAN` (o estados habilitados para producción).
2. Poblar `<select id="poDropdown">` con `codigo_po`.
3. Al cambiar selección, habilitar botón "Registrar WO".

## 7.3 Crear WO vinculada a una PO

1. Leer `codigo_po` seleccionado + `modelo`, `cantidad_planeada`, `fecha_operacion`.
2. Generar `codigo_wo`; confirmar no duplicado con `GET /api/work_orders?codigo_wo=...`.
3. `POST /api/work_orders`.
4. **201**: refrescar grilla de WOs con `GET /api/work_orders?po=...`.
5. **404 PO\_NOT\_FOUND**: recargar POs, pedir selección nuevamente y reintentar.
6. **409**: tratar como éxito lógico y mostrar registro.

---

# 8) Automatización UI (DOM hooks mínimos)

## 8.1 Control de Embarque (Control de Embarque.html)

- Reemplazar `abrirModalRegistro()` por un modal real con formulario PO.
- En submit → `registrarPO(datos)` → `fetch('/api/embarques', {method:'POST', body: JSON.stringify(datos)})`.
- `cargarDatosEmbarques()` debe consumir `GET /api/embarques` y pintar `#tabla-embarques`.
- Actualizar contador `Total Rows` tras render.

## 8.2 Plan de Producción (Crear plan de produccion.html)

- Añadir `<select id="poDropdown"></select>` en la barra.
- `DOMContentLoaded` → `cargarPOsParaWO()` → `GET /api/embarques?estado=PLAN`.
- Botón **Registrar** → abrir modal WO (campos: PO, modelo, cantidad, fecha).
- Submit → `POST /api/work_orders` y refrescar tabla.

---

# 9) Snippets clave (frontend)

```js
async function fetchJSON(url, opts={}) {
  const r = await fetch(url, {headers:{'Content-Type':'application/json'}, ...opts});
  const data = await r.json().catch(()=>({}));
  if (!r.ok) throw Object.assign(new Error(`HTTP ${r.status}`), {status:r.status, data});
  return data;
}

async function registrarPO(datos) {
  try {
    await fetchJSON('/api/embarques', {method:'POST', body: JSON.stringify(datos)});
  } catch(e) {
    if (e.status === 409) {/* éxito lógico: ya existe */}
    else throw e;
  }
  await refrescarPOs();
}

async function crearWO(datos) {
  try {
    await fetchJSON('/api/work_orders', {method:'POST', body: JSON.stringify(datos)});
  } catch(e) {
    if (e.status === 404 && e.data?.code === 'PO_NOT_FOUND') { await cargarPOsParaWO(); return; }
    if (e.status === 409) {/* ya existe: recuperar y mostrar */ return; }
    throw e;
  }
  await refrescarWOs();
}
```

---

# 10) Snippets (Flask/SQLAlchemy)

```python
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:pass@localhost/tu_db'
db = SQLAlchemy(app)

class Embarque(db.Model):
    __tablename__ = 'embarques'
    id = db.Column(db.Integer, primary_key=True)
    codigo_po = db.Column(db.String(32), unique=True, nullable=False)
    cliente = db.Column(db.String(64))
    fecha_registro = db.Column(db.Date)
    estado = db.Column(db.String(16), default='PLAN')
    modificado = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class WorkOrder(db.Model):
    __tablename__ = 'work_orders'
    id = db.Column(db.Integer, primary_key=True)
    codigo_wo = db.Column(db.String(32), unique=True, nullable=False)
    codigo_po = db.Column(db.String(32), db.ForeignKey('embarques.codigo_po'), nullable=False)
    modelo = db.Column(db.String(64))
    cantidad_planeada = db.Column(db.Integer)
    fecha_operacion = db.Column(db.Date)
    modificador = db.Column(db.String(64))
    fecha_modificacion = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

@app.post('/api/embarques')
def crear_po():
    j = request.get_json(force=True)
    try:
        po = Embarque(**j)
        db.session.add(po)
        db.session.commit()
        return jsonify({"ok": True, "id": po.id}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"ok": False, "code": "DUPLICATE_PO"}), 409

@app.get('/api/embarques')
def listar_pos():
    q = Embarque.query
    estado = request.args.get('estado')
    codigo_po = request.args.get('codigo_po')
    if estado: q = q.filter_by(estado=estado)
    if codigo_po: q = q.filter_by(codigo_po=codigo_po)
    return jsonify([
        {
            'codigo_po': e.codigo_po,
            'cliente': e.cliente,
            'fecha_registro': e.fecha_registro.isoformat() if e.fecha_registro else None,
            'estado': e.estado
        } for e in q.all()
    ])

@app.post('/api/work_orders')
def crear_wo():
    j = request.get_json(force=True)
    # validar existencia de la PO
    if not Embarque.query.filter_by(codigo_po=j.get('codigo_po')).first():
        return jsonify({"ok": False, "code": "PO_NOT_FOUND"}), 404
    try:
        wo = WorkOrder(**j)
        db.session.add(wo)
        db.session.commit()
        return jsonify({"ok": True, "id": wo.id}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"ok": False, "code": "DUPLICATE_WO"}), 409

@app.get('/api/work_orders')
def listar_wos():
    q = WorkOrder.query
    po = request.args.get('po')
    if po: q = q.filter_by(codigo_po=po)
    return jsonify([
        {
            'codigo_wo': w.codigo_wo,
            'codigo_po': w.codigo_po,
            'modelo': w.modelo,
            'cantidad_planeada': w.cantidad_planeada,
            'fecha_operacion': w.fecha_operacion.isoformat() if w.fecha_operacion else None
        } for w in q.all()
    ])
```

---

# 11) Telemetría y auditoría

- Log por cada transición de estado.
- Guardar `agent_id`, timestamps, payloads sanitizados.
- Encabezado `X-Request-Id` por acción del agente para rastreo.

---

# 12) Seguridad

- Validar inputs en backend y frontend.
- Limitar CORS a orígenes conocidos.
- Si hay endpoints internos del agente, usar token de servicio.

---

# 13) Pruebas E2E (lista)

- Crear PO nueva → visible en `/api/embarques` y en tabla Embarque.
- Duplicar PO → 409 y UI muestra existente.
- Crear WO con PO válida → 201 y visible en tabla Producción.
- Crear WO con PO inexistente → 404 y el agente recarga POs.
- Filtros por estado de PO y WO.
- Reintentos ante 5xx sin duplicar (idempotencia).

---

# 14) Recuperación y rollback

- Si `POST /api/work_orders` falla después de escribir parcialmente, exponer `DELETE /api/work_orders/{codigo_wo}` y que el agente la invoque.
- Backoff y circuit breaker si persisten 5xx.

---

# 15) Plan de integración incremental

1. Implementar endpoints con validaciones y errores normalizados.
2. Conectar Control de Embarque → creación/consulta de POs.
3. Conectar Plan de Producción → dropdown POs + creación de WOs.
4. Añadir update de estados (PO y WO).
5. Telemetría, seguridad y pruebas E2E.

