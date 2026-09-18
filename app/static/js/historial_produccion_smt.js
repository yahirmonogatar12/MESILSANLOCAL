(function historialProduccionSmtModule() {
  "use strict";

  const ROOT_SELECTOR = "#hps-module";
  const API_URL = "/api/control_resultados/historial_produccion_smt";
  const EXPORT_URL = `${API_URL}/export`;
  const FILTER_STORAGE_KEY = "historialProduccionSmtColumnFilters";
  const CSS_VERSION = "20260918d";

  function ensureStyles() {
    const sheets = [
      { id: "ilsan-theme-css", href: "/static/css/ilsan-theme.css?v=20260522a" },
      { id: "ict-css", href: "/static/css/ict.css?v=20260630a" },
      {
        id: "historial-produccion-ensamble-css",
        href: `/static/css/historial_produccion_ensamble.css?v=${CSS_VERSION}`,
      },
    ];

    sheets.forEach(({ id, href }) => {
      let link = document.getElementById(id);
      if (!link) {
        link = document.createElement("link");
        link.id = id;
        link.rel = "stylesheet";
        document.head.appendChild(link);
      }
      if (link.getAttribute("href") !== href) link.setAttribute("href", href);
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

  function readStoredColumnFilters() {
    try {
      const value = JSON.parse(localStorage.getItem(FILTER_STORAGE_KEY) || "{}");
      return value && typeof value === "object" ? value : {};
    } catch (error) {
      console.warn("No se pudieron leer los filtros del historial SMT", error);
      return {};
    }
  }

  function saveColumnFilters(filters) {
    try {
      localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(filters));
    } catch (error) {
      console.warn("No se pudieron guardar los filtros del historial SMT", error);
    }
  }

  function getRoot(selector = ROOT_SELECTOR) {
    return typeof selector === "string" ? document.querySelector(selector) : selector;
  }

  function closeColumnFilters(root, except = null) {
    root.querySelectorAll(".hpe-column-filter-popover.open").forEach((popover) => {
      if (popover === except) return;
      popover.classList.remove("open");
      const header = popover.closest("th");
      header?.classList.remove("hpe-filter-open");
      const button = header?.querySelector(".hpe-column-filter-btn");
      button?.classList.remove("open");
      button?.setAttribute("aria-expanded", "false");
    });
  }

  function renderColumnFilterHeaders(root, state) {
    root.querySelectorAll("th[data-hps-filter-field]").forEach((header) => {
      if (header.dataset.hpsFilterReady === "true") return;
      const field = header.dataset.hpsFilterField;
      const label = header.textContent.trim();
      const value = state.columnFilters[field] || "";
      header.dataset.hpsFilterReady = "true";
      header.innerHTML = `
        <div class="hpe-column-header">
          <span>${escapeHtml(label)}</span>
          <button class="hpe-column-filter-btn${value ? " active" : ""}"
                  type="button" aria-expanded="false"
                  aria-label="Filtrar ${escapeHtml(label)}" title="Filtrar ${escapeHtml(label)}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18l-7 8v5l-4 2v-7L3 5z"></path></svg>
          </button>
        </div>
        <div class="hpe-column-filter-popover" data-hps-field="${escapeHtml(field)}">
          <input class="hpe-column-filter-input" data-hps-field="${escapeHtml(field)}"
                 value="${escapeHtml(value)}" placeholder="Buscar..."
                 aria-label="Buscar en ${escapeHtml(label)}" autocomplete="off">
          <div class="hpe-column-filter-actions">
            <button type="button" data-hps-action="clear-column">Limpiar</button>
            <button type="button" data-hps-action="clear-all-columns">Todos</button>
          </div>
        </div>`;
    });
  }

  function syncColumnFilterControls(root, state) {
    root.querySelectorAll(".hpe-column-filter-input").forEach((input) => {
      const value = state.columnFilters[input.dataset.hpsField] || "";
      input.value = value;
      input.closest("th")?.querySelector(".hpe-column-filter-btn")
        ?.classList.toggle("active", Boolean(value));
    });
  }

  function showNotification(root, message, type = "error") {
    const notification = root.querySelector("#hps-notification");
    if (!notification) return;
    window.clearTimeout(root.__hpsNotificationTimer);
    notification.textContent = message;
    notification.className = `hpe-notification ${type}`;
    notification.hidden = false;
    root.__hpsNotificationTimer = window.setTimeout(() => {
      notification.hidden = true;
    }, 4500);
  }

  function setLoading(root, loading) {
    const loader = root.querySelector("#hps-table-loading");
    const table = root.querySelector("#hps-table");
    const wrap = table?.closest(".hpe-table-wrap");
    const head = table?.querySelector("thead");
    if (wrap && head) wrap.style.setProperty("--thead-height", `${head.offsetHeight}px`);
    loader?.classList.toggle("active", loading);
    root.querySelector("#hps-btn-consultar")?.toggleAttribute("disabled", loading);
    root.querySelector("#hps-btn-export-excel")?.toggleAttribute("disabled", loading);
  }

  function buildQuery(root, state) {
    const params = new URLSearchParams();
    const fields = {
      fecha_desde: "#hps-fecha-desde",
      fecha_hasta: "#hps-fecha-hasta",
      hora_desde: "#hps-hora-desde",
      hora_hasta: "#hps-hora-hasta",
      linea: "#hps-linea",
      qr: "#hps-qr",
      lote: "#hps-lote",
    };

    Object.entries(fields).forEach(([name, selector]) => {
      const value = root.querySelector(selector)?.value?.trim() || "";
      if (value) params.set(name, value);
    });
    Object.entries(state.columnFilters).forEach(([field, value]) => {
      if (value) params.set(`cf_${field}`, value);
    });
    params.set("page", String(state.page));
    params.set("per_page", String(state.perPage));
    return params;
  }

  async function fetchJson(url, signal) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      signal,
    });
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : null;

    if (response.status === 401) {
      window.location.assign(payload?.redirect || "/login");
      throw new Error("La sesión expiró. Redirigiendo al inicio de sesión...");
    }
    if (!response.ok) {
      throw new Error(payload?.error || `Error del servidor (${response.status})`);
    }
    if (!payload) throw new Error("El servidor devolvió una respuesta no válida");
    return payload;
  }

  function filenameFromDisposition(disposition, fallback) {
    const match = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition || "");
    return match?.[1] ? match[1].replace(/['"]/g, "").trim() : fallback;
  }

  async function exportExcel(root) {
    const state = root.__hpsState;
    if (!state || state.total <= 0) {
      showNotification(root, "No hay registros visibles para exportar");
      return;
    }
    const button = root.querySelector("#hps-btn-export-excel");
    button?.setAttribute("disabled", "");
    try {
      const query = state.lastQuery || buildQuery(root, state).toString();
      const response = await fetch(`${EXPORT_URL}?${query}`, {
        credentials: "same-origin",
        headers: { Accept: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
      });
      const contentType = response.headers.get("content-type") || "";
      if (response.status === 401 || response.redirected || contentType.includes("text/html")) {
        window.location.assign("/login");
        throw new Error("La sesión expiró. Redirigiendo al inicio de sesión...");
      }
      if (!response.ok) {
        let message = `Error al exportar (${response.status})`;
        if (contentType.includes("application/json")) {
          const payload = await response.json();
          message = payload?.error || message;
        }
        throw new Error(message);
      }
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = downloadUrl;
      anchor.download = filenameFromDisposition(
        response.headers.get("content-disposition"),
        `historial_input_smt_${Date.now()}.xlsx`,
      );
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(downloadUrl);
      showNotification(root, "Excel de la página visible exportado", "success");
    } catch (error) {
      console.error("Error exportando historial de produccion SMT", error);
      showNotification(root, error.message || "No fue posible exportar a Excel");
    } finally {
      button?.removeAttribute("disabled");
    }
  }

  function renderRows(root, rows) {
    const tbody = root.querySelector("#hps-table-body");
    if (!tbody) return;
    if (!rows.length) {
      tbody.innerHTML = '<tr class="hpe-empty-row"><td colspan="6">No se encontraron registros con los filtros seleccionados.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map((row) => `
      <tr>
        <td>${escapeHtml(row.numero)}</td>
        <td title="${escapeHtml(row.linea)}">${escapeHtml(row.linea)}</td>
        <td>${escapeHtml(row.fecha)}</td>
        <td>${escapeHtml(row.hora)}</td>
        <td title="${escapeHtml(row.qr)}">${escapeHtml(row.qr)}</td>
        <td title="${escapeHtml(row.lote)}">${escapeHtml(row.lote)}</td>
      </tr>`).join("");
  }

  function renderPagination(root, state) {
    const pagination = root.querySelector("#hps-pagination");
    if (!pagination) return;
    pagination.hidden = state.total <= 0;
    if (state.total <= 0) return;

    const start = (state.page - 1) * state.perPage + 1;
    const end = Math.min(state.page * state.perPage, state.total);
    root.querySelector("#hps-pagination-summary").textContent = `${start} - ${end} de ${state.total}`;
    const input = root.querySelector("#hps-page-input");
    input.value = String(state.page);
    input.max = String(state.totalPages);
    root.querySelector("#hps-page-total").textContent = String(state.totalPages);
    root.querySelector("#hps-page-first").disabled = state.page <= 1;
    root.querySelector("#hps-page-prev").disabled = state.page <= 1;
    root.querySelector("#hps-page-next").disabled = state.page >= state.totalPages;
    root.querySelector("#hps-page-last").disabled = state.page >= state.totalPages;
  }

  async function loadData(rootOrSelector = ROOT_SELECTOR, options = {}) {
    const root = getRoot(rootOrSelector);
    if (!root || !root.__hpsState) return;
    const state = root.__hpsState;
    if (options.resetPage !== false) state.page = 1;

    state.controller?.abort();
    state.controller = new AbortController();
    setLoading(root, true);
    try {
      const payload = await fetchJson(
        `${API_URL}?${buildQuery(root, state).toString()}`,
        state.controller.signal,
      );
      if (!root.isConnected) return;
      state.total = Number(payload.total || 0);
      state.page = Number(payload.page || 1);
      state.perPage = Number(payload.per_page || state.perPage);
      state.totalPages = Math.max(1, Number(payload.total_pages || 1));
      state.lastQuery = buildQuery(root, state).toString();
      const rows = Array.isArray(payload.rows) ? payload.rows : [];
      renderRows(root, rows);
      renderPagination(root, state);
      const count = root.querySelector("#hps-record-count");
      if (count) count.textContent = `${state.total} registro${state.total === 1 ? "" : "s"}`;
    } catch (error) {
      if (error.name === "AbortError") return;
      console.error("Error cargando historial de produccion SMT", error);
      if (root.isConnected) {
        renderRows(root, []);
        showNotification(root, error.message || "No fue posible cargar el historial");
      }
    } finally {
      if (root.isConnected) setLoading(root, false);
    }
  }

  function scheduleColumnFilter(root) {
    const state = root.__hpsState;
    window.clearTimeout(state.filterTimer);
    state.filterTimer = window.setTimeout(() => loadData(root), 300);
  }

  function goToPage(root, value) {
    const state = root.__hpsState;
    const page = Math.max(1, Math.min(state.totalPages, Number.parseInt(value, 10) || 1));
    if (page === state.page) return;
    state.page = page;
    loadData(root, { resetPage: false });
  }

  function bindEvents(root) {
    root.addEventListener("click", (event) => {
      const filterButton = event.target.closest(".hpe-column-filter-btn");
      if (filterButton) {
        event.preventDefault();
        const popover = filterButton.closest("th")?.querySelector(".hpe-column-filter-popover");
        const opening = !popover?.classList.contains("open");
        closeColumnFilters(root, popover);
        popover?.classList.toggle("open", opening);
        filterButton.classList.toggle("open", opening);
        filterButton.setAttribute("aria-expanded", String(opening));
        filterButton.closest("th")?.classList.toggle("hpe-filter-open", opening);
        if (opening) popover?.querySelector("input")?.focus();
        return;
      }

      const action = event.target.closest("[data-hps-action]")?.dataset.hpsAction;
      if (action === "clear-column") {
        const input = event.target.closest("th")?.querySelector(".hpe-column-filter-input");
        if (input) {
          delete root.__hpsState.columnFilters[input.dataset.hpsField];
          saveColumnFilters(root.__hpsState.columnFilters);
          syncColumnFilterControls(root, root.__hpsState);
          loadData(root);
        }
        return;
      }
      if (action === "clear-all-columns") {
        root.__hpsState.columnFilters = {};
        saveColumnFilters({});
        syncColumnFilterControls(root, root.__hpsState);
        loadData(root);
        return;
      }

      const id = event.target.closest("button")?.id;
      if (id === "hps-btn-consultar") loadData(root);
      else if (id === "hps-btn-export-excel") exportExcel(root);
      else if (id === "hps-page-first") goToPage(root, 1);
      else if (id === "hps-page-prev") goToPage(root, root.__hpsState.page - 1);
      else if (id === "hps-page-next") goToPage(root, root.__hpsState.page + 1);
      else if (id === "hps-page-last") goToPage(root, root.__hpsState.totalPages);
      else if (!event.target.closest(".hpe-column-filter-popover")) closeColumnFilters(root);
    });

    root.addEventListener("input", (event) => {
      if (!event.target.matches(".hpe-column-filter-input")) return;
      const field = event.target.dataset.hpsField;
      const value = event.target.value.trim();
      if (value) root.__hpsState.columnFilters[field] = value;
      else delete root.__hpsState.columnFilters[field];
      saveColumnFilters(root.__hpsState.columnFilters);
      event.target.closest("th")?.querySelector(".hpe-column-filter-btn")
        ?.classList.toggle("active", Boolean(value));
      scheduleColumnFilter(root);
    });

    root.addEventListener("change", (event) => {
      if (event.target.id !== "hps-per-page") return;
      root.__hpsState.perPage = Number.parseInt(event.target.value, 10) || 1000;
      loadData(root);
    });

    root.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeColumnFilters(root);
        return;
      }
      if (event.key !== "Enter") return;
      if (event.target.id === "hps-page-input") {
        event.preventDefault();
        goToPage(root, event.target.value);
      } else if (event.target.matches(".hpe-column-filter-input")) {
        event.preventDefault();
        window.clearTimeout(root.__hpsState.filterTimer);
        loadData(root);
      } else if (event.target.closest("#hps-filters")) {
        event.preventDefault();
        loadData(root);
      }
    });
  }

  function initialize(rootOrSelector = ROOT_SELECTOR) {
    const root = getRoot(rootOrSelector);
    if (!root || root.dataset.hpsInitialized === "true") return;
    ensureStyles();
    root.dataset.hpsInitialized = "true";
    root.__hpsState = {
      page: 1,
      perPage: Number.parseInt(root.querySelector("#hps-per-page")?.value, 10) || 1000,
      total: 0,
      totalPages: 1,
      columnFilters: readStoredColumnFilters(),
      controller: null,
      filterTimer: null,
      lastQuery: "",
    };
    renderColumnFilterHeaders(root, root.__hpsState);
    bindEvents(root);
    loadData(root);
  }

  window.inicializarHistorialProduccionSmt = initialize;
  window.cargarHistorialProduccionSmt = loadData;
  window.limpiarHistorialProduccionSmt = function limpiarHistorialProduccionSmt() {
    const root = getRoot();
    root?.__hpsState?.controller?.abort();
    if (root?.__hpsState?.filterTimer) window.clearTimeout(root.__hpsState.filterTimer);
  };

  initialize();
})();
