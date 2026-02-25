# Solución: Diferencia de Horas entre Frontend y MySQL

## 📋 Problema Identificado

Las horas mostradas en el frontend (tabla Plan Main) eran **diferentes** a las horas guardadas en MySQL.

**Ejemplo:**
- Frontend muestra: `07:30` (hora de inicio)
- MySQL guarda: `13:30` (diferencia de 6 horas)

---

##  Causa Raíz

El problema estaba en la función `saveGroupSequences()` en el archivo `plan.js` (líneas ~3568-3590).

### Flujo Incorrecto (ANTES):

```javascript
//  CÓDIGO INCORRECTO
const dateTime = new Date(year, month - 1, day, hours, minutes, 0);
plannedStart = dateTime.toISOString().slice(0, 19).replace('T', ' ');
```

**¿Por qué era incorrecto?**

1. `new Date(year, month-1, day, hours, minutes, 0)` crea una fecha en la **zona horaria LOCAL del navegador**
2. `.toISOString()` convierte la fecha a **UTC (Tiempo Universal Coordinado)**
3. Si el navegador está en **GMT-6** (México), `.toISOString()` **suma 6 horas** para convertir a UTC
4. MySQL recibe y guarda la hora **en UTC** sin conversión adicional

**Ejemplo del flujo:**
```
Hora calculada:     07:30 (Nuevo León)
↓
new Date():         2025-10-22 07:30:00 (Local GMT-6)
↓
.toISOString():     2025-10-22T13:30:00.000Z (UTC, +6 horas)
↓
MySQL guarda:       2025-10-22 13:30:00 (como DATETIME)
↓
Frontend lee:       13:30  (diferente a 07:30 mostrado)
```

---

##  Solución Implementada

### Código Corregido (DESPUÉS):

```javascript
//  CÓDIGO CORRECTO
const todayStr = getTodayInNuevoLeon(); // '2025-10-22'
const [hours, minutes] = startTime.split(':');
plannedStart = `${todayStr} ${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00`;
```

**¿Por qué funciona correctamente?**

1. **NO usa `new Date()`** - evita conversiones automáticas de zona horaria
2. **NO usa `.toISOString()`** - evita conversión a UTC
3. **Construye el string directamente** - formato `YYYY-MM-DD HH:MM:SS`
4. MySQL recibe la hora **exacta** sin conversiones adicionales

**Ejemplo del flujo corregido:**
```
Hora calculada:     07:30 (Nuevo León)
↓
Construcción directa:   2025-10-22 07:30:00
↓
MySQL guarda:       2025-10-22 07:30:00 
↓
Frontend lee:       07:30  (coincide perfectamente)
```

---

##  Archivos Modificados

### `app/static/js/plan.js`

**Función:** `saveGroupSequences()`  
**Líneas:** ~3554-3576

**Cambios:**

1. **planned_start** - Conversión de `startTime` (HH:MM) a DATETIME
   -  Antes: `dateTime.toISOString().slice(0, 19).replace('T', ' ')`
   -  Ahora: `` `${todayStr} ${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00` ``

2. **planned_end** - Conversión de `endTime` (HH:MM) a DATETIME
   -  Antes: `dateTime.toISOString().slice(0, 19).replace('T', ' ')`
   -  Ahora: `` `${todayStr} ${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00` ``

---

## 🎯 Beneficios de la Solución

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Conversión UTC** | Sí (suma 6 horas) | No |
| **Complejidad** | Alta (usa Date objects) | Baja (string directo) |
| **Consistencia** |  Frontend ≠ MySQL |  Frontend = MySQL |
| **Zona horaria** | Depende del navegador | Siempre Nuevo León |
| **Legibilidad** | Difícil de debuggear | Fácil de entender |

---

##  Verificación de la Corrección

### Pasos para verificar:

1. **Recargar la página** `Control_produccion_assy.html`
2. **Mover planes** usando drag & drop o auto-acomodo
3. **Observar las horas** en las columnas "Inicio" y "Fin"
4. **Guardar el orden** haciendo clic en el botón " Guardar Orden"
5. **Verificar en MySQL** que las horas coincidan exactamente

### Query SQL para verificar:

```sql
SELECT 
  lot_no,
  planned_start,
  planned_end,
  TIME(planned_start) AS hora_inicio,
  TIME(planned_end) AS hora_fin
FROM plan_main
WHERE working_date = CURDATE()
ORDER BY group_no, sequence;
```

**Resultado esperado:**
- `hora_inicio` debería mostrar `07:30:00` (no `13:30:00`)
- `hora_fin` debería coincidir con la hora del frontend

---

## 🛡️ Prevención de Problemas Similares

### ⚠️ Regla General: **NO usar `.toISOString()` para fechas locales**

**Cuándo usar `.toISOString()`:**
-  Para timestamps UTC (logs, auditoría)
-  Para comunicación con APIs internacionales
-  Para almacenar fechas en formato ISO 8601

**Cuándo NO usar `.toISOString()`:**
-  Para fechas/horas de eventos locales (producción, turnos)
-  Para campos DATETIME que representan zona horaria específica
-  Cuando la hora mostrada debe coincidir con la guardada

### 💡 Mejores Prácticas:

1. **Para DATETIME local:**
   ```javascript
   //  CORRECTO
   const dateStr = `${year}-${month}-${day} ${hours}:${minutes}:00`;
   ```

2. **Para Date objects locales:**
   ```javascript
   //  CORRECTO - sin conversión UTC
   const localDate = new Date(year, month-1, day, hours, minutes, 0);
   const dateStr = localDate.toLocaleString('sv-SE'); // Formato: YYYY-MM-DD HH:MM:SS
   ```

3. **Para timestamps UTC:**
   ```javascript
   //  CORRECTO - cuando SÍ necesitas UTC
   const utcDate = new Date().toISOString(); // '2025-10-22T13:30:00.000Z'
   ```

---

##  Comparación de Métodos

| Método | Zona Horaria | Conversión UTC | Uso Recomendado |
|--------|--------------|----------------|-----------------|
| `.toISOString()` | UTC | Sí (automática) | APIs, logs globales |
| `.toLocaleString()` | Local | No | Mostrar al usuario |
| String template | Control manual | No | **Mejor para DATETIME local**  |
| `.getTime()` | Timestamp Unix | N/A | Cálculos de tiempo |

---

## 🔧 Código de Referencia Completo

```javascript
// Función: saveGroupSequences() - plan.js

// Convertir startTime (HH:MM) a DATETIME para planned_start
// IMPORTANTE: NO usar toISOString() porque convierte a UTC sumando horas
// En su lugar, construir el string directamente en zona horaria local (Nuevo León)
let plannedStart = null;
if (startTime !== '--') {
  const todayStr = getTodayInNuevoLeon(); // Fecha en Nuevo Leon (YYYY-MM-DD)
  const [hours, minutes] = startTime.split(':');
  // Formato directo: YYYY-MM-DD HH:MM:SS sin conversión a UTC
  plannedStart = `${todayStr} ${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00`;
}

// Convertir endTime (HH:MM) a DATETIME para planned_end
// IMPORTANTE: NO usar toISOString() porque convierte a UTC sumando horas
let plannedEnd = null;
if (endTime !== '--') {
  const todayStr = getTodayInNuevoLeon(); // Fecha en Nuevo Leon (YYYY-MM-DD)
  const [hours, minutes] = endTime.split(':');
  // Formato directo: YYYY-MM-DD HH:MM:SS sin conversión a UTC
  plannedEnd = `${todayStr} ${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00`;
}
```

---

## 📌 Resumen

- **Problema:** MySQL guardaba horas 6 horas adelantadas (UTC en vez de local)
- **Causa:** Uso de `.toISOString()` que convierte a UTC automáticamente
- **Solución:** Construir string DATETIME directamente sin conversión UTC
- **Resultado:**  Horas consistentes entre frontend y MySQL

**Fecha de Corrección:** 22 de octubre de 2025  
**Archivo Modificado:** `app/static/js/plan.js`  
**Función Corregida:** `saveGroupSequences()`
