// ====== plan-assy-excel.js (exportar planes a Excel) ======
// Extraido de plan.js (2026-05-26). Sin cambios funcionales, solo IDs renombrados a #assy-*.

async function exportarExcel() {
  try {
    const exportBtn = document.getElementById('assy-export-excel-btn');
    const originalText = exportBtn.textContent;

    // Mostrar estado de carga
    exportBtn.textContent = 'Generando Excel...';
    exportBtn.disabled = true;
    exportBtn.style.backgroundColor = '#f39c12';

    // Recopilar todos los datos organizados por grupos visuales
    const groupedPlansData = [];

    // Iterar sobre los grupos visuales en orden
    visualGroups.groups.forEach((group, groupIndex) => {
      if (group.plans && group.plans.length > 0) {
        // Aoadir marcador de grupo
        groupedPlansData.push({
          isGroupHeader: true,
          groupTitle: group.title || `GRUPO ${groupIndex + 1}`,
          groupIndex: groupIndex
        });

        // Aoadir todos los planes del grupo en orden de secuencia
        const sortedPlans = [...group.plans].sort((a, b) => (a.sequence || 0) - (b.sequence || 0));

        sortedPlans.forEach(plan => {
          const planData = {
            secuencia: plan.sequence || '',
            lot_no: plan.lot_no || '',
            wo_code: plan.wo_code || '',
            po_code: plan.po_code || '',
            working_date: plan.working_date || '',
            line: plan.line || '',
            turno: plan.turno || '',
            model_code: plan.model_code || '',
            part_no: plan.part_no || '',
            project: plan.project || '',
            process: plan.process || '',
            ct: plan.ct || '',
            uph: plan.uph || '',
            plan_count: parseInt(plan.plan_count) || 0,
            produced: parseInt(plan.produced) || 0,
            output: parseInt(plan.output) || 0,
            entregadas_main: parseInt(plan.entregadas_main) || 0,
            status: plan.status || 'PLAN',
            tiempo_produccion: plan.tiempo_produccion || '',
            inicio: plan.inicio || '',
            fin: plan.fin || '',
            grupo: group.title || `GRUPO ${groupIndex + 1}`,
            extra: plan.extra || '',
            groupIndex: groupIndex
          };

          groupedPlansData.push(planData);
        });
      }
    });

    // Si no hay grupos visuales definidos, usar el motodo anterior como fallback
    if (groupedPlansData.length === 0) {
      const tbody = document.getElementById('assy-tableBody');
      const rows = Array.from(tbody.querySelectorAll('tr'));

      rows.forEach((row, index) => {
        // Saltar filas de separadores de grupos
        if (row.classList.contains('group-spacer')) {
          // Agregar marcador de grupo
          const groupTitle = row.textContent?.trim() || `GRUPO ${Math.floor(index / 5) + 1}`;
          groupedPlansData.push({
            isGroupHeader: true,
            groupTitle: groupTitle,
            groupIndex: Math.floor(index / 5)
          });
          return;
        }

        const cells = row.querySelectorAll('td');
        if (cells.length === 0) return;

        // Obtener lot_no para determinar el grupo visual
        const lot_no = cells[1]?.textContent?.trim() || '';

        // Determinar el grupo visual basado en la posicion en visualGroups
        let grupoVisual = `GRUPO ${Math.floor(index / 5) + 1}`;
        if (lot_no && visualGroups.planAssignments.has(lot_no)) {
          const groupIndex = visualGroups.planAssignments.get(lot_no);
          if (visualGroups.groups[groupIndex]) {
            grupoVisual = visualGroups.groups[groupIndex].title || `GRUPO ${groupIndex + 1}`;
          }
        }

        // Si no se encuentra en visualGroups, buscar por la seccion del DOM
        if (!grupoVisual || grupoVisual.includes('undefined')) {
          // Buscar hacia atros para encontrar el separador de grupo mos cercano
          let currentRow = row.previousElementSibling;
          while (currentRow) {
            if (currentRow.classList.contains('group-spacer')) {
              const spacerText = currentRow.textContent?.trim();
              if (spacerText && spacerText.includes('GRUPO')) {
                grupoVisual = spacerText;
                break;
              }
            }
            currentRow = currentRow.previousElementSibling;
          }
        }

        // Extraer datos de cada celda
        const planData = {
          secuencia: cells[0]?.textContent?.trim() || '',
          lot_no: lot_no,
          wo_code: cells[2]?.textContent?.trim() || '',
          po_code: cells[3]?.textContent?.trim() || '',
          working_date: cells[4]?.textContent?.trim() || '',
          line: cells[5]?.textContent?.trim() || '',
          turno: cells[6]?.textContent?.trim() || '',
          model_code: cells[7]?.textContent?.trim() || '',
          part_no: cells[8]?.textContent?.trim() || '',
          project: cells[9]?.textContent?.trim() || '',
          process: cells[10]?.textContent?.trim() || '',
          ct: cells[11]?.textContent?.trim() || '',
          uph: cells[12]?.textContent?.trim() || '',
          plan_count: parseInt(cells[13]?.textContent) || 0,
          produced: parseInt(cells[14]?.textContent) || 0,
          output: parseInt(cells[15]?.textContent) || 0,
          entregadas_main: parseInt(cells[16]?.textContent) || 0,
          status: cells[17]?.textContent?.trim() || 'PLAN',
          tiempo_produccion: cells[18]?.textContent?.trim() || '',
          inicio: cells[19]?.textContent?.trim() || '',
          fin: cells[20]?.textContent?.trim() || '',
          grupo: grupoVisual, // Usar el grupo visual real en lugar del campo de celda
          extra: cells[21]?.textContent?.trim() || '',
          groupIndex: Math.floor(index / 5)
        };

        groupedPlansData.push(planData);
      });
    }

    if (groupedPlansData.length === 0) {
      throw new Error('No hay datos para exportar');
    }

    // Enviar datos al backend
    const response = await fetch('/api/plan/export-excel', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        plans: groupedPlansData
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Error al generar el archivo Excel');
    }

    // Obtener el archivo como blob
    const blob = await response.blob();

    // Crear enlace de descarga
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;

    // Generar nombre del archivo con fecha
    const now = new Date();
    const dateStr = now.getFullYear().toString() +
      (now.getMonth() + 1).toString().padStart(2, '0') +
      now.getDate().toString().padStart(2, '0') + '_' +
      now.getHours().toString().padStart(2, '0') +
      now.getMinutes().toString().padStart(2, '0');
    const filename = `Plan_Produccion_${dateStr}.xlsx`;

    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);

    // Feedback de oxito
    exportBtn.textContent = '? Excel Descargado';
    exportBtn.style.backgroundColor = '#27ae60';

    setTimeout(() => {
      exportBtn.textContent = originalText;
      exportBtn.style.backgroundColor = '#27ae60';
      exportBtn.disabled = false;
    }, 2000);

  } catch (error) {
    // Error al exportar a Excel

    const exportBtn = document.getElementById('assy-export-excel-btn');
    exportBtn.textContent = '? Error al exportar';
    exportBtn.style.backgroundColor = '#e74c3c';

    setTimeout(() => {
      exportBtn.textContent = '?? Exportar Excel';
      exportBtn.style.backgroundColor = '#27ae60';
      exportBtn.disabled = false;
    }, 3000);
  }
}

// Export window.assyExportarExcel (consumido desde scriptMain.js y delegation)
window.assyExportarExcel = exportarExcel;
