// Historial de operacion por proceso: planes SMT / IMT / ASSY. Prefijo de IDs: hop-
// scriptMain.mostrarHistorialOperacionProceso() llama a
// window.inicializarHistorialOperacionProcesoAjax despues de cada carga AJAX;
// este archivo se carga una sola vez. Mismo patron que control_scrap.js.
(function () {
  const FILTER_STORAGE_KEY = 'historialOperacionProcesoColumnFilters';
  let listenersListos = false;
  let columnFilters = leerFiltrosGuardados();
  let filterTimer = null;
  let controller = null;

  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
  const hoy = () => new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Monterrey', year: 'numeric', month: '2-digit', day: '2-digit'
  }).format(new Date());

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

  async function pedir(url, opts) {
    const resp = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts));
    let data = null;
    try { data = await resp.json(); } catch (_) { /* HTML de login u otro */ }
    if (!resp.ok || !data || data.success === false) {
      const porStatus = { 401: 'Sesión expirada, vuelve a iniciar sesión', 403: 'Sin permiso para Historial de operación por proceso', 404: 'Ruta no encontrada' };
      throw new Error((data && data.error) || porStatus[resp.status] || (data ? `Error ${resp.status}` : 'Respuesta inválida (¿sesión expirada?)'));
    }
    return data;
  }

  function filtros() {
    const p = new URLSearchParams({ start: $('hop-filter-start').value, end: $('hop-filter-end').value });
    if ($('hop-filter-proceso').value) p.set('proceso', $('hop-filter-proceso').value);
    Object.entries(columnFilters).forEach(([campo, valor]) => { if (valor) p.set(`cf_${campo}`, valor); });
    return p.toString();
  }

  function mensaje(texto, color) {
    $('hop-tbody').innerHTML = `<tr class="hpe-empty-row"><td colspan="11"${color ? ` style="color:${color} !important;"` : ''}>${esc(texto)}</td></tr>`;
    $('hop-resumen').textContent = '0 planes';
  }

  function setLoading(loading) {
    const head = document.querySelector('#hop-table thead');
    const wrap = document.querySelector('#hop-root .hpe-table-wrap');
    if (wrap && head) wrap.style.setProperty('--thead-height', `${head.offsetHeight}px`);
    $('hop-table-loading')?.classList.toggle('active', loading);
    $('hop-btn-filtrar')?.toggleAttribute('disabled', loading);
  }

  async function cargar() {
    if (!$('hop-tbody')) return;
    controller?.abort(); // al teclear en filtros, gana la ultima consulta
    const actual = controller = new AbortController();
    setLoading(true);
    try {
      render((await pedir('/api/historial-operacion-proceso?' + filtros(), { signal: actual.signal })).data || []);
    } catch (e) {
      if (e.name === 'AbortError') return;
      mensaje('Error: ' + e.message, '#e74c3c');
    } finally {
      if (controller === actual && $('hop-tbody')) setLoading(false);
    }
  }

  function render(rows) {
    if (!rows.length) return mensaje('No se encontraron planes con los filtros seleccionados.');
    $('hop-tbody').innerHTML = rows.map((r) => `
      <tr>
        <td class="hop-proceso">${esc(r.proceso)}</td>
        <td>${esc(r.fecha)}</td>
        <td title="${esc(r.linea)}">${esc(r.linea)}</td>
        <td title="${esc(r.wo)}">${esc(r.wo)}</td>
        <td title="${esc(r.lote)}">${esc(r.lote)}</td>
        <td title="${esc(r.part_no)}">${esc(r.part_no)}</td>
        <td title="${esc(r.modelo)}">${esc(r.modelo)}</td>
        <td>${esc(r.plan_count)}</td>
        <td>${esc(r.input_count)}</td>
        <td class="${r.output_count === 'N/A' ? 'hop-na' : ''}">${esc(r.output_count)}</td>
        <td title="${esc(r.status)}">${esc(r.status)}</td>
      </tr>`).join('');
    $('hop-resumen').textContent = `${rows.length} planes`;
  }

  async function exportar() {
    try {
      const resp = await fetch('/api/historial-operacion-proceso/export?' + filtros(), { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      const a = document.createElement('a');
      a.href = URL.createObjectURL(await resp.blob());
      a.download = `Historial_Operacion_Proceso_${hoy()}.xlsx`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      alert('Error al exportar: ' + e.message);
    }
  }

  // ====== Filtros por encabezado (mismo patron que Historial de input) ======
  function renderEncabezadosFiltro() {
    document.querySelectorAll('#hop-table th[data-hop-filter-field]').forEach((th) => {
      if (th.dataset.hopFilterReady === 'true') return;
      const campo = th.dataset.hopFilterField;
      const label = th.textContent.trim();
      const valor = columnFilters[campo] || '';
      th.dataset.hopFilterReady = 'true';
      th.innerHTML = `
        <div class="hpe-column-header">
          <span>${esc(label)}</span>
          <button class="hpe-column-filter-btn${valor ? ' active' : ''}" type="button" aria-expanded="false"
                  aria-label="Filtrar ${esc(label)}" title="Filtrar ${esc(label)}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18l-7 8v5l-4 2v-7L3 5z"></path></svg>
          </button>
        </div>
        <div class="hpe-column-filter-popover">
          <input class="hpe-column-filter-input" data-hop-field="${esc(campo)}" value="${esc(valor)}"
                 placeholder="Buscar..." aria-label="Buscar en ${esc(label)}" autocomplete="off">
          <div class="hpe-column-filter-actions">
            <button type="button" data-hop-action="clear-column">Limpiar</button>
            <button type="button" data-hop-action="clear-all-columns">Todos</button>
          </div>
        </div>`;
    });
  }

  function cerrarPopovers(excepto = null) {
    document.querySelectorAll('#hop-table .hpe-column-filter-popover.open').forEach((pop) => {
      if (pop === excepto) return;
      pop.classList.remove('open');
      const th = pop.closest('th');
      th?.classList.remove('hpe-filter-open');
      th?.querySelector('.hpe-column-filter-btn')?.classList.remove('open');
    });
  }

  function sincronizarFiltros() {
    document.querySelectorAll('#hop-table .hpe-column-filter-input').forEach((input) => {
      const valor = columnFilters[input.dataset.hopField] || '';
      input.value = valor;
      input.closest('th')?.querySelector('.hpe-column-filter-btn')?.classList.toggle('active', Boolean(valor));
    });
  }

  function initListeners() {
    if (listenersListos) return;
    listenersListos = true;
    document.body.addEventListener('click', (e) => {
      const filterBtn = e.target.closest('#hop-table .hpe-column-filter-btn');
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

      const action = e.target.closest('#hop-table [data-hop-action]')?.dataset.hopAction;
      if (action === 'clear-column') {
        delete columnFilters[e.target.closest('th').querySelector('.hpe-column-filter-input').dataset.hopField];
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
      if (id === 'hop-btn-filtrar') cargar();
      else if (id === 'hop-btn-export') exportar();
    });
    document.body.addEventListener('input', (e) => {
      if (!e.target.matches('#hop-table .hpe-column-filter-input')) return;
      const campo = e.target.dataset.hopField;
      const valor = e.target.value.trim();
      if (valor) columnFilters[campo] = valor;
      else delete columnFilters[campo];
      guardarFiltros();
      e.target.closest('th')?.querySelector('.hpe-column-filter-btn')?.classList.toggle('active', Boolean(valor));
      clearTimeout(filterTimer);
      filterTimer = setTimeout(cargar, 300);
    });
    document.body.addEventListener('change', (e) => {
      if (e.target.id === 'hop-filter-proceso') cargar();
    });
    document.body.addEventListener('keydown', (e) => {
      if (!e.target.closest('#hop-root')) return;
      if (e.key === 'Escape') return cerrarPopovers();
      if (e.key !== 'Enter') return;
      if (e.target.matches('.hpe-column-filter-input') || e.target.closest('#hop-filters')) {
        e.preventDefault();
        clearTimeout(filterTimer);
        cargar();
      }
    });
  }

  window.inicializarHistorialOperacionProcesoAjax = function () {
    initListeners();
    if (!$('hop-root')) return;
    if (!$('hop-filter-start').value) $('hop-filter-start').value = hoy();
    if (!$('hop-filter-end').value) $('hop-filter-end').value = hoy();
    renderEncabezadosFiltro();
    cargar();
  };
})();
