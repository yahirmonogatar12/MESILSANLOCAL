(function () {
  const STYLESHEET_ID = "almacen-embarques-history-css";
  const STYLESHEET_HREF = "/static/css/almacen_embarques_history.css?v=20260415a";

  const movementModuleState = {
    rows: [],
    editingKey: "",
    originalRow: null,
    draftRow: null,
  };

  const confirmState = {
    config: null,
    movementType: "",
    recordId: null,
    changes: null,
    beforeRows: [],
    afterRows: [],
  };

  function ensureModuleStyles() {
    const currentLink = document.getElementById(STYLESHEET_ID);
    if (currentLink) {
      if (!currentLink.getAttribute("href")?.includes("20260415a")) {
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

  function getElements(prefix) {
    return {
      searchInput: document.getElementById(`${prefix}-search`),
      typeSelect: document.getElementById(`${prefix}-type`),
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

  function getModuleRoot(prefix) {
    return document.getElementById(`${prefix}-module`);
  }

  function buildQuery(prefix) {
    const elements = getElements(prefix);
    const params = new URLSearchParams();

    if (elements.searchInput?.value.trim()) {
      params.set("search", elements.searchInput.value.trim());
    }
    if (elements.typeSelect?.value) {
      params.set("tipo", elements.typeSelect.value);
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
    statusLabel.textContent = message || "";
    statusLabel.style.color = isError ? "#ff8f8f" : "#8fb8ff";
  }

  function setLoading(prefix, colspan, message) {
    const { tableBody } = getElements(prefix);
    if (!tableBody) {
      return;
    }
    tableBody.innerHTML = `<tr><td colspan="${colspan}" class="ae-empty-cell">${escapeHtml(
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
    tableBody.innerHTML = `<tr><td colspan="${colspan}" class="ae-empty-cell">${escapeHtml(
      message,
    )}</td></tr>`;
  }

  function syncScrollableHeight(moduleRoot) {
    const bodyWrap = moduleRoot?.querySelector(".ae-table-body-wrap");
    if (!bodyWrap) {
      return;
    }

    const viewportHeight =
      window.innerHeight || document.documentElement.clientHeight || 0;
    const rect = bodyWrap.getBoundingClientRect();
    const bottomGap = 20;
    const availableHeight = Math.max(220, viewportHeight - rect.top - bottomGap);

    bodyWrap.style.height = `${availableHeight}px`;
    bodyWrap.style.maxHeight = `${availableHeight}px`;
  }

  function syncTableWidths(moduleRoot) {
    const headerWrap = moduleRoot?.querySelector(".ae-table-head");
    const headerTable = moduleRoot?.querySelector(".ae-history-table--head");
    const bodyWrap = moduleRoot?.querySelector(".ae-table-body-wrap");
    const bodyTable = moduleRoot?.querySelector(".ae-history-table--body");
    if (!headerWrap || !headerTable || !bodyWrap || !bodyTable) {
      return;
    }

    const scrollbarWidth = Math.max(0, bodyWrap.offsetWidth - bodyWrap.clientWidth);
    const targetWidth = Math.max(bodyWrap.clientWidth, bodyTable.scrollWidth);

    headerWrap.style.paddingRight = `${scrollbarWidth}px`;
    headerTable.style.width = `${targetWidth}px`;
    bodyTable.style.width = `${targetWidth}px`;
  }

  function getMovementRecordKey(row) {
    return `${row.movement_type}:${row.record_id}`;
  }

  function cloneMovementRow(row) {
    return JSON.parse(JSON.stringify(row || {}));
  }

  function getMovementQuantity(row) {
    if (row.movement_type === "return") {
      return row.return_quantity ?? row.quantity_primary ?? 0;
    }
    return row.quantity_primary ?? row.quantity ?? 0;
  }

  function getMovementDateValue(row) {
    return row.fecha || "";
  }

  function getMovementLocationValue(row) {
    return row.location_value || "";
  }

  function getMovementEditableFields(row) {
    const fields = [
      {
        name: "fecha",
        label: "Fecha",
        type: "date",
        previous: getMovementDateValue(row),
      },
      {
        name: "cantidad",
        label: "Cantidad",
        type: "integer",
        previous: getMovementQuantity(row),
      },
      {
        name: "zona",
        label: "Zona",
        type: "text",
        previous: row.zone_code || "",
      },
      {
        name: "ubicacion_destino",
        label: "Ubicación / Destino",
        type: "text",
        previous: getMovementLocationValue(row),
      },
    ];

    if (row.movement_type === "exit") {
      fields.push({
        name: "departure",
        label: "Departure",
        type: "text",
        previous: row.departure_code || "",
      });
    }

    return fields;
  }

  function getEditableValue(fieldName, row) {
    switch (fieldName) {
      case "fecha":
        return getMovementDateValue(row);
      case "cantidad":
        return String(getMovementQuantity(row) ?? "");
      case "zona":
        return row.zone_code || "";
      case "ubicacion_destino":
        return getMovementLocationValue(row);
      case "departure":
        return row.departure_code || "";
      default:
        return "";
    }
  }

  function getEditableInputMarkup(fieldName, row) {
    const value = escapeHtml(getEditableValue(fieldName, row));

    if (fieldName === "fecha") {
      return `<input type="date" class="ae-inline-input" data-field-name="${fieldName}" value="${value}">`;
    }

    if (fieldName === "cantidad") {
      return `<input type="text" class="ae-inline-input ae-inline-input--number" data-field-name="${fieldName}" data-field-type="integer" inputmode="numeric" value="${value}">`;
    }

    if (fieldName === "departure" && row.movement_type !== "exit") {
      return `<span class="ae-inline-static">-</span>`;
    }

    return `<input type="text" class="ae-inline-input" data-field-name="${fieldName}" value="${value}">`;
  }

  function renderMovementNormalRow(row) {
    const typeVariant =
      row.movement_type === "entry"
        ? "success"
        : row.movement_type === "exit"
          ? "warning"
          : "neutral";

    return `
      <tr data-record-key="${escapeHtml(getMovementRecordKey(row))}">
        <td>${escapeHtml(row.fecha)}</td>
        <td>${escapeHtml(row.hora)}</td>
        <td>${buildBadge(row.movement_label || row.movement_type, typeVariant)}</td>
        <td>${escapeHtml(row.folio)}</td>
        <td><strong>${escapeHtml(row.part_number)}</strong></td>
        <td>${formatNumber(getMovementQuantity(row))}</td>
        <td>${escapeHtml(row.product_model || "-")}</td>
        <td>${escapeHtml(row.customer || "-")}</td>
        <td>${escapeHtml(row.zone_code || "-")}</td>
        <td>${escapeHtml(getMovementLocationValue(row) || "-")}</td>
        <td>${escapeHtml(row.departure_code || "-")}</td>
        <td>
          <button
            type="button"
            class="ae-btn-inline ae-btn-inline-edit"
            data-action="edit-movement"
            data-record-key="${escapeHtml(getMovementRecordKey(row))}"
          >
            Editar
          </button>
        </td>
      </tr>
    `;
  }

  function renderMovementEditableRow(row) {
    return `
      <tr class="ae-row-editing" data-record-key="${escapeHtml(getMovementRecordKey(row))}">
        <td class="ae-edit-cell">${getEditableInputMarkup("fecha", row)}</td>
        <td>${escapeHtml(row.hora)}</td>
        <td>${buildBadge(row.movement_label || row.movement_type, "neutral")}</td>
        <td>${escapeHtml(row.folio)}</td>
        <td><strong>${escapeHtml(row.part_number)}</strong></td>
        <td class="ae-edit-cell">${getEditableInputMarkup("cantidad", row)}</td>
        <td>${escapeHtml(row.product_model || "-")}</td>
        <td>${escapeHtml(row.customer || "-")}</td>
        <td class="ae-edit-cell">${getEditableInputMarkup("zona", row)}</td>
        <td class="ae-edit-cell">${getEditableInputMarkup("ubicacion_destino", row)}</td>
        <td class="ae-edit-cell">${getEditableInputMarkup("departure", row)}</td>
        <td>
          <div class="ae-inline-actions">
            <button
              type="button"
              class="ae-btn-inline ae-btn-inline-save"
              data-action="save-movement"
              data-record-key="${escapeHtml(getMovementRecordKey(row))}"
            >
              Guardar
            </button>
            <button
              type="button"
              class="ae-btn-inline ae-btn-inline-cancel"
              data-action="cancel-edit-movement"
              data-record-key="${escapeHtml(getMovementRecordKey(row))}"
            >
              Cancelar
            </button>
          </div>
        </td>
      </tr>
    `;
  }

  function renderMovementsRows(rows) {
    return rows
      .map((row) =>
        movementModuleState.editingKey === getMovementRecordKey(row)
          ? renderMovementEditableRow(row)
          : renderMovementNormalRow(row),
      )
      .join("");
  }

  function renderInventoryRows(rows) {
    return rows
      .map(
        (row) => `
          <tr>
            <td><strong>${escapeHtml(row.part_number)}</strong></td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${escapeHtml(row.customer || "-")}</td>
            <td>${formatNumber(row.initial_quantity)}</td>
            <td>${formatNumber(row.entries_qty)}</td>
            <td>${formatNumber(row.exits_qty)}</td>
            <td>${formatNumber(row.return_entries_qty)}</td>
            <td>${formatNumber(row.return_exits_qty)}</td>
            <td><strong>${formatNumber(row.current_quantity)}</strong></td>
          </tr>
        `,
      )
      .join("");
  }

  async function loadModule(config) {
    const { prefix, apiUrl, colspan, emptyMessage, renderer } = config;
    const elements = getElements(prefix);
    if (!elements.tableBody) {
      return;
    }

    setLoading(prefix, colspan, "Cargando información...");
    setStatus(prefix, "Consultando datos...");

    try {
      const params = buildQuery(prefix);
      const response = await fetch(`${apiUrl}?${params.toString()}`, {
        credentials: "same-origin",
      });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
      }

      const rows = Array.isArray(payload) ? payload : payload.rows || [];
      if (prefix === "almacen-embarques-movements") {
        movementModuleState.rows = rows.map((row) => cloneMovementRow(row));
      }

      if (!rows.length) {
        renderEmpty(prefix, colspan, emptyMessage);
        if (typeof config.onAfterLoad === "function") {
          config.onAfterLoad(payload);
        }
        setStatus(prefix, "Sin registros para los filtros actuales");
        return;
      }

      elements.tableBody.innerHTML = renderer(rows, payload);
      if (elements.countLabel) {
        const suffix = rows.length === 1 ? "registro" : "registros";
        elements.countLabel.textContent = `${rows.length} ${suffix}`;
      }

      if (typeof config.onAfterLoad === "function") {
        config.onAfterLoad(payload);
      } else {
        const updatedAt = new Date().toLocaleTimeString("es-MX", {
          hour: "2-digit",
          minute: "2-digit",
        });
        setStatus(prefix, `Actualizado a las ${updatedAt}`);
      }

      const moduleRoot = getModuleRoot(prefix);
      syncScrollableHeight(moduleRoot);
      syncTableWidths(moduleRoot);
    } catch (error) {
      console.error(`Error cargando módulo ${prefix}:`, error);
      renderEmpty(prefix, colspan, "No fue posible cargar la información.");
      setStatus(prefix, error.message || "Error al consultar información", true);
      const moduleRoot = getModuleRoot(prefix);
      syncScrollableHeight(moduleRoot);
      syncTableWidths(moduleRoot);
    }
  }

  function exportModule(config) {
    const params = buildQuery(config.prefix);
    const url = `${config.exportUrl}?${params.toString()}`;
    window.open(url, "_blank");
  }

  function rerenderMovementTable() {
    const { tableBody } = getElements("almacen-embarques-movements");
    if (!tableBody) {
      return;
    }

    if (!movementModuleState.rows.length) {
      renderEmpty(
        "almacen-embarques-movements",
        12,
        "No hay movimientos disponibles para los filtros actuales.",
      );
      return;
    }

    tableBody.innerHTML = renderMovementsRows(movementModuleState.rows);
    syncTableWidths(getModuleRoot("almacen-embarques-movements"));
  }

  function startMovementEdit(recordKey) {
    const originalRow = movementModuleState.rows.find(
      (row) => getMovementRecordKey(row) === recordKey,
    );
    if (!originalRow) {
      return;
    }

    movementModuleState.editingKey = recordKey;
    movementModuleState.originalRow = cloneMovementRow(originalRow);
    movementModuleState.draftRow = cloneMovementRow(originalRow);
    rerenderMovementTable();

    const firstEditable = getElements("almacen-embarques-movements").tableBody?.querySelector(
      `tr[data-record-key="${CSS.escape(recordKey)}"] .ae-inline-input`,
    );
    firstEditable?.focus();
    firstEditable?.select?.();
  }

  function cancelMovementEdit() {
    movementModuleState.editingKey = "";
    movementModuleState.originalRow = null;
    movementModuleState.draftRow = null;
    rerenderMovementTable();
  }

  function sanitizeIntegerValue(value) {
    return String(value ?? "").replace(/\D+/g, "");
  }

  function updateDraftFromRowInput(input) {
    if (!movementModuleState.draftRow) {
      return;
    }
    const fieldName = input.dataset.fieldName;
    if (!fieldName) {
      return;
    }

    let nextValue = input.value ?? "";
    if (input.dataset.fieldType === "integer") {
      nextValue = sanitizeIntegerValue(nextValue);
      input.value = nextValue;
    }

    switch (fieldName) {
      case "fecha":
        movementModuleState.draftRow.fecha = nextValue;
        break;
      case "cantidad":
        if (movementModuleState.draftRow.movement_type === "return") {
          movementModuleState.draftRow.return_quantity = nextValue === "" ? "" : Number(nextValue);
        } else {
          movementModuleState.draftRow.quantity_primary = nextValue === "" ? "" : Number(nextValue);
        }
        break;
      case "zona":
        movementModuleState.draftRow.zone_code = nextValue.trim();
        break;
      case "ubicacion_destino":
        movementModuleState.draftRow.location_value = nextValue.trim();
        break;
      case "departure":
        movementModuleState.draftRow.departure_code = nextValue.trim().toUpperCase();
        input.value = movementModuleState.draftRow.departure_code;
        break;
      default:
        break;
    }
  }

  function buildChangesForMovement(originalRow, draftRow) {
    const changes = {};
    const beforeRows = [];
    const afterRows = [];

    const editableFields = getMovementEditableFields(originalRow);
    editableFields.forEach((field) => {
      const originalValue = String(getEditableValue(field.name, originalRow) ?? "");
      const draftValue = String(getEditableValue(field.name, draftRow) ?? "");
      if (originalValue === draftValue) {
        return;
      }

      beforeRows.push({ label: field.label, value: originalValue || "-" });
      afterRows.push({ label: field.label, value: draftValue || "-" });

      if (field.name === "fecha") {
        changes.movement_at = draftValue;
      } else if (field.name === "cantidad") {
        if (draftRow.movement_type === "return") {
          changes.return_quantity = draftValue;
        } else {
          changes.quantity = draftValue;
        }
      } else if (field.name === "zona") {
        changes.zone_code = draftValue;
      } else if (field.name === "ubicacion_destino") {
        if (draftRow.movement_type === "exit") {
          changes.destination_area = draftValue;
        } else {
          changes.location_code = draftValue;
        }
      } else if (field.name === "departure") {
        changes.departure_code = draftValue;
      }
    });

    return { changes, beforeRows, afterRows };
  }

  function getConfirmModal() {
    let modal = document.getElementById("ae-movement-confirm-modal");
    if (modal) {
      return modal;
    }

    modal = document.createElement("div");
    modal.id = "ae-movement-confirm-modal";
    modal.className = "ae-confirm-modal";
    modal.innerHTML = `
      <div class="ae-confirm-modal__backdrop" data-action="cancel-confirm"></div>
      <div class="ae-confirm-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="ae-confirm-modal-title">
        <div class="ae-confirm-modal__header">
          <h4 id="ae-confirm-modal-title">Confirmar cambios</h4>
          <button type="button" class="ae-confirm-modal__close" data-action="cancel-confirm" aria-label="Cerrar">&times;</button>
        </div>
        <div class="ae-confirm-modal__body">
          <div class="ae-confirm-modal__summary">
            <div><span>Tipo</span><strong data-role="confirm-type"></strong></div>
            <div><span>Folio</span><strong data-role="confirm-folio"></strong></div>
            <div><span>No. parte</span><strong data-role="confirm-part"></strong></div>
          </div>
          <div class="ae-confirm-modal__comparison">
            <div class="ae-confirm-modal__column">
              <h5>Antes</h5>
              <div data-role="confirm-before"></div>
            </div>
            <div class="ae-confirm-modal__column">
              <h5>Después</h5>
              <div data-role="confirm-after"></div>
            </div>
          </div>
          <div class="ae-confirm-modal__field">
            <label for="ae-confirm-reason">Motivo del ajuste</label>
            <textarea id="ae-confirm-reason" data-role="confirm-reason" rows="3" placeholder="Escribe el motivo del ajuste" required></textarea>
          </div>
          <div class="ae-confirm-modal__error" data-role="confirm-error"></div>
        </div>
        <div class="ae-confirm-modal__actions">
          <button type="button" class="ae-btn-inline ae-btn-inline-cancel" data-action="cancel-confirm">Cancelar</button>
          <button type="button" class="ae-btn-inline ae-btn-inline-save" data-action="submit-confirm">Confirmar cambios</button>
        </div>
      </div>
    `;

    modal.addEventListener("click", (event) => {
      const actionElement = event.target.closest("[data-action]");
      if (!actionElement) {
        return;
      }

      if (actionElement.dataset.action === "cancel-confirm") {
        closeConfirmModal();
        return;
      }

      if (actionElement.dataset.action === "submit-confirm") {
        submitMovementChanges();
      }
    });

    modal.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeConfirmModal();
      }
    });

    document.body.appendChild(modal);
    return modal;
  }

  function setConfirmModalError(message = "") {
    const modal = getConfirmModal();
    const errorElement = modal.querySelector('[data-role="confirm-error"]');
    if (errorElement) {
      errorElement.textContent = message;
    }
  }

  function buildConfirmRowsMarkup(rows) {
    return rows
      .map(
        (row) => `
          <div class="ae-confirm-modal__compare-row">
            <span>${escapeHtml(row.label)}</span>
            <strong>${escapeHtml(row.value)}</strong>
          </div>
        `,
      )
      .join("");
  }

  function openConfirmModal(config, originalRow, draftRow) {
    const modal = getConfirmModal();
    const { changes, beforeRows, afterRows } = buildChangesForMovement(originalRow, draftRow);

    if (!Object.keys(changes).length) {
      setStatus(config.prefix, "No se detectaron cambios para guardar", true);
      return;
    }

    confirmState.config = config;
    confirmState.movementType = draftRow.movement_type;
    confirmState.recordId = draftRow.record_id;
    confirmState.changes = changes;
    confirmState.beforeRows = beforeRows;
    confirmState.afterRows = afterRows;

    modal.querySelector('[data-role="confirm-type"]').textContent =
      draftRow.movement_label || draftRow.movement_type;
    modal.querySelector('[data-role="confirm-folio"]').textContent = draftRow.folio || "-";
    modal.querySelector('[data-role="confirm-part"]').textContent = draftRow.part_number || "-";
    modal.querySelector('[data-role="confirm-before"]').innerHTML =
      buildConfirmRowsMarkup(beforeRows);
    modal.querySelector('[data-role="confirm-after"]').innerHTML =
      buildConfirmRowsMarkup(afterRows);
    modal.querySelector('[data-role="confirm-reason"]').value = "";
    setConfirmModalError("");
    modal.classList.add("is-open");

    const reasonField = modal.querySelector('[data-role="confirm-reason"]');
    reasonField?.focus();
  }

  function closeConfirmModal() {
    const modal = document.getElementById("ae-movement-confirm-modal");
    modal?.classList.remove("is-open");
    setConfirmModalError("");
  }

  async function submitMovementChanges() {
    const modal = document.getElementById("ae-movement-confirm-modal");
    const { config, movementType, recordId, changes } = confirmState;
    if (!modal || !config || !movementType || !recordId || !changes) {
      return;
    }

    const reasonField = modal.querySelector('[data-role="confirm-reason"]');
    const confirmButton = modal.querySelector('[data-action="submit-confirm"]');
    const notes = reasonField?.value?.trim() || "";

    if (!notes) {
      setConfirmModalError("El motivo del ajuste es obligatorio.");
      reasonField?.focus();
      return;
    }

    try {
      setConfirmModalError("");
      confirmButton.disabled = true;
      confirmButton.textContent = "Guardando...";

      const response = await fetch(
        `/api/almacen-embarques/movimientos/${encodeURIComponent(movementType)}/${encodeURIComponent(
          recordId,
        )}`,
        {
          method: "PATCH",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            changes,
            notes,
          }),
        },
      );

      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
      }

      closeConfirmModal();
      cancelMovementEdit();
      setStatus(config.prefix, payload.message || "Movimiento actualizado correctamente");
      await loadModule(config);
    } catch (error) {
      setConfirmModalError(error.message || "No fue posible guardar el ajuste.");
    } finally {
      confirmButton.disabled = false;
      confirmButton.textContent = "Confirmar cambios";
    }
  }

  function bindMovementTable(config) {
    const { tableBody } = getElements(config.prefix);
    if (!tableBody || tableBody.dataset.editBound === "true") {
      return;
    }

    tableBody.addEventListener("click", (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) {
        return;
      }

      const recordKey = button.dataset.recordKey;
      if (button.dataset.action === "edit-movement" && recordKey) {
        startMovementEdit(recordKey);
      }

      if (button.dataset.action === "cancel-edit-movement") {
        cancelMovementEdit();
      }

      if (button.dataset.action === "save-movement") {
        if (!movementModuleState.originalRow || !movementModuleState.draftRow) {
          return;
        }
        openConfirmModal(config, movementModuleState.originalRow, movementModuleState.draftRow);
      }
    });

    tableBody.addEventListener("input", (event) => {
      const input = event.target.closest("[data-field-name]");
      if (!input) {
        return;
      }
      updateDraftFromRowInput(input);
    });

    tableBody.addEventListener("keydown", (event) => {
      const input = event.target.closest("[data-field-name]");
      if (!input) {
        return;
      }

      if (input.dataset.fieldType === "integer") {
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

        if (
          !event.ctrlKey &&
          !event.metaKey &&
          !event.altKey &&
          !allowedKeys.has(event.key) &&
          !/^\d$/.test(event.key)
        ) {
          event.preventDefault();
        }
      }

      if (event.key === "Enter") {
        event.preventDefault();
        if (movementModuleState.originalRow && movementModuleState.draftRow) {
          openConfirmModal(config, movementModuleState.originalRow, movementModuleState.draftRow);
        }
      }

      if (event.key === "Escape") {
        event.preventDefault();
        cancelMovementEdit();
      }
    });

    tableBody.dataset.editBound = "true";
  }

  function bindModule(config) {
    const elements = getElements(config.prefix);
    if (!elements.tableBody) {
      return;
    }

    const moduleRoot = getModuleRoot(config.prefix);
    const headerWrap = moduleRoot?.querySelector(".ae-table-head");
    const bodyWrap = moduleRoot?.querySelector(".ae-table-body-wrap");
    if (headerWrap && bodyWrap && bodyWrap.dataset.scrollBound !== "true") {
      bodyWrap.addEventListener("scroll", () => {
        headerWrap.scrollLeft = bodyWrap.scrollLeft;
      });
      bodyWrap.dataset.scrollBound = "true";
    }

    if (moduleRoot && moduleRoot.dataset.resizeBound !== "true") {
      const updateHeight = () => {
        syncScrollableHeight(moduleRoot);
        syncTableWidths(moduleRoot);
      };
      window.addEventListener("resize", updateHeight);
      requestAnimationFrame(() => requestAnimationFrame(updateHeight));
      moduleRoot.dataset.resizeBound = "true";
    }

    elements.searchBtn?.addEventListener("click", () => {
      cancelMovementEdit();
      loadModule(config);
    });
    elements.exportBtn?.addEventListener("click", () => exportModule(config));
    elements.clearBtn?.addEventListener("click", () => {
      if (elements.searchInput) elements.searchInput.value = "";
      if (elements.typeSelect) elements.typeSelect.value = "";
      if (elements.dateFrom) elements.dateFrom.value = "";
      if (elements.dateTo) elements.dateTo.value = "";
      cancelMovementEdit();
      loadModule(config);
    });
    elements.searchInput?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        cancelMovementEdit();
        loadModule(config);
      }
    });

    if (config.prefix === "almacen-embarques-movements") {
      bindMovementTable(config);
    }
  }

  function initializeModule(config) {
    ensureModuleStyles();
    bindModule(config);
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        const moduleRoot = getModuleRoot(config.prefix);
        syncScrollableHeight(moduleRoot);
        syncTableWidths(moduleRoot);
      }),
    );
    loadModule(config);
  }

  window.inicializarAlmacenEmbarquesMovimientosAjax = function () {
    initializeModule({
      prefix: "almacen-embarques-movements",
      apiUrl: "/api/almacen-embarques/movimientos",
      exportUrl: "/api/almacen-embarques/movimientos/export",
      colspan: 12,
      emptyMessage: "No hay movimientos disponibles para los filtros actuales.",
      renderer: renderMovementsRows,
    });
  };

  window.inicializarAlmacenEmbarquesInventarioGeneralAjax = function () {
    initializeModule({
      prefix: "almacen-embarques-inventory",
      apiUrl: "/api/almacen-embarques/inventario-general",
      exportUrl: "/api/almacen-embarques/inventario-general/export",
      colspan: 9,
      emptyMessage: "No hay registros de inventario para los filtros actuales.",
      renderer: renderInventoryRows,
      onAfterLoad(payload) {
        const summary = payload?.summary || {};
        if (summary.has_closure && summary.latest_period_start) {
          setStatus(
            "almacen-embarques-inventory",
            `Movimientos acumulados desde el cierre ${summary.latest_period_start}`,
          );
        } else {
          setStatus(
            "almacen-embarques-inventory",
            "Sin cierre previo: mostrando acumulado total del historial",
          );
        }
      },
    });
  };
})();
