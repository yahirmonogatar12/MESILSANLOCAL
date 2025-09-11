(()=>{
const USE_DEMO_BACKEND=false;const API_BASE='';
const isActive=()=>!!document.querySelector('#mm-app[data-module="storage-box"]');
const showLoading=()=>{try{portalToBody('#mm-loading',2147483647,'storage-box');}catch(_){ } const l=document.querySelector('#mm-loading[data-owner="storage-box"]')||document.querySelector('#mm-loading'); if(l){l.style.zIndex='2147483647'; l.style.display='flex';} const btn=document.querySelector('#mm-app[data-module="storage-box"] #mm-btn-save'); if(btn) btn.disabled=true};
const hideLoading=()=>{const l=document.querySelector('#mm-loading[data-owner="storage-box"]')||document.querySelector('#mm-loading'); if(l){l.style.display='none';} const btn=document.querySelector('#mm-app[data-module="storage-box"] #mm-btn-save'); if(btn) btn.disabled=false};
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
let MM_ROWS=[];let MM_FILTER='ALL';let EDIT_MODE=false;let EDIT_ITEM=null;const $=s=>document.querySelector(s);const todayISO=()=>new Date().toISOString().slice(0,10);const showToast=m=>{const t=$('#mm-toast');t.textContent=m;t.classList.add('mm-show');setTimeout(()=>t.classList.remove('mm-show'),1600)};
function renderGrid(){ if(!isActive()) return; const tb=$('#mm-grid-body'); if(!tb) return; tb.innerHTML='';if(!Array.isArray(MM_ROWS)){MM_ROWS=[];console.warn('MM_ROWS is not an array, resetting to empty array')}const rows=MM_ROWS.filter(r=>MM_FILTER==='ALL'?true:r.storage_status===MM_FILTER);for(const r of rows){const tr=document.createElement('tr');tr.innerHTML=`
<td>${r.management_no??''}</td><td>${r.code??''}</td><td>${r.name??''}</td><td>${r.location??''}</td>
<td>${r.storage_status==='Ocupado'?'<span class="mm-tag occupied">Ocupado</span>':r.storage_status==='Mantenimiento'?'<span class="mm-tag maintenance">Mantenimiento</span>':'<span class="mm-tag available">Disponible</span>'}</td>
<td>${r.used_status==='No Usado'?'<span class="mm-tag unused">No Usado</span>':'<span class="mm-tag used">Usado</span>'}</td>
<td title="${r.note??''}">${(r.note??'').slice(0,50)}${(r.note||'').length>50?'…':''}</td><td>${r.registration_date??''}</td>`;tr.addEventListener('dblclick',()=>editRow(r));tb.appendChild(tr)}$('#mm-total').textContent=`Total de Filas : ${rows.length}`}
function rootSB(){ return document.querySelector('#mm-app[data-module="storage-box"]'); }
function owned(sel){ return document.querySelector(sel+"[data-owner='storage-box']") || document.querySelector(sel); }
const openDrawer=()=>{
  try{ portalToBody('#mm-drawer', 2147483647,'storage-box'); }catch(_){ }
  const d=owned('#mm-drawer');
  if(d){ d.classList.add('mm-open'); d.setAttribute('aria-hidden','false'); }
};
const closeDrawer=()=>{
  const d=owned('#mm-drawer');
  if(d){
    d.style.removeProperty('transform');
    d.classList.remove('mm-open');
    d.setAttribute('aria-hidden','true');
    // Reubicar el drawer de vuelta al root del módulo para evitar interferencias
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
const resetForm=()=>{$('#mm-form').reset();$('#mm-storage_status').value='Disponible';$('#mm-used_status').value='Usado';$('#mm-management_no').readOnly=false;$('#mm-drawer-title').textContent='Gestión de Cajas de Almacenamiento — Registrar';$('#mm-btn-save').textContent='Registrar';hideLoading();EDIT_MODE=false;EDIT_ITEM=null;generateManagementNo()};
function editRow(r){EDIT_MODE=true;EDIT_ITEM=r;$('#mm-management_no').value=r.management_no??'';$('#mm-code').value=r.code??'';$('#mm-name').value=r.name??'';$('#mm-location').value=r.location??'';$('#mm-storage_status').value=r.storage_status??'Disponible';$('#mm-used_status').value=r.used_status??'Usado';$('#mm-note').value=r.note??'';$('#mm-management_no').readOnly=true;$('#mm-drawer-title').textContent=`Gestión de Cajas de Almacenamiento — Editar ${r.management_no}`;$('#mm-btn-save').textContent='Actualizar';openDrawer()}
function generateManagementNo(){const code=$('#mm-code').value;const location=$('#mm-location').value;const managementNoField=$('#mm-management_no');if(code&&location){managementNoField.value=code+'-'+location}else if(code){managementNoField.value=code+'-'}else{managementNoField.value=''}}
async function saveRecord(){const p={management_no:$('#mm-management_no').value.trim(),code:$('#mm-code').value.trim(),name:$('#mm-name').value.trim(),location:$('#mm-location').value.trim(),storage_status:$('#mm-storage_status').value||'Disponible',used_status:$('#mm-used_status').value||'Usado',note:$('#mm-note').value.trim(),registration_date:new Date().toLocaleString('en-GB').replace(',','')};console.log('DEBUG - Datos a enviar:',p);if(!p.management_no){showToast('Falta Número de Gestión');hideLoading();return}
showLoading();try{if(EDIT_MODE){const r=await fetch(`${API_BASE}/api/storage/${EDIT_ITEM.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){const errorData=await r.json();throw new Error(errorData.error||'Error al actualizar')}const result=await r.json();Object.assign(EDIT_ITEM,p);await loadRows();showToast(result.message||'Actualizado');closeDrawer()}else{const r=await fetch(`${API_BASE}/api/storage`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){const errorData=await r.json();console.log('ERROR DATA:',errorData);showToast(errorData.error||'Error al registrar');hideLoading();return}const result=await r.json();await loadRows();showToast(result.message||'Registrado');closeDrawer()}}catch(err){console.error('CATCH ERROR:',err);showToast(err.message||'Error en la operación')}finally{hideLoading()}} 
async function loadRows(){ if(!isActive()) return; try{const r=await fetch(`${API_BASE}/api/storage?filter_storage_status=${encodeURIComponent(MM_FILTER === 'ALL' ? '' : MM_FILTER)}`);if(!r.ok)throw new Error(await r.text());const response=await r.json();MM_ROWS=response.data || response;renderGrid()}catch(e){console.error(e);showToast('No se pudo cargar')}}
function exportCSV(){const headers=['Número de Gestión','Código','Nombre','Ubicación','Estado de Almacenamiento','Estado de Uso','Nota','Fecha de Registro'];const rows=MM_ROWS.filter(r=>MM_FILTER==='ALL'?true:r.storage_status===MM_FILTER).map(r=>[r.management_no,r.code,r.name,r.location,r.storage_status,r.used_status,r.note,r.registration_date]);const content=[headers,...rows].map(a=>a.map(v=>{const s=(v??'').toString().replace(/"/g,'""');return /[",\n]/.test(s)?`"${s}"`:s}).join(',')).join('\n');const blob=new Blob([content],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='storage_management.csv';document.body.appendChild(a);a.click();a.remove()}


// Export global handlers used by inline HTML attributes
if (typeof generateManagementNo==='function') window.generateManagementNo=generateManagementNo;

// Provide a re-init function to rebind events after dynamic HTML insertion
window.initStorageBox=window.initStorageBox||(function(){
  return function(){
    try{
      // Elevar overlays al <body> para evitar quedar debajo del header
      portalToBody('#mm-drawer', 2147483600,'storage-box');
      portalToBody('#mm-loading', 2147483580,'storage-box');
      portalToBody('#mm-toast', 2147483610,'storage-box');
      var app=document.querySelector('#mm-app[data-module="storage-box"]');
      if(!app) return;
      if(app.dataset.sbInit==='1'){return;}
      app.dataset.sbInit='1';
      var root=app; var q=function(s){return root? root.querySelector(s): null}; var el;
      // Topbar (dentro del app root)
      el=q('#mm-btn-open'); if(el && !el._sbBound){ el.addEventListener('click',function(){try{resetForm();openDrawer()}catch(e){}}); el._sbBound=true; }
      el=q('#mm-btn-export'); if(el && !el._sbBound){ el.addEventListener('click',function(){try{exportCSV&&exportCSV()}catch(e){}}); el._sbBound=true; }
      el=q('#mm-status'); if(el && !el._sbBound){ el.addEventListener('change',function(e){try{MM_FILTER=e.target.value;renderGrid()}catch(_){}}); el._sbBound=true; }
      el=q('#mm-btn-search'); if(el && !el._sbBound){ el.addEventListener('click',function(){try{loadRows()}catch(e){}}); el._sbBound=true; }
      el=q('#mm-btn-import'); if(el && !el._sbBound){ el.addEventListener('click',function(){try{showToast&&showToast('Implementa /api/storage/import en el backend')}catch(e){}}); el._sbBound=true; }
      // Drawer (ya fue portalizado: está en body). Enlazar directamente dentro del drawer movido
      const drawer=document.querySelector('#mm-drawer[data-owner="storage-box"]')||document.querySelector('#mm-drawer');
      if(drawer){
        const btnClose=drawer.querySelector('#mm-btn-close'); if(btnClose && !btnClose._sbBound){ btnClose.addEventListener('click',function(){ try{ closeDrawer(); }catch(e){} }); btnClose._sbBound=true; }
        const btnSave=drawer.querySelector('#mm-btn-save'); if(btnSave && !btnSave._sbBound){ btnSave.addEventListener('click',function(){ try{ saveRecord(); }catch(e){} }); btnSave._sbBound=true; }
        const btnReset=drawer.querySelector('#mm-btn-reset'); if(btnReset && !btnReset._sbBound){ btnReset.addEventListener('click',function(){ try{ resetForm(); }catch(e){} }); btnReset._sbBound=true; }
      }
      try{resetForm();loadRows()}catch(e){}
    }catch(e){console.warn('initStorageBox error',e)}
  }
})();

// Teardown del módulo StorageBox: quitar listeners, cerrar y remover overlays propios
window.destroyStorageBox = window.destroyStorageBox || function(){
  try{
    const app = document.querySelector('#mm-app[data-module="storage-box"]');
    if (app) { app.dataset.sbInit = '0'; }
    // Limpiar listeners del topbar (clonar nodos)
    ['#mm-btn-open','#mm-btn-export','#mm-status','#mm-btn-search','#mm-btn-import'].forEach(sel=>{
      const el = app ? app.querySelector(sel) : null; if(el && el.parentNode){ const cl = el.cloneNode(true); el.parentNode.replaceChild(cl, el); }
    });
    // Cerrar y limpiar drawer y botones del drawer
    const drawer = document.querySelector('#mm-drawer[data-owner="storage-box"]');
    if (drawer) {
      ['#mm-btn-close','#mm-btn-save','#mm-btn-reset'].forEach(sel=>{
        const el = drawer.querySelector(sel); if(el && el.parentNode){ const cl = el.cloneNode(true); el.parentNode.replaceChild(cl, el); }
      });
      drawer.classList.remove('mm-open');
      try { drawer.remove(); } catch(_) {}
    }
    // Quitar overlays restantes propios
    ['#mm-loading','#mm-toast'].forEach(id=>{
      const el = document.querySelector(`${id}[data-owner="storage-box"]`); if(el && el.parentElement===document.body){ try{ el.remove(); }catch(_){} }
    });
  }catch(e){ console.warn('destroyStorageBox error', e); }
};

// Auto-init seguro para carga directa (no AJAX)
try{
  const doInit=()=>{ if(document.querySelector('#mm-app[data-module="storage-box"]')){ try{ window.initStorageBox(); }catch(e){} } };
  if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', doInit); } else { doInit(); }
}catch(_){ }

})();

