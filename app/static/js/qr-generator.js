/**
 * Generador de QR para Control de Material - Almacén
 * Script independiente para generar códigos QR sin interferir con el código existente
 */

// Variable global para manejar el generador QR
let qrGeneratorModule = (function() {
    
    // Función para generar QR usando QRCode.js
    function generarQR(codigoMaterialRecibido) {
        console.log('🔄 Generando QR para:', codigoMaterialRecibido);
        
        // Crear contenedor modal para mostrar el QR
        const modalQR = crearModalQR();
        
        // Limpiar contenido previo
        const qrContainer = modalQR.querySelector('#qr-code-container');
        qrContainer.innerHTML = '';
        
        // Generar el QR usando QRCode.js
        try {
            const qr = new QRCode(qrContainer, {
                text: codigoMaterialRecibido,
                width: 256,
                height: 256,
                colorDark: "#000000",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.M
            });
            
            // Actualizar el texto del código
            const codigoTexto = modalQR.querySelector('#codigo-texto');
            codigoTexto.textContent = codigoMaterialRecibido;
            
            // Mostrar el modal
            modalQR.style.display = 'flex';
            
            console.log('✅ QR generado exitosamente');
            
        } catch (error) {
            console.error('❌ Error al generar QR:', error);
            alert('Error al generar el código QR');
        }
    }
    
    // Función para crear el modal del QR
    function crearModalQR() {
        let modal = document.getElementById('modal-qr-generator');
        
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-qr-generator';
            modal.innerHTML = `
                <div class="qr-modal-overlay">
                    <div class="qr-modal-content">
                        <div class="qr-modal-header">
                            <h3>📱 Código QR Generado</h3>
                            <button class="qr-close-btn" onclick="qrGeneratorModule.cerrarModalQR()">&times;</button>
                        </div>
                        <div class="qr-modal-body">
                            <div id="qr-code-container"></div>
                            <p class="qr-codigo-texto">
                                <strong>Código:</strong> <span id="codigo-texto"></span>
                            </p>
                            <div class="qr-botones">
                                <button class="material-btn orange" onclick="qrGeneratorModule.descargarQR()">💾 Descargar QR</button>
                                <button class="material-btn" onclick="qrGeneratorModule.imprimirQR()">🖨️ Imprimir</button>
                                <button class="material-btn secondary" onclick="qrGeneratorModule.cerrarModalQR()">Cerrar</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Añadir estilos CSS
            const styles = document.createElement('style');
            styles.textContent = `
                #modal-qr-generator {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: 10000;
                    background-color: rgba(0, 0, 0, 0.7);
                }
                
                .qr-modal-overlay {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    width: 100%;
                    height: 100%;
                }
                
                .qr-modal-content {
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                    max-width: 450px;
                    width: 90%;
                    max-height: 90%;
                    overflow-y: auto;
                }
                
                .qr-modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 20px;
                    border-bottom: 1px solid #eee;
                    background: #f8f9fa;
                    border-radius: 12px 12px 0 0;
                }
                
                .qr-modal-header h3 {
                    margin: 0;
                    color: #333;
                    font-size: 18px;
                }
                
                .qr-close-btn {
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #666;
                    padding: 0;
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    transition: background-color 0.2s;
                }
                
                .qr-close-btn:hover {
                    background-color: #f0f0f0;
                }
                
                .qr-modal-body {
                    padding: 30px;
                    text-align: center;
                }
                
                #qr-code-container {
                    display: flex;
                    justify-content: center;
                    margin: 20px 0;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border: 2px dashed #ddd;
                }
                
                .qr-codigo-texto {
                    margin: 20px 0;
                    padding: 15px;
                    background: #e3f2fd;
                    border-radius: 6px;
                    font-family: 'Courier New', monospace;
                    word-break: break-all;
                }
                
                .qr-botones {
                    display: flex;
                    gap: 10px;
                    justify-content: center;
                    flex-wrap: wrap;
                    margin-top: 25px;
                }
                
                .qr-botones button {
                    padding: 10px 20px;
                    border-radius: 6px;
                    border: none;
                    cursor: pointer;
                    font-size: 14px;
                    transition: all 0.2s;
                }
                
                @media (max-width: 600px) {
                    .qr-modal-content {
                        margin: 20px;
                        width: calc(100% - 40px);
                    }
                    
                    .qr-botones {
                        flex-direction: column;
                    }
                    
                    .qr-botones button {
                        width: 100%;
                    }
                }
            `;
            
            document.head.appendChild(styles);
            document.body.appendChild(modal);
        }
        
        return modal;
    }
    
    // Función para cerrar el modal
    function cerrarModalQR() {
        const modal = document.getElementById('modal-qr-generator');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    // Función para descargar el QR como imagen
    function descargarQR() {
        try {
            const qrContainer = document.getElementById('qr-code-container');
            const canvas = qrContainer.querySelector('canvas');
            
            if (canvas) {
                // Crear enlace de descarga
                const link = document.createElement('a');
                link.download = `QR_${document.getElementById('codigo-texto').textContent}.png`;
                link.href = canvas.toDataURL();
                link.click();
                
                console.log('✅ QR descargado exitosamente');
            } else {
                alert('No se pudo encontrar el código QR para descargar');
            }
        } catch (error) {
            console.error('❌ Error al descargar QR:', error);
            alert('Error al descargar el código QR');
        }
    }
    
    // Función para imprimir el QR
    function imprimirQR() {
        try {
            const qrContainer = document.getElementById('qr-code-container');
            const canvas = qrContainer.querySelector('canvas');
            const codigoTexto = document.getElementById('codigo-texto').textContent;
            
            if (canvas) {
                // Crear ventana de impresión
                const printWindow = window.open('', '_blank');
                printWindow.document.write(`
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Código QR - ${codigoTexto}</title>
                        <style>
                            body {
                                font-family: Arial, sans-serif;
                                text-align: center;
                                padding: 20px;
                                margin: 0;
                            }
                            .qr-print-container {
                                max-width: 400px;
                                margin: 0 auto;
                            }
                            .qr-print-title {
                                font-size: 18px;
                                font-weight: bold;
                                margin-bottom: 20px;
                                color: #333;
                            }
                            .qr-print-code {
                                font-family: 'Courier New', monospace;
                                font-size: 14px;
                                margin-top: 20px;
                                word-break: break-all;
                                padding: 10px;
                                background: #f5f5f5;
                                border: 1px solid #ddd;
                            }
                            .qr-print-footer {
                                margin-top: 30px;
                                font-size: 12px;
                                color: #666;
                            }
                            @media print {
                                body { margin: 0; }
                            }
                        </style>
                    </head>
                    <body>
                        <div class="qr-print-container">
                            <div class="qr-print-title">Control de Material - Almacén</div>
                            <img src="${canvas.toDataURL()}" alt="Código QR" style="max-width: 100%; height: auto;"/>
                            <div class="qr-print-code">${codigoTexto}</div>
                            <div class="qr-print-footer">
                                Generado el: ${new Date().toLocaleString('es-ES')}
                            </div>
                        </div>
                    </body>
                    </html>
                `);
                
                printWindow.document.close();
                printWindow.focus();
                
                // Esperar a que cargue la imagen y luego imprimir
                setTimeout(() => {
                    printWindow.print();
                    printWindow.close();
                }, 500);
                
                console.log('✅ QR enviado a impresión');
            } else {
                alert('No se pudo encontrar el código QR para imprimir');
            }
        } catch (error) {
            console.error('❌ Error al imprimir QR:', error);
            alert('Error al imprimir el código QR');
        }
    }
    
    // Función principal que se llama después de guardar exitosamente
    function mostrarQRDespuesDeGuardar(codigoMaterialRecibido) {
        if (!codigoMaterialRecibido) {
            console.warn('⚠️ No se proporcionó código de material recibido para generar QR');
            return;
        }
        
        console.log('🎯 Iniciando generación de QR para:', codigoMaterialRecibido);
        
        // Pequeño delay para asegurar que el guardado se completó
        setTimeout(() => {
            generarQR(codigoMaterialRecibido);
        }, 500);
    }
    
    // Función de test para verificar funcionalidad
    function testGenerarQR() {
        const codigoPrueba = 'M2606809020,202507150001';
        console.log('🧪 Probando generación de QR con código:', codigoPrueba);
        generarQR(codigoPrueba);
    }
    
    // API pública del módulo
    return {
        mostrarQRDespuesDeGuardar: mostrarQRDespuesDeGuardar,
        generarQR: generarQR,
        cerrarModalQR: cerrarModalQR,
        descargarQR: descargarQR,
        imprimirQR: imprimirQR,
        testGenerarQR: testGenerarQR
    };
    
})();

// Función global de acceso rápido
window.generarQRMaterial = function(codigo) {
    qrGeneratorModule.generarQR(codigo);
};

// Test function para debugging
window.testQRGenerator = function() {
    qrGeneratorModule.testGenerarQR();
};

console.log('✅ Módulo QR Generator cargado correctamente');
