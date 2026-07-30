// ====== plan-assy-ia.js ======
// Baja una propuesta del asistente IA (lg_plan_proposals) al plan ASSY
// (plan_main). Bloque B<n> de la propuesta -> GRUPO n de esta pantalla.
// Solo agrega lo que falta: reimportar no duplica.
(function () {
  if (window.__assyIaPlanReady) return;   // el fragment AJAX recarga los scripts
  window.__assyIaPlanReady = true;

  const MODAL_ID = 'assy-ia-plan-modal';

  function cerrar() {
    const m = document.getElementById(MODAL_ID);
    if (m) m.remove();
  }

  function abrirModal() {
    cerrar();
    const modal = document.createElement('div');
    modal.id = MODAL_ID;
    modal.style.cssText = 'display:flex;position:fixed;inset:0;background:rgba(0,0,0,.6);' +
      'justify-content:center;align-items:center;z-index:10000;';
    modal.innerHTML =
      '<div style="background:#0e2233;color:#dbe7f3;border:1px solid #20688C;border-radius:6px;' +
      'min-width:560px;max-width:90vw;max-height:80vh;overflow:auto;padding:16px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
      '    <b>Insertar propuesta de la IA</b>' +
      '    <button type="button" data-ia-act="close" class="assy-btn">✕</button>' +
      '  </div>' +
      '  <div data-ia-list>Cargando…</div>' +
      '</div>';
    document.body.appendChild(modal);
    cargarPropuestas();
  }

  async function cargarPropuestas() {
    const cont = document.querySelector(`#${MODAL_ID} [data-ia-list]`);
    try {
      const r = await fetch('/api/plan/propuestas-ia', { credentials: 'same-origin' });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'No se pudieron leer las propuestas');
      if (!data.length) {
        cont.textContent = 'No tienes propuestas. Pídele un plan al asistente IA primero.';
        return;
      }
      cont.innerHTML =
        '<table style="width:100%;border-collapse:collapse;font-size:13px;">' +
        '<thead><tr style="color:#8fa6c6;text-align:left;">' +
        '<th>Fecha</th><th>Versión</th><th>Lotes</th><th>Piezas</th><th>Estado</th><th></th>' +
        '</tr></thead><tbody>' +
        data.map(p =>
          '<tr style="border-top:1px solid #1b3a52;">' +
          `<td>${p.date_to && p.date_to !== p.date_from ? `${p.date_from} a ${p.date_to}` : p.date_from}</td>` +
          `<td>v${p.version}</td><td>${p.total_items}</td>` +
          `<td>${(p.total_qty || 0).toLocaleString()}</td><td>${p.status}</td>` +
          `<td><button type="button" class="assy-btn" data-ia-act="insert" ` +
          `data-id="${p.proposal_id}">Insertar</button></td></tr>`
        ).join('') +
        '</tbody></table>';
    } catch (e) {
      cont.textContent = e.message;
    }
  }

  async function insertar(btn) {
    btn.disabled = true;
    btn.textContent = 'Insertando…';
    try {
      const r = await fetch('/api/plan/importar-propuesta-ia', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal_id: btn.dataset.id }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'No se pudo insertar');
      cerrar();
      alert(`Insertados ${data.insertados} lotes` +
            (data.omitidos ? `, ${data.omitidos} ya estaban en el plan.` : '.'));
      if (window.assyLoadPlans) window.assyLoadPlans();
    } catch (e) {
      alert(e.message);
      btn.disabled = false;
      btn.textContent = 'Insertar';
    }
  }

  document.addEventListener('click', (e) => {
    const abrir = e.target.closest('#assy-ia-plan-btn');
    if (abrir) { e.preventDefault(); abrirModal(); return; }
    const act = e.target.closest('[data-ia-act]');
    if (!act || !act.closest(`#${MODAL_ID}`)) return;
    e.preventDefault();
    if (act.dataset.iaAct === 'close') cerrar();
    else insertar(act);
  });

  document.addEventListener('click', (e) => {
    if (e.target.id === MODAL_ID) cerrar();   // clic fuera de la caja
  });
})();
