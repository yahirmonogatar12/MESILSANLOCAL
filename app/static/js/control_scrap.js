// Control de Scrap (tabla scrap_records). Prefijo de IDs: scrap-
// scriptMain.mostrarControlScrap() llama a window.inicializarControlScrapAjax
// despues de cada carga AJAX del fragmento; este archivo se carga una sola vez.
(function () {
  const FILTER_STORAGE_KEY = 'controlScrapColumnFilters';
  let registros = [];
  let motivos = [];
  let listenersListos = false;
  let columnFilters = leerFiltrosGuardados();
  let filterTimer = null;
  let controller = null;

  function leerFiltrosGuardados() {
    try {
      const v = JSON.parse(localStorage.getItem(FILTER_STORAGE_KEY) || '{}');
      return v && typeof v === 'object' ? v : {};
    } catch (_) {
      return {};
    }
  }

  function guardarFiltros() {
    try { localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(columnFilters)); } catch (_) { /* sin storage */ }
  }

  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
  const hoy = () => new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Monterrey', year: 'numeric', month: '2-digit', day: '2-digit'
  }).format(new Date());

  async function pedir(url, opts) {
    const resp = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts));
    let data = null;
    try { data = await resp.json(); } catch (_) { /* HTML de login u otro */ }
    if (!resp.ok || !data || data.success === false) {
      const porStatus = { 401: 'Sesión expirada, vuelve a iniciar sesión', 403: 'Sin permiso para Control de Scrap', 404: 'Ruta no encontrada' };
      throw new Error((data && data.error) || porStatus[resp.status] || (data ? `Error ${resp.status}` : 'Respuesta inválida (¿sesión expirada?)'));
    }
    return data;
  }

  function filtros() {
    const p = new URLSearchParams({ start: $('scrap-filter-start').value, end: $('scrap-filter-end').value });
    if ($('scrap-filter-area').value) p.set('area', $('scrap-filter-area').value);
    Object.entries(columnFilters).forEach(([campo, valor]) => { if (valor) p.set(`cf_${campo}`, valor); });
    return p.toString();
  }

  function mensaje(texto, color) {
    $('scrap-tbody').innerHTML = `<tr class="hpe-empty-row"><td colspan="12"${color ? ` style="color:${color} !important;"` : ''}>${esc(texto)}</td></tr>`;
    $('scrap-resumen').textContent = '0 registros';
  }

  function setLoading(loading) {
    const head = document.querySelector('#scrap-table thead');
    const wrap = document.querySelector('#scrap-root .hpe-table-wrap');
    if (wrap && head) wrap.style.setProperty('--thead-height', `${head.offsetHeight}px`);
    $('scrap-table-loading')?.classList.toggle('active', loading);
    $('scrap-btn-filtrar')?.toggleAttribute('disabled', loading);
  }

  async function cargar() {
    if (!$('scrap-tbody')) return;
    controller?.abort(); // al teclear en filtros, gana la ultima consulta
    const actual = controller = new AbortController();
    setLoading(true);
    try {
      registros = (await pedir('/api/control-scrap?' + filtros(), { signal: actual.signal })).data || [];
      render();
    } catch (e) {
      if (e.name === 'AbortError') return;
      registros = [];
      mensaje('Error: ' + e.message, '#e74c3c');
    } finally {
      if (controller === actual && $('scrap-tbody')) setLoading(false);
    }
  }

  // ====== Filtros por encabezado (mismo patron que Historial de input) ======
  function renderEncabezadosFiltro() {
    document.querySelectorAll('#scrap-table th[data-scrap-filter-field]').forEach((th) => {
      if (th.dataset.scrapFilterReady === 'true') return;
      const campo = th.dataset.scrapFilterField;
      const label = th.textContent.trim();
      const valor = columnFilters[campo] || '';
      th.dataset.scrapFilterReady = 'true';
      th.innerHTML = `
        <div class="hpe-column-header">
          <span>${esc(label)}</span>
          <button class="hpe-column-filter-btn${valor ? ' active' : ''}" type="button" aria-expanded="false"
                  aria-label="Filtrar ${esc(label)}" title="Filtrar ${esc(label)}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18l-7 8v5l-4 2v-7L3 5z"></path></svg>
          </button>
        </div>
        <div class="hpe-column-filter-popover">
          <input class="hpe-column-filter-input" data-scrap-field="${esc(campo)}" value="${esc(valor)}"
                 placeholder="Buscar..." aria-label="Buscar en ${esc(label)}" autocomplete="off">
          <div class="hpe-column-filter-actions">
            <button type="button" data-scrap-action="clear-column">Limpiar</button>
            <button type="button" data-scrap-action="clear-all-columns">Todos</button>
          </div>
        </div>`;
    });
  }

  function cerrarPopovers(excepto = null) {
    document.querySelectorAll('#scrap-table .hpe-column-filter-popover.open').forEach((pop) => {
      if (pop === excepto) return;
      pop.classList.remove('open');
      const th = pop.closest('th');
      th?.classList.remove('hpe-filter-open');
      th?.querySelector('.hpe-column-filter-btn')?.classList.remove('open');
    });
  }

  function sincronizarFiltros() {
    document.querySelectorAll('#scrap-table .hpe-column-filter-input').forEach((input) => {
      const valor = columnFilters[input.dataset.scrapField] || '';
      input.value = valor;
      input.closest('th')?.querySelector('.hpe-column-filter-btn')?.classList.toggle('active', Boolean(valor));
    });
  }

  function render() {
    if (!registros.length) return mensaje('No se encontraron registros con los filtros seleccionados.');
    $('scrap-tbody').innerHTML = registros.map((r) => `
      <tr class="scrap-row" data-id="${esc(r.id)}" title="Doble clic para editar">
        <td title="${esc(r.cliente)}">${esc(r.cliente)}</td>
        <td>${esc(r.fecha)}</td>
        <td>${esc(r.hora)}</td>
        <td title="${esc(r.scanned_original)}">${esc(r.scanned_original)}</td>
        <td title="${esc(r.part_no)}">${esc(r.part_no)}</td>
        <td title="${esc(r.modelo)}">${esc(r.modelo)}</td>
        <td title="${esc(r.area)}">${esc(r.area)}</td>
        <td>${esc(r.proceso)}</td>
        <td title="${esc(r.motivo_scrap_texto)}">${esc(r.motivo_scrap_texto)}</td>
        <td class="${Number(r.cantidad) === 0 ? 'scrap-cero' : ''}">${esc(r.cantidad)}</td>
        <td title="${esc(r.comentarios)}">${esc(r.comentarios)}</td>
        <td title="${esc(r.usuario_registro)}">${esc(r.usuario_registro)}</td>
      </tr>`).join('');
    const piezas = registros.reduce((s, r) => s + (Number(r.cantidad) || 0), 0);
    $('scrap-resumen').textContent = `${registros.length} registros · ${piezas} piezas`;
  }

  async function exportar() {
    try {
      const resp = await fetch('/api/control-scrap/export?' + filtros(), { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      const a = document.createElement('a');
      a.href = URL.createObjectURL(await resp.blob());
      a.download = `Control_Scrap_${hoy()}.xlsx`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      alert('Error al exportar: ' + e.message);
    }
  }

  const estiloCampo = 'width:100%; background:#1a1b26; border:1px solid #444; color:lightgray; padding:8px; border-radius:4px; box-sizing:border-box;';

  function modalEdicion() {
    let modal = $('scrap-edit-modal');
    if (modal) return modal;
    document.body.insertAdjacentHTML('beforeend', `
      <div id="scrap-edit-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.8); z-index:10001; align-items:center; justify-content:center;">
        <div style="background:#32323E; border-radius:8px; padding:20px; max-width:520px; width:90%; max-height:85vh; overflow-y:auto;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; border-bottom:1px solid #444; padding-bottom:10px;">
            <h3 style="color:#ecf0f1; margin:0;">Editar Scrap</h3>
            <button type="button" id="scrap-edit-close" style="background:none; border:none; color:#888; font-size:24px; cursor:pointer;">&times;</button>
          </div>
          <form id="scrap-edit-form">
            <input type="hidden" name="id" id="scrap-edit-id">
            <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px;">
              <div style="grid-column:1 / -1;"><label style="color:#888; font-size:12px;">Código</label><input type="text" id="scrap-edit-codigo" disabled style="${estiloCampo} color:#888;"></div>
              <div><label style="color:#888; font-size:12px;">Cantidad</label><input type="number" name="cantidad" id="scrap-edit-cantidad" min="0" step="1" required title="0 permitido" style="${estiloCampo}"></div>
              <div><label style="color:#888; font-size:12px;">Ubicación</label><input type="text" name="ubicacion" id="scrap-edit-ubicacion" maxlength="100" style="${estiloCampo}"></div>
              <div style="grid-column:1 / -1;"><label style="color:#888; font-size:12px;">Motivo</label><select name="motivo_scrap_id" id="scrap-edit-motivo" required style="${estiloCampo}"></select></div>
              <div style="grid-column:1 / -1;"><label style="color:#888; font-size:12px;">Comentarios</label><textarea name="comentarios" id="scrap-edit-comentarios" rows="3" style="${estiloCampo}"></textarea></div>
              <div style="grid-column:1 / -1;"><label style="color:#888; font-size:12px;">Motivo de la edición *</label><input type="text" name="edit_reason" id="scrap-edit-reason" required style="${estiloCampo}"></div>
            </div>
            <div style="display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px; margin-top:20px;">
              <button type="submit" style="background:#e67e22; color:white; border:none; padding:10px; border-radius:4px; cursor:pointer;">Guardar Cambios</button>
              <button type="button" id="scrap-edit-cancel" style="background:#7f8c8d; color:white; border:none; padding:10px; border-radius:4px; cursor:pointer;">Cerrar</button>
            </div>
          </form>
        </div>
      </div>`);
    return $('scrap-edit-modal');
  }

  async function abrirEdicion(id) {
    const r = registros.find((x) => String(x.id) === String(id));
    if (!r) return;
    if (!motivos.length) {
      try {
        motivos = (await pedir('/api/control-scrap/motivos')).data || [];
      } catch (e) {
        return alert('No se pudieron cargar los motivos: ' + e.message);
      }
    }
    const modal = modalEdicion();
    const opciones = motivos.map((m) => ({ id: m.id, texto: m.motivo }));
    // El motivo actual puede estar inactivo (p.ej. motivos de sistema): se conserva.
    if (r.motivo_scrap_id != null && !opciones.some((m) => String(m.id) === String(r.motivo_scrap_id))) {
      opciones.unshift({ id: r.motivo_scrap_id, texto: `${r.motivo_scrap_texto || r.motivo_scrap_id} (inactivo)` });
    }
    $('scrap-edit-motivo').innerHTML = '<option value="">Selecciona motivo</option>' +
      opciones.map((m) => `<option value="${esc(m.id)}">${esc(m.texto)}</option>`).join('');
    $('scrap-edit-id').value = r.id;
    $('scrap-edit-codigo').value = r.scanned_original || '';
    $('scrap-edit-cantidad').value = r.cantidad ?? 0;
    $('scrap-edit-ubicacion').value = r.ubicacion || '';
    $('scrap-edit-motivo').value = r.motivo_scrap_id ?? '';
    $('scrap-edit-comentarios').value = r.comentarios || '';
    $('scrap-edit-reason').value = '';
    modal.style.display = 'flex';
  }

  async function guardar(form) {
    const fd = new FormData(form);
    const cantidad = parseInt(fd.get('cantidad'), 10);
    if (Number.isNaN(cantidad) || cantidad < 0) return alert('La cantidad debe ser 0 o mayor');
    try {
      await pedir('/api/control-scrap/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: fd.get('id'),
          cantidad,
          motivo_scrap_id: fd.get('motivo_scrap_id'),
          ubicacion: fd.get('ubicacion'),
          comentarios: fd.get('comentarios'),
          edit_reason: fd.get('edit_reason'),
        }),
      });
      $('scrap-edit-modal').style.display = 'none';
      cargar();
    } catch (e) {
      alert('Error al guardar: ' + e.message);
    }
  }

  function initListeners() {
    if (listenersListos) return;
    listenersListos = true;
    document.body.addEventListener('click', (e) => {
      const filterBtn = e.target.closest('#scrap-table .hpe-column-filter-btn');
      if (filterBtn) {
        e.preventDefault();
        const th = filterBtn.closest('th');
        const pop = th.querySelector('.hpe-column-filter-popover');
        const abrir = !pop.classList.contains('open');
        cerrarPopovers(pop);
        pop.classList.toggle('open', abrir);
        filterBtn.classList.toggle('open', abrir);
        filterBtn.setAttribute('aria-expanded', String(abrir));
        th.classList.toggle('hpe-filter-open', abrir);
        if (abrir) pop.querySelector('input')?.focus();
        return;
      }

      const action = e.target.closest('#scrap-table [data-scrap-action]')?.dataset.scrapAction;
      if (action === 'clear-column') {
        delete columnFilters[e.target.closest('th').querySelector('.hpe-column-filter-input').dataset.scrapField];
      } else if (action === 'clear-all-columns') {
        columnFilters = {};
      }
      if (action) {
        guardarFiltros();
        sincronizarFiltros();
        cargar();
        return;
      }
      if (!e.target.closest('.hpe-column-filter-popover')) cerrarPopovers();

      // closest: los botones llevan <svg>, el click puede caer en el icono.
      const id = e.target.closest('button')?.id;
      if (id === 'scrap-btn-filtrar') cargar();
      else if (id === 'scrap-btn-export') exportar();
      else if (id === 'scrap-edit-close' || id === 'scrap-edit-cancel') $('scrap-edit-modal').style.display = 'none';
    });
    document.body.addEventListener('input', (e) => {
      if (!e.target.matches('#scrap-table .hpe-column-filter-input')) return;
      const campo = e.target.dataset.scrapField;
      const valor = e.target.value.trim();
      if (valor) columnFilters[campo] = valor;
      else delete columnFilters[campo];
      guardarFiltros();
      e.target.closest('th')?.querySelector('.hpe-column-filter-btn')?.classList.toggle('active', Boolean(valor));
      clearTimeout(filterTimer);
      filterTimer = setTimeout(cargar, 300);
    });
    document.body.addEventListener('keydown', (e) => {
      if (!e.target.closest('#scrap-root')) return;
      if (e.key === 'Escape') return cerrarPopovers();
      if (e.key !== 'Enter') return;
      if (e.target.matches('.hpe-column-filter-input') || e.target.closest('#scrap-filters')) {
        e.preventDefault();
        clearTimeout(filterTimer);
        cargar();
      }
    });
    document.body.addEventListener('dblclick', (e) => {
      const row = e.target.closest('#scrap-root tr.scrap-row');
      if (row) abrirEdicion(row.dataset.id);
    });
    document.body.addEventListener('submit', (e) => {
      if (e.target.id !== 'scrap-edit-form') return;
      e.preventDefault();
      guardar(e.target);
    });
  }

  window.inicializarControlScrapAjax = function () {
    initListeners();
    if (!$('scrap-root')) return;
    if (!$('scrap-filter-start').value) $('scrap-filter-start').value = hoy();
    if (!$('scrap-filter-end').value) $('scrap-filter-end').value = hoy();
    renderEncabezadosFiltro();
    cargar();
  };
})();
