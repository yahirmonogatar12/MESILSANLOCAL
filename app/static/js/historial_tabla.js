/* Tabla de historial con filtros, paginacion y export (WF_002 / WF_003 / WF_004).
 *
 * Generico: el fragmento declara en su contenedor raiz que modulo es, a que
 * API pega y que filtros tiene, y este archivo hace el resto. Hoy lo usan:
 *   - Historial de cambio de material de IMD / ASSY
 *     (historial_material_area_ajax.html + historial_material_areas.py)
 *   - Process interlock History
 *     (process_interlock_history_ajax.html + process_interlock_history.py)
 *
 * Contrato del contenedor:
 *   class="hist-tbl-area-container"
 *   data-modulo   clave de la instancia (unica por modulo/area)
 *   data-prefijo  prefijo de los IDs del fragmento
 *   data-api-base base de los endpoints: <base>/data, /opciones, /export
 *   data-filtros  "sufijo-del-input:query_param,..." de los filtros de la tarjeta
 *   data-archivo  nombre base del .xlsx exportado
 *
 * Una instancia de estado por modulo, porque el portal permite tener varias
 * pestanas abiertas a la vez. Todo dentro de un IIFE: ict.js y el JS del
 * historial de SMT declaran helpers globales con los mismos nombres.
 */
(function () {
  "use strict";

  const CSS_VERSION = "20260922f";

  // ====== WF_004 capa 2: asegurar CSS en <head> ======
  // MainTemplate.html ya los declara con cache-busting. Esta capa cubre que el
  // fragmento se cargue sin pasar por el layout, y que el portal lleve abierto
  // desde antes del deploy (el <link> apuntaria a la version anterior y el
  // navegador reusaria el CSS viejo cacheado con esa URL).
  const MODULE_CSS_ID = "historial-tablas-css";
  [
    { id: "ilsan-theme-css", href: "/static/css/ilsan-theme.css?v=20260522a" },
    { id: "ict-css", href: "/static/css/ict.css?v=20260630a" },
    { id: MODULE_CSS_ID, href: `/static/css/historial_tablas.css?v=${CSS_VERSION}` },
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

  function crearInstancia(container) {
    const modulo = container.dataset.modulo;
    return {
      modulo,
      prefijo: container.dataset.prefijo,
      apiBase: container.dataset.apiBase,
      archivo: container.dataset.archivo || modulo,
      // "fecha-desde:fecha_desde,linea:linea" -> [["fecha-desde","fecha_desde"],...]
      filtros: (container.dataset.filtros || "")
        .split(",")
        .map(par => par.trim())
        .filter(Boolean)
        .map(par => par.split(":")),
      storageKey: `historialTabla_${modulo}_columnFilters`,
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
      console.warn(`No se pudieron leer los filtros por columna de ${inst.modulo}`, error);
    }
    return inst.columnFilters;
  }

  function saveColumnFilters(inst) {
    try {
      window.localStorage.setItem(inst.storageKey, JSON.stringify(getColumnFilters(inst)));
    } catch (error) {
      console.warn(`No se pudieron guardar los filtros por columna de ${inst.modulo}`, error);
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

    tabla.querySelectorAll("th[data-hist-filter-field]").forEach(header => {
      const field = header.dataset.histFilterField;
      inst.columnas.push(field);
      if (header.dataset.histFilterReady === "true") return;

      const label = header.textContent.trim();
      const value = getColumnFilters(inst)[field] || "";
      header.classList.add("hist-tbl-column-filterable");
      header.dataset.histFilterReady = "true";
      header.innerHTML = `
        <div class="hist-tbl-column-header">
          <span>${escapeHtml(label)}</span>
          <button class="hist-tbl-column-filter-btn${value ? " active" : ""}"
                  type="button"
                  aria-label="Filtrar ${escapeHtml(label)}"
                  aria-expanded="false"
                  title="Filtrar ${escapeHtml(label)}">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M3 5h18l-7 8v5l-4 2v-7L3 5z"></path>
            </svg>
          </button>
        </div>
        <div class="hist-tbl-column-filter-popover" data-hist-field="${escapeHtml(field)}">
          <input class="hist-tbl-column-filter-input"
                 data-hist-field="${escapeHtml(field)}"
                 value="${escapeHtml(value)}"
                 placeholder="Buscar..."
                 aria-label="Buscar en ${escapeHtml(label)}"
                 autocomplete="off">
          <div class="hist-tbl-column-filter-actions">
            <button class="hist-tbl-column-filter-clear" type="button">Limpiar</button>
            <button class="hist-tbl-column-filter-clear-all" type="button">Todos</button>
          </div>
        </div>`;
    });
  }

  // .hist-tbl-* tambien las usa el historial de SMT, que tiene sus propios
  // listeners en document. Cada modulo actua solo sobre lo suyo.
  function closeColumnFilterPopovers(except = null) {
    document
      .querySelectorAll(".hist-tbl-area-container .hist-tbl-column-filter-popover.open")
      .forEach(popover => {
      if (popover === except) return;
      popover.classList.remove("open");
      const th = popover.closest("th");
      th?.classList.remove("filter-open");
      const button = th?.querySelector(".hist-tbl-column-filter-btn");
      button?.classList.remove("open");
      button?.setAttribute("aria-expanded", "false");
    });
  }

  function syncColumnFilterControls(inst) {
    const filters = getColumnFilters(inst);
    el(inst, "table")
      ?.querySelectorAll(".hist-tbl-column-filter-input")
      .forEach(input => {
        const value = filters[input.dataset.histField] || "";
        input.value = value;
        input
          .closest("th")
          ?.querySelector(".hist-tbl-column-filter-btn")
          ?.classList.toggle("active", Boolean(value));
      });
  }

  function scheduleColumnFilter(inst) {
    window.clearTimeout(inst.filterTimer);
    inst.currentPage = 1;
    inst.filterTimer = window.setTimeout(() => loadData(inst, { resetPage: false }), 250);
  }

  // ====== Datos ======
  function esFiltro(inst, sufijo) {
    return inst.filtros.some(([s]) => s === sufijo);
  }

  function buildQuery(inst) {
    const qs = new URLSearchParams();
    inst.filtros.forEach(([sufijo, param]) => {
      const control = el(inst, sufijo);
      if (!control) return;
      const valor =
        control.type === "checkbox"
          ? (control.checked ? "1" : "")
          : control.value.trim();
      if (valor) qs.set(param, valor);
    });

    Object.entries(getColumnFilters(inst)).forEach(([field, value]) => {
      if (value) qs.set(`cf_${field}`, value);
    });
    return qs;
  }

  async function loadOpciones(inst) {
    if (inst.opcionesCargadas) return;
    try {
      const response = await fetch(`${inst.apiBase}/opciones`, {
        credentials: "same-origin",
      });
      if (!response.ok) return;
      const data = await response.json();
      // Cada clave de la respuesta nombra el sufijo del select que rellena.
      Object.entries(data).forEach(([sufijo, valores]) => {
        const select = el(inst, sufijo);
        if (!select || !Array.isArray(valores)) return;
        const actual = select.value;
        // Conserva la etiqueta del "sin filtro" que puso el template.
        const todos = select.querySelector('option[value=""]')?.textContent?.trim() || "Todos";
        select.innerHTML =
          `<option value="">${escapeHtml(todos)}</option>` +
          valores
            .map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`)
            .join("");
        if (actual) select.value = actual;
      });
      inst.opcionesCargadas = true;
    } catch (error) {
      console.warn("No se pudieron cargar las opciones de los filtros", error);
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
        `${inst.apiBase}/data?${qs.toString()}`,
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
      // Opcional: solo los modulos que lo declaran (p.ej. tiempo detenido).
      const agregado = el(inst, "total-detenido");
      if (agregado && data.total_detenido !== undefined) {
        agregado.textContent = `${data.total_detenido} detenidos`;
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
      tbody.innerHTML = `<tr><td class="hist-tbl-empty" colspan="${inst.columnas.length}">Sin registros para los filtros seleccionados</td></tr>`;
      return;
    }

    tbody.innerHTML = rows
      .map(row => {
        // El backend decide que fila se resalta (_destacar): cada modulo sabe
        // que es "malo" en su dominio.
        const ng = row._destacar === true;
        const celdas = inst.columnas
          .map(key => {
            const value = escapeHtml(row[key]);
            return `<td title="${value}">${value}</td>`;
          })
          .join("");
        return `<tr class="${ng ? "hist-tbl-row-ng" : ""}">${celdas}</tr>`;
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
    const url = `${inst.apiBase}/export?${buildQuery(inst).toString()}`;
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
      anchor.download = `${inst.archivo}_${Date.now()}.xlsx`;
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
    const container = node?.closest?.(".hist-tbl-area-container");
    return container ? instancias.get(container.dataset.modulo) : null;
  }

  function attachListeners() {
    if (document.body.dataset.histTblListeners === "true") return;
    document.body.dataset.histTblListeners = "true";

    document.addEventListener("click", event => {
      const target = event.target;
      const inst = instanciaDe(target);

      const filterButton = target.closest?.(".hist-tbl-column-filter-btn");
      if (filterButton && inst) {
        event.preventDefault();
        const th = filterButton.closest("th");
        const popover = th?.querySelector(".hist-tbl-column-filter-popover");
        if (!popover) return;
        const shouldOpen = !popover.classList.contains("open");
        closeColumnFilterPopovers();
        if (shouldOpen) {
          popover.classList.add("open");
          th.classList.add("filter-open");
          filterButton.classList.add("open");
          filterButton.setAttribute("aria-expanded", "true");
          popover.querySelector(".hist-tbl-column-filter-input")?.focus();
        }
        return;
      }

      if (!inst) {
        // Fuera de las areas: si el click cayo en otro modulo que usa estas
        // clases (historial de SMT), no tocar nada; el suyo se encarga.
        if (!target.closest?.(".hist-tbl-column-filter-popover")) {
          closeColumnFilterPopovers();
        }
        return;
      }

      if (target.closest(".hist-tbl-column-filter-clear")) {
        event.preventDefault();
        const field = target.closest(".hist-tbl-column-filter-popover")?.dataset.histField;
        if (field) {
          setColumnFilter(inst, field, "");
          syncColumnFilterControls(inst);
          scheduleColumnFilter(inst);
        }
        return;
      }

      if (target.closest(".hist-tbl-column-filter-clear-all")) {
        event.preventDefault();
        inst.columnFilters = {};
        saveColumnFilters(inst);
        syncColumnFilterControls(inst);
        closeColumnFilterPopovers();
        scheduleColumnFilter(inst);
        return;
      }

      if (target.closest(".hist-tbl-column-filter-popover")) return;
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
      const input = event.target.closest?.(".hist-tbl-column-filter-input");
      const inst = instanciaDe(input);
      if (!input || !inst) return;
      setColumnFilter(inst, input.dataset.histField, input.value);
      input
        .closest("th")
        ?.querySelector(".hist-tbl-column-filter-btn")
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
      } else if (sufijo === "page-input") {
        gotoPage(inst, event.target.value);
      } else if (
        esFiltro(inst, sufijo) &&
        (event.target.tagName === "SELECT" || event.target.type === "checkbox")
      ) {
        // Los <input> de texto esperan Enter; select y checkbox recargan solos.
        loadData(inst);
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
      if (esFiltro(inst, sufijo)) {
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
  function init(modulo) {
    // Sin `modulo` inicializa todo contenedor presente: asi sirve tanto al
    // callback de cargarContenidoDinamico como a la auto-ejecucion del script.
    const contenedores = document.querySelectorAll(
      modulo
        ? `.hist-tbl-area-container[data-modulo="${modulo}"]`
        : ".hist-tbl-area-container",
    );
    contenedores.forEach(container => {
      const clave = container.dataset.modulo;
      // Siempre desde el contenedor vivo: el fragmento se recrea en cada
      // carga AJAX y sus data-* mandan sobre el estado anterior.
      const nueva = crearInstancia(container);
      const inst = Object.assign(instancias.get(clave) || nueva, {
        prefijo: nueva.prefijo,
        apiBase: nueva.apiBase,
        archivo: nueva.archivo,
        filtros: nueva.filtros,
      });
      instancias.set(clave, inst);
      renderColumnFilterHeaders(inst);
      syncColumnFilterControls(inst);
      attachListeners();
      setDefaultDates(inst);
      loadOpciones(inst);
      loadData(inst);
    });
  }

  function cleanup(modulo) {
    closeColumnFilterPopovers();
    instancias.forEach(inst => {
      if (modulo && inst.modulo !== modulo) return;
      window.clearTimeout(inst.filterTimer);
      showLoading(inst, false);
    });
  }

  window.initHistorialTabla = init;
  window.limpiarHistorialTabla = cleanup;
  // Alias historico: las funciones mostrar* de IMD/ASSY lo llaman por este nombre.
  window.initHistorialMaterialArea = init;
  window.limpiarHistorialMaterialArea = cleanup;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init());
  } else {
    init();
  }
})();
