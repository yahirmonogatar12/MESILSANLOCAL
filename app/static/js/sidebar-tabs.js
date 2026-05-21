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

    // ====================================================
    // Localizar el *-content-area dueño de un container
    // ====================================================
    function findAreaFor(containerId) {
        const cont = document.getElementById(containerId);
        if (!cont) return null;
        return cont.closest('[id$="-content-area"]') || cont.parentElement;
    }

    // ====================================================
    // Crear la barra de tabs si no existe
    // ====================================================
    function ensureTabsBar(area) {
        if (!area) return null;
        let bar = area.querySelector(':scope > .section-tabs-bar');
        if (bar) return bar;
        bar = document.createElement('div');
        bar.className = 'section-tabs-bar';
        // Insertar al principio del area
        area.insertBefore(bar, area.firstChild);
        return bar;
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
            chip.querySelector('.section-tab-title').addEventListener('click', () => {
                switchTab(tabInfo.container);
            });
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
        // Tooltip nativo con el texto completo (aparece al hover si se trunca)
        chip.setAttribute('title', tabInfo.label);
        return chip;
    }

    // ====================================================
    // Marcar tab activo (UI + ocultar contenidos hermanos)
    // ====================================================
    function markActive(area, containerActivo) {
        if (!area) return;
        // Tabs visuales
        area.querySelectorAll(':scope > .section-tabs-bar > .section-tab').forEach(chip => {
            const isActive = chip.getAttribute('data-tab-container') === containerActivo;
            chip.classList.toggle('active', isActive);
        });
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
        const area = findAreaFor(containerId);
        if (!area) return;
        markActive(area, containerId);

        // Persistir como activo en su seccion navbar
        const navTab = containerToNavTab.get(containerId) || getNavTabActiva();
        if (navTab) {
            const state = readState();
            if (!state[navTab]) state[navTab] = { tabs: [], active: null };
            state[navTab].active = containerId;
            writeState(state);
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

        // Quitar chip
        if (area) {
            const chip = area.querySelector(`.section-tab[data-tab-container="${CSS.escape(containerId)}"]`);
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
        renderTabChip(bar, { container: containerId, label, path });

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

    async function restaurarTabsDeSeccion(navTabId) {
        if (restauracionEnCurso) {
            console.log('[TABS-RESTORE] omitiendo: ya hay restauracion en curso para', restauracionEnCurso);
            return;
        }
        restauracionEnCurso = navTabId;

        try {
            await _restaurarTabsDeSeccionInterna(navTabId);
        } finally {
            restauracionEnCurso = null;
        }
    }

    async function _restaurarTabsDeSeccionInterna(navTabId) {
        const state = readState();
        const seccion = state[navTabId];
        if (!seccion || !seccion.tabs || !seccion.tabs.length) return;

        // Esperar a que al menos un container exista en DOM
        let intentos = 0;
        while (intentos < 30) {
            const algoDisponible = seccion.tabs.some(t => document.getElementById(t.container));
            if (algoDisponible) break;
            await new Promise(r => setTimeout(r, 100));
            intentos++;
        }

        if (typeof window.cargarContenidoDinamico !== 'function') return;

        // Cargar tabs uno por uno (secuencial por el AbortController).
        // Replayeamos el onclick original del sidebar-link para que se
        // ejecute la funcion mostrar*() correspondiente CON su
        // initCallback (que inicializa listeners del modulo). Sin esto
        // solo se carga el HTML pero los botones no responden.
        console.log('[TABS-RESTORE] iniciando, total tabs:', seccion.tabs.length);
        for (const tab of seccion.tabs) {
            containerToNavTab.set(tab.container, navTabId);

            // Si el container ya tiene contenido cargado (no esta vacio
            // ni con "Cargando..."), no recargar. Solo registrar la
            // tab visualmente y restaurar visibilidad.
            const cont = document.getElementById(tab.container);
            const yaCargado = cont &&
                cont.innerHTML.trim().length > 100 &&
                !cont.innerHTML.includes('loading-indicator');

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
        console.log('[TABS-RESTORE] terminado');

        // Activar el guardado como activo (oculta los demas y muestra el activo)
        if (seccion.active) {
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
