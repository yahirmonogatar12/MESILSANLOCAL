// Visor MySQL - Sistema MES con Modal de Edición

// ====== WF_004: Garantizar CSS del modulo en <head> ======
// El CSS ya esta en MainTemplate.html, pero si este JS se carga desde
// el visor standalone (/visor-mysql) sin pasar por MainTemplate,
// inyectarlo aqui como red de seguridad.
(function ensureModuleStyles() {
  const id = 'visor-mysql-css';
  const version = '20260611b';
  const href = '/static/css/visor_mysql.css?v=' + version;
  let link = document.getElementById(id);
  if (link) {
    if (!link.getAttribute('href')?.includes(version)) {
      link.setAttribute('href', href);
    }
    return;
  }
  link = document.createElement('link');
  link.id = id;
  link.rel = 'stylesheet';
  link.href = href;
  document.head.appendChild(link);
})();

(() => {
  const RX = {
    table: (window.IX_BOOT && window.IX_BOOT.table) || "raw", // Siempre usar tabla raw por defecto
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
    
    // Escapar HTML para evitar inyeccion
    const escapeAttr = (s) => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
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
      return `<span title="${escapeAttr(str)}">${escapeAttr(str.substring(0, 50))}...</span>`;
    }
    
    return escapeAttr(str);
  }

  function render() {
    const thead = $("ix-thead");
    const tbody = $("ix-tbody");
    const table = $("ix-table");
    
    if (!RX.columns.length) {
      thead.innerHTML = '<tr><th>Sin columnas</th></tr>';
      tbody.innerHTML = '<tr><td>Sin datos</td></tr>';
      return;
    }
    
    // Generar encabezados
    const escapeAttr = (s) => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const headerCells = RX.columns.map(col => `<th title="${escapeAttr(col)}">${escapeAttr(col)}</th>`).join("");
    thead.innerHTML = `<tr>${headerCells}</tr>`;
    if (table && window.MesColumnResizer) {
      window.MesColumnResizer.setup({
        table,
        wrap: "#ix-table-wrap",
        storageKeyPrefix: `ix-column-widths:${RX.table}`,
        defaultWidth(label, index) {
          const normalized = String(label || "").toLowerCase();
          if (index === 0 || normalized.includes("part_no")) return 150;
          if (normalized.includes("sub_assy")) return 170;
          if (normalized.includes("model")) return 165;
          if (normalized.includes("project")) return 145;
          if (normalized.includes("main")) return 135;
          if (normalized.includes("cantidad")) return 126;
          if (normalized.includes("persona")) return 118;
          if (normalized.includes("usuario")) return 112;
          if (normalized.includes("hash")) return 155;
          return 96;
        },
        minWidth(label, index) {
          const normalized = String(label || "").toLowerCase();
          if (index === 0 || normalized.includes("part_no")) return 118;
          if (normalized.includes("sub_assy")) return 125;
          if (normalized.includes("model")) return 118;
          if (normalized.includes("project")) return 105;
          if (normalized.includes("hash")) return 110;
          return 72;
        },
      });
    }
    
    // Generar filas con doble click para editar
    if (RX.rows.length > 0) {
      const bodyRows = RX.rows.map((row, index) => {
        const cells = RX.columns.map(col => {
          const value = row[col];
          const displayValue = formatCellValue(value, col);
          const rawText = String(value === null || value === undefined ? '' : value);
          const fullText = rawText.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          
          // Agregar data-full-text solo si el texto es largo
          const dataAttr = rawText.length > 50 ? `data-full-text="${fullText}"` : '';
          
          return `<td ${dataAttr}>${displayValue}</td>`;
        }).join("");
        
        // Obtener ID del registro para la funcionalidad de eliminación
        const recordId = row._recordId || null;
        
        return `<tr data-row-index="${index}" data-record-id="${recordId || ''}" style="cursor: pointer;" ondblclick="abrirModalEdicion(this)" title="Doble click para editar">${cells}</tr>`;
      }).join("");
      
      tbody.innerHTML = bodyRows;
    } else {
      tbody.innerHTML = `<tr><td class="ix-no-data" colspan="${RX.columns.length}">Sin modelos para mostrar.</td></tr>`;
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

  // Asignar lineas permitidas (Plan Proyectado) a toda una familia en raw
  async function asignarLineasFamilia() {
    const sugerida = (RX.search || "").trim().toUpperCase().slice(0, 9);
    let familia = prompt(
      "Familia (inicio del numero de parte, ej. EBR807574).\n" +
      "Aplica a TODAS las partes que empiecen igual:",
      sugerida
    );
    if (familia === null || !familia.trim()) return;
    familia = familia.trim().toUpperCase();

    const filaActual = (RX.allRows || []).find(
      (r) => String(r.part_no || "").trim().toUpperCase().startsWith(familia) && r.lineas_permitidas
    );
    const lineas = prompt(
      "Lineas donde puede correr la familia " + familia +
      ", separadas por coma (ej. M1,M2,M4).\nVacio = cualquier linea:",
      filaActual ? filaActual.lineas_permitidas : ""
    );
    if (lineas === null) return;

    try {
      const resp = await fetch("/api/mysql/familia-lineas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ familia: familia, lineas: lineas }),
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || "Error");
      alert("Familia " + data.familia + ": " + (data.lineas || "cualquier linea") +
        "\nAplicado a " + data.partes + " partes.");
      refreshAll();
    } catch (e) {
      alert("Error: " + (e.message || e));
    }
  }

  // Bindear event listeners a los elementos del fragment.
  // Idempotente: usa dataset.boundVisor para no duplicar al re-inicializar.
  function bindVisorListeners() {
    const refreshBtn = $("ix-refresh");
    const registerBtn = $("ix-register");
    const familiaBtn = $("ix-familia-lineas");
    const searchInput = $("ix-search");

    if (refreshBtn && refreshBtn.dataset.boundVisor !== "true") {
      refreshBtn.addEventListener("click", () => {
        RX.offset = 0;
        refreshAll();
      });
      refreshBtn.dataset.boundVisor = "true";
    }

    if (registerBtn && registerBtn.dataset.boundVisor !== "true") {
      registerBtn.addEventListener("click", () => {
        abrirModalRegistro();
      });
      registerBtn.dataset.boundVisor = "true";
    }

    if (familiaBtn && familiaBtn.dataset.boundVisor !== "true") {
      familiaBtn.addEventListener("click", () => {
        asignarLineasFamilia();
      });
      familiaBtn.dataset.boundVisor = "true";
    }

    if (searchInput && searchInput.dataset.boundVisor !== "true") {
      searchInput.addEventListener("input", (e) => {
        RX.search = e.target.value.trim();
        applyLocalFilter();
        render();
      });
      searchInput.dataset.boundVisor = "true";
    }
  }

  // Keyboard shortcuts (global, bind solo una vez)
  if (!window.__visorMysqlKeyboardBound) {
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
          case 'r':
            e.preventDefault();
            if (typeof window.refreshAll === "function") window.refreshAll();
            break;
          case 'f':
            e.preventDefault();
            const searchEl = $("ix-search");
            if (searchEl) searchEl.focus();
            break;
        }
      }
    });
    window.__visorMysqlKeyboardBound = true;
  }

  // Inicializacion expuesta global para que ejecutarScriptsDinamicos no
  // sea necesario para re-disparar la carga. Cada vez que se inyecta el
  // fragment via AJAX, el callback de mostrarControlModelosVisor llama
  // esta funcion, lo que re-bindea los listeners (idempotente) y dispara
  // refreshAll() en los nuevos elementos del DOM.
  window.inicializarControlModelosVisorAjax = async function () {
    try {
      let modalReady = false;
      let attempts = 0;
      const maxAttempts = 50;

      while (!modalReady && attempts < maxAttempts) {
        if (window.rawEditModal) {
          modalReady = true;
        } else {
          await new Promise(resolve => setTimeout(resolve, 100));
          attempts++;
        }
      }

      bindVisorListeners();
      await refreshAll();

      setStatus("Visor MySQL listo - Ctrl+R para actualizar, Ctrl+F para buscar");
    } catch (error) {
      console.error('Initialization error:', error);
      setStatus(`Error de inicialización: ${error.message}`, 'error');
    }
  };

  // Auto-init la primera vez que se carga el script (cubre tanto la carga
  // standalone /visor-mysql como la primera carga del fragment AJAX).
  window.inicializarControlModelosVisorAjax();

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
    /* Modal de Edicion RAW - estilo alineado con ICT */
    .raw-edit-modal {
      position: fixed !important;
      top: 50% !important;
      left: 50% !important;
      transform: translate(-50%, -50%) scale(0.7) !important;
      width: min(920px, 96vw) !important;
      max-width: 920px !important;
      max-height: 90vh !important;
      background: linear-gradient(135deg, var(--ilsan-dark-secondary, #40424f) 0%, #2d2d3f 100%) !important;
      border: 1px solid rgba(255, 255, 255, 0.1) !important;
      z-index: 9999999 !important;
      display: none !important;
      flex-direction: column !important;
      font-family: "LG regular", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
      opacity: 0 !important;
      transition: opacity 0.2s ease, transform 0.2s ease !important;
      border-radius: 16px !important;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6) !important;
      overflow: hidden !important;
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
      backdrop-filter: blur(6px) !important;
    }

    .modal-overlay.active {
      display: block !important;
      opacity: 1 !important;
    }

    .raw-edit-modal .modal-header {
      background: rgba(255, 255, 255, 0.02) !important;
      color: var(--ilsan-text-light, #f3f6fb) !important;
      padding: 16px 20px !important;
      display: flex !important;
      justify-content: space-between !important;
      align-items: center !important;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    .raw-edit-modal .modal-header h3 {
      margin: 0 !important;
      font-size: 1rem !important;
      font-weight: 700 !important;
      color: var(--ilsan-text-light, #f3f6fb) !important;
    }

    .btn-close-modal {
      background: rgba(231, 76, 60, 0.1) !important;
      border: 1px solid rgba(231, 76, 60, 0.3) !important;
      color: #e74c3c !important;
      font-size: 14px !important;
      cursor: pointer !important;
      padding: 0 !important;
      border-radius: 8px !important;
      transition: background-color 0.2s ease, transform 0.2s ease !important;
      width: 32px !important;
      height: 32px !important;
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
    }

    .btn-close-modal:hover {
      background: rgba(231, 76, 60, 0.2) !important;
      transform: rotate(90deg) !important;
    }

    .raw-edit-modal .modal-body {
      flex: 1 !important;
      overflow-y: auto !important;
      padding: 16px 20px !important;
      background: transparent !important;
    }

    .form-fields {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
    }

    .form-group {
      display: flex;
      flex-direction: column;
    }

    .form-label {
      color: var(--ilsan-text-light, #f3f6fb);
      margin-bottom: 5px;
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.3px;
      text-transform: uppercase;
    }

    .raw-edit-modal .form-control {
      background: rgba(255, 255, 255, 0.03) !important;
      border: 1px solid rgba(255, 255, 255, 0.1) !important;
      color: var(--ilsan-text-light, #f3f6fb) !important;
      padding: 6px 8px !important;
      border-radius: 5px !important;
      font-size: 0.8rem !important;
      height: 32px !important;
      transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease !important;
    }

    .raw-edit-modal .form-control:focus {
      outline: none;
      border-color: var(--ilsan-accent-blue, #3498db) !important;
      background: rgba(255, 255, 255, 0.05) !important;
      box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.15) !important;
    }

    .form-control::placeholder {
      color: #718096;
    }

    .raw-edit-modal .form-control.readonly-field {
      background: rgba(0, 0, 0, 0.18) !important;
      border-color: rgba(255, 255, 255, 0.06) !important;
      color: var(--ilsan-text-gray, #95a5a6) !important;
      cursor: not-allowed;
    }

    .form-control.readonly-field:focus {
      border-color: #4a5568;
      box-shadow: none;
    }

    .raw-edit-modal .form-control.numeric-field {
      border-left: 3px solid var(--ilsan-accent-blue, #3498db) !important;
    }

    .raw-edit-modal .modal-footer {
      background: rgba(255, 255, 255, 0.02) !important;
      padding: 14px 20px 18px !important;
      border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
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
      min-height: 34px;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 700;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      border: none;
      cursor: pointer;
    }

    .modal-footer .btn-secondary {
      background: rgba(255, 255, 255, 0.1);
      color: #ffffff;
      border: 0;
    }

    .modal-footer .btn-secondary:hover {
      transform: translateY(-1px);
      background: rgba(255, 255, 255, 0.16);
    }

    .modal-footer .btn-primary {
      background: linear-gradient(135deg, var(--ilsan-accent-blue, #3498db) 0%, var(--ilsan-accent-dark-blue, #20688c) 100%);
      color: #ffffff;
      border: 0;
    }

    .modal-footer .btn-primary:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(52, 152, 219, 0.3);
    }

    .modal-footer .btn-danger {
      background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
      color: #fff;
      border: 0;
    }

    .modal-footer .btn-danger:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(231, 76, 60, 0.28);
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
      background: var(--ilsan-dark-header, #172a46);
    }

    .modal-body::-webkit-scrollbar-thumb {
      background: linear-gradient(180deg, var(--ilsan-accent-blue, #3498db), var(--ilsan-accent-dark-blue, #20688c));
      border-radius: 10px;
    }

    .modal-body::-webkit-scrollbar-thumb:hover {
      background: var(--ilsan-accent-blue, #3498db);
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
    
    // Escapar HTML para atributos de forma segura
    const escapeHtml = (str) => {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    };
    
    Object.keys(data).forEach(key => {
      // Excluir campos de metadatos
      if (key.startsWith('_')) return;
      
      // Usar comparacion estricta para no perder valores como 0
      const rawValue = data[key];
      const value = (rawValue === null || rawValue === undefined || rawValue === '') ? '' : String(rawValue);
      const isReadonly = readonlyFields.includes(key);
      const isNumeric = numericFields.includes(key);
      const readonlyAttr = isReadonly ? 'readonly' : '';
      const readonlyClass = isReadonly ? 'readonly-field' : '';
      const numericClass = isNumeric ? 'numeric-field' : '';
      const readonlyLabel = isReadonly ? ' (Solo lectura)' : '';
      const numericLabel = isNumeric ? ' (Numérico)' : '';
      
      const fieldHTML = `
        <div class="form-group">
          <label class="form-label">${escapeHtml(key)}${readonlyLabel}${numericLabel}</label>
          <input 
            type="text" 
            class="form-control ${readonlyClass} ${numericClass}" 
            name="${key}" 
            value="${escapeHtml(value)}"
            placeholder="Ingrese ${escapeHtml(key)}"
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
