(function () {
  "use strict";

  let currentSummaryRow = null;

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
    const desde = document.getElementById("fct-pass-fail-filter-fecha-desde");
    const hasta = document.getElementById("fct-pass-fail-filter-fecha-hasta");
    if (desde && !desde.value) desde.value = today;
    if (hasta && !hasta.value) hasta.value = today;
  }

  function buildQuery(extra) {
    const query = new URLSearchParams();
    const fields = [
      ["fecha_desde", "fct-pass-fail-filter-fecha-desde"],
      ["fecha_hasta", "fct-pass-fail-filter-fecha-hasta"],
      ["numero_parte", "fct-pass-fail-filter-numero-parte"],
      ["linea", "fct-pass-fail-filter-linea"],
      ["estacion", "fct-pass-fail-filter-estacion"],
      ["turno", "fct-pass-fail-filter-turno"],
      ["serial", "fct-pass-fail-filter-serial"],
    ];
    fields.forEach(([key, id]) => {
      const value = document.getElementById(id)?.value?.trim();
      if (value) query.set(key, value);
    });
    Object.entries(extra || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && String(value) !== "") {
        query.set(key, String(value));
      }
    });
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
    if (!response.ok) throw new Error(payload?.error || `HTTP ${response.status}`);
    return payload;
  }

  function badge(result) {
    const value = String(result || "").toUpperCase();
    const cls = value === "PASS" ? "ict-pass-fail-detail-badge-ok" : value === "FAIL" ? "ict-pass-fail-detail-badge-ng" : "ict-pass-fail-detail-badge-warn";
    return `<span class="${cls}">${escapeHtml(value || "UNKNOWN")}</span>`;
  }

  function pctBar(value, cls) {
    const pct = Math.max(0, Math.min(100, Number(value || 0)));
    const barClass = cls === "ok" ? "ict-pass-fail-bar-ok" : "ict-pass-fail-bar-ng";
    return `<div class="ict-pass-fail-bar-row"><div class="ict-pass-fail-bar"><span class="${barClass}" style="width:${pct}%"></span></div><span class="ict-pass-fail-bar-side-label">${pct.toFixed(2)}%</span></div>`;
  }

  function renderSummary(rows) {
    const tbody = document.getElementById("fct-pass-fail-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="12" class="ict-pass-fail-table-empty">Sin datos FCT para el filtro.</td></tr>';
      return;
    }
    rows.forEach((row, index) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(row.fecha)}</td>
        <td>${escapeHtml(row.linea)}</td>
        <td>${escapeHtml(row.estacion)}</td>
        <td>${escapeHtml(row.turno)}</td>
        <td>${escapeHtml(row.numero_parte)}</td>
        <td>${escapeHtml(row.total)}</td>
        <td>${escapeHtml(row.pass_count)}</td>
        <td>${escapeHtml(row.fail_count)}</td>
        <td>${pctBar(row.pass_pct, "ok")}</td>
        <td>${pctBar(row.fail_pct, "ng")}</td>
        <td>${escapeHtml(row.fallas_con_paso)} / ${escapeHtml(row.fail_count)}</td>
        <td><button type="button" class="btn-page" data-fct-pf-detail="${index}">Ver</button></td>
      `;
      tr.dataset.summaryIndex = String(index);
      tbody.appendChild(tr);
    });
    window.__fctPassFailRows = rows;
  }

  async function loadHistorialFctPassFailData() {
    setDefaultDates();
    setLoading("fct-pass-fail-table-loading", true);
    try {
      const rows = await fetchJson(`/api/fct/pass-fail?${buildQuery().toString()}`);
      renderSummary(Array.isArray(rows) ? rows : []);
      const count = document.getElementById("fct-pass-fail-record-count");
      if (count) count.textContent = `${Array.isArray(rows) ? rows.length : 0} registros`;
    } catch (error) {
      renderSummary([]);
      notify(`Error cargando FCT Pass/Fail: ${error.message}`, "error");
    } finally {
      setLoading("fct-pass-fail-table-loading", false);
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

  async function exportFctPassFailToExcel() {
    try {
      await downloadFile(`/api/fct/pass-fail/export?${buildQuery().toString()}`, `historial_fct_pass_fail_${Date.now()}.xlsx`);
      notify("Exportación FCT Pass/Fail completada");
    } catch (error) {
      notify(`Error exportando FCT Pass/Fail: ${error.message}`, "error");
    }
  }

  function openDetailModal(row) {
    currentSummaryRow = row;
    const modal = document.getElementById("fct-pass-fail-detail-modal");
    const subtitle = document.getElementById("fct-pass-fail-detail-subtitle");
    const summary = document.getElementById("fct-pass-fail-detail-summary");
    if (!modal || !row) return;
    if (modal.parentNode !== document.body) document.body.appendChild(modal);
    if (subtitle) {
      subtitle.textContent = `${row.fecha} · ${row.linea} · ${row.estacion} · ${row.turno} · ${row.numero_parte}`;
    }
    if (summary) {
      summary.innerHTML = `
        <span>Total: <strong>${escapeHtml(row.total)}</strong></span>
        <span>PASS: <strong>${escapeHtml(row.pass_count)}</strong></span>
        <span>FAIL: <strong>${escapeHtml(row.fail_count)}</strong></span>
        <span>% PASS: <strong>${escapeHtml(row.pass_pct)}%</strong></span>
        <span>Operador: <strong>${escapeHtml(row.operador)}</strong></span>
      `;
    }
    modal.classList.add("show");
    modal.style.display = "flex";
    modal.setAttribute("aria-hidden", "false");
    loadDetailRows();
  }

  function closeDetailModal() {
    const modal = document.getElementById("fct-pass-fail-detail-modal");
    if (!modal) return;
    modal.classList.remove("show");
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
  }

  function renderDetail(rows) {
    const tbody = document.getElementById("fct-pass-fail-detail-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="ict-pass-fail-table-empty">Sin detalle para este resumen.</td></tr>';
      return;
    }
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(row.start_at)}</td>
        <td>${escapeHtml(row.serial_number)}</td>
        <td>${badge(row.resultado)}</td>
        <td>${escapeHtml(row.failed_step)}</td>
        <td>${escapeHtml(row.failed_test_name)}</td>
        <td>${escapeHtml(row.failed_measured_value)} ${escapeHtml(row.failed_unit)}</td>
        <td title="${escapeHtml(row.fuente_archivo)}">${escapeHtml(row.fuente_archivo)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  async function loadDetailRows() {
    if (!currentSummaryRow) return;
    const extra = {
      fecha_jornada: currentSummaryRow.fecha,
      grupo_linea: currentSummaryRow.linea,
      grupo_estacion: currentSummaryRow.estacion,
      grupo_turno: currentSummaryRow.turno,
      grupo_numero_parte: currentSummaryRow.numero_parte,
    };
    setLoading("fct-pass-fail-detail-loading", true);
    try {
      const rows = await fetchJson(`/api/fct/pass-fail/detail?${buildQuery(extra).toString()}`);
      renderDetail(Array.isArray(rows) ? rows : []);
    } catch (error) {
      renderDetail([]);
      notify(`Error cargando detalle FCT: ${error.message}`, "error");
    } finally {
      setLoading("fct-pass-fail-detail-loading", false);
    }
  }

  function cleanupFctPassFailModule() {
    closeDetailModal();
    setLoading("fct-pass-fail-table-loading", false);
    setLoading("fct-pass-fail-detail-loading", false);
  }

  function initializeHistorialFctPassFailEventListeners() {
    setDefaultDates();
    if (document.body.dataset.fctPassFailListenersAttached === "true") return;

    document.body.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.id === "fct-pass-fail-btn-consultar" || target.closest("#fct-pass-fail-btn-consultar")) {
        loadHistorialFctPassFailData();
        return;
      }
      if (target.id === "fct-pass-fail-btn-export-excel" || target.closest("#fct-pass-fail-btn-export-excel")) {
        exportFctPassFailToExcel();
        return;
      }
      const detailButton = target.closest("[data-fct-pf-detail]");
      if (detailButton) {
        const rows = window.__fctPassFailRows || [];
        openDetailModal(rows[Number(detailButton.getAttribute("data-fct-pf-detail"))]);
        return;
      }
      if (target.matches("[data-fct-pass-fail-detail-close]") || target.closest("[data-fct-pass-fail-detail-close]")) {
        closeDetailModal();
      }
    });

    document.body.addEventListener("keydown", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement)) return;
      if (target.closest("#fct-pass-fail-filters") && event.key === "Enter") {
        loadHistorialFctPassFailData();
      }
    });

    document.body.dataset.fctPassFailListenersAttached = "true";
  }

  window.limpiarHistorialFCTPassFail = cleanupFctPassFailModule;
  window.initializeHistorialFctPassFailEventListeners = initializeHistorialFctPassFailEventListeners;
  window.loadHistorialFctPassFailData = loadHistorialFctPassFailData;

  if (document.getElementById("fct-pass-fail-container")) {
    initializeHistorialFctPassFailEventListeners();
    setTimeout(loadHistorialFctPassFailData, 50);
  }
})();
