/* =============================================================
   SALIDAS MASIVAS - MÓDULO INDEPENDIENTE
   ============================================================= */

// Variables globales del módulo
let materialesMasivos = [];
let contadorEscaneados = 0;
let contadorValidos = 0;
let contadorErrores = 0;
let escaneoMasivoPausado = false;

/* =============================================================
   FUNCIÓN PRINCIPAL - ABRIR MODAL
   ============================================================= */
function abrirModalSalidasMasivas() {
    console.log('Abriendo modal de salidas masivas...');
    
    // Verificar si el modal ya existe
    let modal = document.getElementById('modalSalidasMasivas');
    if (modal) {
        modal.remove();
    }
    
    // Crear el modal dinámicamente
    crearModalSalidasMasivas();
    
    // Mostrar el modal
    modal = document.getElementById('modalSalidasMasivas');
    modal.style.display = 'flex';
    
    limpiarEscaneoMasivo();
    
    setTimeout(() => {
        const input = document.getElementById('inputEscaneoMasivo');
        if (input) {
            input.focus();
            configurarListenersEscaneoMasivo();
        }
    }, 100);
    
    console.log('Modal de salidas masivas abierto');
}

/* =============================================================
   CREAR MODAL DINÁMICAMENTE
   ============================================================= */
function crearModalSalidasMasivas() {
    const modalHTML = `
        <div id="modalSalidasMasivas" class="modal-overlay" style="display: none; position: fixed; z-index: 10000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.7); align-items: center; justify-content: center;">
            <div class="modal-container" style="background-color: #40424F; padding: 25px; border-radius: 8px; width: 90%; max-width: 900px; height: 80vh; color: #ecf0f1; font-family: 'Segoe UI', sans-serif; box-shadow: 0 4px 20px rgba(0,0,0,0.5); display: flex; flex-direction: column;">
                
                <!-- Header con estilo trazabilidad -->
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin: 0; font-size: 20px; font-weight: 600;">SALIDAS RAPIDO</h2>
                    <button class="modal-close" onclick="cerrarModalSalidasMasivas()" style="background: none; border: none; font-size: 24px; color: #e74c3c; cursor: pointer; padding: 5px; border-radius: 50%; width: 35px; height: 35px; display: flex; align-items: center; justify-content: center; transition: background-color 0.3s;" onmouseover="this.style.backgroundColor='#e74c3c'; this.style.color='white';" onmouseout="this.style.backgroundColor='transparent'; this.style.color='#e74c3c';">&times;</button>
                </div>
                
                <div class="modal-body" style="display: flex; flex-direction: column; gap: 20px; flex: 1; min-height: 0;">
                    
                    <!-- Panel de escaneo arriba con estilo trazabilidad -->
                    <div class="panel-escaneo" style="background-color: #2c3e50; padding: 15px; border-radius: 4px; border: 2px dashed #3498db;">
                        <div style="display: flex; gap: 20px; align-items: flex-start;">
                            <div style="flex: 1;">
                                <h4 style="margin: 0 0 15px 0; color: #3498db; font-size: 16px; font-weight: 600;">ESCANEAR CÓDIGOS</h4>
                                <input type="text" id="inputEscaneoMasivo" placeholder="Escanear aquí (automático con Enter)" 
                                       style="font-size: 16px; padding: 12px; width: 100%; border: 1px solid #95a5a6; 
                                              background-color: #e3f2fd; color: #2c3e50; font-weight: bold; border-radius: 4px;
                                              box-sizing: border-box; font-family: monospace;">
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 15px;">
                                <div class="escaneo-stats" style="background-color: #40424F; padding: 10px 15px; border-radius: 4px; 
                                                                  font-size: 13px; color: #ecf0f1; font-weight: 500; white-space: nowrap; border: 1px solid #3498db;">
                                    <span id="contadorEscaneados">0</span> escaneados | 
                                    <span id="contadorValidos" style="color: #27ae60;">0</span> válidos | 
                                    <span id="contadorErrores" style="color: #e74c3c;">0</span> errores
                                </div>
                                <div style="display: flex; gap: 10px;">
                                    <button class="trazabilidad-btn danger" onclick="limpiarEscaneoMasivo()" 
                                            style="padding: 8px 15px; font-size: 13px; white-space: nowrap; border: none; border-radius: 4px; cursor: pointer; color: white; transition: background-color 0.3s; background-color: #e74c3c;" 
                                            onmouseover="this.style.backgroundColor='#c0392b';" onmouseout="this.style.backgroundColor='#e74c3c';">Limpiar todo</button>
                                    <button class="trazabilidad-btn" onclick="pausarEscaneoMasivo()" id="btnPausar" 
                                            style="padding: 8px 15px; font-size: 13px; white-space: nowrap; border: none; border-radius: 4px; cursor: pointer; color: white; transition: background-color 0.3s; background-color: #f39c12;"
                                            onmouseover="this.style.backgroundColor='#e67e22';" onmouseout="this.style.backgroundColor='#f39c12';">Pausar</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Panel de materiales abajo con estilo trazabilidad -->
                    <div class="panel-materiales" style="flex: 1; display: flex; flex-direction: column; min-height: 0; background-color: #2c3e50; padding: 15px; border-radius: 4px;">
                        <div class="materiales-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h4 style="margin: 0; color: #3498db; font-size: 16px; font-weight: 600;">MATERIALES PARA SALIDA</h4>
                            <button class="trazabilidad-btn primary" onclick="procesarSalidasMasivas()" id="btnProcesarMasivo" 
                                    style="padding: 10px 20px; font-size: 14px; border: none; border-radius: 4px; cursor: pointer; color: white; transition: background-color 0.3s; background-color: #3498db; font-weight: bold;" disabled
                                    onmouseover="if(!this.disabled) this.style.backgroundColor='#2980b9';" onmouseout="if(!this.disabled) this.style.backgroundColor='#3498db';">
                                PROCESAR TODAS LAS SALIDAS
                            </button>
                        </div>
                        <div class="materiales-lista" style="flex: 1; overflow-y: auto; border: 1px solid #95a5a6; border-radius: 4px; background-color: #40424F;">
                            <table class="material-table" style="font-size: 12px; width: 100%; table-layout: fixed; border-collapse: collapse;">
                                <thead>
                                    <tr>
                                        <th style="background-color: #34495e; color: #ecf0f1; padding: 10px 8px; border: 1px solid #2c3e50; width: 30%; font-weight: 600;">Código</th>
                                        <th style="background-color: #34495e; color: #ecf0f1; padding: 10px 8px; border: 1px solid #2c3e50; width: 35%; font-weight: 600;">Número Parte</th>
                                        <th style="background-color: #34495e; color: #ecf0f1; padding: 10px 8px; border: 1px solid #2c3e50; width: 15%; font-weight: 600;">Stock</th>
                                        <th style="background-color: #34495e; color: #ecf0f1; padding: 10px 8px; border: 1px solid #2c3e50; width: 20%; font-weight: 600;">Estado</th>
                                    </tr>
                                </thead>
                                <tbody id="tablaMaterialesMasivos">
                                    <tr>
                                        <td colspan="4" style="text-align: center; padding: 20px; color: #7f8c8d; font-style: italic;">
                                            Escanee códigos para ver materiales aquí...
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Insertar el modal en el body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Agregar listener para cerrar al hacer clic fuera del modal
    const modal = document.getElementById('modalSalidasMasivas');
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            cerrarModalSalidasMasivas();
        }
    });
    
    // Agregar listener para cerrar con ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            cerrarModalSalidasMasivas();
        }
    });
    
    console.log('Modal creado dinámicamente con listeners');
}

/* =============================================================
   CERRAR MODAL
   ============================================================= */
function cerrarModalSalidasMasivas() {
    const modal = document.getElementById('modalSalidasMasivas');
    if (modal) {
        modal.style.display = 'none';
        // Eliminar el modal después de un breve delay
        setTimeout(() => {
            modal.remove();
        }, 300);
    }
    limpiarEscaneoMasivo();
    console.log('Modal de salidas masivas cerrado');
}

/* =============================================================
   CONFIGURAR LISTENERS DE ESCANEO INTELIGENTES
   ============================================================= */
function configurarListenersEscaneoMasivo() {
    const input = document.getElementById('inputEscaneoMasivo');
    if (!input) return;
    
    // Limpiar listeners previos
    const nuevo = input.cloneNode(true);
    input.parentNode.replaceChild(nuevo, input);
    const inputRef = document.getElementById('inputEscaneoMasivo');
    
    // Variables para control inteligente
    let yaFueProcesado = false;
    let timeoutEscaneoFinal = null;
    let ultimoTamano = 0;
    
    // ENTER MANUAL - SIEMPRE FUNCIONA
    inputRef.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') {
            ev.preventDefault();
            if (!escaneoMasivoPausado) {
                const codigo = ev.target.value.trim();
                if (codigo && codigo.length >= 8 && !yaFueProcesado) {
                    // Limpiar timeout si existe
                    if (timeoutEscaneoFinal) clearTimeout(timeoutEscaneoFinal);
                    
                    yaFueProcesado = true;
                    ev.target.value = ''; // LIMPIAR INMEDIATAMENTE
                    
                    // PROCESAR EN SEGUNDO PLANO (NO AWAIT)
                    procesarEscaneoMasivoItem(codigo).catch(console.error);
                    
                    // Resetear
                    setTimeout(() => {
                        yaFueProcesado = false;
                        ultimoTamano = 0;
                    }, 200);
                }
            }
        }
    });
    
    // DETECCIÓN INTELIGENTE PARA ESCÁNER QUE ESCRIBE POCO A POCO
    inputRef.addEventListener('input', async (ev) => {
        if (escaneoMasivoPausado) return;
        
        const val = ev.target.value.trim();
        const tamanoActual = val.length;
        
        // Si ya fue procesado, no hacer nada
        if (yaFueProcesado) return;
        
        // Limpiar timeout anterior
        if (timeoutEscaneoFinal) {
            clearTimeout(timeoutEscaneoFinal);
        }
        
        // Solo si el código está creciendo y es suficientemente largo
        if (tamanoActual > ultimoTamano && tamanoActual >= 15) {
            ultimoTamano = tamanoActual;
            
            // Trigger más agresivo para códigos muy largos (probablemente completos)
            if (tamanoActual >= 25) {
                // Para códigos muy largos, timeout más corto
                timeoutEscaneoFinal = setTimeout(() => {
                    const codigoFinal = ev.target.value.trim();
                    if (codigoFinal.length >= 15 && 
                        codigoFinal === val && 
                        !yaFueProcesado &&
                        !escaneoMasivoPausado) {
                        
                        yaFueProcesado = true;
                        ev.target.value = ''; // LIMPIAR INMEDIATAMENTE
                        
                        // PROCESAR EN SEGUNDO PLANO (NO AWAIT)
                        procesarEscaneoMasivoItem(codigoFinal).catch(console.error);
                        
                        setTimeout(() => {
                            yaFueProcesado = false;
                            ultimoTamano = 0;
                        }, 200);
                    }
                }, 150); // Solo 150ms para códigos muy largos
            } else {
                // Timeout de 300ms - RÁPIDO pero seguro para códigos normales
                timeoutEscaneoFinal = setTimeout(() => {
                    const codigoFinal = ev.target.value.trim();
                    if (codigoFinal.length >= 15 && 
                        codigoFinal === val && 
                        !yaFueProcesado &&
                        !escaneoMasivoPausado) {
                        
                        yaFueProcesado = true;
                        ev.target.value = ''; // LIMPIAR INMEDIATAMENTE
                        
                        // PROCESAR EN SEGUNDO PLANO (NO AWAIT)
                        procesarEscaneoMasivoItem(codigoFinal).catch(console.error);
                        
                        setTimeout(() => {
                            yaFueProcesado = false;
                            ultimoTamano = 0;
                        }, 200);
                    }
                }, 300); // 300ms sin nuevos caracteres = RÁPIDO
            }
        } else {
            ultimoTamano = tamanoActual;
        }
    });
    
    // PASTE - PARA ESCÁNERES QUE FUNCIONAN COMO PASTE
    inputRef.addEventListener('paste', async (ev) => {
        if (escaneoMasivoPausado || yaFueProcesado) return;
        
        setTimeout(async () => {
            const val = ev.target.value.trim();
            if (val.length >= 8 && !yaFueProcesado) {
                yaFueProcesado = true;
                await procesarEscaneoMasivoItem(val);
                ev.target.value = '';
                
                // Resetear
                setTimeout(() => {
                    yaFueProcesado = false;
                    ultimoTamano = 0;
                }, 200);
            }
        }, 50);
    });
    
    inputRef.focus();
}

/* =============================================================
   ⚡ PROCESAR ITEM ESCANEADO
   ============================================================= */
async function procesarEscaneoMasivoItem(codigo) {
    if (!codigo || escaneoMasivoPausado) return;
    
    contadorEscaneados++;
    actualizarContadores();
    
    // Verificar si ya existe en la lista
    const existe = materialesMasivos.find(m => m.codigo === codigo);
    if (existe) {
        return;
    }
    
    try {
        // USAR EL MISMO ENDPOINT QUE LA PANTALLA PRINCIPAL
        const response = await fetch(`/buscar_material_por_codigo?codigo_recibido=${encodeURIComponent(codigo)}`);
        const data = await response.json();
        
        if (data.success && data.material) {
            const material = data.material;
            const stock = parseFloat(material.cantidad_actual) || 0;
            
            if (stock > 0) {
                // Material válido con stock
                const materialMasivo = {
                    codigo: codigo,
                    numero_parte: material.numero_parte || 'N/A',
                    stock: stock,
                    estado: 'LISTO',
                    data: material // Guardar todos los datos del material
                };
                
                materialesMasivos.push(materialMasivo);
                contadorValidos++;
                
            } else {
                // Material encontrado pero sin stock
                const materialMasivo = {
                    codigo: codigo,
                    numero_parte: material.numero_parte || 'N/A',
                    stock: 0,
                    estado: 'SIN STOCK',
                    error: 'Stock insuficiente'
                };
                
                materialesMasivos.push(materialMasivo);
                contadorErrores++;
            }
            
        } else {
            // Material no encontrado
            const materialMasivo = {
                codigo: codigo,
                numero_parte: 'N/A',
                stock: 0,
                estado: 'NO ENCONTRADO',
                error: data.error || 'Material no encontrado'
            };
            
            materialesMasivos.push(materialMasivo);
            contadorErrores++;
        }
        
        } catch (error) {
            // Error de conexión o problema en la petición
            const materialMasivo = {
                codigo: codigo,
                numero_parte: 'ERROR',
                stock: 0,
                estado: 'ERROR',
                error: 'Error de conexión'
            };
            
            materialesMasivos.push(materialMasivo);
            contadorErrores++;
        }
        
        actualizarTablaMateriales();
        actualizarContadores();
        habilitarBotonProcesar();
    }

/* =============================================================
   ACTUALIZAR TABLA DE MATERIALES
   ============================================================= */
function actualizarTablaMateriales() {
    const tbody = document.getElementById('tablaMaterialesMasivos');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (materialesMasivos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 20px; color: #bdc3c7; font-style: italic; background-color: #40424F;">
                    Escanee códigos para ver materiales aquí...
                </td>
            </tr>
        `;
        return;
    }
    
    materialesMasivos.forEach((material, index) => {
        const row = document.createElement('tr');
        row.className = material.estado === 'LISTO' ? 'material-masivo-valido' : 
                       material.estado === 'PROCESADO' ? 'material-masivo-procesado' : 
                       'material-masivo-error';
        
        row.innerHTML = `
            <td style="padding: 10px 8px; border: 1px solid #34495e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; background-color: inherit;" title="${material.codigo}">${material.codigo}</td>
            <td style="padding: 10px 8px; border: 1px solid #34495e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; background-color: inherit;" title="${material.numero_parte}">${material.numero_parte}</td>
            <td style="padding: 10px 8px; border: 1px solid #34495e; text-align: center; background-color: inherit; font-weight: 600;">${material.stock}</td>
            <td style="padding: 10px 8px; border: 1px solid #34495e; text-align: center; font-weight: bold; background-color: inherit;">${material.estado}</td>
        `;
        
        tbody.appendChild(row);
    });
}

/* =============================================================
   🔢 ACTUALIZAR CONTADORES
   ============================================================= */
function actualizarContadores() {
    const escaneados = document.getElementById('contadorEscaneados');
    const validos = document.getElementById('contadorValidos');
    const errores = document.getElementById('contadorErrores');
    
    if (escaneados) escaneados.textContent = contadorEscaneados;
    if (validos) validos.textContent = contadorValidos;
    if (errores) errores.textContent = contadorErrores;
}

/* =============================================================
   🔘 HABILITAR BOTÓN PROCESAR
   ============================================================= */
function habilitarBotonProcesar() {
    const btn = document.getElementById('btnProcesarMasivo');
    if (!btn) return;
    
    const materialesListos = materialesMasivos.filter(m => m.estado === 'LISTO').length;
    
    if (materialesListos > 0) {
        btn.disabled = false;
        btn.textContent = `PROCESAR ${materialesListos} SALIDAS`;
    } else {
        btn.disabled = true;
        btn.textContent = 'PROCESAR TODAS LAS SALIDAS';
    }
}

/* =============================================================
   ⏸️ PAUSAR/REANUDAR ESCANEO
   ============================================================= */
function pausarEscaneoMasivo() {
    escaneoMasivoPausado = !escaneoMasivoPausado;
    const btn = document.getElementById('btnPausar');
    
    if (escaneoMasivoPausado) {
        btn.textContent = 'Reanudar';
        btn.style.backgroundColor = '#27ae60';
    } else {
        btn.textContent = 'Pausar';
        btn.style.backgroundColor = '#f39c12';
        
        setTimeout(() => {
            const input = document.getElementById('inputEscaneoMasivo');
            if (input) input.focus();
        }, 100);
    }
}

/* =============================================================
   LIMPIAR ESCANEO MASIVO
   ============================================================= */
function limpiarEscaneoMasivo() {
    materialesMasivos = [];
    contadorEscaneados = 0;
    contadorValidos = 0;
    contadorErrores = 0;
    escaneoMasivoPausado = false;
    
    actualizarContadores();
    actualizarTablaMateriales();
    habilitarBotonProcesar();
    
    const btn = document.getElementById('btnPausar');
    if (btn) {
        btn.textContent = 'Pausar';
        btn.style.backgroundColor = '#f39c12';
    }
}

/* =============================================================
   PROCESAR SALIDAS MASIVAS
   ============================================================= */
async function procesarSalidasMasivas() {
    const materialesListos = materialesMasivos.filter(m => m.estado === 'LISTO');
    
    if (materialesListos.length === 0) {
        alert('No hay materiales listos para procesar');
        return;
    }
    
    const btn = document.getElementById('btnProcesarMasivo');
    btn.disabled = true;
    btn.textContent = 'PROCESANDO...';
    
    let exitosos = 0;
    let fallidos = 0;
    
    for (const material of materialesListos) {
        try {
            // Obtener datos completos del material usando su data guardada
            const materialData = material.data;
            const modelo = document.getElementById('salida_modelo')?.value || 'SIN_MODELO';
            const fechaSalida = document.getElementById('salida_fecha_salida_form')?.value || new Date().toISOString().split('T')[0];
            
            const payload = {
                codigo_material_recibido: material.codigo,
                cantidad_salida: material.stock,
                modelo: modelo,
                numero_lote: materialData.numero_lote_material || '',
                fecha_salida: fechaSalida,
                depto_salida: 'Producción',
                proceso_salida: 'SMT 1st SIDE',
                codigo_verificacion: 'AUTO_MASIVO'
            };
            
            const response = await fetch('/procesar_salida_material', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (data.success) {
                material.estado = 'PROCESADO';
                exitosos++;
            } else {
                material.estado = 'ERROR';
                material.error = data.error;
                fallidos++;
            }
            
        } catch (error) {
            material.estado = 'ERROR';
            material.error = 'Error de conexión';
            fallidos++;
        }
        
        actualizarTablaMateriales();
        
        // Pequeña pausa para no sobrecargar el servidor
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // Mostrar resultado final
    alert(`Procesamiento completo: ${exitosos} exitosos, ${fallidos} fallidos`);
    
    btn.disabled = false;
    btn.textContent = 'PROCESAR TODAS LAS SALIDAS';
    
    // Mostrar mensaje en la interfaz principal si existe la función
    if (typeof mostrarMensajeSimple === 'function') {
        mostrarMensajeSimple(`Salidas masivas: ${exitosos} exitosos, ${fallidos} fallidos`, exitosos > 0 ? 'success' : 'error');
    }
}

/* =============================================================
   EXPOSICIÓN GLOBAL DE FUNCIONES
   ============================================================= */
// Hacer las funciones disponibles globalmente para uso con onclick
window.abrirModalSalidasMasivas = abrirModalSalidasMasivas;
window.cerrarModalSalidasMasivas = cerrarModalSalidasMasivas;
window.configurarListenersEscaneoMasivo = configurarListenersEscaneoMasivo;
window.procesarEscaneoMasivoItem = procesarEscaneoMasivoItem;
window.pausarEscaneoMasivo = pausarEscaneoMasivo;
window.limpiarEscaneoMasivo = limpiarEscaneoMasivo;
window.procesarSalidasMasivas = procesarSalidasMasivas;
