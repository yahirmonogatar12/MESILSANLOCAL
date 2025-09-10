      function renderPlanData(data) {
        // aplica después de render
        if (!elements.tableBody) return;
        
        // Limpiar tabla
        elements.tableBody.innerHTML = '';
        
        data.forEach((item, index) => {
          const row = document.createElement('tr');
          row.setAttribute('data-plan-id', String(item.id||''));
          const pct = Math.min(100, Math.round(((item.producido || 0) / (item.qty || 1)) * 100));
          const falta = Math.max(0, (item.qty || 0) - (item.producido || 0));
          
          let statusClass = 'pending';
          let statusText = 'PLANEADO';
          
          // Lógica simplificada: priorizar run_status sobre estatus
          console.log(`🔄 Plan ${item.id} - run_status: ${item.run_status}, estatus: ${item.estatus}`);
          
          // Primero verificar run_status (más específico)
          if (item.run_status === 'RUNNING') {
            statusClass = 'partial';
            statusText = 'INICIADO';
          } else if (item.run_status === 'PAUSED') {
            statusClass = 'warning';
            statusText = 'PAUSADO';
          } else if (item.run_status === 'ENDED') {
            statusClass = 'completed';
            statusText = 'FINALIZADO';
          }
          // Si no hay run_status activo, usar estatus de trazabilidad
          else if (item.estatus === 'FINALIZADO') {
            statusClass = 'completed';
            statusText = 'FINALIZADO';
          } else if (item.estatus === 'INICIADO') {
            statusClass = 'partial';
            statusText = 'INICIADO';
          } else if (item.estatus === 'PLANEADO') {
            statusClass = 'pending';
            statusText = 'PLANEADO';
          }
          // Fallback basado en progreso
          else {
            if (pct >= 100) {
              statusClass = 'completed';
              statusText = 'COMPLETADO';
            } else if (pct > 0) {
              statusClass = 'partial';
              statusText = 'EN PROCESO';
            } else {
              statusClass = 'pending';
              statusText = 'PENDIENTE';
            }
          }
          
          row.innerHTML = `
            <td class="mono text-center">${item.id || '-'}</td>
            <td class="text-center">${item.linea || '-'}</td>
            <td class="text-center font-mono">${item.lote || '-'}</td>
            <td class="text-center">${item.nparte || '-'}</td>
            <td class="text-center">${item.modelo || '-'}</td>
            <td class="text-center">${item.tipo || '-'}</td>
            <td class="text-center">${item.turno || '-'}</td>
            <td class="text-center">${item.ct || '-'}</td>
            <td class="text-center">${item.uph || '-'}</td>
            <td class="text-center">${item.qty || 0}</td>
            <td class="text-center">${item.producido || 0}</td>
            <td class="text-center">${falta}</td>
            <td class="text-center">${pct}%</td>
            <td class="text-center">
              <span class="status-tag ${statusClass}">${statusText}</span>
            </td>
            <td class="text-center">
              <div class="btn-group">
                <button onclick="startRun(${item.id})" class="btn-start" title="Iniciar">▶</button>
                <button onclick="pauseRun(${item.id})" class="btn-pause" title="Pausar">⏸</button>
                <button onclick="endRun(${item.id})" class="btn-end" title="Terminar">⏹</button>
              </div>
            </td>
          `;
          
          // MODO ENFOQUE: efecto visual cuando está enfocado
          if (currentPlanEnfoque && currentPlanEnfoque.toString() === item.id.toString()) {
            row.style.background = 'rgba(52, 152, 219, 0.1)';
            row.style.border = '2px solid rgba(52, 152, 219, 0.3)';
            row.style.borderRadius = '4px';
          }
          
          // Agregar event listener para doble click (MODO ENFOQUE)
          row.addEventListener('dblclick', function() {
            filtrarPorPlan(item.id);
          });
          
          elements.tableBody.appendChild(row);
        });
      }
