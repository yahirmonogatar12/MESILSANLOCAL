(function () {
  const PREFIX = "historial-liberacion-oqc";
  const MODULE_ID = `${PREFIX}-module`;
  const ASSET_VERSION = "20260903a";
  const TABLE_COLSPAN = 9;
  const STYLESHEETS = [
    {
      id: "almacen-embarques-history-css",
      href: "/static/css/almacen_embarques_history.css?v=20260824b",
      version: "20260824b",
    },
    {
      id: "historial-liberacion-oqc-css",
      href: `/static/css/historial_liberacion_oqc.css?v=${ASSET_VERSION}`,
      version: ASSET_VERSION,
    },
  ];

  function ensureStyles() {
    STYLESHEETS.forEach((style) => {
      const currentLink = document.getElementById(style.id);
      if (currentLink) {
        const href = currentLink.getAttribute("href") || "";
        if (!href.includes(style.version)) {
          currentLink.setAttribute("href", style.href);
        }
        return;
      }

      const link = document.createElement("link");
      link.id = style.id;
      link.rel = "stylesheet";
      link.href = style.href;
      document.head.appendChild(link);
    });
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
    if (value === null || value === undefined || value === "") {
      return "0";
    }

    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) {
      return escapeHtml(value);
    }

    return Number.isInteger(numericValue)
      ? numericValue.toLocaleString("es-MX")
      : numericValue.toLocaleString("es-MX", {
          minimumFractionDigits: 0,
          maximumFractionDigits: 2,
        });
  }

  function getElements() {
    return {
      module: document.getElementById(MODULE_ID),
      searchInput: document.getElementById(`${PREFIX}-search`),
      dateFrom: document.getElementById(`${PREFIX}-date-from`),
      dateTo: document.getElementById(`${PREFIX}-date-to`),
      searchBtn: document.getElementById(`${PREFIX}-search-btn`),
      clearBtn: document.getElementById(`${PREFIX}-clear-btn`),
      exportBtn: document.getElementById(`${PREFIX}-export-btn`),
      countLabel: document.getElementById(`${PREFIX}-count`),
      statusLabel: document.getElementById(`${PREFIX}-status-label`),
      tableBody: document.getElementById(`${PREFIX}-tbody`),
    };
  }

  function buildParams() {
    const elements = getElements();
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

  function setStatus(message, isError = false) {
    const { statusLabel } = getElements();
    if (!statusLabel) {
      return;
    }
    statusLabel.textContent = message;
    statusLabel.classList.toggle("is-error", isError);
  }

  function setLoading(message) {
    const { tableBody } = getElements();
    if (tableBody) {
      tableBody.innerHTML = `<tr><td colspan="${TABLE_COLSPAN}" class="ae-empty-cell">${escapeHtml(message)}</td></tr>`;
    }
  }

  function setEmpty(message) {
    const { tableBody, countLabel } = getElements();
    if (countLabel) {
      countLabel.textContent = "0 cajas mostradas";
    }
    if (tableBody) {
      tableBody.innerHTML = `<tr><td colspan="${TABLE_COLSPAN}" class="ae-empty-cell">${escapeHtml(message)}</td></tr>`;
    }
  }

  function renderUserCell(row) {
    const inspector = row.released_by_name || row.inspector_name || "";
    return `
      <div class="oqc-release-user-cell">
        <span class="oqc-release-cell-main">${escapeHtml(inspector || "-")}</span>
      </div>
    `;
  }

  function renderRows(rows) {
    return rows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.fecha || "-")}</td>
            <td>${escapeHtml(row.hora || "-")}</td>
            <td>${escapeHtml(row.oqc_folio || "-")}</td>
            <td><strong>${escapeHtml(row.box_code || "-")}</strong></td>
            <td><strong>${escapeHtml(row.part_number || "-")}</strong></td>
            <td>${formatNumber(row.quantity)}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${escapeHtml(row.customer || "-")}</td>
            <td>${renderUserCell(row)}</td>
          </tr>
        `,
      )
      .join("");
  }

  function bindScrollableShell(moduleRoot) {
    const tableShells = moduleRoot?.querySelectorAll(".ae-table-shell");
    tableShells?.forEach((tableShell) => {
      const headerWrap = tableShell.querySelector(".ae-table-head");
      const bodyWrap = tableShell.querySelector(".ae-table-body-wrap");
      if (!headerWrap || !bodyWrap || bodyWrap.dataset.oqcScrollBound === "true") {
        return;
      }

      bodyWrap.addEventListener("scroll", () => {
        headerWrap.scrollLeft = bodyWrap.scrollLeft;
      });
      bodyWrap.dataset.oqcScrollBound = "true";
    });
  }

  function syncScrollableHeight(moduleRoot) {
    const bodyWraps = moduleRoot?.querySelectorAll(".ae-table-body-wrap");
    if (!bodyWraps?.length) {
      return;
    }

    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
    bodyWraps.forEach((bodyWrap) => {
      const rect = bodyWrap.getBoundingClientRect();
      const availableHeight = Math.max(220, viewportHeight - rect.top - 20);
      bodyWrap.style.height = `${availableHeight}px`;
      bodyWrap.style.maxHeight = `${availableHeight}px`;
    });
  }

  async function loadData() {
    const elements = getElements();
    if (!elements.tableBody) {
      return;
    }

    setLoading("Cargando historial...");
    setStatus("Consultando datos...");

    try {
      const params = buildParams();
      const response = await fetch(`/api/oqc/liberaciones?${params.toString()}`, {
        credentials: "same-origin",
      });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || `HTTP ${response.status}`);
      }

      const rows = payload.records || payload.rows || [];

      if (!rows.length) {
        setEmpty("No hay liberaciones OQC para los filtros actuales.");
        setStatus("Sin registros para los filtros actuales");
        return;
      }

      elements.tableBody.innerHTML = renderRows(rows);
      if (elements.countLabel) {
        elements.countLabel.textContent = `${formatNumber(rows.length)} cajas mostradas`;
      }

      const totalBoxes = Number(payload.summary?.total_boxes || rows.length) || 0;
      const updatedAt = new Date().toLocaleTimeString("es-MX", {
        hour: "2-digit",
        minute: "2-digit",
      });
      const limitText = payload.truncated
        ? `Mostrando ${formatNumber(rows.length)} de ${formatNumber(totalBoxes)} cajas`
        : `${formatNumber(totalBoxes)} cajas en el filtro`;
      setStatus(`${limitText}. Actualizado a las ${updatedAt}`);

      const moduleRoot = document.getElementById(MODULE_ID);
      bindScrollableShell(moduleRoot);
      syncScrollableHeight(moduleRoot);
    } catch (error) {
      console.error("Error cargando Historial de liberacion OQC:", error);
      setEmpty("No fue posible cargar el historial.");
      setStatus(error.message || "Error al consultar el historial", true);
    }
  }

  function clearFilters() {
    const elements = getElements();
    [
      elements.searchInput,
      elements.dateFrom,
      elements.dateTo,
    ].forEach((input) => {
      if (input) input.value = "";
    });
    loadData();
  }

  function exportExcel() {
    const params = buildParams();
    window.open(`/api/oqc/liberaciones/export?${params.toString()}`, "_blank");
  }

  function bindEvents() {
    const elements = getElements();
    const moduleRoot = elements.module;
    if (!moduleRoot || moduleRoot.dataset.oqcBound === "true") {
      return;
    }

    elements.searchBtn?.addEventListener("click", loadData);
    elements.clearBtn?.addEventListener("click", clearFilters);
    elements.exportBtn?.addEventListener("click", exportExcel);

    [
      elements.searchInput,
      elements.dateFrom,
      elements.dateTo,
    ].forEach((input) => {
      input?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          loadData();
        }
      });
    });

    bindScrollableShell(moduleRoot);
    window.addEventListener("resize", () => syncScrollableHeight(moduleRoot));
    moduleRoot.dataset.oqcBound = "true";
  }

  function init() {
    ensureStyles();
    bindEvents();
    requestAnimationFrame(() => {
      const moduleRoot = document.getElementById(MODULE_ID);
      syncScrollableHeight(moduleRoot);
    });
    loadData();
  }

  window.inicializarHistorialLiberacionOQC = init;

  if (document.readyState === "interactive" || document.readyState === "complete") {
    const moduleRoot = document.getElementById(MODULE_ID);
    if (moduleRoot) {
      setTimeout(init, 50);
    }
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      const moduleRoot = document.getElementById(MODULE_ID);
      if (moduleRoot) {
        init();
      }
    });
  }
})();
