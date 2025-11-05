# Solución: Conflicto de Modales en Control de Material de Almacén

## Problema

Cuando el usuario hacía clic en el botón "Unidades" (modo manual) en el módulo de Control de Material de Almacén, a veces se abría el modal incorrecto (modal de asignación de lotes de proveedor) en lugar de procesar la impresión directamente.

### Síntomas
- Usuario selecciona modo "Manual" (sin lote de proveedor)
- Hace clic en botón "Unidades"
- Aparece modal pequeño para ingresar cantidad
- Ingresa cantidad y confirma
- **PROBLEMA**: Se abre el modal de "Asignación de Lotes de Proveedor" cuando NO debería

## Causa Raíz

El problema estaba en la función `procesarImpresionUnidades()` (línea ~5397) que **siempre** abría el modal de asignación de lotes (`abrirModalAsignacionLotes()`), sin importar si el usuario había marcado o no el checkbox de "lote interno".

### Código Problemático (Antes)
```javascript
function procesarImpresionUnidades() {
    // ... código de validación y generación de códigos ...
    
    // PROBLEMA: Siempre abre modal de asignación
    abrirModalAsignacionLotes();
    imprimirEnSegundoPlano(cantidad);
}
```

### Lógica Incorrecta
1. Usuario hace clic en "Unidades" → modal pequeño para cantidad
2. Usuario ingresa cantidad (sin marcar checkbox de lote interno)
3. Confirma → `procesarImpresionUnidades()` se ejecuta
4. **Función SIEMPRE abre `modal-asignacion-lotes`** ❌
5. Usuario confundido porque no quería asignar lotes de proveedor

## Solución Implementada

Se modificó `procesarImpresionUnidades()` para verificar si el usuario marcó el checkbox de lote interno **antes** de decidir qué hacer:

### Código Corregido (Después)
```javascript
function procesarImpresionUnidades() {
    const cantidad = parseInt(document.getElementById('cantidad-unidades').value);
    
    if (!cantidad || cantidad < 1 || cantidad > 999) {
        alert('Por favor ingrese una cantidad válida (1-999)');
        return;
    }
    
    try {
        cerrarModalUnidades();
        
        // ✅ CLAVE: Verificar si se va a usar lote interno
        const usarLoteInterno = window.loteInternoParaGuardar !== null && 
                               window.loteInternoParaGuardar !== undefined;
        
        // Generar códigos consecutivos
        etiquetasImpresas = [];
        const codigoBase = document.getElementById('numero_parte_lower')?.value || 
                          materialExistente.codigo;
        
        for (let i = 1; i <= cantidad; i++) {
            const codigoConsecutivo = generarCodigoConsecutivo(codigoBase, i);
            etiquetasImpresas.push({
                numero: i,
                codigo: codigoConsecutivo,
                loteProveedor: null,
                asignado: false
            });
        }
        
        // ✅ DECISIÓN: Según checkbox de lote interno
        if (usarLoteInterno) {
            // Con lote interno: abrir modal para escanear etiquetas
            abrirModalAsignacionLotes();
            imprimirEnSegundoPlano(cantidad);
        } else {
            // Sin lote interno: imprimir y guardar directamente
            imprimirYGuardarDirecto(cantidad);
        }
        
    } catch (error) {
        console.error('Error en impresión:', error);
        alert('Error al imprimir etiquetas: ' + error.message);
        ocultarIndicadorProceso();
    }
}
```

### Nuevas Funciones Creadas

#### 1. `imprimirYGuardarDirecto(cantidad)`
Función que procesa la impresión y guardado sin abrir modal de asignación:

```javascript
async function imprimirYGuardarDirecto(cantidad) {
    try {
        // 1. Imprimir todas las etiquetas
        mostrarIndicadorProceso('Imprimiendo etiquetas...');
        for (let i = 0; i < etiquetasImpresas.length; i++) {
            const etiqueta = etiquetasImpresas[i];
            await imprimirEtiquetaIndividual(etiqueta.codigo, i + 1, cantidad);
        }
        
        // 2. Guardar en inventario
        mostrarIndicadorProceso('Guardando en inventario...');
        let exitosas = 0;
        let fallidas = 0;
        
        for (const item of etiquetasImpresas) {
            try {
                await guardarEntradaInventarioDirecto(item);
                exitosas++;
            } catch (error) {
                fallidas++;
            }
        }
        
        // 3. Mostrar resultado
        ocultarIndicadorProceso();
        const mensaje = `Etiquetas procesadas: ${cantidad}
                        Guardadas exitosamente: ${exitosas}`;
        mostrarModalCompletado(mensaje);
        
    } catch (error) {
        alert('Error al procesar: ' + error.message);
        ocultarIndicadorProceso();
    }
}
```

#### 2. `guardarEntradaInventarioDirecto(item)`
Guarda entrada en inventario sin lote de proveedor:

```javascript
async function guardarEntradaInventarioDirecto(item) {
    const formData = {
        forma_material: document.getElementById('forma_material').value,
        cliente: document.getElementById('cliente').value,
        codigo_material_original: materialExistente.codigo,
        codigo_material: document.getElementById('codigoMaterialSelect').value,
        // ... otros campos del formulario ...
        numero_lote_material: '', // ✅ Sin lote de proveedor
        codigo_material_recibido: item.codigo, // Código consecutivo generado
        // ... resto de campos ...
    };
    
    const response = await fetch('/guardar_control_almacen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    });
    
    const data = await response.json();
    if (!data.success) {
        throw new Error(data.message || 'Error al guardar');
    }
}
```

## Flujos de Trabajo

### Flujo 1: Sin Lote Interno (Modo Manual Simple)
```
1. Usuario clic "Unidades"
   ↓
2. Modal pequeño: ingresar cantidad
   ↓
3. Usuario NO marca checkbox "lote interno"
   ↓
4. Confirma cantidad
   ↓
5. procesarImpresionUnidades() detecta: usarLoteInterno = false
   ↓
6. Ejecuta: imprimirYGuardarDirecto()
   ↓
7. Imprime etiquetas → Guarda directamente en inventario
   ↓
8. Muestra modal de éxito
   ✅ NO abre modal de asignación de lotes
```

### Flujo 2: Con Lote Interno
```
1. Usuario clic "Unidades"
   ↓
2. Modal pequeño: ingresar cantidad
   ↓
3. Usuario SÍ marca checkbox "lote interno"
   ↓
4. Confirma cantidad
   ↓
5. procesarImpresionUnidades() detecta: usarLoteInterno = true
   ↓
6. Ejecuta: abrirModalAsignacionLotes()
   ↓
7. Imprime en segundo plano
   ↓
8. Abre modal para escanear etiquetas impresas
   ✅ Modal correcto se abre
```

## Archivos Modificados

### `app/templates/Control de material/Control de material de almacen.html`

**Líneas modificadas:**
- ~5397-5445: Función `procesarImpresionUnidades()` - agregada lógica condicional
- ~5520-5610: Nuevas funciones `imprimirYGuardarDirecto()` y `guardarEntradaInventarioDirecto()`

**Cambios clave:**
1. ✅ Verificación de `window.loteInternoParaGuardar` para decidir flujo
2. ✅ Creación de función `imprimirYGuardarDirecto()` para modo manual
3. ✅ Creación de función `guardarEntradaInventarioDirecto()` sin lote proveedor
4. ✅ Mantenimiento de flujo existente cuando sí se usa lote interno

## Validación

### Pruebas Recomendadas

1. **Caso 1: Modo Manual sin Lote Interno**
   - Hacer clic en "Unidades"
   - Ingresar cantidad (NO marcar checkbox)
   - Confirmar
   - **Resultado esperado**: Imprime y guarda directamente, NO abre modal de asignación

2. **Caso 2: Modo Manual con Lote Interno**
   - Hacer clic en "Unidades"
   - Marcar checkbox "lote interno"
   - Ingresar cantidad
   - Confirmar
   - **Resultado esperado**: Abre modal de asignación para escanear etiquetas

3. **Caso 3: Verificar Inventario**
   - Después de ambos casos, verificar que entradas se guardaron correctamente
   - Caso 1: `numero_lote_material` debe estar vacío
   - Caso 2: `numero_lote_material` debe tener el lote interno

## Beneficios

1. ✅ **Eliminado conflicto de modales**: Ya no se abre modal incorrecto
2. ✅ **Flujo más rápido**: Modo manual procesa directamente sin pasos adicionales
3. ✅ **Mejor UX**: Usuario obtiene feedback inmediato sin modales innecesarios
4. ✅ **Código más claro**: Separación de responsabilidades (con lote vs sin lote)
5. ✅ **Mantenibilidad**: Funciones independientes para cada flujo

## Notas Técnicas

- Variable global `window.loteInternoParaGuardar` se usa como flag
- Esta variable se establece en wrapper de línea ~7014
- `null` o `undefined` = sin lote interno
- String con formato "DD.MM.YYYY.XXXX" = con lote interno
- Funciones asíncronas para no bloquear UI durante impresión
- Continúa procesamiento aunque algunas impresiones fallen

## Historial de Cambios

- **Fecha**: 2024
- **Autor**: GitHub Copilot
- **Tipo**: Corrección de bug (conflicto de modales)
- **Impacto**: Crítico - afecta flujo principal de entrada de material
- **Módulo**: Control de Material de Almacén
- **Función afectada**: `procesarImpresionUnidades()`
