# 📦 SISTEMA DE INVENTARIO GENERAL

## 🎯 OBJETIVO
Mantener un inventario unificado por **número de parte** que se actualice automáticamente con entradas y salidas, preservando el historial completo.

## 🗄️ ESTRUCTURA DE DATOS

### 1. **control_material_almacen** (ENTRADAS)
- ✅ Se mantiene **SIN MODIFICAR**
- ✅ Historial completo de todas las entradas
- ✅ **NO se elimina** ni modifica al hacer salidas

### 2. **control_material_salida** (SALIDAS)  
- ✅ Se mantiene **SIN MODIFICAR**
- ✅ Historial completo de todas las salidas
- ✅ Registra cada movimiento de salida

### 3. **inventario_general** (NUEVO - UNIFICADO)
```sql
CREATE TABLE inventario_general (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_parte TEXT UNIQUE NOT NULL,        -- Clave de unificación
    codigo_material TEXT,                     -- Último código registrado  
    propiedad_material TEXT,                  -- Última propiedad registrada
    especificacion TEXT,                      -- Última especificación registrada
    cantidad_total REAL DEFAULT 0,           -- = cantidad_entradas - cantidad_salidas
    cantidad_entradas REAL DEFAULT 0,        -- Suma de todas las entradas
    cantidad_salidas REAL DEFAULT 0,         -- Suma de todas las salidas
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🔄 FLUJO DE OPERACIONES

### ➕ **ENTRADA DE MATERIAL**
1. Se registra en `control_material_almacen` (como siempre)
2. **NUEVO:** Se actualiza `inventario_general`:
   - Si existe el número de parte: suma a `cantidad_entradas` y `cantidad_total`
   - Si no existe: crea nuevo registro

### ➖ **SALIDA DE MATERIAL**  
1. Se registra en `control_material_salida` (como siempre)
2. **NUEVO:** Ya NO se modifica `control_material_almacen`
3. **NUEVO:** Se actualiza `inventario_general`:
   - Suma a `cantidad_salidas` 
   - Resta de `cantidad_total`

## 🎯 BENEFICIOS

### ✅ **HISTORIALES COMPLETOS**
- **Entradas:** Historial completo y permanente
- **Salidas:** Historial completo y permanente  
- **Inventario:** Totales unificados por número de parte

### ✅ **UNIFICACIÓN INTELIGENTE**
- Múltiples lotes del mismo número de parte se unifican
- Ejemplo: 
  - Lote A: 0RH5602C622/202507100001 → 100 unidades
  - Lote B: 0RH5602C622/202507100002 → 50 unidades
  - **Inventario general:** 0RH5602C622 → 150 unidades total

### ✅ **DATOS PRESERVADOS**
- No se pierde información histórica
- Auditoría completa de movimientos
- Trazabilidad total

## 🚀 USO DEL SISTEMA

### **Funciones Disponibles:**

#### 1. **Automáticas** (se ejecutan automáticamente):
```python
# Al registrar entrada
actualizar_inventario_general_entrada(numero_parte, codigo_material, propiedad, especificacion, cantidad)

# Al registrar salida  
actualizar_inventario_general_salida(numero_parte, cantidad_salida)
```

#### 2. **Manuales** (para administración):
```python
# Recalcular todo desde cero
recalcular_inventario_general()

# Obtener inventario completo
obtener_inventario_general()
```

### **Endpoints Disponibles:**
```
POST /recalcular_inventario_general  - Recalcular inventario
GET  /obtener_inventario_general     - Obtener inventario completo
```

## 🔧 INICIALIZACIÓN

### **Primera vez:**
```bash
cd /path/to/ISEMM_MES
python inicializar_inventario.py
```

Este script:
1. Crea la tabla `inventario_general` si no existe
2. Calcula totales desde datos existentes
3. Unifica por número de parte
4. Muestra resumen del inventario creado

## 💡 NOTAS IMPORTANTES

### **Para el Usuario:**
- ✅ El sistema funciona igual desde la interfaz
- ✅ Los historiales están completos y seguros
- ✅ El inventario se unifica automáticamente por número de parte
- ✅ **NO se pierden datos** de entradas al hacer salidas

### **Para el Desarrollador:**
- ✅ La tabla `inventario_general` es invisible para el usuario final
- ✅ Se actualiza automáticamente en segundo plano
- ✅ Diseñada para consultas futuras de inventario unificado
- ✅ Puede usarse después para reportes y dashboards

## 🔍 EJEMPLO DE USO

### **Entrada:**
```
Número de parte: 0RH5602C622
Cantidad: 100
→ inventario_general.cantidad_entradas += 100
→ inventario_general.cantidad_total = entradas - salidas
```

### **Salida:**  
```
Número de parte: 0RH5602C622  
Cantidad: 30
→ inventario_general.cantidad_salidas += 30
→ inventario_general.cantidad_total = entradas - salidas
```

### **Resultado:**
```
Número de parte: 0RH5602C622
- Entradas totales: 100
- Salidas totales: 30  
- Stock actual: 70
```

## 🎯 PRÓXIMOS PASOS

Esta tabla está lista para:
- 📊 **Reportes de inventario unificado**
- 📈 **Dashboards de stock**
- 🔍 **Consultas rápidas por número de parte**
- 📋 **Alertas de stock bajo**
- 📊 **Análisis de rotación de inventario**
