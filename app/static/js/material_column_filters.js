(function () {
  if (window.MatColumnFilters) return;

  const STORAGE_PREFIX = "materialColumnFilters:";

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function storageKey(tableKey) {
    return `${STORAGE_PREFIX}${tableKey}`;
  }

  function load(tableKey) {
    try {
      return JSON.parse(localStorage.getItem(storageKey(tableKey)) || "{}");
    } catch (err) {
      console.warn("No se pudieron cargar filtros de tabla:", err);
      return {};
    }
  }

  function save(tableKey, filters) {
    try {
      localStorage.setItem(storageKey(tableKey), JSON.stringify(filters || {}));
    } catch (err) {
      console.warn("No se pudieron guardar filtros de tabla:", err);
    }
  }

  function set(tableKey, field, value) {
    if (!tableKey || !field) return;
    const filters = load(tableKey);
    const cleanValue = String(value || "").trim();
    if (cleanValue) {
      filters[field] = cleanValue;
    } else {
      delete filters[field];
    }
    save(tableKey, filters);
  }

  function notify(tableKey) {
    document.dispatchEvent(new CustomEvent("mat-column-filter-change", { detail: { tableKey } }));
  }

  function closeOpenFilters(exceptPanel) {
    document.querySelectorAll(".mat-invoice-header-filter.open").forEach((panel) => {
      if (panel !== exceptPanel) panel.classList.remove("open");
    });
    document.querySelectorAll(".mat-invoice-filter-btn.open").forEach((button) => {
      const headerPanel = button.closest("th")?.querySelector(".mat-invoice-header-filter");
      if (headerPanel !== exceptPanel) button.classList.remove("open");
    });
  }

  function getColumnText(row, column, rowIndex) {
    if (!column) return "";
    if (typeof column.filterValue === "function") return column.filterValue(row, rowIndex);
    if (typeof column.value === "function") return column.value(row, rowIndex);
    return row?.[column.field];
  }

  function filterRows(tableKey, columns, rows) {
    const filters = load(tableKey);
    const activeFilters = (columns || [])
      .filter((column) => column && column.filterable !== false)
      .map((column) => [column, String(filters[column.field] || "").toLowerCase()])
      .filter(([, value]) => value);
    if (!activeFilters.length) return rows || [];

    return (rows || []).filter((row, rowIndex) => {
      return activeFilters.every(([column, value]) => {
        return String(getColumnText(row, column, rowIndex) ?? "").toLowerCase().includes(value);
      });
    });
  }

  function renderHead(tableKey, headId, columns) {
    const head = document.getElementById(headId);
    if (!head || !Array.isArray(columns)) return;

    const table = head.closest("table");
    if (table) table.dataset.filterKey = tableKey;
    const filters = load(tableKey);
    head.innerHTML = `<tr>${columns.map((column) => {
      const field = column.field;
      const label = column.label || field;
      if (column.filterable === false) {
        return `<th data-field="${escapeHtml(field)}"><span class="mat-invoice-th-label">${escapeHtml(label)}</span></th>`;
      }
      const value = filters[field] || "";
      const activeClass = value ? " active" : "";
      return `<th class="mat-invoice-filterable" data-field="${escapeHtml(field)}">
        <div class="mat-invoice-header-cell">
          <span class="mat-invoice-th-label">${escapeHtml(label)}</span>
          <button type="button" class="mat-invoice-filter-btn${activeClass}" data-field="${escapeHtml(field)}" title="Filtrar ${escapeHtml(label)}">▼</button>
        </div>
        <div class="mat-invoice-header-filter" data-field="${escapeHtml(field)}">
          <input class="mat-invoice-filter-input" data-field="${escapeHtml(field)}" value="${escapeHtml(value)}" placeholder="Buscar..." autocomplete="off">
          <div class="mat-invoice-filter-actions">
            <button type="button" class="mat-invoice-filter-clear-col" data-field="${escapeHtml(field)}">Limpiar</button>
            <button type="button" class="mat-invoice-filter-clear-all">Todos</button>
          </div>
        </div>
      </th>`;
    }).join("")}</tr>`;
  }

  function clearByPrefix(prefix) {
    try {
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith(`${STORAGE_PREFIX}${prefix}`)) {
          localStorage.removeItem(key);
        }
      });
    } catch (err) {
      console.warn("No se pudieron limpiar filtros de tabla:", err);
    }
  }

  function attachGlobalHandlers() {
    if (document.body.dataset.materialColumnFiltersAttached) return;
    document.body.dataset.materialColumnFiltersAttached = "1";

    document.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;

      const filterButton = target.closest(".mat-invoice-filter-btn");
      if (filterButton) {
        event.preventDefault();
        event.stopPropagation();
        const header = filterButton.closest("th");
        const panel = header?.querySelector(".mat-invoice-header-filter");
        if (!panel) return;
        const willOpen = !panel.classList.contains("open");
        closeOpenFilters(willOpen ? panel : null);
        panel.classList.toggle("open", willOpen);
        filterButton.classList.toggle("open", willOpen);
        if (willOpen) {
          setTimeout(() => panel.querySelector(".mat-invoice-filter-input")?.focus(), 0);
        }
        return;
      }

      const clearColumn = target.closest(".mat-invoice-filter-clear-col");
      if (clearColumn) {
        event.preventDefault();
        event.stopPropagation();
        const table = clearColumn.closest("table");
        const tableKey = table?.dataset.filterKey;
        const field = clearColumn.dataset.field;
        set(tableKey, field, "");
        const header = clearColumn.closest("th");
        const input = header?.querySelector(".mat-invoice-filter-input");
        if (input) input.value = "";
        header?.querySelector(".mat-invoice-filter-btn")?.classList.remove("active");
        notify(tableKey);
        return;
      }

      const clearAll = target.closest(".mat-invoice-filter-clear-all");
      if (clearAll) {
        event.preventDefault();
        event.stopPropagation();
        const table = clearAll.closest("table");
        const tableKey = table?.dataset.filterKey;
        save(tableKey, {});
        table?.querySelectorAll(".mat-invoice-filter-input").forEach((input) => { input.value = ""; });
        table?.querySelectorAll(".mat-invoice-filter-btn").forEach((button) => button.classList.remove("active", "open"));
        table?.querySelectorAll(".mat-invoice-header-filter").forEach((panel) => panel.classList.remove("open"));
        notify(tableKey);
        return;
      }

      if (!target.closest(".mat-invoice-filterable")) {
        closeOpenFilters(null);
      }
    });

    document.addEventListener("input", (event) => {
      const input = event.target instanceof Element ? event.target.closest(".mat-invoice-filter-input") : null;
      if (!input) return;
      const table = input.closest("table");
      const tableKey = table?.dataset.filterKey;
      const field = input.dataset.field;
      set(tableKey, field, input.value);
      input.closest("th")?.querySelector(".mat-invoice-filter-btn")?.classList.toggle("active", Boolean(input.value.trim()));
      notify(tableKey);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeOpenFilters(null);
    });
  }

  window.MatColumnFilters = {
    attachGlobalHandlers,
    clearByPrefix,
    filterRows,
    renderHead,
  };

  attachGlobalHandlers();
})();
