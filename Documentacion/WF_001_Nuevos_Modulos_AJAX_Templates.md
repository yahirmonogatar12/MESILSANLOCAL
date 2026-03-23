# WF_001 — Flujo para Agregar Nuevos Templates y Botones al Sidebar

> **Versión:** 1.0  
> **Fecha:** 2026-03-23  
> **Estado:** Documentación inicial / Descubrimiento

---

## 1. Resumen de la Arquitectura Actual

La app utiliza un sistema de **carga dinámica de contenido** donde:

1. **MaterialTemplate.html** es el layout principal (navbar + área de contenido).
2. Los **botones de navegación** en la navbar cargan archivos **LISTA_*.html** dentro del sidebar.
3. Cada **LISTA** contiene un sidebar con elementos `<li>` que cargan templates específicos al área de contenido principal.
4. Un sistema de **permisos granulares** (`data-permiso-*`) controla qué botones ve cada usuario según su rol.

```
┌─────────────────────────────────────────────────────┐
│  MaterialTemplate.html (Layout Principal)           │
│  ┌──────────────┐  ┌─────────────────────────────┐  │
│  │ Navbar       │  │                             │  │
│  │ (8 botones)  │  │   Área de Contenido         │  │
│  └──────┬───────┘  │   (cargado dinámicamente)   │  │
│         │          │                             │  │
│         ▼          │                             │  │
│  ┌──────────────┐  │                             │  │
│  │ Sidebar      │  │                             │  │
│  │ (LISTA_*.html│──│──▶ Templates específicos    │  │
│  │  cargado     │  │                             │  │
│  │  dinámicam.) │  │                             │  │
│  └──────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 2. Componentes Involucrados

### 2.1 Archivos de Listas (Sidebar)

Ubicación: `app/templates/LISTAS/`

| Archivo | Sección de Navbar | Ruta Flask |
|---|---|---|
| `LISTA_INFORMACIONBASICA.html` | Información Básica | `/listas/informacion_basica` |
| `LISTA_DE_MATERIALES.html` | Control de material | `/listas/control_material` |
| `LISTA_CONTROLDEPRODUCCION.html` | Control de producción | `/listas/control_produccion` |
| `LISTA_CONTROL_DE_PROCESO.html` | Control de proceso | `/listas/control_proceso` |
| `LISTA_CONTROL_DE_CALIDAD.html` | Control de calidad | `/listas/control_calidad` |
| `LISTA_DE_CONTROL_DE_RESULTADOS.html` | Control de resultados | `/listas/control_resultados` |
| `LISTA_DE_CONTROL_DE_REPORTE.html` | Control de reporte | `/listas/control_reporte` |
| `LISTA_DE_CONFIGPG.html` | Configuración de programa | `/listas/configuracion_programa` |
| `menu_sidebar.html` | *(sidebar legacy, sin permisos)* | — |

### 2.2 Archivos Clave del Backend

| Archivo | Responsabilidad |
|---|---|
| `app/routes.py` | Rutas Flask para servir listas y templates AJAX |
| `app/auth_system.py` | Sistema de permisos: roles, botones, verificación |
| `app/user_admin.py` | CRUD de permisos, sincronización HTML→BD |

### 2.3 Archivos Clave del Frontend

| Archivo | Responsabilidad |
|---|---|
| `app/templates/MaterialTemplate.html` | Layout principal, `cargarContenidoDinamico()`, nav buttons |
| `app/static/js/permisos-dropdowns.js` | Validación de permisos en frontend (ocultar/mostrar) |

### 2.4 Tablas en MySQL

| Tabla | Contenido |
|---|---|
| `permisos_botones` | `id`, `pagina`, `seccion`, `boton`, `descripcion`, `activo` |
| `rol_permisos_botones` | `rol_id`, `permiso_boton_id` |
| `usuario_roles` | `usuario_id`, `rol_id` |
| `roles` | `id`, `nombre`, `nivel`, `activo` |

---

## 3. Anatomía de un Elemento con Permisos

Cada `<li>` en los archivos LISTA lleva **3 data-attributes** obligatorios:

```html
<li class="sidebar-link" tabindex="0"
    onclick="window.miFuncion()"
    data-permiso-pagina="LISTA_INFORMACIONBASICA"
    data-permiso-seccion="Administración de usuario"
    data-permiso-boton="Administración de menu">
    Administración de menu
</li>
```

| Atributo | Significado | Ejemplo |
|---|---|---|
| `data-permiso-pagina` | Nombre del archivo LISTA (sin extensión) | `LISTA_INFORMACIONBASICA` |
| `data-permiso-seccion` | Grupo/sección del sidebar | `Administración de usuario` |
| `data-permiso-boton` | Identificador único del botón | `Administración de menu` |

---

## 4. Flujo Completo del Sistema de Permisos

```
                    ┌────────────────────────┐
                    │  HTML Templates        │
                    │  (data-permiso-*)      │
                    └──────────┬─────────────┘
                               │
                    ┌──────────▼─────────────┐
                    │  Sincronización         │
                    │  POST /admin/           │
                    │  sincronizar_permisos   │
                    │  _dropdowns             │
                    │  (BeautifulSoup scan)   │
                    └──────────┬─────────────┘
                               │
                    ┌──────────▼─────────────┐
                    │  MySQL                  │
                    │  permisos_botones       │
                    │  rol_permisos_botones   │
                    └──────────┬─────────────┘
                               │
                    ┌──────────▼─────────────┐
                    │  API Backend            │
                    │  GET /admin/obtener_    │
                    │  permisos_usuario_actual│
                    └──────────┬─────────────┘
                               │
                    ┌──────────▼─────────────┐
                    │  Frontend JS            │
                    │  permisos-dropdowns.js  │
                    │  → oculta/muestra       │
                    │    elementos del DOM    │
                    └────────────────────────┘
```

---

## 5. Flujo para Agregar un NUEVO Botón a un LISTA Existente

### Paso 1: Agregar el `<li>` al archivo LISTA

Abrir el archivo LISTA correspondiente y agregar un nuevo `<li>` dentro de la sección `<ul>` apropiada:

```html
<li class="sidebar-link" tabindex="0"
    onclick="window.miNuevaFuncion()"
    data-permiso-pagina="LISTA_INFORMACIONBASICA"
    data-permiso-seccion="Administración de usuario"
    data-permiso-boton="Mi nuevo botón">
    Mi nuevo botón
</li>
```

### Paso 2: Crear la función JS que cargará el contenido

En `MaterialTemplate.html`, agregar la función `window`:

```javascript
window.miNuevaFuncion = function() {
    cargarContenidoDinamico(
        'mi-nuevo-contenido-container',           // ID del container destino
        '/mi_modulo/mi_template',                  // Ruta Flask AJAX
        () => {
            // Callback de inicialización (opcional)
            console.log('Template cargado');
        }
    );
};
```

### Paso 3: Crear la ruta Flask

En `app/routes.py`:

```python
@app.route("/mi_modulo/mi_template")
@login_requerido
def mi_template_ajax():
    """Ruta AJAX para cargar dinámicamente mi template"""
    try:
        return render_template("MI_MODULO/MI_TEMPLATE.html")
    except Exception as e:
        print(f"Error al cargar MI_TEMPLATE: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500
```

### Paso 4: Crear el archivo HTML del template

Crear `app/templates/MI_MODULO/MI_TEMPLATE.html` con el contenido deseado.

### Paso 5: Sincronizar permisos

Ir a la interfaz de administración y ejecutar la **sincronización de permisos de dropdowns**, o llamar:

```
POST /admin/sincronizar_permisos_dropdowns
```

Esto escanea los HTMLs y actualiza la tabla `permisos_botones` automáticamente.

### Paso 6: Asignar permisos al rol

Desde la interfaz de administración de roles, asignar el nuevo permiso de botón a los roles que deban tener acceso.

---

## 6. Flujo para Agregar una NUEVA Sección (LISTA completa)

### Paso 1: Crear el archivo LISTA

Crear `app/templates/LISTAS/LISTA_MI_SECCION.html`:

```html
<div class="app-container">
    <aside class="app-sidebar">
        <ul class="sidebar-menu">
            <li class="sidebar-section">
                <button class="sidebar-dropdown-btn"
                        data-bs-toggle="collapse"
                        data-bs-target="#sidebarMiGrupo"
                        aria-expanded="false">
                    <span class="sidebar-icon"></span>
                    Mi grupo de funciones
                    <span class="sidebar-caret">
                        <i class="bi bi-chevron-down"></i>
                    </span>
                </button>
                <ul class="collapse sidebar-dropdown-list" id="sidebarMiGrupo">
                    <li class="sidebar-link" tabindex="0"
                        onclick="window.miFuncion1()"
                        data-permiso-pagina="LISTA_MI_SECCION"
                        data-permiso-seccion="Mi grupo de funciones"
                        data-permiso-boton="Mi función 1">
                        Mi función 1
                    </li>
                    <!-- Más botones aquí -->
                </ul>
            </li>
        </ul>
    </aside>
    <div class="overlay"></div>
</div>

<script src="{{ url_for('static', filename='js/permisos-dropdowns.js') }}"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        if (typeof PermisosDropdowns !== 'undefined') {
            PermisosDropdowns.inicializar();
        }
    });
</script>
```

### Paso 2: Crear la ruta Flask para la lista

En `app/routes.py`:

```python
@app.route("/listas/mi_seccion")
@login_requerido
def lista_mi_seccion():
    """Cargar dinámicamente la lista de Mi Sección"""
    try:
        return render_template("LISTAS/LISTA_MI_SECCION.html")
    except Exception as e:
        print(f"Error al cargar LISTA_MI_SECCION: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500
```

### Paso 3: Agregar el botón en la navbar de MaterialTemplate.html

Buscar la sección de `navButtons` en `MaterialTemplate.html` y agregar el nuevo botón con su acción correspondiente. Hay **dos lugares** que se deben actualizar:

**A) El HTML del botón de navegación:**  
Agregar un `<button class="nav-button">` en la barra de navegación.

**B) El mapeo de acciones en JavaScript:**  
En la sección `buttonActions` (~línea 1508), agregar:

```javascript
'Mi nueva sección': () => {
    window.mostrarMiSeccion();
    setTimeout(() => {
        cargarContenidoDinamico('mi-seccion-content', '/listas/mi_seccion');
    }, 100);
},
```

### Paso 4: Crear la función `mostrarMiSeccion()` en MaterialTemplate

Seguir el patrón de las funciones existentes como `mostrarInformacionBasica()`:

```javascript
window.mostrarMiSeccion = function() {
    // Ocultar todos los contenedores
    ocultarTodosLosContenedores();
    // Mostrar el contenedor de mi sección
    const container = document.getElementById('mi-seccion-content-area');
    if (container) {
        container.style.display = 'block';
    }
    // Cargar la lista del sidebar
    cargarContenidoDinamico('mi-seccion-content', '/listas/mi_seccion');
};
```

### Paso 5: Agregar el content-area en el HTML de MaterialTemplate

Agregar un nuevo div contenedor donde se renderizará el contenido:

```html
<div id="mi-seccion-content-area" style="display: none;">
    <div id="mi-seccion-content"></div>
</div>
```

### Paso 6: Actualizar el menú móvil (opcional pero recomendado)

En la función `loadListContent()` (~línea 1236), agregar un nuevo case al switch:

```javascript
case 'mi-seccion':
    listUrl = '/templates/LISTAS/LISTA_MI_SECCION.html';
    title = 'Mi Sección';
    break;
```

Y en `detectActiveSection()` (~línea 1199), agregar:

```javascript
{ id: 'mi-seccion-content-area', section: 'mi-seccion' },
```

### Paso 7: Sincronizar permisos y asignar roles (igual que sección 5)

---

## 7. Checklist Rápido

### Para un nuevo **botón** en lista existente:
- [ ] Agregar `<li>` con `data-permiso-*` al archivo LISTA
- [ ] Crear función `window.miNuevaFuncion()` en MaterialTemplate.html
- [ ] Crear ruta Flask en `routes.py`
- [ ] Crear template HTML del contenido
- [ ] Sincronizar permisos (POST `/admin/sincronizar_permisos_dropdowns`)
- [ ] Asignar permiso al rol correspondiente

### Para una nueva **sección completa**:
- [ ] Crear `LISTA_MI_SECCION.html` en `app/templates/LISTAS/`
- [ ] Crear ruta Flask `/listas/mi_seccion` en `routes.py`
- [ ] Agregar botón de navegación en MaterialTemplate.html
- [ ] Crear función `mostrarMiSeccion()` en MaterialTemplate.html
- [ ] Agregar content-area div en MaterialTemplate.html
- [ ] Agregar mapeo en `buttonActions` para móvil
- [ ] Actualizar `detectActiveSection()` y `loadListContent()` para móvil
- [ ] Crear los templates de contenido individual
- [ ] Crear las rutas Flask para cada template
- [ ] Sincronizar permisos
- [ ] Asignar permisos a roles

---

## 8. Notas y Observaciones

### Comportamiento del Superadmin
El rol `superadmin` **siempre** tiene acceso a todos los botones. El JS de permisos hace skip completo si `rolUsuario === 'superadmin'`.

### Cache de Permisos
- **Frontend:** LocalStorage con TTL de 5 minutos + auto-refresh.
- **Backend:** Cache en memoria Python con TTL configurable (`_BUTTON_PERMISSIONS_CACHE_TTL`).
- **Invalidación:** `auth_system.invalidar_cache_permisos_botones(username)`.

### menu_sidebar.html
Es un archivo legacy que **NO** tiene `data-permiso-*` y **NO** está cubierto por el sistema de permisos. No se usa como referencia para nuevos desarrollos.

### Sincronización automática
`sincronizar_permisos_dropdowns` excluye `menu_sidebar.html` del escaneo. Cualquier nuevo archivo `LISTA_*.html` será incluido automáticamente.

---

## 9. Puntos Pendientes de Investigar

- [ ] ¿Cómo se manejan los permisos por defecto para nuevos roles? (`_crear_permisos_botones_default` en `auth_system.py`)
- [ ] ¿Existe un mecanismo de migración automática al agregar nuevos permisos?
- [ ] ¿Cómo funcionan los templates de contenido internos (ej: `INFORMACION BASICA/CONTROL_DE_MATERIAL.html`)? → Patrón de carpetas
- [ ] Documentar las funciones de cleanup (`cleanupControlAlmacen`, etc.) para cada módulo
