# Roadmap: ILSAN Multi-App Ecosystem

## Objetivo General

Transformar ILSAN de un sistema MES monolítico a un **hub centralizado de aplicaciones** que integra múltiples departamentos (Quality, Production, IT) bajo una plataforma única con autenticación y control de permisos unificados.

---

## Fase 1: Landing Page Hub ✅ COMPLETADO

**Estado:** ✅ Implementado y documentado

**Entregables:**
- [x] Landing page (`app/templates/landing.html`) con 4 app cards
- [x] Endpoint `/inicio` con filtrado por permisos y roles
- [x] Redirección de login unificada hacia hub
- [x] Documentación en README
- [x] Archivo `.env.example` para setup

**Características implementadas:**
- Navbar con nombre del usuario, avatar, logout
- Grid responsivo de aplicaciones (desktop/móvil)
- Filtrado dinámico por permisos Jinja2
- Badges de estado (NUEVO, PROXIMAMENTE)
- Animaciones fade-in en cascada

**Próximo paso:** Pruebas en ambiente local

---

## Fase 2: Sistema de Control de Defectos (Próximo)

**Descripción:** Módulo para que el departamento de Calidad registre, asigne y resuelva defectos encontrados en productos.

### 2.1 Diseño de Base de Datos

**Tabla: `defectos`**
```sql
CREATE TABLE defectos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    codigo VARCHAR(50) UNIQUE NOT NULL,  -- ej: DEF-001-2024
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    numero_parte VARCHAR(100) FOREIGN KEY referencias material,
    lote VARCHAR(100),
    severidad ENUM('CRITICA', 'ALTA', 'MEDIA', 'BAJA'),
    estado ENUM('ABIERTO', 'EN_PROGRESO', 'RESUELTO', 'CERRADO', 'RECHAZADO'),
    usuario_reporta VARCHAR(100) FOREIGN KEY referencias usuarios_sistema,
    usuario_asignado VARCHAR(100) FOREIGN KEY referencias usuarios_sistema,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion DATETIME,
    observaciones TEXT,
    evidencia_url VARCHAR(255),  -- URL a foto/documento
    root_cause_analysis TEXT,
    acciones_correctivas TEXT,
    INDEX(estado),
    INDEX(severidad),
    INDEX(usuario_asignado),
    INDEX(numero_parte)
);
```

**Tabla: `defectos_historial`** (auditoría)
```sql
CREATE TABLE defectos_historial (
    id INT PRIMARY KEY AUTO_INCREMENT,
    defecto_id INT FOREIGN KEY referencias defectos,
    usuario VARCHAR(100),
    cambio_tipo VARCHAR(50),  -- 'CREACION', 'ASIGNACION', 'ESTADO', 'COMENTARIO'
    valor_anterior VARCHAR(255),
    valor_nuevo VARCHAR(255),
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Backend (API Endpoints)

**Archivo:** `app/defect_api.py` (nuevo blueprint)

**Endpoints principales:**

```python
@defect_bp.route('/api/defectos', methods=['GET'])
def listar_defectos():
    """
    GET /api/defectos?estado=ABIERTO&severidad=ALTA&usuario_asignado=...
    Devuelve lista JSON de defectos con filtros opcionales
    Permisos: requiere 'calidad' en permisos
    """

@defect_bp.route('/api/defectos/<int:defecto_id>', methods=['GET'])
def obtener_defecto(defecto_id):
    """Detalle de un defecto específico + historial"""

@defect_bp.route('/api/defectos', methods=['POST'])
def crear_defecto():
    """
    POST con JSON:
    {
        "titulo": "...",
        "descripcion": "...",
        "numero_parte": "...",
        "lote": "...",
        "severidad": "ALTA"
    }
    Crea defecto con estado inicial ABIERTO
    """

@defect_bp.route('/api/defectos/<int:defecto_id>', methods=['PUT'])
def actualizar_defecto(defecto_id):
    """Actualiza campos del defecto (estado, asignado, observaciones, etc.)"""

@defect_bp.route('/api/defectos/<int:defecto_id>/asignar', methods=['POST'])
def asignar_defecto(defecto_id):
    """Asigna a usuario_asignado, registra en historial"""

@defect_bp.route('/api/defectos/<int:defecto_id>/resolver', methods=['POST'])
def resolver_defecto(defecto_id):
    """
    Marca como RESUELTO con:
    - root_cause_analysis
    - acciones_correctivas
    - observaciones
    """

@defect_bp.route('/api/defectos/<int:defecto_id>/comentario', methods=['POST'])
def agregar_comentario(defecto_id):
    """Agrega comentario/observación, genera entrada en historial"""

@defect_bp.route('/api/defectos/estadisticas', methods=['GET'])
def estadisticas():
    """Dashboard de métricas: total abiertos, por severidad, por usuario, etc."""
```

### 2.3 Frontend (Templates)

**Archivo base:** `app/templates/defect_management.html`

**Vistas necesarias:**

1. **Listado de defectos** (tabla filtrable)
   - Columnas: código, título, severidad (color-coded), estado, usuario_asignado, fecha_creacion
   - Filtros: estado, severidad, usuario_asignado, rango de fechas, número de parte
   - Botones: "Nuevo defecto", "Detalles", "Editar"

2. **Formulario de nuevo defecto** (modal o página separada)
   - Campos: título, descripción, número de parte (autocomplete), lote, severidad
   - Validación cliente-lado (requeridos)
   - Envío vía AJAX a `/api/defectos` (POST)

3. **Detalle de defecto** (modal o página)
   - Información completa del defecto
   - Historial de cambios (tabla chronológica)
   - Panel de asignación (si usuario es admin/calidad_lead)
   - Panel de resolución (si asignado al usuario actual)
   - Botones contextuales (Asignar, Resolver, Cerrar, Rechazar)

4. **Dashboard de estadísticas**
   - Cards de KPIs: Total abiertos, Críticos pendientes, Resueltos hoy, Tasa de cierre
   - Gráfico: defectos por severidad (doughnut)
   - Gráfico: defectos por estado (bar)
   - Top 5 usuarios con más defectos asignados
   - Timeline de defectos recientes

### 2.4 Integración en Landing Page

**Cambios a `landing.html`:**
- Cambiar card "Control de Defectos" de `disabled` a `enabled`
- Actualizar `href` a `/defect-management`
- Cambiar badge de `PROXIMAMENTE` a `NUEVO` (o removerlo)

**Cambios a `routes.py`:**
- Importar blueprint: `from app.defect_api import defect_bp`
- Registrar: `app.register_blueprint(defect_bp)`
- Crear endpoint raíz `/defect-management` que renderiza `defect_management.html`

### 2.5 Permisos

**Requiere:**
- Permiso `'calidad'` para ver card en hub
- Permiso `'calidad_admin'` para asignar defectos a otros
- Permiso `'calidad_jefe'` para cerrar/rechazar defectos

**Agregar en `auth_system.py`:**
```python
# En función que carga permisos del usuario
permisos_calidad = ['calidad', 'calidad_admin', 'calidad_jefe']
```

**Agregar usuarios en BD:**
```sql
INSERT INTO usuario_permisos (usuario_id, permiso) VALUES
  (usuario_calidad_id, 'calidad'),
  (usuario_calidad_admin_id, 'calidad'),
  (usuario_calidad_admin_id, 'calidad_admin');
```

---

## Fase 3: Portal de Tickets IT (Futuro)

**Descripción:** Sistema para que departamentos de IT registren y resuelvan tickets (problemas de infraestructura, requests de usuario, etc.)

### 3.1 Base de Datos

**Tabla: `tickets_it`**
```sql
CREATE TABLE tickets_it (
    id INT PRIMARY KEY AUTO_INCREMENT,
    codigo VARCHAR(50) UNIQUE,  -- TIC-001-2024
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    categoria ENUM('INFRAESTRUCTURA', 'USUARIO_REQUEST', 'BUG', 'OTRO'),
    prioridad ENUM('BAJA', 'NORMAL', 'ALTA', 'CRITICA'),
    estado ENUM('ABIERTO', 'EN_PROGRESO', 'RESUELTO', 'CERRADO'),
    usuario_reporta VARCHAR(100),
    usuario_asignado VARCHAR(100),
    departamento_origen VARCHAR(100),
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion DATETIME,
    sla_target DATETIME,
    resolucion_tecnica TEXT,
    feedback_usuario TEXT,
    tiempo_resolucion_minutos INT,
    INDEX(estado),
    INDEX(prioridad),
    INDEX(usuario_asignado)
);
```

### 3.2 Diferenciales respecto a Defectos

- **SLA tracking:** Mostrar alertas si ticket próximo a vencer SLA
- **Categorización más abierta:** Para requests de usuarios, no solo técnicos
- **Feedback del usuario:** Después de resolver, pedir confirmación
- **Knowledge base link:** Artículos de auto-servicio asociados

### 3.3 Endpoint raíz

```
/tickets → Renderiza app/templates/tickets.html
```

---

## Fase 4: Módulos adicionales (Largo plazo)

Potenciales:
- **Control de Documentos** (normativas, manuales, procedimientos)
- **Gestión de Capacitación** (cursos, registros de asistencia, certificaciones)
- **Portal de Reportes** (reportes ejecutivos, dashboards de KPIs por departamento)
- **Sistema de Evaluaciones** (desempeño del personal, feedback 360)
- **Base de Datos de Proveedores** (contactos, ratings, órdenes de compra)

---

## Guía de Implementación (Checklist)

### Para cada nueva aplicación:

- [ ] **1. Diseñar tablas en BD**
  - Crear schema en MySQL
  - Agregar índices para queries frecuentes
  - Incluir tabla de auditoría si aplica

- [ ] **2. Crear blueprint (API backend)**
  - Crear archivo `app/<module>_api.py`
  - Definir endpoints con decoradores `@login_requerido` y permisos
  - Usar MySQLdb para queries
  - Retornar JSON para APIs internas

- [ ] **3. Crear templates frontend**
  - Plantilla principal: `app/templates/<module>.html`
  - Modales para formularios si aplica
  - Tablas con DataTables para listados
  - Gráficos con Chart.js si aplica

- [ ] **4. Agregar permisos**
  - Definir permisos en `auth_system.py`
  - Insertar filas en `usuario_permisos` para usuarios de prueba

- [ ] **5. Integrar en landing page**
  - Agregar card en `landing.html`
  - Actualizar filtro Jinja2 con permiso requerido
  - Crear endpoint raíz (ej. `/defect-management`)

- [ ] **6. Documentar**
  - Agregar sección en README.md
  - Documentar endpoints en este roadmap
  - Crear guide de usuario si es complejo

- [ ] **7. Testing**
  - Test endpoints con Postman/curl
  - Probar filtros y búsquedas
  - Verificar permisos en diferentes roles
  - Test responsivo en móvil

---

## Stack técnico consolidado

| Área | Tecnología |
|------|-----------|
| Backend | Flask 2.3.3 (Python 3.11) |
| BD Primaria | MySQL 8.x |
| BD Fallback | SQLite (legacy) |
| Autenticación | Custom SHA-256 + sesiones |
| Templates | Jinja2 + Bootstrap 5 |
| Frontend Interactividad | Vanilla JS + jQuery (legacy en algunos módulos) |
| Tablas dinámicas | DataTables.js |
| Gráficos | Chart.js |
| Iconos | Font Awesome 6 |
| Deployment Local | run.py (Flask dev server) |
| Deployment Serverless | Vercel (api/index.py) |

---

## Notas importantes

1. **Permisos:** Siempre verificar permisos en backend, NO confiar solo en frontend.
2. **Auditoría:** Registrar cambios importantes en tabla `_historial` correspondiente.
3. **Validación:** Validar inputs en backend; sanitizar para SQL injection.
4. **CORS:** Si APIs consumidas desde frontend SPA, considerar CORS headers.
5. **Escalabilidad:** Landing page hub soporta N aplicaciones sin cambios en core.
6. **Mantenibilidad:** Usar blueprints separados por módulo para evitar monolito.

---

## Próximas acciones recomendadas

1. **Inmediato:** Probar landing page en ambiente local (run.py)
2. **Corto plazo (1-2 semanas):** Implementar Sistema de Control de Defectos (Fase 2)
3. **Mediano plazo (3-4 semanas):** Portal IT (Fase 3)
4. **Largo plazo:** Evaluar nuevas aplicaciones según feedback usuarios

