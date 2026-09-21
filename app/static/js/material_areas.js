// Control de material SMD: entradas / salidas / inventario de Control_inventario_SMD.
// Prefijo de IDs: msmd-. mostrarControlMaterialSmd() (MainTemplate) llama a
// window.initControlMaterialSmd despues de cada carga AJAX; este archivo se carga
// una sola vez. Mismo patron que control_scrap.js + paginacion del Historial de input.
(function () {
  const FILTER_STORAGE_KEY = 'controlMaterialSmdColumnFilters';
  // Mismas claves que VISTAS en app/api/control_material/material_smd.py.
  const COLUMNAS = {
    entradas: [
      ['fecha', 'Fecha'], ['hora', 'Hora'], ['codigo', 'Código'], ['part_no', 'Part No'],
      ['lote', 'Lote'], ['cantidad', 'Cantidad'], ['unidad', 'Unidad'], ['ubicacion', 'Ubicación'],
      ['cliente', 'Cliente'], ['especificacion', 'Especificación'], ['usuario', 'Usuario'],
    ],
    salidas: [
      ['fecha', 'Fecha'], ['hora', 'Hora'], ['codigo', 'Código'], ['part_no', 'Part No'],
      ['lote', 'Lote'], ['cantidad', 'Cantidad'], ['unidad', 'Unidad'], ['modelo', 'Modelo'],
      ['depto', 'Depto'], ['proceso', 'Proceso'], ['linea', 'Línea'], ['usuario', 'Usuario'],
    ],
    // Inventario detallado: un renglon por lote.
    inventario: [
      ['part_no', 'Part No'], ['lote', 'Lote'], ['codigo', 'Código'], ['entrada', 'Entrada'],
      ['salida', 'Salida'], ['stock', 'Stock'], ['unidad', 'Unidad'], ['ubicacion', 'Ubicación'],
      ['fecha_recibo', 'Fecha recibo'], ['especificacion', 'Especificación'],
    ],
    // Inventario general: suma por numero de parte.
    inventario_general: [
      ['part_no', 'Part No'], ['especificacion', 'Especificación'], ['unidad', 'Unidad'],
      ['stock', 'Stock total'], ['lotes', 'Lotes distintos'], ['lotes_con_stock', 'Etiquetas con stock'],
    ],
  };

  let listenersListos = false;
  let filtrosPorVista = leerFiltrosGuardados(); // { entradas: {campo: valor}, ... }
  let filterTimer = null;
  let controller = null;
  const pag = { page: 1, perPage: 1000, totalPages: 1 };

  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
  const hoy = () => new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Monterrey', year: 'numeric', month: '2-digit', day: '2-digit'
  }).format(new Date());
  const esInventario = () => $('msmd-vista')?.value === 'inventario';
  // Vista efectiva (= clave de VISTAS en el backend): inventario tiene modo general/detallado.
  const vista = () => {
    if (esInventario()) return $('msmd-modo').value === 'general' ? 'inventario_general' : 'inventario';
    return $('msmd-vista')?.value || 'entradas';
  };
  const filtrosVista = () => (filtrosPorVista[vista()] ||= {});
  const num = (v) => Number(v || 0).toLocaleString('es-MX');

  function leerFiltrosGuardados() {
    try {
      const v = JSON.parse(localStorage.getItem(FILTER_STORAGE_KEY) || '{}');
      return v && typeof v === 'object' ? v : {};
    } catch (_) {
      return {};
    }
  }

  function guardarFiltros() {
    try { localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(filtrosPorVista)); } catch (_) { /* sin storage */ }
  }

  async function pedir(url, opts) {
    const resp = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts));
    let data = null;
    try { data = await resp.json(); } catch (_) { /* HTML de login u otro */ }
    if (!resp.ok || !data || data.success === false) {
      const porStatus = { 401: 'Sesión expirada, vuelve a iniciar sesión', 403: 'Sin permiso para Control de material SMD', 404: 'Ruta no encontrada' };
      throw new Error((data && data.error) || porStatus[resp.status] || (data ? `Error ${resp.status}` : 'Respuesta inválida (¿sesión expirada?)'));
    }
    return data;
  }

  function filtros(conPagina) {
    const p = new URLSearchParams({ vista: vista(), start: $('msmd-filter-start').value, end: $('msmd-filter-end').value });
    Object.entries(filtrosVista()).forEach(([campo, valor]) => { if (valor) p.set(`cf_${campo}`, valor); });
    if (conPagina) {
      p.set('page', pag.page);
      p.set('per_page', pag.perPage);
    }
    return p.toString();
  }

  // ====== Encabezados (cambian con la vista) + filtros por columna ======
  function renderEncabezados() {
    const valores = filtrosVista();
    $('msmd-thead-row').innerHTML = COLUMNAS[vista()].map(([clave, label]) => {
      const valor = valores[clave] || '';
      return `
        <th data-key="${clave}">
          <div class="hpe-column-header">
            <span>${esc(label)}</span>
            <button class="hpe-column-filter-btn${valor ? ' active' : ''}" type="button" aria-expanded="false"
                    aria-label="Filtrar ${esc(label)}" title="Filtrar ${esc(label)}">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18l-7 8v5l-4 2v-7L3 5z"></path></svg>
            </button>
          </div>
          <div class="hpe-column-filter-popover">
            <input class="hpe-column-filter-input" data-msmd-field="${clave}" value="${esc(valor)}"
                   placeholder="Buscar..." aria-label="Buscar en ${esc(label)}" autocomplete="off">
            <div class="hpe-column-filter-actions">
              <button type="button" data-msmd-action="clear-column">Limpiar</button>
              <button type="button" data-msmd-action="clear-all-columns">Todos</button>
            </div>
          </div>
        </th>`;
    }).join('');
    // Inventario es el stock actual: el rango de fechas no aplica y se elige el modo.
    $('msmd-filter-start').disabled = esInventario();
    $('msmd-filter-end').disabled = esInventario();
    $('msmd-modo-group').hidden = !esInventario();
  }

  function cerrarPopovers(excepto = null) {
    document.querySelectorAll('#msmd-table .hpe-column-filter-popover.open').forEach((pop) => {
      if (pop === excepto) return;
      pop.classList.remove('open');
      const th = pop.closest('th');
      th?.classList.remove('hpe-filter-open');
      th?.querySelector('.hpe-column-filter-btn')?.classList.remove('open');
    });
  }

  // ====== Carga y render ======
  function mensaje(texto, color) {
    const cols = COLUMNAS[vista()].length;
    $('msmd-tbody').innerHTML = `<tr class="hpe-empty-row"><td colspan="${cols}"${color ? ` style="color:${color} !important;"` : ''}>${esc(texto)}</td></tr>`;
    $('msmd-resumen').textContent = '0 registros';
    $('msmd-pagination').hidden = true;
  }

  function setLoading(loading) {
    const head = document.querySelector('#msmd-table thead');
    const wrap = document.querySelector('#msmd-root .hpe-table-wrap');
    if (wrap && head) wrap.style.setProperty('--thead-height', `${head.offsetHeight}px`);
    $('msmd-table-loading')?.classList.toggle('active', loading);
    $('msmd-btn-filtrar')?.toggleAttribute('disabled', loading);
  }

  async function cargar({ resetPage = true } = {}) {
    if (!$('msmd-tbody')) return;
    if (resetPage) pag.page = 1;
    controller?.abort(); // al teclear en filtros, gana la ultima consulta
    const actual = controller = new AbortController();
    setLoading(true);
    try {
      const data = await pedir('/api/material/smd?' + filtros(true), { signal: actual.signal });
      pag.page = data.page;
      pag.totalPages = data.total_pages;
      render(data);
    } catch (e) {
      if (e.name === 'AbortError') return;
      mensaje('Error: ' + e.message, '#e74c3c');
    } finally {
      if (controller === actual && $('msmd-tbody')) setLoading(false);
    }
  }

  function render(data) {
    const rows = data.rows || [];
    if (!rows.length) return mensaje('No se encontraron registros con los filtros seleccionados.');
    const cols = COLUMNAS[vista()];
    $('msmd-tbody').innerHTML = rows.map((r) => '<tr>' + cols.map(([clave]) => {
      const clase = clave === 'stock' ? ' class="msmd-stock"' : '';
      return `<td${clase} title="${esc(r[clave])}">${esc(r[clave])}</td>`;
    }).join('') + '</tr>').join('');

    const etiquetas = {
      inventario: `${num(data.total)} etiquetas · stock ${num(data.piezas)}`,
      inventario_general: `${num(data.total)} números de parte · stock ${num(data.piezas)}`,
    };
    $('msmd-resumen').textContent = etiquetas[vista()] || `${num(data.total)} registros · ${num(data.piezas)} piezas`;

    const inicio = (data.page - 1) * data.per_page + 1;
    const fin = Math.min(data.page * data.per_page, data.total);
    $('msmd-pagination').hidden = data.total <= 0;
    $('msmd-pagination-summary').textContent = `${num(inicio)} - ${num(fin)} de ${num(data.total)}`;
    $('msmd-page-input').value = data.page;
    $('msmd-page-input').max = data.total_pages;
    $('msmd-page-total').textContent = data.total_pages;
    $('msmd-page-first').disabled = $('msmd-page-prev').disabled = data.page <= 1;
    $('msmd-page-next').disabled = $('msmd-page-last').disabled = data.page >= data.total_pages;
  }

  function irAPagina(valor) {
    const page = Math.max(1, Math.min(pag.totalPages, parseInt(valor, 10) || 1));
    if (page === pag.page) return;
    pag.page = page;
    cargar({ resetPage: false });
  }

  async function exportar() {
    try {
      const resp = await fetch('/api/material/smd/export?' + filtros(false), { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(resp.status === 403 ? 'Sin permiso' : `Error ${resp.status}`);
      const a = document.createElement('a');
      a.href = URL.createObjectURL(await resp.blob());
      a.download = `Material_SMD_${vista()}_${hoy()}.xlsx`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      alert('Error al exportar: ' + e.message);
    }
  }

  function initListeners() {
    if (listenersListos) return;
    listenersListos = true;
    document.body.addEventListener('click', (e) => {
      const filterBtn = e.target.closest('#msmd-table .hpe-column-filter-btn');
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

      const action = e.target.closest('#msmd-table [data-msmd-action]')?.dataset.msmdAction;
      if (action === 'clear-column') {
        delete filtrosVista()[e.target.closest('th').querySelector('.hpe-column-filter-input').dataset.msmdField];
      } else if (action === 'clear-all-columns') {
        filtrosPorVista[vista()] = {};
      }
      if (action) {
        guardarFiltros();
        renderEncabezados();
        cargar();
        return;
      }
      if (!e.target.closest('.hpe-column-filter-popover')) cerrarPopovers();

      // closest: los botones llevan <svg>, el click puede caer en el icono.
      const id = e.target.closest('button')?.id;
      if (id === 'msmd-btn-filtrar') cargar();
      else if (id === 'msmd-btn-export') exportar();
      else if (id === 'msmd-page-first') irAPagina(1);
      else if (id === 'msmd-page-prev') irAPagina(pag.page - 1);
      else if (id === 'msmd-page-next') irAPagina(pag.page + 1);
      else if (id === 'msmd-page-last') irAPagina(pag.totalPages);
    });
    document.body.addEventListener('input', (e) => {
      if (!e.target.matches('#msmd-table .hpe-column-filter-input')) return;
      const campo = e.target.dataset.msmdField;
      const valor = e.target.value.trim();
      if (valor) filtrosVista()[campo] = valor;
      else delete filtrosVista()[campo];
      guardarFiltros();
      e.target.closest('th')?.querySelector('.hpe-column-filter-btn')?.classList.toggle('active', Boolean(valor));
      clearTimeout(filterTimer);
      filterTimer = setTimeout(cargar, 300);
    });
    document.body.addEventListener('change', (e) => {
      if (e.target.id === 'msmd-vista' || e.target.id === 'msmd-modo') {
        renderEncabezados();
        cargar();
      } else if (e.target.id === 'msmd-per-page') {
        pag.perPage = parseInt(e.target.value, 10) || 1000;
        cargar();
      }
    });
    document.body.addEventListener('keydown', (e) => {
      if (!e.target.closest('#msmd-root')) return;
      if (e.key === 'Escape') return cerrarPopovers();
      if (e.key !== 'Enter') return;
      if (e.target.id === 'msmd-page-input') {
        e.preventDefault();
        irAPagina(e.target.value);
      } else if (e.target.matches('.hpe-column-filter-input') || e.target.closest('#msmd-filters')) {
        e.preventDefault();
        clearTimeout(filterTimer);
        cargar();
      }
    });
  }

  window.initControlMaterialSmd = function () {
    initListeners();
    if (!$('msmd-root')) return;
    if (!$('msmd-filter-start').value) $('msmd-filter-start').value = hoy();
    if (!$('msmd-filter-end').value) $('msmd-filter-end').value = hoy();
    pag.perPage = parseInt($('msmd-per-page').value, 10) || 1000;
    renderEncabezados();
    cargar();
  };
})();
