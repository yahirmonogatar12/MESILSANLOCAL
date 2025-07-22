# 🔐 Sistema de Permisos de Dropdowns - ILSAN MES

## 📋 Descripción

El sistema de permisos de dropdowns permite controlar el acceso específico a cada opción dentro de los menús desplegables (dropdowns) de las listas AJAX del sistema. En lugar de tener permisos generales de "exportación", ahora se pueden configurar permisos granulares para cada botón/opción individual.

## 🎯 Características Principales

### ✨ **Permisos Granulares**
- Control específico por cada dropdown/botón
- Organizados por lista (LISTA_DE_MATERIALES, LISTA_INFORMACIONBASICA, etc.)
- Agrupados por secciones lógicas
- Descripciones detalladas para cada permiso

### 🗂️ **Estructura Organizativa**
```
LISTA_DE_MATERIALES/
├── Control de material/
│   ├── Control de material de almacén
│   ├── Control de salida
│   ├── Control de material retorno
│   └── ... (más opciones)
├── Control de material MSL/
│   ├── Control total de material
│   └── ... (más opciones)
└── Control de refacciones/
    └── ... (más opciones)
```

### 👥 **Gestión de Roles**
- Asignación masiva de permisos por rol
- Vista previa de permisos asignados
- Interfaz intuitiva de selección/deselección
- Aplicación inmediata de cambios

## 🚀 Cómo Usar el Sistema

### 1. **Acceso al Panel de Administración**

Navegar a: `http://localhost:5000/admin/panel`

### 2. **Ver Permisos de un Usuario**

1. En la tabla de usuarios, clic en el botón amarillo de "Ver permisos de dropdowns" (🔑)
2. Se abrirá un modal mostrando todos los permisos de dropdowns por rol
3. Los permisos están organizados por:
   - **Lista**: LISTA_DE_MATERIALES, LISTA_INFORMACIONBASICA, etc.
   - **Sección**: Control de material, Control de proceso, etc.
   - **Botón específico**: Control de salida, Gestión de departamentos, etc.

### 3. **Editar Permisos de Dropdowns**

1. En el modal de permisos, clic en "Editar Permisos de Dropdowns"
2. Seleccionar el rol a modificar en el dropdown
3. Se cargarán todos los permisos disponibles organizados por lista y sección
4. Marcar/desmarcar los permisos deseados
5. Usar "Seleccionar Todos" o "Deseleccionar Todos" para operaciones masivas
6. Clic en "Guardar Permisos"

## 🏗️ Estructura Técnica

### **Tablas de Base de Datos**

```sql
-- Tabla de permisos específicos de botones/dropdowns
CREATE TABLE permisos_botones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pagina TEXT NOT NULL,           -- Ej: LISTA_DE_MATERIALES
    seccion TEXT NOT NULL,          -- Ej: Control de material
    boton TEXT NOT NULL,            -- Ej: Control de salida
    descripcion TEXT,               -- Descripción del permiso
    activo INTEGER DEFAULT 1,
    UNIQUE(pagina, seccion, boton)
);

-- Tabla de relación roles-permisos de botones
CREATE TABLE rol_permisos_botones (
    rol_id INTEGER NOT NULL,
    permiso_boton_id INTEGER NOT NULL,
    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (rol_id, permiso_boton_id),
    FOREIGN KEY (rol_id) REFERENCES roles(id),
    FOREIGN KEY (permiso_boton_id) REFERENCES permisos_botones(id)
);
```

### **Rutas de API**

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/admin/listar_permisos_dropdowns` | Obtener todos los permisos de dropdowns |
| GET | `/admin/obtener_permisos_dropdowns_rol/<rol_id>` | Obtener permisos de un rol específico |
| POST | `/admin/actualizar_permisos_dropdowns_rol` | Actualizar permisos de un rol |

### **Ejemplo de Uso en Código**

```python
from app.db import get_db_connection

# Verificar si un usuario tiene permiso para un dropdown específico
def verificar_permiso_dropdown(usuario_id, pagina, seccion, boton):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) FROM usuarios_sistema u
        JOIN usuario_roles ur ON u.id = ur.usuario_id
        JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
        JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
        WHERE u.id = ? AND pb.pagina = ? AND pb.seccion = ? AND pb.boton = ?
        AND u.activo = 1 AND pb.activo = 1
    ''', (usuario_id, pagina, seccion, boton))
    
    tiene_permiso = cursor.fetchone()[0] > 0
    conn.close()
    
    return tiene_permiso

# Ejemplo de uso
usuario_id = 1
puede_acceder = verificar_permiso_dropdown(
    usuario_id, 
    'LISTA_DE_MATERIALES', 
    'Control de material', 
    'Control de salida'
)

if puede_acceder:
    print("✅ Usuario puede acceder al control de salida")
else:
    print("❌ Usuario no tiene permisos para este dropdown")
```

## 📊 Permisos Disponibles

### **LISTA_DE_MATERIALES**
- **Control de material**:
  - Control de material de almacén
  - Control de salida  
  - Control de material retorno
  - Recibo y pago del material
  - Historial de material
  - Estatus de material
  - Material sustituto
  - Consultar PEPS
  - Control de Long-Term Inventory
  - Registro de material real
  - Historial de inventario real
  - Ajuste de número de parte

- **Control de material MSL**:
  - Control total de material
  - Control de entrada y salida de material
  - Estatus de material MSL

- **Control de refacciones**:
  - Estándares sobre refacciones
  - Control de recibo de refacciones
  - Control de salida de refacciones
  - Estatus de inventario de refacciones

### **LISTA_INFORMACIONBASICA**
- **Información básica**:
  - Gestión de departamentos
  - Gestión de empleados
  - Gestión de proveedores
  - Gestión de clientes
  - Administracion de itinerario
  - Consultar licencias

- **Control de Proceso**:
  - Control de departamento
  - Control de proceso

### **LISTA_CONTROL_DE_PROCESO**
- **Control de produccion**:
  - Historial de operacion por proceso
  - BOM Management By Process

- **Reporte diario de inspeccion**:
  - Reporte diario de inspeccion

- **Control de otras identificaciones**:
  - Registro de movimiento de identificacion
  - Control de otras identificaciones

- **Control de N/S**:
  - Control de movimiento de N/S de producto
  - Model S/N Management

- **Control de material Scrap**:
  - Control de Scrap

### **LISTA_CONTROL_DE_CALIDAD**
- **Control de calidad**:
  - Inspección de entrada
  - Inspección en proceso
  - Inspección final
  - Control de calibracion
  - Reportes de calidad

### **LISTA_DE_CONTROL_DE_RESULTADOS**
- **Control de resultados**:
  - Análisis de resultados
  - Reportes estadísticos
  - Gráficos de tendencia

### **LISTA_DE_CONTROL_DE_REPORTE**
- **Control de reporte**:
  - Generación de reportes
  - Configuración de reportes
  - Programación de reportes

### **LISTA_DE_CONFIGPG**
- **Configuración**:
  - Configuración general
  - Configuración de usuarios
  - Configuración de impresión
  - Configuración de red

## 🔒 Seguridad

### **Principios de Seguridad**
- **Deny by Default**: Sin permisos específicos, no se permite acceso
- **Least Privilege**: Solo los permisos mínimos necesarios
- **Separation of Duties**: Diferentes niveles de acceso por rol
- **Auditabilidad**: Todos los cambios de permisos se registran

### **Jerarquía de Roles**
1. **superadmin** (Nivel 10): Todos los permisos
2. **admin** (Nivel 9): Casi todos los permisos
3. **supervisor_almacen** (Nivel 8): Permisos de almacén y materiales
4. **operador_almacen** (Nivel 5): Operaciones básicas de almacén
5. **consulta** (Nivel 2): Solo visualización

## 🛠️ Mantenimiento

### **Agregar Nuevos Permisos**
Para agregar nuevos permisos de dropdowns, modificar el método `_crear_permisos_botones_default()` en `app/auth_system.py`:

```python
permisos_botones.append(
    ('NUEVA_LISTA', 'Nueva Sección', 'Nuevo Botón', 'Descripción del nuevo permiso')
)
```

Luego ejecutar:
```bash
python inicializar_usuarios.py
```

### **Backup y Restauración**
Los permisos se almacenan en la base de datos SQLite y se respaldan automáticamente con el sistema de auditoría.

## 🐛 Solución de Problemas

### **Problema: No se muestran permisos**
**Solución**: Verificar que el rol tenga permisos asignados y que estén activos.

### **Problema: Cambios no se aplican**
**Solución**: Verificar la consola del navegador y los logs del servidor para errores.

### **Problema: Usuario no puede acceder después de asignar permisos**
**Solución**: Verificar que el usuario esté activo y no bloqueado.

## 📞 Soporte

Para soporte técnico o consultas sobre el sistema de permisos de dropdowns, contactar al administrador del sistema.

---

**Versión**: 2.0  
**Última actualización**: Enero 2025  
**Sistema**: ILSAN MES
