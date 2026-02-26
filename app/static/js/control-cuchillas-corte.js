(function() {
  var MODULE_ROOT_ID = 'control-cuchillas-corte-module';
  var POLL_INTERVAL_MS = 12000;
  var pollingTimer = null;
  var state = {
    selectedLinea: '',
    dashboardItems: [],
    lineas: [],
    historialSesiones: [],
    globalButtonsLocked: false
  };

  function getEl(id) {
    return document.getElementById(id);
  }

  function moduleExists() {
    return !!getEl(MODULE_ROOT_ID);
  }

  function moduleVisible() {
    var root = getEl(MODULE_ROOT_ID);
    return !!root && root.offsetParent !== null;
  }

  function toNumber(value, fallback) {
    var n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function formatNumber(value, decimals) {
    var d = typeof decimals === 'number' ? decimals : 4;
    var num = toNumber(value, 0);
    return num.toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: d
    });
  }

  function nowLabel() {
    return new Date().toLocaleTimeString('es-MX', { hour12: false });
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function parseError(error) {
    if (!error) return 'Error desconocido';
    if (error.response && error.response.data && error.response.data.error) {
      return error.response.data.error;
    }
    if (error.data && error.data.error) {
      return error.data.error;
    }
    if (error.message) return error.message;
    return String(error);
  }

  async function requestApi(method, url, payload, params) {
    var m = (method || 'GET').toUpperCase();

    if (typeof axios !== 'undefined') {
      var resp = await axios({
        method: m,
        url: url,
        data: payload || undefined,
        params: params || undefined,
        headers: { 'Content-Type': 'application/json' }
      });
      return resp.data;
    }

    var finalUrl = url;
    if (params && typeof URLSearchParams !== 'undefined') {
      var qs = new URLSearchParams(params).toString();
      if (qs) finalUrl += '?' + qs;
    }

    var opts = {
      method: m,
      headers: { 'Content-Type': 'application/json' }
    };
    if (payload) {
      opts.body = JSON.stringify(payload);
    }

    var res = await fetch(finalUrl, opts);
    var data;
    try {
      data = await res.json();
    } catch (e) {
      data = { success: false, error: 'Respuesta no JSON' };
    }

    if (!res.ok) {
      var err = new Error((data && data.error) || ('HTTP ' + res.status));
      err.data = data;
      throw err;
    }

    return data;
  }

  function setStatus(message, tone) {
    var el = getEl('cc-module-status');
    if (!el) return;

    var cls = 'cc-status-badge';
    if (tone === 'ok') cls += ' is-ok';
    if (tone === 'warn') cls += ' is-warn';
    if (tone === 'error') cls += ' is-error';

    el.className = cls;
    el.textContent = message || 'Listo';
  }

  function ensureConfigModalInBody() {
    var modals = document.querySelectorAll('#cc-config-modal');
    if (!modals || !modals.length) return null;

    var modal = modals[0];
    for (var i = 1; i < modals.length; i += 1) {
      try {
        modals[i].remove();
      } catch (e) {
        if (modals[i].parentNode) {
          modals[i].parentNode.removeChild(modals[i]);
        }
      }
    }

    var root = getEl(MODULE_ROOT_ID);
    if (root && root.contains(modal)) {
      document.body.appendChild(modal);
    }

    return modal;
  }

  function setConfigModalOpen(open) {
    var modal = ensureConfigModalInBody() || getEl('cc-config-modal');
    if (!modal) return;

    if (open) {
      modal.classList.add('is-open');
      modal.setAttribute('aria-hidden', 'false');
      modal.style.cssText = [
        'display: flex !important',
        'position: fixed !important',
        'top: 0 !important',
        'left: 0 !important',
        'width: 100% !important',
        'height: 100% !important',
        'justify-content: center !important',
        'align-items: flex-start !important',
        'background: rgba(0,0,0,0.6) !important',
        'z-index: 100000 !important',
        'opacity: 1 !important',
        'visibility: visible !important'
      ].join('; ');
      return;
    }

    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
    modal.style.cssText = [
      'display: none !important',
      'position: fixed !important',
      'top: 0 !important',
      'left: 0 !important',
      'width: 100% !important',
      'height: 100% !important',
      'z-index: 100000 !important',
      'opacity: 0 !important',
      'visibility: hidden !important',
      'pointer-events: none !important'
    ].join('; ');
  }

  function setButtonLoading(buttonId, loading, loadingText) {
    var btn = getEl(buttonId);
    if (!btn) return;

    var textEl = btn.querySelector('.cc-btn-text');
    if (!btn.dataset.defaultText) {
      btn.dataset.defaultText = textEl
        ? String(textEl.textContent || '').trim()
        : String(btn.textContent || '').trim();
    }

    if (loading) {
      if (textEl && loadingText) textEl.textContent = loadingText;
      btn.classList.add('is-loading');
      btn.disabled = true;
      return;
    }

    if (textEl && btn.dataset.defaultText) {
      textEl.textContent = btn.dataset.defaultText;
    }
    btn.classList.remove('is-loading');
    btn.disabled = !!state.globalButtonsLocked;
  }

  function setButtonsDisabled(disabled) {
    var ids = [
      'cc-btn-recargar-lineas',
      'cc-btn-refrescar-dashboard',
      'cc-btn-guardar-config',
      'cc-btn-iniciar-sesion',
      'cc-btn-reemplazar-sesion',
      'cc-btn-eliminar-sesion',
      'cc-btn-refrescar-estado',
      'cc-btn-recalcular',
      'cc-btn-refrescar-historial',
      'cc-btn-refrescar-eventos'
    ];
    state.globalButtonsLocked = !!disabled;
    ids.forEach(function(id) {
      var btn = getEl(id);
      if (!btn) return;
      if (disabled) {
        btn.disabled = true;
      } else {
        btn.disabled = btn.classList.contains('is-loading');
      }
    });
  }

  function stopPolling() {
    if (pollingTimer) {
      clearInterval(pollingTimer);
      pollingTimer = null;
    }
  }

  function startPolling() {
    stopPolling();
    pollingTimer = setInterval(function() {
      if (!moduleExists() || !moduleVisible()) {
        stopPolling();
        return;
      }
      loadDashboard(false);
      if (state.selectedLinea) {
        loadLineaDetalle(state.selectedLinea, false);
        loadHistorial(false);
        loadEventos(false);
      }
    }, POLL_INTERVAL_MS);
  }

  function getCurrentLinea() {
    var select = getEl('cc-linea-select');
    var fromSelect = select ? String(select.value || '').trim() : '';
    return fromSelect || state.selectedLinea;
  }

  function setSelectedLinea(linea, syncSelect) {
    var value = String(linea || '').trim();
    state.selectedLinea = value;

    if (syncSelect) {
      var select = getEl('cc-linea-select');
      if (select && value) {
        var exists = false;
        for (var i = 0; i < select.options.length; i += 1) {
          if (select.options[i].value === value) {
            exists = true;
            break;
          }
        }
        if (exists) {
          select.value = value;
        }
      }
    }

    renderDashboard(state.dashboardItems || []);
  }

  function estadoBadge(estado) {
    var text = String(estado || '-').trim().toUpperCase();
    if (!text || text === '-') return '-';
    return '<span class="cc-state ' + escapeHtml(text) + '">' + escapeHtml(text) + '</span>';
  }

  function configBadge(config) {
    var isActive = !!(config && Number(config.activo || 0) === 1);
    var cls = isActive ? 'cc-pill ok' : 'cc-pill off';
    return '<span class="' + cls + '">' + (isActive ? 'ACTIVA' : 'INACTIVA') + '</span>';
  }

  function sourceLabel(metric) {
    var m = String(metric || 'PRODUCED_COUNT').toUpperCase();
    if (m === 'PLAN_COUNT') return 'PLAN_COUNT';
    return 'PRODUCED_COUNT';
  }

  function clearEstadoFields() {
    var fields = {
      'cc-plan-lot': '-',
      'cc-plan-status': '-',
      'cc-plan-input': '0',
      'cc-plan-count': '0',
      'cc-source-actual-kpi': '0',
      'cc-source-metric-kpi': 'PRODUCED_COUNT',
      'cc-hourly-sync-at': '-',
      'cc-sesion-id': '-',
      'cc-sesion-blade': '-',
      'cc-sesion-estado': '-',
      'cc-factor': '-',
      'cc-sesion-consumo': '0',
      'cc-sesion-max': '0',
      'cc-sesion-restante': '0',
      'cc-sesion-pct': '0%',
      'cc-config-activo-kpi': '-',
      'cc-diag-source-metric': '-',
      'cc-diag-source-actual': '0',
      'cc-diag-last-snapshot': '0',
      'cc-diag-delta': '0',
      'cc-diag-same-lot': '-',
      'cc-diag-habilitado': '-',
      'cc-diag-motivo': '-'
    };

    Object.keys(fields).forEach(function(id) {
      var el = getEl(id);
      if (!el) return;
      if (id === 'cc-sesion-estado' || id === 'cc-diag-habilitado' || id === 'cc-config-activo-kpi') {
        el.innerHTML = fields[id];
      } else {
        el.textContent = fields[id];
      }
    });
  }

  function fillConfigForm(config, linea) {
    var select = getEl('cc-linea-select');
    if (select && linea) {
      select.value = linea;
    }

    var cfg = config || {};
    var pcbQty = getEl('cc-pcb-qty');
    var cutQty = getEl('cc-cut-qty');
    var prealert = getEl('cc-prealert-pct');
    var source = getEl('cc-source-metric');
    var activo = getEl('cc-config-activo');

    if (pcbQty) pcbQty.value = cfg.pcb_qty != null ? cfg.pcb_qty : 1;
    if (cutQty) cutQty.value = cfg.cut_qty != null ? cfg.cut_qty : 1;
    if (prealert) prealert.value = cfg.prealert_pct != null ? cfg.prealert_pct : 90;
    if (source) source.value = sourceLabel(cfg.source_metric || 'PRODUCED_COUNT');
    if (activo) activo.checked = Number(cfg.activo || 0) === 1;
  }

  // ---- Config por modelo ----

  async function loadModelosLinea(linea) {
    var datalist = getEl('cc-modelo-datalist');
    if (!datalist) return;
    datalist.innerHTML = '';
    if (!linea) return;
    try {
      var resp = await requestApi('GET', '/api/cuchillas-corte/modelos-linea', null, { linea: linea });
      var modelos = Array.isArray(resp.modelos) ? resp.modelos : [];
      modelos.forEach(function(m) {
        var opt = document.createElement('option');
        opt.value = m;
        datalist.appendChild(opt);
      });
    } catch (err) {
      console.warn('Error cargando modelos:', err);
    }
  }

  async function loadConfigModelos(linea) {
    var tbody = getEl('cc-modelos-config-tbody');
    if (!tbody) return;
    if (!linea) {
      tbody.innerHTML = '<tr><td colspan="5" class="cc-empty">Selecciona una linea</td></tr>';
      return;
    }
    try {
      var resp = await requestApi('GET', '/api/cuchillas-corte/config-modelo', null, { linea: linea });
      var modelos = Array.isArray(resp.modelos) ? resp.modelos : [];
      if (!modelos.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="cc-empty">Sin configuraciones de modelo (se usa config de linea)</td></tr>';
        return;
      }
      var html = modelos.map(function(m) {
        var pcb = toNumber(m.pcb_qty, 0);
        var cut = toNumber(m.cut_qty, 0);
        var factor = pcb > 0 ? (cut / pcb) : 0;
        var sinCorte = cut <= 0;
        return [
          '<tr>',
            '<td>', escapeHtml(m.model_code || '-'), '</td>',
            '<td>', formatNumber(pcb, 4), '</td>',
            '<td>', sinCorte ? '<span class="cc-pill off">0 (sin corte)</span>' : formatNumber(cut, 4), '</td>',
            '<td>', formatNumber(factor, 6), '</td>',
            '<td>',
              '<button class="cc-btn danger cc-btn-eliminar-modelo" data-modelo="', escapeHtml(m.model_code), '" style="padding:2px 8px; font-size:11px;">Eliminar</button>',
            '</td>',
          '</tr>'
        ].join('');
      }).join('');
      tbody.innerHTML = html;
    } catch (err) {
      tbody.innerHTML = '<tr><td colspan="5" class="cc-empty">Error cargando modelos</td></tr>';
    }
  }

  async function saveConfigModelo() {
    var linea = getCurrentLinea();
    if (!linea) {
      setStatus('Selecciona una linea', 'warn');
      return;
    }
    var modelInput = getEl('cc-modelo-select');
    var pcbInput = getEl('cc-modelo-pcb-qty');
    var cutInput = getEl('cc-modelo-cut-qty');
    var modelCode = String(modelInput ? modelInput.value : '').trim();
    var pcbQty = toNumber(pcbInput ? pcbInput.value : '', NaN);
    var cutQty = toNumber(cutInput ? cutInput.value : '', NaN);

    if (!modelCode) {
      setStatus('Ingresa un modelo', 'warn');
      return;
    }
    if (!Number.isFinite(pcbQty) || pcbQty <= 0) {
      setStatus('PCB Qty debe ser mayor a 0', 'warn');
      return;
    }
    if (!Number.isFinite(cutQty) || cutQty < 0) {
      setStatus('Cut Qty no puede ser negativo', 'warn');
      return;
    }

    try {
      setButtonLoading('cc-btn-guardar-config-modelo', true, 'Guardando...');
      await requestApi('POST', '/api/cuchillas-corte/config-modelo', {
        linea: linea,
        model_code: modelCode,
        pcb_qty: pcbQty,
        cut_qty: cutQty,
        activo: 1
      });
      setStatus('Config de modelo ' + modelCode + ' guardada', 'ok');
      if (modelInput) modelInput.value = '';
      if (pcbInput) pcbInput.value = '1';
      if (cutInput) cutInput.value = '0';
      await loadConfigModelos(linea);
    } catch (err) {
      setStatus(parseError(err), 'error');
    } finally {
      setButtonLoading('cc-btn-guardar-config-modelo', false);
    }
  }

  async function deleteConfigModelo(linea, modelCode) {
    if (!confirm('Eliminar configuracion del modelo ' + modelCode + '?\nSe usara la config de linea como default.')) return;
    try {
      await requestApi('POST', '/api/cuchillas-corte/config-modelo/eliminar', {
        linea: linea,
        model_code: modelCode
      });
      setStatus('Config de modelo ' + modelCode + ' eliminada', 'ok');
      await loadConfigModelos(linea);
    } catch (err) {
      setStatus(parseError(err), 'error');
    }
  }

  // ---- Fin config por modelo ----

  function renderDashboard(items) {
    var tbody = getEl('cc-dashboard-tbody');
    if (!tbody) return;

    var rows = Array.isArray(items) ? items : [];
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="13" class="cc-empty">No hay lineas configuradas activas</td></tr>';
      return;
    }

    var html = rows.map(function(item) {
      var linea = String(item.linea || '');
      var plan = item.plan_activo || {};
      var sesion = item.sesion || {};
      var diag = item.diagnostico || {};
      var config = item.config || {};
      var selected = linea && linea === state.selectedLinea;
      var rowClass = selected ? 'cc-row-selected' : '';

      var usoPct = sesion.porcentaje_uso != null ? formatNumber(sesion.porcentaje_uso, 2) + '%' : '0%';
      var consumo = formatNumber(sesion.consumo_cortes || 0, 4);
      var maximo = formatNumber(sesion.max_cortes || 0, 4);
      var restante = formatNumber(sesion.restante_cortes || 0, 4);
      var pendExt = formatNumber(item.eventos_vencida_pendientes || 0, 0);

      var cfgEfectiva = item.config_efectiva || {};
      var cfgTipo = cfgEfectiva.config_tipo || 'LINEA';
      var cfgModelCode = cfgEfectiva.config_model_code || '';
      var cfgUsadaLabel = cfgTipo === 'MODELO'
        ? '<span class="cc-pill ok">' + escapeHtml(cfgModelCode) + '</span>'
        : '<span class="cc-pill">LINEA</span>';

      return [
        '<tr class="', rowClass, '" data-cc-linea="', escapeHtml(linea), '">',
          '<td>', escapeHtml(linea || '-'), '</td>',
          '<td>', configBadge(config), '</td>',
          '<td>', escapeHtml(sourceLabel(config.source_metric || diag.source_metric || 'PRODUCED_COUNT')), '</td>',
          '<td>', escapeHtml(plan.lot_no || '-'), '</td>',
          '<td>', escapeHtml(plan.model_code || '-'), '</td>',
          '<td>', cfgUsadaLabel, '</td>',
          '<td>', escapeHtml(plan.status || '-'), '</td>',
          '<td>', escapeHtml(sesion.blade_code || '-'), '</td>',
          '<td>', estadoBadge(sesion.estado), '</td>',
          '<td>', usoPct, '</td>',
          '<td>', consumo, ' / ', maximo, '</td>',
          '<td>', restante, '</td>',
          '<td>', pendExt, '</td>',
        '</tr>'
      ].join('');
    }).join('');

    tbody.innerHTML = html;
  }

  function renderDiagnostico(diag) {
    var d = diag || {};

    var mapText = {
      'cc-diag-source-metric': sourceLabel(d.source_metric || 'PRODUCED_COUNT'),
      'cc-diag-source-actual': formatNumber(d.source_actual || 0, 4),
      'cc-diag-last-snapshot': formatNumber(d.last_input_snapshot || 0, 4),
      'cc-diag-delta': formatNumber(d.delta_estimado || 0, 4),
      'cc-diag-same-lot': d.same_lot ? 'SI' : 'NO',
      'cc-diag-motivo': d.motivo_no_descuento || '-'
    };

    Object.keys(mapText).forEach(function(id) {
      var el = getEl(id);
      if (el) el.textContent = mapText[id];
    });

    var enabledEl = getEl('cc-diag-habilitado');
    if (enabledEl) {
      if (d.consumo_habilitado) {
        enabledEl.innerHTML = '<span class="cc-pill ok">SI</span>';
      } else {
        enabledEl.innerHTML = '<span class="cc-pill off">NO</span>';
      }
    }
  }

  function renderEstado(payload) {
    var plan = (payload && payload.plan_activo) || null;
    var sesion = (payload && payload.sesion) || null;
    var config = (payload && payload.config) || null;
    var diagnostico = (payload && payload.diagnostico) || null;
    var cfgEfectiva = (payload && payload.config_efectiva) || null;

    var cfgTipoEl = getEl('cc-config-tipo-kpi');
    if (cfgTipoEl) {
      if (cfgEfectiva && cfgEfectiva.config_tipo === 'MODELO') {
        cfgTipoEl.innerHTML = '<span class="cc-pill ok">MODELO: ' + escapeHtml(cfgEfectiva.config_model_code || '') + '</span>';
      } else {
        cfgTipoEl.innerHTML = '<span class="cc-pill">LINEA (default)</span>';
      }
    }

    var planLot = getEl('cc-plan-lot');
    var planStatus = getEl('cc-plan-status');
    var planInput = getEl('cc-plan-input');
    var planCount = getEl('cc-plan-count');
    var sourceActual = getEl('cc-source-actual-kpi');
    var sourceMetric = getEl('cc-source-metric-kpi');
    var hourlySyncAt = getEl('cc-hourly-sync-at');
    var sesionId = getEl('cc-sesion-id');
    var sesionBlade = getEl('cc-sesion-blade');
    var sesionEstado = getEl('cc-sesion-estado');
    var sesionConsumo = getEl('cc-sesion-consumo');
    var sesionMax = getEl('cc-sesion-max');
    var sesionRestante = getEl('cc-sesion-restante');
    var sesionPct = getEl('cc-sesion-pct');
    var factor = getEl('cc-factor');
    var cfgActivo = getEl('cc-config-activo-kpi');

    if (planLot) planLot.textContent = plan ? (plan.lot_no || '-') : '-';
    if (planStatus) planStatus.textContent = plan ? (plan.status || '-') : '-';
    if (planInput) planInput.textContent = plan ? formatNumber(plan.produced_count || 0, 4) : '0';
    if (planCount) planCount.textContent = plan ? formatNumber(plan.plan_count || 0, 4) : '0';
    if (sourceMetric) sourceMetric.textContent = sourceLabel((config || {}).source_metric || (diagnostico || {}).source_metric || 'PRODUCED_COUNT');
    if (sourceActual) sourceActual.textContent = diagnostico ? formatNumber(diagnostico.source_actual || 0, 4) : '0';
    if (hourlySyncAt) hourlySyncAt.textContent = sesion ? (sesion.last_hourly_sync_at || '-') : '-';

    if (cfgActivo) {
      cfgActivo.innerHTML = config && Number(config.activo || 0) === 1
        ? '<span class="cc-pill ok">ACTIVA</span>'
        : '<span class="cc-pill off">INACTIVA</span>';
    }

    if (!sesion) {
      if (sesionId) sesionId.textContent = '-';
      if (sesionBlade) sesionBlade.textContent = '-';
      if (sesionEstado) sesionEstado.innerHTML = '-';
      if (sesionConsumo) sesionConsumo.textContent = '0';
      if (sesionMax) sesionMax.textContent = '0';
      if (sesionRestante) sesionRestante.textContent = '0';
      if (sesionPct) sesionPct.textContent = '0%';
      if (factor) factor.textContent = '-';
      renderDiagnostico(diagnostico || {});
      return;
    }

    var estadoText = String(sesion.estado || '-').trim().toUpperCase();
    var consumo = toNumber(sesion.consumo_cortes, 0);
    var maxCortes = toNumber(sesion.max_cortes, 0);
    var restante = toNumber(sesion.restante_cortes, Math.max(0, maxCortes - consumo));
    var pctUso = toNumber(sesion.porcentaje_uso, maxCortes > 0 ? (consumo / maxCortes) * 100 : 0);

    if (sesionId) sesionId.textContent = sesion.id != null ? String(sesion.id) : '-';
    if (sesionBlade) sesionBlade.textContent = sesion.blade_code || '-';
    if (sesionEstado) sesionEstado.innerHTML = estadoBadge(estadoText);
    if (sesionConsumo) sesionConsumo.textContent = formatNumber(consumo, 4);
    if (sesionMax) sesionMax.textContent = formatNumber(maxCortes, 4);
    if (sesionRestante) sesionRestante.textContent = formatNumber(restante, 4);
    if (sesionPct) sesionPct.textContent = formatNumber(pctUso, 2) + '%';
    if (factor) {
      factor.textContent = sesion.factor_corte != null ? formatNumber(sesion.factor_corte, 6) : '-';
    }

    renderDiagnostico(diagnostico || {});
  }

  function renderEventos(eventos) {
    var tbody = getEl('cc-eventos-tbody');
    if (!tbody) return;

    var rows = Array.isArray(eventos) ? eventos : [];
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="cc-empty">Sin eventos para mostrar</td></tr>';
      return;
    }

    var html = rows.map(function(ev) {
      var tipo = String(ev.event_type || '').toUpperCase();
      var consumo = formatNumber(ev.consumo_cortes || 0, 4);
      var max = formatNumber(ev.max_cortes || 0, 4);
      var pct = formatNumber(ev.porcentaje_uso || 0, 2) + '%';
      var pendiente = Number(ev.pendiente_externo || 0) === 1 ? 'SI' : 'NO';
      var rowClass = '';
      if (tipo === 'PREALERTA') rowClass = 'cc-event-PREALERTA';
      if (tipo === 'VENCIDA') rowClass = 'cc-event-VENCIDA';

      return [
        '<tr class="', rowClass, '">',
          '<td>', escapeHtml(ev.created_at || '-'), '</td>',
          '<td>', escapeHtml(tipo || '-'), '</td>',
          '<td>', escapeHtml(ev.linea || '-'), '</td>',
          '<td>', escapeHtml(ev.lot_no || '-'), '</td>',
          '<td>', consumo, ' / ', max, '</td>',
          '<td>', pct, '</td>',
          '<td>', pendiente, '</td>',
          '<td>', escapeHtml(ev.mensaje || '-'), '</td>',
        '</tr>'
      ].join('');
    }).join('');

    tbody.innerHTML = html;
  }

  function renderHistorial(sesiones) {
    var tbody = getEl('cc-historial-tbody');
    if (!tbody) return;

    var rows = Array.isArray(sesiones) ? sesiones : [];
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="cc-empty">Sin historial para mostrar</td></tr>';
      return;
    }

    var html = rows.map(function(item) {
      var estado = String(item.estado || '').toUpperCase();
      var inicio = item.started_at || '-';
      var fin = item.ended_at || item.expired_at || '-';
      var consumo = formatNumber(item.consumo_cortes || 0, 4);
      var maximo = formatNumber(item.max_cortes || 0, 4);
      var uso = formatNumber(item.porcentaje_uso || 0, 2) + '%';

      return [
        '<tr>',
          '<td>', escapeHtml(inicio), '</td>',
          '<td>', escapeHtml(fin), '</td>',
          '<td>', escapeHtml(item.linea || '-'), '</td>',
          '<td>', escapeHtml(item.id != null ? String(item.id) : '-'), '</td>',
          '<td>', escapeHtml(item.blade_code || '-'), '</td>',
          '<td>', estadoBadge(estado), '</td>',
          '<td>', consumo, ' / ', maximo, '</td>',
          '<td>', uso, '</td>',
          '<td>', escapeHtml(item.created_by || '-'), '</td>',
        '</tr>'
      ].join('');
    }).join('');

    tbody.innerHTML = html;
  }

  async function loadLineas(preferredLinea, showAllOverride) {
    var includeAllCheckbox = getEl('cc-show-all-lineas');
    var includeAll = typeof showAllOverride === 'boolean'
      ? showAllOverride
      : !!(includeAllCheckbox && includeAllCheckbox.checked);

    var data = await requestApi('GET', '/api/cuchillas-corte/lineas', null, {
      include_all: includeAll ? 1 : 0
    });

    var lineas = Array.isArray(data.lineas) ? data.lineas : [];
    if (!lineas.length && !includeAll) {
      data = await requestApi('GET', '/api/cuchillas-corte/lineas', null, { include_all: 1 });
      lineas = Array.isArray(data.lineas) ? data.lineas : [];
      if (includeAllCheckbox) includeAllCheckbox.checked = true;
    }

    state.lineas = lineas;

    var select = getEl('cc-linea-select');
    if (select) {
      var current = preferredLinea || state.selectedLinea || select.value || '';
      var options = ['<option value="">Selecciona linea</option>'];
      lineas.forEach(function(linea) {
        options.push('<option value="' + escapeHtml(linea) + '">' + escapeHtml(linea) + '</option>');
      });
      select.innerHTML = options.join('');

      if (lineas.length) {
        if (current && lineas.indexOf(current) >= 0) {
          select.value = current;
        } else {
          select.value = lineas[0];
        }
      }
    }

    return lineas;
  }

  async function loadDashboard(showFeedback) {
    var payload = await requestApi('GET', '/api/cuchillas-corte/dashboard');
    var items = Array.isArray(payload.items) ? payload.items : [];
    state.dashboardItems = items;
    renderDashboard(items);
    if (showFeedback) {
      setStatus('Tablero actualizado (' + nowLabel() + ')', 'ok');
    }
    return items;
  }

  async function loadConfig(linea) {
    var l = String(linea || '').trim();
    if (!l) return null;
    var payload = await requestApi('GET', '/api/cuchillas-corte/config', null, { linea: l });
    fillConfigForm(payload.config || null, l);
    return payload.config || null;
  }

  async function loadLineaDetalle(linea, showFeedback) {
    var l = String(linea || '').trim();
    if (!l) {
      clearEstadoFields();
      return;
    }

    if (showFeedback) {
      setStatus('Cargando detalle de ' + l + '...', 'warn');
    }

    var estadoResp = await requestApi('GET', '/api/cuchillas-corte/estado', null, { linea: l });
    renderEstado(estadoResp);
    fillConfigForm(estadoResp.config || null, l);
    loadModelosLinea(l);
    loadConfigModelos(l);

    if (showFeedback) {
      setStatus('Detalle actualizado (' + nowLabel() + ')', 'ok');
    }
  }

  async function loadEventos(showFeedback) {
    var linea = getCurrentLinea();
    if (!linea) {
      renderEventos([]);
      return;
    }

    var soloPendientes = !!(getEl('cc-solo-pendientes') && getEl('cc-solo-pendientes').checked);
    if (showFeedback) {
      setStatus('Cargando eventos...', 'warn');
    }

    var payload = await requestApi('GET', '/api/cuchillas-corte/eventos', null, {
      linea: linea,
      solo_pendientes: soloPendientes ? 1 : 0
    });
    renderEventos(payload.eventos || []);

    if (showFeedback) {
      setStatus('Eventos actualizados (' + nowLabel() + ')', 'ok');
    }
  }

  async function loadHistorial(showFeedback) {
    var linea = getCurrentLinea();
    if (!linea) {
      state.historialSesiones = [];
      renderHistorial([]);
      return;
    }

    if (showFeedback) {
      setStatus('Cargando historial de cuchillas...', 'warn');
    }

    var payload = await requestApi('GET', '/api/cuchillas-corte/sesiones', null, {
      linea: linea,
      limit: 120
    });
    var sesiones = Array.isArray(payload.sesiones) ? payload.sesiones : [];
    state.historialSesiones = sesiones;
    renderHistorial(sesiones);

    if (showFeedback) {
      setStatus('Historial actualizado (' + nowLabel() + ')', 'ok');
    }
  }

  async function refreshModuleData(preferredLinea, showFeedback) {
    try {
      setButtonsDisabled(true);
      if (showFeedback) {
        setStatus('Sincronizando modulo...', 'warn');
      }

      await loadLineas(preferredLinea);
      await loadDashboard(false);

      var linea = preferredLinea || state.selectedLinea || getCurrentLinea();
      if (!linea) {
        if (state.dashboardItems.length) {
          linea = state.dashboardItems[0].linea;
        } else if (state.lineas.length) {
          linea = state.lineas[0];
        }
      }

      setSelectedLinea(linea || '', true);

      if (linea) {
        await loadLineaDetalle(linea, false);
        await loadHistorial(false);
        await loadEventos(false);
        startPolling();
        if (showFeedback) {
          setStatus('Modulo listo (' + nowLabel() + ')', 'ok');
        }
      } else {
        stopPolling();
        clearEstadoFields();
        state.historialSesiones = [];
        renderHistorial([]);
        renderEventos([]);
        if (showFeedback) {
          setStatus('No hay lineas disponibles', 'warn');
        }
      }
    } catch (error) {
      setStatus(parseError(error), 'error');
    } finally {
      setButtonsDisabled(false);
    }
  }

  async function saveConfig() {
    var linea = getCurrentLinea();
    var actionBtnId = 'cc-btn-guardar-config';
    if (!linea) {
      setStatus('Selecciona una linea', 'warn');
      return;
    }

    var pcbQty = toNumber(getEl('cc-pcb-qty') ? getEl('cc-pcb-qty').value : null, NaN);
    var cutQty = toNumber(getEl('cc-cut-qty') ? getEl('cc-cut-qty').value : null, NaN);
    var prealertPct = toNumber(getEl('cc-prealert-pct') ? getEl('cc-prealert-pct').value : null, NaN);
    var sourceMetric = getEl('cc-source-metric') ? String(getEl('cc-source-metric').value || '').trim().toUpperCase() : 'PRODUCED_COUNT';
    var activo = !!(getEl('cc-config-activo') && getEl('cc-config-activo').checked);

    if (!(pcbQty > 0)) {
      setStatus('pcb_qty debe ser mayor a 0', 'warn');
      return;
    }
    if (!(cutQty > 0)) {
      setStatus('cut_qty debe ser mayor a 0', 'warn');
      return;
    }
    if (!(prealertPct > 0 && prealertPct <= 100)) {
      setStatus('prealert_pct debe estar entre 0 y 100', 'warn');
      return;
    }
    if (sourceMetric !== 'PRODUCED_COUNT' && sourceMetric !== 'PLAN_COUNT') {
      setStatus('source_metric invalido', 'warn');
      return;
    }

    try {
      setButtonsDisabled(true);
      setButtonLoading(actionBtnId, true, 'Guardando...');
      setStatus('Guardando configuracion...', 'warn');
      await requestApi('POST', '/api/cuchillas-corte/config', {
        linea: linea,
        pcb_qty: pcbQty,
        cut_qty: cutQty,
        prealert_pct: prealertPct,
        source_metric: sourceMetric,
        activo: activo ? 1 : 0
      });
      await refreshModuleData(linea, true);
    } catch (error) {
      setStatus(parseError(error), 'error');
    } finally {
      setButtonsDisabled(false);
      setButtonLoading(actionBtnId, false);
    }
  }

  async function iniciarSesionCuchilla() {
    var linea = getCurrentLinea();
    var actionBtnId = 'cc-btn-iniciar-sesion';
    var bladeCode = getEl('cc-blade-code') ? getEl('cc-blade-code').value.trim() : '';
    var maxCortes = toNumber(getEl('cc-max-cortes') ? getEl('cc-max-cortes').value : null, NaN);

    if (!linea) {
      setStatus('Selecciona una linea', 'warn');
      return;
    }
    if (!bladeCode) {
      setStatus('Blade code es requerido', 'warn');
      return;
    }
    if (!(maxCortes > 0)) {
      setStatus('max_cortes debe ser mayor a 0', 'warn');
      return;
    }

    try {
      setButtonsDisabled(true);
      setButtonLoading(actionBtnId, true, 'Iniciando...');
      setStatus('Iniciando sesion...', 'warn');
      await requestApi('POST', '/api/cuchillas-corte/sesion/iniciar', {
        linea: linea,
        blade_code: bladeCode,
        max_cortes: maxCortes
      });

      if (getEl('cc-blade-code')) getEl('cc-blade-code').value = '';
      if (getEl('cc-max-cortes')) getEl('cc-max-cortes').value = '';

      await refreshModuleData(linea, true);
    } catch (error) {
      setStatus(parseError(error), 'error');
    } finally {
      setButtonsDisabled(false);
      setButtonLoading(actionBtnId, false);
    }
  }

  async function reemplazarSesionCuchilla() {
    var linea = getCurrentLinea();
    var actionBtnId = 'cc-btn-reemplazar-sesion';
    var bladeCode = getEl('cc-blade-code') ? getEl('cc-blade-code').value.trim() : '';
    var maxCortes = toNumber(getEl('cc-max-cortes') ? getEl('cc-max-cortes').value : null, NaN);

    if (!linea) {
      setStatus('Selecciona una linea', 'warn');
      return;
    }
    if (!bladeCode) {
      setStatus('Blade code es requerido', 'warn');
      return;
    }
    if (!(maxCortes > 0)) {
      setStatus('max_cortes debe ser mayor a 0', 'warn');
      return;
    }

    if (!window.confirm('Se reemplazara la cuchilla activa en ' + linea + '. Continuar?')) {
      return;
    }

    try {
      setButtonsDisabled(true);
      setButtonLoading(actionBtnId, true, 'Reemplazando...');
      setStatus('Reemplazando cuchilla...', 'warn');
      await requestApi('POST', '/api/cuchillas-corte/sesion/reemplazar', {
        linea: linea,
        blade_code: bladeCode,
        max_cortes: maxCortes
      });

      if (getEl('cc-blade-code')) getEl('cc-blade-code').value = '';
      if (getEl('cc-max-cortes')) getEl('cc-max-cortes').value = '';

      await refreshModuleData(linea, true);
    } catch (error) {
      setStatus(parseError(error), 'error');
    } finally {
      setButtonsDisabled(false);
      setButtonLoading(actionBtnId, false);
    }
  }

  async function eliminarSesionCuchilla() {
    var linea = getCurrentLinea();
    var actionBtnId = 'cc-btn-eliminar-sesion';
    var sesionIdText = getEl('cc-sesion-id') ? String(getEl('cc-sesion-id').textContent || '').trim() : '';
    var bladeCode = getEl('cc-sesion-blade') ? String(getEl('cc-sesion-blade').textContent || '').trim() : '';
    var sesionId = Number(sesionIdText);

    if (!linea) {
      setStatus('Selecciona una linea', 'warn');
      return;
    }

    if (!Number.isFinite(sesionId) || sesionId <= 0) {
      setStatus('No hay sesion de cuchilla para eliminar', 'warn');
      return;
    }

    var confirmMsg = 'Se eliminara la cuchilla actual de ' + linea + ' (Sesion ' + sesionId + '). Esta accion borra su historial de eventos. Continuar?';
    if (!window.confirm(confirmMsg)) {
      return;
    }

    try {
      setButtonsDisabled(true);
      setButtonLoading(actionBtnId, true, 'Eliminando...');
      setStatus('Eliminando cuchilla...', 'warn');

      await requestApi('POST', '/api/cuchillas-corte/sesion/eliminar', {
        linea: linea,
        sesion_id: sesionId
      });

      if (getEl('cc-blade-code')) getEl('cc-blade-code').value = '';
      if (getEl('cc-max-cortes')) getEl('cc-max-cortes').value = '';

      await refreshModuleData(linea, false);
      setStatus(
        'Cuchilla eliminada: ' + (bladeCode || ('Sesion ' + sesionId)) + ' (' + nowLabel() + ')',
        'ok'
      );
    } catch (error) {
      setStatus(parseError(error), 'error');
    } finally {
      setButtonsDisabled(false);
      setButtonLoading(actionBtnId, false);
    }
  }

  async function recalcularConsumo() {
    var linea = getCurrentLinea();
    var actionBtnId = 'cc-btn-recalcular';
    if (!linea) {
      setStatus('Selecciona una linea', 'warn');
      return;
    }

    try {
      setButtonsDisabled(true);
      setButtonLoading(actionBtnId, true, 'Recalculando...');
      setStatus('Aplicando recalculo...', 'warn');
      var resp = await requestApi('POST', '/api/cuchillas-corte/recalcular', { linea: linea });
      await refreshModuleData(linea, false);
      if (resp && resp.aplico_cambios) {
        setStatus('Recalculo aplicado (' + nowLabel() + ')', 'ok');
      } else {
        setStatus((resp && resp.mensaje) || 'Sin cambios en recalculo', 'warn');
      }
    } catch (error) {
      setStatus(parseError(error), 'error');
    } finally {
      setButtonsDisabled(false);
      setButtonLoading(actionBtnId, false);
    }
  }

  async function onLineaChanged() {
    var linea = getCurrentLinea();
    setSelectedLinea(linea, true);
    if (!linea) {
      clearEstadoFields();
      state.historialSesiones = [];
      renderHistorial([]);
      renderEventos([]);
      return;
    }

    try {
      setStatus('Cargando linea ' + linea + '...', 'warn');
      await loadLineaDetalle(linea, false);
      await loadHistorial(false);
      await loadEventos(false);
      loadModelosLinea(linea);
      loadConfigModelos(linea);
      setStatus('Linea ' + linea + ' lista', 'ok');
    } catch (error) {
      setStatus(parseError(error), 'error');
    }
  }

  function handleDashboardRowClick(target) {
    var row = target.closest('[data-cc-linea]');
    if (!row) return false;
    var linea = String(row.getAttribute('data-cc-linea') || '').trim();
    if (!linea) return false;

    setSelectedLinea(linea, true);
    loadLineaDetalle(linea, true);
    loadHistorial(false);
    loadEventos(false);
    loadModelosLinea(linea);
    loadConfigModelos(linea);
    return true;
  }

  function handleDocumentClick(e) {
    var target = e.target;
    if (!target) return;

    if (
      target.id === 'cc-btn-close-config-modal' ||
      target.closest('#cc-btn-close-config-modal') ||
      target.closest('[data-cc-modal-close]')
    ) {
      e.preventDefault();
      setConfigModalOpen(false);
      return;
    }

    if (!moduleExists()) return;

    if (target.id === 'cc-btn-open-config-modal' || target.closest('#cc-btn-open-config-modal')) {
      e.preventDefault();
      setConfigModalOpen(true);
      return;
    }

    if (handleDashboardRowClick(target)) {
      return;
    }

    if (target.id === 'cc-btn-recargar-lineas' || target.closest('#cc-btn-recargar-lineas')) {
      e.preventDefault();
      (async function() {
        try {
          setButtonLoading('cc-btn-recargar-lineas', true, 'Recargando...');
          await refreshModuleData(getCurrentLinea(), true);
        } finally {
          setButtonLoading('cc-btn-recargar-lineas', false);
        }
      })();
      return;
    }

    if (target.id === 'cc-btn-refrescar-dashboard' || target.closest('#cc-btn-refrescar-dashboard')) {
      e.preventDefault();
      (async function() {
        try {
          setButtonsDisabled(true);
          setButtonLoading('cc-btn-refrescar-dashboard', true, 'Cargando...');
          setStatus('Actualizando tablero...', 'warn');
          await loadDashboard(true);
        } catch (error) {
          setStatus(parseError(error), 'error');
        } finally {
          setButtonsDisabled(false);
          setButtonLoading('cc-btn-refrescar-dashboard', false);
        }
      })();
      return;
    }

    if (target.id === 'cc-btn-guardar-config' || target.closest('#cc-btn-guardar-config')) {
      e.preventDefault();
      saveConfig();
      return;
    }

    if (target.id === 'cc-btn-guardar-config-modelo' || target.closest('#cc-btn-guardar-config-modelo')) {
      e.preventDefault();
      saveConfigModelo();
      return;
    }

    if (target.classList.contains('cc-btn-eliminar-modelo') || target.closest('.cc-btn-eliminar-modelo')) {
      e.preventDefault();
      var btn = target.classList.contains('cc-btn-eliminar-modelo') ? target : target.closest('.cc-btn-eliminar-modelo');
      var modelo = btn ? btn.getAttribute('data-modelo') : '';
      var linea = getCurrentLinea();
      if (modelo && linea) {
        deleteConfigModelo(linea, modelo);
      }
      return;
    }

    if (target.id === 'cc-btn-iniciar-sesion' || target.closest('#cc-btn-iniciar-sesion')) {
      e.preventDefault();
      iniciarSesionCuchilla();
      return;
    }

    if (target.id === 'cc-btn-reemplazar-sesion' || target.closest('#cc-btn-reemplazar-sesion')) {
      e.preventDefault();
      reemplazarSesionCuchilla();
      return;
    }

    if (target.id === 'cc-btn-eliminar-sesion' || target.closest('#cc-btn-eliminar-sesion')) {
      e.preventDefault();
      eliminarSesionCuchilla();
      return;
    }

    if (target.id === 'cc-btn-refrescar-estado' || target.closest('#cc-btn-refrescar-estado')) {
      e.preventDefault();
      (async function() {
        if (!state.selectedLinea) {
          setStatus('Selecciona una linea', 'warn');
          return;
        }
        try {
          setButtonsDisabled(true);
          setButtonLoading('cc-btn-refrescar-estado', true, 'Cargando...');
          await loadLineaDetalle(state.selectedLinea, true);
        } catch (error) {
          setStatus(parseError(error), 'error');
        } finally {
          setButtonsDisabled(false);
          setButtonLoading('cc-btn-refrescar-estado', false);
        }
      })();
      return;
    }

    if (target.id === 'cc-btn-refrescar-historial' || target.closest('#cc-btn-refrescar-historial')) {
      e.preventDefault();
      (async function() {
        try {
          setButtonsDisabled(true);
          setButtonLoading('cc-btn-refrescar-historial', true, 'Cargando...');
          await loadHistorial(true);
        } catch (error) {
          setStatus(parseError(error), 'error');
        } finally {
          setButtonsDisabled(false);
          setButtonLoading('cc-btn-refrescar-historial', false);
        }
      })();
      return;
    }

    if (target.id === 'cc-btn-recalcular' || target.closest('#cc-btn-recalcular')) {
      e.preventDefault();
      recalcularConsumo();
      return;
    }

    if (target.id === 'cc-btn-refrescar-eventos' || target.closest('#cc-btn-refrescar-eventos')) {
      e.preventDefault();
      (async function() {
        try {
          setButtonsDisabled(true);
          setButtonLoading('cc-btn-refrescar-eventos', true, 'Cargando...');
          await loadEventos(true);
        } catch (error) {
          setStatus(parseError(error), 'error');
        } finally {
          setButtonsDisabled(false);
          setButtonLoading('cc-btn-refrescar-eventos', false);
        }
      })();
      return;
    }
  }

  function handleDocumentChange(e) {
    if (!moduleExists()) return;

    if (e.target && e.target.id === 'cc-linea-select') {
      onLineaChanged();
      return;
    }

    if (e.target && e.target.id === 'cc-solo-pendientes') {
      loadEventos(true);
      return;
    }

    if (e.target && e.target.id === 'cc-show-all-lineas') {
      refreshModuleData(getCurrentLinea(), true);
    }
  }

  function handleDocumentKeydown(e) {
    if (!e || e.key !== 'Escape') return;

    var modal = document.getElementById('cc-config-modal');
    if (modal && modal.classList.contains('is-open')) {
      setConfigModalOpen(false);
    }
  }

  function initializeControlCuchillasCorteEventListeners() {
    if (!document.body.dataset.controlCuchillasCorteListenersAttached) {
      document.body.addEventListener('click', handleDocumentClick);
      document.body.addEventListener('change', handleDocumentChange);
      document.body.addEventListener('keydown', handleDocumentKeydown);
      document.body.dataset.controlCuchillasCorteListenersAttached = 'true';
    }
  }

  async function cuchillasCorteLoadInitialData(forceReload) {
    if (!moduleExists()) return;

    var root = getEl(MODULE_ROOT_ID);
    if (!root) return;

    if (!forceReload && root.dataset.ccLoaded === '1') {
      return;
    }

    root.dataset.ccLoaded = '1';
    ensureConfigModalInBody();
    setConfigModalOpen(false);
    await refreshModuleData('', true);
  }

  window.initializeControlCuchillasCorteEventListeners = initializeControlCuchillasCorteEventListeners;
  window.cuchillasCorteLoadInitialData = cuchillasCorteLoadInitialData;
  window.refreshCuchillasCorteDashboard = loadDashboard;
  window.saveCuchillasConfig = saveConfig;
  window.iniciarSesionCuchilla = iniciarSesionCuchilla;
  window.reemplazarSesionCuchilla = reemplazarSesionCuchilla;
  window.eliminarSesionCuchilla = eliminarSesionCuchilla;
  window.recalcularCuchillasConsumo = recalcularConsumo;

  if (document.readyState === 'interactive' || document.readyState === 'complete') {
    initializeControlCuchillasCorteEventListeners();
  } else {
    document.addEventListener('DOMContentLoaded', initializeControlCuchillasCorteEventListeners);
  }
})();
