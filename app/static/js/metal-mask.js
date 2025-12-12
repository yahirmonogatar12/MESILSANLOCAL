(function(){
const USE_DEMO_BACKEND=false;const API_BASE='';
const isActive=()=>!!document.querySelector('#mm-app[data-module="metal-mask"]');
let MM_ROWS=[];let MM_FILTER='ALL';let EDIT_MODE=false;let EDIT_ITEM=null;
let STORAGE_BOXES=[];let SELECTED_STORAGE=null;let PENDING_BOX_OCCUPIED=null;
const $=s=>document.querySelector(s);const fmtInt=n=>(n??0).toLocaleString('en-US');const fmt2=n=>Number.isFinite(n)?n.toFixed(2):'0.00';const todayISO=()=>new Date().toISOString().slice(0,10);const showToast=m=>{const t=$('#mm-toast');t.textContent=m;t.classList.add('mm-show');setTimeout(()=>t.classList.remove('mm-show'),1600)};const perc=(u,m)=>{u=Number(u)||0;m=Number(m)||0;if(!m)return 0;return(u/m)*100};const showLoading=()=>{try{portalToBody('#mm-loading',2147483647,'metal-mask');}catch(_){ } const l=document.querySelector('#mm-loading[data-owner="metal-mask"]')||$('#mm-loading'); if(l){l.style.zIndex='2147483647'; l.style.display='flex';} const b=document.querySelector('#mm-app[data-module="metal-mask"] #mm-btn-save'); if(b) b.disabled=true};const hideLoading=()=>{const l=document.querySelector('#mm-loading[data-owner="metal-mask"]')||$('#mm-loading'); if(l){l.style.display='none';} const b=document.querySelector('#mm-app[data-module="metal-mask"] #mm-btn-save'); if(b) b.disabled=false};
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
function renderGrid(){ if(!isActive()) return; const tb=$('#mm-grid-body'); if(!tb) return; tb.innerHTML='';const rows=MM_ROWS.filter(r=>MM_FILTER==='ALL'?true:r.disuse===MM_FILTER);for(const r of rows){const tr=document.createElement('tr');tr.innerHTML=`
<td>${r.management_no??''}</td><td>${r.storage_box??''}</td><td>${r.pcb_code??''}</td><td>${r.side??''}</td><td>${r.production_date??''}</td>
<td class="mm-num">${fmtInt(r.used_count)}</td><td class="mm-num">${fmtInt(r.max_count)}</td><td class="mm-num">${fmt2(perc(r.used_count,r.max_count))}%</td>
<td class="mm-num">${fmtInt(r.allowance)}</td><td title="${r.model_name??''}">${(r.model_name??'').slice(0,38)}${(r.model_name||'').length>38?'â€¦':''}</td>
<td class="mm-num">${fmt2(r.tension_min)}</td><td class="mm-num">${fmt2(r.tension_max)}</td><td class="mm-num">${fmt2(r.thickness)}</td><td>${r.supplier??''}</td><td>${r.registration_date??''}</td>
<td>${r.disuse==='Desuso'?'<span class="mm-tag disuse">Desuso</span>':r.disuse==='Scrap'?'<span class="mm-tag scrap">Scrap</span>':'<span class="mm-tag use">Uso</span>'}</td>`;tr.addEventListener('dblclick',()=>editRow(r));tb.appendChild(tr)}$('#mm-total').textContent=`Total de Filas : ${rows.length}`}
function rootMM(){ return document.querySelector('#mm-app[data-module="metal-mask"]'); }
function owned(sel){ return document.querySelector(sel+"[data-owner='metal-mask']") || document.querySelector(sel); }
const openDrawer=()=>{
  try{ portalToBody('#mm-drawer', 2147483647,'metal-mask'); }catch(_){ }
  const d=owned('#mm-drawer');
  if(d){ d.classList.add('mm-open'); d.setAttribute('aria-hidden','false'); }
};
const closeDrawer=()=>{
  const d=owned('#mm-drawer');
  if(d){
    d.style.removeProperty('transform');
    d.classList.remove('mm-open');
    d.setAttribute('aria-hidden','true');
    // Reubicar el drawer de vuelta al root del mÃ³dulo para evitar interferencias
    try {
      const root = rootMM();
      if (root && d.parentElement === document.body) {
        root.appendChild(d);
      }
    } catch(_){}
    // Refrescar datos tras cerrar si hubo cambios
    try { if (typeof loadRows==='function') loadRows(); } catch(_){}
  }
};
const resetForm=()=>{$('#mm-form').reset();$('#mm-prod_date').value=todayISO();$('#mm-tension_min').value=0.20;$('#mm-tension_max').value=0.40;$('#mm-thickness').value=0.13;$('#mm-max_count').value=50000;$('#mm-allowance').value=0;$('#mm-disuse-input').value='Uso';$('#mm-management_no').disabled=false;$('#mm-drawer-title').textContent='Gestion de metal mask Registrar';$('#mm-btn-save').textContent='Registrar';hideLoading();EDIT_MODE=false;EDIT_ITEM=null;SELECTED_STORAGE=null};
function editRow(r){EDIT_MODE=true;EDIT_ITEM=r;SELECTED_STORAGE=null;$('#mm-management_no').value=r.management_no??'';$('#mm-storage_box').value=r.storage_box??'';$('#mm-pcb_code').value=r.pcb_code??'';$('#mm-side').value=r.side??'';$('#mm-prod_date').value=r.production_date || todayISO();$('#mm-used_count').value=r.used_count??0;$('#mm-max_count').value=r.max_count??0;$('#mm-allowance').value=r.allowance??0;$('#mm-model_name').value=r.model_name??'';$('#mm-tension_min').value=r.tension_min??0;$('#mm-tension_max').value=r.tension_max??0;$('#mm-thickness').value=r.thickness??0;$('#mm-supplier').value=r.supplier??'';$('#mm-disuse-input').value=r.disuse??'Uso';$('#mm-management_no').disabled=true;$('#mm-drawer-title').textContent=`Gestion de metal mask Editar ${r.management_no}`;$('#mm-btn-save').textContent='Actualizar';openDrawer()}
async function saveRecord(){const p={management_no:$('#mm-management_no').value.trim(),storage_box:$('#mm-storage_box').value.trim(),pcb_code:$('#mm-pcb_code').value.trim(),side:$('#mm-side').value,production_date:$('#mm-prod_date').value||todayISO(),used_count:Number($('#mm-used_count').value||0),max_count:Number($('#mm-max_count').value||0),allowance:Number($('#mm-allowance').value||0),model_name:$('#mm-model_name').value.trim(),tension_min:Number($('#mm-tension_min').value||0),tension_max:Number($('#mm-tension_max').value||0),thickness:Number($('#mm-thickness').value||0),supplier:$('#mm-supplier').value.trim(),registration_date:new Date().toLocaleString('en-GB').replace(',',''),disuse:$('#mm-disuse-input').value||'Uso'};if(!p.management_no){showToast('Falta NÃºmero de GestiÃ³n');hideLoading();return}
showLoading();try{if(EDIT_MODE){const r=await fetch(`${API_BASE}/api/masks/${EDIT_ITEM.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){const errorData=await r.json();throw new Error(errorData.error||'Error al actualizar')}const result=await r.json();
// Handle storage box changes during edit
console.log('Edit mode - SELECTED_STORAGE:', SELECTED_STORAGE);console.log('Edit mode - old storage_box:', EDIT_ITEM.storage_box);console.log('Edit mode - new storage_box:', p.storage_box);
if(p.storage_box !== EDIT_ITEM.storage_box){
// If old storage box exists, set it back to "Disponible"
if(EDIT_ITEM.storage_box){console.log('Setting old storage box to Disponible...');try{const oldStorageBoxes=STORAGE_BOXES.filter(box=>box.management_no===EDIT_ITEM.storage_box);if(oldStorageBoxes.length>0){const oldBox=oldStorageBoxes[0];await fetch(`${API_BASE}/api/storage/${oldBox.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({...oldBox,storage_status:'Disponible'})});console.log('Old storage box set to Disponible')}}catch(err){console.warn('Could not update old storage box:', err)}}
// If new storage box was selected, set it to "Ocupado"
if(SELECTED_STORAGE && p.storage_box){console.log('Setting new storage box to Ocupado...');try{const updateData={management_no:SELECTED_STORAGE.management_no,code:SELECTED_STORAGE.code,name:SELECTED_STORAGE.name,location:SELECTED_STORAGE.location,storage_status:'Ocupado',used_status:SELECTED_STORAGE.used_status||'Usado',note:SELECTED_STORAGE.note||'',registration_date:SELECTED_STORAGE.registration_date||''};await fetch(`${API_BASE}/api/storage/${SELECTED_STORAGE.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(updateData)});console.log('New storage box set to Ocupado')}catch(storageErr){console.error('Could not update new storage status:', storageErr);showToast('MÃ¡scara actualizada, pero no se pudo actualizar el estado de la nueva caja')}}}
Object.assign(EDIT_ITEM,p);await loadRows();showToast(result.message||'Actualizado');closeDrawer()}else{const r=await fetch(`${API_BASE}/api/masks`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){const errorData=await r.json();throw new Error(errorData.error||'Error al registrar')}const result=await r.json();
// Update storage box status to "Ocupado" if storage box was selected
console.log('SELECTED_STORAGE:', SELECTED_STORAGE);console.log('p.storage_box:', p.storage_box);
if(SELECTED_STORAGE && p.storage_box){console.log('Updating storage box to Ocupado...');try{const updateData={management_no:SELECTED_STORAGE.management_no,code:SELECTED_STORAGE.code,name:SELECTED_STORAGE.name,location:SELECTED_STORAGE.location,storage_status:'Ocupado',used_status:SELECTED_STORAGE.used_status||'Usado',note:SELECTED_STORAGE.note||'',registration_date:SELECTED_STORAGE.registration_date||''};console.log('Update data:', updateData);const storageResponse=await fetch(`${API_BASE}/api/storage/${SELECTED_STORAGE.id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(updateData)});console.log('Storage update response:', storageResponse.status);if(!storageResponse.ok){const errorText=await storageResponse.text();console.error('Storage update error:', errorText)}else{console.log('Storage updated successfully')}}catch(storageErr){console.error('Could not update storage status:', storageErr);showToast('MÃ¡scara registrada, pero no se pudo actualizar el estado de la caja')}}
await loadRows();showToast(result.message||'Registrado');closeDrawer()}}catch(err){console.error(err);showToast(err.message||'Error en la operaciÃ³n')}finally{hideLoading()}} 
async function loadRows(){ if(!isActive()) return; try{const r=await fetch(`${API_BASE}/api/masks?disuse=${encodeURIComponent(MM_FILTER)}`);if(!r.ok)throw new Error(await r.text());MM_ROWS=await r.json();renderGrid()}catch(e){console.error(e);showToast('No se pudo cargar')}}
function exportCSV(){const headers=['NÃºmero de GestiÃ³n','Caja de Almacenamiento','CÃ³digo PCB','Lado','Fecha de ProducciÃ³n','Conteo Usado','Conteo MÃ¡ximo','Porcentaje(%)','Tolerancia','Nombre del Modelo','TensiÃ³n(MÃ­n)','TensiÃ³n(MÃ¡x)','Grosor','Proveedor','Fecha de Registro','Desuso'];const rows=MM_ROWS.filter(r=>MM_FILTER==='ALL'?true:r.disuse===MM_FILTER).map(r=>[r.management_no,r.storage_box,r.pcb_code,r.side,r.production_date,r.used_count,r.max_count,(r.max_count?(r.used_count/r.max_count*100).toFixed(2):'0.00'),r.allowance,r.model_name,r.tension_min,r.tension_max,r.thickness,r.supplier,r.registration_date,r.disuse]);const content=[headers,...rows].map(a=>a.map(v=>{const s=(v??'').toString().replace(/"/g,'""');return /[",\n]/.test(s)?`"${s}"`:s}).join(',')).join('\n');const blob=new Blob([content],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='mask_management.csv';document.body.appendChild(a);a.click();a.remove()}

// Storage Modal Functions
async function loadStorageBoxes(){try{const r=await fetch(`${API_BASE}/api/storage`);if(!r.ok)throw new Error('Error al cargar cajas');const response=await r.json();STORAGE_BOXES=response.data||response;renderStorageTable()}catch(e){console.error(e);showToast('Error al cargar cajas de almacenamiento')}}

function renderStorageTable(){const tbody=$('#mm-storage-tbody');const search=$('#mm-storage-search').value.toLowerCase();tbody.innerHTML='';console.log('Total storage boxes loaded:', STORAGE_BOXES.length);console.log('Storage boxes:', STORAGE_BOXES);const filtered=STORAGE_BOXES.filter(box=>box.storage_status==='Disponible'&&((box.management_no||'').toLowerCase().includes(search)||(box.code||'').toLowerCase().includes(search)||(box.name||'').toLowerCase().includes(search)));console.log('Filtered available boxes:', filtered.length);for(const box of filtered){const tr=document.createElement('tr');tr.innerHTML=`<td>${box.management_no||''}</td><td>${box.code||''}</td><td>${box.name||''}</td><td><span class="mm-tag ${box.storage_status==='Disponible'?'available':box.storage_status==='Ocupado'?'occupied':'maintenance'}">${box.storage_status||'Disponible'}</span></td>`;tr.onclick=()=>selectStorageBox(tr,box);tbody.appendChild(tr)}}

function selectStorageBox(tr,box){console.log('Selecting storage box:', box);if(box.storage_status!=='Disponible'){showToast('Solo se pueden seleccionar cajas disponibles');return}document.querySelectorAll('.mm-storage-table tbody tr').forEach(r=>r.classList.remove('selected'));tr.classList.add('selected');SELECTED_STORAGE=box;console.log('SELECTED_STORAGE set to:', SELECTED_STORAGE)}

function filterStorageBoxes(){renderStorageTable()}

function openStorageModal(){
  SELECTED_STORAGE=null;
  try{ portalToBody('#mm-storage-modal', 2147483647,'metal-mask'); }catch(_){ }
  const m=owned('#mm-storage-modal');
  if(m){ m.style.zIndex='2147483647'; m.style.position='fixed'; m.classList.add('show'); }
  const s=document.querySelector('#mm-app[data-module="metal-mask"] #mm-storage-search'); if(s) s.value='';
  loadStorageBoxes()
}

function closeStorageModal(){
  const m=owned('#mm-storage-modal');
  if(m){
    m.classList.remove('show');
    try{ const root=rootMM(); if(root && m.parentElement===document.body){ root.appendChild(m); } }catch(_){ }
  }
}

async function saveStorageChoice(){
  if(!SELECTED_STORAGE){showToast("Selecciona una caja de almacenamiento");return}
  try{ if(PENDING_BOX_OCCUPIED && PENDING_BOX_OCCUPIED.id && PENDING_BOX_OCCUPIED.id!==SELECTED_STORAGE.id){
      const prev=PENDING_BOX_OCCUPIED;
      const payloadPrev={management_no:prev.management_no,code:prev.code,name:prev.name,location:prev.location,storage_status:"Disponible",used_status:prev.used_status||"Usado",note:prev.note||"",registration_date:prev.registration_date||""};
      await fetch(`${API_BASE}/api/storage/${prev.id}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(payloadPrev)});
  }}catch(e){ console.warn("No se pudo liberar caja previa:", e); }
  try{
    const box=SELECTED_STORAGE;
    const payload={management_no:box.management_no,code:box.code,name:box.name,location:box.location,storage_status:"Ocupado",used_status:box.used_status||"Usado",note:box.note||"",registration_date:box.registration_date||""};
    const resp=await fetch(`${API_BASE}/api/storage/${box.id}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    if(!resp.ok){ const txt=await resp.text(); console.error("Error marcando Ocupado:", txt); showToast("No se pudo actualizar estado de la caja"); return; }
    PENDING_BOX_OCCUPIED=box;
  }catch(e){ console.error(e); showToast("Error actualizando caja"); return; }
  document.querySelector('#mm-storage_box').value=SELECTED_STORAGE.management_no||"";
  closeStorageModal();
  showToast("Caja asignada y marcada Ocupado");
}


// Export global handlers used by inline HTML attributes
if (typeof openStorageModal==='function') window.openStorageModal=openStorageModal;
if (typeof closeStorageModal==='function') window.closeStorageModal=closeStorageModal;
if (typeof saveStorageChoice==='function') window.saveStorageChoice=saveStorageChoice;
if (typeof filterStorageBoxes==='function') window.filterStorageBoxes=filterStorageBoxes;

// Provide a re-init function to rebind events after dynamic HTML insertion
window.initMetalMask=window.initMetalMask||(function(){
  return function(){
    try{
      // Elevar overlays al <body> para evitar quedar debajo del header
      portalToBody('#mm-drawer', 2147483600,'metal-mask');
      portalToBody('#mm-storage-modal', 2147483590,'metal-mask');
      portalToBody('#mm-loading', 2147483580,'metal-mask');
      portalToBody('#mm-toast', 2147483610,'metal-mask');
      var app=document.querySelector('#mm-app[data-module="metal-mask"]');
      if(!app) return;
      if(app.dataset.mmInit==='1'){return;}
      app.dataset.mmInit='1';
      var root=app; var q=function(s){return root? root.querySelector(s): null}; var el;
      // Topbar dentro del root
      el=q('#mm-btn-open'); if(el && !el._mmBound){ el.addEventListener('click',function(){try{resetForm();openDrawer()}catch(e){}}); el._mmBound=true; }
      el=q('#mm-btn-export'); if(el && !el._mmBound){ el.addEventListener('click',function(){try{exportCSV&&exportCSV()}catch(e){}}); el._mmBound=true; }
      el=q('#mm-disuse'); if(el && !el._mmBound){ el.addEventListener('change',function(e){try{MM_FILTER=e.target.value;renderGrid()}catch(_){}}); el._mmBound=true; }
      el=q('#mm-btn-search'); if(el && !el._mmBound){ el.addEventListener('click',function(){try{loadRows()}catch(e){}}); el._mmBound=true; }
      el=q('#mm-btn-import'); if(el && !el._mmBound){ el.addEventListener('click',function(){try{showToast&&showToast('Implementa /api/masks/import en el backend')}catch(e){}}); el._mmBound=true; }
      // Drawer (ya portalizado)
      const drawer=document.querySelector('#mm-drawer[data-owner="metal-mask"]')||document.querySelector('#mm-drawer');
      if(drawer){
        const btnClose=drawer.querySelector('#mm-btn-close'); if(btnClose && !btnClose._mmBound){ btnClose.addEventListener('click',function(){ try{ closeDrawer(); }catch(e){} }); btnClose._mmBound=true; }
        const btnSave=drawer.querySelector('#mm-btn-save'); if(btnSave && !btnSave._mmBound){ btnSave.addEventListener('click',function(){ try{ saveRecord(); }catch(e){} }); btnSave._mmBound=true; }
        const btnReset=drawer.querySelector('#mm-btn-reset'); if(btnReset && !btnReset._mmBound){ btnReset.addEventListener('click',function(){ try{ resetForm(); }catch(e){} }); btnReset._mmBound=true; }
      }
      try{if(!EDIT_MODE){resetForm();}loadRows()}catch(e){}
    }catch(e){console.warn('initMetalMask error',e)}
  }
})();

// Teardown del mÃ³dulo MetalMask: quitar listeners, cerrar y remover overlays propios
window.destroyMetalMask = window.destroyMetalMask || function(){
  try{
    const app = document.querySelector('#mm-app[data-module="metal-mask"]');
    if (app) { app.dataset.mmInit = '0'; }
    // Limpiar listeners del topbar (clonar nodos)
    ['#mm-btn-open','#mm-btn-export','#mm-disuse','#mm-btn-search','#mm-btn-import'].forEach(sel=>{
      const el = app ? app.querySelector(sel) : null; if(el && el.parentNode){ const cl = el.cloneNode(true); el.parentNode.replaceChild(cl, el); }
    });
    // Cerrar y limpiar drawer y botones del drawer
    const drawer = document.querySelector('#mm-drawer[data-owner="metal-mask"]');
    if (drawer) {
      ['#mm-btn-close','#mm-btn-save','#mm-btn-reset'].forEach(sel=>{
        const el = drawer.querySelector(sel); if(el && el.parentNode){ const cl = el.cloneNode(true); el.parentNode.replaceChild(cl, el); }
      });
      drawer.classList.remove('mm-open');
      try { drawer.remove(); } catch(_) {}
    }
    // Quitar overlays restantes propios
    ['#mm-loading','#mm-toast','#mm-storage-modal'].forEach(id=>{
      const el = document.querySelector(`${id}[data-owner="metal-mask"]`); if(el && el.parentElement===document.body){ try{ el.remove(); }catch(_){} }
    });
  }catch(e){ console.warn('destroyMetalMask error', e); }
};

// Auto-init seguro para carga directa (no AJAX)
try{
  const doInit=()=>{ if(document.querySelector('#mm-app[data-module="metal-mask"]')){ try{ window.initMetalMask(); }catch(e){} } };
  if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', doInit); } else { doInit(); }
}catch(_){ }

})();
