# 📚 DOCUMENTACIÓN COMPLETA DE APIs - SISTEMA MES ILSAN

> **Versión:** 1.0  
> **Fecha:** 11 de Diciembre 2025  
> **Sistema:** Manufacturing Execution System (MES) - ILSAN Electronics

---

## 📋 ÍNDICE

1. [Introducción](#introducción)
2. [Arquitectura General](#arquitectura-general)
3. [APIs de Autenticación y Usuarios](#1-apis-de-autenticación-y-usuarios)
4. [APIs de Administración](#2-apis-de-administración)
5. [APIs de Permisos y Roles](#3-apis-de-permisos-y-roles)
6. [APIs de Planeación de Producción (Plan Main)](#4-apis-de-planeación-de-producción-plan-main)
7. [APIs de Work Orders (WO) y Purchase Orders (PO)](#5-apis-de-work-orders-wo-y-purchase-orders-po)
8. [APIs de Materiales e Inventario](#6-apis-de-materiales-e-inventario)
9. [APIs de BOM (Bill of Materials)](#7-apis-de-bom-bill-of-materials)
10. [APIs de SMD/SMT](#8-apis-de-smdsmt)
11. [APIs de AOI (Automatic Optical Inspection)](#9-apis-de-aoi-automatic-optical-inspection)
12. [APIs de Modelos RAW](#10-apis-de-modelos-raw)
13. [APIs de Control de Almacén](#11-apis-de-control-de-almacén)
14. [Rutas de Vistas (Frontend)](#12-rutas-de-vistas-frontend)

---

## Introducción

El sistema MES ILSAN es una aplicación web desarrollada en Flask (Python) que gestiona los procesos de manufactura electrónica. Este documento detalla todas las APIs disponibles, sus endpoints, métodos HTTP, parámetros y respuestas esperadas.

### Base URL
```
Desarrollo: http://localhost:5000
Producción: Configurado según despliegue
```

### Formato de Respuesta Estándar
```json
{
    "success": true/false,
    "data": {...},
    "message": "Descripción del resultado",
    "error": "Mensaje de error (si aplica)"
}
```

---

## Arquitectura General

El sistema está organizado en **Blueprints** de Flask:

| Blueprint | Prefijo URL | Archivo | Descripción |
|-----------|-------------|---------|-------------|
| `user_admin_bp` | `/admin` | `user_admin.py` | Administración de usuarios |
| `admin_bp` | `/admin` | `admin_api.py` | Gestión de permisos dropdowns |
| `api_po_wo` | `/api` | `api_po_wo.py` | Work Orders y Purchase Orders |
| `api_raw` | `/api/raw` | `api_raw_modelos.py` | Modelos desde tabla RAW |
| `smd_inventory_api` | `/` | `smd_inventory_api.py` | Inventario de rollos SMD |
| `aoi_api` | `/` | `aoi_api.py` | Inspección óptica automática |
| `smt_bp` | `/` | `smt_routes_date_fixed.py` | Historial SMT |
| `smt_api` | `/` | `smt_routes.py` | API SMT CSV |

---

## 1. APIs de Autenticación y Usuarios

### 1.1 Login
```
POST /login
```
**Descripción:** Autenticar usuario en el sistema.

**Body (form-data):**
```
username: string (requerido)
password: string (requerido)
```

**Respuesta exitosa (AJAX):**
```json
{
    "success": true,
    "redirect": "/inicio"
}
```

**Respuesta error:**
```json
{
    "success": false,
    "message": "Usuario o contraseña incorrectos"
}
```

---

### 1.2 Logout
```
GET /logout
```
**Descripción:** Cerrar sesión del usuario actual.

**Respuesta:** Redirección a `/inicio`

---

### 1.3 Listar Usuarios
```
GET /admin/listar_usuarios
```
**Descripción:** Obtener lista completa de usuarios con sus roles.

**Requiere:** Permiso `sistema.usuarios`

**Respuesta:**
```json
[
    {
        "id": 1,
        "username": "admin",
        "email": "admin@ilsan.com",
        "nombre_completo": "Administrador Sistema",
        "departamento": "Sistemas",
        "cargo": "Administrador",
        "activo": 1,
        "roles": ["superadmin"],
        "ultimo_acceso": "2025-12-11 10:30:00",
        "bloqueado": false
    }
]
```

---

### 1.4 Obtener Usuario Específico
```
GET /admin/obtener_usuario/<username>
```
**Descripción:** Obtener datos detallados de un usuario.

**Parámetros URL:**
- `username`: Nombre de usuario

**Respuesta:**
```json
{
    "id": 1,
    "username": "admin",
    "email": "admin@ilsan.com",
    "nombre_completo": "Administrador Sistema",
    "roles": [
        {"id": 1, "nombre": "superadmin", "descripcion": "Super Administrador"}
    ]
}
```

---

### 1.5 Guardar Usuario
```
POST /admin/guardar_usuario
```
**Descripción:** Crear o actualizar un usuario.

**Body JSON:**
```json
{
    "username": "string (requerido)",
    "password": "string (solo para crear)",
    "email": "string",
    "nombre_completo": "string",
    "departamento": "string",
    "cargo": "string",
    "roles": ["rol1", "rol2"]
}
```

---

### 1.6 Cambiar Estado Usuario
```
POST /admin/cambiar_estado_usuario
```
**Descripción:** Activar/desactivar un usuario.

**Body JSON:**
```json
{
    "username": "string",
    "activo": true/false
}
```

---

### 1.7 Desbloquear Usuario
```
POST /admin/desbloquear_usuario
```
**Descripción:** Desbloquear usuario bloqueado por intentos fallidos.

**Body JSON:**
```json
{
    "username": "string"
}
```

---

### 1.8 Borrar Usuario
```
DELETE /admin/borrar_usuario/<username>
```
**Descripción:** Eliminar un usuario del sistema.

---

## 2. APIs de Administración

### 2.1 Panel de Administración
```
GET /admin/panel
```
**Descripción:** Renderiza la página principal de administración.

---

### 2.2 Panel de Auditoría
```
GET /admin/auditoria
```
**Descripción:** Panel para ver logs de auditoría del sistema.

---

### 2.3 Buscar Auditoría
```
GET /admin/buscar_auditoria
```
**Descripción:** Buscar registros de auditoría con filtros.

**Parámetros Query:**
- `usuario`: Filtrar por usuario
- `modulo`: Filtrar por módulo
- `accion`: Filtrar por acción
- `fecha_desde`: Fecha inicio (YYYY-MM-DD)
- `fecha_hasta`: Fecha fin (YYYY-MM-DD)

---

## 3. APIs de Permisos y Roles

### 3.1 Obtener Roles
```
GET /admin/api/roles
```
**Descripción:** Obtener todos los roles disponibles.

**Respuesta:**
```json
[
    {
        "nombre": "superadmin",
        "descripcion": "Super Administrador con acceso total"
    },
    {
        "nombre": "operador_almacen",
        "descripcion": "Operador de almacén"
    }
]
```

---

### 3.2 Obtener Dropdowns (Permisos de Botones)
```
GET /admin/api/dropdowns
```
**Descripción:** Obtener todos los permisos de botones/dropdowns disponibles.

**Respuesta:**
```json
[
    {
        "pagina": "LISTA_DE_MATERIALES",
        "seccion": "Control de material",
        "boton": "Control de material de almacén",
        "descripcion": "Acceso al control de material de almacén",
        "key": "LISTA_DE_MATERIALES|Control de material|Control de material de almacén",
        "display_name": "LISTA_DE_MATERIALES > Control de material > Control de material de almacén"
    }
]
```

---

### 3.3 Obtener Permisos de un Rol
```
GET /admin/api/role-permissions/<role_name>
```
**Descripción:** Obtener permisos asignados a un rol específico.

**Parámetros URL:**
- `role_name`: Nombre del rol

---

### 3.4 Alternar Permiso
```
POST /admin/api/toggle-permission
```
**Descripción:** Agregar o quitar permiso de un rol.

**Body JSON:**
```json
{
    "role": "operador_almacen",
    "permission_key": "LISTA_DE_MATERIALES|Control de material|Control de salida",
    "action": "add" | "remove"
}
```

---

### 3.5 Habilitar Todos los Permisos
```
POST /admin/api/enable-all-permissions
```
**Descripción:** Habilitar todos los permisos para un rol.

**Body JSON:**
```json
{
    "role": "admin"
}
```

---

### 3.6 Deshabilitar Todos los Permisos
```
POST /admin/api/disable-all-permissions
```
**Descripción:** Deshabilitar todos los permisos de un rol.

---

### 3.7 Listar Roles
```
GET /admin/listar_roles
```
**Descripción:** Listar todos los roles del sistema.

---

### 3.8 Listar Permisos de Botones
```
GET /admin/listar_permisos_botones
```
**Descripción:** Listar todos los permisos de botones definidos.

---

### 3.9 Permisos de Botones por Rol
```
GET /admin/permisos_botones_rol/<rol_id>
```
**Descripción:** Obtener permisos de botones asignados a un rol específico.

---

### 3.10 Actualizar Permisos de Botones de Rol
```
POST /admin/actualizar_permisos_botones_rol
```
**Descripción:** Actualizar los permisos de botones asignados a un rol.

---

### 3.11 Verificar Permiso de Dropdown
```
POST /admin/verificar_permiso_dropdown
```
**Descripción:** Verificar si el usuario actual tiene permiso para un dropdown específico.

**Body JSON:**
```json
{
    "pagina": "LISTA_DE_MATERIALES",
    "seccion": "Control de material",
    "boton": "Control de salida"
}
```

---

### 3.12 Obtener Permisos del Usuario Actual
```
GET /admin/obtener_permisos_usuario_actual
```
**Descripción:** Obtener todos los permisos del usuario en sesión.

---

## 4. APIs de Planeación de Producción (Plan Main)

### 4.1 Listar Planes
```
GET /api/plan
```
**Descripción:** Obtener lista de planes de producción con filtros opcionales.

**Parámetros Query:**
- `start`: Fecha inicio (YYYY-MM-DD)
- `end`: Fecha fin (YYYY-MM-DD)

**Respuesta:**
```json
[
    {
        "lot_no": "ASSYLINE-251211-001",
        "wo_code": "WO-251211-0001",
        "po_code": "PO-251211-0001",
        "working_date": "2025-12-11",
        "line": "SMT A",
        "routing": 1,
        "model_code": "MODEL-001",
        "part_no": "PN-12345",
        "project": "Proyecto X",
        "process": "MAIN",
        "ct": 10.5,
        "uph": 300,
        "plan_count": 1000,
        "input": 500,
        "output": 0,
        "entregadas_main": 450,
        "produced": 500,
        "status": "EN PROGRESO",
        "group_no": 1,
        "sequence": 1
    }
]
```

---

### 4.2 Crear Plan
```
POST /api/plan
```
**Descripción:** Crear un nuevo plan de producción.

**Body JSON:**
```json
{
    "working_date": "2025-12-11",
    "part_no": "PN-12345",
    "line": "SMT A",
    "turno": "DIA",
    "plan_count": 1000,
    "wo_code": "WO-251211-0001",
    "po_code": "PO-251211-0001",
    "group_no": 1
}
```

**Respuesta:**
```json
{
    "success": true,
    "lot_no": "ASSYLINE-251211-001",
    "model_code": "MODEL-001",
    "ct": 10.5,
    "uph": 300,
    "project": "Proyecto X"
}
```

---

### 4.3 Actualizar Plan
```
POST /api/plan/update
```
**Descripción:** Actualizar campos de un plan existente.

**Body JSON:**
```json
{
    "lot_no": "ASSYLINE-251211-001",
    "plan_count": 1200,
    "status": "PLAN",
    "line": "SMT B",
    "wo_code": "WO-251211-0002",
    "turno": "NOCHE",
    "uph": 350,
    "ct": 9.5
}
```

---

### 4.4 Actualizar Estado de Plan
```
POST /api/plan/status
```
**Descripción:** Cambiar el estado de un plan con validaciones.

**Estados válidos:** `PENDIENTE`, `EN PROGRESO`, `PAUSADO`, `TERMINADO`, `CANCELADO`

**Body JSON:**
```json
{
    "lot_no": "ASSYLINE-251211-001",
    "status": "EN PROGRESO"
}
```

**Para PAUSADO (con motivo):**
```json
{
    "lot_no": "ASSYLINE-251211-001",
    "status": "PAUSADO",
    "pause_reason": "Falta de material"
}
```

**Para TERMINADO (con motivo si incompleto):**
```json
{
    "lot_no": "ASSYLINE-251211-001",
    "status": "TERMINADO",
    "end_reason": "Cambio de prioridad"
}
```

**Respuesta:**
```json
{
    "success": true,
    "lot_no": "ASSYLINE-251211-001",
    "new_status": "EN PROGRESO",
    "line": "SMT A"
}
```

**Error de conflicto (otra línea en progreso):**
```json
{
    "error": "Ya existe un plan EN PROGRESO en esta línea",
    "error_code": "LINE_CONFLICT",
    "line": "SMT A",
    "lot_no_en_progreso": "ASSYLINE-251211-002"
}
```

---

### 4.5 Guardar Secuencias
```
POST /api/plan/save-sequences
```
**Descripción:** Guardar el orden de secuencia de múltiples planes.

**Body JSON:**
```json
{
    "sequences": [
        {
            "lot_no": "ASSYLINE-251211-001",
            "group_no": 1,
            "sequence": 1,
            "plan_start_date": "2025-12-11",
            "planned_start": "07:30:00",
            "planned_end": "12:30:00",
            "effective_minutes": 300,
            "breaks_minutes": 30
        }
    ]
}
```

---

### 4.6 Planes Pendientes
```
GET /api/plan/pending
```
**Descripción:** Obtener planes con cantidad pendiente (plan_count > produced_count).

**Parámetros Query:**
- `start`: Fecha inicio
- `end`: Fecha fin

---

### 4.7 Reprogramar Planes
```
POST /api/plan/reschedule
```
**Descripción:** Crear nuevos planes con la cantidad pendiente de planes existentes.

**Body JSON:**
```json
{
    "lot_nos": ["ASSYLINE-251211-001", "ASSYLINE-251211-002"],
    "new_working_date": "2025-12-12"
}
```

**Respuesta:**
```json
{
    "success": true,
    "created": 2,
    "message": "2 nuevo(s) plan(es) creado(s) para 2025-12-12"
}
```

---

### 4.8 Exportar a Excel
```
POST /api/plan/export-excel
```
**Descripción:** Exportar planes a archivo Excel.

**Body JSON:**
```json
{
    "plans": [...]
}
```

---

### 4.9 Lista Plan Main
```
GET /api/plan-main/list
```
**Descripción:** Listar planes de producción main.

---

### 4.10 Buscar en RAW
```
GET /api/raw/search
```
**Descripción:** Buscar datos en tabla RAW por part_no o model.

**Parámetros Query:**
- `part_no`: Número de parte a buscar (requerido)

**Respuesta:**
```json
[
    {
        "part_no": "PN-12345",
        "model": "MODEL-001",
        "model_code": "MODEL-001",
        "project": "Proyecto X",
        "ct": "10.5",
        "uph": "300"
    }
]
```

---

## 5. APIs de Work Orders (WO) y Purchase Orders (PO)

### 5.1 Crear Work Order
```
POST /api/work_orders
```
**Descripción:** Crear nueva Work Order.

**Body JSON:**
```json
{
    "codigo_wo": "WO-251211-0001",
    "modelo": "PN-12345",
    "codigo_po": "PO-251211-0001",
    "fecha_operacion": "2025-12-11",
    "cantidad_planeada": 1000,
    "usuario_creador": "admin"
}
```

**Respuesta:**
```json
{
    "ok": true,
    "codigo_wo": "WO-251211-0001",
    "message": "Work Order creada exitosamente"
}
```

---

### 5.2 Generar Código WO Automático
```
GET /api/generar_codigo_wo
```
**Descripción:** Generar código WO automático con formato WO-YYMMDD-####.

**Respuesta:**
```json
{
    "ok": true,
    "codigo_wo": "WO-251211-0001"
}
```

---

### 5.3 Listar Work Orders
```
GET /api/work_orders
```
**Descripción:** Listar Work Orders con filtros opcionales.

**Parámetros Query:**
- `estado`: Filtrar por estado
- `codigo_wo`: Filtrar por código WO
- `modelo`: Filtrar por modelo
- `fecha_desde`: Fecha inicio
- `fecha_hasta`: Fecha fin
- `incluir_planificadas`: true/false (por defecto excluye PLANIFICADA)

**Respuesta:**
```json
{
    "ok": true,
    "work_orders": [
        {
            "codigo_wo": "WO-251211-0001",
            "codigo_po": "PO-251211-0001",
            "modelo": "PN-12345",
            "codigo_modelo": "PN-12345",
            "nombre_modelo": "Proyecto X",
            "cantidad_planeada": 1000,
            "fecha_operacion": "2025-12-11",
            "estado": "CREADA"
        }
    ]
}
```

---

### 5.4 Listar WOs (Ruta Alternativa)
```
GET /api/wo/listar
```
**Descripción:** Ruta alternativa para compatibilidad con frontend.

**Respuesta:**
```json
{
    "success": true,
    "data": [...]
}
```

---

### 5.5 Actualizar Estado WO
```
PUT /api/wo/<codigo>/estado
```
**Descripción:** Actualizar estado de una Work Order.

**Estados válidos:** `CREADA`, `PLANIFICADA`, `EN_PRODUCCION`, `CERRADA`

**Body JSON:**
```json
{
    "estado": "EN_PRODUCCION",
    "modificador": "admin"
}
```

---

### 5.6 Actualizar PO de WO
```
POST /api/wo/actualizar-po
```
**Descripción:** Actualizar el código PO de una Work Order.

**Body JSON:**
```json
{
    "codigo_wo": "WO-251211-0001",
    "codigo_po": "PO-251211-0002"
}
```

---

### 5.7 Actualizar WO Completa
```
POST /api/wo/actualizar
```
**Descripción:** Actualizar Work Order completa (modelo, cantidad, PO).

**Body JSON:**
```json
{
    "codigo_wo": "WO-251211-0001",
    "modelo": "PN-12346",
    "cantidad_planeada": 1200,
    "codigo_po": "PO-251211-0002"
}
```

---

### 5.8 Eliminar WO
```
DELETE /api/wo/eliminar
```
**Descripción:** Eliminar una Work Order.

**Body JSON:**
```json
{
    "codigo_wo": "WO-251211-0001"
}
```

---

### 5.9 Listar Purchase Orders
```
GET /api/po/listar
```
**Descripción:** Listar Purchase Orders desde tabla embarques.

**Parámetros Query:**
- `estado`: Filtrar por estado
- `fecha_desde`: Fecha inicio
- `fecha_hasta`: Fecha fin

**Respuesta:**
```json
{
    "success": true,
    "data": [
        {
            "codigo_po": "PO-251211-0001",
            "nombre_po": "Orden ABC",
            "fecha_registro": "2025-12-11",
            "modelo": "PN-12345",
            "nombre_modelo": "Proyecto X",
            "cliente": "Cliente A",
            "proveedor": "Proveedor B",
            "total_cantidad_entregada": 1000,
            "estado": "PLAN"
        }
    ],
    "total": 1
}
```

---

### 5.10 Crear Purchase Order
```
POST /api/po/crear
```
**Descripción:** Crear nueva Purchase Order.

**Body JSON:**
```json
{
    "nombre_po": "Orden ABC",
    "fecha_registro": "2025-12-11",
    "modelo": "PN-12345",
    "cliente": "Cliente A",
    "proveedor": "Proveedor B",
    "total_cantidad_entregada": 1000,
    "fecha_entrega": "2025-12-20",
    "estado": "PLAN"
}
```

---

### 5.11 Importar Work Orders
```
POST /api/work-orders/import
```
**Descripción:** Importar múltiples Work Orders desde archivo.

---

## 6. APIs de Materiales e Inventario

### 6.1 Guardar Material
```
POST /guardar_material
```
**Descripción:** Crear o actualizar un material.

**Body JSON:**
```json
{
    "numero_parte": "PN-12345",
    "descripcion": "Descripción del material",
    "unidad_medida": "PZ",
    "tipo_material": "COMPONENTE"
}
```

---

### 6.2 Listar Materiales
```
GET /listar_materiales
```
**Descripción:** Obtener lista de todos los materiales.

---

### 6.3 Obtener Códigos de Material
```
GET /obtener_codigos_material
```
**Descripción:** Obtener lista de códigos/números de parte de materiales.

---

### 6.4 Actualizar Campo de Material
```
POST /actualizar_campo_material
```
**Descripción:** Actualizar un campo específico de un material.

---

### 6.5 Actualizar Material Completo
```
POST /actualizar_material_completo
```
**Descripción:** Actualizar todos los campos de un material.

---

### 6.6 Detalle de Lotes de Inventario
```
POST /api/inventario/lotes_detalle
```
**Descripción:** Obtener detalle de lotes de inventario.

---

### 6.7 Inventario por Modelo
```
GET /api/inventario/modelo/<codigo_modelo>
```
**Descripción:** Obtener inventario filtrado por modelo específico.

---

### 6.8 Importar Excel de Materiales
```
POST /importar_excel
```
**Descripción:** Importar materiales desde archivo Excel.

---

### 6.9 Exportar Excel de Materiales
```
GET /exportar_excel
```
**Descripción:** Exportar materiales a archivo Excel.

---

## 7. APIs de BOM (Bill of Materials)

### 7.1 Importar Excel BOM
```
POST /importar_excel_bom
```
**Descripción:** Importar BOM desde archivo Excel.

---

### 7.2 Listar Modelos BOM
```
GET /listar_modelos_bom
```
**Descripción:** Obtener lista de modelos con BOM definido.

---

### 7.3 Listar BOM por Modelo
```
POST /listar_bom
```
**Descripción:** Obtener BOM completo de un modelo.

**Body JSON:**
```json
{
    "modelo": "MODEL-001"
}
```

---

### 7.4 Consultar BOM
```
GET /consultar_bom
```
**Descripción:** Consultar BOM con parámetros de búsqueda.

---

### 7.5 Buscar Material por Número de Parte
```
GET /buscar_material_por_numero_parte
```
**Descripción:** Buscar información de material en BOM por número de parte.

---

### 7.6 Exportar Excel BOM
```
GET /exportar_excel_bom
```
**Descripción:** Exportar BOM a archivo Excel.

---

### 7.7 Actualizar BOM
```
POST /api/bom/update
```
**Descripción:** Actualizar componentes del BOM.

---

### 7.8 Actualizar Posiciones ASSY
```
POST /api/bom/update-posiciones-assy
```
**Descripción:** Actualizar posiciones de ensamble en BOM.

---

## 8. APIs de SMD/SMT

### 8.1 Ver Inventario de Rollos SMD
```
GET /smd/inventario
```
**Descripción:** Página HTML para visualizar inventario de rollos SMD.

---

### 8.2 Obtener Inventario de Rollos
```
GET /api/smd/inventario/rollos
```
**Descripción:** API para obtener inventario actual de rollos SMD.

**Parámetros Query:**
- `estado`: Filtrar por estado
- `numero_parte`: Filtrar por número de parte
- `linea`: Filtrar por línea
- `maquina`: Filtrar por máquina
- `fecha_desde`: Fecha inicio
- `fecha_hasta`: Fecha fin

**Respuesta:**
```json
{
    "success": true,
    "data": [...],
    "stats": {
        "total_rollos": 100,
        "activos": 80,
        "en_uso": 15,
        "agotados": 5,
        "asignados": 20,
        "cantidad_total_disponible": 50000
    },
    "total": 100,
    "message": "Encontrados 100 rollos"
}
```

---

### 8.3 Detalle de Rollo
```
GET /api/smd/inventario/rollo/<rollo_id>
```
**Descripción:** Obtener detalle completo de un rollo con su historial.

---

### 8.4 Marcar Rollo Agotado
```
POST /api/smd/inventario/rollo/<rollo_id>/marcar_agotado
```
**Descripción:** Marcar un rollo como agotado manualmente.

**Body JSON:**
```json
{
    "observaciones": "Motivo del agotamiento",
    "usuario": "admin"
}
```

---

### 8.5 Asignar Rollo a Mounter
```
POST /api/smd/inventario/rollo/<rollo_id>/asignar_mounter
```
**Descripción:** Asignar un rollo a una máquina mounter específica.

**Body JSON:**
```json
{
    "linea": "SMT A",
    "maquina": "Mounter 1",
    "slot": "S01",
    "usuario": "operador1"
}
```

---

### 8.6 Estadísticas de Inventario SMD
```
GET /api/smd/inventario/stats
```
**Descripción:** Obtener estadísticas generales del inventario SMD.

---

### 8.7 Sincronizar Inventario
```
POST /api/smd/inventario/sincronizar
```
**Descripción:** Sincronizar inventario SMD con movimientos del almacén.

**Body JSON:**
```json
{
    "horas_atras": 24
}
```

---

### 8.8 Historial SMT Data
```
GET /api/historial_smt_data
```
**Descripción:** Obtener datos de historial de cambio de material SMT.

**Parámetros Query:**
- `fecha_desde`: Fecha inicio (YYYY-MM-DD)
- `fecha_hasta`: Fecha fin (YYYY-MM-DD)
- `limit`: Límite de registros (default 1000)

**Respuesta:**
```json
{
    "status": "success",
    "data": [
        {
            "SlotNo": "S01",
            "Result": "OK",
            "LOTNO": "LOT123",
            "Barcode": "BC123456",
            "PartName": "Resistor 10K",
            "linea": "SMT A",
            "maquina": "Mounter 1",
            "fecha_formateada": "2025-12-11",
            "hora_formateada": "10:30:00"
        }
    ],
    "total": 100,
    "message": "Se encontraron 100 registros"
}
```

---

### 8.9 Estadísticas SMT
```
GET /api/smt_stats
```
**Descripción:** Estadísticas básicas de SMT.

---

### 8.10 Historial SMT (rutas smt_routes.py)
```
GET /api/smt/historial/data
```
**Descripción:** Obtener datos del historial con filtros.

**Parámetros Query:**
- `folder`: Carpeta/línea
- `part_name`: Nombre de parte
- `result`: Resultado
- `date_from`: Fecha desde
- `date_to`: Fecha hasta

---

### 8.11 Exportar Historial SMT
```
GET /api/smt/historial/export
```
**Descripción:** Exportar historial SMT para descarga.

---

### 8.12 Subir CSV SMT
```
POST /api/smt/historial/upload
```
**Descripción:** Subir archivo CSV a la base de datos.

**Form Data:**
- `csvFile`: Archivo CSV
- `lineNumber`: Número de línea (opcional)
- `mounterNumber`: Número de mounter (opcional)

---

### 8.13 Carpetas SMT Disponibles
```
GET /api/smt/folders
```
**Descripción:** Obtener lista de carpetas/líneas disponibles.

---

### 8.14 Estadísticas SMT General
```
GET /api/smt/stats
```
**Descripción:** Estadísticas generales del sistema SMT.

---

## 9. APIs de AOI (Automatic Optical Inspection)

### 9.1 Turno Actual
```
GET /api/shift-now
```
**Descripción:** Obtener información del turno actual según hora de México.

**Respuesta:**
```json
{
    "now": "2025-12-11T10:30:00",
    "shift": "DIA",
    "shift_date": "2025-12-11"
}
```

**Clasificación de turnos:**
- **DÍA:** 7:30 - 17:30
- **TIEMPO_EXTRA:** 17:30 - 22:00
- **NOCHE:** 22:30 - 7:00

---

### 9.2 Datos en Tiempo Real
```
GET /api/realtime
```
**Descripción:** Obtener tabla de producción AOI del turno actual en tiempo real.

**Respuesta:**
```json
{
    "shift_date": "2025-12-11",
    "shift": "DIA",
    "rows": [
        {
            "linea": "A",
            "modelo": "MODEL-001",
            "lado": "TOP",
            "cantidad": 500
        }
    ]
}
```

---

### 9.3 Datos por Día
```
GET /api/day
```
**Descripción:** Obtener datos AOI agrupados por día lógico.

**Parámetros Query:**
- `date`: Fecha a consultar (YYYY-MM-DD)

**Respuesta:**
```json
{
    "rows": [
        {
            "fecha": "2025-12-11",
            "turno": "DIA",
            "linea": "A",
            "modelo": "MODEL-001",
            "lado": "TOP",
            "cantidad": 500
        }
    ]
}
```

---

## 10. APIs de Modelos RAW

### 10.1 Listar Modelos RAW
```
GET /api/raw/modelos
```
**Descripción:** Listar modelos desde la tabla RAW (columna part_no).

**Respuesta:**
```json
{
    "success": true,
    "data": ["PN-12345", "PN-12346", "PN-12347"],
    "count": 3
}
```

---

### 10.2 Obtener CT y UPH
```
GET /api/raw/ct_uph
```
**Descripción:** Obtener Cycle Time (CT) y Units Per Hour (UPH) desde raw_smd.

**Parámetros Query:**
- `part_no`: Número de parte (requerido)
- `linea`: Línea específica (opcional)

**Respuesta:**
```json
{
    "success": true,
    "part_no": "PN-12345",
    "model": "MODEL-001",
    "ct": 10.5,
    "uph": 300
}
```

---

## 11. APIs de Control de Almacén

### 11.1 Control de Almacén
```
GET /control_almacen
```
**Descripción:** Página de control de almacén.

---

### 11.2 Control de Salida
```
GET /control_salida
```
**Descripción:** Página de control de salida de material.

---

### 11.3 Guardar Control de Almacén
```
POST /guardar_control_almacen
```
**Descripción:** Guardar registro de control de almacén.

---

### 11.4 Obtener Secuencial de Lote Interno
```
POST /obtener_secuencial_lote_interno
```
**Descripción:** Obtener siguiente número secuencial para lote interno.

---

### 11.5 Consultar Control de Almacén
```
GET /consultar_control_almacen
```
**Descripción:** Consultar registros de control de almacén.

---

### 11.6 Actualizar Control de Almacén
```
POST /actualizar_control_almacen
```
**Descripción:** Actualizar registro de control de almacén.

---

### 11.7 Guardar Cliente Seleccionado
```
POST /guardar_cliente_seleccionado
```
**Descripción:** Guardar cliente seleccionado para el usuario.

---

### 11.8 Cargar Cliente Seleccionado
```
GET /cargar_cliente_seleccionado
```
**Descripción:** Cargar cliente previamente seleccionado.

---

### 11.9 Actualizar Estado de Desecho
```
POST /actualizar_estado_desecho_almacen
```
**Descripción:** Actualizar estado de desecho de material.

---

### 11.10 Obtener Siguiente Secuencial
```
GET /obtener_siguiente_secuencial
```
**Descripción:** Obtener siguiente número secuencial.

---

### 11.11 Guardar Entrada Aéreo
```
POST /guardar_entrada_aereo
```
**Descripción:** Registrar entrada de material por envío aéreo.

---

### 11.12 Listar Entradas Aéreo
```
GET /listar_entradas_aereo
```
**Descripción:** Listar entradas de material por envío aéreo.

---

## 12. Rutas de Vistas (Frontend)

### Páginas Principales

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET | Redirecciona a `/inicio` |
| `/inicio` | GET | Landing page / Hub de aplicaciones |
| `/login` | GET/POST | Página de login |
| `/logout` | GET | Cerrar sesión |
| `/ILSAN-ELECTRONICS` | GET | Dashboard principal de materiales |
| `/dashboard` | GET | Alias para MaterialTemplate |
| `/calendario` | GET | Calendario de producción |
| `/sistemas` | GET | Redirige a inicio |
| `/soporte` | GET | Página de soporte técnico |
| `/documentacion` | GET | Página de documentación |

### Control de Producción

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/plan-main` | GET | Página de planeación ASSY |
| `/control-main` | GET | Control de operación línea Main |
| `/control_produccion/control_embarque` | GET | Control de embarque |
| `/control_produccion/crear_plan` | GET | Crear plan de producción |
| `/control_produccion/plan_smt` | GET | Plan SMT |
| `/control_proceso/control_produccion_smt` | GET | Control de producción SMT |

### Rutas AJAX (Carga dinámica de módulos)

| Ruta | Descripción |
|------|-------------|
| `/plan-main-assy-ajax` | Módulo planeación ASSY |
| `/control-operacion-linea-main-ajax` | Control operación línea Main |
| `/control-bom-ajax` | Control de BOM |
| `/crear-plan-micom-ajax` | Crear plan MICOM |
| `/control-operacion-linea-smt-ajax` | Control operación SMT |
| `/control-impresion-identificacion-smt-ajax` | Impresión identificación SMT |
| `/control-registro-identificacion-smt-ajax` | Registro identificación SMT |
| `/historial-operacion-proceso-ajax` | Historial operación por proceso |
| `/bom-management-process-ajax` | BOM Management por proceso |
| `/reporte-diario-inspeccion-smt-ajax` | Reporte diario inspección SMT |
| `/control-diario-inspeccion-smt-ajax` | Control diario inspección SMT |
| `/control-unidad-empaque-modelo-ajax` | Control unidad empaque |
| `/packaging-register-management-ajax` | Registro empaque |
| `/search-packaging-history-ajax` | Historial empaque |
| `/shipping-register-management-ajax` | Registro embarque |
| `/search-shipping-history-ajax` | Historial embarque |
| `/registro-movimiento-identificacion-ajax` | Movimiento identificación |
| `/control-otras-identificaciones-ajax` | Control otras identificaciones |
| `/control-movimiento-ns-producto-ajax` | Movimiento N/S producto |
| `/model-sn-management-ajax` | Model S/N Management |
| `/control-scrap-ajax` | Control de Scrap |
| `/line-material-status-ajax` | Estado material de línea |
| `/control-mask-metal-ajax` | Control mask metal |
| `/control-squeegee-ajax` | Control squeegee |
| `/control-caja-mask-metal-ajax` | Control caja mask metal |

### Listas (Menús de navegación)

| Ruta | Descripción |
|------|-------------|
| `/listas/informacion_basica` | Lista información básica |
| `/listas/control_material` | Lista control de material |
| `/listas/control_produccion` | Lista control de producción |

### Información Básica

| Ruta | Descripción |
|------|-------------|
| `/informacion_basica/control_de_material` | Control de material |
| `/informacion_basica/control_de_bom` | Control de BOM |

---

## 🔒 Autenticación y Autorización

### Decoradores de Seguridad

El sistema utiliza varios decoradores para controlar el acceso:

```python
@login_requerido  # Requiere sesión activa
@auth_system.login_requerido_avanzado  # Requiere sesión con verificación extendida
@auth_system.requiere_permiso('modulo', 'accion')  # Requiere permiso específico
@requiere_permiso_dropdown(pagina, seccion, boton)  # Requiere permiso de botón específico
```

### Estructura de Permisos de Botones

Los permisos se organizan jerárquicamente:

```
PAGINA > SECCION > BOTON
```

Ejemplo:
```
LISTA_DE_MATERIALES > Control de material > Control de material de almacén
```

---

## 📊 Códigos de Estado HTTP

| Código | Significado |
|--------|-------------|
| 200 | OK - Solicitud exitosa |
| 201 | Created - Recurso creado exitosamente |
| 400 | Bad Request - Parámetros inválidos |
| 401 | Unauthorized - No autenticado |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no encontrado |
| 409 | Conflict - Conflicto (ej. duplicado) |
| 500 | Internal Server Error - Error del servidor |

---

## 🔧 Configuración de Base de Datos

El sistema utiliza MySQL como base de datos principal. La configuración se obtiene de variables de entorno:

```python
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE'),
    'charset': 'utf8mb4'
}
```

---

## 📝 Notas Importantes

1. **Zona Horaria:** El sistema opera en zona horaria de México (GMT-6).

2. **Formato de Fechas:** Se utiliza formato ISO 8601 (YYYY-MM-DD) para fechas.

3. **Formato de Códigos:**
   - WO: `WO-YYMMDD-####` (ej. WO-251211-0001)
   - PO: `PO-YYMMDD-####` (ej. PO-251211-0001)
   - LOT: `ASSYLINE-YYMMDD-###` (ej. ASSYLINE-251211-001)

4. **Turnos de Producción:**
   - DIA (routing=1): 7:30 - 17:30
   - TIEMPO_EXTRA (routing=2): 17:30 - 22:00
   - NOCHE (routing=3): 22:30 - 7:00

---

*Documento generado para el Sistema MES ILSAN Electronics*
