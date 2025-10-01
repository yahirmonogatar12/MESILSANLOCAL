# Sistema de Planeación de Producción Automática

## 📋 Descripción General

Este sistema genera automáticamente la planeación de producción en formato de tabla por línea, calculando tiempos, asignando breaks y turnos, y marcando "TIEMPO EXTRA" cuando se exceda la jornada configurada.

## 🚀 Características Principales

### ✅ Funcionalidades Implementadas

1. **Cálculo Automático de Tiempos**
   - Fórmula: `Tiempo = Plan ÷ UPH` (en formato hh:mm)
   - Suma secuencial por línea
   - Asignación automática de hora de inicio y fin

2. **Sistema de Breaks Configurables**
   - Break 1: 09:30–09:45 (15 min)
   - Almuerzo: 12:00–12:30 (30 min)
   - Break 2: 15:00–15:15 (15 min)
   - Inserción automática cuando caen dentro del rango

3. **Detección de Tiempo Extra**
   - Jornada normal configurable (default: 9 horas)
   - Marcado automático como "TIEMPO EXTRA"
   - Resaltado visual de filas en overtime

4. **Agrupación por Flujos de Línea**
   - M1 → D1, M2 → D2, M3 → D3
   - Grupos respetan secuencia de líneas conectadas
   - Totales por línea/grupo

5. **Tabla de Salida Completa**
   - Línea, Part No, Cantidad, UPH, Tiempo
   - Break, Inicio Plan, Fin Plan
   - Total por Línea, Status (DIA/TIEMPO EXTRA)

## 🖥️ Uso del Sistema

### Acceso
1. Desde la página principal: Click en **"📋 Planeación Producción"**
2. URL directa: `http://localhost:4000/production-planning`

### Generar Planeación
1. **Seleccionar fecha** en el campo de fecha
2. **Elegir línea** (Todas las líneas, M1, M2, M3, D1, D2, D3)
3. Click en **"🔄 Generar Planeación"**

### Configuración Avanzada
1. Click en **"⚙️ Configuración"** para expandir panel
2. **Configurar Breaks**: Modificar horarios de descansos
3. **Configurar Jornada**: Hora inicio y duración normal
4. **Flujos de Línea**: Activar/desactivar conexiones M→D
5. **Guardar** configuración o **Restaurar** defaults

### Exportar Datos
- Click en **"📊 Exportar"** para descargar CSV
- Formato: `planeacion_produccion_YYYY-MM-DD.csv`

## 🔧 API Endpoints

### Generar Planeación
```http
POST /api/production-planning/generate
Content-Type: application/json

{
  "date": "2024-01-15",
  "line": "ALL",
  "config": {
    "breaks": [
      {"start": "09:30", "end": "09:45", "name": "Break 1"},
      {"start": "12:00", "end": "12:30", "name": "Almuerzo"},
      {"start": "15:00", "end": "15:15", "name": "Break 2"}
    ],
    "shiftStart": "07:00",
    "normalHours": 9,
    "lineFlows": {"M1": "D1", "M2": "D2", "M3": "D3"}
  }
}
```

### Obtener Configuración
```http
GET /api/production-planning/config
```

## 📊 Estructura de Datos de Salida

### Tipos de Filas en la Tabla

1. **group-header**: Encabezado de grupo (ej: "GRUPO M1-D1")
2. **plan**: Fila de plan de producción individual
3. **break**: Fila de descanso/break
4. **total**: Fila de totales por línea

### Ejemplo de Salida
```
GRUPO M1-D1
M1    | EBR123456 | 100 | 50  | 02:00 |           | 07:00 | 09:00 |       | 
M1    |           |     |     | 00:15 | Break 1   | 09:30 | 09:45 |       |
M1    | EBR789012 | 150 | 75  | 02:00 |           | 09:45 | 11:45 |       |
M1    | TOTAL M1  |     |     |       |           |       |       | 4.25h | DIA

D1    | EBR345678 | 200 | 40  | 05:00 |           | 07:00 | 12:00 |       |
D1    |           |     |     | 00:30 | Almuerzo  | 12:00 | 12:30 |       |
D1    | EBR901234 | 300 | 60  | 05:00 |           | 12:30 | 17:30 |       |
D1    | TOTAL D1  |     |     |       |           |       |       | 10.5h | TIEMPO EXTRA
```

## 🎨 Indicadores Visuales

- **🟦 Grupo Header**: Fondo azul oscuro
- **🟨 Breaks**: Fondo amarillo
- **🟩 Totales**: Fondo verde
- **🟥 Tiempo Extra**: Fondo rojo para filas que exceden jornada normal

## ⚙️ Configuración por Defecto

```javascript
{
  breaks: [
    { start: '09:30', end: '09:45', name: 'Break 1' },
    { start: '12:00', end: '12:30', name: 'Almuerzo' },
    { start: '15:00', end: '15:15', name: 'Break 2' }
  ],
  shiftStart: '07:00',
  normalHours: 9,
  lineFlows: {
    'M1': 'D1',
    'M2': 'D2', 
    'M3': 'D3'
  }
}
```

## 🔄 Lógica de Cálculo

1. **Filtrado**: Planes por fecha y línea seleccionadas
2. **Agrupación**: Por flujos de línea configurados
3. **Ordenamiento**: Por secuencia y fecha de creación
4. **Cálculo Secuencial**: 
   - Tiempo producción = Plan ÷ UPH × 60 minutos
   - Hora inicio = Hora anterior + tiempo anterior
   - Insertar breaks cuando corresponda
5. **Detección Overtime**: Si total > jornada normal
6. **Renderizado**: Tabla con estilos según tipo de fila

## 🐛 Solución de Problemas

### No aparecen datos
- Verificar que existan planes para la fecha seleccionada
- Revisar que los planes tengan UPH > 0
- Confirmar que el status no sea 'CANCELADO'

### Tiempos incorrectos
- Verificar valores de UPH en la tabla plan_main
- Revisar configuración de breaks
- Confirmar hora de inicio del turno

### Configuración no se guarda
- Verificar localStorage del navegador
- Probar con "Restaurar Defaults" y reconfigurar

## 📝 Notas Técnicas

- Configuración se guarda en localStorage del navegador
- Cálculos se realizan en el backend (Python)
- Frontend usa JavaScript vanilla + Axios
- Compatible con la base de datos existente (plan_main)
- Responsivo para dispositivos móviles
