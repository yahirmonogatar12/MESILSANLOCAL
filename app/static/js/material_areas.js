// Control de material por areas (SMD, MICOM...): entradas / salidas / inventario.
// Un solo JS para todas las areas: cada fragmento trae data-mat-area="<area>" e
// IDs "mat-<area>-*", y el estado se guarda por area (pueden estar abiertas a la vez).
// mostrarMaterialArea(area) (MainTemplate) llama a window.initMaterialArea(area)
// despues de cada carga AJAX; este archivo se carga una sola vez.
(function () {
  // Mismas claves que _vistas() en app/api/control_material/material_areas.py.
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

  const estados = {}; // area -> { filtrosPorVista, filterTimer, controller, pag }
  let listenersListos = false;

  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
  const hoy = () => new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Monterrey', year: 'numeric', month: '2-digit', day: '2-digit'
  }).format(new Date());
  const num = (v) => Number(v || 0).toLocaleString('es-MX');
  const el = (area, id) => document.getElementById(`mat-${area}-${id}`);
  const areaDe = (nodo) => nodo.closest?.('[data-mat-area]')?.dataset.matArea;
  const storageKey = (area) => `materialArea_${area}_ColumnFilters`;

  function estado(area) {
    if (!estados[area]) {
      let filtros = {};
      try {
        const v = JSON.parse(localStorage.getItem(storageKey(area)) || '{}');
        if (v && typeof v === 'object') filtros = v;
      } catch (_) { /* sin storage */ }
      estados[area] = { filtrosPorVista: filtros, filterTimer: null, controller: null, pag: { page: 1, perPage: 1000, totalPages: 1 } };
    }
    return estados[area];
  }

  function guardarFiltros(area) {
    try { localStorage.setItem(storageKey(area), JSON.stringify(estado(area).filtrosPorVista)); } catch (_) { /* sin storage */ }
  }

  const esInventario = (area) => el(area, 'vista')?.value === 'inventario';
  // Vista efectiva (= clave de _vistas en el backend): inventario tiene modo general/detallado.
  function vista(area) {
    if (esInventario(area)) return el(area, 'modo').value === 'general' ? 'inventario_general' : 'inventario';
    return el(area, 'vista')?.value || 'entradas';
  }
  function filtrosVista(area) {
    const f = estado(area).filtrosPorVista;
    return (f[vista(area)] ||= {});
  }

  async function pedir(area, url, opts) {
    const resp = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts));
    let data = null;
    try { data = await resp.json(); } catch (_) { /* HTML de login u otro */ }
    if (!resp.ok || !data || data.success === false) {
      const titulo = el(area, 'root')?.dataset.matTitulo || area;
      const porStatus = { 401: 'Sesión expirada, vuelve a iniciar sesión', 403: `Sin permiso para Control de material ${titulo}`, 404: 'Ruta no encontrada' };
      throw new Error((data && data.error) || porStatus[resp.status] || (data ? `Error ${resp.status}` : 'Respuesta inválida (¿sesión expirada?)'));
    }
    return data;
  }

  function filtros(area, conPagina) {
    const p = new URLSearchParams({ vista: vista(area), start: el(area, 'filter-start').value, end: el(area, 'filter-end').value });
    Object.entries(filtrosVista(area)).forEach(([campo, valor]) => { if (valor) p.set(`cf_${campo}`, valor); });
    if (conPagina) {
      const { pag } = estado(area);
      p.set('page', pag.page);
      p.set('per_page', pag.perPage);
    }
    return p.toString();
  }

  // ====== Encabezados (cambian con la vista) + filtros por columna ======
  function renderEncabezados(area) {
    const valores = filtrosVista(area);
    el(area, 'thead-row').innerHTML = COLUMNAS[vista(area)].map(([clave, label]) => {
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
            <input class="hpe-column-filter-input" data-mat-field="${clave}" value="${esc(valor)}"
                   placeholder="Buscar..." aria-label="Buscar en ${esc(label)}" autocomplete="off">
            <div class="hpe-column-filter-actions">
              <button type="button" data-mat-action="clear-column">Limpiar</button>
              <button type="button" data-mat-action="clear-all-columns">Todos</button>
            </div>
          </div>
        </th>`;
    }).join('');
    // Inventario es el stock actual: el rango de fechas no aplica y se elige el modo.
    el(area, 'filter-start').disabled = esInventario(area);
    el(area, 'filter-end').disabled = esInventario(area);
    el(area, 'modo-group').hidden = !esInventario(area);
  }

  function cerrarPopovers(root, excepto = null) {
    root.querySelectorAll('.hpe-column-filter-popover.open').forEach((pop) => {
      if (pop === excepto) return;
      pop.classList.remove('open');
      const th = pop.closest('th');
      th?.classList.remove('hpe-filter-open');
      th?.querySelector('.hpe-column-filter-btn')?.classList.remove('open');
    });
  }

  // ====== Carga y render ======
  function mensaje(area, texto, color) {
    const cols = COLUMNAS[vista(area)].length;
    el(area, 'tbody').innerHTML = `<tr class="hpe-empty-row"><td colspan="${cols}"${color ? ` style="color:${color} !important;"` : ''}>${esc(texto)}</td></tr>`;
    el(area, 'resumen').textContent = '0 registros';
    el(area, 'pagination').hidden = true;
  }

  function setLoading(area, loading) {
    const root = el(area, 'root');
    const head = root.querySelector('thead');
    const wrap = root.querySelector('.hpe-table-wrap');
    if (wrap && head) wrap.style.setProperty('--thead-height', `${head.offsetHeight}px`);
    el(area, 'table-loading')?.classList.toggle('active', loading);
    root.querySelector('[data-mat-action="filtrar"]')?.toggleAttribute('disabled', loading);
  }

  async function cargar(area, { resetPage = true } = {}) {
    if (!el(area, 'tbody')) return;
    const st = estado(area);
    if (resetPage) st.pag.page = 1;
    st.controller?.abort(); // al teclear en filtros, gana la ultima consulta
    const actual = st.controller = new AbortController();
    setLoading(area, true);
    try {
      const data = await pedir(area, `/api/material/${area}?` + filtros(area, true), { signal: actual.signal });
      st.pag.page = data.page;
      st.pag.totalPages = data.total_pages;
      render(area, data);
    } catch (e) {
      if (e.name === 'AbortError') return;
      mensaje(area, 'Error: ' + e.message, '#e74c3c');
    } finally {
      if (st.controller === actual && el(area, 'tbody')) setLoading(area, false);
    }
  }

  function render(area, data) {
    const rows = data.rows || [];
    if (!rows.length) return mensaje(area, 'No se encontraron registros con los filtros seleccionados.');
    const cols = COLUMNAS[vista(area)];
    el(area, 'tbody').innerHTML = rows.map((r) => '<tr>' + cols.map(([clave]) => {
      const clase = clave === 'stock' ? ' class="mat-area-stock"' : '';
      return `<td${clase} title="${esc(r[clave])}">${esc(r[clave])}</td>`;
    }).join('') + '</tr>').join('');

    const etiquetas = {
      inventario: `${num(data.total)} etiquetas · stock ${num(data.piezas)}`,
      inventario_general: `${num(data.total)} números de parte · stock ${num(data.piezas)}`,
    };
    el(area, 'resumen').textContent = etiquetas[vista(area)] || `${num(data.total)} registros · ${num(data.piezas)} piezas`;

    const inicio = (data.page - 1) * data.per_page + 1;
    const fin = Math.min(data.page * data.per_page, data.total);
    el(area, 'pagination').hidden = data.total <= 0;
    el(area, 'pagination-summary').textContent = `${num(inicio)} - ${num(fin)} de ${num(data.total)}`;
    el(area, 'page-input').value = data.page;
    el(area, 'page-input').max = data.total_pages;
    el(area, 'page-total').textContent = data.total_pages;
    el(area, 'page-first').disabled = el(area, 'page-prev').disabled = data.page <= 1;
    el(area, 'page-next').disabled = el(area, 'page-last').disabled = data.page >= data.total_pages;
  }

  function irAPagina(area, valor) {
    const { pag } = estado(area);
    const page = Math.max(1, Math.min(pag.totalPages, parseInt(valor, 10) || 1));
    if (page === pag.page) return;
    pag.page = page;
    cargar(area, { resetPage: false });
  }

  async function exportar(area) {
    try {
      const resp = await fetch(`/api/material/${area}/export?` + filtros(area, false), { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(resp.status === 403 ? 'Sin permiso' : `Error ${resp.status}`);
      const a = document.createElement('a');
      a.href = URL.createObjectURL(await resp.blob());
      a.download = `Material_${area.toUpperCase()}_${vista(area)}_${hoy()}.xlsx`;
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
      const area = areaDe(e.target);
      if (!area) return;
      const root = el(area, 'root');

      const filterBtn = e.target.closest('.hpe-column-filter-btn');
      if (filterBtn) {
        e.preventDefault();
        const th = filterBtn.closest('th');
        const pop = th.querySelector('.hpe-column-filter-popover');
        const abrir = !pop.classList.contains('open');
        cerrarPopovers(root, pop);
        pop.classList.toggle('open', abrir);
        filterBtn.classList.toggle('open', abrir);
        filterBtn.setAttribute('aria-expanded', String(abrir));
        th.classList.toggle('hpe-filter-open', abrir);
        if (abrir) pop.querySelector('input')?.focus();
        return;
      }

      // closest: los botones llevan <svg>, el click puede caer en el icono.
      const action = e.target.closest('[data-mat-action]')?.dataset.matAction;
      if (!e.target.closest('.hpe-column-filter-popover')) cerrarPopovers(root);
      if (action === 'clear-column' || action === 'clear-all-columns') {
        if (action === 'clear-column') {
          delete filtrosVista(area)[e.target.closest('th').querySelector('.hpe-column-filter-input').dataset.matField];
        } else {
          estado(area).filtrosPorVista[vista(area)] = {};
        }
        guardarFiltros(area);
        renderEncabezados(area);
        cargar(area);
      } else if (action === 'filtrar') cargar(area);
      else if (action === 'export') exportar(area);
      else if (action === 'first') irAPagina(area, 1);
      else if (action === 'prev') irAPagina(area, estado(area).pag.page - 1);
      else if (action === 'next') irAPagina(area, estado(area).pag.page + 1);
      else if (action === 'last') irAPagina(area, estado(area).pag.totalPages);
    });
    document.body.addEventListener('input', (e) => {
      if (!e.target.matches('.mat-area .hpe-column-filter-input')) return;
      const area = areaDe(e.target);
      const campo = e.target.dataset.matField;
      const valor = e.target.value.trim();
      if (valor) filtrosVista(area)[campo] = valor;
      else delete filtrosVista(area)[campo];
      guardarFiltros(area);
      e.target.closest('th')?.querySelector('.hpe-column-filter-btn')?.classList.toggle('active', Boolean(valor));
      const st = estado(area);
      clearTimeout(st.filterTimer);
      st.filterTimer = setTimeout(() => cargar(area), 300);
    });
    document.body.addEventListener('change', (e) => {
      const area = areaDe(e.target);
      const campo = e.target.dataset?.matEl;
      if (!area || !campo) return;
      if (campo === 'vista' || campo === 'modo') {
        renderEncabezados(area);
        cargar(area);
      } else if (campo === 'per-page') {
        estado(area).pag.perPage = parseInt(e.target.value, 10) || 1000;
        cargar(area);
      }
    });
    document.body.addEventListener('keydown', (e) => {
      const area = areaDe(e.target);
      if (!area) return;
      if (e.key === 'Escape') return cerrarPopovers(el(area, 'root'));
      if (e.key !== 'Enter') return;
      if (e.target.dataset?.matEl === 'page-input') {
        e.preventDefault();
        irAPagina(area, e.target.value);
      } else if (e.target.matches('.hpe-column-filter-input') || e.target.closest('.mat-area-filters')) {
        e.preventDefault();
        clearTimeout(estado(area).filterTimer);
        cargar(area);
      }
    });
  }

  window.initMaterialArea = function (area) {
    initListeners();
    if (!el(area, 'root')) return;
    if (!el(area, 'filter-start').value) el(area, 'filter-start').value = hoy();
    if (!el(area, 'filter-end').value) el(area, 'filter-end').value = hoy();
    estado(area).pag.perPage = parseInt(el(area, 'per-page').value, 10) || 1000;
    renderEncabezados(area);
    cargar(area);
  };
})();
