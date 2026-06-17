/* Historial de Operadores por Maquina (vista historial_estaciones_qa).
 * Modulo de SOLO LECTURA: sesiones de operadores en estaciones de calidad.
 */
(function () {
  "use strict";

  const STYLESHEET_ID = "historial-operadores-maquina-css";
  const STYLESHEET_HREF = "/static/css/historial_operadores_maquina.css?v=20260617a";
  const API_BASE = "/api/control_resultados/historial_operadores_maquina";

  // Etiqueta y clase por estado; default "Cerrada" para Closed/AutoClosed.
  const STATUS_TEXT = { Open: "En curso", Ajuste: "Ajuste" };
  const STATUS_CLASS = { Open: "hopm-status--open", Ajuste: "hopm-status--ajuste" };

  let records = [];

  function ensureStylesheet() {
    const existing = document.getElementById(STYLESHEET_ID);
    if (existing) {
      if (existing.getAttribute("href") !== STYLESHEET_HREF) {
        existing.setAttribute("href", STYLESHEET_HREF);
      }
      return;
    }
    const link = document.createElement("link");
    link.id = STYLESHEET_ID;
    link.rel = "stylesheet";
    link.href = STYLESHEET_HREF;
    document.head.appendChild(link);
  }

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function getElements(root) {
    return {
      root,
      filters: root.querySelector("#hopm-filters"),
      search: root.querySelector("#hopm-search"),
      typeFilter: root.querySelector("#hopm-type-filter"),
      statusFilter: root.querySelector("#hopm-status-filter"),
      dateFrom: root.querySelector("#hopm-date-from"),
      dateTo: root.querySelector("#hopm-date-to"),
      clear: root.querySelector("#hopm-clear"),
      exportBtn: root.querySelector("#hopm-export"),
      refresh: root.querySelector("#hopm-refresh"),
      loading: root.querySelector("#hopm-loading"),
      tbody: root.querySelector("#hopm-tbody"),
      total: root.querySelector("#hopm-total"),
      open: root.querySelector("#hopm-open"),
      closed: root.querySelector("#hopm-closed"),
    };
  }

  function notify(message, type) {
    const old = document.querySelector(".hopm-toast");
    if (old) old.remove();
    const toast = document.createElement("div");
    toast.className = `hopm-toast hopm-toast--${type || "info"}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 4200);
  }

  function setLoading(elements, loading) {
    if (elements.loading) elements.loading.hidden = !loading;
    elements.root.classList.toggle("is-loading", loading);
    elements.root.querySelectorAll("button, input, select").forEach((el) => {
      el.disabled = loading;
    });
  }

  async function fetchJson(url) {
    const response = await fetch(url, { credentials: "same-origin" });
    const text = await response.text();
    let payload = {};
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch (error) {
        payload = {};
      }
    }
    if (!response.ok || payload.success === false) {
      throw new Error(payload.error || `Solicitud fallida (${response.status})`);
    }
    return payload;
  }

  function buildListUrl(elements, base) {
    const params = new URLSearchParams();
    const q = elements.search.value.trim();
    const tipo = elements.typeFilter.value;
    const estado = elements.statusFilter.value;
    const fechaDesde = elements.dateFrom.value;
    const fechaHasta = elements.dateTo.value;
    if (q) params.set("q", q);
    if (tipo) params.set("tipo", tipo);
    if (estado) params.set("estado", estado);
    if (fechaDesde) params.set("fecha_desde", fechaDesde);
    if (fechaHasta) params.set("fecha_hasta", fechaHasta);
    const query = params.toString();
    return `${base || API_BASE}${query ? `?${query}` : ""}`;
  }

  function updateStats(elements) {
    const open = records.filter((item) => item.estado === "Open").length;
    elements.total.textContent = String(records.length);
    elements.open.textContent = String(open);
    elements.closed.textContent = String(records.length - open);
  }

  function renderTable(elements) {
    updateStats(elements);
    if (!records.length) {
      elements.tbody.innerHTML = '<tr><td colspan="10" class="hopm-empty">Sin sesiones registradas</td></tr>';
      return;
    }
    elements.tbody.innerHTML = records
      .map((row) => {
        const statusClass = STATUS_CLASS[row.estado] || "hopm-status--closed";
        const statusText = STATUS_TEXT[row.estado] || "Cerrada";
        const usuarioTitle = row.username && row.username !== row.usuario
          ? ` title="Badge: ${esc(row.username)}"`
          : "";
        return `
          <tr>
            <td>${esc(row.linea || "-")}</td>
            <td><span class="hopm-code">${esc(row.estacion)}</span></td>
            <td>${esc(row.nombre_estacion)}</td>
            <td><span class="hopm-type">${esc(row.tipo)}</span></td>
            <td${usuarioTitle}>${esc(row.usuario || "-")}</td>
            <td>${esc(row.fecha)}</td>
            <td>${esc(row.hora_entrada || "-")}</td>
            <td>${esc(row.hora_salida || "-")}</td>
            <td>${esc(row.duracion)}</td>
            <td><span class="hopm-status ${statusClass}">${statusText}</span></td>
          </tr>
        `;
      })
      .join("");
  }

  async function loadSessions(elements) {
    setLoading(elements, true);
    try {
      const payload = await fetchJson(buildListUrl(elements));
      records = payload.records || [];
      renderTable(elements);
    } catch (error) {
      records = [];
      renderTable(elements);
      notify(error.message || "No fue posible cargar el historial.", "error");
    } finally {
      setLoading(elements, false);
    }
  }

  function bindEvents(elements) {
    elements.filters.addEventListener("submit", (event) => {
      event.preventDefault();
      loadSessions(elements);
    });

    elements.typeFilter.addEventListener("change", () => loadSessions(elements));
    elements.statusFilter.addEventListener("change", () => loadSessions(elements));
    elements.clear.addEventListener("click", () => {
      elements.search.value = "";
      elements.typeFilter.value = "";
      elements.statusFilter.value = "";
      elements.dateFrom.value = "";
      elements.dateTo.value = "";
      loadSessions(elements);
    });
    elements.refresh.addEventListener("click", () => loadSessions(elements));
    elements.exportBtn.addEventListener("click", () => {
      window.open(buildListUrl(elements, `${API_BASE}/export`), "_blank");
    });
  }

  function inicializarHistorialOperadoresMaquina(root) {
    ensureStylesheet();
    const moduleRoot = typeof root === "string" ? document.querySelector(root) : root;
    if (!moduleRoot || moduleRoot.dataset.initialized === "true") return;
    moduleRoot.dataset.initialized = "true";
    const elements = getElements(moduleRoot);
    bindEvents(elements);
    loadSessions(elements);
  }

  window.inicializarHistorialOperadoresMaquina = inicializarHistorialOperadoresMaquina;
  document.querySelectorAll("#hopm-module").forEach(inicializarHistorialOperadoresMaquina);
})();
