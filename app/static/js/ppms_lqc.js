/* PPM's LQC.
 * WF_004: garantiza CSS persistente propio si el template se carga por AJAX.
 */
(function () {
  "use strict";

  const STYLESHEET_ID = "ppms-lqc-css";
  const STYLESHEET_HREF = "/static/css/ppms_lqc.css?v=20260608d";
  const API_DATA = "/api/control_calidad/ppms/lqc";
  const API_TARGET = "/api/control_calidad/ppms/lqc/target";

  function ensureStylesheet() {
    const existing = document.getElementById(STYLESHEET_ID);
    if (existing) {
      if (existing.getAttribute("href") !== STYLESHEET_HREF) {
        existing.setAttribute("href", STYLESHEET_HREF);
      }
      return;
    }
    const link = document.createElement("link");
    link.id = STYLESHEET_ID;
    link.rel = "stylesheet";
    link.href = STYLESHEET_HREF;
    document.head.appendChild(link);
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString("es-MX");
  }

  function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function currentMonthStart() {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, {
      credentials: "same-origin",
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === false) {
      throw new Error(payload.error || "No fue posible completar la solicitud.");
    }
    return payload;
  }

  function getLqcElements(root) {
    return {
      root,
      target: root.querySelector("#ppms-lqc-target"),
      saveTarget: root.querySelector("#ppms-lqc-save-target"),
      filters: root.querySelector("#ppms-lqc-filters"),
      dateFrom: root.querySelector("#ppms-lqc-date-from"),
      dateTo: root.querySelector("#ppms-lqc-date-to"),
      line: root.querySelector("#ppms-lqc-line"),
      search: root.querySelector("#ppms-lqc-search"),
      clear: root.querySelector("#ppms-lqc-clear"),
      trendTitle: root.querySelector("#ppms-lqc-trend-title"),
      trendChart: root.querySelector("#ppms-lqc-trend-chart"),
      topPartChart: root.querySelector("#ppms-lqc-top-part-chart"),
      trendTable: root.querySelector("#ppms-lqc-trend-table"),
      topDetailTable: root.querySelector("#ppms-lqc-top-detail-table"),
      lineWeeklyTable: root.querySelector("#ppms-lqc-line-weekly-table"),
    };
  }

  function buildLqcQuery(elements) {
    const params = new URLSearchParams();
    if (elements.dateFrom.value) params.set("fecha_inicio", elements.dateFrom.value);
    if (elements.dateTo.value) params.set("fecha_fin", elements.dateTo.value);
    if (elements.line.value) params.append("lineas", elements.line.value);
    if (elements.search.value.trim()) params.set("q", elements.search.value.trim());
    const query = params.toString();
    return `${API_DATA}${query ? `?${query}` : ""}`;
  }

  function setLqcLoading(elements, loading) {
    elements.root.classList.toggle("is-loading", loading);
    elements.filters?.querySelectorAll("button, input, select").forEach((el) => {
      el.disabled = loading;
    });
    if (elements.saveTarget) elements.saveTarget.disabled = loading;
  }

  function renderTarget(elements, payload) {
    elements.target.value = payload.target || 0;
  }

  function renderLineOptions(elements, lines) {
    const current = elements.line.value;
    const options = ['<option value="">Todas</option>']
      .concat((lines || []).map((line) => `<option value="${escapeAttr(line)}">${escapeHtml(line)}</option>`));
    elements.line.innerHTML = options.join("");
    if ([...elements.line.options].some((option) => option.value === current)) {
      elements.line.value = current;
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, "&#096;");
  }

  function renderTrendTable(elements, periods) {
    const headers = (periods || []).map((item) => `<th>${escapeHtml(item.label)}</th>`).join("");
    const row = (label, key) =>
      `<tr><th>${label}</th>${(periods || []).map((item) => `<td>${formatNumber(item[key])}</td>`).join("")}</tr>`;
    elements.trendTable.innerHTML = `
      <thead><tr><th></th>${headers}</tr></thead>
      <tbody>
        ${row("TTL PDN", "inspected")}
        ${row("TARGET", "target")}
        ${row("TTL DEFECT", "defects")}
        ${row("PPM", "ppm")}
      </tbody>
    `;
  }

  function renderTopDetailTable(elements, rows) {
    const body = (rows || []).length
      ? rows
          .map(
            (row) => `
              <tr>
                <td>${escapeHtml(row.part_number)}</td>
                <td>${escapeHtml(row.model)}</td>
                <td>${formatNumber(row.inspected)}</td>
                <td>${formatNumber(row.defects)}</td>
                <td class="${Number(row.ppm || 0) > Number(row.target || 0) ? "is-over-target" : ""}">${formatNumber(row.ppm)}</td>
              </tr>
            `,
          )
          .join("")
      : '<tr><td colspan="5" class="ppms-empty">Sin datos</td></tr>';
    elements.topDetailTable.innerHTML = `
      <thead><tr><th>Proyecto</th><th>Modelo</th><th>TTL PDN</th><th>TTL DEFECT</th><th>PPM</th></tr></thead>
      <tbody>${body}</tbody>
    `;
  }

  function renderLineWeeklyTable(elements, payload) {
    const periods = payload?.periods || [];
    const rows = payload?.rows || [];
    const headers = periods.map((period) => `<th>${escapeHtml(period.label)}</th>`).join("");
    const metrics = [
      { label: "TTL PDN", key: "inspected" },
      { label: "TTL DEFECT", key: "defects" },
      { label: "PPM", key: "ppm", compareTarget: true },
    ];

    const body = rows.length
      ? rows
          .map((row) => {
            const weekByKey = new Map((row.weeks || []).map((week) => [week.key, week]));
            return metrics
              .map((metric, index) => {
                const cells = periods
                  .map((period) => {
                    const week = weekByKey.get(period.key) || {};
                    const overTarget = metric.compareTarget && Number(week.ppm || 0) > Number(week.target || 0);
                    return `<td class="${overTarget ? "is-over-target" : ""}">${formatNumber(week[metric.key])}</td>`;
                  })
                  .join("");
                const lineCell = index === 0 ? `<td rowspan="${metrics.length}" class="ppms-line-name ppms-line-group-cell">${escapeHtml(row.line)}</td>` : "";
                const rowClass = metric.key === "ppm" ? ' class="ppms-line-group-end"' : "";
                return `<tr${rowClass}>${lineCell}<td>${metric.label}</td>${cells}</tr>`;
              })
              .join("");
          })
          .join("")
      : `<tr><td colspan="${periods.length + 2}" class="ppms-empty">Sin datos</td></tr>`;

    elements.lineWeeklyTable.innerHTML = `
      <thead><tr><th>Linea</th><th>Item</th>${headers}</tr></thead>
      <tbody>${body}</tbody>
    `;
  }

  function compactLabel(value, maxLength) {
    const text = String(value || "");
    if (text.length <= maxLength) return text;
    return `${text.slice(0, Math.max(1, maxLength - 3))}...`;
  }

  function chartTitleText(lines) {
    return escapeHtml(lines.filter(Boolean).join("\n"));
  }

  function niceMax(value) {
    const max = Number(value || 0);
    if (!Number.isFinite(max) || max <= 0) return 1000;
    const step = max > 50000 ? 10000 : 5000;
    return Math.ceil((max * 1.12) / step) * step;
  }

  function renderEmptyChart(container, message) {
    if (!container) return;
    container.innerHTML = `
      <svg class="ppms-chart-svg" viewBox="0 0 760 300" preserveAspectRatio="xMidYMid meet">
        <rect x="0" y="0" width="760" height="300" fill="#ffffff"></rect>
        <text x="380" y="150" text-anchor="middle" fill="#5f6670" font-size="16" font-weight="700">${escapeHtml(message)}</text>
      </svg>
    `;
  }

  function axisGrid(yMax, y, pad, width, plotW) {
    const rows = [];
    for (let i = 0; i <= 5; i += 1) {
      const value = Math.round((yMax / 5) * i);
      const yy = y(value);
      rows.push(`
        <line x1="${pad.left}" y1="${yy}" x2="${pad.left + plotW}" y2="${yy}" stroke="#d8d8d8" stroke-width="1"></line>
        <text x="${pad.left - 9}" y="${yy + 4}" text-anchor="end" fill="#4b5563" font-size="12">${formatNumber(value)}</text>
      `);
    }
    rows.push(`<line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${pad.top + pad.plotH}" stroke="#cfcfcf" stroke-width="1"></line>`);
    rows.push(`<line x1="${pad.left}" y1="${pad.top + pad.plotH}" x2="${width - pad.right}" y2="${pad.top + pad.plotH}" stroke="#cfcfcf" stroke-width="1"></line>`);
    return rows.join("");
  }

  function updateTrendTitle(elements, payload) {
    if (!elements.trendTitle) return;
    const year = payload.trendYear || String(payload.dateTo || "").slice(0, 4);
    const stageLabel = payload.stage || "LQC";
    elements.trendTitle.textContent = `Trend TTL PPMs ${stageLabel}${year ? ` ${year}` : ""}`;
  }

  function renderTrendChart(container, periods) {
    const data = periods || [];
    if (!data.length) {
      renderEmptyChart(container, "Sin datos de tendencia");
      return;
    }

    const width = 760;
    const height = 300;
    const pad = { top: 34, right: 28, bottom: 42, left: 66, plotH: 206 };
    const plotW = width - pad.left - pad.right;
    const yMax = niceMax(Math.max(...data.map((item) => Number(item.ppm || 0)), ...data.map((item) => Number(item.target || 0))));
    const x = (index) => pad.left + (data.length > 1 ? (plotW / (data.length - 1)) * index : plotW / 2);
    const y = (value) => pad.top + pad.plotH - (Number(value || 0) / yMax) * pad.plotH;
    const ppmPoints = data.map((item, index) => `${x(index)},${y(item.ppm)}`).join(" ");
    const targetPoints = data.map((item, index) => `${x(index)},${y(item.target)}`).join(" ");

    const ppmMarkers = data
      .map((item, index) => {
        const xx = x(index);
        const yy = y(item.ppm);
        return `
          <g class="ppms-chart-point">
            <title>${chartTitleText([item.label, `PPM: ${formatNumber(item.ppm)}`, `TTL PDN: ${formatNumber(item.inspected)}`, `TTL DEFECT: ${formatNumber(item.defects)}`])}</title>
            <circle cx="${xx}" cy="${yy}" r="5" fill="#4a90e2"></circle>
            <text x="${xx}" y="${Math.max(20, yy - 12)}" text-anchor="middle" fill="#222222" font-size="12">${formatNumber(item.ppm)}</text>
          </g>
        `;
      })
      .join("");
    const targetMarkers = data
      .map((item, index) => {
        const xx = x(index);
        const yy = y(item.target);
        return `
          <g class="ppms-chart-point">
            <title>${chartTitleText([item.label, `TARGET: ${formatNumber(item.target)}`])}</title>
            <rect x="${xx - 5}" y="${yy - 5}" width="10" height="10" transform="rotate(45 ${xx} ${yy})" fill="#ff1f1f"></rect>
          </g>
        `;
      })
      .join("");
    const xLabels = data
      .map((item, index) => `<text x="${x(index)}" y="${height - 14}" text-anchor="middle" fill="#4b5563" font-size="13">${escapeHtml(item.label)}</text>`)
      .join("");

    container.innerHTML = `
      <svg class="ppms-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
        <rect x="0" y="0" width="${width}" height="${height}" fill="#ffffff"></rect>
        ${axisGrid(yMax, y, pad, width, plotW)}
        <g class="ppms-chart-legend">
          <line x1="600" y1="24" x2="626" y2="24" stroke="#4a90e2" stroke-width="2"></line>
          <circle cx="613" cy="24" r="4" fill="#4a90e2"></circle>
          <text x="632" y="28" fill="#333333" font-size="11">PPM</text>
          <line x1="676" y1="24" x2="702" y2="24" stroke="#ff1f1f" stroke-width="2"></line>
          <rect x="686" y="20" width="8" height="8" transform="rotate(45 690 24)" fill="#ff1f1f"></rect>
          <text x="708" y="28" fill="#333333" font-size="11">TARGET</text>
        </g>
        <polyline points="${targetPoints}" fill="none" stroke="#ff1f1f" stroke-width="2"></polyline>
        <polyline points="${ppmPoints}" fill="none" stroke="#4a90e2" stroke-width="2"></polyline>
        ${targetMarkers}
        ${ppmMarkers}
        ${xLabels}
      </svg>
    `;
  }

  function renderTopPartChart(container, rows) {
    const data = (rows || []).slice(0, 5);
    if (!data.length) {
      renderEmptyChart(container, "Sin datos por numero de parte");
      return;
    }

    const width = 760;
    const height = 300;
    const pad = { top: 38, right: 30, bottom: 50, left: 70, plotH: 202 };
    const plotW = width - pad.left - pad.right;
    const target = Number(data[0]?.target || 0);
    const yMax = niceMax(Math.max(target, ...data.map((item) => Number(item.ppm || 0))));
    const y = (value) => pad.top + pad.plotH - (Number(value || 0) / yMax) * pad.plotH;
    const slot = plotW / data.length;
    const barWidth = Math.min(72, slot * 0.45);
    const targetY = y(target);

    const bars = data
      .map((item, index) => {
        const centerX = pad.left + slot * index + slot / 2;
        const ppm = Number(item.ppm || 0);
        const barHeight = pad.top + pad.plotH - y(ppm);
        const barX = centerX - barWidth / 2;
        const barY = y(ppm);
        const color = ppm > target ? "#ff1f1f" : "#858585";
        return `
          <g class="ppms-chart-bar">
            <title>${chartTitleText([item.part_number, item.model, `PPM: ${formatNumber(item.ppm)}`, `TARGET: ${formatNumber(item.target)}`, `TTL PDN: ${formatNumber(item.inspected)}`, `TTL DEFECT: ${formatNumber(item.defects)}`])}</title>
            <rect x="${barX}" y="${barY}" width="${barWidth}" height="${Math.max(0, barHeight)}" fill="${color}"></rect>
            <text x="${centerX}" y="${Math.max(20, barY - 10)}" text-anchor="middle" fill="#333333" font-size="13">${formatNumber(item.ppm)}</text>
            <text x="${centerX}" y="${height - 18}" text-anchor="middle" fill="#4b5563" font-size="13">${escapeHtml(compactLabel(item.part_number, 13))}</text>
          </g>
        `;
      })
      .join("");

    container.innerHTML = `
      <svg class="ppms-chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
        <rect x="0" y="0" width="${width}" height="${height}" fill="#ffffff"></rect>
        ${axisGrid(yMax, y, pad, width, plotW)}
        <line x1="${pad.left}" y1="${targetY}" x2="${width - pad.right}" y2="${targetY}" stroke="#ff1f1f" stroke-width="4"></line>
        ${bars}
      </svg>
    `;
  }

  function renderCharts(elements, payload) {
    updateTrendTitle(elements, payload);
    renderTrendChart(elements.trendChart, payload.trendPeriods || payload.periods || []);
    renderTopPartChart(elements.topPartChart, payload.topParts || []);
  }

  async function loadLqc(elements) {
    setLqcLoading(elements, true);
    try {
      const payload = await fetchJson(buildLqcQuery(elements));
      elements.root.__lastPayload = payload;
      renderLineOptions(elements, payload.lines || []);
      renderTarget(elements, payload);
      renderTrendTable(elements, payload.trendPeriods || payload.periods || []);
      renderTopDetailTable(elements, payload.topPartDetails || payload.topParts || []);
      renderLineWeeklyTable(elements, payload.lineWeeklyDetails || {});
      renderCharts(elements, payload);
    } catch (error) {
      elements.trendTable.innerHTML = `<tbody><tr><td class="ppms-empty">${escapeHtml(error.message)}</td></tr></tbody>`;
      renderTopDetailTable(elements, []);
      renderLineWeeklyTable(elements, {});
      renderEmptyChart(elements.trendChart, error.message);
      renderEmptyChart(elements.topPartChart, "Sin datos por numero de parte");
    } finally {
      setLqcLoading(elements, false);
    }
  }

  async function saveLqcTarget(elements) {
    const target = Number(elements.target.value || 0);
    await fetchJson(API_TARGET, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target }),
    });
    await loadLqc(elements);
  }

  function initLqc(root) {
    const elements = getLqcElements(root);
    const today = new Date();
    elements.dateFrom.value = formatDate(currentMonthStart());
    elements.dateTo.value = formatDate(today);

    elements.filters.addEventListener("submit", (event) => {
      event.preventDefault();
      loadLqc(elements);
    });
    elements.clear.addEventListener("click", () => {
      elements.dateFrom.value = formatDate(currentMonthStart());
      elements.dateTo.value = formatDate(new Date());
      elements.line.value = "";
      elements.search.value = "";
      loadLqc(elements);
    });
    elements.saveTarget.addEventListener("click", () => {
      saveLqcTarget(elements).catch((error) => {
        elements.trendTable.innerHTML = `<tbody><tr><td class="ppms-empty">${escapeHtml(error.message)}</td></tr></tbody>`;
      });
    });
    window.addEventListener("resize", () => {
      if (root.__lastPayload) renderCharts(elements, root.__lastPayload);
    });

    loadLqc(elements);
  }

  function inicializarPPMsLQC(root) {
    ensureStylesheet();
    const moduleRoot =
      typeof root === "string" ? document.querySelector(root) : root;
    if (!moduleRoot || moduleRoot.dataset.initialized === "true") return;
    moduleRoot.dataset.initialized = "true";
    initLqc(moduleRoot);
  }

  window.inicializarPPMsLQC = inicializarPPMsLQC;
  document.querySelectorAll("#ppms-lqc-module").forEach(inicializarPPMsLQC);
})();
