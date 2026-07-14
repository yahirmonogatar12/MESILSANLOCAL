/**
 * Part Planning LG - Import del plan diario de produccion LG (Etapa 1).
 *
 * WF_003: todo prefijado pp/pp-, listeners delegados sobre document.body
 * (el fragmento se inyecta por AJAX), init dual, exports globales que
 * consume scriptMain.js (mostrarPartPlanning).
 */
(function () {
  "use strict";

  const ppState = {
    file: null,
    fileSha256: null,
    preview: null,
    page: 1,
    pageSize: 50,
    totalParts: 0,
  };

  // =============================
  // Helpers
  // =============================

  function ppEl(id) {
    return document.getElementById(id);
  }

  function ppEscapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function ppFmtNum(n) {
    return (n == null ? 0 : n).toLocaleString("es-MX");
  }

  function ppFmtBytes(bytes) {
    if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    if (bytes >= 1024) return (bytes / 1024).toFixed(1) + " KB";
    return bytes + " B";
  }

  function ppIsoToday() {
    const d = new Date();
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);
  }

  function ppWeekRange() {
    const d = new Date();
    const dow = (d.getDay() + 6) % 7; // 0 = lunes
    const lunes = new Date(d);
    lunes.setDate(d.getDate() - dow);
    const domingo = new Date(lunes);
    domingo.setDate(lunes.getDate() + 6);
    const iso = (x) =>
      new Date(x.getTime() - x.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 10);
    return [iso(lunes), iso(domingo)];
  }

  function ppSetDefaultDates(force) {
    const from = ppEl("pp-filter-date-from");
    const to = ppEl("pp-filter-date-to");
    if (!from || !to) return;
    if (force || !from.value || !to.value) {
      const [lunes, domingo] = ppWeekRange();
      from.value = lunes;
      to.value = domingo;
    }
  }

  // =============================
  // Tabla principal (plan pivotado)
  // =============================

  async function ppLoadData() {
    ppSetDefaultDates(false);
    const from = ppEl("pp-filter-date-from");
    const to = ppEl("pp-filter-date-to");
    const part = ppEl("pp-filter-part");
    const tabla = ppEl("pp-plan-table");
    if (!tabla) return;

    const params = new URLSearchParams({
      date_from: from ? from.value : "",
      date_to: to ? to.value : "",
      part: part ? part.value.trim() : "",
      page: String(ppState.page),
      page_size: String(ppState.pageSize),
    });

    const tbody = tabla.querySelector("tbody");
    tbody.innerHTML = '<tr><td class="pp-empty">Cargando...</td></tr>';
    try {
      const resp = await fetch("/api/part-planning/plan?" + params.toString(), {
        credentials: "same-origin",
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || "Error al consultar");
      ppState.totalParts = data.total_parts;
      ppRenderPlanTable(data);
    } catch (e) {
      console.error("part-planning: error cargando plan:", e);
      tbody.innerHTML =
        '<tr><td class="pp-empty pp-error-text">' +
        ppEscapeHtml(e.message || "Error al cargar") +
        "</td></tr>";
    }
  }

  function ppRenderPlanTable(data) {
    const tabla = ppEl("pp-plan-table");
    const thead = tabla.querySelector("thead");
    const tbody = tabla.querySelector("tbody");
    const hoy = ppIsoToday();

    const DIAS = ["Dom", "Lun", "Mar", "Mie", "Jue", "Vie", "Sab"];
    let head = "<tr><th class=\"pp-col-part\">Numero de parte</th><th>Total</th>";
    for (const iso of data.dates) {
      const f = new Date(iso + "T00:00:00");
      const esHoy = iso === hoy ? " pp-col-today" : "";
      head +=
        '<th class="pp-col-date' + esHoy + '">' +
        DIAS[f.getDay()] + "<br>" +
        String(f.getDate()).padStart(2, "0") + "/" + String(f.getMonth() + 1).padStart(2, "0") +
        "</th>";
    }
    head += "</tr>";
    thead.innerHTML = head;

    if (!data.rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="' + (data.dates.length + 2) +
        '" class="pp-empty">Sin plan en el rango seleccionado</td></tr>';
    } else {
      let html = "";
      for (const row of data.rows) {
        html += '<tr><td class="pp-col-part">' + ppEscapeHtml(row.part_no) + "</td>";
        html += "<td class=\"pp-col-total\">" + ppFmtNum(row.total) + "</td>";
        for (const iso of data.dates) {
          const qty = row.qty[iso];
          const esHoy = iso === hoy ? " pp-col-today" : "";
          if (qty == null) {
            html += '<td class="pp-cell-none' + esHoy + '">-</td>';
          } else if (qty === 0) {
            html += '<td class="pp-cell-zero' + esHoy + '">0</td>';
          } else {
            html += '<td class="pp-cell-qty' + esHoy + '">' + ppFmtNum(qty) + "</td>";
          }
        }
        html += "</tr>";
      }
      tbody.innerHTML = html;
    }

    const info = ppEl("pp-page-info");
    const desde = (data.page - 1) * data.page_size + 1;
    const hasta = Math.min(data.page * data.page_size, data.total_parts);
    if (info) {
      info.textContent = data.total_parts
        ? "Partes " + desde + "-" + hasta + " de " + ppFmtNum(data.total_parts)
        : "Sin partes";
    }
    const prev = ppEl("pp-btn-prev");
    const next = ppEl("pp-btn-next");
    if (prev) prev.disabled = data.page <= 1;
    if (next) next.disabled = hasta >= data.total_parts;
  }

  // =============================
  // Modal de importacion
  // =============================

  function ppShowStep(step) {
    ["pp-step-file", "pp-step-preview", "pp-step-options", "pp-step-confirm", "pp-step-done"]
      .forEach((id) => {
        const el = ppEl(id);
        if (el) el.style.display = id === step ? "block" : "none";
      });
  }

  function ppOpenImportModal() {
    ppState.file = null;
    ppState.fileSha256 = null;
    ppState.preview = null;
    const input = ppEl("pp-file-input");
    if (input) input.value = "";
    const info = ppEl("pp-file-info");
    if (info) info.style.display = "none";
    const analyze = ppEl("pp-btn-analyze");
    if (analyze) analyze.disabled = true;
    const year = ppEl("pp-plan-year");
    if (year) year.value = "";
    ppShowStep("pp-step-file");
    const modal = ppEl("pp-import-modal");
    if (modal) modal.style.display = "flex";
  }

  function ppCloseImportModal() {
    const modal = ppEl("pp-import-modal");
    if (modal) modal.style.display = "none";
  }

  function ppOnFileSelected(input) {
    const file = input.files && input.files[0];
    if (!file) return;
    const nombre = file.name.toLowerCase();
    if (!nombre.endsWith(".xlsx") && !nombre.endsWith(".xlsm")) {
      alert("Formato no permitido. Solo .xlsx o .xlsm");
      input.value = "";
      return;
    }
    ppState.file = file;
    ppState.fileSha256 = null;
    ppEl("pp-file-name").textContent = file.name;
    ppEl("pp-file-size").textContent = ppFmtBytes(file.size);
    ppEl("pp-file-status").textContent = "Pendiente de validar";
    ppEl("pp-file-info").style.display = "block";
    ppEl("pp-btn-analyze").disabled = false;
  }

  async function ppAnalyze() {
    if (!ppState.file) return;
    const btn = ppEl("pp-btn-analyze");
    const spinner = ppEl("pp-analyze-spinner");
    btn.disabled = true;
    if (spinner) spinner.style.display = "inline-block";
    try {
      const fd = new FormData();
      fd.append("file", ppState.file);
      const yearInput = ppEl("pp-plan-year");
      if (yearInput && yearInput.value) fd.append("plan_year", yearInput.value);

      const resp = await fetch("/api/part-planning/import/preview", {
        method: "POST",
        body: fd,
        credentials: "same-origin",
      });
      const data = await resp.json();
      ppState.preview = data;
      ppState.fileSha256 = data.file_sha256 || null;
      ppRenderPreview(data);
      ppShowStep("pp-step-preview");
    } catch (e) {
      console.error("part-planning: error en preview:", e);
      alert("Error al analizar el archivo: " + (e.message || e));
    } finally {
      btn.disabled = false;
      if (spinner) spinner.style.display = "none";
    }
  }

  function ppRenderPreview(data) {
    const ok = !!data.success;
    const summary = data.summary || {};
    ppEl("pp-sum-parts").textContent = ppFmtNum(summary.parts_count);
    ppEl("pp-sum-dates").textContent = ppFmtNum(summary.dates_count);
    ppEl("pp-sum-records").textContent = ppFmtNum(summary.records_count);
    ppEl("pp-sum-zeros").textContent = ppFmtNum(summary.zero_records_count);
    ppEl("pp-sum-dups").textContent = ppFmtNum(summary.duplicates_count);
    ppEl("pp-sum-range").textContent = ok
      ? (summary.date_from || "-") + " a " + (summary.date_to || "-")
      : "-";

    const errores = data.errors || [];
    const avisos = data.warnings || [];
    const listaErr = ppEl("pp-errors-list");
    const listaWarn = ppEl("pp-warnings-list");
    listaErr.innerHTML = errores.map((e) => "<li>" + ppEscapeHtml(e) + "</li>").join("");
    listaErr.style.display = errores.length ? "block" : "none";
    listaWarn.innerHTML = avisos.map((w) => "<li>" + ppEscapeHtml(w) + "</li>").join("");
    listaWarn.style.display = avisos.length ? "block" : "none";

    const tbody = ppEl("pp-preview-table").querySelector("tbody");
    const filas = data.sample_rows || [];
    tbody.innerHTML = filas.length
      ? filas
          .map(
            (r) =>
              "<tr><td>" + ppEscapeHtml(r.part_no) + "</td><td>" +
              ppEscapeHtml(r.plan_date) + "</td><td>" + ppFmtNum(r.plan_qty) + "</td></tr>"
          )
          .join("")
      : '<tr><td colspan="3" class="pp-empty">Sin registros con cantidad</td></tr>';
    ppEl("pp-preview-note").textContent = ok
      ? "Vista previa de " + filas.length + " registros; el resumen considera todo el archivo."
      : "";

    ppEl("pp-btn-preview-next").disabled = !ok || errores.length > 0;

    const year = ppEl("pp-plan-year");
    if (year && ok && summary.plan_year) year.value = summary.plan_year;
    if (ok) ppEl("pp-file-status").textContent = "Validado";
  }

  function ppRenderConfirmSummary() {
    const s = (ppState.preview && ppState.preview.summary) || {};
    const modo = document.querySelector('input[name="pp-mode"]:checked');
    const modoTexto = {
      upsert: "Actualizar cantidades existentes",
      only_positive: "Actualizar solamente cantidades mayores que cero",
      only_new: "Importar unicamente registros nuevos",
    }[modo ? modo.value : "upsert"];
    const incluirCeros = ppEl("pp-include-zero").checked;
    const archivo = ppState.file ? ppState.file.name : "-";

    ppEl("pp-confirm-summary").innerHTML =
      "<div><strong>Archivo:</strong> " + ppEscapeHtml(archivo) + "</div>" +
      "<div><strong>Se actualizaran:</strong> " + ppFmtNum(s.parts_count) +
      " numeros de parte, " + ppFmtNum(s.dates_count) + " fechas</div>" +
      "<div><strong>Registros con cantidad:</strong> " + ppFmtNum(s.records_count) +
      " &middot; <strong>En cero:</strong> " + ppFmtNum(s.zero_records_count) + "</div>" +
      "<div><strong>Rango afectado:</strong> " + ppEscapeHtml(s.date_from || "-") +
      " al " + ppEscapeHtml(s.date_to || "-") + "</div>" +
      "<div><strong>Modo:</strong> " + modoTexto + "</div>" +
      "<div><strong>Importar ceros:</strong> " + (incluirCeros ? "Si" : "No") + "</div>";
  }

  async function ppConfirm() {
    if (!ppState.file || !ppState.fileSha256) {
      alert("Analiza el archivo antes de confirmar.");
      return;
    }
    const btn = ppEl("pp-btn-confirm-import");
    const spinner = ppEl("pp-confirm-spinner");
    btn.disabled = true;
    if (spinner) spinner.style.display = "inline-block";
    try {
      const modo = document.querySelector('input[name="pp-mode"]:checked');
      const fd = new FormData();
      fd.append("file", ppState.file);
      fd.append("file_sha256", ppState.fileSha256);
      fd.append("import_mode", modo ? modo.value : "upsert");
      fd.append("include_zero", ppEl("pp-include-zero").checked ? "1" : "0");
      const year = ppEl("pp-plan-year");
      if (year && year.value) fd.append("plan_year", year.value);

      const resp = await fetch("/api/part-planning/import/confirm", {
        method: "POST",
        body: fd,
        credentials: "same-origin",
      });
      const data = await resp.json();
      if (!data.success) {
        const msg = (data.errors || [data.error || "Error desconocido"]).join("\n");
        ppEl("pp-done-title").textContent = "La importacion fue rechazada";
        ppEl("pp-done-summary").innerHTML =
          '<div class="pp-error-text">' + ppEscapeHtml(msg) + "</div>";
      } else {
        ppEl("pp-done-title").textContent = "Importacion completada";
        ppEl("pp-done-summary").innerHTML =
          "<div><strong>Importacion #" + data.import_id + "</strong></div>" +
          "<div>Registros nuevos: <strong>" + ppFmtNum(data.inserted) + "</strong></div>" +
          "<div>Registros actualizados: <strong>" + ppFmtNum(data.updated) + "</strong></div>" +
          "<div>Sin cambios: <strong>" + ppFmtNum(data.unchanged) + "</strong></div>" +
          "<div>Rango: " + ppEscapeHtml(data.date_from) + " al " +
          ppEscapeHtml(data.date_to) + "</div>";
        ppState.page = 1;
        ppLoadData();
      }
      ppShowStep("pp-step-done");
    } catch (e) {
      console.error("part-planning: error en confirm:", e);
      alert("Error al confirmar la importacion: " + (e.message || e));
    } finally {
      btn.disabled = false;
      if (spinner) spinner.style.display = "none";
    }
  }

  // =============================
  // Historial
  // =============================

  async function ppLoadHistory() {
    const modal = ppEl("pp-history-modal");
    const tbody = ppEl("pp-history-table").querySelector("tbody");
    tbody.innerHTML = '<tr><td colspan="12" class="pp-empty">Cargando...</td></tr>';
    if (modal) modal.style.display = "flex";
    try {
      const resp = await fetch("/api/part-planning/imports?limit=50", {
        credentials: "same-origin",
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || "Error");
      const imports = data.imports || [];
      tbody.innerHTML = imports.length
        ? imports
            .map(
              (r) =>
                "<tr><td>" + ppEscapeHtml(r.imported_at) + "</td>" +
                "<td class=\"pp-col-file\">" + ppEscapeHtml(r.original_filename) + "</td>" +
                "<td>" + ppEscapeHtml(r.plan_year) + "</td>" +
                "<td>" + ppEscapeHtml(r.date_from) + " a " + ppEscapeHtml(r.date_to) + "</td>" +
                "<td>" + ppFmtNum(r.parts_count) + "</td>" +
                "<td>" + ppFmtNum(r.dates_count) + "</td>" +
                "<td>" + ppFmtNum(r.records_count) + "</td>" +
                "<td>" + ppFmtNum(r.zero_records_count) + "</td>" +
                "<td>" + ppFmtNum(r.warning_count) + "</td>" +
                "<td>" + ppEscapeHtml(r.import_mode) + "</td>" +
                "<td>" + ppEscapeHtml(r.imported_by) + "</td>" +
                "<td>" + ppEscapeHtml(r.status) + "</td></tr>"
            )
            .join("")
        : '<tr><td colspan="12" class="pp-empty">Sin importaciones registradas</td></tr>';
    } catch (e) {
      tbody.innerHTML =
        '<tr><td colspan="12" class="pp-empty pp-error-text">' +
        ppEscapeHtml(e.message || "Error al cargar historial") + "</td></tr>";
    }
  }

  // =============================
  // Listeners delegados (idempotentes)
  // =============================

  function ppInitListeners() {
    if (document.body.dataset.ppListenersAttached) return;
    document.body.dataset.ppListenersAttached = "1";

    document.body.addEventListener("click", function (e) {
      const t = e.target;
      const hit = (id) => t.id === id || (t.closest && t.closest("#" + id));

      if (hit("pp-btn-import")) { e.preventDefault(); ppOpenImportModal(); return; }
      if (hit("pp-btn-history")) { e.preventDefault(); ppLoadHistory(); return; }
      if (hit("pp-btn-history-close")) { ppEl("pp-history-modal").style.display = "none"; return; }
      if (hit("pp-btn-modal-close") || (t.classList && t.classList.contains("pp-btn-cancel"))) {
        ppCloseImportModal(); return;
      }
      if (hit("pp-btn-analyze")) { e.preventDefault(); ppAnalyze(); return; }
      if (hit("pp-btn-preview-back")) { ppShowStep("pp-step-file"); return; }
      if (hit("pp-btn-preview-next")) { ppShowStep("pp-step-options"); return; }
      if (hit("pp-btn-options-back")) { ppShowStep("pp-step-preview"); return; }
      if (hit("pp-btn-options-next")) { ppRenderConfirmSummary(); ppShowStep("pp-step-confirm"); return; }
      if (hit("pp-btn-confirm-back")) { ppShowStep("pp-step-options"); return; }
      if (hit("pp-btn-confirm-import")) { e.preventDefault(); ppConfirm(); return; }
      if (hit("pp-btn-done-close")) { ppCloseImportModal(); return; }
      if (hit("pp-btn-search")) { e.preventDefault(); ppState.page = 1; ppLoadData(); return; }
      if (hit("pp-btn-week")) { e.preventDefault(); ppSetDefaultDates(true); ppState.page = 1; ppLoadData(); return; }
      if (hit("pp-btn-prev")) { if (ppState.page > 1) { ppState.page--; ppLoadData(); } return; }
      if (hit("pp-btn-next")) { ppState.page++; ppLoadData(); return; }
    });

    document.body.addEventListener("change", function (e) {
      if (e.target.id === "pp-file-input") ppOnFileSelected(e.target);
    });

    document.body.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && e.target.id === "pp-filter-part") {
        e.preventDefault();
        ppState.page = 1;
        ppLoadData();
      }
    });
  }

  function ppCleanup() {
    ppState.file = null;
    ppState.fileSha256 = null;
    ppState.preview = null;
    ppState.page = 1;
  }

  // =============================
  // Exports globales + init dual (WF_003)
  // =============================

  window.initializePartPlanningEventListeners = ppInitListeners;
  window.loadPartPlanningData = function () {
    ppState.page = 1;
    ppLoadData();
  };
  window.limpiarPartPlanning = ppCleanup;

  function ppBoot() {
    if (!document.getElementById("part-planning-root")) return;
    ppInitListeners();
    ppSetDefaultDates(false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ppBoot);
  } else {
    ppBoot();
  }
})();
