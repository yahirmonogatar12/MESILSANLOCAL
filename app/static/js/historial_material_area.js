/* Historial de cambio de material por area: IMD y ASSY (WF_002 / WF_003 / WF_004).
 *
 * Template: app/templates/Control de calidad/historial_material_area_ajax.html
 * Backend:  app/api/control_calidad/historial_material_areas.py
 *
 * Una instancia de estado por area, porque el portal permite tener las dos
 * pestanas abiertas a la vez. Todo dentro de un IIFE: ict.js y el JS del
 * historial de SMT declaran helpers globales con los mismos nombres.
 */
(function () {
  "use strict";

  const CSS_VERSION = "20260922d";

  // ====== WF_004 capa 2: asegurar CSS en <head> ======
  // MainTemplate.html ya los declara con cache-busting. Esta capa cubre que el
  // fragmento se cargue sin pasar por el layout, y que el portal lleve abierto
  // desde antes del deploy (el <link> apuntaria a la version anterior y el
  // navegador reusaria el CSS viejo cacheado con esa URL).
  const MODULE_CSS_ID = "historial-material-css";
  [
    { id: "ilsan-theme-css", href: "/static/css/ilsan-theme.css?v=20260522a" },
    { id: "ict-css", href: "/static/css/ict.css?v=20260630a" },
    { id: MODULE_CSS_ID, href: `/static/css/historial_material.css?v=${CSS_VERSION}` },
  ].forEach(({ id, href }) => {
    const existing = document.getElementById(id);
    if (existing) {
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

  // ====== Utilidades ======
  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
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

  // ====== Una instancia por area ======
  const instancias = new Map(); // area -> estado

  function crearInstancia(area, prefijo) {
    return {
      area,
      prefijo,
      storageKey: `historialMaterial_${area}_columnFilters`,
      currentPage: 1,
      perPage: 1000,
      totalRows: 0,
      totalPages: 1,
      filterTimer: null,
      columnFilters: null,
      opcionesCargadas: false,
      cargando: false,
      recarga: null,
      columnas: [],
    };
  }

  function el(inst, sufijo) {
    return document.getElementById(`${inst.prefijo}-${sufijo}`);
  }

  function showLoading(inst, on) {
    const loader = el(inst, "table-loading");
    if (!loader) return;
    const tabla = el(inst, "table");
    const thead = tabla?.querySelector("thead");
    const wrap = tabla?.closest(".table-wrap");
    if (on && wrap && thead) {
      wrap.style.setProperty("--thead-height", `${thead.offsetHeight}px`);
    }
    loader.classList.toggle("active", Boolean(on));
  }

  // ====== Filtros por encabezado ======
  function getColumnFilters(inst) {
    if (inst.columnFilters) return inst.columnFilters;
    inst.columnFilters = {};
    try {
      const stored = JSON.parse(window.localStorage.getItem(inst.storageKey) || "{}");
      if (stored && typeof stored === "object") inst.columnFilters = stored;
    } catch (error) {
      console.warn(`No se pudieron leer los filtros por columna de ${inst.area}`, error);
    }
    return inst.columnFilters;
  }

  function saveColumnFilters(inst) {
    try {
      window.localStorage.setItem(inst.storageKey, JSON.stringify(getColumnFilters(inst)));
    } catch (error) {
      console.warn(`No se pudieron guardar los filtros por columna de ${inst.area}`, error);
    }
  }

  function setColumnFilter(inst, field, value) {
    const state = getColumnFilters(inst);
    const normalized = String(value || "").trim();
    if (normalized) state[field] = normalized;
    else delete state[field];
    saveColumnFilters(inst);
  }

  function renderColumnFilterHeaders(inst) {
    const tabla = el(inst, "table");
    if (!tabla) return;
    inst.columnas = [];

    tabla.querySelectorAll("th[data-mat-filter-field]").forEach(header => {
      const field = header.dataset.matFilterField;
      inst.columnas.push(field);
      if (header.dataset.matFilterReady === "true") return;

      const label = header.textContent.trim();
      const value = getColumnFilters(inst)[field] || "";
      header.classList.add("mat-hist-column-filterable");
      header.dataset.matFilterReady = "true";
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
        <div class="mat-hist-column-filter-popover" data-mat-field="${escapeHtml(field)}">
          <input class="mat-hist-column-filter-input"
                 data-mat-field="${escapeHtml(field)}"
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

  // .mat-hist-* tambien las usa el historial de SMT, que tiene sus propios
  // listeners en document. Cada modulo actua solo sobre lo suyo.
  function closeColumnFilterPopovers(except = null) {
    document
      .querySelectorAll(".mat-hist-area-container .mat-hist-column-filter-popover.open")
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

  function syncColumnFilterControls(inst) {
    const filters = getColumnFilters(inst);
    el(inst, "table")
      ?.querySelectorAll(".mat-hist-column-filter-input")
      .forEach(input => {
        const value = filters[input.dataset.matField] || "";
        input.value = value;
        input
          .closest("th")
          ?.querySelector(".mat-hist-column-filter-btn")
          ?.classList.toggle("active", Boolean(value));
      });
  }

  function scheduleColumnFilter(inst) {
    window.clearTimeout(inst.filterTimer);
    inst.currentPage = 1;
    inst.filterTimer = window.setTimeout(() => loadData(inst, { resetPage: false }), 250);
  }

  // ====== Datos ======
  function buildQuery(inst) {
    const qs = new URLSearchParams();
    const val = sufijo => el(inst, sufijo)?.value.trim() || "";

    const desde = val("fecha-desde");
    const hasta = val("fecha-hasta");
    const material = val("material");
    const linea = val("linea");
    const resultado = val("resultado");
    const contenedor = val("contenedor");

    if (desde) qs.set("fecha_desde", desde);
    if (hasta) qs.set("fecha_hasta", hasta);
    if (material) qs.set("material", material);
    if (linea) qs.set("linea", linea);
    if (resultado) qs.set("resultado", resultado);
    if (contenedor) qs.set("contenedor", contenedor);

    Object.entries(getColumnFilters(inst)).forEach(([field, value]) => {
      if (value) qs.set(`cf_${field}`, value);
    });
    return qs;
  }

  async function loadOpciones(inst) {
    if (inst.opcionesCargadas) return;
    try {
      const response = await fetch(`/api/historial-material/${inst.area}/opciones`, {
        credentials: "same-origin",
      });
      if (!response.ok) return;
      const data = await response.json();
      const select = el(inst, "linea");
      if (!select) return;
      const actual = select.value;
      select.innerHTML =
        '<option value="">Todas</option>' +
        (data.lineas || [])
          .map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`)
          .join("");
      if (actual) select.value = actual;
      inst.opcionesCargadas = true;
    } catch (error) {
      console.warn("No se pudieron cargar las lineas", error);
    }
  }

  async function loadData(inst, opts) {
    // El fragmento se inicializa dos veces (el <script> al inyectarse y el
    // callback de cargarContenidoDinamico); la segunda cae aqui con la
    // primera peticion en vuelo. Se encola para no perder un cambio de filtro.
    if (inst.cargando) {
      inst.recarga = opts || {};
      return;
    }
    inst.cargando = true;
    inst.recarga = null;
    if (!opts || opts.resetPage !== false) inst.currentPage = 1;
    showLoading(inst, true);

    try {
      const select = el(inst, "per-page");
      const value = parseInt(select?.value || "", 10);
      if (!Number.isNaN(value) && value > 0) inst.perPage = value;

      const qs = buildQuery(inst);
      qs.set("page", String(inst.currentPage));
      qs.set("per_page", String(inst.perPage));

      const response = await fetch(
        `/api/historial-material/${inst.area}/data?${qs.toString()}`,
        { credentials: "same-origin" },
      );
      if (response.status === 401 || response.redirected) {
        notify("Sesion expirada, vuelve a iniciar sesion", "error");
        return;
      }
      if (!response.ok) throw new Error(`Error ${response.status}`);

      const data = await response.json();
      if (data.error) throw new Error(data.error);

      inst.totalRows = data.total || 0;
      inst.totalPages = Math.max(1, data.total_pages || 1);
      if (data.page) inst.currentPage = data.page;

      const count = el(inst, "record-count");
      if (count) {
        count.textContent = `${inst.totalRows} registro${inst.totalRows !== 1 ? "s" : ""}`;
      }

      renderTable(inst, data.rows || []);
      renderPagination(inst);
    } catch (error) {
      console.error(error);
      notify(error.message || "Error al cargar datos", "error");
      renderTable(inst, []);
    } finally {
      inst.cargando = false;
      showLoading(inst, false);
      if (inst.recarga) {
        const pendiente = inst.recarga;
        inst.recarga = null;
        loadData(inst, pendiente);
      }
    }
  }

  function renderTable(inst, rows) {
    const tbody = el(inst, "body");
    if (!tbody) return;

    if (!rows.length) {
      tbody.innerHTML = `<tr><td class="mat-hist-empty" colspan="${inst.columnas.length}">Sin registros para los filtros seleccionados</td></tr>`;
      return;
    }

    tbody.innerHTML = rows
      .map(row => {
        const ng = String(row.resultado || "").toUpperCase() === "NG";
        const celdas = inst.columnas
          .map(key => {
            const value = escapeHtml(row[key]);
            return `<td title="${value}">${value}</td>`;
          })
          .join("");
        return `<tr class="${ng ? "mat-hist-row-ng" : ""}">${celdas}</tr>`;
      })
      .join("");
  }

  function renderPagination(inst) {
    const wrap = el(inst, "pagination");
    if (!wrap) return;
    if (inst.totalRows <= 0) {
      wrap.style.display = "none";
      return;
    }
    wrap.style.display = "";

    const start = (inst.currentPage - 1) * inst.perPage + 1;
    const end = Math.min(inst.currentPage * inst.perPage, inst.totalRows);
    const summary = el(inst, "pagination-summary");
    if (summary) summary.textContent = `${start} - ${end} de ${inst.totalRows}`;

    const input = el(inst, "page-input");
    if (input) {
      input.value = String(inst.currentPage);
      input.max = String(inst.totalPages);
    }
    const total = el(inst, "page-total");
    if (total) total.textContent = String(inst.totalPages);

    const atFirst = inst.currentPage <= 1;
    const atLast = inst.currentPage >= inst.totalPages;
    [["page-first", atFirst], ["page-prev", atFirst],
     ["page-next", atLast], ["page-last", atLast]].forEach(([sufijo, disabled]) => {
      const boton = el(inst, sufijo);
      if (boton) boton.disabled = disabled;
    });
  }

  function gotoPage(inst, page) {
    const target = Math.max(1, Math.min(inst.totalPages, parseInt(page, 10) || 1));
    if (target === inst.currentPage) return;
    inst.currentPage = target;
    loadData(inst, { resetPage: false });
  }

  async function exportExcel(inst) {
    const url = `/api/historial-material/${inst.area}/export?${buildQuery(inst).toString()}`;
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
      anchor.download = `historial_material_${inst.area}_${Date.now()}.xlsx`;
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

  // ====== Event delegation ======
  // Un unico juego de listeners para las dos areas: el contenedor mas cercano
  // al evento dice a que instancia pertenece.
  function instanciaDe(node) {
    const container = node?.closest?.(".mat-hist-area-container");
    return container ? instancias.get(container.dataset.area) : null;
  }

  function attachListeners() {
    if (document.body.dataset.matHistListeners === "true") return;
    document.body.dataset.matHistListeners = "true";

    document.addEventListener("click", event => {
      const target = event.target;
      const inst = instanciaDe(target);

      const filterButton = target.closest?.(".mat-hist-column-filter-btn");
      if (filterButton && inst) {
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

      if (!inst) {
        // Fuera de las areas: si el click cayo en otro modulo que usa estas
        // clases (historial de SMT), no tocar nada; el suyo se encarga.
        if (!target.closest?.(".mat-hist-column-filter-popover")) {
          closeColumnFilterPopovers();
        }
        return;
      }

      if (target.closest(".mat-hist-column-filter-clear")) {
        event.preventDefault();
        const field = target.closest(".mat-hist-column-filter-popover")?.dataset.matField;
        if (field) {
          setColumnFilter(inst, field, "");
          syncColumnFilterControls(inst);
          scheduleColumnFilter(inst);
        }
        return;
      }

      if (target.closest(".mat-hist-column-filter-clear-all")) {
        event.preventDefault();
        inst.columnFilters = {};
        saveColumnFilters(inst);
        syncColumnFilterControls(inst);
        closeColumnFilterPopovers();
        scheduleColumnFilter(inst);
        return;
      }

      if (target.closest(".mat-hist-column-filter-popover")) return;
      closeColumnFilterPopovers();

      const p = inst.prefijo;
      if (target.closest(`#${p}-btn-consultar`)) {
        event.preventDefault();
        loadData(inst);
      } else if (target.closest(`#${p}-btn-export`)) {
        event.preventDefault();
        exportExcel(inst);
      } else if (target.closest(`#${p}-page-first`)) {
        gotoPage(inst, 1);
      } else if (target.closest(`#${p}-page-prev`)) {
        gotoPage(inst, inst.currentPage - 1);
      } else if (target.closest(`#${p}-page-next`)) {
        gotoPage(inst, inst.currentPage + 1);
      } else if (target.closest(`#${p}-page-last`)) {
        gotoPage(inst, inst.totalPages);
      }
    });

    document.addEventListener("input", event => {
      const input = event.target.closest?.(".mat-hist-column-filter-input");
      const inst = instanciaDe(input);
      if (!input || !inst) return;
      setColumnFilter(inst, input.dataset.matField, input.value);
      input
        .closest("th")
        ?.querySelector(".mat-hist-column-filter-btn")
        ?.classList.toggle("active", Boolean(input.value.trim()));
      scheduleColumnFilter(inst);
    });

    document.addEventListener("change", event => {
      const inst = instanciaDe(event.target);
      if (!inst) return;
      const sufijo = event.target.id.replace(`${inst.prefijo}-`, "");
      if (sufijo === "per-page") {
        inst.perPage = parseInt(event.target.value, 10) || 1000;
        loadData(inst);
      } else if (["linea", "resultado"].includes(sufijo)) {
        loadData(inst);
      } else if (sufijo === "page-input") {
        gotoPage(inst, event.target.value);
      }
    });

    document.addEventListener("keydown", event => {
      if (event.key === "Escape") {
        closeColumnFilterPopovers();
        return;
      }
      if (event.key !== "Enter") return;
      const inst = instanciaDe(event.target);
      if (!inst) return;
      const sufijo = event.target.id.replace(`${inst.prefijo}-`, "");
      if (["material", "contenedor", "fecha-desde", "fecha-hasta"].includes(sufijo)) {
        event.preventDefault();
        loadData(inst);
      } else if (sufijo === "page-input") {
        event.preventDefault();
        gotoPage(inst, event.target.value);
      }
    });
  }

  function setDefaultDates(inst) {
    const hoy = new Date().toISOString().split("T")[0];
    const desde = el(inst, "fecha-desde");
    const hasta = el(inst, "fecha-hasta");
    if (desde && !desde.value) desde.value = hoy;
    if (hasta && !hasta.value) hasta.value = hoy;
  }

  // ====== Inicializacion idempotente (WF_007) ======
  function init(area) {
    // Sin `area` inicializa todo contenedor presente: asi sirve tanto al
    // callback de cargarContenidoDinamico como a la auto-ejecucion del script.
    const contenedores = document.querySelectorAll(
      area
        ? `.mat-hist-area-container[data-area="${area}"]`
        : ".mat-hist-area-container",
    );
    contenedores.forEach(container => {
      const clave = container.dataset.area;
      let inst = instancias.get(clave);
      if (!inst) {
        inst = crearInstancia(clave, container.dataset.prefijo);
        instancias.set(clave, inst);
      } else {
        inst.prefijo = container.dataset.prefijo;
      }
      renderColumnFilterHeaders(inst);
      syncColumnFilterControls(inst);
      attachListeners();
      setDefaultDates(inst);
      loadOpciones(inst);
      loadData(inst);
    });
  }

  function cleanup(area) {
    closeColumnFilterPopovers();
    instancias.forEach(inst => {
      if (area && inst.area !== area) return;
      window.clearTimeout(inst.filterTimer);
      showLoading(inst, false);
    });
  }

  window.initHistorialMaterialArea = init;
  window.limpiarHistorialMaterialArea = cleanup;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init());
  } else {
    init();
  }
})();
