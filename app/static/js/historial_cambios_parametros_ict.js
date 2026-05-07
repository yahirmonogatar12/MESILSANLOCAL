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
      'Grupos: ' + (meta.grupos_total || 0) +
      ' | Con cambios: ' + (meta.grupos_con_cambios || 0) +
      ' | Archivos parseados: ' + (meta.archivos_leidos || 0) +
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
    var hd     = el('cp-filter-hora-desde');
    var hh     = el('cp-filter-hora-hasta');

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
    if (hd && hd.value) p.set('hora_desde', hd.value);
    if (hh && hh.value) p.set('hora_hasta', hh.value);

    return p;
  }

  /* ===== RENDERIZAR FILA ===== */
  function renderFila(row, idx) {
    var tr = document.createElement('tr');
    var vAnterior = row.valor_anterior != null ? row.valor_anterior : '';
    var vNuevo    = row.valor_nuevo    != null ? row.valor_nuevo    : '';
    var horaAnt   = row.hora_anterior || '';
    var horaCam   = row.hora_cambio   || '';

    tr.setAttribute('data-linea',            row.linea || '');
    tr.setAttribute('data-ict',              row.ict_num != null ? row.ict_num : '');
    tr.setAttribute('data-noparte',          row.no_parte || row.std || '');
    tr.setAttribute('data-componente',       row.componente || '');
    tr.setAttribute('data-componente-raw',   row.componente_raw || '');
    tr.setAttribute('data-pinref',           row.pinref || '');
    tr.setAttribute('data-parametro',        row.parametro || '');
    tr.setAttribute('data-field',            row.field_key || '');
    tr.setAttribute('data-valor-anterior',   vAnterior);
    tr.setAttribute('data-valor-nuevo',      vNuevo);
    tr.setAttribute('data-jornada',          row.jornada || '');
    tr.setAttribute('data-hora-anterior',    horaAnt);
    tr.setAttribute('data-hora-cambio',      horaCam);
    tr.setAttribute('data-archivo-anterior', row.archivo_anterior || '');
    tr.setAttribute('data-archivo-cambio',   row.archivo_cambio   || '');
    tr.setAttribute('data-barcode-anterior', row.barcode_anterior || '');
    tr.setAttribute('data-barcode-cambio',   row.barcode_cambio   || '');

    tr.innerHTML =
      '<td class="cp-row-num">' + idx + '</td>' +
      '<td>' + escHtml(row.jornada || '') + '</td>' +
      '<td class="cp-col-hora-cambio">' + escHtml(horaCam) + '</td>' +
      '<td class="cp-col-ict">'  + escHtml(row.ict || '') + '</td>' +
      '<td title="' + escHtml(row.no_parte || row.std || '') + '">' + escHtml(row.no_parte || row.std || '') + '</td>' +
      '<td title="' + escHtml(row.componente || '') + '">' + escHtml(row.componente || '') + '</td>' +
      '<td class="cp-col-param">' + escHtml(row.parametro  || '') + '</td>' +
      '<td><span class="cp-val-old" title="' + escHtml(vAnterior) + '">' + escHtml(vAnterior || '—') + '</span></td>' +
      '<td><span class="cp-val-new" title="' + escHtml(vNuevo)    + '">' + escHtml(vNuevo    || '—') + '</span></td>' +
      '<td><span class="cp-row-num">ver…</span></td>';

    return tr;
  }

  /* ===== CARGAR DATOS ===== */
  // Token incremental para descartar respuestas obsoletas si se disparan
  // varios fetch en paralelo (proteccion ante double-binding o re-clicks).
  var _requestSeq = 0;

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

    var mySeq = ++_requestSeq;

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
      // Si llegamos tarde (otro fetch mas reciente ya esta en curso),
      // descartar este resultado para evitar apilar filas.
      if (mySeq !== _requestSeq) return;
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

      // Garantia extra: limpiar tbody justo antes de pintar para evitar
      // restos si por alguna razon llegaron filas previas.
      if (tbody) tbody.innerHTML = '';
      var frag = document.createDocumentFragment();
      rows.forEach(function (row, idx) {
        frag.appendChild(renderFila(row, idx + 1));
      });
      if (tbody) tbody.appendChild(frag);
    })
    .catch(function (err) {
      if (mySeq !== _requestSeq) return;
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

  /* ===== MODAL DETALLE ===== */
  function abrirModalDetalle() {
    var ov = el('cp-modal-detalle');
    if (ov) ov.classList.add('active');
  }

  function cerrarModalDetalle() {
    var ov = el('cp-modal-detalle');
    if (ov) ov.classList.remove('active');
  }

  function setModalSpinner(visible) {
    var sp = el('cp-modal-spinner');
    if (sp) sp.style.display = visible ? 'block' : 'none';
  }

  function setModalContent(html) {
    var c = el('cp-modal-content');
    if (c) {
      c.innerHTML = html || '';
      c.style.display = html ? 'block' : 'none';
    }
  }

  function setModalError(msg) {
    var e = el('cp-modal-error');
    if (!e) return;
    if (!msg) {
      e.style.display = 'none';
      e.textContent = '';
      return;
    }
    e.textContent = msg;
    e.style.display = 'block';
  }

  function buildDetalleHtmlFromRow(tr) {
    var jornada       = tr.getAttribute('data-jornada')          || '';
    var ict           = tr.getAttribute('data-ict')              || '';
    var linea         = tr.getAttribute('data-linea')            || '';
    var noParte       = tr.getAttribute('data-noparte')          || '';
    var componente    = tr.getAttribute('data-componente')       || '';
    var parametro     = tr.getAttribute('data-parametro')        || '';
    var vAnt          = tr.getAttribute('data-valor-anterior')   || '';
    var vNue          = tr.getAttribute('data-valor-nuevo')      || '';
    var horaAnt       = tr.getAttribute('data-hora-anterior')    || '';
    var horaCam       = tr.getAttribute('data-hora-cambio')      || '';
    var archivoAnt    = tr.getAttribute('data-archivo-anterior') || '';
    var archivoCam    = tr.getAttribute('data-archivo-cambio')   || '';
    var barcodeAnt    = tr.getAttribute('data-barcode-anterior') || '';
    var barcodeCam    = tr.getAttribute('data-barcode-cambio')   || '';

    return (
      '<div class="cp-modal-row"><span class="cp-modal-key">Jornada</span>' +
        '<span class="cp-modal-val">' + escHtml(jornada) + '</span></div>' +
      '<div class="cp-modal-row"><span class="cp-modal-key">ICT / Linea</span>' +
        '<span class="cp-modal-val">' + escHtml(ict) + ' (' + escHtml(linea) + ')</span></div>' +
      '<div class="cp-modal-row"><span class="cp-modal-key">No Parte</span>' +
        '<span class="cp-modal-val">' + escHtml(noParte) + '</span></div>' +
      '<div class="cp-modal-row"><span class="cp-modal-key">Componente</span>' +
        '<span class="cp-modal-val">' + escHtml(componente) + '</span></div>' +
      '<div class="cp-modal-row"><span class="cp-modal-key">Parametro</span>' +
        '<span class="cp-modal-val">' + escHtml(parametro) + ': ' +
        escHtml(vAnt || '—') + ' → ' + escHtml(vNue || '—') + '</span></div>' +
      '<div class="cp-modal-row"><span class="cp-modal-key">Hora anterior</span>' +
        '<span class="cp-modal-val">' + escHtml(horaAnt) + '</span></div>' +
      '<div class="cp-modal-row"><span class="cp-modal-key">Hora del cambio</span>' +
        '<span class="cp-modal-val">' + escHtml(horaCam) + '</span></div>' +
      '<div class="cp-modal-row"><span class="cp-modal-key">Archivo anterior</span>' +
        '<span class="cp-modal-val">' + escHtml(archivoAnt) + '</span></div>' +
      '<div class="cp-modal-row"><span class="cp-modal-key">Archivo del cambio</span>' +
        '<span class="cp-modal-val">' + escHtml(archivoCam) + '</span></div>' +
      '<div class="cp-modal-row"><span class="cp-modal-key">Barcode/PCB anterior</span>' +
        '<span class="cp-modal-val">' + escHtml(barcodeAnt) + '</span></div>' +
      '<div class="cp-modal-row"><span class="cp-modal-key">Barcode/PCB del cambio</span>' +
        '<span class="cp-modal-val">' + escHtml(barcodeCam) + '</span></div>'
    );
  }

  function consultarDetalleCambio(tr) {
    abrirModalDetalle();
    setModalSpinner(false);
    setModalError('');
    setModalContent(buildDetalleHtmlFromRow(tr));
  }

  /* ===== INIT ===== */
  // Helper para registrar listeners de forma idempotente. El modulo se carga
  // dinamicamente y `initializeCambiosParametrosICT` puede invocarse varias
  // veces (auto-init del IIFE + scriptMain.js + setTimeout). Sin proteccion
  // los listeners se duplican y cada click dispara N fetches concurrentes
  // que apilan filas duplicadas en el tbody.
  function bindOnce(target, key, type, handler) {
    if (!target) return;
    if (target.dataset && target.dataset[key] === '1') return;
    target.addEventListener(type, handler);
    if (target.dataset) target.dataset[key] = '1';
  }

  var _docKeydownBound = false;

  function initializeCambiosParametrosICT() {
    /* Ocultar tabla inicialmente */
    var tableEl = el('cp-params-table');
    if (tableEl) tableEl.style.display = 'none';

    /* Fecha de hoy por defecto */
    var hoy = new Date().toISOString().split('T')[0];
    var dia = el('cp-filter-dia');
    if (dia && !dia.value) dia.value = hoy;

    /* Boton consultar */
    bindOnce(el('cp-btn-consultar'), 'cpBound', 'click', loadCambiosParametrosICT);

    /* Boton exportar */
    bindOnce(el('cp-btn-export'), 'cpBound', 'click', exportarExcel);

    /* Enter en cualquier input dispara consulta */
    var inputIds = [
      'cp-filter-dia',
      'cp-filter-no-parte',
      'cp-filter-componente',  'cp-filter-parametro'
    ];
    inputIds.forEach(function (id) {
      bindOnce(el(id), 'cpBound', 'keydown', function (e) {
        if (e.key === 'Enter') loadCambiosParametrosICT();
      });
    });

    /* Cambio en el dropdown ICT: solo mostrar/limpiar advertencias.
       El usuario debe presionar "Consultar" para ejecutar la busqueda. */
    var ictSel = el('cp-filter-ict');
    bindOnce(ictSel, 'cpBound', 'change', function () {
      if (ictSel.value === 'ALL') {
        mostrarWarnings(['Consulta sobre todas las ICTs: puede tardar varios minutos. De click a Consultar para ejecutar.']);
      } else {
        mostrarWarnings([]);
      }
    });

    /* Click delegado en el tbody: abre modal de detalle */
    bindOnce(el('cp-params-body'), 'cpBound', 'click', function (e) {
      var tr = e.target.closest('tr');
      if (!tr || !tr.hasAttribute('data-noparte')) return;
      consultarDetalleCambio(tr);
    });

    /* Cerrar modal: boton X, fondo y tecla Escape */
    bindOnce(el('cp-modal-close'), 'cpBound', 'click', cerrarModalDetalle);
    var modalOverlay = el('cp-modal-detalle');
    bindOnce(modalOverlay, 'cpBound', 'click', function (e) {
      if (e.target === modalOverlay) cerrarModalDetalle();
    });
    if (!_docKeydownBound) {
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') cerrarModalDetalle();
      });
      _docKeydownBound = true;
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
