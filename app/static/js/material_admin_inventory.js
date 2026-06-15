(function () {
  const STYLE_ID = "material-admin-inventory-css";
  const STATIC_VERSION = "20260615a";
  const STYLE_HREF = `/static/css/material_admin_inventory.css?v=${STATIC_VERSION}`;
  const COLUMN_WIDTHS_PREFIX = "materialAdminColumnWidths:";
  const COLUMN_FILTERS_PREFIX = "materialAdminColumnFilters:";
  const ROW_NUMBER_FIELD = "__row_number";
  const MIN_COLUMN_WIDTH = 64;
  const tableCache = new Map();

  const inventoryState = {
    view: "summary",
    limit: 500,
    offset: 0,
    total: 0,
  };

  // historyStates: un estado por tipo (entradas/salidas/retornos).
  // Cada tipo es una pestaña independiente con su propio paginado.
  const historyStates = {
    entradas: { limit: 500, offset: 0, total: 0 },
    salidas: { limit: 500, offset: 0, total: 0 },
    retornos: { limit: 500, offset: 0, total: 0 },
  };
  function getHistoryState(tipo) {
    if (!historyStates[tipo]) {
      historyStates[tipo] = { limit: 500, offset: 0, total: 0 };
    }
    return historyStates[tipo];
  }
  // Helper: construye un ID interno sufijado por tipo.
  function H(tipo, suffix) {
    return `mat-admin-history-${suffix}-${tipo}`;
  }
  // Extrae el tipo de un ID con formato mat-admin-history-<suffix>-<tipo>
  function tipoFromElementId(id) {
    if (!id) return null;
    const match = id.match(/^mat-admin-history-(?:[a-z-]+)-(entradas|salidas|retornos)$/);
    return match ? match[1] : null;
  }
  let columnFilterReloadTimer = null;

  const historyTitles = {
    entradas: "Historial de entradas",
    salidas: "Historial de salidas",
    retornos: "Historial de retornos",
  };

  const inventoryColumns = {
    summaryBase: [
      ["numero_parte_base", "Numero de parte"],
      ["version", "Version"],
      ["especificacion", "Especificacion"],
      ["ubicacion", "Ubicacion"],
      ["unidad_medida", "Unidad"],
    ],
    summaryMovement: [
      ["total_entrada", "Entradas"],
      ["total_salida", "Salidas"],
    ],
    summaryTotals: [
      ["stock_total", "Stock total"],
      ["lotes_distintos", "Lotes"],
      ["lotes_con_stock", "Lotes con stock"],
    ],
    detail: [
      ["numero_parte_base", "Numero de parte"],
      ["version", "Version"],
      ["numero_lote", "Lote"],
      ["codigo_material_recibido", "Codigo recibido"],
      ["especificacion", "Especificacion"],
      ["ubicacion", "Ubicacion"],
      ["in_quarantine", "Cuarentena"],
      ["unidad_medida", "Unidad"],
      ["total_entrada", "Total entrada"],
      ["total_salida", "Total salida"],
      ["stock_actual", "Stock actual"],
      ["fecha_recibo", "Fecha recibo"],
      ["fecha_salida", "Fecha salida"],
      ["usuario_entrada", "Usuario entrada"],
      ["usuario_salida", "Usuario salida"],
    ],
  };

  const historyColumns = {
    entradas: [
      ["numero_parte", "Numero de parte"],
      ["especificacion", "Especificacion"],
      ["codigo_material_recibido", "Codigo recibido"],
      ["numero_lote_material", "Lote"],
      ["numero_invoice", "Invoice"],
      ["iqc_status", "IQC Status"],
      ["in_quarantine", "Cuarentena"],
      ["cantidad_actual", "Cantidad"],
      ["cantidad_estandarizada", "Unidad empaque"],
      ["location", "Ubicacion"],
      ["fecha_recibo", "Fecha recibo"],
      ["fecha_recibo_hora", "Hora"],
      ["vendedor", "Vendedor"],
      ["costo_unitario", "Costo unit."],
      ["costo_total", "Costo total"],
      ["moneda_costo", "Moneda"],
      ["cancelado", "Cancelado"],
      ["usuario_registro", "Registrado por"],
    ],
    salidas: [
      ["fecha_salida", "Fecha salida"],
      ["fecha_salida_hora", "Hora"],
      ["proceso_salida", "Proceso salida"],
      ["codigo_material_recibido", "Codigo recibido"],
      ["material_code", "Codigo material"],
      ["numero_parte", "Numero de parte"],
      ["cantidad_salida", "Cantidad"],
      ["numero_lote", "Lote"],
      ["especificacion_material", "Especificacion"],
      ["depto_salida", "Depto"],
      ["vendedor", "Vendedor"],
      ["usuario_registro", "Registrado por"],
    ],
    retornos: [
      ["fecha_creacion", "Fecha retorno"],
      ["warehousing_code", "Codigo recibido"],
      ["material_code", "Codigo material"],
      ["numero_parte", "Numero de parte"],
      ["numero_lote_material", "Lote"],
      ["packaging_unit", "Unidad empaque"],
      ["cantidad_devuelta", "Cantidad"],
      ["material_spec", "Especificacion"],
      ["descripcion_motivo", "Motivo"],
    ],
  };

  function getInventoryColumns(view) {
    if (view === "detail") return inventoryColumns.detail;
    const columns = [...inventoryColumns.summaryBase];
    if (el("mat-admin-inv-use-date")?.checked) {
      columns.push(...inventoryColumns.summaryMovement);
    }
    columns.push(...inventoryColumns.summaryTotals);
    return columns;
  }

  function ensureModuleStyles() {
    const current = document.getElementById(STYLE_ID);
    if (current) {
      if (!current.getAttribute("href")?.includes(STATIC_VERSION)) {
        current.setAttribute("href", STYLE_HREF);
      }
      return;
    }

    const link = document.createElement("link");
    link.id = STYLE_ID;
    link.rel = "stylesheet";
    link.href = STYLE_HREF;
    document.head.appendChild(link);
  }

  function el(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatNumber(value) {
    if (value === null || value === undefined || value === "") return "";
    const n = Number(value);
    if (!Number.isFinite(n)) return escapeHtml(value);
    return n.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }

  // Costos: 4 decimales. Vacio ('') cuando el lote aun no tiene costo aplicado.
  function formatMoney(value) {
    if (value === null || value === undefined || value === "") return "";
    const n = Number(value);
    if (!Number.isFinite(n)) return escapeHtml(value);
    return n.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  }

  function isMoneyField(field) {
    return field === "costo_unitario" || field === "costo_total";
  }

  function todayIso() {
    return new Date().toISOString().slice(0, 10);
  }

  function monthStartIso() {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
  }

  function setMessage(id, message) {
    const box = el(id);
    if (!box) return;
    if (!message) {
      box.hidden = true;
      box.textContent = "";
      return;
    }
    box.hidden = false;
    box.textContent = message;
  }

  function setLoading(id, active) {
    const loader = el(id);
    if (loader) loader.classList.toggle("active", active);
  }

  function removeLegacyPageHeaders(rootId) {
    const root = el(rootId);
    root?.querySelectorAll(":scope > .mat-admin-header").forEach((header) => header.remove());
  }

  function storageKey(tableKey) {
    return `${COLUMN_WIDTHS_PREFIX}${tableKey}`;
  }

  function filterStorageKey(tableKey) {
    return `${COLUMN_FILTERS_PREFIX}${tableKey}`;
  }

  function loadColumnWidths(tableKey) {
    try {
      return JSON.parse(localStorage.getItem(storageKey(tableKey)) || "{}");
    } catch (err) {
      console.warn("No se pudieron cargar anchos de columnas:", err);
      return {};
    }
  }

  function saveColumnWidths(tableKey, widths) {
    try {
      localStorage.setItem(storageKey(tableKey), JSON.stringify(widths));
    } catch (err) {
      console.warn("No se pudieron guardar anchos de columnas:", err);
    }
  }

  function loadColumnFilters(tableKey) {
    try {
      return JSON.parse(localStorage.getItem(filterStorageKey(tableKey)) || "{}");
    } catch (err) {
      console.warn("No se pudieron cargar filtros de columnas:", err);
      return {};
    }
  }

  function saveColumnFilters(tableKey, filters) {
    try {
      localStorage.setItem(filterStorageKey(tableKey), JSON.stringify(filters));
    } catch (err) {
      console.warn("No se pudieron guardar filtros de columnas:", err);
    }
  }

  function appendColumnFilters(params, tableKey) {
    const filters = loadColumnFilters(tableKey);
    Object.entries(filters).forEach(([field, value]) => {
      const cleanValue = String(value || "").trim();
      if (!cleanValue || field === ROW_NUMBER_FIELD) return;
      params.set(`cf_${field}`, cleanValue);
    });
  }

  function setColumnFilter(tableKey, field, value) {
    const filters = loadColumnFilters(tableKey);
    const cleanValue = String(value || "").trim();
    if (cleanValue) {
      filters[field] = cleanValue;
    } else {
      delete filters[field];
    }
    saveColumnFilters(tableKey, filters);
  }

  function clearColumnFiltersByPrefix(prefix) {
    try {
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith(`${COLUMN_FILTERS_PREFIX}${prefix}`)) {
          localStorage.removeItem(key);
        }
      });
    } catch (err) {
      console.warn("No se pudieron limpiar filtros de columnas:", err);
    }
  }

  function defaultColumnWidth(field, label) {
    if (field === ROW_NUMBER_FIELD) return MIN_COLUMN_WIDTH;
    const fixedWidths = {
      fecha_recibo: 150,
      fecha_salida: 150,
      fecha_creacion: 150,
      fecha_recibo_hora: 82,
      fecha_salida_hora: 82,
      cantidad_actual: 96,
      cantidad_salida: 96,
      cantidad_devuelta: 96,
      cantidad_estandarizada: 118,
      unidad_medida: 78,
      in_quarantine: 92,
      cancelado: 86,
      stock_actual: 105,
      stock_total: 105,
      total_entrada: 108,
      total_salida: 108,
      lotes_distintos: 92,
      lotes_con_stock: 116,
      costo_unitario: 104,
      costo_total: 116,
      moneda_costo: 76,
    };
    if (fixedWidths[field]) return fixedWidths[field];
    if (field.includes("codigo") || field.includes("warehousing")) return 172;
    if (field.includes("numero_parte") || field === "material_code") return 140;
    if (field.includes("lote")) return 160;
    if (field.includes("especificacion") || field.includes("spec")) return 230;
    if (field.includes("usuario") || field.includes("vendedor")) return 132;
    if (field.includes("ubicacion") || field === "location") return 120;
    return Math.max(MIN_COLUMN_WIDTH, Math.min(220, 52 + String(label || field).length * 8));
  }

  function withRowNumberColumn(columns) {
    if ((columns || [])[0]?.[0] === ROW_NUMBER_FIELD) return columns || [];
    return [[ROW_NUMBER_FIELD, "No."], ...(columns || [])];
  }

  function rowNumberOffset(tableKey) {
    if (tableKey.startsWith("history:")) {
      const tipo = tableKey.split(":")[1];
      return getHistoryState(tipo).offset;
    }
    if (tableKey.startsWith("inventory:detail")) return inventoryState.offset;
    return 0;
  }

  function getColumnWidths(tableKey, columns) {
    const saved = loadColumnWidths(tableKey);
    const widths = {};
    columns.forEach(([field, label]) => {
      const savedWidth = Number(saved[field]);
      widths[field] = Number.isFinite(savedWidth) && savedWidth >= MIN_COLUMN_WIDTH
        ? savedWidth
        : defaultColumnWidth(field, label);
    });
    return widths;
  }

  function fitWidthsToContainer(table, columns, widths) {
    const wrap = table?.closest(".mat-admin-grid-wrap");
    const availableWidth = Math.floor((wrap?.clientWidth || 0) - 2);
    const minTotal = columns.length * MIN_COLUMN_WIDTH;
    const currentTotal = columns.reduce((sum, [field]) => {
      return sum + Math.max(MIN_COLUMN_WIDTH, Number(widths[field]) || MIN_COLUMN_WIDTH);
    }, 0);

    if (!availableWidth || currentTotal <= 0) return widths;
    if (availableWidth < minTotal) return widths;

    const targetTotal = Math.max(availableWidth, minTotal);
    const ratio = targetTotal / currentTotal;
    const fitted = {};
    let fittedTotal = 0;

    columns.forEach(([field]) => {
      const nextWidth = Math.max(MIN_COLUMN_WIDTH, Math.round((Number(widths[field]) || MIN_COLUMN_WIDTH) * ratio));
      fitted[field] = nextWidth;
      fittedTotal += nextWidth;
    });

    const lastField = columns[columns.length - 1]?.[0];
    if (lastField && fittedTotal !== targetTotal) {
      fitted[lastField] = Math.max(MIN_COLUMN_WIDTH, fitted[lastField] + targetTotal - fittedTotal);
    }

    return fitted;
  }

  function applyColumnWidths(table, columns, widths, options = {}) {
    if (!table) return;
    const oldColgroup = table.querySelector("colgroup");
    if (oldColgroup) oldColgroup.remove();

    const activeWidths = options.fitToContainer === false ? widths : fitWidthsToContainer(table, columns, widths);
    const colgroup = document.createElement("colgroup");
    let totalWidth = 0;
    columns.forEach(([field]) => {
      const width = Math.max(MIN_COLUMN_WIDTH, Number(activeWidths[field]) || MIN_COLUMN_WIDTH);
      totalWidth += width;
      const col = document.createElement("col");
      col.dataset.field = field;
      col.style.width = `${width}px`;
      colgroup.appendChild(col);
    });

    table.insertBefore(colgroup, table.firstChild);
    table.style.width = "100%";
    table.style.minWidth = `${totalWidth}px`;
  }

  function readRenderedColumnWidths(table, columns) {
    const widths = {};
    columns.forEach(([field, label]) => {
      const renderedWidth = table.querySelector(`col[data-field="${CSS.escape(field)}"]`)?.getBoundingClientRect().width;
      widths[field] = Number.isFinite(renderedWidth) && renderedWidth >= MIN_COLUMN_WIDTH
        ? Math.round(renderedWidth)
        : defaultColumnWidth(field, label);
    });
    return widths;
  }

  function resizeColumnsWithCompensation(columns, startWidths, field, desiredWidth) {
    const widths = { ...startWidths };
    const oldWidth = Math.max(MIN_COLUMN_WIDTH, Number(startWidths[field]) || MIN_COLUMN_WIDTH);
    const nextWidth = Math.max(MIN_COLUMN_WIDTH, Math.round(desiredWidth));
    const delta = nextWidth - oldWidth;
    widths[field] = nextWidth;

    if (delta > 0) {
      let remaining = delta;
      const fieldIndex = columns.findIndex(([columnField]) => columnField === field);
      const candidates = [
        ...columns.slice(fieldIndex + 1),
        ...columns.slice(0, fieldIndex),
      ];

      candidates.forEach(([candidateField]) => {
        if (remaining <= 0 || candidateField === field) return;
        const candidateWidth = Math.max(MIN_COLUMN_WIDTH, Number(widths[candidateField]) || MIN_COLUMN_WIDTH);
        const reducible = Math.max(0, candidateWidth - MIN_COLUMN_WIDTH);
        const reduction = Math.min(reducible, remaining);
        widths[candidateField] = candidateWidth - reduction;
        remaining -= reduction;
      });
      return widths;
    }

    if (delta < 0) {
      const fieldIndex = columns.findIndex(([columnField]) => columnField === field);
      const receiver = columns[fieldIndex + 1]?.[0] || columns[fieldIndex - 1]?.[0];
      if (receiver) {
        widths[receiver] = Math.max(MIN_COLUMN_WIDTH, Number(widths[receiver]) || MIN_COLUMN_WIDTH) + Math.abs(delta);
      }
    }

    return widths;
  }

  function filterRows(tableKey, columns, rows) {
    const filters = loadColumnFilters(tableKey);
    const activeFilters = columns
      .map(([field]) => [field, String(filters[field] || "").toLowerCase()])
      .filter(([, value]) => value);

    if (!activeFilters.length) return rows || [];

    return (rows || []).filter((row) => {
      return activeFilters.every(([field, value]) => {
        const cellValue = String(getCellValue(row, field) ?? "").toLowerCase();
        return cellValue.includes(value);
      });
    });
  }

  function renderTableBody(bodyId, columns, rows, tableKey, onRender) {
    const body = el(bodyId);
    if (!body) return 0;
    const visibleRows = filterRows(tableKey, columns, rows);
    const cached = tableCache.get(tableKey);
    if (cached) cached.visibleRows = visibleRows;

    if (!visibleRows.length) {
      body.innerHTML = `<tr><td class="mat-admin-empty" colspan="${columns.length}">No hay registros disponibles.</td></tr>`;
      if (typeof onRender === "function") onRender(0, (rows || []).length);
      return 0;
    }

    body.innerHTML = visibleRows.map((row, rowIndex) => {
      return `<tr data-row-index="${rowIndex}">${columns.map(([field]) => {
        if (field === ROW_NUMBER_FIELD) {
          return `<td data-field="${ROW_NUMBER_FIELD}" class="mat-admin-row-number">${rowNumberOffset(tableKey) + rowIndex + 1}</td>`;
        }
        const rawValue = getCellValue(row, field);
        const value = isMoneyField(field)
          ? formatMoney(rawValue)
          : (isNumericField(field) ? formatNumber(rawValue) : escapeHtml(rawValue));
        const canDrilldown = tableKey.startsWith("inventory:summary") && (field === "numero_parte" || field === "numero_parte_base");
        const className = canDrilldown ? " class=\"mat-admin-drilldown-cell\"" : "";
        const title = canDrilldown ? "Doble clic para ver detalle" : rawValue;
        return `<td data-field="${escapeHtml(field)}"${className} title="${escapeHtml(title)}">${value}</td>`;
      }).join("")}</tr>`;
    }).join("");

    if (typeof onRender === "function") onRender(visibleRows.length, (rows || []).length);
    return visibleRows.length;
  }

  function renderCachedTableBody(tableKey) {
    const cached = tableCache.get(tableKey);
    if (!cached) return;
    renderTableBody(cached.bodyId, cached.columns, cached.rows, tableKey, cached.onRender);
  }

  function renderTable(headId, bodyId, columns, rows, tableKey, onRender) {
    const head = el(headId);
    const body = el(bodyId);
    if (!head || !body) return;
    const displayColumns = withRowNumberColumn(columns);
    const table = head.closest("table");
    const widths = getColumnWidths(tableKey, displayColumns);
    const filters = loadColumnFilters(tableKey);
    tableCache.set(tableKey, { headId, bodyId, columns: displayColumns, rows: rows || [], onRender });

    if (table) {
      table.dataset.tableKey = tableKey;
      applyColumnWidths(table, displayColumns, widths);
    }

    head.innerHTML = `<tr>${displayColumns.map(([field, label]) => {
      if (field === ROW_NUMBER_FIELD) {
        return `<th class="mat-admin-row-number-head" data-field="${ROW_NUMBER_FIELD}">
          <div class="mat-admin-header-cell">
            <span class="mat-admin-th-label">${escapeHtml(label)}</span>
          </div>
          <span class="mat-admin-col-resizer" role="separator" aria-label="Ajustar columna" title="Arrastra para ajustar. Doble clic para restablecer."></span>
        </th>`;
      }
      const filterValue = filters[field] || "";
      const activeClass = filterValue ? " active" : "";
      return `<th class="mat-admin-filterable" data-field="${escapeHtml(field)}">
        <div class="mat-admin-header-cell">
          <span class="mat-admin-th-label">${escapeHtml(label)}</span>
          <button type="button" class="mat-admin-filter-btn${activeClass}" data-field="${escapeHtml(field)}" title="Filtrar ${escapeHtml(label)}">▼</button>
        </div>
        <div class="mat-admin-header-filter" data-field="${escapeHtml(field)}">
          <input class="mat-admin-filter-input" data-field="${escapeHtml(field)}" value="${escapeHtml(filterValue)}" placeholder="Buscar..." autocomplete="off">
          <div class="mat-admin-filter-actions">
            <button type="button" class="mat-admin-filter-clear-col" data-field="${escapeHtml(field)}">Limpiar</button>
            <button type="button" class="mat-admin-filter-clear-all">Todos</button>
          </div>
        </div>
        <span class="mat-admin-col-resizer" role="separator" aria-label="Ajustar columna" title="Arrastra para ajustar. Doble clic para restablecer."></span>
      </th>`;
    }).join("")}</tr>`;
    renderTableBody(bodyId, displayColumns, rows || [], tableKey, onRender);
  }

  function isNumericField(field) {
    return field.includes("cantidad") || field.includes("stock") || field.startsWith("total_") || field.startsWith("lotes_");
  }

  function getCellValue(row, field) {
    if (field === "in_quarantine") {
      const value = row.in_quarantine ?? row.en_cuarentena;
      return value === 1 || value === "1" || value === true ? "Si" : "No";
    }
    if (field === "cancelado") {
      const value = row.cancelado;
      return value === 1 || value === "1" || value === true ? "Si" : "No";
    }
    if (field.endsWith("_hora") && !row[field]) {
      const sourceField = field.replace("_hora", "");
      const rawDate = String(row[sourceField] ?? "");
      return rawDate.includes(" ") ? rawDate.split(" ")[1].slice(0, 8) : "";
    }
    return row[field] ?? "";
  }

  function inventoryTableKey(view = inventoryState.view) {
    return `inventory:${view}:${el("mat-admin-inv-use-date")?.checked ? "range" : "current"}`;
  }

  function inventoryQueryParams(tableKey = null) {
    const params = new URLSearchParams();
    const part = el("mat-admin-inv-part")?.value.trim();
    const label = el("mat-admin-inv-label")?.value.trim();
    const location = el("mat-admin-inv-location")?.value.trim();
    const includeZero = el("mat-admin-inv-include-zero")?.checked;
    const onlyNa = el("mat-admin-inv-only-na")?.checked;
    const useDate = el("mat-admin-inv-use-date")?.checked;

    if (part) params.set("numero_parte", part);
    if (label) params.set("codigo_material_recibido", label);
    if (location) params.set("ubicacion", location);
    if (includeZero) params.set("include_zero_stock", "true");
    if (onlyNa) params.set("only_na", "true");
    if (useDate) {
      const start = el("mat-admin-inv-start")?.value;
      const end = el("mat-admin-inv-end")?.value;
      if (start && end) {
        params.set("fecha_inicio", start);
        params.set("fecha_fin", end);
      }
    }
    if (tableKey) appendColumnFilters(params, tableKey);

    return params;
  }

  function syncInventoryControls() {
    const isDetail = inventoryState.view === "detail";
    const useDate = el("mat-admin-inv-use-date")?.checked;
    const labelWrap = el("mat-admin-inv-label-wrap");
    const onlyNaWrap = el("mat-admin-inv-only-na-wrap");
    const pagination = el("mat-admin-inv-pagination");
    const startWrap = el("mat-admin-inv-start-wrap");
    const endWrap = el("mat-admin-inv-end-wrap");

    if (labelWrap) labelWrap.style.display = isDetail ? "flex" : "none";
    if (onlyNaWrap) onlyNaWrap.style.display = isDetail ? "flex" : "none";
    if (pagination) pagination.style.display = isDetail ? "flex" : "none";
    if (startWrap) startWrap.style.display = useDate ? "flex" : "none";
    if (endWrap) endWrap.style.display = useDate ? "flex" : "none";

    el("mat-admin-inv-tab-summary")?.classList.toggle("active", inventoryState.view === "summary");
    el("mat-admin-inv-tab-detail")?.classList.toggle("active", inventoryState.view === "detail");
  }

  async function loadInventory(resetPage = false) {
    ensureModuleStyles();
    syncInventoryControls();
    setMessage("mat-admin-inv-message", "");
    setLoading("mat-admin-inv-loading", true);

    if (resetPage) inventoryState.offset = 0;

    try {
      const tableKey = inventoryTableKey(inventoryState.view);
      const params = inventoryQueryParams(inventoryState.view === "detail" ? tableKey : null);
      let url = "/api/material_admin/inventory/summary";
      if (inventoryState.view === "detail") {
        inventoryState.limit = Number(el("mat-admin-inv-page-size")?.value || 500);
        params.set("limit", String(inventoryState.limit));
        params.set("offset", String(inventoryState.offset));
        url = "/api/material_admin/inventory/lots";
      }

      const res = await fetch(`${url}?${params.toString()}`, { credentials: "same-origin" });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);

      const rows = Array.isArray(data) ? data : data.data || [];
      inventoryState.total = Array.isArray(data) ? rows.length : Number(data.total || rows.length);
      const columns = getInventoryColumns(inventoryState.view);

      renderTable("mat-admin-inv-head", "mat-admin-inv-body", columns, rows, tableKey, (visibleRows, pageRows) => {
        const count = el("mat-admin-inv-count");
        if (!count) return;
        if (inventoryState.view === "detail") {
          const start = inventoryState.total === 0 ? 0 : inventoryState.offset + 1;
          const end = Math.min(inventoryState.offset + rows.length, inventoryState.total);
          const filteredText = visibleRows === pageRows ? "" : `, Filtrado: ${visibleRows}/${pageRows}`;
          count.textContent = `Total Rows: ${inventoryState.total} (${start}-${end}${filteredText})`;
        } else {
          count.textContent = visibleRows === pageRows ? `Total Rows: ${pageRows}` : `Total Rows: ${visibleRows} / ${pageRows}`;
        }
      });

      const page = el("mat-admin-inv-page");
      if (page) {
        const pageNumber = Math.floor(inventoryState.offset / inventoryState.limit) + 1;
        page.textContent = `Pagina ${pageNumber}`;
      }
    } catch (err) {
      console.error("Error cargando inventario actual:", err);
      setMessage("mat-admin-inv-message", `Error al cargar inventario: ${err.message}`);
    } finally {
      setLoading("mat-admin-inv-loading", false);
    }
  }

  async function exportInventory() {
    const tableKey = inventoryTableKey(inventoryState.view);
    const params = inventoryQueryParams(inventoryState.view === "detail" ? tableKey : null);
    params.set("view", inventoryState.view);
    window.location.href = `/api/material_admin/inventory/export?${params.toString()}`;
  }

  function openInventoryDetailForPart(partNumber) {
    const cleanPart = String(partNumber || "").trim();
    if (!cleanPart) return;

    inventoryState.view = "detail";
    inventoryState.offset = 0;

    const partInput = el("mat-admin-inv-part");
    if (partInput) partInput.value = cleanPart;

    const labelInput = el("mat-admin-inv-label");
    if (labelInput) labelInput.value = "";

    clearColumnFiltersByPrefix("inventory:detail:");
    syncInventoryControls();
    loadInventory(true);
  }

  function resetInventoryFilters() {
    ["mat-admin-inv-part", "mat-admin-inv-label", "mat-admin-inv-location"].forEach((id) => {
      const input = el(id);
      if (input) input.value = "";
    });
    ["mat-admin-inv-include-zero", "mat-admin-inv-only-na", "mat-admin-inv-use-date"].forEach((id) => {
      const input = el(id);
      if (input) input.checked = false;
    });
    if (el("mat-admin-inv-start")) el("mat-admin-inv-start").value = monthStartIso();
    if (el("mat-admin-inv-end")) el("mat-admin-inv-end").value = todayIso();
    inventoryState.view = "summary";
    inventoryState.offset = 0;
    clearColumnFiltersByPrefix("inventory:");
    loadInventory(true);
  }

  function historyParams(historyType) {
    const state = getHistoryState(historyType);
    const params = new URLSearchParams();
    const start = el(H(historyType, "start"))?.value;
    const end = el(H(historyType, "end"))?.value;
    const text = el(H(historyType, "text"))?.value.trim();

    if (start) params.set("fecha_inicio", start);
    if (end) params.set("fecha_fin", end);
    if (text) params.set("texto", text);
    state.limit = Number(el(H(historyType, "page-size"))?.value || 500);
    params.set("limit", String(state.limit));
    params.set("offset", String(state.offset));
    appendColumnFilters(params, `history:${historyType}`);
    return params;
  }

  async function loadHistory(tipo, resetPage = false) {
    const historyType = tipo;
    if (!historyType) return;
    const state = getHistoryState(historyType);
    ensureModuleStyles();
    setMessage(H(historyType, "message"), "");
    setLoading(H(historyType, "loading"), true);
    if (resetPage) state.offset = 0;

    try {
      const res = await fetch(`/api/material_admin/history/${encodeURIComponent(historyType)}?${historyParams(historyType).toString()}`, {
        credentials: "same-origin",
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);

      const rows = Array.isArray(data) ? data : data.data || [];
      state.total = Array.isArray(data) ? rows.length : Number(data.total || rows.length);
      state.limit = Array.isArray(data) ? state.limit : Number(data.limit || state.limit);
      state.offset = Array.isArray(data) ? state.offset : Number(data.offset || state.offset);

      renderTable(H(historyType, "head"), H(historyType, "body"), historyColumns[historyType], rows, `history:${historyType}`, (visibleRows, pageRows) => {
        const count = el(H(historyType, "count"));
        if (!count) return;
        const start = state.total === 0 ? 0 : state.offset + 1;
        const end = Math.min(state.offset + pageRows, state.total);
        const filteredText = visibleRows === pageRows ? "" : `, Filtrado: ${visibleRows}/${pageRows}`;
        count.textContent = `Total Rows: ${state.total} (${start}-${end}${filteredText})`;
      });

      const page = el(H(historyType, "page"));
      if (page) {
        const pageNumber = Math.floor(state.offset / state.limit) + 1;
        page.textContent = `Pagina ${pageNumber}`;
      }
    } catch (err) {
      console.error(`Error cargando ${historyType}:`, err);
      setMessage(H(historyType, "message"), `Error al cargar ${historyTitles[historyType] || "historial"}: ${err.message}`);
    } finally {
      setLoading(H(historyType, "loading"), false);
    }
  }

  function exportHistory(historyType) {
    if (!historyType) return;
    window.location.href = `/api/material_admin/history/${encodeURIComponent(historyType)}/export?${historyParams(historyType).toString()}`;
  }

  function reloadForColumnFilter(tableKey) {
    window.clearTimeout(columnFilterReloadTimer);
    columnFilterReloadTimer = window.setTimeout(() => {
      if (tableKey.startsWith("history:")) {
        const tipo = tableKey.split(":")[1];
        getHistoryState(tipo).offset = 0;
        loadHistory(tipo, true);
        return;
      }
      if (tableKey.startsWith("inventory:detail")) {
        inventoryState.offset = 0;
        loadInventory(true);
      }
    }, 300);
  }

  function resetHistoryFilters(historyType) {
    if (!historyType) return;
    const state = getHistoryState(historyType);
    if (el(H(historyType, "start"))) el(H(historyType, "start")).value = todayIso();
    if (el(H(historyType, "end"))) el(H(historyType, "end")).value = todayIso();
    const text = el(H(historyType, "text"));
    if (text) text.value = "";
    state.offset = 0;
    clearColumnFiltersByPrefix(`history:${historyType}`);
    loadHistory(historyType, true);
  }

  function initListeners() {
    if (document.body.dataset.matAdminListenersAttached) return;

    const resizeState = {
      active: false,
      table: null,
      tableKey: "",
      field: "",
      startX: 0,
      startWidth: 0,
      columns: [],
      widths: {},
    };

    function stopResize() {
      if (!resizeState.active) return;
      resizeState.active = false;
      document.body.classList.remove("mat-admin-resizing");
      saveColumnWidths(resizeState.tableKey, resizeState.widths);
    }

    document.body.addEventListener("pointerdown", (event) => {
      const handle = event.target instanceof Element ? event.target.closest(".mat-admin-col-resizer") : null;
      if (!handle) return;

      const th = handle.closest("th");
      const table = th?.closest("table");
      const tableKey = table?.dataset.tableKey;
      const field = th?.dataset.field;
      if (!th || !table || !tableKey || !field) return;

      const columns = Array.from(table.querySelectorAll("thead tr:first-child th")).map((header) => {
        const headerField = header.dataset.field || "";
        const label = header.querySelector(".mat-admin-th-label")?.textContent || headerField;
        return [headerField, label];
      }).filter(([headerField]) => headerField);

      resizeState.active = true;
      resizeState.table = table;
      resizeState.tableKey = tableKey;
      resizeState.field = field;
      resizeState.startX = event.clientX;
      resizeState.startWidth = table.querySelector(`col[data-field="${CSS.escape(field)}"]`)?.getBoundingClientRect().width || th.getBoundingClientRect().width;
      resizeState.columns = columns;
      resizeState.widths = readRenderedColumnWidths(table, columns);

      document.body.classList.add("mat-admin-resizing");
      event.preventDefault();
      event.stopPropagation();
    });

    document.body.addEventListener("pointermove", (event) => {
      if (!resizeState.active || !resizeState.table) return;
      const nextWidth = Math.max(MIN_COLUMN_WIDTH, Math.round(resizeState.startWidth + event.clientX - resizeState.startX));
      resizeState.widths = resizeColumnsWithCompensation(resizeState.columns, resizeState.widths, resizeState.field, nextWidth);
      applyColumnWidths(resizeState.table, resizeState.columns, resizeState.widths, { fitToContainer: false });
      event.preventDefault();
    });

    document.body.addEventListener("pointerup", stopResize);
    document.body.addEventListener("pointercancel", stopResize);

    document.body.addEventListener("dblclick", (event) => {
      const handle = event.target instanceof Element ? event.target.closest(".mat-admin-col-resizer") : null;
      if (!handle) return;
      const th = handle.closest("th");
      const table = th?.closest("table");
      const tableKey = table?.dataset.tableKey;
      const field = th?.dataset.field;
      if (!table || !tableKey || !field) return;

      const columns = Array.from(table.querySelectorAll("thead tr:first-child th")).map((header) => {
        const headerField = header.dataset.field || "";
        const label = header.querySelector(".mat-admin-th-label")?.textContent || headerField;
        return [headerField, label];
      }).filter(([headerField]) => headerField);
      const widths = getColumnWidths(tableKey, columns);
      delete widths[field];
      saveColumnWidths(tableKey, widths);
      applyColumnWidths(table, columns, getColumnWidths(tableKey, columns));
      event.preventDefault();
      event.stopPropagation();
    });

    document.body.addEventListener("dblclick", (event) => {
      const cell = event.target instanceof Element ? event.target.closest("td.mat-admin-drilldown-cell") : null;
      if (!cell) return;
      const table = cell.closest("table");
      const tableKey = table?.dataset.tableKey || "";
      if (!tableKey.startsWith("inventory:summary")) return;

      const rowIndex = Number(cell.closest("tr")?.dataset.rowIndex);
      const row = Number.isInteger(rowIndex) ? tableCache.get(tableKey)?.visibleRows?.[rowIndex] : null;
      const partNumber = row?.numero_parte || row?.numero_parte_base || cell.textContent;
      openInventoryDetailForPart(partNumber);
      event.preventDefault();
      event.stopPropagation();
    });

    document.body.addEventListener("input", (event) => {
      const input = event.target instanceof Element ? event.target.closest(".mat-admin-filter-input") : null;
      if (!input) return;
      const table = input.closest("table");
      const tableKey = table?.dataset.tableKey;
      const field = input.dataset.field;
      if (!tableKey || !field) return;
      setColumnFilter(tableKey, field, input.value);
      input.closest("th")?.querySelector(".mat-admin-filter-btn")?.classList.toggle("active", Boolean(input.value.trim()));
      if (tableKey.startsWith("history:") || tableKey.startsWith("inventory:detail")) {
        reloadForColumnFilter(tableKey);
      } else {
        renderCachedTableBody(tableKey);
      }
    });

    document.body.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;

      const filterButton = target.closest(".mat-admin-filter-btn");
      if (filterButton) {
        event.preventDefault();
        event.stopPropagation();
        const header = filterButton.closest("th");
        const panel = header?.querySelector(".mat-admin-header-filter");
        document.querySelectorAll(".mat-admin-header-filter.open").forEach((filter) => {
          if (filter !== panel) filter.classList.remove("open");
        });
        document.querySelectorAll(".mat-admin-filter-btn.open").forEach((button) => {
          if (button !== filterButton) button.classList.remove("open");
        });
        panel?.classList.toggle("open");
        filterButton.classList.toggle("open", panel?.classList.contains("open"));
        if (panel?.classList.contains("open")) {
          setTimeout(() => panel.querySelector(".mat-admin-filter-input")?.focus(), 0);
        }
        return;
      }

      const clearColumnButton = target.closest(".mat-admin-filter-clear-col");
      if (clearColumnButton) {
        event.preventDefault();
        const table = clearColumnButton.closest("table");
        const tableKey = table?.dataset.tableKey;
        const field = clearColumnButton.dataset.field;
        if (!tableKey || !field) return;
        setColumnFilter(tableKey, field, "");
        const header = clearColumnButton.closest("th");
        const input = header?.querySelector(".mat-admin-filter-input");
        if (input) input.value = "";
        header?.querySelector(".mat-admin-filter-btn")?.classList.remove("active");
        if (tableKey.startsWith("history:") || tableKey.startsWith("inventory:detail")) {
          reloadForColumnFilter(tableKey);
        } else {
          renderCachedTableBody(tableKey);
        }
        return;
      }

      const clearAllButton = target.closest(".mat-admin-filter-clear-all");
      if (clearAllButton) {
        event.preventDefault();
        const table = clearAllButton.closest("table");
        const tableKey = table?.dataset.tableKey;
        if (!tableKey) return;
        saveColumnFilters(tableKey, {});
        table.querySelectorAll(".mat-admin-filter-input").forEach((input) => { input.value = ""; });
        table.querySelectorAll(".mat-admin-filter-btn").forEach((button) => button.classList.remove("active", "open"));
        table.querySelectorAll(".mat-admin-header-filter").forEach((filter) => filter.classList.remove("open"));
        if (tableKey.startsWith("history:") || tableKey.startsWith("inventory:detail")) {
          reloadForColumnFilter(tableKey);
        } else {
          renderCachedTableBody(tableKey);
        }
        return;
      }

      if (!target.closest(".mat-admin-filterable")) {
        document.querySelectorAll(".mat-admin-header-filter.open").forEach((filter) => filter.classList.remove("open"));
        document.querySelectorAll(".mat-admin-filter-btn.open").forEach((button) => button.classList.remove("open"));
      }

      if (target.closest("#mat-admin-inv-btn-search")) {
        event.preventDefault();
        loadInventory(true);
        return;
      }
      if (target.closest("#mat-admin-inv-btn-clear")) {
        event.preventDefault();
        resetInventoryFilters();
        return;
      }
      if (target.closest("#mat-admin-inv-btn-export")) {
        event.preventDefault();
        exportInventory();
        return;
      }
      const invTab = target.closest(".mat-admin-tab");
      if (invTab?.dataset.view) {
        event.preventDefault();
        inventoryState.view = invTab.dataset.view;
        inventoryState.offset = 0;
        loadInventory(true);
        return;
      }
      if (target.closest("#mat-admin-inv-prev")) {
        event.preventDefault();
        inventoryState.offset = Math.max(0, inventoryState.offset - inventoryState.limit);
        loadInventory(false);
        return;
      }
      if (target.closest("#mat-admin-inv-next")) {
        event.preventDefault();
        const nextOffset = inventoryState.offset + inventoryState.limit;
        if (nextOffset < inventoryState.total) {
          inventoryState.offset = nextOffset;
          loadInventory(false);
        }
        return;
      }
      const histSearchBtn = target.closest("[id^='mat-admin-history-btn-search-']");
      if (histSearchBtn) {
        event.preventDefault();
        loadHistory(tipoFromElementId(histSearchBtn.id), true);
        return;
      }
      const histClearBtn = target.closest("[id^='mat-admin-history-btn-clear-']");
      if (histClearBtn) {
        event.preventDefault();
        resetHistoryFilters(tipoFromElementId(histClearBtn.id));
        return;
      }
      const histExportBtn = target.closest("[id^='mat-admin-history-btn-export-']");
      if (histExportBtn) {
        event.preventDefault();
        exportHistory(tipoFromElementId(histExportBtn.id));
        return;
      }
      const histPrevBtn = target.closest("[id^='mat-admin-history-prev-']");
      if (histPrevBtn) {
        event.preventDefault();
        const tipo = tipoFromElementId(histPrevBtn.id);
        const state = getHistoryState(tipo);
        state.offset = Math.max(0, state.offset - state.limit);
        loadHistory(tipo, false);
        return;
      }
      const histNextBtn = target.closest("[id^='mat-admin-history-next-']");
      if (histNextBtn) {
        event.preventDefault();
        const tipo = tipoFromElementId(histNextBtn.id);
        const state = getHistoryState(tipo);
        const nextOffset = state.offset + state.limit;
        if (nextOffset < state.total) {
          state.offset = nextOffset;
          loadHistory(tipo, false);
        }
      }
    });

    document.body.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.id === "mat-admin-inv-use-date") {
        loadInventory(true);
        return;
      }
      if (target.id === "mat-admin-inv-page-size") {
        inventoryState.offset = 0;
        loadInventory(true);
        return;
      }
      if (target.id && target.id.startsWith("mat-admin-history-page-size-")) {
        const tipo = tipoFromElementId(target.id);
        getHistoryState(tipo).offset = 0;
        loadHistory(tipo, true);
      }
    });

    document.body.dataset.matAdminListenersAttached = "true";
  }

  window.initMaterialCurrentInventory = function () {
    ensureModuleStyles();
    initListeners();
    removeLegacyPageHeaders("mat-admin-inventory-unique-container");
    inventoryState.view = "summary";
    inventoryState.offset = 0;

    if (el("mat-admin-inv-start") && !el("mat-admin-inv-start").value) {
      el("mat-admin-inv-start").value = monthStartIso();
    }
    if (el("mat-admin-inv-end") && !el("mat-admin-inv-end").value) {
      el("mat-admin-inv-end").value = todayIso();
    }
    syncInventoryControls();
    loadInventory(true);
  };

  window.initMaterialAdminHistory = function (tipo) {
    ensureModuleStyles();
    initListeners();
    const historyType = tipo || "entradas";
    removeLegacyPageHeaders(`mat-admin-history-${historyType}-root`);

    const startEl = el(H(historyType, "start"));
    const endEl = el(H(historyType, "end"));
    if (startEl && !startEl.value) startEl.value = todayIso();
    if (endEl && !endEl.value) endEl.value = todayIso();

    const state = getHistoryState(historyType);
    state.offset = 0;
    loadHistory(historyType, true);
  };

  window.limpiarMaterialAdminInventory = function () {
    setLoading("mat-admin-inv-loading", false);
    setLoading(H("entradas", "loading"), false);
    setLoading(H("salidas", "loading"), false);
    setLoading(H("retornos", "loading"), false);
  };
})();
