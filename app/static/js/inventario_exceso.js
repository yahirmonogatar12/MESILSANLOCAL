(function () {
  // Inventario Exceso QA.
  // WF_002: JS propio con IDs prefijados inventario-exceso-*.
  // WF_003: integra API JSON/Excel del blueprint control_resultados.inventario_exceso.
  // WF_004: garantiza CSS persistente/cache-busted aunque el template se cargue por AJAX.
  const ASSET_VERSION = "20260601e";
  const STYLESHEET_ID = "inventario-exceso-css";
  const STYLESHEET_HREF = `/static/css/inventario_exceso.css?v=${ASSET_VERSION}`;

  const state = {
    batchId: null,
    valid: false,
    history: [],
  };

  function ensureStylesheet() {
    if (document.getElementById(STYLESHEET_ID)) return;
    const link = document.createElement("link");
    link.id = STYLESHEET_ID;
    link.rel = "stylesheet";
    link.href = STYLESHEET_HREF;
    document.head.appendChild(link);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatNumber(value) {
    const number = Number(value || 0);
    return number.toLocaleString("es-MX");
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, {
      credentials: "same-origin",
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === false) {
      throw new Error(payload.error || payload.message || "No fue posible completar la solicitud.");
    }
    return payload;
  }

  function getElements() {
    return {
      root: document.getElementById("inventario-exceso-module"),
      search: document.getElementById("inventario-exceso-search"),
      searchBtn: document.getElementById("inventario-exceso-search-btn"),
      clearBtn: document.getElementById("inventario-exceso-clear-btn"),
      exportBtn: document.getElementById("inventario-exceso-export-btn"),
      status: document.getElementById("inventario-exceso-status"),
      count: document.getElementById("inventario-exceso-count"),
      tbody: document.getElementById("inventario-exceso-tbody"),
      openClosureBtn: document.getElementById("inventario-exceso-open-closure-btn"),
      backClosureBtn: document.getElementById("inventario-exceso-closure-back-btn"),
      closureStatus: document.getElementById("inventario-exceso-closure-status"),
      closureDate: document.getElementById("inventario-exceso-closure-date"),
      closureUser: document.getElementById("inventario-exceso-closure-user"),
      closureMonth: document.getElementById("inventario-exceso-closure-month"),
      closureFile: document.getElementById("inventario-exceso-closure-file"),
      templateBtn: document.getElementById("inventario-exceso-closure-template-btn"),
      resetBtn: document.getElementById("inventario-exceso-closure-reset-btn"),
      previewBtn: document.getElementById("inventario-exceso-closure-preview-btn"),
      confirmBtn: document.getElementById("inventario-exceso-closure-confirm-btn"),
      errors: document.getElementById("inventario-exceso-closure-errors"),
      donut: document.getElementById("inventario-exceso-closure-donut"),
      accuracy: document.getElementById("inventario-exceso-closure-accuracy"),
      previewCount: document.getElementById("inventario-exceso-closure-preview-count"),
      previewTbody: document.getElementById("inventario-exceso-closure-preview-tbody"),
      historyCount: document.getElementById("inventario-exceso-closure-history-count"),
      historyTbody: document.getElementById("inventario-exceso-closure-history-tbody"),
    };
  }

  function setStatus(text, isError) {
    const { status } = getElements();
    if (!status) return;
    status.textContent = text || "";
    status.classList.toggle("is-error", Boolean(isError));
  }

  function setClosureStatus(text, isError) {
    const { closureStatus } = getElements();
    if (!closureStatus) return;
    closureStatus.textContent = text || "";
    closureStatus.classList.toggle("is-error", Boolean(isError));
  }

  function renderErrors(errors) {
    const { errors: wrap } = getElements();
    if (!wrap) return;
    const items = errors || [];
    wrap.innerHTML = items.length
      ? items.map((error) => `<span class="ae-closure-error-chip">${escapeHtml(error)}</span>`).join("")
      : "";
  }

  function badge(text, variant) {
    return `<span class="history-badge history-badge--${variant || "neutral"}">${escapeHtml(text)}</span>`;
  }

  function renderInventoryRows(rows) {
    if (!rows.length) {
      return `<tr><td colspan="7" class="ae-empty-cell">Sin partes con movimiento.</td></tr>`;
    }
    return rows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.part_number)}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${escapeHtml(row.customer || "-")}</td>
            <td>${formatNumber(row.initial_quantity)}</td>
            <td>${formatNumber(row.entries_qty)}</td>
            <td>${formatNumber(row.exits_qty)}</td>
            <td>${formatNumber(row.current_quantity)}</td>
          </tr>
        `,
      )
      .join("");
  }

  async function loadInventory() {
    const { search, tbody, count } = getElements();
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" class="ae-empty-cell">Cargando inventario...</td></tr>`;
    setStatus("Consultando inventario...");
    try {
      const params = new URLSearchParams();
      if (search?.value.trim()) params.set("q", search.value.trim());
      const payload = await fetchJson(`/api/inventario_exceso/inventory?${params.toString()}`);
      tbody.innerHTML = renderInventoryRows(payload.items || []);
      if (count) {
        count.textContent = `${formatNumber(payload.totalQuantity)} piezas / ${formatNumber(payload.totalParts)} partes`;
      }
      setStatus("Inventario actualizado.");
    } catch (error) {
      tbody.innerHTML = `<tr><td colspan="7" class="ae-empty-cell">${escapeHtml(error.message)}</td></tr>`;
      setStatus(error.message, true);
    }
  }

  function applyMetadata(metadata) {
    const { closureDate, closureUser, closureMonth } = getElements();
    if (closureDate) closureDate.value = metadata?.closureDateTime || metadata?.closureDate || "";
    if (closureUser) closureUser.value = metadata?.closureUser || "";
    if (closureMonth) closureMonth.value = metadata?.closureMonthLabel || metadata?.closureMonth || "";
  }

  function renderPreviewRows(rows) {
    if (!rows.length) {
      return `<tr><td colspan="7" class="ae-empty-cell">Sin datos de preview.</td></tr>`;
    }
    return rows
      .map((row) => {
        const statusVariant = row.status === "igual" ? "success" : row.status === "pendiente" ? "warning" : "danger";
        return `
          <tr>
            <td>${escapeHtml(row.part_number || "-")}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${escapeHtml(row.customer || "-")}</td>
            <td>${formatNumber(row.system_quantity)}</td>
            <td>${row.physical_quantity === null || row.physical_quantity === undefined ? "-" : formatNumber(row.physical_quantity)}</td>
            <td>${row.difference_quantity === null || row.difference_quantity === undefined ? "-" : formatNumber(row.difference_quantity)}</td>
            <td>${badge(row.status || "-", statusVariant)}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderPreview(preview, payload) {
    const { previewTbody, previewCount, accuracy, donut, confirmBtn } = getElements();
    const rows = preview?.rows || [];
    const summary = preview?.summary || {};

    if (previewTbody) previewTbody.innerHTML = renderPreviewRows(rows);
    if (previewCount) previewCount.textContent = `${rows.length} ${rows.length === 1 ? "registro" : "registros"}`;
    if (accuracy) accuracy.textContent = `${Number(summary.accuracyPct || 0).toFixed(2)}%`;
    if (donut) {
      const pct = Math.max(0, Math.min(100, Number(summary.accuracyPct || 0)));
      const degrees = (pct / 100) * 360;
      donut.style.background = `conic-gradient(#27ae60 0deg, #27ae60 ${degrees}deg, rgba(255,255,255,0.08) ${degrees}deg)`;
    }

    state.batchId = payload?.batchId || state.batchId;
    state.valid = Boolean(payload?.valid && state.batchId);
    if (confirmBtn) confirmBtn.disabled = !state.valid;
  }

  function renderHistoryRows(rows) {
    if (!rows.length) {
      return `<tr><td colspan="7" class="ae-empty-cell">Sin cierres registrados.</td></tr>`;
    }
    return rows
      .map((row) => {
        const accuracy = row.summary?.accuracyPct;
        return `
          <tr>
            <td>${escapeHtml(row.closure_label || "-")}</td>
            <td>${escapeHtml(row.closure_month || "-")}</td>
            <td>${escapeHtml(row.confirmed_at || row.closed_at || row.created_at || "-")}</td>
            <td>${escapeHtml(row.confirmed_by || row.created_by || "-")}</td>
            <td>${accuracy === undefined ? "-" : `${Number(accuracy).toFixed(2)}%`}</td>
            <td>${badge(row.status || "-", row.status === "confirmed" ? "success" : "warning")}</td>
            <td>
              <button class="ae-btn-inline ae-btn-inline-save" type="button" data-action="view-closure" data-batch-id="${escapeHtml(row.id)}">Ver</button>
              <button class="ae-btn-inline ae-btn-inline-secondary" type="button" data-action="export-closure" data-batch-id="${escapeHtml(row.id)}" ${row.status !== "confirmed" ? "disabled" : ""}>CSV</button>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function renderHistory(rows) {
    const { historyTbody, historyCount } = getElements();
    state.history = rows || [];
    if (historyTbody) historyTbody.innerHTML = renderHistoryRows(state.history);
    if (historyCount) {
      historyCount.textContent = `${state.history.length} ${state.history.length === 1 ? "registro" : "registros"}`;
    }
  }

  async function openClosure() {
    const { root, previewTbody } = getElements();
    root?.classList.add("is-closure-active");
    if (previewTbody) {
      previewTbody.innerHTML = `<tr><td colspan="7" class="ae-empty-cell">Cargando baseline del cierre...</td></tr>`;
    }
    renderErrors([]);
    setClosureStatus("Cargando contexto del cierre...");
    try {
      const payload = await fetchJson("/api/inventario_exceso/cierre/bootstrap");
      applyMetadata(payload.metadata);
      renderPreview(payload.preview, payload);
      renderHistory(payload.history || []);
      setClosureStatus("Carga el CSV fisico para validar el cierre.");
    } catch (error) {
      setClosureStatus(error.message, true);
      renderErrors([error.message]);
    }
  }

  function closeClosure() {
    const { root } = getElements();
    root?.classList.remove("is-closure-active");
  }

  async function previewClosure() {
    const { closureFile, previewBtn } = getElements();
    const file = closureFile?.files?.[0];
    if (!file) {
      setClosureStatus("Selecciona el CSV de inventario fisico.", true);
      return;
    }
    const formData = new FormData();
    formData.append("closure_file", file);
    previewBtn.disabled = true;
    previewBtn.textContent = "Validando...";
    setClosureStatus("Validando CSV...");
    renderErrors([]);
    try {
      const payload = await fetchJson("/api/inventario_exceso/cierre/preview", {
        method: "POST",
        body: formData,
      });
      renderPreview(payload.preview, payload);
      renderHistory(payload.history || []);
      renderErrors(payload.errors || []);
      setClosureStatus(
        payload.valid ? "Preview validado. Ya puedes confirmar el cierre." : "El CSV contiene errores.",
        !payload.valid,
      );
    } catch (error) {
      setClosureStatus(error.message, true);
      renderErrors([error.message]);
    } finally {
      previewBtn.disabled = false;
      previewBtn.textContent = "Validar preview";
    }
  }

  async function confirmClosure() {
    const { confirmBtn } = getElements();
    if (!state.valid || !state.batchId) {
      setClosureStatus("No hay un preview valido para confirmar.", true);
      return;
    }
    confirmBtn.disabled = true;
    confirmBtn.textContent = "Confirmando...";
    setClosureStatus("Confirmando cierre...");
    try {
      const payload = await fetchJson("/api/inventario_exceso/cierre/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batchId: state.batchId }),
      });
      state.batchId = null;
      state.valid = false;
      renderHistory(payload.history || []);
      setClosureStatus(payload.message || "Cierre confirmado.");
      await loadInventory();
    } catch (error) {
      setClosureStatus(error.message, true);
      confirmBtn.disabled = false;
    } finally {
      confirmBtn.textContent = "Confirmar cierre";
    }
  }

  async function viewClosure(batchId) {
    setClosureStatus("Consultando detalle del cierre...");
    try {
      const payload = await fetchJson(`/api/inventario_exceso/cierre/history/${encodeURIComponent(batchId)}`);
      const batch = payload.batch || {};
      const innerPayload = payload.payload || {};
      applyMetadata({
        ...(innerPayload.metadata || {}),
        closureDateTime: batch.closed_at || batch.created_at || innerPayload.metadata?.closureDateTime,
        closureUser: batch.confirmed_by || batch.created_by || innerPayload.metadata?.closureUser,
      });
      state.batchId = batch.status === "pending" ? batch.id : null;
      renderPreview(innerPayload.preview || { rows: [], summary: {} }, {
        batchId: state.batchId,
        valid: batch.status === "pending",
      });
      setClosureStatus(batch.status === "pending" ? "Preview pendiente retomado." : "Cierre consultado.");
    } catch (error) {
      setClosureStatus(error.message, true);
      renderErrors([error.message]);
    }
  }

  function resetClosure() {
    const { closureFile, confirmBtn } = getElements();
    if (closureFile) closureFile.value = "";
    state.batchId = null;
    state.valid = false;
    if (confirmBtn) confirmBtn.disabled = true;
    openClosure();
  }

  function initInventarioExceso() {
    ensureStylesheet();
    const elements = getElements();
    if (!elements.root || elements.root.dataset.initialized === "true") return;
    elements.root.dataset.initialized = "true";

    elements.searchBtn?.addEventListener("click", () => {
      loadInventory();
    });
    elements.search?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        loadInventory();
      }
    });
    elements.clearBtn?.addEventListener("click", () => {
      if (elements.search) elements.search.value = "";
      loadInventory();
    });
    elements.exportBtn?.addEventListener("click", () => {
      const params = new URLSearchParams();
      if (elements.search?.value.trim()) params.set("search", elements.search.value.trim());
      const suffix = params.toString() ? `?${params.toString()}` : "";
      window.open(`/api/inventario_exceso/inventory/export${suffix}`, "_blank");
    });
    elements.openClosureBtn?.addEventListener("click", openClosure);
    elements.backClosureBtn?.addEventListener("click", closeClosure);
    elements.templateBtn?.addEventListener("click", () => {
      window.open("/api/inventario_exceso/cierre/template", "_blank");
    });
    elements.resetBtn?.addEventListener("click", resetClosure);
    elements.previewBtn?.addEventListener("click", previewClosure);
    elements.confirmBtn?.addEventListener("click", confirmClosure);
    elements.historyTbody?.addEventListener("click", (event) => {
      const actionButton = event.target.closest("[data-action]");
      if (!actionButton) return;
      const batchId = actionButton.dataset.batchId;
      if (actionButton.dataset.action === "view-closure") {
        viewClosure(batchId);
      }
      if (actionButton.dataset.action === "export-closure") {
        window.open(`/api/inventario_exceso/cierre/history/${encodeURIComponent(batchId)}/export`, "_blank");
      }
    });

    loadInventory();
  }

  window.initInventarioExceso = initInventarioExceso;
  initInventarioExceso();
})();
