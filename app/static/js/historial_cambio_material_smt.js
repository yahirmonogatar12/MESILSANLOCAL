/* Historial de cambio de material de SMT (WF_002 / WF_003 / WF_004).
 *
 * Template: app/templates/Control de calidad/historial_cambio_material_smt_ajax.html
 * Backend:  app/api/control_calidad/smt_historial.py
 *
 * Todo vive dentro de un IIFE: ict.js declara helpers globales con los mismos
 * nombres (escapeHtml, showLoading...) y el portal puede tener ambos modulos
 * cargados en la misma pagina.
 */
(function () {
  "use strict";

  const CSS_VERSION = "20260922d";
  const STORAGE_KEY = "historialCambioMaterialSmtColumnFilters";

  // ====== WF_004 capa 2: asegurar CSS del modulo en <head> ======
  // MainTemplate.html ya los declara con cache-busting. Esta capa cubre dos
  // casos: que el fragmento se cargue sin pasar por el layout, y que el portal
  // lleve abierto desde antes del deploy — ahi el <link> sigue apuntando a la
  // version anterior y el navegador reusa el CSS viejo cacheado con esa URL.
  const MODULE_CSS_ID = "historial-material-css";
  [
    { id: "ilsan-theme-css", href: "/static/css/ilsan-theme.css?v=20260522a" },
    { id: "ict-css", href: "/static/css/ict.css?v=20260630a" },
    {
      id: MODULE_CSS_ID,
      href: `/static/css/historial_material.css?v=${CSS_VERSION}`,
    },
  ].forEach(({ id, href }) => {
    const existing = document.getElementById(id);
    if (existing) {
      // Solo se corrige la version del CSS propio; ict.css e ilsan-theme.css
      // los versiona su modulo dueno.
      if (id === MODULE_CSS_ID && !existing.getAttribute("href")?.includes(CSS_VERSION)) {
        existing.setAttribute("href", href);
      }
      return;
    }
    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href = href;
    document.head.appendChild(link);
  });

  // ====== Estado ======
  let currentPage = 1;
  let perPage = 1000;
  let totalRows = 0;
  let totalPages = 1;
  let filterTimer = null;
  let columnFilters = null;
  let opcionesCargadas = false;
  let cargando = false;
  let recarga = null;

  // ====== Utilidades ======
  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function el(id) {
    return document.getElementById(id);
  }

  function notify(message, type = "info") {
    const box = document.createElement("div");
    box.textContent = message;
    box.style.cssText = `
      position: fixed; top: 20px; right: 20px; padding: 12px 20px;
      border-radius: 6px; color: #fff; font-weight: 500; z-index: 10000;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);`;
    box.style.backgroundColor =
      type === "success" ? "#27ae60" : type === "error" ? "#e74c3c" : "#3498db";
    document.body.appendChild(box);
    setTimeout(() => box.remove(), 4000);
  }

  function showLoading(on) {
    const loader = el("smt-hist-table-loading");
    if (!loader) return;
    const thead = el("smt-hist-table")?.querySelector("thead");
    const wrap = el("smt-hist-table")?.closest(".table-wrap");
    if (on && wrap && thead) {
      wrap.style.setProperty("--thead-height", `${thead.offsetHeight}px`);
    }
    loader.classList.toggle("active", Boolean(on));
  }

  // ====== Filtros por encabezado ======
  function getColumnFilters() {
    if (columnFilters) return columnFilters;
    columnFilters = {};
    try {
      const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
      if (stored && typeof stored === "object") columnFilters = stored;
    } catch (error) {
      console.warn("No se pudieron leer los filtros por columna de SMT", error);
    }
    return columnFilters;
  }

  function saveColumnFilters() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(getColumnFilters()));
    } catch (error) {
      console.warn("No se pudieron guardar los filtros por columna de SMT", error);
    }
  }

  function setColumnFilter(field, value) {
    const state = getColumnFilters();
    const normalized = String(value || "").trim();
    if (normalized) state[field] = normalized;
    else delete state[field];
    saveColumnFilters();
  }

  function renderColumnFilterHeaders() {
    document.querySelectorAll("#smt-hist-table th[data-smt-filter-field]").forEach(header => {
      if (header.dataset.smtFilterReady === "true") return;

      const field = header.dataset.smtFilterField;
      const label = header.textContent.trim();
      const value = getColumnFilters()[field] || "";
      header.classList.add("mat-hist-column-filterable");
      header.dataset.smtFilterReady = "true";
      header.innerHTML = `
        <div class="mat-hist-column-header">
          <span>${escapeHtml(label)}</span>
          <button class="mat-hist-column-filter-btn${value ? " active" : ""}"
                  type="button"
                  aria-label="Filtrar ${escapeHtml(label)}"
                  aria-expanded="false"
                  title="Filtrar ${escapeHtml(label)}">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M3 5h18l-7 8v5l-4 2v-7L3 5z"></path>
            </svg>
          </button>
        </div>
        <div class="mat-hist-column-filter-popover" data-smt-field="${escapeHtml(field)}">
          <input class="mat-hist-column-filter-input"
                 data-smt-field="${escapeHtml(field)}"
                 value="${escapeHtml(value)}"
                 placeholder="Buscar..."
                 aria-label="Buscar en ${escapeHtml(label)}"
                 autocomplete="off">
          <div class="mat-hist-column-filter-actions">
            <button class="mat-hist-column-filter-clear" type="button">Limpiar</button>
            <button class="mat-hist-column-filter-clear-all" type="button">Todos</button>
          </div>
        </div>`;
    });
  }

  // Las clases .mat-hist-* las comparte con los historiales de IMD/ASSY, que
  // tienen sus propios listeners en document. Cada modulo actua solo sobre lo
  // que cuelga de su contenedor.
  function esDeEsteModulo(node) {
    return Boolean(node?.closest?.("#smt-hist-container"));
  }

  function closeColumnFilterPopovers(except = null) {
    document
      .querySelectorAll("#smt-hist-container .mat-hist-column-filter-popover.open")
      .forEach(popover => {
      if (popover === except) return;
      popover.classList.remove("open");
      const th = popover.closest("th");
      th?.classList.remove("filter-open");
      const button = th?.querySelector(".mat-hist-column-filter-btn");
      button?.classList.remove("open");
      button?.setAttribute("aria-expanded", "false");
    });
  }

  function syncColumnFilterControls() {
    const filters = getColumnFilters();
    document
      .querySelectorAll("#smt-hist-container .mat-hist-column-filter-input")
      .forEach(input => {
      const value = filters[input.dataset.smtField] || "";
      input.value = value;
      input
        .closest("th")
        ?.querySelector(".mat-hist-column-filter-btn")
        ?.classList.toggle("active", Boolean(value));
    });
  }

  function scheduleColumnFilter() {
    window.clearTimeout(filterTimer);
    currentPage = 1;
    filterTimer = window.setTimeout(() => loadData({ resetPage: false }), 250);
  }

  // ====== Datos ======
  function buildQuery() {
    const qs = new URLSearchParams();
    const barcode = el("smt-hist-barcode")?.value.trim() || "";

    // Con barcode se busca en toda la BD, sin acotar por fecha (igual que ICT).
    if (!barcode) {
      const desde = el("smt-hist-fecha-desde")?.value || "";
      const hasta = el("smt-hist-fecha-hasta")?.value || "";
      if (desde) qs.set("fecha_desde", desde);
      if (hasta) qs.set("fecha_hasta", hasta);
    } else {
      qs.set("barcode_like", barcode);
    }

    const parte = el("smt-hist-parte")?.value.trim() || "";
    const linea = el("smt-hist-linea")?.value || "";
    const maquina = el("smt-hist-maquina")?.value || "";
    const resultado = el("smt-hist-resultado")?.value || "";
    if (parte) qs.set("parte", parte);
    if (linea) qs.set("linea", linea);
    if (maquina) qs.set("maquina", maquina);
    if (resultado) qs.set("resultado", resultado);

    Object.entries(getColumnFilters()).forEach(([field, value]) => {
      if (value) qs.set(`cf_${field}`, value);
    });
    return qs;
  }

  async function loadOpciones() {
    if (opcionesCargadas) return;
    try {
      const response = await fetch("/api/smt-historial/opciones", {
        credentials: "same-origin",
      });
      if (!response.ok) return;
      const data = await response.json();
      const fill = (id, values, etiqueta) => {
        const select = el(id);
        if (!select) return;
        const actual = select.value;
        select.innerHTML =
          `<option value="">${etiqueta}</option>` +
          (values || [])
            .map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`)
            .join("");
        if (actual) select.value = actual;
      };
      fill("smt-hist-linea", data.lineas, "Todas");
      fill("smt-hist-maquina", data.maquinas, "Todas");
      opcionesCargadas = true;
    } catch (error) {
      console.warn("No se pudieron cargar las opciones de linea/maquina", error);
    }
  }

  async function loadData(opts) {
    // El fragmento se inicializa dos veces (el <script> al inyectarse y el
    // callback de cargarContenidoDinamico); la segunda cae aqui con la
    // primera peticion aun en vuelo. Se encola para no perder un cambio de
    // filtro que llegue mientras la anterior sigue corriendo.
    if (cargando) {
      recarga = opts || {};
      return;
    }
    cargando = true;
    recarga = null;
    if (!opts || opts.resetPage !== false) currentPage = 1;
    showLoading(true);

    try {
      const select = el("smt-hist-per-page");
      const value = parseInt(select?.value || "", 10);
      if (!Number.isNaN(value) && value > 0) perPage = value;

      const qs = buildQuery();
      qs.set("page", String(currentPage));
      qs.set("per_page", String(perPage));

      const response = await fetch(`/api/smt-historial/data?${qs.toString()}`, {
        credentials: "same-origin",
      });
      if (response.status === 401 || response.redirected) {
        notify("Sesion expirada, vuelve a iniciar sesion", "error");
        return;
      }
      if (!response.ok) throw new Error(`Error ${response.status}`);

      const data = await response.json();
      if (data.error) throw new Error(data.error);

      const rows = data.rows || [];
      totalRows = data.total || 0;
      totalPages = Math.max(1, data.total_pages || 1);
      if (data.page) currentPage = data.page;

      const count = el("smt-hist-record-count");
      if (count) {
        count.textContent = `${totalRows} registro${totalRows !== 1 ? "s" : ""}`;
      }

      renderTable(rows);
      renderPagination();
    } catch (error) {
      console.error(error);
      notify(error.message || "Error al cargar datos", "error");
      renderTable([]);
    } finally {
      cargando = false;
      showLoading(false);
      if (recarga) {
        const pendiente = recarga;
        recarga = null;
        loadData(pendiente);
      }
    }
  }

  const COLUMNS = [
    "fecha", "hora", "linea", "maquina", "slot", "feeder", "resultado",
    "parte", "cantidad", "lote", "barcode", "barcode_anterior", "seq",
    "vendor", "archivo",
  ];

  function renderTable(rows) {
    const tbody = el("smt-hist-body");
    if (!tbody) return;

    if (!rows.length) {
      tbody.innerHTML = `<tr><td class="mat-hist-empty" colspan="${COLUMNS.length}">Sin registros para los filtros seleccionados</td></tr>`;
      return;
    }

    tbody.innerHTML = rows
      .map(row => {
        const ng = String(row.resultado || "").toUpperCase() === "NG";
        const celdas = COLUMNS.map(key => {
          const value = escapeHtml(row[key]);
          return `<td title="${value}">${value}</td>`;
        }).join("");
        return `<tr class="${ng ? "mat-hist-row-ng" : ""}">${celdas}</tr>`;
      })
      .join("");
  }

  function renderPagination() {
    const wrap = el("smt-hist-pagination");
    if (!wrap) return;
    if (totalRows <= 0) {
      wrap.style.display = "none";
      return;
    }
    wrap.style.display = "";

    const start = (currentPage - 1) * perPage + 1;
    const end = Math.min(currentPage * perPage, totalRows);
    const summary = el("smt-hist-pagination-summary");
    if (summary) summary.textContent = `${start} - ${end} de ${totalRows}`;

    const input = el("smt-hist-page-input");
    if (input) {
      input.value = String(currentPage);
      input.max = String(totalPages);
    }
    const total = el("smt-hist-page-total");
    if (total) total.textContent = String(totalPages);

    const atFirst = currentPage <= 1;
    const atLast = currentPage >= totalPages;
    if (el("smt-hist-page-first")) el("smt-hist-page-first").disabled = atFirst;
    if (el("smt-hist-page-prev")) el("smt-hist-page-prev").disabled = atFirst;
    if (el("smt-hist-page-next")) el("smt-hist-page-next").disabled = atLast;
    if (el("smt-hist-page-last")) el("smt-hist-page-last").disabled = atLast;
  }

  function gotoPage(page) {
    const target = Math.max(1, Math.min(totalPages, parseInt(page, 10) || 1));
    if (target === currentPage) return;
    currentPage = target;
    loadData({ resetPage: false });
  }

  async function exportExcel() {
    const url = `/api/smt-historial/export?${buildQuery().toString()}`;
    try {
      const response = await fetch(url, { credentials: "same-origin" });
      if (!response.ok) {
        let message = `Error al descargar archivo (status ${response.status})`;
        try {
          message = (await response.json())?.error || message;
        } catch (_) {
          /* el backend no mando JSON */
        }
        throw new Error(message);
      }
      const blob = await response.blob();
      const href = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = `historial_cambio_material_smt_${Date.now()}.xlsx`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(href);
      notify("Exportación completada", "success");
    } catch (error) {
      console.error(error);
      notify(error.message || "Error al exportar", "error");
    }
  }

  // ====== Event delegation (el fragmento se recrea en cada carga AJAX) ======
  function attachListeners() {
    if (document.body.dataset.smtHistListeners === "true") return;
    document.body.dataset.smtHistListeners = "true";

    document.addEventListener("click", event => {
      const target = event.target;
      if (!esDeEsteModulo(target)) return;

      const filterButton = target.closest?.(".mat-hist-column-filter-btn");
      if (filterButton) {
        event.preventDefault();
        const th = filterButton.closest("th");
        const popover = th?.querySelector(".mat-hist-column-filter-popover");
        if (!popover) return;
        const shouldOpen = !popover.classList.contains("open");
        closeColumnFilterPopovers();
        if (shouldOpen) {
          popover.classList.add("open");
          th.classList.add("filter-open");
          filterButton.classList.add("open");
          filterButton.setAttribute("aria-expanded", "true");
          popover.querySelector(".mat-hist-column-filter-input")?.focus();
        }
        return;
      }

      if (target.closest?.(".mat-hist-column-filter-clear")) {
        event.preventDefault();
        const field = target.closest(".mat-hist-column-filter-popover")?.dataset.smtField;
        if (field) {
          setColumnFilter(field, "");
          syncColumnFilterControls();
          scheduleColumnFilter();
        }
        return;
      }

      if (target.closest?.(".mat-hist-column-filter-clear-all")) {
        event.preventDefault();
        columnFilters = {};
        saveColumnFilters();
        syncColumnFilterControls();
        closeColumnFilterPopovers();
        scheduleColumnFilter();
        return;
      }

      if (target.closest?.(".mat-hist-column-filter-popover")) return;
      closeColumnFilterPopovers();

      if (target.closest?.("#smt-hist-btn-consultar")) {
        event.preventDefault();
        loadData();
        return;
      }
      if (target.closest?.("#smt-hist-btn-export")) {
        event.preventDefault();
        exportExcel();
        return;
      }
      if (target.closest?.("#smt-hist-page-first")) return gotoPage(1);
      if (target.closest?.("#smt-hist-page-prev")) return gotoPage(currentPage - 1);
      if (target.closest?.("#smt-hist-page-next")) return gotoPage(currentPage + 1);
      if (target.closest?.("#smt-hist-page-last")) return gotoPage(totalPages);
    });

    document.addEventListener("input", event => {
      const input = event.target.closest?.(".mat-hist-column-filter-input");
      if (!input || !esDeEsteModulo(input)) return;
      setColumnFilter(input.dataset.smtField, input.value);
      input
        .closest("th")
        ?.querySelector(".mat-hist-column-filter-btn")
        ?.classList.toggle("active", Boolean(input.value.trim()));
      scheduleColumnFilter();
    });

    document.addEventListener("change", event => {
      const target = event.target;
      if (target.id === "smt-hist-per-page") {
        perPage = parseInt(target.value, 10) || 1000;
        loadData();
      } else if (
        ["smt-hist-linea", "smt-hist-maquina", "smt-hist-resultado"].includes(target.id)
      ) {
        loadData();
      } else if (target.id === "smt-hist-page-input") {
        gotoPage(target.value);
      }
    });

    document.addEventListener("keydown", event => {
      if (event.key === "Escape") {
        closeColumnFilterPopovers();
        return;
      }
      if (!esDeEsteModulo(event.target)) return;
      if (event.key !== "Enter") return;
      const id = event.target.id;
      if (["smt-hist-parte", "smt-hist-barcode", "smt-hist-fecha-desde", "smt-hist-fecha-hasta"].includes(id)) {
        event.preventDefault();
        loadData();
      } else if (id === "smt-hist-page-input") {
        event.preventDefault();
        gotoPage(event.target.value);
      }
    });
  }

  function setDefaultDates() {
    const hoy = new Date().toISOString().split("T")[0];
    const desde = el("smt-hist-fecha-desde");
    const hasta = el("smt-hist-fecha-hasta");
    if (desde && !desde.value) desde.value = hoy;
    if (hasta && !hasta.value) hasta.value = hoy;
  }

  // ====== Inicializacion idempotente (WF_007) ======
  function init() {
    if (!el("smt-hist-container")) return;
    renderColumnFilterHeaders();
    syncColumnFilterControls();
    attachListeners();
    setDefaultDates();
    loadOpciones();
    loadData();
  }

  function cleanup() {
    window.clearTimeout(filterTimer);
    showLoading(false);
    closeColumnFilterPopovers();
  }

  window.initHistorialSMT = init;
  window.limpiarHistorialSMT = cleanup;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
