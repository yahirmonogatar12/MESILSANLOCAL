// Visor MySQL - Sistema MES con Modal de Edición
(() => {
  const RX = {
    table: "raw", // Siempre usar tabla raw
    columns: [], 
    rows: [], 
    allRows: [], // Todos los datos del servidor para filtro local
    total: 0,
    limit: 1000, 
    offset: 0, 
    search: ""
  };

  const $ = (id) => document.getElementById(id);
  const fmt = (n) => new Intl.NumberFormat('es-MX').format(n);
  const debounce = (fn, t=300) => { 
    let h; 
    return (...a) => { 
      clearTimeout(h); 
      h = setTimeout(() => fn(...a), t); 
    }; 
  };

  function setStatus(msg, type = 'info') {
    // Estado actualizado silenciosamente
  }

  function formatCellValue(value, columnName) {
    if (value === null || value === undefined) return '<span class="text-muted">NULL</span>';
    if (value === '') return '<span class="text-muted">-</span>';
    
    // Formatear fechas
    if (columnName.includes('fecha') || columnName.includes('date') || columnName.includes('time')) {
      try {
        const date = new Date(value);
        if (!isNaN(date.getTime())) {
          return date.toLocaleString('es-MX');
        }
      } catch (e) {
        // Si no es fecha válida, continuar
      }
    }
    
    // Formatear números grandes
    if (typeof value === 'number' && value > 999) {
      return fmt(value);
    }
    
    // Truncar texto muy largo y agregar tooltip
    const str = String(value);
    if (str.length > 50) {
      return `<span title="${str}">${str.substring(0, 50)}...</span>`;
    }
    
    return str;
  }

  function render() {
    const thead = $("ix-thead");
    const tbody = $("ix-tbody");
    
    if (!RX.columns.length) {
      thead.innerHTML = '<tr><th>Sin columnas</th></tr>';
      tbody.innerHTML = '<tr><td>Sin datos</td></tr>';
      return;
    }
    
    // Generar encabezados
    const headerCells = RX.columns.map(col => `<th>${col}</th>`).join("");
    thead.innerHTML = `<tr>${headerCells}</tr>`;
    
    // Generar filas con doble click para editar
    if (RX.rows.length > 0) {
      const bodyRows = RX.rows.map((row, index) => {
        const cells = RX.columns.map(col => {
          const value = row[col];
          const displayValue = formatCellValue(value, col);
          const fullText = String(value || '').replace(/"/g, '&quot;');
          
          // Agregar data-full-text solo si el texto es largo
          const dataAttr = fullText.length > 50 ? `data-full-text="${fullText}"` : '';
          
          return `<td ${dataAttr}>${displayValue}</td>`;
        }).join("");
        
        // Obtener ID del registro para la funcionalidad de eliminación
        const recordId = row._recordId || null;
        
        return `<tr data-row-index="${index}" data-record-id="${recordId || ''}" style="cursor: pointer;" ondblclick="abrirModalEdicion(this)" title="Doble click para editar">${cells}</tr>`;
      }).join("");
      
      tbody.innerHTML = bodyRows;
    }
    
    // Update counters
    const filteredCount = RX.rows.length;
    const totalCount = RX.allRows.length || RX.total;
    const isFiltered = RX.search && RX.search.trim() !== '';
    
    $("ix-counter").innerHTML = isFiltered 
      ? `<strong>${fmt(filteredCount)}</strong> de ${fmt(totalCount)} filas (filtradas)`
      : `<strong>${fmt(totalCount)}</strong> filas total`;
    
    // Update table info
    $("ix-table-info").innerHTML = `
      Mostrando ${filteredCount} registros${isFiltered ? ` para "${RX.search}"` : ''} • Doble click para editar
    `;
  }

  async function fetchColumns() {
    const url = new URL(`${location.origin}/api/mysql/columns`);
    url.searchParams.set("table", RX.table);
    
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    if (data.error) {
      throw new Error(data.error);
    }
    
    // Filtrar columnas no deseadas PERO no el ID (lo usaremos internamente)
    const hiddenColumns = ['_raw_rowhash', 'ID', 'id', 'raw', 'crea', 'upt'];
    RX.columns = (data.columns || []).filter(col => 
      !hiddenColumns.includes(col)
    );
  }

  async function fetchData() {
    const url = new URL(`${location.origin}/api/mysql/data`);
    url.searchParams.set("table", RX.table);
    url.searchParams.set("limit", RX.limit);
    url.searchParams.set("offset", RX.offset);
    // No enviar search - cargar todos los datos para filtro local
    
    const startTime = performance.now();
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    if (data.error) {
      throw new Error(data.error);
    }
    
    // Filtrar columnas no deseadas PERO preservar ID para funcionalidad
    const hiddenColumns = ['_raw_rowhash', 'raw', 'crea', 'upt'];
    const originalColumns = data.columns || [];
    const filteredColumns = originalColumns.filter(col => 
      !hiddenColumns.includes(col) && !['ID', 'id'].includes(col)
    );
    
    // Filtrar las filas para remover las columnas ocultas PERO preservar ID
    const filteredRows = (data.rows || []).map(row => {
      const filteredRow = {};
      
      // Preservar ID para funcionalidad de eliminación
      if (row.ID !== undefined) filteredRow._recordId = row.ID;
      else if (row.id !== undefined) filteredRow._recordId = row.id;
      filteredColumns.forEach(col => {
        if (row.hasOwnProperty(col)) {
          filteredRow[col] = row[col];
        }
      });
      return filteredRow;
    });
    
    // Guardar todos los datos para filtro local
    RX.allRows = filteredRows;
    RX.total = data.total || 0;
    RX.limit = data.limit || RX.limit;
    RX.offset = data.offset || RX.offset;
    
    // Aplicar filtro actual
    applyLocalFilter();
    
    const elapsed = Math.round(performance.now() - startTime);
    const timestamp = new Date().toLocaleTimeString('es-MX');
    
    setStatus(`Actualizado: ${timestamp} • ${fmt(RX.total)} filas • ${elapsed}ms`, 'success');
    render();
  }

  // Nueva función para filtro local instantáneo con ordenamiento inteligente
  function applyLocalFilter() {
    if (!RX.search || RX.search.trim() === '') {
      RX.rows = [...RX.allRows];
    } else {
      const searchTerm = RX.search.toLowerCase();
      RX.rows = RX.allRows.filter(row => {
        return Object.values(row).some(value => {
          if (value === null || value === undefined) return false;
          return String(value).toLowerCase().includes(searchTerm);
        });
      });
    }
    
    // Aplicar ordenamiento inteligente en el cliente
    smartSort(RX.rows);
  }

  // Función para ordenamiento inteligente de modelos similares
  function smartSort(rows) {
    if (!rows.length || !RX.columns.length) return;
    
    // Buscar columnas que podrían contener códigos de modelo
    const modelColumns = RX.columns.filter(col => {
      const colLower = col.toLowerCase();
      return ['modelo', 'model', 'codigo', 'parte', 'part', 'ebr', 'product'].some(keyword => 
        colLower.includes(keyword)
      );
    });
    
    if (modelColumns.length === 0) {
      // Si no hay columnas obvias de modelo, ordenar por la primera columna
      const sortCol = RX.columns[0];
      rows.sort((a, b) => {
        const valA = String(a[sortCol] || '');
        const valB = String(b[sortCol] || '');
        return valA.localeCompare(valB);
      });
      return;
    }
    
    // Usar la primera columna que parece ser de modelo
    const sortCol = modelColumns[0];
    
    rows.sort((a, b) => {
      const valA = String(a[sortCol] || '');
      const valB = String(b[sortCol] || '');
      
      // Extraer la parte base del código (sin números finales)
      const baseA = valA.replace(/\d+$/, '');
      const baseB = valB.replace(/\d+$/, '');
      
      // Primero ordenar por la parte base
      if (baseA !== baseB) {
        return baseA.localeCompare(baseB);
      }
      
      // Si las bases son iguales, ordenar por el código completo
      return valA.localeCompare(valB);
    });
  }

  async function refreshAll() {
    try {
      setStatus("Cargando datos...", 'loading');
      $("ix-table-wrap").classList.add('loading');
      
      if (!RX.columns.length) {
        await fetchColumns();
      }
      await fetchData();
      
    } catch (error) {
      console.error('Error refreshing data:', error);
      setStatus(`Error: ${error.message}`, 'error');
    } finally {
      $("ix-table-wrap").classList.remove('loading');
    }
  }

  // Función para abrir modal de registro (nuevo)
  async function abrirModalRegistro() {
    if (!window.rawEditModal) {
      console.error('Modal no inicializado');
      return;
    }
    
    if (!RX.columns || RX.columns.length === 0) {
      console.error('Columnas no cargadas aún');
      return;
    }
    
    // Crear objeto vacío para nuevo registro
    // Usuario debe ser el usuario logueado actual
    const emptyRow = {};
    RX.columns.forEach(col => {
      if (col === 'Usuario') {
        emptyRow[col] = window.usuarioLogueado || 'Usuario no identificado';
      } else {
        emptyRow[col] = '';
      }
    });
    
    window.rawEditModal.abrir(emptyRow, 'NUEVO');
  }

  // Event Listeners
  $("ix-refresh").addEventListener("click", () => {
    RX.offset = 0;
    refreshAll();
  });

  $("ix-register").addEventListener("click", () => {
    abrirModalRegistro();
  });

  $("ix-search").addEventListener("input", (e) => {
    RX.search = e.target.value.trim();
    applyLocalFilter();
    render();
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
      switch(e.key) {
        case 'r':
          e.preventDefault();
          refreshAll();
          break;
        case 'f':
          e.preventDefault();
          $("ix-search").focus();
          break;
      }
    }
  });

  // Initialize
  (async function init() {
    try {
      // Esperar a que el modal esté inicializado
      let modalReady = false;
      let attempts = 0;
      const maxAttempts = 50; // 5 segundos máximo
      
      while (!modalReady && attempts < maxAttempts) {
        if (window.rawEditModal) {
          modalReady = true;
        } else {
          await new Promise(resolve => setTimeout(resolve, 100));
          attempts++;
        }
      }
      
      await refreshAll();
      
      setStatus("Visor MySQL listo - Ctrl+R para actualizar, Ctrl+F para buscar");
      
    } catch (error) {
      console.error('Initialization error:', error);
      setStatus(`Error de inicialización: ${error.message}`, 'error');
    }
  })();

  // Función global para abrir modal de edición
  window.abrirModalEdicion = function(row) {
    const cells = row.querySelectorAll('td');
    const rowData = {};
    const rowIndex = row.getAttribute('data-row-index');
    const recordId = row.getAttribute('data-record-id');
    
    // Extraer datos de la fila
    RX.columns.forEach((col, index) => {
      const cell = cells[index];
      if (cell) {
        // Obtener el valor real, no el HTML formateado
        let value = cell.getAttribute('data-full-text') || cell.textContent.trim();
        
        // Limpiar valores especiales
        if (value === 'NULL' || value === '-') {
          value = '';
        }
        
        rowData[col] = value;
      }
    });
    
    // Agregar información adicional para identificación
    rowData._row_index = rowIndex;
    rowData._timestamp = Date.now();
    
    // Asegurar que el ID esté disponible en los datos - usar el ID del data-record-id
    if (recordId && recordId !== '') {
      rowData._recordId = recordId;
      // También agregar como ID para compatibilidad
      if (!rowData.id && !rowData.ID && !rowData.Id) {
        rowData.id = recordId;
      }
    }
    
    // Abrir modal con los datos
    if (window.rawEditModal) {
      window.rawEditModal.abrir(rowData);
    } else {
      // Crear modal si no existe
      window.rawEditModal = new RawEditModal();
      window.rawEditModal.abrir(rowData);
    }
  };

  // Exponer refreshAll globalmente
  window.refreshAll = refreshAll;

})();

// Modal de Edición para tabla RAW
class RawEditModal {
  constructor() {
    this.createModalHTML();
    this.currentData = null;
  }

  createModalHTML() {
    const modalHTML = `
    <!-- Modal de Edición RAW -->
    <div id="rawEditModal" class="raw-edit-modal">
      <div class="modal-header">
        <h3>Editar Registro RAW</h3>
        <button type="button" class="btn-close-modal" onclick="rawEditModal.cerrar()">
          <i class="fas fa-times"></i>
        </button>
      </div>
      
      <div class="modal-body">
        <form id="rawEditForm">
          <div id="rawFormFields" class="form-fields">
            <!-- Los campos se generan dinámicamente -->
          </div>
        </form>
      </div>
      
      <div class="modal-footer">
        <div class="modal-footer-left">
          <button type="button" id="btn-eliminar" class="btn btn-danger" onclick="rawEditModal.eliminar()" style="display: none;">
            Eliminar
          </button>
        </div>
        <div class="modal-footer-right">
          <button type="button" class="btn btn-secondary" onclick="rawEditModal.cerrar()">
            Cancelar
          </button>
          <button type="button" class="btn btn-primary" onclick="rawEditModal.guardar()">
            Guardar Cambios
          </button>
        </div>
      </div>
    </div>

    <!-- Overlay -->
    <div id="rawModalOverlay" class="modal-overlay" onclick="rawEditModal.cerrar()"></div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    this.injectStyles();
  }

  injectStyles() {
    const styles = `
    <style>
    /* Modal de Edición RAW - Estilo del Sistema */
    .raw-edit-modal {
      position: fixed !important;
      top: 50% !important;
      left: 50% !important;
      transform: translate(-50%, -50%) scale(0.7) !important;
      width: 90% !important;
      max-width: 800px !important;
      max-height: 80vh !important;
      background: #4a5568 !important;
      border: 2px solid #2d3748 !important;
      z-index: 9999999 !important;
      display: none !important;
      flex-direction: column !important;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif !important;
      opacity: 0 !important;
      transition: all 0.3s ease !important;
      border-radius: 8px !important;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8) !important;
    }

    .raw-edit-modal.open {
      display: flex !important;
      opacity: 1 !important;
      transform: translate(-50%, -50%) scale(1) !important;
    }

    .modal-overlay {
      display: none !important;
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      bottom: 0 !important;
      background: rgba(0, 0, 0, 0.8) !important;
      z-index: 9999998 !important;
      opacity: 0 !important;
      transition: opacity 0.3s ease !important;
    }

    .modal-overlay.active {
      display: block !important;
      opacity: 1 !important;
    }

    .modal-header {
      background-color: #2d3748 !important;
      color: #e2e8f0 !important;
      padding: 20px !important;
      display: flex !important;
      justify-content: space-between !important;
      align-items: center !important;
      border-bottom: 2px solid #1a202c !important;
    }

    .modal-header h3 {
      margin: 0 !important;
      font-size: 16px !important;
      font-weight: 400 !important;
      color: #e2e8f0 !important;
    }

    .btn-close-modal {
      background: none !important;
      border: none !important;
      color: #e2e8f0 !important;
      font-size: 18px !important;
      cursor: pointer !important;
      padding: 8px !important;
      border-radius: 0 !important;
      transition: background-color 0.3s ease !important;
      width: 36px !important;
      height: 36px !important;
    }

    .btn-close-modal:hover {
      background-color: #1a202c !important;
    }

    .modal-body {
      flex: 1 !important;
      overflow-y: auto !important;
      padding: 20px !important;
      background: #3a4556;
    }

    .form-fields {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 15px;
    }

    .form-group {
      display: flex;
      flex-direction: column;
    }

    .form-label {
      color: #cbd5e0;
      margin-bottom: 5px;
      font-size: 13px;
      font-weight: 400;
    }

    .form-control {
      background-color: #2d3748;
      border: 1px solid #5e9ed6;
      color: #e2e8f0;
      padding: 8px 12px;
      border-radius: 0;
      font-size: 14px;
      height: 36px;
      transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }

    .form-control:focus {
      outline: none;
      border-color: #63b3ed;
      box-shadow: 0 0 0 1px #63b3ed;
    }

    .form-control::placeholder {
      color: #718096;
    }

    .form-control.readonly-field {
      background-color: #1a202c;
      border-color: #4a5568;
      color: #a0aec0;
      cursor: not-allowed;
    }

    .form-control.readonly-field:focus {
      border-color: #4a5568;
      box-shadow: none;
    }

    .form-control.numeric-field {
      border-left: 3px solid #5e9ed6;
    }

    .modal-footer {
      background: #2d3748;
      padding: 20px;
      border-top: 2px solid #1a202c;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .modal-footer-left {
      display: flex;
      gap: 10px;
    }

    .modal-footer-right {
      display: flex;
      gap: 10px;
    }

    .modal-footer .btn {
      padding: 8px 24px;
      border-radius: 0;
      font-size: 14px;
      font-weight: 400;
      transition: all 0.3s ease;
      border: none;
      height: 36px;
      cursor: pointer;
    }

    .modal-footer .btn-secondary {
      background-color: #4a5568;
      color: #e2e8f0;
      border: 1px solid #2d3748;
    }

    .modal-footer .btn-secondary:hover {
      background-color: #2d3748;
    }

    .modal-footer .btn-primary {
      background-color: #5e9ed6;
      color: #1a202c;
      border: 1px solid #5e9ed6;
    }

    .modal-footer .btn-primary:hover {
      background-color: #63b3ed;
      border-color: #63b3ed;
    }

    .modal-footer .btn-danger {
      background-color: #e53e3e;
      color: #fff;
      border: 1px solid #e53e3e;
    }

    .modal-footer .btn-danger:hover {
      background-color: #c53030;
      border-color: #c53030;
    }

    .modal-footer .btn:disabled {
      opacity: 0.7;
      cursor: not-allowed;
      background-color: #4a5568 !important;
      border-color: #4a5568 !important;
    }

    .modal-footer .btn:disabled:hover {
      background-color: #4a5568 !important;
      border-color: #4a5568 !important;
    }

    /* Scroll personalizado */
    .modal-body::-webkit-scrollbar {
      width: 8px;
    }

    .modal-body::-webkit-scrollbar-track {
      background: #2d3748;
    }

    .modal-body::-webkit-scrollbar-thumb {
      background: #4a5568;
      border-radius: 0;
    }

    .modal-body::-webkit-scrollbar-thumb:hover {
      background: #5e9ed6;
    }

    /* Bloquear interacción con el body cuando modal está activo */
    body.modal-open {
      overflow: hidden !important;
      position: fixed !important;
      width: 100% !important;
      height: 100% !important;
    }
    
    body.modal-open > *:not(#rawEditModal):not(#rawModalOverlay) {
      pointer-events: none !important;
    }

    /* Responsive */
    @media (max-width: 768px) {
      .raw-edit-modal {
        width: 95%;
        max-height: 90vh;
      }
      
      .form-fields {
        grid-template-columns: 1fr;
      }
    }
    </style>
    `;

    document.head.insertAdjacentHTML('beforeend', styles);
  }

  abrir(data, modo = 'EDITAR') {
    this.currentData = { ...data };
    this.modo = modo;
    this.generarCampos(data);
    
    // Actualizar título del modal
    const titulo = document.querySelector('#rawEditModal .modal-header h3');
    if (titulo) {
      titulo.textContent = modo === 'NUEVO' ? 'Registrar Nuevo Modelo' : 'Editar Registro';
    }
    
    // Mostrar/ocultar botón de eliminación
    const btnEliminar = document.getElementById('btn-eliminar');
    if (btnEliminar) {
      // Solo mostrar botón de eliminar si es modo EDITAR y hay un ID válido
      const recordId = data.id || data.ID || data.Id || data._recordId || null;
      
      if (modo === 'EDITAR' && recordId && recordId !== '' && recordId !== 'null') {
        btnEliminar.style.display = 'inline-flex';
        btnEliminar.setAttribute('data-record-id', recordId);
      } else {
        btnEliminar.style.display = 'none';
      }
    }
    
    document.getElementById('rawEditModal').classList.add('open');
    document.getElementById('rawModalOverlay').classList.add('active');
    
    // Agregar clase al body para bloquear interacciones
    document.body.classList.add('modal-open');
    
    // Forzar z-index y visibilidad para evitar sobreescritura
    const modal = document.getElementById('rawEditModal');
    const overlay = document.getElementById('rawModalOverlay');
    
    if (modal) {
      modal.style.zIndex = '9999999';
      modal.style.position = 'fixed';
      modal.style.display = 'flex';
      modal.style.opacity = '1';
      modal.style.transform = 'translate(-50%, -50%) scale(1)';
    }
    
    if (overlay) {
      overlay.style.zIndex = '9999998';
      overlay.style.position = 'fixed';
      overlay.style.display = 'block';
      overlay.style.opacity = '1';
    }
    
    // Forzar que el modal esté por encima de cualquier otro elemento
    setTimeout(() => {
      if (modal) {
        modal.style.zIndex = '9999999';
        modal.style.display = 'flex';
      }
      if (overlay) {
        overlay.style.zIndex = '9999998';
        overlay.style.display = 'block';
      }
    }, 50);
  }

  generarCampos(data) {
    const container = document.getElementById('rawFormFields');
    container.innerHTML = '';
    
    // Definir campos de solo lectura (no editables)
    // Usuario siempre es readonly - se asigna automáticamente
    const readonlyFields = ['Usuario', 'crea', 'upt'];
    
    // Definir campos numéricos
    const numericFields = ['hora_dia', 'c_t', 'uph', 'price', 'st', 'neck_st', 'l_b', 'input', 'output'];
    
    Object.keys(data).forEach(key => {
      // Excluir campos de metadatos
      if (key.startsWith('_')) return;
      
      const value = data[key] || '';
      const isReadonly = readonlyFields.includes(key);
      const isNumeric = numericFields.includes(key);
      const readonlyAttr = isReadonly ? 'readonly' : '';
      const readonlyClass = isReadonly ? 'readonly-field' : '';
      const numericClass = isNumeric ? 'numeric-field' : '';
      const readonlyLabel = isReadonly ? ' (Solo lectura)' : '';
      const numericLabel = isNumeric ? ' (Numérico)' : '';
      
      const fieldHTML = `
        <div class="form-group">
          <label class="form-label">${key}${readonlyLabel}${numericLabel}</label>
          <input 
            type="${isNumeric ? 'text' : 'text'}" 
            class="form-control ${readonlyClass} ${numericClass}" 
            name="${key}" 
            value="${value}"
            placeholder="Ingrese ${key}"
            ${readonlyAttr}
          />
        </div>
      `;
      
      container.insertAdjacentHTML('beforeend', fieldHTML);
    });
  }

  cerrar() {
    document.getElementById('rawEditModal').classList.remove('open');
    document.getElementById('rawModalOverlay').classList.remove('active');
    
    // Remover clase del body para restaurar interacciones
    document.body.classList.remove('modal-open');
    
    this.currentData = null;
  }

  async guardar() {
    try {
      // Mostrar estado de carga
      this.showLoadingButton(true);
      
      const formData = new FormData(document.getElementById('rawEditForm'));
      const newData = {};
      
      // Definir campos de solo lectura que no se deben enviar desde el formulario
      // Usuario se maneja por separado para asignarlo automáticamente
      const readonlyFields = ['Usuario', 'crea', 'upt'];
      
      // Definir campos numéricos para limpieza
      const numericFields = ['hora_dia', 'c_t', 'uph', 'price', 'st', 'neck_st', 'l_b', 'input', 'output'];
      
      for (let [key, value] of formData.entries()) {
        // Solo incluir campos que no son de solo lectura
        if (!readonlyFields.includes(key)) {
          // Limpiar valores numéricos
          if (numericFields.includes(key)) {
            // Remover comas y espacios de campos numéricos
            value = value.replace(/,/g, '').replace(/\s/g, '');
          }
          newData[key] = value;
        }
      }
      
      // SIEMPRE asignar el usuario logueado actual
      newData.Usuario = window.usuarioLogueado || 'Usuario no identificado';
      
      let response, endpoint, requestBody;
      
      if (this.modo === 'NUEVO') {
        // Crear nuevo registro
        endpoint = '/api/mysql/create';
        requestBody = { data: newData };
      } else {
        // Actualizar registro existente
        endpoint = '/api/mysql/update';
        
        // Filtrar datos originales para enviar solo los campos de datos (sin metadatos y sin readonly excepto Usuario)
        const originalData = {};
        Object.keys(this.currentData).forEach(key => {
          if (!key.startsWith('_') && !['crea', 'upt'].includes(key)) {
            let value = this.currentData[key];
            // Limpiar valores numéricos en datos originales también
            if (numericFields.includes(key) && typeof value === 'string') {
              value = value.replace(/,/g, '').replace(/\s/g, '');
            }
            originalData[key] = value;
          }
        });
        
        // Para actualizaciones, también incluir el Usuario actualizado
        originalData.Usuario = window.usuarioLogueado || 'Usuario no identificado';
        
        requestBody = {
          original: originalData,
          new: newData
        };
        
        // Verificar si hay cambios reales para updates
        const hasChanges = Object.keys(newData).some(key => 
          newData[key] !== originalData[key]
        );
        
        if (!hasChanges) {
          this.showError('No se detectaron cambios para guardar');
          return;
        }
      }
      
      // Enviar datos al servidor
      response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });
      
      const result = await response.json();
      
      if (response.ok && result.success) {
        const successMessage = this.modo === 'NUEVO' 
          ? 'Registro creado exitosamente' 
          : 'Registro actualizado exitosamente';
        this.showSuccess(successMessage);
        this.cerrar();
        
        // Refrescar la tabla después de un breve delay
        setTimeout(() => {
          if (window.refreshAll) {
            window.refreshAll();
          }
        }, 500);
      } else {
        throw new Error(result.error || 'Error desconocido al guardar');
      }
      
    } catch (error) {
      console.error('Error al guardar:', error);
      this.showError(`Error al guardar: ${error.message}`);
    } finally {
      this.showLoadingButton(false);
    }
  }

  async eliminar() {
    try {
      // Obtener el ID del registro
      const recordId = this.currentData.id || this.currentData.ID || this.currentData.Id || null;
      
      if (!recordId) {
        this.showError('No se puede eliminar: ID del registro no válido');
        return;
      }
      
      // Confirmación de eliminación
      const confirmacion = confirm(
        `¿Estás seguro que deseas eliminar este registro?\n\n` +
        `ID: ${recordId}\n\n` +
        `Esta acción no se puede deshacer.`
      );
      
      if (!confirmacion) {
        return;
      }
      
      // Mostrar estado de carga en botón eliminar
      // Cambiar estado del botón
      const btnEliminar = document.getElementById('btn-eliminar');
      const originalText = btnEliminar.innerHTML;
      btnEliminar.disabled = true;
      btnEliminar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Eliminando...';
      
      // Enviar solicitud de eliminación
      const response = await fetch('/api/mysql/delete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          table: 'raw', // Siempre usar tabla raw
          id: recordId
        })
      });
      
      const result = await response.json();
      
      if (response.ok && result.success) {
        this.showSuccess(result.message || 'Registro eliminado exitosamente');
        this.cerrar();
        
        // Refrescar la tabla después de eliminar
        setTimeout(() => {
          if (window.refreshAll) {
            window.refreshAll();
          }
        }, 500);
      } else {
        throw new Error(result.error || 'Error al eliminar el registro');
      }
      
    } catch (error) {
      this.showError(`Error al eliminar: ${error.message}`);
    } finally {
      // Restaurar botón eliminar
      const btnEliminar = document.getElementById('btn-eliminar');
      if (btnEliminar) {
        btnEliminar.disabled = false;
        btnEliminar.innerHTML = 'Eliminar';
      }
    }
  }

  showLoadingButton(loading) {
    const saveButton = document.querySelector('.modal-footer .btn-primary');
    
    if (loading) {
      saveButton.disabled = true;
      const loadingText = this.modo === 'NUEVO' ? 'Creando...' : 'Guardando...';
      saveButton.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>${loadingText}`;
    } else {
      saveButton.disabled = false;
      const buttonText = this.modo === 'NUEVO' ? 'Crear Registro' : 'Guardar Cambios';
      saveButton.innerHTML = buttonText;
    }
  }

  showSuccess(message) {
    this.showToast(message, 'success');
  }

  showError(message) {
    this.showToast(message, 'error');
  }

  showToast(message, type) {
    const toastClass = type === 'success' ? 'bg-success' : 'bg-danger';
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle';
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white ${toastClass} border-0 position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 11000; min-width: 300px;';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          <i class="fas ${icon} me-2"></i>${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.parentElement.parentElement.remove()"></button>
      </div>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove después de 3 segundos
    setTimeout(() => {
      if (toast.parentElement) {
        toast.remove();
      }
    }, 3000);
  }
}

// Inicializar modal cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
  if (!window.rawEditModal) {
    window.rawEditModal = new RawEditModal();
  }
});

// También intentar inicializar inmediatamente por si el DOM ya está listo
if (document.readyState === 'loading') {
  // El DOM aún se está cargando
} else {
  // El DOM ya está cargado
  if (!window.rawEditModal) {
    window.rawEditModal = new RawEditModal();
  }
}
