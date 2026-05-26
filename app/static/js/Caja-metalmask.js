(()=>{
// Refactor 2026-05-26 (WF_002): prefijo renombrado #mm-* -> #cmm-* para
// evitar colision de IDs con Metal Mask (que conserva #mm-*). Funcion
// global generateManagementNo -> cmmGenerateManagementNo.
const USE_DEMO_BACKEND=false;const API_BASE='';
const STYLESHEET_ID="control-caja-metal-mask-css";
const STYLESHEET_HREF="/static/css/control_caja_metal_mask.css?v=20260526a";
function ensureModuleStyles(){
  const cur=document.getElementById(STYLESHEET_ID);
  if(cur){
    if(!cur.getAttribute("href")?.includes("20260526a")){
      cur.setAttribute("href",STYLESHEET_HREF);
    }
    return;
  }
  const link=document.createElement("link");
  link.id=STYLESHEET_ID; link.rel="stylesheet"; link.href=STYLESHEET_HREF;
  document.head.appendChild(link);
}
const isActive=()=>!!document.querySelector('#cmm-app[data-module="storage-box"]');
const showLoading=()=>{try{portalToBody('#cmm-loading',2147483647,'storage-box');}catch(_){ } const l=document.querySelector('#cmm-loading[data-owner="storage-box"]')||document.querySelector('#cmm-loading'); if(l){l.style.zIndex='2147483647'; l.style.display='flex';} const btn=document.querySelector('#cmm-app[data-module="storage-box"] #cmm-btn-save'); if(btn) btn.disabled=true};
const hideLoading=()=>{const l=document.querySelector('#cmm-loading[data-owner="storage-box"]')||document.querySelector('#cmm-loading'); if(l){l.style.display='none';} const btn=document.querySelector('#cmm-app[data-module="storage-box"] #cmm-btn-save'); if(btn) btn.disabled=false};
function portalToBody(selector,z,owner){
  try{
    const el=document.querySelector(selector);
    if(!el) return;
    const id=el.id;
    if(id){ const existing=document.getElementById(id); if(existing && existing!==el && existing.parentElement===document.body){ existing.remove(); } }
    if(el.parentElement!==document.body){ document.body.appendChild(el); }
    if(z!=null){ el.style.zIndex=String(z); }
    if(owner){ try{ el.setAttribute('data-owner', owner);}catch(_){}}
  }catch(_){ }
}
let MM_ROWS=[];let MM_FILTER='ALL';let EDIT_MODE=false;let EDIT_ITEM=null;const $=s=>document.querySelector(s);const todayISO=()=>new Date().toISOString().slice(0,10);const showToast=m=>{const t=$('#cmm-toast');t.textContent=m;t.classList.add('cmm-show');setTimeout(()=>t.classList.remove('cmm-show'),1600)};
function renderGrid(){ if(!isActive()) return; const tb=$('#cmm-grid-body'); if(!tb) return; tb.innerHTML='';if(!Array.isArray(MM_ROWS)){MM_ROWS=[];console.warn('MM_ROWS is not an array, resetting to empty array')}const rows=MM_ROWS.filter(r=>MM_FILTER==='ALL'?true:r.storage_status===MM_FILTER);for(const r of rows){const tr=document.createElement('tr');tr.innerHTML=`
<td>${r.management_no??''}</td><td>${r.code??''}</td><td>${r.name??''}</td><td>${r.location??''}</td>
<td>${r.storage_status==='Ocupado'?'<span class="cmm-tag occupied">Ocupado</span>':r.storage_status==='Mantenimiento'?'<span class="cmm-tag maintenance">Mantenimiento</span>':'<span class="cmm-tag available">Disponible</span>'}</td>
<td>${r.used_status==='No Usado'?'<span class="cmm-tag unused">No Usado</span>':'<span class="cmm-tag used">Usado</span>'}</td>
<td title="${r.note??''}">${(r.note??'').slice(0,50)}${(r.note||'').length>50?'â€¦':''}</td><td>${r.registration_date??''}</td>`;tr.addEventListener('dblclick',()=>editRow(r));tb.appendChild(tr)}$('#cmm-total').textContent=`Total de Filas : ${rows.length}`}
function rootSB(){ return document.querySelector('#cmm-app[data-module="storage-box"]'); }
function owned(sel){ return document.querySelector(sel+"[data-owner='storage-box']") || document.querySelector(sel); }
const openDrawer=()=>{
  try{ portalToBody('#cmm-drawer', 2147483647,'storage-box'); }catch(_){ }
  const d=owned('#cmm-drawer');
  if(d){ d.classList.add('cmm-open'); d.setAttribute('aria-hidden','false'); }
};
const closeDrawer=()=>{
  const d=owned('#cmm-drawer');
  if(d){
    d.style.removeProperty('transform');
    d.classList.remove('cmm-open');
    d.setAttribute('aria-hidden','true');
    // Reubicar el drawer de vuelta al root del modulo para evitar interferencias
    try {
      const root = rootSB();
      if (root && d.parentElement === document.body) {
        root.appendChild(d);
      }
    } catch(_){}
    // Refrescar datos tras cerrar si hubo cambios
    try { if (typeof loadRows==='function') loadRows(); } catch(_){}
  }
};
const resetForm=()=>{$('#cmm-form').reset();$('#cmm-storage_status').value='Disponible';$('#cmm-used_status').value='Usado';$('#cmm-management_no').readOnly=false;$('#cmm-drawer-title').textContent='Gestion de Cajas de Almacenamiento - Registrar';$('#cmm-btn-save').textContent='Registrar';hideLoading();EDIT_MODE=false;EDIT_ITEM=null;cmmGenerateManagementNo()};
function editRow(r){EDIT_MODE=true;EDIT_ITEM=r;$('#cmm-management_no').value=r.management_no??'';$('#cmm-code').value=r.code??'';$('#cmm-name').value=r.name??'';$('#cmm-location').value=r.location??'';$('#cmm-storage_status').value=r.storage_status??'Disponible';$('#cmm-used_status').value=r.used_status??'Usado';$('#cmm-note').value=r.note??'';$('#cmm-management_no').readOnly=true;$('#cmm-drawer-title').textContent=`Gestion de Cajas de Almacenamiento - Editar ${r.management_no}`;$('#cmm-btn-save').textContent='Actualizar';openDrawer()}
function cmmGenerateManagementNo(){const code=$('#cmm-code').value;const location=$('#cmm-location').value;const managementNoField=$('#cmm-management_no');if(code&&location){managementNoField.value=code+'-'+location}else if(code){managementNoField.value=code+'-'}else{managementNoField.value=''}}
async function saveRecord(){const p={management_no:$('#cmm-management_no').value.trim(),code:$('#cmm-code').value.trim(),name:$('#cmm-name').value.trim(),location:$('#cmm-location').value.trim(),storage_status:$('#cmm-storage_status').value||'Disponible',used_status:$('#cmm-used_status').value||'Usado',note:$('#cmm-note').value.trim(),registration_date:new Date().toLocaleString('en-GB').replace(',','')};console.log('DEBUG - Datos a enviar:',p);if(!p.management_no){showToast('Falta Numero de Gestion');hideLoading();return}
showLoading();try{if(EDIT_MODE){const r=await fetch(`${API_BASE}/api/storage/${EDIT_ITEM.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){const errorData=await r.json();throw new Error(errorData.error||'Error al actualizar')}const result=await r.json();Object.assign(EDIT_ITEM,p);await loadRows();showToast(result.message||'Actualizado');closeDrawer()}else{const r=await fetch(`${API_BASE}/api/storage`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){const errorData=await r.json();console.log('ERROR DATA:',errorData);showToast(errorData.error||'Error al registrar');hideLoading();return}const result=await r.json();await loadRows();showToast(result.message||'Registrado');closeDrawer()}}catch(err){console.error('CATCH ERROR:',err);showToast(err.message||'Error en la operacion')}finally{hideLoading()}}
async function loadRows(){ if(!isActive()) return; try{const r=await fetch(`${API_BASE}/api/storage?filter_storage_status=${encodeURIComponent(MM_FILTER === 'ALL' ? '' : MM_FILTER)}`);if(!r.ok)throw new Error(await r.text());const response=await r.json();MM_ROWS=response.data || response;renderGrid()}catch(e){console.error(e);showToast('No se pudo cargar')}}
function exportCSV(){const headers=['Numero de Gestion','Codigo','Nombre','Ubicacion','Estado de Almacenamiento','Estado de Uso','Nota','Fecha de Registro'];const rows=MM_ROWS.filter(r=>MM_FILTER==='ALL'?true:r.storage_status===MM_FILTER).map(r=>[r.management_no,r.code,r.name,r.location,r.storage_status,r.used_status,r.note,r.registration_date]);const content=[headers,...rows].map(a=>a.map(v=>{const s=(v??'').toString().replace(/"/g,'""');return /[",\n]/.test(s)?`"${s}"`:s}).join(',')).join('\n');const blob=new Blob([content],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='storage_management.csv';document.body.appendChild(a);a.click();a.remove()}


// Export global handlers used by inline HTML attributes
if (typeof cmmGenerateManagementNo==='function') window.cmmGenerateManagementNo=cmmGenerateManagementNo;

// Provide a re-init function to rebind events after dynamic HTML insertion
window.initStorageBox=window.initStorageBox||(function(){
  return function(){
    try{
      ensureModuleStyles();
      // Elevar overlays al <body> para evitar quedar debajo del header
      portalToBody('#cmm-drawer', 2147483600,'storage-box');
      portalToBody('#cmm-loading', 2147483580,'storage-box');
      portalToBody('#cmm-toast', 2147483610,'storage-box');
      var app=document.querySelector('#cmm-app[data-module="storage-box"]');
      if(!app) return;
      if(app.dataset.cmmInit==='1'){return;}
      app.dataset.cmmInit='1';
      var root=app; var q=function(s){return root? root.querySelector(s): null}; var el;
      // Topbar (dentro del app root)
      el=q('#cmm-btn-open'); if(el && !el._cmmBound){ el.addEventListener('click',function(){try{resetForm();openDrawer()}catch(e){}}); el._cmmBound=true; }
      el=q('#cmm-btn-export'); if(el && !el._cmmBound){ el.addEventListener('click',function(){try{exportCSV&&exportCSV()}catch(e){}}); el._cmmBound=true; }
      el=q('#cmm-status'); if(el && !el._cmmBound){ el.addEventListener('change',function(e){try{MM_FILTER=e.target.value;renderGrid()}catch(_){}}); el._cmmBound=true; }
      el=q('#cmm-btn-search'); if(el && !el._cmmBound){ el.addEventListener('click',function(){try{loadRows()}catch(e){}}); el._cmmBound=true; }
      el=q('#cmm-btn-import'); if(el && !el._cmmBound){ el.addEventListener('click',function(){try{showToast&&showToast('Implementa /api/storage/import en el backend')}catch(e){}}); el._cmmBound=true; }
      // Drawer (ya fue portalizado: esta en body). Enlazar directamente dentro del drawer movido
      const drawer=document.querySelector('#cmm-drawer[data-owner="storage-box"]')||document.querySelector('#cmm-drawer');
      if(drawer){
        const btnClose=drawer.querySelector('#cmm-btn-close'); if(btnClose && !btnClose._cmmBound){ btnClose.addEventListener('click',function(){ try{ closeDrawer(); }catch(e){} }); btnClose._cmmBound=true; }
        const btnSave=drawer.querySelector('#cmm-btn-save'); if(btnSave && !btnSave._cmmBound){ btnSave.addEventListener('click',function(){ try{ saveRecord(); }catch(e){} }); btnSave._cmmBound=true; }
        const btnReset=drawer.querySelector('#cmm-btn-reset'); if(btnReset && !btnReset._cmmBound){ btnReset.addEventListener('click',function(){ try{ resetForm(); }catch(e){} }); btnReset._cmmBound=true; }
      }
      try{resetForm();loadRows()}catch(e){}
    }catch(e){console.warn('initStorageBox error',e)}
  }
})();

// Teardown del modulo StorageBox: quitar listeners, cerrar y remover overlays propios
window.destroyStorageBox = window.destroyStorageBox || function(){
  try{
    const app = document.querySelector('#cmm-app[data-module="storage-box"]');
    if (app) { app.dataset.cmmInit = '0'; }
    // Limpiar listeners del topbar (clonar nodos)
    ['#cmm-btn-open','#cmm-btn-export','#cmm-status','#cmm-btn-search','#cmm-btn-import'].forEach(sel=>{
      const el = app ? app.querySelector(sel) : null; if(el && el.parentNode){ const cl = el.cloneNode(true); el.parentNode.replaceChild(cl, el); }
    });
    // Cerrar y limpiar drawer y botones del drawer
    const drawer = document.querySelector('#cmm-drawer[data-owner="storage-box"]');
    if (drawer) {
      ['#cmm-btn-close','#cmm-btn-save','#cmm-btn-reset'].forEach(sel=>{
        const el = drawer.querySelector(sel); if(el && el.parentNode){ const cl = el.cloneNode(true); el.parentNode.replaceChild(cl, el); }
      });
      drawer.classList.remove('cmm-open');
      try { drawer.remove(); } catch(_) {}
    }
    // Quitar overlays restantes propios
    ['#cmm-loading','#cmm-toast'].forEach(id=>{
      const el = document.querySelector(`${id}[data-owner="storage-box"]`); if(el && el.parentElement===document.body){ try{ el.remove(); }catch(_){} }
    });
  }catch(e){ console.warn('destroyStorageBox error', e); }
};

// Auto-init seguro para carga directa (no AJAX)
try{
  const doInit=()=>{ if(document.querySelector('#cmm-app[data-module="storage-box"]')){ try{ window.initStorageBox(); }catch(e){} } };
  if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', doInit); } else { doInit(); }
}catch(_){ }

})();
