/* ============================================================
 * Historial Cambios Parametros ICT - JS del modulo
 * Cargado dinamicamente vIa cargarContenidoDinamico() / ejecutarScriptsDinamicos()
 * ============================================================ */
(function () {
  'use strict';

  /* ===== HELPERS ===== */
  function el(id) { return document.getElementById(id); }

  function escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ===== ESTADO UI ===== */
  function mostrarCargando(v) {
    var loading = el('cp-table-loading');
    if (loading) loading.classList.toggle('active', v);
  }

  function mostrarSinDatos(v) {
    var nd = el('cp-no-data');
    if (nd) nd.style.display = v ? 'block' : 'none';
  }

  function setNoDataMessage(main, detail) {
    var nd = el('cp-no-data');
    if (!nd) return;
    var ps = nd.querySelectorAll('p');
    if (ps[0]) ps[0].textContent = main;
    if (ps[1]) ps[1].textContent = detail || '';
  }

  function actualizarContador(n) {
    var cnt = el('cp-record-count');
    if (cnt) cnt.textContent = n + ' registro' + (n !== 1 ? 's' : '');
  }

  function mostrarWarnings(warnings) {
    var box = el('cp-warning-box');
    if (!box) return;
    if (!warnings || warnings.length === 0) {
      box.style.display = 'none';
      box.innerHTML = '';
      return;
    }
    box.innerHTML = warnings.slice(0, 5).map(escHtml).join('<br>');
    if (warnings.length > 5) {
      box.innerHTML += '<br>' + escHtml('+' + (warnings.length - 5) + ' advertencias mas.');
    }
    box.style.display = 'block';
  }

  function mostrarMeta(meta) {
    var line = el('cp-meta-line');
    if (!line) return;
    if (!meta) {
      line.style.display = 'none';
      line.textContent = '';
      return;
    }
    line.textContent =
      'Archivos consultados: ' + (meta.archivos_consultados || 0) +
      ' | Unicos: ' + (meta.archivos_unicos || 0) +
      ' | Leidos: ' + (meta.archivos_leidos || 0) +
      ' | Snapshots: ' + (meta.snapshots || 0) +
      ' | Cambios: ' + (meta.eventos || 0);
    line.style.display = 'block';
  }

  /* ===== BARRA DE PROGRESO ===== */
  var PHASE_LABELS = {
    'iniciando':           'Iniciando',
    'consultando_db':      'Consultando base de datos',
    'parseando_archivos':  'Comparando datos',
    'detectando_cambios':  'Detectando cambios',
    'completado':          'Completado',
    'desconocido':         'Iniciando'
  };

  function mostrarProgreso(visible) {
    var box = el('cp-progress');
    if (box) box.style.display = visible ? 'flex' : 'none';
    if (visible) actualizarProgreso(0, 0, 'iniciando');
  }

  function actualizarProgreso(done, total, phase) {
    var fill = el('cp-progress-fill');
    var label = el('cp-progress-label');
    var pct = total > 0 ? Math.min(100, Math.floor((done / total) * 100)) : 0;
    if (phase === 'completado') pct = 100;
    if (fill) fill.style.width = pct + '%';
    if (label) {
      var phaseTxt = PHASE_LABELS[phase] || phase || 'Procesando';
      if (total > 0) {
        label.textContent = phaseTxt + ' ' + done + '/' + total + ' (' + pct + '%)';
      } else {
        label.textContent = phaseTxt + (pct ? ' (' + pct + '%)' : '…');
      }
    }
  }

  function newProgressId() {
    return 'pc-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8);
  }

  function startProgressPolling(progressId) {
    var stopped = false;
    var timer = null;

    function poll() {
      if (stopped) return;
      fetch('/api/ict/param-changes/progress?id=' + encodeURIComponent(progressId), {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      })
        .then(function (r) { return r.json(); })
        .then(function (s) {
          if (stopped) return;
          actualizarProgreso(s.done || 0, s.total || 0, s.phase || '');
        })
        .catch(function () { /* ignorar errores transitorios */ })
        .then(function () {
          if (!stopped) timer = setTimeout(poll, 400);
        });
    }

    timer = setTimeout(poll, 200);
    return function stop() {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }

  /* ===== CONSTRUIR PARAMS ===== */
  function buildParams() {
    var p = new URLSearchParams();
    var dia    = el('cp-filter-dia');
    var ict    = el('cp-filter-ict');
    var noParte = el('cp-filter-no-parte');
    var comp   = el('cp-filter-componente');
    var param  = el('cp-filter-parametro');

    if (dia && dia.value) {
      p.set('fecha_desde', dia.value);
      p.set('fecha_hasta', dia.value);
    }
    if (ict && ict.value === 'ALL') {
      p.set('ict_all', '1');
    } else if (ict && ict.value.trim()) {
      p.set('ict', ict.value.trim());
    }
    if (noParte && noParte.value.trim()) p.set('no_parte', noParte.value.trim());
    if (comp  && comp.value.trim()) p.set('componente', comp.value.trim());
    if (param && param.value.trim()) p.set('parametro', param.value.trim());

    return p;
  }

  /* ===== RENDERIZAR FILA ===== */
  function renderFila(row, idx) {
    var tr = document.createElement('tr');
    var vAnterior = row.valor_anterior != null ? row.valor_anterior : '';
    var vNuevo    = row.valor_nuevo    != null ? row.valor_nuevo    : '';

    tr.innerHTML =
      '<td class="cp-row-num">' + idx + '</td>' +
      '<td>' + escHtml(row.jornada || row.fecha || '') + '</td>' +
      '<td>' + escHtml(row.hora  || '') + '</td>' +
      '<td class="cp-col-ict">'  + escHtml(row.ict        || '') + '</td>' +
      '<td title="' + escHtml(row.no_parte || row.std || '') + '">' + escHtml(row.no_parte || row.std || '') + '</td>' +
      '<td>' + escHtml(row.componente || '') + '</td>' +
      '<td class="cp-col-param">' + escHtml(row.parametro  || '') + '</td>' +
      '<td><span class="cp-val-old" title="' + escHtml(vAnterior) + '">' + escHtml(vAnterior || '—') + '</span></td>' +
      '<td><span class="cp-val-new" title="' + escHtml(vNuevo)    + '">' + escHtml(vNuevo    || '—') + '</span></td>';

    tr.innerHTML += '<td title="' + escHtml(row.archivo || '') + '">' + escHtml(row.archivo || '') + '</td>';
    return tr;
  }

  /* ===== CARGAR DATOS ===== */
  function loadCambiosParametrosICT() {
    var params = buildParams();
    var ict = el('cp-filter-ict');
    if (!ict || !ict.value.trim()) {
      actualizarContador(0);
      var tableElRequired = el('cp-params-table');
      if (tableElRequired) tableElRequired.style.display = 'none';
      setNoDataMessage('ICT es requerido.', 'Seleccione una ICT del catalogo o "Todas (puede tardar)".');
      mostrarSinDatos(true);
      mostrarWarnings([]);
      mostrarMeta(null);
      return;
    }

    var progressId = newProgressId();
    params.set('progress_id', progressId);

    mostrarCargando(true);
    mostrarProgreso(true);
    mostrarSinDatos(false);
    setNoDataMessage('No se encontraron registros con los filtros aplicados.', 'Ajuste los filtros y vuelva a consultar.');
    if (ict.value === 'ALL') {
      mostrarWarnings(['Consulta sobre todas las ICTs: puede tardar varios minutos. Considere filtrar por No Parte para acelerar.']);
    } else {
      mostrarWarnings([]);
    }
    mostrarMeta(null);

    var tbody = el('cp-params-body');
    if (tbody) tbody.innerHTML = '';

    var tableEl = el('cp-params-table');

    var stopPoll = startProgressPolling(progressId);

    fetch('/api/ict/param-changes?' + params.toString(), {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    })
    .then(function (res) {
      return res.json().catch(function () {
        return { error: 'HTTP ' + res.status };
      }).then(function (payload) {
        if (!res.ok) throw new Error(payload.error || ('HTTP ' + res.status));
        return payload;
      });
    })
    .then(function (data) {
      stopPoll();
      actualizarProgreso(1, 1, 'completado');
      setTimeout(function () { mostrarProgreso(false); }, 250);
      mostrarCargando(false);
      var rows = Array.isArray(data) ? data : (data.data || data.rows || []);
      mostrarWarnings(Array.isArray(data.warnings) ? data.warnings : []);
      mostrarMeta(data.meta || null);

      actualizarContador(rows.length);

      if (rows.length === 0) {
        if (tableEl) tableEl.style.display = 'none';
        mostrarSinDatos(true);
        return;
      }

      if (tableEl) tableEl.style.display = '';
      mostrarSinDatos(false);

      rows.forEach(function (row, idx) {
        if (tbody) tbody.appendChild(renderFila(row, idx + 1));
      });
    })
    .catch(function (err) {
      stopPoll();
      mostrarProgreso(false);
      console.error('[CambiosICT] Error:', err);
      mostrarCargando(false);
      if (tableEl) tableEl.style.display = 'none';
      mostrarSinDatos(true);
      setNoDataMessage(err.message || 'Error al cargar los datos.', 'Verifique los filtros y vuelva a consultar.');
    });
  }

  /* ===== EXPORTAR ===== */
  function exportarExcel() {
    var ict = el('cp-filter-ict');
    if (!ict || !ict.value.trim()) {
      setNoDataMessage('ICT es requerido.', 'Seleccione una ICT del catalogo o "Todas (puede tardar)" antes de exportar.');
      mostrarSinDatos(true);
      return;
    }
    var params = buildParams();
    window.location.href = '/api/ict/param-changes/export?' + params.toString();
  }

  /* ===== INIT ===== */
  function initializeCambiosParametrosICT() {
    /* Ocultar tabla inicialmente */
    var tableEl = el('cp-params-table');
    if (tableEl) tableEl.style.display = 'none';

    /* Fecha de hoy por defecto */
    var hoy = new Date().toISOString().split('T')[0];
    var dia = el('cp-filter-dia');
    if (dia && !dia.value) dia.value = hoy;

    /* Boton consultar */
    var btnConsultar = el('cp-btn-consultar');
    if (btnConsultar) {
      btnConsultar.addEventListener('click', loadCambiosParametrosICT);
    }

    /* Boton exportar */
    var btnExport = el('cp-btn-export');
    if (btnExport) {
      btnExport.addEventListener('click', exportarExcel);
    }

    /* Enter en cualquier input dispara consulta */
    var inputIds = [
      'cp-filter-dia',
      'cp-filter-no-parte',
      'cp-filter-componente',  'cp-filter-parametro'
    ];
    inputIds.forEach(function (id) {
      var inp = el(id);
      if (inp) {
        inp.addEventListener('keydown', function (e) {
          if (e.key === 'Enter') loadCambiosParametrosICT();
        });
      }
    });

    /* Cambio en el dropdown ICT:
       - Si es "Todas" mostrar advertencia y NO consultar automaticamente
         (forzar al usuario a confirmar dando click a Consultar).
       - Si es una ICT especifica, consultar inmediatamente. */
    var ictSel = el('cp-filter-ict');
    if (ictSel) {
      ictSel.addEventListener('change', function () {
        if (ictSel.value === 'ALL') {
          mostrarWarnings(['Consulta sobre todas las ICTs: puede tardar varios minutos. De click a Consultar para ejecutar.']);
          return;
        }
        if (!ictSel.value) {
          mostrarWarnings([]);
          return;
        }
        loadCambiosParametrosICT();
      });
    }

    mostrarSinDatos(true);
  }

  /* ===== EXPONER GLOBALMENTE ===== */
  window.initializeCambiosParametrosICT = initializeCambiosParametrosICT;
  window.loadCambiosParametrosICT       = loadCambiosParametrosICT;

  /* ===== AUTO-INIT ===== */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeCambiosParametrosICT);
  } else {
    initializeCambiosParametrosICT();
  }

})();
