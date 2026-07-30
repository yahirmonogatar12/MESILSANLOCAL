// ====== plan-assy-ia.js ======
// Propuesta del asistente IA aplicada al plan ASSY (plan_main).
//
// Recalculo del dia: los lotes ya existen y ya estan ligados a material, asi
// que lo normal es APLICAR CAMBIOS sobre ellos (cantidad, linea, grupo, orden)
// conservando su lot_no. Insertar lotes nuevos es una accion aparte y opcional.
(function () {
  if (window.__assyIaPlanReady) return;   // el fragment AJAX recarga los scripts
  window.__assyIaPlanReady = true;

  const MODAL_ID = 'assy-ia-plan-modal';
  const ETIQUETA = { cantidad: 'Cantidad', linea: 'Línea', grupo: 'Grupo', secuencia: 'Orden' };
  let diffActual = null;
  let verMenores = false;

  // Toda diferencia de cantidad viene de que LG movió su demanda: la cantidad
  // del lote es el faltante + colchón + 10%, redondeado a caja. Aunque sean 20
  // pzs, ignorarla deja el plan corto. Lo único que no cambia la cobertura es
  // el reacomodo de bloques (grupo/orden), y eso es lo que se oculta.
  function esRelevante(c) {
    return c.campos.some(k => k === 'cantidad' || k === 'linea');
  }

  const caja = () => document.querySelector(`#${MODAL_ID} [data-ia-list]`);
  const cerrar = () => { const m = document.getElementById(MODAL_ID); if (m) m.remove(); };

  async function api(url, body) {
    const r = await fetch(url, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Error en el servidor');
    return data;
  }

  function abrirModal() {
    cerrar();
    const modal = document.createElement('div');
    modal.id = MODAL_ID;
    modal.style.cssText = 'display:flex;position:fixed;inset:0;background:rgba(0,0,0,.6);' +
      // 16050: por encima del modal de la propuesta del asistente (16000).
      'justify-content:center;align-items:center;z-index:16050;';
    modal.innerHTML =
      '<div style="background:#0e2233;color:#dbe7f3;border:1px solid #20688C;border-radius:6px;' +
      'min-width:640px;max-width:92vw;max-height:85vh;overflow:auto;padding:16px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
      '    <b data-ia-title>Propuesta de la IA</b>' +
      '    <button type="button" data-ia-act="close" class="assy-btn">✕</button>' +
      '  </div>' +
      '  <div data-ia-list>Cargando…</div>' +
      '</div>';
    document.body.appendChild(modal);
    listarPropuestas();
  }

  async function listarPropuestas() {
    const cont = caja();
    try {
      const r = await fetch('/api/plan/propuestas-ia', { credentials: 'same-origin' });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'No se pudieron leer las propuestas');
      if (!data.length) {
        cont.textContent = 'No tienes propuestas. Pídele un plan al asistente IA primero.';
        return;
      }
      cont.innerHTML = tabla(
        ['Fecha', 'Versión', 'Lotes', 'Piezas', 'Estado', ''],
        data.map(p => [
          p.date_to && p.date_to !== p.date_from ? `${p.date_from} a ${p.date_to}` : p.date_from,
          `v${p.version}`, p.total_items, (p.total_qty || 0).toLocaleString(), p.status,
          `<button type="button" class="assy-btn" data-ia-act="diff" data-id="${p.proposal_id}">Revisar</button>`,
        ]));
    } catch (e) { cont.textContent = e.message; }
  }

  function tabla(cabeceras, filas) {
    return '<table style="width:100%;border-collapse:collapse;font-size:13px;">' +
      `<thead><tr style="color:#8fa6c6;text-align:left;">${cabeceras.map(h => `<th>${h}</th>`).join('')}</tr></thead>` +
      `<tbody>${filas.map(f => `<tr style="border-top:1px solid #1b3a52;">${f.map(c => `<td style="padding:3px 6px;">${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  }

  async function verDiff(proposalId) {
    const cont = caja();
    cont.textContent = 'Comparando contra el plan del día…';
    verMenores = false;
    try {
      diffActual = await api('/api/plan/propuesta-ia/diff', { proposal_id: proposalId });
      renderDiff();
    } catch (e) { cont.textContent = e.message; }
  }

  function renderDiff() {
    const d = diffActual;
    const relevantes = d.cambios.filter(esRelevante);
    const menores = d.cambios.filter(c => !esRelevante(c));
    const lista = verMenores ? d.cambios : relevantes;
    const aplicables = relevantes.filter(c => !c.bloqueado).length;
    let html = `<div style="margin-bottom:10px;color:#8fa6c6;">${d.fechas.join(', ')} · ` +
      `${relevantes.length} lotes cambian · ${d.sin_cambio} sin cambio · ` +
      `${d.nuevos.length} requieren lote nuevo · ${d.sobran.length} ya no están en la propuesta</div>` +
      (menores.length
        ? `<div style="margin-bottom:10px;">Se ocultan ${menores.length} lotes que ` +
          `solo se reacomodan de grupo u orden, sin cambiar cantidad ni línea · ` +
          `<a href="#" data-ia-act="toggle-menores" style="color:#7dd3fc;">` +
          `${verMenores ? 'ocultar' : 'verlos'}</a></div>`
        : '');

    if (lista.length) {
      html += '<b>Cambios sobre los lotes que ya están</b>' + tabla(
        ['<input type="checkbox" data-ia-act="all" checked>', 'Lote', 'Parte', 'Cambios', ''],
        lista.map((c) => [
          `<input type="checkbox" class="ia-chk" data-i="${d.cambios.indexOf(c)}" ` +
          `${c.bloqueado ? 'disabled' : (esRelevante(c) ? 'checked' : '')}>`,
          c.lot_no, c.part_no,
          // Un lote arrancado solo admite bajar la cantidad: los demás campos
          // se muestran en gris porque el servidor no los va a aplicar.
          c.campos.map(k => {
            const aplica = (c.aplicables || []).includes(k);
            return `<span title="${aplica ? '' : 'no se aplica: el lote ya arrancó'}" ` +
              `style="background:${aplica ? '#1b3a52' : '#16233300'};border:1px solid #1b3a52;` +
              `color:${aplica ? '' : '#6b7f96'};border-radius:3px;padding:1px 5px;margin-right:4px;">` +
              `${ETIQUETA[k]}: ${c.antes[k]} → <b>${c.despues[k]}</b></span>`;
          }).join(''),
          c.bloqueado
            ? `<span style="color:#fbbf24;">no aplicable: ${c.bloqueado}</span>`
            : [c.urgente ? `<span style="color:#7dd3fc;">${c.razon}</span>` : '',
               c.producido ? `<span style="color:#8fa6c6;">lleva ${c.producido} pzs</span>` : '']
              .filter(Boolean).join(' · '),
        ]));
      html += `<div style="margin:10px 0;"><button type="button" class="assy-btn assy-btn-add" ` +
        `data-ia-act="apply" ${aplicables ? '' : 'disabled'}>Aplicar cambios (${aplicables})</button></div>`;
    } else {
      html += `<div style="margin:8px 0;">Ningún lote cambia de cantidad ni de línea` +
        (menores.length ? `; solo hay ${menores.length} reacomodos de bloque.` : '.') + '</div>';
    }

    if (d.nuevos.length) {
      html += '<b>Requieren lote nuevo (no se suben solos)</b>' + tabla(
        ['Parte', 'Línea', 'Cantidad', 'Grupo'],
        d.nuevos.map(n => [n.part_no, n.linea, n.cantidad, n.grupo]));
      html += `<div style="margin:10px 0;"><button type="button" class="assy-btn" data-ia-act="insert" ` +
        `data-id="${d.proposal_id}">Insertar ${d.nuevos.length} lotes nuevos</button></div>`;
    }

    if (d.sobran.length) {
      html += '<b>Ya no están en la propuesta (revísalos a mano)</b>' + tabla(
        ['Lote', 'Parte', 'Línea', 'Cantidad', 'Estado'],
        d.sobran.map(s => [s.lot_no, s.part_no, s.linea, s.cantidad, s.status]));
    }
    caja().innerHTML = html;
  }

  async function aplicar(btn) {
    const marcados = [...document.querySelectorAll(`#${MODAL_ID} .ia-chk:checked`)]
      .map(chk => diffActual.cambios[Number(chk.dataset.i)])
      .map(c => ({ lot_no: c.lot_no, ...c.despues }));
    if (!marcados.length) { alert('No hay cambios marcados.'); return; }
    btn.disabled = true;
    try {
      const r = await api('/api/plan/propuesta-ia/aplicar-cambios',
        { cambios: marcados, proposal_id: diffActual.proposal_id });
      cerrar();
      const partes = Object.keys(r.schedule || {}).length;
      alert(`Se aplicaron ${r.aplicados} cambios` +
        (partes ? `; el Schedule se actualizó en ${partes} partes` : '') +
        (r.omitidos.length ? `. Omitidos: ${r.omitidos.map(o => `${o.lot_no} (${o.motivo})`).join(', ')}` : '.'));
      if (window.assyLoadPlans) window.assyLoadPlans();
    } catch (e) { alert(e.message); btn.disabled = false; }
  }

  async function insertarNuevos(btn) {
    btn.disabled = true;
    btn.textContent = 'Insertando…';
    try {
      const r = await api('/api/plan/importar-propuesta-ia', { proposal_id: btn.dataset.id });
      cerrar();
      alert(`Insertados ${r.insertados} lotes nuevos` +
        (r.omitidos ? `, ${r.omitidos} ya estaban.` : '.'));
      if (window.assyLoadPlans) window.assyLoadPlans();
    } catch (e) { alert(e.message); btn.disabled = false; btn.textContent = 'Insertar lotes nuevos'; }
  }

  document.addEventListener('click', (e) => {
    if (e.target.closest('#assy-ia-plan-btn')) { e.preventDefault(); abrirModal(); return; }
    if (e.target.id === MODAL_ID) { cerrar(); return; }   // clic fuera de la caja
    const act = e.target.closest('[data-ia-act]');
    if (!act || !act.closest(`#${MODAL_ID}`)) return;
    const accion = act.dataset.iaAct;
    if (accion === 'all') {
      document.querySelectorAll(`#${MODAL_ID} .ia-chk:not(:disabled)`)
        .forEach(chk => { chk.checked = act.checked; });
      return;
    }
    e.preventDefault();
    if (accion === 'close') cerrar();
    else if (accion === 'diff') verDiff(act.dataset.id);
    else if (accion === 'apply') aplicar(act);
    else if (accion === 'insert') insertarNuevos(act);
    else if (accion === 'toggle-menores') { verMenores = !verMenores; renderDiff(); }
  });

  // Entrada directa desde el modal de la propuesta en el asistente IA: se salta
  // la lista y compara esa propuesta contra el plan del dia.
  window.abrirDiffPropuestaIA = (proposalId) => { abrirModal(); verDiff(proposalId); };
})();
