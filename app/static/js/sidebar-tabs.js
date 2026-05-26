/* ============================================
   SISTEMA DE TABS DEL PANEL DERECHO
   ============================================
   Intercepta cargarContenidoDinamico para que en
   vez de reemplazar el contenido del area, abra
   un tab nuevo (o cambie al existente). Cada
   *-content-area tiene su propia barra de tabs.

   Persiste en localStorage por seccion navbar:
     mes_tabs_v1 = {
        "Control de proceso": {
           tabs: [{ id, label, area, container, path }, ...],
           active: id
        },
        ...
     }
*/

(function () {
    'use strict';

    const STORAGE_KEY = 'mes_tabs_v1';

    // Mapeo de cada container -> a que pestaña navbar pertenece
    // (para guardar y restaurar tabs por seccion). Se rellena al
    // interceptar cada cargarContenidoDinamico.
    const containerToNavTab = new Map(); // containerId -> navTabName

    // ====================================================
    // Persistencia
    // ====================================================
    function readState() {
        try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
        catch (e) { return {}; }
    }
    function writeState(state) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
        catch (e) {}
    }
    function getNavTabActiva() {
        const btn = document.querySelector('.nav-button.active');
        return btn ? btn.id : null;
    }

    function containerTieneContenido(container) {
        return !!container &&
            container.innerHTML.trim().length > 100 &&
            !container.innerHTML.includes('loading-indicator');
    }

    function buscarTabPersistido(navTabId, containerId) {
        const seccion = readState()[navTabId];
        if (!seccion || !Array.isArray(seccion.tabs)) return null;
        return seccion.tabs.find(tab => tab.container === containerId) || null;
    }

    // ====================================================
    // Localizar el *-content-area dueño de un container
    // ====================================================
    function findAreaFor(containerId) {
        const cont = document.getElementById(containerId);
        if (!cont) return null;
        return cont.closest('[id$="-content-area"]') || cont.parentElement;
    }

    // ====================================================
    // Barra de tabs GLOBAL (una sola para toda la app).
    // Se inserta fija debajo del navbar (via CSS position:fixed).
    // ====================================================
    function ensureGlobalTabsBar() {
        let bar = document.getElementById('global-tabs-bar');
        if (bar) return bar;
        bar = document.createElement('div');
        bar.id = 'global-tabs-bar';
        document.body.appendChild(bar);
        return bar;
    }

    // Mantener compat: la API vieja sigue existiendo pero devuelve
    // la barra global. Asi todo el codigo que usaba bar local sigue
    // funcionando sin cambiar.
    function ensureTabsBar(/* area ignorado */) {
        return ensureGlobalTabsBar();
    }

    // ====================================================
    // Crear o actualizar el chip de un tab
    // ====================================================
    function renderTabChip(bar, tabInfo) {
        let chip = bar.querySelector(`[data-tab-container="${CSS.escape(tabInfo.container)}"]`);
        if (!chip) {
            chip = document.createElement('div');
            chip.className = 'section-tab';
            chip.setAttribute('data-tab-container', tabInfo.container);
            chip.innerHTML = `
                <span class="section-tab-title"></span>
                <button type="button" class="section-tab-close" title="Cerrar">×</button>
            `;
            chip.addEventListener('click', (e) => {
                if (e.target.closest('.section-tab-close')) return;
                switchTab(tabInfo.container);
            });
            chip.querySelector('.section-tab-close').addEventListener('click', (e) => {
                e.stopPropagation();
                closeTab(tabInfo.container);
            });
            bar.appendChild(chip);
        }
        chip.querySelector('.section-tab-title').textContent = tabInfo.label;
        // Guardar el navTab al que pertenece, para que switchTab pueda
        // saltar de pestaña navbar automaticamente si es necesario.
        if (tabInfo.navTab) {
            chip.setAttribute('data-tab-navtab', tabInfo.navTab);
        }
        // Tooltip nativo con el texto completo + indicador de seccion
        const tooltip = tabInfo.navTab
            ? `${tabInfo.label}  [${tabInfo.navTab}]`
            : tabInfo.label;
        chip.setAttribute('title', tooltip);
        return chip;
    }

    // ====================================================
    // Marcar tab activo (UI + ocultar contenidos hermanos)
    // ====================================================
    function markActive(area, containerActivo) {
        if (!area) return;
        // Tabs visuales: ahora viven en la barra GLOBAL.
        const bar = document.getElementById('global-tabs-bar');
        if (bar) {
            bar.querySelectorAll('.section-tab').forEach(chip => {
                const isActive = chip.getAttribute('data-tab-container') === containerActivo;
                chip.classList.toggle('active', isActive);
            });
        }
        // IDs de "placeholders default" que NUNCA son tabs y nunca se
        // tocan aqui (se gestionan via CSS con :has).
        const PLACEHOLDERS = new Set([
            'info-basica-default-container',
            'material-info-container',
            'produccion-info-container',
            'control-proceso-info-container',
            'control-resultados-info-container'
        ]);
        // Containers: solo el activo visible. Cualquier otro hijo del
        // area que sea un container con contenido -> ocultar.
        area.querySelectorAll(':scope > [id]').forEach(cont => {
            if (cont.classList.contains('section-tabs-bar')) return;
            if (PLACEHOLDERS.has(cont.id)) return;
            // Solo nos interesan containers (-unique-container / -info-container)
            const esContainer = cont.id.endsWith('-unique-container') || cont.id.endsWith('-info-container');
            if (!esContainer) return;

            if (cont.id === containerActivo) {
                cont.style.display = 'block';
                // Algunos modulos usan clase '.visible' con !important
                // para forzar display:block; respetarla al activar.
                cont.classList.add('visible');
            } else if (cont.innerHTML.trim()) {
                cont.style.display = 'none';
                // Quitar clase '.visible' que algunos modulos
                // (ej. control-material-info-container) usan con
                // display:block !important y bloquea el ocultado.
                cont.classList.remove('visible');
            }
        });
    }

    // ====================================================
    // API: cambiar al tab del container dado
    // ====================================================
    function switchTab(containerId) {
        const navTabDestino = containerToNavTab.get(containerId);
        const navTabActual = getNavTabActiva();

        // Cambio cross-section
        if (navTabDestino && navTabDestino !== navTabActual) {
            const btnNav = document.getElementById(navTabDestino);
            const contDestino = document.getElementById(containerId);
            const yaCargado = containerTieneContenido(contDestino);
            const areaDestino = contDestino ? findAreaFor(containerId) : null;
            const sidebarDestino = document.getElementById(SECCIONES_SIDEBARS_MAP[navTabDestino]);
            const sidebarYaCacheado = sidebarDestino && sidebarDestino.dataset.sidebarCargado === '1';

            // FAST PATH: si el container destino YA esta cargado Y el
            // area/sidebar destino ya estan montados, hacer cambio
            // cosmetico directo sin disparar btnNav.click() (que llamaria
            // hideAllContent, prepararPanelSeccion, etc.).
            if (yaCargado && areaDestino && sidebarYaCacheado && btnNav) {
                fastSwitchCrossSection(containerId, navTabDestino, btnNav, areaDestino);
                return;
            }

            // SLOW PATH: primera vez en esta seccion, necesita montaje completo
            if (btnNav) {
                window.__pendingSwitchToContainer = containerId;
                const PLACEHOLDERS = [
                    'info-basica-default-container',
                    'material-info-container',
                    'produccion-info-container',
                    'control-proceso-info-container',
                    'control-resultados-info-container'
                ];
                PLACEHOLDERS.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.style.display = 'none';
                });
                if (yaCargado) contDestino.style.display = 'block';
                btnNav.click();
                return;
            }
        }

        const area = findAreaFor(containerId);
        if (!area) return;
        markActive(area, containerId);

        // Red de seguridad: algunos modulos (ej. embarques) calculan
        // anchos de tabla a partir de clientWidth. Si se restauraron tras
        // un F5 mientras estaban ocultos, midieron 0 y quedaron mal hasta
        // que algo dispare reflow. Forzar 'resize' tras el switch los
        // hace recalcular sin acoplar sidebar-tabs a cada modulo.
        requestAnimationFrame(() => {
            try { window.dispatchEvent(new Event('resize')); } catch (e) {}
        });

        const navTab = containerToNavTab.get(containerId) || getNavTabActiva();
        if (navTab) {
            const state = readState();
            if (!state[navTab]) state[navTab] = { tabs: [], active: null };
            state[navTab].active = containerId;
            writeState(state);

            // Los chips globales se pintan desde localStorage antes de
            // que todos los tabs hayan recargado su HTML. Si el usuario
            // activa uno vacio en la seccion ya visible, cargarlo aqui.
            cargarTabPersistidoSiHaceFalta(navTab, containerId);
        }
    }

    // Mapa local: nombre de seccion -> id del sidebar (espejo del
    // SECCIONES_SIDEBARS de MainTemplate.html). Necesario para
    // el fast-path porque no podemos importarlo.
    const SECCIONES_SIDEBARS_MAP = {
        'Información Basica': 'informacion-basica-content',
        'Control de material': 'control-material-content',
        'Control de producción': 'control-produccion-content',
        'Control de proceso': 'control-proceso-content',
        'Control de calidad': 'control-calidad-content',
        'Control de resultados': 'control-resultados-content',
        'Control de reporte': 'control-reporte-content',
        'Configuración de programa': 'configuracion-programa-content'
    };

    // IDs de los content-areas por seccion (espejo de SECCIONES_AREAS)
    const SECCIONES_AREAS_MAP = {
        'Información Basica': 'informacion-basica-content-area',
        'Control de material': 'material-content-area',
        'Control de producción': 'produccion-content-area',
        'Control de proceso': 'control-proceso-content-area',
        'Control de calidad': 'calidad-content-area',
        'Control de resultados': 'control-resultados-content-area'
    };

    // Cambio rapido entre tabs de secciones distintas SIN disparar
    // el handler navbar completo. Solo cambia visibilidad y marca
    // la pestaña navbar como activa visualmente.
    function fastSwitchCrossSection(containerId, navTabDestino, btnNav, areaDestino) {
        window.__pendingSwitchToContainer = null;

        // 1. Actualizar visualmente la pestaña navbar
        document.querySelectorAll('.nav-button').forEach(b => b.classList.remove('active'));
        btnNav.classList.add('active');

        // 2. Ocultar todos los content-areas y sidebars excepto los destino
        Object.entries(SECCIONES_AREAS_MAP).forEach(([nav, areaId]) => {
            const el = document.getElementById(areaId);
            if (!el) return;
            if (nav === navTabDestino) {
                el.classList.remove('mes-area-hidden');
                el.style.display = 'block';
                el.style.width = '100%';
            } else {
                el.style.cssText = '';
                el.style.display = 'none';
                el.classList.add('mes-area-hidden');
            }
        });
        Object.entries(SECCIONES_SIDEBARS_MAP).forEach(([nav, sbId]) => {
            const el = document.getElementById(sbId);
            if (!el) return;
            if (nav === navTabDestino) {
                el.style.display = 'block';
            } else {
                el.style.display = 'none';
            }
        });

        // 3. Asegurar que material-container este visible
        const matCont = document.getElementById('material-container');
        if (matCont) matCont.style.display = 'block';

        // 4. Activar el tab pedido (oculta los demas de su seccion)
        areaDestino.classList.remove('mes-area-hidden');
        areaDestino.style.display = 'block';
        areaDestino.style.width = '100%';
        markActive(areaDestino, containerId);

        // 5. Persistir pestaña navbar activa
        try { localStorage.setItem('mes_nav_active_v1', navTabDestino); } catch (e) {}

        // 6. Persistir tab activo en su seccion
        const state = readState();
        if (!state[navTabDestino]) state[navTabDestino] = { tabs: [], active: null };
        state[navTabDestino].active = containerId;
        writeState(state);
    }

    const cargasTabsPersistidos = new Set();

    async function esperarCargaDeContainer(containerId) {
        let intentos = 0;
        while (intentos < 50) {
            const container = document.getElementById(containerId);
            if (!container || !container.innerHTML.includes('loading-indicator')) return;
            await new Promise(resolve => setTimeout(resolve, 100));
            intentos++;
        }
    }

    async function cargarTabPersistidoSiHaceFalta(navTabId, containerId) {
        const container = document.getElementById(containerId);
        if (!container || containerTieneContenido(container) || cargasTabsPersistidos.has(containerId)) {
            return;
        }

        const tab = buscarTabPersistido(navTabId, containerId);
        if (!tab || (!tab.onclick && !tab.path) || typeof window.cargarContenidoDinamico !== 'function') {
            return;
        }

        cargasTabsPersistidos.add(containerId);
        window.__ultimoSidebarLinkLabel = tab.label || containerId;
        window.__ultimoSidebarLinkOnclick = tab.onclick || null;

        try {
            if (tab.onclick) {
                const result = new Function(tab.onclick).call(document.body);
                if (result && typeof result.then === 'function') {
                    await result;
                }
                await esperarCargaDeContainer(containerId);
            } else {
                await window.cargarContenidoDinamico(containerId, tab.path);
            }
        } catch (error) {
            console.warn('[TABS] Error recargando tab persistido', containerId, error);
        } finally {
            cargasTabsPersistidos.delete(containerId);
        }
    }

    // ====================================================
    // API: cerrar un tab (vacia su container y quita el chip)
    // ====================================================
    function closeTab(containerId) {
        const area = findAreaFor(containerId);
        const cont = document.getElementById(containerId);
        if (cont) {
            cont.innerHTML = '';
            cont.style.display = 'none';
        }

        // Quitar chip de la barra GLOBAL (antes estaba dentro del area,
        // ahora vive en #global-tabs-bar).
        const bar = document.getElementById('global-tabs-bar');
        if (bar) {
            const chip = bar.querySelector(`.section-tab[data-tab-container="${CSS.escape(containerId)}"]`);
            if (chip) chip.remove();
        }

        // Actualizar persistencia
        const navTab = containerToNavTab.get(containerId);
        if (navTab) {
            const state = readState();
            if (state[navTab]) {
                state[navTab].tabs = (state[navTab].tabs || []).filter(t => t.container !== containerId);
                if (state[navTab].active === containerId) {
                    state[navTab].active = state[navTab].tabs.length
                        ? state[navTab].tabs[state[navTab].tabs.length - 1].container
                        : null;
                }
                writeState(state);
            }
        }
        containerToNavTab.delete(containerId);

        // Si queda otro tab, activarlo
        if (area) {
            const state = readState();
            const navTabNow = getNavTabActiva();
            const activo = state[navTabNow] && state[navTabNow].active;
            if (activo) {
                switchTab(activo);
            }
        }
    }

    // ====================================================
    // API: abrir/registrar un tab (lo crea si no existe)
    // ====================================================
    function openTab(containerId, label, path, onclick) {
        const area = findAreaFor(containerId);
        if (!area) return;

        const navTab = getNavTabActiva();
        if (navTab) containerToNavTab.set(containerId, navTab);

        const bar = ensureTabsBar(area);
        renderTabChip(bar, { container: containerId, label, path, navTab });

        // Persistir
        if (navTab) {
            const state = readState();
            if (!state[navTab]) state[navTab] = { tabs: [], active: null };
            const existe = (state[navTab].tabs || []).find(t => t.container === containerId);
            if (!existe) {
                state[navTab].tabs.push({ container: containerId, label, path, onclick });
            } else {
                existe.label = label;
                existe.path = path;
                if (onclick) existe.onclick = onclick;
            }
            state[navTab].active = containerId;
            writeState(state);
        }

        markActive(area, containerId);
    }

    // ====================================================
    // Interceptor de cargarContenidoDinamico
    // ====================================================
    function instalarInterceptor() {
        const original = window.cargarContenidoDinamico;
        if (!original || original.__tabsInstalled) return;

        window.cargarContenidoDinamico = function (containerId, templatePath, initCallback) {
            // Detectar el label desde el ultimo .sidebar-link clickeado
            const label = window.__ultimoSidebarLinkLabel || containerId;
            const onclick = window.__ultimoSidebarLinkOnclick || null;
            const sidebarClickAge = Date.now() - (window.__ultimoSidebarLinkAt || 0);

            console.log('[TABS-INTERCEPT]', containerId, 'sidebarAge=', sidebarClickAge, 'ms');

            // Tratar como modulo (con tab) si el container termina en
            // -unique-container o -info-container (Informacion Basica).
            // Excluir los "default-container" que son placeholders vacios.
            const esModulo = containerId && (
                containerId.endsWith('-unique-container') ||
                (containerId.endsWith('-info-container') && containerId !== 'info-basica-default-container')
            );

            if (!esModulo) {
                return original.call(this, containerId, templatePath, initCallback);
            }

            // Si el ultimo click en sidebar fue hace MAS de 2 segundos,
            // esta llamada viene de codigo programatico (navegacion
            // interna desde DENTRO de un modulo, p.ej. "Ver detalle"
            // que abre otro container). NO abrir tab nuevo: solo cargar
            // contenido en el container existente.
            const esNavegacionInterna = sidebarClickAge > 2000;
            if (esNavegacionInterna) {
                console.log('[TABS-INTERCEPT] navegacion interna, no creo tab para', containerId);
                return original.call(this, containerId, templatePath, initCallback);
            }

            // Abrir/registrar tab antes de cargar (guardar onclick para
            // poder replayear el flujo completo al restaurar)
            openTab(containerId, label, templatePath, onclick);

            return original.call(this, containerId, templatePath, function () {
                console.log('[TABS-INITCB]', containerId, 'ejecutando initCallback?', typeof initCallback);
                if (initCallback) initCallback();
                // Marcar como activo despues de cargar
                switchTab(containerId);
            });
        };
        window.cargarContenidoDinamico.__tabsInstalled = true;
    }

    // ====================================================
    // Capturar el label y el onclick del ultimo link clickeado
    // ====================================================
    // El onclick contiene la llamada exacta (con su initCallback)
    // que carga el modulo. Lo guardamos para poder replayearlo en la
    // restauracion (sin esto, restauramos el HTML pero los listeners
    // del modulo no se inicializan -> botones no responden).
    document.addEventListener('click', function (e) {
        const link = e.target.closest('.sidebar-link');
        if (link) {
            window.__ultimoSidebarLinkLabel = link.textContent.trim();
            window.__ultimoSidebarLinkOnclick = link.getAttribute('onclick');
            window.__ultimoSidebarLinkAt = Date.now();
        }
    }, true);

    // ====================================================
    // Restauracion de tabs al cargar una seccion navbar
    // ====================================================
    // CRITICO: cargarContenidoDinamico usa un AbortController
    // global (__dynamicModuleLoadController) que aborta la carga
    // anterior al iniciar una nueva. Por eso restauramos en
    // SECUENCIA con await, no en paralelo. Si fueran en paralelo,
    // solo el ultimo terminaria y los demas se quedan en "Cargando...".
    // Guardia: solo permitir UNA restauracion en curso a la vez.
    let restauracionEnCurso = null;
    let restauracionVersion = 0;

    async function restaurarTabsDeSeccion(navTabId) {
        if (!navTabId || getNavTabActiva() !== navTabId) {
            return;
        }

        const version = ++restauracionVersion;
        restauracionEnCurso = navTabId;

        try {
            // Primero pintar chips de TODAS las secciones (no solo
            // la activa) para que la barra global tenga todos los
            // tabs visibles desde el primer momento.
            renderChipsGlobales();
            await _restaurarTabsDeSeccionInterna(navTabId, () => {
                return version === restauracionVersion && getNavTabActiva() === navTabId;
            });
            // _restaurarTabsDeSeccionInterna ya activa el container
            // correcto al final (pending o seccion.active). No duplicar.
            if (version === restauracionVersion && window.__pendingSwitchToContainer) {
                window.__pendingSwitchToContainer = null;
            }
        } finally {
            if (version === restauracionVersion) {
                restauracionEnCurso = null;
            }
        }
    }

    // ====================================================
    // Migracion: si un container fue movido a otra seccion
    // navbar (cambio de codigo) pero el state persistido
    // todavia lo apunta a la seccion vieja, moverlo a la
    // seccion correcta en base al *-content-area real del DOM.
    // ====================================================
    function migrarTabsACorrectaSeccion() {
        const state = readState();
        let cambio = false;
        // areaId -> navTab (espejo invertido de SECCIONES_AREAS_MAP)
        const areaIdToNavTab = {};
        Object.entries(SECCIONES_AREAS_MAP).forEach(([navTab, areaId]) => {
            areaIdToNavTab[areaId] = navTab;
        });

        Object.entries(state).forEach(([navTabActual, seccion]) => {
            if (!seccion || !Array.isArray(seccion.tabs)) return;
            const tabsAMover = [];
            seccion.tabs = seccion.tabs.filter(tab => {
                const cont = document.getElementById(tab.container);
                if (!cont) return true; // container no en DOM aun: dejarlo
                const area = cont.closest('[id$="-content-area"]');
                if (!area) return true;
                const navTabReal = areaIdToNavTab[area.id];
                if (!navTabReal || navTabReal === navTabActual) return true;
                tabsAMover.push({ tab, navTabReal });
                return false; // sacarlo de la seccion actual
            });
            tabsAMover.forEach(({ tab, navTabReal }) => {
                if (!state[navTabReal]) state[navTabReal] = { tabs: [], active: null };
                const yaExiste = (state[navTabReal].tabs || []).some(t => t.container === tab.container);
                if (!yaExiste) state[navTabReal].tabs.push(tab);
                // Si el tab era el activo de la seccion vieja, transferir
                if (seccion.active === tab.container) seccion.active = null;
                cambio = true;
                console.log('[TABS-MIGRATE]', tab.container, navTabActual, '->', navTabReal);
            });
        });

        if (cambio) writeState(state);
    }

    // Pinta TODOS los chips de TODAS las secciones en la barra global,
    // sin cargar el contenido (eso lo hace restaurarTabsDeSeccion
    // solo para la seccion activa, los demas tabs cargan lazy al click).
    function renderChipsGlobales() {
        migrarTabsACorrectaSeccion();
        const bar = ensureGlobalTabsBar();
        bar.innerHTML = '';
        const state = readState();
        Object.entries(state).forEach(([navTab, seccion]) => {
            if (!seccion || !seccion.tabs) return;
            seccion.tabs.forEach(tab => {
                containerToNavTab.set(tab.container, navTab);
                renderTabChip(bar, {
                    container: tab.container,
                    label: tab.label,
                    path: tab.path,
                    navTab: navTab
                });
            });
        });
    }
    window.renderChipsGlobales = renderChipsGlobales;

    async function _restaurarTabsDeSeccionInterna(navTabId, sigueVigente) {
        if (!sigueVigente()) return;

        const state = readState();
        const seccion = state[navTabId];
        if (!seccion || !seccion.tabs || !seccion.tabs.length) return;

        // Esperar a que al menos un container exista en DOM
        let intentos = 0;
        while (intentos < 30) {
            if (!sigueVigente()) return;
            const algoDisponible = seccion.tabs.some(t => document.getElementById(t.container));
            if (algoDisponible) break;
            await new Promise(r => setTimeout(r, 100));
            intentos++;
        }

        if (typeof window.cargarContenidoDinamico !== 'function') return;

        // Si hay un switchTab pendiente (venimos de otra seccion para
        // activar UN tab especifico), solo cargar ESE tab — los demas
        // se cargaran lazy cuando el usuario haga click en su chip.
        // Esto evita el parpadeo "ultimo active de la seccion -> tab pedido".
        let tabsACargar = seccion.tabs;
        if (window.__pendingSwitchToContainer) {
            const objetivo = window.__pendingSwitchToContainer;
            tabsACargar = seccion.tabs.filter(t => t.container === objetivo);
            console.log('[TABS-RESTORE] switchTab pendiente, solo cargando:', objetivo);
        }

        console.log('[TABS-RESTORE] iniciando, total tabs:', tabsACargar.length);
        for (const tab of tabsACargar) {
            if (!sigueVigente()) return;
            containerToNavTab.set(tab.container, navTabId);

            // Si el container ya tiene contenido cargado (no esta vacio
            // ni con "Cargando..."), no recargar. Solo registrar la
            // tab visualmente y restaurar visibilidad.
            const cont = document.getElementById(tab.container);
            const yaCargado = containerTieneContenido(cont);

            if (yaCargado) {
                console.log('[TABS-RESTORE] ya cargado, solo registrando chip:', tab.container);
                const area = findAreaFor(tab.container);
                if (area) {
                    const bar = ensureTabsBar(area);
                    renderTabChip(bar, { container: tab.container, label: tab.label, path: tab.path });
                }
                continue;
            }

            window.__ultimoSidebarLinkLabel = tab.label;
            window.__ultimoSidebarLinkOnclick = tab.onclick || null;
            console.log('[TABS-RESTORE] cargando:', tab.container);
            try {
                if (tab.onclick) {
                    const result = new Function(tab.onclick).call(document.body);
                    if (result && typeof result.then === 'function') {
                        await result;
                    }
                    const cont2 = document.getElementById(tab.container);
                    let espera = 0;
                    while (cont2 && cont2.innerHTML.includes('loading-indicator') && espera < 50) {
                        await new Promise(r => setTimeout(r, 100));
                        espera++;
                    }
                } else {
                    await window.cargarContenidoDinamico(tab.container, tab.path);
                }
                console.log('[TABS-RESTORE] OK:', tab.container);
            } catch (e) {
                console.warn('[TABS-RESTORE] Error cargando tab', tab.container, e);
            }
        }
        if (!sigueVigente()) return;
        console.log('[TABS-RESTORE] terminado');

        // Si hay switchTab pendiente, activar ese (no el ultimo active
        // de la seccion). Sin esto se ve parpadear el ultimo active
        // antes del tab realmente pedido.
        if (window.__pendingSwitchToContainer) {
            switchTab(window.__pendingSwitchToContainer);
        } else if (seccion.active) {
            switchTab(seccion.active);
        }
    }
    window.restaurarTabsDeSeccion = restaurarTabsDeSeccion;

    // ====================================================
    // Init: esperar a que cargarContenidoDinamico exista
    // ====================================================
    function init() {
        let intentos = 0;
        const tick = setInterval(() => {
            intentos++;
            if (typeof window.cargarContenidoDinamico === 'function') {
                instalarInterceptor();
                clearInterval(tick);
            } else if (intentos > 50) {
                console.warn('[TABS] cargarContenidoDinamico no aparecio en 5s');
                clearInterval(tick);
            }
        }, 100);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Exponer API
    window.sidebarTabs = { openTab, closeTab, switchTab, restaurarTabsDeSeccion };
})();
