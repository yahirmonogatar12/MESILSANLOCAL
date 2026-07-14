(function () {
  const STYLESHEET_ID = "exceso-history-css";
  const ASSET_VERSION = "20260713a";
  const STYLESHEET_HREF = `/static/css/exceso_history.css?v=${ASSET_VERSION}`;

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
    if (!Number.isFinite(numericValue)) return "0";
    return numericValue.toLocaleString("es-MX");
  }

  function getQuantityTotalLabel(rows) {
    const total = rows.reduce((sum, row) => sum + (Number(row.quantity) || 0), 0);
    return `${formatNumber(total)} ${Math.abs(total) === 1 ? "pieza" : "piezas"}`;
  }

  function getElements(prefix) {
    return {
      searchInput: document.getElementById(`${prefix}-search`),
      dateFrom: document.getElementById(`${prefix}-date-from`),
      dateTo: document.getElementById(`${prefix}-date-to`),
      searchBtn: document.getElementById(`${prefix}-search-btn`),
      clearBtn: document.getElementById(`${prefix}-clear-btn`),
      exportBtn: document.getElementById(`${prefix}-export-btn`),
      countLabel: document.getElementById(`${prefix}-count`),
      statusLabel: document.getElementById(`${prefix}-status`),
      tableBody: document.getElementById(`${prefix}-tbody`),
    };
  }

  function buildQuery(prefix) {
    const elements = getElements(prefix);
    const params = new URLSearchParams();
    if (elements.searchInput?.value.trim()) {
      params.set("search", elements.searchInput.value.trim());
    }
    if (elements.dateFrom?.value) {
      params.set("fecha_desde", elements.dateFrom.value);
    }
    if (elements.dateTo?.value) {
      params.set("fecha_hasta", elements.dateTo.value);
    }
    return params;
  }

  function setStatus(prefix, message, isError = false) {
    const { statusLabel } = getElements(prefix);
    if (!statusLabel) return;
    statusLabel.textContent = message || "";
    statusLabel.classList.toggle("is-error", Boolean(isError));
  }

  function renderEmpty(prefix, colspan, message) {
    const { tableBody, countLabel } = getElements(prefix);
    if (tableBody) {
      tableBody.innerHTML = `<tr><td colspan="${colspan}" class="exceso-history-empty-cell">${escapeHtml(message)}</td></tr>`;
    }
    if (countLabel) {
      countLabel.textContent = "0 piezas";
    }
  }

  function setLoading(prefix, colspan) {
    renderEmpty(prefix, colspan, "Cargando historial...");
  }

  function buildBadge(text, variant) {
    return `<span class="exceso-history-badge exceso-history-badge--${variant}">${escapeHtml(text || "-")}</span>`;
  }

  function renderEntriesRows(rows) {
    return rows
      .map((row) => {
        return `
          <tr>
            <td>${escapeHtml(row.fecha || "-")}</td>
            <td>${escapeHtml(row.hora || "-")}</td>
            <td><strong>${escapeHtml(row.part_number || "-")}</strong></td>
            <td class="exceso-history-cell-code" title="${escapeHtml(row.scan_code || "")}">${escapeHtml(row.scan_code || "-")}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${escapeHtml(row.registered_by || "-")}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderExitsRows(rows) {
    return rows
      .map((row) => `
        <tr>
          <td>${escapeHtml(row.fecha || "-")}</td>
          <td>${escapeHtml(row.hora || "-")}</td>
          <td><strong>${escapeHtml(row.part_number || "-")}</strong></td>
          <td class="exceso-history-cell-code" title="${escapeHtml(row.scan_code || "")}">${escapeHtml(row.scan_code || "-")}</td>
          <td class="exceso-history-cell-code" title="${escapeHtml(row.box_code || "")}">${escapeHtml(row.box_code || "-")}</td>
          <td>${escapeHtml(row.oqc_folio || "-")}</td>
        </tr>
      `)
      .join("");
  }

  function syncTableShell(moduleRoot) {
    const tableShells = moduleRoot?.querySelectorAll(".exceso-history-table-shell") || [];
    tableShells.forEach((tableShell) => {
      const headerWrap = tableShell.querySelector(".exceso-history-table-head");
      const bodyWrap = tableShell.querySelector(".exceso-history-table-body-wrap");
      if (!headerWrap || !bodyWrap) return;
      if (bodyWrap.dataset.scrollBound !== "true") {
        bodyWrap.addEventListener("scroll", () => {
          headerWrap.scrollLeft = bodyWrap.scrollLeft;
        });
        bodyWrap.dataset.scrollBound = "true";
      }
    });
  }

  function getDeclaredColumnWidth(col) {
    const width = String(col?.style?.width || "").trim();
    if (width.endsWith("%")) {
      return { unit: "%", value: Number(width.slice(0, -1)) || 0 };
    }
    if (width.endsWith("px")) {
      return { unit: "px", value: Number(width.slice(0, -2)) || 0 };
    }
    return { unit: "%", value: 0 };
  }

  function syncTableWidths(moduleRoot) {
    const tableShells = moduleRoot?.querySelectorAll(".exceso-history-table-shell") || [];
    tableShells.forEach((tableShell) => {
      const headerWrap = tableShell.querySelector(".exceso-history-table-head");
      const headerTable = tableShell.querySelector(".exceso-history-table--head");
      const bodyWrap = tableShell.querySelector(".exceso-history-table-body-wrap");
      const bodyTable = tableShell.querySelector(".exceso-history-table--body");
      const headerCols = [...(headerTable?.querySelectorAll("colgroup col") || [])];
      const bodyCols = [...(bodyTable?.querySelectorAll("colgroup col") || [])];
      if (!headerWrap || !headerTable || !bodyWrap || !bodyTable || !bodyCols.length) {
        return;
      }

      const scrollbarWidth = Math.max(0, bodyWrap.offsetWidth - bodyWrap.clientWidth);
      const availableWidth = Math.max(1, bodyWrap.clientWidth);
      const declared = bodyCols.map(getDeclaredColumnWidth);
      const totalPercent = declared.reduce(
        (sum, item) => sum + (item.unit === "%" ? item.value : 0),
        0,
      );
      const fixedPixels = declared.reduce(
        (sum, item) => sum + (item.unit === "px" ? item.value : 0),
        0,
      );
      const fluidWidth = Math.max(1, availableWidth - fixedPixels);
      const widths = declared.map((item) => {
        if (item.unit === "px") return Math.max(1, Math.round(item.value));
        return Math.max(
          1,
          Math.round((fluidWidth * item.value) / Math.max(1, totalPercent || 100)),
        );
      });
      const widthDelta = availableWidth - widths.reduce((sum, width) => sum + width, 0);
      if (widths.length) {
        widths[widths.length - 1] += widthDelta;
      }

      widths.forEach((width, index) => {
        if (headerCols[index]) headerCols[index].style.width = `${width}px`;
        if (bodyCols[index]) bodyCols[index].style.width = `${width}px`;
      });

      headerWrap.style.paddingRight = `${scrollbarWidth}px`;
      headerTable.style.width = `${availableWidth}px`;
      headerTable.style.minWidth = `${availableWidth}px`;
      bodyTable.style.width = `${availableWidth}px`;
      bodyTable.style.minWidth = `${availableWidth}px`;
    });
  }

  function syncScrollableHeight(moduleRoot) {
    const bodyWraps = moduleRoot?.querySelectorAll(".exceso-history-table-body-wrap");
    if (!bodyWraps?.length) return;

    const viewportHeight =
      window.innerHeight || document.documentElement.clientHeight || 0;
    bodyWraps.forEach((bodyWrap) => {
      const rect = bodyWrap.getBoundingClientRect();
      const bottomGap = 20;
      const availableHeight = Math.max(220, viewportHeight - rect.top - bottomGap);
      bodyWrap.style.height = `${availableHeight}px`;
      bodyWrap.style.maxHeight = `${availableHeight}px`;
    });
  }

  async function loadModule(config) {
    const { prefix, apiUrl, colspan, emptyMessage, renderer } = config;
    const elements = getElements(prefix);
    if (!elements.tableBody) return;

    setLoading(prefix, colspan);
    setStatus(prefix, "Consultando datos...");

    try {
      const params = buildQuery(prefix);
      const response = await fetch(`${apiUrl}?${params.toString()}`, {
        credentials: "same-origin",
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || !Array.isArray(payload)) {
        throw new Error(payload?.error || `HTTP ${response.status}`);
      }

      if (!payload.length) {
        renderEmpty(prefix, colspan, emptyMessage);
        setStatus(prefix, "Sin registros para los filtros actuales");
        return;
      }

      elements.tableBody.innerHTML = renderer(payload);
      if (elements.countLabel) {
        elements.countLabel.textContent = getQuantityTotalLabel(payload);
      }
      const updatedAt = new Date().toLocaleTimeString("es-MX", {
        hour: "2-digit",
        minute: "2-digit",
      });
      setStatus(prefix, `Actualizado a las ${updatedAt}`);
    } catch (error) {
      console.error(`Error cargando ${prefix}:`, error);
      renderEmpty(prefix, colspan, "No fue posible cargar el historial.");
      setStatus(prefix, "Error al consultar el historial", true);
    } finally {
      const moduleRoot = document.getElementById(`${prefix}-module`);
      syncTableShell(moduleRoot);
      syncScrollableHeight(moduleRoot);
      syncTableWidths(moduleRoot);
    }
  }

  function exportModule(config) {
    const params = buildQuery(config.prefix);
    window.open(`${config.exportUrl}?${params.toString()}`, "_blank");
  }

  function bindModule(config) {
    const { prefix } = config;
    const moduleRoot = document.getElementById(`${prefix}-module`);
    const elements = getElements(prefix);
    if (!moduleRoot || !elements.tableBody) return;

    syncTableShell(moduleRoot);
    syncScrollableHeight(moduleRoot);
    syncTableWidths(moduleRoot);

    if (moduleRoot.dataset.bound === "true") return;

    elements.searchBtn?.addEventListener("click", () => loadModule(config));
    elements.exportBtn?.addEventListener("click", () => exportModule(config));
    elements.clearBtn?.addEventListener("click", () => {
      if (elements.searchInput) elements.searchInput.value = "";
      if (elements.dateFrom) elements.dateFrom.value = "";
      if (elements.dateTo) elements.dateTo.value = "";
      loadModule(config);
    });
    [elements.searchInput, elements.dateFrom, elements.dateTo].forEach((input) => {
      input?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          loadModule(config);
        }
      });
    });

    const updateHeight = () => {
      syncScrollableHeight(moduleRoot);
      syncTableWidths(moduleRoot);
    };

    if (typeof ResizeObserver === "function" && !moduleRoot.__excesoHistoryResizeObserver) {
      let lastWidth = Math.floor(moduleRoot.getBoundingClientRect().width || 0);
      const observer = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const width = Math.floor(entry.contentRect?.width || 0);
          if (width <= 0) continue;
          if (Math.abs(width - lastWidth) < 1) continue;
          lastWidth = width;
          updateHeight();
        }
      });
      observer.observe(moduleRoot);
      moduleRoot.__excesoHistoryResizeObserver = observer;
    }

    window.addEventListener("resize", updateHeight);
    moduleRoot.dataset.bound = "true";
  }

  function initializeModule(config) {
    ensureModuleStyles();
    bindModule(config);
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        const moduleRoot = document.getElementById(`${config.prefix}-module`);
        syncTableShell(moduleRoot);
        syncScrollableHeight(moduleRoot);
        syncTableWidths(moduleRoot);
        loadModule(config);
      }),
    );
  }

  window.inicializarEntradasExcesoAjax = function () {
    initializeModule({
      prefix: "exceso-entries",
      apiUrl: "/api/inventario_exceso/entradas",
      exportUrl: "/api/inventario_exceso/entradas/export",
      colspan: 6,
      emptyMessage: "No hay entradas de exceso para los filtros actuales.",
      renderer: renderEntriesRows,
    });
  };

  window.inicializarSalidasExcesoAjax = function () {
    initializeModule({
      prefix: "exceso-exits",
      apiUrl: "/api/inventario_exceso/salidas",
      exportUrl: "/api/inventario_exceso/salidas/export",
      colspan: 6,
      emptyMessage: "No hay salidas de exceso para los filtros actuales.",
      renderer: renderExitsRows,
    });
  };
})();
