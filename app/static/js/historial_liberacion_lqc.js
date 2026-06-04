/* Historial de liberacion LQC - JS extraido de template (WF_004).
 * CSS persistente cargado desde MainTemplate.html.
 * Fallback ensureModuleStyles() para servidores sin acceso al template.
 */
(function () {
  'use strict';

  const STYLESHEETS = [
    {
      id: 'historial-liberacion-lqc-css',
      href: '/static/css/historial_liberacion_lqc.css?v=20260604a',
    },
  ];

  function ensureModuleStyles() {
    STYLESHEETS.forEach(function (cfg) {
      if (document.getElementById(cfg.id)) return;
      var link = document.createElement('link');
      link.id = cfg.id;
      link.rel = 'stylesheet';
      link.href = cfg.href;
      document.head.appendChild(link);
    });
  }

  var LINES = ['M1', 'M2', 'M3', 'M4', 'DP1', 'DP2', 'DP3', 'H1'];
  var LINE_COLORS = {
    M1: '#3498db', M2: '#2980b9', M3: '#8e44ad', M4: '#502696',
    DP1: '#27ae60', DP2: '#229954', DP3: '#1a7a44', H1: '#1abc9c',
    'SIN PLAN': '#95a5a6',
  };
  var COLOR_PALETTE = [
    '#3498db', '#2980b9', '#8e44ad', '#502696', '#27ae60', '#229954',
    '#1a7a44', '#1abc9c', '#f39c12', '#d35400', '#95a5a6',
  ];
  var DEFAULT_SHIFT_HOURS = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6];

  var state = {
    view: 'grid',
    selectedLines: [],
    allLines: false,
    records: [],
    tableView: 'summary',
    dateFrom: todayStr(),
    dateTo: todayStr(),
    turno: 'Todos',
    searchQ: '',
    page: 1,
    loading: false,
    counts: {},
    uphData: {},
    uphSlots: [],
    chartSel: null,
  };
  var PER_PAGE = 500;

  function todayStr() {
    var d = new Date();
    var corte = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 7, 30, 0, 0);
    if (d < corte) d.setDate(d.getDate() - 1);
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function fmtDate(ds) {
    if (!ds) return '-';
    var p = String(ds).slice(0, 10).split('-');
    return p[2] + '/' + p[1] + '/' + p[0];
  }
  // Turnos: DIA 07:30-17:30, TIEMPO EXTRA 17:30-22:00, NOCHE 22:00-07:30 (mismo dia operativo).
  function getTurno(hour, minute) {
    var t = hour + (minute || 0) / 60;
    if (t >= 7.5 && t < 17.5) return 'DIA';
    if (t >= 17.5 && t < 22) return 'TIEMPO EXTRA';
    return 'NOCHE';
  }
  function chipClass(t) {
    if (t === 'DIA') return 'lqcs-chip-dia';
    if (t === 'TIEMPO EXTRA') return 'lqcs-chip-extra';
    return 'lqcs-chip-noche';
  }
  function statusHTML(status) {
    var s = status || '-';
    var cls = String(s).toLowerCase().indexOf('duplic') !== -1 ? 'lqcs-status-dup' : 'lqcs-status-ok';
    return '<span class="lqcs-chip ' + cls + '">' + esc(s) + '</span>';
  }
  function esc(v) {
    return String(v || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function shell() {
    return document.getElementById('lqc-smts-shell');
  }
  function lineColor(line, index) {
    var safeIndex = index >= 0 ? index : 0;
    if (!LINE_COLORS[line]) LINE_COLORS[line] = COLOR_PALETTE[safeIndex % COLOR_PALETTE.length];
    return LINE_COLORS[line];
  }
  function syncLines(lineas) {
    var next = (lineas || []).map(function (l) { return l.linea; }).filter(Boolean);
    if (next.length) LINES = next;
    LINES.forEach(function (line, index) { lineColor(line, index); });
    if (state.chartSel && LINES.indexOf(state.chartSel) === -1) state.chartSel = null;
  }
  function buttonLines() {
    return LINES.filter(function (line) { return line !== 'SIN PLAN'; });
  }
  function isAllLinesMode() {
    return state.allLines === true;
  }
  function syncDateInputs(changed) {
    var fromEl = document.getElementById('lqcs-from');
    var toEl = document.getElementById('lqcs-to');
    if (!fromEl || !toEl) return;
    var today = todayStr();
    if (!fromEl.value) fromEl.value = state.dateFrom || today;
    if (!toEl.value) toEl.value = state.dateTo || fromEl.value;
    if (fromEl.value > toEl.value) {
      if (changed === 'from') toEl.value = fromEl.value;
      else fromEl.value = toEl.value;
    }
    fromEl.max = toEl.value || today;
    toEl.min = fromEl.value || '';
    toEl.max = today;
    state.dateFrom = fromEl.value;
    state.dateTo = toEl.value;
  }
  function defaultUphSlots() {
    return DEFAULT_SHIFT_HOURS.map(function (h) {
      return { key: String(h), label: String(h).padStart(2, '0') + ':30', hour: h };
    });
  }
  function slotShiftColor(slot) {
    var hour = (slot && typeof slot.hour === 'number') ? slot.hour : 0;
    var minute = 0;
    if (slot && slot.label && slot.label.indexOf(':') !== -1) {
      minute = parseInt(slot.label.split(':')[1], 10) || 0;
    }
    var t = hour + minute / 60;
    if (t >= 7.5 && t < 17.5) return 'rgba(52,152,219,0.07)';
    if (t >= 17.5 && t < 22) return 'rgba(80,38,150,0.07)';
    return 'rgba(39,174,96,0.07)';
  }

  function exportCSV(filename, headers, rows) {
    var e = function (v) { return '"' + String(v || '').replace(/"/g, '""') + '"'; };
    var lines = [headers.map(e).join(',')].concat(rows.map(function (r) { return r.map(e).join(','); }));
    var blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function buildChart() {
    var uphData = state.uphData;
    var sel = state.chartSel;
    var W = 780, H = 220, PL = 48, PR = 16, PT = 16, PB = 60;
    var chartW = W - PL - PR, chartH = H - PT - PB;
    var slotData = state.uphSlots && state.uphSlots.length ? state.uphSlots : defaultUphSlots();
    var slots = slotData.length, xStep = slots > 1 ? chartW / (slots - 1) : chartW;

    var pts;
    if (sel === null) {
      pts = slotData.map(function (slot) {
        return { slot: slot, uph: LINES.reduce(function (s, l) { return s + ((uphData[l] || {})[slot.key] || 0); }, 0) };
      });
    } else {
      pts = slotData.map(function (slot) { return { slot: slot, uph: ((uphData[sel] || {})[slot.key] || 0) }; });
    }
    var color = sel === null ? '#3498db' : lineColor(sel, LINES.indexOf(sel));
    var maxUPH = Math.max.apply(null, pts.map(function (p) { return p.uph; }));
    if (!maxUPH) maxUPH = 1;
    function yScale(v) { return chartH - (v / maxUPH) * chartH; }

    var pathD = pts.map(function (p, i) {
      return (i === 0 ? 'M' : 'L') + (PL + i * xStep).toFixed(1) + ',' + (PT + yScale(p.uph)).toFixed(1);
    }).join(' ');
    var fillD = pathD + ' L' + (PL + (slots - 1) * xStep).toFixed(1) + ',' + (PT + chartH) + ' L' + PL + ',' + (PT + chartH) + ' Z';

    var zonesSVG = slotData.map(function (slot, i) {
      var x1 = slots === 1 ? PL : Math.max(PL, PL + (i - 0.5) * xStep);
      var x2 = slots === 1 ? PL + chartW : Math.min(PL + chartW, PL + (i + 0.5) * xStep);
      return '<rect x="' + x1 + '" y="' + PT + '" width="' + Math.max(1, x2 - x1) + '" height="' + chartH + '" fill="' + slotShiftColor(slot.hour) + '"/>';
    }).join('');

    var gridSVG = '';
    for (var gi = 0; gi < 5; gi++) {
      var gv = Math.round((maxUPH / 4) * gi), gy = PT + yScale(gv);
      gridSVG += '<line x1="' + PL + '" x2="' + (PL + chartW) + '" y1="' + gy + '" y2="' + gy + '" stroke="#2a2d38" stroke-width="1"/>'
        + '<text x="' + (PL - 5) + '" y="' + (gy + 4) + '" text-anchor="end" font-size="9" fill="#5F6375">' + gv + '</text>';
    }

    var tickSVG = slotData.map(function (slot, idx) {
      var x = PL + idx * xStep, lbl = slotData[idx].label;
      return '<line x1="' + x + '" x2="' + x + '" y1="' + (PT + chartH) + '" y2="' + (PT + chartH + 4) + '" stroke="#5F6375"/>'
        + '<text x="' + x + '" y="' + (PT + chartH + 17) + '" text-anchor="end" font-size="7.5" fill="#95a5a6" transform="rotate(-45 ' + x + ' ' + (PT + chartH + 17) + ')">' + esc(lbl) + '</text>';
    }).join('');

    var circlesSVG = pts.map(function (p, i) {
      if (!p.uph) return '';
      var cx = PL + i * xStep, cy = PT + yScale(p.uph);
      return '<circle cx="' + cx + '" cy="' + cy + '" r="3.5" fill="' + color + '" opacity="0.8" data-lqclabel="' + esc(p.slot.label) + '" data-lqcuph="' + p.uph + '" class="lqcs-chart-dot"/>';
    }).join('');

    var labelStr = sel === null ? 'Total todas las lineas' : sel;
    var legendHTML = '<div class="lqcs-legend-pill' + (sel === null ? ' active' : '') + '" data-lqcline="__total__">'
      + '<div class="lqcs-legend-dot" style="background:#3498db;width:14px;height:3px;border-radius:2px;"></div>Total</div>';
    legendHTML += buttonLines().map(function (l) {
      return '<div class="lqcs-legend-pill' + (sel === l ? ' active' : '') + '" data-lqcline="' + l + '">'
        + '<div class="lqcs-legend-dot" style="background:' + lineColor(l, LINES.indexOf(l)) + ';"></div>' + esc(l) + '</div>';
    }).join('');

    return '<div class="lqcs-chart-box"><div class="lqcs-chart-top">'
      + '<div class="lqcs-chart-title"><span style="color:' + color + '">' + esc(labelStr) + '</span>'
      + ' <span style="font-size:.68rem;color:#95a5a6;font-weight:400;">- UPH por hora</span></div>'
      + '<div class="lqcs-chart-legend" id="lqcs-legend">' + legendHTML + '</div>'
      + '</div>'
      + '<div id="lqcs-tooltip" style="position:fixed;display:none;background:#172A46;border:1px solid #20688C;border-radius:4px;padding:4px 8px;font-size:10px;color:#ecf0f1;pointer-events:none;z-index:9999;"></div>'
      + '<svg width="100%" viewBox="0 0 ' + W + ' ' + H + '" style="overflow:visible;">'
      + zonesSVG + gridSVG + tickSVG
      + '<path d="' + fillD + '" fill="' + color + '" opacity="0.07"/>'
      + '<path d="' + pathD + '" fill="none" stroke="' + color + '" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
      + circlesSVG
      + '</svg></div>';
  }

  function renderGrid() {
    var visibleLines = buttonLines();
    var countsHTML = visibleLines.map(function (l, i) {
      var c = state.counts[l] || 0;
      return '<div class="lqcs-line-card" data-lqcl="' + esc(l) + '" style="border-color:' + lineColor(l, i) + ';">'
        + '<div class="lqcs-line-name">' + esc(l) + '</div>'
        + '<div class="lqcs-line-badge">' + c.toLocaleString() + ' hoy</div>'
        + '</div>';
    }).join('');

    shell().innerHTML = '<div class="lqcs-grid-wrap">'
      + '<div class="lqcs-heading">Selecciona una l\xednea</div>'
      + '<div class="lqcs-sub">Haz clic para ver los escaneos del d\xeda</div>'
      + '<div class="lqcs-line-grid">' + countsHTML + '</div>'
      + '<div><div class="lqcs-all-btn" id="lqcs-all-btn">Ver todas las l\xedneas</div></div>'
      + '<div id="lqcs-chart-area" style="width:100%;max-width:820px;">' + buildChart() + '</div>'
      + '</div>';

    bindGridEvents();
  }

  function bindGridEvents() {
    var s = shell();
    s.querySelectorAll('.lqcs-line-card').forEach(function (el) {
      el.addEventListener('click', function () { openLine(this.dataset.lqcl); });
    });
    var allBtn = s.querySelector('#lqcs-all-btn');
    if (allBtn) allBtn.addEventListener('click', openAll);
    bindChartLegend();
    bindChartDots();
  }

  function bindChartLegend() {
    var s = shell();
    s.querySelectorAll('.lqcs-legend-pill').forEach(function (el) {
      el.addEventListener('click', function () {
        var l = this.dataset.lqcline;
        state.chartSel = (l === '__total__') ? null : (state.chartSel === l ? null : l);
        var area = document.getElementById('lqcs-chart-area');
        if (area) { area.innerHTML = buildChart(); bindChartLegend(); bindChartDots(); }
      });
    });
  }

  function bindChartDots() {
    var tooltip = document.getElementById('lqcs-tooltip');
    if (!tooltip) return;
    shell().querySelectorAll('.lqcs-chart-dot').forEach(function (dot) {
      dot.addEventListener('mouseenter', function () {
        tooltip.style.display = 'block';
        tooltip.textContent = this.dataset.lqclabel + ' - ' + this.dataset.lqcuph + ' uph';
      });
      dot.addEventListener('mousemove', function (e) {
        tooltip.style.left = (e.clientX + 12) + 'px';
        tooltip.style.top = (e.clientY - 28) + 'px';
      });
      dot.addEventListener('mouseleave', function () {
        tooltip.style.display = 'none';
      });
    });
  }

  function renderTable() {
    var allLines = isAllLinesMode();
    var title = allLines ? 'Todas las l\xedneas' : state.selectedLines[0];
    var pillSub = allLines ? '<span class="lqcs-pill-sub">General</span>' : '';

    var filtersHTML = '<div class="lqcs-filters">'
      + '<div class="lqcs-filter-group lqcs-filter-group-main">'
      + '<span class="lqcs-filter-lbl">Fecha:</span>'
      + '<input type="date" class="lqcs-date" id="lqcs-from" value="' + state.dateFrom + '">'
      + '<span class="lqcs-filter-lbl">a</span>'
      + '<input type="date" class="lqcs-date" id="lqcs-to" value="' + state.dateTo + '">'
      + '<button class="lqcs-apply-btn" id="lqcs-apply">Aplicar</button>'
      + '<button class="lqcs-today-btn" id="lqcs-today">Hoy</button>'
      + '</div>'
      + '<div class="lqcs-filter-group">'
      + '<span class="lqcs-filter-lbl">Turno:</span>'
      + '<select class="lqcs-sel" id="lqcs-turno"><option>Todos</option><option>DIA</option><option>TIEMPO EXTRA</option><option>NOCHE</option></select>'
      + '</div>'
      + '<div class="lqcs-filter-group">'
      + '<div class="lqcs-view-toggle">'
      + '<button class="lqcs-view-btn' + (state.tableView === 'summary' ? ' active' : '') + '" id="lqcs-v-sum">Resumen</button>'
      + '<button class="lqcs-view-btn' + (state.tableView === 'detail' ? ' active' : '') + '" id="lqcs-v-det">Detalle</button>'
      + '</div>'
      + '</div>'
      + '<div class="lqcs-filter-group">'
      + '<button class="lqcs-export-btn" id="lqcs-export">Exportar</button>'
      + '</div>'
      + '</div>';

    shell().innerHTML = '<div class="lqcs-table-screen">'
      + '<div class="lqcs-table-header">'
      + '<button class="lqcs-back-btn" id="lqcs-back">Lineas</button>'
      + '<div class="lqcs-pill"><div style="width:8px;height:8px;border-radius:50%;background:#3498db;"></div>'
      + '<span class="lqcs-pill-name">' + esc(title) + '</span>' + pillSub + '</div>'
      + '</div>'
      + filtersHTML
      + '<div id="lqcs-search-area"></div>'
      + '<div class="lqcs-stats">'
      + '<div class="lqcs-stat-card"><span class="lqcs-stat-val" id="lqcs-total-v">...</span><span class="lqcs-stat-lbl">Total piezas</span></div>'
      + '<div class="lqcs-stat-card"><span class="lqcs-stat-val" id="lqcs-parts-v">...</span><span class="lqcs-stat-lbl">No. partes</span></div>'
      + '</div>'
      + '<div id="lqcs-content-area"><div class="lqcs-loading"><span class="lqcs-spin"></span>Cargando...</div></div>'
      + '</div>';

    var selEl = document.getElementById('lqcs-turno');
    if (selEl) selEl.value = state.turno;
    syncDateInputs();

    bindTableEvents();
    loadTableData();
  }

  function bindTableEvents() {
    var backBtn = document.getElementById('lqcs-back');
    if (backBtn) backBtn.addEventListener('click', function () { state.view = 'grid'; state.records = []; renderGrid(); loadGridData(); });

    var fromEl = document.getElementById('lqcs-from');
    var toEl = document.getElementById('lqcs-to');
    if (fromEl) fromEl.addEventListener('change', function () { syncDateInputs('from'); });
    if (toEl) toEl.addEventListener('change', function () { syncDateInputs('to'); });

    var applyBtn = document.getElementById('lqcs-apply');
    if (applyBtn) applyBtn.addEventListener('click', function () { syncDateInputs(); loadTableData(); });

    var todayBtn = document.getElementById('lqcs-today');
    if (todayBtn) todayBtn.addEventListener('click', function () {
      state.dateFrom = state.dateTo = todayStr();
      var f = document.getElementById('lqcs-from'), t = document.getElementById('lqcs-to');
      if (f) f.value = state.dateFrom;
      if (t) t.value = state.dateTo;
      syncDateInputs();
      loadTableData();
    });

    var turnoEl = document.getElementById('lqcs-turno');
    if (turnoEl) turnoEl.addEventListener('change', function () { state.turno = this.value; loadTableData(); });

    var vSum = document.getElementById('lqcs-v-sum');
    var vDet = document.getElementById('lqcs-v-det');
    if (vSum) vSum.addEventListener('click', function () { state.tableView = 'summary'; state.searchQ = ''; state.page = 1; renderContentArea(); });
    if (vDet) vDet.addEventListener('click', function () { state.tableView = 'detail'; state.searchQ = ''; state.page = 1; renderContentArea(); });

    var expBtn = document.getElementById('lqcs-export');
    if (expBtn) expBtn.addEventListener('click', doExport);
  }

  function loadGridData() {
    fetch('/api/lqc/lineas')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.success) {
          syncLines(d.lineas || []);
          var c = {};
          (d.lineas || []).forEach(function (l) { c[l.linea] = l.total_hoy || 0; });
          state.counts = c;
          state.uphData = d.uph_hoy || {};
          state.uphSlots = d.uph_slots || [];
          renderGrid();
        }
      })
      .catch(function () {});
  }

  function loadTableData() {
    var area = document.getElementById('lqcs-content-area');
    if (area) area.innerHTML = '<div class="lqcs-loading"><span class="lqcs-spin"></span>Cargando...</div>';
    var tv = document.getElementById('lqcs-total-v'), pv = document.getElementById('lqcs-parts-v');
    if (tv) tv.textContent = '...';
    if (pv) pv.textContent = '...';

    var params = new URLSearchParams();
    if (!isAllLinesMode()) {
      state.selectedLines.forEach(function (l) { params.append('lineas', l); });
    }
    params.set('fecha_inicio', state.dateFrom);
    params.set('fecha_fin', state.dateTo);
    if (state.turno !== 'Todos') params.set('turno', state.turno);

    fetch('/api/lqc/datos?' + params.toString())
      .then(function (r) { return r.json(); })
      .then(function (d) {
        state.records = d.success ? (d.records || []) : [];
        state.page = 1;
        updateStats();
        renderContentArea();
      })
      .catch(function () { state.records = []; updateStats(); renderContentArea(); });
  }

  function updateStats() {
    var tv = document.getElementById('lqcs-total-v'), pv = document.getElementById('lqcs-parts-v');
    if (tv) tv.textContent = state.records.length.toLocaleString();
    if (pv) {
      var parts = {};
      state.records.forEach(function (r) { parts[r.part] = 1; });
      pv.textContent = Object.keys(parts).length;
    }
  }

  function renderContentArea() {
    var area = document.getElementById('lqcs-content-area');
    if (!area) return;
    var allLines = isAllLinesMode();

    var filtered = state.records;
    if (state.searchQ) {
      var q = state.searchQ.toLowerCase();
      filtered = state.records.filter(function (r) {
        return [
          r.linea, r.part, r.model_code, r.lot_no, r.box_code, r.serial,
          r.status, r.turno, String(r.fecha), String(r.last_scan),
          r.fechas_repetidas, r.escaneos_repetidos,
        ].join(' ').toLowerCase().indexOf(q) !== -1;
      });
    }

    var vSum = document.getElementById('lqcs-v-sum'), vDet = document.getElementById('lqcs-v-det');
    if (vSum) { vSum.className = 'lqcs-view-btn' + (state.tableView === 'summary' ? ' active' : ''); }
    if (vDet) { vDet.className = 'lqcs-view-btn' + (state.tableView === 'detail' ? ' active' : ''); }

    if (state.tableView === 'summary') {
      area.innerHTML = buildSummaryView(filtered, allLines);
    } else {
      area.innerHTML = buildDetailView(filtered, allLines);
    }
    bindContentEvents(filtered, allLines);
  }

  function buildSearchBar(filtered, total, grouped) {
    var suffix = grouped ? ' grupos / ' + total + ' escaneos' : ' de ' + total + ' escaneos';
    return '<div class="lqcs-search-bar">'
      + '<span style="color:#95a5a6;font-size:.75rem;">Buscar:</span>'
      + '<input class="lqcs-search-input" id="lqcs-search" placeholder="Buscar..." value="' + esc(state.searchQ) + '">'
      + (state.searchQ ? '<button class="lqcs-search-clear" id="lqcs-search-clear">Limpiar</button>' : '')
      + '<span class="lqcs-search-count">' + filtered + suffix + '</span>'
      + '</div>';
  }
  function renderSearchArea(filtered, total, grouped) {
    var searchArea = document.getElementById('lqcs-search-area');
    if (searchArea) searchArea.innerHTML = buildSearchBar(filtered, total, grouped);
  }

  function buildSummaryView(filtered, allLines) {
    var map = {};
    filtered.forEach(function (r) {
      var k = allLines ? (r.fecha + '|' + r.part) : (r.linea + '|' + r.fecha + '|' + r.part + '|' + (r.lot_no || ''));
      if (!map[k]) map[k] = { linea: r.linea, fecha: r.fecha, part: r.part, lot_no: allLines ? '' : (r.lot_no || ''), model_code: r.model_code || '', total: 0, seriales: {}, unicas: 0, repetidas: 0, DIA: 0, 'TIEMPO EXTRA': 0, NOCHE: 0 };
      map[k].total++;
      if (r.serial) map[k].seriales[r.serial] = 1;
      if (r.duplicado_historico || String(r.status || '').toLowerCase().indexOf('duplic') !== -1) map[k].repetidas++;
      map[k][r.turno] = (map[k][r.turno] || 0) + 1;
    });
    Object.keys(map).forEach(function (k) { map[k].unicas = Math.max(0, map[k].total - map[k].repetidas); });
    var groups = Object.values(map).sort(function (a, b) { return b.total - a.total; });

    renderSearchArea(groups.length, state.records.length, true);
    if (!groups.length) return '<div class="lqcs-empty">Sin registros</div>';

    var thLinea = '';
    var thLote = allLines ? '' : '<th>LOTE</th>';
    var rows = groups.map(function (g) {
      var tdLinea = '';
      var tdLote = allLines ? '' : '<td style="font-family:monospace;font-size:.72rem;color:#95a5a6;">' + esc(g.lot_no || '-') + '</td>';
      var tdDia = g.DIA > 0 ? '<span class="lqcs-chip lqcs-chip-dia">' + g.DIA + '</span>' : '<span style="color:#5F6375">-</span>';
      var tdExtra = g['TIEMPO EXTRA'] > 0 ? '<span class="lqcs-chip lqcs-chip-extra">' + g['TIEMPO EXTRA'] + '</span>' : '<span style="color:#5F6375">-</span>';
      var tdNoche = g.NOCHE > 0 ? '<span class="lqcs-chip lqcs-chip-noche">' + g.NOCHE + '</span>' : '<span style="color:#5F6375">-</span>';
      return '<tr>' + tdLinea + '<td>' + fmtDate(g.fecha) + '</td><td style="color:#ecf0f1;font-weight:500;">' + esc(g.part) + '</td>'
        + tdLote
        + '<td style="text-align:center;color:#3498db;font-weight:700;">' + g.total.toLocaleString() + '</td>'
        + '<td style="text-align:center;color:#27ae60;font-weight:700;">' + g.unicas.toLocaleString() + '</td>'
        + '<td style="text-align:center;color:#ff8b7d;font-weight:700;">' + (g.repetidas ? g.repetidas.toLocaleString() : '-') + '</td>'
        + '<td style="text-align:center;">' + tdDia + '</td><td style="text-align:center;">' + tdExtra + '</td><td style="text-align:center;">' + tdNoche + '</td></tr>';
    }).join('');

    return '<div class="lqcs-table-wrap"><table class="lqcs-tbl"><thead><tr>'
      + thLinea + '<th>FECHA</th><th>N\xdaMERO DE PARTE</th>' + thLote + '<th style="text-align:center;">TOTAL</th><th style="text-align:center;">UNICAS</th>'
      + '<th style="text-align:center;">REPETIDAS HIST.</th><th style="text-align:center;">DIA</th><th style="text-align:center;">T. EXTRA</th><th style="text-align:center;">NOCHE</th>'
      + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  function buildDetailView(filtered, allLines) {
    var total = filtered.length;
    var pages = Math.max(1, Math.ceil(total / PER_PAGE));
    var safePage = Math.min(Math.max(state.page, 1), pages);
    state.page = safePage;
    var start = (safePage - 1) * PER_PAGE;
    var slice = filtered.slice(start, start + PER_PAGE);

    renderSearchArea(total, state.records.length);
    if (!slice.length) return '<div class="lqcs-empty">Sin registros</div>';

    var thLinea = allLines ? '<th>L\xcdNEA</th>' : '';
    var rows = slice.map(function (r) {
      var tdLinea = allLines ? '<td><span class="lqcs-badge-linea">' + esc(r.linea) + '</span></td>' : '';
      return '<tr>' + tdLinea + '<td>' + fmtDate(r.fecha) + '</td>'
        + '<td style="color:#ecf0f1;font-weight:500;">' + esc(r.part) + '</td>'
        + '<td style="font-family:monospace;font-size:.72rem;color:#95a5a6;">' + esc(r.lot_no || '-') + '</td>'
        + '<td style="font-family:monospace;font-size:.72rem;color:#95a5a6;">' + esc(r.box_code || '-') + '</td>'
        + '<td style="text-align:center;color:#3498db;font-weight:600;">1</td>'
        + '<td><span class="lqcs-chip ' + chipClass(r.turno) + '">' + esc(r.turno) + '</span></td>'
        + '<td>' + statusHTML(r.status) + '</td>'
        + '<td style="color:#ffb0a7;font-size:.75rem;">' + esc(r.fechas_repetidas || '-') + '</td>'
        + '<td style="color:#95a5a6;font-size:.75rem;">' + esc(r.escaneos_repetidos || '-') + '</td>'
        + '<td style="font-family:monospace;font-size:.72rem;color:#95a5a6;">' + esc(r.serial) + '</td>'
        + '<td style="color:#95a5a6;font-size:.75rem;">' + esc(r.last_scan) + '</td>'
        + '</tr>';
    }).join('');

    var pagBar = total > PER_PAGE ? '<div class="lqcs-page-bar">'
      + '<span class="lqcs-page-info">' + (start + 1) + '-' + Math.min(start + PER_PAGE, total) + ' de ' + total + ' escaneos</span>'
      + '<div style="display:flex;gap:4px;align-items:center;">'
      + '<button class="lqcs-page-btn" id="lqcs-prev"' + (safePage <= 1 ? ' disabled' : '') + '>Ant.</button>'
      + '<span class="lqcs-page-info">Pag. ' + safePage + '/' + pages + '</span>'
      + '<button class="lqcs-page-btn" id="lqcs-next"' + (safePage >= pages ? ' disabled' : '') + '>Sig.</button>'
      + '</div></div>' : '';

    return '<div class="lqcs-table-wrap"><table class="lqcs-tbl"><thead><tr>'
      + thLinea + '<th>FECHA</th><th>N\xdaMERO DE PARTE</th><th>LOTE</th><th>CAJA</th><th style="text-align:center;">CANTIDAD</th>'
      + '<th>TURNO</th><th>ESTADO</th><th>FECHA HISTORICA</th><th>ESCANEO HISTORICO</th><th>SERIAL</th><th>\xdaLTIMO ESCANEO</th>'
      + '</tr></thead><tbody>' + rows + '</tbody></table></div>' + pagBar;
  }

  function bindContentEvents(filtered, allLines) {
    var searchEl = document.getElementById('lqcs-search');
    if (searchEl) {
      searchEl.addEventListener('input', function () {
        state.searchQ = this.value;
        state.page = 1;
        renderContentArea();
        var nextSearch = document.getElementById('lqcs-search');
        if (nextSearch) {
          nextSearch.focus();
          nextSearch.setSelectionRange(nextSearch.value.length, nextSearch.value.length);
        }
      });
    }
    var clearEl = document.getElementById('lqcs-search-clear');
    if (clearEl) clearEl.addEventListener('click', function () { state.searchQ = ''; state.page = 1; renderContentArea(); });

    var prevBtn = document.getElementById('lqcs-prev');
    var nextBtn = document.getElementById('lqcs-next');
    if (prevBtn) prevBtn.addEventListener('click', function () { state.page--; renderContentArea(); });
    if (nextBtn) nextBtn.addEventListener('click', function () { state.page++; renderContentArea(); });
  }

  function doExport() {
    var allLines = isAllLinesMode();
    var dateLabel = state.dateFrom + '_' + state.dateTo;
    var lineLabel = allLines ? 'todas' : state.selectedLines.join('-');
    if (state.tableView === 'summary') {
      var map = {};
      state.records.forEach(function (r) {
        var k = allLines ? (r.fecha + '|' + r.part) : (r.linea + '|' + r.fecha + '|' + r.part + '|' + (r.lot_no || ''));
        if (!map[k]) map[k] = { linea: r.linea, fecha: r.fecha, part: r.part, lot_no: allLines ? '' : (r.lot_no || ''), total: 0, seriales: {}, unicas: 0, repetidas: 0, DIA: 0, 'TIEMPO EXTRA': 0, NOCHE: 0 };
        map[k].total++;
        if (r.serial) map[k].seriales[r.serial] = 1;
        if (r.duplicado_historico || String(r.status || '').toLowerCase().indexOf('duplic') !== -1) map[k].repetidas++;
        map[k][r.turno] = (map[k][r.turno] || 0) + 1;
      });
      Object.keys(map).forEach(function (k) { map[k].unicas = Math.max(0, map[k].total - map[k].repetidas); });
      var groups = Object.values(map);
      var hdr = allLines ? ['FECHA', 'NUMERO DE PARTE', 'TOTAL', 'UNICAS', 'REPETIDAS HISTORICAS', 'DIA', 'TIEMPO EXTRA', 'NOCHE'] : ['FECHA', 'NUMERO DE PARTE', 'LOTE', 'TOTAL', 'UNICAS', 'REPETIDAS HISTORICAS', 'DIA', 'TIEMPO EXTRA', 'NOCHE'];
      var rows = groups.map(function (g) { return allLines ? [g.fecha, g.part, g.total, g.unicas, g.repetidas, g.DIA, g['TIEMPO EXTRA'], g.NOCHE] : [g.fecha, g.part, g.lot_no, g.total, g.unicas, g.repetidas, g.DIA, g['TIEMPO EXTRA'], g.NOCHE]; });
      exportCSV('resumen_' + lineLabel + '_' + dateLabel + '.csv', hdr, rows);
    } else {
      var hdr2 = allLines ? ['LINEA', 'FECHA', 'NUMERO DE PARTE', 'LOTE', 'CAJA', 'CANTIDAD', 'TURNO', 'ESTADO', 'FECHA HISTORICA', 'ESCANEO HISTORICO', 'SERIAL', 'ULTIMO ESCANEO'] : ['FECHA', 'NUMERO DE PARTE', 'LOTE', 'CAJA', 'CANTIDAD', 'TURNO', 'ESTADO', 'FECHA HISTORICA', 'ESCANEO HISTORICO', 'SERIAL', 'ULTIMO ESCANEO'];
      var rows2 = state.records.map(function (r) { return allLines ? [r.linea, r.fecha, r.part, r.lot_no, r.box_code, 1, r.turno, r.status, r.fechas_repetidas, r.escaneos_repetidos, r.serial, r.last_scan] : [r.fecha, r.part, r.lot_no, r.box_code, 1, r.turno, r.status, r.fechas_repetidas, r.escaneos_repetidos, r.serial, r.last_scan]; });
      exportCSV('detalle_' + lineLabel + '_' + dateLabel + '.csv', hdr2, rows2);
    }
  }

  function openLine(line) { state.selectedLines = [line]; state.allLines = false; state.view = 'table'; state.records = []; state.page = 1; renderTable(); }
  function openAll() { state.selectedLines = []; state.allLines = true; state.view = 'table'; state.records = []; state.page = 1; renderTable(); }

  function init() {
    ensureModuleStyles();
    state = {
      view: 'grid', selectedLines: [], records: [], tableView: 'summary',
      dateFrom: todayStr(), dateTo: todayStr(), turno: 'Todos', searchQ: '', page: 1,
      loading: false, counts: {}, uphData: {}, uphSlots: [], allLines: false, chartSel: null,
    };
    renderGrid();
    loadGridData();
  }

  window.inicializarHistorialLiberacionLQC = init;
})();
