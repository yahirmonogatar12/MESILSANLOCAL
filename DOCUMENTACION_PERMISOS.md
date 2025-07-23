# Sistema de Permisos de Dropdowns - Documentación

## 📋 Resumen del Sistema

El sistema de permisos de dropdowns ahora está **completamente automatizado** y sincronizado con los archivos reales de tu aplicación.

## 🔄 ¿Cómo Funciona?

### 1. **Escaneo Automático**
- Escanea todos los archivos en `app/templates/LISTAS/` (excepto `menu_sidebar.html`)
- Extrae automáticamente elementos con atributos:
  - `data-permiso-pagina`
  - `data-permiso-seccion` 
  - `data-permiso-boton`

### 2. **Sincronización con Base de Datos**
- **Agrega** permisos nuevos encontrados en archivos
- **Desactiva** permisos que ya no existen en archivos
- **Actualiza** descripciones de permisos existentes

### 3. **Gestión por Roles**
- Cada rol puede tener permisos específicos habilitados/deshabilitados
- Interfaz visual para gestionar permisos por rol
- Filtros avanzados por página, sección y estado

## 🚀 Archivos Escaneados

Los siguientes archivos son procesados automáticamente:

✅ **LISTA_DE_MATERIALES.html** - 19 permisos
- Control de material (12 botones)
- Control de material MSL (3 botones)  
- Control de refacciones (4 botones)

✅ **LISTA_INFORMACIONBASICA.html** - 24 permisos
- Administración de usuario (6 botones)
- Control de Proceso (7 botones)
- Control de producción (6 botones)
- Control de material (2 botones)
- Control de cliente (2 botones)
- Otros (1 botón)

✅ **LISTA_CONTROLDEPRODUCCION.html** - 10 permisos
- Control de plan de producción (2 botones)
- Control de SMT (3 botones)
- Control de sub Material (4 botones)
- Line Material Management (1 botón)

✅ **LISTA_CONTROL_DE_PROCESO.html** - 21 permisos
- Control de producción (6 botones)
- Reporte diario de inspección (3 botones)
- Control de empaque (5 botones)
- Return Warehousing (2 botones)
- Control de otras identificaciones (2 botones)
- Control de N/S (2 botones)
- Control de material Scrap (1 botón)

✅ **LISTA_CONTROL_DE_CALIDAD.html** - 11 permisos
- Control de item de reparación (2 botones)
- Historial de material (2 botones)
- Historial de Sub Material (3 botones)
- Interlock History (1 botón)
- Control de Master Sample de SMT (2 botones)
- Inspección de calidad (1 botón)

✅ **LISTA_DE_CONTROL_DE_RESULTADOS.html** - 12 permisos
- Control de inventario (1 botón)
- Consultar resultados (1 botón)
- Historial de máquinas SMT (5 botones)
- Historial de máquinas calidad (4 botones)
- Historial de otras máquinas (1 botón)

✅ **LISTA_DE_CONTROL_DE_REPORTE.html** - 5 permisos
- Product Tracking (2 botones)
- Defect information (1 botón)
- Monitoreo (2 botones)

✅ **LISTA_DE_CONFIGPG.html** - 5 permisos
- Product Tracking (2 botones)
- Defect information (1 botón)
- Monitoreo (2 botones)

❌ **menu_sidebar.html** - Excluido (no debe tener permisos)

**Total: 107 permisos únicos**

## 🛠️ Uso del Sistema

### Interfaz de Gestión
Accede a: `/admin/gestionar_permisos_dropdowns`

### Funciones Disponibles:

1. **Sincronizar** - Actualiza permisos desde archivos LISTAS
2. **Exportar** - Descarga permisos de un rol en JSON
3. **Reset** - Recarga permisos desde la base de datos
4. **Filtros** - Busca por página, sección o estado
5. **Habilitar/Deshabilitar** - Gestiona permisos individuales o masivos

### Script Manual
Ejecuta cuando necesites: `python sincronizar_permisos_dropdowns.py`

## 📊 Estadísticas de la Última Sincronización

- ✅ **107 permisos activos** (sincronizados con archivos)
- ❌ **90 permisos inactivos** (obsoletos, no existen en archivos)
- ➕ **79 nuevos agregados** (encontrados en archivos)
- 🗑️ **90 desactivados** (no encontrados en archivos)

## 🔧 Mantenimiento

### Agregar Nuevos Permisos
1. Edita cualquier archivo en `app/templates/LISTAS/`
2. Agrega elementos con atributos `data-permiso-*`
3. Ejecuta sincronización desde la interfaz o script
4. Los nuevos permisos aparecerán automáticamente

### Eliminar Permisos
1. Elimina o modifica elementos en archivos LISTAS
2. Ejecuta sincronización
3. Los permisos obsoletos se desactivarán automáticamente

## 🚨 Importante

- Solo se procesan archivos `.html` en la carpeta `LISTAS`
- `menu_sidebar.html` está excluido intencionalmente
- Los permisos desactivados se conservan en la BD para auditoría
- Cada sincronización genera un reporte JSON con estadísticas

## 🎯 Beneficios del Nuevo Sistema

✅ **Sincronización automática** con archivos reales
✅ **No más permisos hardcodeados** en el código
✅ **Detección automática** de nuevos permisos
✅ **Limpieza automática** de permisos obsoletos  
✅ **Interfaz visual** para gestión de roles
✅ **Filtros avanzados** y búsqueda
✅ **Reportes detallados** de cada sincronización
✅ **Auditoría completa** de cambios

¡El sistema ahora está completamente sincronizado y listo para usar! 🎉
