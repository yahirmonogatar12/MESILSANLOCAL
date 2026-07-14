// Plan Proyectado: generador de lotes tipo hoja "LOTE N" (WF_003)
// Prefijo ppy-. Reusa estilos pp- de part_planning.css.
(function () {
  "use strict";

  const ppyState = { fecha: null };

  function ppyRoot() {
    return document.getElementById("plan-proyectado-root");
  }

  function ppyHoy() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
  }

  function ppyFecha() {
    const inp = document.getElementById("ppy-fecha");
    return (inp && inp.value) || ppyHoy();
  }

  function ppyNum(v) {
    return v === null || v === undefined ? "" : Number(v).toLocaleString("en-US");
  }

  function ppyEsc(s) {
    const div = document.createElement("div");
    div.textContent = s == null ? "" : String(s);
    return div.innerHTML;
  }

  function ppyMsg(texto, esError) {
    const el = document.getElementById("ppy-status-msg");
    if (!el) return;
    el.textContent = texto || "";
    el.style.color = esError ? "#ffb3b3" : "";
    if (texto) setTimeout(() => { if (el.textContent === texto) el.textContent = ""; }, 6000);
  }

  // ---------- Render ----------

  function ppyRender(data) {
    const lineasInp = document.getElementById("ppy-lineas");
    if (lineasInp && data.lineas_activas && document.activeElement !== lineasInp) {
      lineasInp.value = data.lineas_activas.join(",");
    }
    const tabla = document.getElementById("ppy-table");
    if (!tabla) return;
    const wrap = tabla.closest(".pp-table-wrap");
    const sl = wrap ? wrap.scrollLeft : 0;
    const st = wrap ? wrap.scrollTop : 0;

    const tbody = tabla.querySelector("tbody");
    const lotes = data.lotes || [];
    if (!lotes.length) {
      tbody.innerHTML =
        '<tr><td colspan="16" class="pp-empty">Sin lotes. Genera la propuesta del dia.</td></tr>';
      return;
    }
    const porLinea = {};
    (data.lineas || []).forEach((l) => { porLinea[l.linea] = l; });

    let html = "";
    let lineaActual = null;
    lotes.forEach((l) => {
      const clave = l.linea || "SIN LINEA";
      if (clave !== lineaActual) {
        lineaActual = clave;
        const res = porLinea[clave] || {};
        const horas = res.horas != null ? res.horas.toFixed(2) : "?";
        html +=
          '<tr class="ppy-linea-row' + (res.excede ? " ppy-excede" : "") + '">' +
          '<td class="pp-col-part">' + ppyEsc(clave) + "</td>" +
          '<td colspan="15">' + horas + " h / " + (res.horas_max || 9) + " h &middot; " +
          (res.lotes || 0) + " lotes" +
          (res.excede ? ' &nbsp;<strong>EXCEDE TIEMPO SIN TE</strong>' : "") +
          "</td></tr>";
      }
      const pend = l.status === "PENDIENTE";
      const qtyEditable = pend ? " ppy-edit" : "";
      html +=
        "<tr>" +
        '<td class="pp-col-part">' + (l.lot_no ? ppyEsc(l.lot_no) : "&mdash;") + "</td>" +
        "<td>" + ppyEsc(l.part_no) +
        (l.warn_uph ? ' <span class="ppy-warn" title="Sin UPH en raw: no se calcula el tiempo">!UPH</span>' : "") +
        "</td>" +
        "<td>" + ppyEsc(l.model || "") + "</td>" +
        "<td>" + ppyEsc(l.main_sub || "") + "</td>" +
        "<td>" + ppyNum(l.uph) + "</td>" +
        "<td>" + ppyNum(l.estandar_pack) + "</td>" +
        "<td>" + ppyNum(l.faltante) + "</td>" +
        '<td class="pp-cell-sched' + qtyEditable + (l.warn_pack ? " ppy-warn-pack" : "") + '"' +
        (pend ? ' data-id="' + l.id + '" data-field="qty_plan" title="' +
          (l.warn_pack ? "No es multiplo del pack. " : "") + 'Clic para editar"' : "") + ">" +
        ppyNum(l.qty_plan) + "</td>" +
        "<td>" + (l.time_horas != null ? l.time_horas.toFixed(2) : "") + "</td>" +
        '<td class="ppy-turno' + (pend ? " ppy-edit" : "") + '"' +
        (pend ? ' data-id="' + l.id + '" title="Clic para cambiar turno"' : "") + ">" +
        ppyEsc(l.turno) + "</td>" +
        '<td class="pp-cell-sched ppy-edit" data-id="' + l.id + '" data-field="fisico" title="Clic para capturar FISICO">' +
        ppyNum(l.fisico) + "</td>" +
        "<td" + (l.falta != null && l.falta < 0 ? ' class="pp-cell-neg"' : "") + ">" +
        ppyNum(l.falta) + "</td>" +
        "<td>" + (l.pct != null ? l.pct + "%" : "") + "</td>" +
        '<td class="ppy-edit ppy-coment" data-id="' + l.id + '" data-field="comentario" title="Clic para editar">' +
        ppyEsc(l.comentario || "") + "</td>" +
        '<td class="ppy-status-' + l.status.toLowerCase() + '">' + l.status + "</td>" +
        '<td><button class="pp-modal-x ppy-del" data-id="' + l.id + '" data-status="' + l.status +
        '" title="Eliminar/cancelar lote" type="button">&times;</button></td>' +
        "</tr>";
    });
    tbody.innerHTML = html;
    if (wrap) { wrap.scrollLeft = sl; wrap.scrollTop = st; }
  }

  // ---------- API ----------

  async function ppyPost(url, body) {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || "Error");
    return data;
  }

  async function ppyLoadData() {
    ppyState.fecha = ppyFecha();
    try {
      const resp = await fetch("/api/plan-proyectado?fecha=" + ppyState.fecha, {
        credentials: "same-origin",
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || "Error");
      ppyRender(data);
    } catch (e) {
      console.error("plan_proyectado: error cargando:", e);
      ppyMsg("Error al cargar: " + (e.message || e), true);
    }
  }

  async function ppyGenerate() {
    if (!confirm("Generar la propuesta reemplaza los lotes PENDIENTES de la fecha (los confirmados no se tocan). Continuar?")) return;
    const btn = document.getElementById("ppy-btn-generate");
    if (btn) btn.disabled = true;
    try {
      const data = await ppyPost("/api/plan-proyectado/generate", { fecha: ppyFecha() });
      ppyRender(data);
      let msg = "Propuesta generada: " + data.generados + " lotes.";
      const fuera = data.no_incluidos || [];
      if (fuera.length) {
        msg += " No cupieron " + fuera.length + ": " +
          fuera.slice(0, 5).map((f) => f.part_no + " (" + f.motivo + ")").join(", ") +
          (fuera.length > 5 ? "..." : "");
      }
      ppyMsg(msg, fuera.length > 0);
    } catch (e) {
      ppyMsg("Error al generar: " + (e.message || e), true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function ppyConfirmDia() {
    if (!confirm("Se asignaran numeros de lote (I" + ppyFecha().replace(/-/g, "") +
      "-####) y las cantidades se sumaran al renglon S de Proyeccion. Confirmar?")) return;
    const btn = document.getElementById("ppy-btn-confirm");
    if (btn) btn.disabled = true;
    try {
      const data = await ppyPost("/api/plan-proyectado/confirm", { fecha: ppyFecha() });
      ppyRender(data);
      ppyMsg("Confirmados " + data.confirmados + " lotes.");
    } catch (e) {
      alert(e.message || e);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function ppyAdd() {
    const partInp = document.getElementById("ppy-add-part");
    const qtyInp = document.getElementById("ppy-add-qty");
    const part = (partInp.value || "").trim();
    const qty = parseInt(qtyInp.value, 10);
    if (!part || !qty || qty <= 0) {
      ppyMsg("Captura parte y cantidad validas.", true);
      return;
    }
    try {
      const data = await ppyPost("/api/plan-proyectado/add", {
        fecha: ppyFecha(), part_no: part, qty: qty,
      });
      ppyRender(data);
      partInp.value = "";
      qtyInp.value = "";
    } catch (e) {
      ppyMsg("Error al agregar: " + (e.message || e), true);
    }
  }

  async function ppyGuardarLineas() {
    const inp = document.getElementById("ppy-lineas");
    try {
      const data = await ppyPost("/api/plan-proyectado/config", { lineas: inp.value });
      inp.value = data.lineas_activas.join(",");
      ppyMsg("Lineas guardadas: " + data.lineas_activas.join(", ") +
        ". Vuelve a generar la propuesta para aplicarlas.");
    } catch (e) {
      ppyMsg("Error al guardar lineas: " + (e.message || e), true);
    }
  }

  async function ppyDelete(btn) {
    const status = btn.dataset.status;
    if (status === "CONFIRMADO" &&
      !confirm("El lote esta CONFIRMADO: se cancelara y su cantidad se restara del Schedule S. Continuar?")) return;
    try {
      const data = await ppyPost("/api/plan-proyectado/delete", { id: parseInt(btn.dataset.id, 10) });
      ppyRender(data);
    } catch (e) {
      ppyMsg("Error al eliminar: " + (e.message || e), true);
    }
  }

  async function ppyTurnoCycle(td) {
    const turnos = ["DIA", "TIEMPO EXTRA", "NOCHE"];
    const actual = td.textContent.trim();
    const sig = turnos[(turnos.indexOf(actual) + 1) % turnos.length];
    try {
      const data = await ppyPost("/api/plan-proyectado/update", {
        id: parseInt(td.dataset.id, 10), field: "turno", value: sig,
      });
      ppyRender(data);
    } catch (e) {
      ppyMsg("Error al cambiar turno: " + (e.message || e), true);
    }
  }

  // ---------- Edicion inline (mismo patron que Proyeccion: celda congelada) ----------

  function ppyFreeze(td) {
    const w = td.offsetWidth + "px";
    const h = td.offsetHeight + "px";
    td.style.width = w; td.style.minWidth = w; td.style.maxWidth = w;
    td.style.height = h; td.style.boxSizing = "border-box"; td.style.overflow = "hidden";
  }

  function ppyUnfreeze(td) {
    td.style.width = ""; td.style.minWidth = ""; td.style.maxWidth = "";
    td.style.height = ""; td.style.boxSizing = ""; td.style.overflow = "";
  }

  function ppyEditCell(td) {
    if (td.querySelector("input")) return;
    const campo = td.dataset.field;
    const esTexto = campo === "comentario";
    const actual = esTexto ? td.textContent.trim() : td.textContent.replace(/[^\d]/g, "");
    td.dataset.prev = td.innerHTML;
    ppyFreeze(td);
    td.innerHTML = esTexto
      ? '<input type="text" class="pp-sched-input" maxlength="255">'
      : '<input type="number" class="pp-sched-input" min="0">';
    const input = td.querySelector("input");
    input.value = actual;
    input.focus();
    input.select();

    let cerrado = false;
    const cancelar = () => {
      if (cerrado) return;
      cerrado = true;
      td.innerHTML = td.dataset.prev;
      ppyUnfreeze(td);
    };
    const guardar = async () => {
      if (cerrado) return;
      cerrado = true;
      const valor = input.value.trim();
      td.innerHTML = '<span class="pp-spinner"></span>';
      try {
        const data = await ppyPost("/api/plan-proyectado/update", {
          id: parseInt(td.dataset.id, 10),
          field: campo,
          value: valor === "" ? null : (esTexto ? valor : parseInt(valor, 10)),
        });
        ppyRender(data);
      } catch (e) {
        ppyMsg("Error al guardar: " + (e.message || e), true);
        td.innerHTML = td.dataset.prev;
        ppyUnfreeze(td);
      }
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); guardar(); }
      if (e.key === "Escape") { e.preventDefault(); cancelar(); }
    });
    input.addEventListener("blur", guardar);
  }

  // ---------- Listeners (delegados, anti-duplicado) ----------

  function initializePlanProyectadoEventListeners() {
    const fechaInp = document.getElementById("ppy-fecha");
    if (fechaInp && !fechaInp.value) fechaInp.value = ppyHoy();

    if (document.body.dataset.ppyListenersAttached === "true") return;
    document.body.dataset.ppyListenersAttached = "true";

    document.body.addEventListener("click", (ev) => {
      if (!ppyRoot()) return;
      const del = ev.target.closest(".ppy-del");
      if (del) { ppyDelete(del); return; }
      if (ev.target.closest("#ppy-btn-generate")) { ppyGenerate(); return; }
      if (ev.target.closest("#ppy-btn-confirm")) { ppyConfirmDia(); return; }
      if (ev.target.closest("#ppy-btn-add")) { ppyAdd(); return; }
      if (ev.target.closest("#ppy-btn-lineas")) { ppyGuardarLineas(); return; }
      const turno = ev.target.closest(".ppy-turno.ppy-edit");
      if (turno) { ppyTurnoCycle(turno); return; }
      const celda = ev.target.closest("td.ppy-edit[data-field]");
      if (celda) { ppyEditCell(celda); }
    });

    document.body.addEventListener("change", (ev) => {
      if (ev.target && ev.target.id === "ppy-fecha") ppyLoadData();
    });

    document.body.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && ev.target &&
        (ev.target.id === "ppy-add-part" || ev.target.id === "ppy-add-qty")) {
        ev.preventDefault();
        ppyAdd();
      }
    });
  }

  function loadPlanProyectadoData() {
    initializePlanProyectadoEventListeners();
    ppyLoadData();
  }

  function limpiarPlanProyectado() {
    const tabla = document.getElementById("ppy-table");
    if (tabla) {
      tabla.querySelector("tbody").innerHTML =
        '<tr><td colspan="16" class="pp-empty">Sin lotes. Genera la propuesta del dia.</td></tr>';
    }
  }

  window.initializePlanProyectadoEventListeners = initializePlanProyectadoEventListeners;
  window.loadPlanProyectadoData = loadPlanProyectadoData;
  window.limpiarPlanProyectado = limpiarPlanProyectado;

  function ppyBoot() {
    if (ppyRoot()) loadPlanProyectadoData();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ppyBoot);
  } else {
    ppyBoot();
  }
})();
