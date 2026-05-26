// Mostrar/ocultar el contenedor de material según el botón
document.addEventListener("DOMContentLoaded", function () {
  const materialContainer = document.getElementById("material-container");
  const informacionBasicaContent = document.getElementById(
    "informacion-basica-content",
  );
  const controlMaterialContent = document.getElementById(
    "control-material-content",
  );
  const controlProduccionContent = document.getElementById(
    "control-produccion-content",
  );
  const controlProcesoContent = document.getElementById(
    "control-proceso-content",
  );
  const controlCalidadContent = document.getElementById(
    "control-calidad-content",
  );
  const controlResultadosContent = document.getElementById(
    "control-resultados-content",
  );
  const controlReporteContent = document.getElementById(
    "control-reporte-content",
  );
  const configuracionProgramaContent = document.getElementById(
    "configuracion-programa-content",
  );
  const materialContentArea = document.getElementById("material-content-area");
  const informacionBasicaContentArea = document.getElementById(
    "informacion-basica-content-area",
  );
  const materialInfoContainer = document.getElementById(
    "material-info-container",
  );
  const controlAlmacenContainer = document.getElementById(
    "control-almacen-container",
  );
  const controlSalidaContainer = document.getElementById(
    "control-salida-container",
  );
  const controlRetornoContainer = document.getElementById(
    "control-retorno-container",
  );
  const reciboPagoContainer = document.getElementById("recibo-pago-container");
  const historialEntradasContainer = document.getElementById(
    "historial-entradas-unique-container",
  );
  const historialSalidasContainer = document.getElementById(
    "historial-salidas-unique-container",
  );
  const historialRetornosContainer = document.getElementById(
    "historial-retornos-unique-container",
  );
  const estatusMaterialContainer = document.getElementById(
    "estatus-material-container",
  );
  const materialSustitutoContainer = document.getElementById(
    "material-sustituto-container",
  );
  const consultarPepsContainer = document.getElementById(
    "consultar-peps-container",
  );
  const longtermInventoryContainer = document.getElementById(
    "longterm-inventory-unique-container",
  );
  const registroMaterialContainer = document.getElementById(
    "registro-material-container",
  );
  const historialInventarioContainer = document.getElementById(
    "historial-inventario-container",
  );
  const ajusteNumeroContainer = document.getElementById(
    "ajuste-numero-container",
  );
  const navButtons = document.querySelectorAll(".nav-button");

  // Función para ocultar todo el contenido
  function hideAllContent() {
    informacionBasicaContent.style.display = "none";
    controlMaterialContent.style.display = "none";
    controlProduccionContent.style.display = "none";
    controlProcesoContent.style.display = "none";
    controlCalidadContent.style.display = "none";
    controlResultadosContent.style.display = "none";
    if (controlReporteContent) controlReporteContent.style.display = "none";
    configuracionProgramaContent.style.display = "none";

    // FORZAR ocultar completamente las áreas de contenido
    materialContentArea.style.display = "none";
    informacionBasicaContentArea.style.display = "none";
    hideAllMaterialContainers();
    hideAllInformacionBasicaContainers();

    // Cerrar Control de Embarque cuando se cambie a otra sección
    if (typeof window.cerrarControlEmbarque === "function") {
      window.cerrarControlEmbarque();
    }
  }

  // Función para resetear completamente la pestaña de Información Básica
  function resetInformacionBasica() {
    // Llamar a la función global de reseteo si existe
    if (typeof window.resetInfoBasicaToDefault === "function") {
      window.resetInfoBasicaToDefault();
    } else {
    }

    // Asegurar que todos los sidebar-links funcionen
    const sidebarLinks =
      informacionBasicaContent.querySelectorAll(".sidebar-link");
    sidebarLinks.forEach((link) => {
      link.style.pointerEvents = "auto";
      link.style.cursor = "pointer";
    });
  }

  // Función para ocultar todos los contenedores de material
  function hideAllMaterialContainers() {
    if (materialInfoContainer) materialInfoContainer.style.display = "none";
    if (controlAlmacenContainer) controlAlmacenContainer.style.display = "none";
    if (controlSalidaContainer) controlSalidaContainer.style.display = "none";
    if (controlRetornoContainer) controlRetornoContainer.style.display = "none";
    if (reciboPagoContainer) reciboPagoContainer.style.display = "none";
    if (historialEntradasContainer) historialEntradasContainer.style.display = "none";
    if (historialSalidasContainer) historialSalidasContainer.style.display = "none";
    if (historialRetornosContainer) historialRetornosContainer.style.display = "none";
    if (estatusMaterialContainer) estatusMaterialContainer.style.display = "none";
    if (materialSustitutoContainer) materialSustitutoContainer.style.display = "none";
    if (consultarPepsContainer) consultarPepsContainer.style.display = "none";
    if (longtermInventoryContainer) longtermInventoryContainer.style.display = "none";
    if (registroMaterialContainer) registroMaterialContainer.style.display = "none";
    if (historialInventarioContainer) historialInventarioContainer.style.display = "none";
    if (ajusteNumeroContainer) ajusteNumeroContainer.style.display = "none";

    // Ocultar contenedor de operación de línea SMT
    const operacionLineaSMTContainer = document.getElementById(
      "operacion-linea-smt-unique-container",
    );
    if (operacionLineaSMTContainer) {
      operacionLineaSMTContainer.style.display = "none";
    }

    // Ocultar área de Control de Calidad
    const calidadContentArea = document.getElementById("calidad-content-area");
    if (calidadContentArea) calidadContentArea.style.display = "none";

    // Ocultar contenedor de Plan SMD Diario
    const planSmdDiarioContainer = document.getElementById(
      "plan-smd-diario-unique-container",
    );
    if (planSmdDiarioContainer) {
      planSmdDiarioContainer.style.display = "none";
    }

    // Ocultar contenedor de Control de producción SMT
    const controlProduccionSMTContainer = document.getElementById(
      "Control de produccion SMT-unique-container",
    );
    if (controlProduccionSMTContainer) {
      controlProduccionSMTContainer.style.display = "none";
    }

    // Ocultar contenedores específicos de Control de Producción que pueden quedar visibles
    const controlProduccionSpecificContainers = [
      "control-mask-metal-unique-container",
      "control-squeegee-unique-container",
      "control-caja-mask-metal-unique-container",
      "estandares-soldadura-unique-container",
      "registro-recibo-soldadura-unique-container",
      "control-salida-soldadura-unique-container",
      "historial-tension-mask-metal-unique-container",
    ];

    controlProduccionSpecificContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    // Ocultar contenedores específicos de Control de Proceso que pueden quedar visibles
    const controlProcesoSpecificContainers = [
      "control-proceso-info-container",
      "control-produccion-smt-container",
    ];

    controlProcesoSpecificContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        // Limpiar TODOS los estilos inline y ocultar
        container.style.cssText = "";
        container.style.display = "none";
      }
    });

    // Ocultar todos los contenedores AJAX de Control de Proceso
    const controlProcesoAjaxContainers = [
      "plan-smd-diario-unique-container",
      "operacion-linea-smt-unique-container",
      "operacion-linea-main-unique-container",
      "plan-main-assy-unique-container",
      "control-cuchillas-corte-unique-container",
      "plan-main-imd-unique-container",
      "plan-main-smt-unique-container",
      "control-impresion-identificacion-smt-unique-container",
      "control-registro-identificacion-smt-unique-container",
      "historial-operacion-proceso-unique-container",
      "bom-management-process-unique-container",
      "control-salida-lineas-unique-container",
      "bom-unique-container",
      "reporte-diario-inspeccion-smt-unique-container",
      "control-diario-inspeccion-smt-unique-container",
      "reporte-diario-inspeccion-proceso-unique-container",
      "control-unidad-empaque-modelo-unique-container",
      "packaging-register-management-unique-container",
      "search-packaging-history-unique-container",
      "shipping-register-management-unique-container",
      "search-shipping-history-unique-container",
      "almacen-embarques-entradas-unique-container",
      "almacen-embarques-salidas-unique-container",
      "almacen-embarques-retorno-unique-container",
      "almacen-embarques-movimientos-unique-container",
      "almacen-embarques-inventario-general-unique-container",
      "almacen-embarques-catalogo-unique-container",
      "registro-movimiento-identificacion-unique-container",
      "control-otras-identificaciones-unique-container",
      "control-movimiento-ns-producto-unique-container",
      "model-sn-management-unique-container",
      "control-scrap-unique-container",
    ];

    controlProcesoAjaxContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        // Limpiar TODOS los estilos inline y ocultar
        container.style.cssText = "";
        container.style.display = "none";
      }
    });

    // 🧹 LIMPIAR estilos inline de áreas de Control de Proceso
    const controlProcesoContent = document.getElementById(
      "control-proceso-content",
    );
    const controlProcesoContentArea = document.getElementById(
      "control-proceso-content-area",
    );

    if (controlProcesoContent) {
      controlProcesoContent.style.cssText = "";
      controlProcesoContent.style.display = "none";
    }

    if (controlProcesoContentArea) {
      controlProcesoContentArea.style.cssText = "";
      controlProcesoContentArea.style.display = "none";
    }

    // Ocultar todos los contenedores AJAX de Control de Resultados
    const controlResultadosAjaxContainers = [
      "historial-aoi-unique-container",
      "historial-ict-unique-container",
      "historial-cambios-parametros-ict-unique-container",
      "historial-maquina-ict-pass-fail-unique-container",
      "historial-vision-unique-container",
      "historial-vision-pass-fail-unique-container",
    ];

    controlResultadosAjaxContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    // 🧹 LIMPIAR estilos inline forzados de Control de Resultados
    const controlResultadosContent = document.getElementById(
      "control-resultados-content",
    );
    const controlResultadosContentArea = document.getElementById(
      "control-resultados-content-area",
    );

    if (controlResultadosContent) {
      // Remover estilos inline para que vuelva a usar CSS normal
      controlResultadosContent.style.cssText = "";
      controlResultadosContent.style.display = "none";
    }

    if (controlResultadosContentArea) {
      // Remover estilos inline para que vuelva a usar CSS normal
      controlResultadosContentArea.style.cssText = "";
      controlResultadosContentArea.style.display = "none";
    }

    // Limpiar estilos de contenedores específicos
    controlResultadosAjaxContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.cssText = "display: none;";
      }
    });

    // Ocultar contenedor de visor MySQL para control de modelos
    const controlModelosVisorContainer = document.getElementById(
      "control-modelos-visor-unique-container",
    );
    if (controlModelosVisorContainer) {
      controlModelosVisorContainer.style.display = "none";
    }

    // Ocultar contenedor de Control de Modelos SMT
    const controlModelosSMTContainer = document.getElementById(
      "control-modelos-smt-unique-container",
    );
    if (controlModelosSMTContainer) {
      controlModelosSMTContainer.style.display = "none";
    }

    // Ocultar wrappers de otras secciones que pueden quedar visibles
    // (mismo patrón que control-proceso-content-area y control-resultados-content-area)
    const materialContentAreaEl = document.getElementById("material-content-area");
    if (materialContentAreaEl) {
      materialContentAreaEl.style.cssText = "";
      materialContentAreaEl.style.display = "none";
    }

    const produccionContentAreaEl = document.getElementById("produccion-content-area");
    if (produccionContentAreaEl) {
      produccionContentAreaEl.style.cssText = "";
      produccionContentAreaEl.style.display = "none";
    }

    const informacionBasicaContentAreaEl = document.getElementById("informacion-basica-content-area");
    if (informacionBasicaContentAreaEl) {
      informacionBasicaContentAreaEl.style.cssText = "";
      informacionBasicaContentAreaEl.style.display = "none";
    }
  }

  function hideAllInformacionBasicaContainers() {
    const containers = [
      "info-basica-default-container",
      "admin-usuario-info-container",
      "admin-menu-info-container",
      "admin-autoridad-info-container",
      "control-codigo-info-container",
      "admin-itinerario-info-container",
      "consultar-licencias-info-container",
      "control-departamento-info-container",
      "control-proceso-info-container",
      "control-orden-proceso-info-container",
      "control-orden-proceso2-info-container",
      "control-defecto-info-container",
      "control-interfaces-info-container",
      "control-interlock-info-container",
      "control-material-info-container",
      "configuracion-msl-info-container",
      "control-cliente-info-container",
      "control-proveedor-info-container",
      "control-moneda-info-container",
      "info-empresa-info-container",
    ];

    containers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    // Ocultar también el contenedor de Control de Modelos SMT AJAX
    const controlModelosSMTContainer = document.getElementById(
      "control-modelos-smt-unique-container",
    );
    if (controlModelosSMTContainer) {
      controlModelosSMTContainer.style.display = "none";
    }
  }

  // Hacer las funciones disponibles globalmente
  window.hideAllInformacionBasicaContainers =
    hideAllInformacionBasicaContainers;
  window.hideAllMaterialContainers = hideAllMaterialContainers;

  // Funciones globales para mostrar cada contenedor de Información Básica.
  // WF_002: usar prepararPanelInformacionBasica() (definida en
  // MainTemplate.html) en vez del bloque manual de ocultar.
  function _prepInfoBasica() {
    if (typeof window.prepararPanelInformacionBasica === "function") {
      window.prepararPanelInformacionBasica();
    } else {
      hideAllInformacionBasicaContainers();
    }
  }

  window.mostrarAdminUsuarioInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById("admin-usuario-info-container");
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarAdminMenuInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById("admin-menu-info-container");
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarAdminAutoridadInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById("admin-autoridad-info-container");
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarControlCodigoInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById("control-codigo-info-container");
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarAdminItinerarioInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById(
      "admin-itinerario-info-container",
    );
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarConsultarLicenciasInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById(
      "consultar-licencias-info-container",
    );
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarControlDepartamentoInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById(
      "control-departamento-info-container",
    );
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarControlProcesoInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById("control-proceso-info-container");
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarControlOrdenProcesoInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById(
      "control-orden-proceso-info-container",
    );
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarControlOrdenProceso2Info = function () {
    _prepInfoBasica();
    const container = document.getElementById(
      "control-orden-proceso2-info-container",
    );
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarControlDefectoInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById("control-defecto-info-container");
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarControlInterfacesInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById(
      "control-interfaces-info-container",
    );
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarControlInterlockInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById(
      "control-interlock-info-container",
    );
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarConfiguracionMSLInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById(
      "configuracion-msl-info-container",
    );
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarControlClienteInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById("control-cliente-info-container");
    if (container) {
      container.style.display = "block";
    }
  };

  window.mostrarControlProveedorInfo = function () {
    _prepInfoBasica();
    const container = document.getElementById(
      "control-proveedor-info-container",
    );
    if (container) {
      container.style.display = "block";
    }
  };

  // Función para mostrar el contenido por defecto de material
  window.mostrarInfoMaterial = function () {
    hideAllMaterialContainers();
    materialContentArea.style.display = "block";
    materialInfoContainer.style.display = "block";
  };

  window.mostrarReciboPago = function () {
    hideAllMaterialContainers();
    materialContentArea.style.display = "block";
    reciboPagoContainer.style.display = "block";
  };

  // mostrarHistorialEntradas/Salidas/Retornos, mostrarHistorialMaterial,
  // mostrarInventarioActual y mostrarLongtermInventory estan definidas en
  // MainTemplate.html (WF_002 con prepararPanelSeccion('material') +
  // *-unique-container). No re-definir aqui para evitar shadowing.

  window.mostrarMaterialSustituto = function () {
    hideAllMaterialContainers();
    materialContentArea.style.display = "block";
    materialSustitutoContainer.style.display = "block";
  };

  window.mostrarConsultarPeps = function () {
    hideAllMaterialContainers();
    materialContentArea.style.display = "block";
    consultarPepsContainer.style.display = "block";
  };

  window.mostrarRegistroMaterial = function () {
    hideAllMaterialContainers();
    materialContentArea.style.display = "block";
    registroMaterialContainer.style.display = "block";
  };

  window.mostrarHistorialInventario = function () {
    hideAllMaterialContainers();
    materialContentArea.style.display = "block";
    historialInventarioContainer.style.display = "block";
  };

  window.mostrarAjusteNumero = function () {
    hideAllMaterialContainers();
    materialContentArea.style.display = "block";
    ajusteNumeroContainer.style.display = "block";
  };

  // Función global para ocultar el contenido de almacén
  window.ocultarControlAlmacen = function () {
    materialContentArea.style.display = "none";
    hideAllMaterialContainers();
  };

  // Persistencia de pestaña activa (compartida con MainTemplate.html)
  const STORAGE_KEY_NAV_SM = "mes_nav_active_v1";
  function guardarPestanaActivaSM(id) {
    try { localStorage.setItem(STORAGE_KEY_NAV_SM, id); } catch (e) {}
  }

  // OBSOLETO 2026-05-22: el sistema de 'ultimo item por seccion'
  // se eliminó porque causaba parpadeo al cambiar de pestaña navbar
  // via switchTab desde un tab de otra seccion (se mostraba primero el
  // ultimo item de esa seccion y luego el tab pedido).
  // El sistema de tabs (sidebar-tabs.js + mes_tabs_v1) ya gestiona
  // qué container activar al cambiar de seccion via switchTab/restaurarTabsDeSeccion.
  function restaurarItemSidebar() { /* no-op, mantenido por compatibilidad */ }
  window.restaurarItemSidebar = restaurarItemSidebar;
  // Limpiar localStorage huerfano del sistema viejo
  try { localStorage.removeItem("mes_sidebar_item_v1"); } catch (e) {}

  let restaurarTabsTimer = null;

  navButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      // Remover la clase 'active' de todos los botones
      navButtons.forEach((b) => b.classList.remove("active"));
      // Agregar la clase 'active' al botón clickeado
      this.classList.add("active");

      // Persistir cual pestaña dejo el usuario abierta
      guardarPestanaActivaSM(this.id);

      // Restaurar tabs de la nueva seccion (despues de que cargue el sidebar)
      const navTabId = this.id;
      if (typeof window.restaurarTabsDeSeccion === 'function') {
        if (restaurarTabsTimer) {
          clearTimeout(restaurarTabsTimer);
        }
        restaurarTabsTimer = setTimeout(() => {
          const navActivo = document.querySelector(".nav-button.active");
          if (!navActivo || navActivo.id !== navTabId) return;
          window.restaurarTabsDeSeccion(navTabId);
        }, 600);
      }

      // Ocultar todo el contenido primero
      hideAllContent();

      if (this.id === "Información Basica") {
        // Usar la función global de MainTemplate.html si está disponible
        if (typeof window.mostrarInformacionBasica === "function") {
          window.mostrarInformacionBasica();
        } else {
          // Fallback básico
          materialContainer.style.display = "block";
          informacionBasicaContent.style.display = "block";
          informacionBasicaContentArea.style.display = "block";
          hideAllInformacionBasicaContainers();
          const defaultContainer = document.getElementById(
            "info-basica-default-container",
          );
          if (defaultContainer) {
            defaultContainer.style.display = "block";
          }
        }
      } else if (this.id === "Control de material") {
        // Usar la función global de MainTemplate.html si está disponible
        if (typeof window.mostrarControlMaterial === "function") {
          window.mostrarControlMaterial();
        } else {
          // Fallback básico
          materialContainer.style.display = "block";
          controlMaterialContent.style.display = "block";
          mostrarInfoMaterial();
        }
      } else if (this.id === "Control de producción") {
        // Usar la función global de MainTemplate.html si está disponible
        if (typeof window.mostrarControlProduccion === "function") {
          window.mostrarControlProduccion();
        } else {
          // Fallback básico
          materialContainer.style.display = "block";
          controlProduccionContent.style.display = "block";
          materialContentArea.style.display = "none";
        }
      } else if (this.id === "Control de proceso") {
        materialContainer.style.display = "block";
        controlProcesoContent.style.display = "block";
        // FORZAR ocultar el área de material cuando no estés en Control de material
        materialContentArea.style.display = "none";
      } else if (this.id === "Control de calidad") {
        hideAllMaterialContainers();
        materialContainer.style.display = "block";
        controlCalidadContent.style.display = "block";
        // FORZAR ocultar el área de material cuando no estés en Control de material
        materialContentArea.style.display = "none";
      } else if (this.id === "Control de resultados") {
        materialContainer.style.display = "block";
        controlResultadosContent.style.display = "block";
        // FORZAR ocultar el área de material cuando no estés en Control de material
        materialContentArea.style.display = "none";
      } else if (this.id === "Control de reporte") {
        materialContainer.style.display = "block";
        if (controlReporteContent)
          controlReporteContent.style.display = "block";
        // FORZAR ocultar el área de material cuando no estés en Control de material
        materialContentArea.style.display = "none";
      } else if (this.id === "Configuración de programa") {
        materialContainer.style.display = "block";
        configuracionProgramaContent.style.display = "block";
        // FORZAR ocultar el área de material cuando no estés en Control de material
        materialContentArea.style.display = "none";
      } else {
        materialContainer.style.display = "none";
        // FORZAR ocultar el área de material para cualquier otro caso
        materialContentArea.style.display = "none";
      }
    });
  });

  // Por defecto oculto
  materialContainer.style.display = "none";

  // FORZAR estado inicial correcto
  materialContentArea.style.display = "none";
  hideAllMaterialContainers();

  // Restaurar pestaña activa desde localStorage (o Info Basica por defecto)
  setTimeout(() => {
    const activeButton = document.querySelector(".nav-button.active");
    if (activeButton) return; // alguien ya la activo

    const pestanaGuardada = (() => {
      try { return localStorage.getItem(STORAGE_KEY_NAV_SM); } catch (e) { return null; }
    })();
    let boton = pestanaGuardada ? document.getElementById(pestanaGuardada) : null;
    if (!boton) boton = document.getElementById("Información Basica");
    if (boton) {
      // Solo dispara el click. La restauracion de tabs ya esta en
      // el listener del nav-button (no la dispares aqui tambien o
      // habra DOS corridas en paralelo que se cancelan entre si).
      boton.click();
    }
  }, 200);

  // ============== FUNCIONES PARA CONTROL DE CALIDAD ==============

  // mostrarHistorialSMT: ahora delega directo a mostrarHistorialCambioSMT
  // (definida en MainTemplate.html con prepararPanelSeccion('calidad')).
  // Se conserva el alias porque LISTA_CONTROL_DE_CALIDAD.html lo llama por
  // ese nombre via window.parent.mostrarHistorialSMT.
  window.mostrarHistorialSMT = function () {
    if (typeof window.mostrarHistorialCambioSMT === "function") {
      window.mostrarHistorialCambioSMT();
    } else {
      console.warn("mostrarHistorialCambioSMT no esta disponible");
    }
  };

  // Función para historial de cambio de material por máquina
  window.mostrarHistorialMaterialMaquina = function () {
    hideAllContent();
    controlCalidadContent.style.display = "block";

    // Aquí puedes agregar la lógica específica para esta funcionalidad
    const appContent = document.querySelector("main.app-content");
    if (appContent) {
      appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Historial de cambio de material por máquina</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
    }
  };

  // Función para control de resultado de reparación
  window.mostrarControlReparacion = function () {
    hideAllContent();
    controlCalidadContent.style.display = "block";

    const appContent = document.querySelector("main.app-content");
    if (appContent) {
      appContent.innerHTML = `
                        <div class="container-fluid mt-4">
                            <h2>Control de resultado de reparación</h2>
                            <p>Funcionalidad en desarrollo...</p>
                        </div>
                    `;
    }
  };

  // NOTA: las funciones mostrar*ItemReparado / mostrarHistorialPegamento /
  // mostrarHistorialMask / mostrarHistorialSqueeguee / mostrarProcessInterlockHistory /
  // mostrarControlMasterSample / mostrarHistorialInspeccionMaster /
  // mostrarControlInspeccionOQC tenian aqui versiones zombie que renderizaban
  // "Funcionalidad en desarrollo..." y eran sobreescritas mas abajo en este
  // mismo archivo por las versiones reales. Eliminadas para simplificar.
  // Las versiones activas estan ~linea 3700+ y usan _mostrarModuloCalidad().

  // NOTA: mostrarControlMaterialInfo está definida en MainTemplate.html con AJAX
  // No redefinir aquí para evitar conflictos

  // Función AJAX para Control de operación de línea SMT - GLOBAL
  window.mostrarControlOperacionLineaSMT = function () {
    try {
      // IMPORTANTE: Asegurar que estamos en la sección correcta
      // Activar el botón "Control de proceso" para que scriptMain.js no interfiera
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        // Remover active de otros botones
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      // Ocultar todos los contenedores primero
      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      if (typeof window.hideAllInformacionBasicaContainers === "function") {
        window.hideAllInformacionBasicaContainers();
      }

      // Ocultar otros contenedores dentro del área de control de proceso
      const controlProcesoContainers = [
        "control-proceso-info-container",
        "control-produccion-smt-container",
        "Control de produccion SMT-unique-container",
        "control-cuchillas-corte-unique-container",
        "bom-unique-container",
      ];

      controlProcesoContainers.forEach((containerId) => {
        const container = document.getElementById(containerId);
        if (container) {
          container.style.display = "none";
        }
      });

      // Mostrar el área de control de proceso (esto es lo que scriptMain.js maneja)
      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      // Obtener el contenedor específico
      const operacionLineaContainer = document.getElementById(
        "operacion-linea-smt-unique-container",
      );
      if (!operacionLineaContainer) {
        console.error(
          "El contenedor operacion-linea-smt-unique-container no existe en el HTML",
        );
        return;
      }

      // Mostrar el contenedor específico
      operacionLineaContainer.style.display = "block";
      operacionLineaContainer.style.opacity = "1";

      // Cargar contenido dinámicamente usando la nueva ruta AJAX
      if (typeof window.cargarContenidoDinamico === "function") {
        window
          .cargarContenidoDinamico(
            "operacion-linea-smt-unique-container",
            "/control-operacion-linea-smt-ajax",
            () => {
              // Verificar que el contenedor esté visible
              const containerAfterLoad = document.getElementById(
                "operacion-linea-smt-unique-container",
              );
              if (containerAfterLoad) {
              }

              // Ejecutar inicialización específica del módulo si existe
              if (
                typeof window.inicializarControlOperacionLineaSMTAjax ===
                "function"
              ) {
                window.inicializarControlOperacionLineaSMTAjax();
              }
            },
          )
          .catch((error) => {
            console.error(
              "Error cargando Control de operación de línea SMT AJAX:",
              error,
            );

            // Mostrar mensaje de error al usuario
            const errorContainer = document.querySelector(
              "#operacion-linea-smt-unique-container",
            );
            if (errorContainer) {
              errorContainer.innerHTML = `
                                    <div class="error-message" style="padding: 20px; text-align: center; color: #dc3545; background-color: #2B2D3E; border: 1px solid #dc3545; border-radius: 4px;">
                                        <h3>Error al cargar Control de operación de línea SMT</h3>
                                        <p>No se pudo cargar el módulo. Por favor, intente nuevamente.</p>
                                        <button onclick="window.mostrarControlOperacionLineaSMT()" style="background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-top: 10px;">Reintentar</button>
                                    </div>
                                `;
            }
          });
      } else {
        console.error("Función cargarContenidoDinamico no está disponible");
      }
    } catch (error) {
      console.error("Error crítico en mostrarControlOperacionLineaSMT:", error);
      alert(
        "Error crítico al cargar Control de operación de línea SMT. Consulte la consola para más detalles.",
      );
    }
  };

  // Función AJAX: Control de operación de línea Main
  window.mostrarControlOperacionLineaMain = function () {
    try {
      // Activar sección Control de proceso
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") btn.classList.remove("active");
        });
      }
      // Ocultar todo
      if (typeof window.hideAllMaterialContainers === "function")
        window.hideAllMaterialContainers();
      if (typeof window.hideAllInformacionBasicaContainers === "function")
        window.hideAllInformacionBasicaContainers();
      // Mostrar área de Control de proceso
      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );
      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";
      // Contenedor específico
      const containerId = "operacion-linea-main-unique-container";
      const cont = document.getElementById(containerId);
      if (!cont) return console.error("Contenedor no existe:", containerId);
      cont.style.display = "block";
      cont.style.opacity = "1";
      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          containerId,
          "/control-operacion-linea-main-ajax",
          () => {
            if (
              typeof window.inicializarControlOperacionLineaMainAjax ===
              "function"
            ) {
              window.inicializarControlOperacionLineaMainAjax();
            }
          },
        );
      }
    } catch (e) {
      console.error("Error en mostrarControlOperacionLineaMain:", e);
    }
  };

  // Función AJAX: Plan Main ASSY
  window.mostrarPlanMainASSY = function () {
    try {
      // console.log(" Cargando Plan Main ASSY...");

      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") btn.classList.remove("active");
        });
      }
      if (typeof window.hideAllMaterialContainers === "function")
        window.hideAllMaterialContainers();
      if (typeof window.hideAllInformacionBasicaContainers === "function")
        window.hideAllInformacionBasicaContainers();
      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );
      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";
      const containerId = "plan-main-assy-unique-container";
      const cont = document.getElementById(containerId);
      if (!cont) return console.error(" Contenedor no existe:", containerId);
      // Mostrar contenedor SIN !important
      cont.style.display = "block";
      cont.style.opacity = "1";
      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          containerId,
          "/plan-main-assy-ajax",
          () => {
            // console.log(" Contenido de Plan Main ASSY cargado, inicializando...");

            // Esperar a que los scripts se carguen completamente
            function tryInitialize() {
              if (
                typeof window.assyInitializePlanEventListeners === "function" &&
                typeof window.assyLoadPlans === "function"
              ) {
                // console.log(" Inicializando event listeners de Plan Main ASSY");
                window.assyInitializePlanEventListeners();

                // Cargar datos iniciales
                // console.log(" Cargando planes iniciales...");
                window.assyLoadPlans();
              } else {
                // console.log("⏳ Esperando a que plan-assy-*.js se cargue completamente...");
                setTimeout(tryInitialize, 100);
              }
            }

            tryInitialize();
          },
        );
      }
    } catch (e) {
      console.error(" Error en mostrarPlanMainASSY:", e);
    }
  };

  // Función AJAX: Control de Cuchillas de Corte (ASSY)
  // Refactor WF_002 (2026-05-25): usar prepararPanelSeccion + contenedor unique
  window.mostrarControlCuchillasCorte = function () {
    if (typeof window.prepararPanelSeccion !== "function") {
      console.error("prepararPanelSeccion no disponible");
      return;
    }
    window.prepararPanelSeccion("produccion");

    const containerId = "control-cuchillas-corte-unique-container";
    const cont = document.getElementById(containerId);
    if (cont) cont.style.display = "block";

    window.cargarContenidoDinamico(containerId, "/control-cuchillas-corte-ajax", () => {
      const init = () => {
        if (typeof window.initializeControlCuchillasCorteEventListeners === "function") {
          window.initializeControlCuchillasCorteEventListeners();
        }
        if (typeof window.cuchillasCorteLoadInitialData === "function") {
          window.cuchillasCorteLoadInitialData();
        }
      };
      init();
      setTimeout(init, 120);
    });
  };

  // Función AJAX: Plan Main IMD
  window.mostrarPlanMainIMD = function () {
    try {
      // console.log(" Cargando Plan Main IMD...");

      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") btn.classList.remove("active");
        });
      }
      if (typeof window.hideAllMaterialContainers === "function")
        window.hideAllMaterialContainers();
      if (typeof window.hideAllInformacionBasicaContainers === "function")
        window.hideAllInformacionBasicaContainers();
      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );
      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";
      const containerId = "plan-main-imd-unique-container";
      const cont = document.getElementById(containerId);
      if (!cont) return console.error(" Contenedor no existe:", containerId);
      // Mostrar contenedor SIN !important
      cont.style.display = "block";
      cont.style.opacity = "1";
      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          containerId,
          "/plan-main-imd-ajax",
          () => {
            // console.log(" Contenido de Plan Main IMD cargado, inicializando...");

            // Esperar a que los scripts se carguen completamente
            function tryInitialize() {
              if (
                typeof window.initializePlanIMDEventListeners === "function" &&
                typeof window.loadPlansIMD === "function"
              ) {
                // Crear modales en el body (Nuevo Plan / Edit / Reschedule)
                // antes de cablear los listeners que los abren.
                if (typeof window.createModalsInBodyIMD === "function") {
                  window.createModalsInBodyIMD();
                }
                window.initializePlanIMDEventListeners();
                window.loadPlansIMD();
              } else {
                setTimeout(tryInitialize, 100);
              }
            }

            tryInitialize();
          },
        );
      }
    } catch (e) {
      console.error(" Error en mostrarPlanMainIMD:", e);
    }
  };

  // Funcion AJAX: Plan Main SMT
  window.mostrarPlanMainSMT = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") btn.classList.remove("active");
        });
      }
      if (typeof window.hideAllMaterialContainers === "function")
        window.hideAllMaterialContainers();
      if (typeof window.hideAllInformacionBasicaContainers === "function")
        window.hideAllInformacionBasicaContainers();
      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );
      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";
      const containerId = "plan-main-smt-unique-container";
      const cont = document.getElementById(containerId);
      if (!cont) return console.error("Contenedor no existe:", containerId);
      cont.style.display = "block";
      cont.style.opacity = "1";
      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          containerId,
          "/plan-main-smt-ajax",
          () => {
            function tryInitialize() {
              if (
                typeof window.initializePlanSMTEventListeners === "function" &&
                typeof window.loadPlansSMT === "function"
              ) {
                // Crear modales en el body (Nuevo Plan / Edit / Reschedule)
                // antes de cablear los listeners que los abren.
                if (typeof window.createModalsInBodySMT === "function") {
                  window.createModalsInBodySMT();
                }
                window.initializePlanSMTEventListeners();
                window.loadPlansSMT();
              } else {
                setTimeout(tryInitialize, 100);
              }
            }
            tryInitialize();
          },
        );
      }
    } catch (e) {
      console.error("Error en mostrarPlanMainSMT:", e);
    }
  };

  // ========================================
  // FUNCIONES AJAX PARA CONTROL DE PROCESO
  // ========================================

  // Control de impresión de identificación SMT
  window.mostrarControlImpresionIdentificacionSMT = function () {
    try {
      // Activar el botón correcto en la navegación
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      // Ocultar todos los contenedores primero
      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      // Mostrar áreas necesarias
      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      // Obtener y mostrar el contenedor específico
      const container = document.getElementById(
        "control-impresion-identificacion-smt-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      // Cargar contenido dinámicamente
      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "control-impresion-identificacion-smt-unique-container",
          "/control-impresion-identificacion-smt-ajax",
          () => {
            if (
              typeof window.inicializarControlImpresionIdentificacionSMTAjax ===
              "function"
            ) {
              window.inicializarControlImpresionIdentificacionSMTAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Control de registro de identificación SMT
  window.mostrarControlRegistroIdentificacionSMT = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "control-registro-identificacion-smt-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "control-registro-identificacion-smt-unique-container",
          "/control-registro-identificacion-smt-ajax",
          () => {
            if (
              typeof window.inicializarControlRegistroIdentificacionSMTAjax ===
              "function"
            ) {
              window.inicializarControlRegistroIdentificacionSMTAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Historial de operación de proceso
  window.mostrarHistorialOperacionProceso = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "historial-operacion-proceso-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "historial-operacion-proceso-unique-container",
          "/historial-operacion-proceso-ajax",
          () => {
            if (
              typeof window.inicializarHistorialOperacionProcesoAjax ===
              "function"
            ) {
              window.inicializarHistorialOperacionProcesoAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // BOM Management Process
  window.mostrarBomManagementProcess = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "bom-management-process-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "bom-management-process-unique-container",
          "/bom-management-process-ajax",
          () => {
            if (
              typeof window.inicializarBomManagementProcessAjax === "function"
            ) {
              window.inicializarBomManagementProcessAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Reporte diario de inspección SMT
  window.mostrarReporteDiarioInspeccionSMT = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "reporte-diario-inspeccion-smt-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "reporte-diario-inspeccion-smt-unique-container",
          "/reporte-diario-inspeccion-smt-ajax",
          () => {
            if (
              typeof window.inicializarReporteDiarioInspeccionSMTAjax ===
              "function"
            ) {
              window.inicializarReporteDiarioInspeccionSMTAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Control diario de inspección SMT
  window.mostrarControlDiarioInspeccionSMT = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "control-diario-inspeccion-smt-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "control-diario-inspeccion-smt-unique-container",
          "/control-diario-inspeccion-smt-ajax",
          () => {
            if (
              typeof window.inicializarControlDiarioInspeccionSMTAjax ===
              "function"
            ) {
              window.inicializarControlDiarioInspeccionSMTAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Reporte diario de inspección de proceso
  window.mostrarReporteDiarioInspeccionProceso = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "reporte-diario-inspeccion-proceso-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "reporte-diario-inspeccion-proceso-unique-container",
          "/reporte-diario-inspeccion-proceso-ajax",
          () => {
            if (
              typeof window.inicializarReporteDiarioInspeccionProcesoAjax ===
              "function"
            ) {
              window.inicializarReporteDiarioInspeccionProcesoAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Control de unidad de empaque por modelo
  window.mostrarControlUnidadEmpaqueModelo = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "control-unidad-empaque-modelo-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "control-unidad-empaque-modelo-unique-container",
          "/control-unidad-empaque-modelo-ajax",
          () => {
            if (
              typeof window.inicializarControlUnidadEmpaqueModeloAjax ===
              "function"
            ) {
              window.inicializarControlUnidadEmpaqueModeloAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Packaging Register Management
  window.mostrarPackagingRegisterManagement = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "packaging-register-management-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "packaging-register-management-unique-container",
          "/packaging-register-management-ajax",
          () => {
            if (
              typeof window.inicializarPackagingRegisterManagementAjax ===
              "function"
            ) {
              window.inicializarPackagingRegisterManagementAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Search Packaging History
  window.mostrarSearchPackagingHistory = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "search-packaging-history-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "search-packaging-history-unique-container",
          "/search-packaging-history-ajax",
          () => {
            if (
              typeof window.inicializarSearchPackagingHistoryAjax === "function"
            ) {
              window.inicializarSearchPackagingHistoryAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  function prepararModuloControlProceso() {
    const controlProcesoButton = document.getElementById("Control de proceso");
    if (controlProcesoButton) {
      controlProcesoButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de proceso") {
          btn.classList.remove("active");
        }
      });
    }

    if (typeof window.prepararPanelSeccion === "function") {
      window.prepararPanelSeccion("proceso");
      return;
    }

    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    const materialContainer = document.getElementById("material-container");
    const controlProcesoContent = document.getElementById(
      "control-proceso-content",
    );
    const controlProcesoContentArea = document.getElementById(
      "control-proceso-content-area",
    );

    if (materialContainer) materialContainer.style.display = "block";
    if (controlProcesoContent) controlProcesoContent.style.display = "block";
    if (controlProcesoContentArea)
      controlProcesoContentArea.style.display = "block";
  }

  // Shipping Register Management
  window.mostrarShippingRegisterManagement = function () {
    try {
      prepararModuloControlProceso();

      const container = document.getElementById(
        "shipping-register-management-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "shipping-register-management-unique-container",
          "/shipping-register-management-ajax",
          () => {
            if (
              typeof window.inicializarShippingRegisterManagementAjax ===
              "function"
            ) {
              window.inicializarShippingRegisterManagementAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Search Shipping History
  window.mostrarSearchShippingHistory = function () {
    try {
      prepararModuloControlProceso();

      const container = document.getElementById(
        "search-shipping-history-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "search-shipping-history-unique-container",
          "/search-shipping-history-ajax",
          () => {
            if (
              typeof window.inicializarSearchShippingHistoryAjax === "function"
            ) {
              window.inicializarSearchShippingHistoryAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  function mostrarModuloAlmacenEmbarques(
    containerId,
    templatePath,
    initFunctionName,
  ) {
    try {
      prepararModuloControlProceso();

      const container = document.getElementById(containerId);
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          containerId,
          templatePath,
          () => {
            if (typeof window[initFunctionName] === "function") {
              window[initFunctionName]();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Almacén de Embarques - Entradas
  window.mostrarAlmacenEmbarquesEntradas = function () {
    mostrarModuloAlmacenEmbarques(
      "almacen-embarques-entradas-unique-container",
      "/almacen-embarques-entradas-ajax",
      "inicializarAlmacenEmbarquesEntradasAjax",
    );
  };

  // Almacén de Embarques - Salidas
  window.mostrarAlmacenEmbarquesSalidas = function () {
    mostrarModuloAlmacenEmbarques(
      "almacen-embarques-salidas-unique-container",
      "/almacen-embarques-salidas-ajax",
      "inicializarAlmacenEmbarquesSalidasAjax",
    );
  };

  // Almacén de Embarques - Retorno
  window.mostrarAlmacenEmbarquesRetorno = function () {
    mostrarModuloAlmacenEmbarques(
      "almacen-embarques-retorno-unique-container",
      "/almacen-embarques-retorno-ajax?v=20260513b",
      "inicializarAlmacenEmbarquesRetornoAjax",
    );
  };

  // Almacén de Embarques - Modificar movimientos
  window.mostrarAlmacenEmbarquesMovimientos = function () {
    mostrarModuloAlmacenEmbarques(
      "almacen-embarques-movimientos-unique-container",
      "/almacen-embarques-movimientos-ajax?v=20260513b",
      "inicializarAlmacenEmbarquesMovimientosAjax",
    );
  };

  // Almacén de Embarques - Inventario general
  window.mostrarAlmacenEmbarquesInventarioGeneral = function () {
    mostrarModuloAlmacenEmbarques(
      "almacen-embarques-inventario-general-unique-container",
      "/almacen-embarques-inventario-general-ajax",
      "inicializarAlmacenEmbarquesInventarioGeneralAjax",
    );
  };

  // Almacén de Embarques - Catálogo
  window.mostrarAlmacenEmbarquesCatalogo = function () {
    mostrarModuloAlmacenEmbarques(
      "almacen-embarques-catalogo-unique-container",
      "/almacen-embarques-catalogo-ajax?v=20260513b",
      "inicializarAlmacenEmbarquesCatalogoAjax",
    );
  };

  // Control de salida de lineas
  window.mostrarControlSalidaLineas = function () {
    mostrarModuloAlmacenEmbarques(
      "control-salida-lineas-unique-container",
      "/control-salida-lineas-ajax?v=20260513b",
      "inicializarControlSalidaLineasAjax",
    );
  };

  // Registro de movimiento de identificación
  window.mostrarRegistroMovimientoIdentificacion = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "registro-movimiento-identificacion-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "registro-movimiento-identificacion-unique-container",
          "/registro-movimiento-identificacion-ajax",
          () => {
            if (
              typeof window.inicializarRegistroMovimientoIdentificacionAjax ===
              "function"
            ) {
              window.inicializarRegistroMovimientoIdentificacionAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Control de otras identificaciones
  window.mostrarControlOtrasIdentificaciones = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "control-otras-identificaciones-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "control-otras-identificaciones-unique-container",
          "/control-otras-identificaciones-ajax",
          () => {
            if (
              typeof window.inicializarControlOtrasIdentificacionesAjax ===
              "function"
            ) {
              window.inicializarControlOtrasIdentificacionesAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Control de movimiento NS producto
  window.mostrarControlMovimientoNSProducto = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "control-movimiento-ns-producto-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "control-movimiento-ns-producto-unique-container",
          "/control-movimiento-ns-producto-ajax",
          () => {
            if (
              typeof window.inicializarControlMovimientoNSProductoAjax ===
              "function"
            ) {
              window.inicializarControlMovimientoNSProductoAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Model SN Management
  window.mostrarModelSNManagement = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "model-sn-management-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "model-sn-management-unique-container",
          "/model-sn-management-ajax",
          () => {
            if (typeof window.inicializarModelSNManagementAjax === "function") {
              window.inicializarModelSNManagementAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // Control Scrap
  window.mostrarControlScrap = function () {
    try {
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      const container = document.getElementById(
        "control-scrap-unique-container",
      );
      if (!container) {
        console.error("Contenedor no encontrado");
        return;
      }

      container.style.display = "block";
      container.style.opacity = "1";

      if (typeof window.cargarContenidoDinamico === "function") {
        window.cargarContenidoDinamico(
          "control-scrap-unique-container",
          "/control-scrap-ajax",
          () => {
            if (typeof window.inicializarControlScrapAjax === "function") {
              window.inicializarControlScrapAjax();
            }
          },
        );
      }
    } catch (error) {
      console.error("Error crítico:", error);
    }
  };

  // ========================================
  // FUNCIÓN PARA CONTROL DE PRODUCCIÓN SMT
  // ========================================

  // Control de producción SMT - SIGUIENDO EL PATRÓN EXITOSO
  window.mostrarControldeproduccionSMT = function () {
    try {
      // FORZAR ocultado de TODAS las secciones primero
      const informacionBasicaElSMT = document.getElementById(
        "informacion-basica-content",
      );
      const controlMaterialElSMT = document.getElementById(
        "control-material-content",
      );
      const controlProduccionElSMT = document.getElementById(
        "control-produccion-content",
      );
      const controlProcesoElSMT = document.getElementById(
        "control-proceso-content",
      );
      const controlCalidadElSMT = document.getElementById(
        "control-calidad-content",
      );
      const controlResultadosElSMT = document.getElementById(
        "control-resultados-content",
      );
      const configuracionProgramaElSMT = document.getElementById(
        "configuracion-programa-content",
      );
      const materialContentElSMT = document.getElementById(
        "material-content-area",
      );
      const informacionBasicaContentElSMT = document.getElementById(
        "informacion-basica-content-area",
      );

      // Ocultar todas las secciones principales
      if (informacionBasicaElSMT) informacionBasicaElSMT.style.display = "none";
      if (controlMaterialElSMT) controlMaterialElSMT.style.display = "none";
      if (controlProduccionElSMT) controlProduccionElSMT.style.display = "none";
      if (controlProcesoElSMT) controlProcesoElSMT.style.display = "none";
      if (controlCalidadElSMT) controlCalidadElSMT.style.display = "none";
      if (controlResultadosElSMT) controlResultadosElSMT.style.display = "none";
      if (configuracionProgramaElSMT)
        configuracionProgramaElSMT.style.display = "none";
      if (materialContentElSMT) materialContentElSMT.style.display = "none";
      if (informacionBasicaContentElSMT)
        informacionBasicaContentElSMT.style.display = "none";

      // IMPORTANTE: Asegurar que estamos en la sección correcta
      // Activar el botón "Control de proceso" para que scriptMain.js no interfiera
      const controlProcesoButton =
        document.getElementById("Control de proceso");
      if (controlProcesoButton) {
        controlProcesoButton.classList.add("active");
        // Remover active de otros botones
        document.querySelectorAll(".nav-button").forEach((btn) => {
          if (btn.id !== "Control de proceso") {
            btn.classList.remove("active");
          }
        });
      }

      // Ocultar todos los contenedores primero
      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      if (typeof window.hideAllInformacionBasicaContainers === "function") {
        window.hideAllInformacionBasicaContainers();
      }

      // Ocultar otros contenedores dentro del área de control de proceso
      const controlProcesoContainers = [
        "control-proceso-info-container",
        "control-produccion-smt-container",
        "operacion-linea-smt-unique-container",
        "control-cuchillas-corte-unique-container",
      ];

      controlProcesoContainers.forEach((containerId) => {
        const container = document.getElementById(containerId);
        if (container) {
          container.style.display = "none";
        }
      });

      // Mostrar el área de control de proceso (esto es lo que scriptMain.js maneja)
      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) materialContainer.style.display = "block";
      if (controlProcesoContent) controlProcesoContent.style.display = "block";
      if (controlProcesoContentArea)
        controlProcesoContentArea.style.display = "block";

      // Obtener el contenedor específico
      const controlProduccionSMTContainer = document.getElementById(
        "Control de produccion SMT-unique-container",
      );
      if (!controlProduccionSMTContainer) {
        console.error(
          "El contenedor Control de produccion SMT-unique-container no existe en el HTML",
        );
        return;
      }

      // Mostrar el contenedor específico
      controlProduccionSMTContainer.style.display = "block";
      controlProduccionSMTContainer.style.opacity = "1";

      // Cargar contenido dinámicamente usando la ruta completa
      if (typeof window.cargarContenidoDinamico === "function") {
        window
          .cargarContenidoDinamico(
            "Control de produccion SMT-unique-container",
            "/control_proceso/control_produccion_smt",
            () => {
              // Verificar que el contenedor esté visible
              const containerAfterLoad = document.getElementById(
                "Control de produccion SMT-unique-container",
              );
              if (containerAfterLoad) {
                // Verificar que el contenedor esté realmente visible

                // Verificar que los contenedores padre también estén visibles
                const materialContainerAfter =
                  document.getElementById("material-container");
                const controlProcesoContentAfter = document.getElementById(
                  "control-proceso-content",
                );
                const controlProcesoContentAreaAfter = document.getElementById(
                  "control-proceso-content-area",
                );
              }

              // Ejecutar inicialización específica del módulo si existe
              if (
                typeof window.inicializarControlProduccionSMTModule ===
                "function"
              ) {
                window.inicializarControlProduccionSMTModule();
              }
            },
          )
          .catch((error) => {
            console.error("Error cargando Control de producción SMT:", error);

            // Mostrar mensaje de error al usuario
            const errorContainer = document.querySelector(
              "#Control de produccion SMT-unique-container",
            );
            if (errorContainer) {
              errorContainer.innerHTML = `
                                    <div class="error-message" style="padding: 20px; text-align: center; color: #dc3545; background-color: #2B2D3E; border: 1px solid #dc3545; border-radius: 4px;">
                                        <h3>Error al cargar Control de producción SMT</h3>
                                        <p>No se pudo cargar el módulo. Por favor, intente nuevamente.</p>
                                        <button onclick="window.mostrarControldeproduccionSMT()" style="background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-top: 10px;">Reintentar</button>
                                    </div>
                                `;
            }
          });
      } else {
        console.error("Función cargarContenidoDinamico no está disponible");
      }
    } catch (error) {
      console.error("Error crítico en mostrarControldeproduccionSMT:", error);
      alert(
        "Error crítico al cargar Control de producción SMT. Consulte la consola para más detalles.",
      );
    }
  };

  // mostrarCrearPlanMicom eliminado (modulo Crear plan micom removido el 2026-05-25)

  // ========================================
  // FUNCIÓN PARA CONTROL BOM
  // ========================================

  // Control BOM - SIGUIENDO EL PATRÓN EXITOSO
  window.mostrarControlBOM = function () {
    try {
      // PASO 1: Ocultar TODOS los contenedores de todas las secciones
      // Ocultar secciones principales
      const allSections = [
        "informacion-basica-content",
        "control-material-content",
        "control-produccion-content",
        "control-proceso-content",
        "control-calidad-content",
        "control-resultados-content",
        "configuracion-programa-content",
      ];

      allSections.forEach((sectionId) => {
        const section = document.getElementById(sectionId);
        if (section) section.style.display = "none";
      });

      // Ocultar áreas de contenido
      const allAreas = [
        "material-content-area",
        "informacion-basica-content-area",
        "control-produccion-content-area",
        "control-proceso-content-area",
      ];

      allAreas.forEach((areaId) => {
        const area = document.getElementById(areaId);
        if (area) area.style.display = "none";
      });

      // Ocultar TODOS los contenedores AJAX específicos
      if (typeof window.hideAllMaterialContainers === "function") {
        window.hideAllMaterialContainers();
      }

      if (typeof window.hideAllInformacionBasicaContainers === "function") {
        window.hideAllInformacionBasicaContainers();
      }

      // Ocultar contenedores de Control de Proceso manualmente
      const allControlProcesoContainers = [
        "control-proceso-info-container",
        "control-produccion-smt-container",
        "operacion-linea-smt-unique-container",
        "control-cuchillas-corte-unique-container",
        "Control de produccion SMT-unique-container",
        "line-material-status-unique-container",
      ];

      allControlProcesoContainers.forEach((containerId) => {
        const container = document.getElementById(containerId);
        if (container) container.style.display = "none";
      });

      // PASO 2: Mostrar el contenedor padre de Control de Proceso
      const materialContainer = document.getElementById("material-container");
      const controlProcesoContent = document.getElementById(
        "control-proceso-content",
      );
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );

      if (materialContainer) {
        materialContainer.style.display = "block";
      }

      if (controlProcesoContent) {
        controlProcesoContent.style.display = "block";
        controlProcesoContent.style.width = "100%";
        controlProcesoContent.style.maxWidth = "none";
      }

      if (controlProcesoContentArea) {
        controlProcesoContentArea.style.display = "block";
        controlProcesoContentArea.style.width = "100%";
        controlProcesoContentArea.style.maxWidth = "none";
        controlProcesoContentArea.style.margin = "0";
        controlProcesoContentArea.style.padding = "0";
      }

      // PASO 3: Obtener y mostrar el contenedor específico de BOM
      const bomContainer = document.getElementById("bom-unique-container");
      if (!bomContainer) {
        console.error(
          " El contenedor bom-unique-container no existe en el HTML",
        );
        return;
      }

      // Aplicar estilos de ancho completo al contenedor BOM
      bomContainer.style.display = "block";
      bomContainer.style.width = "100%";
      bomContainer.style.maxWidth = "none";
      bomContainer.style.margin = "0";
      bomContainer.style.padding = "0";

      // PASO 4: Cargar contenido dinámicamente (esto también ejecuta cleanup)
      if (typeof window.cargarContenidoDinamico === "function") {
        window
          .cargarContenidoDinamico(
            "bom-unique-container",
            "/control-bom-ajax",
            () => {
              // Ejecutar inicialización específica del módulo si existe
              if (
                typeof window.initializeControlBOMEventListeners === "function"
              ) {
                window.initializeControlBOMEventListeners();
              }
            },
          )
          .catch((error) => {
            console.error(" Error cargando Control BOM:", error);
            const errorContainer = document.getElementById(
              "bom-unique-container",
            );
            if (errorContainer) {
              errorContainer.innerHTML = `
                                    <div class="error-message" style="padding: 20px; text-align: center; color: #dc3545; background-color: #2B2D3E; border: 1px solid #dc3545; border-radius: 4px;">
                                        <h3>Error al cargar Control BOM</h3>
                                        <p>No se pudo cargar el módulo. Por favor, intente nuevamente.</p>
                                        <button onclick="window.mostrarControlBOM()" style="background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-top: 10px;">Reintentar</button>
                                    </div>
                                `;
            }
          });
      } else {
        console.error(" Función cargarContenidoDinamico no está disponible");
      }
    } catch (error) {
      console.error(" Error crítico en mostrarControlBOM:", error);
      alert(
        "Error crítico al cargar Control BOM. Consulte la consola para más detalles.",
      );
    }
  };
});

// ========================================
// FUNCIÓN PARA LINE MATERIAL STATUS_ES
// ========================================

window.mostrarLineMaterialStatus = function () {
  try {
    // IMPORTANTE: Asegurar que estamos en la sección correcta
    // Activar el botón "Control de produccion" para que scriptMain.js no interfiera
    const controlProduccionButton = document.getElementById(
      "Control de produccion",
    );
    if (controlProduccionButton) {
      controlProduccionButton.classList.add("active");
      // Remover active de otros botones
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de produccion") {
          btn.classList.remove("active");
        }
      });
    }

    // Ocultar todos los contenedores primero
    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    // Ocultar otros contenedores dentro del área de produccion
    const produccionContainers = [
      "produccion-info-container",
      "crear-plan-produccion-unique-container",
      "plan-smt-unique-container",
      "control-embarque-unique-container",
    ];

    produccionContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    // Mostrar el área de produccion (esto es lo que scriptMain.js maneja)
    const materialContainer = document.getElementById("material-container");
    const produccionContent = document.getElementById("produccion-content");
    const produccionContentArea = document.getElementById(
      "produccion-content-area",
    );

    if (materialContainer) {
      materialContainer.style.display = "block";
    }
    if (produccionContent) {
      produccionContent.style.display = "block";
    }
    if (produccionContentArea) {
      produccionContentArea.style.display = "block";
    }

    // Obtener el contenedor específico
    const lineMaterialStatusContainer = document.getElementById(
      "produccion-info-container",
    );
    if (!lineMaterialStatusContainer) {
      console.error(
        "El contenedor produccion-info-container no existe en el HTML",
      );
      return;
    }

    // Mostrar el contenedor específico
    lineMaterialStatusContainer.style.display = "block";
    lineMaterialStatusContainer.style.opacity = "1";

    // Cargar contenido dinámicamente usando la ruta AJAX
    if (typeof window.cargarContenidoDinamico === "function") {
      window
        .cargarContenidoDinamico(
          "produccion-info-container",
          "/line-material-status-ajax",
          () => {
            // Verificar que el contenedor esté visible
            const containerAfterLoad = document.getElementById(
              "produccion-info-container",
            );
            if (containerAfterLoad) {
              // Verificar que el contenedor esté realmente visible

              // Verificar que los contenedores padre también estén visibles
              const materialContainerAfter =
                document.getElementById("material-container");
              const produccionContentAfter =
                document.getElementById("produccion-content");
              const produccionContentAreaAfter = document.getElementById(
                "produccion-content-area",
              );
            }

            // Ejecutar inicialización específica del módulo si existe
            if (
              typeof window.inicializarLineMaterialStatusModule === "function"
            ) {
              window.inicializarLineMaterialStatusModule();
            }
          },
        )
        .catch((error) => {
          console.error("Error cargando Line Material Status_es:", error);
        });
    } else {
      console.error("La función cargarContenidoDinamico no está disponible");
    }
  } catch (error) {
    console.error("Error crítico en mostrarLineMaterialStatus:", error);
  }
};

// ========================================
// FUNCIONES AJAX PARA MÓDULOS DE CONTROL DE PRODUCCIÓN
// ========================================

// Refactor 2026-05-26 (WF_002): las 3 funciones mostrar* de Control de SMT
// (Metal Mask / Squeegee / Caja Metal Mask) ahora usan prepararPanelSeccion +
// container *-unique-container. El init JS de cada modulo lo expone su
// propio script (MetalMask.js -> window.initMetalMask,
// Caja-metalmask.js -> window.initStorageBox,
// control-squeegee.js -> window.initControlSqueegee).
window.mostrarControlMaskMetal = function () {
  if (typeof window.prepararPanelSeccion !== "function") {
    console.error("prepararPanelSeccion no disponible");
    return;
  }
  window.prepararPanelSeccion("produccion");
  const containerId = "control-mask-metal-unique-container";
  const cont = document.getElementById(containerId);
  if (cont) cont.style.display = "block";
  window.cargarContenidoDinamico(containerId, "/control-mask-metal-ajax", () => {
    const init = () => {
      if (typeof window.initMetalMask === "function") window.initMetalMask();
    };
    init();
    setTimeout(init, 120);
  });
};

window.mostrarControlSqueegee = function () {
  if (typeof window.prepararPanelSeccion !== "function") {
    console.error("prepararPanelSeccion no disponible");
    return;
  }
  window.prepararPanelSeccion("produccion");
  const containerId = "control-squeegee-unique-container";
  const cont = document.getElementById(containerId);
  if (cont) cont.style.display = "block";
  window.cargarContenidoDinamico(containerId, "/control-squeegee-ajax", () => {
    const init = () => {
      if (typeof window.initControlSqueegee === "function") window.initControlSqueegee();
    };
    init();
    setTimeout(init, 120);
  });
};

window.mostrarControlCajaMaskMetal = function () {
  if (typeof window.prepararPanelSeccion !== "function") {
    console.error("prepararPanelSeccion no disponible");
    return;
  }
  window.prepararPanelSeccion("produccion");
  const containerId = "control-caja-mask-metal-unique-container";
  const cont = document.getElementById(containerId);
  if (cont) cont.style.display = "block";
  window.cargarContenidoDinamico(containerId, "/control-caja-mask-metal-ajax", () => {
    const init = () => {
      if (typeof window.initStorageBox === "function") window.initStorageBox();
    };
    init();
    setTimeout(init, 120);
  });
};

window.mostrarEstandaresSoldadura = function () {
  try {
    // Activar el botón "Control de produccion"
    const controlProduccionButton = document.getElementById(
      "Control de produccion",
    );
    if (controlProduccionButton) {
      controlProduccionButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de produccion") {
          btn.classList.remove("active");
        }
      });
    }

    // Ocultar todos los contenedores primero
    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    // Ocultar otros contenedores dentro del área de produccion
    const produccionContainers = [
      "produccion-info-container",
      "crear-plan-produccion-unique-container",
      "plan-smt-unique-container",
      "control-embarque-unique-container",
    ];

    produccionContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    // Mostrar el área de produccion
    const materialContainer = document.getElementById("material-container");
    const produccionContent = document.getElementById("produccion-content");
    const produccionContentArea = document.getElementById(
      "produccion-content-area",
    );

    if (materialContainer) materialContainer.style.display = "block";
    if (produccionContent) produccionContent.style.display = "block";
    if (produccionContentArea) produccionContentArea.style.display = "block";

    // Obtener el contenedor específico
    const estandaresSoldaduraContainer = document.getElementById(
      "produccion-info-container",
    );
    if (!estandaresSoldaduraContainer) {
      console.error(
        "El contenedor produccion-info-container no existe en el HTML",
      );
      return;
    }

    // Mostrar el contenedor específico
    estandaresSoldaduraContainer.style.display = "block";
    estandaresSoldaduraContainer.style.opacity = "1";

    // Cargar contenido dinámicamente usando la ruta AJAX
    if (typeof window.cargarContenidoDinamico === "function") {
      window
        .cargarContenidoDinamico(
          "produccion-info-container",
          "/estandares-soldadura-ajax",
          () => {
            // Ejecutar inicialización específica del módulo si existe
            if (
              typeof window.inicializarEstandaresSoldaduraModule === "function"
            ) {
              window.inicializarEstandaresSoldaduraModule();
            }
          },
        )
        .catch((error) => {
          console.error(
            "Error cargando Estandares sobre control de soldadura:",
            error,
          );
        });
    } else {
      console.error("La función cargarContenidoDinamico no está disponible");
    }
  } catch (error) {
    console.error("Error crítico en mostrarEstandaresSoldadura:", error);
  }
};

window.mostrarRegistroReciboSoldadura = function () {
  try {
    // Activar el botón "Control de produccion"
    const controlProduccionButton = document.getElementById(
      "Control de produccion",
    );
    if (controlProduccionButton) {
      controlProduccionButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de produccion") {
          btn.classList.remove("active");
        }
      });
    }

    // Ocultar todos los contenedores primero
    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    // Ocultar otros contenedores dentro del área de produccion
    const produccionContainers = [
      "produccion-info-container",
      "crear-plan-produccion-unique-container",
      "plan-smt-unique-container",
      "control-embarque-unique-container",
    ];

    produccionContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    // Mostrar el área de produccion
    const materialContainer = document.getElementById("material-container");
    const produccionContent = document.getElementById("produccion-content");
    const produccionContentArea = document.getElementById(
      "produccion-content-area",
    );

    if (materialContainer) materialContainer.style.display = "block";
    if (produccionContent) produccionContent.style.display = "block";
    if (produccionContentArea) produccionContentArea.style.display = "block";

    // Obtener el contenedor específico
    const registroReciboSoldaduraContainer = document.getElementById(
      "produccion-info-container",
    );
    if (!registroReciboSoldaduraContainer) {
      console.error(
        "El contenedor produccion-info-container no existe en el HTML",
      );
      return;
    }

    // Mostrar el contenedor específico
    registroReciboSoldaduraContainer.style.display = "block";
    registroReciboSoldaduraContainer.style.opacity = "1";

    // Cargar contenido dinámicamente usando la ruta AJAX
    if (typeof window.cargarContenidoDinamico === "function") {
      window
        .cargarContenidoDinamico(
          "produccion-info-container",
          "/registro-recibo-soldadura-ajax",
          () => {
            // Ejecutar inicialización específica del módulo si existe
            if (
              typeof window.inicializarRegistroReciboSoldaduraModule ===
              "function"
            ) {
              window.inicializarRegistroReciboSoldaduraModule();
            }
          },
        )
        .catch((error) => {
          console.error(
            "Error cargando Registro de recibo de soldadura:",
            error,
          );
        });
    } else {
      console.error("La función cargarContenidoDinamico no está disponible");
    }
  } catch (error) {
    console.error("Error crítico en mostrarRegistroReciboSoldadura:", error);
  }
};

window.mostrarControlSalidaSoldadura = function () {
  try {
    // Activar el botón "Control de produccion"
    const controlProduccionButton = document.getElementById(
      "Control de produccion",
    );
    if (controlProduccionButton) {
      controlProduccionButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de produccion") {
          btn.classList.remove("active");
        }
      });
    }

    // Ocultar todos los contenedores primero
    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    // Ocultar otros contenedores dentro del área de produccion
    const produccionContainers = [
      "produccion-info-container",
      "crear-plan-produccion-unique-container",
      "plan-smt-unique-container",
      "control-embarque-unique-container",
    ];

    produccionContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    // Mostrar el área de produccion
    const materialContainer = document.getElementById("material-container");
    const produccionContent = document.getElementById("produccion-content");
    const produccionContentArea = document.getElementById(
      "produccion-content-area",
    );

    if (materialContainer) materialContainer.style.display = "block";
    if (produccionContent) produccionContent.style.display = "block";
    if (produccionContentArea) produccionContentArea.style.display = "block";

    // Obtener el contenedor específico
    const controlSalidaSoldaduraContainer = document.getElementById(
      "produccion-info-container",
    );
    if (!controlSalidaSoldaduraContainer) {
      console.error(
        "El contenedor produccion-info-container no existe en el HTML",
      );
      return;
    }

    // Mostrar el contenedor específico
    controlSalidaSoldaduraContainer.style.display = "block";
    controlSalidaSoldaduraContainer.style.opacity = "1";

    // Cargar contenido dinámicamente usando la ruta AJAX
    if (typeof window.cargarContenidoDinamico === "function") {
      window
        .cargarContenidoDinamico(
          "produccion-info-container",
          "/control-salida-soldadura-ajax",
          () => {
            // Ejecutar inicialización específica del módulo si existe
            if (
              typeof window.inicializarControlSalidaSoldaduraModule ===
              "function"
            ) {
              window.inicializarControlSalidaSoldaduraModule();
            }
          },
        )
        .catch((error) => {
          console.error(
            "Error cargando Control de salida de soldadura:",
            error,
          );
        });
    } else {
      console.error("La función cargarContenidoDinamico no está disponible");
    }
  } catch (error) {
    console.error("Error crítico en mostrarControlSalidaSoldadura:", error);
  }
};

window.mostrarHistorialTensionMaskMetal = function () {
  try {
    // Activar el botón "Control de produccion"
    const controlProduccionButton = document.getElementById(
      "Control de produccion",
    );
    if (controlProduccionButton) {
      controlProduccionButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de produccion") {
          btn.classList.remove("active");
        }
      });
    }

    // Ocultar todos los contenedores primero
    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    // Ocultar otros contenedores dentro del área de produccion
    const produccionContainers = [
      "produccion-info-container",
      "crear-plan-produccion-unique-container",
      "plan-smt-unique-container",
      "control-embarque-unique-container",
    ];

    produccionContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    // Mostrar el área de produccion
    const materialContainer = document.getElementById("material-container");
    const produccionContent = document.getElementById("produccion-content");
    const produccionContentArea = document.getElementById(
      "produccion-content-area",
    );

    if (materialContainer) materialContainer.style.display = "block";
    if (produccionContent) produccionContent.style.display = "block";
    if (produccionContentArea) produccionContentArea.style.display = "block";

    // Obtener el contenedor específico
    const historialTensionMaskMetalContainer = document.getElementById(
      "produccion-info-container",
    );
    if (!historialTensionMaskMetalContainer) {
      console.error(
        "El contenedor produccion-info-container no existe en el HTML",
      );
      return;
    }

    // Mostrar el contenedor específico
    historialTensionMaskMetalContainer.style.display = "block";
    historialTensionMaskMetalContainer.style.opacity = "1";

    // Cargar contenido dinámicamente usando la ruta AJAX
    if (typeof window.cargarContenidoDinamico === "function") {
      window
        .cargarContenidoDinamico(
          "produccion-info-container",
          "/historial-tension-mask-metal-ajax",
          () => {
            // Ejecutar inicialización específica del módulo si existe
            if (
              typeof window.inicializarHistorialTensionMaskMetalModule ===
              "function"
            ) {
              window.inicializarHistorialTensionMaskMetalModule();
            }
          },
        )
        .catch((error) => {
          console.error(
            "Error cargando Historial de tension de mask de metal:",
            error,
          );
        });
    } else {
      console.error("La función cargarContenidoDinamico no está disponible");
    }
  } catch (error) {
    console.error("Error crítico en mostrarHistorialTensionMaskMetal:", error);
  }
};

// ============================================================================
// FUNCIONES PARA CONTROL DE CALIDAD
// ============================================================================

// ============================================================
// Funciones mostrar* de Control de calidad (WF_002 compliant).
// Antes: cada funcion tenia ~50 lineas con boilerplate manual de ocultar
// secciones y mostrar areas. Ahora todas usan _mostrarModuloCalidad(),
// que invoca prepararPanelSeccion('calidad') + muestra el container
// -unique-container correspondiente y dispara cargarContenidoDinamico.
// El sistema de tabs (sidebar-tabs.js) abre pestaña por modulo porque
// el containerId termina en -unique-container.
// ============================================================
function _mostrarModuloCalidad(containerId, ruta, initCb) {
  try {
    if (typeof window.prepararPanelSeccion === "function") {
      window.prepararPanelSeccion("calidad");
    }
    const container = document.getElementById(containerId);
    if (container) container.style.display = "block";

    if (typeof window.cargarContenidoDinamico !== "function") {
      console.error("cargarContenidoDinamico no esta disponible");
      return;
    }
    const result = window.cargarContenidoDinamico(containerId, ruta, initCb || (() => {}));
    if (result && typeof result.catch === "function") {
      result.catch((error) => {
        console.error(`Error cargando ${ruta}:`, error);
      });
    }
  } catch (error) {
    console.error(`Error critico cargando ${ruta}:`, error);
  }
}

window.mostrarControlResultadoReparacion = function () {
  _mostrarModuloCalidad(
    "control-resultado-reparacion-unique-container",
    "/control-resultado-reparacion-ajax",
  );
};

window.mostrarControlItemReparado = function () {
  _mostrarModuloCalidad(
    "control-item-reparado-unique-container",
    "/control-item-reparado-ajax",
  );
};

window.mostrarHistorialCambioMaterialMaquina = function () {
  _mostrarModuloCalidad(
    "historial-cambio-material-maquina-unique-container",
    "/historial-cambio-material-maquina-ajax",
  );
};

window.mostrarHistorialUsoPegamentoSoldadura = function () {
  _mostrarModuloCalidad(
    "historial-uso-pegamento-soldadura-unique-container",
    "/historial-uso-pegamento-soldadura-ajax",
  );
};

window.mostrarHistorialUsoMaskMetal = function () {
  _mostrarModuloCalidad(
    "historial-uso-mask-metal-unique-container",
    "/historial-uso-mask-metal-ajax",
  );
};

window.mostrarHistorialUsoSqueegee = function () {
  _mostrarModuloCalidad(
    "historial-uso-squeegee-unique-container",
    "/historial-uso-squeegee-ajax",
  );
};

window.mostrarProcessInterlockHistory = function () {
  _mostrarModuloCalidad(
    "process-interlock-history-unique-container",
    "/process-interlock-history-ajax",
  );
};

window.mostrarControlMasterSampleSMT = function () {
  _mostrarModuloCalidad(
    "control-master-sample-smt-unique-container",
    "/control-master-sample-smt-ajax",
  );
};

window.mostrarHistorialInspeccionMasterSampleSMT = function () {
  _mostrarModuloCalidad(
    "historial-inspeccion-master-sample-smt-unique-container",
    "/historial-inspeccion-master-sample-smt-ajax",
  );
};

window.mostrarControlInspeccionOQC = function () {
  _mostrarModuloCalidad(
    "control-inspeccion-oqc-unique-container",
    "/control-inspeccion-oqc-ajax",
  );
};

window.mostrarHistorialLiberacionLQC = function () {
  _mostrarModuloCalidad(
    "historial-liberacion-lqc-unique-container",
    "/historial-liberacion-lqc-ajax",
    () => {
      if (typeof window.inicializarHistorialLiberacionLQC === "function") {
        window.inicializarHistorialLiberacionLQC();
      }
    },
  );
};

// Función AJAX para Historial AOI - GLOBAL
window.mostrarHistorialAOI = function () {
  try {
    // Activar el botón correcto en la navegación
    const controlResultadosButton = document.getElementById(
      "Control de resultados",
    );
    if (controlResultadosButton) {
      controlResultadosButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de resultados") {
          btn.classList.remove("active");
        }
      });
    }

    // Ocultar todos los contenedores primero
    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    // Limpiar módulos previos de Control de Resultados si existen
    if (typeof window.limpiarHistorialAOI === "function") {
      window.limpiarHistorialAOI();
    }

    // Ocultar otros contenedores dentro del área de control de resultados
    const controlResultadosContainers = ["control-resultados-info-container"];

    controlResultadosContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    // Mostrar TODAS las áreas necesarias
    const materialContainer = document.getElementById("material-container");
    const controlResultadosContent = document.getElementById(
      "control-resultados-content",
    );
    const controlResultadosContentArea = document.getElementById(
      "control-resultados-content-area",
    );

    if (materialContainer) materialContainer.style.display = "block";
    if (controlResultadosContent)
      controlResultadosContent.style.display = "block";
    if (controlResultadosContentArea)
      controlResultadosContentArea.style.display = "block";

    // Obtener y mostrar el contenedor específico
    const historialAOIContainer = document.getElementById(
      "historial-aoi-unique-container",
    );
    if (!historialAOIContainer) {
      console.error("El contenedor no existe en el HTML");
      return;
    }

    historialAOIContainer.style.display = "block";
    historialAOIContainer.style.opacity = "1";

    // Cargar contenido dinámicamente
    if (typeof window.cargarContenidoDinamico === "function") {
      window.cargarContenidoDinamico(
        "historial-aoi-unique-container",
        "/historial-aoi-ajax",
        () => {
          // Ejecutar inicialización del módulo si existe
          if (typeof window.inicializarHistorialAOI === "function") {
            window.inicializarHistorialAOI();
          }
        },
      );
    }
  } catch (error) {
    console.error("Error crítico:", error);
  }
};

// Función AJAX para Historial ICT - GLOBAL
window.mostrarHistorialICT = function () {
  try {
    const controlResultadosButton = document.getElementById(
      "Control de resultados",
    );
    if (controlResultadosButton) {
      controlResultadosButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de resultados") {
          btn.classList.remove("active");
        }
      });
    }

    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    if (typeof window.limpiarHistorialICT === "function") {
      window.limpiarHistorialICT();
    }
    if (typeof window.limpiarHistorialICTPassFail === "function") {
      window.limpiarHistorialICTPassFail();
    }

    const controlResultadosContainers = [
      "control-resultados-info-container",
      "historial-aoi-unique-container",
      "historial-maquina-ict-pass-fail-unique-container",
      "historial-cambios-parametros-ict-unique-container",
      "historial-vision-unique-container",
      "historial-vision-pass-fail-unique-container",
      "inventario-imd-terminado-unique-container",
    ];

    controlResultadosContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    const materialContainer = document.getElementById("material-container");
    const controlResultadosContent = document.getElementById(
      "control-resultados-content",
    );
    const controlResultadosContentArea = document.getElementById(
      "control-resultados-content-area",
    );

    // 🎨 Aplicar estilos específicos SOLO para Historial ICT
    if (materialContainer) {
      materialContainer.style.display = "block";
    }

    if (controlResultadosContent) {
      controlResultadosContent.style.display = "block";
      // Solo aplicar width en este contenedor específico
      controlResultadosContent.style.width = "100%";
      controlResultadosContent.style.maxWidth = "none";
    }

    if (controlResultadosContentArea) {
      controlResultadosContentArea.style.display = "block";
      // Aplicar estilos de ancho completo solo para este módulo
      controlResultadosContentArea.style.width = "100%";
      controlResultadosContentArea.style.maxWidth = "none";
      controlResultadosContentArea.style.margin = "0";
      controlResultadosContentArea.style.paddingRight = "0";
    }

    const historialICTContainer = document.getElementById(
      "historial-ict-unique-container",
    );
    if (!historialICTContainer) {
      console.error("El contenedor Historial ICT no existe en el HTML");
      return;
    }

    // 🎨 Estilos para el contenedor ICT
    historialICTContainer.style.display = "block";
    historialICTContainer.style.opacity = "1";
    historialICTContainer.style.width = "100%";
    historialICTContainer.style.maxWidth = "none";
    historialICTContainer.style.margin = "0";
    historialICTContainer.style.visibility = "visible";

    if (typeof window.cargarContenidoDinamico === "function") {
      window.cargarContenidoDinamico(
        "historial-ict-unique-container",
        "/historial-ict-ajax",
        () => {
          const intentarInicializarICT = () => {
            if (typeof window.initializeIctEventListeners === "function") {
              window.initializeIctEventListeners();
            }
            if (typeof window.loadIctData === "function") {
              window.loadIctData();
            }
          };

          intentarInicializarICT();
          // Reintentar por si los scripts externos todavía se están cargando
          setTimeout(intentarInicializarICT, 200);
        },
      );
    }
  } catch (error) {
    console.error("Error crítico en mostrarHistorialICT:", error);
  }
};

// ============================================================
// Funcion AJAX para Historial Vision - GLOBAL
// ============================================================
window.mostrarHistorialVision = function () {
  try {
    const controlResultadosButton = document.getElementById(
      "Control de resultados",
    );
    if (controlResultadosButton) {
      controlResultadosButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de resultados") {
          btn.classList.remove("active");
        }
      });
    }

    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    if (typeof window.limpiarHistorialVision === "function") {
      window.limpiarHistorialVision();
    }

    const controlResultadosContainers = [
      "control-resultados-info-container",
      "historial-aoi-unique-container",
      "historial-ict-unique-container",
      "historial-cambios-parametros-ict-unique-container",
      "historial-maquina-ict-pass-fail-unique-container",
      "historial-vision-unique-container",
      "historial-vision-pass-fail-unique-container",
      "inventario-imd-terminado-unique-container",
    ];

    controlResultadosContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    const materialContainer = document.getElementById("material-container");
    const controlResultadosContent = document.getElementById(
      "control-resultados-content",
    );
    const controlResultadosContentArea = document.getElementById(
      "control-resultados-content-area",
    );

    if (materialContainer) {
      materialContainer.style.display = "block";
    }

    if (controlResultadosContent) {
      controlResultadosContent.style.display = "block";
      controlResultadosContent.style.width = "100%";
      controlResultadosContent.style.maxWidth = "none";
    }

    if (controlResultadosContentArea) {
      controlResultadosContentArea.style.display = "block";
      controlResultadosContentArea.style.width = "100%";
      controlResultadosContentArea.style.maxWidth = "none";
      controlResultadosContentArea.style.margin = "0";
      controlResultadosContentArea.style.paddingRight = "0";
    }

    const historialVisionContainer = document.getElementById(
      "historial-vision-unique-container",
    );
    if (!historialVisionContainer) {
      console.error("El contenedor Historial Vision no existe en el HTML");
      return;
    }

    historialVisionContainer.style.display = "block";
    historialVisionContainer.style.opacity = "1";
    historialVisionContainer.style.width = "100%";
    historialVisionContainer.style.maxWidth = "none";
    historialVisionContainer.style.margin = "0";
    historialVisionContainer.style.visibility = "visible";

    if (typeof window.cargarContenidoDinamico === "function") {
      window.cargarContenidoDinamico(
        "historial-vision-unique-container",
        "/historial-vision-ajax",
        () => {
          const intentarInicializarVision = () => {
            if (
              typeof window.initializeHistorialVisionEventListeners ===
              "function"
            ) {
              window.initializeHistorialVisionEventListeners();
            }
            if (typeof window.loadHistorialVisionData === "function") {
              window.loadHistorialVisionData();
            }
          };

          intentarInicializarVision();
          setTimeout(intentarInicializarVision, 200);
        },
      );
    }
  } catch (error) {
    console.error("Error crítico en mostrarHistorialVision:", error);
  }
};

// ============================================================
// Función AJAX para Historial de Maquinas ICT % Pass/Fail
// ============================================================
window.mostrarHistorialMaquinaICTPassFail = function () {
  try {
    const controlResultadosButton = document.getElementById(
      "Control de resultados",
    );
    if (controlResultadosButton) {
      controlResultadosButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de resultados") {
          btn.classList.remove("active");
        }
      });
    }

    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    if (typeof window.limpiarHistorialICT === "function") {
      window.limpiarHistorialICT();
    }
    if (typeof window.limpiarHistorialICTPassFail === "function") {
      window.limpiarHistorialICTPassFail();
    }

    // Ocultar otros contenedores de Control de Resultados
    const controlResultadosContainers = [
      "control-resultados-info-container",
      "historial-aoi-unique-container",
      "historial-ict-unique-container",
      "historial-cambios-parametros-ict-unique-container",
      "historial-maquina-ict-pass-fail-unique-container",
      "historial-vision-unique-container",
      "historial-vision-pass-fail-unique-container",
      "inventario-imd-terminado-unique-container",
    ];

    controlResultadosContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    const materialContainer = document.getElementById("material-container");
    const controlResultadosContent = document.getElementById(
      "control-resultados-content",
    );
    const controlResultadosContentArea = document.getElementById(
      "control-resultados-content-area",
    );

    if (materialContainer) {
      materialContainer.style.display = "block";
    }

    if (controlResultadosContent) {
      controlResultadosContent.style.display = "block";
      controlResultadosContent.style.width = "100%";
      controlResultadosContent.style.maxWidth = "none";
    }

    if (controlResultadosContentArea) {
      controlResultadosContentArea.style.display = "block";
      controlResultadosContentArea.style.width = "100%";
      controlResultadosContentArea.style.maxWidth = "none";
      controlResultadosContentArea.style.margin = "0";
      controlResultadosContentArea.style.paddingRight = "0";
    }

    const historialMaquinaICTPassFailContainer = document.getElementById(
      "historial-maquina-ict-pass-fail-unique-container",
    );
    if (!historialMaquinaICTPassFailContainer) {
      console.error("El contenedor Historial Maquina ICT % Pass/Fail no existe en el HTML");
      return;
    }

    // 🎨 Estilos para el contenedor Historial Maquina ICT % Pass/Fail
    historialMaquinaICTPassFailContainer.style.display = "block";
    historialMaquinaICTPassFailContainer.style.opacity = "1";
    historialMaquinaICTPassFailContainer.style.width = "100%";
    historialMaquinaICTPassFailContainer.style.maxWidth = "none";
    historialMaquinaICTPassFailContainer.style.margin = "0";
    historialMaquinaICTPassFailContainer.style.visibility = "visible";

    if (typeof window.cargarContenidoDinamico === "function") {
      window.cargarContenidoDinamico(
        "historial-maquina-ict-pass-fail-unique-container",
        "/historial-maquina-ict-pass-fail",
        () => {
          // Ejecutar inicialización del módulo si existe
          const intentarInicializarIctPassFail = () => {
            if (
              typeof window.initializeHistorialIctPassFailEventListeners ===
              "function"
            ) {
              window.initializeHistorialIctPassFailEventListeners();
            } else if (typeof window.initializeIctPassFailEventListeners === "function") {
              window.initializeIctPassFailEventListeners();
            }

            if (typeof window.loadHistorialIctPassFailData === "function") {
              window.loadHistorialIctPassFailData();
            } else if (typeof window.loadIctPassFailData === "function") {
              window.loadIctPassFailData();
            }
          };

          intentarInicializarIctPassFail();
          setTimeout(intentarInicializarIctPassFail, 200);
        },
      );
    }
  } catch (error) {
    console.error("Error crítico en mostrarHistorialMaquinaICTPassFail:", error);
  }
};

// ============================================================
// Funcion AJAX para Historial de Maquina Vision % Pass/Fail
// ============================================================
window.mostrarHistorialVisionPassFail = function () {
  try {
    const controlResultadosButton = document.getElementById(
      "Control de resultados",
    );
    if (controlResultadosButton) {
      controlResultadosButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de resultados") {
          btn.classList.remove("active");
        }
      });
    }

    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    if (typeof window.limpiarHistorialVisionPassFail === "function") {
      window.limpiarHistorialVisionPassFail();
    }

    const controlResultadosContainers = [
      "control-resultados-info-container",
      "historial-aoi-unique-container",
      "historial-ict-unique-container",
      "historial-cambios-parametros-ict-unique-container",
      "historial-maquina-ict-pass-fail-unique-container",
      "historial-vision-unique-container",
      "historial-vision-pass-fail-unique-container",
      "inventario-imd-terminado-unique-container",
    ];

    controlResultadosContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    const materialContainer = document.getElementById("material-container");
    const controlResultadosContent = document.getElementById(
      "control-resultados-content",
    );
    const controlResultadosContentArea = document.getElementById(
      "control-resultados-content-area",
    );

    if (materialContainer) {
      materialContainer.style.display = "block";
    }

    if (controlResultadosContent) {
      controlResultadosContent.style.display = "block";
      controlResultadosContent.style.width = "100%";
      controlResultadosContent.style.maxWidth = "none";
    }

    if (controlResultadosContentArea) {
      controlResultadosContentArea.style.display = "block";
      controlResultadosContentArea.style.width = "100%";
      controlResultadosContentArea.style.maxWidth = "none";
      controlResultadosContentArea.style.margin = "0";
      controlResultadosContentArea.style.paddingRight = "0";
    }

    const historialVisionPassFailContainer = document.getElementById(
      "historial-vision-pass-fail-unique-container",
    );
    if (!historialVisionPassFailContainer) {
      console.error(
        "El contenedor Historial Vision % Pass/Fail no existe en el HTML",
      );
      return;
    }

    historialVisionPassFailContainer.style.display = "block";
    historialVisionPassFailContainer.style.opacity = "1";
    historialVisionPassFailContainer.style.width = "100%";
    historialVisionPassFailContainer.style.maxWidth = "none";
    historialVisionPassFailContainer.style.margin = "0";
    historialVisionPassFailContainer.style.visibility = "visible";

    if (typeof window.cargarContenidoDinamico === "function") {
      window.cargarContenidoDinamico(
        "historial-vision-pass-fail-unique-container",
        "/historial-vision-pass-fail-ajax",
        () => {
          const intentarInicializarVisionPassFail = () => {
            if (
              typeof window.initializeHistorialVisionPassFailEventListeners ===
              "function"
            ) {
              window.initializeHistorialVisionPassFailEventListeners();
            }
            if (typeof window.loadHistorialVisionPassFailData === "function") {
              window.loadHistorialVisionPassFailData();
            }
          };

          intentarInicializarVisionPassFail();
          setTimeout(intentarInicializarVisionPassFail, 200);
        },
      );
    }
  } catch (error) {
    console.error("Error crítico en mostrarHistorialVisionPassFail:", error);
  }
};

// ============================================================
// Función AJAX para Historial de Cambios de Parámetros ICT
// ============================================================
window.mostrarHistorialCambiosParametrosICT = function () {
  try {
    const controlResultadosButton = document.getElementById(
      "Control de resultados",
    );
    if (controlResultadosButton) {
      controlResultadosButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de resultados") {
          btn.classList.remove("active");
        }
      });
    }

    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    // Ocultar otros contenedores de Control de Resultados
    const controlResultadosContainers = [
      "control-resultados-info-container",
      "historial-aoi-unique-container",
      "historial-ict-unique-container",
      "historial-vision-unique-container",
      "historial-vision-pass-fail-unique-container",
    ];

    controlResultadosContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    const materialContainer = document.getElementById("material-container");
    const controlResultadosContent = document.getElementById(
      "control-resultados-content",
    );
    const controlResultadosContentArea = document.getElementById(
      "control-resultados-content-area",
    );

    if (materialContainer) {
      materialContainer.style.display = "block";
    }

    if (controlResultadosContent) {
      controlResultadosContent.style.display = "block";
      controlResultadosContent.style.width = "100%";
      controlResultadosContent.style.maxWidth = "none";
    }

    if (controlResultadosContentArea) {
      controlResultadosContentArea.style.display = "block";
      controlResultadosContentArea.style.width = "100%";
      controlResultadosContentArea.style.maxWidth = "none";
      controlResultadosContentArea.style.margin = "0";
      controlResultadosContentArea.style.paddingRight = "0";
    }

    const cambiosICTContainer = document.getElementById(
      "historial-cambios-parametros-ict-unique-container",
    );
    if (!cambiosICTContainer) {
      console.error(
        "El contenedor Historial Cambios Parámetros ICT no existe en el HTML",
      );
      return;
    }

    cambiosICTContainer.style.display = "block";
    cambiosICTContainer.style.opacity = "1";
    cambiosICTContainer.style.width = "100%";
    cambiosICTContainer.style.maxWidth = "none";
    cambiosICTContainer.style.margin = "0";
    cambiosICTContainer.style.visibility = "visible";

    if (typeof window.cargarContenidoDinamico === "function") {
      window.cargarContenidoDinamico(
        "historial-cambios-parametros-ict-unique-container",
        "/historial-cambios-parametros-ict-ajax",
        () => {
          const intentarInicializar = () => {
            if (typeof window.initializeCambiosParametrosICT === "function") {
              window.initializeCambiosParametrosICT();
            }
            if (typeof window.loadCambiosParametrosICT === "function") {
              window.loadCambiosParametrosICT();
            }
          };
          intentarInicializar();
          setTimeout(intentarInicializar, 200);
        },
      );
    }
  } catch (error) {
    console.error(
      "Error crítico en mostrarHistorialCambiosParametrosICT:",
      error,
    );
  }
};

// Función AJAX para Plan SMD Diario - GLOBAL
window.mostrarPlanSmdDiario = function () {
  try {
    // Activar el botón correcto en la navegación
    const controlProcesoButton = document.getElementById("Control de proceso");
    if (controlProcesoButton) {
      controlProcesoButton.classList.add("active");
      document.querySelectorAll(".nav-button").forEach((btn) => {
        if (btn.id !== "Control de proceso") {
          btn.classList.remove("active");
        }
      });
    }

    // Ocultar todos los contenedores primero
    if (typeof window.hideAllMaterialContainers === "function") {
      window.hideAllMaterialContainers();
    }

    // Ocultar otros contenedores dentro del área de control de proceso
    const controlProcesoContainers = [
      "operacion-linea-smt-unique-container",
      "Control de produccion SMT-unique-container",
      "control-cuchillas-corte-unique-container",
      "bom-unique-container",
      "bom-management-process-unique-container",
      "control-salida-lineas-unique-container",
    ];

    controlProcesoContainers.forEach((containerId) => {
      const container = document.getElementById(containerId);
      if (container) {
        container.style.display = "none";
      }
    });

    // Mostrar TODAS las áreas necesarias
    const materialContainer = document.getElementById("material-container");
    const controlProcesoContent = document.getElementById(
      "control-proceso-content",
    );

    if (materialContainer) materialContainer.style.display = "block";
    if (controlProcesoContent) controlProcesoContent.style.display = "block";

    // Crear o mostrar el contenedor específico del plan SMD diario
    let planSmdDiarioContainer = document.getElementById(
      "plan-smd-diario-unique-container",
    );
    if (!planSmdDiarioContainer) {
      // Crear el contenedor si no existe
      planSmdDiarioContainer = document.createElement("div");
      planSmdDiarioContainer.id = "plan-smd-diario-unique-container";
      planSmdDiarioContainer.className = "unique-container";
      planSmdDiarioContainer.style.display = "none";

      // Agregar al área de control de proceso
      const controlProcesoContentArea = document.getElementById(
        "control-proceso-content-area",
      );
      if (controlProcesoContentArea) {
        controlProcesoContentArea.appendChild(planSmdDiarioContainer);
      }
    }

    planSmdDiarioContainer.style.display = "block";
    planSmdDiarioContainer.style.opacity = "1";

    // Cargar contenido dinámicamente
    if (typeof window.cargarContenidoDinamico === "function") {
      window.cargarContenidoDinamico(
        "plan-smd-diario-unique-container",
        "/plan-smd-diario",
        () => {},
      );
    }
  } catch (error) {
    console.error("Error crítico en mostrarPlanSmdDiario:", error);
  }
};

// Función AJAX para Control de modelos - VISOR MYSQL - GLOBAL
// WF_002: usa prepararPanelInformacionBasica() en vez del bloque manual.
// Antes eran ~98 lineas con lista hardcoded de 22 IDs para ocultar y
// activacion manual del nav button. El helper hace todo eso.
window.mostrarControlModelosVisor = function () {
  try {
    if (typeof window.prepararPanelInformacionBasica === "function") {
      window.prepararPanelInformacionBasica();
    }
    const container = document.getElementById(
      "control-modelos-visor-unique-container",
    );
    if (container) container.style.display = "block";

    if (typeof window.cargarContenidoDinamico !== "function") {
      console.error("cargarContenidoDinamico no esta disponible");
      return;
    }
    window.cargarContenidoDinamico(
      "control-modelos-visor-unique-container",
      "/control-modelos-visor-ajax",
      () => {
        if (typeof window.inicializarControlModelosVisorAjax === "function") {
          window.inicializarControlModelosVisorAjax();
        }
      },
    );
  } catch (error) {
    console.error("Error critico en mostrarControlModelosVisor:", error);
  }
};

// Función AJAX para Control de Modelos SMT - GLOBAL
// WF_002: usa prepararPanelInformacionBasica() en vez de bloque manual.
// El container 'control-modelos-smt-unique-container' es hijo de
// informacion-basica-content-area; al prepararse el panel, todos los
// otros containers de la seccion quedan ocultos y este se muestra.
window.mostrarControlModelosSMT = function () {
  try {
    if (typeof window.prepararPanelInformacionBasica === "function") {
      window.prepararPanelInformacionBasica();
    }
    const container = document.getElementById(
      "control-modelos-smt-unique-container",
    );
    if (container) container.style.display = "block";

    if (typeof window.cargarContenidoDinamico !== "function") {
      console.error("cargarContenidoDinamico no esta disponible");
      return;
    }
    window.cargarContenidoDinamico(
      "control-modelos-smt-unique-container",
      "/control-modelos-smt-ajax",
      () => {
        if (typeof window.inicializarControlModelosSMTAjax === "function") {
          window.inicializarControlModelosSMTAjax();
        }
      },
    );
  } catch (error) {
    console.error("Error critico en mostrarControlModelosSMT:", error);
  }
};
