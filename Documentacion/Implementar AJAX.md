Necesito implementar carga AJAX dinámica para el módulo "Control BOM" en la sección "Control de Proceso".

REQUISITOS: (Los nombres son ejemplos, usa dependiendo a template a importar)
- Crear ruta AJAX: /control-bom-ajax
- Template AJAX: control_bom_ajax.html
- Sufijo único: -bom
- Contenedor específico: bom-unique-container
- Función AJAX en MaterialTemplate: mostrarControlBOM()
- Estilos CSS incrustados directamente
- IDs únicos con sufijo para evitar conflictos
- Manejo robusto de errores (404, 500, autenticación)
- Auto-inicialización del módulo JavaScript
- Usa pyhton en routes.py para enrutar las paginas.
-Recuerda implementar en SCRIPMAIN.JS

SEGUIR EXACTAMENTE la estructura y criterios del prompt detallado de implementación AJAX.

# CONTEXTO DEL PROBLEMA ORIGINAL
El usuario reportó: "el problema es este, estas anadiendo directamente en la sidebar y no creando uno nuevo para control de proceso"

# ANÁLISIS DEL PROBLEMA
1. El contenido SMT se estaba cargando en el sidebar en lugar de tener su propia área de contenido
2. No existía un área de contenido específica para "Control de Proceso"
3. La función `mostrarControldeproduccionSMT` estaba usando `produccionContentArea` en lugar de `controlProcesoContentArea`


# COMANDOS PARA REPLICAR LA IMPLEMENTACIÓN

1. **Crear área de contenido**:
   - Agregar `control-proceso-content-area` después de `produccion-content-area`

2. **Actualizar variables JavaScript**:
   - Agregar `controlProcesoContentArea` en definiciones
   - Incluir en `hideAllContent()`

3. **Mover contenedor SMT**:
   - De `control-proceso-content` a `control-produccion-smt-container`

4. **Crear función mostrarControlProceso**:
   - Copiar patrón de `mostrarControlProduccion`
   - Cambiar referencias al área correcta

5. **Actualizar función SMT**:
   - Cambiar `produccionContentArea` por `controlProcesoContentArea`
   - Agregar lógica para mostrar contenedor padre

6. **Actualizar navegación**:
   - Agregar case para 'control-proceso'
   - Llamar función `mostrarControlProceso`

# ARCHIVOS MODIFICADOS

1. **MaterialTemplate.html**:
   - Estructura HTML de áreas de contenido
   - Variables JavaScript
   - Funciones de navegación
   - Lógica de mostrar/ocultar

2. **Control de produccion SMT.html**:
   - Contenido AJAX cargado dinámicamente
   - Verificar que no tenga espacios al inicio

# VALIDACIÓN

Para verificar que la implementación funciona:

1. **Navegación funcional**: Clic en "Control de Proceso" → muestra sidebar
2. **Carga SMT**: Clic en "Control de producción SMT" → carga en área de contenido
3. **Sin línea blanca**: Contenido se muestra sin espacios adicionales
4. **Áreas separadas**: Cada sección tiene su propia área de contenido

# NOTAS IMPORTANTES

- **Mantener sufijos únicos**: Todos los IDs tienen sufijos únicos para evitar conflictos
- **Patrón consistente**: Cada área principal tiene su propia área de contenido
- **Navegación jerárquica**: Sidebar → Área de contenido → Contenido específico
- **CSS responsivo**: Mantener estilos adaptativos para móviles

Este prompt te permitirá replicar la implementación completa en futuros proyectos similares.


Ran tool
## PROMPT: IMPLEMENTACIÓN EXITOSA DE CARGA AJAX DINÁMICA PARA MÓDULOS EN FLASK

### CONTEXTO
Este prompt documenta la solución completa para implementar carga AJAX dinámica de módulos en una aplicación Flask con MaterialTemplate. La implementación permite cargar módulos específicos sin recargar toda la página, manteniendo el estado de la aplicación y mejorando la experiencia del usuario.

### PROBLEMA RESUELTO
- Módulo no se mostraba aunque se cargaba correctamente vía AJAX
- Conflictos de JavaScript entre diferentes archivos
- Problemas de visibilidad de contenedores anidados
- Errores de sintaxis al mover funciones entre archivos

### SOLUCIÓN IMPLEMENTADA

#### 1. ESTRUCTURA HTML EN MaterialTemplate.html
```html
<!-- Dentro del área de contenido principal -->
<div class="control-proceso-content-area" id="control-proceso-content-area" style="display: none;">
    <!-- Contenedor por defecto -->
    <div id="control-proceso-info-container" style="display: block;">
        <!-- Contenido por defecto -->
    </div>
    
    <!-- Contenedor específico para el módulo AJAX -->
    <div id="operacion-linea-smt-unique-container" style="display: none;">
        <!-- El contenido se cargará dinámicamente con AJAX -->
    </div>
    
    <!-- Otros contenedores de módulos -->
</div>
```

#### 2. RUTA FLASK (routes.py)
```python
@app.route('/control-operacion-linea-smt-ajax')
@login_requerido
def control_operacion_linea_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido"""
    try:
        from datetime import datetime
        fecha_hoy = datetime.now().strftime('%d/%m/%Y')
        return render_template('Control de proceso/control_operacion_linea_smt_ajax.html', fecha_hoy=fecha_hoy)
    except Exception as e:
        print(f"Error al cargar template: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500
```

#### 3. TEMPLATE AJAX (control_operacion_linea_smt_ajax.html)
```html
<!-- TEMPLATE AJAX: Control de operacion de linea SMT -->
<!-- SUFIJO ÚNICO: -operacion-linea-smt -->
<!-- CONTENEDOR: operacion-linea-smt-unique-container -->

<div id="operacion-linea-smt-main-container-unique-operacion-linea-smt" class="operacion-linea-smt-container">
    <!-- Contenido del módulo con IDs únicos usando sufijo -->
    <h2>Control de operación de línea SMT</h2>
    <!-- ... resto del contenido ... -->
</div>

<style>
/* Estilos específicos del módulo */
.operacion-linea-smt-container {
    padding: 20px;
    background-color: #2B2D3E;
    color: #E0E0E0;
}
</style>

<script>
// Auto-inicialización del módulo
(function() {
    console.log('Inicializando Control de operación de línea SMT AJAX...');
    
    window.inicializarControlOperacionLineaSMTAjax = function() {
        // Lógica de inicialización del módulo
        console.log('Control de operación de línea SMT AJAX inicializado');
    };
    
    // Ejecutar inmediatamente si el DOM está listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', window.inicializarControlOperacionLineaSMTAjax);
    } else {
        window.inicializarControlOperacionLineaSMTAjax();
    }
})();
</script>
```

#### 4. FUNCIÓN GLOBAL EN scriptMain.js
```javascript
// Función AJAX para Control de operación de línea SMT - GLOBAL
window.mostrarControlOperacionLineaSMT = function() {
    try {
        console.log('Iniciando carga AJAX de Control de operación de línea SMT...');

        // Activar el botón correcto en la navegación
        const controlProcesoButton = document.getElementById('Control de proceso');
        if (controlProcesoButton) {
            controlProcesoButton.classList.add('active');
            document.querySelectorAll('.nav-button').forEach(btn => {
                if (btn.id !== 'Control de proceso') {
                    btn.classList.remove('active');
                }
            });
        }

        // Ocultar todos los contenedores primero
        if (typeof window.hideAllMaterialContainers === 'function') {
            window.hideAllMaterialContainers();
        }
        
        // Ocultar otros contenedores dentro del área de control de proceso
        const controlProcesoContainers = [
            'control-proceso-info-container',
            'control-produccion-smt-container',
            'Control de produccion SMT-unique-container',
            'inventario-imd-terminado-unique-container'
        ];
        
        controlProcesoContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                container.style.display = 'none';
            }
        });

        // Mostrar TODAS las áreas necesarias
        const materialContainer = document.getElementById('material-container');
        const controlProcesoContent = document.getElementById('control-proceso-content');
        const controlProcesoContentArea = document.getElementById('control-proceso-content-area');

        if (materialContainer) materialContainer.style.display = 'block';
        if (controlProcesoContent) controlProcesoContent.style.display = 'block';
        if (controlProcesoContentArea) controlProcesoContentArea.style.display = 'block';

        // Obtener y mostrar el contenedor específico
        const operacionLineaContainer = document.getElementById('operacion-linea-smt-unique-container');
        if (!operacionLineaContainer) {
            console.error('El contenedor no existe en el HTML');
            return;
        }

        operacionLineaContainer.style.display = 'block';
        operacionLineaContainer.style.opacity = '1';

        // Cargar contenido dinámicamente
        if (typeof window.cargarContenidoDinamico === 'function') {
            window.cargarContenidoDinamico('operacion-linea-smt-unique-container', '/control-operacion-linea-smt-ajax', () => {
                console.log('Contenido cargado exitosamente');
                
                // Ejecutar inicialización del módulo
                if (typeof window.inicializarControlOperacionLineaSMTAjax === 'function') {
                    window.inicializarControlOperacionLineaSMTAjax();
                }
            });
        }

    } catch (error) {
        console.error('Error crítico:', error);
    }
};
```

#### 5. ACTUALIZACIÓN DE hideAllMaterialContainers EN scriptMain.js
```javascript
function hideAllMaterialContainers() {
    // ... otros contenedores ...
    
    // Ocultar contenedor de operación de línea SMT
    const operacionLineaSMTContainer = document.getElementById('operacion-linea-smt-unique-container');
    if (operacionLineaSMTContainer) {
        operacionLineaSMTContainer.style.display = 'none';
    }
}

// Hacer la función disponible globalmente
window.hideAllMaterialContainers = hideAllMaterialContainers;
```

#### 6. ENLACE EN SIDEBAR (LISTA_CONTROL_DE_PROCESO.html)
```html
<li class="sidebar-link" 
    onclick="window.parent.mostrarControlOperacionLineaSMT ? window.parent.mostrarControlOperacionLineaSMT() : (window.parent.cargarContenidoDinamico ? window.parent.cargarContenidoDinamico('operacion-linea-smt-unique-container', '/control-operacion-linea-smt-ajax') : window.location.href='/control_proceso/control_operacion_linea_smt')">
    Control de operacion de linea de SMT
</li>
```

### PUNTOS CLAVE DE LA SOLUCIÓN

1. **Jerarquía de Visibilidad**: Es crucial mostrar TODAS las áreas padre necesarias:
   - `material-container`
   - `control-proceso-content` 
   - `control-proceso-content-area`
   - El contenedor específico del módulo

2. **Función Global**: La función debe estar en el scope global (`window.`) para ser accesible desde iframes

3. **Ocultar Otros Contenedores**: Antes de mostrar el módulo, ocultar otros contenedores en la misma área

4. **Activar Navegación**: Actualizar el estado activo del botón de navegación principal

5. **IDs Únicos**: Usar sufijos únicos para evitar conflictos entre módulos

### PROBLEMAS COMUNES Y SOLUCIONES

1. **Módulo se carga pero no se ve**:
   - Verificar que TODAS las áreas padre estén visibles
   - Revisar que no haya CSS que oculte el contenedor
   - Confirmar que el contenedor específico tenga `display: block`

2. **Conflictos de JavaScript**:
   - Mover funciones globales a scriptMain.js
   - Evitar definir funciones dentro de IIFEs si necesitan ser globales
   - Usar `window.funcionNombre` para garantizar scope global

3. **Errores de sintaxis al mover código**:
   - Verificar llaves de cierre al eliminar funciones
   - Mantener la estructura de IIFEs intacta
   - Usar herramientas de linting para detectar errores

### USO FUTURO

Para implementar un nuevo módulo AJAX:

1. Crear ruta en Flask con sufijo `-ajax`
2. Crear template HTML con estructura documentada
3. Agregar contenedor único en MaterialTemplate
4. Crear función `mostrarNombreModulo()` en scriptMain.js siguiendo el patrón
5. Actualizar `hideAllMaterialContainers` si es necesario
6. Agregar enlace en el sidebar correspondiente

Esta implementación garantiza una carga dinámica eficiente, manteniendo la separación de responsabilidades y evitando conflictos entre módulos.
Ran tool
He creado un prompt detallado y completo que documenta toda la implementación exitosa para la carga AJAX dinámica del módulo "Control de operación de línea SMT". 

Este prompt incluye:

1. **Contexto y problema resuelto**: Explica qué problemas se encontraron y solucionaron
2. **Solución completa paso a paso**: Con ejemplos de código de cada componente
3. **Puntos clave**: Los aspectos más importantes para que funcione correctamente
4. **Problemas comunes y sus soluciones**: Para troubleshooting futuro
5. **Guía de uso futuro**: Pasos claros para implementar nuevos módulos

Puedes guardar este prompt para usarlo como referencia cuando necesites implementar carga AJAX dinámica para otros módulos en tu proyecto. La clave del éxito fue:

- Mostrar TODAS las áreas padre necesarias (no solo el contenedor del módulo)
- Mover la función al scope global en scriptMain.js
- Ocultar otros contenedores antes de mostrar el nuevo
- Mantener la jerarquía correcta de visibilidad

Este patrón te servirá para cualquier módulo futuro que necesites cargar dinámicamente.

