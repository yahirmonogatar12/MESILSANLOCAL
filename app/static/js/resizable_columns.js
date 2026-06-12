// Columnas redimensionables para tablas largas del MES.
(function () {
  if (window.MesColumnResizer) {
    return;
  }

  function normalizeLabel(label) {
    return String(label || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function storageKey(prefix, labels) {
    return `${prefix || "mes-columns"}:${labels.map(normalizeLabel).join("|")}`;
  }

  function defaultMinWidth(label) {
    const normalized = normalizeLabel(label);
    if (normalized.includes("hash")) return 120;
    if (normalized.includes("part") || normalized.includes("assy")) return 130;
    if (normalized.includes("model") || normalized.includes("modelo")) return 130;
    if (normalized.includes("project") || normalized.includes("proyecto")) return 116;
    if (normalized.includes("usuario")) return 96;
    if (normalized.includes("fecha") || normalized.includes("hora")) return 92;
    if (normalized.includes("cantidad")) return 96;
    return 78;
  }

  function defaultColumnWidth(label, index) {
    const normalized = normalizeLabel(label);
    if (index === 0 || normalized.includes("part_no")) return 140;
    if (normalized.includes("sub_assy") || normalized.includes("assy")) return 155;
    if (normalized.includes("model") || normalized.includes("modelo")) return 150;
    if (normalized.includes("project") || normalized.includes("proyecto")) return 140;
    if (normalized.includes("main") || normalized.includes("display")) return 126;
    if (normalized.includes("cantidad")) return 118;
    if (normalized.includes("persona")) return 112;
    if (normalized.includes("usuario")) return 110;
    if (normalized.includes("hash")) return 150;
    return 92;
  }

  function ensureColgroup(table, count) {
    let colgroup = table.querySelector(":scope > colgroup");
    if (!colgroup) {
      colgroup = document.createElement("colgroup");
      table.insertBefore(colgroup, table.firstChild);
    }

    while (colgroup.children.length < count) {
      colgroup.appendChild(document.createElement("col"));
    }
    while (colgroup.children.length > count) {
      colgroup.removeChild(colgroup.lastElementChild);
    }

    return Array.from(colgroup.children);
  }

  function numberFromPx(value) {
    const parsed = Number.parseFloat(String(value || "").replace("px", ""));
    return Number.isFinite(parsed) ? Math.round(parsed) : null;
  }

  function getSavedWidths(key, count) {
    try {
      const saved = JSON.parse(localStorage.getItem(key) || "null");
      if (
        Array.isArray(saved) &&
        saved.length === count &&
        saved.every((width) => Number.isFinite(Number(width)))
      ) {
        return saved.map((width) => Math.round(Number(width)));
      }
    } catch (error) {
      // Preferencias corruptas o localStorage bloqueado: se usan anchos base.
    }
    return null;
  }

  function saveWidths(key, widths) {
    try {
      localStorage.setItem(key, JSON.stringify(widths.map((width) => Math.round(width))));
    } catch (error) {
      // localStorage puede estar bloqueado por politicas del navegador.
    }
  }

  function distributeExtra(widths, amount) {
    if (amount <= 0 || !widths.length) {
      return widths;
    }
    let remaining = Math.round(amount);
    let cursor = 0;
    while (remaining > 0) {
      widths[cursor % widths.length] += 1;
      remaining -= 1;
      cursor += 1;
    }
    return widths;
  }

  function normalizeWidths(widths, minWidths, containerWidth, fillContainer) {
    const next = widths.map((width, index) =>
      Math.max(minWidths[index], Math.round(Number(width) || minWidths[index])),
    );
    const total = next.reduce((sum, width) => sum + width, 0);
    if (fillContainer && containerWidth > total) {
      distributeExtra(next, containerWidth - total);
    }
    return next;
  }

  function applyWidths(table, cols, widths, minWidths, wrap, fillContainer) {
    const containerWidth = Math.floor(wrap?.clientWidth || table.parentElement?.clientWidth || 0);
    const finalWidths = normalizeWidths(widths, minWidths, containerWidth, fillContainer);
    const tableWidth = Math.max(
      containerWidth,
      finalWidths.reduce((sum, width) => sum + width, 0),
    );

    finalWidths.forEach((width, index) => {
      if (cols[index]) {
        cols[index].style.width = `${width}px`;
      }
    });

    table.style.width = `${tableWidth}px`;
    table.style.minWidth = `${tableWidth}px`;
    return finalWidths;
  }

  function setup(options) {
    const table =
      typeof options.table === "string" ? document.querySelector(options.table) : options.table;
    if (!table) {
      return;
    }

    const headers = Array.from(table.querySelectorAll(options.headerSelector || "thead th"));
    if (!headers.length) {
      return;
    }

    const wrap =
      (options.wrap && (typeof options.wrap === "string" ? document.querySelector(options.wrap) : options.wrap)) ||
      table.parentElement;
    const labels = headers.map((header) => header.getAttribute("title") || header.textContent || "");
    const minWidth = options.minWidth || defaultMinWidth;
    const baseWidth = options.defaultWidth || defaultColumnWidth;
    const minWidths = labels.map((label, index) => minWidth(label, index));
    const key = storageKey(options.storageKeyPrefix, labels);
    const cols = ensureColgroup(table, headers.length);
    const currentWidths = cols.map((col, index) => {
      return (
        numberFromPx(col.style.width) ||
        Math.round(headers[index]?.getBoundingClientRect().width || 0) ||
        baseWidth(labels[index], index)
      );
    });
    const initialWidths =
      getSavedWidths(key, headers.length) ||
      currentWidths.map((width, index) => Math.max(width, baseWidth(labels[index], index)));

    table.__mesColumnWidths = applyWidths(
      table,
      cols,
      initialWidths,
      minWidths,
      wrap,
      options.fillContainer !== false,
    );
    table.__mesColumnStorageKey = key;

    headers.forEach((header, columnIndex) => {
      header.classList.add(options.resizableClass || "mes-resizable-th");
      let handle = header.querySelector(":scope > .mes-column-resizer");
      if (!handle) {
        handle = document.createElement("span");
        handle.className = "mes-column-resizer";
        handle.setAttribute("aria-hidden", "true");
        header.appendChild(handle);
      }

      handle.onpointerdown = (event) => {
        event.preventDefault();
        event.stopPropagation();

        const startX = event.clientX;
        const startWidths = (table.__mesColumnWidths || initialWidths).slice();
        document.body.classList.add("mes-column-resizing");
        try {
          handle.setPointerCapture?.(event.pointerId);
        } catch (error) {
          // Algunos entornos de prueba emiten PointerEvent sinteticos sin captura activa.
        }

        const moveHandler = (moveEvent) => {
          const nextWidths = startWidths.slice();
          nextWidths[columnIndex] = Math.max(
            minWidths[columnIndex],
            Math.round(startWidths[columnIndex] + moveEvent.clientX - startX),
          );
          table.__mesColumnWidths = applyWidths(
            table,
            cols,
            nextWidths,
            minWidths,
            wrap,
            options.fillContainer !== false,
          );
          saveWidths(key, table.__mesColumnWidths);
        };

        const upHandler = () => {
          document.body.classList.remove("mes-column-resizing");
          document.removeEventListener("pointermove", moveHandler);
          document.removeEventListener("pointerup", upHandler);
          document.removeEventListener("pointercancel", upHandler);
          saveWidths(key, table.__mesColumnWidths || startWidths);
        };

        document.addEventListener("pointermove", moveHandler);
        document.addEventListener("pointerup", upHandler);
        document.addEventListener("pointercancel", upHandler);
      };

      handle.ondblclick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        const nextWidths = (table.__mesColumnWidths || initialWidths).slice();
        nextWidths[columnIndex] = Math.max(
          minWidths[columnIndex],
          baseWidth(labels[columnIndex], columnIndex),
        );
        table.__mesColumnWidths = applyWidths(
          table,
          cols,
          nextWidths,
          minWidths,
          wrap,
          options.fillContainer !== false,
        );
        saveWidths(key, table.__mesColumnWidths);
      };
    });
  }

  window.MesColumnResizer = { setup };
})();
