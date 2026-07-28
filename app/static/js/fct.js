(function () {
  "use strict";

  const state = {
    page: 1,
    perPage: 1000,
    totalPages: 1,
    currentStepsHash: "",
    currentStepsSerial: "",
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function todayIso() {
    const date = new Date();
    date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
    return date.toISOString().slice(0, 10);
  }

  function notify(message, type) {
    if (typeof window.mostrarNotificacion === "function") {
      window.mostrarNotificacion(message, type || "info");
      return;
    }
    if (type === "error") console.error(message);
    else console.log(message);
  }

  function setLoading(id, active) {
    const loader = document.getElementById(id);
    if (!loader) return;
    loader.classList.toggle("active", Boolean(active));
  }

  function setDefaultDates() {
    const today = todayIso();
    const desde = document.getElementById("fct-filter-fecha-desde");
    const hasta = document.getElementById("fct-filter-fecha-hasta");
    if (desde && !desde.value) desde.value = today;
    if (hasta && !hasta.value) hasta.value = today;
  }

  function buildQuery(includePagination) {
    const query = new URLSearchParams();
    const fields = [
      ["fecha_desde", "fct-filter-fecha-desde"],
      ["fecha_hasta", "fct-filter-fecha-hasta"],
      ["no_parte", "fct-filter-no-parte"],
      ["linea", "fct-filter-linea"],
      ["estacion", "fct-filter-estacion"],
      ["resultado", "fct-filter-resultado"],
      ["serial_like", "fct-filter-serial"],
    ];
    fields.forEach(([key, id]) => {
      const value = document.getElementById(id)?.value?.trim();
      if (value) query.set(key, value);
    });
    if (includePagination) {
      query.set("page", String(state.page));
      query.set("per_page", String(state.perPage));
    }
    return query;
  }

  async function fetchJson(url) {
    const response = await fetch(url, { credentials: "same-origin" });
    const text = await response.text();
    let payload;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch (_error) {
      payload = { error: text || "Respuesta no JSON" };
    }
    if (!response.ok) {
      throw new Error(payload?.error || `HTTP ${response.status}`);
    }
    return payload;
  }

  function formatResultBadge(result) {
    const normalized = String(result || "").toUpperCase();
    const cls = normalized === "PASS" ? "ict-pass-fail-detail-badge-ok" : normalized === "FAIL" ? "ict-pass-fail-detail-badge-ng" : "ict-pass-fail-detail-badge-warn";
    return `<span class="${cls}">${escapeHtml(normalized || "UNKNOWN")}</span>`;
  }

  function renderRows(rows) {
    const tbody = document.getElementById("fct-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="14" class="ict-empty-row">Sin registros FCT.</td></tr>';
      return;
    }
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(row.fecha)}</td>
        <td>${escapeHtml(row.hora)}</td>
        <td>${escapeHtml(row.linea)}</td>
        <td>${escapeHtml(row.estacion)}</td>
        <td>${formatResultBadge(row.resultado)}</td>
        <td>${escapeHtml(row.operador)}</td>
        <td>${escapeHtml(row.tiempo_ajuste)}</td>
        <td>${escapeHtml(row.no_parte)}</td>
        <td>${escapeHtml(row.serial_number)}</td>
        <td title="${escapeHtml(row.fuente_archivo)}">${escapeHtml(row.fuente_archivo)}</td>
        <td>${escapeHtml(row.failed_step)}</td>
        <td>${escapeHtml(row.failed_test_name)}</td>
        <td>${escapeHtml(row.failed_measured_value)} ${escapeHtml(row.failed_unit)}</td>
        <td>
          <button type="button" class="btn-page" data-fct-open-steps="${escapeHtml(row.source_path_hash)}" data-fct-serial="${escapeHtml(row.serial_number)}">Ver</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderPagination(payload) {
    const pagination = document.getElementById("fct-pagination");
    const summary = document.getElementById("fct-pagination-summary");
    const pageInput = document.getElementById("fct-page-input");
    const totalSpan = document.getElementById("fct-page-total");
    if (!pagination || !summary || !pageInput || !totalSpan) return;

    const total = Number(payload.total || 0);
    const page = Number(payload.page || 1);
    const perPage = Number(payload.per_page || state.perPage);
    const totalPages = Number(payload.total_pages || 1) || 1;
    const from = total ? (page - 1) * perPage + 1 : 0;
    const to = total ? Math.min(page * perPage, total) : 0;
    state.page = page;
    state.totalPages = totalPages;
    summary.textContent = `${from} - ${to} de ${total}`;
    pageInput.value = String(page);
    totalSpan.textContent = String(totalPages);
    pagination.style.display = "flex";
  }

  async function loadFctData(options) {
    const opts = options || {};
    setDefaultDates();
    if (opts.resetPage !== false) state.page = 1;
    const perPageSelect = document.getElementById("fct-per-page");
    state.perPage = Number(perPageSelect?.value || state.perPage || 1000);

    setLoading("fct-table-loading", true);
    try {
      const payload = await fetchJson(`/api/fct/data?${buildQuery(true).toString()}`);
      const rows = Array.isArray(payload) ? payload : payload.rows || [];
      renderRows(rows);
      renderPagination(Array.isArray(payload) ? { total: rows.length, page: 1, per_page: rows.length, total_pages: 1 } : payload);
      const count = document.getElementById("fct-record-count");
      if (count) count.textContent = `${payload.total ?? rows.length} registros`;
    } catch (error) {
      renderRows([]);
      notify(`Error cargando FCT: ${error.message}`, "error");
    } finally {
      setLoading("fct-table-loading", false);
    }
  }

  async function downloadFile(url, fallbackName) {
    const response = await fetch(url, { credentials: "same-origin" });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }
    const blob = await response.blob();
    const objectUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = fallbackName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(objectUrl);
  }

  async function exportFctToExcel() {
    try {
      await downloadFile(`/api/fct/export?${buildQuery(false).toString()}`, `historial_fct_${Date.now()}.xlsx`);
      notify("Exportación FCT completada");
    } catch (error) {
      notify(`Error exportando FCT: ${error.message}`, "error");
    }
  }

  function renderSteps(rows) {
    const tbody = document.getElementById("fct-steps-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="10" class="ict-empty-row">Sin pasos para mostrar.</td></tr>';
      return;
    }
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(row.idx)}</td>
        <td>${escapeHtml(row.step)}</td>
        <td>${escapeHtml(row.tested_at)}</td>
        <td>${escapeHtml(row.test_name)}</td>
        <td>${escapeHtml(row.measured_value)}</td>
        <td>${escapeHtml(row.unit)}</td>
        <td>${escapeHtml(row.nominal)}</td>
        <td>${escapeHtml(row.upper_limit)}</td>
        <td>${escapeHtml(row.lower_limit)}</td>
        <td>${formatResultBadge(row.row_result)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  async function loadSteps() {
    if (!state.currentStepsHash) return;
    const onlyFail = document.getElementById("fct-modal-only-fail")?.value || "";
    const query = new URLSearchParams({ source_path_hash: state.currentStepsHash });
    if (onlyFail) query.set("only_fail", onlyFail);
    setLoading("fct-steps-loading", true);
    try {
      const rows = await fetchJson(`/api/fct/steps?${query.toString()}`);
      renderSteps(Array.isArray(rows) ? rows : []);
    } catch (error) {
      renderSteps([]);
      notify(`Error cargando pasos FCT: ${error.message}`, "error");
    } finally {
      setLoading("fct-steps-loading", false);
    }
  }

  function openStepsModal(hash, serial) {
    state.currentStepsHash = hash || "";
    state.currentStepsSerial = serial || "";
    const modal = document.getElementById("fct-steps-modal");
    const modalSerial = document.getElementById("fct-modal-serial");
    if (!modal) return;
    if (modal.parentNode !== document.body) document.body.appendChild(modal);
    if (modalSerial) modalSerial.textContent = state.currentStepsSerial;
    modal.style.display = "flex";
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    loadSteps();
  }

  function closeStepsModal() {
    const modal = document.getElementById("fct-steps-modal");
    if (!modal) return;
    modal.classList.remove("show");
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
  }

  function cleanupFctModule() {
    closeStepsModal();
    setLoading("fct-table-loading", false);
    setLoading("fct-steps-loading", false);
  }

  function initializeFctEventListeners() {
    setDefaultDates();
    if (document.body.dataset.fctListenersAttached === "true") return;

    document.body.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;

      if (target.id === "fct-btn-consultar" || target.closest("#fct-btn-consultar")) {
        loadFctData({ resetPage: true });
        return;
      }
      if (target.id === "fct-btn-export-excel" || target.closest("#fct-btn-export-excel")) {
        exportFctToExcel();
        return;
      }
      const stepsButton = target.closest("[data-fct-open-steps]");
      if (stepsButton) {
        openStepsModal(stepsButton.getAttribute("data-fct-open-steps"), stepsButton.getAttribute("data-fct-serial"));
        return;
      }
      if (target.matches("[data-fct-steps-close]") || target.closest("[data-fct-steps-close]")) {
        closeStepsModal();
        return;
      }
      if (target.id === "fct-page-first") {
        state.page = 1;
        loadFctData({ resetPage: false });
        return;
      }
      if (target.id === "fct-page-prev") {
        state.page = Math.max(1, state.page - 1);
        loadFctData({ resetPage: false });
        return;
      }
      if (target.id === "fct-page-next") {
        state.page = Math.min(state.totalPages, state.page + 1);
        loadFctData({ resetPage: false });
        return;
      }
      if (target.id === "fct-page-last") {
        state.page = state.totalPages;
        loadFctData({ resetPage: false });
      }
    });

    document.body.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLSelectElement || target instanceof HTMLInputElement)) return;
      if (target.id === "fct-per-page") {
        state.perPage = Number(target.value || 1000);
        loadFctData({ resetPage: true });
      }
      if (target.id === "fct-modal-only-fail") {
        loadSteps();
      }
    });

    document.body.addEventListener("keydown", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement)) return;
      if (target.id === "fct-page-input" && event.key === "Enter") {
        state.page = Math.min(state.totalPages, Math.max(1, Number(target.value || 1)));
        loadFctData({ resetPage: false });
      }
      if (target.closest("#fct-filters") && event.key === "Enter") {
        loadFctData({ resetPage: true });
      }
    });

    document.body.dataset.fctListenersAttached = "true";
  }

  window.limpiarHistorialFCT = cleanupFctModule;
  window.initializeFctEventListeners = initializeFctEventListeners;
  window.loadFctData = loadFctData;

  if (document.getElementById("fct-container")) {
    initializeFctEventListeners();
    setTimeout(() => loadFctData({ resetPage: true }), 50);
  }
})();
