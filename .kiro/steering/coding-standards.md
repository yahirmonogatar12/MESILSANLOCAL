# Coding Standards

## Python Code Style

### General Guidelines

- Follow PEP 8 style guide (loosely)
- Use 4 spaces for indentation
- Maximum line length: flexible (no strict limit)
- Use descriptive variable names in Spanish or English

### Naming Conventions

#### Variables and Functions

```python
# Snake case for variables and functions
numero_parte = "ABC123"
cantidad_actual = 100

def obtener_materiales():
    pass

def guardar_material(data):
    pass
```

#### Classes

```python
# PascalCase for classes
class AuthSystem:
    pass

class MaterialManager:
    pass
```

#### Constants

```python
# Uppercase for constants
MYSQL_CONFIG = {...}
MAX_INTENTOS = 3
TIMEOUT_SECONDS = 60
```

### Function Documentation

```python
def guardar_material(data, usuario_registro=None):
    """
    Guardar material en la base de datos

    Args:
        data (dict): Datos del material
        usuario_registro (str, optional): Usuario que registra

    Returns:
        bool: True si se guardó exitosamente

    Raises:
        ValueError: Si faltan campos requeridos
    """
    pass
```

### Error Handling

```python
# Always use try-except for database operations
try:
    result = execute_query(query, params)
    return result
except Exception as e:
    print(f"❌ Error en operación: {e}")
    return None
```

### Logging

```python
# Use emoji prefixes for visibility
print("✅ Operación exitosa")
print("❌ Error crítico")
print("⚠️ Advertencia")
print("🔍 Debug info")
print("📦 Cargando datos")
print("💾 Guardando")
```

## JavaScript Code Style

### General Guidelines

- Use modern ES6+ syntax
- Prefer `const` and `let` over `var`
- Use arrow functions for callbacks
- Use template literals for strings

### Naming Conventions

#### Variables and Functions

```javascript
// camelCase for variables and functions
let miVariable = "valor";
const datosUsuario = {};

function cargarDatos() {}
async function guardarMaterial() {}
```

#### Constants

```javascript
// UPPER_CASE for constants
const API_BASE_URL = "/api";
const MAX_RETRIES = 3;
```

#### Event Handlers

```javascript
// Prefix with 'handle' or 'on'
function handleButtonClick(e) {}
function onDataLoaded(data) {}
```

### Async/Await Pattern

```javascript
// Prefer async/await over promises
async function loadData() {
  try {
    const response = await axios.get("/api/data");
    return response.data;
  } catch (error) {
    console.error("❌ Error:", error);
    return null;
  }
}
```

### Event Delegation

```javascript
// Always use event delegation for dynamic content
function initializeEventListeners() {
  if (document.body.dataset.listenersAttached) return;

  document.body.addEventListener("click", function (e) {
    if (e.target.id === "my-button") {
      handleButtonClick(e);
    }
  });

  document.body.dataset.listenersAttached = "true";
}
```

### Function Exposure

```javascript
// Always expose critical functions globally
function myFunction() {
  // Implementation
}

// Expose
window.myFunction = myFunction;
```

### Comments

```javascript
// Single line comments for brief explanations

/**
 * Multi-line comments for function documentation
 * @param {string} id - The item ID
 * @returns {Object} The item data
 */
function getItem(id) {}
```

## HTML/Jinja2 Templates

### Structure

```html
<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <title>{{ title }}</title>
    <link
      rel="stylesheet"
      href="{{ url_for('static', filename='css/styles.css') }}"
    />
  </head>
  <body id="module-container">
    <!-- Content -->

    <script
      src="{{ url_for('static', filename='js/module.js') }}"
      defer
    ></script>
    <script>
      // Inline initialization
    </script>
  </body>
</html>
```

### Naming Conventions

```html
<!-- IDs: module-element-action -->
<button id="plan-btn-guardar">Guardar</button>
<div id="smt-table-container"></div>

<!-- Classes: module-element -->
<div class="plan-row">
  <span class="smt-status"></span>
</div>
```

### Jinja2 Filters

```html
<!-- Check permissions -->
{% if usuario|tiene_permiso_boton('Crear material') %}
<button>Crear</button>
{% endif %}

<!-- Format dates -->
{{ fecha|strftime('%Y-%m-%d') }}

<!-- Safe HTML -->
{{ contenido|safe }}
```

## SQL Queries

### Formatting

```python
# Multi-line for readability
query = """
    SELECT u.*, r.nombre as rol_nombre
    FROM usuarios_sistema u
    LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
    LEFT JOIN roles r ON ur.rol_id = r.id
    WHERE u.username = %s
    ORDER BY u.fecha_creacion DESC
"""
```

### Parameterization

```python
# Always use parameterized queries
query = "SELECT * FROM materiales WHERE numero_parte = %s"
result = execute_query(query, (numero_parte,), fetch='one')

# Never use string formatting
# BAD: query = f"SELECT * FROM materiales WHERE numero_parte = '{numero_parte}'"
```

### Table and Column Names

```sql
-- Use descriptive names in Spanish
CREATE TABLE materiales (
    numero_parte VARCHAR(512),
    descripcion TEXT,
    fecha_registro DATETIME
)

-- Use indexes for performance
CREATE INDEX idx_numero_parte ON materiales(numero_parte);
```

## File Organization

### Module Structure

```
module_name/
├── __init__.py          # Package initialization
├── routes.py            # Route definitions
├── models.py            # Data models (if any)
├── utils.py             # Utility functions
└── templates/
    └── module.html      # Templates
```

### Import Order

```python
# Standard library
import os
import json
from datetime import datetime

# Third-party
from flask import Flask, request, jsonify
import pandas as pd

# Local application
from .db_mysql import execute_query
from .auth_system import AuthSystem
```

## Git Commit Messages

### Format

```
<tipo>: <descripción breve>

<descripción detallada opcional>
```

### Types

- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `docs`: Cambios en documentación
- `style`: Cambios de formato (no afectan código)
- `refactor`: Refactorización de código
- `test`: Agregar o modificar tests
- `chore`: Tareas de mantenimiento

### Examples

```
feat: Agregar inventario de rollos SMD

Implementa sistema automático de tracking de rollos SMD
con triggers y vistas para monitoreo en tiempo real.

fix: Corregir error en cálculo de inventario

El cálculo no consideraba movimientos de retorno.

docs: Actualizar guía de desarrollo de módulos
```

## Code Review Checklist

### Before Committing

- [ ] Code follows naming conventions
- [ ] All functions have docstrings
- [ ] Error handling implemented
- [ ] No hardcoded credentials
- [ ] Console logs use emoji prefixes
- [ ] Event delegation used for dynamic content
- [ ] Functions exposed globally when needed
- [ ] SQL queries are parameterized
- [ ] No debug code left in

### Before Deploying

- [ ] Tested locally
- [ ] Database migrations applied
- [ ] Environment variables configured
- [ ] No breaking changes to existing APIs
- [ ] Audit logging added for sensitive operations
- [ ] Permission checks in place
- [ ] Documentation updated

## Common Patterns to Follow

### Database Operations

```python
def obtener_datos(filtro=None):
    """Pattern for database queries"""
    try:
        query = "SELECT * FROM tabla WHERE condicion = %s"
        result = execute_query(query, (filtro,), fetch='all')
        return result or []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []
```

### API Endpoints

```python
@app.route('/api/recurso', methods=['POST'])
@login_requerido
def crear_recurso():
    """Pattern for API endpoints"""
    try:
        data = request.get_json()

        # Validation
        if not data.get('campo_requerido'):
            return jsonify({'error': 'Campo requerido'}), 400

        # Business logic
        result = procesar_datos(data)

        # Audit
        auth_system.registrar_auditoria(
            usuario=session.get('usuario'),
            modulo='modulo',
            accion='crear',
            descripcion='Recurso creado'
        )

        return jsonify({'success': True, 'data': result})

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': 'Error interno'}), 500
```

### Frontend Module

```javascript
// Pattern for frontend modules

// State
let moduleData = [];

// Load data
async function loadModuleData() {
  try {
    const response = await axios.get("/api/module/data");
    moduleData = response.data;
    renderModule();
  } catch (error) {
    console.error("❌ Error:", error);
  }
}

// Render
function renderModule() {
  const container = document.getElementById("module-container");
  if (!container) return;

  container.innerHTML = moduleData
    .map(
      (item) => `
        <div class="module-item" data-id="${item.id}">
            ${item.name}
        </div>
    `
    )
    .join("");
}

// Event delegation
function initializeEventListeners() {
  if (document.body.dataset.moduleListenersAttached) return;

  document.body.addEventListener("click", function (e) {
    if (e.target.closest(".module-item")) {
      handleItemClick(e.target.closest(".module-item"));
    }
  });

  document.body.dataset.moduleListenersAttached = "true";
}

// Expose
window.initializeModuleEventListeners = initializeEventListeners;
window.loadModuleData = loadModuleData;

// Auto-initialize
document.addEventListener("DOMContentLoaded", initializeEventListeners);
if (document.readyState !== "loading") {
  initializeEventListeners();
}
```
