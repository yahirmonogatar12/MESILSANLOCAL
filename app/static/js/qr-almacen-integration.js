/**
 * Integración QR Almacén - Funciones de utilidad
 * Demuestra el uso del nuevo formato ZPL para impresión Zebra
 */

window.QRAlmacenIntegration = (function() {
    
    /**
     * Función para obtener datos del formulario y generar QR con formato ZPL actualizado
     */
    function obtenerDatosFormulario() {
        const datos = {
            codigoMaterialRecibido: document.getElementById('codigo_material_recibido')?.value || '',
            codigoMaterial: document.getElementById('codigo_material_lower')?.value || '',
            numeroParte: document.getElementById('numero_parte_lower')?.value || '',
            cantidadEstandarizada: document.getElementById('cantidad_estandarizada')?.value || '5000',
            fechaRecibo: document.getElementById('fecha_recibo')?.value || '',
            propiedadMaterial: document.getElementById('propiedad_material')?.value || '',
            cliente: document.getElementById('cliente')?.value || '',
            numeroLoteMaterial: document.getElementById('numero_lote_material')?.value || ''
        };
        
        console.log('📋 Datos extraídos del formulario:', datos);
        return datos;
    }
    
    /**
     * Función para generar QR después de guardar exitosamente
     * Se integra con el sistema existente sin modificar funciones actuales
     */
    function generarQRPostGuardado(codigoMaterialRecibido) {
        if (!codigoMaterialRecibido || codigoMaterialRecibido.trim() === '') {
            console.warn('⚠️ No se proporcionó código de material recibido válido');
            return;
        }
        
        console.log('🎯 Iniciando generación QR post-guardado:', codigoMaterialRecibido);
        
        // Usar el módulo QR existente
        if (window.QRAlmacenSimple && typeof QRAlmacenSimple.generarQR === 'function') {
            // Delay para asegurar que el guardado se completó
            setTimeout(() => {
                QRAlmacenSimple.generarQR(codigoMaterialRecibido);
            }, 500);
        } else {
            console.error('❌ Módulo QRAlmacenSimple no disponible');
        }
    }
    
    /**
     * Función para demostrar el formato ZPL que se está usando
     */
    function mostrarEjemploZPL() {
        const datosEjemplo = {
            codigoCompleto: '0RH5602C622,202507170003',
            codigoMaterial: '0RH5602C622',
            numeroSerie: '202507170003',
            fecha: '17/07/2025',
            cantidadEstandarizada: '5000',
            descripcionMaterial: '56KJ 1/10W (SMD 1608)'
        };
        
        const zplEjemplo = `
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
^FT168,75^A0N,16,15^FH\\^CI28^FDFecha de entrada:^FS^CI27
^FT167,122^A0N,18,18^FH\\^CI28^FDQTY:^FS^CI27
^FT5,175^BQN,2,6
^FH\\^FDLA,${datosEjemplo.codigoCompleto}^FS
^FT168,26^A0N,25,25^FH\\^CI28^FD${datosEjemplo.codigoMaterial}^FS^CI27
^FT168,57^A0N,25,25^FH\\^CI28^FD${datosEjemplo.numeroSerie}^FS^CI27
^FT168,97^A0N,21,20^FH\\^CI28^FD${datosEjemplo.fecha}^FS^CI27
^FT168,151^A0N,21,20^FH\\^CI28^FD${datosEjemplo.descripcionMaterial}^FS^CI27
^FT203,124^A0N,22,20^FH\\^CI28^FD${datosEjemplo.cantidadEstandarizada}^FS^CI27
^PQ1,0,1,Y
^XZ
        `.trim();
        
        console.log('📝 Ejemplo de formato ZPL actualizado:');
        console.log(zplEjemplo);
        
        // Mostrar en modal informativo
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
            background: rgba(0,0,0,0.8); display: flex; justify-content: center; 
            align-items: center; z-index: 10003; padding: 20px; box-sizing: border-box;
        `;
        
        modal.innerHTML = `
            <div style="background: white; padding: 30px; border-radius: 15px; max-width: 800px; width: 100%; max-height: 90vh; overflow-y: auto;">
                <h3 style="margin: 0 0 20px 0; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px;">
                    📋 Formato ZPL Actualizado - Zebra ZD421
                </h3>
                
                <div style="margin: 20px 0;">
                    <h4 style="color: #6f42c1; margin-bottom: 10px;">📊 Variables que se insertan automáticamente:</h4>
                    <ul style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 0;">
                        <li><strong>Código completo:</strong> ${datosEjemplo.codigoCompleto}</li>
                        <li><strong>Código material:</strong> ${datosEjemplo.codigoMaterial}</li>
                        <li><strong>Número serie:</strong> ${datosEjemplo.numeroSerie}</li>
                        <li><strong>Fecha entrada:</strong> ${datosEjemplo.fecha}</li>
                        <li><strong>Cantidad:</strong> ${datosEjemplo.cantidadEstandarizada}</li>
                        <li><strong>Descripción:</strong> ${datosEjemplo.descripcionMaterial}</li>
                    </ul>
                </div>
                
                <div style="margin: 20px 0;">
                    <h4 style="color: #28a745; margin-bottom: 10px;">🖨️ Comando ZPL Generado:</h4>
                    <pre style="background: #f8f9fa; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 12px; border: 1px solid #dee2e6;">${zplEjemplo}</pre>
                </div>
                
                <div style="margin: 20px 0;">
                    <h4 style="color: #dc3545; margin-bottom: 10px;">⚡ Características del formato:</h4>
                    <ul style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 0; border: 1px solid #ffeaa7;">
                        <li>✅ Compatible con Zebra ZD421</li>
                        <li>✅ Código QR automático con datos completos</li>
                        <li>✅ Variables dinámicas del formulario</li>
                        <li>✅ Formato de fecha DD/MM/YYYY</li>
                        <li>✅ Campos de cantidad y descripción configurables</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <button onclick="this.closest('div').remove()" 
                        style="padding: 12px 30px; background: #007bff; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 500;">
                        ✓ Entendido
                    </button>
                </div>
            </div>
        `;
        
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        
        document.body.appendChild(modal);
        
        return zplEjemplo;
    }
    
    /**
     * Función para probar la generación ZPL con datos de ejemplo
     */
    function probarGeneracionZPL() {
        const codigoPrueba = '0RH5602C622,202507170003';
        
        console.log('🧪 Probando generación ZPL con código:', codigoPrueba);
        
        if (window.QRAlmacenSimple && typeof QRAlmacenSimple.generarQR === 'function') {
            QRAlmacenSimple.generarQR(codigoPrueba);
        } else {
            console.error('❌ No se pudo acceder al módulo QRAlmacenSimple');
            alert('❌ Error: Módulo QR no disponible');
        }
    }
    
    /**
     * Función de hook para integrar con el sistema de guardado existente
     * Llama esta función después de un guardado exitoso
     */
    function hookPostGuardado(datos) {
        console.log('🔗 Hook post-guardado ejecutado:', datos);
        
        if (datos && datos.codigo_material_recibido) {
            generarQRPostGuardado(datos.codigo_material_recibido);
        } else {
            console.warn('⚠️ No se encontró código de material recibido en los datos');
        }
    }
    
    /**
     * Función para verificar que todos los módulos necesarios estén cargados
     */
    function verificarModulosDisponibles() {
        const modulos = {
            'QRAlmacenSimple': window.QRAlmacenSimple,
            'qrGeneratorModule': window.qrGeneratorModule,
            'jQuery': window.$
        };
        
        console.log('🔍 Verificando módulos disponibles:');
        
        Object.entries(modulos).forEach(([nombre, modulo]) => {
            const disponible = !!modulo;
            console.log(`${disponible ? '✅' : '❌'} ${nombre}: ${disponible ? 'Disponible' : 'No disponible'}`);
        });
        
        return modulos;
    }
    
    // API pública del módulo de integración
    return {
        obtenerDatosFormulario: obtenerDatosFormulario,
        generarQRPostGuardado: generarQRPostGuardado,
        mostrarEjemploZPL: mostrarEjemploZPL,
        probarGeneracionZPL: probarGeneracionZPL,
        hookPostGuardado: hookPostGuardado,
        verificarModulosDisponibles: verificarModulosDisponibles
    };

})();

// Funciones globales para fácil acceso
window.mostrarEjemploZPL = function() {
    QRAlmacenIntegration.mostrarEjemploZPL();
};

window.probarQRZPL = function() {
    QRAlmacenIntegration.probarGeneracionZPL();
};

window.verificarModulosQR = function() {
    QRAlmacenIntegration.verificarModulosDisponibles();
};

console.log('✅ QR Almacén Integration cargado correctamente');
console.log('🔧 Funciones disponibles:');
console.log('   - window.mostrarEjemploZPL() : Muestra ejemplo del formato ZPL');
console.log('   - window.probarQRZPL() : Prueba la generación de QR');
console.log('   - window.verificarModulosQR() : Verifica módulos disponibles');
