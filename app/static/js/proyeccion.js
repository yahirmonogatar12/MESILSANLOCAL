/**
 * Proyeccion - Renglones P/S/I por parte (Etapa 2 de Part Planning).
 *
 * P = plan LG importado (modulo Part Planning LG).
 * S = schedule: importado de la hoja Part 10 y/o capturado aqui (clic en celda).
 * I = inventario proyectado: I(t) = I(t-1) - P(t) + S(t),
 *     I0 = LGEMM+ISEMM+SVC+DIF+PENDIENTE+REWORK (import semanal Part 10).
 *
 * WF_003: prefijo pr/pr-, listeners delegados, init dual, exports globales.
 * Reutiliza las clases CSS pp-* de part_planning.css (solo los IDs cambian).
 */
(function () {
  "use strict";

  const prState = {
    page: 1,
    pageSize: 50,
    totalParts: 0,
    propuestas: null,
    proposalId: null,
    proposalVersion: null,
    originalItems: null,
    propItems: null,
    proposalMeta: null,
    proposalBusy: false,
    proposalStale: false,
    proposalStaleMessage: "",
  };

  function prEl(id) {
    return document.getElementById(id);
  }

  function prEscapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
  }

  function prEscapeAttr(text) {
    return prEscapeHtml(text).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function prFmtNum(n) {
    return (n == null ? 0 : n).toLocaleString("es-MX");
  }

  function prIsoToday() {
    const d = new Date();
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);
  }

  function prWeekRange() {
    const d = new Date();
    const dow = (d.getDay() + 6) % 7;
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

  function prSetDefaultDates(force) {
    const from = prEl("pr-filter-date-from");
    const to = prEl("pr-filter-date-to");
    if (!from || !to) return;
    if (force || !from.value || !to.value) {
      const [lunes, domingo] = prWeekRange();
      from.value = lunes;
      to.value = domingo;
    }
  }

  // =============================
  // Tabla P/S/I
  // =============================

  async function prLoadData(opts) {
    // silent: refresco tras capturar una celda — sin "Cargando..." y
    // conservando el scroll para no perder el lugar en la tabla.
    const silent = !!(opts && opts.silent);
    prSetDefaultDates(false);
    const from = prEl("pr-filter-date-from");
    const to = prEl("pr-filter-date-to");
    const part = prEl("pr-filter-part");
    const tabla = prEl("pr-plan-table");
    if (!tabla) return;

    const wrap = tabla.closest(".pp-table-wrap");
    const scrollX = wrap ? wrap.scrollLeft : 0;
    const scrollY = wrap ? wrap.scrollTop : 0;

    const shortage = prEl("pr-filter-shortage");
    const params = new URLSearchParams({
      date_from: from ? from.value : "",
      date_to: to ? to.value : "",
      part: part ? part.value.trim() : "",
      page: String(prState.page),
      page_size: String(prState.pageSize),
      only_shortage: shortage && shortage.checked ? "1" : "",
    });

    const tbody = tabla.querySelector("tbody");
    if (!silent) {
      tbody.innerHTML = '<tr><td class="pp-empty">Cargando...</td></tr>';
    }
    try {
      const resp = await fetch("/api/part-planning/plan?" + params.toString(), {
        credentials: "same-origin",
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || "Error al consultar");
      prState.totalParts = data.total_parts;
      prRenderTable(data);
      if (silent && wrap) {
        wrap.scrollLeft = scrollX;
        wrap.scrollTop = scrollY;
      }
    } catch (e) {
      console.error("proyeccion: error cargando datos:", e);
      tbody.innerHTML =
        '<tr><td class="pp-empty pp-error-text">' +
        prEscapeHtml(e.message || "Error al cargar") +
        "</td></tr>";
    }
  }

  function prInvTooltip(inv) {
    if (!inv) return "Sin inventario. Clic en las celdas de la derecha para capturar.";
    return (
      "I inicial: " + inv.i0 + " (desde " + (inv.ref_date || "-") + ")" +
      (inv.line ? "\nLinea: " + inv.line : "") +
      (inv.board ? "\nBoard: " + inv.board : "")
    );
  }

  // Columnas de inventario editables (mismo orden que la hoja Part 10)
  const PR_INV_COLS = [
    { f: "lgemm", label: "LGEMM" },
    { f: "isemm", label: "ISEMM" },
    { f: "svc", label: "SVC" },
    { f: "dif", label: "DIF" },
    { f: "pendiente", label: "PEND" },
    { f: "rework", label: "REW" },
    { f: "smt", label: "SMT" },
    { f: "imd", label: "IMD" },
  ];

  function prRenderTable(data) {
    const tabla = prEl("pr-plan-table");
    const thead = tabla.querySelector("thead");
    const tbody = tabla.querySelector("tbody");
    const hoy = prIsoToday();

    const DIAS = ["Dom", "Lun", "Mar", "Mie", "Jue", "Vie", "Sab"];
    let head = '<tr><th class="pp-col-part">Numero de parte</th>' +
      '<th class="pp-col-inv pp-col-req" title="Demanda total del plan LG desde hoy (todas las fechas importadas)">Req<br>LG</th>';
    for (const col of PR_INV_COLS) {
      head += '<th class="pp-col-inv" title="Clic en la celda para capturar">' + col.label + "</th>";
    }
    head += '<th class="pp-col-tipo">&nbsp;</th><th>Total</th>';
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
        '<tr><td colspan="' + (data.dates.length + 4 + PR_INV_COLS.length) +
        '" class="pp-empty">Sin plan en el rango seleccionado</td></tr>';
    } else {
      let html = "";
      for (const row of data.rows) {
        const proj = row.proj || {};
        const sched = row.sched || {};
        const projVals = data.dates.map((iso) => proj[iso]).filter((v) => v != null);
        const projFinal = projVals.length ? projVals[projVals.length - 1] : null;

        // Renglon P (plan LG)
        html +=
          '<tr class="pp-row-p"><td class="pp-col-part" rowspan="3" title="' +
          prEscapeHtml(prInvTooltip(row.inv)) + '">' + prEscapeHtml(row.part_no) +
          (row.inv && row.inv.line
            ? ' <span class="pp-line-tag">' + prEscapeHtml(row.inv.line) + "</span>"
            : "") +
          "</td>";
        const i0 = row.inv ? row.inv.i0 : 0;
        const req = row.req_lg || 0;
        html +=
          '<td class="pp-cell-req' + (req > i0 ? " pp-cell-neg" : "") +
          '" rowspan="3" title="Demanda LG desde hoy: ' + req +
          (row.inv ? " | I inicial: " + i0 : " | Sin inventario") + '">' +
          prFmtNum(req) + "</td>";
        for (const col of PR_INV_COLS) {
          const v = row.inv ? row.inv[col.f] : null;
          html +=
            '<td class="pp-cell-inv' + (v != null && v < 0 ? " pp-cell-neg" : "") +
            '" rowspan="3" data-part="' + prEscapeHtml(row.part_no) +
            '" data-field="' + col.f + '" title="Clic para capturar ' + col.label + '">' +
            (v == null ? "-" : prFmtNum(v)) + "</td>";
        }
        html += '<td class="pp-col-tipo pp-tipo-p">P</td>';
        html += '<td class="pp-col-total">' + prFmtNum(row.total) + "</td>";
        for (const iso of data.dates) {
          const qty = row.qty[iso];
          const esHoy = iso === hoy ? " pp-col-today" : "";
          if (qty == null) {
            html += '<td class="pp-cell-none' + esHoy + '">-</td>';
          } else if (qty === 0) {
            html += '<td class="pp-cell-zero' + esHoy + '">0</td>';
          } else {
            html += '<td class="pp-cell-qty' + esHoy + '">' + prFmtNum(qty) + "</td>";
          }
        }
        html += "</tr>";

        // Renglon S (schedule, editable)
        html += '<tr class="pp-row-s"><td class="pp-col-tipo pp-tipo-s">S</td>';
        html += '<td class="pp-col-total">' + prFmtNum(row.sched_total || 0) + "</td>";
        for (const iso of data.dates) {
          const q = sched[iso];
          const esHoy = iso === hoy ? " pp-col-today" : "";
          const prop = prState.propuestas
            ? prState.propuestas[row.part_no + "|" + iso]
            : null;
          html +=
            '<td class="pp-cell-sched' + esHoy + '" data-part="' +
            prEscapeAttr(row.part_no) + '" data-date="' + iso + '" data-line="' +
            prEscapeAttr(row.inv && row.inv.line ? row.inv.line : "") +
            '" title="Clic para capturar schedule">' +
            (q != null ? prFmtNum(q) : "") +
            (prop
              ? '<span class="pp-sched-prop" title="Propuesta (sin guardar): +' + prop + '">&asymp;' +
                prFmtNum(prop) + "</span>"
              : "") +
            "</td>";
        }
        html += "</tr>";

        // Renglon I (proyeccion calculada)
        html += '<tr class="pp-row-i"><td class="pp-col-tipo pp-tipo-i">I</td>';
        html +=
          '<td class="pp-col-total">' +
          (projFinal == null ? "-" : prFmtNum(projFinal)) + "</td>";
        for (const iso of data.dates) {
          const v = proj[iso];
          const esHoy = iso === hoy ? " pp-col-today" : "";
          if (v == null) {
            html += '<td class="pp-cell-none' + esHoy + '">-</td>';
          } else {
            html +=
              '<td class="pp-cell-proj' + (v < 0 ? " pp-cell-neg" : "") + esHoy + '">' +
              prFmtNum(v) + "</td>";
          }
        }
        html += "</tr>";
      }
      tbody.innerHTML = html;
    }

    const info = prEl("pr-page-info");
    const desde = (data.page - 1) * data.page_size + 1;
    const hasta = Math.min(data.page * data.page_size, data.total_parts);
    if (info) {
      info.textContent = data.total_parts
        ? "Partes " + desde + "-" + hasta + " de " + prFmtNum(data.total_parts)
        : "Sin partes";
    }
    const prev = prEl("pr-btn-prev");
    const next = prEl("pr-btn-next");
    if (prev) prev.disabled = data.page <= 1;
    if (next) next.disabled = hasta >= data.total_parts;
  }

  // =============================
  // Schedule inline (renglon S)
  // =============================

  function prFreezeCellWidth(td) {
    // Congela ancho Y alto actuales para que el input no mueva la tabla
    const w = td.offsetWidth + "px";
    const h = td.offsetHeight + "px";
    td.style.width = w;
    td.style.minWidth = w;
    td.style.maxWidth = w;
    td.style.height = h;
    td.style.boxSizing = "border-box";
    td.style.overflow = "hidden";
  }

  function prUnfreezeCellWidth(td) {
    td.style.width = "";
    td.style.minWidth = "";
    td.style.maxWidth = "";
    td.style.height = "";
    td.style.boxSizing = "";
    td.style.overflow = "";
  }

  function prEditSchedCell(td) {
    if (td.querySelector("input")) return;
    const actual = td.textContent.replace(/[^\d]/g, "");
    td.dataset.prev = td.innerHTML;
    prFreezeCellWidth(td);
    td.innerHTML =
      '<input type="number" class="pp-sched-input" min="0" value="' + actual + '">';
    const input = td.querySelector("input");
    input.focus();
    input.select();

    let cerrado = false;
    const cancelar = () => {
      if (cerrado) return;
      cerrado = true;
      td.innerHTML = td.dataset.prev;
      prUnfreezeCellWidth(td);
    };
    const guardar = async () => {
      if (cerrado) return;
      cerrado = true;
      const valor = input.value.trim();
      td.innerHTML = '<span class="pp-spinner"></span>';
      try {
        const resp = await fetch("/api/part-planning/schedule", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({
            part_no: td.dataset.part,
            sched_date: td.dataset.date,
            sched_qty: valor === "" ? null : parseInt(valor, 10),
            linea: td.dataset.line || null,
            turno: "DIA",
          }),
        });
        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Error al guardar");
        prLoadData({ silent: true }); // recalcula renglon I sin perder el scroll
      } catch (e) {
        console.error("proyeccion: error guardando schedule:", e);
        alert("Error al guardar schedule: " + (e.message || e));
        td.innerHTML = td.dataset.prev;
        prUnfreezeCellWidth(td);
      }
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); guardar(); }
      else if (e.key === "Escape") cancelar();
    });
    input.addEventListener("blur", guardar);
  }

  // =============================
  // Inventario inline (LGEMM, ISEMM, SVC, ...)
  // =============================

  function prEditInvCell(td) {
    if (td.querySelector("input")) return;
    const actual = td.textContent.replace(/[^\d-]/g, "");
    td.dataset.prev = td.innerHTML;
    prFreezeCellWidth(td);
    td.innerHTML =
      '<input type="number" class="pp-sched-input" value="' +
      (actual === "-" ? "" : actual) + '">';
    const input = td.querySelector("input");
    input.focus();
    input.select();

    let cerrado = false;
    const cancelar = () => {
      if (cerrado) return;
      cerrado = true;
      td.innerHTML = td.dataset.prev;
      prUnfreezeCellWidth(td);
    };
    const guardar = async () => {
      if (cerrado) return;
      cerrado = true;
      const valor = input.value.trim();
      td.innerHTML = '<span class="pp-spinner"></span>';
      try {
        const resp = await fetch("/api/part-planning/inventory/field", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({
            part_no: td.dataset.part,
            field: td.dataset.field,
            value: valor === "" ? 0 : parseInt(valor, 10),
          }),
        });
        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Error al guardar");
        prLoadData({ silent: true }); // recalcula sin perder el scroll
      } catch (e) {
        console.error("proyeccion: error guardando inventario:", e);
        alert("Error al guardar inventario: " + (e.message || e));
        td.innerHTML = td.dataset.prev;
        prUnfreezeCellWidth(td);
      }
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); guardar(); }
      else if (e.key === "Escape") cancelar();
    });
    input.addEventListener("blur", guardar);
  }

  // =============================
  // Modal inventario (Part 10)
  // =============================

  function prOpenInvModal() {
    const input = prEl("pr-inv-file");
    if (input) input.value = "";
    prEl("pr-inv-file-info").style.display = "none";
    prEl("pr-inv-result").style.display = "none";
    prEl("pr-btn-inv-import").disabled = true;
    prEl("pr-inv-modal").style.display = "flex";
  }

  async function prInvImport() {
    const input = prEl("pr-inv-file");
    const file = input.files && input.files[0];
    if (!file) return;
    const btn = prEl("pr-btn-inv-import");
    const spinner = prEl("pr-inv-spinner");
    btn.disabled = true;
    if (spinner) spinner.style.display = "inline-block";
    const resultado = prEl("pr-inv-result");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const resp = await fetch("/api/part-planning/inventory/import", {
        method: "POST",
        body: fd,
        credentials: "same-origin",
      });
      const data = await resp.json();
      resultado.style.display = "block";
      if (!data.success) {
        resultado.innerHTML =
          '<div class="pp-error-text">' +
          prEscapeHtml((data.errors || ["Error desconocido"]).join(" | ")) + "</div>";
        return;
      }
      resultado.innerHTML =
        "<div><strong>Inventario importado (#" + data.import_id + ")</strong></div>" +
        "<div>Partes actualizadas: <strong>" + prFmtNum(data.parts) + "</strong></div>" +
        "<div>Schedules importados: <strong>" + prFmtNum(data.schedules) + "</strong></div>" +
        "<div>Vigente desde: " + prEscapeHtml(data.ref_date) + " al " +
        prEscapeHtml(data.date_to) + "</div>" +
        (data.warnings && data.warnings.length
          ? '<div class="pp-error-text">' + prEscapeHtml(data.warnings.join(" | ")) + "</div>"
          : "");
      prLoadData();
    } catch (e) {
      resultado.style.display = "block";
      resultado.innerHTML =
        '<div class="pp-error-text">' + prEscapeHtml(e.message || String(e)) + "</div>";
    } finally {
      btn.disabled = false;
      if (spinner) spinner.style.display = "none";
    }
  }

  // =============================
  // Historial
  // =============================

  async function prLoadHistory() {
    const modal = prEl("pr-history-modal");
    const tbody = prEl("pr-history-table").querySelector("tbody");
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
                "<tr><td>" + prEscapeHtml(r.imported_at) + "</td>" +
                "<td class=\"pp-col-file\">" + prEscapeHtml(r.original_filename) + "</td>" +
                "<td>" + prEscapeHtml(r.plan_year) + "</td>" +
                "<td>" + prEscapeHtml(r.date_from) + " a " + prEscapeHtml(r.date_to) + "</td>" +
                "<td>" + prFmtNum(r.parts_count) + "</td>" +
                "<td>" + prFmtNum(r.dates_count) + "</td>" +
                "<td>" + prFmtNum(r.records_count) + "</td>" +
                "<td>" + prFmtNum(r.zero_records_count) + "</td>" +
                "<td>" + prFmtNum(r.warning_count) + "</td>" +
                "<td>" + prEscapeHtml(r.import_mode) + "</td>" +
                "<td>" + prEscapeHtml(r.imported_by) + "</td>" +
                "<td>" + prEscapeHtml(r.status) + "</td></tr>"
            )
            .join("")
        : '<tr><td colspan="12" class="pp-empty">Sin importaciones registradas</td></tr>';
    } catch (e) {
      tbody.innerHTML =
        '<tr><td colspan="12" class="pp-empty pp-error-text">' +
        prEscapeHtml(e.message || "Error al cargar historial") + "</td></tr>";
    }
  }

  // =============================
  // Propuesta de schedule (mismo motor que Plan Proyectado)
  // =============================

  function prPropFecha(iso) {
    const DIAS = ["Dom", "Lun", "Mar", "Mie", "Jue", "Vie", "Sab"];
    const f = new Date(iso + "T00:00:00");
    return DIAS[f.getDay()] + " " +
      String(f.getDate()).padStart(2, "0") + "/" +
      String(f.getMonth() + 1).padStart(2, "0");
  }

  function prPropResetState() {
    prState.propuestas = null;
    prState.proposalId = null;
    prState.proposalVersion = null;
    prState.originalItems = null;
    prState.propItems = null;
    prState.proposalMeta = null;
    prState.proposalBusy = false;
    prState.proposalStale = false;
    prState.proposalStaleMessage = "";
  }

  function prPropCerrar(descartar, recargar) {
    const modal = prEl("pr-prop-modal");
    if (modal) modal.style.display = "none";
    if (descartar && (prState.propuestas || prState.proposalId)) {
      prPropResetState();
      if (recargar !== false) prLoadData({ silent: true }); // quita los fantasmas de la tabla
    }
  }

  function prPropDismiss() {
    if (prState.proposalBusy) return;
    const proposalId = prState.proposalId;
    const version = prState.proposalVersion;
    if (proposalId) {
      // Best effort: cerrar no equivale a una aprobacion, pero tampoco debe
      // dejar borradores DRAFT huerfanos en la base de datos.
      fetch("/api/part-planning/schedule/proponer/rechazar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        keepalive: true,
        body: JSON.stringify({
          proposal_id: proposalId,
          version: version,
          reason_code: "UI_DISMISSED",
          reason_text: "Cerrada sin aplicar",
        }),
      }).catch((error) => console.warn("No se pudo cerrar la propuesta persistida:", error));
    }
    prPropCerrar(true);
  }

  function prPropSetBusy(busy) {
    prState.proposalBusy = !!busy;
    const modal = prEl("pr-prop-modal");
    const bloquearCampos = prState.proposalBusy || prState.proposalStale;
    if (modal) {
      modal.setAttribute("aria-busy", prState.proposalBusy ? "true" : "false");
      modal.querySelectorAll("[data-prop-index]").forEach((control) => {
        control.disabled = bloquearCampos;
      });
    }
    const hayItems = (prState.propItems || []).length > 0;
    const applyBtn = prEl("pr-btn-prop-apply");
    const rejectBtn = prEl("pr-btn-prop-reject");
    const closeBtn = prEl("pr-btn-prop-close");
    const cancelBtn = prEl("pr-btn-prop-cancel");
    if (applyBtn) applyBtn.disabled = bloquearCampos || !hayItems || !prState.proposalId;
    if (rejectBtn) rejectBtn.disabled = bloquearCampos || !prState.proposalId;
    // Mientras hay una decision en vuelo no se permite desmontar el modal.
    // Una propuesta STALE si puede cerrarse para generar otra.
    if (closeBtn) closeBtn.disabled = prState.proposalBusy;
    if (cancelBtn) cancelBtn.disabled = prState.proposalBusy;
  }

  function prPropLineSummary(rows) {
    if (!rows || !rows.length) return "";
    return "<div class='pp-prop-line-summary'>" + rows.map((row) => {
      const klass = row.excede ? " pp-prop-line-card warn" : " pp-prop-line-card";
      return "<span class='" + klass.trim() + "'><strong>" +
        prEscapeHtml(row.linea) + " / " + prEscapeHtml(row.turno) + "</strong> &middot; " +
        prEscapeHtml(row.fecha) + " &middot; " + Number(row.horas || 0).toFixed(2) + "/" +
        Number(row.horas_max || 0).toFixed(1) + " h &middot; " +
        prFmtNum(row.lotes) + " lotes</span>";
    }).join("") + "</div>";
  }

  function prPropIsModified(item, index) {
    const original = (prState.originalItems || [])[index];
    if (!item || !original) return false;
    return item.included === false || item.sched_date !== original.sched_date ||
      item.linea !== original.linea || item.turno !== original.turno ||
      Number(item.qty) !== Number(original.qty);
  }

  function prPropLiveSummary() {
    const items = (prState.propItems || []).filter((item) => item.included !== false);
    const meta = prState.proposalMeta || {};
    const horasMax = Number(meta.horasMax || 9);
    const grupos = new Map();
    let totalQty = 0;
    const partes = new Set();
    let modificadas = 0;

    (prState.propItems || []).forEach((item, index) => {
      if (prPropIsModified(item, index)) modificadas++;
      if (item.included === false) return;
      const qty = Number(item.qty) || 0;
      const uph = Number(item.uph) || 0;
      totalQty += qty;
      partes.add(item.part_no);
      const key = [item.sched_date || "", item.linea || "SIN LINEA", item.turno || ""].join("|");
      if (!grupos.has(key)) {
        grupos.set(key, {
          fecha: item.sched_date || "",
          linea: item.linea || "SIN LINEA",
          turno: item.turno || "",
          horas: 0,
          horas_max: horasMax,
          lotes: 0,
        });
      }
      const grupo = grupos.get(key);
      grupo.horas += uph > 0 ? qty / uph : 0;
      grupo.lotes++;
    });

    const lineSummary = Array.from(grupos.values())
      .map((row) => ({ ...row, excede: row.horas > row.horas_max + 1e-6 }))
      .sort((a, b) => (a.fecha + a.linea + a.turno).localeCompare(b.fecha + b.linea + b.turno));
    return { items, totalQty, partes: partes.size, modificadas, lineSummary };
  }

  function prPropRenderSummary() {
    const container = prEl("pr-prop-resumen");
    if (!container) return;
    const meta = prState.proposalMeta || {};
    const live = prPropLiveSummary();
    const excluidas = Math.max((prState.propItems || []).length - live.items.length, 0);
    const stale = prState.proposalStale
      ? "<div class='pp-prop-stale'><strong>Propuesta desactualizada.</strong> " +
        prEscapeHtml(prState.proposalStaleMessage || "Los datos del MES cambiaron; genera una propuesta nueva.") +
        "</div>"
      : "";
    container.innerHTML =
      stale +
      "<div><strong>Propuesta " + prEscapeHtml(prState.proposalId || "") +
      "</strong> &middot; motor " + prEscapeHtml(meta.engineVersion || "") + "</div>" +
      "<div><strong>" + live.items.length + "</strong> capturas incluidas &middot; <strong>" +
      prFmtNum(live.totalQty) + "</strong> pzs &middot; <strong>" + live.partes +
      "</strong> partes &middot; " + prEscapeHtml(meta.dateFrom || "") + " a " +
      prEscapeHtml(meta.dateTo || "") + " &middot; " + live.modificadas +
      " modificadas &middot; " + excluidas + " excluidas</div>" +
      "<div class='pp-hint'>Puedes corregir fecha, linea, turno o cantidad. " +
      "El servidor volvera a validar datos, empaque y capacidad antes de aplicar. " +
      "Cada aceptacion o correccion se conserva para mejorar futuras propuestas.</div>" +
      prPropLineSummary(live.lineSummary);
  }

  function prPropRenderRows(items) {
    let filas = "";
    for (let index = 0; index < items.length; index++) {
      const p = items[index];
      const excepciones = (p.excepciones || []);
      const turnoOptions = ["DIA", "TIEMPO EXTRA", "NOCHE"].map((turno) =>
        "<option value='" + turno + "'" + (p.turno === turno ? " selected" : "") + ">" +
        turno + "</option>"
      ).join("");
      filas +=
        "<tr data-prop-row='" + index + "'>" +
        "<td><input type='checkbox' data-prop-index='" + index + "' data-prop-field='included' checked></td>" +
        "<td>" + prFmtNum(p.prioridad) + "</td>" +
        "<td class='pp-col-part'>" + prEscapeHtml(p.part_no) + "</td>" +
        "<td><input class='pp-prop-input' type='date' value='" + prEscapeHtml(p.sched_date) +
          "' data-prop-index='" + index + "' data-prop-field='sched_date'></td>" +
        "<td><input class='pp-prop-input pp-prop-line' maxlength='10' value='" +
          prEscapeHtml(p.linea) + "' data-prop-index='" + index + "' data-prop-field='linea'></td>" +
        "<td><select class='pp-prop-select' data-prop-index='" + index +
          "' data-prop-field='turno'>" + turnoOptions + "</select></td>" +
        "<td><input class='pp-prop-input pp-prop-qty' type='number' min='" +
          prEscapeHtml(p.pack_size || 1) + "' step='" + prEscapeHtml(p.pack_size || 1) +
          "' value='" + prEscapeHtml(p.qty) +
          "' data-prop-index='" + index + "' data-prop-field='qty'></td>" +
        "<td>" + prFmtNum(p.ct) + "</td>" +
        "<td>" + prFmtNum(p.uph) + "</td>" +
        "<td><span data-prop-hours='" + index + "'>" + Number(p.horas_requeridas || 0).toFixed(2) +
          " h</span></td>" +
        "<td>" + prFmtNum(p.inventario_antes) + " &rarr; <span data-prop-inv-after='" + index +
          "'>" + prFmtNum(p.inventario_despues) + "</span></td>" +
        "<td>" + prEscapeHtml(p.fecha_shortage) + "</td>" +
        "<td>" + prFmtNum(p.sched_actual || 0) + "</td>" +
        "<td>" + (excepciones.length
          ? "<span class='pp-prop-exception'>" + prEscapeHtml(excepciones.join(", ")) + "</span>"
          : "<span class='pp-prop-ok'>Sin excepciones</span>") + "</td></tr>";
    }
    return filas || "<tr><td colspan='14' class='pp-empty'>Sin faltantes factibles por cubrir en el rango</td></tr>";
  }

  function prPropRefreshRow(index) {
    const item = (prState.propItems || [])[index];
    const original = (prState.originalItems || [])[index];
    if (!item || !original) return;
    const row = document.querySelector("[data-prop-row='" + index + "']");
    if (row) {
      row.classList.toggle("pp-prop-row-excluded", item.included === false);
      const changed = prPropIsModified(item, index);
      row.classList.toggle("pp-prop-row-modified", changed);
    }
    const hours = document.querySelector("[data-prop-hours='" + index + "']");
    if (hours) hours.textContent = ((Number(item.qty) || 0) / (Number(item.uph) || 1)).toFixed(2) + " h";
    const invAfter = document.querySelector("[data-prop-inv-after='" + index + "']");
    if (invAfter) invAfter.textContent = prFmtNum((Number(item.inventario_antes) || 0) + (Number(item.qty) || 0));
  }

  function prPropHandleChange(target) {
    if (!target.dataset || target.dataset.propIndex == null) return false;
    if (prState.proposalBusy || prState.proposalStale) return true;
    const index = Number(target.dataset.propIndex);
    const item = (prState.propItems || [])[index];
    if (!item) return false;
    const field = target.dataset.propField;
    if (field === "included") item.included = !!target.checked;
    else if (field === "qty") item.qty = Number(target.value || 0);
    else if (field === "linea") item.linea = String(target.value || "").trim().toUpperCase();
    else if (field === "turno") item.turno = String(target.value || "").trim().toUpperCase();
    else if (field === "sched_date") item.sched_date = target.value;
    prPropRefreshRow(index);
    prPropRenderSummary();
    return true;
  }

  async function prProponerSchedule() {
    const btn = prEl("pr-btn-proponer");
    const from = prEl("pr-filter-date-from");
    const to = prEl("pr-filter-date-to");
    if (btn) { btn.disabled = true; btn.textContent = "Calculando..."; }
    try {
      const resp = await fetch("/api/part-planning/schedule/proponer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          date_from: from ? from.value : "",
          date_to: to ? to.value : "",
        }),
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || "Error al proponer");

      prState.propuestas = {};
      for (const p of data.proposals) {
        prState.propuestas[p.part_no + "|" + p.sched_date] = p.qty;
      }
      prState.proposalId = data.proposal_id;
      prState.proposalVersion = data.version;
      prState.originalItems = JSON.parse(JSON.stringify(data.proposals));
      prState.propItems = JSON.parse(JSON.stringify(data.proposals));
      prState.proposalMeta = {
        engineVersion: data.engine_version,
        dateFrom: data.date_from,
        dateTo: data.date_to,
        horasMax: data.line_summary && data.line_summary.length
          ? Number(data.line_summary[0].horas_max || 9)
          : 9,
      };
      prState.proposalBusy = false;
      prState.proposalStale = false;
      prState.proposalStaleMessage = "";
      for (const item of prState.propItems) item.included = true;
      await prLoadData({ silent: true }); // fantasmas visibles detras del modal

      // Llenar modal de revision
      prEl("pr-prop-table").querySelector("tbody").innerHTML = prPropRenderRows(prState.propItems);
      prPropRenderSummary();

      const ul = prEl("pr-prop-omitidas");
      if (data.omitidas_count) {
        ul.innerHTML =
          "<li><strong>Sin cubrir (" + data.omitidas_count + "):</strong></li>" +
          data.omitidas.map((o) => "<li>" + prEscapeHtml(o) + "</li>").join("");
        ul.style.display = "";
      } else {
        ul.style.display = "none";
      }

      prEl("pr-prop-wrap").style.display = "";
      const aplicarBtn = prEl("pr-btn-prop-apply");
      aplicarBtn.style.display = data.proposals.length ? "" : "none";
      const rejectBtn = prEl("pr-btn-prop-reject");
      rejectBtn.style.display = data.proposal_id ? "" : "none";
      prEl("pr-btn-prop-cancel").textContent = "Cerrar";
      prEl("pr-prop-modal").style.display = "flex";
      // Restablece tambien el boton Rechazar tras una decision anterior.
      prPropSetBusy(false);
    } catch (e) {
      alert("Error al proponer schedule: " + (e.message || e));
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Proponer schedule"; }
    }
  }

  async function prPropHandleStale(data) {
    prState.proposalBusy = false;
    prState.proposalStale = true;
    prState.proposalStaleMessage = data.error ||
      "El plan, inventario, RAW, capacidad o schedule cambio.";
    prPropRenderSummary();
    prPropSetBusy(false);
    if (confirm(prState.proposalStaleMessage + "\n\n¿Generar una propuesta nueva ahora?")) {
      prPropCerrar(true, false);
      await prProponerSchedule();
    }
  }

  async function prAplicarPropuesta() {
    const items = prState.propItems || [];
    if (!items.length || !prState.proposalId) { prPropCerrar(true); return; }
    if (prState.proposalBusy || prState.proposalStale) return;
    const btn = prEl("pr-btn-prop-apply");
    prPropSetBusy(true);
    try {
      const resp = await fetch("/api/part-planning/schedule/proponer/aplicar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          proposal_id: prState.proposalId,
          version: prState.proposalVersion,
          items: items.map((p) => ({
            item_id: p.item_id,
            included: p.included !== false,
            sched_date: p.sched_date,
            linea: p.linea,
            turno: p.turno,
            qty: Number(p.qty),
          })),
        }),
      });
      const data = await resp.json();
      if (resp.status === 409 && data.code === "PROPOSAL_STALE") {
        await prPropHandleStale(data);
        return;
      }
      if (!data.success) throw new Error(data.error || "Error al aplicar");
      prPropResetState();
      await prLoadData({ silent: true });
      // Resultado dentro del mismo modal
      prEl("pr-prop-resumen").innerHTML = data.already_applied
        ? "<div><strong>La propuesta ya habia sido aplicada.</strong> El renglon I esta actualizado.</div>"
        : "<div><strong>Aplicadas " + data.aplicadas + " capturas al schedule.</strong> " +
          prFmtNum(data.total_qty || 0) + " piezas. Modificadas: " +
          prFmtNum(data.modificadas || 0) + "; excluidas: " +
          prFmtNum(data.excluidas || 0) + ". El renglon I ya esta recalculado.</div>";
      prEl("pr-prop-wrap").style.display = "none";
      prEl("pr-prop-omitidas").style.display = "none";
      if (btn) btn.style.display = "none";
      prEl("pr-btn-prop-reject").style.display = "none";
      prEl("pr-btn-prop-cancel").textContent = "Cerrar";
      prPropSetBusy(false);
    } catch (e) {
      alert("Error al aplicar propuesta: " + (e.message || e));
      prPropSetBusy(false);
    }
  }

  async function prRechazarPropuesta() {
    if (!prState.proposalId) { prPropCerrar(true); return; }
    if (prState.proposalBusy || prState.proposalStale) return;
    const motivo = prompt(
      "Motivo del rechazo (linea, cantidad, material, capacidad, secuencia u otro):",
      ""
    );
    if (motivo === null) return;
    if (!motivo.trim()) {
      alert("Captura el motivo del rechazo para conservar feedback util.");
      return;
    }
    prPropSetBusy(true);
    try {
      const resp = await fetch("/api/part-planning/schedule/proponer/rechazar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          proposal_id: prState.proposalId,
          version: prState.proposalVersion,
          reason_code: "USER_REJECTED",
          reason_text: motivo.trim(),
        }),
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || "Error al rechazar");
      prPropCerrar(true);
    } catch (e) {
      alert("Error al rechazar propuesta: " + (e.message || e));
      prPropSetBusy(false);
    }
  }

  // TEMPORAL: sincroniza solo el schedule desde la hoja Part N del Excel
  async function prSyncSchedule(file) {
    const nombre = file.name.toLowerCase();
    if (!nombre.endsWith(".xlsx") && !nombre.endsWith(".xlsm")) {
      alert("Formato no permitido. Solo .xlsx o .xlsm");
      return;
    }
    if (!confirm("Reemplaza el schedule (renglon S) de cada parte del Excel por el del archivo, en el rango del Excel. Las partes que no esten en el Excel no se tocan. Continuar?")) return;
    const btn = prEl("pr-btn-sync-sched");
    if (btn) { btn.disabled = true; btn.textContent = "Sincronizando..."; }
    try {
      const fd = new FormData();
      fd.append("file", file);
      const resp = await fetch("/api/part-planning/schedule/sync-excel", {
        method: "POST",
        credentials: "same-origin",
        body: fd,
      });
      const data = await resp.json();
      if (!data.success) throw new Error((data.errors && data.errors[0]) || data.error || "Error");
      await prLoadData({ silent: true });
      alert(
        "Schedule sincronizado desde hoja " + data.sheet_name + ".\n" +
        data.parts + " partes, " + data.schedules + " capturas (" +
        data.date_from + " a " + data.date_to + ")."
      );
    } catch (e) {
      alert("Error al sincronizar schedule: " + (e.message || e));
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Sincronizar schedule (Excel)"; }
    }
  }

  // =============================
  // Listeners delegados (idempotentes)
  // =============================

  function prInitListeners() {
    if (document.body.dataset.prListenersAttached) return;
    document.body.dataset.prListenersAttached = "1";

    document.body.addEventListener("click", function (e) {
      const t = e.target;
      const hit = (id) => t.id === id || (t.closest && t.closest("#" + id));

      if (hit("pr-btn-proponer")) { e.preventDefault(); prProponerSchedule(); return; }
      if (hit("pr-btn-sync-sched")) {
        e.preventDefault();
        const f = prEl("pr-sync-file");
        if (f) { f.value = ""; f.click(); }
        return;
      }
      if (hit("pr-btn-prop-apply")) { e.preventDefault(); prAplicarPropuesta(); return; }
      if (hit("pr-btn-prop-reject")) { e.preventDefault(); prRechazarPropuesta(); return; }
      if (hit("pr-btn-prop-close") || hit("pr-btn-prop-cancel")) {
        prPropDismiss(); return;
      }
      if (hit("pr-btn-inventory")) { e.preventDefault(); prOpenInvModal(); return; }
      if (hit("pr-btn-inv-close") || hit("pr-btn-inv-cancel")) {
        prEl("pr-inv-modal").style.display = "none"; return;
      }
      if (hit("pr-btn-inv-import")) { e.preventDefault(); prInvImport(); return; }
      if (hit("pr-btn-history")) { e.preventDefault(); prLoadHistory(); return; }
      if (hit("pr-btn-history-close")) { prEl("pr-history-modal").style.display = "none"; return; }
      if (hit("pr-btn-search")) { e.preventDefault(); prState.page = 1; prLoadData(); return; }
      if (hit("pr-btn-week")) { e.preventDefault(); prSetDefaultDates(true); prState.page = 1; prLoadData(); return; }
      if (hit("pr-btn-prev")) { if (prState.page > 1) { prState.page--; prLoadData(); } return; }
      if (hit("pr-btn-next")) { prState.page++; prLoadData(); return; }
      const schedCell = t.closest && t.closest("#pr-plan-table td.pp-cell-sched");
      if (schedCell) { prEditSchedCell(schedCell); return; }
      const invCell = t.closest && t.closest("#pr-plan-table td.pp-cell-inv");
      if (invCell) { prEditInvCell(invCell); return; }
    });

    document.body.addEventListener("change", function (e) {
      if (prPropHandleChange(e.target)) return;
      if (e.target.id === "pr-filter-shortage") {
        prState.page = 1;
        prLoadData();
        return;
      }
      if (e.target.id === "pr-inv-file") {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        const nombre = file.name.toLowerCase();
        if (!nombre.endsWith(".xlsx") && !nombre.endsWith(".xlsm")) {
          alert("Formato no permitido. Solo .xlsx o .xlsm");
          e.target.value = "";
          return;
        }
        prEl("pr-inv-file-name").textContent = file.name;
        prEl("pr-inv-file-info").style.display = "block";
        prEl("pr-btn-inv-import").disabled = false;
      }
      if (e.target.id === "pr-sync-file") {
        const file = e.target.files && e.target.files[0];
        if (file) prSyncSchedule(file);
      }
    });

    document.body.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && e.target.id === "pr-filter-part") {
        e.preventDefault();
        prState.page = 1;
        prLoadData();
      }
    });
  }

  function prCleanup() {
    prState.page = 1;
  }

  // Los fragmentos AJAX viven dentro de contenedores con stacking contexts
  // propios. Portar los modales al body evita que queden debajo del navbar
  // aunque su z-index sea mayor.
  function prMoveModalsToBody() {
    ["pr-inv-modal", "pr-prop-modal", "pr-history-modal"].forEach((id) => {
      const matches = Array.from(document.querySelectorAll("#" + id));
      const modal = matches.pop();
      matches.forEach((duplicate) => duplicate.remove());
      if (modal && modal.parentNode !== document.body) document.body.appendChild(modal);
    });
  }

  // =============================
  // Exports globales + init dual (WF_003)
  // =============================

  window.initializeProyeccionEventListeners = prInitListeners;
  window.loadProyeccionData = function () {
    prState.page = 1;
    prLoadData();
  };
  window.limpiarProyeccion = prCleanup;

  function prBoot() {
    if (!document.getElementById("proyeccion-root")) return;
    prMoveModalsToBody();
    prInitListeners();
    prSetDefaultDates(false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", prBoot);
  } else {
    prBoot();
  }
})();
