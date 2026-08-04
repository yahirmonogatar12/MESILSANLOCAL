(function () {
  "use strict";

  const VERSION = "20260804e";
  const STYLESHEET_ID = "almacen-embarques-oqc-pendientes-css";
  const STYLESHEET_HREF = `/static/css/almacen_embarques_oqc_pendientes.css?v=${VERSION}`;
  const API_SUMMARY = "/api/almacen-embarques/qa-pendientes";
  const API_DETAIL = "/api/almacen-embarques/qa-pendientes/cajas";

  let lastEntryRows = [];
  let lastReleaseRows = [];

  function ensureStyles() {
    const current = document.getElementById(STYLESHEET_ID);
    if (current) {
      if (!current.getAttribute("href")?.includes(VERSION)) {
        current.setAttribute("href", STYLESHEET_HREF);
      }
      return;
    }

    const link = document.createElement("link");
    link.id = STYLESHEET_ID;
    link.rel = "stylesheet";
    link.href = STYLESHEET_HREF;
    document.head.appendChild(link);
  }

  function root() {
    return document.getElementById("ae-oqc-pending-module");
  }

  function byId(id) {
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
    const number = Number(value || 0);
    return Number.isFinite(number) ? number.toLocaleString("en-US") : "0";
  }

  function formatDate(value) {
    if (!value) return "-";
    return String(value).replace("T", " ").slice(0, 19);
  }

  function todayValue() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function setDefaultDates(force) {
    const value = todayValue();
    const dateFrom = byId("ae-oqc-pending-date-from");
    const dateTo = byId("ae-oqc-pending-date-to");
    if (dateFrom && (force || !dateFrom.value)) dateFrom.value = value;
    if (dateTo && (force || !dateTo.value)) dateTo.value = value;
  }

  function setStatus(message, type) {
    const el = byId("ae-oqc-pending-status");
    if (!el) return;
    el.textContent = message || "";
    el.classList.toggle("is-error", type === "error");
  }

  function buildParams(extra) {
    setDefaultDates(false);
    const params = new URLSearchParams();
    const dateFrom = byId("ae-oqc-pending-date-from")?.value || "";
    const dateTo = byId("ae-oqc-pending-date-to")?.value || "";
    const search = byId("ae-oqc-pending-search")?.value.trim() || "";

    if (dateFrom) params.set("fecha_desde", dateFrom);
    if (dateTo) params.set("fecha_hasta", dateTo);
    if (search) params.set("q", search);

    Object.entries(extra || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        params.set(key, value);
      }
    });

    return params;
  }

  async function fetchJson(url) {
    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });

    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      throw new Error(`Respuesta no JSON (${response.status})`);
    }

    const data = await response.json();
    if (!response.ok || data.success === false) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    return data;
  }

  function setCount(countElId, qtyElId, rows, summary) {
    const countEl = byId(countElId);
    const qtyEl = byId(qtyElId);
    const parts = Number(summary?.pending_parts ?? rows.length ?? 0);
    const qty = Number(summary?.pending_quantity ?? 0);
    if (countEl) {
      countEl.textContent = `${formatNumber(parts)} parte${parts === 1 ? "" : "s"}`;
    }
    if (qtyEl) {
      qtyEl.textContent = `${formatNumber(qty)} ea`;
    }
  }

  function renderEntryRows(rows, summary) {
    const tbody = byId("ae-oqc-pending-tbody");
    if (!tbody) return;
    setCount("ae-oqc-pending-count", "ae-oqc-pending-entry-qty-count", rows, summary);

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="ae-oqc-pending-empty">No hay pendiente de entrada a Almacen con los filtros actuales.</td></tr>';
      return;
    }

    tbody.innerHTML = rows
      .map((row) => `
        <tr>
          <td class="ae-oqc-pending-code">${escapeHtml(row.part_number)}</td>
          <td title="${escapeHtml(row.product_model)}">${escapeHtml(row.product_model || "-")}</td>
          <td>${formatNumber(row.pending_boxes)}</td>
          <td>${formatNumber(row.pending_quantity)}</td>
          <td>
            <button
              type="button"
              class="ae-oqc-pending-detail-btn"
              data-detail-type="entrada"
              data-part-number="${escapeHtml(row.part_number)}"
            >
              Ver cajas
            </button>
          </td>
        </tr>
      `)
      .join("");
  }

  function renderReleaseRows(rows, summary) {
    const tbody = byId("ae-oqc-release-pending-tbody");
    if (!tbody) return;
    setCount("ae-oqc-release-pending-count", "ae-oqc-release-pending-qty-count", rows, summary);

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="ae-oqc-pending-empty">No hay pendiente de liberacion OQC con los filtros actuales.</td></tr>';
      return;
    }

    tbody.innerHTML = rows
      .map((row) => `
        <tr>
          <td class="ae-oqc-pending-code">${escapeHtml(row.part_number)}</td>
          <td title="${escapeHtml(row.product_model)}">${escapeHtml(row.product_model || "-")}</td>
          <td>${formatNumber(row.pending_boxes)}</td>
          <td>${formatNumber(row.pending_quantity)}</td>
          <td>
            <button
              type="button"
              class="ae-oqc-pending-detail-btn"
              data-detail-type="liberacion"
              data-part-number="${escapeHtml(row.part_number)}"
            >
              Ver cajas
            </button>
          </td>
        </tr>
      `)
      .join("");
  }

  async function loadSummary() {
    const moduleRoot = root();
    if (!moduleRoot) return;

    moduleRoot.classList.add("is-loading");
    setStatus("Consultando pendientes...");

    try {
      const params = buildParams({ limit: 1000 });
      const data = await fetchJson(`${API_SUMMARY}?${params.toString()}`);
      lastEntryRows = data.entry?.rows || [];
      lastReleaseRows = data.release?.rows || [];
      renderEntryRows(lastEntryRows, data.entry?.summary || {});
      renderReleaseRows(lastReleaseRows, data.release?.summary || {});
      setStatus("Actualizado");
    } catch (error) {
      console.error("Error cargando pendientes QA:", error);
      renderEntryRows([], {});
      renderReleaseRows([], {});
      setStatus(error.message || "No fue posible cargar los pendientes.", "error");
    } finally {
      moduleRoot.classList.remove("is-loading");
    }
  }

  function detailMeta(type) {
    if (type === "liberacion") {
      return {
        title: "Detalle pendiente liberacion OQC",
        loadingColspan: 6,
        empty: "No hay cajas pendientes de liberacion OQC para este numero de parte.",
        header: `
          <tr>
            <th>Box ID</th>
            <th>Pendiente</th>
            <th>LQC</th>
            <th>OQC</th>
            <th>Ultimo LQC</th>
            <th>Linea</th>
          </tr>
        `,
      };
    }
    return {
      title: "Detalle pendiente de entrada Almacen",
      loadingColspan: 4,
      empty: "No hay cajas pendientes de entrada para este numero de parte.",
      header: `
        <tr>
          <th>Box ID</th>
          <th>Cantidad</th>
          <th>Folio OQC</th>
          <th>Liberado</th>
        </tr>
      `,
    };
  }

  function setDetailHeader(type) {
    const head = byId("ae-oqc-pending-detail-head");
    const meta = detailMeta(type);
    if (head) head.innerHTML = meta.header;
    return meta;
  }

  function openModal(type, partNumber) {
    const modal = byId("ae-oqc-pending-modal");
    if (!modal) return;
    const meta = setDetailHeader(type);
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    const title = byId("ae-oqc-pending-modal-title");
    const subtitle = byId("ae-oqc-pending-modal-subtitle");
    if (title) title.textContent = meta.title;
    if (subtitle) subtitle.textContent = partNumber || "";
  }

  function closeModal() {
    const modal = byId("ae-oqc-pending-modal");
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
  }

  function renderDetailBoxes(type, boxes) {
    const tbody = byId("ae-oqc-pending-detail-tbody");
    const count = byId("ae-oqc-pending-detail-count");
    const qty = byId("ae-oqc-pending-detail-qty");
    const meta = setDetailHeader(type);
    if (!tbody) return;

    const totalQty = boxes.reduce((sum, box) => sum + Number(box.pending_quantity || box.quantity || 0), 0);
    if (count) count.textContent = `${formatNumber(boxes.length)} caja${boxes.length === 1 ? "" : "s"}`;
    if (qty) qty.textContent = `${formatNumber(totalQty)} ea`;

    if (!boxes.length) {
      tbody.innerHTML = `<tr><td colspan="${meta.loadingColspan}" class="ae-oqc-pending-empty">${escapeHtml(meta.empty)}</td></tr>`;
      return;
    }

    if (type === "liberacion") {
      tbody.innerHTML = boxes
        .map((box) => `
          <tr>
            <td class="ae-oqc-pending-code">${escapeHtml(box.box_code)}</td>
            <td>${formatNumber(box.pending_quantity)}</td>
            <td>${formatNumber(box.lqc_quantity)}</td>
            <td>${formatNumber(box.oqc_quantity)}</td>
            <td>${escapeHtml(formatDate(box.last_lqc_scan))}</td>
            <td title="${escapeHtml([box.lineas, box.lotes].filter(Boolean).join(" | "))}">
              ${escapeHtml(box.lineas || "-")}
            </td>
          </tr>
        `)
        .join("");
      return;
    }

    tbody.innerHTML = boxes
      .map((box) => `
        <tr>
          <td class="ae-oqc-pending-code">${escapeHtml(box.box_code)}</td>
          <td>${formatNumber(box.quantity)}</td>
          <td>${escapeHtml(box.oqc_folio || "-")}</td>
          <td>${escapeHtml(formatDate(box.released_at))}</td>
        </tr>
      `)
      .join("");
  }

  async function loadDetail(type, partNumber) {
    const normalizedType = type === "liberacion" ? "liberacion" : "entrada";
    openModal(normalizedType, partNumber);
    const meta = detailMeta(normalizedType);
    const tbody = byId("ae-oqc-pending-detail-tbody");
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="${meta.loadingColspan}" class="ae-oqc-pending-empty">Cargando cajas pendientes...</td></tr>`;
    }
    const count = byId("ae-oqc-pending-detail-count");
    const qty = byId("ae-oqc-pending-detail-qty");
    if (count) count.textContent = "0 cajas";
    if (qty) qty.textContent = "0 ea";

    try {
      const params = buildParams({ part_number: partNumber, tipo: normalizedType, limit: 5000 });
      const data = await fetchJson(`${API_DETAIL}?${params.toString()}`);
      renderDetailBoxes(normalizedType, data.boxes || []);
    } catch (error) {
      console.error("Error cargando detalle QA:", error);
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="${meta.loadingColspan}" class="ae-oqc-pending-empty">${escapeHtml(error.message || "No fue posible cargar el detalle.")}</td></tr>`;
      }
    }
  }

  function clearFilters() {
    const search = byId("ae-oqc-pending-search");
    setDefaultDates(true);
    if (search) search.value = "";
    loadSummary();
  }

  function bindEvents() {
    const moduleRoot = root();
    if (!moduleRoot || moduleRoot.dataset.aeOqcPendingBound === "true") return;

    moduleRoot.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : event.target?.parentElement;
      if (!target) return;
      const searchButton = target.closest("#ae-oqc-pending-search-btn");
      const clearButton = target.closest("#ae-oqc-pending-clear-btn");
      const detailButton = target.closest(".ae-oqc-pending-detail-btn");
      const closeButton = target.closest("[data-ae-oqc-pending-close]");

      if (searchButton) {
        event.preventDefault();
        loadSummary();
        return;
      }
      if (clearButton) {
        event.preventDefault();
        clearFilters();
        return;
      }
      if (detailButton) {
        event.preventDefault();
        loadDetail(detailButton.dataset.detailType || "entrada", detailButton.dataset.partNumber || "");
        return;
      }
      if (closeButton) {
        event.preventDefault();
        closeModal();
      }
    });

    moduleRoot.addEventListener("keydown", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (event.key === "Enter" && target?.matches("input")) {
        event.preventDefault();
        loadSummary();
      }
      if (event.key === "Escape") {
        closeModal();
      }
    });

    moduleRoot.dataset.aeOqcPendingBound = "true";
  }

  function init() {
    ensureStyles();
    setDefaultDates(false);
    bindEvents();
    loadSummary();
  }

  window.inicializarAlmacenEmbarquesPendientesOQCAjax = init;
  window.inicializarAlmacenEmbarquesPendientesQAAjax = init;
  window.limpiarAlmacenEmbarquesPendientesOQC = closeModal;
  window.limpiarAlmacenEmbarquesPendientesQA = closeModal;

  if (document.readyState === "interactive" || document.readyState === "complete") {
    setTimeout(() => {
      if (root()) init();
    }, 50);
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      if (root()) init();
    });
  }
})();
