/* =====================================================================
   admin_permisos.js — lógica del Gestor de Permisos de dropdowns.
   Cargado con defer; las funciones usadas desde onclick= en el HTML se
   exponen en window al final del archivo.
   ===================================================================== */

// Estado global de la aplicación
let currentRole = null;
let allRoles = [];
let allDropdowns = [];
let rolePermissions = {};
let filteredPermissions = [];

// Inicializar la aplicación
document.addEventListener('DOMContentLoaded', async function() {
    updateStickyOffset();
    await Promise.all([loadRoles(), loadDropdowns()]);
    updateStats([]);
});

// Mide la altura real del header global y la expone como --stick-top, para
// que la sidebar y el encabezado del panel se peguen justo debajo de él
// (altura + margin inferior, para que el bloque NO se desplace al scrollear).
function updateStickyOffset() {
    const header = document.querySelector('.page-header');
    if (!header) return;
    const marginBottom = parseFloat(getComputedStyle(header).marginBottom) || 0;
    const offset = Math.round(header.offsetHeight + marginBottom);
    document.documentElement.style.setProperty('--stick-top', offset + 'px');
}

window.addEventListener('resize', updateStickyOffset);
// El header puede reflujar cuando los botones cambian de fila en pantallas medianas.
if ('ResizeObserver' in window) {
    const headerEl = document.querySelector('.page-header');
    if (headerEl) new ResizeObserver(updateStickyOffset).observe(headerEl);
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function normalizePageName(pageName) {
    return String(pageName || '')
        .replace('LISTA_', '')
        .replaceAll('_', ' ')
        .trim();
}

function getRoleByName(roleName) {
    return allRoles.find(r => r.nombre === roleName);
}

function getCurrentRolePermissions() {
    return currentRole && rolePermissions[currentRole] ? rolePermissions[currentRole] : [];
}

// Función para actualizar el contador de roles con animación
function updateRoleCounter(count, isLoading = false) {
    const counterElement = document.getElementById('totalRoles');
    const containerElement = document.getElementById('totalRolesContainer');
    
    if (counterElement && containerElement) {
        if (isLoading) {
            // Mostrar efecto de carga
            containerElement.classList.add('loading');
            counterElement.textContent = '...';
        } else {
            // Remover efecto de carga
            containerElement.classList.remove('loading');
            
            // Agregar animación al contenedor
            containerElement.classList.add('updating');
            
            // Actualizar el número con un pequeño delay para que se vea la animación
            setTimeout(() => {
                counterElement.textContent = count;
            }, 100);
            
            // Remover la clase de animación después de que termine
            setTimeout(() => {
                containerElement.classList.remove('updating');
            }, 600);
        }
    }
}

// Cargar roles disponibles
async function loadRoles() {
    try {
        // Mostrar efecto de carga en el contador
        updateRoleCounter(0, true);
        
        const response = await fetch('/admin/listar_roles');
        const roles = await response.json();
        
        // Mapear iconos para cada rol
        const rolesWithIcons = roles.map(role => ({
            ...role,
            icon: getRoleIcon(role.nombre)
        }));
        
        allRoles = rolesWithIcons;
        updateRoleCounter(roles.length);
        renderRoles(rolesWithIcons);
    } catch (error) {
        showError('Error cargando roles: ' + error.message);
    }
}

// Obtener icono para un rol
function getRoleIcon(roleName) {
    const iconMap = {
        'superadmin': 'fa-crown',
        'admin': 'fa-user-shield',
        'supervisor_almacen': 'fa-warehouse',
        'supervisor_produccion': 'fa-industry',
        'operador_almacen': 'fa-boxes',
        'operador_produccion': 'fa-cogs',
        'calidad': 'fa-medal',
        'Inspector': 'fa-clipboard-check',
        'Tecnico QA': 'fa-screwdriver-wrench',
        'Supervisor QA': 'fa-user-tie',
        'Diseño': 'fa-drafting-compass',
        'Planeacion': 'fa-calendar-check',
        'supervisor_embarques': 'fa-truck-ramp-box',
        'operador_embarques': 'fa-dolly',
        'consulta': 'fa-eye',
        'invitado': 'fa-user-clock'
    };
    return iconMap[roleName] || 'fa-user';
}

// Cargar dropdowns disponibles
async function loadDropdowns() {
    try {
        const response = await fetch('/admin/listar_permisos_dropdowns');
        const permisosAgrupados = await response.json();
        
        // Convertir estructura agrupada a lista plana
        allDropdowns = [];
        Object.keys(permisosAgrupados).forEach(pagina => {
            Object.keys(permisosAgrupados[pagina]).forEach(seccion => {
                permisosAgrupados[pagina][seccion].forEach(permiso => {
                    allDropdowns.push({
                        id: permiso.id,
                        pagina: pagina,
                        seccion: seccion,
                        boton: permiso.boton,
                        descripcion: permiso.descripcion
                    });
                });
            });
        });
        
        populateFilterOptions();
    } catch (error) {
        showError('Error cargando dropdowns: ' + error.message);
    }
}

// Renderizar lista de roles
function renderRoles(roles) {
    const container = document.getElementById('rolesContainer');
    container.innerHTML = '';

    if (!roles || roles.length === 0) {
        container.innerHTML = `
            <div class="empty-state py-4">
                <div class="empty-icon">
                    <i class="fas fa-search"></i>
                </div>
                <h6>No hay roles</h6>
                <p class="mb-0">Ajusta la búsqueda de roles.</p>
            </div>
        `;
        return;
    }
    
    roles.forEach(role => {
        const roleElement = document.createElement('div');
        roleElement.className = 'role-item';
        roleElement.dataset.roleName = role.nombre;
        if (role.nombre === currentRole) {
            roleElement.classList.add('active');
        }
        
        const esSistema = role.nivel >= 8;
        const puedeEliminar = !esSistema && role.total_usuarios === 0;
        
        roleElement.innerHTML = `
            <div class="role-item-row">
                <div class="role-item-body" style="cursor: pointer;">
                    <div class="role-name">
                        <i class="fas ${role.icon}"></i>
                        <span class="role-name-text">${escapeHtml(role.nombre)}</span>
                        ${esSistema ? '<span class="badge bg-warning role-system-badge">Sistema</span>' : ''}
                    </div>
                    <div class="role-description">${escapeHtml(role.descripcion || 'Sin descripción')}</div>
                    <div class="role-count" id="count-${role.id}">Nivel ${role.nivel} • Cargando...</div>
                </div>
                <div class="role-actions">
                    <button class="btn btn-sm btn-outline-primary js-edit-role" type="button" title="Editar rol">
                        <i class="fas fa-edit"></i>
                    </button>
                    ${puedeEliminar ? `
                        <button class="btn btn-sm btn-outline-danger js-delete-role" type="button" title="Eliminar rol">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : `
                        <button class="btn btn-sm btn-outline-secondary" type="button" disabled title="${esSistema ? 'No se puede eliminar un rol del sistema' : 'El rol tiene usuarios asignados'}">
                            <i class="fas fa-ban"></i>
                        </button>
                    `}
                </div>
            </div>
        `;

        roleElement.addEventListener('click', () => selectRole(role.nombre, roleElement));
        roleElement.querySelector('.js-edit-role')?.addEventListener('click', (event) => {
            event.stopPropagation();
            mostrarModalEditarRol(role.id);
        });
        roleElement.querySelector('.js-delete-role')?.addEventListener('click', (event) => {
            event.stopPropagation();
            mostrarModalEliminarRol(role.id, role.nombre);
        });
        
        container.appendChild(roleElement);
        loadRolePermissionCount(role.nombre);
    });
}

function filterRoles() {
    const term = document.getElementById('roleSearchInput').value.toLowerCase().trim();
    const filtered = term
        ? allRoles.filter(role =>
            String(role.nombre || '').toLowerCase().includes(term) ||
            String(role.descripcion || '').toLowerCase().includes(term)
        )
        : allRoles;
    renderRoles(filtered);
}

// Cargar contador de permisos para un rol
async function loadRolePermissionCount(roleName) {
    try {
        const role = allRoles.find(r => r.nombre === roleName);
        if (!role) return;
        
        const response = await fetch(`/admin/obtener_permisos_dropdowns_rol/${role.id}`);
        const permisos = await response.json();
        
        const countElement = document.getElementById(`count-${role.id}`);
        if (countElement) {
            if (Array.isArray(permisos)) {
                countElement.textContent = `Nivel ${role.nivel} • ${permisos.length} permisos`;
            } else {
                countElement.textContent = `Nivel ${role.nivel} • Error`;
            }
        }
    } catch (error) {
        const role = allRoles.find(r => r.nombre === roleName);
        const countElement = role ? document.getElementById(`count-${role.id}`) : null;
        if (countElement) {
            countElement.textContent = 'Error';
        }
    }
}

// === FUNCIONES DE GESTIÓN DE ROLES ===

// Mostrar modal para crear rol
function mostrarModalCrearRol() {
    document.getElementById('formCrearRol').reset();
    const modal = new bootstrap.Modal(document.getElementById('modalCrearRol'));
    modal.show();
}

// Crear nuevo rol
async function crearRol() {
    const form = document.getElementById('formCrearRol');
    const formData = new FormData(form);
    
    const data = {
        nombre: document.getElementById('nombreRol').value.trim(),
        descripcion: document.getElementById('descripcionRol').value.trim(),
        nivel: parseInt(document.getElementById('nivelRol').value)
    };
    
    // Validar datos
    if (!data.nombre) {
        showError('El nombre del rol es requerido');
        return;
    }
    
    if (!data.descripcion) {
        showError('La descripción del rol es requerida');
        return;
    }
    
    if (!data.nivel) {
        showError('Debe seleccionar un nivel de acceso');
        return;
    }
    
    try {
        const response = await fetch('/admin/crear_rol', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.mensaje);
            bootstrap.Modal.getInstance(document.getElementById('modalCrearRol')).hide();
            
            // Recargar roles
            await loadRoles();
        } else {
            showError(result.error || 'Error creando el rol');
        }
        
    } catch (error) {
        showError('Error creando el rol: ' + error.message);
    }
}

// Mostrar modal para editar rol
async function mostrarModalEditarRol(rolId) {
    try {
        // Buscar el rol en la lista actual
        const role = allRoles.find(r => r.id === rolId);
        if (!role) {
            showError('Rol no encontrado');
            return;
        }
        
        // Llenar el formulario
        document.getElementById('editRolId').value = role.id;
        document.getElementById('editNombreRol').value = role.nombre;
        document.getElementById('editDescripcionRol').value = role.descripcion;
        document.getElementById('editNivelRol').value = role.nivel;
        
        // Mostrar/ocultar warning para roles del sistema
        const esSistema = role.nivel >= 8;
        const warningElement = document.getElementById('warningEditSistema');
        const nombreInput = document.getElementById('editNombreRol');
        const nivelSelect = document.getElementById('editNivelRol');
        
        warningElement.classList.toggle('d-none', !esSistema);
        nombreInput.disabled = esSistema;
        nivelSelect.disabled = esSistema;
        
        const modal = new bootstrap.Modal(document.getElementById('modalEditarRol'));
        modal.show();
        
    } catch (error) {
        showError('Error cargando datos del rol: ' + error.message);
    }
}

// Actualizar rol
async function actualizarRol() {
    const data = {
        nombre: document.getElementById('editNombreRol').value.trim(),
        descripcion: document.getElementById('editDescripcionRol').value.trim(),
        nivel: parseInt(document.getElementById('editNivelRol').value)
    };
    
    const rolId = document.getElementById('editRolId').value;
    
    // Validar datos
    if (!data.nombre) {
        showError('El nombre del rol es requerido');
        return;
    }
    
    if (!data.descripcion) {
        showError('La descripción del rol es requerida');
        return;
    }
    
    if (!data.nivel) {
        showError('Debe seleccionar un nivel de acceso');
        return;
    }
    
    try {
        const response = await fetch(`/admin/actualizar_rol/${rolId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.mensaje);
            bootstrap.Modal.getInstance(document.getElementById('modalEditarRol')).hide();
            
            // Recargar roles
            await loadRoles();
            
            // Si es el rol actual, recargar permisos
            if (currentRole && result.rol && result.rol.nombre === currentRole) {
                await loadRolePermissions(currentRole);
            }
        } else {
            showError(result.error || 'Error actualizando el rol');
        }
        
    } catch (error) {
        showError('Error actualizando el rol: ' + error.message);
    }
}

// Mostrar modal para eliminar rol
function mostrarModalEliminarRol(rolId, rolNombre) {
    document.getElementById('deleteRolId').value = rolId;
    document.getElementById('deleteRolInfo').textContent = `Se eliminará el rol "${rolNombre}" y todos sus permisos asociados.`;
    
    const modal = new bootstrap.Modal(document.getElementById('modalEliminarRol'));
    modal.show();
}

// Confirmar eliminación de rol
async function confirmarEliminarRol() {
    const rolId = document.getElementById('deleteRolId').value;
    
    try {
        const response = await fetch(`/admin/eliminar_rol/${rolId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.mensaje);
            bootstrap.Modal.getInstance(document.getElementById('modalEliminarRol')).hide();
            
            // Recargar roles
            await loadRoles();
            
            // Si era el rol actual, limpiar selección
            if (currentRole) {
                const rolEliminado = allRoles.find(r => r.id == rolId);
                if (rolEliminado && rolEliminado.nombre === currentRole) {
                    currentRole = null;
                    document.getElementById('permissionsContainer').innerHTML = `
                        <div class="empty-state">
                            <div class="empty-icon">
                                <i class="fas fa-hand-pointer"></i>
                            </div>
                            <h5>Selecciona un rol</h5>
                            <p class="mb-0">Elige un rol de la barra lateral para ver y gestionar sus permisos</p>
                        </div>
                    `;
                }
            }
        } else {
            showError(result.error || 'Error eliminando el rol');
        }
        
    } catch (error) {
        showError('Error eliminando el rol: ' + error.message);
    }
}

// Seleccionar un rol
async function selectRole(roleName, sourceElement = null) {
    document.querySelectorAll('.role-item').forEach(item => {
        item.classList.remove('active');
    });
    if (sourceElement) {
        sourceElement.classList.add('active');
    } else {
        Array.from(document.querySelectorAll('.role-item'))
            .find(item => item.dataset.roleName === roleName)
            ?.classList.add('active');
    }
    
    currentRole = roleName;
    renderRoleSummary(roleName);
    await loadRolePermissions(roleName);
}

function renderRoleSummary(roleName) {
    const role = getRoleByName(roleName);
    const summary = document.getElementById('roleSummary');
    const title = document.getElementById('summaryRoleName');
    const meta = document.getElementById('summaryRoleMeta');

    if (!role) {
        summary.classList.remove('is-visible');
        return;
    }

    const systemBadge = role.nivel >= 8
        ? `<span class="summary-pill"><i class="fas fa-lock"></i> Rol de sistema</span>`
        : `<span class="summary-pill"><i class="fas fa-pen"></i> Rol editable</span>`;

    title.innerHTML = `
        <i class="fas ${role.icon}"></i>
        ${escapeHtml(role.nombre)}
    `;
    meta.innerHTML = `
        <span class="summary-pill"><i class="fas fa-layer-group"></i> Nivel ${escapeHtml(role.nivel)}</span>
        <span class="summary-pill"><i class="fas fa-users"></i> ${escapeHtml(role.total_usuarios || 0)} usuarios</span>
        ${systemBadge}
        <span class="summary-pill"><i class="fas fa-circle-info"></i> ${escapeHtml(role.descripcion || 'Sin descripción')}</span>
    `;
    summary.classList.add('is-visible');
}

// Cargar permisos de un rol específico
async function loadRolePermissions(roleName) {
    const container = document.getElementById('permissionsContainer');
    container.innerHTML = `
        <div class="loading-container">
            <div class="spinner"></div>
            <small class="mt-2">Cargando permisos para ${roleName}...</small>
        </div>
    `;
    
    try {
        // Obtener ID del rol
        const role = allRoles.find(r => r.nombre === roleName);
        if (!role) {
            throw new Error('Rol no encontrado');
        }
        
        // Cargar permisos desde el servidor
        const response = await fetch(`/admin/obtener_permisos_dropdowns_rol/${role.id}`);
        const permisosDelRol = await response.json();
        
        // Verificar que la respuesta sea válida y sea un array
        if (!Array.isArray(permisosDelRol)) {
            throw new Error('Error en la respuesta del servidor: ' + (permisosDelRol.error || 'Formato de datos inválido'));
        }
        
        // Convertir los permisos del rol a nuestra estructura
        const permissions = allDropdowns.map(dropdown => {
            const hasPermission = permisosDelRol.some(p => 
                p.pagina === dropdown.pagina && 
                p.seccion === dropdown.seccion && 
                p.boton === dropdown.boton
            );
            
            return {
                id: dropdown.id,
                pagina: dropdown.pagina,
                seccion: dropdown.seccion,
                boton: dropdown.boton,
                descripcion: dropdown.descripcion,
                activo: hasPermission ? 1 : 0
            };
        });
        
        rolePermissions[roleName] = permissions;
        filteredPermissions = [...permissions];
        renderPermissions(filteredPermissions);
        updateStats(filteredPermissions);
        
    } catch (error) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <h5>Error cargando permisos</h5>
                <p class="mb-0">${error.message}</p>
            </div>
        `;
    }
}

// Renderizar permisos
function renderPermissions(permissions) {
    const container = document.getElementById('permissionsContainer');
    
    if (!permissions || permissions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">
                    <i class="fas fa-search"></i>
                </div>
                <h5>No se encontraron permisos</h5>
                <p class="mb-0">Ajusta los filtros para ver más resultados</p>
            </div>
        `;
        return;
    }

    const grid = document.createElement('div');
    grid.className = 'permission-grid';

    const groupedByPage = permissions.reduce((acc, permission) => {
        if (!acc[permission.pagina]) acc[permission.pagina] = {};
        if (!acc[permission.pagina][permission.seccion]) acc[permission.pagina][permission.seccion] = [];
        acc[permission.pagina][permission.seccion].push(permission);
        return acc;
    }, {});

    Object.keys(groupedByPage).sort().forEach(page => {
        const pageGroup = document.createElement('section');
        pageGroup.className = 'permission-page-group';
        const pagePermissions = Object.values(groupedByPage[page]).flat();
        const enabledInPage = pagePermissions.filter(p => p.activo === 1).length;

        pageGroup.innerHTML = `
            <div class="permission-page-header">
                <div class="permission-page-title">
                    <i class="fas fa-folder-tree"></i>
                    <span>${escapeHtml(normalizePageName(page))}</span>
                </div>
                <div class="permission-page-count">${enabledInPage}/${pagePermissions.length} habilitados</div>
            </div>
        `;

        Object.keys(groupedByPage[page]).sort().forEach(section => {
            const sectionBlock = document.createElement('div');
            sectionBlock.className = 'permission-section';
            sectionBlock.innerHTML = `
                <div class="permission-section-title">${escapeHtml(section)}</div>
            `;

            groupedByPage[page][section]
                .sort((a, b) => a.boton.localeCompare(b.boton))
                .forEach(permission => {
                    const permissionElement = document.createElement('div');
                    permissionElement.className = `permission-item ${permission.activo ? 'enabled' : 'disabled'}`;
                    const displayBoton = permission.boton === 'Crear ECO' ? 'Crear ECO' : permission.boton;
                    const displayDescripcion = permission.boton === 'Crear ECO'
                        ? 'Permite crear, importar, aprobar, cancelar y borrar ECOs desde Control de BOM'
                        : (permission.descripcion || '');
                    const statusText = permission.activo ? 'Habilitado' : 'Deshabilitado';
                    const statusIcon = permission.activo ? 'fa-check-circle' : 'fa-circle-xmark';

                    permissionElement.innerHTML = `
                        <div>
                            <div class="permission-state-label">
                                <i class="fas ${statusIcon}"></i>
                                ${statusText}
                            </div>
                            <div class="permission-header">
                                <div class="permission-title">${escapeHtml(displayBoton)}</div>
                            </div>
                            <div class="permission-meta">
                                <div class="permission-path">
                                    <i class="fas fa-folder me-1"></i>
                                    <span class="permission-badge">${escapeHtml(normalizePageName(permission.pagina))}</span>
                                    ${permission.boton === 'Crear ECO' ? '<span class="permission-badge">Acción ECO</span>' : ''}
                                </div>
                                <div class="permission-path">
                                    <i class="fas fa-layer-group me-1"></i>
                                    <span>${escapeHtml(permission.seccion)}</span>
                                </div>
                                ${displayDescripcion ? `
                                    <div class="permission-path">
                                        <i class="fas fa-info-circle me-1"></i>
                                        <span>${escapeHtml(displayDescripcion)}</span>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                        <label class="permission-toggle" title="${statusText}">
                            <input type="checkbox" data-permission-id="${permission.id}" ${permission.activo ? 'checked' : ''}>
                            <span class="slider"></span>
                        </label>
                    `;

                    sectionBlock.appendChild(permissionElement);
                });

            pageGroup.appendChild(sectionBlock);
        });

        grid.appendChild(pageGroup);
    });
    
    container.innerHTML = '';
    container.appendChild(grid);

    container.querySelectorAll('input[data-permission-id]').forEach(input => {
        input.addEventListener('change', () => {
            togglePermissionById(Number(input.dataset.permissionId), input.checked);
        });
    });
}

// Guardar permisos de un rol
async function saveRolePermissions(roleName, permissions) {
    try {
        // Obtener ID del rol
        const role = allRoles.find(r => r.nombre === roleName);
        if (!role) {
            throw new Error('Rol no encontrado');
        }
        
        // Extraer IDs de permisos habilitados
        const permisosIds = permissions
            .filter(p => p.activo === 1)
            .map(p => p.id);
        
        // Enviar al servidor
        const response = await fetch('/admin/actualizar_permisos_dropdowns_rol', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rol_id: role.id,
                permisos_ids: permisosIds
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Error desconocido');
        }
        
        // Actualizar contador del rol
        loadRolePermissionCount(roleName);
        
        return true;
    } catch (error) {
        console.error('Error guardando permisos:', error);
        showError('Error guardando los cambios: ' + error.message);
        return false;
    }
}

async function togglePermissionById(permissionId, habilitar) {
    if (!currentRole) {
        showError('Selecciona un rol primero');
        return;
    }

    const permissions = rolePermissions[currentRole] || [];
    const permissionIndex = permissions.findIndex(p => Number(p.id) === Number(permissionId));
    if (permissionIndex === -1) {
        showError('Permiso no encontrado');
        return;
    }

    const permission = permissions[permissionIndex];
    permissions[permissionIndex].activo = habilitar ? 1 : 0;

    const success = await saveRolePermissions(currentRole, permissions);
    if (success) {
        showSuccess(`${permission.boton} ${habilitar ? 'habilitado' : 'deshabilitado'}`);
        applyCurrentFilters();
    } else {
        permissions[permissionIndex].activo = habilitar ? 0 : 1;
        applyCurrentFilters();
    }
}

// Alternar permiso individual
async function togglePermission(pagina, seccion, boton, habilitar) {
    if (!currentRole) {
        showError('Selecciona un rol primero');
        return;
    }
    
    const permissions = rolePermissions[currentRole];
    const permissionIndex = permissions.findIndex(p => 
        p.pagina === pagina && 
        p.seccion === seccion && 
        p.boton === boton
    );
    
    if (permissionIndex !== -1) {
        permissions[permissionIndex].activo = habilitar ? 1 : 0;
        
        const success = await saveRolePermissions(currentRole, permissions);
        if (success) {
            showSuccess(`${boton} ${habilitar ? 'habilitado' : 'deshabilitado'}`);
            
            // Actualizar la visualización manteniendo los filtros
            applyCurrentFilters();
            updateStats(filteredPermissions);
        } else {
            // Revertir el cambio si falló
            permissions[permissionIndex].activo = habilitar ? 0 : 1;
            applyCurrentFilters();
        }
    }
}

// Habilitar todos los permisos
async function enableAllPermissions() {
    if (!currentRole) {
        showError('Selecciona un rol primero');
        return;
    }
    
    if (!confirm(`¿Habilitar TODOS los permisos para "${currentRole}"?`)) {
        return;
    }
    
    const permissions = rolePermissions[currentRole];
    permissions.forEach(p => p.activo = 1);
    
    const success = await saveRolePermissions(currentRole, permissions);
    if (success) {
        showSuccess('Todos los permisos habilitados');
        applyCurrentFilters();
        updateStats(filteredPermissions);
    }
}

// Deshabilitar todos los permisos
async function disableAllPermissions() {
    if (!currentRole) {
        showError('Selecciona un rol primero');
        return;
    }
    
    if (!confirm(`¿Deshabilitar TODOS los permisos para "${currentRole}"?`)) {
        return;
    }
    
    const permissions = rolePermissions[currentRole];
    permissions.forEach(p => p.activo = 0);
    
    const success = await saveRolePermissions(currentRole, permissions);
    if (success) {
        showSuccess('Todos los permisos deshabilitados');
        applyCurrentFilters();
        updateStats(filteredPermissions);
    }
}

// Actualizar estadísticas
function updateStats(permissions) {
    const fullPermissions = getCurrentRolePermissions();
    const total = fullPermissions.length || permissions.length;
    const enabled = (fullPermissions.length ? fullPermissions : permissions).filter(p => p.activo === 1).length;
    const disabled = total - enabled;
    const visible = permissions.length;
    const ratio = total ? Math.round((enabled / total) * 100) : 0;
    
    document.getElementById('totalPermissions').textContent = total;
    const visibleElement = document.getElementById('visiblePermissions');
    if (visibleElement) visibleElement.textContent = visible;
    document.getElementById('enabledCount').textContent = enabled;
    document.getElementById('disabledCount').textContent = disabled;

    const ratioElement = document.getElementById('summaryEnabledRatio');
    const progressElement = document.getElementById('summaryProgressFill');
    if (ratioElement) ratioElement.textContent = `${ratio}%`;
    if (progressElement) progressElement.style.width = `${ratio}%`;
}

// Poblar opciones de filtros
function populateFilterOptions() {
    const pages = [...new Set(allDropdowns.map(d => d.pagina))].sort();
    const sections = [...new Set(allDropdowns.map(d => d.seccion))].sort();
    
    const pageFilter = document.getElementById('pageFilter');
    const sectionFilter = document.getElementById('sectionFilter');

    pageFilter.innerHTML = '<option value="">Todas las páginas</option>';
    sectionFilter.innerHTML = '<option value="">Todas las secciones</option>';
    
    pages.forEach(page => {
        const option = document.createElement('option');
        option.value = page;
        option.textContent = normalizePageName(page);
        pageFilter.appendChild(option);
    });
    
    sections.forEach(section => {
        const option = document.createElement('option');
        option.value = section;
        option.textContent = section;
        sectionFilter.appendChild(option);
    });
}

// Aplicar filtros actuales
function applyCurrentFilters() {
    if (!rolePermissions[currentRole]) return;
    
    let filtered = [...rolePermissions[currentRole]];
    
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const pageFilter = document.getElementById('pageFilter').value;
    const sectionFilter = document.getElementById('sectionFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;
    
    if (searchTerm) {
        filtered = filtered.filter(p => 
            p.boton.toLowerCase().includes(searchTerm) ||
            p.seccion.toLowerCase().includes(searchTerm) ||
            p.pagina.toLowerCase().includes(searchTerm) ||
            String(p.descripcion || '').toLowerCase().includes(searchTerm)
        );
    }
    
    if (pageFilter) {
        filtered = filtered.filter(p => p.pagina === pageFilter);
    }
    
    if (sectionFilter) {
        filtered = filtered.filter(p => p.seccion === sectionFilter);
    }
    
    if (statusFilter === 'enabled') {
        filtered = filtered.filter(p => p.activo === 1);
    } else if (statusFilter === 'disabled') {
        filtered = filtered.filter(p => p.activo === 0);
    }
    
    filteredPermissions = filtered;
    renderPermissions(filteredPermissions);
    updateStats(filteredPermissions);
}

// Funciones de filtrado
function filterPermissions() {
    applyCurrentFilters();
}

function filterByPage() {
    applyCurrentFilters();
}

function filterBySection() {
    applyCurrentFilters();
}

function filterByStatus() {
    applyCurrentFilters();
}

function resetPermissionFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('pageFilter').value = '';
    document.getElementById('sectionFilter').value = '';
    document.getElementById('statusFilter').value = '';
    applyCurrentFilters();
}

// Exportar permisos
function exportPermissions() {
    if (!currentRole) {
        showError('Selecciona un rol primero');
        return;
    }
    
    const data = {
        role: currentRole,
        permissions: rolePermissions[currentRole],
        exportDate: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `permisos_${currentRole}_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showSuccess('Permisos exportados correctamente');
}

// Sincronizar permisos desde archivos
async function sincronizarPermisos() {
    if (!confirm('¿Sincronizar permisos desde los archivos LISTAS? Esto puede tomar unos segundos.')) {
        return;
    }
    
    try {
        showSuccess('Iniciando sincronización...');
        
        const response = await fetch('/admin/sincronizar_permisos_dropdowns', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`Sincronización completada: ${result.nuevos_agregados} nuevos, ${result.desactivados} desactivados`);
            
            // Recargar datos
            await loadDropdowns();
            if (currentRole) {
                await loadRolePermissions(currentRole);
            }
        } else {
            showError('Error en la sincronización: ' + (result.error || 'Error desconocido'));
        }
        
    } catch (error) {
        showError('Error sincronizando permisos: ' + error.message);
    }
}

// Reset todos los permisos
function resetAllPermissions() {
    if (!confirm('¿Estás seguro de que quieres restablecer TODOS los permisos? Esto volverá a cargar desde la base de datos.')) {
        return;
    }
    
    if (currentRole) {
        loadRolePermissions(currentRole);
        showSuccess('Permisos restablecidos desde la base de datos');
    }
}

// Mostrar mensaje de éxito
function showSuccess(message) {
    document.getElementById('successMessage').textContent = message;
    const toast = new bootstrap.Toast(document.getElementById('successToast'));
    toast.show();
}

// Mostrar mensaje de error
function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    const toast = new bootstrap.Toast(document.getElementById('errorToast'));
    toast.show();
}

// Exponer a window las funciones llamadas desde onclick= en el HTML
window.sincronizarPermisos = sincronizarPermisos;
window.exportPermissions = exportPermissions;
window.resetAllPermissions = resetAllPermissions;
window.mostrarModalCrearRol = mostrarModalCrearRol;
window.crearRol = crearRol;
window.actualizarRol = actualizarRol;
window.confirmarEliminarRol = confirmarEliminarRol;
window.filterRoles = filterRoles;
window.filterPermissions = filterPermissions;
window.filterByPage = filterByPage;
window.filterBySection = filterBySection;
window.filterByStatus = filterByStatus;
window.resetPermissionFilters = resetPermissionFilters;
window.enableAllPermissions = enableAllPermissions;
window.disableAllPermissions = disableAllPermissions;
