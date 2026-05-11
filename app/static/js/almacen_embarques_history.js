(function () {
  const STYLESHEET_ID = "almacen-embarques-history-css";
  const ASSET_VERSION = "20260507b";
  const STYLESHEET_HREF = `/static/css/almacen_embarques_history.css?v=${ASSET_VERSION}`;
  const adjustmentState = {};
  const returnPrintState = {
    exitRows: [],
    selectedKeys: new Set(),
    previewRows: [],
  };

  function ensureModuleStyles() {
    const currentLink = document.getElementById(STYLESHEET_ID);
    if (currentLink) {
      if (!currentLink.getAttribute("href")?.includes(ASSET_VERSION)) {
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

  function getNumericValue(value) {
    const numericValue = Number(value);
    return Number.isFinite(numericValue) ? numericValue : 0;
  }

  function sumQuantity(rows, accessor) {
    return rows.reduce((sum, row) => sum + getNumericValue(accessor(row)), 0);
  }

  function getQuantityTotalLabel(total) {
    const normalizedTotal = getNumericValue(total);
    const suffix = Math.abs(normalizedTotal) === 1 ? "pieza" : "piezas";
    return `${formatNumber(normalizedTotal)} ${suffix}`;
  }

  function getModuleQuantityTotal(config, rows) {
    const accessor = config.quantityTotalAccessor || ((row) => row.cantidad ?? row.quantity ?? 0);
    return sumQuantity(rows, accessor);
  }

  function buildBadge(text, variant) {
    return `<span class="history-badge history-badge--${variant}">${escapeHtml(text)}</span>`;
  }

  function buildDepartureCell(row) {
    if (row.departure_code) {
      return `
        <div class="ae-departure-view">
          ${escapeHtml(row.departure_code)}
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
      const bodyCols = [...(bodyTable.querySelectorAll("colgroup col") || [])];
      const headerCells = [...(headerTable.querySelectorAll("thead th") || [])];
      const labels = tableShell.__aeColumnLabels?.length
        ? tableShell.__aeColumnLabels
        : headerCells.map((cell) => cell.textContent || "");
      tableShell.__aeColumnLabels = labels;
      const currentWidths = bodyCols.map((col, index) =>
        getColWidthPx(
          col,
          headerCells[index]?.getBoundingClientRect().width || getColumnMinWidth(labels[index]),
          bodyWrap.clientWidth || tableShell.clientWidth || 1,
        ),
      );
      const appliedWidths = currentWidths.length
        ? applyColumnWidths(tableShell, currentWidths, {
            preferPriority: false,
            fillAvailable: tableShell.__aeCompactColumns !== true,
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

  function getReturnPrintColumnMinWidth(label) {
    const normalized = normalizeColumnLabel(label);
    if (normalized.includes("sel")) return 54;
    if (normalized.includes("folio")) return 220;
    if (normalized.includes("no. parte") || normalized.includes("no parte")) return 130;
    if (normalized.includes("fecha")) return 110;
    if (normalized.includes("hora")) return 90;
    if (normalized.includes("cantidad")) return 88;
    if (normalized.includes("tipo")) return 96;
    if (normalized.includes("usuario")) return 118;
    return getColumnMinWidth(label);
  }

  function getReturnPrintColumnDefaultWidth(label) {
    const normalized = normalizeColumnLabel(label);
    if (normalized.includes("sel")) return 54;
    if (normalized.includes("folio")) return 330;
    if (normalized.includes("no. parte") || normalized.includes("no parte")) return 150;
    if (normalized.includes("fecha")) return 112;
    if (normalized.includes("hora")) return 92;
    if (normalized.includes("cantidad")) return 92;
    if (normalized.includes("tipo")) return 108;
    if (normalized.includes("usuario")) return 130;
    return getReturnPrintColumnMinWidth(label);
  }

  function getReturnPrintTableAvailableWidth(table) {
    const wrap = table?.closest(".ae-return-print-table-wrap");
    return Math.max(1, Math.floor(wrap?.clientWidth || table?.clientWidth || 0));
  }

  function getReturnPrintResizeKey(labels) {
    return `ae-column-widths:return-print-selection:${labels.map(normalizeColumnLabel).join("|")}`;
  }

  function normalizeReturnPrintColumnWidths(widths, labels, availableWidth, fillAvailable = true) {
    const targetWidth = Math.max(1, Math.floor(availableWidth));
    const minWidths = labels.map(getReturnPrintColumnMinWidth);
    const minTotal = minWidths.reduce((sum, width) => sum + width, 0);
    if (minTotal > targetWidth) {
      const ratio = targetWidth / minTotal;
      const scaled = minWidths.map((width) => Math.max(1, Math.floor(width * ratio)));
      return settleWidthTotal(
        scaled,
        scaled.map(() => 1),
        labels,
        targetWidth,
        false,
        true,
      );
    }

    const normalized = widths.map((width, index) =>
      Math.max(minWidths[index], Math.round(Number(width) || minWidths[index])),
    );
    let total = normalized.reduce((sum, width) => sum + width, 0);

    if (total > targetWidth) {
      const folioIndex = labels.findIndex((label) => normalizeColumnLabel(label).includes("folio"));
      const nonFolioIndexes = normalized
        .map((_, index) => index)
        .filter((index) => index !== folioIndex);
      reduceWidthsEvenly(normalized, minWidths, total - targetWidth, nonFolioIndexes);
      total = normalized.reduce((sum, width) => sum + width, 0);
      if (total > targetWidth) {
        reduceWidthsEvenly(
          normalized,
          minWidths,
          total - targetWidth,
          normalized.map((_, index) => index),
        );
      }
    }

    total = normalized.reduce((sum, width) => sum + width, 0);
    if (fillAvailable && total < targetWidth) {
      const folioIndex = labels.findIndex((label) => normalizeColumnLabel(label).includes("folio"));
      normalized[folioIndex >= 0 ? folioIndex : normalized.length - 1] += targetWidth - total;
    }

    return normalized;
  }

  function getReturnPrintCurrentColumnWidths(table, labels) {
    const cols = [...(table?.querySelectorAll("colgroup col") || [])];
    const fallbackWidth = getReturnPrintTableAvailableWidth(table) / Math.max(1, labels.length);
    return labels.map((label, index) =>
      getColWidthPx(cols[index], getReturnPrintColumnDefaultWidth(label) || fallbackWidth, getReturnPrintTableAvailableWidth(table)),
    );
  }

  function applyReturnPrintColumnWidths(table, widths, options = {}) {
    const cols = [...(table?.querySelectorAll("colgroup col") || [])];
    const headerCells = [...(table?.querySelectorAll("thead th") || [])];
    if (!table || !cols.length || !headerCells.length) {
      return [];
    }

    const labels = headerCells.map((cell) => cell.textContent || "");
    const finalWidths = normalizeReturnPrintColumnWidths(
      widths,
      labels,
      getReturnPrintTableAvailableWidth(table),
      options.fillAvailable !== false,
    );
    finalWidths.forEach((width, index) => {
      if (cols[index]) {
        cols[index].style.width = `${width}px`;
      }
    });

    const tableWidth = finalWidths.reduce((sum, width) => sum + width, 0);
    table.style.width = `${tableWidth}px`;
    table.style.minWidth = `${tableWidth}px`;

    if (options.persist) {
      try {
        localStorage.setItem(getReturnPrintResizeKey(labels), JSON.stringify(finalWidths));
      } catch (error) {
        // localStorage puede estar bloqueado por políticas del navegador.
      }
    }

    return finalWidths;
  }

  function resizeReturnPrintColumnWithinAvailable(widths, labels, columnIndex, delta, availableWidth) {
    const targetWidth = Math.max(1, Math.floor(availableWidth));
    const startWidths = normalizeReturnPrintColumnWidths(widths, labels, targetWidth, false);
    const minWidths = labels.map(getReturnPrintColumnMinWidth);
    const minTotal = minWidths.reduce((sum, width) => sum + width, 0);
    if (minTotal > targetWidth) {
      return normalizeReturnPrintColumnWidths(startWidths, labels, targetWidth, true);
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

    return normalizeReturnPrintColumnWidths(nextWidths, labels, targetWidth, false);
  }

  function getReturnPrintInitialColumnWidths(table) {
    const headerCells = [...(table?.querySelectorAll("thead th") || [])];
    const labels = headerCells.map((cell) => cell.textContent || "");
    try {
      const saved = JSON.parse(localStorage.getItem(getReturnPrintResizeKey(labels)) || "null");
      if (
        Array.isArray(saved) &&
        saved.length === labels.length &&
        saved.every((width) => Number.isFinite(Number(width)))
      ) {
        return normalizeReturnPrintColumnWidths(
          saved.map((width) => Math.round(Number(width))),
          labels,
          getReturnPrintTableAvailableWidth(table),
        );
      }
    } catch (error) {
      // Se ignoran preferencias corruptas.
    }

    return normalizeReturnPrintColumnWidths(
      labels.map(getReturnPrintColumnDefaultWidth),
      labels,
      getReturnPrintTableAvailableWidth(table),
    );
  }

  function bindReturnPrintTableResizers() {
    const modal = document.getElementById("ae-return-print-modal");
    const table = modal?.querySelector(".ae-return-print-table");
    const headerCells = [...(table?.querySelectorAll("thead th") || [])];
    if (!table || !headerCells.length) {
      return;
    }

    if (table.dataset.columnWidthsReady !== "true") {
      applyReturnPrintColumnWidths(table, getReturnPrintInitialColumnWidths(table));
      table.dataset.columnWidthsReady = "true";
    }

    if (table.dataset.columnResizeBound === "true") {
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

        const labels = headerCells.map((cell) => cell.textContent || "");
        const startX = event.clientX;
        const startWidths = applyReturnPrintColumnWidths(
          table,
          getReturnPrintCurrentColumnWidths(table, labels),
        );
        const availableWidth = getReturnPrintTableAvailableWidth(table);

        document.body.classList.add("ae-column-resizing");
        handle.setPointerCapture?.(event.pointerId);

        const moveHandler = (moveEvent) => {
          const delta = moveEvent.clientX - startX;
          const nextWidths = resizeReturnPrintColumnWithinAvailable(
            startWidths,
            labels,
            columnIndex,
            delta,
            availableWidth,
          );
          applyReturnPrintColumnWidths(table, nextWidths, {
            persist: true,
            fillAvailable: false,
          });
        };

        const upHandler = () => {
          document.body.classList.remove("ae-column-resizing");
          document.removeEventListener("pointermove", moveHandler);
          document.removeEventListener("pointerup", upHandler);
          document.removeEventListener("pointercancel", upHandler);
        };

        document.addEventListener("pointermove", moveHandler);
        document.addEventListener("pointerup", upHandler);
        document.addEventListener("pointercancel", upHandler);
      });
    });

    table.dataset.columnResizeBound = "true";
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

  function getAdjustmentElements(prefix) {
    return {
      openBtn: document.getElementById(`${prefix}-adjustment-open-btn`),
      modal: document.getElementById(`${prefix}-adjustment-modal`),
      dateInput: document.getElementById(`${prefix}-adjustment-date`),
      reasonInput: document.getElementById(`${prefix}-adjustment-reason`),
      fileInput: document.getElementById(`${prefix}-adjustment-file`),
      manualDateInput: document.getElementById(`${prefix}-adjustment-manual-date`),
      manualPartInput: document.getElementById(`${prefix}-adjustment-manual-part`),
      manualQuantityInput: document.getElementById(`${prefix}-adjustment-manual-quantity`),
      manualReasonInput: document.getElementById(`${prefix}-adjustment-manual-reason`),
      manualSubmitBtn: document.getElementById(`${prefix}-adjustment-manual-submit-btn`),
      templateBtn: document.getElementById(`${prefix}-adjustment-template-btn`),
      previewBtn: document.getElementById(`${prefix}-adjustment-preview-btn`),
      confirmBtn: document.getElementById(`${prefix}-adjustment-confirm-btn`),
      resetBtn: document.getElementById(`${prefix}-adjustment-reset-btn`),
      statusLabel: document.getElementById(`${prefix}-adjustment-status`),
      errorsWrap: document.getElementById(`${prefix}-adjustment-errors`),
      previewWrap: document.getElementById(`${prefix}-adjustment-preview`),
      summaryLabel: document.getElementById(`${prefix}-adjustment-summary`),
      impactLabel: document.getElementById(`${prefix}-adjustment-impact`),
      previewBody: document.getElementById(`${prefix}-adjustment-tbody`),
    };
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
      searchInput: document.getElementById("almacen-embarques-returns-search"),
      dateFrom: document.getElementById("almacen-embarques-returns-date-from"),
      dateTo: document.getElementById("almacen-embarques-returns-date-to"),
      dateFilterBtn: document.getElementById("almacen-embarques-returns-filter-btn"),
      entryExportBtn: document.getElementById("almacen-embarques-return-in-export-btn"),
      entryBody: document.getElementById("almacen-embarques-return-in-tbody"),
      entryCount: document.getElementById("almacen-embarques-return-in-count"),
      entryStatus: document.getElementById("almacen-embarques-return-in-status"),
      exitExportBtn: document.getElementById("almacen-embarques-return-out-export-btn"),
      exitPrintBtn: document.getElementById("almacen-embarques-return-out-print-btn"),
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

  function getTodayDateValue() {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);
  }

  function setReturnDateInputsToToday(elements) {
    const today = getTodayDateValue();
    if (elements.dateFrom) {
      elements.dateFrom.value = today;
    }
    if (elements.dateTo) {
      elements.dateTo.value = today;
    }
  }

  function ensureReturnDefaultDates(elements) {
    const today = getTodayDateValue();
    if (elements.dateFrom && !elements.dateFrom.value) {
      elements.dateFrom.value = today;
    }
    if (elements.dateTo && !elements.dateTo.value) {
      elements.dateTo.value = today;
    }
  }

  function buildDateParams(dateFrom, dateTo) {
    const params = new URLSearchParams();
    if (dateFrom) {
      params.set("fecha_desde", dateFrom);
    }
    if (dateTo) {
      params.set("fecha_hasta", dateTo);
    }
    return params;
  }

  function buildReturnHistoryParams() {
    const elements = getReturnModuleElements();
    ensureReturnDefaultDates(elements);
    const params = buildDateParams(elements.dateFrom?.value || "", elements.dateTo?.value || "");
    const search = elements.searchInput?.value?.trim();
    if (search) {
      params.set("search", search);
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

  function setAdjustmentStatus(prefix, message, isError = false) {
    const { statusLabel } = getAdjustmentElements(prefix);
    if (!statusLabel) {
      return;
    }
    statusLabel.textContent = message || "";
    statusLabel.style.color = isError ? "#ff8f8f" : "#8fb8ff";
  }

  function renderAdjustmentErrors(prefix, errors = []) {
    const { errorsWrap } = getAdjustmentElements(prefix);
    if (!errorsWrap) {
      return;
    }
    const visibleErrors = errors.filter(Boolean);
    if (!visibleErrors.length) {
      errorsWrap.innerHTML = "";
      return;
    }
    errorsWrap.innerHTML = visibleErrors
      .slice(0, 8)
      .map((error) => `<span class="ae-adjustment-error-chip">${escapeHtml(error)}</span>`)
      .join("");
  }

  function setDefaultAdjustmentDate(prefix) {
    const { dateInput, manualDateInput } = getAdjustmentElements(prefix);
    const now = new Date();
    const localIso = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);
    if (dateInput && !dateInput.value) {
      dateInput.value = localIso;
    }
    if (manualDateInput && !manualDateInput.value) {
      manualDateInput.value = localIso;
    }
  }

  function openAdjustmentModal(config) {
    const elements = getAdjustmentElements(config.prefix);
    if (!elements.modal) {
      return;
    }
    elements.modal.classList.remove("is-hidden");
    elements.modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("ae-modal-open");
    setDefaultAdjustmentDate(config.prefix);
    requestAnimationFrame(() => {
      elements.manualPartInput?.focus();
    });
  }

  function closeAdjustmentModal(prefix) {
    const elements = getAdjustmentElements(prefix);
    if (!elements.modal) {
      return;
    }
    elements.modal.classList.add("is-hidden");
    elements.modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("ae-modal-open");
  }

  function renderAdjustmentPreview(prefix, preview) {
    const elements = getAdjustmentElements(prefix);
    if (!elements.previewWrap || !elements.previewBody) {
      return;
    }

    const rows = preview?.rows || [];
    const summary = preview?.summary || {};
    const closureImpact = preview?.closureImpact || {};

    if (!rows.length) {
      elements.previewWrap.classList.add("is-hidden");
      elements.previewBody.innerHTML = "";
      if (elements.summaryLabel) {
        elements.summaryLabel.textContent = "Sin preview validado";
      }
      if (elements.impactLabel) {
        elements.impactLabel.textContent = "";
      }
      return;
    }

    elements.previewWrap.classList.remove("is-hidden");
    if (elements.summaryLabel) {
      elements.summaryLabel.textContent = `${formatNumber(summary.totalRows)} registros · ${formatNumber(summary.totalQuantity)} piezas`;
    }
    if (elements.impactLabel) {
      elements.impactLabel.textContent = closureImpact.affected
        ? `${formatNumber(closureImpact.affectedRows)} cierres impactados`
        : "Sin impacto en cierres";
      elements.impactLabel.classList.toggle("is-warning", Boolean(closureImpact.affected));
    }
    elements.previewBody.innerHTML = rows
      .map(
        (row) => `
          <tr>
            <td><strong>${escapeHtml(row.part_number)}</strong></td>
            <td>${formatNumber(row.quantity)}</td>
            <td>${formatNumber(row.current_quantity)}</td>
            <td>${formatNumber(row.new_quantity)}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${row.closureImpactCount ? `${formatNumber(row.closureImpactCount)} cierre(s)` : "Sin cierre"}</td>
          </tr>
        `,
      )
      .join("");
  }

  async function resetAdjustment(config, cancelDraft = true) {
    const prefix = config.prefix;
    const elements = getAdjustmentElements(prefix);
    const currentBatchId = adjustmentState[prefix]?.batchId;

    if (cancelDraft && currentBatchId) {
      try {
        await fetch(`/api/almacen-embarques/${config.adjustmentModule}/ajustes/cancel`, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ batchId: currentBatchId }),
        });
      } catch (error) {
        console.warn("No fue posible cancelar el preview pendiente:", error);
      }
    }

    adjustmentState[prefix] = { batchId: null, preview: null };
    if (elements.reasonInput) elements.reasonInput.value = "";
    if (elements.fileInput) elements.fileInput.value = "";
    if (elements.manualPartInput) elements.manualPartInput.value = "";
    if (elements.manualQuantityInput) elements.manualQuantityInput.value = "";
    if (elements.manualReasonInput) elements.manualReasonInput.value = "";
    if (elements.confirmBtn) elements.confirmBtn.disabled = true;
    renderAdjustmentErrors(prefix, []);
    renderAdjustmentPreview(prefix, null);
    setDefaultAdjustmentDate(prefix);
    setAdjustmentStatus(prefix, "");
  }

  function downloadAdjustmentTemplate(config) {
    window.open(`/api/almacen-embarques/${config.adjustmentModule}/ajustes/template`, "_blank");
  }

  async function submitManualAdjustment(config) {
    const prefix = config.prefix;
    const elements = getAdjustmentElements(prefix);
    const movementAt = elements.manualDateInput?.value || "";
    const partNumber = elements.manualPartInput?.value?.trim() || "";
    const quantity = Number(elements.manualQuantityInput?.value || 0);
    const reason = elements.manualReasonInput?.value?.trim() || "";

    renderAdjustmentErrors(prefix, []);
    if (!movementAt) {
      setAdjustmentStatus(prefix, "Captura la fecha del movimiento", true);
      elements.manualDateInput?.focus();
      return;
    }
    if (!partNumber) {
      setAdjustmentStatus(prefix, "Captura el número de parte", true);
      elements.manualPartInput?.focus();
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setAdjustmentStatus(prefix, "Captura una cantidad mayor a cero", true);
      elements.manualQuantityInput?.focus();
      return;
    }
    if (!reason) {
      setAdjustmentStatus(prefix, "Captura el motivo del registro", true);
      elements.manualReasonInput?.focus();
      return;
    }

    const originalText = elements.manualSubmitBtn?.textContent;
    if (elements.manualSubmitBtn) {
      elements.manualSubmitBtn.disabled = true;
      elements.manualSubmitBtn.textContent = "Registrando...";
    }
    setAdjustmentStatus(prefix, "Registrando movimiento...");

    try {
      const response = await fetch(`/api/almacen-embarques/${config.adjustmentModule}/ajustes/manual`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          movementAt,
          partNumber,
          quantity,
          reason,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || `HTTP ${response.status}`);
      }

      setAdjustmentStatus(prefix, `${config.adjustmentLabel || "Movimiento"} registrado correctamente.`);
      if (elements.manualPartInput) elements.manualPartInput.value = "";
      if (elements.manualQuantityInput) elements.manualQuantityInput.value = "";
      if (elements.manualReasonInput) elements.manualReasonInput.value = "";
      await loadModule(config);
      elements.manualPartInput?.focus();
    } catch (error) {
      console.error("Error registrando ajuste manual:", error);
      renderAdjustmentErrors(prefix, [error.message || "No fue posible registrar el movimiento."]);
      setAdjustmentStatus(prefix, "Error registrando movimiento", true);
    } finally {
      if (elements.manualSubmitBtn) {
        elements.manualSubmitBtn.disabled = false;
        elements.manualSubmitBtn.textContent = originalText || "Registrar";
      }
    }
  }

  async function validateAdjustmentPreview(config) {
    const prefix = config.prefix;
    const elements = getAdjustmentElements(prefix);
    const file = elements.fileInput?.files?.[0];
    const reason = elements.reasonInput?.value?.trim() || "";
    const movementAt = elements.dateInput?.value || "";

    renderAdjustmentErrors(prefix, []);
    renderAdjustmentPreview(prefix, null);

    if (!movementAt) {
      setAdjustmentStatus(prefix, "Captura la fecha del movimiento", true);
      elements.dateInput?.focus();
      return;
    }
    if (!reason) {
      setAdjustmentStatus(prefix, "Captura el motivo del ajuste", true);
      elements.reasonInput?.focus();
      return;
    }
    if (!file) {
      setAdjustmentStatus(prefix, "Selecciona un archivo CSV o Excel", true);
      elements.fileInput?.focus();
      return;
    }

    const formData = new FormData();
    formData.append("adjustment_file", file);
    formData.append("reason", reason);
    formData.append("movement_at", movementAt);

    const originalText = elements.previewBtn?.textContent;
    if (elements.previewBtn) {
      elements.previewBtn.disabled = true;
      elements.previewBtn.textContent = "Validando...";
    }
    if (elements.confirmBtn) {
      elements.confirmBtn.disabled = true;
    }
    setAdjustmentStatus(prefix, "Validando archivo...");

    try {
      const response = await fetch(`/api/almacen-embarques/${config.adjustmentModule}/ajustes/preview`, {
        method: "POST",
        credentials: "same-origin",
        body: formData,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || `HTTP ${response.status}`);
      }
      if (!payload.valid) {
        renderAdjustmentErrors(prefix, payload.errors || ["El archivo contiene errores."]);
        setAdjustmentStatus(prefix, "Preview no válido", true);
        adjustmentState[prefix] = { batchId: null, preview: null };
        return;
      }

      adjustmentState[prefix] = {
        batchId: payload.batchId,
        batchCode: payload.batchCode,
        preview: payload.preview,
      };
      renderAdjustmentPreview(prefix, payload.preview);
      if (elements.confirmBtn) {
        elements.confirmBtn.disabled = false;
      }
      const impacted = payload.preview?.closureImpact?.affectedRows || 0;
      setAdjustmentStatus(
        prefix,
        impacted
          ? `Preview listo. Impacta ${formatNumber(impacted)} cierre(s).`
          : "Preview listo para confirmar.",
      );
    } catch (error) {
      console.error("Error validando ajuste por lote:", error);
      renderAdjustmentErrors(prefix, [error.message || "No fue posible validar el archivo."]);
      setAdjustmentStatus(prefix, "Error validando archivo", true);
    } finally {
      if (elements.previewBtn) {
        elements.previewBtn.disabled = false;
        elements.previewBtn.textContent = originalText || "Validar";
      }
    }
  }

  async function confirmAdjustment(config) {
    const prefix = config.prefix;
    const elements = getAdjustmentElements(prefix);
    const batchId = adjustmentState[prefix]?.batchId;
    if (!batchId) {
      setAdjustmentStatus(prefix, "Primero valida un preview", true);
      return;
    }

    const originalText = elements.confirmBtn?.textContent;
    if (elements.confirmBtn) {
      elements.confirmBtn.disabled = true;
      elements.confirmBtn.textContent = "Confirmando...";
    }
    setAdjustmentStatus(prefix, "Aplicando lote...");

    try {
      const response = await fetch(`/api/almacen-embarques/${config.adjustmentModule}/ajustes/confirm`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ batchId }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || `HTTP ${response.status}`);
      }

      setAdjustmentStatus(
        prefix,
        `${payload.insertedRows || 0} registros aplicados. ${payload.updatedClosureRows || 0} cierres recalculados.`,
      );
      adjustmentState[prefix] = { batchId: null, preview: null };
      if (elements.fileInput) elements.fileInput.value = "";
      if (elements.reasonInput) elements.reasonInput.value = "";
      renderAdjustmentErrors(prefix, []);
      renderAdjustmentPreview(prefix, null);
      await loadModule(config);
    } catch (error) {
      console.error("Error confirmando ajuste por lote:", error);
      renderAdjustmentErrors(prefix, [error.message || "No fue posible confirmar el lote."]);
      setAdjustmentStatus(prefix, "Error confirmando lote", true);
      if (elements.confirmBtn) {
        elements.confirmBtn.disabled = false;
      }
    } finally {
      if (elements.confirmBtn) {
        elements.confirmBtn.textContent = originalText || "Confirmar";
      }
    }
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
      countLabel.textContent = "0 piezas";
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

  function normalizeReturnType(reason) {
    const value = String(reason || "")
      .split("/")
      .map((part) => part.trim())
      .filter(Boolean)[0];
    return value || "Retorno";
  }

  function getReturnPrintRowKey(row) {
    return String(row?.id || row?.folio || `${row?.part_number || ""}-${row?.hora || ""}`);
  }

  function renderReturnsRows(rows) {
    return rows
      .map((row) => {
        const badgeText = normalizeReturnType(row.reason || "Sin tipo");
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
        return `
          <tr>
            <td>${escapeHtml(row.fecha)}</td>
            <td>${escapeHtml(row.hora)}</td>
            <td>${escapeHtml(row.folio)}</td>
            <td><strong>${escapeHtml(row.part_number)}</strong></td>
            <td>${formatNumber(quantity)}</td>
            <td>${escapeHtml(row.product_model || "-")}</td>
            <td>${escapeHtml(normalizeReturnType(row.reason || "Retorno"))}</td>
            <td>${escapeHtml(row.registered_by || "-")}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderReturnExitRows(rows) {
    return rows
      .map((row) => `
        <tr>
          <td>${escapeHtml(row.fecha)}</td>
          <td>${escapeHtml(row.hora)}</td>
          <td>${escapeHtml(row.folio)}</td>
          <td><strong>${escapeHtml(row.part_number)}</strong></td>
          <td>${formatNumber(row.loss_quantity)}</td>
          <td>${escapeHtml(row.product_model || "-")}</td>
          <td>${escapeHtml(normalizeReturnType(row.reason || "Salida retorno"))}</td>
          <td>${escapeHtml(row.registered_by || "-")}</td>
        </tr>
      `)
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

  function renderReturnHistoryTable(
    targetBody,
    targetCount,
    rows,
    emptyMessage,
    renderer,
    quantityAccessor,
  ) {
    if (!targetBody || !targetCount) {
      return;
    }

    if (!rows.length) {
      targetCount.textContent = "0 piezas";
      targetBody.innerHTML = `<tr><td colspan="8" class="ae-empty-cell">${escapeHtml(
        emptyMessage,
      )}</td></tr>`;
      return;
    }

    const accessor = quantityAccessor || ((row) => row.movement_quantity ?? row.return_quantity ?? 0);
    targetCount.textContent = getQuantityTotalLabel(sumQuantity(rows, accessor));
    targetBody.innerHTML = renderer(rows);
  }

  function getReturnPrintModal() {
    let modal = document.getElementById("ae-return-print-modal");
    if (modal) {
      return modal;
    }

    modal = document.createElement("div");
    modal.id = "ae-return-print-modal";
    modal.className = "ae-return-print-modal";
    modal.innerHTML = `
      <div class="ae-return-print-modal__backdrop" data-action="close-return-print"></div>
      <div class="ae-return-print-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="ae-return-print-title">
        <div class="ae-return-print-modal__header">
          <div>
            <h4 id="ae-return-print-title">Formato de salidas de retorno</h4>
            <p>Selecciona los registros que se incluirán en el formato imprimible.</p>
          </div>
          <button type="button" class="ae-return-print-modal__close" data-action="close-return-print" aria-label="Cerrar">
            &times;
          </button>
        </div>
        <div class="ae-return-print-modal__body">
          <div class="ae-return-print-step" data-step="selection">
            <div class="ae-return-print-filter-row">
              <div class="ae-filter-group">
                <label for="ae-return-print-date-from">Fecha desde</label>
                <input type="date" id="ae-return-print-date-from" data-role="return-print-date-from">
              </div>
              <div class="ae-filter-group">
                <label for="ae-return-print-date-to">Fecha hasta</label>
                <input type="date" id="ae-return-print-date-to" data-role="return-print-date-to">
              </div>
              <button type="button" class="ae-btn-primary" data-action="filter-return-print-date">
                Consultar
              </button>
              <button type="button" class="ae-btn-secondary" data-action="today-return-print-date">
                Hoy
              </button>
            </div>
            <div class="ae-return-print-toolbar">
              <label class="ae-return-print-check-all">
                <input type="checkbox" data-role="return-print-select-all">
                Seleccionar todo
              </label>
              <span data-role="return-print-selected-count">0 seleccionados</span>
            </div>
            <div class="ae-return-print-table-wrap">
              <table class="ae-history-table ae-return-print-table">
                <colgroup>
                  <col style="width: 54px;">
                  <col style="width: 112px;">
                  <col style="width: 92px;">
                  <col style="width: 330px;">
                  <col style="width: 150px;">
                  <col style="width: 92px;">
                  <col style="width: 108px;">
                  <col style="width: 130px;">
                </colgroup>
                <thead>
                  <tr>
                    <th>Sel.</th>
                    <th>Fecha</th>
                    <th>Hora</th>
                    <th>Folio</th>
                    <th>No. parte</th>
                    <th>Cantidad</th>
                    <th>Tipo</th>
                    <th>Usuario</th>
                  </tr>
                </thead>
                <tbody data-role="return-print-selection-body"></tbody>
              </table>
            </div>
            <div class="ae-return-print-error" data-role="return-print-error"></div>
          </div>
          <div class="ae-return-print-step is-hidden" data-step="preview">
            <div class="ae-return-print-preview-toolbar">
              <button type="button" class="ae-btn-secondary" data-action="back-return-print-selection">
                Volver a selección
              </button>
              <span data-role="return-print-preview-count"></span>
            </div>
            <div class="ae-return-print-preview-scroll">
              <div data-role="return-print-preview"></div>
            </div>
          </div>
        </div>
        <div class="ae-return-print-modal__actions">
          <button type="button" class="ae-btn-secondary" data-action="close-return-print">Cancelar</button>
          <button type="button" class="ae-btn-primary" data-action="preview-return-print">Generar previsualización</button>
          <button type="button" class="ae-btn-secondary is-hidden" data-action="download-return-print">Guardar</button>
          <button type="button" class="ae-btn-success is-hidden" data-action="print-return-print">Imprimir</button>
        </div>
      </div>
    `;

    modal.addEventListener("click", (event) => {
      const actionElement = event.target.closest("[data-action]");
      if (!actionElement) {
        return;
      }

      const action = actionElement.dataset.action;
      if (action === "close-return-print") {
        closeReturnPrintModal();
      } else if (action === "preview-return-print") {
        renderReturnPrintPreview();
      } else if (action === "back-return-print-selection") {
        setReturnPrintStep("selection");
      } else if (action === "filter-return-print-date") {
        loadReturnPrintRows();
      } else if (action === "today-return-print-date") {
        setReturnPrintDatesToToday();
        loadReturnPrintRows();
      } else if (action === "download-return-print") {
        downloadReturnPrintPreview(actionElement);
      } else if (action === "print-return-print") {
        printReturnPrintPreview();
      }
    });

    modal.addEventListener("change", (event) => {
      const target = event.target;
      if (target.matches('[data-role="return-print-select-all"]')) {
        const checked = target.checked;
        returnPrintState.selectedKeys.clear();
        if (checked) {
          returnPrintState.exitRows.forEach((row) => {
            returnPrintState.selectedKeys.add(getReturnPrintRowKey(row));
          });
        }
        modal
          .querySelectorAll('[data-role="return-print-row-checkbox"]')
          .forEach((checkbox) => {
            checkbox.checked = checked;
          });
        updateReturnPrintSelectionCount();
        return;
      }

      if (target.matches('[data-role="return-print-row-checkbox"]')) {
        const key = target.value;
        if (target.checked) {
          returnPrintState.selectedKeys.add(key);
        } else {
          returnPrintState.selectedKeys.delete(key);
        }
        syncReturnPrintSelectAll();
        updateReturnPrintSelectionCount();
      }
    });

    modal.addEventListener("keydown", (event) => {
      if (!event.target.matches('[data-role="return-print-date-from"], [data-role="return-print-date-to"]')) {
        return;
      }
      if (event.key === "Enter") {
        event.preventDefault();
        loadReturnPrintRows();
      }
    });

    document.body.appendChild(modal);
    return modal;
  }

  function getReturnPrintDateElements() {
    const modal = getReturnPrintModal();
    return {
      dateFrom: modal.querySelector('[data-role="return-print-date-from"]'),
      dateTo: modal.querySelector('[data-role="return-print-date-to"]'),
    };
  }

  function setReturnPrintDatesToToday() {
    setReturnDateInputsToToday(getReturnPrintDateElements());
  }

  function ensureReturnPrintDefaultDates() {
    ensureReturnDefaultDates(getReturnPrintDateElements());
  }

  function buildReturnPrintParams() {
    const { dateFrom, dateTo } = getReturnPrintDateElements();
    ensureReturnPrintDefaultDates();
    return buildDateParams(dateFrom?.value || "", dateTo?.value || "");
  }

  function renderReturnPrintLoadingRows(message = "Cargando salidas de retorno...") {
    const modal = getReturnPrintModal();
    const tbody = modal.querySelector('[data-role="return-print-selection-body"]');
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="8" class="ae-empty-cell">${escapeHtml(message)}</td></tr>`;
    }
    returnPrintState.exitRows = [];
    returnPrintState.selectedKeys.clear();
    returnPrintState.previewRows = [];
    syncReturnPrintSelectAll();
    updateReturnPrintSelectionCount();
  }

  async function loadReturnPrintRows() {
    const modal = getReturnPrintModal();
    renderReturnPrintLoadingRows();
    setReturnPrintError("");
    setReturnPrintStep("selection");

    try {
      const params = buildReturnPrintParams();
      const response = await fetch(`/api/almacen-embarques/retorno?${params.toString()}`, {
        credentials: "same-origin",
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const rows = await response.json();
      if (!Array.isArray(rows)) {
        throw new Error("Respuesta inválida del servidor");
      }

      returnPrintState.exitRows = rows
        .filter((row) => Number(row.loss_quantity || 0) > 0)
        .map((row) => ({
          ...row,
          movement_quantity: Number(row.loss_quantity || 0) || 0,
        }));
      returnPrintState.selectedKeys.clear();
      returnPrintState.previewRows = [];
      renderReturnPrintSelectionRows();
      syncReturnPrintSelectAll();
      updateReturnPrintSelectionCount();
    } catch (error) {
      console.error("Error cargando salidas de retorno para impresión:", error);
      returnPrintState.exitRows = [];
      returnPrintState.selectedKeys.clear();
      returnPrintState.previewRows = [];
      renderReturnPrintSelectionRows();
      setReturnPrintError(error.message || "No fue posible cargar salidas de retorno.");
      syncReturnPrintSelectAll();
      updateReturnPrintSelectionCount();
    }

    modal.querySelector('[data-role="return-print-date-from"]')?.focus();
  }

  function setReturnPrintStep(stepName) {
    const modal = getReturnPrintModal();
    const isPreview = stepName === "preview";
    modal.querySelector('[data-step="selection"]')?.classList.toggle("is-hidden", isPreview);
    modal.querySelector('[data-step="preview"]')?.classList.toggle("is-hidden", !isPreview);
    modal.querySelector('[data-action="preview-return-print"]')?.classList.toggle("is-hidden", isPreview);
    modal.querySelector('[data-action="download-return-print"]')?.classList.toggle("is-hidden", !isPreview);
    modal.querySelector('[data-action="print-return-print"]')?.classList.toggle("is-hidden", !isPreview);
  }

  function setReturnPrintError(message = "") {
    const errorLabel = getReturnPrintModal().querySelector('[data-role="return-print-error"]');
    if (errorLabel) {
      errorLabel.textContent = message;
    }
  }

  function syncReturnPrintSelectAll() {
    const modal = getReturnPrintModal();
    const selectAll = modal.querySelector('[data-role="return-print-select-all"]');
    if (!selectAll) {
      return;
    }
    const total = returnPrintState.exitRows.length;
    const selected = returnPrintState.selectedKeys.size;
    selectAll.checked = total > 0 && selected === total;
    selectAll.indeterminate = selected > 0 && selected < total;
  }

  function updateReturnPrintSelectionCount() {
    const modal = getReturnPrintModal();
    const countLabel = modal.querySelector('[data-role="return-print-selected-count"]');
    const selected = returnPrintState.selectedKeys.size;
    const total = returnPrintState.exitRows.length;
    if (countLabel) {
      countLabel.textContent = `${selected} de ${total} seleccionados`;
    }
  }

  function renderReturnPrintSelectionRows() {
    const modal = getReturnPrintModal();
    const tbody = modal.querySelector('[data-role="return-print-selection-body"]');
    if (!tbody) {
      return;
    }

    if (!returnPrintState.exitRows.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="ae-empty-cell">No hay salidas de retorno disponibles para imprimir.</td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = returnPrintState.exitRows
      .map((row) => {
        const key = getReturnPrintRowKey(row);
        return `
          <tr>
            <td>
              <input
                type="checkbox"
                data-role="return-print-row-checkbox"
                value="${escapeHtml(key)}"
                ${returnPrintState.selectedKeys.has(key) ? "checked" : ""}
              >
            </td>
            <td>${escapeHtml(row.fecha || "-")}</td>
            <td>${escapeHtml(row.hora || "-")}</td>
            <td>${escapeHtml(row.folio || "-")}</td>
            <td><strong>${escapeHtml(row.part_number || "-")}</strong></td>
            <td>${formatNumber(row.movement_quantity || row.loss_quantity)}</td>
            <td>${escapeHtml(normalizeReturnType(row.reason || "Salida retorno"))}</td>
            <td>${escapeHtml(row.registered_by || "-")}</td>
          </tr>
        `;
      })
      .join("");
  }

  function getSelectedReturnPrintRows() {
    return returnPrintState.exitRows.filter((row) =>
      returnPrintState.selectedKeys.has(getReturnPrintRowKey(row)),
    );
  }

  function sortReturnPrintRows(rows) {
    return [...rows].sort((left, right) => {
      const partComparison = String(left.part_number || "").localeCompare(
        String(right.part_number || ""),
        "es-MX",
        { numeric: true, sensitivity: "base" },
      );
      if (partComparison !== 0) {
        return partComparison;
      }

      const folioComparison = String(left.folio || "").localeCompare(
        String(right.folio || ""),
        "es-MX",
        { numeric: true, sensitivity: "base" },
      );
      if (folioComparison !== 0) {
        return folioComparison;
      }

      return String(left.hora || "").localeCompare(String(right.hora || ""));
    });
  }

  function buildReturnPrintDocumentBody(rows) {
    const generatedAt = new Date().toLocaleString("es-MX", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
    const totalQuantity = rows.reduce(
      (sum, row) => sum + (Number(row.movement_quantity || row.loss_quantity || 0) || 0),
      0,
    );

    return `
      <section class="ae-return-print-sheet">
        <header class="ae-return-print-sheet__header">
          <div>
            <span class="ae-return-print-sheet__eyebrow">Almacén de Embarques</span>
            <h1>Salida de retorno</h1>
          </div>
          <div class="ae-return-print-sheet__meta">
            <span>Generado</span>
            <strong>${escapeHtml(generatedAt)}</strong>
          </div>
        </header>
        <div class="ae-return-print-sheet__summary">
          <div>
            <span>Registros</span>
            <strong>${formatNumber(rows.length)}</strong>
          </div>
          <div>
            <span>Cantidad total</span>
            <strong>${formatNumber(totalQuantity)}</strong>
          </div>
        </div>
        <table class="ae-return-print-sheet__table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Hora</th>
              <th>Folio</th>
              <th>No. parte</th>
              <th>Cantidad</th>
              <th>Modelo</th>
              <th>Tipo</th>
              <th>Usuario</th>
            </tr>
          </thead>
          <tbody>
            ${rows
              .map(
                (row) => `
                  <tr>
                    <td>${escapeHtml(row.fecha || "-")}</td>
                    <td>${escapeHtml(row.hora || "-")}</td>
                    <td>${escapeHtml(row.folio || "-")}</td>
                    <td>${escapeHtml(row.part_number || "-")}</td>
                    <td>${formatNumber(row.movement_quantity || row.loss_quantity)}</td>
                    <td>${escapeHtml(row.product_model || "-")}</td>
                    <td>${escapeHtml(normalizeReturnType(row.reason || "Salida retorno"))}</td>
                    <td>${escapeHtml(row.registered_by || "-")}</td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
        <footer class="ae-return-print-sheet__footer">
          <div>Entrega</div>
          <div>Recibe</div>
          <div>Validación</div>
        </footer>
      </section>
    `;
  }

  function buildReturnPrintHtml(rows) {
    const body = buildReturnPrintDocumentBody(rows);
    return `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Formato salidas de retorno</title>
  <style>
    @page { size: letter landscape; margin: 25mm 10mm 10mm; }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: #eef1f5;
      color: #162033;
      font-family: Arial, sans-serif;
    }
    .ae-return-print-sheet {
      width: 11in;
      min-height: 8.5in;
      margin: 0 auto;
      padding: 0.72in 0.45in 0.45in;
      background: #fff;
    }
    .ae-return-print-sheet__header {
      display: flex;
      justify-content: space-between;
      gap: 24px;
      border-bottom: 3px solid #11213c;
      padding-bottom: 14px;
      margin-bottom: 14px;
    }
    .ae-return-print-sheet__eyebrow,
    .ae-return-print-sheet__meta span,
    .ae-return-print-sheet__summary span {
      color: #63708a;
      display: block;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    h1 {
      margin: 2px 0 0;
      color: #11213c;
      font-size: 28px;
      line-height: 1;
      text-transform: uppercase;
    }
    .ae-return-print-sheet__meta {
      text-align: right;
      white-space: nowrap;
    }
    .ae-return-print-sheet__meta strong {
      display: block;
      margin-top: 4px;
      font-size: 13px;
    }
    .ae-return-print-sheet__summary {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      margin-bottom: 14px;
    }
    .ae-return-print-sheet__summary div {
      border: 1px solid #d5dbe7;
      border-radius: 8px;
      padding: 10px 12px;
    }
    .ae-return-print-sheet__summary strong {
      display: block;
      margin-top: 3px;
      font-size: 18px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 10.5px;
    }
    th {
      background: #11213c;
      color: #fff;
      text-align: left;
      padding: 7px 6px;
      border: 1px solid #11213c;
    }
    td {
      padding: 7px 6px;
      border: 1px solid #d5dbe7;
      vertical-align: top;
    }
    tr:nth-child(even) td { background: #f7f9fc; }
    .ae-return-print-sheet__footer {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 18px;
      margin-top: 48px;
      color: #47536a;
      font-size: 12px;
      text-align: center;
    }
    .ae-return-print-sheet__footer div {
      border-top: 1px solid #162033;
      padding-top: 8px;
    }
    @media print {
      body { background: #fff; }
      .ae-return-print-sheet {
        width: auto;
        min-height: auto;
        margin: 0;
        padding: 0;
      }
    }
  </style>
</head>
<body>${body}</body>
</html>`;
  }

  function renderReturnPrintPreview() {
    const rows = sortReturnPrintRows(getSelectedReturnPrintRows());
    if (!rows.length) {
      setReturnPrintError("Selecciona al menos un registro para generar el formato.");
      return;
    }

    returnPrintState.previewRows = rows;
    const modal = getReturnPrintModal();
    const preview = modal.querySelector('[data-role="return-print-preview"]');
    const countLabel = modal.querySelector('[data-role="return-print-preview-count"]');
    if (preview) {
      preview.innerHTML = buildReturnPrintDocumentBody(rows);
    }
    if (countLabel) {
      countLabel.textContent = `${rows.length} ${rows.length === 1 ? "registro" : "registros"} en previsualización`;
    }
    setReturnPrintError("");
    setReturnPrintStep("preview");
  }

  function openReturnPrintModal() {
    const modal = getReturnPrintModal();
    returnPrintState.selectedKeys.clear();
    returnPrintState.previewRows = [];
    setReturnPrintError("");
    setReturnPrintDatesToToday();
    setReturnPrintStep("selection");
    modal.classList.add("is-open");
    requestAnimationFrame(bindReturnPrintTableResizers);
    loadReturnPrintRows();
  }

  function closeReturnPrintModal() {
    const modal = document.getElementById("ae-return-print-modal");
    if (!modal) {
      return;
    }
    modal.classList.remove("is-open");
    returnPrintState.exitRows = [];
    returnPrintState.selectedKeys.clear();
    returnPrintState.previewRows = [];
    setReturnPrintError("");
  }

  async function downloadReturnPrintPreview(button) {
    const rows = returnPrintState.previewRows;
    if (!rows.length) {
      renderReturnPrintPreview();
      return;
    }

    const originalText = button?.textContent;
    if (button) {
      button.disabled = true;
      button.textContent = "Generando PDF...";
    }

    try {
      const response = await fetch("/api/almacen-embarques/retorno/print-pdf", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/pdf",
        },
        body: JSON.stringify({ rows: sortReturnPrintRows(rows) }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || `HTTP ${response.status}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const timestamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "");
      const link = document.createElement("a");
      link.href = url;
      link.download = `formato_salidas_retorno_${timestamp}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setReturnPrintError("");
    } catch (error) {
      console.error("Error generando PDF de salidas de retorno:", error);
      setReturnPrintError(error.message || "No fue posible generar el PDF.");
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = originalText || "Guardar";
      }
    }
  }

  function printReturnPrintPreview() {
    const rows = returnPrintState.previewRows;
    if (!rows.length) {
      renderReturnPrintPreview();
      return;
    }

    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      setReturnPrintError("El navegador bloqueó la ventana de impresión.");
      return;
    }

    printWindow.document.open();
    printWindow.document.write(buildReturnPrintHtml(rows));
    printWindow.document.close();
    printWindow.focus();
    window.setTimeout(() => {
      try {
        printWindow.print();
      } catch (error) {
        console.warn("No fue posible abrir impresión automáticamente:", error);
      }
    }, 350);
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
      const params = buildReturnHistoryParams();
      const response = await fetch(`/api/almacen-embarques/retorno?${params.toString()}`, {
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
      const exitRows = rows
        .filter((row) => Number(row.loss_quantity || 0) > 0)
        .map((row) => ({
          ...row,
          movement_quantity: Number(row.loss_quantity || 0) || 0,
        }));
      returnPrintState.selectedKeys.clear();
      returnPrintState.previewRows = [];

      renderReturnHistoryTable(
        elements.entryBody,
        elements.entryCount,
        entryRows,
        "No hay entradas de retorno registradas.",
        renderReturnEntryRows,
        (row) => Math.max(0, Number(row.return_quantity || 0) - Number(row.loss_quantity || 0)),
      );
      renderReturnHistoryTable(
        elements.exitBody,
        elements.exitCount,
        exitRows,
        "No hay salidas de retorno registradas.",
        renderReturnExitRows,
        (row) => row.movement_quantity ?? row.loss_quantity ?? 0,
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
      if (elements.exitPrintBtn) {
        elements.exitPrintBtn.disabled = false;
        elements.exitPrintBtn.title = "Seleccionar salidas de retorno por fecha para imprimir";
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
      returnPrintState.exitRows = [];
      returnPrintState.selectedKeys.clear();
      returnPrintState.previewRows = [];
      if (elements.exitPrintBtn) {
        elements.exitPrintBtn.disabled = true;
        elements.exitPrintBtn.title = "No hay salidas de retorno disponibles para imprimir";
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
    const params = buildReturnHistoryParams();
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
        elements.countLabel.textContent = getQuantityTotalLabel(
          getModuleQuantityTotal(config, rows),
        );
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
      bindColumnResizers(moduleRoot);
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
    bindColumnResizers(moduleRoot);
    bindModuleResize(moduleRoot);
    ensureReturnDefaultDates(elements);

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

    if (elements.exitPrintBtn && elements.exitPrintBtn.dataset.bound !== "true") {
      elements.exitPrintBtn.addEventListener("click", openReturnPrintModal);
      elements.exitPrintBtn.dataset.bound = "true";
    }

    if (elements.dateFilterBtn && elements.dateFilterBtn.dataset.bound !== "true") {
      elements.dateFilterBtn.addEventListener("click", loadReturnsModule);
      elements.dateFilterBtn.dataset.bound = "true";
    }

    [elements.searchInput, elements.dateFrom, elements.dateTo].forEach((input) => {
      if (!input || input.dataset.bound === "true") {
        return;
      }
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          loadReturnsModule();
        }
      });
      input.dataset.bound = "true";
    });

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
    if (config.prefix === "almacen-embarques-returns") {
      bindReturnsModule(config);
      return;
    }

    const elements = getElements(config.prefix);
    if (!elements.tableBody) {
      return;
    }

    bindScrollableShells(moduleRoot);
    bindColumnResizers(moduleRoot);
    bindModuleResize(moduleRoot);
    setDefaultAdjustmentDate(config.prefix);

    const adjustmentElements = getAdjustmentElements(config.prefix);
    if (config.adjustmentModule && adjustmentElements.openBtn && adjustmentElements.openBtn.dataset.bound !== "true") {
      adjustmentElements.openBtn.addEventListener("click", () => openAdjustmentModal(config));
      adjustmentElements.openBtn.dataset.bound = "true";
    }
    if (config.adjustmentModule && adjustmentElements.modal && adjustmentElements.modal.dataset.closeBound !== "true") {
      adjustmentElements.modal.querySelectorAll("[data-adjustment-close]").forEach((button) => {
        button.addEventListener("click", () => closeAdjustmentModal(config.prefix));
      });
      adjustmentElements.modal.dataset.closeBound = "true";
    }
    if (config.adjustmentModule && adjustmentElements.manualQuantityInput && adjustmentElements.manualQuantityInput.dataset.numericBound !== "true") {
      adjustmentElements.manualQuantityInput.addEventListener("input", () => {
        adjustmentElements.manualQuantityInput.value = adjustmentElements.manualQuantityInput.value.replace(/\D+/g, "");
      });
      adjustmentElements.manualQuantityInput.dataset.numericBound = "true";
    }
    if (config.adjustmentModule && adjustmentElements.manualSubmitBtn && adjustmentElements.manualSubmitBtn.dataset.bound !== "true") {
      adjustmentElements.manualSubmitBtn.addEventListener("click", () => submitManualAdjustment(config));
      adjustmentElements.manualSubmitBtn.dataset.bound = "true";
    }
    [adjustmentElements.manualPartInput, adjustmentElements.manualQuantityInput, adjustmentElements.manualReasonInput].forEach((input) => {
      if (!config.adjustmentModule || !input || input.dataset.enterBound === "true") {
        return;
      }
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          submitManualAdjustment(config);
        }
      });
      input.dataset.enterBound = "true";
    });
    if (config.adjustmentModule && adjustmentElements.templateBtn && adjustmentElements.templateBtn.dataset.bound !== "true") {
      adjustmentElements.templateBtn.addEventListener("click", () => downloadAdjustmentTemplate(config));
      adjustmentElements.templateBtn.dataset.bound = "true";
    }
    if (config.adjustmentModule && adjustmentElements.previewBtn && adjustmentElements.previewBtn.dataset.bound !== "true") {
      adjustmentElements.previewBtn.addEventListener("click", () => validateAdjustmentPreview(config));
      adjustmentElements.previewBtn.dataset.bound = "true";
    }
    if (config.adjustmentModule && adjustmentElements.confirmBtn && adjustmentElements.confirmBtn.dataset.bound !== "true") {
      adjustmentElements.confirmBtn.addEventListener("click", () => confirmAdjustment(config));
      adjustmentElements.confirmBtn.dataset.bound = "true";
    }
    if (config.adjustmentModule && adjustmentElements.resetBtn && adjustmentElements.resetBtn.dataset.bound !== "true") {
      adjustmentElements.resetBtn.addEventListener("click", () => resetAdjustment(config, true));
      adjustmentElements.resetBtn.dataset.bound = "true";
    }

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
        bindColumnResizers(moduleRoot);
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
      adjustmentModule: "entradas",
      adjustmentLabel: "Entrada",
      colspan: 10,
      emptyMessage: "No hay entradas registradas para los filtros actuales.",
      renderer: renderEntriesRows,
      quantityTotalAccessor: (row) => row.cantidad,
    });
  };

  window.inicializarAlmacenEmbarquesSalidasAjax = function () {
    initializeModule({
      prefix: "almacen-embarques-exits",
      apiUrl: "/api/almacen-embarques/salidas",
      exportUrl: "/api/almacen-embarques/salidas/export",
      adjustmentModule: "salidas",
      adjustmentLabel: "Salida",
      colspan: 9,
      emptyMessage: "No hay salidas registradas para los filtros actuales.",
      renderer: renderExitsRows,
      quantityTotalAccessor: (row) => row.cantidad,
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
