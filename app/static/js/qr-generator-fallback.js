/**
 * Generador de QR alternativo usando qrcode.js
 * Fallback en caso de problemas con la librería principal
 */

let qrGeneratorAlternativo = (function() {
    
    // Función para generar QR usando la librería qrcode
    function generarQRAlternativo(codigoMaterialRecibido) {
        console.log('🔄 Generando QR alternativo para:', codigoMaterialRecibido);
        
        // Crear contenedor modal para mostrar el QR
        const modalQR = crearModalQRAlternativo();
        
        // Limpiar contenido previo
        const qrContainer = modalQR.querySelector('#qr-code-container-alt');
        qrContainer.innerHTML = '';
        
        // Crear canvas para el QR
        const canvas = document.createElement('canvas');
        qrContainer.appendChild(canvas);
        
        // Generar el QR usando qrcode.js
        if (typeof QRCode !== 'undefined' && QRCode.toCanvas) {
            QRCode.toCanvas(canvas, codigoMaterialRecibido, {
                width: 256,
                margin: 2,
                color: {
                    dark: '#000000',
                    light: '#FFFFFF'
                }
            }, function (error) {
                if (error) {
                    console.error('❌ Error al generar QR alternativo:', error);
                    qrContainer.innerHTML = '<p style="color: red;">Error al generar QR</p>';
                } else {
                    console.log('✅ QR alternativo generado exitosamente');
                    
                    // Actualizar el texto del código
                    const codigoTexto = modalQR.querySelector('#codigo-texto-alt');
                    codigoTexto.textContent = codigoMaterialRecibido;
                    
                    // Mostrar el modal
                    modalQR.style.display = 'flex';
                }
            });
        } else {
            console.error('❌ Librería QRCode no disponible');
            qrContainer.innerHTML = '<p style="color: red;">Librería QR no disponible</p>';
        }
    }
    
    // Función para crear el modal alternativo del QR
    function crearModalQRAlternativo() {
        let modal = document.getElementById('modal-qr-generator-alt');
        
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-qr-generator-alt';
            modal.innerHTML = `
                <div class="qr-modal-overlay-alt">
                    <div class="qr-modal-content-alt">
                        <div class="qr-modal-header-alt">
                            <h3>📱 Código QR - Control de Material</h3>
                            <button class="qr-close-btn-alt" onclick="qrGeneratorAlternativo.cerrarModalQRAlternativo()">&times;</button>
                        </div>
                        <div class="qr-modal-body-alt">
                            <div id="qr-code-container-alt"></div>
                            <p class="qr-codigo-texto-alt">
                                <strong>Código Material Recibido:</strong><br>
                                <span id="codigo-texto-alt"></span>
                            </p>
                            <div class="qr-botones-alt">
                                <button class="material-btn orange" onclick="qrGeneratorAlternativo.descargarQRAlternativo()">💾 Descargar</button>
                                <button class="material-btn" onclick="qrGeneratorAlternativo.imprimirQRAlternativo()">🖨️ Imprimir</button>
                                <button class="material-btn secondary" onclick="qrGeneratorAlternativo.cerrarModalQRAlternativo()">Cerrar</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Añadir estilos CSS específicos
            const styles = document.createElement('style');
            styles.textContent = `
                #modal-qr-generator-alt {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: 10001;
                    background-color: rgba(0, 0, 0, 0.8);
                }
                
                .qr-modal-overlay-alt {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    width: 100%;
                    height: 100%;
                    padding: 20px;
                    box-sizing: border-box;
                }
                
                .qr-modal-content-alt {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 15px;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
                    max-width: 500px;
                    width: 100%;
                    max-height: 90vh;
                    overflow-y: auto;
                }
                
                .qr-modal-header-alt {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 25px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
                }
                
                .qr-modal-header-alt h3 {
                    margin: 0;
                    font-size: 20px;
                    font-weight: 500;
                }
                
                .qr-close-btn-alt {
                    background: rgba(255, 255, 255, 0.2);
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: white;
                    padding: 5px;
                    width: 35px;
                    height: 35px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    transition: background-color 0.3s;
                }
                
                .qr-close-btn-alt:hover {
                    background-color: rgba(255, 255, 255, 0.3);
                }
                
                .qr-modal-body-alt {
                    padding: 30px;
                    text-align: center;
                }
                
                #qr-code-container-alt {
                    display: flex;
                    justify-content: center;
                    margin: 25px 0;
                    padding: 25px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.1);
                }
                
                #qr-code-container-alt canvas {
                    border-radius: 8px;
                }
                
                .qr-codigo-texto-alt {
                    margin: 25px 0;
                    padding: 20px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    font-family: 'Courier New', monospace;
                    word-break: break-all;
                    line-height: 1.5;
                    backdrop-filter: blur(10px);
                }
                
                .qr-botones-alt {
                    display: flex;
                    gap: 12px;
                    justify-content: center;
                    flex-wrap: wrap;
                    margin-top: 30px;
                }
                
                .qr-botones-alt button {
                    padding: 12px 24px;
                    border-radius: 8px;
                    border: none;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 500;
                    transition: all 0.3s;
                    min-width: 120px;
                }
                
                .qr-botones-alt button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
                }
                
                @media (max-width: 600px) {
                    .qr-modal-content-alt {
                        margin: 10px;
                        width: calc(100% - 20px);
                    }
                    
                    .qr-modal-header-alt,
                    .qr-modal-body-alt {
                        padding: 20px;
                    }
                    
                    .qr-botones-alt {
                        flex-direction: column;
                    }
                    
                    .qr-botones-alt button {
                        width: 100%;
                        min-width: auto;
                    }
                }
            `;
            
            document.head.appendChild(styles);
            document.body.appendChild(modal);
        }
        
        return modal;
    }
    
    // Función para cerrar el modal alternativo
    function cerrarModalQRAlternativo() {
        const modal = document.getElementById('modal-qr-generator-alt');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    // Función para descargar el QR alternativo
    function descargarQRAlternativo() {
        try {
            const qrContainer = document.getElementById('qr-code-container-alt');
            const canvas = qrContainer.querySelector('canvas');
            
            if (canvas) {
                const link = document.createElement('a');
                const codigo = document.getElementById('codigo-texto-alt').textContent;
                link.download = `QR_MaterialRecibido_${codigo.replace(/[^a-zA-Z0-9]/g, '_')}.png`;
                link.href = canvas.toDataURL('image/png');
                link.click();
                
                console.log('✅ QR alternativo descargado');
            } else {
                alert('No se encontró el código QR para descargar');
            }
        } catch (error) {
            console.error('❌ Error al descargar QR alternativo:', error);
            alert('Error al descargar el código QR');
        }
    }
    
    // Función para imprimir el QR alternativo
    function imprimirQRAlternativo() {
        try {
            const qrContainer = document.getElementById('qr-code-container-alt');
            const canvas = qrContainer.querySelector('canvas');
            const codigoTexto = document.getElementById('codigo-texto-alt').textContent;
            
            if (canvas) {
                const printWindow = window.open('', '_blank');
                const qrDataUrl = canvas.toDataURL('image/png');
                
                printWindow.document.write(`
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>QR - Control de Material</title>
                        <style>
                            @page { margin: 20mm; }
                            body {
                                font-family: Arial, sans-serif;
                                text-align: center;
                                margin: 0;
                                padding: 20px;
                            }
                            .header {
                                font-size: 22px;
                                font-weight: bold;
                                margin-bottom: 30px;
                                color: #333;
                            }
                            .qr-container {
                                margin: 30px 0;
                            }
                            .qr-container img {
                                max-width: 300px;
                                height: auto;
                                border: 2px solid #ddd;
                                border-radius: 8px;
                            }
                            .codigo-info {
                                margin: 30px 0;
                                padding: 15px;
                                background: #f8f9fa;
                                border: 1px solid #dee2e6;
                                border-radius: 5px;
                                font-family: 'Courier New', monospace;
                                font-size: 14px;
                                word-break: break-all;
                            }
                            .footer {
                                margin-top: 40px;
                                font-size: 12px;
                                color: #666;
                                border-top: 1px solid #eee;
                                padding-top: 15px;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="header">Control de Material - Almacén</div>
                        <div class="qr-container">
                            <img src="${qrDataUrl}" alt="Código QR"/>
                        </div>
                        <div class="codigo-info">
                            <strong>Código de Material Recibido:</strong><br>
                            ${codigoTexto}
                        </div>
                        <div class="footer">
                            Generado el: ${new Date().toLocaleString('es-ES')}<br>
                            Sistema ISEMM MES
                        </div>
                    </body>
                    </html>
                `);
                
                printWindow.document.close();
                printWindow.focus();
                
                setTimeout(() => {
                    printWindow.print();
                }, 1000);
                
                console.log('✅ QR alternativo enviado a impresión');
            } else {
                alert('No se encontró el código QR para imprimir');
            }
        } catch (error) {
            console.error('❌ Error al imprimir QR alternativo:', error);
            alert('Error al imprimir el código QR');
        }
    }
    
    // API pública del módulo alternativo
    return {
        generarQRAlternativo: generarQRAlternativo,
        cerrarModalQRAlternativo: cerrarModalQRAlternativo,
        descargarQRAlternativo: descargarQRAlternativo,
        imprimirQRAlternativo: imprimirQRAlternativo
    };
    
})();

// Función de fallback que detecta qué librería usar
window.generarQRConFallback = function(codigo) {
    console.log('🎯 Intentando generar QR con fallback para:', codigo);
    
    // Intentar con el módulo principal primero
    if (window.qrGeneratorModule && typeof qrGeneratorModule.generarQR === 'function') {
        console.log('✅ Usando generador QR principal');
        qrGeneratorModule.generarQR(codigo);
    } 
    // Fallback al generador alternativo
    else if (typeof qrGeneratorAlternativo.generarQRAlternativo === 'function') {
        console.log('⚠️ Usando generador QR alternativo');
        qrGeneratorAlternativo.generarQRAlternativo(codigo);
    } 
    // Último recurso: generar QR simple
    else {
        console.log('❌ Generando QR con método básico');
        generarQRBasico(codigo);
    }
};

// Método básico de último recurso
function generarQRBasico(codigo) {
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=${encodeURIComponent(codigo)}`;
    
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background: rgba(0,0,0,0.8); display: flex; justify-content: center; 
        align-items: center; z-index: 10002;
    `;
    
    modal.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 10px; text-align: center; max-width: 400px;">
            <h3>📱 Código QR</h3>
            <img src="${qrUrl}" alt="QR Code" style="max-width: 100%; margin: 20px 0;"/>
            <p style="font-family: monospace; word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                ${codigo}
            </p>
            <button onclick="this.closest('div').remove()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">
                Cerrar
            </button>
        </div>
    `;
    
    modal.onclick = (e) => {
        if (e.target === modal) modal.remove();
    };
    
    document.body.appendChild(modal);
}

console.log('✅ Generador QR alternativo cargado correctamente');
