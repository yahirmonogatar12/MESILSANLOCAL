/* =====================================================================
   admin_auditoria.js — lógica de la pantalla de Auditoría del Sistema.
   Cargado con defer; las funciones usadas desde onclick= en el HTML se
   exponen en window al final del archivo.
   ===================================================================== */

let usuarios = [];
let registrosAuditoria = [];

// Escapar texto para evitar inyección de HTML al renderizar datos del servidor
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Toast de notificación con estilo (sustituye alert())
function mostrarNotificacion(mensaje, tipo = 'success') {
    const clase = tipo === 'success' ? 'alert-success' : tipo === 'warning' ? 'alert-warning' : 'alert-danger';
    const toast = document.createElement('div');
    toast.className = `alert ${clase} alert-dismissible fade show`;
    toast.style.cssText = 'position:fixed;top:20px;right:20px;z-index:1090;min-width:300px;box-shadow:var(--shadow-md);';
    toast.innerHTML = `${escapeHtml(mensaje)}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(toast);
    setTimeout(() => { if (toast.parentNode) toast.parentNode.removeChild(toast); }, tipo === 'warning' ? 5000 : 3500);
}

// Confirmación con modal de estilo (sustituye confirm() nativo). Devuelve promesa true/false.
function confirmarAccion(mensaje, { titulo = 'Confirmar', textoOk = 'Aceptar', estiloOk = 'btn-primary' } = {}) {
    return new Promise(resolve => {
        const modalEl = document.getElementById('modalConfirmar');
        document.getElementById('modalConfirmarMensaje').textContent = mensaje;
        document.getElementById('modalConfirmarTitulo').innerHTML =
            `<i class="fas fa-circle-question text-info me-1"></i> ${titulo}`;
        const okBtn = document.getElementById('modalConfirmarOk');
        okBtn.className = `btn ${estiloOk}`;
        okBtn.innerHTML = `<i class="fas fa-check"></i> ${textoOk}`;

        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        let aceptado = false;
        const onOk = () => { aceptado = true; modal.hide(); };
        const onHidden = () => {
            okBtn.removeEventListener('click', onOk);
            modalEl.removeEventListener('hidden.bs.modal', onHidden);
            resolve(aceptado);
        };
        okBtn.addEventListener('click', onOk);
        modalEl.addEventListener('hidden.bs.modal', onHidden);
        modal.show();
    });
}

// Cargar datos iniciales
document.addEventListener('DOMContentLoaded', function() {
    // Establecer fecha por defecto (últimos 7 días)
    const hoy = new Date();
    const hace7dias = new Date(hoy.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    document.getElementById('fechaInicio').value = hace7dias.toISOString().split('T')[0];
    document.getElementById('fechaFin').value = hoy.toISOString().split('T')[0];
    
    cargarUsuarios();
    buscarAuditoria();
    iniciarActividadReciente();
});

async function cargarUsuarios() {
    try {
        const response = await fetch('/admin/listar_usuarios');
        usuarios = await response.json();
        
        const select = document.getElementById('filtroUsuario');
        usuarios.forEach(user => {
            const option = document.createElement('option');
            option.value = user.username;
            option.textContent = user.username;
            select.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error cargando usuarios:', error);
    }
}

async function buscarAuditoria() {
    const loading = document.getElementById('loading');
    const tbody = document.getElementById('auditoriaTableBody');
    
    try {
        loading.style.display = 'block';
        
        const filtros = new URLSearchParams({
            fecha_inicio: document.getElementById('fechaInicio').value,
            fecha_fin: document.getElementById('fechaFin').value,
            usuario: document.getElementById('filtroUsuario').value,
            modulo: document.getElementById('filtroModulo').value,
            resultado: document.getElementById('filtroResultado').value,
            limite: 500
        });
        
        const response = await fetch(`/admin/buscar_auditoria?${filtros}`);
        const data = await response.json();
        
        registrosAuditoria = data.registros;
        
        // Actualizar estadísticas
        actualizarEstadisticas(data.estadisticas);
        
        // Renderizar tabla
        tbody.innerHTML = registrosAuditoria.map(log => {
            const descripcion = escapeHtml(log.descripcion) || '-';
            return `
            <tr class="${log.resultado === 'ERROR' ? 'table-danger' : ''}">
                <td>
                    <small>${formatearFecha(log.fecha_hora)}</small>
                </td>
                <td>
                    <span class="badge bg-secondary">${escapeHtml(log.usuario)}</span>
                </td>
                <td>
                    <span class="badge bg-info">${escapeHtml(log.modulo)}</span>
                </td>
                <td>
                    <small>${escapeHtml(log.accion)}</small>
                </td>
                <td>
                    <small class="text-truncate d-inline-block" style="max-width: 200px;" title="${descripcion}">${descripcion}</small>
                </td>
                <td class="d-none d-md-table-cell">
                    <small>${escapeHtml(log.ip_address) || '-'}</small>
                </td>
                <td>
                    ${getResultadoBadge(log.resultado)}
                </td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="verDetallesAuditoria(${Number(log.id)})" title="Ver detalles">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
        }).join('');

        if (registrosAuditoria.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted py-4">
                        <i class="fas fa-search fa-2x mb-2"></i>
                        <div>No se encontraron registros con los filtros aplicados</div>
                    </td>
                </tr>
            `;
        }
        
    } catch (error) {
        console.error('Error buscando auditoría:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-danger py-4">
                    <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                    <div>Error cargando registros de auditoría</div>
                    <small>Intente nuevamente en unos momentos</small>
                </td>
            </tr>
        `;
    } finally {
        loading.style.display = 'none';
    }
}

function formatearFecha(fechaStr) {
    const fecha = new Date(fechaStr);
    const isMobile = window.innerWidth < 768;
    
    if (isMobile) {
        return fecha.toLocaleString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } else {
        return fecha.toLocaleString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            year: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
}

function getResultadoBadge(resultado) {
    const badges = {
        'EXITOSO': '<span class="badge bg-success">Exitoso</span>',
        'ERROR': '<span class="badge bg-danger">Error</span>',
        'DENEGADO': '<span class="badge bg-warning">Denegado</span>'
    };
    return badges[resultado] || '<span class="badge bg-secondary">Desconocido</span>';
}

function actualizarEstadisticas(stats) {
    document.getElementById('totalRegistros').textContent = registrosAuditoria.length;
    document.getElementById('totalExitosos').textContent = stats.exitosos || 0;
    document.getElementById('totalErrores').textContent = stats.errores || 0;
    document.getElementById('totalDenegados').textContent = stats.denegados || 0;
}

async function verDetallesAuditoria(id) {
    try {
        const response = await fetch(`/admin/detalle_auditoria/${id}`);
        const detalle = await response.json();
        
        let contenidoHtml = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Información General</h6>
                    <table class="table table-sm">
                        <tr><td><strong>ID:</strong></td><td>${escapeHtml(detalle.id)}</td></tr>
                        <tr><td><strong>Usuario:</strong></td><td>${escapeHtml(detalle.usuario)}</td></tr>
                        <tr><td><strong>Módulo:</strong></td><td>${escapeHtml(detalle.modulo)}</td></tr>
                        <tr><td><strong>Acción:</strong></td><td>${escapeHtml(detalle.accion)}</td></tr>
                        <tr><td><strong>Resultado:</strong></td><td>${getResultadoBadge(detalle.resultado)}</td></tr>
                        <tr><td><strong>Fecha/Hora:</strong></td><td>${formatearFecha(detalle.fecha_hora)}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Información Técnica</h6>
                    <table class="table table-sm">
                        <tr><td><strong>IP:</strong></td><td>${escapeHtml(detalle.ip_address) || '-'}</td></tr>
                        <tr><td><strong>Endpoint:</strong></td><td>${escapeHtml(detalle.endpoint) || '-'}</td></tr>
                        <tr><td><strong>Método HTTP:</strong></td><td>${escapeHtml(detalle.metodo_http) || '-'}</td></tr>
                        <tr><td><strong>Duración:</strong></td><td>${detalle.duracion_ms ? escapeHtml(detalle.duracion_ms) + 'ms' : '-'}</td></tr>
                    </table>
                </div>
            </div>

            <div class="mt-3">
                <h6>Descripción</h6>
                <div class="alert alert-info">${escapeHtml(detalle.descripcion) || 'Sin descripción'}</div>
            </div>
        `;

        if (detalle.user_agent) {
            contenidoHtml += `
                <div class="mt-3">
                    <h6>User Agent</h6>
                    <pre>${escapeHtml(detalle.user_agent)}</pre>
                </div>
            `;
        }

        if (detalle.datos_antes_json) {
            contenidoHtml += `
                <div class="mt-3">
                    <h6>Datos Anteriores</h6>
                    <pre>${escapeHtml(JSON.stringify(detalle.datos_antes_json, null, 2))}</pre>
                </div>
            `;
        }

        if (detalle.datos_despues_json) {
            contenidoHtml += `
                <div class="mt-3">
                    <h6>Datos Posteriores</h6>
                    <pre>${escapeHtml(JSON.stringify(detalle.datos_despues_json, null, 2))}</pre>
                </div>
            `;
        }
        
        document.getElementById('detallesContent').innerHTML = contenidoHtml;
        new bootstrap.Modal(document.getElementById('modalDetalles')).show();
        
    } catch (error) {
        console.error('Error cargando detalles:', error);
        mostrarNotificacion('Error cargando detalles del registro', 'error');
    }
}

async function exportarAuditoria() {
    try {
        const filtros = new URLSearchParams({
            fecha_inicio: document.getElementById('fechaInicio').value,
            fecha_fin: document.getElementById('fechaFin').value,
            usuario: document.getElementById('filtroUsuario').value,
            modulo: document.getElementById('filtroModulo').value
        });
        
        window.open(`/admin/exportar_auditoria?${filtros}`, '_blank');

    } catch (error) {
        console.error('Error exportando:', error);
        mostrarNotificacion('Error exportando auditoría', 'error');
    }
}

function iniciarActividadReciente() {
    cargarActividadReciente();
    
    // Actualizar cada 10 segundos
    setInterval(cargarActividadReciente, 10000);
}

async function cargarActividadReciente() {
    try {
        const response = await fetch('/admin/actividad_reciente');
        const data = await response.json();
        
        // Usuarios activos
        const usuariosContainer = document.getElementById('usuariosActivosContainer');
        if (data.usuarios_activos.length > 0) {
            usuariosContainer.innerHTML = data.usuarios_activos.map(u => `
                <div class="usuario-activo">
                    <span class="usuario-nombre"><strong>${escapeHtml(u.usuario)}</strong></span>
                    <span class="usuario-accion"><small>${escapeHtml(u.ultima_accion)}</small></span>
                    <span class="usuario-tiempo"><small class="text-muted">${escapeHtml(u.hace)}</small></span>
                </div>
            `).join('');
        } else {
            usuariosContainer.innerHTML = '<div class="text-muted text-center py-3">No hay usuarios activos</div>';
        }
        
        // Últimas acciones
        const accionesContainer = document.getElementById('ultimasAccionesContainer');
        if (data.ultimas_acciones.length > 0) {
            accionesContainer.innerHTML = data.ultimas_acciones.slice(0, 8).map(a => `
                <div class="usuario-activo">
                    <span class="usuario-nombre"><small><strong>${escapeHtml(a.usuario)}</strong></small></span>
                    <span class="usuario-accion"><small>${escapeHtml(a.modulo)}.${escapeHtml(a.accion)}</small></span>
                    <span class="usuario-tiempo"><small class="text-muted">${formatearFecha(a.fecha_hora)}</small></span>
                </div>
            `).join('');
        } else {
            accionesContainer.innerHTML = '<div class="text-muted text-center py-3">No hay acciones recientes</div>';
        }
        
    } catch (error) {
        console.error('Error cargando actividad reciente:', error);
    }
}

// Búsqueda automática al cambiar filtros
document.getElementById('fechaInicio').addEventListener('change', buscarAuditoria);
document.getElementById('fechaFin').addEventListener('change', buscarAuditoria);
document.getElementById('filtroUsuario').addEventListener('change', buscarAuditoria);
document.getElementById('filtroModulo').addEventListener('change', buscarAuditoria);
document.getElementById('filtroResultado').addEventListener('change', buscarAuditoria);

// Detección de cambios en orientación/resize para responsive
window.addEventListener('resize', function() {
    // Re-formatear fechas si es necesario
    const fechaElements = document.querySelectorAll('td:first-child small');
    fechaElements.forEach(el => {
        const fechaOriginal = el.textContent;
        if (fechaOriginal && fechaOriginal !== '-') {
            const fecha = new Date(fechaOriginal);
            if (!isNaN(fecha.getTime())) {
                el.textContent = formatearFecha(fecha.toISOString());
            }
        }
    });
});

// Mejorar scroll horizontal en móvil
const tableContainer = document.querySelector('.auditoria-table-container');
if (tableContainer) {
    let isScrolling = false;
    
    tableContainer.addEventListener('touchstart', function() {
        isScrolling = true;
    });
    
    tableContainer.addEventListener('touchend', function() {
        isScrolling = false;
    });
}

// Función para confirmar logout
async function confirmarLogout() {
    const ok = await confirmarAccion('¿Está seguro que desea cerrar la sesión?', {
        titulo: 'Cerrar sesión', textoOk: 'Cerrar sesión', estiloOk: 'btn-danger'
    });
    if (!ok) return;

    // Mostrar mensaje de cierre
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        color: white;
        font-size: 1.2rem;
        text-align: center;
    `;
    overlay.innerHTML = `
        <div>
            <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
            <div>Cerrando sesión...</div>
        </div>
    `;
    document.body.appendChild(overlay);

    setTimeout(() => {
        window.location.href = '/logout';
    }, 1000);
}

// Exponer a window las funciones llamadas desde onclick= en el HTML
window.buscarAuditoria = buscarAuditoria;
window.exportarAuditoria = exportarAuditoria;
window.verDetallesAuditoria = verDetallesAuditoria;
window.confirmarLogout = confirmarLogout;
