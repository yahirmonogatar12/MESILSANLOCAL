/* =====================================================================
   admin_usuarios.js — lógica de Administración de Usuarios.
   Cargado con defer; las funciones usadas desde onclick= en el HTML se
   exponen en window al final del archivo.
   ===================================================================== */

let usuarios = [];
let roles = [];
let usuarioEditando = null;

// Cargar datos iniciales
document.addEventListener('DOMContentLoaded', function() {
    cargarRoles();
    cargarUsuarios();
});

// Confirmación con modal de estilo (sustituye confirm() nativo).
// Devuelve una promesa que resuelve true/false.
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

// Cargar lista de roles
async function cargarRoles() {
    try {
        const response = await fetch('/admin/listar_roles');
        roles = await response.json();
        
    } catch (error) {
        console.error('Error cargando roles:', error);
    }
}

// Escapar texto para evitar inyección de HTML al renderizar
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Cargar usuarios
async function cargarUsuarios() {
    const loading = document.getElementById('loading');
    const tbody = document.getElementById('usuariosTableBody');

    try {
        loading.style.display = 'block';

        const response = await fetch('/admin/listar_usuarios');
        usuarios = await response.json();

        // Actualizar estadísticas y filtros
        actualizarEstadisticas();
        poblarFiltroDepartamentos();
        aplicarFiltros();

    } catch (error) {
        console.error('Error cargando usuarios:', error);
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="7" class="text-danger">
                    <i class="fas fa-exclamation-triangle"></i> Error cargando usuarios
                </td>
            </tr>
        `;
    } finally {
        loading.style.display = 'none';
    }
}

// Renderiza una lista de usuarios en la tabla
function renderizarUsuarios(lista) {
    const tbody = document.getElementById('usuariosTableBody');

    if (!lista || lista.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="7">
                    <i class="fas fa-user-slash me-1"></i> No hay usuarios que coincidan con los filtros
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = lista.map(user => {
        const username = escapeHtml(user.username);
        const esAdmin = user.username === 'admin';
        return `
            <tr>
                <td>
                    <strong>${username}</strong>
                    ${esAdmin ? '<i class="fas fa-crown text-warning ms-1" title="Super Admin"></i><i class="fas fa-shield-alt text-info ms-1" title="Usuario Protegido"></i>' : ''}
                </td>
                <td>${escapeHtml(user.nombre_completo) || '-'}</td>
                <td>
                    <span class="badge bg-info">${escapeHtml(user.departamento) || 'Sin asignar'}</span>
                </td>
                <td>
                    <small>${(user.roles || []).map(r => `<span class="badge bg-secondary me-1">${escapeHtml(r)}</span>`).join('')}</small>
                </td>
                <td>${getEstadoBadge(user)}</td>
                <td>
                    <small>${user.ultimo_acceso ? new Date(user.ultimo_acceso).toLocaleString() : 'Nunca'}</small>
                </td>
                <td>
                    <div class="user-actions">
                        ${!esAdmin ? `
                            <button class="btn btn-sm btn-info" onclick="editarUsuario('${username}')" title="Editar">
                                <i class="fas fa-edit"></i>
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-secondary" disabled title="Usuario protegido">
                                <i class="fas fa-shield-alt"></i>
                            </button>
                        `}
                        ${!esAdmin ? `
                            <button class="btn btn-sm btn-danger" onclick="confirmarBorrarUsuario('${username}')" title="Borrar Usuario">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                        ${user.bloqueado ? `
                            <button class="btn btn-sm btn-success" onclick="desbloquearUsuario('${username}')" title="Desbloquear">
                                <i class="fas fa-unlock"></i>
                            </button>
                        ` : ''}
                        ${!esAdmin ? `
                            <button class="btn btn-sm ${user.activo ? 'btn-danger' : 'btn-success'}"
                                    onclick="toggleUsuario('${username}', ${!user.activo})"
                                    title="${user.activo ? 'Desactivar' : 'Activar'}">
                                <i class="fas fa-${user.activo ? 'ban' : 'check'}"></i>
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Llena el select de departamentos con los presentes en los usuarios
function poblarFiltroDepartamentos() {
    const select = document.getElementById('departamentoFilter');
    const previo = select.value;
    const departamentos = [...new Set(usuarios.map(u => u.departamento).filter(Boolean))].sort();
    select.innerHTML = '<option value="">Todos</option>' +
        departamentos.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('');
    select.value = previo;
}

// Aplica búsqueda + filtros de estado/departamento y re-renderiza
function aplicarFiltros() {
    const termino = document.getElementById('searchInput').value.toLowerCase().trim();
    const estado = document.getElementById('estadoFilter').value;
    const departamento = document.getElementById('departamentoFilter').value;

    let lista = usuarios.filter(u => {
        if (termino) {
            const campos = [u.username, u.nombre_completo, u.email, u.cargo]
                .map(v => String(v || '').toLowerCase());
            if (!campos.some(c => c.includes(termino))) return false;
        }
        if (estado === 'activo' && !(u.activo && !u.bloqueado)) return false;
        if (estado === 'inactivo' && (u.activo || u.bloqueado)) return false;
        if (estado === 'bloqueado' && !u.bloqueado) return false;
        if (departamento && u.departamento !== departamento) return false;
        return true;
    });

    renderizarUsuarios(lista);
    const resultado = document.getElementById('resultadoFiltro');
    resultado.textContent = lista.length === usuarios.length
        ? `${lista.length} usuarios`
        : `${lista.length} de ${usuarios.length} usuarios`;
}

function getEstadoBadge(user) {
    if (user.bloqueado) {
        return '<span class="badge bg-warning"><i class="fas fa-lock"></i> Bloqueado</span>';
    } else if (user.activo) {
        return '<span class="badge bg-success"><i class="fas fa-check"></i> Activo</span>';
    } else {
        return '<span class="badge bg-danger"><i class="fas fa-ban"></i> Inactivo</span>';
    }
}

function actualizarEstadisticas() {
    const total = usuarios.length;
    const activos = usuarios.filter(u => u.activo && !u.bloqueado).length;
    const bloqueados = usuarios.filter(u => u.bloqueado).length;
    const conectadosHoy = usuarios.filter(u => {
        if (!u.ultimo_acceso) return false;
        const acceso = new Date(u.ultimo_acceso);
        const hoy = new Date();
        return acceso.toDateString() === hoy.toDateString();
    }).length;
    
    document.getElementById('totalUsuarios').textContent = total;
    document.getElementById('usuariosActivos').textContent = activos;
    document.getElementById('usuariosBloqueados').textContent = bloqueados;
    document.getElementById('conectadosHoy').textContent = conectadosHoy;
}

function mostrarModalNuevoUsuario() {
    usuarioEditando = null;
    document.getElementById('modalUsuarioTitulo').textContent = 'Nuevo Usuario';
    document.getElementById('passwordHelp').textContent = 'Contraseña requerida para nuevos usuarios';
    document.getElementById('password').required = true;
    
    // Limpiar formulario
    document.getElementById('formUsuario').reset();
    document.getElementById('activo').checked = true;
    
    // Cargar roles
    cargarRolesEnModal();
    
    new bootstrap.Modal(document.getElementById('modalUsuario')).show();
}

async function editarUsuario(username) {
    // Proteger el usuario admin
    if (username === 'admin') {
        mostrarNotificacion(' El usuario administrador está protegido y no puede ser modificado desde este panel por motivos de seguridad.', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/admin/obtener_usuario/${username}`);
        const usuario = await response.json();
        
        usuarioEditando = usuario;
        document.getElementById('modalUsuarioTitulo').textContent = 'Editar Usuario';
        document.getElementById('passwordHelp').textContent = 'Dejar en blanco para mantener la actual';
        document.getElementById('password').required = false;
        
        // Llenar formulario
        document.getElementById('username').value = usuario.username;
        document.getElementById('username').readOnly = true;
        document.getElementById('nombreCompleto').value = usuario.nombre_completo || '';
        document.getElementById('email').value = usuario.email || '';
        document.getElementById('departamento').value = usuario.departamento || '';
        document.getElementById('cargo').value = usuario.cargo || '';
        document.getElementById('activo').checked = usuario.activo;
        
        // CRÍTICO: Limpiar el campo de contraseña para evitar que se envíe el valor autocompletado
        document.getElementById('password').value = '';
        
        // Cargar roles y marcar los asignados
        await cargarRolesEnModal();
        usuario.roles.forEach(rol => {
            const checkbox = document.querySelector(`input[name="roles"][value="${rol.nombre}"]`);
            if (checkbox) checkbox.checked = true;
        });
        actualizarContadorRoles();

        new bootstrap.Modal(document.getElementById('modalUsuario')).show();
        
    } catch (error) {
        console.error('Error cargando usuario:', error);
        mostrarNotificacion('Error cargando datos del usuario', 'error');
    }
}

function cargarRolesEnModal() {
    const tbody = document.getElementById('rolesTableBody');
    tbody.innerHTML = roles.map(rol => `
        <tr class="role-row" data-rol-nombre="${escapeHtml(rol.nombre).toLowerCase()}"
            data-rol-desc="${escapeHtml(rol.descripcion || '').toLowerCase()}">
            <td class="role-check-cell">
                <input class="form-check-input" type="checkbox" name="roles"
                    value="${escapeHtml(rol.nombre)}" id="rol_${rol.id}"
                    onchange="actualizarContadorRoles()">
            </td>
            <td><strong>${escapeHtml(rol.nombre)}</strong></td>
            <td><small class="text-muted">${escapeHtml(rol.descripcion) || '—'}</small></td>
        </tr>
    `).join('');

    // Click en cualquier parte de la fila alterna el checkbox
    tbody.querySelectorAll('.role-row').forEach(row => {
        row.addEventListener('click', (event) => {
            if (event.target.tagName === 'INPUT') return;
            const cb = row.querySelector('input[name="roles"]');
            cb.checked = !cb.checked;
            actualizarContadorRoles();
        });
    });

    // Reset de buscador/contador al cargar
    const search = document.getElementById('rolesSearchInput');
    if (search) search.value = '';
    filtrarRolesModal();
    actualizarContadorRoles();
}

// Filtra las filas de la tabla de roles por nombre o descripción
function filtrarRolesModal() {
    const termino = (document.getElementById('rolesSearchInput')?.value || '').toLowerCase().trim();
    document.querySelectorAll('#rolesTableBody .role-row').forEach(row => {
        const coincide = !termino
            || row.dataset.rolNombre.includes(termino)
            || row.dataset.rolDesc.includes(termino);
        row.style.display = coincide ? '' : 'none';
    });
}

// Actualiza el contador "N seleccionados"
function actualizarContadorRoles() {
    const total = document.querySelectorAll('#rolesTableBody input[name="roles"]:checked').length;
    const label = document.getElementById('rolesSeleccionadosCount');
    if (label) label.textContent = `${total} seleccionado${total === 1 ? '' : 's'}`;
}

// Marca/desmarca todos los roles actualmente visibles (respeta el filtro)
function toggleRolesVisibles() {
    const visibles = Array.from(document.querySelectorAll('#rolesTableBody .role-row'))
        .filter(row => row.style.display !== 'none')
        .map(row => row.querySelector('input[name="roles"]'));
    // Si todos los visibles ya están marcados, los desmarca; si no, los marca
    const todosMarcados = visibles.length > 0 && visibles.every(cb => cb.checked);
    visibles.forEach(cb => { cb.checked = !todosMarcados; });
    actualizarContadorRoles();
}

async function guardarUsuario() {
    const form = document.getElementById('formUsuario');
    
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const roles_seleccionados = Array.from(document.querySelectorAll('input[name="roles"]:checked'))
        .map(cb => cb.value);
    
    const passwordValue = document.getElementById('password').value;
    
    // Construir objeto de datos
    const datos = {
        username: document.getElementById('username').value,
        nombre_completo: document.getElementById('nombreCompleto').value,
        email: document.getElementById('email').value,
        departamento: document.getElementById('departamento').value,
        cargo: document.getElementById('cargo').value,
        activo: document.getElementById('activo').checked,
        roles: roles_seleccionados
    };
    
    // CRÍTICO: Solo incluir password si NO está vacío
    // Esto evita sobrescribir la contraseña cuando solo se editan otros campos
    if (passwordValue && passwordValue.trim() !== '') {
        datos.password = passwordValue;
    }
    
    // Validación adicional para nuevos usuarios
    if (!usuarioEditando && !datos.password) {
        mostrarNotificacion('La contraseña es obligatoria para nuevos usuarios', 'warning');
        document.getElementById('password').focus();
        return;
    }
    
    try {
        const response = await fetch('/admin/guardar_usuario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        
        const result = await response.json();
        
        if (result.success) {
            bootstrap.Modal.getInstance(document.getElementById('modalUsuario')).hide();
            cargarUsuarios();
            
            // Mensaje personalizado si se cambió la contraseña
            let mensaje = result.mensaje || 'Usuario guardado exitosamente';
            if (usuarioEditando && passwordValue && passwordValue.trim() !== '') {
                mensaje = `Usuario actualizado y contraseña cambiada exitosamente`;
            } else if (usuarioEditando) {
                mensaje = `Usuario actualizado exitosamente (contraseña sin cambios)`;
            }
            
            mostrarNotificacion(mensaje, 'success');
        } else {
            mostrarNotificacion('Error: ' + result.error, 'error');
        }

    } catch (error) {
        console.error('Error guardando usuario:', error);
        mostrarNotificacion('Error guardando usuario', 'error');
    }
}

async function toggleUsuario(username, activar) {
    const ok = await confirmarAccion(
        `¿Está seguro de ${activar ? 'activar' : 'desactivar'} el usuario "${username}"?`,
        { titulo: activar ? 'Activar usuario' : 'Desactivar usuario',
          textoOk: activar ? 'Activar' : 'Desactivar',
          estiloOk: activar ? 'btn-success' : 'btn-danger' }
    );
    if (!ok) return;

    try {
        const response = await fetch('/admin/cambiar_estado_usuario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, activo: activar })
        });

        const result = await response.json();

        if (result.success) {
            cargarUsuarios();
            mostrarNotificacion(`Usuario ${username} ${activar ? 'activado' : 'desactivado'}`, 'success');
        } else {
            mostrarNotificacion('Error: ' + result.error, 'error');
        }

    } catch (error) {
        console.error('Error cambiando estado:', error);
        mostrarNotificacion('Error cambiando estado del usuario', 'error');
    }
}

async function desbloquearUsuario(username) {
    const ok = await confirmarAccion(
        `¿Desbloquear el usuario "${username}"?`,
        { titulo: 'Desbloquear usuario', textoOk: 'Desbloquear', estiloOk: 'btn-success' }
    );
    if (!ok) return;

    try {
        const response = await fetch('/admin/desbloquear_usuario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });

        const result = await response.json();

        if (result.success) {
            cargarUsuarios();
            mostrarNotificacion(result.mensaje, 'success');
        } else {
            mostrarNotificacion('Error: ' + result.error, 'error');
        }

    } catch (error) {
        console.error('Error desbloqueando usuario:', error);
        mostrarNotificacion('Error desbloqueando usuario', 'error');
    }
}

// Funciones para borrar usuario
let usuarioABorrar = null;

function confirmarBorrarUsuario(username) {
    // Proteger el usuario admin
    if (username === 'admin') {
        mostrarNotificacion(' El usuario administrador está protegido y no puede ser eliminado.', 'warning');
        return;
    }
    
    usuarioABorrar = username;
    document.getElementById('usuarioABorrar').textContent = username;
    new bootstrap.Modal(document.getElementById('modalConfirmarBorrar')).show();
}

async function borrarUsuario() {
    if (!usuarioABorrar) return;
    
    try {
        const response = await fetch(`/admin/borrar_usuario/${usuarioABorrar}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            bootstrap.Modal.getInstance(document.getElementById('modalConfirmarBorrar')).hide();
            mostrarNotificacion(`Usuario ${usuarioABorrar} eliminado exitosamente`, 'success');
            cargarUsuarios(); // Recargar la lista
            usuarioABorrar = null;
        } else {
            mostrarNotificacion('Error: ' + (result.error || 'No se pudo eliminar el usuario'), 'error');
        }

    } catch (error) {
        console.error('Error borrando usuario:', error);
        mostrarNotificacion('Error eliminando usuario', 'error');
    }
}

function mostrarNotificacion(mensaje, tipo) {
    // Crear notificación toast
    const toast = document.createElement('div');
    toast.className = `alert alert-${tipo === 'success' ? 'success' : tipo === 'warning' ? 'warning' : 'danger'} alert-dismissible fade show`;
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '300px';
    toast.innerHTML = `
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove después de 5 segundos para warnings, 3 para otros
    const timeout = tipo === 'warning' ? 5000 : 3000;
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, timeout);
}

// Limpiar readonly cuando se cierra el modal
document.getElementById('modalUsuario').addEventListener('hidden.bs.modal', function() {
    document.getElementById('username').readOnly = false;
    // Limpiar el campo de contraseña al cerrar el modal por seguridad
    document.getElementById('password').value = '';
});

// Limpiar el campo de contraseña cuando se abre el modal (medida de seguridad adicional)
document.getElementById('modalUsuario').addEventListener('shown.bs.modal', function() {
    // Solo limpiar si estamos editando (no en nuevo usuario)
    if (usuarioEditando) {
        document.getElementById('password').value = '';
    }
});

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

    // Redirigir después de un breve delay
    setTimeout(() => {
        window.location.href = '/logout';
    }, 1000);
}

// Exponer a window las funciones llamadas desde onclick= en el HTML
window.mostrarModalNuevoUsuario = mostrarModalNuevoUsuario;
window.editarUsuario = editarUsuario;
window.guardarUsuario = guardarUsuario;
window.toggleUsuario = toggleUsuario;
window.desbloquearUsuario = desbloquearUsuario;
window.confirmarBorrarUsuario = confirmarBorrarUsuario;
window.borrarUsuario = borrarUsuario;
window.confirmarLogout = confirmarLogout;
window.aplicarFiltros = aplicarFiltros;
window.filtrarRolesModal = filtrarRolesModal;
window.toggleRolesVisibles = toggleRolesVisibles;
window.actualizarContadorRoles = actualizarContadorRoles;
