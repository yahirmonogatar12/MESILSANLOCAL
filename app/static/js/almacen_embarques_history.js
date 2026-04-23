(function () {
  const STYLESHEET_ID = "almacen-embarques-history-css";
  const STYLESHEET_HREF = "/static/css/almacen_embarques_history.css?v=20260422g";

  function ensureModuleStyles() {
    const currentLink = document.getElementById(STYLESHEET_ID);
    if (currentLink) {
      if (!currentLink.getAttribute("href")?.includes("20260422g")) {
        currentLink.setAttribute("href", STYLESHEET_HREF);
      }
      return;
    }

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
      .replace(/'/g, "&#39;");
  }

  function formatNumber(value) {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    const numericValue = Number(value);
    if (Number.isNaN(numericValue)) {
      return escapeHtml(value);
    }

    return Number.isInteger(numericValue)
      ? numericValue.toLocaleString("es-MX")
      : numericValue.toLocaleString("es-MX", {
          minimumFractionDigits: 0,
          maximumFractionDigits: 2,
        });
  }

  function buildBadge(text, variant) {
    return `<span class="history-badge history-badge--${variant}">${escapeHtml(text)}</span>`;
  }

  function getNormalizedReturnType(rawValue) {
    const value = String(rawValue || "").trim();
    if (!value) {
      return "Sin tipo";
    }
    if (/os\s*&\s*d/i.test(value)) {
      return "OS&D";
    }
    if (/exceso/i.test(value)) {
      return "Exceso";
    }
    return value;
  }

  function buildDepartureCell(row) {
    if (row.departure_code) {
      const metaParts = [];
      if (row.departure_assigned_by) {
        metaParts.push(escapeHtml(row.departure_assigned_by));
      }
      if (row.departure_assigned_at) {
        metaParts.push(escapeHtml(row.departure_assigned_at));
      }
      const meta = metaParts.length
        ? `<span class="ae-departure-meta">${metaParts.join(" · ")}</span>`
        : "";

      return `
        <div class="ae-departure-view">
          <span class="ae-departure-badge">${escapeHtml(row.departure_code)}</span>
          ${meta}
        </div>
      `;
    }

    return `
      <div class="ae-departure-editor" data-exit-id="${escapeHtml(row.id)}">
        <input
          type="text"
          class="ae-departure-input"
          data-exit-id="${escapeHtml(row.id)}"
          data-folio="${escapeHtml(row.folio || "")}"
          data-part-number="${escapeHtml(row.part_number || "")}"
          data-total-quantity="${escapeHtml(row.cantidad || 0)}"
          placeholder="Asignar departure"
          maxlength="120"
        >
      </div>
    `;
  }

  let departureModalState = {
    config: null,
    sourceInput: null,
  };

  function getDepartureModal() {
    let modal = document.getElementById("ae-departure-modal");
    if (modal) {
      return modal;
    }

    modal = document.createElement("div");
    modal.id = "ae-departure-modal";
    modal.className = "ae-departure-modal";
    modal.innerHTML = `
      <div class="ae-departure-modal__backdrop" data-action="cancel"></div>
      <div class="ae-departure-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="ae-departure-modal-title">
        <div class="ae-departure-modal__header">
          <h4 id="ae-departure-modal-title">Confirmar departure</h4>
          <button type="button" class="ae-departure-modal__close" data-action="cancel" aria-label="Cerrar">
            &times;
          </button>
        </div>
        <div class="ae-departure-modal__body">
          <div class="ae-departure-modal__summary">
            <div class="ae-departure-modal__summary-row">
              <span>Departure</span>
              <strong data-role="departure-value"></strong>
            </div>
            <div class="ae-departure-modal__summary-row">
              <span>No. parte</span>
              <strong data-role="part-value"></strong>
            </div>
          </div>
          <div class="ae-departure-modal__field">
            <label for="ae-departure-modal-quantity">Cantidad para el departure</label>
            <input
              type="text"
              id="ae-departure-modal-quantity"
              class="ae-departure-modal__qty-input"
              inputmode="numeric"
              autocomplete="off"
              spellcheck="false"
            >
            <small class="ae-departure-modal__hint" data-role="quantity-hint"></small>
            <div class="ae-departure-modal__error" data-role="modal-error"></div>
          </div>
        </div>
        <div class="ae-departure-modal__actions">
          <button type="button" class="ae-btn-secondary" data-action="cancel">Cancelar</button>
          <button type="button" class="ae-btn-primary" data-action="save">Guardar</button>
        </div>
      </div>
    `;

    modal.addEventListener("click", (event) => {
      const actionElement = event.target.closest("[data-action]");
      if (!actionElement) {
        return;
      }

      const action = actionElement.dataset.action;
      if (action === "cancel") {
        closeDepartureModal({ restoreFocus: true });
        return;
      }

      if (action === "save") {
        submitDepartureModal();
      }
    });

    modal.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDepartureModal({ restoreFocus: true });
        return;
      }

      if (event.key === "Enter" && event.target.closest(".ae-departure-modal__dialog")) {
        event.preventDefault();
        submitDepartureModal();
      }
    });

    const quantityInput = modal.querySelector("#ae-departure-modal-quantity");
    quantityInput?.addEventListener("input", () => {
      quantityInput.value = quantityInput.value.replace(/\D+/g, "");
    });
    quantityInput?.addEventListener("keydown", (event) => {
      const allowedKeys = new Set([
        "Backspace",
        "Delete",
        "ArrowLeft",
        "ArrowRight",
        "ArrowUp",
        "ArrowDown",
        "Home",
        "End",
        "Tab",
        "Enter",
      ]);
      if (event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }
      if (allowedKeys.has(event.key)) {
        return;
      }
      if (!/^\d$/.test(event.key)) {
        event.preventDefault();
      }
    });

    document.body.appendChild(modal);
    return modal;
  }

  function setDepartureModalError(message = "") {
    const modal = getDepartureModal();
    const errorLabel = modal.querySelector('[data-role="modal-error"]');
    if (errorLabel) {
      errorLabel.textContent = message;
    }
  }

  function openDepartureModal(config, input) {
    const departureValue = input?.value?.trim() || "";
    if (!departureValue) {
      return;
    }

    const modal = getDepartureModal();
    const totalQuantity = Number(input?.dataset.totalQuantity || 0) || 0;
    departureModalState = {
      config,
      sourceInput: input,
    };

    modal.dataset.exitId = input?.dataset.exitId || "";
    modal.dataset.departureCode = departureValue;
    modal.dataset.totalQuantity = String(totalQuantity);

    const departureLabel = modal.querySelector('[data-role="departure-value"]');
    const partLabel = modal.querySelector('[data-role="part-value"]');
    const hintLabel = modal.querySelector('[data-role="quantity-hint"]');
    const quantityInput = modal.querySelector("#ae-departure-modal-quantity");

    if (departureLabel) {
      departureLabel.textContent = departureValue;
    }
    if (partLabel) {
      partLabel.textContent = input?.dataset.partNumber || "-";
    }
    if (hintLabel) {
      hintLabel.textContent = `Cantidad disponible en el registro: ${formatNumber(totalQuantity)}`;
    }
    if (quantityInput) {
      quantityInput.value = totalQuantity > 0 ? String(totalQuantity) : "";
      quantityInput.min = "1";
      quantityInput.max = totalQuantity > 0 ? String(totalQuantity) : "";
    }

    setDepartureModalError("");
    modal.classList.add("is-open");
    requestAnimationFrame(() => {
      quantityInput?.focus();
      quantityInput?.select();
    });
  }

  function closeDepartureModal({ restoreFocus = false } = {}) {
    const modal = document.getElementById("ae-departure-modal");
    if (!modal) {
      return;
    }

    modal.classList.remove("is-open");
    setDepartureModalError("");

    const sourceInput = departureModalState?.sourceInput;
    departureModalState = {
      config: null,
      sourceInput: null,
    };

    if (restoreFocus && sourceInput && document.body.contains(sourceInput)) {
      requestAnimationFrame(() => {
        sourceInput.focus();
        sourceInput.select?.();
      });
    }
  }

  function syncScrollableHeight(moduleRoot) {
    const bodyWraps = moduleRoot?.querySelectorAll(".ae-table-body-wrap");
    if (!bodyWraps?.length) {
      return;
    }

    const viewportHeight =
      window.innerHeight || document.documentElement.clientHeight || 0;
    bodyWraps.forEach((bodyWrap) => {
      const rect = bodyWrap.getBoundingClientRect();
      const bottomGap = 20;
      const availableHeight = Math.max(220, viewportHeight - rect.top - bottomGap);
      bodyWrap.style.height = `${availableHeight}px`;
      bodyWrap.style.maxHeight = `${availableHeight}px`;
    });
  }

  function syncTableWidths(moduleRoot) {
    const tableShells = moduleRoot?.querySelectorAll(".ae-table-shell");
    if (!tableShells?.length) {
      return;
    }

    tableShells.forEach((tableShell) => {
      const headerWrap = tableShell.querySelector(".ae-table-head");
      const headerTable = tableShell.querySelector(".ae-history-table--head");
      const bodyWrap = tableShell.querySelector(".ae-table-body-wrap");
      const bodyTable = tableShell.querySelector(".ae-history-table--body");
      if (!headerWrap || !headerTable || !bodyWrap || !bodyTable) {
        return;
      }

      const scrollbarWidth = Math.max(0, bodyWrap.offsetWidth - bodyWrap.clientWidth);
      const explicitWidth = getExplicitTableWidth(headerTable);
      const targetWidth = Math.max(bodyWrap.clientWidth, explicitWidth || bodyTable.scrollWidth);

      headerWrap.style.paddingRight = `${scrollbarWidth}px`;
      headerTable.style.width = `${targetWidth}px`;
      bodyTable.style.width = `${targetWidth}px`;
    });
  }

  function getExplicitTableWidth(table) {
    const cols = table?.querySelectorAll("colgroup col");
    if (!cols?.length) {
      return 0;
    }

    return Array.from(cols).reduce((total, col) => {
      const width = parseFloat(col.style.width || "0");
      return total + (Number.isFinite(width) ? width : 0);
    }, 0);
  }

  function getHeaderCellMinimumWidth(cell) {
    const headerText = String(cell?.textContent || "")
      .trim()
      .toLowerCase();

    if (headerText === "acción" || headerText === "accion") {
      return 180;
    }

    if (headerText === "departure") {
      return 120;
    }

    if (headerText.includes("ubicación") || headerText.includes("destino")) {
      return 160;
    }

    if (headerText.includes("folio")) {
      return 180;
    }

    if (headerText.includes("no. parte")) {
      return 140;
    }

    if (headerText.includes("modelo")) {
      return 140;
    }

    return 72;
  }

  function freezeShellColumnWidths(tableShell) {
    if (!tableShell || tableShell.dataset.colWidthsReady === "true") {
      return;
    }

    const headerTable = tableShell.querySelector(".ae-history-table--head");
    const bodyTable = tableShell.querySelector(".ae-history-table--body");
    const headerCells = headerTable?.querySelectorAll("thead th");
    const headerCols = headerTable?.querySelectorAll("colgroup col");
    const bodyCols = bodyTable?.querySelectorAll("colgroup col");
    if (!headerTable || !bodyTable || !headerCells?.length || !headerCols?.length || !bodyCols?.length) {
      return;
    }

    const widths = Array.from(headerCells).map((cell) =>
      Math.max(
        getHeaderCellMinimumWidth(cell),
        Math.ceil(cell.getBoundingClientRect().width),
      ),
    );

    widths.forEach((width, index) => {
      [headerCols[index], bodyCols[index]].forEach((col) => {
        if (!col) {
          return;
        }
        col.style.width = `${width}px`;
        col.style.minWidth = `${width}px`;
        col.style.maxWidth = `${width}px`;
      });
    });

    const totalWidth = widths.reduce((sum, width) => sum + width, 0);
    headerTable.style.width = `${totalWidth}px`;
    bodyTable.style.width = `${totalWidth}px`;
    tableShell.dataset.colWidthsReady = "true";
  }

  function updateShellColumnWidth(tableShell, columnIndex, nextWidth) {
    const headerTable = tableShell?.querySelector(".ae-history-table--head");
    const bodyTable = tableShell?.querySelector(".ae-history-table--body");
    const headerCols = headerTable?.querySelectorAll("colgroup col");
    const bodyCols = bodyTable?.querySelectorAll("colgroup col");
    if (!headerTable || !bodyTable || !headerCols?.[columnIndex] || !bodyCols?.[columnIndex]) {
      return;
    }

    const headerCells = headerTable?.querySelectorAll("thead th");
    const minWidth = headerCells?.[columnIndex]
      ? getHeaderCellMinimumWidth(headerCells[columnIndex])
      : 72;
    const width = Math.max(minWidth, Math.round(nextWidth));
    [headerCols[columnIndex], bodyCols[columnIndex]].forEach((col) => {
      col.style.width = `${width}px`;
      col.style.minWidth = `${width}px`;
      col.style.maxWidth = `${width}px`;
    });

    const totalWidth = getExplicitTableWidth(headerTable);
    headerTable.style.width = `${totalWidth}px`;
    bodyTable.style.width = `${totalWidth}px`;
  }

  function initResizableShells(moduleRoot) {
    const tableShells = moduleRoot?.querySelectorAll(".ae-table-shell");
    if (!tableShells?.length) {
      return;
    }

    tableShells.forEach((tableShell) => {
      freezeShellColumnWidths(tableShell);

      const headerTable = tableShell.querySelector(".ae-history-table--head");
      const headerCells = headerTable?.querySelectorAll("thead th");
      if (!headerTable || !headerCells?.length || tableShell.dataset.resizeReady === "true") {
        return;
      }

      headerCells.forEach((cell, index) => {
        if (cell.querySelector(".ae-col-resizer")) {
          return;
        }

        const handle = document.createElement("div");
        handle.className = "ae-col-resizer";
        handle.setAttribute("data-column-index", String(index));
        handle.addEventListener("mousedown", (event) => {
          event.preventDefault();
          event.stopPropagation();

          const startX = event.clientX;
          const startWidth = cell.getBoundingClientRect().width;

          document.body.classList.add("ae-col-resizing");

          const onMouseMove = (moveEvent) => {
            const deltaX = moveEvent.clientX - startX;
            updateShellColumnWidth(tableShell, index, startWidth + deltaX);
            syncTableWidths(moduleRoot);
          };

          const onMouseUp = () => {
            document.body.classList.remove("ae-col-resizing");
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("mouseup", onMouseUp);
          };

          window.addEventListener("mousemove", onMouseMove);
          window.addEventListener("mouseup", onMouseUp);
        });

        cell.appendChild(handle);
      });

      tableShell.dataset.resizeReady = "true";
    });
  }

  function getElements(prefix) {
    return {
      searchInput: document.getElementById(`${prefix}-search`),
      dateFrom: document.getElementById(`${prefix}-date-from`),
      dateTo: document.getElementById(`${prefix}-date-to`),
      searchBtn: document.getElementById(`${prefix}-search-btn`),
      clearBtn: document.getElementById(`${prefix}-clear-btn`),
      exportBtn: document.getElementById(`${prefix}-export-btn`),
      countLabel: document.getElementById(`${prefix}-count`),
      statusLabel: document.getElementById(`${prefix}-status`),
      tableBody: document.getElementById(`${prefix}-tbody`),
    };
  }

  function normalizeModuleTableColumns(moduleRoot, prefix) {
    if (!moduleRoot || moduleRoot.dataset[`normalized${prefix}`] === "true") {
      return;
    }

    const labelsToRemove =
      prefix === "almacen-embarques-exits" ? ["Destino", "Motivo"] : [];

    if (!labelsToRemove.length) {
      moduleRoot.dataset[`normalized${prefix}`] = "true";
      return;
    }

    const headTable = moduleRoot.querySelector(".ae-history-table--head");
    const bodyTable = moduleRoot.querySelector(".ae-history-table--body");
    const headerRow = headTable?.querySelector("thead tr");
    if (!headTable || !bodyTable || !headerRow) {
      return;
    }

    const indexesToRemove = Array.from(headerRow.children)
      .map((cell, index) => ({
        index,
        label: String(cell.textContent || "").trim(),
      }))
      .filter(({ label }) => labelsToRemove.includes(label))
      .map(({ index }) => index)
      .sort((a, b) => b - a);

    if (!indexesToRemove.length) {
      moduleRoot.dataset[`normalized${prefix}`] = "true";
      return;
    }

    [headTable, bodyTable].forEach((table) => {
      table.querySelectorAll("colgroup").forEach((colgroup) => {
        indexesToRemove.forEach((index) => {
          colgroup.children[index]?.remove();
        });
      });
    });

    indexesToRemove.forEach((index) => {
      headerRow.children[index]?.remove();
    });

    bodyTable.querySelectorAll("tbody tr").forEach((row) => {
      indexesToRemove.forEach((index) => {
        row.children[index]?.remove();
      });
    });

    moduleRoot.dataset[`normalized${prefix}`] = "true";
  }

  function getReturnModuleElements() {
    return {
      movementType: document.getElementById("almacen-embarques-returns-movement-type"),
      partNumber: document.getElementById("almacen-embarques-returns-part-number"),
      quantity: document.getElementById("almacen-embarques-returns-quantity"),
      reason: document.getElementById("almacen-embarques-returns-reason"),
      location: document.getElementById("almacen-embarques-returns-location"),
      remarks: document.getElementById("almacen-embarques-returns-remarks"),
      submitBtn: document.getElementById("almacen-embarques-returns-submit-btn"),
      formStatus: document.getElementById("almacen-embarques-returns-form-status"),
      entryExportBtn: document.getElementById("almacen-embarques-return-in-export-btn"),
      entryBody: document.getElementById("almacen-embarques-return-in-tbody"),
      entryCount: document.getElementById("almacen-embarques-return-in-count"),
      entryStatus: document.getElementById("almacen-embarques-return-in-status"),
      exitExportBtn: document.getElementById("almacen-embarques-return-out-export-btn"),
      exitBody: document.getElementById("almacen-embarques-return-out-tbody"),
      exitCount: document.getElementById("almacen-embarques-return-out-count"),
      exitStatus: document.getElementById("almacen-embarques-return-out-status"),
    };
  }

  function buildQuery(prefix) {
    const elements = getElements(prefix);
    const params = new URLSearchParams();

    if (elements.searchInput?.value.trim()) {
      params.set("search", elements.searchInput.value.trim());
    }

    if (elements.dateFrom?.value) {
      params.set("fecha_desde", elements.dateFrom.value);
    }

    if (elements.dateTo?.value) {
      params.set("fecha_hasta", elements.dateTo.value);
    }

    return params;
  }

  function setStatus(prefix, message, isError = false) {
    const { statusLabel } = getElements(prefix);
    if (!statusLabel) {
      return;
    }

    statusLabel.textContent = message;
    statusLabel.style.color = isError ? "#ff8f8f" : "#8fb8ff";
  }

  function setLoading(prefix, colspan, message) {
    const { tableBody } = getElements(prefix);
    if (!tableBody) {
      return;
    }

    tableBody.innerHTML = `<tr><td colspan="${colspan}" class="history-empty-cell">${escapeHtml(
      message,
    )}</td></tr>`;
  }

  function renderEmpty(prefix, colspan, message) {
    const { tableBody, countLabel } = getElements(prefix);
    if (!tableBody) {
      return;
    }

    if (countLabel) {
      countLabel.textContent = "0 registros";
    }

    tableBody.innerHTML = `<tr><td colspan="${colspan}" class="history-empty-cell">${escapeHtml(
      message,
    )}</td></tr>`;
  }

  function renderEntriesRows(rows) {
    return rows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.fecha)}</td>
            <td>${escapeHtml(row.hora)}</td>
            <td>${escapeHtml(row.folio)}</td>
            <td><strong>${escapeHtml(row.part_number)}</strong></td>
            <td>${formatNumber(row.cantidad)}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${escapeHtml(row.customer || "-")}</td>
            <td>${escapeHtml(row.zone_code || "-")}</td>
            <td>${escapeHtml(row.location_code || "-")}</td>
            <td>${escapeHtml(row.registered_by || "-")}</td>
          </tr>
        `,
      )
      .join("");
  }

  function renderExitsRows(rows) {
    return rows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.fecha)}</td>
            <td>${escapeHtml(row.hora)}</td>
            <td>${escapeHtml(row.folio)}</td>
            <td><strong>${escapeHtml(row.part_number)}</strong></td>
            <td>${formatNumber(row.cantidad)}</td>
            <td>${buildDepartureCell(row)}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${escapeHtml(row.customer || "-")}</td>
            <td>${escapeHtml(row.registered_by || "-")}</td>
          </tr>
        `,
      )
      .join("");
  }

  function renderReturnsRows(rows) {
    return rows
      .map((row) => {
        const badgeText = getNormalizedReturnType(row.reason);
        const badgeVariant =
          badgeText.toLowerCase() === "os&d" ? "warning" : "success";

        return `
          <tr>
            <td>${escapeHtml(row.fecha)}</td>
            <td>${escapeHtml(row.hora)}</td>
            <td>${escapeHtml(row.folio)}</td>
            <td><strong>${escapeHtml(row.part_number)}</strong></td>
            <td>${formatNumber(row.return_quantity)}</td>
            <td>${formatNumber(row.loss_quantity)}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${escapeHtml(row.customer || "-")}</td>
            <td>${buildBadge(badgeText, badgeVariant)}</td>
            <td>${escapeHtml(row.registered_by || "-")}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderReturnEntryRows(rows) {
    return rows
      .map((row) => {
        const quantity = Math.max(
          0,
          Number(row.return_quantity || 0) - Number(row.loss_quantity || 0),
        );
        const returnType = getNormalizedReturnType(row.reason);
        return `
          <tr>
            <td>${escapeHtml(row.fecha)}</td>
            <td>${escapeHtml(row.hora)}</td>
            <td>${escapeHtml(row.folio)}</td>
            <td><strong>${escapeHtml(row.part_number)}</strong></td>
            <td>${formatNumber(quantity)}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${buildBadge(returnType, returnType === "OS&D" ? "warning" : "success")}</td>
            <td>${escapeHtml(row.registered_by || "-")}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderReturnExitRows(rows) {
    return rows
      .map((row) => {
        const returnType = getNormalizedReturnType(row.reason);
        return `
          <tr>
            <td>${escapeHtml(row.fecha)}</td>
            <td>${escapeHtml(row.hora)}</td>
            <td>${escapeHtml(row.folio)}</td>
            <td><strong>${escapeHtml(row.part_number)}</strong></td>
            <td>${formatNumber(row.loss_quantity)}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${buildBadge(returnType, returnType === "OS&D" ? "warning" : "success")}</td>
            <td>${escapeHtml(row.registered_by || "-")}</td>
          </tr>
        `;
      })
      .join("");
  }

  function setReturnFormStatus(message, isError = false) {
    const { formStatus } = getReturnModuleElements();
    if (!formStatus) {
      return;
    }
    formStatus.textContent = message || "";
    formStatus.style.color = isError ? "#ff8f8f" : "#8fb8ff";
  }

  function renderReturnHistoryTable(targetBody, targetCount, rows, emptyMessage, renderer) {
    if (!targetBody || !targetCount) {
      return;
    }

    if (!rows.length) {
      targetCount.textContent = "0 registros";
      targetBody.innerHTML = `<tr><td colspan="8" class="ae-empty-cell">${escapeHtml(
        emptyMessage,
      )}</td></tr>`;
      return;
    }

    const suffix = rows.length === 1 ? "registro" : "registros";
    targetCount.textContent = `${rows.length} ${suffix}`;
    targetBody.innerHTML = renderer(rows);
  }

  async function loadReturnsModule() {
    const elements = getReturnModuleElements();
    if (!elements.entryBody || !elements.exitBody) {
      return;
    }

    elements.entryBody.innerHTML =
      '<tr><td colspan="8" class="ae-empty-cell">Cargando historial...</td></tr>';
    elements.exitBody.innerHTML =
      '<tr><td colspan="8" class="ae-empty-cell">Cargando historial...</td></tr>';

    if (elements.entryStatus) {
      elements.entryStatus.textContent = "Consultando datos...";
      elements.entryStatus.style.color = "#8fb8ff";
    }
    if (elements.exitStatus) {
      elements.exitStatus.textContent = "Consultando datos...";
      elements.exitStatus.style.color = "#8fb8ff";
    }

    try {
      const response = await fetch("/api/almacen-embarques/retorno", {
        credentials: "same-origin",
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const rows = await response.json();
      if (!Array.isArray(rows)) {
        throw new Error("Respuesta inválida del servidor");
      }

      const entryRows = rows.filter(
        (row) => Number(row.return_quantity || 0) - Number(row.loss_quantity || 0) > 0,
      );
      const exitRows = rows.filter((row) => Number(row.loss_quantity || 0) > 0);

      renderReturnHistoryTable(
        elements.entryBody,
        elements.entryCount,
        entryRows,
        "No hay entradas de retorno registradas.",
        renderReturnEntryRows,
      );
      renderReturnHistoryTable(
        elements.exitBody,
        elements.exitCount,
        exitRows,
        "No hay salidas de retorno registradas.",
        renderReturnExitRows,
      );

      const updatedAt = new Date().toLocaleTimeString("es-MX", {
        hour: "2-digit",
        minute: "2-digit",
      });
      if (elements.entryStatus) {
        elements.entryStatus.textContent = `Actualizado a las ${updatedAt}`;
        elements.entryStatus.style.color = "#8fb8ff";
      }
      if (elements.exitStatus) {
        elements.exitStatus.textContent = `Actualizado a las ${updatedAt}`;
        elements.exitStatus.style.color = "#8fb8ff";
      }

      const moduleRoot = document.getElementById("almacen-embarques-returns-module");
      syncScrollableHeight(moduleRoot);
      syncTableWidths(moduleRoot);
    } catch (error) {
      console.error("Error cargando módulo retornos:", error);
      renderReturnHistoryTable(
        elements.entryBody,
        elements.entryCount,
        [],
        "No fue posible cargar entradas de retorno.",
        renderReturnEntryRows,
      );
      renderReturnHistoryTable(
        elements.exitBody,
        elements.exitCount,
        [],
        "No fue posible cargar salidas de retorno.",
        renderReturnExitRows,
      );
      if (elements.entryStatus) {
        elements.entryStatus.textContent = "Error al consultar historial";
        elements.entryStatus.style.color = "#ff8f8f";
      }
      if (elements.exitStatus) {
        elements.exitStatus.textContent = "Error al consultar historial";
        elements.exitStatus.style.color = "#ff8f8f";
      }
    }
  }

  function clearReturnForm() {
    const elements = getReturnModuleElements();
    if (elements.movementType) elements.movementType.value = "entry";
    if (elements.partNumber) elements.partNumber.value = "";
    if (elements.quantity) elements.quantity.value = "";
    if (elements.reason) elements.reason.value = "Exceso";
    if (elements.location) elements.location.value = "";
    if (elements.remarks) elements.remarks.value = "";
    setReturnFormStatus("");
  }

  function exportReturnsByMovement(movementType) {
    const params = new URLSearchParams();
    params.set("movement", movementType);
    window.open(`/api/almacen-embarques/retorno/export?${params.toString()}`, "_blank");
  }

  async function submitReturnForm() {
    const moduleRoot = document.getElementById("almacen-embarques-returns-module");
    const elements = getReturnModuleElements();
    if (!moduleRoot || !elements.submitBtn) {
      return;
    }

    const movementType = elements.movementType?.value || "entry";
    const partNumber = elements.partNumber?.value?.trim()?.toUpperCase() || "";
    const quantity = Number((elements.quantity?.value || "").replace(/\D+/g, ""));
    const reason = elements.reason?.value || "Exceso";
    const location = elements.location?.value?.trim() || "";
    const remarks = elements.remarks?.value?.trim() || "";
    const registeredBy = moduleRoot.dataset.registeredBy || "Sistema";

    if (!partNumber) {
      setReturnFormStatus("El número de parte es obligatorio.", true);
      elements.partNumber?.focus();
      return;
    }

    if (!Number.isFinite(quantity) || quantity <= 0) {
      setReturnFormStatus("La cantidad debe ser mayor a cero.", true);
      elements.quantity?.focus();
      return;
    }

    const requestBody = {
      partNumber,
      returnQty: quantity,
      lossQty: movementType === "exit" ? quantity : 0,
      location,
      reason: movementType === "exit" ? `${reason} / Salida retorno` : reason,
      remarks,
      registeredBy,
    };

    try {
      elements.submitBtn.disabled = true;
      elements.submitBtn.textContent =
        movementType === "exit" ? "Guardando..." : "Guardando...";
      setReturnFormStatus("Guardando movimiento...");

      const response = await fetch("/api/shipping/material/returns", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
      }

      clearReturnForm();
      setReturnFormStatus(
        movementType === "exit"
          ? "Salida de retorno registrada correctamente."
          : "Entrada de retorno registrada correctamente.",
      );
      await loadReturnsModule();
    } catch (error) {
      setReturnFormStatus(error.message || "No fue posible registrar el movimiento.", true);
    } finally {
      elements.submitBtn.disabled = false;
      elements.submitBtn.textContent = "Registrar";
    }
  }

  async function loadModule(config) {
    const { prefix, apiUrl, colspan, emptyMessage, renderer } = config;
    const elements = getElements(prefix);
    if (!elements.tableBody) {
      return;
    }

    setLoading(prefix, colspan, "Cargando historial...");
    setStatus(prefix, "Consultando datos...");

    try {
      const params = buildQuery(prefix);
      const response = await fetch(`${apiUrl}?${params.toString()}`, {
        credentials: "same-origin",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const rows = await response.json();
      if (!Array.isArray(rows)) {
        throw new Error("Respuesta inválida del servidor");
      }

      if (!rows.length) {
        renderEmpty(prefix, colspan, emptyMessage);
        setStatus(prefix, "Sin registros para los filtros actuales");
        return;
      }

      elements.tableBody.innerHTML = renderer(rows);
      if (elements.countLabel) {
        const suffix = rows.length === 1 ? "registro" : "registros";
        elements.countLabel.textContent = `${rows.length} ${suffix}`;
      }

      const updatedAt = new Date().toLocaleTimeString("es-MX", {
        hour: "2-digit",
        minute: "2-digit",
      });
      setStatus(prefix, `Actualizado a las ${updatedAt}`);
      const moduleRoot = document.getElementById(`${prefix}-module`);
      syncScrollableHeight(moduleRoot);
      syncTableWidths(moduleRoot);
    } catch (error) {
      console.error(`Error cargando módulo ${prefix}:`, error);
      renderEmpty(prefix, colspan, "No fue posible cargar el historial.");
      setStatus(prefix, "Error al consultar el historial", true);
      const moduleRoot = document.getElementById(`${prefix}-module`);
      syncScrollableHeight(moduleRoot);
      syncTableWidths(moduleRoot);
    }
  }

  function exportModule(config) {
    const params = buildQuery(config.prefix);
    const url = `${config.exportUrl}?${params.toString()}`;
    window.open(url, "_blank");
  }

  async function saveDepartureAssignment(config, assignmentPayload, button) {
    const departureValue = assignmentPayload?.departureCode?.trim?.() || "";
    const departureQuantity = Number(assignmentPayload?.departureQuantity ?? "");
    if (!departureValue) {
      setStatus(config.prefix, "Captura un departure antes de guardar", true);
      setDepartureModalError("Captura un departure valido antes de guardar.");
      return;
    }
    if (!Number.isFinite(departureQuantity) || departureQuantity <= 0) {
      setStatus(config.prefix, "Captura una cantidad valida para el departure", true);
      setDepartureModalError("La cantidad debe ser mayor a cero.");
      return;
    }

    if (button) {
      button.disabled = true;
      button.textContent = "Guardando...";
    }

    try {
      const response = await fetch(`/api/almacen-embarques/salidas/${assignmentPayload.exitId}/departure`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          departureCode: departureValue,
          departureQuantity,
        }),
      });

      const responsePayload = await response.json().catch(() => ({}));
      if (!response.ok || responsePayload.success === false) {
        throw new Error(responsePayload.error || responsePayload.message || `HTTP ${response.status}`);
      }

      const successMessage = responsePayload.splitCreated
        ? `Departure ${responsePayload.departureCode || departureValue} asignado. Resto enviado a ${responsePayload.splitFolio}`
        : `Departure ${responsePayload.departureCode || departureValue} asignado`;
      closeDepartureModal();
      setStatus(config.prefix, successMessage);
      await loadModule(config);
    } catch (error) {
      setStatus(config.prefix, error.message || "No fue posible asignar el departure", true);
      setDepartureModalError(error.message || "No fue posible asignar el departure.");
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = "Guardar";
      }
    }
  }

  function submitDepartureModal() {
    const modal = document.getElementById("ae-departure-modal");
    const config = departureModalState?.config;
    if (!modal || !config) {
      return;
    }

    const quantityInput = modal.querySelector("#ae-departure-modal-quantity");
    const saveButton = modal.querySelector('[data-action="save"]');
    const totalQuantity = Number(modal.dataset.totalQuantity || 0) || 0;
    const departureQuantity = Number(quantityInput?.value ?? "");

    if (!Number.isFinite(departureQuantity) || departureQuantity <= 0) {
      setDepartureModalError("La cantidad debe ser mayor a cero.");
      quantityInput?.focus();
      quantityInput?.select?.();
      return;
    }

    if (totalQuantity > 0 && departureQuantity > totalQuantity) {
      setDepartureModalError(`La cantidad no puede ser mayor a ${formatNumber(totalQuantity)}.`);
      quantityInput?.focus();
      quantityInput?.select?.();
      return;
    }

    saveDepartureAssignment(
      config,
      {
        exitId: modal.dataset.exitId,
        departureCode: modal.dataset.departureCode,
        departureQuantity,
      },
      saveButton,
    );
  }

  function bindScrollableShells(moduleRoot) {
    if (!moduleRoot) {
      return;
    }

    const tableShells = moduleRoot.querySelectorAll(".ae-table-shell");
    tableShells.forEach((tableShell) => {
      const headerWrap = tableShell.querySelector(".ae-table-head");
      const bodyWrap = tableShell.querySelector(".ae-table-body-wrap");
      if (!headerWrap || !bodyWrap || bodyWrap.dataset.scrollBound === "true") {
        return;
      }

      bodyWrap.addEventListener("scroll", () => {
        headerWrap.scrollLeft = bodyWrap.scrollLeft;
      });
      bodyWrap.dataset.scrollBound = "true";
    });
  }

  function bindModuleResize(moduleRoot) {
    if (!moduleRoot || moduleRoot.dataset.resizeBound === "true") {
      return;
    }

    const updateHeight = () => {
      initResizableShells(moduleRoot);
      syncScrollableHeight(moduleRoot);
      syncTableWidths(moduleRoot);
    };

    window.addEventListener("resize", updateHeight);
    requestAnimationFrame(() => requestAnimationFrame(updateHeight));
    moduleRoot.dataset.resizeBound = "true";
  }

  function bindReturnsModule(config) {
    const moduleRoot = document.getElementById(`${config.prefix}-module`);
    const elements = getReturnModuleElements();
    if (!moduleRoot || !elements.entryBody || !elements.exitBody) {
      return;
    }

    bindScrollableShells(moduleRoot);
    bindModuleResize(moduleRoot);

    if (elements.quantity && elements.quantity.dataset.numericBound !== "true") {
      elements.quantity.addEventListener("input", () => {
        elements.quantity.value = elements.quantity.value.replace(/\D+/g, "");
      });
      elements.quantity.dataset.numericBound = "true";
    }

    if (elements.submitBtn && elements.submitBtn.dataset.bound !== "true") {
      elements.submitBtn.addEventListener("click", submitReturnForm);
      elements.submitBtn.dataset.bound = "true";
    }

    if (elements.entryExportBtn && elements.entryExportBtn.dataset.bound !== "true") {
      elements.entryExportBtn.addEventListener("click", () => exportReturnsByMovement("entry"));
      elements.entryExportBtn.dataset.bound = "true";
    }

    if (elements.exitExportBtn && elements.exitExportBtn.dataset.bound !== "true") {
      elements.exitExportBtn.addEventListener("click", () => exportReturnsByMovement("exit"));
      elements.exitExportBtn.dataset.bound = "true";
    }

    if (elements.partNumber && elements.partNumber.dataset.bound !== "true") {
      elements.partNumber.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          submitReturnForm();
        }
      });
      elements.partNumber.dataset.bound = "true";
    }

    if (elements.quantity && elements.quantity.dataset.submitBound !== "true") {
      elements.quantity.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          submitReturnForm();
        }
      });
      elements.quantity.dataset.submitBound = "true";
    }
  }

  function bindModule(config) {
    const moduleRoot = document.getElementById(`${config.prefix}-module`);
    normalizeModuleTableColumns(moduleRoot, config.prefix);
    if (config.prefix === "almacen-embarques-returns") {
      bindReturnsModule(config);
      return;
    }

    const elements = getElements(config.prefix);
    if (!elements.tableBody) {
      return;
    }

    bindScrollableShells(moduleRoot);
    bindModuleResize(moduleRoot);

    if (config.prefix === "almacen-embarques-exits" && elements.tableBody.dataset.departureBound !== "true") {
      elements.tableBody.addEventListener("keydown", (event) => {
        if (!event.target.classList.contains("ae-departure-input")) {
          return;
        }
        if (event.key !== "Enter" && event.key !== "Tab") {
          return;
        }

        const input = event.target;
        const departureValue = input.value?.trim();
        if (!departureValue) {
          return;
        }

        event.preventDefault();
        openDepartureModal(config, input);
      });

      elements.tableBody.dataset.departureBound = "true";
    }

    elements.searchBtn?.addEventListener("click", () => loadModule(config));
    elements.exportBtn?.addEventListener("click", () => exportModule(config));
    elements.clearBtn?.addEventListener("click", () => {
      if (elements.searchInput) {
        elements.searchInput.value = "";
      }
      if (elements.dateFrom) {
        elements.dateFrom.value = "";
      }
      if (elements.dateTo) {
        elements.dateTo.value = "";
      }
      loadModule(config);
    });
    elements.searchInput?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        loadModule(config);
      }
    });
  }

  function initializeModule(config) {
    ensureModuleStyles();
    bindModule(config);
    requestAnimationFrame(() =>
      requestAnimationFrame(() =>
        (() => {
          const moduleRoot = document.getElementById(`${config.prefix}-module`);
          syncScrollableHeight(moduleRoot);
          syncTableWidths(moduleRoot);
        })(),
      ),
    );
    if (config.prefix === "almacen-embarques-returns") {
      loadReturnsModule();
      return;
    }

    loadModule(config);
  }

  window.inicializarAlmacenEmbarquesEntradasAjax = function () {
    initializeModule({
      prefix: "almacen-embarques-entries",
      apiUrl: "/api/almacen-embarques/entradas",
      exportUrl: "/api/almacen-embarques/entradas/export",
      colspan: 10,
      emptyMessage: "No hay entradas registradas para los filtros actuales.",
      renderer: renderEntriesRows,
    });
  };

  window.inicializarAlmacenEmbarquesSalidasAjax = function () {
    initializeModule({
      prefix: "almacen-embarques-exits",
      apiUrl: "/api/almacen-embarques/salidas",
      exportUrl: "/api/almacen-embarques/salidas/export",
      colspan: 9,
      emptyMessage: "No hay salidas registradas para los filtros actuales.",
      renderer: renderExitsRows,
    });
  };

  window.inicializarAlmacenEmbarquesRetornoAjax = function () {
    initializeModule({
      prefix: "almacen-embarques-returns",
      apiUrl: "/api/almacen-embarques/retorno",
      exportUrl: "/api/almacen-embarques/retorno/export",
      colspan: 8,
      emptyMessage: "No hay retornos registrados para los filtros actuales.",
      renderer: renderReturnsRows,
    });
  };
})();
