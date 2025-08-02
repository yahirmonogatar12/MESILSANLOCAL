# 🚀 PROMPT DETALLADO: Implementación de Sistema AJAX Dinámico con Contenedores Específicos

## 📋 CONTEXTO Y OBJETIVO
Necesito implementar un sistema de carga dinámica AJAX para módulos específicos en una aplicación Flask, evitando conflictos entre diferentes componentes y asegurando que los estilos CSS se apliquen correctamente.

## 🎯 REQUISITOS ESPECÍFICOS

### 1. **Estructura Base Requerida:**
- Aplicación Flask con Jinja2 templating
- Template base: `MaterialTemplate.html` con sistema de navegación
- Bootstrap 5.3.2 como framework frontend
- Sistema de autenticación de usuarios

### 2. **Funcionalidad AJAX Deseada:**
- Carga dinámica de contenido sin recargar página completa
- Contenedores únicos para evitar conflictos entre módulos
- Sufijos específicos en IDs y clases CSS para prevenir colisiones
- Preservación de estilos CSS específicos del módulo
- Manejo de errores robusto (404, 500, autenticación)

## 🛠️ PASOS DE IMPLEMENTACIÓN

### **PASO 1: Crear Ruta AJAX Específica**
```python
# En app/routes.py
@app.route('/nombre-modulo-ajax')
@login_required
def nombre_modulo_ajax():
    try:
        if 'username' not in session:
            return redirect(url_for('login'))
        return render_template('ruta/nombre_modulo_ajax.html')
    except Exception as e:
        print(f"Error en nombre_modulo_ajax: {e}")
        return "Error interno del servidor", 500
```

**Criterios importantes:**
- ✅ Incluir `@login_required` para autenticación
- ✅ Verificar `session['username']` para doble seguridad
- ✅ Manejo de excepciones con logs
- ✅ Ruta específica con sufijo `-ajax`

### **PASO 2: Crear Template AJAX Específico**
```html
<!-- archivo: nombre_modulo_ajax.html -->
<!DOCTYPE html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Título del Módulo</title>
</head>
<body>

<!-- ESTILOS INCRUSTADOS DIRECTAMENTE -->
<style>
/* Todos los estilos CSS específicos del módulo aquí */
.contenedor-modulo {
    /* Estilos específicos */
}
/* ... resto de estilos ... */
</style>

<!-- CONTENEDOR PRINCIPAL CON ID ÚNICO -->
<div class="contenedor-modulo" id="modulo-sufijo-unique-container">
    <!-- Contenido específico del módulo -->
    
    <!-- Panel de estadísticas con IDs únicos -->
    <div class="stats-panel" id="statsPanel-sufijo">
        <div class="stat-card">
            <div class="stat-value" id="statTotal-sufijo">0</div>
        </div>
    </div>
    
    <!-- Controles con IDs únicos -->
    <div class="controls-panel">
        <button onclick="funcionEspecifica_sufijo()" id="btnAccion-sufijo">
            Acción
        </button>
    </div>
    
    <!-- Contenido principal -->
    <div class="content-container" id="contentContainer-sufijo">
        <!-- Contenido dinámico -->
    </div>
</div>

<!-- JAVASCRIPT ESPECÍFICO DEL MÓDULO -->
<script src="{{ url_for('static', filename='js/nombre_modulo_especifico.js') }}?v=1.0"></script>

<!-- FUNCIONES JAVASCRIPT INLINE ESPECÍFICAS -->
<script>
// Funciones específicas para el módulo con sufijos únicos
function funcionEspecifica_sufijo() {
    // Lógica específica
}

function inicializarModulo_sufijo() {
    console.log('🚀 Inicializando módulo con sufijo');
    // Lógica de inicialización
}

// Auto-inicialización
document.addEventListener('DOMContentLoaded', inicializarModulo_sufijo);
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarModulo_sufijo);
} else {
    inicializarModulo_sufijo();
}
</script>

</body>
</html>
```

**Criterios importantes:**
- ✅ NO extender MaterialTemplate (usar `<!DOCTYPE html>` simple)
- ✅ Estilos CSS incrustados directamente en `<style>`
- ✅ IDs únicos con sufijos específicos (`-sufijo`)
- ✅ Funciones JavaScript con sufijos únicos
- ✅ Auto-inicialización robusta del módulo

### **PASO 3: Modificar Template Base (MaterialTemplate.html)**
```javascript
// En MaterialTemplate.html, agregar función AJAX específica
async function mostrarModuloEspecifico() {
    try {
        // Limpiar contenido previo
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
            mainContent.innerHTML = '<div class="loading-indicator">Cargando...</div>';
        }
        
        // Cargar contenido AJAX
        const response = await fetch('/nombre-modulo-ajax');
        
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('Módulo no encontrado (404)');
            } else if (response.status === 500) {
                throw new Error('Error interno del servidor (500)');
            } else if (response.status === 401 || response.status === 403) {
                throw new Error('No autorizado - redirigiendo al login');
            }
            throw new Error(`Error HTTP: ${response.status}`);
        }
        
        const html = await response.text();
        
        if (mainContent) {
            mainContent.innerHTML = html;
            
            // Ejecutar inicialización si existe
            if (typeof window.inicializarModulo_sufijo === 'function') {
                window.inicializarModulo_sufijo();
                console.log('✅ Módulo inicializado correctamente');
            }
        }
        
    } catch (error) {
        console.error('❌ Error cargando módulo:', error);
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
            mainContent.innerHTML = `
                <div class="alert alert-danger">
                    <h4>Error al cargar el módulo</h4>
                    <p>${error.message}</p>
                    <button onclick="location.reload()" class="btn btn-primary">
                        Recargar página
                    </button>
                </div>
            `;
        }
    }
}
```

**Criterios importantes:**
- ✅ Manejo de errores HTTP específicos (404, 500, 401/403)
- ✅ Indicador de carga mientras se procesa
- ✅ Limpieza de contenido previo
- ✅ Inicialización automática del módulo cargado
- ✅ Fallback de recarga de página en caso de error

### **PASO 4: Modificar Botón/Enlace de Navegación**
```html
<!-- En LISTA_NOMBRE_SECCION.html o donde esté el botón -->
<li class="nav-item">
    <a class="nav-link d-flex align-items-center" 
       href="#" 
       onclick="mostrarModuloEspecifico(); return false;">
        <i class="fas fa-icon-específico me-2"></i>
        Nombre del Módulo
    </a>
</li>
```

**Criterios importantes:**
- ✅ `href="#"` para evitar navegación tradicional
- ✅ `onclick` con `return false` para prevenir comportamiento por defecto
- ✅ Llamada a función AJAX específica

## 🔧 RESOLUCIÓN DE PROBLEMAS COMUNES

### **Problema 1: Estilos CSS no se aplican**
**Solución:** Incrustar estilos directamente en el template AJAX
```html
<style>
/* Todos los estilos específicos aquí */
</style>
```

### **Problema 2: Error 404 - Ruta no encontrada**
**Verificar:**
- ✅ Ruta definida correctamente en `routes.py`
- ✅ Decorador `@app.route` con URL correcta
- ✅ Función nombrada correctamente

### **Problema 3: Error 500 - Error interno**
**Verificar:**
- ✅ Template existe en la ruta correcta
- ✅ Sintaxis Jinja2 correcta
- ✅ Manejo de excepciones en la ruta

### **Problema 4: Error de autenticación**
**Verificar:**
- ✅ `@login_required` presente
- ✅ Verificación de `session['username']`
- ✅ Usuario logueado correctamente

### **Problema 5: Conflictos entre módulos**
**Solución:** Usar sufijos únicos en todos los elementos
```javascript
// ❌ MAL - IDs genéricos
document.getElementById('statsPanel')

// ✅ BIEN - IDs con sufijos únicos
document.getElementById('statsPanel-smt')
```

## 📁 ESTRUCTURA DE ARCHIVOS RESULTANTE

```
app/
├── routes.py                     # Rutas Flask con nueva ruta AJAX
├── templates/
│   ├── MaterialTemplate.html     # Template base con función AJAX
│   ├── Sección/
│   │   ├── modulo_original.html   # Template original (mantener)
│   │   └── modulo_ajax.html       # Nuevo template AJAX
│   └── LISTAS/
│       └── LISTA_SECCION.html     # Lista con botón modificado
└── static/
    ├── js/
    │   └── modulo_especifico.js   # JavaScript específico del módulo
    └── css/
        └── modulo_especifico.css  # CSS específico (opcional)
```

## 🎯 VALIDACIÓN DE IMPLEMENTACIÓN EXITOSA

### **Checklist de Verificación:**
- [ ] **Ruta AJAX**: Funciona sin errores 404/500
- [ ] **Autenticación**: Solo usuarios logueados pueden acceder
- [ ] **Carga AJAX**: Contenido se carga dinámicamente sin recargar página
- [ ] **Estilos CSS**: Se aplican correctamente al contenido cargado
- [ ] **JavaScript**: Funciones específicas del módulo funcionan
- [ ] **IDs únicos**: No hay conflictos con otros módulos
- [ ] **Manejo de errores**: Errores se muestran apropiadamente
- [ ] **Inicialización**: Módulo se inicializa automáticamente al cargar

### **Comandos de Prueba:**
```bash
# 1. Verificar que el servidor Flask está corriendo
python run.py

# 2. Probar ruta AJAX directamente en navegador
http://localhost:5000/nombre-modulo-ajax

# 3. Verificar logs en consola del navegador (F12)
# Debe mostrar: "🚀 Inicializando módulo con sufijo"
```

## 🚨 NOTAS IMPORTANTES

1. **Siempre usar sufijos únicos** para evitar conflictos entre módulos
2. **Incrustar CSS directamente** en templates AJAX para garantizar que se apliquen
3. **Manejar todos los códigos de error HTTP** (404, 500, 401/403)
4. **Verificar autenticación** tanto con decorador como con session
5. **Probar en diferentes navegadores** para asegurar compatibilidad
6. **Mantener templates originales** como respaldo
7. **Usar versionado en archivos JS/CSS** (`?v=1.0`) para evitar caché

## 📝 PLANTILLA DE PROMPT PARA FUTURAS IMPLEMENTACIONES

```
Necesito implementar carga AJAX dinámica para el módulo [NOMBRE_MODULO] en la sección [NOMBRE_SECCION].

REQUISITOS:
- Crear ruta AJAX: /[nombre-modulo]-ajax
- Template AJAX: [nombre_modulo]_ajax.html
- Sufijo único: -[sufijo]
- Contenedor específico: [sufijo]-unique-container
- Función AJAX en MaterialTemplate: mostrar[NombreModulo]()
- Estilos CSS incrustados directamente
- IDs únicos con sufijo para evitar conflictos
- Manejo robusto de errores (404, 500, autenticación)
- Auto-inicialización del módulo JavaScript

SEGUIR EXACTAMENTE la estructura y criterios del prompt detallado de implementación AJAX.
```

Este prompt te permitirá reproducir el sistema AJAX de manera consistente en futuros módulos, manteniendo la misma estructura, manejo de errores y prevención de conflictos que implementamos exitosamente. 🚀
