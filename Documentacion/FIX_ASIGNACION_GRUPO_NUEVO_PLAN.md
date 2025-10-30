# 🔧 FIX: Asignación de Grupo al Crear Nuevo Plan

## 🐛 Problema Identificado

### Síntomas
- Usuario creaba plan para línea M4 seleccionando "Grupo 4"
- El plan aparecía en "Grupo 1" en lugar de "Grupo 4"
- La funcionalidad de selección de grupo no funcionaba correctamente

### Causa Raíz
El flujo original tenía una falla de diseño:

```javascript
// FLUJO INCORRECTO:
1. Usuario selecciona "Grupo 4" en el modal
2. Frontend envía plan al backend SIN group_no
3. Backend crea plan sin group_no en la BD
4. Frontend llama loadPlans()
5. loadPlans() ejecuta renderTableWithVisualGroups()
6. renderTableWithVisualGroups() REDISTRIBUYE todos los planes automáticamente
   (usando algoritmo round-robin que ignora group_no porque es NULL)
7. Frontend intenta mover el plan con assignPlanToGroup()
8. ❌ YA ES TARDE: el plan ya fue distribuido automáticamente
```

**Problema principal**: El plan se creaba en la BD sin `group_no`, por lo que al recargar, el algoritmo automático lo redistribuía antes de que el frontend pudiera moverlo.

---

## ✅ Solución Implementada

### Cambio de Estrategia
En lugar de intentar mover el plan después de crearlo, **guardamos el grupo directamente en la base de datos** al momento de crear el plan.

### Modificaciones Realizadas

#### 1. Backend (`app/routes.py` - líneas 808-833)

**Antes:**
```python
# Insert sin group_no
sql = "INSERT INTO plan_main (lot_no, wo_code, ..., status, created_at) ..."
params = (lot_no, wo_code, ..., 'PLAN')
```

**Después:**
```python
# Obtener group_no del request
group_no = data.get('group_no')
sequence = None

# Si se especifica grupo, calcular siguiente sequence
if group_no is not None:
    seq_query = "SELECT MAX(sequence) as max_seq FROM plan_main WHERE group_no = %s"
    seq_result = execute_query(seq_query, (int(group_no),), fetch='one')
    max_seq = seq_result.get('max_seq') if seq_result else None
    sequence = (max_seq + 1) if max_seq is not None else 1

# Insert con group_no y sequence
if group_no is not None and sequence is not None:
    sql = """INSERT INTO plan_main 
             (lot_no, wo_code, ..., group_no, sequence, created_at) 
             VALUES (%s,%s,...,%s,%s,NOW())"""
    params = (lot_no, wo_code, ..., int(group_no), sequence)
```

**Lógica:**
- Si el usuario selecciona un grupo (group_no != null):
  1. Buscar el `sequence` más alto del grupo
  2. Asignar `sequence = max_seq + 1` (o 1 si es el primer plan del grupo)
  3. Guardar el plan con `group_no` y `sequence` en la BD
- Si el usuario selecciona "Automático" (group_no = null):
  - Crear el plan sin `group_no` ni `sequence`
  - El algoritmo automático lo distribuirá al recargar

---

#### 2. Frontend (`app/static/js/plan.js` - líneas 902-933)

**Antes:**
```javascript
async function handleNewPlanSubmit(form) {
  const data = Object.fromEntries(new FormData(form));
  
  // Extraer grupo seleccionado
  const targetGroup = data.target_group ? parseInt(data.target_group) : null;
  delete data.target_group; // ❌ NO enviar al backend

  // Crear plan (sin group_no)
  const response = await axios.post("/api/plan", data);
  
  // Recargar planes
  await loadPlans(); // ⚠️ Esto redistribuye todo automáticamente
  
  // Intentar mover el plan (ya es tarde)
  if (targetGroup !== null && newPlan && newPlan.lot_no) {
    setTimeout(() => {
      assignPlanToGroup(newPlan.lot_no, targetGroup - 1);
    }, 500);
  }
}
```

**Después:**
```javascript
async function handleNewPlanSubmit(form) {
  const data = Object.fromEntries(new FormData(form));
  
  // ✅ Renombrar target_group a group_no para el backend
  if (data.target_group && data.target_group !== '0') {
    data.group_no = parseInt(data.target_group);
  }
  delete data.target_group; // Eliminar campo temporal
  
  // Crear plan (CON group_no)
  const response = await axios.post("/api/plan", data);
  
  // Recargar planes - el plan ya viene con su grupo desde la BD
  await loadPlans();
  
  // ✅ Ya no necesitamos mover manualmente
  // renderTableWithVisualGroups() respeta el group_no del backend
}
```

**Cambios clave:**
1. `target_group` se convierte en `group_no` antes de enviar al backend
2. Se elimina la lógica de `assignPlanToGroup()` post-creación
3. Se elimina el `setTimeout()` de 500ms (ya no es necesario)
4. El plan se recarga con su `group_no` correcto desde la BD

---

## 🔄 Flujo Correcto Ahora

```
1. Usuario selecciona "Grupo 4" en el modal
2. Frontend convierte target_group=4 a group_no=4
3. Backend recibe group_no=4
4. Backend calcula sequence = MAX(sequence) + 1 del Grupo 4
5. Backend guarda plan con group_no=4 y sequence=N en la BD
6. Frontend llama loadPlans()
7. loadPlans() carga TODOS los planes (incluyendo el nuevo con group_no=4)
8. renderTableWithVisualGroups() detecta que los planes tienen group_no
9. renderTableWithVisualGroups() usa la rama hasGroupData = true
10. Cada plan se asigna a su grupo según plan.group_no desde la BD
11. ✅ El plan aparece correctamente en el Grupo 4
```

---

## 📊 Verificación del Código

### Frontend respeta `group_no` de la BD

En `renderTableWithVisualGroups()` (líneas 1740-1780):

```javascript
// Verificar si los datos tienen group_no y sequence
const hasGroupData = data.some(plan => plan.group_no != null && plan.sequence != null);

if (hasGroupData) {
  // Asignar planes basándose en group_no de la BD
  data.forEach((plan) => {
    if (plan.group_no != null && plan.sequence != null) {
      const groupIndex = plan.group_no - 1; // 1-indexed → 0-indexed
      if (groupIndex >= 0 && groupIndex < groupCount) {
        visualGroups.groups[groupIndex].plans.push(plan);
        visualGroups.planAssignments.set(plan.lot_no, groupIndex);
      }
    }
  });
  
  // Ordenar por sequence dentro de cada grupo
  visualGroups.groups.forEach(group => {
    group.plans.sort((a, b) => (a.sequence || 999) - (b.sequence || 999));
  });
}
```

**Clave:** Si los planes tienen `group_no` y `sequence` desde la BD, se respetan esos valores en lugar de usar el algoritmo automático.

---

## 🎯 Ventajas de esta Solución

1. **Persistencia**: El grupo se guarda en la BD, no solo en memoria
2. **Consistencia**: Al recargar la página, el plan mantiene su grupo
3. **Simplicidad**: No necesita lógica frontend compleja de timing
4. **Performance**: Elimina el `setTimeout()` de 500ms
5. **Mantenibilidad**: Flujo más claro y predecible
6. **Escalabilidad**: Si hay múltiples usuarios, todos ven el mismo grupo

---

## 🧪 Prueba del Fix

### Antes del Fix:
```
1. Crear plan para M4 → Seleccionar "Grupo 4"
2. Resultado: Plan aparece en Grupo 1 ❌
```

### Después del Fix:
```
1. Crear plan para M4 → Seleccionar "Grupo 4"
2. Resultado: Plan aparece en Grupo 4 ✅
3. Recargar página → Plan sigue en Grupo 4 ✅
```

---

## 📝 Notas Técnicas

### Opción "Automático"
- Si el usuario selecciona "Automático (al final)" (value="0")
- El frontend NO envía `group_no` al backend
- El backend crea el plan sin `group_no` ni `sequence`
- Al recargar, el algoritmo round-robin lo distribuye automáticamente

### Cálculo de `sequence`
- Se consulta `MAX(sequence)` del grupo seleccionado
- Si el grupo está vacío: sequence = 1
- Si tiene planes: sequence = max_seq + 1
- Esto asegura que el nuevo plan se agregue al final del grupo

### Compatibilidad con Drag & Drop
- El sistema de arrastrar y soltar sigue funcionando
- Cuando se mueve un plan manualmente, se actualiza `group_no` y `sequence` en la BD
- Ambos sistemas (selector + drag&drop) son compatibles

---

## 🔍 Archivos Modificados

1. **Backend**: `app/routes.py` (líneas 808-833)
   - Endpoint `/api/plan` (POST)
   - Acepta `group_no` opcional
   - Calcula `sequence` automáticamente
   - Guarda ambos campos en la BD

2. **Frontend**: `app/static/js/plan.js` (líneas 902-933)
   - Función `handleNewPlanSubmit()`
   - Convierte `target_group` a `group_no`
   - Envía `group_no` al backend
   - Elimina lógica post-creación

---

## ✅ Resultado Final

El bug está completamente resuelto. Ahora cuando un usuario crea un plan y selecciona un grupo específico, el plan aparece correctamente en ese grupo de forma inmediata y persistente.
