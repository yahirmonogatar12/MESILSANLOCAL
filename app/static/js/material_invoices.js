(function () {
  const STYLE_ID = "material-invoices-css";
  const STYLE_VERSION = "20260624b";
  const STYLE_HREF = `/static/css/material_invoices.css?v=${STYLE_VERSION}`;

  const state = {
    selectedInvoiceId: null,
    selectedInvoice: null,
    activeTab: "lines",
    viewerInvoiceId: null,
    viewerWorkbook: null,
    viewerSheet: null,
    pendingUpload: null,
    // Lote pendiente de confirmar en pallet distinto (modal de linkeo).
    pendingPalletLink: null,
    pendingLineEdit: null,
    // Copia de los datos renderizados para exportar a Excel sin volver al backend.
    data: { invoices: [], lines: [], packing: [], links: [] },
  };

  function ensureModuleStyles() {
    const current = document.getElementById(STYLE_ID);
    if (current) {
      if (!current.getAttribute("href")?.includes(STYLE_VERSION)) {
        current.setAttribute("href", STYLE_HREF);
      }
      return;
    }
    const link = document.createElement("link");
    link.id = STYLE_ID;
    link.rel = "stylesheet";
    link.href = STYLE_HREF;
    document.head.appendChild(link);
  }

  function el(id) {
    return document.getElementById(id);
  }

  // Patron de modales del MES (ver Documentacion/SOLUCION_MODALES.md):
  // los modales deben vivir en document.body, no dentro del contenedor AJAX
  // (#mat-invoice-page), porque el header/tabs global crea contexto de apilado
  // y recorte. Al abrir se fuerzan estilos inline con !important para ganarle
  // a cualquier CSS conflictivo.
  function openModal(id) {
    const modal = el(id);
    if (!modal) return null;
    if (modal.parentElement !== document.body) {
      document.body.appendChild(modal);
    }
    modal.hidden = false;
    modal.style.cssText = `
      display: flex !important;
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      width: 100% !important;
      height: 100% !important;
      background: rgba(0,0,0,0.6) !important;
      justify-content: center !important;
      align-items: center !important;
      padding: 12px !important;
      z-index: 2147483600 !important;
      opacity: 1 !important;
      visibility: visible !important;
    `;
    return modal;
  }

  function hideModal(id) {
    const modal = el(id);
    if (!modal) return;
    modal.style.cssText = "display: none !important;";
    modal.hidden = true;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function numberText(value) {
    if (value === null || value === undefined || value === "") return "";
    const n = Number(value);
    if (!Number.isFinite(n)) return escapeHtml(value);
    return n.toLocaleString("en-US", { maximumFractionDigits: 4 });
  }

  function statusBadge(value) {
    const text = String(value || "");
    return `<span class="mat-invoice-status ${escapeHtml(text)}">${escapeHtml(text)}</span>`;
  }

  function setMessage(targetId, message, type) {
    const box = el(targetId);
    if (!box) return;
    if (!message) {
      box.hidden = true;
      box.textContent = "";
      box.classList.remove("success");
      return;
    }
    box.hidden = false;
    box.textContent = message;
    box.classList.toggle("success", type === "success");
  }

  function setLoading(active) {
    const loader = el("mat-invoice-loading");
    if (loader) loader.hidden = !active;
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, { credentials: "same-origin", ...(options || {}) });
    const contentType = res.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await res.json() : { error: await res.text() };
    if (!res.ok || data.error || data.success === false) {
      const err = new Error(data.message || data.error || `HTTP ${res.status}`);
      err.payload = data;
      err.status = res.status;
      throw err;
    }
    return data;
  }

  function queryParams() {
    const params = new URLSearchParams();
    const q = el("mat-invoice-search")?.value.trim();
    const estado = el("mat-invoice-state")?.value;
    const desde = el("mat-invoice-date-from")?.value;
    const hasta = el("mat-invoice-date-to")?.value;
    if (q) params.set("q", q);
    if (estado) params.set("estado", estado);
    // "Solo pendientes" ignora el rango de fechas: un invoice pendiente de dias
    // anteriores sigue abierto y debe verse aunque no sea de hoy.
    const soloPendientes = estado === "PENDIENTES";
    if (!soloPendientes && desde) params.set("fecha_inicio", desde);
    if (!soloPendientes && hasta) params.set("fecha_fin", hasta);
    return params;
  }

  function clearFilters() {
    if (el("mat-invoice-search")) el("mat-invoice-search").value = "";
    if (el("mat-invoice-state")) el("mat-invoice-state").value = "";
    // Las fechas vuelven al dia de hoy (default inyectado por el servidor),
    // no a vacio, para mantener el filtro centrado en el dia actual.
    const from = el("mat-invoice-date-from");
    const to = el("mat-invoice-date-to");
    if (from) from.value = from.dataset.defaultDate || "";
    if (to) to.value = to.dataset.defaultDate || "";
    loadInvoices();
  }

  async function loadInvoices() {
    ensureModuleStyles();
    setLoading(true);
    setMessage("mat-invoice-upload-message", "");
    try {
      const data = await fetchJson(`/api/material_admin/invoices?${queryParams().toString()}`);
      renderInvoiceList(data.records || []);
    } catch (err) {
      setMessage("mat-invoice-upload-message", `Error al cargar invoices: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function renderInvoiceList(rows) {
    const body = el("mat-invoice-list-body");
    state.data.invoices = rows;
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="9">No hay invoices cargadas.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => {
      const selected = Number(row.id) === Number(state.selectedInvoiceId) ? " selected" : "";
      const tieneArchivo = Boolean(row.archivo_ruta);
      const verBtn = tieneArchivo
        ? `<button class="mat-invoice-btn mat-invoice-view-excel" type="button" data-view-excel-id="${escapeHtml(row.id)}" data-view-excel-name="${escapeHtml(row.numero_invoice)}">Ver</button>`
        : `<span class="mat-invoice-muted">—</span>`;
      const tieneLinks = Number(row.links_activos) > 0;
      const delBtn = `<button class="mat-invoice-btn danger mat-invoice-delete" type="button" data-delete-invoice-id="${escapeHtml(row.id)}" data-delete-invoice-name="${escapeHtml(row.numero_invoice)}" ${tieneLinks ? "disabled title=\"Tiene links activos; no se puede eliminar\"" : ""}>Eliminar</button>`;
      return `<tr class="${selected}" data-invoice-id="${escapeHtml(row.id)}">
        <td class="mat-invoice-clickable">${escapeHtml(row.numero_invoice)}</td>
        <td>${statusBadge(row.estado)}</td>
        <td title="${escapeHtml(row.tipo)}">${escapeHtml(row.tipo)}</td>
        <td>${numberText(row.total_lineas)}</td>
        <td>${numberText(row.total_packing)}</td>
        <td>${numberText(row.links_activos)}</td>
        <td>${escapeHtml(row.fecha_carga)}</td>
        <td>${verBtn}</td>
        <td>${delBtn}</td>
      </tr>`;
    }).join("");
  }

  async function loadDetail(invoiceId) {
    if (!invoiceId) return;
    state.selectedInvoiceId = invoiceId;
    setLoading(true);
    setMessage("mat-invoice-detail-message", "");
    try {
      const data = await fetchJson(`/api/material_admin/invoices/${encodeURIComponent(invoiceId)}`);
      state.selectedInvoice = data.invoice;
      renderDetail(data);
      el("mat-invoice-detail").hidden = false;
      await loadInvoices();
    } catch (err) {
      setMessage("mat-invoice-upload-message", `Error al cargar detalle: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function renderDetail(data) {
    const invoice = data.invoice || {};
    const title = el("mat-invoice-detail-title");
    const subtitle = el("mat-invoice-detail-subtitle");
    if (title) title.textContent = `Invoice ${invoice.numero_invoice || ""}`;
    if (subtitle) {
      subtitle.textContent = `${invoice.estado || ""} | ${invoice.tipo || ""} | ${invoice.archivo_nombre || ""}`;
    }
    // El boton Cerrar refleja el estado: cerrado -> "Reabrir invoice".
    const closeBtn = el("mat-invoice-close");
    if (closeBtn) {
      const cerrado = invoice.cerrado_manual == 1 || invoice.cerrado_manual === true;
      closeBtn.textContent = cerrado ? "Reabrir invoice" : "Cerrar invoice";
      closeBtn.dataset.cerrado = cerrado ? "1" : "0";
    }
    renderLines(data.lines || []);
    renderPacking(data.packing || []);
    renderLinks(data.links || []);
    syncTabs();
  }

  function renderLines(rows) {
    const body = el("mat-invoice-lines-body");
    state.data.lines = rows;
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="10">Sin lineas.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => {
      const links = Number(row.links_activos || 0);
      const editBtn = `<button type="button" class="mat-invoice-btn small mat-invoice-edit-line"
        data-edit-line-id="${escapeHtml(row.id)}"
        ${links > 0 ? "disabled title=\"Tiene links activos; no se puede editar\"" : ""}>Editar</button>`;
      return `<tr>
      <td>${numberText(row.line_no)}</td>
      <td title="${escapeHtml(row.raw_part_num)}">${escapeHtml(row.raw_part_num)}</td>
      <td title="${escapeHtml(row.numero_parte_sistema)}">${escapeHtml(row.numero_parte_sistema)}</td>
      <td title="${escapeHtml(row.descripcion)}">${escapeHtml(row.descripcion)}</td>
      <td>${numberText(row.cantidad)}</td>
      <td>${escapeHtml(row.uom)}</td>
      <td>${numberText(row.costo_unitario)}</td>
      <td>${numberText(row.costo_total)}</td>
      <td>${statusBadge(row.estado_match)}</td>
      <td>${editBtn}</td>
    </tr>`;
    }).join("");
  }

  function renderPacking(rows) {
    const body = el("mat-invoice-packing-body");
    state.data.packing = rows;
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="13">Sin packing.</td></tr>`;
      return;
    }
    // Las diferencias de pallet van primero (requieren atencion); el resto
    // conserva su orden. Array.sort es estable, asi que no altera lo demas.
    const ordered = rows.slice().sort((a, b) => {
      const da = a.estado_match === "DIFERENCIA_PALLET" ? 0 : 1;
      const db = b.estado_match === "DIFERENCIA_PALLET" ? 0 : 1;
      return da - db;
    });
    body.innerHTML = ordered.map((row) => {
      // Filas de material llegado en pallet inesperado: se resaltan y ofrecen
      // un boton para confirmar/linkear a un packing parcial de la misma parte.
      const diff = row.estado_match === "DIFERENCIA_PALLET";
      const accion = diff
        ? `<button type="button" class="mat-invoice-btn small warning mat-invoice-link-pallet"
             data-lote="${escapeHtml(row.ejemplo_codigo)}"
             data-pallet="${escapeHtml(row.pallet_no)}"
             data-parte="${escapeHtml(row.numero_parte_sistema)}">Confirmar/linkear</button>`
        : escapeHtml(row.mensaje_match);
      // Flecha desplegable solo cuando el packing tiene lotes aplicados.
      const tieneLotes = Array.isArray(row.lotes) && row.lotes.length;
      const toggle = tieneLotes
        ? `<button type="button" class="mat-invoice-lote-toggle" data-toggle-lotes="${escapeHtml(row.id)}" aria-expanded="false" title="Ver lotes aplicados">▶</button> `
        : "";
      // Exceso: se aplico mas de lo facturado. Se resalta la celda Aplicado y
      // se agrega un badge "EXCESO +N" junto al estado.
      const exceso = row.cantidad_exceso != null && Number(row.cantidad_exceso) > 0
        ? Number(row.cantidad_exceso) : 0;
      const aplicadoCell = exceso
        ? `<td class="mat-invoice-status DIFERENCIA" title="Aplicado ${numberText(row.cantidad_aplicada_activa)} sobre ${numberText(row.cantidad_packing)} facturado (+${numberText(exceso)})">${numberText(row.cantidad_aplicada_activa)}</td>`
        : `<td>${numberText(row.cantidad_aplicada_activa)}</td>`;
      const estadoCell = exceso
        ? `${statusBadge(row.estado_match)} <span class="mat-invoice-status DIFERENCIA" title="Sobrante sobre lo facturado">EXCESO +${numberText(exceso)}</span>`
        : statusBadge(row.estado_match);
      const fila = `<tr class="${diff ? "mat-invoice-row-diff" : ""}">
      <td>${toggle}${numberText(row.line_no)}</td>
      <td>${escapeHtml(row.pallet_no_original)}</td>
      <td>${escapeHtml(row.pallet_no)}</td>
      <td title="${escapeHtml(row.numero_parte_sistema)}">${escapeHtml(row.numero_parte_sistema)}</td>
      <td>${numberText(row.cantidad_packing)}</td>
      <td>${numberText(row.entradas_recibidas)}</td>
      <td>${numberText(row.cantidad_recibida)}</td>
      <td>${numberText(row.cantidad_pendiente_entrada)}</td>
      ${aplicadoCell}
      <td>${numberText(row.kg)}</td>
      <td>${numberText(row.cbm)}</td>
      <td>${estadoCell}</td>
      <td title="${escapeHtml(row.mensaje_match)}">${accion}</td>
    </tr>`;
      return fila + renderPackingLotes(row.id, row.lotes);
    }).join("");
  }

  // Sub-filas: desglose de los lotes aplicados a un packing line. Conserva la
  // trazabilidad de que pallet real llego cada cantidad. Las que llegaron en
  // pallet distinto se marcan con su pallet recibido vs esperado + nota.
  // Arrancan ocultas; se despliegan con la flecha del packing line.
  function renderPackingLotes(parentId, lotes) {
    if (!Array.isArray(lotes) || !lotes.length) return "";
    return lotes.map((l) => {
      const palletDistinto = l.pallet_recibido != null && l.pallet_recibido !== "";
      let palletCell = "";
      if (palletDistinto) {
        const tip = `Llego en pallet ${l.pallet_recibido} (esperado ${l.pallet_esperado || "?"})` +
          (l.nota_aplicacion ? ` — ${l.nota_aplicacion}` : "");
        palletCell = `<span class="mat-invoice-status DIFERENCIA" title="${escapeHtml(tip)}">pallet ${escapeHtml(l.pallet_recibido)}</span>`;
      }
      return `<tr class="mat-invoice-lote-row${palletDistinto ? " mat-invoice-row-diff" : ""}" data-lotes-of="${escapeHtml(parentId)}" hidden>
        <td></td>
        <td></td>
        <td>${palletCell}</td>
        <td colspan="2" title="${escapeHtml(l.codigo_material_recibido)}">↳ ${escapeHtml(l.codigo_material_recibido)}</td>
        <td></td>
        <td></td>
        <td></td>
        <td>${numberText(l.cantidad_aplicada)}</td>
        <td></td>
        <td></td>
        <td></td>
        <td title="${escapeHtml(l.nota_aplicacion)}">${escapeHtml(l.nota_aplicacion || "")}</td>
      </tr>`;
    }).join("");
  }

  function renderLinks(rows) {
    const body = el("mat-invoice-links-body");
    state.data.links = rows;
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="10">Sin links.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => {
      // Registro de pallet distinto: esperado -> recibido + nota.
      let pallet = "";
      if (row.pallet_recibido || row.pallet_esperado) {
        const txt = `${row.pallet_recibido || "?"} (esperado ${row.pallet_esperado || "?"})`;
        const tip = row.nota_aplicacion ? `${txt} — ${row.nota_aplicacion}` : txt;
        pallet = `<span class="mat-invoice-status DIFERENCIA" title="${escapeHtml(tip)}">${escapeHtml(txt)}</span>`;
      }
      return `<tr>
      <td>${escapeHtml(row.id)}</td>
      <td title="${escapeHtml(row.codigo_material_recibido)}">${escapeHtml(row.codigo_material_recibido)}</td>
      <td title="${escapeHtml(row.numero_parte_sistema)}">${escapeHtml(row.numero_parte_sistema)}</td>
      <td>${numberText(row.cantidad_aplicada)}</td>
      <td>${numberText(row.costo_unitario)} ${escapeHtml(row.moneda)}</td>
      <td>${pallet}</td>
      <td>${statusBadge(row.estado)}</td>
      <td>${escapeHtml(row.usuario_aplicacion)}</td>
      <td>${escapeHtml(row.fecha_aplicacion)}</td>
      <td>${escapeHtml(row.usuario_desaplicado)}</td>
    </tr>`;
    }).join("");
  }

  function closePreview() {
    setPreviewLoading(false);
    hideModal("mat-invoice-preview");
    state.pendingUpload = null;
  }

  // Paso 1: parsea el Excel y muestra en un modal lo que se cargaria.
  async function openPreview(event) {
    event.preventDefault();
    const form = el("mat-invoice-upload-form");
    const file = el("mat-invoice-upload-file")?.files?.[0];
    if (!form || !file) {
      setMessage("mat-invoice-upload-message", "Selecciona un archivo Excel.");
      return;
    }
    // Guarda una copia del FormData para la confirmacion (el input no cambia).
    state.pendingUpload = new FormData(form);
    setLoading(true);
    try {
      const data = await fetchJson("/api/material_admin/invoices/preview", {
        method: "POST",
        body: state.pendingUpload,
      });
      renderPreview(data);
      openModal("mat-invoice-preview");
      setMessage("mat-invoice-upload-message", "");
    } catch (err) {
      state.pendingUpload = null;
      setMessage("mat-invoice-upload-message", `No se pudo previsualizar: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function renderPreview(data) {
    const subtitle = el("mat-invoice-preview-subtitle");
    if (subtitle) {
      const dup = data.duplicado
        ? ` — YA EXISTE (${data.duplicado.motivo})`
        : "";
      subtitle.textContent =
        `Invoice ${data.numero_invoice || ""} · ${numberText(data.total_lineas)} lineas · ` +
        `Total ${data.total_monto} · Sin parte en sistema: ${numberText(data.partes_sin_sistema)}${dup}`;
    }
    const msg = el("mat-invoice-preview-message");
    const confirmBtn = el("mat-invoice-preview-confirm");
    const avisos = [];
    if (data.duplicado) avisos.push("Esta invoice ya fue cargada; no se podra confirmar.");
    if (data.partes_sin_sistema) avisos.push(`${data.partes_sin_sistema} parte(s) no existen en materiales (quedaran como diferencia).`);
    (data.warnings || []).forEach((w) => avisos.push(w));
    if (avisos.length) {
      setMessage("mat-invoice-preview-message", avisos.join(" "), data.duplicado ? "" : "success");
    } else if (msg) {
      msg.hidden = true;
    }
    if (confirmBtn) confirmBtn.disabled = Boolean(data.duplicado);

    const body = el("mat-invoice-preview-body");
    if (!body) return;
    const rows = data.lines || [];
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="10">Sin lineas.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map((row) => {
      const diff = row.estado_match === "SIN_ALIAS";
      return `<tr class="${diff ? "mat-invoice-row-diff" : ""}">
        <td>${escapeHtml(row.line_no)}</td>
        <td>${escapeHtml(row.pallet_no)}</td>
        <td>${escapeHtml(row.raw_part_num)}</td>
        <td>${escapeHtml(row.numero_parte_sistema)}</td>
        <td title="${escapeHtml(row.descripcion)}">${escapeHtml(row.descripcion)}</td>
        <td>${numberText(row.cantidad)}</td>
        <td>${escapeHtml(row.uom)}</td>
        <td>${escapeHtml(row.costo_unitario)}</td>
        <td>${escapeHtml(row.costo_total)}</td>
        <td>${escapeHtml(diff ? "SIN PARTE" : "OK")}</td>
      </tr>`;
    }).join("");
  }

  // Activa/desactiva el estado "cargando" dentro del modal de preview:
  // el loader global vive fuera del modal (z-index del modal lo tapa),
  // asi que mostramos el progreso en el propio boton de confirmar.
  function setPreviewLoading(active) {
    const confirmBtn = el("mat-invoice-preview-confirm");
    const cancelBtns = document.querySelectorAll("#mat-invoice-preview [data-preview-close]");
    if (confirmBtn) {
      if (active) {
        if (!confirmBtn.dataset.label) confirmBtn.dataset.label = confirmBtn.textContent;
        confirmBtn.disabled = true;
        confirmBtn.classList.add("is-loading");
        confirmBtn.textContent = "Cargando...";
      } else {
        confirmBtn.disabled = false;
        confirmBtn.classList.remove("is-loading");
        if (confirmBtn.dataset.label) {
          confirmBtn.textContent = confirmBtn.dataset.label;
          delete confirmBtn.dataset.label;
        }
      }
    }
    cancelBtns.forEach((btn) => { btn.disabled = active; });
  }

  // Paso 2: confirma y carga de verdad usando el FormData previsualizado.
  async function confirmUpload() {
    if (!state.pendingUpload) return;
    setLoading(true);
    setPreviewLoading(true);
    setMessage("mat-invoice-preview-message", "Cargando invoice, no cierres esta ventana...", "success");
    try {
      const data = await fetchJson("/api/material_admin/invoices/upload", {
        method: "POST",
        body: state.pendingUpload,
      });
      closePreview();
      setMessage("mat-invoice-upload-message", `Invoice cargada: ${data.lineas} lineas, ${data.packing} packing.`, "success");
      el("mat-invoice-upload-form")?.reset();
      await loadInvoices();
      await loadDetail(data.invoice_id);
    } catch (err) {
      if (err.status === 409 && err.payload?.duplicado) {
        setMessage("mat-invoice-preview-message", `${err.payload.message || "Duplicado"} (${err.payload.motivo || ""})`);
      } else {
        setMessage("mat-invoice-preview-message", `Error al cargar: ${err.message}`);
      }
    } finally {
      setPreviewLoading(false);
      setLoading(false);
    }
  }

  async function deleteInvoice(invoiceId, numeroInvoice) {
    if (!invoiceId) return;
    if (!window.confirm(`¿Eliminar la invoice ${numeroInvoice || invoiceId}? Esta accion no se puede deshacer.`)) {
      return;
    }
    setLoading(true);
    try {
      await fetchJson(`/api/material_admin/invoices/${encodeURIComponent(invoiceId)}`, {
        method: "DELETE",
      });
      setMessage("mat-invoice-upload-message", `Invoice ${numeroInvoice || invoiceId} eliminada.`, "success");
      if (Number(state.selectedInvoiceId) === Number(invoiceId)) {
        state.selectedInvoiceId = null;
        if (el("mat-invoice-detail")) el("mat-invoice-detail").hidden = true;
      }
      await loadInvoices();
    } catch (err) {
      const msg = err.status === 409 ? (err.payload?.error || err.message) : err.message;
      setMessage("mat-invoice-upload-message", `No se pudo eliminar: ${msg}`);
    } finally {
      setLoading(false);
    }
  }

  async function postAction(action, body) {
    if (!state.selectedInvoiceId) return;
    setLoading(true);
    setMessage("mat-invoice-detail-message", "");
    try {
      const data = await fetchJson(`/api/material_admin/invoices/${state.selectedInvoiceId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      });
      const omitted = Number(data.omitidos || 0);
      const applied = Number(data.aplicados || 0);
      const unapplied = Number(data.links_desaplicados || data.unapply?.links_desaplicados || 0);
      // Lotes que llegaron en un pallet distinto: se detectan pero no se aplican.
      const palletDiffs = (data.skipped || []).filter((s) => s && s.pallet_mismatch);
      let extra = "";
      if (palletDiffs.length) {
        const detalle = palletDiffs.slice(0, 8).map((s) =>
          `${s.codigo_material_recibido} (pallet ${s.pallet_lote} vs ${s.pallet_packing})`
        ).join(", ");
        const mas = palletDiffs.length > 8 ? ` y ${palletDiffs.length - 8} mas` : "";
        extra = ` ⚠️ ${palletDiffs.length} lote(s) con pallet distinto, no aplicados (revisar): ${detalle}${mas}.`;
      }
      setMessage(
        "mat-invoice-detail-message",
        `Estado: ${data.estado || ""}. Aplicados: ${applied}. Omitidos: ${omitted}. Desaplicados: ${unapplied}.${extra}`,
        palletDiffs.length ? "" : "success"
      );
      await loadDetail(state.selectedInvoiceId);
    } catch (err) {
      setMessage("mat-invoice-detail-message", `Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function closeLineEdit() {
    hideModal("mat-invoice-line-edit");
    state.pendingLineEdit = null;
  }

  function setInputValue(id, value) {
    const input = el(id);
    if (input) input.value = value ?? "";
  }

  function openLineEdit(lineId) {
    if (!state.selectedInvoiceId || !lineId) return;
    const row = state.data.lines.find((item) => Number(item.id) === Number(lineId));
    if (!row) {
      setMessage("mat-invoice-detail-message", "No se encontro la linea para editar.");
      return;
    }
    state.pendingLineEdit = { lineId, row };
    const modal = openModal("mat-invoice-line-edit");
    if (!modal) return;
    const subtitle = el("mat-invoice-line-edit-subtitle");
    if (subtitle) subtitle.textContent = `Linea ${row.line_no || lineId}`;
    setInputValue("mat-invoice-line-no", row.line_no);
    setInputValue("mat-invoice-line-raw-part", row.raw_part_num);
    setInputValue("mat-invoice-line-part", row.numero_parte_sistema);
    setInputValue("mat-invoice-line-description", row.descripcion);
    setInputValue("mat-invoice-line-qty", row.cantidad);
    setInputValue("mat-invoice-line-uom", row.uom);
    setInputValue("mat-invoice-line-unit-cost", row.costo_unitario);
    setInputValue("mat-invoice-line-total", row.costo_total);
    const partInput = el("mat-invoice-line-part");
    if (partInput) {
      setTimeout(() => {
        partInput.focus();
        partInput.select();
      }, 0);
    }
    setMessage("mat-invoice-line-edit-message", "");
  }

  function lineEditPayload() {
    return {
      line_no: el("mat-invoice-line-no")?.value?.trim() || "",
      raw_part_num: el("mat-invoice-line-raw-part")?.value?.trim() || "",
      numero_parte_sistema: el("mat-invoice-line-part")?.value?.trim() || "",
      descripcion: el("mat-invoice-line-description")?.value?.trim() || "",
      cantidad: el("mat-invoice-line-qty")?.value?.trim() || "",
      uom: el("mat-invoice-line-uom")?.value?.trim() || "",
      costo_unitario: el("mat-invoice-line-unit-cost")?.value?.trim() || "",
      costo_total: el("mat-invoice-line-total")?.value?.trim() || "",
    };
  }

  async function saveLineEdit() {
    const pending = state.pendingLineEdit;
    const payload = lineEditPayload();
    if (!pending) return;
    if (!payload.raw_part_num || !payload.numero_parte_sistema || !payload.cantidad) {
      setMessage("mat-invoice-line-edit-message", "Parte raw, Parte sistema y Cantidad son requeridos.");
      return;
    }
    setLoading(true);
    try {
      const data = await fetchJson(
        `/api/material_admin/invoices/${state.selectedInvoiceId}/lines/${pending.lineId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      closeLineEdit();
      const extra = data.estado_match === "SIN_ALIAS"
        ? " La parte no existe en materiales; queda marcada como diferencia."
        : "";
      setMessage(
        "mat-invoice-detail-message",
        `Linea actualizada. Parte sistema: ${data.numero_parte_sistema}. Packing actualizado: ${numberText(data.packing_actualizados)}.${extra}`,
        data.estado_match === "SIN_ALIAS" ? "" : "success"
      );
      await loadDetail(state.selectedInvoiceId);
    } catch (err) {
      const msg = err.status === 409 ? (err.payload?.error || err.message) : err.message;
      setMessage("mat-invoice-line-edit-message", `No se pudo guardar: ${msg}`);
    } finally {
      setLoading(false);
    }
  }

  function closePalletLink() {
    hideModal("mat-invoice-pallet-link");
    state.pendingPalletLink = null;
  }

  // Abre el modal para confirmar un lote que llego en pallet distinto y elegir
  // a que packing parcial (de la misma parte) linkearlo.
  async function openPalletLink(codigo, palletRecibido, parte) {
    if (!state.selectedInvoiceId || !codigo) return;
    state.pendingPalletLink = { codigo };
    const modal = openModal("mat-invoice-pallet-link");
    if (!modal) return;
    const subtitle = el("mat-invoice-pallet-link-subtitle");
    const target = el("mat-invoice-pallet-link-target");
    const note = el("mat-invoice-pallet-link-note");
    if (subtitle) subtitle.textContent = "Cargando...";
    if (target) target.innerHTML = "";
    if (note) note.value = "";
    setMessage("mat-invoice-pallet-link-message", "");
    try {
      const params = new URLSearchParams({ codigo_material_recibido: codigo });
      const data = await fetchJson(
        `/api/material_admin/invoices/${state.selectedInvoiceId}/partial-packing?${params.toString()}`
      );
      const records = data.records || [];
      if (subtitle) {
        subtitle.textContent =
          `Lote ${codigo} · parte ${data.numero_parte_sistema || parte || ""} · ` +
          `llego en pallet ${data.pallet_recibido || palletRecibido || "?"} · ` +
          `cantidad ${numberText(data.cantidad_lote)}`;
      }
      if (!records.length) {
        setMessage("mat-invoice-pallet-link-message",
          "No hay packing lines parciales de esta parte para linkear.");
        if (target) target.innerHTML = `<option value="">(sin opciones)</option>`;
        return;
      }
      if (target) {
        target.innerHTML = records.map((r) =>
          `<option value="${escapeHtml(r.id)}">Packing #${escapeHtml(r.line_no)} · pallet ${escapeHtml(r.pallet_no)} · ` +
          `pendiente ${numberText(r.cantidad_pendiente)} de ${numberText(r.cantidad_packing)}</option>`
        ).join("");
      }
    } catch (err) {
      if (subtitle) subtitle.textContent = "";
      setMessage("mat-invoice-pallet-link-message", `No se pudo cargar: ${err.message}`);
    }
  }

  async function confirmPalletLink() {
    const pending = state.pendingPalletLink;
    const target = el("mat-invoice-pallet-link-target");
    const note = el("mat-invoice-pallet-link-note");
    if (!pending || !target?.value) {
      setMessage("mat-invoice-pallet-link-message", "Selecciona un packing destino.");
      return;
    }
    setLoading(true);
    try {
      const data = await fetchJson(`/api/material_admin/invoices/${state.selectedInvoiceId}/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items: [{
            codigo_material_recibido: pending.codigo,
            packing_line_id: Number(target.value),
            permitir_pallet_distinto: true,
            nota_aplicacion: note?.value?.trim() || "Material recibido en pallet distinto",
          }],
        }),
      });
      const applied = Number(data.aplicados || 0);
      if (applied > 0) {
        closePalletLink();
        setMessage("mat-invoice-detail-message",
          `Lote ${pending.codigo} linkeado (llego en pallet distinto, registrado).`, "success");
        await loadDetail(state.selectedInvoiceId);
      } else {
        const motivo = (data.skipped && data.skipped[0]?.error) || "No se pudo aplicar.";
        setMessage("mat-invoice-pallet-link-message", motivo);
      }
    } catch (err) {
      setMessage("mat-invoice-pallet-link-message", `Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function syncTabs() {
    document.querySelectorAll("#mat-invoice-page .mat-invoice-tab").forEach((button) => {
      button.classList.toggle("active", button.dataset.tab === state.activeTab);
    });
    ["lines", "packing", "links"].forEach((tab) => {
      const panel = el(`mat-invoice-tab-${tab}`);
      if (panel) panel.hidden = tab !== state.activeTab;
    });
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(`script[data-src="${src}"]`);
      if (existing) {
        resolve();
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.dataset.src = src;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
      document.head.appendChild(script);
    });
  }

  // SheetJS vendored en static/js/lib con respaldo CDN (planta puede ir sin internet).
  async function ensureSheetJs() {
    if (typeof window.XLSX !== "undefined") return;
    try {
      await loadScript("/static/js/lib/xlsx.full.min.js");
    } catch (err) {
      await loadScript("https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js");
    }
    if (typeof window.XLSX === "undefined") {
      throw new Error("La libreria de Excel no se cargo.");
    }
  }

  // Definicion de columnas por tabla: [encabezado, accessor]. El accessor
  // devuelve el valor crudo para el Excel (numeros como numero, no texto).
  function numericCell(value) {
    if (value === null || value === undefined || value === "") return "";
    const n = Number(value);
    return Number.isFinite(n) ? n : value;
  }

  const EXPORT_TABLES = {
    invoices: {
      sheet: "Invoices",
      file: () => "invoices",
      get rows() { return state.data.invoices; },
      columns: [
        ["Invoice", (r) => r.numero_invoice],
        ["Estado", (r) => r.estado],
        ["Tipo", (r) => r.tipo],
        ["Lineas", (r) => numericCell(r.total_lineas)],
        ["Packing", (r) => numericCell(r.total_packing)],
        ["Links", (r) => numericCell(r.links_activos)],
        ["Fecha", (r) => r.fecha_carga],
        ["Archivo", (r) => r.archivo_nombre || r.archivo_ruta || ""],
      ],
    },
    lines: {
      sheet: "Lineas",
      file: () => `lineas_${state.selectedInvoice?.numero_invoice || state.selectedInvoiceId}`,
      get rows() { return state.data.lines; },
      columns: [
        ["No.", (r) => numericCell(r.line_no)],
        ["Parte raw", (r) => r.raw_part_num],
        ["Parte sistema", (r) => r.numero_parte_sistema],
        ["Descripcion", (r) => r.descripcion],
        ["Cantidad", (r) => numericCell(r.cantidad)],
        ["UOM", (r) => r.uom],
        ["Costo unit.", (r) => numericCell(r.costo_unitario)],
        ["Total", (r) => numericCell(r.costo_total)],
        ["Estado", (r) => r.estado_match],
      ],
    },
    packing: {
      sheet: "Packing",
      file: () => `packing_${state.selectedInvoice?.numero_invoice || state.selectedInvoiceId}`,
      get rows() { return state.data.packing; },
      // Hoja principal: resumen, una fila por packing (sin bulto de lotes).
      columns: [
        ["No.", (r) => numericCell(r.line_no)],
        ["Pallet raw", (r) => r.pallet_no_original],
        ["Pallet", (r) => r.pallet_no],
        ["Parte sistema", (r) => r.numero_parte_sistema],
        ["Cantidad", (r) => numericCell(r.cantidad_packing)],
        ["Entradas", (r) => numericCell(r.entradas_recibidas)],
        ["Cant. entrada", (r) => numericCell(r.cantidad_recibida)],
        ["Pend. entrada", (r) => numericCell(r.cantidad_pendiente_entrada)],
        ["Aplicado", (r) => numericCell(r.cantidad_aplicada_activa)],
        ["Exceso", (r) => numericCell(r.cantidad_exceso)],
        ["KG", (r) => numericCell(r.kg)],
        ["CBM", (r) => numericCell(r.cbm)],
        ["Estado", (r) => r.estado_match],
        ["Mensaje", (r) => r.mensaje_match],
      ],
      // Hoja adicional "Detallado": una fila por lote aplicado, con el detalle
      // de pallet recibido/esperado para conservar la trazabilidad.
      extraSheets: [{
        name: "Detallado",
        rows: () => state.data.packing.flatMap((p) =>
          (Array.isArray(p.lotes) ? p.lotes : []).map((l) => ({ packing: p, lote: l }))
        ),
        columns: [
          ["No. packing", (x) => numericCell(x.packing.line_no)],
          ["Pallet packing", (x) => x.packing.pallet_no],
          ["Parte sistema", (x) => x.packing.numero_parte_sistema],
          ["Cantidad packing", (x) => numericCell(x.packing.cantidad_packing)],
          ["Lote aplicado", (x) => x.lote.codigo_material_recibido],
          ["Cant. lote", (x) => numericCell(x.lote.cantidad_aplicada)],
          ["Pallet recibido", (x) => x.lote.pallet_recibido],
          ["Pallet esperado", (x) => x.lote.pallet_esperado],
          ["Nota pallet", (x) => x.lote.nota_aplicacion],
        ],
      }],
    },
    links: {
      sheet: "Links",
      file: () => `links_${state.selectedInvoice?.numero_invoice || state.selectedInvoiceId}`,
      get rows() { return state.data.links; },
      columns: [
        ["ID", (r) => numericCell(r.id)],
        ["Codigo recibido", (r) => r.codigo_material_recibido],
        ["Parte", (r) => r.numero_parte_sistema],
        ["Cantidad", (r) => numericCell(r.cantidad_aplicada)],
        ["Costo", (r) => numericCell(r.costo_unitario)],
        ["Moneda", (r) => r.moneda],
        ["Pallet recibido", (r) => r.pallet_recibido],
        ["Pallet esperado", (r) => r.pallet_esperado],
        ["Nota pallet", (r) => r.nota_aplicacion],
        ["Estado", (r) => r.estado],
        ["Aplicado por", (r) => r.usuario_aplicacion],
        ["Fecha aplicacion", (r) => r.fecha_aplicacion],
        ["Desaplicado por", (r) => r.usuario_desaplicado],
      ],
    },
  };

  // Limpia un nombre para usarlo como archivo (sin caracteres invalidos).
  function safeFileName(value) {
    return String(value || "export").replace(/[\\/:*?"<>|]+/g, "_").slice(0, 100);
  }

  async function exportTable(key) {
    const def = EXPORT_TABLES[key];
    if (!def) return;
    const rows = def.rows || [];
    if (!rows.length) {
      setMessage("mat-invoice-detail-message", "No hay datos para exportar.");
      return;
    }
    setLoading(true);
    try {
      await ensureSheetJs();
      // Convierte (columns, rows) en una matriz [encabezados, ...filas].
      const toAoa = (columns, dataRows) => {
        const aoa = [columns.map(([title]) => title)];
        (dataRows || []).forEach((row) => {
          aoa.push(columns.map(([, accessor]) => {
            const value = accessor(row);
            return value === null || value === undefined ? "" : value;
          }));
        });
        return aoa;
      };
      const wb = window.XLSX.utils.book_new();
      // Hoja principal (resumen).
      window.XLSX.utils.book_append_sheet(
        wb, window.XLSX.utils.aoa_to_sheet(toAoa(def.columns, rows)), def.sheet
      );
      // Hojas adicionales (p.ej. "Detallado") para no recargar la principal.
      (def.extraSheets || []).forEach((extra) => {
        const extraRows = typeof extra.rows === "function" ? extra.rows() : (extra.rows || []);
        window.XLSX.utils.book_append_sheet(
          wb, window.XLSX.utils.aoa_to_sheet(toAoa(extra.columns, extraRows)), extra.name
        );
      });
      const fecha = new Date().toISOString().slice(0, 10);
      window.XLSX.writeFile(wb, `${safeFileName(def.file())}_${fecha}.xlsx`);
    } catch (err) {
      setMessage("mat-invoice-detail-message", `No se pudo exportar: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function closeViewer() {
    hideModal("mat-invoice-viewer");
    state.viewerWorkbook = null;
    state.viewerSheet = null;
  }

  function renderViewerSheet(sheetName) {
    const body = el("mat-invoice-viewer-body");
    const wb = state.viewerWorkbook;
    if (!body || !wb) return;
    const sheet = wb.Sheets[sheetName];
    if (!sheet) {
      body.innerHTML = "";
      return;
    }
    // SheetJS genera la tabla HTML respetando merges y valores.
    body.innerHTML = window.XLSX.utils.sheet_to_html(sheet, { id: "mat-invoice-xlsx-table" });
  }

  // Punto unico para cambiar de hoja: sincroniza pestanas, select y cuerpo.
  function selectViewerSheet(sheetName) {
    if (!sheetName) return;
    state.viewerSheet = sheetName;
    const sheetsSelect = el("mat-invoice-viewer-sheets");
    if (sheetsSelect && sheetsSelect.value !== sheetName) {
      sheetsSelect.value = sheetName;
    }
    const tabs = el("mat-invoice-viewer-tabs");
    if (tabs) {
      tabs.querySelectorAll("[data-sheet-name]").forEach((btn) => {
        btn.classList.toggle("active", btn.getAttribute("data-sheet-name") === sheetName);
      });
    }
    const body = el("mat-invoice-viewer-body");
    if (body) body.scrollTop = 0;
    renderViewerSheet(sheetName);
  }

  function renderViewerTabs(names) {
    const tabs = el("mat-invoice-viewer-tabs");
    if (!tabs) return;
    tabs.innerHTML = names
      .map(
        (name) =>
          `<button type="button" class="mat-invoice-viewer-tab" data-sheet-name="${escapeHtml(name)}" title="${escapeHtml(name)}">${escapeHtml(name)}</button>`
      )
      .join("");
  }

  async function openExcelViewer(invoiceId, numeroInvoice) {
    const viewer = openModal("mat-invoice-viewer");
    if (!viewer) return;
    setMessage("mat-invoice-viewer-message", "", "");
    el("mat-invoice-viewer-message").hidden = true;
    const title = el("mat-invoice-viewer-title");
    const subtitle = el("mat-invoice-viewer-subtitle");
    const sheetsSelect = el("mat-invoice-viewer-sheets");
    const tabsEl = el("mat-invoice-viewer-tabs");
    const bodyEl = el("mat-invoice-viewer-body");
    if (title) title.textContent = `Excel: ${numeroInvoice || invoiceId}`;
    if (subtitle) subtitle.textContent = "Cargando...";
    if (bodyEl) bodyEl.innerHTML = "";
    if (sheetsSelect) sheetsSelect.innerHTML = "";
    if (tabsEl) tabsEl.innerHTML = "";
    state.viewerInvoiceId = invoiceId;

    try {
      await ensureSheetJs();
      const res = await fetch(`/api/material_admin/invoices/${encodeURIComponent(invoiceId)}/file`, {
        credentials: "same-origin",
      });
      if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try {
          const data = await res.json();
          msg = data.error || msg;
        } catch (_) {}
        throw new Error(msg);
      }
      const buffer = await res.arrayBuffer();
      const wb = window.XLSX.read(buffer, { type: "array" });
      state.viewerWorkbook = wb;
      const names = wb.SheetNames || [];
      if (sheetsSelect) {
        sheetsSelect.innerHTML = names
          .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
          .join("");
      }
      renderViewerTabs(names);
      if (subtitle) subtitle.textContent = `${names.length} hoja(s)`;
      // Abre por defecto en INVOICE(CONVERTED) si existe.
      const preferida = names.find((n) => n.toUpperCase().replace(/\s+/g, "") === "INVOICE(CONVERTED)");
      const inicial = preferida || names[0];
      if (inicial) {
        selectViewerSheet(inicial);
      }
    } catch (err) {
      if (subtitle) subtitle.textContent = "";
      setMessage("mat-invoice-viewer-message", `No se pudo abrir el Excel: ${err.message}`);
    }
  }

  function attachListeners() {
    if (document.body.dataset.materialInvoicesListenersAttached) return;

    document.body.addEventListener("submit", (event) => {
      if (event.target?.id === "mat-invoice-upload-form") {
        openPreview(event);
      }
    });

    document.body.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;

      if (target.closest("#mat-invoice-preview-confirm")) {
        event.preventDefault();
        confirmUpload();
        return;
      }
      if (target.closest("[data-preview-close]")) {
        event.preventDefault();
        closePreview();
        return;
      }
      const linkPalletBtn = target.closest(".mat-invoice-link-pallet");
      if (linkPalletBtn) {
        event.preventDefault();
        openPalletLink(
          linkPalletBtn.getAttribute("data-lote"),
          linkPalletBtn.getAttribute("data-pallet"),
          linkPalletBtn.getAttribute("data-parte")
        );
        return;
      }
      if (target.closest("#mat-invoice-pallet-link-confirm")) {
        event.preventDefault();
        confirmPalletLink();
        return;
      }
      if (target.closest("[data-pallet-link-close]")) {
        event.preventDefault();
        closePalletLink();
        return;
      }
      const editLineBtn = target.closest("[data-edit-line-id]");
      if (editLineBtn) {
        event.preventDefault();
        openLineEdit(editLineBtn.getAttribute("data-edit-line-id"));
        return;
      }
      if (target.closest("#mat-invoice-line-edit-confirm")) {
        event.preventDefault();
        saveLineEdit();
        return;
      }
      if (target.closest("[data-line-edit-close]")) {
        event.preventDefault();
        closeLineEdit();
        return;
      }
      const deleteBtn = target.closest("[data-delete-invoice-id]");
      if (deleteBtn) {
        event.preventDefault();
        event.stopPropagation();
        deleteInvoice(
          deleteBtn.getAttribute("data-delete-invoice-id"),
          deleteBtn.getAttribute("data-delete-invoice-name")
        );
        return;
      }

      const viewExcel = target.closest("[data-view-excel-id]");
      if (viewExcel) {
        event.preventDefault();
        openExcelViewer(
          viewExcel.getAttribute("data-view-excel-id"),
          viewExcel.getAttribute("data-view-excel-name")
        );
        return;
      }
      if (target.closest("[data-viewer-close]")) {
        event.preventDefault();
        closeViewer();
        return;
      }
      const sheetTab = target.closest("[data-sheet-name]");
      if (sheetTab) {
        event.preventDefault();
        selectViewerSheet(sheetTab.getAttribute("data-sheet-name"));
        return;
      }
      if (target.closest("#mat-invoice-viewer-download")) {
        event.preventDefault();
        if (state.viewerInvoiceId) {
          window.location.href = `/api/material_admin/invoices/${encodeURIComponent(state.viewerInvoiceId)}/file?download=1`;
        }
        return;
      }

      const row = target.closest("#mat-invoice-list-body tr[data-invoice-id]");
      if (row) {
        event.preventDefault();
        loadDetail(row.dataset.invoiceId);
        return;
      }
      if (target.closest("#mat-invoice-refresh") || target.closest("#mat-invoice-search-btn")) {
        event.preventDefault();
        loadInvoices();
        return;
      }
      if (target.closest("#mat-invoice-clear-filters")) {
        event.preventDefault();
        clearFilters();
        return;
      }
      const exportBtn = target.closest("[data-export]");
      if (exportBtn) {
        event.preventDefault();
        exportTable(exportBtn.getAttribute("data-export"));
        return;
      }
      if (target.closest("#mat-invoice-apply-auto")) {
        event.preventDefault();
        postAction("apply", {});
        return;
      }
      if (target.closest("#mat-invoice-reapply")) {
        event.preventDefault();
        postAction("reapply", { motivo: "Reaplicacion desde modulo web" });
        return;
      }
      if (target.closest("#mat-invoice-unapply")) {
        event.preventDefault();
        const motivo = window.prompt("Motivo de desaplicacion") || "";
        postAction("unapply", { motivo_desaplicado: motivo });
        return;
      }
      const closeBtn = target.closest("#mat-invoice-close");
      if (closeBtn) {
        event.preventDefault();
        const cerrar = closeBtn.dataset.cerrado !== "1"; // toggle
        postAction("close", { cerrado: cerrar });
        return;
      }
      const loteToggle = target.closest("[data-toggle-lotes]");
      if (loteToggle) {
        event.preventDefault();
        const parentId = loteToggle.getAttribute("data-toggle-lotes");
        const subRows = document.querySelectorAll(`#mat-invoice-packing-body [data-lotes-of="${CSS.escape(parentId)}"]`);
        const expandir = loteToggle.getAttribute("aria-expanded") !== "true";
        subRows.forEach((tr) => { tr.hidden = !expandir; });
        loteToggle.setAttribute("aria-expanded", expandir ? "true" : "false");
        loteToggle.textContent = expandir ? "▼" : "▶";
        return;
      }
      const tabButton = target.closest("#mat-invoice-page .mat-invoice-tab");
      if (tabButton?.dataset.tab) {
        event.preventDefault();
        state.activeTab = tabButton.dataset.tab;
        syncTabs();
      }
    });

    document.body.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.id === "mat-invoice-state"
          || target.id === "mat-invoice-date-from"
          || target.id === "mat-invoice-date-to") {
        loadInvoices();
      }
      if (target.id === "mat-invoice-viewer-sheets") {
        selectViewerSheet(target.value);
      }
    });

    document.body.addEventListener("keydown", (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.id === "mat-invoice-search" && event.key === "Enter") {
        event.preventDefault();
        loadInvoices();
      }
      if (target.closest("#mat-invoice-line-edit") && event.key === "Enter") {
        event.preventDefault();
        saveLineEdit();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (!el("mat-invoice-line-edit")?.hidden) {
        closeLineEdit();
      } else if (!el("mat-invoice-pallet-link")?.hidden) {
        closePalletLink();
      } else if (!el("mat-invoice-preview")?.hidden) {
        closePreview();
      } else if (!el("mat-invoice-viewer")?.hidden) {
        closeViewer();
      }
    });

    document.body.dataset.materialInvoicesListenersAttached = "1";
  }

  window.initMaterialInvoices = function () {
    ensureModuleStyles();
    attachListeners();
    state.selectedInvoiceId = null;
    state.selectedInvoice = null;
    state.activeTab = "lines";
    state.viewerInvoiceId = null;
    state.viewerWorkbook = null;
    state.pendingUpload = null;
    state.pendingPalletLink = null;
    state.pendingLineEdit = null;
    hideModal("mat-invoice-viewer");
    hideModal("mat-invoice-preview");
    hideModal("mat-invoice-pallet-link");
    hideModal("mat-invoice-line-edit");
    if (el("mat-invoice-detail")) el("mat-invoice-detail").hidden = true;
    // Arrancar mostrando los pendientes (de cualquier fecha), no solo los de hoy.
    if (el("mat-invoice-state")) el("mat-invoice-state").value = "PENDIENTES";
    loadInvoices();
  };
})();
