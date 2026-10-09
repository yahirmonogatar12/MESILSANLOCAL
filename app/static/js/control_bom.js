(function () {
    const CONTROL_BOM_STYLESHEET_ID = 'control-bom-css';
    const CONTROL_BOM_STYLESHEET_HREF = '/static/css/control_bom.css?v=20261009e';

    function ensureControlBomStyles() {
        const stylesheet = document.getElementById(CONTROL_BOM_STYLESHEET_ID);
        if (stylesheet) {
            if (!stylesheet.getAttribute('href')?.includes('20261009e')) {
                stylesheet.setAttribute('href', CONTROL_BOM_STYLESHEET_HREF);
            }
            return;
        }

        const link = document.createElement('link');
        link.id = CONTROL_BOM_STYLESHEET_ID;
        link.rel = 'stylesheet';
        link.href = CONTROL_BOM_STYLESHEET_HREF;
        document.head.appendChild(link);
    }

    function getControlBomRoot() {
        return document.getElementById('controlBomModule');
    }

    // ========== FILTROS POR COLUMNA (mismo patron que ICT) ==========
    // Filtran en el navegador las filas ya cargadas; se reaplican cada vez que
    // se vuelve a llenar la tabla. Estado en memoria por columna (cellIndex).
    const bomColumnFilters = {};

    function renderBomColumnFilterHeaders() {
        document.querySelectorAll('#bomDataTable th[data-bom-filter]').forEach(header => {
            if (header.dataset.bomFilterReady === 'true') return;
            const col = header.cellIndex;
            const label = header.textContent.trim();
            const value = bomColumnFilters[col] || '';
            header.classList.add('bom-column-filterable');
            header.dataset.bomFilterReady = 'true';
            header.innerHTML = `
                <div class="bom-column-header">
                    <span>${escapeHtml(label)}</span>
                    <button class="bom-column-filter-btn${value ? ' active' : ''}" type="button"
                            aria-label="Filtrar ${escapeHtml(label)}" aria-expanded="false" title="Filtrar ${escapeHtml(label)}">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18l-7 8v5l-4 2v-7L3 5z"></path></svg>
                    </button>
                </div>
                <div class="bom-column-filter-popover">
                    <input class="bom-column-filter-input" data-bom-filter-col="${col}" value="${escapeHtml(value)}"
                           placeholder="Buscar..." aria-label="Buscar en ${escapeHtml(label)}" autocomplete="off">
                    <div class="bom-column-filter-actions">
                        <button class="bom-column-filter-clear" type="button">Limpiar</button>
                        <button class="bom-column-filter-clear-all" type="button">Todos</button>
                    </div>
                </div>`;
        });
    }

    function cerrarFiltrosColumnaBOM(excepto) {
        document.querySelectorAll('#bomDataTable .bom-column-filter-popover.open').forEach(popover => {
            if (popover === excepto) return;
            popover.classList.remove('open');
            const header = popover.closest('th');
            header?.classList.remove('filter-open');
            const button = header?.querySelector('.bom-column-filter-btn');
            button?.classList.remove('open');
            button?.setAttribute('aria-expanded', 'false');
        });
    }

    function alternarFiltroColumnaBOM(button) {
        const header = button.closest('th');
        const popover = header?.querySelector('.bom-column-filter-popover');
        if (!popover) return;
        const abrir = !popover.classList.contains('open');
        cerrarFiltrosColumnaBOM(popover);
        popover.classList.toggle('open', abrir);
        header.classList.toggle('filter-open', abrir);
        button.classList.toggle('open', abrir);
        button.setAttribute('aria-expanded', abrir ? 'true' : 'false');
        if (abrir) popover.querySelector('.bom-column-filter-input')?.focus();
    }

    function setFiltroColumnaBOM(col, value) {
        const texto = String(value || '').trim();
        if (texto) {
            bomColumnFilters[col] = texto;
        } else {
            delete bomColumnFilters[col];
        }
    }

    function limpiarFiltrosColumnaBOM(col) {
        if (col === undefined) {
            Object.keys(bomColumnFilters).forEach(key => delete bomColumnFilters[key]);
        } else {
            delete bomColumnFilters[col];
        }
        document.querySelectorAll('#bomDataTable .bom-column-filter-input').forEach(input => {
            input.value = bomColumnFilters[input.dataset.bomFilterCol] || '';
        });
        aplicarFiltrosColumnaBOM();
    }

    // Texto comparable de una celda; el checkbox de "Material original" vale CHECKED/UNCHECKED.
    function valorColumnaBOM(row, col) {
        const cell = row.cells[col];
        if (!cell) return '';
        const checkbox = cell.querySelector('input[type="checkbox"]');
        if (checkbox) return checkbox.checked ? 'CHECKED' : 'UNCHECKED';
        return (cell.dataset.fullText || cell.textContent || '').trim();
    }

    function aplicarFiltrosColumnaBOM() {
        const activos = Object.entries(bomColumnFilters).map(([col, value]) => [Number(col), value.toLowerCase()]);
        let total = 0;
        let visibles = 0;
        document.querySelectorAll('#bomTableBody tr').forEach(row => {
            if (row.cells.length <= 1) return; // fila de mensaje (sin datos / cargando)
            total++;
            const coincide = activos.every(([col, value]) => valorColumnaBOM(row, col).toLowerCase().includes(value));
            row.classList.toggle('bom-col-filtered', !coincide);
            if (coincide) visibles++;
        });
        document.querySelectorAll('#bomDataTable th[data-bom-filter]').forEach(header => {
            header.querySelector('.bom-column-filter-btn')?.classList.toggle('active', Boolean(bomColumnFilters[header.cellIndex]));
        });
        const contador = document.getElementById('bomResultCounter');
        if (contador) {
            contador.style.display = '';
            contador.textContent = activos.length ? `${visibles} de ${total} registros` : `${total} registros`;
        }
    }

    // ========== MODALES (WF_008) ==========
    // Los modales se crean por JS directamente en document.body (no viven en
    // el fragmento AJAX), una sola vez; ensureControlBomModals() es idempotente.
    const PERMISO_CREAR_ECO_ATTRS = 'data-permiso-pagina="LISTA_INFORMACIONBASICA" data-permiso-seccion="Control de produccion" data-permiso-boton="Crear ECO"';
    const PERMISO_APROBAR_ECO_ATTRS = 'data-permiso-pagina="LISTA_INFORMACIONBASICA" data-permiso-seccion="Control de produccion" data-permiso-boton="Aprobar ECO"';
    const BOM_ICON_PATHS = {
        close: '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>',
        eco: '<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"></path>',
        list: '<path d="M8 7h12M8 12h12M8 17h12M4 7h.01M4 12h.01M4 17h.01"></path>',
        detail: '<path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>',
        sync: '<polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"></path>',
        info: '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>'
    };

    function bomSvg(name, cls) {
        return `<svg class="${cls || ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">${BOM_ICON_PATHS[name]}</svg>`;
    }

    function bomModalHeader(icon, titleId, title, subtitle, closeId) {
        return `
            <div class="bom-modal-header">
                <div class="bom-modal-title-group">
                    ${bomSvg(icon, 'bom-modal-icon')}
                    <div>
                        <h3 id="${titleId}">${title}</h3>
                        ${subtitle ? `<span class="bom-modal-subtitle">${subtitle}</span>` : ''}
                    </div>
                </div>
                <button type="button" class="bom-modal-close" id="${closeId}" aria-label="Cerrar">${bomSvg('close')}</button>
            </div>`;
    }

    function bomFilterGroup(id, label, control) {
        return `<div class="bom-filter-group"><label for="${id}">${label}</label>${control}</div>`;
    }

    const CONTROL_BOM_MODALS = {
        controlBomAlertModal: () => `
            <div id="controlBomAlertDialog" tabindex="0" role="alertdialog" aria-modal="true" aria-describedby="controlBomAlertMessage">
                ${bomSvg('info', 'bom-alert-icon')}
                <div id="controlBomAlertMessage"></div>
                <button type="button" id="controlBomAlertOkBtn" class="bom-btn consultar">OK</button>
            </div>`,
        controlBomLoadingModal: () => `
            <div id="controlBomLoadingDialog" role="dialog" aria-modal="true" aria-labelledby="controlBomLoadingTitle">
                <div id="controlBomLoadingTitle">Cargando BOM</div>
                <div id="controlBomLoadingMessage">Procesando archivo Excel...</div>
                <div id="controlBomLoadingProgressContainer">
                    <div id="controlBomLoadingProgressBar"><div id="controlBomLoadingProgressFill"></div></div>
                    <div id="controlBomLoadingProgressText">0% completado</div>
                    <div id="controlBomLoadingTimeEstimate">Estimando tiempo...</div>
                </div>
                <div id="controlBomLoadingSpinner"></div>
            </div>`,
        ecoModal: () => `
            <div class="bom-modal-content" role="dialog" aria-modal="true" aria-labelledby="ecoModalTitle">
                ${bomModalHeader('eco', 'ecoModalTitle', 'Crear ECO / Cambio de ingenieria', 'Descargar BOM, modificarlo y aprobar el cambio', 'btnCerrarEcoModal')}
                <div class="bom-modal-filters bom-eco-steps">
                    <div id="ecoStepIndicator1" class="bom-eco-step active">1. Descargar BOM</div>
                    <div id="ecoStepIndicator2" class="bom-eco-step">2. Subir Excel modificado</div>
                    <div id="ecoStepIndicator3" class="bom-eco-step">3. Revisar y aprobar</div>
                </div>
                <div class="bom-modal-body">
                    <div id="ecoStep1">
                        <div class="bom-scope-options">
                            <label class="bom-scope-option">
                                <input type="radio" name="ecoScopeKind" value="SINGLE" id="ecoScopeSingle" checked>
                                <span><b>ECO individual</b><br><small>Un solo modelo</small></span>
                            </label>
                            <label class="bom-scope-option">
                                <input type="radio" name="ecoScopeKind" value="FAMILY" id="ecoScopeFamily">
                                <span><b>ECO de familia</b><br><small>Aplicar a varios modelos de una familia</small></span>
                            </label>
                            <label class="bom-scope-option">
                                <input type="radio" name="ecoScopeKind" value="NEW_BOM" id="ecoScopeNewBom">
                                <span><b>Nuevo BOM</b><br><small>Primera carga para un modelo</small></span>
                            </label>
                        </div>
                        <div class="bom-form-grid">
                            <label class="bom-modal-field">ECO <input id="ecoNoInput" type="text"></label>
                            <label id="ecoPartNoLabel" class="bom-modal-field">Numero de parte / modelo <input id="ecoPartNoInput" type="text"></label>
                            <label class="bom-modal-field">Revision BOM nueva <input id="ecoRevisionInput" type="text" value="Automatica" readonly title="MES asigna la siguiente revision disponible"></label>
                            <label class="bom-modal-field">Fecha efectiva <input id="ecoEffectiveAtInput" type="datetime-local"></label>
                        </div>
                        <div id="ecoFamilyFields" class="bom-family-fields" style="display:none;">
                            <div class="bom-form-grid is-family">
                                <label class="bom-modal-field">Familia (prefijo) <input id="ecoFamilyInput" type="text" placeholder="Ej: EBR239662"></label>
                                <label class="bom-modal-field">Sufijos <input id="ecoSuffixesInput" type="text" placeholder="Ej: 01,05,14"></label>
                                <button id="btnResolverFamilia" class="bom-btn consultar" type="button">Resolver</button>
                            </div>
                            <div id="ecoFamilyResolveBox" class="bom-info-box" style="display:none;"></div>
                        </div>
                        <label class="bom-modal-field is-spaced">Nombre del modelo (item_name)
                            <input id="ecoItemNameInput" type="text" placeholder="Opcional: si esta vacio se autocompleta desde KS catalog">
                        </label>
                        <label class="bom-modal-field is-spaced">Notas <textarea id="ecoNotesInput" rows="3"></textarea></label>
                        <div id="ecoStatusBox" class="bom-info-box">
                            Llene los datos y descargue el BOM actual. Modifique el Excel y suba el archivo en el paso 2. No edite la columna oculta __row_id.
                        </div>
                        <div class="bom-modal-footer is-end">
                            <button id="btnDescargarBomExcel" class="bom-btn exportar" type="button">Descargar BOM como Excel</button>
                            <button id="btnIrPaso2" class="bom-btn consultar" type="button">Siguiente: subir Excel &rarr;</button>
                        </div>
                    </div>
                    <div id="ecoStep2" style="display:none;">
                        <div id="ecoStep2Help" class="bom-info-box">
                            Suba el Excel modificado. El sistema validara y mostrara los cambios detectados (anadidos, eliminados, modificados).
                        </div>
                        <label class="bom-modal-field is-spaced">Archivo Excel <input type="file" id="ecoExcelInput" accept=".xlsx,.xls"></label>
                        <div id="ecoValidationBox" class="bom-info-box" style="display:none;"></div>
                        <div class="bom-modal-footer">
                            <button id="btnVolverPaso1" class="bom-btn" type="button">&larr; Volver</button>
                            <button id="btnValidarExcel" class="bom-btn registrar" type="button">Validar y crear borrador</button>
                        </div>
                    </div>
                    <div id="ecoStep3" style="display:none;">
                        <div id="ecoDiffSummary" class="bom-info-box">Resumen de cambios</div>
                        <div id="ecoDiffDetails" class="bom-diff-details"></div>
                        <div class="bom-modal-footer">
                            <button id="btnCancelarEcoDraft" class="bom-btn eliminar" type="button" ${PERMISO_CREAR_ECO_ATTRS}>Cancelar borrador</button>
                            <button id="btnAprobarEco" class="bom-btn consultar" type="button" ${PERMISO_APROBAR_ECO_ATTRS}>Aprobar ECO y aplicar cambios</button>
                        </div>
                    </div>
                </div>
            </div>`,
        ecoListModal: () => `
            <div class="bom-modal-content is-wide" role="dialog" aria-modal="true" aria-labelledby="ecoListModalTitle">
                ${bomModalHeader('list', 'ecoListModalTitle', 'ECOs / Cambios de ingenieria', 'Historial unificado MES + K-system', 'btnCerrarEcoListModal')}
                <div class="bom-modal-filters">
                    ${bomFilterGroup('ecoListOrigenFilter', 'Tipo', `<select id="ecoListOrigenFilter"><option value="">TODOS</option><option value="MES">MES</option><option value="KS">KS</option></select>`)}
                    ${bomFilterGroup('ecoListStatusFilter', 'Estatus', `<select id="ecoListStatusFilter"><option value="">TODOS</option><option value="DRAFT">DRAFT</option><option value="APPROVED">APPROVED</option><option value="CANCELLED">CANCELLED</option></select>`)}
                    ${bomFilterGroup('ecoListPartFilter', 'Modelo', '<input id="ecoListPartFilter" type="text" placeholder="Opcional">')}
                    ${bomFilterGroup('ecoListEcoFilter', 'ECO / ID', '<input id="ecoListEcoFilter" type="text" placeholder="02 o KS#28695">')}
                    ${bomFilterGroup('ecoListDateFromFilter', 'Desde', '<input id="ecoListDateFromFilter" type="date">')}
                    ${bomFilterGroup('ecoListDateToFilter', 'Hasta', '<input id="ecoListDateToFilter" type="date">')}
                    <button id="btnRefrescarEcoList" class="bom-btn consultar" type="button">Refrescar</button>
                    <button id="btnExportarEcoList" class="bom-btn exportar" type="button">Exportar Excel</button>
                </div>
                <div class="bom-modal-body">
                    <div id="ecoListStatusBox" class="bom-info-box">Cargando ECOs...</div>
                    <div class="bom-table-wrap bom-eco-list-wrap">
                        <table class="bom-subtable">
                            <thead>
                                <tr>
                                    <th>ECO</th><th>Modelo(s)</th><th>Revision</th><th>Fecha efectiva</th>
                                    <th>Estatus</th><th>Aprobado por</th><th class="is-center">Accion</th>
                                </tr>
                            </thead>
                            <tbody id="ecoListTableBody">
                                <tr class="bom-empty-row"><td colspan="7">Sin datos</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div id="ecoListPaginationBox" class="bom-pagination">
                        <button id="btnEcoListPrevPage" class="bom-btn bom-btn-sm" type="button">Anterior</button>
                        <span id="ecoListPageInfo"></span>
                        <button id="btnEcoListNextPage" class="bom-btn bom-btn-sm" type="button">Siguiente</button>
                    </div>
                </div>
            </div>`,
        ecoDetailBox: () => `
            <div class="bom-modal-content is-wide" role="dialog" aria-modal="true" aria-labelledby="ecoDetailTitle">
                ${bomModalHeader('detail', 'ecoDetailTitle', 'Detalle ECO', '', 'btnCerrarEcoDetailModal')}
                <div id="ecoDetailContent" class="bom-modal-body">Cargando...</div>
            </div>`,
        ecnKsDetailModal: () => `
            <div class="bom-modal-content" role="dialog" aria-modal="true" aria-labelledby="ecnKsDetailTitle">
                ${bomModalHeader('sync', 'ecnKsDetailTitle', 'Detalle ECN K-system', '', 'btnCerrarEcnKsModal')}
                <div id="ecnKsDetailContent" class="bom-modal-body">Cargando...</div>
            </div>`
    };

    // Se cierran con clic fuera o Escape, del de arriba hacia abajo (z-index).
    // El asistente de ECO no, para no perder lo capturado por un clic accidental.
    const BOM_MODALES_CERRABLES = ['ecoDetailBox', 'ecnKsDetailModal', 'ecoListModal'];
    let controlBomModalKeysAttached = false;

    function ensureControlBomModals() {
        Object.keys(CONTROL_BOM_MODALS).forEach(id => {
            if (document.getElementById(id)) return;
            const modal = document.createElement('div');
            modal.id = id;
            modal.className = 'bom-modal';
            modal.innerHTML = CONTROL_BOM_MODALS[id]();
            if (BOM_MODALES_CERRABLES.includes(id)) {
                modal.addEventListener('click', event => {
                    if (event.target === modal) cerrarModalBom(id);
                });
            }
            if (id === 'controlBomAlertModal') {
                modal.querySelector('#controlBomAlertOkBtn').addEventListener('click', () => window.hideCustomAlert());
            }
            document.body.appendChild(modal);
        });
        if (!controlBomModalKeysAttached) {
            controlBomModalKeysAttached = true;
            document.addEventListener('keydown', onControlBomModalKeydown);
        }
    }

    function bomModalVisible(id) {
        const modal = document.getElementById(id);
        return Boolean(modal) && modal.style.display === 'flex';
    }

    function onControlBomModalKeydown(event) {
        if (bomModalVisible('controlBomAlertModal')) {
            if (event.key === 'Escape' || event.key === 'Enter') {
                event.preventDefault();
                window.hideCustomAlert();
            }
            return;
        }
        if (event.key !== 'Escape') return;
        if (bomModalVisible('ecoFilesViewer')) {
            cerrarVisorPapeleria();
            return;
        }
        const abierto = BOM_MODALES_CERRABLES.find(bomModalVisible);
        if (abierto === 'ecoListModal') {
            cerrarModalEcoList();
        } else if (abierto) {
            cerrarModalBom(abierto);
        }
    }

    function abrirModalBom(id) {
        ensureControlBomModals();
        const modal = document.getElementById(id);
        if (!modal) return null;
        modal.style.display = 'flex';
        modal.style.opacity = '1';
        modal.style.visibility = 'visible';
        return modal;
    }

    function cerrarModalBom(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.style.display = 'none';
        modal.style.opacity = '0';
        modal.style.visibility = 'hidden';
    }

    // ========== EVENT DELEGATION PARA AJAX ==========
    function initializeControlBOMEventListeners() {
        ensureControlBomStyles();
        ensureControlBomModals();
        renderBomColumnFilterHeaders();
        console.log('🎯 Inicializando Event Listeners para Control BOM');
        
        // Protección contra inicialización múltiple
        if (!document.body.dataset.controlBOMListenersAttached) {
            
            // Event delegation para clicks en botones principales
            document.body.addEventListener('click', function(e) {
                const target = e.target;
                
                // Filtros por columna de la tabla (estilo ICT)
                const columnFilterButton = target.closest('.bom-column-filter-btn');
                if (columnFilterButton) {
                    e.preventDefault();
                    alternarFiltroColumnaBOM(columnFilterButton);
                    return;
                }
                const columnFilterClear = target.closest('.bom-column-filter-clear');
                if (columnFilterClear) {
                    e.preventDefault();
                    limpiarFiltrosColumnaBOM(columnFilterClear.closest('th').cellIndex);
                    return;
                }
                if (target.closest('.bom-column-filter-clear-all')) {
                    e.preventDefault();
                    limpiarFiltrosColumnaBOM();
                    return;
                }
                if (!target.closest('.bom-column-filter-popover')) {
                    cerrarFiltrosColumnaBOM();
                }

                // Botón Consultar
                if (target.id === 'btnConsultarBOM' || target.closest('#btnConsultarBOM')) {
                    e.preventDefault();
                    consultarBOM();
                    return;
                }
                
                // Boton Crear ECO
                if (target.id === 'btnCrearECO' || target.closest('#btnCrearECO')) {
                    e.preventDefault();
                    if (!requierePermisoCrearEco()) return;
                    abrirModalECO();
                    return;
                }

                // Boton Ver ECOs
                if (target.id === 'btnVerECOS' || target.closest('#btnVerECOS')) {
                    e.preventDefault();
                    abrirModalEcoList();
                    return;
                }
                
                // Botón Exportar Excel
                if (target.id === 'btnExportarExcelBOM' || target.closest('#btnExportarExcelBOM')) {
                    e.preventDefault();
                    exportarExcelBOM();
                    return;
                }
                
                // Dropdown items
                if (target.classList.contains('bom-dropdown-item')) {
                    const modelo = target.dataset.value;
                    seleccionarModelo(modelo);
                    return;
                }
                
                if (target.id === 'btnCerrarEcoModal') {
                    e.preventDefault();
                    cerrarModalECO();
                    return;
                }

                if (target.id === 'btnDescargarBomExcel') {
                    e.preventDefault();
                    descargarBomExcel();
                    return;
                }

                if (target.id === 'btnResolverFamilia') {
                    e.preventDefault();
                    resolverFamilia();
                    return;
                }

                if (target.name === 'ecoScopeKind') {
                    onEcoScopeChange();
                    return;
                }

                if (target.id === 'btnIrPaso2') {
                    e.preventDefault();
                    irPasoEco(2);
                    return;
                }

                if (target.id === 'btnVolverPaso1') {
                    e.preventDefault();
                    irPasoEco(1);
                    return;
                }

                if (target.id === 'btnValidarExcel') {
                    e.preventDefault();
                    validarExcelEco();
                    return;
                }

                if (target.id === 'btnCancelarEcoDraft') {
                    e.preventDefault();
                    cancelarBorradorEco();
                    return;
                }

                if (target.id === 'btnAprobarEco') {
                    e.preventDefault();
                    aprobarEcoActual();
                    return;
                }

                if (target.id === 'btnCerrarEcoListModal') {
                    e.preventDefault();
                    cerrarModalEcoList();
                    return;
                }

                if (target.id === 'btnRefrescarEcoList') {
                    e.preventDefault();
                    cargarEcoList(1);
                    return;
                }

                if (target.id === 'btnExportarEcoList') {
                    e.preventDefault();
                    exportarEcoList();
                    return;
                }

                if (target.id === 'btnEcoListPrevPage') {
                    e.preventDefault();
                    cargarEcoList(Math.max(1, ecoListPage - 1));
                    return;
                }

                if (target.id === 'btnEcoListNextPage') {
                    e.preventDefault();
                    cargarEcoList(ecoListPage + 1);
                    return;
                }

                const detailButton = target.closest('[data-eco-detail-id]');
                if (detailButton) {
                    e.preventDefault();
                    cargarDetalleEco(detailButton.dataset.ecoDetailId);
                    return;
                }

                if (target.id === 'btnCerrarEcoDetailModal' || target.closest('#btnCerrarEcoDetailModal')) {
                    e.preventDefault();
                    cerrarModalEcoDetalle();
                    return;
                }

                const ecnKsButton = target.closest('[data-ecn-ks-id]');
                if (ecnKsButton) {
                    e.preventDefault();
                    verEcnKs(ecnKsButton.dataset.ecnKsId);
                    return;
                }

                if (target.id === 'btnCerrarEcnKsModal' || target.closest('#btnCerrarEcnKsModal')) {
                    e.preventDefault();
                    cerrarModalEcnKs();
                    return;
                }

                if (target.closest('#btnPapeleriaBOM')) {
                    e.preventDefault();
                    verArchivosModelo();
                    return;
                }

                const fileTab = target.closest('[data-eco-file-tab]');
                if (fileTab) {
                    e.preventDefault();
                    abrirArchivoModelo(fileTab.dataset.ecoFileTab);
                    return;
                }

                const fileViewButton = target.closest('[data-eco-file-view]');
                if (fileViewButton) {
                    e.preventDefault();
                    verPapeleriaEco(
                        fileViewButton.dataset.ecoFileView,
                        fileViewButton.dataset.ecoFileExt,
                        fileViewButton.dataset.ecoFileName
                    );
                    return;
                }

                const fileDeleteButton = target.closest('[data-eco-file-delete]');
                if (fileDeleteButton) {
                    e.preventDefault();
                    borrarPapeleriaEco(fileDeleteButton.dataset.ecoFileDelete, fileDeleteButton.dataset.ecoFileName);
                    return;
                }

                const deleteButton = target.closest('[data-eco-delete-id]');
                if (deleteButton) {
                    e.preventDefault();
                    borrarEco(deleteButton.dataset.ecoDeleteId, deleteButton.dataset.ecoNo || '');
                    return;
                }

                const approveButton = target.closest('[data-eco-approve-id]');
                if (approveButton) {
                    e.preventDefault();
                    aprobarEcoDesdeLista(
                        approveButton.dataset.ecoApproveId,
                        approveButton.dataset.ecoNo || '',
                        approveButton
                    );
                    return;
                }
            });
            
            document.body.addEventListener('input', function(e) {
                if (e.target.matches('.bom-column-filter-input')) {
                    setFiltroColumnaBOM(e.target.dataset.bomFilterCol, e.target.value);
                    aplicarFiltrosColumnaBOM();
                }
            });

            document.body.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' && e.target.matches('.bom-column-filter-input')) {
                    cerrarFiltrosColumnaBOM();
                }
            });

            // Event delegation para input en el buscador
            document.body.addEventListener('keyup', function(e) {
                if (e.target.id === 'bomModeloSearch') {
                    filtrarModelos();
                    limpiarRevisionSiCambioModelo(e.target.value);
                }
            });
            
            // Event delegation para click en el buscador
            document.body.addEventListener('click', function(e) {
                if (e.target.id === 'bomModeloSearch') {
                    mostrarDropdown();
                }
            });
            
            // Event delegation para change en file input
            document.body.addEventListener('change', function(e) {
                if (e.target.id === 'ecoExcelInput') {
                    const fileName = e.target.files?.[0]?.name || '';
                    const box = document.getElementById('ecoValidationBox');
                    if (box && fileName) {
                        box.style.display = 'block';
                        box.innerHTML = `<span class="bom-msg">Archivo seleccionado: ${escapeHtml(fileName)}</span>`;
                    }
                    if (ecoScopeKind === 'NEW_BOM') {
                        inferPartNoFromSelectedFile();
                    }
                    return;
                }

                if (e.target.id === 'ecoFileInput') {
                    subirPapeleriaEco(e.target.files);
                    return;
                }

                if (e.target.id === 'ecoPartNoInput' && ecoScopeKind !== 'FAMILY') {
                    cargarRevisionEcoAutomatica({
                        partNo: (e.target.value || '').trim().toUpperCase()
                    });
                }

                if ([
                    'ecoListOrigenFilter',
                    'ecoListStatusFilter',
                    'ecoListPartFilter',
                    'ecoListEcoFilter',
                    'ecoListDateFromFilter',
                    'ecoListDateToFilter'
                ].includes(e.target.id)) {
                    cargarEcoList(1);
                }
                
                // Filtro por classification
                if (e.target.id === 'bomClassificationFilter') {
                    aplicarFiltroClassification();
                }

                if (e.target.id === 'bomRevisionFilter') {
                    aplicarFiltroRevisionBOM();
                }
            });
            
            document.body.dataset.controlBOMListenersAttached = 'true';
            console.log(' Event Listeners de Control BOM inicializados correctamente');
        } else {
            console.log('⚠️ Event Listeners de Control BOM ya estaban inicializados');
        }
    }
    
    // Exponer función de inicialización globalmente
    window.initializeControlBOMEventListeners = initializeControlBOMEventListeners;

    // Cache para datos de BOM
    const controlBomRoot = getControlBomRoot();
    const puedeCrearEco = controlBomRoot?.dataset.puedeCrearEco === 'true';
    const puedeAprobarEco = controlBomRoot?.dataset.puedeAprobarEco === 'true';
    let bomDataCache = [];
    let ecoActualId = null;
    let ecoScopeKind = 'SINGLE'; // 'SINGLE', 'FAMILY' o 'NEW_BOM'
    let ecoScopeParts = []; // part_no resueltos cuando FAMILY
    let ecoListPage = 1;
    let ecoListMeta = { total: 0, page: 1, page_size: 500, filters_active: false };

    function ecoAlert(message) {
        if (typeof showCustomAlert === 'function') {
            showCustomAlert(message);
        } else {
            alert(String(message).replace(/<br\s*\/?>/gi, '\n'));
        }
    }

    function setEcoStatus(message) {
        const box = document.getElementById('ecoStatusBox');
        if (box) box.innerHTML = message;
    }

    function syncEcoModeText() {
        const isNewBom = ecoScopeKind === 'NEW_BOM';
        const step1 = document.getElementById('ecoStepIndicator1');
        const step2 = document.getElementById('ecoStepIndicator2');
        const downloadBtn = document.getElementById('btnDescargarBomExcel');
        const uploadHelp = document.getElementById('ecoStep2Help');
        if (step1) step1.textContent = isNewBom ? '1. Plantilla nuevo BOM' : '1. Descargar BOM';
        if (step2) step2.textContent = isNewBom ? '2. Subir nuevo BOM' : '2. Subir Excel modificado';
        if (downloadBtn) downloadBtn.textContent = isNewBom ? 'Descargar plantilla BOM' : 'Descargar BOM como Excel';
        if (uploadHelp) {
            uploadHelp.textContent = isNewBom
                ? 'Suba el Excel del BOM nuevo. El sistema validara que el modelo no tenga BOM vigente y creara el borrador con todos los renglones como anadidos.'
                : 'Suba el Excel modificado. El sistema validara y mostrara los cambios detectados (anadidos, eliminados, modificados).';
        }
    }

    function setRevisionEcoAutomatica(value, title = '') {
        const input = document.getElementById('ecoRevisionInput');
        if (!input) return;
        input.value = value || 'Automatica';
        input.title = title || 'MES asigna la siguiente revision disponible';
    }

    function inferPartNoFromSelectedFile() {
        const partInput = document.getElementById('ecoPartNoInput');
        const fileInput = document.getElementById('ecoExcelInput');
        if (!partInput || !fileInput || String(partInput.value || '').trim()) return '';
        const fileName = fileInput.files?.[0]?.name || '';
        const match = fileName.toUpperCase().match(/[A-Z]{2,}\d{5,}/);
        if (!match) return '';
        partInput.value = match[0];
        cargarRevisionEcoAutomatica({ partNo: match[0] });
        setEcoStatus(`Modelo ${match[0]} detectado desde el nombre del archivo.`);
        return match[0];
    }

    async function cargarRevisionEcoAutomatica({ partNo = '', scopeParts = [] } = {}) {
        const parts = Array.isArray(scopeParts)
            ? scopeParts.map(part => String(part || '').trim().toUpperCase()).filter(Boolean)
            : [];
        const modelo = String(partNo || '').trim().toUpperCase();
        if (!modelo && !parts.length) {
            setRevisionEcoAutomatica('Automatica', 'Capture modelo o resuelva familia para calcularla');
            return;
        }

        setRevisionEcoAutomatica('Calculando...', 'Consultando revisiones KS y ECO reservadas');
        const params = new URLSearchParams();
        if (parts.length) {
            params.set('scope_parts', parts.join(','));
        } else {
            params.set('part_no', modelo);
        }

        try {
            const response = await fetch(`/api/bom/next-eco-revision?${params.toString()}`);
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'No se pudo calcular revision');
            }
            const revision = data.data?.bom_revision || 'Automatica';
            setRevisionEcoAutomatica(
                revision,
                `Revision nueva reservada al crear el ECO: ${revision}`
            );
        } catch (error) {
            console.error('Error calculando revision ECO automatica:', error);
            setRevisionEcoAutomatica(
                'Automatica al validar',
                'MES calculara la revision al crear el borrador'
            );
        }
    }

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, function(char) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[char];
        });
    }

    function setEcoListStatus(message) {
        const box = document.getElementById('ecoListStatusBox');
        if (box) box.innerHTML = message;
    }

    function statusBadge(status) {
        const value = String(status || '').toUpperCase();
        const variante = value === 'APPROVED' ? ' is-approved' : value === 'DRAFT' ? ' is-draft' : '';
        return `<span class="bom-badge${variante}">${escapeHtml(value || '-')}</span>`;
    }

    function formatFechaEfectiva(value) {
        if (!value) return '-';
        const text = String(value);
        const match = text.match(/^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}(?::\d{2})?))?/);
        if (!match) return text;
        const fecha = match[1];
        const hora = match[2];
        if (!hora || hora.startsWith('00:00')) return fecha;
        return `${fecha} ${hora.slice(0, 5)}`;
    }

    function asegurarMetadatosEcoParaImportar() {
        const ecoNoInput = document.getElementById('ecoNoInput');
        const effectiveAtInput = document.getElementById('ecoEffectiveAtInput');
        if (!ecoNoInput || !effectiveAtInput) return { ecoNo: '', effectiveAt: '' };

        let ecoNo = (ecoNoInput.value || '').trim().toUpperCase();
        let effectiveAt = (effectiveAtInput.value || '').trim();
        const ajustes = [];

        if (!ecoNo) {
            const now = new Date();
            const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;
            ecoNo = `AUTO-${stamp}`;
            ecoNoInput.value = ecoNo;
            ajustes.push(`ECO ${ecoNo}`);
        }

        if (!effectiveAt) {
            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            effectiveAt = now.toISOString().slice(0, 16);
            effectiveAtInput.value = effectiveAt;
            ajustes.push(`fecha efectiva ${effectiveAt.replace('T', ' ')}`);
        }

        if (ajustes.length) {
            setEcoStatus(`Se completaron automaticamente ${ajustes.join(' y ')} para importar el BOM como ECO.`);
        }

        return { ecoNo, effectiveAt };
    }

    function abrirModalECO() {
        if (!requierePermisoCrearEco()) return;
        ensureControlBomModals();
        const selectedModel = (document.getElementById('bomModeloSearch')?.value || '').trim().toUpperCase();
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        const defaultEffective = now.toISOString().slice(0, 16);

        ecoActualId = null;
        ecoScopeKind = 'SINGLE';
        ecoScopeParts = [];
        document.getElementById('ecoScopeSingle').checked = true;
        document.getElementById('ecoScopeFamily').checked = false;
        const newBomRadio = document.getElementById('ecoScopeNewBom');
        if (newBomRadio) newBomRadio.checked = false;
        document.getElementById('ecoFamilyFields').style.display = 'none';
        document.getElementById('ecoFamilyResolveBox').style.display = 'none';
        document.getElementById('ecoFamilyInput').value = '';
        document.getElementById('ecoSuffixesInput').value = '';
        document.getElementById('ecoPartNoLabel').style.display = '';

        document.getElementById('ecoNoInput').value = '';
        document.getElementById('ecoPartNoInput').value = selectedModel;
        setRevisionEcoAutomatica('Automatica');
        document.getElementById('ecoEffectiveAtInput').value = defaultEffective;
        document.getElementById('ecoItemNameInput').value = '';
        document.getElementById('ecoNotesInput').value = '';
        const excelInput = document.getElementById('ecoExcelInput');
        if (excelInput) excelInput.value = '';
        document.getElementById('ecoValidationBox').style.display = 'none';
        document.getElementById('ecoValidationBox').innerHTML = '';
        setEcoStatus('Llene los datos y descargue el BOM actual. Modifique el Excel y suba el archivo en el paso 2.');
        syncEcoModeText();
        irPasoEco(1);
        cargarRevisionEcoAutomatica({ partNo: selectedModel });
        abrirModalBom('ecoModal');
    }

    function irPasoEco(paso) {
        for (let i = 1; i <= 3; i++) {
            const step = document.getElementById('ecoStep' + i);
            const indicator = document.getElementById('ecoStepIndicator' + i);
            if (step) step.style.display = (i === paso) ? 'block' : 'none';
            if (indicator) {
                indicator.classList.toggle('active', i === paso);
                indicator.classList.toggle('done', i < paso);
            }
        }
        syncEcoApprovalControls();
    }

    function onEcoScopeChange() {
        ecoScopeKind = document.querySelector('input[name="ecoScopeKind"]:checked')?.value || 'SINGLE';
        const isFamily = ecoScopeKind === 'FAMILY';
        const isNewBom = ecoScopeKind === 'NEW_BOM';
        document.getElementById('ecoFamilyFields').style.display = isFamily ? 'block' : 'none';
        document.getElementById('ecoPartNoLabel').style.display = isFamily ? 'none' : '';
        syncEcoModeText();
        // En FAMILY el part_no representa la familia, no se llena manualmente.
        if (isFamily) {
            ecoScopeParts = [];
            setRevisionEcoAutomatica('Resuelva familia', 'La revision se calcula con los modelos del scope');
            setEcoStatus('Resuelva la familia, descargue el BOM multi-modelo, modifiquelo y suba el Excel en el paso 2.');
            return;
        }
        if (isNewBom) {
            ecoScopeParts = [];
            setEcoStatus('Modo Nuevo BOM: descargue la plantilla o suba un Excel con las columnas BOM. Al validar, todos los renglones se marcaran como anadidos.');
        } else {
            setEcoStatus('Llene los datos y descargue el BOM actual. Modifique el Excel y suba el archivo en el paso 2.');
        }
        cargarRevisionEcoAutomatica({
            partNo: (document.getElementById('ecoPartNoInput')?.value || '').trim().toUpperCase()
        });
    }

    async function resolverFamilia() {
        if (!requierePermisoCrearEco()) return;
        const family = (document.getElementById('ecoFamilyInput')?.value || '').trim().toUpperCase();
        const suffixes = (document.getElementById('ecoSuffixesInput')?.value || '').trim();
        const box = document.getElementById('ecoFamilyResolveBox');
        box.style.display = 'block';
        if (!family || !suffixes) {
            box.innerHTML = `<span class="bom-msg is-error">Familia y sufijos son requeridos.</span>`;
            ecoScopeParts = [];
            return;
        }
        box.innerHTML = `<span class="bom-msg">Resolviendo...</span>`;
        try {
            const params = new URLSearchParams({ family, suffixes });
            const response = await fetch(`/api/bom/resolve-family?${params.toString()}`);
            const data = await response.json();
            if (!data.success) {
                box.innerHTML = `<span class="bom-msg is-error">${escapeHtml(data.error || 'Error')}</span>`;
                ecoScopeParts = [];
                return;
            }
            const d = data.data || {};
            const parts = d.parts || [];
            const missing = d.missing || [];
            ecoScopeParts = parts.map(p => p.part_no);
            cargarRevisionEcoAutomatica({ scopeParts: ecoScopeParts });
            const partsList = parts.map(p => `<li><b>${escapeHtml(p.part_no)}</b> ${p.item_name ? '— ' + escapeHtml(p.item_name) : ''}</li>`).join('');
            const missingNote = missing.length ? `<span class="bom-msg is-error is-title">Sufijos no encontrados en KS: ${missing.map(escapeHtml).join(', ')}</span>` : '';
            box.innerHTML = `
                <span class="bom-msg is-ok is-title">${parts.length} modelo(s) resuelto(s):</span>
                <ul class="bom-msg-list">${partsList}</ul>
                ${missingNote}
            `;
        } catch (err) {
            box.innerHTML = `<span class="bom-msg is-error">Error: ${escapeHtml(err.message || String(err))}</span>`;
            ecoScopeParts = [];
        }
    }

    function descargarBomExcel() {
        if (!requierePermisoCrearEco()) return;
        if (ecoScopeKind === 'FAMILY') {
            const family = (document.getElementById('ecoFamilyInput')?.value || '').trim().toUpperCase();
            const suffixes = (document.getElementById('ecoSuffixesInput')?.value || '').trim();
            if (!family || !suffixes) {
                ecoAlert('Capture familia y sufijos, y haga click en Resolver antes de descargar.');
                return;
            }
            if (!ecoScopeParts.length) {
                ecoAlert('Primero resuelva la familia (boton Resolver).');
                return;
            }
            const params = new URLSearchParams({ family, suffixes });
            const link = document.createElement('a');
            link.href = `/api/bom/download-excel-family?${params.toString()}`;
            link.target = '_blank';
            link.rel = 'noopener';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            setEcoStatus(`Descargando BOM multi-modelo de familia ${family} (${ecoScopeParts.length} modelos). Modifique y avance al paso 2.`);
            return;
        }

        const partNo = (document.getElementById('ecoPartNoInput')?.value || '').trim().toUpperCase();
        if (!partNo) {
            ecoAlert('Capture el numero de parte / modelo antes de descargar.');
            return;
        }
        cargarRevisionEcoAutomatica({ partNo });
        const isNewBom = ecoScopeKind === 'NEW_BOM';
        const params = new URLSearchParams({ part_no: partNo });
        if (isNewBom) params.set('mode', 'new_bom');
        const link = document.createElement('a');
        link.href = `/api/bom/download-excel?${params.toString()}`;
        link.target = '_blank';
        link.rel = 'noopener';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setEcoStatus(
            isNewBom
                ? `Descargando plantilla para nuevo BOM de ${partNo}. Capture los renglones y avance al paso 2.`
                : `Descargando BOM de ${partNo}. Modifique el Excel y avance al paso 2.`
        );
    }

    async function validarExcelEco() {
        if (!requierePermisoCrearEco()) return;
        const ecoMeta = asegurarMetadatosEcoParaImportar();
        const ecoNo = ecoMeta.ecoNo;
        const effectiveAt = ecoMeta.effectiveAt;
        const itemName = (document.getElementById('ecoItemNameInput')?.value || '').trim();
        const notes = (document.getElementById('ecoNotesInput')?.value || '').trim();
        const fileInput = document.getElementById('ecoExcelInput');
        const file = fileInput?.files?.[0];

        const box = document.getElementById('ecoValidationBox');
        box.style.display = 'block';

        if (!ecoNo || !effectiveAt) {
            box.innerHTML = `<span class="bom-msg is-error">Faltan campos requeridos (paso 1): ECO y Fecha efectiva.</span>`;
            return;
        }
        if (!file) {
            box.innerHTML = `<span class="bom-msg is-error">Seleccione el archivo Excel modificado.</span>`;
            return;
        }

        box.innerHTML = `<span class="bom-msg">Validando Excel...</span>`;
        const fd = new FormData();
        fd.append('file', file);
        fd.append('eco_no', ecoNo);
        fd.append('effective_at', effectiveAt);
        fd.append('item_name', itemName);
        fd.append('notes', notes);
        if (ecoScopeKind === 'NEW_BOM') {
            fd.append('bom_mode', 'NEW_BOM');
        }

        let endpoint;
        if (ecoScopeKind === 'FAMILY') {
            const family = (document.getElementById('ecoFamilyInput')?.value || '').trim().toUpperCase();
            if (!family) {
                box.innerHTML = `<span class="bom-msg is-error">Familia requerida.</span>`;
                return;
            }
            if (!ecoScopeParts.length) {
                box.innerHTML = `<span class="bom-msg is-error">No hay modelos resueltos. Vuelva al paso 1 y resuelva la familia.</span>`;
                return;
            }
            fd.append('family_prefix', family);
            fd.append('scope_parts', ecoScopeParts.join(','));
            endpoint = '/api/ecos/from-excel-family';
        } else {
            const inferredPartNo = ecoScopeKind === 'NEW_BOM' ? inferPartNoFromSelectedFile() : '';
            const partNo = ((document.getElementById('ecoPartNoInput')?.value || inferredPartNo || '')).trim().toUpperCase();
            if (!partNo) {
                box.innerHTML = `<span class="bom-msg is-error">Numero de parte requerido.</span>`;
                return;
            }
            fd.append('part_no', partNo);
            endpoint = '/api/ecos/from-excel';
        }

        try {
            const response = await fetch(endpoint, { method: 'POST', body: fd });
            const data = await response.json();
            if (!data.success) {
                const errors = data.errors || [data.error || 'Error desconocido'];
                box.innerHTML = `<span class="bom-msg is-error is-title">Validacion fallida:</span><ul class="bom-msg-list bom-msg is-error">${errors.map(e => `<li>${escapeHtml(e)}</li>`).join('')}</ul>`;
                return;
            }
            ecoActualId = data.eco_id;
            if (data.bom_revision) {
                setRevisionEcoAutomatica(data.bom_revision);
            }
            const revisionTexto = data.bom_revision ? ` - BOM rev ${escapeHtml(data.bom_revision)}` : '';
            box.innerHTML = `<span class="bom-msg is-ok">Borrador creado (ECO ${escapeHtml(ecoNo)}${revisionTexto}). Avanzando al paso 3...</span>`;
            await cargarPreviewDiff(data.eco_id);
            irPasoEco(3);
        } catch (err) {
            box.innerHTML = `<span class="bom-msg is-error">Error de red: ${escapeHtml(err.message || String(err))}</span>`;
        }
    }

    // Fechas, remark, clase, proveedor y proceso: se aplican al aprobar pero no son cambio de ingenieria.
    function renderAdminChanges(rows, render) {
        if (!rows || !rows.length) return '';
        return `<details class="bom-admin-details">
            <summary>Ver ${rows.length} cambios de datos administrativos (fechas, remark, clase, proveedor, proceso)</summary>
            ${render(rows)}
        </details>`;
    }

    // Aviso (no bloquea) cuando el ECO elimina mas de la mitad del BOM: casi siempre es el Excel de otro modelo.
    function renderBigChangeWarning(warning) {
        if (!warning) return '';
        return `<div class="bom-warning">&#9888; ${escapeHtml(warning)}</div>`;
    }

    // Seccion del diff (anadidos / modificados / eliminados / administrativos),
    // compartida por el paso 3 del asistente y el detalle del ECO.
    function renderDiffSection(title, rows, accion, showPart, defaultPart) {
        if (!rows || !rows.length) return '';
        const variante = { ADD: 'is-add', MODIFY: 'is-mod', REMOVE: 'is-del' }[accion] || 'is-admin';
        const esModificacion = accion === 'MODIFY' || accion === 'ADMIN';
        const value = v => String(v ?? '').trim() || '-';
        const cell = (v, cls) => `<td class="${cls || ''}">${escapeHtml(value(v))}</td>`;
        const headers = (showPart ? ['Modelo'] : []).concat(esModificacion
            ? ['Nivel', 'Item', 'Campo', 'Antes', 'Despues']
            : ['Nivel', 'Item', 'Nombre', 'Qty', 'Ubicacion', 'Maker / proveedor']);
        const body = rows.map(r => {
            const part = showPart ? cell(r.part_no || defaultPart, 'c-part') : '';
            if (esModificacion) {
                return `<tr>${part}${cell(r.bom_level, 'c-muted')}${cell(r.item_no, 'c-strong')}${cell(r.field_changed, 'c-field')}${cell(r.old_value, 'c-old')}${cell(r.new_value, 'c-new')}</tr>`;
            }
            const qtyUnit = [value(r.eco_qty), value(r.eco_unit)].filter(v => v !== '-').join(' ');
            const makerSupplier = [value(r.eco_maker), value(r.eco_supplier)].filter(v => v !== '-').join(' / ');
            return `<tr>${part}${cell(r.bom_level, 'c-muted')}${cell(r.item_no, 'c-strong')}${cell(r.eco_item_name, 'c-wide')}${cell(qtyUnit, 'c-qty')}${cell(r.eco_location_text, 'c-wrap')}${cell(makerSupplier, 'c-wide')}</tr>`;
        }).join('');
        return `
            <div class="bom-section ${variante}">
                <div class="bom-section-title">${escapeHtml(title)} (${rows.length})</div>
                <table class="bom-subtable ${esModificacion ? 'is-diff-mod' : 'is-diff-full'}">
                    <thead><tr>${headers.map(h => `<th>${escapeHtml(h)}</th>`).join('')}</tr></thead>
                    <tbody>${body}</tbody>
                </table>
            </div>`;
    }

    function renderDiffChips(counts) {
        return `
            <div class="bom-chips">
                <span class="bom-chip is-add">+ ${escapeHtml(counts.added || 0)} anadidos</span>
                <span class="bom-chip is-mod">~ ${escapeHtml(counts.modified || 0)} modificados</span>
                <span class="bom-chip is-del">- ${escapeHtml(counts.removed || 0)} eliminados</span>
                ${counts.modified_admin ? `<span class="bom-chip">${escapeHtml(counts.modified_admin)} datos administrativos</span>` : ''}
            </div>`;
    }

    async function cargarPreviewDiff(ecoId) {
        const summary = document.getElementById('ecoDiffSummary');
        const details = document.getElementById('ecoDiffDetails');
        summary.innerHTML = 'Cargando diff...';
        details.innerHTML = '';
        try {
            const response = await fetch(`/api/ecos/${ecoId}/diff`);
            const data = await response.json();
            if (!data.success) {
                summary.innerHTML = `<span class="bom-msg is-error">${escapeHtml(data.error || 'Error cargando diff')}</span>`;
                return;
            }
            const d = data.data || {};
            const perPart = d.per_part || {};
            const perPartKeys = Object.keys(perPart).filter(k => k);
            const showPart = perPartKeys.length > 1;
            const perPartHtml = showPart
                ? `<div class="bom-per-part">
                    <b>Cambios por modelo:</b>
                    <div class="bom-chips">
                        ${perPartKeys.sort().map(pn => {
                            const c = perPart[pn];
                            return `<span class="bom-chip"><b>${escapeHtml(pn)}</b>: +${escapeHtml(c.added)} ~${escapeHtml(c.modified)} -${escapeHtml(c.removed)}</span>`;
                        }).join('')}
                    </div>
                </div>`
                : '';
            summary.innerHTML = renderDiffChips(d.counts || {}) + renderBigChangeWarning(d.warning) + perPartHtml;
            details.innerHTML =
                renderDiffSection('Anadidos', d.added, 'ADD', showPart) +
                renderDiffSection('Modificados', d.modified, 'MODIFY', showPart) +
                renderDiffSection('Eliminados', d.removed, 'REMOVE', showPart) +
                renderAdminChanges(d.modified_admin, rows => renderDiffSection('Datos administrativos', rows, 'ADMIN', showPart));
        } catch (err) {
            summary.innerHTML = `<span class="bom-msg is-error">Error: ${escapeHtml(err.message || String(err))}</span>`;
        }
    }

    async function cancelarBorradorEco() {
        if (!requierePermisoCrearEco()) return;
        if (!ecoActualId) {
            cerrarModalECO();
            return;
        }
        if (!confirm('Cancelar y eliminar este borrador?')) return;
        try {
            await fetch(`/api/ecos/${ecoActualId}`, { method: 'DELETE' });
        } catch (err) {
            console.warn('Error eliminando borrador:', err);
        }
        ecoActualId = null;
        cerrarModalECO();
    }

    function cerrarModalECO() {
        cerrarModalBom('ecoModal');
    }

    function abrirModalEcoList() {
        ensureControlBomModals();
        const selectedModel = (document.getElementById('bomModeloSearch')?.value || '').trim().toUpperCase();
        const partFilter = document.getElementById('ecoListPartFilter');
        if (partFilter && selectedModel) partFilter.value = selectedModel;
        cerrarModalEcoDetalle();
        abrirModalBom('ecoListModal');
        cargarEcoList(1);
    }

    function cerrarModalEcoList() {
        cerrarModalEcoDetalle();
        cerrarModalBom('ecoListModal');
    }

    function abrirModalEcoDetalle() {
        abrirModalBom('ecoDetailBox');
    }

    function cerrarModalEcoDetalle() {
        cerrarModalBom('ecoDetailBox');
    }

    function abrirModalEcnKs() {
        abrirModalBom('ecnKsDetailModal');
    }

    function cerrarModalEcnKs() {
        cerrarModalBom('ecnKsDetailModal');
    }

    function renderEcnKsField(label, value, opts) {
        opts = opts || {};
        const v = (value === null || value === undefined || value === '') ? '-' : String(value);
        const valor = opts.pre
            ? `<pre class="bom-field-pre">${escapeHtml(v)}</pre>`
            : `<div class="bom-field-value">${escapeHtml(v)}</div>`;
        return `<div class="bom-field"><div class="bom-field-label">${escapeHtml(label)}</div>${valor}</div>`;
    }

    async function verEcnKs(histSeq) {
        abrirModalEcnKs();
        const content = document.getElementById('ecnKsDetailContent');
        const title = document.getElementById('ecnKsDetailTitle');
        title.textContent = `ECN KS#${histSeq}`;
        content.innerHTML = '<div class="bom-msg">Cargando...</div>';
        try {
            const response = await fetch(`/api/ecn-ks/${encodeURIComponent(histSeq)}`);
            const data = await response.json();
            if (!data.success) {
                content.innerHTML = `<div class="bom-msg is-error">Error: ${escapeHtml(data.error || 'No se pudo cargar')}</div>`;
                return;
            }
            const e = data.data || {};
            title.textContent = `ECN KS#${e.hist_seq} - ${e.family_prefix || ''}`;
            content.innerHTML = `
                <div class="bom-field-grid">
                    ${renderEcnKsField('Family prefix', e.family_prefix)}
                    ${renderEcnKsField('Hist seq', e.hist_seq)}
                    ${renderEcnKsField('Item no', e.item_no)}
                    ${renderEcnKsField('Item seq', e.item_seq)}
                    ${renderEcnKsField('SB date', e.sb_date)}
                    ${renderEcnKsField('Work no', e.work_no)}
                    ${renderEcnKsField('Ord 1', e.ord1)}
                    ${renderEcnKsField('Decide 1', e.decide1)}
                    ${renderEcnKsField('Ord 2', e.ord2)}
                    ${renderEcnKsField('Decide 2', e.decide2)}
                    ${renderEcnKsField('BOM emp', e.bom_emp_name ? `${e.bom_emp_name} (${e.bom_emp_seq || '-'})` : '-')}
                    ${renderEcnKsField('Dev emp', e.dev_emp_name ? `${e.dev_emp_name} (${e.dev_emp_seq || '-'})` : '-')}
                    ${renderEcnKsField('Seongcheolsa', e.seongcheolsa)}
                    ${renderEcnKsField('Sincronizado', e.synced_at)}
                </div>
                ${renderEcnKsField('Remark del cambio (chg_remark)', e.chg_remark, { pre: true })}
                ${renderEcnKsField('Causa', e.cause, { pre: true })}
                ${renderEcnKsField('Resultado del paso (step_result)', e.step_result, { pre: true })}
                ${renderEcnKsField('Contexto del cambio (change_context)', e.change_context, { pre: true })}
                ${renderEcnKsField('Remark', e.remark, { pre: true })}
            `;
        } catch (err) {
            console.error('Error cargando ECN KS:', err);
            content.innerHTML = `<div class="bom-msg is-error">Error de red: ${escapeHtml(err.message || String(err))}</div>`;
        }
    }

    function buildEcoListParams(includePage) {
        const status = (document.getElementById('ecoListStatusFilter')?.value || '').trim();
        const partNo = (document.getElementById('ecoListPartFilter')?.value || '').trim().toUpperCase();
        const origen = (document.getElementById('ecoListOrigenFilter')?.value || '').trim().toUpperCase();
        const ecoNo = (document.getElementById('ecoListEcoFilter')?.value || '').trim().toUpperCase();
        const dateFrom = (document.getElementById('ecoListDateFromFilter')?.value || '').trim();
        const dateTo = (document.getElementById('ecoListDateToFilter')?.value || '').trim();
        const params = new URLSearchParams();
        if (origen) params.set('origen', origen);
        if (status) params.set('status', status);
        if (partNo) params.set('part_no', partNo);
        if (ecoNo) params.set('eco_no', ecoNo);
        if (dateFrom) params.set('date_from', dateFrom);
        if (dateTo) params.set('date_to', dateTo);
        if (includePage) {
            params.set('page', String(ecoListPage));
            params.set('page_size', '500');
        }
        return params;
    }

    function updateEcoListPagination(meta) {
        const box = document.getElementById('ecoListPaginationBox');
        const info = document.getElementById('ecoListPageInfo');
        const prev = document.getElementById('btnEcoListPrevPage');
        const next = document.getElementById('btnEcoListNextPage');
        if (!box || !info || !prev || !next) return;
        const total = Number(meta.total || 0);
        const pageSize = Number(meta.page_size || 500);
        const page = Number(meta.page || 1);
        const totalPages = Math.max(1, Math.ceil(total / pageSize));
        if (!meta.filters_active || total <= pageSize) {
            box.style.display = 'none';
            return;
        }
        box.style.display = 'flex';
        info.textContent = `Pagina ${page} de ${totalPages} · ${total} ECOs`;
        prev.disabled = page <= 1;
        next.disabled = page >= totalPages;
    }

    function exportarEcoList() {
        const params = buildEcoListParams(false);
        window.location.href = `/api/ecos/export?${params.toString()}`;
    }

    async function cargarEcoList(page) {
        const tbody = document.getElementById('ecoListTableBody');
        ecoListPage = Math.max(1, Number(page || ecoListPage || 1));

        tbody.innerHTML = '<tr class="bom-empty-row"><td colspan="7">Cargando...</td></tr>';
        setEcoListStatus('Consultando ECOs...');

        try {
            const params = buildEcoListParams(true);

            const response = await fetch(`/api/ecos?${params.toString()}`);
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'No se pudieron cargar los ECOs');
            }

            const rows = data.data || [];
            if (!rows.length) {
                tbody.innerHTML = '<tr class="bom-empty-row"><td colspan="7">No hay ECOs con esos filtros.</td></tr>';
                ecoListMeta = data.meta || ecoListMeta;
                updateEcoListPagination(ecoListMeta);
                setEcoListStatus('Sin ECOs para mostrar.');
                return;
            }

            tbody.innerHTML = rows.map(function(row) {
                const isKs = String(row.origen || '').toUpperCase() === 'KS';
                const statusValue = String(row.status || '').toUpperCase();
                const canDelete = !isKs && statusValue !== 'APPROVED';
                const canApprove = !isKs && statusValue === 'DRAFT';
                // Sin permiso de Crear ECO no se ofrece Borrar (WF_009); el backend lo valida igual.
                const deleteControl = canDelete
                    ? (puedeCrearEco ? `<button type="button" class="bom-btn eliminar" data-eco-delete-id="${escapeHtml(row.id)}" data-eco-no="${escapeHtml(row.eco_no)}" ${PERMISO_CREAR_ECO_ATTRS}>Borrar</button>` : '')
                    : `<span class="bom-msg">${isKs ? 'KS sync' : 'Inmutable'}</span>`;
                const approveControl = canApprove && puedeAprobarEco
                    ? `<button type="button" class="bom-btn registrar" data-eco-approve-id="${escapeHtml(row.id)}" data-eco-no="${escapeHtml(row.eco_no)}" ${PERMISO_APROBAR_ECO_ATTRS}>Aprobar</button>`
                    : '';
                const viewControl = isKs
                    ? `<button type="button" class="bom-btn consultar" data-ecn-ks-id="${escapeHtml(String(row.id).replace(/^ks-/, ''))}">Ver</button>`
                    : `<button type="button" class="bom-btn consultar" data-eco-detail-id="${escapeHtml(row.id)}">Ver</button>`;
                const origenBadge = isKs
                    ? '<span class="bom-badge is-ks">KS</span>'
                    : '<span class="bom-badge is-mes">MES</span>';
                const scopeCount = Number(row.scope_count || 0);
                const scopeParts = String(row.scope_parts || '').trim();
                const scopePartList = scopeParts.split(',').map(function(part) {
                    return part.trim();
                }).filter(Boolean);
                const isFamilyEco = !isKs && scopeCount > 1 && scopeParts;
                let familyLabel = scopePartList[0] || row.part_no || '-';
                if (scopePartList.length > 1) {
                    familyLabel = scopePartList.reduce(function(prefix, part) {
                        let i = 0;
                        while (i < prefix.length && i < part.length && prefix[i] === part[i]) i++;
                        return prefix.slice(0, i);
                    }, familyLabel);
                }
                const jobSuffixes = scopePartList.map(function(part) {
                    return familyLabel && part.indexOf(familyLabel) === 0 ? part.slice(familyLabel.length) : part;
                }).filter(Boolean).join(', ');
                const modeloCell = isFamilyEco
                    ? `<div title="${escapeHtml(scopeParts)}">
                           <b>${escapeHtml(familyLabel || scopeParts)}</b>
                           <div class="bom-family-sub">Trabajo: ${escapeHtml(jobSuffixes || scopeParts)}</div>
                       </div>`
                    : escapeHtml(row.part_no || '-');
                return `
                    <tr>
                        <td class="c-strong">${escapeHtml(row.eco_no)}${origenBadge}</td>
                        <td>${modeloCell}</td>
                        <td>${escapeHtml(row.bom_revision)}</td>
                        <td>${escapeHtml(formatFechaEfectiva(row.effective_at))}</td>
                        <td>${statusBadge(row.status)}</td>
                        <td>${escapeHtml(row.approved_by || '-')}</td>
                        <td><div class="bom-actions-cell">${viewControl}${approveControl}${deleteControl}</div></td>
                    </tr>
                `;
            }).join('');
            ecoListMeta = data.meta || {};
            updateEcoListPagination(ecoListMeta);
            const total = Number(ecoListMeta.total || rows.length);
            if (ecoListMeta.filters_active) {
                const from = ((Number(ecoListMeta.page || 1) - 1) * Number(ecoListMeta.page_size || 500)) + 1;
                const to = from + rows.length - 1;
                setEcoListStatus(`${rows.length} ECO(s) en esta pagina. Mostrando ${from}-${to} de ${total}.`);
            } else {
                const suffix = total > rows.length ? ` de ${total} totales` : '';
                setEcoListStatus(`Ultimos ${rows.length} ECO(s)${suffix}. Usa filtros para buscar sin limite fijo.`);
            }
        } catch (error) {
            console.error('Error cargando ECOs:', error);
            tbody.innerHTML = '<tr class="bom-empty-row"><td colspan="7" class="bom-msg is-error">Error cargando ECOs.</td></tr>';
            updateEcoListPagination({ filters_active: false });
            setEcoListStatus(`Error: ${escapeHtml(error.message)}`);
        }
    }

    function requierePermisoCrearEco() {
        if (puedeCrearEco) return true;
        ecoAlert('No tienes permiso para crear o modificar ECOs.');
        return false;
    }

    function requierePermisoAprobarEco() {
        if (puedeAprobarEco) return true;
        ecoAlert('No tienes permiso para aprobar ECOs.');
        return false;
    }

    function syncEcoApprovalControls() {
        const approveButton = document.getElementById('btnAprobarEco');
        if (!approveButton) return;
        approveButton.style.display = puedeAprobarEco ? '' : 'none';
        approveButton.disabled = false;
    }

    async function borrarEco(ecoId, ecoNo) {
        const label = ecoNo ? ` ${ecoNo}` : '';
        if (!confirm(`Borrar definitivamente el ECO${label}? Solo se permite si no esta APPROVED.`)) {
            return;
        }

        setEcoListStatus('Borrando ECO...');
        try {
            const response = await fetch(`/api/ecos/${encodeURIComponent(ecoId)}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'No se pudo borrar el ECO');
            }
            cerrarModalEcoDetalle();
            await cargarEcoList();
            setEcoListStatus(`ECO${label} borrado.`);
        } catch (error) {
            console.error('Error borrando ECO:', error);
            setEcoListStatus(`Error: ${escapeHtml(error.message)}`);
            ecoAlert(`Error borrando ECO:<br>${error.message}`);
        }
    }

    async function cargarDetalleEco(ecoId) {
        abrirModalEcoDetalle();
        const title = document.getElementById('ecoDetailTitle');
        const content = document.getElementById('ecoDetailContent');
        title.textContent = 'Cargando detalle...';
        content.innerHTML = '<div class="bom-msg">Cargando...</div>';

        try {
            const [detailResponse, diffResponse] = await Promise.all([
                fetch(`/api/ecos/${encodeURIComponent(ecoId)}`),
                fetch(`/api/ecos/${encodeURIComponent(ecoId)}/diff`)
            ]);
            const data = await detailResponse.json();
            const diffData = await diffResponse.json();
            if (!detailResponse.ok || !data.success) {
                throw new Error(data.error || 'No se pudo cargar el detalle');
            }
            if (!diffResponse.ok || !diffData.success) {
                throw new Error(diffData.error || 'No se pudo cargar el diff');
            }

            const eco = data.data || {};
            const diff = diffData.data || {};
            const totalCambios = (diff.added || []).length + (diff.modified || []).length + (diff.removed || []).length;
            const scopeParts = String(eco.scope_parts || '').trim();
            const scopeList = Array.isArray(eco.scope)
                ? eco.scope.map(row => row.part_no).filter(Boolean)
                : [];
            const modelScope = scopeParts || scopeList.join(', ') || eco.part_no || '-';
            const isFamily = String(eco.scope_kind || '').toUpperCase() === 'FAMILY' || scopeList.length > 1;
            const status = String(eco.status || '').toUpperCase();
            title.innerHTML = `ECO MES ${escapeHtml(eco.eco_no || eco.id || '')} ${statusBadge(eco.status)} <span class="bom-modal-subtitle">${totalCambios} cambios</span>`;

            const actionButtons = `
                <div class="bom-modal-footer is-end">
                    ${status === 'DRAFT' && puedeAprobarEco
                        ? `<button type="button" class="bom-btn registrar" data-eco-approve-id="${escapeHtml(eco.id)}" data-eco-no="${escapeHtml(eco.eco_no || '')}" ${PERMISO_APROBAR_ECO_ATTRS}>Aprobar ECO</button>`
                        : ''}
                    ${status !== 'APPROVED' && puedeCrearEco
                        ? `<button type="button" class="bom-btn eliminar" data-eco-delete-id="${escapeHtml(eco.id)}" data-eco-no="${escapeHtml(eco.eco_no || '')}" ${PERMISO_CREAR_ECO_ATTRS}>Borrar borrador</button>`
                        : ''}
                </div>
            `;

            content.innerHTML = `
                <div class="bom-field-grid">
                    ${renderEcnKsField('Origen', 'MES')}
                    ${renderEcnKsField('ECO', eco.eco_no || eco.id)}
                    ${renderEcnKsField(isFamily ? 'Familia' : 'Modelo', isFamily ? (eco.family_prefix || modelScope) : (eco.part_no || modelScope))}
                    ${renderEcnKsField('Scope / Modelos', modelScope)}
                    ${renderEcnKsField('Revision BOM', eco.bom_revision)}
                    ${renderEcnKsField('Estatus', eco.status)}
                    ${renderEcnKsField('Fecha efectiva', formatFechaEfectiva(eco.effective_at))}
                    ${renderEcnKsField('Creado por', eco.created_by)}
                    ${renderEcnKsField('Aprobado por', eco.approved_by)}
                    ${renderEcnKsField('Creado', eco.created_at)}
                    ${renderEcnKsField('Aprobado', eco.approved_at)}
                    ${renderEcnKsField('Actualizado', eco.updated_at)}
                </div>
                ${renderEcnKsField('Notas', eco.notes, { pre: true })}
                <div class="bom-summary-box">
                    <div class="bom-field-label">Resumen de cambios</div>
                    ${renderDiffChips(diff.counts || {})}
                    ${renderBigChangeWarning(diff.warning)}
                </div>
                ${totalCambios
                    ? renderDiffSection('Anadidos', diff.added, 'ADD', true, eco.part_no) +
                      renderDiffSection('Modificados', diff.modified, 'MODIFY', true, eco.part_no) +
                      renderDiffSection('Eliminados', diff.removed, 'REMOVE', true, eco.part_no) +
                      renderAdminChanges(diff.modified_admin, rows => renderDiffSection('Datos administrativos', rows, 'ADMIN', true, eco.part_no))
                    : renderEcnKsField('Cambios registrados', 'Este ECO no tiene cambios registrados en el diff.')}
                <div id="ecoFilesBox"></div>
                ${actionButtons}
            `;
            cargarPapeleriaEco(eco.id, eco.status);
        } catch (error) {
            console.error('Error detalle ECO:', error);
            title.textContent = 'Error cargando detalle';
            content.innerHTML = `<div class="bom-msg is-error">${escapeHtml(error.message)}</div>`;
        }
    }

    // ===== Archivos del ECO: HTML / PPT / PDF (look del modulo ICT) =====
    let ecoPapeleriaActual = { id: null, status: '' };
    const ECO_FILES_ACCEPT = '.html,.htm,.ppt,.pptx,.pdf';
    const ECO_FILES_ICONS = {
        clip: '<path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"></path>',
        doc: '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline>',
        eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>',
        download: '<path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line>',
        trash: '<polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m5 0V4a2 2 0 012-2h0a2 2 0 012 2v2"></path>',
        upload: '<path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line>',
        close: '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>'
    };

    function ecoFilesIcon(name, cls) {
        return `<svg class="${cls || ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">${ECO_FILES_ICONS[name]}</svg>`;
    }

    function ecoFileUrl(ecoId, fileId) {
        return `/api/ecos/${encodeURIComponent(ecoId)}/files/${encodeURIComponent(fileId)}`;
    }

    // fetch + JSON con los casos de WF_007: sesion vencida (el redirect a login
    // devuelve HTML), 403 sin permiso, 404/500 y JSON invalido.
    async function fetchJsonArchivos(url, options) {
        const response = await fetch(url, options);
        let data = null;
        try {
            data = await response.json();
        } catch (error) {
            data = null;
        }
        if (!data) {
            throw new Error(response.redirected || response.status === 401
                ? 'La sesion expiro; vuelve a iniciar sesion.'
                : `Respuesta invalida del servidor (HTTP ${response.status}).`);
        }
        if (!response.ok || !data.success) {
            if (response.status === 403) throw new Error(data.error || 'No tienes permiso para esta accion.');
            throw new Error(data.error || `Error del servidor (HTTP ${response.status}).`);
        }
        return data;
    }

    async function cargarPapeleriaEco(ecoId, status) {
        ecoPapeleriaActual = { id: ecoId, status: status };
        const box = document.getElementById('ecoFilesBox');
        if (!box) return;
        box.innerHTML = '<div class="eco-files-card"><div class="eco-files-empty">Cargando archivos...</div></div>';
        try {
            const data = await fetchJsonArchivos(`/api/ecos/${encodeURIComponent(ecoId)}/files`);
            const files = data.data || [];
            // Un ECO aprobado es inmutable: se puede seguir adjuntando, pero no borrar.
            const puedeBorrar = puedeCrearEco && String(status || '').toUpperCase() !== 'APPROVED';
            const rows = files.map(f => `
                <tr>
                    <td class="eco-files-name">${escapeHtml(f.nombre_original)}</td>
                    <td><span class="eco-files-ext">${escapeHtml(String(f.extension || '').replace('.', ''))}</span></td>
                    <td>${escapeHtml(f.created_by || '-')}</td>
                    <td>${escapeHtml(f.created_at || '-')}</td>
                    <td>
                        <div class="eco-files-actions">
                            <button type="button" class="eco-files-btn eco-files-btn-primary" data-eco-file-view="${escapeHtml(f.id)}" data-eco-file-ext="${escapeHtml(f.extension)}" data-eco-file-name="${escapeHtml(f.nombre_original)}">${ecoFilesIcon('eye')}Ver</button>
                            <a class="eco-files-btn eco-files-btn-export" href="${escapeHtml(ecoFileUrl(ecoId, f.id))}?download=1">${ecoFilesIcon('download')}Descargar</a>
                            ${puedeBorrar ? `<button type="button" class="eco-files-btn eco-files-btn-danger" data-eco-file-delete="${escapeHtml(f.id)}" data-eco-file-name="${escapeHtml(f.nombre_original)}" ${PERMISO_CREAR_ECO_ATTRS}>${ecoFilesIcon('trash')}Borrar</button>` : ''}
                        </div>
                    </td>
                </tr>`).join('');
            const upload = puedeCrearEco
                ? `<label class="eco-files-btn eco-files-btn-primary" id="ecoFileUploadLabel" ${PERMISO_CREAR_ECO_ATTRS}>
                       ${ecoFilesIcon('upload')}Adjuntar archivo
                       <input type="file" id="ecoFileInput" accept="${ECO_FILES_ACCEPT}" multiple hidden>
                   </label>`
                : '';
            box.innerHTML = `
                <div class="eco-files-card">
                    <div class="eco-files-card-header">
                        ${ecoFilesIcon('clip', 'eco-files-card-icon')}
                        <h3>Archivos</h3>
                        <span class="eco-files-count" id="ecoFilesCount">${files.length} archivo(s)</span>
                        ${upload}
                    </div>
                    ${files.length
                        ? `<div class="eco-files-table-wrap"><table class="eco-files-table">
                               <thead><tr><th>Archivo</th><th>Tipo</th><th>Subido por</th><th>Fecha</th><th></th></tr></thead>
                               <tbody>${rows}</tbody>
                           </table></div>`
                        : '<div class="eco-files-empty">Sin archivos. Formatos: HTML, PPT/PPTX o PDF.</div>'}
                </div>`;
        } catch (error) {
            box.innerHTML = `<div class="eco-files-card"><div class="eco-files-empty is-error">${escapeHtml(error.message)}</div></div>`;
        }
    }

    async function subirPapeleriaEco(files) {
        const { id, status } = ecoPapeleriaActual;
        const lista = Array.from(files || []);
        if (!id || !lista.length) return;
        const label = document.getElementById('ecoFileUploadLabel');
        const count = document.getElementById('ecoFilesCount');
        if (label) label.setAttribute('aria-disabled', 'true');
        try {
            for (let i = 0; i < lista.length; i++) {
                if (count) count.textContent = `Subiendo ${i + 1} de ${lista.length}...`;
                const form = new FormData();
                form.append('file', lista[i]);
                try {
                    await fetchJsonArchivos(`/api/ecos/${encodeURIComponent(id)}/files`, { method: 'POST', body: form });
                } catch (error) {
                    ecoAlert(`No se pudo subir ${escapeHtml(lista[i].name)}:<br>${escapeHtml(error.message)}`);
                    break;
                }
            }
        } finally {
            cargarPapeleriaEco(id, status);
        }
    }

    async function borrarPapeleriaEco(fileId, nombre) {
        const { id, status } = ecoPapeleriaActual;
        if (!id || !confirm(`Borrar el archivo ${nombre}?`)) return;
        try {
            await fetchJsonArchivos(ecoFileUrl(id, fileId), { method: 'DELETE' });
        } catch (error) {
            ecoAlert(`No se pudo borrar:<br>${escapeHtml(error.message)}`);
        }
        cargarPapeleriaEco(id, status);
    }

    function cargarScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
            document.head.appendChild(script);
        });
    }

    async function ensurePptxPreview() {
        if (window.pptxPreview) return;
        try {
            await cargarScript('/static/js/lib/pptx-preview.umd.js');
        } catch (error) {
            await cargarScript('https://cdn.jsdelivr.net/npm/pptx-preview@1.0.7/dist/pptx-preview.umd.js');
        }
    }

    // WF_008: el visor se crea por JS en document.body (no vive en el
    // fragmento AJAX) y es idempotente; Escape lo maneja onControlBomModalKeydown.
    function ensureEcoFilesViewer() {
        let modal = document.getElementById('ecoFilesViewer');
        if (modal) return modal;
        modal = document.createElement('div');
        modal.id = 'ecoFilesViewer';
        modal.className = 'eco-files-modal';
        modal.innerHTML = `
            <div class="eco-files-dialog" role="dialog" aria-modal="true" aria-labelledby="ecoFilesViewerTitle">
                <div class="eco-files-header">
                    <div class="eco-files-title-group">
                        ${ecoFilesIcon('doc', 'eco-files-modal-icon')}
                        <div>
                            <h3 id="ecoFilesViewerTitle">Archivos</h3>
                            <span class="eco-files-subtitle" id="ecoFilesViewerSubtitle"></span>
                        </div>
                    </div>
                    <button type="button" class="eco-files-close" data-eco-files-close aria-label="Cerrar">${ecoFilesIcon('close')}</button>
                </div>
                <div class="eco-files-toolbar" id="ecoFilesViewerTabs" hidden></div>
                <div class="eco-files-body" id="ecoFilesViewerBody"></div>
            </div>`;
        modal.addEventListener('click', event => {
            if (event.target === modal || event.target.closest('[data-eco-files-close]')) {
                cerrarVisorPapeleria();
            }
        });
        document.body.appendChild(modal);
        return modal;
    }

    function abrirVisorPapeleria(titulo, subtitulo) {
        const modal = ensureEcoFilesViewer();
        modal.style.display = 'flex';
        modal.style.opacity = '1';
        modal.style.visibility = 'visible';
        document.getElementById('ecoFilesViewerTitle').textContent = titulo || 'Archivos';
        document.getElementById('ecoFilesViewerSubtitle').textContent = subtitulo || '';
        return document.getElementById('ecoFilesViewerBody');
    }

    function cerrarVisorPapeleria() {
        const modal = document.getElementById('ecoFilesViewer');
        if (!modal) return;
        modal.style.display = 'none';
        modal.style.opacity = '0';
        modal.style.visibility = 'hidden';
        // Vacia el cuerpo para soltar el iframe o el render del PPTX.
        document.getElementById('ecoFilesViewerBody').innerHTML = '';
    }

    // Desde el detalle del ECO: un solo archivo, sin pestanas.
    function verPapeleriaEco(fileId, extension, nombre) {
        const ecoId = ecoPapeleriaActual.id;
        abrirVisorPapeleria(nombre, `ECO ${ecoId}`);
        renderTabsPapeleria(ecoId, [], fileId);
        mostrarArchivoEco(ecoId, fileId, extension, nombre);
    }

    // Boton "Archivos" de la barra: los del ultimo ECO del numero de parte
    // que tenga archivos (cuando se actualiza el dibujo, el nuevo ECO manda).
    let archivosModelo = { ecoId: null, files: [] };

    async function verArchivosModelo() {
        const partNo = (document.getElementById('bomModeloSearch')?.value || '').trim().toUpperCase();
        if (!partNo) {
            ecoAlert('Selecciona un modelo para ver sus archivos.');
            return;
        }
        try {
            const data = await fetchJsonArchivos(`/api/bom/papeleria?part_no=${encodeURIComponent(partNo)}`);
            if (!data.eco || !(data.files || []).length) {
                ecoAlert(`El modelo ${escapeHtml(data.part_no)} no tiene archivos en ningun ECO.`);
                return;
            }
            const eco = data.eco;
            abrirVisorPapeleria(
                `Archivos - ${data.part_no}`,
                `ECO ${eco.eco_no} · ${eco.status} · ${formatFechaEfectiva(eco.effective_at)}`
            );
            archivosModelo = { ecoId: eco.id, files: data.files };
            abrirArchivoModelo(data.files[0].id);
        } catch (error) {
            ecoAlert(`Error cargando archivos:<br>${escapeHtml(error.message)}`);
        }
    }

    function abrirArchivoModelo(fileId) {
        const file = archivosModelo.files.find(f => String(f.id) === String(fileId));
        if (!file) return;
        renderTabsPapeleria(archivosModelo.ecoId, archivosModelo.files, file.id);
        mostrarArchivoEco(archivosModelo.ecoId, file.id, file.extension, file.nombre_original);
    }

    function renderTabsPapeleria(ecoId, files, activeId) {
        const tabs = document.getElementById('ecoFilesViewerTabs');
        if (!tabs) return;
        tabs.hidden = !activeId;
        tabs.innerHTML = files.map(f => `
            <button type="button" class="eco-files-tab${String(f.id) === String(activeId) ? ' active' : ''}" data-eco-file-tab="${escapeHtml(f.id)}">${escapeHtml(f.nombre_original)}</button>
        `).join('') + (activeId
            ? `<a class="eco-files-btn eco-files-btn-export" href="${escapeHtml(ecoFileUrl(ecoId, activeId))}?download=1">${ecoFilesIcon('download')}Descargar</a>`
            : '');
    }

    // Dibuja un archivo en el cuerpo del visor ya abierto.
    async function mostrarArchivoEco(ecoId, fileId, extension, nombre) {
        const body = document.getElementById('ecoFilesViewerBody');
        if (!body) return;
        const url = ecoFileUrl(ecoId, fileId);
        if (extension === '.ppt') {
            body.innerHTML = `<div class="eco-files-empty">
                    El formato PPT antiguo no se puede mostrar en el navegador.<br>
                    Guardalo como PPTX en PowerPoint para verlo aqui, o
                    <a href="${escapeHtml(url)}?download=1">descargalo</a>.
                </div>`;
            return;
        }
        if (extension === '.pptx') {
            body.innerHTML = '<div class="eco-files-loading"><div class="eco-files-spinner"></div><span>Cargando presentacion...</span></div>';
            try {
                await ensurePptxPreview();
                const response = await fetch(url);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const buffer = await response.arrayBuffer();
                body.innerHTML = '';
                const width = Math.max(320, Math.min(body.clientWidth - 40, 1200));
                const height = Math.max(300, body.clientHeight - 40);
                await window.pptxPreview.init(body, { width: width, height: height, mode: 'list' }).preview(buffer);
                // La barra vertical de la libreria le resta ancho a la lamina
                // (sale scroll horizontal): se ensancha el contenedor lo mismo.
                const wrapper = body.querySelector('.pptx-preview-wrapper');
                if (wrapper) wrapper.style.width = `${width + wrapper.offsetWidth - wrapper.clientWidth}px`;
            } catch (error) {
                body.innerHTML = `<div class="eco-files-empty is-error">No se pudo mostrar la presentacion: ${escapeHtml(error.message)}</div>`;
            }
            return;
        }
        // El HTML va en un iframe sandbox sin permisos (sin scripts ni acceso al
        // MES); el PDF usa el visor nativo, que no funciona dentro de sandbox.
        const sandbox = extension === '.pdf' ? '' : ' sandbox=""';
        body.innerHTML = `<iframe src="${escapeHtml(url)}"${sandbox} title="${escapeHtml(nombre)}"></iframe>`;
    }

    async function aprobarEcoPorId(ecoId, ecoNo, btn, onSuccess) {
        if (!requierePermisoAprobarEco()) return false;
        if (!ecoId) {
            ecoAlert('No hay ECO seleccionado para aprobar.');
            return false;
        }
        const label = ecoNo ? ` ${ecoNo}` : '';
        if (!confirm(`Aprobar el ECO${label}? Una vez aprobado quedara inmutable y los cambios se aplicaran al BOM vigente.`)) {
            return false;
        }
        if (btn) btn.disabled = true;
        try {
            const response = await fetch(`/api/ecos/${encodeURIComponent(ecoId)}/approve`, { method: 'POST' });
            const data = await response.json();
            if (!response.ok || !data.success) {
                const errors = (data.errors || []).join('<br>');
                throw new Error(errors || data.error || 'No se pudo aprobar el ECO');
            }
            ecoAlert('ECO aprobado correctamente. Los cambios fueron aplicados al BOM.');
            if (typeof onSuccess === 'function') {
                await onSuccess();
            }
            return true;
        } catch (error) {
            console.error('Error aprobando ECO:', error);
            ecoAlert(`Error aprobando ECO:<br>${error.message}`);
            if (btn) btn.disabled = false;
            return false;
        }
    }

    async function aprobarEcoDesdeLista(ecoId, ecoNo, btn) {
        await aprobarEcoPorId(ecoId, ecoNo, btn, async function() {
            cerrarModalEcoDetalle();
            await cargarEcoList(ecoListPage);
            setEcoListStatus(`ECO${ecoNo ? ' ' + escapeHtml(ecoNo) : ''} aprobado.`);
            if (typeof consultarBOMOriginal === 'function') {
                try { consultarBOMOriginal(); } catch (_) {}
            }
        });
    }

    async function aprobarEcoActual() {
        if (!ecoActualId) {
            ecoAlert('No hay ECO activo para aprobar.');
            return;
        }
        const btn = document.getElementById('btnAprobarEco');
        await aprobarEcoPorId(ecoActualId, '', btn, async function() {
            ecoActualId = null;
            cerrarModalECO();
            if (typeof consultarBOMOriginal === 'function') {
                try { consultarBOMOriginal(); } catch (_) {}
            }
        });
    }

    function cargarDatosBOMEnTabla(datos) {
        // Si se pasa un string (modelo), cargar desde servidor
        if (typeof datos === 'string') {
            const modelo = datos;
            
            // Validar que no se intente cargar todos los modelos
            if (modelo === 'todos' || !modelo || modelo.trim() === '') {
                showCustomAlert(' Debe seleccionar un modelo específico.<br><br>Utilice el buscador para seleccionar un modelo (ej: EBR30299301, EBR30299302, etc.)');
                const tbody = document.querySelector('#bomTableBody');
                tbody.innerHTML = '<tr><td colspan="12" class="no-data">Seleccione un modelo específico para visualizar los datos de BOM.</td></tr>';
                return;
            }
            
            // Obtener filtro de classification
            const classificationFilter = document.getElementById('bomClassificationFilter').value;
            const bomRevision = obtenerRevisionBOMSeleccionada(modelo);

            // Construir body de la petición
            const requestBody = { modelo: modelo };
            if (classificationFilter && classificationFilter !== 'TODOS') {
                requestBody.classification = classificationFilter;
            }
            if (bomRevision) {
                requestBody.bom_revision = bomRevision;
            }
            
            console.log('📡 Consultando BOM con filtros:', requestBody);
            
            fetch('/listar_bom', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            })
            .then(response => response.json())
            .then(data => {
                
                // El servidor devuelve directamente un array
                if (Array.isArray(data)) {
                    // Guardar en cache
                    bomDataCache = data;
                    mostrarDatosEnTabla(data);
                    console.log(` Cargados ${data.length} registros de BOM`);
                } else if (data.error) {
                    console.error(' Error del servidor:', data.error);
                    showCustomAlert('Error al cargar datos de BOM: ' + data.error);
                } else {
                    console.error(' Formato de respuesta no reconocido:', data);
                    showCustomAlert('Error al procesar datos de BOM: formato no válido');
                }
            })
            .catch(error => {
                console.error(' Error en la petición:', error);
                showCustomAlert('Error al conectar con el servidor: ' + error.message);
            });
            return;
        }
        
        // Si se pasan datos directamente, mostrarlos
        bomDataCache = datos;
        mostrarDatosEnTabla(datos);
    }

    function aplicarFiltroClassification() {
        const filtro = document.getElementById('bomClassificationFilter').value;
        const modeloSeleccionado = document.getElementById('bomModeloSearch').value;
        
        console.log(' Aplicando filtro:', filtro);
        
        // Verificar si hay un modelo seleccionado
        if (!modeloSeleccionado || modeloSeleccionado.trim() === '' || modeloSeleccionado === 'todos') {
            console.warn('⚠️ No hay modelo seleccionado, no se puede filtrar');
            showCustomAlert('Por favor seleccione un modelo antes de aplicar filtros');
            return;
        }
        
        // Reconsultar desde el servidor con el filtro
        cargarDatosBOMEnTabla(modeloSeleccionado);
    }

    function mostrarDatosEnTabla(datos) {
        const tbody = document.querySelector('#bomTableBody');
        tbody.innerHTML = '';
        actualizarEstadoRevisionBOM(datos);

        if (!datos || datos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="12" class="no-data">No hay datos de BOM registrados. Use el botón "Registrar" para añadir nuevos elementos.</td></tr>';
            aplicarFiltrosColumnaBOM();
            return;
        }
        
        datos.forEach((item, index) => {
            const row = document.createElement('tr');
            
            // Agregar el modelo como data attribute para el filtro
            row.dataset.modelo = item.modelo || '';
            // Agregar ID de BOM para identificación en edición
            row.dataset.bomId = item.id || index;
            row.dataset.bomData = JSON.stringify(item);
            
            // Función para limpiar decimales innecesarios en números
            function limpiarNumero(valor) {
                if (!valor) return '';
                const numero = parseFloat(valor);
                if (!isNaN(numero) && numero % 1 === 0) {
                    return numero.toString();
                }
                return valor.toString();
            }
            
            // Checkbox selector (sin handler inline: la seleccion aun no tiene acciones).
            const selectorCheckbox = '<input type="checkbox" aria-label="Seleccionar fila">';
            
            // Función para crear celda con tooltip si es necesario
            function crearCelda(valor) {
                const textoLimpio = escapeHtml((valor || '').toString().trim());
                if (textoLimpio.length > 20) {
                    return `<td data-full-text="${textoLimpio}" title="${textoLimpio}">${textoLimpio}</td>`;
                }
                return `<td>${textoLimpio}</td>`;
            }

            // Función para crear celda con checkbox para CHECKED/UNCHECKED
            function crearCeldaCheckbox(valor, rowIndex, columnName) {
                const textoLimpio = (valor || '').toString().trim().toUpperCase();
                if (textoLimpio === 'CHECKED' || textoLimpio === 'UNCHECKED') {
                    const isChecked = textoLimpio === 'CHECKED';
                    const checkboxId = `checkbox_${rowIndex}_${columnName}`;
                    return `<td>
                        <input type="checkbox" id="${checkboxId}" ${isChecked ? 'checked' : ''} disabled readonly>
                    </td>`;
                } else {
                    // Si no es CHECKED/UNCHECKED, usar la función normal
                    return crearCelda(valor);
                }
            }
            
            row.innerHTML = `
                <td>${selectorCheckbox}</td>
                ${crearCelda(item.numeroParte)}
                ${crearCelda(item.tipoMaterial)}
                ${crearCelda(item.classification)}
                ${crearCelda(item.especificacionMaterial)}
                ${crearCelda(item.vender)}
                ${crearCelda(limpiarNumero(item.cantidadTotal || '0'))}
                ${crearCelda(item.ubicacion)}
                ${crearCelda(item.materialSustituto)}
                ${crearCeldaCheckbox(item.materialOriginal, index, 'materialOriginal')}
                ${crearCelda(item.registrador)}
                ${crearCelda(item.fechaRegistro)}
            `;
            tbody.appendChild(row);
        });
        aplicarFiltrosColumnaBOM();
    }

    function consultarBOM() {
        consultarBOMOriginal();
    }

    function mostrarFormularioBOM() {
        alert('Funcionalidad de registro de BOM en desarrollo');
    }

    function eliminarBOM() {
        alert('Funcionalidad de eliminación de BOM en desarrollo');
    }

    function mostrarSustitutoBOM() {
        alert('Funcionalidad de registro de material sustituto en desarrollo');
    }

    function exportarExcelBOM() {
        try {
            // Obtener el modelo seleccionado
            const modeloSeleccionado = document.getElementById('bomModeloSearch').value;
            
            // Validar que haya un modelo seleccionado
            if (!modeloSeleccionado || modeloSeleccionado.trim() === '' || modeloSeleccionado === 'todos') {
                showCustomAlert(' Debe seleccionar un modelo específico antes de exportar.<br><br>Utilice el buscador para seleccionar un modelo (ej: EBR30299301, EBR30299302, etc.)');
                return;
            }
            
            // Obtener filtro de classification
            const classificationFilter = document.getElementById('bomClassificationFilter').value;
            const bomRevision = obtenerRevisionBOMSeleccionada(modeloSeleccionado);

            let mensaje = `Generando archivo Excel de BOM para modelo: ${modeloSeleccionado}`;
            if (bomRevision) {
                mensaje += ` - Revision: ${bomRevision}`;
            }
            if (classificationFilter && classificationFilter !== 'TODOS') {
                mensaje += ` - Filtro: ${classificationFilter}`;
            }
            alert(mensaje + ', por favor espere...');
            
            // Construir URL con parámetros
            let url = `/exportar_excel_bom?modelo=${encodeURIComponent(modeloSeleccionado)}`;
            if (bomRevision) {
                url += `&bom_revision=${encodeURIComponent(bomRevision)}`;
            }
            if (classificationFilter && classificationFilter !== 'TODOS') {
                url += `&classification=${encodeURIComponent(classificationFilter)}`;
            }
            
            // Enviar solicitud
            fetch(url, {
                method: 'GET',
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en el servidor');
                }
                return response.blob();
            })
            .then(blob => {
                const urlBlob = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = urlBlob;

                let filename = `bom_export_${modeloSeleccionado}`;
                if (bomRevision) {
                    filename += `_${bomRevision}`;
                }
                if (classificationFilter && classificationFilter !== 'TODOS') {
                    filename += `_${classificationFilter}`;
                }
                filename += `_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.xlsx`;
                
                link.download = filename;
                
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                window.URL.revokeObjectURL(urlBlob);
                alert(`Archivo Excel de BOM descargado exitosamente`);
            })
            .catch(error => {
                console.error('Error al exportar Excel de BOM:', error);
                alert('Error al exportar el archivo Excel de BOM: ' + error.message);
            });
            
        } catch (error) {
            console.error('Error al exportar Excel de BOM:', error);
            alert('Error al exportar el archivo Excel de BOM');
        }
    }

    function importarExcelBOM() {
        const fileInput = document.getElementById('importarExcelBOM');
        const file = fileInput.files[0];
        
        if (!file) {
            showCustomAlert("Por favor selecciona un archivo Excel de BOM.");
            return;
        }
        
        if (!file.name.toLowerCase().endsWith('.xlsx') && !file.name.toLowerCase().endsWith('.xls')) {
            showCustomAlert("Por favor selecciona un archivo Excel válido (.xlsx o .xls)");
            return;
        }
        
        // Mostrar modal de carga
        showLoadingModal();
        
        const formData = new FormData();
        formData.append('file', file);
        
        // Variables para tracking de progreso
        let startTime = Date.now();
        let progressInterval;
        
        // Simular progreso inicial
        updateLoadingProgress(0, "Iniciando carga del archivo...", "Calculando tiempo estimado...");
        
        // Estimación basada en datos reales: ~67 filas por segundo (9525 filas en 141.7s)
        // Aproximadamente 15ms por fila
        let currentProgress = 0;
        let estimatedRowsPerSecond = 67; // Basado en datos reales
        
        progressInterval = setInterval(() => {
            if (currentProgress < 95) {
                // Progreso más gradual y realista
                if (currentProgress < 20) {
                    currentProgress += Math.random() * 3; // Lento al inicio (lectura del archivo)
                } else if (currentProgress < 40) {
                    currentProgress += Math.random() * 5; // Procesamiento inicial
                } else if (currentProgress < 80) {
                    currentProgress += Math.random() * 2; // Inserción en BD (más lento)
                } else {
                    currentProgress += Math.random() * 1; // Finalización
                }
                
                if (currentProgress > 95) currentProgress = 95;
                
                const elapsed = (Date.now() - startTime) / 1000;
                let estimated = null;
                let timeText = "Calculando tiempo...";
                
                // Estimación más precisa basada en el progreso real
                if (currentProgress > 15) {
                    estimated = (elapsed / currentProgress * 100) - elapsed;
                    
                    // Ajustar estimación basada en datos históricos
                    if (currentProgress < 30) {
                        // En las primeras etapas, usar estimación histórica
                        estimated = estimated * 1.8; // Factor de corrección
                    } else if (currentProgress < 60) {
                        estimated = estimated * 1.4;
                    } else {
                        estimated = estimated * 1.1;
                    }
                    
                    if (estimated > 60) {
                        timeText = `Tiempo estimado: ${Math.ceil(estimated / 60)}m ${Math.ceil(estimated % 60)}s`;
                    } else {
                        timeText = `Tiempo estimado: ${Math.ceil(estimated)}s`;
                    }
                }
                
                let message = "Procesando archivo Excel...";
                if (currentProgress < 20) {
                    message = "Leyendo y analizando archivo Excel...";
                } else if (currentProgress < 40) {
                    message = "Validando y preparando datos...";
                } else if (currentProgress < 80) {
                    message = "Insertando registros en base de datos...";
                } else {
                    message = "Finalizando proceso de importación...";
                }
                
                updateLoadingProgress(currentProgress, message, timeText);
            }
        }, 1000); // Actualizar cada segundo para ser más realista
        
        fetch('/importar_excel_bom', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            clearInterval(progressInterval);
            
            if (data.success) {
                // Completar progreso
                updateLoadingProgress(100, "¡Carga completada exitosamente!", "Finalizado");
                
                setTimeout(() => {
                    hideLoadingModal();
                    
                    const now = new Date();
                    const fecha = now.toLocaleDateString();
                    const hora = now.toLocaleTimeString();
                    const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
                    
                    let summary = `Importación de BOM completada<br>`;
                    summary += `<span style='font-size:0.9em;color:#b0eaff;'>${fecha} ${hora}</span><br><br>`;
                    
                    if (data.insertados !== undefined) {
                        summary += `<span style='font-size:0.9em;color:#27ae60;'> Registros procesados: ${data.insertados}</span><br>`;
                    }
                    if (data.omitidos !== undefined && data.omitidos > 0) {
                        summary += `<span style='font-size:0.9em;color:#f39c12;'>⚠️ Filas omitidas: ${data.omitidos}</span><br>`;
                    }
                    if (data.total_procesado !== undefined) {
                        summary += `<span style='font-size:0.85em;color:#3498db;'> Total en archivo: ${data.total_procesado}</span><br>`;
                    }
                    if (data.filas_bd_afectadas !== undefined) {
                        summary += `<span style='font-size:0.85em;color:#9b59b6;'> Filas en BD: ${data.filas_bd_afectadas}</span><br>`;
                    }
                    summary += `<span style='font-size:0.8em;color:#95a5a6;'>⏱️ Tiempo total: ${totalTime}s</span><br>`;
                    
                    // Calcular velocidad de procesamiento
                    if (data.insertados > 0) {
                        const filasPerSegundo = Math.round(data.insertados / parseFloat(totalTime));
                        summary += `<span style='font-size:0.8em;color:#95a5a6;'>⚡ Velocidad: ${filasPerSegundo} filas/seg</span>`;
                    }
                    
                    showCustomAlert(summary);
                    fileInput.value = '';
                }, 1000);
                
            } else {
                hideLoadingModal();
                showCustomAlert("Error al importar BOM: " + data.error);
            }
        })
        .catch(error => {
            clearInterval(progressInterval);
            hideLoadingModal();
            console.error('Error:', error);
            showCustomAlert("Error al importar el archivo de BOM");
        });
    }

    function seleccionarFilaBOM(index, seleccionado) {
        // Aquí puedes agregar lógica adicional para manejar la selección
    }

    function actualizarEstadoCheckbox(rowIndex, columnName, isChecked) {
        // Los checkboxes están deshabilitados, esta función no debería ejecutarse
        console.warn(` Intento de modificar checkbox deshabilitado: Fila ${rowIndex}, Columna ${columnName}`);
        return false;
    }

    function cargarModelosBOM() {
        const select = document.getElementById('bomModeloSelect');
        
        // Verificar si ya hay modelos cargados desde el servidor
        if (select.options.length > 1) {
            return;
        }
        
        fetch('/listar_modelos_bom', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(modelos => {
            select.innerHTML = '<option value="todos">Todos los modelos</option>';
            
            modelos.forEach(modelo => {
                const option = document.createElement('option');
                option.value = modelo.modelo;
                option.textContent = modelo.modelo;
                select.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error al cargar modelos:', error);
            showCustomAlert('Error al cargar la lista de modelos');
        });
    }

    // Función para filtrar modelos en el dropdown searchable
    function filtrarModelos() {
        const searchInput = document.getElementById('bomModeloSearch');
        const dropdownList = document.getElementById('bomDropdownList');
        const searchTerm = searchInput.value.toLowerCase();
        
        // Mostrar el dropdown
        dropdownList.style.display = 'block';
        
        const items = dropdownList.querySelectorAll('.bom-dropdown-item');
        let hasVisibleItems = false;
        
        items.forEach(item => {
            const modeloText = item.textContent.toLowerCase();
            if (modeloText.includes(searchTerm)) {
                item.classList.remove('hidden');
                hasVisibleItems = true;
            } else {
                item.classList.add('hidden');
            }
        });
        
        // Si no hay coincidencias, ocultar el dropdown
        if (!hasVisibleItems && searchTerm.length > 0) {
            dropdownList.style.display = 'none';
        }
    }

    // Función para mostrar dropdown
    function mostrarDropdown() {
        const dropdownList = document.getElementById('bomDropdownList');
        const searchInput = document.getElementById('bomModeloSearch');
        
        if (searchInput.value.trim() === '') {
            // Si el input está vacío, mostrar todos los modelos
            const items = dropdownList.querySelectorAll('.bom-dropdown-item');
            items.forEach(item => {
                item.classList.remove('hidden');
            });
        }
        
        dropdownList.style.display = 'block';
    }

    function actualizarTextoRevisionBOM(texto) {
        const status = document.getElementById('bomRevisionStatus');
        if (status) {
            status.textContent = texto || 'KS vigente';
            status.title = status.textContent;
        }
    }

    function reiniciarSelectorRevisionesBOM(modelo = '') {
        const select = document.getElementById('bomRevisionFilter');
        if (!select) return;

        select.dataset.modelo = String(modelo || '').trim().toUpperCase();
        select.innerHTML = '<option value="">Vigente</option>';
        select.value = '';
        actualizarTextoRevisionBOM(modelo ? 'Consultando revision vigente' : 'KS vigente');
    }

    function limpiarRevisionSiCambioModelo(modelo) {
        const select = document.getElementById('bomRevisionFilter');
        if (!select) return;

        const modeloActual = String(modelo || '').trim().toUpperCase();
        if (select.dataset.modelo && select.dataset.modelo !== modeloActual) {
            reiniciarSelectorRevisionesBOM();
        }
    }

    function obtenerRevisionBOMSeleccionada(modelo) {
        const select = document.getElementById('bomRevisionFilter');
        const modeloActual = String(modelo || '').trim().toUpperCase();
        if (!select || select.dataset.modelo !== modeloActual) {
            return '';
        }
        return String(select.value || '').trim();
    }

    async function cargarRevisionesBOM(modelo, preservarSeleccion = true) {
        const select = document.getElementById('bomRevisionFilter');
        const modeloNormalizado = String(modelo || '').trim().toUpperCase();
        if (!select || !modeloNormalizado || modeloNormalizado === 'TODOS') {
            reiniciarSelectorRevisionesBOM();
            return;
        }

        const revisionPrevia = preservarSeleccion && select.dataset.modelo === modeloNormalizado
            ? String(select.value || '').trim()
            : '';
        reiniciarSelectorRevisionesBOM(modeloNormalizado);
        actualizarTextoRevisionBOM('Cargando revisiones KS...');

        try {
            const response = await fetch(`/api/bom/revisions?modelo=${encodeURIComponent(modeloNormalizado)}`);
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'No se pudieron cargar revisiones KS');
            }

            const modeloEnPantalla = String(document.getElementById('bomModeloSearch')?.value || '').trim().toUpperCase();
            if (modeloEnPantalla !== modeloNormalizado) {
                return;
            }

            const revisiones = Array.isArray(data.data) ? data.data : [];
            revisiones.forEach(revision => {
                const option = document.createElement('option');
                option.value = revision.bom_rev || '';
                let texto = revision.bom_rev || 'Sin revision';
                if (revision.is_current) {
                    texto += ' - vigente';
                }
                if (revision.eco_no) {
                    texto += ` - ECO ${revision.eco_no}`;
                }
                option.textContent = texto;
                select.appendChild(option);
            });

            if (revisionPrevia && revisiones.some(revision => String(revision.bom_rev || '').toUpperCase() === revisionPrevia.toUpperCase())) {
                select.value = revisionPrevia;
            }

            const cacheDelModelo = Array.isArray(bomDataCache)
                && bomDataCache.some(item => String(item.modelo || '').trim().toUpperCase() === modeloNormalizado);
            if (cacheDelModelo) {
                actualizarEstadoRevisionBOM(bomDataCache);
            } else {
                actualizarTextoRevisionBOM(
                    revisiones.length
                        ? `${revisiones.length} revision(es) KS disponibles`
                        : 'Sin revisiones KS'
                );
            }
        } catch (error) {
            console.error('Error al cargar revisiones BOM KS:', error);
            actualizarTextoRevisionBOM('No se pudieron cargar revisiones');
        }
    }

    function aplicarFiltroRevisionBOM() {
        const modeloSeleccionado = document.getElementById('bomModeloSearch')?.value || '';
        if (!modeloSeleccionado.trim() || modeloSeleccionado === 'todos') {
            return;
        }
        cargarDatosBOMEnTabla(modeloSeleccionado);
    }

    function actualizarEstadoRevisionBOM(datos) {
        const modeloSeleccionado = document.getElementById('bomModeloSearch')?.value || '';
        const revisionSeleccionada = obtenerRevisionBOMSeleccionada(modeloSeleccionado);
        const revisionCargada = Array.isArray(datos) && datos.length
            ? String(datos[0].bomRevision || '').trim()
            : '';

        if (revisionCargada) {
            actualizarTextoRevisionBOM(
                revisionSeleccionada
                    ? `Viendo BOM rev ${revisionCargada}`
                    : `Vigente: BOM rev ${revisionCargada}`
            );
            return;
        }
        if (revisionSeleccionada) {
            actualizarTextoRevisionBOM(`Sin datos para BOM rev ${revisionSeleccionada}`);
            return;
        }
        actualizarTextoRevisionBOM('Sin datos de revision vigente');
    }

    // Función para seleccionar un modelo del dropdown
    function seleccionarModelo(modelo) {
        const searchInput = document.getElementById('bomModeloSearch');
        const dropdownList = document.getElementById('bomDropdownList');
        
        // Validar que no se seleccione "todos"
        if (modelo === 'todos') {
            showCustomAlert(' Debe seleccionar un modelo específico.<br><br>Por favor elija un modelo de la lista para evitar saturar la pantalla.');
            dropdownList.style.display = 'none';
            return;
        }

        searchInput.value = modelo;
        dropdownList.style.display = 'none';
        cargarRevisionesBOM(modelo, false);


        // Limpiar tabla previa
        bomDataCache = [];
        const tbody = document.querySelector('#bomTableBody');
        tbody.innerHTML = '';
    }

    // Event listener para cerrar dropdown cuando se hace clic fuera
    document.addEventListener('click', function(event) {
        const searchContainer = document.querySelector('.bom-search-container');
        const dropdownList = document.getElementById('bomDropdownList');
        
        if (searchContainer && !searchContainer.contains(event.target)) {
            dropdownList.style.display = 'none';
        }
    });

    function cargarModelosFiltro() {
        const selectFiltro = document.getElementById('bomFiltroModeloSelect');
        
        // Verificar si ya hay modelos cargados desde el servidor
        if (selectFiltro.options.length > 1) {
            return;
        }
        
        fetch('/listar_modelos_bom', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            return response.json();
        })
        .then(modelos => {
            if (!selectFiltro) {
                console.error(" No se encontró el elemento bomFiltroModeloSelect");
                return;
            }
            
            selectFiltro.innerHTML = '<option value="todos">Filtrar por modelo (todos)</option>';
            
            modelos.forEach((modelo, index) => {
                const option = document.createElement('option');
                option.value = modelo.modelo;
                option.textContent = modelo.modelo;
                selectFiltro.appendChild(option);
            });
            
        })
        .catch(error => {
            console.error(' Error al cargar modelos para filtro:', error);
        });
    }

    function filtrarPorModelo() {
        const selectFiltro = document.getElementById('bomFiltroModeloSelect');
        const modeloSeleccionado = selectFiltro.value;
        const tbody = document.querySelector('#bomTableBody');
        const rows = tbody.getElementsByTagName('tr');
        
        let visibleCount = 0;
        
        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            
            // Saltar si es la fila de "no data"
            if (row.cells.length === 1 && row.cells[0].classList.contains('no-data')) {
                continue;
            }
            
            if (modeloSeleccionado === 'todos') {
                // Si selecciona "todos", mostrar todas las filas
                row.style.display = '';
                row.classList.remove('filtered-row', 'highlight-match');
                visibleCount++;
            } else {
                // Obtener el modelo de la fila usando el data attribute
                const modeloEnFila = row.dataset.modelo || '';
                
                if (modeloEnFila === modeloSeleccionado) {
                    row.style.display = '';
                    row.classList.remove('filtered-row');
                    row.classList.add('highlight-match');
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                    row.classList.add('filtered-row');
                    row.classList.remove('highlight-match');
                }
            }
        }
        
        // Actualizar contador de resultados
        actualizarContadorResultados(visibleCount, modeloSeleccionado === 'todos' ? '' : modeloSeleccionado);
    }

    function limpiarFiltroModelo() {
        const selectFiltro = document.getElementById('bomFiltroModeloSelect');
        selectFiltro.value = 'todos';
        filtrarPorModelo();
    }

    function actualizarContadorResultados(count, filterText) {
        // Buscar si ya existe un contador, si no, crearlo
        let contador = document.getElementById('bomResultCounter');
        if (!contador) {
            contador = document.createElement('div');
            contador.id = 'bomResultCounter';
            contador.style.cssText = `
                color: #3498db;
                font-size: 10px;
                margin-top: 5px;
                text-align: right;
                padding-right: 10px;
            `;
            const tableContainer = document.querySelector('.bom-table-container');
            tableContainer.insertBefore(contador, tableContainer.firstChild);
        }
        
        if (filterText && filterText.trim() !== '') {
            contador.textContent = `Mostrando ${count} resultado(s) para modelo: "${filterText}"`;
            contador.style.display = 'block';
        } else {
            contador.style.display = 'none';
        }
    }

    // Función modificada para consultar BOM con validación de modelo obligatorio
    function consultarBOMOriginal() {
        // Obtener el modelo seleccionado del buscador
        const modeloSeleccionado = document.getElementById('bomModeloSearch').value;
        
        // Validar que haya un modelo seleccionado
        if (!modeloSeleccionado || modeloSeleccionado.trim() === '' || modeloSeleccionado === 'todos') {
            showCustomAlert(' Debe seleccionar un modelo específico antes de consultar.<br><br>Utilice el buscador para seleccionar un modelo (ej: EBR30299301, EBR30299302, etc.)');
            return;
        }
        
        // Mostrar indicador de carga
        const tbody = document.querySelector('#bomTableBody');
        tbody.innerHTML = '<tr><td colspan="12" class="bom-loading"><div>Cargando datos de BOM para modelo: ' + modeloSeleccionado + '...</div></td></tr>';

        const revisionSelect = document.getElementById('bomRevisionFilter');
        if (!revisionSelect || revisionSelect.dataset.modelo !== modeloSeleccionado.trim().toUpperCase()) {
            cargarRevisionesBOM(modeloSeleccionado, false);
        }

        // Cargar datos desde el servidor
        cargarDatosBOMEnTabla(modeloSeleccionado);
    }

    // Función de prueba inmediata
    window.testCargarModelos = function() {
        cargarModelosFiltro();
    };

    // Permitir redimensionar columnas tipo Excel
    document.addEventListener('DOMContentLoaded', function () {
        
        // Verificar que los elementos existan
        const bomModeloSearch = document.getElementById('bomModeloSearch');
        const bomDropdownList = document.getElementById('bomDropdownList');
        
        
        // Los modelos se cargan desde el servidor directamente en el HTML
        
        // Modal: cerrar con Escape/Enter y bloquear tabulación fuera del modal
        document.addEventListener('keydown', function(e) {
            const modal = document.getElementById('controlBomAlertModal');
            if (modal && modal.style.display === 'flex') {
                if (e.key === 'Escape' || e.key === 'Enter') {
                    e.preventDefault();
                    hideCustomAlert();
                } else if (e.key === 'Tab') {
                    // Bloquear tabulación fuera del modal
                    const dialog = document.getElementById('controlBomAlertDialog');
                    e.preventDefault();
                    dialog.focus();
                }
            }
        });
        const table = document.getElementById('bomDataTable');
        const thElements = table.querySelectorAll('th');
        thElements.forEach(function (th) {
            // Crear un "grip" para el resize
            const resizer = document.createElement('div');
            resizer.style.width = '5px';
            resizer.style.height = '100%';
            resizer.style.position = 'absolute';
            resizer.style.right = '0';
            resizer.style.top = '0';
            resizer.style.cursor = 'col-resize';
            resizer.style.userSelect = 'none';
            resizer.style.zIndex = '100';
            resizer.classList.add('th-resizer');
            th.style.position = 'relative';
            th.appendChild(resizer);

            let startX, startWidth;

            resizer.addEventListener('mousedown', function (e) {
                startX = e.pageX;
                startWidth = th.offsetWidth;
                document.body.style.cursor = 'col-resize';

                function onMouseMove(e) {
                    const newWidth = startWidth + (e.pageX - startX);
                    th.style.width = newWidth + 'px';
                }

                function onMouseUp() {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    document.body.style.cursor = '';
                }

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        });
    });

    // Modal personalizado
    window.showCustomAlert = function(message) {
        abrirModalBom('controlBomAlertModal');
        document.getElementById('controlBomAlertMessage').innerHTML = message;
        setTimeout(() => {
            const okBtn = document.getElementById('controlBomAlertOkBtn');
            if (okBtn) okBtn.focus();
        }, 50);
    }
    window.hideCustomAlert = function() {
        cerrarModalBom('controlBomAlertModal');
    }

    // Modal de carga con progreso
    window.showLoadingModal = function() {
        abrirModalBom('controlBomLoadingModal');
        updateLoadingProgress(0, "Iniciando...", "");
    }

    window.hideLoadingModal = function() {
        cerrarModalBom('controlBomLoadingModal');
    }

    window.updateLoadingProgress = function(percentage, message, timeEstimate) {
        const progressFill = document.getElementById('controlBomLoadingProgressFill');
        const progressText = document.getElementById('controlBomLoadingProgressText');
        const loadingMessage = document.getElementById('controlBomLoadingMessage');
        const timeEstimateElement = document.getElementById('controlBomLoadingTimeEstimate');

        // Asegurar que el porcentaje esté entre 0 y 100
        percentage = Math.max(0, Math.min(100, percentage));

        if (progressFill) {
            progressFill.style.width = percentage + '%';
        }

        if (progressText) {
            progressText.textContent = Math.round(percentage) + '% completado';
        }

        if (loadingMessage && message) {
            loadingMessage.textContent = message;
        }

        if (timeEstimateElement && timeEstimate) {
            timeEstimateElement.textContent = timeEstimate;
        }

        // Cambiar color de la barra según progreso
        if (progressFill) {
            if (percentage < 50) {
                progressFill.style.background = 'linear-gradient(90deg, #3498db, #2980b9)';
            } else if (percentage < 90) {
                progressFill.style.background = 'linear-gradient(90deg, #f39c12, #e67e22)';
            } else {
                progressFill.style.background = 'linear-gradient(90deg, #27ae60, #229954)';
            }
        }
    }

    // ========== FUNCIÓN DE LIMPIEZA PARA AJAX ==========
    function cleanupControlBOM() {
        console.log('🧹 Limpiando módulo Control BOM...');
        
        // Cerrar modales abiertos
        const modalAlert = document.getElementById('controlBomAlertModal');
        const modalLoading = document.getElementById('controlBomLoadingModal');
        
        if (modalAlert) cerrarModalBom('controlBomAlertModal');
        if (modalLoading) cerrarModalBom('controlBomLoadingModal');
        
        // Limpiar dropdown
        const dropdown = document.getElementById('bomDropdownList');
        if (dropdown) dropdown.style.display = 'none';
        
        // Quitar restos de modales legacy si quedaron abiertos antes de recargar el módulo.
        document.getElementById('bomEditPanel')?.remove();
        document.getElementById('bomEditPanelOverlay')?.remove();
        document.getElementById('modalRegistroPosicion')?.remove();
        
        // Los listeners delegados viven en body y deben conservar su flag.
        // El markup AJAX se reemplaza, pero volver a agregarlos duplica requests.
        
        console.log(' Limpieza de Control BOM completada');
    }

    // ========== PANEL DESLIZANTE DE EDICIÓN ==========
    function openBOMEditPanel(bomData) {
        console.warn('Edicion directa de BOM deshabilitada. Use Crear ECO.');
        return;
        console.log('📝 Abriendo panel de edición BOM', bomData);
        
        // Remover panel existente si hay uno
        closeBOMEditPanel();
        
        // Crear overlay
        const overlay = document.createElement('div');
        overlay.id = 'bomEditPanelOverlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(2px);
            z-index: 9998;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        // Crear panel deslizante
        const panel = document.createElement('div');
        panel.id = 'bomEditPanel';
        panel.style.cssText = `
            position: fixed;
            top: 0;
            right: -550px;
            width: 550px;
            height: 100%;
            background-color: #32323E;
            box-shadow: -5px 0 20px rgba(0, 0, 0, 0.5);
            border-left: 2px solid #20688C;
            z-index: 9999;
            overflow-y: auto;
            transition: right 0.3s ease;
            display: flex;
            flex-direction: column;
        `;
        
        // Crear contenido del panel
        const panelContent = document.createElement('div');
        panelContent.style.cssText = `
            padding: 20px;
            flex: 1;
            overflow-y: auto;
        `;
        
        // Header del panel
        const header = document.createElement('div');
        header.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #20688C;
        `;
        header.innerHTML = `
            <h3 style="margin: 0; color: #ecf0f1; font-size: 1.3em; font-weight: 600; font-family: 'LG regular', sans-serif;">
                <i class="fas fa-edit" style="margin-right: 10px; color: #3498db;"></i>
                Editar BOM
            </h3>
            <button id="closeBOMEditPanel" style="
                background-color: #40424F;
                border: 1px solid #20688C;
                border-radius: 4px;
                font-size: 18px;
                cursor: pointer;
                color: lightgray;
                padding: 6px 12px;
                transition: all 0.3s;
            " onmouseover="this.style.backgroundColor='#e74c3c'; this.style.color='white';" onmouseout="this.style.backgroundColor='#40424F'; this.style.color='lightgray';">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Formulario con campos editables
        const form = document.createElement('form');
        form.id = 'bomEditForm';
        form.style.cssText = `
            display: flex;
            flex-direction: column;
            gap: 15px;
        `;
        
        // Función para crear campo de formulario
        function createFormField(label, fieldName, value, type = 'text', readonly = false) {
            const fieldGroup = document.createElement('div');
            fieldGroup.style.cssText = `
                display: flex;
                flex-direction: column;
                gap: 6px;
            `;
            
            const labelEl = document.createElement('label');
            labelEl.textContent = label;
            labelEl.style.cssText = `
                font-weight: 600;
                color: #ecf0f1;
                font-size: 0.9em;
                font-family: 'LG regular', sans-serif;
            `;
            
            const input = document.createElement('input');
            input.type = type;
            input.name = fieldName;
            input.value = value || '';
            input.readOnly = readonly;
            input.style.cssText = `
                padding: 10px 12px;
                border: 1px solid ${readonly ? '#5F6375' : '#34495e'};
                border-radius: 4px;
                font-size: 0.95em;
                background-color: ${readonly ? '#2c3e50' : '#40424F'};
                color: ${readonly ? '#95a5a6' : 'lightgray'};
                transition: all 0.3s;
                font-family: 'LG regular', sans-serif;
            `;
            
            if (!readonly) {
                input.addEventListener('focus', function() {
                    this.style.borderColor = '#3498db';
                    this.style.boxShadow = '0 0 0 3px rgba(52, 152, 219, 0.1)';
                    this.style.backgroundColor = '#34495e';
                });
                input.addEventListener('blur', function() {
                    this.style.borderColor = '#34495e';
                    this.style.boxShadow = 'none';
                    this.style.backgroundColor = '#40424F';
                });
            }
            
            fieldGroup.appendChild(labelEl);
            fieldGroup.appendChild(input);
            return fieldGroup;
        }
        
        // Agregar campos al formulario
        form.appendChild(createFormField('Número de Parte', 'numeroParte', bomData.numeroParte));
        form.appendChild(createFormField('Tipo de Material', 'tipoMaterial', bomData.tipoMaterial));
        form.appendChild(createFormField('Classification', 'classification', bomData.classification));
        form.appendChild(createFormField('Especificación de Material', 'especificacionMaterial', bomData.especificacionMaterial));
        form.appendChild(createFormField('Maker', 'vender', bomData.vender));
        form.appendChild(createFormField('Cantidad Total', 'cantidadTotal', bomData.cantidadTotal, 'number'));
        form.appendChild(createFormField('Ubicación', 'ubicacion', bomData.ubicacion));
        form.appendChild(createFormField('Material Sustituto', 'materialSustituto', bomData.materialSustituto));
        
        // Botones del formulario
        const buttonGroup = document.createElement('div');
        buttonGroup.style.cssText = `
            display: flex;
            gap: 10px;
            margin-top: 20px;
            padding-top: 15px;
            border-top: 2px solid #20688C;
        `;
        
        const saveButton = document.createElement('button');
        saveButton.type = 'button';
        saveButton.id = 'saveBOMChanges';
        saveButton.innerHTML = '<i class="fas fa-save" style="margin-right: 8px;"></i>Guardar Cambios';
        saveButton.style.cssText = `
            flex: 1;
            padding: 10px 20px;
            background-color: #456636;
            color: white;
            border: 1px solid #5a7c42;
            border-radius: 4px;
            font-size: 0.95em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-family: 'LG regular', sans-serif;
        `;
        saveButton.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#5a7c42';
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 4px 12px rgba(69, 102, 54, 0.3)';
        });
        saveButton.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '#456636';
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = 'none';
        });
        
        const cancelButton = document.createElement('button');
        cancelButton.type = 'button';
        cancelButton.innerHTML = '<i class="fas fa-times" style="margin-right: 8px;"></i>Cancelar';
        cancelButton.style.cssText = `
            flex: 1;
            padding: 10px 20px;
            background-color: #95a5a6;
            color: white;
            border: 1px solid #7f8c8d;
            border-radius: 4px;
            font-size: 0.95em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-family: 'LG regular', sans-serif;
        `;
        cancelButton.addEventListener('click', closeBOMEditPanel);
        cancelButton.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#7f8c8d';
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 4px 12px rgba(149, 165, 166, 0.3)';
        });
        cancelButton.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '#95a5a6';
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = 'none';
        });
        
        buttonGroup.appendChild(saveButton);
        buttonGroup.appendChild(cancelButton);
        form.appendChild(buttonGroup);
        
        // Agregar estilos CSS personalizados
        const style = document.createElement('style');
        style.textContent = `
            #bomEditPanel::-webkit-scrollbar {
                width: 8px;
            }
            
            #bomEditPanel::-webkit-scrollbar-track {
                background-color: #2c3e50;
            }
            
            #bomEditPanel::-webkit-scrollbar-thumb {
                background-color: #3498db;
                border-radius: 4px;
            }
            
            #bomEditPanel::-webkit-scrollbar-thumb:hover {
                background-color: #2980b9;
            }
        `;
        document.head.appendChild(style);
        
        // Ensamblar el panel
        panelContent.appendChild(header);
        panelContent.appendChild(form);
        panel.appendChild(panelContent);
        
        // Agregar al DOM
        document.body.appendChild(overlay);
        document.body.appendChild(panel);
        
        // Guardar datos originales para el formulario
        panel.dataset.bomId = bomData.id || '';
        panel.dataset.modelo = bomData.modelo || '';
        panel.dataset.codigoMaterial = bomData.codigoMaterial || '';
        
        // Animar la apertura
        setTimeout(() => {
            overlay.style.opacity = '1';
            panel.style.right = '0';
        }, 10);
    }

    function closeBOMEditPanel() {
        const panel = document.getElementById('bomEditPanel');
        const overlay = document.getElementById('bomEditPanelOverlay');
        
        if (panel) {
            panel.style.right = '-550px';
            setTimeout(() => {
                if (panel.parentNode) panel.parentNode.removeChild(panel);
            }, 300);
        }
        
        if (overlay) {
            overlay.style.opacity = '0';
            setTimeout(() => {
                if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
            }, 300);
        }
    }

    function saveBOMEdit() {
        showCustomAlert('La edicion directa del BOM esta deshabilitada. Usa Crear ECO.');
        return;
        const panel = document.getElementById('bomEditPanel');
        const form = document.getElementById('bomEditForm');
        
        if (!panel || !form) return;
        
        const formData = new FormData(form);
        const bomData = {
            id: panel.dataset.bomId,
            modelo: panel.dataset.modelo,
            codigoMaterial: panel.dataset.codigoMaterial,
            numeroParte: formData.get('numeroParte'),
            tipoMaterial: formData.get('tipoMaterial'),
            classification: formData.get('classification'),
            especificacionMaterial: formData.get('especificacionMaterial'),
            vender: formData.get('vender'),
            cantidadTotal: formData.get('cantidadTotal'),
            ubicacion: formData.get('ubicacion'),
            materialSustituto: formData.get('materialSustituto')
        };
        
        console.log(' Guardando cambios BOM:', bomData);
        
        // Cerrar el panel PRIMERO
        closeBOMEditPanel();
        
        // Luego mostrar loading
        showLoadingModal();
        updateLoadingProgress(30, 'Guardando cambios BOM...', 'Actualizando registro...');
        
        // Enviar al servidor
        fetch('/api/bom/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(bomData)
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.error || 'Error al guardar');
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log(' BOM actualizado:', data);
                updateLoadingProgress(100, ' Cambios guardados', '');
                
                setTimeout(() => {
                    hideLoadingModal();
                    showCustomAlert(' Cambios guardados exitosamente');
                    
                    // Recargar datos después de un delay
                    setTimeout(() => {
                        consultarBOM();
                    }, 500);
                }, 800);
            })
            .catch(error => {
                console.error(' Error al guardar cambios BOM:', error);
                hideLoadingModal();
                showCustomAlert(` Error al guardar cambios: ${error.message}`);
            });
    }

    // ========== REGISTRO DE POSICIÓN ASSY ==========
    
    /**
     * Crear modal dinámicamente en el body
     * Siguiendo las mejores prácticas de la guía de desarrollo
     */
    function createModalRegistroPosicion() {
        console.log('🏗️ Creando modal de registro de posición dinámicamente...');
        
        // Si ya existe, no crear de nuevo
        if (document.getElementById('modalRegistroPosicion')) {
            console.log(' Modal ya existe');
            return;
        }
        
        const modal = document.createElement('div');
        modal.id = 'modalRegistroPosicion';
        modal.style.cssText = `
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 10000;
            overflow: auto;
            padding: 20px;
        `;
        
        modal.innerHTML = `
            <div style="
                background-color: #32323E;
                border: 2px solid #20688C;
                border-radius: 8px;
                max-width: 95%;
                margin: 20px auto;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            ">
                <!-- Header del Modal -->
                <div style="
                    background-color: #172A46;
                    color: #ecf0f1;
                    padding: 15px 20px;
                    border-bottom: 2px solid #20688C;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    border-radius: 6px 6px 0 0;
                ">
                    <h3 style="margin: 0; font-family: 'LG regular', sans-serif; font-size: 1.3em;">
                        <i class="fas fa-map-marked-alt" style="margin-right: 10px; color: #3498db;"></i>
                        Registro de Posición ASSY
                    </h3>
                    <button id="btnCerrarModalPosicion" style="
                        background-color: #40424F;
                        border: 1px solid #20688C;
                        border-radius: 4px;
                        color: lightgray;
                        font-size: 20px;
                        cursor: pointer;
                        padding: 5px 12px;
                        transition: all 0.3s;
                    ">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <!-- Contenido del Modal -->
                <div style="padding: 20px; max-height: 70vh; overflow-y: auto;">
                    <div class="bom-table-container">
                        <table class="bom-table" id="tablaPosicionAssy" style="margin-bottom: 20px;">
                            <thead>
                                <tr>
                                    <th style="min-width: 120px;">Código de Material</th>
                                    <th style="min-width: 120px;">Número de Parte</th>
                                    <th style="min-width: 150px;">Descripción</th>
                                    <th style="min-width: 100px;">Ubicación</th>
                                    <th style="min-width: 150px;">Posición ASSY</th>
                                </tr>
                            </thead>
                            <tbody id="tablaPosicionAssyBody">
                                <!-- Se llenará dinámicamente -->
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Footer con botones -->
                <div style="
                    padding: 15px 20px;
                    border-top: 2px solid #20688C;
                    display: flex;
                    gap: 10px;
                    justify-content: flex-end;
                    background-color: #2c3e50;
                    border-radius: 0 0 6px 6px;
                ">
                    <button id="btnGuardarPosicionesAssy" class="bom-btn exportar" style="
                        padding: 10px 20px;
                        font-size: 1em;
                    ">
                        <i class="fas fa-save" style="margin-right: 8px;"></i>
                        Guardar Cambios
                    </button>
                    <button id="btnCancelarModalPosicion" class="bom-btn limpiar" style="
                        padding: 10px 20px;
                        font-size: 1em;
                    ">
                        <i class="fas fa-times" style="margin-right: 8px;"></i>
                        Cancelar
                    </button>
                </div>
            </div>
        `;
        
        // Agregar al body
        document.body.appendChild(modal);
        console.log(' Modal de registro de posición creado en el body');
    }
    
    function abrirModalRegistroPosicion() {
        showCustomAlert('La edicion directa de posiciones esta deshabilitada. Usa Crear ECO.');
        return;
        console.log('📍 Abriendo modal de registro de posición');
        
        // Crear el modal si no existe
        createModalRegistroPosicion();
        
        // Verificar que haya datos consultados
        if (!bomDataCache || bomDataCache.length === 0) {
            showCustomAlert('Por favor, consulta primero el BOM del modelo que deseas editar.');
            return;
        }
        
        // Llenar la tabla del modal con los datos actuales
        const tbody = document.getElementById('tablaPosicionAssyBody');
        if (!tbody) {
            console.error(' No se encontró el tbody del modal');
            return;
        }
        
        tbody.innerHTML = '';
        
        bomDataCache.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.style.cssText = 'transition: background-color 0.2s;';
            
            tr.innerHTML = `
                <td style="padding: 8px; border: 1px solid #5F6375; background-color: #40424F; color: lightgray; font-size: 0.9em;">
                    ${item.codigoMaterial || ''}
                </td>
                <td style="padding: 8px; border: 1px solid #5F6375; background-color: #40424F; color: lightgray; font-size: 0.9em;">
                    ${item.numeroParte || ''}
                </td>
                <td style="padding: 8px; border: 1px solid #5F6375; background-color: #40424F; color: lightgray; font-size: 0.9em;">
                    ${item.especificacionMaterial || ''}
                </td>
                <td style="padding: 8px; border: 1px solid #5F6375; background-color: #40424F; color: lightgray; font-size: 0.9em;">
                    ${item.ubicacion || ''}
                </td>
                <td style="padding: 8px; border: 1px solid #5F6375; background-color: #40424F;">
                    <input 
                        type="text" 
                        class="input-posicion-assy"
                        data-index="${index}"
                        data-codigo="${item.codigoMaterial}"
                        value="${item.posicionAssy || ''}"
                        style="
                            width: 100%;
                            padding: 12px 15px;
                            background-color: #34495e;
                            color: lightgray;
                            border: 2px solid #20688C;
                            border-radius: 4px;
                            font-family: 'LG regular', sans-serif;
                            font-size: 1.1em;
                            font-weight: 600;
                            transition: all 0.3s;
                            text-align: center;
                        "
                        onfocus="this.style.borderColor='#3498db'; this.style.backgroundColor='#2c3e50'; this.style.boxShadow='0 0 0 3px rgba(52, 152, 219, 0.2)';"
                        onblur="this.style.borderColor='#20688C'; this.style.backgroundColor='#34495e'; this.style.boxShadow='none';"
                    />
                </td>
            `;
            
            tbody.appendChild(tr);
        });
        
        // Mostrar el modal
        const modal = document.getElementById('modalRegistroPosicion');
        if (modal) {
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden'; // Prevenir scroll del body
        }
    }
    
    function cerrarModalRegistroPosicion() {
        console.log(' Cerrando modal de registro de posición');
        const modal = document.getElementById('modalRegistroPosicion');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto'; // Restaurar scroll del body
        }
    }
    
    function guardarPosicionesAssy() {
        showCustomAlert('La edicion directa de posiciones esta deshabilitada. Usa Crear ECO.');
        return;
        console.log(' Guardando posiciones ASSY');
        
        // Recopilar todos los inputs
        const inputs = document.querySelectorAll('.input-posicion-assy');
        if (inputs.length === 0) {
            showCustomAlert('No hay posiciones para guardar.');
            return;
        }
        
        // Crear array de cambios
        const cambios = [];
        inputs.forEach(input => {
            const index = parseInt(input.dataset.index);
            const codigo = input.dataset.codigo;
            const nuevaPosicion = input.value.trim();
            
            if (bomDataCache[index]) {
                cambios.push({
                    codigoMaterial: codigo,
                    modelo: bomDataCache[index].modelo,
                    posicionAssy: nuevaPosicion
                });
            }
        });
        
        if (cambios.length === 0) {
            showCustomAlert('No hay cambios para guardar.');
            return;
        }
        
        console.log('📦 Cambios a guardar:', cambios);
        
        // Cerrar el modal PRIMERO
        cerrarModalRegistroPosicion();
        
        // Luego mostrar loading
        showLoadingModal();
        updateLoadingProgress(30, 'Guardando posiciones ASSY...', 'Procesando en lote...');
        
        // Enviar al servidor
        fetch('/api/bom/update-posiciones-assy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ cambios: cambios })
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.error || 'Error al guardar posiciones');
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log(' Respuesta del servidor:', data);
                updateLoadingProgress(100, ` ${data.actualizados} posiciones guardadas`, '');
                
                // Cerrar loading y mostrar resultado
                setTimeout(() => {
                    hideLoadingModal();
                    
                    // Mostrar alerta de éxito
                    showCustomAlert(` ${data.actualizados} posiciones ASSY guardadas correctamente`);
                    
                    // Recargar la tabla
                    const modeloSeleccionado = document.getElementById('modeloDropdown').value;
                    if (modeloSeleccionado) {
                        setTimeout(() => {
                            consultarBOM();
                        }, 500);
                    }
                }, 800);
            })
            .catch(error => {
                console.error(' Error al guardar posiciones:', error);
                hideLoadingModal();
                showCustomAlert(' Error al guardar posiciones: ' + error.message);
            });
    }

    // Exponer función de limpieza globalmente
    window.cleanupControlBOM = cleanupControlBOM;

    // ========== EXPONER FUNCIONES GLOBALMENTE ==========
    window.cargarDatosBOMEnTabla = cargarDatosBOMEnTabla;
    window.consultarBOM = consultarBOM;
    window.mostrarFormularioBOM = mostrarFormularioBOM;
    window.eliminarBOM = eliminarBOM;
    window.mostrarSustitutoBOM = mostrarSustitutoBOM;
    window.exportarExcelBOM = exportarExcelBOM;
    window.filtrarModelos = filtrarModelos;
    window.mostrarDropdown = mostrarDropdown;
    window.seleccionarModelo = seleccionarModelo;
    window.aplicarFiltroClassification = aplicarFiltroClassification;

(function() {
    console.log('📦 Script de auto-inicialización de Control BOM ejecutándose...');
    
    function tryInitialize() {
        if (typeof window.initializeControlBOMEventListeners === 'function') {
            console.log(' Inicializando Control BOM Event Listeners');
            window.initializeControlBOMEventListeners();
        } else {
            console.log('⏳ Esperando carga de funciones de Control BOM...');
            setTimeout(tryInitialize, 100);
        }
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', tryInitialize);
    } else {
        tryInitialize();
    }
})();
})();
