(function () {
  const STYLESHEET_ID = "almacen-embarques-history-css";
  const STYLESHEET_HREF = "/static/css/almacen_embarques_history.css?v=20260430b";

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

  const deleteState = {
    config: null,
    movementType: "",
    recordId: null,
    row: null,
  };

  const inventoryClosureState = {
    batchId: null,
    valid: false,
    rows: [],
    summary: null,
    history: [],
    metadata: null,
    config: null,
  };

  function ensureModuleStyles() {
    const currentLink = document.getElementById(STYLESHEET_ID);
    if (currentLink) {
      if (!currentLink.getAttribute("href")?.includes("20260430b")) {
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

    if (prefix === "almacen-embarques-inventory") {
      return params;
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
    const shells = moduleRoot?.querySelectorAll(".ae-table-shell");
    if (!shells?.length) {
      return;
    }

    shells.forEach((shell) => {
      const headerWrap = shell.querySelector(":scope > .ae-table-head");
      const headerTable = shell.querySelector(".ae-history-table--head");
      const bodyWrap = shell.querySelector(":scope > .ae-table-body-wrap");
      const bodyTable = shell.querySelector(".ae-history-table--body");
      if (!headerWrap || !headerTable || !bodyWrap || !bodyTable) {
        return;
      }

      const scrollbarWidth = Math.max(0, bodyWrap.offsetWidth - bodyWrap.clientWidth);
      const bodyCols = [...(bodyTable.querySelectorAll("colgroup col") || [])];
      const headerCells = [...(headerTable.querySelectorAll("thead th") || [])];
      const labels = shell.__aeColumnLabels?.length
        ? shell.__aeColumnLabels
        : headerCells.map((cell) => cell.textContent || "");
      shell.__aeColumnLabels = labels;
      const currentWidths = bodyCols.map((col, index) =>
        getColWidthPx(
          col,
          headerCells[index]?.getBoundingClientRect().width || getColumnMinWidth(labels[index]),
          bodyWrap.clientWidth || shell.clientWidth || 1,
        ),
      );
      const appliedWidths = currentWidths.length
        ? applyColumnWidths(shell, currentWidths, {
            preferPriority: false,
            fillAvailable: shell.__aeCompactColumns !== true,
          })
        : [];
      const targetWidth = appliedWidths.length
        ? appliedWidths.reduce((sum, width) => sum + width, 0)
        : bodyWrap.clientWidth;

      headerWrap.style.paddingRight = `${scrollbarWidth}px`;
      headerTable.style.width = `${targetWidth}px`;
      headerTable.style.minWidth = `${targetWidth}px`;
      bodyTable.style.width = `${targetWidth}px`;
      bodyTable.style.minWidth = `${targetWidth}px`;
    });
  }

  function normalizeColumnLabel(label) {
    return String(label || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function getColumnMinWidth(label) {
    const normalized = normalizeColumnLabel(label);
    if (normalized.includes("accion")) return 148;
    if (normalized.includes("folio")) return 150;
    if (normalized.includes("departure")) return 140;
    if (normalized.includes("no. parte") || normalized.includes("no parte")) return 130;
    if (normalized.includes("modelo")) return 108;
    if (normalized.includes("fecha") || normalized.includes("hora")) return 78;
    if (normalized.includes("cantidad") || normalized.includes("cant.")) return 82;
    if (normalized.includes("cliente")) return 72;
    return 70;
  }

  function getPriorityColumnIndexes(labels) {
    return labels
      .map((label, index) => ({ label: normalizeColumnLabel(label), index }))
      .filter(
        ({ label }) =>
          label.includes("folio") ||
          label.includes("no. parte") ||
          label.includes("no parte") ||
          label.includes("departure"),
      )
      .map(({ index }) => index);
  }

  function getShellResizeKey(moduleRoot, tableShell, shellIndex, labels) {
    const moduleId = moduleRoot?.id || "almacen-embarques";
    const signature = labels.map(normalizeColumnLabel).join("|");
    return `ae-column-widths:${moduleId}:${shellIndex}:${signature}`;
  }

  function getColWidthPx(col, fallbackWidth, baseWidth) {
    const rawWidth = col?.style?.width?.trim() || "";
    if (rawWidth.endsWith("%")) {
      const percent = Number.parseFloat(rawWidth);
      if (Number.isFinite(percent)) {
        return Math.round((baseWidth * percent) / 100);
      }
    }
    if (rawWidth.endsWith("px")) {
      const px = Number.parseFloat(rawWidth);
      if (Number.isFinite(px)) {
        return Math.round(px);
      }
    }
    return Math.round(fallbackWidth);
  }

  function getAvailableTableWidth(tableShell) {
    const bodyWrap =
      tableShell.querySelector(":scope > .ae-table-body-wrap") ||
      tableShell.querySelector(".ae-table-body-wrap");
    return Math.max(
      1,
      Math.floor(bodyWrap?.clientWidth || tableShell.clientWidth || 0),
    );
  }

  function getDistributionIndexes(labels, preferPriority) {
    const priorityIndexes = preferPriority ? getPriorityColumnIndexes(labels) : [];
    return priorityIndexes.length
      ? priorityIndexes
      : labels.map((_, index) => index);
  }

  function growWidthsEvenly(widths, amount, indexes) {
    if (amount <= 0 || !indexes.length) {
      return widths;
    }

    let remaining = Math.round(amount);
    let cursor = 0;
    while (remaining > 0) {
      widths[indexes[cursor % indexes.length]] += 1;
      remaining -= 1;
      cursor += 1;
    }
    return widths;
  }

  function reduceWidthsEvenly(widths, minWidths, amount, indexes) {
    let remaining = Math.round(amount);
    let candidates = indexes.filter((index) => widths[index] > minWidths[index]);

    while (remaining > 0 && candidates.length) {
      let changed = false;
      candidates = candidates.filter((index) => {
        if (remaining <= 0) {
          return widths[index] > minWidths[index];
        }
        widths[index] -= 1;
        remaining -= 1;
        changed = true;
        return widths[index] > minWidths[index];
      });

      if (!changed) {
        break;
      }
    }

    return widths;
  }

  function settleWidthTotal(
    widths,
    minWidths,
    labels,
    targetWidth,
    preferPriority,
    fillAvailable,
  ) {
    const roundedWidths = widths.map((width) => Math.max(1, Math.round(width)));
    const indexes = getDistributionIndexes(labels, preferPriority);
    let total = roundedWidths.reduce((sum, width) => sum + width, 0);

    if (total < targetWidth && fillAvailable) {
      growWidthsEvenly(roundedWidths, targetWidth - total, indexes);
    } else if (total > targetWidth) {
      reduceWidthsEvenly(roundedWidths, minWidths, total - targetWidth, indexes);
    }

    total = roundedWidths.reduce((sum, width) => sum + width, 0);
    if (fillAvailable && total !== targetWidth && roundedWidths.length) {
      const lastIndex = roundedWidths.length - 1;
      roundedWidths[lastIndex] = Math.max(1, roundedWidths[lastIndex] + targetWidth - total);
    }

    return roundedWidths;
  }

  function normalizeWidthsToAvailable(widths, labels, availableWidth, options = {}) {
    if (!widths.length) {
      return [];
    }

    const targetWidth = Math.max(1, Math.floor(availableWidth));
    const minWidths = widths.map((_, index) => getColumnMinWidth(labels[index]));
    const minTotal = minWidths.reduce((sum, width) => sum + width, 0);
    const preferPriority = options.preferPriority !== false;
    const fillAvailable = options.fillAvailable !== false;

    if (minTotal > targetWidth) {
      const ratio = targetWidth / minTotal;
      const scaledWidths = minWidths.map((width) => Math.max(1, Math.floor(width * ratio)));
      return settleWidthTotal(
        scaledWidths,
        scaledWidths.map(() => 1),
        labels,
        targetWidth,
        false,
        true,
      );
    }

    const normalized = widths.map((width, index) =>
      Math.max(minWidths[index], Math.round(Number(width) || minWidths[index])),
    );
    const total = normalized.reduce((sum, width) => sum + width, 0);

    if (total > targetWidth) {
      reduceWidthsEvenly(
        normalized,
        minWidths,
        total - targetWidth,
        normalized.map((_, index) => index),
      );
    } else if (total < targetWidth && fillAvailable) {
      growWidthsEvenly(
        normalized,
        targetWidth - total,
        getDistributionIndexes(labels, preferPriority),
      );
    }

    return settleWidthTotal(
      normalized,
      minWidths,
      labels,
      targetWidth,
      preferPriority,
      fillAvailable,
    );
  }

  function resizeColumnWithinAvailable(widths, labels, columnIndex, delta, availableWidth) {
    const targetWidth = Math.max(1, Math.floor(availableWidth));
    const startWidths = normalizeWidthsToAvailable(widths, labels, targetWidth, {
      preferPriority: false,
      fillAvailable: false,
    });
    const minWidths = startWidths.map((_, index) => getColumnMinWidth(labels[index]));
    const minTotal = minWidths.reduce((sum, width) => sum + width, 0);
    if (minTotal > targetWidth) {
      return normalizeWidthsToAvailable(startWidths, labels, targetWidth, {
        preferPriority: false,
      });
    }

    const nextWidths = startWidths.slice();
    const otherIndexes = nextWidths
      .map((_, index) => index)
      .filter((index) => index !== columnIndex);
    const otherMinTotal = otherIndexes.reduce((sum, index) => sum + minWidths[index], 0);
    const startTotal = startWidths.reduce((sum, width) => sum + width, 0);
    const activeMin = minWidths[columnIndex];
    const activeMax = Math.max(activeMin, targetWidth - otherMinTotal);
    const activeWidth = Math.min(
      activeMax,
      Math.max(activeMin, Math.round(startWidths[columnIndex] + delta)),
    );
    const actualDelta = activeWidth - startWidths[columnIndex];

    nextWidths[columnIndex] = activeWidth;

    const overflow = startTotal + actualDelta - targetWidth;
    if (overflow > 0) {
      reduceWidthsEvenly(nextWidths, minWidths, overflow, otherIndexes);
    }

    return normalizeWidthsToAvailable(nextWidths, labels, targetWidth, {
      preferPriority: false,
      fillAvailable: false,
    });
  }

  function expandWidthsToAvailable(widths, labels, availableWidth) {
    return normalizeWidthsToAvailable(widths, labels, availableWidth, {
      preferPriority: true,
    });
  }

  function applyColumnWidths(tableShell, widths, options = {}) {
    const headerTable = tableShell.querySelector(".ae-history-table--head");
    const bodyTable = tableShell.querySelector(".ae-history-table--body");
    const headerCols = [...(headerTable?.querySelectorAll("colgroup col") || [])];
    const bodyCols = [...(bodyTable?.querySelectorAll("colgroup col") || [])];
    const bodyWrap =
      tableShell.querySelector(":scope > .ae-table-body-wrap") ||
      tableShell.querySelector(".ae-table-body-wrap");
    if (!headerTable || !bodyTable || !headerCols.length || !bodyCols.length) {
      return widths;
    }

    const count = Math.min(headerCols.length, bodyCols.length, widths.length);
    const normalizedWidths = widths.slice(0, count).map((width, index) => {
      const label = tableShell.__aeColumnLabels?.[index] || "";
      return Math.max(getColumnMinWidth(label), Math.round(Number(width) || 0));
    });

    const availableWidth = getAvailableTableWidth(tableShell);
    const finalWidths = normalizeWidthsToAvailable(
      normalizedWidths,
      tableShell.__aeColumnLabels || [],
      availableWidth,
      {
        preferPriority: options.preferPriority !== false,
        fillAvailable: options.fillAvailable !== false,
      },
    );

    finalWidths.forEach((width, index) => {
      headerCols[index].style.width = `${width}px`;
      bodyCols[index].style.width = `${width}px`;
    });

    const tableWidth = finalWidths.reduce((sum, width) => sum + width, 0);
    headerTable.style.width = `${tableWidth}px`;
    headerTable.style.minWidth = `${tableWidth}px`;
    bodyTable.style.width = `${tableWidth}px`;
    bodyTable.style.minWidth = `${tableWidth}px`;

    if (options.persist && tableShell.__aeResizeStorageKey) {
      try {
        localStorage.setItem(tableShell.__aeResizeStorageKey, JSON.stringify(finalWidths));
      } catch (error) {
        // localStorage puede estar bloqueado por políticas del navegador.
      }
    }

    return finalWidths;
  }

  function getInitialColumnWidths(tableShell) {
    const headerTable = tableShell.querySelector(".ae-history-table--head");
    const bodyWrap =
      tableShell.querySelector(":scope > .ae-table-body-wrap") ||
      tableShell.querySelector(".ae-table-body-wrap");
    const headerCols = [...(headerTable?.querySelectorAll("colgroup col") || [])];
    const headerCells = [...(headerTable?.querySelectorAll("thead th") || [])];
    const labels = headerCells.map((cell) => cell.textContent || "");
    tableShell.__aeColumnLabels = labels;

    if (tableShell.__aeResizeStorageKey) {
      try {
        const saved = JSON.parse(localStorage.getItem(tableShell.__aeResizeStorageKey) || "null");
        if (
          Array.isArray(saved) &&
          saved.length === headerCols.length &&
          saved.every((width) => Number.isFinite(Number(width)))
        ) {
          return normalizeWidthsToAvailable(
            saved.map((width, index) =>
              Math.max(getColumnMinWidth(labels[index]), Math.round(Number(width))),
            ),
            labels,
            getAvailableTableWidth(tableShell),
            { preferPriority: false },
          );
        }
      } catch (error) {
        // Se ignoran preferencias corruptas.
      }
    }

    const availableWidth = getAvailableTableWidth(tableShell);
    const fallbackWidth = availableWidth / Math.max(1, headerCols.length);
    const widths = headerCols.map((col, index) =>
      Math.max(
        getColumnMinWidth(labels[index]),
        getColWidthPx(col, headerCells[index]?.getBoundingClientRect().width || fallbackWidth, availableWidth),
      ),
    );

    return expandWidthsToAvailable(widths, labels, availableWidth);
  }

  function getCurrentColumnWidths(tableShell) {
    const headerTable = tableShell.querySelector(".ae-history-table--head");
    const bodyTable = tableShell.querySelector(".ae-history-table--body");
    const bodyCols = [...(bodyTable?.querySelectorAll("colgroup col") || [])];
    const headerCells = [...(headerTable?.querySelectorAll("thead th") || [])];
    const labels = tableShell.__aeColumnLabels?.length
      ? tableShell.__aeColumnLabels
      : headerCells.map((cell) => cell.textContent || "");
    tableShell.__aeColumnLabels = labels;

    if (!bodyCols.length) {
      return getInitialColumnWidths(tableShell);
    }

    const availableWidth = getAvailableTableWidth(tableShell);
    return bodyCols.map((col, index) =>
      getColWidthPx(
        col,
        headerCells[index]?.getBoundingClientRect().width || getColumnMinWidth(labels[index]),
        availableWidth,
      ),
    );
  }

  function bindColumnResizers(moduleRoot) {
    const tableShells = moduleRoot?.querySelectorAll(".ae-table-shell");
    if (!tableShells?.length) {
      return;
    }

    tableShells.forEach((tableShell, shellIndex) => {
      const headerCells = [...tableShell.querySelectorAll(".ae-history-table--head thead th")];
      if (!headerCells.length) {
        return;
      }

      const labels = headerCells.map((cell) => cell.textContent || "");
      tableShell.__aeColumnLabels = labels;
      tableShell.__aeResizeStorageKey = getShellResizeKey(moduleRoot, tableShell, shellIndex, labels);

      if (tableShell.dataset.columnWidthsReady !== "true") {
        const initialWidths = getInitialColumnWidths(tableShell);
        applyColumnWidths(tableShell, initialWidths);
        tableShell.__aeCompactColumns = false;
        tableShell.dataset.columnWidthsReady = "true";
      }

      if (tableShell.dataset.columnResizeBound === "true") {
        return;
      }

      headerCells.forEach((headerCell, columnIndex) => {
        headerCell.classList.add("ae-resizable-th");
        if (!headerCell.querySelector(":scope > .ae-column-resizer")) {
          const handle = document.createElement("span");
          handle.className = "ae-column-resizer";
          handle.setAttribute("aria-hidden", "true");
          headerCell.appendChild(handle);
        }

        const handle = headerCell.querySelector(":scope > .ae-column-resizer");
        handle.addEventListener("pointerdown", (event) => {
          event.preventDefault();
          event.stopPropagation();

          const startX = event.clientX;
          const startWidths = applyColumnWidths(tableShell, getCurrentColumnWidths(tableShell), {
            preferPriority: false,
            fillAvailable: tableShell.__aeCompactColumns !== true,
          });
          const availableWidth = getAvailableTableWidth(tableShell);

          document.body.classList.add("ae-column-resizing");
          handle.setPointerCapture?.(event.pointerId);

          const moveHandler = (moveEvent) => {
            const delta = moveEvent.clientX - startX;
            const nextWidths = resizeColumnWithinAvailable(
              startWidths,
              labels,
              columnIndex,
              delta,
              availableWidth,
            );
            tableShell.__aeCompactColumns =
              nextWidths.reduce((sum, width) => sum + width, 0) < availableWidth;
            applyColumnWidths(tableShell, nextWidths, {
              persist: true,
              preferPriority: false,
              fillAvailable: false,
            });
            syncTableWidths(moduleRoot);
          };

          const upHandler = () => {
            document.body.classList.remove("ae-column-resizing");
            document.removeEventListener("pointermove", moveHandler);
            document.removeEventListener("pointerup", upHandler);
            document.removeEventListener("pointercancel", upHandler);
            syncTableWidths(moduleRoot);
          };

          document.addEventListener("pointermove", moveHandler);
          document.addEventListener("pointerup", upHandler);
          document.addEventListener("pointercancel", upHandler);
        });
      });

      tableShell.dataset.columnResizeBound = "true";
    });
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
    return `
      <tr data-record-key="${escapeHtml(getMovementRecordKey(row))}">
        <td>${escapeHtml(row.fecha)}</td>
        <td>${escapeHtml(row.hora)}</td>
        <td>${escapeHtml(row.movement_label || row.movement_type || "-")}</td>
        <td>${escapeHtml(row.folio)}</td>
        <td><strong>${escapeHtml(row.part_number)}</strong></td>
        <td>${formatNumber(getMovementQuantity(row))}</td>
        <td>${escapeHtml(row.product_model || "-")}</td>
        <td>${escapeHtml(row.customer || "-")}</td>
        <td>${escapeHtml(row.zone_code || "-")}</td>
        <td>${escapeHtml(getMovementLocationValue(row) || "-")}</td>
        <td>${escapeHtml(row.departure_code || "-")}</td>
        <td>
          <div class="ae-inline-actions">
            <button
              type="button"
              class="ae-btn-inline ae-btn-inline-edit"
              data-action="edit-movement"
              data-record-key="${escapeHtml(getMovementRecordKey(row))}"
            >
              Editar
            </button>
            <button
              type="button"
              class="ae-btn-inline ae-btn-inline-delete"
              data-action="delete-movement"
              data-record-key="${escapeHtml(getMovementRecordKey(row))}"
            >
              Eliminar
            </button>
          </div>
        </td>
      </tr>
    `;
  }

  function renderMovementEditableRow(row) {
    return `
      <tr class="ae-row-editing" data-record-key="${escapeHtml(getMovementRecordKey(row))}">
        <td class="ae-edit-cell">${getEditableInputMarkup("fecha", row)}</td>
        <td>${escapeHtml(row.hora)}</td>
        <td>${escapeHtml(row.movement_label || row.movement_type || "-")}</td>
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

  function getInventoryClosureElements() {
    return {
      stage: document.getElementById("almacen-embarques-inventory-stage"),
      openBtn: document.getElementById("almacen-embarques-inventory-open-closure-btn"),
      backBtn: document.getElementById("almacen-embarques-inventory-closure-back-btn"),
      statusLabel: document.getElementById("almacen-embarques-inventory-closure-status"),
      dateInput: document.getElementById("almacen-embarques-inventory-closure-date"),
      userInput: document.getElementById("almacen-embarques-inventory-closure-user"),
      monthInput: document.getElementById("almacen-embarques-inventory-closure-month"),
      fileInput: document.getElementById("almacen-embarques-inventory-closure-file"),
      templateBtn: document.getElementById("almacen-embarques-inventory-closure-template-btn"),
      resetBtn: document.getElementById("almacen-embarques-inventory-closure-reset-btn"),
      previewBtn: document.getElementById("almacen-embarques-inventory-closure-preview-btn"),
      confirmBtn: document.getElementById("almacen-embarques-inventory-closure-confirm-btn"),
      errorsWrap: document.getElementById("almacen-embarques-inventory-closure-errors"),
      donut: document.getElementById("almacen-embarques-inventory-closure-donut"),
      accuracyLabel: document.getElementById("almacen-embarques-inventory-closure-accuracy"),
      previewCount: document.getElementById("almacen-embarques-inventory-closure-preview-count"),
      previewTbody: document.getElementById("almacen-embarques-inventory-closure-preview-tbody"),
      historyCount: document.getElementById("almacen-embarques-inventory-closure-history-count"),
      historyTbody: document.getElementById("almacen-embarques-inventory-closure-history-tbody"),
    };
  }

  function sleep(ms) {
    return new Promise((resolve) => {
      window.setTimeout(resolve, ms);
    });
  }

  function setInventoryClosureStatus(message = "", isError = false) {
    const { statusLabel } = getInventoryClosureElements();
    if (!statusLabel) {
      return;
    }
    statusLabel.textContent = message;
    statusLabel.style.color = isError ? "#ff9a9a" : "#8fb8ff";
  }

  function setInventoryClosureView(isOpen) {
    const moduleRoot = getModuleRoot("almacen-embarques-inventory");
    if (!moduleRoot) {
      return;
    }
    moduleRoot.classList.toggle("is-closure-active", Boolean(isOpen));
  }

  function renderInventoryClosureErrors(errors = []) {
    const { errorsWrap } = getInventoryClosureElements();
    if (!errorsWrap) {
      return;
    }
    if (!errors.length) {
      errorsWrap.innerHTML = "";
      return;
    }

    errorsWrap.innerHTML = errors
      .map(
        (error) =>
          `<span class="ae-closure-error-chip">${escapeHtml(error)}</span>`,
      )
      .join("");
  }

  function renderInventoryClosurePreviewRows(rows) {
    return rows
      .map((row) => {
        const statusVariant =
          row.status === "igual"
            ? "success"
            : row.status === "diferencia"
              ? "warning"
              : "neutral";

        return `
          <tr>
            <td><strong>${escapeHtml(row.part_number || "-")}</strong></td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${formatNumber(row.system_quantity)}</td>
            <td>${row.csv_current_qty === null || row.csv_current_qty === undefined ? "-" : formatNumber(row.csv_current_qty)}</td>
            <td>${row.difference_quantity === null || row.difference_quantity === undefined ? "-" : formatNumber(row.difference_quantity)}</td>
            <td>${row.applied_initial_quantity === null || row.applied_initial_quantity === undefined ? "-" : formatNumber(row.applied_initial_quantity)}</td>
            <td>${buildBadge(row.status || "pendiente", statusVariant)}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderInventoryClosureHistoryRows(rows) {
    return rows
      .map((row) => {
        const statusVariant =
          row.status === "confirmed"
            ? "success"
            : row.status === "draft"
              ? "warning"
              : "neutral";

        return `
          <tr>
            <td>${escapeHtml(row.closure_label || "-")}</td>
            <td>${escapeHtml(row.closure_month || "-")}</td>
            <td>${escapeHtml(row.confirmed_at || row.closed_at || "-")}</td>
            <td>${escapeHtml(row.confirmed_by || row.created_by || "-")}</td>
            <td>${formatNumber(row.accuracy_pct)}%</td>
            <td class="ae-closure-history-hash">${escapeHtml((row.rows_hash || "-").slice(0, 12))}</td>
            <td>${buildBadge(row.status || "-", statusVariant)}</td>
            <td>
              <button
                type="button"
                class="ae-btn-inline ae-btn-inline-edit"
                data-action="view-closure-history"
                data-batch-id="${escapeHtml(row.id)}"
              >
                ${row.status === "draft" ? "Retomar" : "Ver"}
              </button>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function updateInventoryClosureSummary(summary = {}, rows = []) {
    const {
      donut,
      accuracyLabel,
      previewCount,
    } = getInventoryClosureElements();

    const accuracy = Number(summary.accuracyPct || 0);
    const boundedAccuracy = Math.max(0, Math.min(100, accuracy));
    const degrees = (boundedAccuracy / 100) * 360;

    if (donut) {
      donut.style.background = `conic-gradient(#27ae60 0deg, #27ae60 ${degrees}deg, rgba(255,255,255,0.08) ${degrees}deg)`;
    }
    if (accuracyLabel) accuracyLabel.textContent = `${formatNumber(boundedAccuracy)}%`;

    if (previewCount) {
      const rowsCount = rows.length || summary.totalRows || 0;
      previewCount.textContent = `${rowsCount} ${rowsCount === 1 ? "registro" : "registros"}`;
    }
  }

  function renderInventoryClosurePreview(payload) {
    const { previewTbody, confirmBtn, historyCount, historyTbody } = getInventoryClosureElements();
    const preview = payload.preview || { rows: [], summary: {} };
    const rows = preview.rows || [];

    inventoryClosureState.batchId = payload.batchId || null;
    inventoryClosureState.valid = Boolean(payload.valid);
    inventoryClosureState.rows = rows;
    inventoryClosureState.summary = preview.summary || {};
    inventoryClosureState.history = payload.history || inventoryClosureState.history || [];
    inventoryClosureState.metadata = payload.metadata || inventoryClosureState.metadata;

    if (previewTbody) {
      previewTbody.innerHTML = rows.length
        ? renderInventoryClosurePreviewRows(rows)
        : `<tr><td colspan="7" class="ae-empty-cell">Sin datos de preview.</td></tr>`;
    }

    updateInventoryClosureSummary(preview.summary || {}, rows);
    renderInventoryClosureErrors(payload.errors || []);

    if (confirmBtn) {
      confirmBtn.disabled = !payload.valid || !payload.batchId;
    }

    if (historyTbody) {
      historyTbody.innerHTML = inventoryClosureState.history.length
        ? renderInventoryClosureHistoryRows(inventoryClosureState.history)
        : `<tr><td colspan="8" class="ae-empty-cell">Sin cierres registrados.</td></tr>`;
    }
    if (historyCount) {
      const rowsCount = inventoryClosureState.history.length;
      historyCount.textContent = `${rowsCount} ${rowsCount === 1 ? "registro" : "registros"}`;
    }
  }

  function fillInventoryClosureMetadata(metadata = {}) {
    const { dateInput, userInput, monthInput } = getInventoryClosureElements();
    if (dateInput) dateInput.value = metadata.closureDate || "";
    if (userInput) userInput.value = metadata.closureUser || "";
    if (monthInput) monthInput.value = metadata.closureMonthLabel || "";
  }

  async function loadInventoryClosureBootstrap() {
    const elements = getInventoryClosureElements();
    if (!elements.previewTbody) {
      return;
    }

    elements.previewTbody.innerHTML =
      '<tr><td colspan="7" class="ae-empty-cell">Cargando baseline del cierre...</td></tr>';
    setInventoryClosureStatus("Cargando contexto del cierre...");

    const response = await fetch(
      "/api/almacen-embarques/inventario-general/cierre/bootstrap",
      { credentials: "same-origin" },
    );
    const payload = await response.json().catch(() => ({}));

    if (!response.ok || payload.success === false) {
      throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
    }

    fillInventoryClosureMetadata(payload.metadata || {});
    renderInventoryClosurePreview({
      ...payload,
      valid: false,
      batchId: null,
      errors: [],
    });
    setInventoryClosureStatus("Baseline cargado. Descarga la plantilla y valida el CSV.");
  }

  async function previewInventoryClosure() {
    const { fileInput, previewBtn } = getInventoryClosureElements();
    const selectedFile = fileInput?.files?.[0];
    if (!selectedFile) {
      renderInventoryClosureErrors(["Debes seleccionar un archivo CSV para validar."]);
      setInventoryClosureStatus("Archivo CSV requerido.", true);
      return;
    }

    const formData = new FormData();
    formData.append("closure_file", selectedFile);
    const minimumDelay = sleep(2000);

    try {
      previewBtn.disabled = true;
      previewBtn.classList.add("ae-btn-loading");
      previewBtn.textContent = "Validando...";
      setInventoryClosureStatus("Validando archivo CSV...");
      const response = await fetch(
        "/api/almacen-embarques/inventario-general/cierre/preview",
        {
          method: "POST",
          credentials: "same-origin",
          body: formData,
        },
      );
      const payload = await response.json().catch(() => ({}));
      await minimumDelay;
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
      }

      fillInventoryClosureMetadata(payload.metadata || {});
      renderInventoryClosurePreview(payload);
      if (payload.valid) {
        setInventoryClosureStatus("Preview validado. Ya puedes confirmar el cierre.");
      } else {
        setInventoryClosureStatus("El CSV contiene errores y no se puede confirmar.", true);
      }
    } catch (error) {
      await minimumDelay;
      renderInventoryClosureErrors([error.message || "No fue posible validar el CSV."]);
      setInventoryClosureStatus(error.message || "Error validando el CSV.", true);
    } finally {
      previewBtn.disabled = false;
      previewBtn.classList.remove("ae-btn-loading");
      previewBtn.textContent = "Validar preview";
    }
  }

  async function resetInventoryClosure() {
    const { fileInput, confirmBtn, previewBtn } = getInventoryClosureElements();

    const currentBatchId = inventoryClosureState.batchId;

    if (currentBatchId) {
      const response = await fetch(
        "/api/almacen-embarques/inventario-general/cierre/cancel",
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ batchId: currentBatchId }),
        },
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
      }
    }

    inventoryClosureState.batchId = null;
    inventoryClosureState.valid = false;
    inventoryClosureState.rows = [];
    inventoryClosureState.summary = {};

    if (fileInput) {
      fileInput.value = "";
    }

    renderInventoryClosureErrors([]);
    setInventoryClosureStatus("Reiniciando carga del cierre...");

    if (confirmBtn) {
      confirmBtn.disabled = true;
    }

    if (previewBtn) {
      previewBtn.disabled = false;
      previewBtn.classList.remove("ae-btn-loading");
      previewBtn.textContent = "Validar preview";
    }

    await loadInventoryClosureBootstrap();
  }

  async function confirmInventoryClosure() {
    const { confirmBtn } = getInventoryClosureElements();
    if (!inventoryClosureState.batchId) {
      setInventoryClosureStatus("No hay un preview válido para confirmar.", true);
      return;
    }

    try {
      confirmBtn.disabled = true;
      confirmBtn.textContent = "Confirmando...";
      setInventoryClosureStatus("Confirmando cierre de inventario...");
      const response = await fetch(
        "/api/almacen-embarques/inventario-general/cierre/confirm",
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ batchId: inventoryClosureState.batchId }),
        },
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
      }

      inventoryClosureState.batchId = null;
      inventoryClosureState.valid = false;
      renderInventoryClosureErrors([]);
      setInventoryClosureStatus(payload.message || "Cierre confirmado correctamente.");

      if (payload.history) {
        inventoryClosureState.history = payload.history;
        renderInventoryClosurePreview({
          valid: false,
          batchId: null,
          preview: {
            rows: inventoryClosureState.rows,
            summary: inventoryClosureState.summary || {},
          },
          history: payload.history,
          metadata: inventoryClosureState.metadata || {},
          errors: [],
        });
      }

      if (inventoryClosureState.config) {
        await loadModule(inventoryClosureState.config);
      }
    } catch (error) {
      setInventoryClosureStatus(error.message || "No fue posible confirmar el cierre.", true);
    } finally {
      confirmBtn.disabled = !inventoryClosureState.valid || !inventoryClosureState.batchId;
      confirmBtn.textContent = "Confirmar cierre";
    }
  }

  async function loadInventoryClosureHistoryDetail(batchId) {
    try {
      setInventoryClosureStatus("Consultando detalle del cierre...");
      const response = await fetch(
        `/api/almacen-embarques/inventario-general/cierre/history/${encodeURIComponent(batchId)}`,
        { credentials: "same-origin" },
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
      }

      fillInventoryClosureMetadata({
        closureDate: payload.payload?.metadata?.closureDate || payload.batch?.closed_at || "",
        closureUser: payload.batch?.confirmed_by || payload.batch?.created_by || "",
        closureMonthLabel: payload.payload?.metadata?.closureMonthLabel || payload.batch?.closure_month || "",
      });
      renderInventoryClosurePreview({
        valid: payload.batch?.status === "draft",
        batchId: payload.batch?.status === "draft" ? payload.batch?.id : null,
        preview: {
          rows: payload.payload?.rows || [],
          summary: payload.payload?.summary || {},
        },
        history: inventoryClosureState.history,
        metadata: payload.payload?.metadata || inventoryClosureState.metadata || {},
        errors: [],
      });
      setInventoryClosureStatus(
        payload.batch?.status === "draft"
          ? `Preview pendiente retomado: ${payload.batch?.closure_label || "cierre"}.`
          : `Consultando ${payload.batch?.closure_label || "cierre"}.`,
      );
    } catch (error) {
      setInventoryClosureStatus(error.message || "No fue posible consultar el cierre.", true);
    }
  }

  function bindInventoryClosureModule(config) {
    const elements = getInventoryClosureElements();
    if (!elements.openBtn || elements.openBtn.dataset.bound === "true") {
      return;
    }

    inventoryClosureState.config = config;

    const closurePane = document.querySelector(".ae-inventory-pane--closure");
    const legacyToolbar = closurePane?.querySelector(".ae-closure-toolbar");
    const closureHeader = closurePane?.querySelector(".ae-closure-meta-card .ae-card-header");
    let titleGroup = closureHeader?.querySelector(".ae-card-header__title-group");

    if (closureHeader && elements.backBtn) {
      if (!titleGroup) {
        titleGroup = document.createElement("div");
        titleGroup.className = "ae-card-header__title-group";
        const title = closureHeader.querySelector("h3");
        if (title) {
          closureHeader.insertBefore(titleGroup, title);
          titleGroup.appendChild(title);
        } else {
          closureHeader.prepend(titleGroup);
        }
      }

      if (!titleGroup.contains(elements.backBtn)) {
        titleGroup.prepend(elements.backBtn);
      }
    }

    legacyToolbar?.remove();

    elements.openBtn.addEventListener("click", async () => {
      try {
        setInventoryClosureView(true);
        await loadInventoryClosureBootstrap();
      } catch (error) {
        renderInventoryClosureErrors([error.message || "No fue posible cargar el cierre."]);
        setInventoryClosureStatus(error.message || "No fue posible cargar el cierre.", true);
      }
    });

    elements.backBtn?.addEventListener("click", () => {
      setInventoryClosureView(false);
      setInventoryClosureStatus("");
    });

    elements.templateBtn?.addEventListener("click", () => {
      window.open(
        "/api/almacen-embarques/inventario-general/cierre/template",
        "_blank",
      );
    });

    elements.resetBtn?.addEventListener("click", async () => {
      try {
        await resetInventoryClosure();
      } catch (error) {
        renderInventoryClosureErrors([error.message || "No fue posible reiniciar la carga."]);
        setInventoryClosureStatus(error.message || "No fue posible reiniciar la carga.", true);
      }
    });

    elements.previewBtn?.addEventListener("click", previewInventoryClosure);
    elements.confirmBtn?.addEventListener("click", confirmInventoryClosure);

    elements.historyTbody?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-action='view-closure-history']");
      if (!button) {
        return;
      }
      loadInventoryClosureHistoryDetail(button.dataset.batchId);
    });

    elements.openBtn.dataset.bound = "true";
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

  function getDeleteModal() {
    let modal = document.getElementById("ae-movement-delete-modal");
    if (modal) {
      return modal;
    }

    modal = document.createElement("div");
    modal.id = "ae-movement-delete-modal";
    modal.className = "ae-confirm-modal";
    modal.innerHTML = `
      <div class="ae-confirm-modal__backdrop" data-action="cancel-delete"></div>
      <div class="ae-confirm-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="ae-delete-modal-title">
        <div class="ae-confirm-modal__header">
          <h4 id="ae-delete-modal-title">Confirmar eliminación</h4>
          <button type="button" class="ae-confirm-modal__close" data-action="cancel-delete" aria-label="Cerrar">&times;</button>
        </div>
        <div class="ae-confirm-modal__body">
          <div class="ae-confirm-modal__summary">
            <div><span>Tipo</span><strong data-role="delete-type"></strong></div>
            <div><span>Folio</span><strong data-role="delete-folio"></strong></div>
            <div><span>No. parte</span><strong data-role="delete-part"></strong></div>
          </div>
          <div class="ae-confirm-modal__warning">
            Esta acción eliminará el movimiento y recalculará el inventario del número de parte.
          </div>
          <div class="ae-confirm-modal__field">
            <label for="ae-delete-password">Contraseña actual</label>
            <input
              id="ae-delete-password"
              type="password"
              data-role="delete-password"
              placeholder="Confirma tu contraseña para eliminar"
              autocomplete="current-password"
              required
            >
          </div>
          <div class="ae-confirm-modal__field">
            <label for="ae-delete-notes">Comentario de eliminación</label>
            <textarea
              id="ae-delete-notes"
              data-role="delete-notes"
              rows="3"
              placeholder="Describe por qué se elimina el movimiento"
              required
            ></textarea>
          </div>
          <div class="ae-confirm-modal__error" data-role="delete-error"></div>
        </div>
        <div class="ae-confirm-modal__actions">
          <button type="button" class="ae-btn-inline ae-btn-inline-cancel" data-action="cancel-delete">Cancelar</button>
          <button type="button" class="ae-btn-inline ae-btn-inline-delete" data-action="submit-delete">Eliminar</button>
        </div>
      </div>
    `;

    modal.addEventListener("click", (event) => {
      const actionElement = event.target.closest("[data-action]");
      if (!actionElement) {
        return;
      }

      if (actionElement.dataset.action === "cancel-delete") {
        closeDeleteModal();
        return;
      }

      if (actionElement.dataset.action === "submit-delete") {
        submitMovementDelete();
      }
    });

    modal.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDeleteModal();
        return;
      }

      if (event.key === "Enter" && event.target?.dataset?.role === "delete-password") {
        event.preventDefault();
        submitMovementDelete();
      }
    });

    document.body.appendChild(modal);
    return modal;
  }

  function setDeleteModalError(message = "") {
    const modal = getDeleteModal();
    const errorElement = modal.querySelector('[data-role="delete-error"]');
    if (errorElement) {
      errorElement.textContent = message;
    }
  }

  function openDeleteModal(config, row) {
    if (!config || !row) {
      return;
    }

    const modal = getDeleteModal();
    deleteState.config = config;
    deleteState.movementType = row.movement_type;
    deleteState.recordId = row.record_id;
    deleteState.row = cloneMovementRow(row);

    modal.querySelector('[data-role="delete-type"]').textContent =
      row.movement_label || row.movement_type || "-";
    modal.querySelector('[data-role="delete-folio"]').textContent = row.folio || "-";
    modal.querySelector('[data-role="delete-part"]').textContent = row.part_number || "-";

    const passwordField = modal.querySelector('[data-role="delete-password"]');
    if (passwordField) {
      passwordField.value = "";
    }
    const notesField = modal.querySelector('[data-role="delete-notes"]');
    if (notesField) {
      notesField.value = "";
    }

    setDeleteModalError("");
    modal.classList.add("is-open");
    passwordField?.focus();
  }

  function closeDeleteModal() {
    const modal = document.getElementById("ae-movement-delete-modal");
    modal?.classList.remove("is-open");
    setDeleteModalError("");
  }

  async function submitMovementDelete() {
    const modal = document.getElementById("ae-movement-delete-modal");
    const { config, movementType, recordId } = deleteState;
    if (!modal || !config || !movementType || !recordId) {
      return;
    }

    const passwordField = modal.querySelector('[data-role="delete-password"]');
    const notesField = modal.querySelector('[data-role="delete-notes"]');
    const deleteButton = modal.querySelector('[data-action="submit-delete"]');
    const password = passwordField?.value?.trim() || "";
    const notes = notesField?.value?.trim() || "";

    if (!password) {
      setDeleteModalError("Debes confirmar tu contraseña actual.");
      passwordField?.focus();
      return;
    }

    if (!notes) {
      setDeleteModalError("El comentario de eliminación es obligatorio.");
      notesField?.focus();
      return;
    }

    try {
      setDeleteModalError("");
      deleteButton.disabled = true;
      deleteButton.textContent = "Eliminando...";

      const response = await fetch(
        `/api/almacen-embarques/movimientos/${encodeURIComponent(movementType)}/${encodeURIComponent(
          recordId,
        )}`,
        {
          method: "DELETE",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            password,
            notes,
          }),
        },
      );

      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || payload.message || `HTTP ${response.status}`);
      }

      closeDeleteModal();
      cancelMovementEdit();
      setStatus(config.prefix, payload.message || "Movimiento eliminado correctamente");
      await loadModule(config);
    } catch (error) {
      setDeleteModalError(error.message || "No fue posible eliminar el movimiento.");
    } finally {
      deleteButton.disabled = false;
      deleteButton.textContent = "Eliminar";
    }
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

      if (button.dataset.action === "delete-movement" && recordKey) {
        const currentRow = movementModuleState.rows.find(
          (row) => getMovementRecordKey(row) === recordKey,
        );
        if (currentRow) {
          openDeleteModal(config, currentRow);
        }
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
    const tableShells = moduleRoot?.querySelectorAll(".ae-table-shell") || [];
    tableShells.forEach((shell) => {
      const headerWrap = shell.querySelector(":scope > .ae-table-head");
      const bodyWrap = shell.querySelector(":scope > .ae-table-body-wrap");
      if (!headerWrap || !bodyWrap || bodyWrap.dataset.scrollBound === "true") {
        return;
      }
      bodyWrap.addEventListener("scroll", () => {
        headerWrap.scrollLeft = bodyWrap.scrollLeft;
      });
      bodyWrap.dataset.scrollBound = "true";
    });

    bindColumnResizers(moduleRoot);

    if (moduleRoot && moduleRoot.dataset.resizeBound !== "true") {
      const updateHeight = () => {
        bindColumnResizers(moduleRoot);
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
        bindColumnResizers(moduleRoot);
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
    const inventoryConfig = {
      prefix: "almacen-embarques-inventory",
      apiUrl: "/api/almacen-embarques/inventario-general",
      exportUrl: "/api/almacen-embarques/inventario-general/export",
      colspan: 9,
      emptyMessage: "No hay registros de inventario para los filtros actuales.",
      renderer: renderInventoryRows,
      onAfterLoad() {
        const currentSearch =
          getElements("almacen-embarques-inventory").searchInput?.value.trim() || "";
        if (currentSearch) {
          setStatus(
            "almacen-embarques-inventory",
            `Inventario actual filtrado por no. parte: ${currentSearch}`,
          );
          return;
        }

        setStatus(
          "almacen-embarques-inventory",
          "Inventario actual del catálogo completo",
        );
      },
    };

    bindInventoryClosureModule(inventoryConfig);
    initializeModule(inventoryConfig);
  };
})();
