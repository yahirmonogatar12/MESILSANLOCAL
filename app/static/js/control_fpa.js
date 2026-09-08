(function () {
  'use strict';
  const state = { page: 1, pageSize: 50, total: 0, rows: [] };
  const $ = (id) => document.getElementById(id);
  const text = (value) => value == null ? '' : String(value);
  const itemOf = (row, type) => (row.items || []).find((item) => item.labelType === type);

  function setBusy(busy) {
    $('fpa-table-loading')?.classList.toggle('active', busy);
    const submit = $('fpa-submit');
    if (submit) submit.disabled = busy;
    const search = $('fpa-search');
    if (search) search.disabled = busy;
  }

  async function jsonFetch(url, options) {
    const response = await fetch(url, options);
    let data;
    try { data = await response.json(); } catch (_) { data = { error: 'Respuesta inválida del servidor' }; }
    if (!response.ok || data.success === false) throw new Error(data.error || `Error ${response.status}`);
    return data;
  }

  function filters() {
    const params = new URLSearchParams({ page: state.page, pageSize: state.pageSize });
    const values = {
      folio: $('fpa-filter-folio').value.trim(), fpaPartNumber: $('fpa-filter-part').value.trim(),
      requester: $('fpa-filter-requester').value.trim(), status: $('fpa-filter-status').value,
      dateFrom: $('fpa-filter-from').value, dateTo: $('fpa-filter-to').value,
    };
    Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, value); });
    return params;
  }

  function updateExportLink() {
    const params = filters(); params.delete('page'); params.delete('pageSize');
    $('fpa-export').href = `/api/control-fpa/export?${params}`;
  }

  function appendCell(row, value, className) {
    const td = document.createElement('td');
    if (className) td.className = className;
    td.textContent = text(value);
    row.appendChild(td);
    return td;
  }

  function appendItemCell(tr, item) {
    const td = appendCell(tr, '', 'fpa-code');
    if (!item) { td.textContent = '—'; return; }
    const code = document.createElement('div'); code.textContent = item.code;
    const counts = document.createElement('small');
    counts.textContent = `${item.confirmed} / ${item.consumed} / ${item.requested} · saldo ${item.remaining}`;
    td.append(code, counts);
  }

  function actionButton(label, className, handler) {
    const button = document.createElement('button');
    button.type = 'button'; button.className = `fpa-action ${className || ''}`; button.textContent = label;
    button.addEventListener('click', handler); return button;
  }

  function renderRows() {
    const tbody = $('fpa-tbody'); tbody.textContent = '';
    if (!state.rows.length) {
      const tr = document.createElement('tr');
      appendCell(tr, 'Sin solicitudes', 'fpa-empty').colSpan = 8;
      tbody.appendChild(tr); return;
    }
    const canAdjust = $('fpa-module').dataset.canAdjust === 'true';
    state.rows.forEach((row) => {
      const tr = document.createElement('tr');
      appendCell(tr, row.folio); appendCell(tr, row.createdAt); appendCell(tr, row.requester); appendCell(tr, row.fpaPartNumber);
      appendItemCell(tr, itemOf(row, 'MICOM')); appendItemCell(tr, itemOf(row, 'COMP'));
      const statusTd = appendCell(tr, '');
      const badge = document.createElement('span'); badge.className = `fpa-status ${row.status}`; badge.textContent = row.status;
      statusTd.appendChild(badge);
      const actions = appendCell(tr, '');
      actions.appendChild(actionButton('Detalle', '', () => showDetail(row.id)));
      if (canAdjust) actions.appendChild(actionButton('Ajustar', 'fpa-action-adjust', () => showDetail(row.id, true)));
      tbody.appendChild(tr);
    });
  }

  function renderPagination() {
    const pages = Math.max(1, Math.ceil(state.total / state.pageSize));
    const from = state.total ? (state.page - 1) * state.pageSize + 1 : 0;
    const to = Math.min(state.page * state.pageSize, state.total);
    $('fpa-record-count').textContent = `${state.total} registros`;
    $('fpa-pagination-summary').textContent = `${from} - ${to} de ${state.total}`;
    $('fpa-page-current').textContent = state.page;
    $('fpa-page-total').textContent = pages;
    $('fpa-page-prev').disabled = state.page <= 1;
    $('fpa-page-next').disabled = state.page >= pages;
  }

  async function load() {
    setBusy(true); $('fpa-list-error').textContent = '';
    try {
      const data = await jsonFetch(`/api/control-fpa/requests?${filters()}`);
      updateExportLink();
      state.rows = data.data || []; state.total = Number(data.meta?.total || 0);
      renderRows(); renderPagination();
    } catch (error) {
      $('fpa-list-error').textContent = error.message;
      state.rows = []; state.total = 0; renderRows(); renderPagination();
    } finally { setBusy(false); }
  }

  async function createRequest(event) {
    event.preventDefault(); $('fpa-form-error').textContent = '';
    const payload = {
      fpaPartNumber: $('fpa-part-number').value.trim(), pgmMicom: $('fpa-pgm-micom').value.trim(),
      micomQuantity: Number($('fpa-qty-micom').value || 0), pgmComp: $('fpa-pgm-comp').value.trim(),
      compQuantity: Number($('fpa-qty-comp').value || 0),
    };
    if (payload.micomQuantity <= 0 && payload.compQuantity <= 0) { $('fpa-form-error').textContent = 'Solicita al menos una etiqueta.'; return; }
    if ((payload.micomQuantity > 0 && !payload.pgmMicom) || (payload.compQuantity > 0 && !payload.pgmComp)) { $('fpa-form-error').textContent = 'Captura el código completo del tipo solicitado.'; return; }
    setBusy(true);
    try {
      const data = await jsonFetch('/api/control-fpa/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': `mes-${Date.now()}-${Math.random().toString(16).slice(2)}` },
        body: JSON.stringify(payload),
      });
      $('fpa-request-form').reset(); $('fpa-qty-micom').value = 0; $('fpa-qty-comp').value = 0;
      closeModal('fpa-request-modal');
      alert(`Solicitud ${data.data.folio} creada correctamente.`); state.page = 1; await load();
    } catch (error) { $('fpa-form-error').textContent = error.message; } finally { setBusy(false); }
  }

  function addDetailValue(container, label, value) {
    const box = document.createElement('div'); box.className = 'fpa-detail-box';
    const b = document.createElement('b'); b.textContent = label;
    const span = document.createElement('span'); span.textContent = text(value);
    box.append(b, span); container.appendChild(box);
  }

  function miniTable(headers, rows) {
    const wrap = document.createElement('div'); wrap.className = 'table-wrap';
    const table = document.createElement('table'); table.className = 'fpa-mini-table';
    const thead = document.createElement('thead'); const hr = document.createElement('tr');
    headers.forEach((h) => { const th = document.createElement('th'); th.textContent = h; hr.appendChild(th); });
    thead.appendChild(hr); table.appendChild(thead);
    const tbody = document.createElement('tbody');
    if (!rows.length) {
      const tr = document.createElement('tr');
      appendCell(tr, 'Sin registros', 'fpa-empty').colSpan = headers.length;
      tbody.appendChild(tr);
    }
    rows.forEach((values) => { const tr = document.createElement('tr'); values.forEach((v) => appendCell(tr, v)); tbody.appendChild(tr); });
    table.appendChild(tbody); wrap.appendChild(table); return wrap;
  }

  function openModal(id) { $(id).hidden = false; }
  function closeModal(id) { $(id).hidden = true; }

  // Cierra por boton X y por click en el fondo (patron de los modales WF).
  function wireModal(id) {
    const modal = $(id);
    if (!modal) return;
    modal.querySelector('.fpa-close-btn').addEventListener('click', () => closeModal(id));
    modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(id); });
  }

  async function showDetail(id, focusAdjust) {
    try {
      const response = await jsonFetch(`/api/control-fpa/requests/${id}`); const data = response.data;
      $('fpa-modal-title').textContent = 'Detalle FPA';
      $('fpa-modal-folio').textContent = data.folio;
      const body = $('fpa-modal-body'); body.textContent = '';
      const grid = document.createElement('div'); grid.className = 'fpa-detail-grid';
      addDetailValue(grid, 'No Parte FPA', data.fpaPartNumber);
      addDetailValue(grid, 'Solicitante', data.requester);
      addDetailValue(grid, 'Fecha y hora', data.createdAt);
      addDetailValue(grid, 'Estado', data.status);
      body.appendChild(grid);
      const hItems = document.createElement('h4'); hItems.textContent = 'Etiquetas autorizadas';
      body.append(hItems, miniTable(
        ['Tipo', 'Código', 'Solicitadas', 'Consumidas', 'Confirmadas', 'Restantes'],
        (data.items || []).map((i) => [i.labelType, i.code, i.requested, i.consumed, i.confirmed, i.remaining])));
      const hAttempts = document.createElement('h4'); hAttempts.textContent = 'Intentos de impresión';
      body.append(hAttempts, miniTable(
        ['Fecha', 'Tipo', 'Cantidad', 'Operador', 'Estación', 'Resultado', 'Error'],
        (data.printAttempts || []).map((a) => [a.createdAt, a.labelType, a.quantity, a.operator, a.stationId, a.status, a.error || ''])));
      const hEvents = document.createElement('h4'); hEvents.textContent = 'Bitácora';
      body.append(hEvents, miniTable(
        ['Fecha', 'Evento', 'Actor', 'Motivo'],
        (data.events || []).map((e) => [e.createdAt, e.type, e.actor, e.reason || ''])));
      if ($('fpa-module').dataset.canAdjust === 'true') body.appendChild(buildAdjustForm(data));
      openModal('fpa-modal');
      if (focusAdjust) setTimeout(() => $('fpa-adjust-reason')?.focus(), 0);
    } catch (error) { $('fpa-list-error').textContent = error.message; }
  }

  function adjustField(label, id, type, value, disabled) {
    const group = document.createElement('div'); group.className = 'filter-group';
    const labelEl = document.createElement('label'); labelEl.htmlFor = id; labelEl.textContent = label;
    const input = document.createElement('input'); input.id = id; input.type = type;
    if (type === 'number') { input.min = 0; input.max = 999; }
    input.value = value ?? ''; input.disabled = Boolean(disabled);
    group.append(labelEl, input); return group;
  }

  function buildAdjustForm(data) {
    const form = document.createElement('form'); form.className = 'fpa-adjust-form';
    const micom = itemOf(data, 'MICOM'); const comp = itemOf(data, 'COMP');
    form.append(
      adjustField('Nueva cantidad MICOM', 'fpa-adjust-micom', 'number', micom?.requested ?? 0, !micom),
      adjustField('Nueva cantidad COMP', 'fpa-adjust-comp', 'number', comp?.requested ?? 0, !comp),
      adjustField('Motivo obligatorio', 'fpa-adjust-reason', 'text', '', false),
    );
    const submit = document.createElement('button');
    submit.className = 'btn-primary'; submit.type = 'submit'; submit.textContent = 'Guardar ajuste';
    form.appendChild(submit);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const reason = $('fpa-adjust-reason').value.trim();
      if (!reason) { alert('El motivo es obligatorio.'); return; }
      const payload = { reason };
      if (micom) payload.micomQuantity = Number($('fpa-adjust-micom').value);
      if (comp) payload.compQuantity = Number($('fpa-adjust-comp').value);
      submit.disabled = true;
      try {
        await jsonFetch(`/api/control-fpa/requests/${data.id}/quantities`, {
          method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
        });
        closeModal('fpa-modal'); await load();
      } catch (error) { alert(error.message); } finally { submit.disabled = false; }
    });
    return form;
  }

  window.initControlFPA = function () {
    const root = $('fpa-module');
    if (!root || root.dataset.initialized === 'true') return;
    root.dataset.initialized = 'true';
    $('fpa-request-form')?.addEventListener('submit', createRequest);
    $('fpa-search').addEventListener('click', () => { state.page = 1; load(); });
    $('fpa-clear').addEventListener('click', () => {
      ['fpa-filter-folio', 'fpa-filter-part', 'fpa-filter-requester', 'fpa-filter-from', 'fpa-filter-to'].forEach((id) => { $(id).value = ''; });
      $('fpa-filter-status').value = ''; state.page = 1; load();
    });
    $('fpa-per-page').addEventListener('change', (event) => { state.pageSize = Number(event.target.value); state.page = 1; load(); });
    $('fpa-page-prev').addEventListener('click', () => { if (state.page > 1) { state.page--; load(); } });
    $('fpa-page-next').addEventListener('click', () => { state.page++; load(); });
    wireModal('fpa-modal');
    wireModal('fpa-request-modal');
    $('fpa-new-request')?.addEventListener('click', () => {
      $('fpa-form-error').textContent = '';
      openModal('fpa-request-modal');
      setTimeout(() => $('fpa-part-number').focus(), 0);
    });
    $('fpa-request-cancel')?.addEventListener('click', () => closeModal('fpa-request-modal'));
    // Escape cierra el modal abierto (un solo binding global, idempotente).
    if (!document.body.dataset.fpaEscBound) {
      document.body.dataset.fpaEscBound = 'true';
      document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        document.querySelectorAll('#fpa-module .fpa-modal:not([hidden])').forEach((m) => { m.hidden = true; });
      });
    }
    load();
  };
  window.initControlFPA();
})();
