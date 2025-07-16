/**
 * Generador QR Simple para Control de Almacén
 * Usa API externa para generar QR automáticamente después de guardar
 * NO MODIFICA FUNCIONES EXISTENTES - TOTALMENTE PASIVO
 */

window.QRAlmacenSimple = (function() {
    
    // Función principal para generar QR
    function generarQR(codigoMaterialRecibido) {
        if (!codigoMaterialRecibido || codigoMaterialRecibido.trim() === '') {
            console.warn('⚠️ No hay código de material recibido para generar QR');
            return;
        }

        console.log('🎯 Generando QR para:', codigoMaterialRecibido);
        mostrarModalQR(codigoMaterialRecibido);
    }

    // Crear y mostrar modal con QR
    function mostrarModalQR(codigo) {
        // Remover modal anterior si existe
        const modalAnterior = document.getElementById('modal-qr-simple');
        if (modalAnterior) {
            modalAnterior.remove();
        }

        // Crear nuevo modal
        const modal = document.createElement('div');
        modal.id = 'modal-qr-simple';
        modal.innerHTML = crearHTMLModal(codigo);
        
        // Añadir estilos CSS
        añadirEstilosModal();
        
        // Añadir al DOM
        document.body.appendChild(modal);
        
        // Mostrar modal
        modal.style.display = 'flex';
        
        console.log('✅ Modal QR creado y mostrado');
    }

    // Crear HTML del modal
    function crearHTMLModal(codigo) {
        const qrURL = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(codigo)}`;
        
        return `
            <div class="qr-overlay-simple" onclick="cerrarModal()">
                <div class="qr-contenido-simple" onclick="event.stopPropagation()">
                    <div class="qr-header-simple">
                        <h3>📱 Código QR - Material Recibido</h3>
                        <button class="qr-cerrar-simple" onclick="QRAlmacenSimple.cerrarModal()">&times;</button>
                    </div>
                    
                    <div class="qr-body-simple">
                        <div class="qr-imagen-container">
                            <img src="${qrURL}" alt="Código QR" class="qr-imagen" 
                                 onload="console.log('✅ QR cargado correctamente')"
                                 onerror="console.error('❌ Error al cargar QR'); this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iI2Y4ZjlmYSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IiM2Yzc1N2QiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5FcnJvciBhbCBjYXJnYXIgUVI8L3RleHQ+PC9zdmc+'" />
                        </div>
                        
                        <div class="qr-codigo-info">
                            <strong>Código de Material Recibido:</strong><br>
                            <span class="codigo-texto">${codigo}</span>
                        </div>
                        
                        <div class="qr-botones-simple">
                            <button class="btn-qr descargar" onclick="QRAlmacenSimple.descargarQR('${codigo}')">
                                💾 Descargar
                            </button>
                            <button class="btn-qr imprimir" onclick="QRAlmacenSimple.imprimirQR('${codigo}')">
                                🖨️ Imprimir Normal
                            </button>
                            <button class="btn-qr zebra" onclick="QRAlmacenSimple.imprimirZebra('${codigo}')">
                                🦓 Zebra ZD421
                            </button>
                            <button class="btn-qr cerrar" onclick="QRAlmacenSimple.cerrarModal()">
                                ✖️ Cerrar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Añadir estilos CSS
    function añadirEstilosModal() {
        const styleId = 'qr-simple-styles';
        if (document.getElementById(styleId)) {
            return; // Ya existe
        }

        const styles = document.createElement('style');
        styles.id = styleId;
        styles.textContent = `
            #modal-qr-simple {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                z-index: 10000;
                justify-content: center;
                align-items: center;
                padding: 20px;
                box-sizing: border-box;
            }

            .qr-overlay-simple {
                width: 100%;
                height: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
            }

            .qr-contenido-simple {
                background: #fff;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
                max-width: 450px;
                width: 100%;
                max-height: 90vh;
                overflow-y: auto;
                animation: modalFadeIn 0.3s ease-out;
            }

            @keyframes modalFadeIn {
                from { opacity: 0; transform: scale(0.8); }
                to { opacity: 1; transform: scale(1); }
            }

            .qr-header-simple {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 25px;
                border-radius: 15px 15px 0 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .qr-header-simple h3 {
                margin: 0;
                font-size: 18px;
                font-weight: 500;
            }

            .qr-cerrar-simple {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                color: white;
                font-size: 24px;
                width: 35px;
                height: 35px;
                border-radius: 50%;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background-color 0.3s;
            }

            .qr-cerrar-simple:hover {
                background: rgba(255, 255, 255, 0.3);
            }

            .qr-body-simple {
                padding: 30px;
                text-align: center;
            }

            .qr-imagen-container {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                border: 2px solid #e9ecef;
            }

            .qr-imagen {
                max-width: 100%;
                height: auto;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }

            .qr-codigo-info {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin: 20px 0;
                font-family: Arial, sans-serif;
            }

            .codigo-texto {
                font-family: 'Courier New', monospace;
                font-weight: bold;
                color: #495057;
                word-break: break-all;
                font-size: 14px;
            }

            .qr-botones-simple {
                display: flex;
                gap: 10px;
                justify-content: center;
                flex-wrap: wrap;
                margin-top: 25px;
            }

            .btn-qr {
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.3s;
                min-width: 120px;
            }

            .btn-qr.descargar {
                background: #28a745;
                color: white;
            }

            .btn-qr.descargar:hover {
                background: #218838;
                transform: translateY(-2px);
            }

            .btn-qr.imprimir {
                background: #007bff;
                color: white;
            }

            .btn-qr.imprimir:hover {
                background: #0056b3;
                transform: translateY(-2px);
            }

            .btn-qr.cerrar {
                background: #6c757d;
                color: white;
            }

            .btn-qr.zebra {
                background: #6f42c1;
                color: white;
            }

            .btn-qr.zebra:hover {
                background: #5a2d91;
                transform: translateY(-2px);
            }

            .btn-qr.cerrar:hover {
                background: #545b62;
                transform: translateY(-2px);
            }

            @media (max-width: 600px) {
                .qr-contenido-simple {
                    margin: 10px;
                    width: calc(100% - 20px);
                }

                .qr-header-simple,
                .qr-body-simple {
                    padding: 20px;
                }

                .qr-botones-simple {
                    flex-direction: column;
                }

                .btn-qr {
                    width: 100%;
                    min-width: auto;
                }
            }
        `;

        document.head.appendChild(styles);
    }

    // Cerrar modal
    function cerrarModal() {
        const modal = document.getElementById('modal-qr-simple');
        if (modal) {
            modal.style.display = 'none';
            setTimeout(() => modal.remove(), 300);
        }
    }

    // Descargar QR
    function descargarQR(codigo) {
        try {
            const qrURL = `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(codigo)}`;
            
            const link = document.createElement('a');
            link.href = qrURL;
            link.download = `QR_Material_${codigo.replace(/[^a-zA-Z0-9]/g, '_')}.png`;
            link.target = '_blank';
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            console.log('✅ QR descargado:', codigo);
            
        } catch (error) {
            console.error('❌ Error al descargar QR:', error);
            alert('Error al descargar el código QR');
        }
    }

    // Imprimir QR
    function imprimirQR(codigo) {
        try {
            const qrURL = `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(codigo)}`;
            
            const ventanaImpresion = window.open('', '_blank');
            ventanaImpresion.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>QR - Material Recibido</title>
                    <style>
                        @page { margin: 15mm; }
                        body {
                            font-family: Arial, sans-serif;
                            text-align: center;
                            margin: 0;
                            padding: 20px;
                        }
                        .titulo {
                            font-size: 24px;
                            font-weight: bold;
                            margin-bottom: 30px;
                            color: #333;
                        }
                        .qr-container {
                            margin: 30px 0;
                        }
                        .qr-imagen {
                            max-width: 350px;
                            border: 2px solid #ddd;
                            border-radius: 10px;
                        }
                        .codigo-info {
                            margin: 30px 0;
                            padding: 20px;
                            background: #f8f9fa;
                            border: 1px solid #dee2e6;
                            border-radius: 8px;
                            font-family: 'Courier New', monospace;
                            font-size: 16px;
                            word-break: break-all;
                        }
                        .pie {
                            margin-top: 50px;
                            font-size: 12px;
                            color: #666;
                            border-top: 1px solid #eee;
                            padding-top: 20px;
                        }
                    </style>
                </head>
                <body>
                    <div class="titulo">Control de Material - Almacén</div>
                    <div class="qr-container">
                        <img src="${qrURL}" alt="Código QR" class="qr-imagen" />
                    </div>
                    <div class="codigo-info">
                        <strong>Código de Material Recibido:</strong><br>
                        ${codigo}
                    </div>
                    <div class="pie">
                        Generado: ${new Date().toLocaleString('es-ES')}<br>
                        Sistema ISEMM MES
                    </div>
                    <script>
                        window.onload = function() {
                            setTimeout(function() {
                                window.print();
                            }, 1000);
                        };
                    </script>
                </body>
                </html>
            `);
            
            ventanaImpresion.document.close();
            console.log('✅ QR enviado a impresión:', codigo);
            
        } catch (error) {
            console.error('❌ Error al imprimir QR:', error);
            alert('Error al imprimir el código QR');
        }
    }

    // Función para imprimir en impresora Zebra ZD421
    function imprimirZebra(codigo) {
        try {
            console.log('🦓 Imprimiendo en Zebra ZD421:', codigo);
            
            // Verificar si hay configuración guardada
            const configZebra = localStorage.getItem('zebra_config');
            
            if (!configZebra) {
                alert('⚠️ Debe configurar la impresora Zebra primero.\nUse el botón "Conf. de impresora" para configurarla.');
                return;
            }
            
            // Imprimir directamente con configuración guardada
            imprimirZebraDirecto(codigo);
            
        } catch (error) {
            console.error('❌ Error al imprimir en Zebra:', error);
            alert('Error al conectar con la impresora Zebra. Verifique la configuración.');
        }
    }
    
    // Función para imprimir directamente (sin modal de configuración)
    async function imprimirZebraDirecto(codigo) {
        try {
            const config = JSON.parse(localStorage.getItem('zebra_config'));
            const metodoConexion = config.metodo || 'usb';
            const ipImpresora = config.ip;
            const tipoEtiqueta = config.tipo;
            
            console.log(`🦓 Imprimiendo automáticamente por ${metodoConexion.toUpperCase()} (${tipoEtiqueta})`);
            
            const comandoZPL = generarComandoZPL(codigo, tipoEtiqueta);
            
            // Mostrar mensaje de envío discreto
            const metodoTexto = metodoConexion === 'usb' ? 'USB' : `Red ${ipImpresora}`;
            mostrarMensajeEnvio(`Imprimiendo en Zebra ${metodoTexto}...`);
            
            // Preparar datos para envío
            const requestData = {
                metodo_conexion: metodoConexion,
                comando_zpl: comandoZPL,
                codigo: codigo,
                tipo_etiqueta: tipoEtiqueta
            };
            
            if (metodoConexion === 'red') {
                requestData.ip_impresora = ipImpresora;
            }
            
            // Enviar comando ZPL directamente a la impresora
            const response = await fetch('/imprimir_zebra', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                // Verificar si es método manual
                if (result.metodo === 'archivo_manual') {
                    // Mostrar instrucciones detalladas para método manual
                    let instrucciones = '';
                    if (Array.isArray(result.instrucciones)) {
                        instrucciones = result.instrucciones.join('\n');
                    } else {
                        instrucciones = result.instrucciones || 'Use software de impresión ZPL';
                    }
                    
                    const mensajeDetallado = `
📁 Archivo ZPL creado para ZT230

📍 Ubicación: ${result.archivo || 'Archivo temporal'}

📋 Instrucciones:
${instrucciones}

💡 Comando alternativo:
${result.comando_manual || 'Use clic derecho → Imprimir'}
                    `.trim();
                    
                    mostrarMensajeExito(mensajeDetallado);
                    console.log('📁 ZT230: Archivo ZPL creado para impresión manual');
                } else {
                    mostrarMensajeExito(`✅ Etiqueta impresa en ZT230 ${metodoTexto} (${result.metodo})`);
                    console.log('✅ Impresión ZT230 automática exitosa');
                }
            } else {
                throw new Error(result.error || 'Error desconocido');
            }
            
        } catch (error) {
            console.error('❌ Error en impresión automática Zebra:', error);
            mostrarMensajeError('Error de impresión: ' + error.message);
        }
    }
    
    // Función para conectar directamente con Zebra (vía USB/Red)
    async function conectarZebraDirect(codigo) {
        try {
            // Intentar obtener configuración guardada
            let ipImpresora = localStorage.getItem('zebra_ip') || '192.168.1.100';
            
            // Mostrar modal de configuración
            const resultado = await mostrarModalConfiguracionZebra(ipImpresora);
            
            if (!resultado || !resultado.ip) {
                console.log('❌ No se proporcionó configuración de impresora');
                return;
            }
            
            ipImpresora = resultado.ip;
            const tipoEtiqueta = resultado.tipo || 'material';
            
            // Guardar IP para próximas veces
            localStorage.setItem('zebra_ip', ipImpresora);
            
            const comandoZPL = generarComandoZPL(codigo, tipoEtiqueta);
            
            // Mostrar mensaje de envío
            mostrarMensajeEnvio('Enviando a Zebra ZD421...');
            
            // Enviar comando ZPL directamente a la impresora
            const response = await fetch('/imprimir_zebra', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ip_impresora: ipImpresora,
                    comando_zpl: comandoZPL,
                    codigo: codigo,
                    tipo_etiqueta: tipoEtiqueta
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                // Verificar si es método manual
                if (result.metodo === 'archivo_manual') {
                    // Mostrar instrucciones detalladas para método manual
                    let instrucciones = '';
                    if (Array.isArray(result.instrucciones)) {
                        instrucciones = result.instrucciones.join('\n');
                    } else {
                        instrucciones = result.instrucciones || 'Use software de impresión ZPL';
                    }
                    
                    const mensajeDetallado = `
📁 Archivo ZPL creado para ZT230

📍 Ubicación: ${result.archivo || 'Archivo temporal'}

📋 Instrucciones:
${instrucciones}

💡 Comando alternativo:
${result.comando_manual || 'Use clic derecho → Imprimir'}
                    `.trim();
                    
                    mostrarMensajeExito(mensajeDetallado);
                    console.log('📁 ZT230: Archivo ZPL creado para impresión manual');
                } else {
                    mostrarMensajeExito(`✅ Etiqueta enviada a ZT230 ${ipImpresora || 'USB'} (${result.metodo})`);
                    console.log('✅ Impresión ZT230 exitosa');
                }
            } else {
                throw new Error(result.error || 'Error desconocido');
            }
            
        } catch (error) {
            console.error('❌ Error en conexión directa Zebra:', error);
            mostrarMensajeError('Error de conexión: ' + error.message);
            
            // Ofrecer descarga de ZPL como alternativa
            const descargar = confirm('¿Desea descargar el archivo ZPL para enviar manualmente?');
            if (descargar) {
                generarArchivoZPL(codigo);
            }
        }
    }
    
    // Modal de configuración para Zebra
    function mostrarModalConfiguracionZebra(ipActual, tipoActual = 'material') {
        return new Promise((resolve) => {
            // Crear modal de configuración
            const modalConfig = document.createElement('div');
            modalConfig.innerHTML = `
                <div class="zebra-config-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10002; display: flex; justify-content: center; align-items: center;">
                    <div class="zebra-config-content" style="background: white; padding: 30px; border-radius: 15px; max-width: 500px; width: 90%;">
                        <h3 style="margin-top: 0; color: #6f42c1;">🦓 Configuración Zebra ZT230</h3>
                        <p style="color: #666; margin-bottom: 25px;">Configure su impresora Zebra ZT230 para impresión automática de etiquetas</p>
                        
                        <div style="margin: 20px 0;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Método de Conexión:</label>
                            <select id="zebra-metodo-select" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px;" onchange="toggleIPField()">
                                <option value="usb">🔌 USB (Recomendado)</option>
                                <option value="red">🌐 Red Ethernet</option>
                            </select>
                        </div>
                        
                        <div id="ip-field" style="margin: 20px 0; display: none;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">IP de la Impresora:</label>
                            <input type="text" id="zebra-ip-input" value="${ipActual}" 
                                   style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px;" 
                                   placeholder="Ej: 192.168.1.100">
                            <small style="color: #666;">Solo necesario para conexión por red</small>
                        </div>
                        
                        <div style="margin: 20px 0;">
                            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Tipo de Etiqueta:</label>
                            <select id="zebra-tipo-select" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                                <option value="material" ${tipoActual === 'material' ? 'selected' : ''}>Completa - Control de Material</option>
                                <option value="simple" ${tipoActual === 'simple' ? 'selected' : ''}>Simple - Solo QR y Código</option>
                            </select>
                        </div>
                        
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                            <h4 style="margin: 0 0 10px 0; color: #495057; font-size: 14px;">ℹ️ Información:</h4>
                            <p style="margin: 0; font-size: 13px; color: #6c757d;" id="info-conexion">
                                <strong>USB:</strong> La impresora debe estar conectada directamente al servidor por USB. No requiere configuración de red.
                            </p>
                        </div>
                        
                        <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 25px;">
                            <button onclick="zebraConfigCancel()" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                Cancelar
                            </button>
                            <button onclick="zebraConfigTest()" style="padding: 10px 20px; background: #17a2b8; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                🧪 Probar
                            </button>
                            <button onclick="zebraConfigOk()" style="padding: 10px 20px; background: #6f42c1; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                ✅ Guardar Config
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modalConfig);
            
            // Función para mostrar/ocultar campo IP
            window.toggleIPField = () => {
                const metodo = document.getElementById('zebra-metodo-select').value;
                const ipField = document.getElementById('ip-field');
                const infoConexion = document.getElementById('info-conexion');
                
                if (metodo === 'usb') {
                    ipField.style.display = 'none';
                    infoConexion.innerHTML = '<strong>USB:</strong> Zebra ZT230 conectada por USB al servidor. Compatible con comandos ZPL. No requiere IP.';
                } else {
                    ipField.style.display = 'block';
                    infoConexion.innerHTML = '<strong>Red:</strong> Zebra ZT230 en red Ethernet. Puerto 9100 (ZPL) debe estar accesible. Velocidad recomendada: 203-300 DPI.';
                }
            };
            
            // Funciones del modal
            window.zebraConfigCancel = () => {
                modalConfig.remove();
                resolve(null);
            };
            
            window.zebraConfigOk = () => {
                const metodo = document.getElementById('zebra-metodo-select').value;
                const ip = document.getElementById('zebra-ip-input').value.trim();
                const tipo = document.getElementById('zebra-tipo-select').value;
                
                if (metodo === 'red' && !ip) {
                    alert('Por favor ingrese la IP de la impresora para conexión por red');
                    return;
                }
                
                modalConfig.remove();
                resolve({ metodo, ip, tipo });
            };
            
            window.zebraConfigTest = async () => {
                const metodo = document.getElementById('zebra-metodo-select').value;
                const ip = document.getElementById('zebra-ip-input').value.trim();
                const tipo = document.getElementById('zebra-tipo-select').value;
                
                if (metodo === 'red' && !ip) {
                    alert('Por favor ingrese una IP válida para conexión por red');
                    return;
                }
                
                try {
                    mostrarMensajeEnvio('Probando conexión...');
                    
                    const testZPL = generarComandoZPL('TEST123', tipo);
                    const requestData = {
                        metodo_conexion: metodo,
                        comando_zpl: testZPL,
                        codigo: 'TEST123',
                        tipo_etiqueta: tipo
                    };
                    
                    if (metodo === 'red') {
                        requestData.ip_impresora = ip;
                    }
                    
                    const response = await fetch('/imprimir_zebra', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(requestData)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok && result.success) {
                        const metodoTexto = metodo === 'usb' ? 'USB' : 'Red';
                        
                        // Verificar si es método manual
                        if (result.metodo === 'archivo_manual') {
                            let instrucciones = '';
                            if (Array.isArray(result.instrucciones)) {
                                instrucciones = result.instrucciones.join('\n');
                            } else {
                                instrucciones = result.instrucciones || 'Use software de impresión ZPL';
                            }
                            
                            const mensajeDetallado = `
📁 Prueba ZT230: Archivo ZPL creado

📍 Ubicación: ${result.archivo || 'Archivo temporal'}

📋 Para probar manualmente:
${instrucciones}

💡 Comando alternativo:
${result.comando_manual || 'Use clic derecho → Imprimir'}

✅ Si ve la etiqueta TEST123, la conexión funciona!
                            `.trim();
                            
                            mostrarMensajeExito(mensajeDetallado);
                        } else {
                            mostrarMensajeExito(`✅ Conexión ${metodoTexto} exitosa! Se imprimió etiqueta de prueba (${result.metodo})`);
                        }
                    } else {
                        mostrarMensajeError('❌ Error: ' + result.error);
                    }
                    
                } catch (error) {
                    mostrarMensajeError('❌ Error de conexión: ' + error.message);
                }
            };
            
            // Configurar estado inicial
            toggleIPField();
            
            // Focus en el campo apropiado
            setTimeout(() => {
                const metodoSelect = document.getElementById('zebra-metodo-select');
                if (metodoSelect) metodoSelect.focus();
            }, 100);
        });
    }
    
    // Función para generar comando ZPL
    function generarComandoZPL(codigo, tipo = 'material') {
        const fechaHora = new Date().toLocaleString('es-ES');
        const fecha = new Date().toLocaleDateString('es-ES');
        const hora = new Date().toLocaleTimeString('es-ES');
        
        let zplCommand;
        
        if (tipo === 'simple') {
            // Etiqueta simple optimizada para ZT230 - Solo QR y código
            zplCommand = `
^XA
^CI28
^PW400
^LL240
^FO80,50^BQN,2,8^FDLA,${codigo}^FS
^FO50,280^CFO,25,15^FD${codigo}^FS
^FO50,320^CFO,15,10^FD${fecha} ${hora}^FS
^XZ
            `.trim();
        } else {
            // Etiqueta completa para ZT230 - Control de material
            zplCommand = `
^XA
^CI28
^LH0,0
^PW600
^LL400
^CFO,20,12
^FO30,30^FD*** CONTROL DE MATERIAL - ALMACEN ***^FS
^CFO,18,10
^FO30,60^FDCodigo Material Recibido:^FS
^CFO,25,15
^FO30,85^FD${codigo}^FS
^CFO,15,10
^FO30,120^FDFecha: ${fecha}^FS
^FO30,140^FDHora: ${hora}^FS
^FO30,160^FDSistema: ISEMM MES^FS
^FO30,180^FDUsuario: ${window.usuario || 'N/A'}^FS
^FO320,60^BQN,2,6^FDLA,${codigo}^FS
^CFO,12,8
^FO30,220^FD*** ZEBRA ZT230 ***^FS
^XZ
            `.trim();
        }
        
        console.log('📝 Comando ZPL ZT230 generado:', zplCommand);
        return zplCommand;
    }
    
    // Funciones de mensajes para mejor UX
    function mostrarMensajeEnvio(mensaje) {
        mostrarNotificacion(mensaje, 'info');
    }
    
    function mostrarMensajeExito(mensaje) {
        mostrarNotificacion(mensaje, 'success');
    }
    
    function mostrarMensajeError(mensaje) {
        mostrarNotificacion(mensaje, 'error');
    }
    
    function mostrarNotificacion(mensaje, tipo) {
        // Remover notificación anterior
        const notifAnterior = document.getElementById('zebra-notification');
        if (notifAnterior) {
            notifAnterior.remove();
        }
        
        const colores = {
            info: '#17a2b8',
            success: '#28a745', 
            error: '#dc3545'
        };
        
        const iconos = {
            info: '🔄',
            success: '✅',
            error: '❌'
        };
        
        const notificacion = document.createElement('div');
        notificacion.id = 'zebra-notification';
        notificacion.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${colores[tipo]};
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10003;
            font-family: Arial, sans-serif;
            font-size: 14px;
            max-width: 350px;
            animation: slideIn 0.3s ease-out;
        `;
        
        notificacion.innerHTML = `${iconos[tipo]} ${mensaje}`;
        
        // Añadir animación CSS
        if (!document.getElementById('zebra-notification-styles')) {
            const styles = document.createElement('style');
            styles.id = 'zebra-notification-styles';
            styles.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(styles);
        }
        
        document.body.appendChild(notificacion);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (notificacion && notificacion.parentNode) {
                notificacion.style.animation = 'slideIn 0.3s ease-out reverse';
                setTimeout(() => notificacion.remove(), 300);
            }
        }, 5000);
    }
    
    // Función para generar archivo ZPL descargable
    function generarArchivoZPL(codigo, tipo = 'material') {
        try {
            const comandoZPL = generarComandoZPL(codigo, tipo);
            
            // Crear blob con el comando ZPL
            const blob = new Blob([comandoZPL], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            
            // Crear enlace de descarga
            const link = document.createElement('a');
            link.href = url;
            link.download = `etiqueta_zebra_${codigo.replace(/[^a-zA-Z0-9]/g, '_')}_${tipo}.zpl`;
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            window.URL.revokeObjectURL(url);
            
            mostrarMensajeExito('📁 Archivo ZPL descargado. Puede enviarlo directamente a la impresora Zebra.');
            console.log('✅ Archivo ZPL descargado:', codigo);
            
        } catch (error) {
            console.error('❌ Error al generar archivo ZPL:', error);
            mostrarMensajeError('Error al generar el archivo ZPL');
        }
    }
    
    // API pública del módulo
    return {
        generarQR: generarQR,
        cerrarModal: cerrarModal,
        descargarQR: descargarQR,
        imprimirQR: imprimirQR,
        imprimirZebra: imprimirZebra,
        configurarImpresora: mostrarModalConfiguracionZebra
    };

})();

// Función global para configurar impresora (llamada desde botón "Conf. de impresora")
window.configurarImpresoraZebra = async function() {
    try {
        console.log('🔧 Configurando impresora Zebra...');
        
        // Obtener configuración actual
        const configActual = localStorage.getItem('zebra_config');
        let ipActual = '192.168.1.100';
        let tipoActual = 'material';
        let metodoActual = 'usb';
        
        if (configActual) {
            const config = JSON.parse(configActual);
            ipActual = config.ip || ipActual;
            tipoActual = config.tipo || tipoActual;
            metodoActual = config.metodo || metodoActual;
        }
        
        // Mostrar modal de configuración
        const resultado = await QRAlmacenSimple.configurarImpresora(ipActual, tipoActual);
        
        if (resultado && (resultado.metodo === 'usb' || resultado.ip)) {
            // Guardar configuración
            const nuevaConfig = {
                metodo: resultado.metodo,
                ip: resultado.ip || '',
                tipo: resultado.tipo,
                fecha_config: new Date().toISOString(),
                usuario: window.usuario || 'N/A'
            };
            
            localStorage.setItem('zebra_config', JSON.stringify(nuevaConfig));
            
            // Mostrar confirmación
            const tipoTexto = resultado.tipo === 'simple' ? 'Simple' : 'Completa';
            const metodoTexto = resultado.metodo === 'usb' ? 'USB' : `Red (${resultado.ip})`;
            
            alert(`✅ Impresora Zebra configurada exitosamente:\n\n� Conexión: ${metodoTexto}\n📋 Tipo: ${tipoTexto}\n\nAhora las etiquetas se imprimirán automáticamente después de guardar.`);
            
            console.log('✅ Configuración Zebra guardada:', nuevaConfig);
        } else {
            console.log('❌ Configuración cancelada');
        }
        
    } catch (error) {
        console.error('❌ Error al configurar impresora:', error);
        alert('Error al configurar la impresora: ' + error.message);
    }
};

// Función para mostrar configuración actual
window.mostrarConfigZebra = function() {
    const config = localStorage.getItem('zebra_config');
    if (config) {
        const cfg = JSON.parse(config);
        const tipoTexto = cfg.tipo === 'simple' ? 'Simple' : 'Completa';
        const metodoTexto = cfg.metodo === 'usb' ? 'USB' : `Red (${cfg.ip || 'Sin IP'})`;
        alert(`📋 Configuración actual de Zebra:\n\n� Conexión: ${metodoTexto}\n📋 Tipo: ${tipoTexto}\n📅 Configurado: ${new Date(cfg.fecha_config).toLocaleString('es-ES')}\n👤 Usuario: ${cfg.usuario}`);
    } else {
        alert('⚠️ No hay configuración de impresora guardada.\nUse "Conf. de impresora" para configurarla.');
    }
};

console.log('✅ QR Almacén Simple cargado correctamente');
