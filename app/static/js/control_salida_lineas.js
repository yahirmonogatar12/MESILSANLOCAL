(function () {
  const STYLESHEET_ID = "almacen-embarques-history-css";
  const ASSET_VERSION = "20260513b";
  const STYLESHEET_HREF = `/static/css/almacen_embarques_history.css?v=${ASSET_VERSION}`;
  const COLUMN_STORAGE_KEY = "control-salida-lineas:column-widths:v1";
  const DEFAULT_COLUMN_WIDTHS = [13, 23, 13, 14, 13, 13, 11];
  const MIN_COLUMN_WIDTHS = [96, 160, 118, 136, 128, 150, 150];

  function ensureModuleStyles() {
    const currentLink = document.getElementById(STYLESHEET_ID);
    if (currentLink) {
      if (!currentLink.getAttribute("href")?.includes(ASSET_VERSION)) {
        currentLink.setAttribute("href", STYLESHEET_HREF);
      }
      return;
    }

    const link = document.createElement("link");
    link.id = STYLESHEET_ID;
    link.rel = "stylesheet";
    link.href = STYLESHEET_HREF;
    document.head.appendChild(link);
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
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) {
      return "0";
    }
    return numericValue.toLocaleString("es-MX");
  }

  function getElements() {
    return {
      moduleRoot: document.getElementById("control-salida-lineas-module"),
      partNumber: document.getElementById("control-salida-lineas-part-number"),
      dateFrom: document.getElementById("control-salida-lineas-date-from"),
      dateTo: document.getElementById("control-salida-lineas-date-to"),
      searchBtn: document.getElementById("control-salida-lineas-search-btn"),
      clearBtn: document.getElementById("control-salida-lineas-clear-btn"),
      exportBtn: document.getElementById("control-salida-lineas-export-btn"),
      tableBody: document.getElementById("control-salida-lineas-tbody"),
      status: document.getElementById("control-salida-lineas-status"),
      count: document.getElementById("control-salida-lineas-count"),
      totalProduction: document.getElementById("control-salida-lineas-total-production"),
      totalOqc: document.getElementById("control-salida-lineas-total-oqc"),
      totalWarehouse: document.getElementById("control-salida-lineas-total-warehouse"),
      totalPendingOqc: document.getElementById("control-salida-lineas-total-pending-oqc"),
      totalPendingWarehouse: document.getElementById("control-salida-lineas-total-pending-warehouse"),
    };
  }

  function setStatus(message, isError = false) {
    const { status } = getElements();
    if (!status) {
      return;
    }
    status.textContent = message || "";
    status.classList.toggle("is-error", Boolean(isError));
  }

  function setDefaultDates() {
    const { dateFrom, dateTo } = getElements();
    const today = new Date();
    const start = new Date(today);
    start.setDate(today.getDate() - 7);
    const toIsoDate = (value) => value.toISOString().slice(0, 10);

    if (dateFrom && !dateFrom.value) {
      dateFrom.value = toIsoDate(start);
    }
    if (dateTo && !dateTo.value) {
      dateTo.value = toIsoDate(today);
    }
  }

  function buildQueryParams() {
    const { partNumber, dateFrom, dateTo } = getElements();
    const params = new URLSearchParams();
    params.set("part_number", partNumber?.value?.trim() || "");
    params.set("fecha_desde", dateFrom?.value || "");
    params.set("fecha_hasta", dateTo?.value || "");
    return params;
  }

  function renderEmpty(message) {
    const { tableBody, count } = getElements();
    if (tableBody) {
      tableBody.innerHTML = `<tr><td colspan="7" class="ae-empty-cell">${escapeHtml(message)}</td></tr>`;
    }
    if (count) {
      count.textContent = "0 registros";
    }
    updateSummary({});
  }

  function updateSummary(summary) {
    const elements = getElements();
    if (elements.totalProduction) {
      elements.totalProduction.textContent = formatNumber(summary.produced_quantity);
    }
    if (elements.totalOqc) {
      elements.totalOqc.textContent = formatNumber(summary.oqc_quantity);
    }
    if (elements.totalWarehouse) {
      elements.totalWarehouse.textContent = formatNumber(summary.warehouse_quantity);
    }
    if (elements.totalPendingOqc) {
      elements.totalPendingOqc.textContent = formatNumber(summary.pending_oqc);
    }
    if (elements.totalPendingWarehouse) {
      elements.totalPendingWarehouse.textContent = formatNumber(summary.pending_warehouse);
    }
  }

  function renderRows(rows) {
    const { tableBody, count } = getElements();
    if (!tableBody) {
      return;
    }

    if (!rows.length) {
      renderEmpty("Sin registros para los filtros actuales.");
      return;
    }

    tableBody.innerHTML = rows
      .map((row) => {
        return `
          <tr>
            <td>${escapeHtml(row.fecha)}</td>
            <td><strong>${escapeHtml(row.part_number)}</strong></td>
            <td>${formatNumber(row.produced_quantity)}</td>
            <td>${formatNumber(row.oqc_quantity)}</td>
            <td>${formatNumber(row.pending_oqc)}</td>
            <td>${formatNumber(row.warehouse_quantity)}</td>
            <td>${formatNumber(row.pending_warehouse)}</td>
          </tr>
        `;
      })
      .join("");

    if (count) {
      count.textContent = `${formatNumber(rows.length)} registro${rows.length === 1 ? "" : "s"}`;
    }
  }

  function syncTableScroll() {
    const { moduleRoot } = getElements();
    const head = moduleRoot?.querySelector(".ae-table-head");
    const bodyWrap = moduleRoot?.querySelector(".ae-table-body-wrap");
    if (!head || !bodyWrap || bodyWrap.dataset.cslScrollBound === "true") {
      return;
    }

    bodyWrap.addEventListener("scroll", () => {
      head.scrollLeft = bodyWrap.scrollLeft;
    });
    bodyWrap.dataset.cslScrollBound = "true";
  }

  function getTableParts() {
    const { moduleRoot } = getElements();
    const tableShell = moduleRoot?.querySelector(".ae-table-shell");
    if (!tableShell) {
      return {};
    }

    return {
      tableShell,
      headerWrap: tableShell.querySelector(".ae-table-head"),
      headerTable: tableShell.querySelector(".ae-history-table--head"),
      bodyWrap: tableShell.querySelector(".ae-table-body-wrap"),
      bodyTable: tableShell.querySelector(".ae-history-table--body"),
      headerCols: [...tableShell.querySelectorAll(".ae-history-table--head colgroup col")],
      bodyCols: [...tableShell.querySelectorAll(".ae-history-table--body colgroup col")],
      headerCells: [...tableShell.querySelectorAll(".ae-history-table--head thead th")],
    };
  }

  function loadStoredColumnWidths() {
    try {
      const raw = window.localStorage?.getItem(COLUMN_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      return Array.isArray(parsed) && parsed.length === DEFAULT_COLUMN_WIDTHS.length
        ? parsed.map((width, index) => Math.max(MIN_COLUMN_WIDTHS[index], Number(width) || 0))
        : null;
    } catch {
      return null;
    }
  }

  function storeColumnWidths(widths) {
    try {
      window.localStorage?.setItem(COLUMN_STORAGE_KEY, JSON.stringify(widths));
    } catch {
      // LocalStorage puede estar deshabilitado; el resize sigue funcionando en memoria.
    }
  }

  function buildDefaultPixelWidths(availableWidth) {
    const baseWidth = Math.max(
      availableWidth || 0,
      MIN_COLUMN_WIDTHS.reduce((sum, width) => sum + width, 0),
    );
    const widths = DEFAULT_COLUMN_WIDTHS.map((percent, index) =>
      Math.max(MIN_COLUMN_WIDTHS[index], Math.round((baseWidth * percent) / 100)),
    );
    const total = widths.reduce((sum, width) => sum + width, 0);
    if (total < baseWidth && widths.length) {
      widths[widths.length - 1] += baseWidth - total;
    }
    return widths;
  }

  function getCurrentColumnWidths(parts) {
    const availableWidth = Math.max(1, Math.floor(parts.bodyWrap?.clientWidth || 0));
    const storedWidths = loadStoredColumnWidths();
    if (storedWidths) {
      return storedWidths;
    }
    return buildDefaultPixelWidths(availableWidth);
  }

  function applyColumnWidths(widths) {
    const parts = getTableParts();
    if (!parts.headerCols?.length || !parts.bodyCols?.length) {
      return;
    }

    const normalized = widths.map((width, index) =>
      Math.max(MIN_COLUMN_WIDTHS[index] || 80, Math.round(Number(width) || 0)),
    );
    const tableWidth = normalized.reduce((sum, width) => sum + width, 0);
    const scrollbarWidth = Math.max(
      0,
      (parts.bodyWrap?.offsetWidth || 0) - (parts.bodyWrap?.clientWidth || 0),
    );

    normalized.forEach((width, index) => {
      const value = `${width}px`;
      if (parts.headerCols[index]) parts.headerCols[index].style.width = value;
      if (parts.bodyCols[index]) parts.bodyCols[index].style.width = value;
    });

    if (parts.headerWrap) {
      parts.headerWrap.style.paddingRight = `${scrollbarWidth}px`;
    }
    [parts.headerTable, parts.bodyTable].forEach((table) => {
      if (!table) return;
      table.style.width = `${tableWidth}px`;
      table.style.minWidth = `${tableWidth}px`;
    });
  }

  function syncTableWidths() {
    const parts = getTableParts();
    if (!parts.bodyWrap || !parts.headerCols?.length || !parts.bodyCols?.length) {
      return;
    }
    applyColumnWidths(getCurrentColumnWidths(parts));
  }

  function bindColumnResizers() {
    const parts = getTableParts();
    if (!parts.headerCells?.length || parts.tableShell?.dataset.cslResizeBound === "true") {
      return;
    }

    parts.headerCells.forEach((cell, index) => {
      if (index >= parts.headerCells.length - 1 || cell.querySelector(".ae-column-resizer")) {
        return;
      }

      const resizer = document.createElement("span");
      resizer.className = "ae-column-resizer";
      resizer.setAttribute("aria-hidden", "true");
      cell.appendChild(resizer);

      resizer.addEventListener("mousedown", (event) => {
        event.preventDefault();
        const startX = event.clientX;
        const startWidths = getCurrentColumnWidths(getTableParts());

        const handleMouseMove = (moveEvent) => {
          const nextWidths = startWidths.slice();
          nextWidths[index] = Math.max(
            MIN_COLUMN_WIDTHS[index] || 80,
            startWidths[index] + moveEvent.clientX - startX,
          );
          applyColumnWidths(nextWidths);
        };

        const handleMouseUp = () => {
          document.body.classList.remove("ae-column-resizing");
          const currentParts = getTableParts();
          const finalWidths = currentParts.headerCols.map((col, colIndex) => {
            const width = Number.parseFloat(col.style.width || "");
            return Math.max(MIN_COLUMN_WIDTHS[colIndex] || 80, Math.round(width || 0));
          });
          storeColumnWidths(finalWidths);
          document.removeEventListener("mousemove", handleMouseMove);
          document.removeEventListener("mouseup", handleMouseUp);
        };

        document.body.classList.add("ae-column-resizing");
        document.addEventListener("mousemove", handleMouseMove);
        document.addEventListener("mouseup", handleMouseUp);
      });
    });

    if (parts.tableShell) {
      parts.tableShell.dataset.cslResizeBound = "true";
    }
  }

  function syncTableHeight() {
    const { moduleRoot } = getElements();
    const bodyWrap = moduleRoot?.querySelector(".ae-table-body-wrap");
    if (!bodyWrap) {
      return;
    }

    const rect = bodyWrap.getBoundingClientRect();
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
    const availableHeight = Math.max(240, viewportHeight - rect.top - 20);
    bodyWrap.style.height = `${availableHeight}px`;
    bodyWrap.style.maxHeight = `${availableHeight}px`;
  }

  async function loadData() {
    const { searchBtn } = getElements();
    setStatus("Consultando datos...");
    renderEmpty("Cargando datos...");

    if (searchBtn) {
      searchBtn.disabled = true;
      searchBtn.classList.add("ae-btn-loading");
    }

    try {
      const params = buildQueryParams();
      const response = await fetch(`/api/control-salida-lineas?${params.toString()}`, {
        credentials: "same-origin",
      });
      const payload = await response.json();

      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || `HTTP ${response.status}`);
      }

      const rows = Array.isArray(payload.rows) ? payload.rows : [];
      updateSummary(payload.summary || {});
      renderRows(rows);

      const updatedAt = new Date().toLocaleTimeString("es-MX", {
        hour: "2-digit",
        minute: "2-digit",
      });
      setStatus(`Actualizado a las ${updatedAt}`);
      requestAnimationFrame(() => {
        syncTableHeight();
        syncTableWidths();
      });
    } catch (error) {
      console.error("Error cargando Control de salida de lineas:", error);
      renderEmpty("No fue posible cargar la informacion.");
      setStatus(error.message || "Error al consultar datos", true);
    } finally {
      if (searchBtn) {
        searchBtn.disabled = false;
        searchBtn.classList.remove("ae-btn-loading");
      }
    }
  }

  function exportExcel() {
    const params = buildQueryParams();
    window.open(`/api/control-salida-lineas/export?${params.toString()}`, "_blank");
  }

  function clearFilters() {
    const { partNumber, dateFrom, dateTo } = getElements();
    if (partNumber) {
      partNumber.value = "";
    }
    if (dateFrom) {
      dateFrom.value = "";
    }
    if (dateTo) {
      dateTo.value = "";
    }
    setDefaultDates();
    loadData();
  }

  function bindEvents() {
    const elements = getElements();
    if (!elements.moduleRoot || elements.moduleRoot.dataset.cslBound === "true") {
      return;
    }

    elements.searchBtn?.addEventListener("click", loadData);
    elements.clearBtn?.addEventListener("click", clearFilters);
    elements.exportBtn?.addEventListener("click", exportExcel);
    elements.partNumber?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        loadData();
      }
    });
    [elements.dateFrom, elements.dateTo].forEach((input) => {
      input?.addEventListener("change", () => {
        if (elements.dateFrom?.value && elements.dateTo?.value) {
          loadData();
        }
      });
    });
    window.addEventListener("resize", syncTableHeight);
    window.addEventListener("resize", syncTableWidths);
    elements.moduleRoot.dataset.cslBound = "true";
  }

  window.inicializarControlSalidaLineasAjax = function () {
    ensureModuleStyles();
    setDefaultDates();
    bindEvents();
    syncTableScroll();
    bindColumnResizers();
    requestAnimationFrame(() => {
      syncTableHeight();
      syncTableWidths();
    });
    loadData();
  };
})();
