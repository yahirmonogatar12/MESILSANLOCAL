# CÓDIGO ZPL ENVIADO A IMPRESORA ZEBRA ZT230

## Descripción General
El sistema genera código **ZPL (Zebra Programming Language)** para imprimir etiquetas de material en impresoras Zebra ZT230.

---

## 🔧 CONFIGURACIÓN DE IMPRESIÓN

### Configuración por Defecto
```javascript
{
    ip: '192.168.1.100',
    tipo: 'material',
    metodo: 'usb',
    server_url: 'http://localhost:5000',        // Servidor principal
    service_url: 'http://localhost:5003'        // Servicio de impresión local
}
```

### Métodos de Impresión
1. **USB** - Impresora conectada directamente a la PC
2. **Red** - Impresora con IP fija en la red local

---

## 📋 TIPOS DE ETIQUETAS

### 1. ETIQUETA SIMPLE (33.2mm x 14mm)

```zpl
^XA
^PW264^LL112
^FO10,2^BQN,2,1^FDQA,CODIGO_MATERIAL^FS
^FO55,10^ADN,12,8^FDCODIGO_MATERIAL^FS
^FO55,32^ADN,10,7^FDFECHA_HORA^FS
^FO5,54^ADN,8,6^FDMAT.REC^FS
^FO5,75^ADN,8,6^FDILSAN^FS
^XZ
```

#### Elementos de la Etiqueta Simple:
- **^XA** - Inicio de formato
- **^PW264** - Ancho de etiqueta: 264 dots
- **^LL112** - Largo de etiqueta: 112 dots
- **^FO10,2** - Posición del QR (X:10, Y:2)
- **^BQN,2,1** - Código QR, magnitud 2, mask 1
- **^FDQA,CODIGO** - Datos del QR
- **^FO55,10** - Posición del código
- **^ADN,12,8** - Fuente D, Normal, alto:12, ancho:8
- **^FD...^FS** - Campo de datos
- **^XZ** - Fin de formato

---

### 2. ETIQUETA COMPLETA (Material - Diseño del Usuario)

```zpl
CT~~CD,~CC^~CT~
^XA
~TA000
~JSN
^LT37
^MNW
^MTT
^PON
^PMN
^LH0,0
^JMA
^PR4,4
~SD15
^JUS
^LRN
^CI27
^PA0,1,1,0
^XZ
^XA
^MMT
^PW392
^LL165
^LS0
^FT188,70^A0N,22,20^FH\^CI28^FDFecha de entrada:^FS^CI27
^FT187,120^A0N,24,22^FH\^CI28^FDQTY:^FS^CI27
^FT25,95^BQN,2,6
^FH\^FDLA,CODIGO_MATERIAL^FS
^FT188,15^A0N,32,30^FH\^CI28^FDCODIGO_PARTE_1^FS^CI27
^FT188,50^A0N,32,30^FH\^CI28^FDCODIGO_PARTE_2^FS^CI27
^FT188,95^A0N,27,25^FH\^CI28^FDFECHA^FS^CI27
^FT188,150^A0N,30,28^FH\^CI28^FDESPECIFICACION_LINEA_1^FS^CI27
^FT188,175^A0N,30,28^FH\^CI28^FDESPECIFICACION_LINEA_2^FS^CI27
^FT240,122^A0N,28,26^FH\^CI28^FDCANTIDAD_ACTUAL^FS^CI27
^PQ1,0,1,Y
^XZ
```

#### Descripción de Comandos Principales:

##### Configuración Inicial
- **CT~~CD,~CC^~CT~** - Limpia buffer de transferencia
- **^XA** - Inicio de formato
- **~TA000** - Configuración avanzada de texto
- **^JSN** - Sensor de papel normal
- **^LT37** - Posición de etiqueta: 37 dots desde el origen
- **^MNW** - Modo de media: Web sensing
- **^MTT** - Tipo de media: Térmica directa
- **^PON** - Orientación de impresión: Normal
- **^PMN** - Modo de impresión: Normal
- **^LH0,0** - Origen de la etiqueta (0,0)
- **^JMA** - Ajuste de margen automático
- **^PR4,4** - Velocidad de impresión: 4 ips, slew speed 4
- **~SD15** - Densidad de oscuridad: 15
- **^JUS** - Configuración de unidades: dots
- **^LRN** - Orientación inversa: No
- **^CI27** - Set de caracteres: UTF-8
- **^PA0,1,1,0** - Configuración avanzada

##### Configuración de Etiqueta
- **^MMT** - Modo de impresión: Tear-off
- **^PW392** - Ancho de impresión: 392 dots
- **^LL165** - Largo de etiqueta: 165 dots
- **^LS0** - Shift de etiqueta: 0

##### Campos de Datos

**1. Texto "Fecha de entrada:"**
```zpl
^FT188,70^A0N,22,20^FH\^CI28^FDFecha de entrada:^FS^CI27
```
- ^FT188,70 - Posición (X:188, Y:70)
- ^A0N,22,20 - Fuente 0, Normal, altura:22, ancho:20
- ^FH\ - Formato hexadecimal
- ^CI28 - Codificación UTF-8
- ^FD...^FS - Datos del campo
- ^CI27 - Volver a UTF-8

**2. Texto "QTY:"**
```zpl
^FT187,120^A0N,24,22^FH\^CI28^FDQTY:^FS^CI27
```
- Posición (X:187, Y:120)
- Fuente tamaño 24x22

**3. Código QR**
```zpl
^FT25,95^BQN,2,6
^FH\^FDLA,CODIGO_MATERIAL^FS
```
- ^FT25,95 - Posición (X:25, Y:95)
- ^BQN,2,6 - Código QR, magnitud 2, nivel de error 6
- ^FDLA,CODIGO - Datos compactos JSON

**4. Código de Material (Línea 1)**
```zpl
^FT188,15^A0N,32,30^FH\^CI28^FDCODIGO_PARTE_1^FS^CI27
```
- Posición (X:188, Y:15)
- Fuente 32x30 (grande)
- Primera parte del código si contiene coma

**5. Código de Material (Línea 2)**
```zpl
^FT188,50^A0N,32,30^FH\^CI28^FDCODIGO_PARTE_2^FS^CI27
```
- Posición (X:188, Y:50)
- Segunda parte del código si contiene coma

**6. Fecha de Entrada**
```zpl
^FT188,95^A0N,27,25^FH\^CI28^FDFECHA^FS^CI27
```
- Posición (X:188, Y:95)
- Formato: DD/MM/YYYY
- Fuente 27x25

**7. Especificación (Línea 1)**
```zpl
^FT188,150^A0N,30,28^FH\^CI28^FDESPECIFICACION_LINEA_1^FS^CI27
```
- Posición (X:188, Y:150)
- Primera línea de especificación (antes del paréntesis)

**8. Especificación (Línea 2)**
```zpl
^FT188,175^A0N,30,28^FH\^CI28^FDESPECIFICACION_LINEA_2^FS^CI27
```
- Posición (X:188, Y:175)
- Segunda línea (desde el paréntesis)

**9. Cantidad Actual**
```zpl
^FT240,122^A0N,28,26^FH\^CI28^FDCANTIDAD_ACTUAL^FS^CI27
```
- Posición (X:240, Y:122)
- Campo editable por el usuario
- Se guarda en base de datos

##### Finalización
```zpl
^PQ1,0,1,Y
^XZ
```
- **^PQ1,0,1,Y** - Cantidad de etiquetas: 1, pausa: 0, duplicados: 1, override: Sí
- **^XZ** - Fin de formato

---

##  DATOS DEL CÓDIGO QR

### Formato JSON Compacto
```javascript
{
    c: codigo.substring(0, 15),          // Código (15 chars)
    f: fecha.substring(0, 10),           // Fecha (10 chars)
    l: numeroLote.substring(0, 8),       // Lote (8 chars)
    p: numeroParte.substring(0, 8),      // Parte (8 chars)
    q: cantidadActual.substring(0, 6),   // Cantidad (6 chars)
    m: especificacion.substring(0, 6),   // Material (6 chars)
    s: 'OK',                             // Estado
    e: 'ILSAN'                           // Empresa
}
```

### Conversión a Texto QR
```javascript
// JSON -> Compacto sin comillas
// Ejemplo: c=12345|f=2025-10-13|l=LOT001|p=PN001|q=100|m=SMD|s=OK|e=ILSAN
const textoQR = JSON.stringify(datosQR)
    .replace(/"/g, '')      // Quitar comillas
    .replace(/:/g, '=')     // : -> =
    .replace(/,/g, '|');    // , -> |
```

---

## 🔄 FUNCIONES QUE GENERAN ZPL

### 1. `generarComandoZPLConDatos(datosEtiqueta, tipo)`
**Uso:** Reimprimir etiquetas con datos de la base de datos

**Parámetros:**
```javascript
datosEtiqueta = {
    codigo: 'MAT-001',
    numeroLote: 'LOT-2024-001',
    numeroParte: 'PN-12345',
    cantidadActual: '100',
    propiedadMaterial: 'SMD',
    especificacionMaterial: 'Resistor 0603 (10K)',
    fechaRecibo: '2024-12-15 10:30:00',
    cantidadEstandarizada: '1000',
    ubicacionSalida: 'A1-B2',
    materialImportacionLocal: 'Importación'
}
```

**Validaciones:**
- Convierte `cantidadActual` a String
- Usa `especificacionMaterial` de SQL si existe, sino `propiedadMaterial`
- Usa `fechaRecibo` de SQL si existe, sino fecha actual
- Valores por defecto si campos están vacíos

---

### 2. `generarComandoZPLDirecto(codigo, tipo)`
**Uso:** Imprimir etiqueta desde formulario (nueva entrada)

**Obtiene datos de:**
```javascript
const numeroLote = document.getElementById('numero_lote_material')?.value
const numeroParte = document.getElementById('numero_parte_lower')?.value
const cantidadActual = getCantidadActual()  // Función robusta
const propiedad = document.getElementById('almacen_especificacion_material')?.value
```

---

## 🖨️ FLUJO DE IMPRESIÓN

### Método 1: Guardar y Imprimir (Formulario)
```
1. Usuario llena formulario
2. guardarFormulario() → Guarda en BD
3. imprimirZebraAutomaticoConDatos(datosParaEtiqueta)
4. generarComandoZPLConDatos() → Genera ZPL
5. enviarAServicioWin32() → Imprime
```

### Método 2: Reimprimir (Tabla)
```
1. Usuario selecciona fila de tabla
2. reimprimirEtiqueta(datosFilaSeleccionada)
3. Mapea datos SQL a datosEtiqueta
4. imprimirZebraAutomaticoConDatos(datosEtiqueta)
5. generarComandoZPLConDatos() → Genera ZPL
6. enviarAServicioWin32() → Imprime
```

### Método 3: Impresión Múltiple
```
1. Usuario selecciona cantidad de etiquetas
2. imprimirEtiquetaIndividual(codigo, numero, total)
3. Loop: Para cada etiqueta
4. imprimirZebraAutomatico(codigo) → Imprime
```

---

## 🚀 SERVICIO DE IMPRESIÓN

### Endpoint Windows Service
```
http://localhost:5003/print
```

### Payload JSON
```json
{
    "zpl": "^XA...^XZ",
    "codigo": "MAT-001",
    "printer_name": "ZDesigner ZT230-203dpi ZPL"
}
```

### Respuesta Exitosa
```json
{
    "success": true,
    "message": "Impresión enviada correctamente",
    "codigo": "MAT-001"
}
```

---

## ⚠️ MANEJO DE ERRORES

### Fallback 1: Backend Anterior
```javascript
try {
    await enviarPorBackendAnterior(comandoZPL, codigo, configuracion);
} catch (fallbackError) {
    // Ir a Fallback 2
}
```

### Fallback 2: Modal QR
```javascript
if (window.QRAlmacenSimple && typeof QRAlmacenSimple.generarQR === 'function') {
    QRAlmacenSimple.generarQR(codigo);
}
```

### Notificaciones
```javascript
mostrarNotificacionImpresion('Mensaje', 'tipo');
// Tipos: 'success', 'error', 'info', 'warning'
```

---

## 📐 ESPECIFICACIONES TÉCNICAS

### Impresora
- **Modelo:** Zebra ZT230
- **Resolución:** 203 DPI
- **Ancho:** 4 pulgadas (392 dots)
- **Conexión:** USB / Red Ethernet

### Etiqueta Simple
- **Dimensiones:** 33.2mm × 14mm
- **Dots:** 264 × 112
- **Orientación:** Horizontal

### Etiqueta Completa
- **Dimensiones:** ~50mm × 21mm
- **Dots:** 392 × 165
- **Orientación:** Horizontal

### Velocidad
- **Impresión:** 4 ips (inches per second)
- **Slew Speed:** 4 ips

### Densidad
- **Configuración:** 15 (^~SD15)
- **Rango:** 0-30 (más oscuro = mayor número)

---

##  VARIABLES CRÍTICAS EN ZPL

### Siempre Presentes
1. **CODIGO_MATERIAL** - Identificador único del material
2. **FECHA** - Fecha de entrada al almacén
3. **CANTIDAD_ACTUAL** - Cantidad guardada en BD
4. **ESPECIFICACION** - Descripción del material
5. **QR_CODE** - Código QR con datos compactos

### Opcionales
- **NUMERO_LOTE** - Lote del proveedor
- **NUMERO_PARTE** - Part number
- **UBICACION_SALIDA** - Ubicación física
- **MATERIAL_IMPORTACION_LOCAL** - Origen del material

---

## 📝 EJEMPLO REAL DE ZPL GENERADO

### Datos de Entrada
```javascript
{
    codigo: 'MAT-2025-001,ROHM',
    cantidadActual: '500',
    especificacion: 'Resistor SMD 0603 (10K Ohm)',
    fecha: '13/10/2025',
    numeroLote: 'L2025001',
    numeroParte: 'RC0603FR'
}
```

### ZPL Generado
```zpl
CT~~CD,~CC^~CT~
^XA
~TA000
~JSN
^LT37
^MNW
^MTT
^PON
^PMN
^LH0,0
^JMA
^PR4,4
~SD15
^JUS
^LRN
^CI27
^PA0,1,1,0
^XZ
^XA
^MMT
^PW392
^LL165
^LS0
^FT188,70^A0N,22,20^FH\^CI28^FDFecha de entrada:^FS^CI27
^FT187,120^A0N,24,22^FH\^CI28^FDQTY:^FS^CI27
^FT25,95^BQN,2,6
^FH\^FDLA,MAT-2025-001,ROHM^FS
^FT188,15^A0N,32,30^FH\^CI28^FDMAT-2025-001^FS^CI27
^FT188,50^A0N,32,30^FH\^CI28^FDROHM^FS^CI27
^FT188,95^A0N,27,25^FH\^CI28^FD13/10/2025^FS^CI27
^FT188,150^A0N,30,28^FH\^CI28^FDResistor SMD 0603 ^FS^CI27
^FT188,175^A0N,30,28^FH\^CI28^FD(10K Ohm)^FS^CI27
^FT240,122^A0N,28,26^FH\^CI28^FD500^FS^CI27
^PQ1,0,1,Y
^XZ
```

---

## 🔧 CONFIGURACIÓN RECOMENDADA

### LocalStorage
```javascript
localStorage.setItem('zebra_config', JSON.stringify({
    ip: '192.168.1.100',
    tipo: 'material',        // 'material' o 'simple'
    metodo: 'usb',           // 'usb' o 'red'
    server_url: 'http://localhost:5000',
    service_url: 'http://localhost:5003'
}));
```

### Servicio Windows
- **Puerto:** 5003
- **Ruta:** `C:\ZebraPrintService\`
- **Archivo:** `zebra_flask_integrado.py`
- **Auto-inicio:** Sí (Windows Task Scheduler)

---

## 📌 NOTAS IMPORTANTES

1. **Cantidad Actual vs Estandarizada:**
   - `cantidad_actual` se imprime en la etiqueta
   - `cantidad_estandarizada` se guarda en BD para referencia
   - Usuario puede editar `cantidad_actual` antes de imprimir

2. **División de Especificación:**
   - Se divide en paréntesis `(`
   - Línea 1: Antes del paréntesis
   - Línea 2: Desde el paréntesis
   - Ejemplo: "Resistor SMD 0603 (10K)" → "Resistor SMD 0603" + "(10K)"

3. **División de Código:**
   - Se divide por coma `,`
   - Parte 1: Código principal
   - Parte 2: Información adicional (fabricante, etc.)

4. **Fecha de Tabla vs Actual:**
   - Prioriza `fechaRecibo` de SQL si existe
   - Fallback a fecha actual del sistema
   - Formato: DD/MM/YYYY

5. **Códigos de Error:**
   - Error de red → Mostrar ZPL en consola
   - Error de servicio → Fallback a QR modal
   - Error de USB → Intentar backend anterior

---

## 🎯 RESUMEN

El sistema genera **código ZPL estándar** para impresoras Zebra ZT230, optimizado para etiquetas de material de almacén. 

**Características principales:**
-  Código QR con datos compactos
-  Información legible (código, fecha, cantidad, especificación)
-  Soporte para múltiples líneas de texto
-  Configuración flexible (USB/Red)
-  Sistema de fallback robusto
-  Validación de datos antes de imprimir

**Archivos involucrados:**
- `Control de material de almacen.html` (líneas 3250-3900)
- `zebra_flask_integrado.py` (servicio Windows)
- `routes.py` (endpoint `/imprimir_etiqueta_qr`)
