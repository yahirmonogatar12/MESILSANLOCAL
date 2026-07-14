(() => {
    'use strict';

    const I18N = {
        es: { assistant:'Asistente',title:'Asistente IA',chat:'Chat',history:'Historial',audit:'Auditoría',limits:'Cuotas',newChat:'Nuevo chat',archive:'Archivar',delete:'Eliminar',deleteConfirm:'¿Eliminar definitivamente este chat y todos sus archivos? Esta acción no se puede deshacer.',deleted:'Conversación eliminada',stopBeforeDelete:'Detén la respuesta antes de eliminar el chat.',message:'Mensaje',placeholder:'Pregunta sobre el MES o solicita un Excel/PowerPoint',stop:'Detener',retry:'Reintentar',send:'Enviar',expand:'Expandir panel',collapse:'Reducir panel',conversations:'Conversaciones',showArchived:'Mostrar archivadas',search:'Buscar',save:'Guardar',welcome:'¿En qué puedo ayudarte con el MES?',welcomeHint:'Puedo explicar módulos, consultar datos autorizados y crear Excel o PowerPoint.',thinking:'Pensando…',reasoning:'Razonando…',consulting:'Consultando datos autorizados…',generating:'Generando archivo…',error:'Ocurrió un error',download:'Descargar',expired:'Expirado',regenerate:'Regenerar',source:'Fuente',rows:'filas',notConfigured:'El administrador debe configurar OPENAI_API_KEY en el servidor.',archived:'Conversación archivada',empty:'No hay conversaciones.',lineProgressTitle:'Meta y avance por área',goal:'Meta',produced:'Producido',output:'Salida',activeLines:'líneas activas',noPlans:'Sin plan cargado',omittedAreas:'Áreas omitidas por permisos',qualityTitle:'Indicadores de calidad',qualityLqcResults:'Resultados LQC',qualityIct:'Historial ICT',qualityLqcRelease:'Liberación LQC',qualityVision:'Historial Vision',inspected:'Inspeccionados',defects:'Defectos',ppm:'PPM',target:'Objetivo',tests:'Pruebas',uniqueUnits:'Piezas únicas',passed:'OK',failed:'NG',passRate:'Rendimiento',scans:'Liberaciones',lots:'Lotes',duplicates:'Duplicados',onTarget:'En objetivo',offTarget:'Fuera de objetivo',noActivity:'Sin actividad',omittedSources:'Fuentes omitidas por permisos'},
        en: { assistant:'Assistant',title:'AI Assistant',chat:'Chat',history:'History',audit:'Audit',limits:'Quotas',newChat:'New chat',archive:'Archive',delete:'Delete',deleteConfirm:'Permanently delete this chat and all its files? This action cannot be undone.',deleted:'Conversation deleted',stopBeforeDelete:'Stop the response before deleting this chat.',message:'Message',placeholder:'Ask about the MES or request an Excel/PowerPoint',stop:'Stop',retry:'Retry',send:'Send',expand:'Expand panel',collapse:'Reduce panel',conversations:'Conversations',showArchived:'Show archived',search:'Search',save:'Save',welcome:'How can I help you with the MES?',welcomeHint:'I can explain modules, query authorized data, and create Excel or PowerPoint files.',thinking:'Thinking…',reasoning:'Reasoning…',consulting:'Querying authorized data…',generating:'Generating file…',error:'An error occurred',download:'Download',expired:'Expired',regenerate:'Regenerate',source:'Source',rows:'rows',notConfigured:'An administrator must configure OPENAI_API_KEY on the server.',archived:'Conversation archived',empty:'No conversations.',lineProgressTitle:'Target and progress by area',goal:'Target',produced:'Produced',output:'Output',activeLines:'active lines',noPlans:'No plan loaded',omittedAreas:'Areas omitted due to permissions',qualityTitle:'Quality indicators',qualityLqcResults:'LQC Results',qualityIct:'ICT History',qualityLqcRelease:'LQC Release',qualityVision:'Vision History',inspected:'Inspected',defects:'Defects',ppm:'PPM',target:'Target',tests:'Tests',uniqueUnits:'Unique units',passed:'OK',failed:'NG',passRate:'Yield',scans:'Releases',lots:'Lots',duplicates:'Duplicates',onTarget:'On target',offTarget:'Off target',noActivity:'No activity',omittedSources:'Sources omitted due to permissions'},
        ko: { assistant:'도우미',title:'AI 도우미',chat:'채팅',history:'기록',audit:'감사',limits:'사용량',newChat:'새 채팅',archive:'보관',delete:'삭제',deleteConfirm:'이 채팅과 모든 파일을 영구적으로 삭제할까요? 이 작업은 취소할 수 없습니다.',deleted:'대화가 삭제되었습니다',stopBeforeDelete:'채팅을 삭제하기 전에 응답을 중지하세요.',message:'메시지',placeholder:'MES 질문 또는 Excel/PowerPoint 생성을 요청하세요',stop:'중지',retry:'다시 시도',send:'전송',expand:'패널 확장',collapse:'패널 축소',conversations:'대화 기록',showArchived:'보관된 항목 표시',search:'검색',save:'저장',welcome:'MES 사용을 어떻게 도와드릴까요?',welcomeHint:'모듈 설명, 권한이 있는 데이터 조회, Excel 또는 PowerPoint 생성을 지원합니다.',thinking:'생각 중…',reasoning:'추론 중…',consulting:'권한이 있는 데이터를 조회 중…',generating:'파일 생성 중…',error:'오류가 발생했습니다',download:'다운로드',expired:'만료됨',regenerate:'다시 생성',source:'출처',rows:'행',notConfigured:'관리자가 서버에 OPENAI_API_KEY를 설정해야 합니다.',archived:'대화가 보관되었습니다',empty:'대화가 없습니다.',lineProgressTitle:'영역별 목표 및 진행률',goal:'목표',produced:'생산',output:'출력',activeLines:'가동 라인',noPlans:'등록된 계획 없음',omittedAreas:'권한으로 제외된 영역',qualityTitle:'품질 지표',qualityLqcResults:'LQC 결과',qualityIct:'ICT 이력',qualityLqcRelease:'LQC 출하 승인',qualityVision:'Vision 이력',inspected:'검사 수량',defects:'불량',ppm:'PPM',target:'목표',tests:'검사',uniqueUnits:'고유 제품',passed:'OK',failed:'NG',passRate:'수율',scans:'승인 수량',lots:'로트',duplicates:'중복',onTarget:'목표 이내',offTarget:'목표 초과',noActivity:'활동 없음',omittedSources:'권한으로 제외된 소스'}
    };

    class MESAI {
        constructor(root) {
            this.root = root;
            this.launcher = root.querySelector('#ai-assistant-launcher');
            this.panel = root.querySelector('#ai-assistant-panel');
            this.backdrop = root.querySelector('#ai-assistant-backdrop');
            this.messages = root.querySelector('#ai-messages');
            this.input = root.querySelector('#ai-input');
            this.language = root.querySelector('#ai-language');
            this.currentConversation = null;
            this.bootstrap = null;
            this.controller = null;
            this.streaming = false;
            this.lastUserMessage = '';
            this.activeAssistantBubble = null;
            this.activeAssistantText = '';
            this.thinkingTimer = null;
            this.expanded = false;
            this.launcherDrag = null;
            this.suppressLauncherClickUntil = 0;
            this.transitioning = false;
            this.artifactIds = new Set();
            this.visualizationIds = new Set();
        }

        async init() {
            this.bind();
            try {
                this.bootstrap = await this.api('/api/ai/bootstrap');
            } catch (error) {
                if (error.status === 401 || error.status === 403) return;
                console.warn('Asistente IA no disponible:', error);
                return;
            }
            this.root.hidden = false;
            this.setLauncherSide(localStorage.getItem('mes-ai-launcher-side') === 'left' ? 'left' : 'right', false);
            this.root.querySelector('#ai-model-label').textContent = this.bootstrap.model || 'GPT';
            const attachBtn = this.root.querySelector('#ai-attach');
            if (attachBtn) attachBtn.hidden = !this.bootstrap.can_use_plan;
            this.root.querySelector('#ai-audit-tab').hidden = !this.bootstrap.can_audit;
            this.root.querySelector('#ai-limits-tab').hidden = !this.bootstrap.can_manage_limits;
            this.root.querySelector('#ai-sidebar-audit-tab').hidden = !this.bootstrap.can_audit;
            this.root.querySelector('#ai-sidebar-limits-tab').hidden = !this.bootstrap.can_manage_limits;
            const savedLanguage = localStorage.getItem('mes-ai-language') || 'auto';
            this.language.value = ['auto','es','en','ko'].includes(savedLanguage) ? savedLanguage : 'auto';
            this.setExpanded(localStorage.getItem('mes-ai-expanded') === '1', false);
            this.translate();
            this.updateUsage(this.bootstrap.usage, this.bootstrap.limits);
            if (!this.bootstrap.configured) this.notice(this.t('notConfigured'));
            await this.loadConversations();
            this.renderEmpty();
        }

        bind() {
            this.launcher.addEventListener('click', event => {
                if (performance.now() < this.suppressLauncherClickUntil) {
                    event.preventDefault();
                    return;
                }
                this.open();
            });
            this.bindLauncherDrag();
            this.root.querySelector('#ai-close').addEventListener('click', () => this.close());
            this.root.querySelector('#ai-expand').addEventListener('click', () => this.setExpanded(!this.expanded));
            this.backdrop.addEventListener('click', () => this.close());
            this.root.querySelectorAll('[data-ai-action="new-chat"]').forEach(button => {
                button.addEventListener('click', () => this.newChat(true));
            });
            this.root.querySelector('#ai-archive-chat').addEventListener('click', () => this.archive());
            this.root.querySelector('#ai-delete-chat').addEventListener('click', () => this.deleteConversation());
            this.root.querySelector('#ai-stop').addEventListener('click', () => this.stop());
            this.root.querySelector('#ai-retry').addEventListener('click', () => this.retry());
            this.root.querySelector('#ai-composer').addEventListener('submit', event => {
                event.preventDefault();
                this.send();
            });
            const attachBtn = this.root.querySelector('#ai-attach');
            const attachFile = this.root.querySelector('#ai-attach-file');
            if (attachBtn && attachFile) {
                attachBtn.addEventListener('click', () => { attachFile.value = ''; attachFile.click(); });
                attachFile.addEventListener('change', () => {
                    const file = attachFile.files && attachFile.files[0];
                    if (file) this.uploadPlanFile(file);
                });
                this.root.querySelector('#ai-attach-clear').addEventListener('click', () => this.clearAttachment());
            }
            this.input.addEventListener('keydown', event => {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    this.send();
                }
            });
            this.language.addEventListener('change', async () => {
                localStorage.setItem('mes-ai-language', this.language.value);
                this.translate();
                if (this.currentConversation) {
                    await this.api(`/api/ai/conversations/${this.currentConversation.public_id}`, {method:'PATCH', body:{language:this.language.value}});
                }
            });
            this.root.querySelectorAll('[data-ai-tab]').forEach(button => button.addEventListener('click', () => this.showTab(button.dataset.aiTab)));
            this.root.querySelector('#ai-show-archived').addEventListener('change', () => this.loadConversations());
            this.root.querySelector('#ai-audit-search').addEventListener('click', () => this.loadAudit());
            this.root.querySelector('#ai-limit-form').addEventListener('submit', event => this.saveLimit(event));
        }

        async api(url, options = {}) {
            const headers = {'X-Requested-With':'XMLHttpRequest','Accept':'application/json', ...(options.headers || {})};
            const fetchOptions = {...options, headers};
            if (options.body && !(options.body instanceof FormData) && typeof options.body !== 'string') {
                headers['Content-Type'] = 'application/json';
                fetchOptions.body = JSON.stringify(options.body);
            } else if (!options.body) {
                headers['Content-Type'] = 'application/json';
            }
            const response = await fetch(url, fetchOptions);
            let data;
            try { data = await response.json(); } catch (_) { data = {error: response.statusText}; }
            if (!response.ok) {
                const error = new Error(data.error || data.message || response.statusText);
                error.status = response.status;
                error.data = data;
                throw error;
            }
            return data;
        }

        t(key) {
            let lang = this.language?.value || 'auto';
            if (lang === 'auto') {
                const browser = (navigator.language || 'es').toLowerCase();
                lang = browser.startsWith('ko') ? 'ko' : browser.startsWith('en') ? 'en' : 'es';
            }
            return (I18N[lang] || I18N.es)[key] || I18N.es[key] || key;
        }

        translate() {
            this.root.querySelectorAll('[data-ai-i18n]').forEach(node => node.textContent = this.t(node.dataset.aiI18n));
            this.root.querySelectorAll('[data-ai-i18n-placeholder]').forEach(node => node.placeholder = this.t(node.dataset.aiI18nPlaceholder));
            this.updateExpandButton();
            if (!this.messages.children.length) this.renderEmpty();
        }

        setExpanded(expanded, persist = true) {
            this.expanded = Boolean(expanded);
            this.panel.classList.toggle('expanded', this.expanded);
            if (persist) localStorage.setItem('mes-ai-expanded', this.expanded ? '1' : '0');
            this.updateExpandButton();
            this.scrollBottom();
        }

        updateExpandButton() {
            const button = this.root.querySelector('#ai-expand');
            if (!button) return;
            const label = this.t(this.expanded ? 'collapse' : 'expand');
            button.setAttribute('aria-label', label);
            button.setAttribute('title', label);
            button.setAttribute('aria-pressed', String(this.expanded));
        }

        setLauncherSide(side, persist = true) {
            const normalized = side === 'left' ? 'left' : 'right';
            this.launcher.dataset.side = normalized;
            if (persist) localStorage.setItem('mes-ai-launcher-side', normalized);
        }

        bindLauncherDrag() {
            const launcher = this.launcher;
            launcher.addEventListener('pointerdown', event => {
                if (event.button !== 0 || this.panel.classList.contains('open')) return;
                const rect = launcher.getBoundingClientRect();
                this.launcherDrag = {
                    pointerId: event.pointerId,
                    startX: event.clientX,
                    offsetX: event.clientX - rect.left,
                    moved: false,
                };
                try { launcher.setPointerCapture(event.pointerId); } catch (_) { /* captura opcional */ }
            });
            launcher.addEventListener('pointermove', event => {
                const drag = this.launcherDrag;
                if (!drag || drag.pointerId !== event.pointerId) return;
                if (!drag.moved && Math.abs(event.clientX - drag.startX) < 6) return;
                drag.moved = true;
                const maxLeft = Math.max(8, window.innerWidth - launcher.offsetWidth - 8);
                const left = Math.min(maxLeft, Math.max(8, event.clientX - drag.offsetX));
                launcher.classList.add('dragging');
                launcher.style.left = `${left}px`;
                launcher.style.right = 'auto';
                event.preventDefault();
            });
            const finish = (event, cancelled = false) => {
                const drag = this.launcherDrag;
                if (!drag || drag.pointerId !== event.pointerId) return;
                this.launcherDrag = null;
                launcher.classList.remove('dragging');
                launcher.style.left = '';
                launcher.style.right = '';
                if (drag.moved && !cancelled) {
                    this.setLauncherSide(event.clientX < window.innerWidth / 2 ? 'left' : 'right');
                    this.suppressLauncherClickUntil = performance.now() + 500;
                    event.preventDefault();
                }
                try { launcher.releasePointerCapture(event.pointerId); } catch (_) { /* captura opcional */ }
            };
            launcher.addEventListener('pointerup', event => finish(event));
            launcher.addEventListener('pointercancel', event => finish(event, true));
        }

        prefersReducedMotion() {
            return Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches);
        }

        wait(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        nextFrame() {
            return new Promise(resolve => requestAnimationFrame(() => resolve()));
        }

        rectStyle(rect, extra = {}) {
            return {
                left: `${rect.left}px`,
                top: `${rect.top}px`,
                width: `${rect.width}px`,
                height: `${rect.height}px`,
                ...extra,
            };
        }

        centerRect(container, size) {
            return {
                left: container.left + (container.width - size) / 2,
                top: container.top + (container.height - size) / 2,
                width: size,
                height: size,
            };
        }

        getPanelTargetRect() {
            const previousTransition = this.panel.style.transition;
            const previousTransform = this.panel.style.transform;
            const previousVisibility = this.panel.style.visibility;
            const previousPointerEvents = this.panel.style.pointerEvents;
            this.panel.style.transition = 'none';
            this.panel.style.transform = 'translateX(0)';
            this.panel.style.visibility = 'hidden';
            this.panel.style.pointerEvents = 'none';
            const rect = this.panel.getBoundingClientRect();
            this.panel.style.transition = previousTransition;
            this.panel.style.transform = previousTransform;
            this.panel.style.visibility = previousVisibility;
            this.panel.style.pointerEvents = previousPointerEvents;
            return rect;
        }

        async setPanelOpenInstant(open) {
            const previousTransition = this.panel.style.transition;
            this.panel.classList.add('is-instant');
            this.panel.style.transition = 'none';
            this.panel.getBoundingClientRect();
            this.panel.classList.toggle('open', open);
            this.panel.setAttribute('aria-hidden', open ? 'false' : 'true');
            this.panel.getBoundingClientRect();
            await this.nextFrame();
            this.panel.style.transition = previousTransition;
            this.panel.classList.remove('is-instant');
        }

        createPanelMorphShell(rect, opacity = 1) {
            const shell = document.createElement('div');
            shell.className = 'ai-panel-morph-shell';
            Object.assign(shell.style, this.rectStyle(rect, {
                opacity: String(opacity),
                borderRadius: rect.width === rect.height ? '50%' : '0px',
            }));
            document.body.appendChild(shell);
            return shell;
        }

        createPanelMorphLogo(rect) {
            const source = this.launcher.querySelector('img') || this.root.querySelector('.ai-panel-mark-logo');
            const logo = document.createElement('img');
            logo.src = source?.currentSrc || source?.src || '/static/icons/1538298822.svg';
            logo.alt = '';
            logo.className = 'ai-panel-morph-logo';
            Object.assign(logo.style, this.rectStyle(rect));
            document.body.appendChild(logo);
            return logo;
        }

        async animateElement(element, keyframes, options) {
            const frames = Array.isArray(keyframes) ? keyframes : [keyframes];
            const finalFrame = frames[frames.length - 1] || {};
            const duration = this.prefersReducedMotion() ? 1 : Number(options?.duration || 0);
            const animationOptions = {...options, duration, fill: 'forwards'};
            if (!element.animate) {
                Object.assign(element.style, finalFrame);
                await this.wait(duration);
                return;
            }
            const animation = element.animate(frames, animationOptions);
            await animation.finished.catch(() => {});
            Object.assign(element.style, finalFrame);
        }

        async runPanelOpenAnimation() {
            if (this.prefersReducedMotion()) {
                this.backdrop.hidden = false;
                this.panel.classList.add('open');
                this.panel.setAttribute('aria-hidden', 'false');
                return;
            }

            const launcherRect = this.launcher.getBoundingClientRect();
            const panelRect = this.getPanelTargetRect();
            const logoSize = Math.min(72, Math.max(58, Math.round(Math.min(panelRect.width, panelRect.height) * .12)));
            const centerLogoRect = this.centerRect(panelRect, logoSize);

            const shell = this.createPanelMorphShell(launcherRect);
            const logo = this.createPanelMorphLogo(launcherRect);
            const easing = 'cubic-bezier(.16,1,.3,1)';
            const launcherSurface = {backgroundColor: '#fff', boxShadow: '0 10px 28px rgba(0,70,36,.22)'};
            const panelSurface = {backgroundColor: '#f2f5f7', boxShadow: '-12px 0 34px rgba(9,24,39,.32)'};
            Object.assign(shell.style, launcherSurface);
            this.launcher.classList.add('is-morphing');
            this.panel.classList.add('is-logo-landing');
            this.backdrop.hidden = false;

            try {
                await Promise.all([
                    this.animateElement(shell, [
                        this.rectStyle(launcherRect, {borderRadius: '50%', opacity: '1', ...launcherSurface}),
                        this.rectStyle(panelRect, {borderRadius: '0px', opacity: '1', ...panelSurface}),
                    ], {duration: 1500, easing}),
                    this.animateElement(logo, [
                        this.rectStyle(launcherRect, {opacity: '1'}),
                        this.rectStyle(centerLogoRect, {opacity: '1'}),
                    ], {duration: 1500, easing}),
                ]);

                await this.setPanelOpenInstant(true);
                await this.wait(1000);

                await this.animateElement(shell, [
                    {opacity: '1'},
                    {opacity: '0'},
                ], {duration: 1000, easing: 'cubic-bezier(.4,0,.2,1)'});

                const mark = this.root.querySelector('.ai-panel-mark-logo');
                const markRect = mark?.getBoundingClientRect();
                if (markRect) {
                    await this.animateElement(logo, [
                        this.rectStyle(centerLogoRect, {opacity: '1'}),
                        this.rectStyle(markRect, {opacity: '1'}),
                    ], {duration: 720, easing: 'cubic-bezier(.2,.85,.25,1)'});
                } else {
                    await this.animateElement(logo, [{opacity: '1'}, {opacity: '0'}], {duration: 240, easing});
                }
            } finally {
                shell.remove();
                logo.remove();
                this.launcher.classList.remove('is-morphing');
                this.panel.classList.remove('is-logo-landing');
            }
        }

        async runPanelCloseAnimation() {
            if (this.prefersReducedMotion()) {
                this.panel.classList.remove('open');
                this.panel.setAttribute('aria-hidden', 'true');
                this.backdrop.hidden = true;
                return;
            }

            const panelRect = this.panel.getBoundingClientRect();
            const launcherRect = this.launcher.getBoundingClientRect();
            const mark = this.root.querySelector('.ai-panel-mark-logo');
            const markRect = mark?.getBoundingClientRect() || this.centerRect(panelRect, 38);
            const logoSize = Math.min(72, Math.max(58, Math.round(Math.min(panelRect.width, panelRect.height) * .12)));
            const centerLogoRect = this.centerRect(panelRect, logoSize);

            const shell = this.createPanelMorphShell(panelRect, 0);
            const logo = this.createPanelMorphLogo(markRect);
            const easing = 'cubic-bezier(.16,1,.3,1)';
            const launcherSurface = {backgroundColor: '#fff', boxShadow: '0 10px 28px rgba(0,70,36,.22)'};
            const panelSurface = {backgroundColor: '#f2f5f7', boxShadow: '-12px 0 34px rgba(9,24,39,.32)'};
            Object.assign(shell.style, panelSurface);
            this.launcher.classList.add('is-morphing');
            this.panel.classList.add('is-logo-landing');

            try {
                await Promise.all([
                    this.animateElement(shell, [{opacity: '0'}, {opacity: '1'}], {duration: 520, easing: 'cubic-bezier(.4,0,.2,1)'}),
                    this.animateElement(logo, [
                        this.rectStyle(markRect, {opacity: '1'}),
                        this.rectStyle(centerLogoRect, {opacity: '1'}),
                    ], {duration: 720, easing}),
                ]);

                await this.setPanelOpenInstant(false);

                await Promise.all([
                    this.animateElement(shell, [
                        this.rectStyle(panelRect, {borderRadius: '0px', opacity: '1', ...panelSurface}),
                        this.rectStyle(launcherRect, {borderRadius: '50%', opacity: '1', ...launcherSurface}),
                    ], {duration: 1100, easing}),
                    this.animateElement(logo, [
                        this.rectStyle(centerLogoRect, {opacity: '1'}),
                        this.rectStyle(launcherRect, {opacity: '1'}),
                    ], {duration: 1100, easing}),
                ]);
            } finally {
                shell.remove();
                logo.remove();
                this.launcher.classList.remove('is-morphing');
                this.panel.classList.remove('is-logo-landing');
                this.backdrop.hidden = true;
            }
        }

        async open() {
            if (this.transitioning || this.panel.classList.contains('open')) return;
            this.transitioning = true;
            this.launcher.setAttribute('aria-expanded', 'true');
            document.body.style.overflow = 'hidden';
            if (!this.currentConversation && this.bootstrap?.configured) this.newChat(false);
            try {
                await this.runPanelOpenAnimation();
                setTimeout(() => this.input.focus(), 120);
            } catch (error) {
                this.launcher.setAttribute('aria-expanded', 'false');
                document.body.style.overflow = '';
                console.warn('No se pudo abrir la animación del asistente IA:', error);
            } finally {
                this.transitioning = false;
            }
        }

        async close() {
            if (this.transitioning || (!this.panel.classList.contains('open') && this.backdrop.hidden)) return;
            this.transitioning = true;
            this.launcher.setAttribute('aria-expanded', 'false');
            try {
                await this.runPanelCloseAnimation();
            } finally {
                document.body.style.overflow = '';
                this.transitioning = false;
            }
        }

        showTab(name) {
            this.root.querySelectorAll('[data-ai-tab]').forEach(node => node.classList.toggle('active', node.dataset.aiTab === name));
            this.root.querySelectorAll('[data-ai-view]').forEach(node => node.classList.toggle('active', node.dataset.aiView === name));
            if (name === 'history') this.loadConversations();
            if (name === 'audit') this.loadAudit();
            if (name === 'limits') this.loadLimits();
        }

        notice(text, type = 'warning') {
            const node = this.root.querySelector('#ai-notice');
            node.textContent = text || '';
            node.hidden = !text;
            node.dataset.type = type;
        }

        renderEmpty() {
            this.messages.innerHTML = '';
            const empty = document.createElement('div');
            empty.className = 'ai-empty';
            const strong = document.createElement('strong');
            strong.textContent = this.t('welcome');
            const text = document.createElement('span');
            text.textContent = this.t('welcomeHint');
            empty.append(strong, text);
            this.messages.appendChild(empty);
        }

        async loadConversations() {
            if (!this.bootstrap) return;
            const archived = this.root.querySelector('#ai-show-archived').checked ? '&include_archived=1' : '';
            const data = await this.api(`/api/ai/conversations?limit=100${archived}`);
            this.root.querySelectorAll('[data-ai-conversation-list]').forEach(list => {
                list.innerHTML = '';
                if (!data.conversations.length) {
                    const empty = document.createElement('div'); empty.className = 'ai-empty'; empty.textContent = this.t('empty'); list.appendChild(empty); return;
                }
                data.conversations.forEach(conversation => {
                    const item = document.createElement('div'); item.className = 'ai-list-row';
                    const button = document.createElement('button'); button.type = 'button'; button.className = 'ai-list-item';
                    button.dataset.conversationId = conversation.public_id;
                    const title = document.createElement('div'); title.className = 'ai-list-title'; title.textContent = conversation.title;
                    const meta = document.createElement('div'); meta.className = 'ai-list-meta'; meta.textContent = `${conversation.status} · ${this.formatDate(conversation.updated_at)}`;
                    button.append(title, meta);
                    button.addEventListener('click', async () => { await this.selectConversation(conversation); this.showTab('chat'); });
                    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'ai-list-delete';
                    remove.textContent = '×'; remove.title = this.t('delete'); remove.setAttribute('aria-label', `${this.t('delete')}: ${conversation.title}`);
                    remove.addEventListener('click', () => this.deleteConversation(conversation));
                    item.append(button, remove);
                    list.appendChild(item);
                });
            });
            this.highlightConversation();
        }

        highlightConversation() {
            const currentId = this.currentConversation?.public_id || '';
            this.root.querySelectorAll('[data-conversation-id]').forEach(button => {
                button.classList.toggle('active', Boolean(currentId) && button.dataset.conversationId === currentId);
            });
        }

        async newChat(select = true) {
            if (!this.bootstrap?.configured) { this.notice(this.t('notConfigured')); return; }
            const data = await this.api('/api/ai/conversations', {method:'POST', body:{language:this.language.value}});
            this.currentConversation = data.conversation;
            this.artifactIds.clear();
            this.visualizationIds.clear();
            this.renderEmpty();
            if (select) this.showTab('chat');
            await this.loadConversations();
        }

        async selectConversation(conversation) {
            this.currentConversation = conversation;
            this.highlightConversation();
            this.language.value = conversation.language || 'auto';
            this.translate();
            const data = await this.api(`/api/ai/conversations/${conversation.public_id}/messages?limit=100`);
            this.messages.innerHTML = '';
            this.artifactIds.clear();
            this.visualizationIds.clear();
            data.messages.forEach(message => {
                const bubble = this.appendMessage(message.role, message.content, message.created_at, message.status);
                const artifacts = message.content_json?.artifacts || [];
                artifacts.forEach(artifact => this.appendArtifact(artifact, bubble.parentElement));
                const visualizations = message.content_json?.visualizations || [];
                visualizations.forEach(visualization => this.appendVisualization(visualization, bubble.parentElement));
            });
            const artifacts = await this.api(`/api/ai/conversations/${conversation.public_id}/artifacts`);
            artifacts.artifacts.forEach(artifact => this.appendArtifact(artifact));
            if (!data.messages.length) this.renderEmpty();
            this.scrollBottom();
        }

        async archive() {
            if (!this.currentConversation) return;
            await this.api(`/api/ai/conversations/${this.currentConversation.public_id}`, {method:'PATCH', body:{status:'archived'}});
            this.currentConversation = null;
            this.renderEmpty();
            this.notice(this.t('archived'), 'success');
            await this.loadConversations();
        }

        async deleteConversation(conversation = this.currentConversation) {
            if (!conversation) return;
            if (this.streaming && conversation.public_id === this.currentConversation?.public_id) {
                this.notice(this.t('stopBeforeDelete'));
                return;
            }
            if (!window.confirm(`${this.t('deleteConfirm')}\n\n${conversation.title || ''}`)) return;
            await this.api(`/api/ai/conversations/${conversation.public_id}`, {method:'DELETE'});
            if (this.currentConversation?.public_id === conversation.public_id) {
                this.currentConversation = null;
                this.artifactIds.clear();
                this.visualizationIds.clear();
                this.renderEmpty();
            }
            this.notice(this.t('deleted'), 'success');
            await this.loadConversations();
        }

        pageContext() {
            const candidates = [...document.querySelectorAll('[id$="-unique-container"], .content-container, .tab-pane')];
            const visible = candidates.find(node => {
                const style = getComputedStyle(node);
                return style.display !== 'none' && style.visibility !== 'hidden' && node.offsetParent !== null;
            });
            return {path: location.pathname, container_id: visible?.id || null, title: document.title};
        }

        appendMessage(role, content = '', date = null, status = 'complete') {
            this.messages.querySelector('.ai-empty')?.remove();
            const wrapper = document.createElement('div'); wrapper.className = `ai-message ${role === 'user' ? 'user' : 'assistant'}`;
            const bubble = document.createElement('div'); bubble.className = 'ai-bubble';
            if (role === 'user') bubble.textContent = content;
            else this.renderMarkdown(bubble, content);
            const meta = document.createElement('div'); meta.className = 'ai-message-meta'; meta.textContent = `${this.formatDate(date || new Date())}${status !== 'complete' ? ` · ${status}` : ''}`;
            wrapper.append(bubble, meta); this.messages.appendChild(wrapper); this.scrollBottom(); return bubble;
        }

        appendInlineMarkdown(parent, source) {
            const text = String(source || '');
            const pattern = /(\*\*[^*\n]+\*\*|`[^`\n]+`)/g;
            let cursor = 0;
            for (const match of text.matchAll(pattern)) {
                if (match.index > cursor) parent.appendChild(document.createTextNode(text.slice(cursor, match.index)));
                const token = match[0];
                const node = document.createElement(token.startsWith('**') ? 'strong' : 'code');
                node.textContent = token.startsWith('**') ? token.slice(2, -2) : token.slice(1, -1);
                parent.appendChild(node);
                cursor = match.index + token.length;
            }
            if (cursor < text.length) parent.appendChild(document.createTextNode(text.slice(cursor)));
        }

        markdownCells(line) {
            return String(line || '').trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim());
        }

        isMarkdownTableSeparator(line) {
            const cells = this.markdownCells(line);
            return cells.length > 0 && cells.every(cell => /^:?-{3,}:?$/.test(cell));
        }

        renderMarkdown(bubble, source) {
            bubble.replaceChildren();
            bubble.classList.remove('ai-streaming-text');
            bubble.classList.add('ai-markdown');
            const lines = String(source || '').replace(/\r\n?/g, '\n').split('\n');
            let index = 0;
            while (index < lines.length) {
                const line = lines[index];
                if (!line.trim()) { index += 1; continue; }

                const heading = line.match(/^(#{1,3})\s+(.+)$/);
                if (heading) {
                    const node = document.createElement(`h${heading[1].length + 2}`);
                    this.appendInlineMarkdown(node, heading[2]);
                    bubble.appendChild(node); index += 1; continue;
                }

                if (line.includes('|') && index + 1 < lines.length && this.isMarkdownTableSeparator(lines[index + 1])) {
                    const wrap = document.createElement('div'); wrap.className = 'ai-markdown-table-wrap';
                    const table = document.createElement('table');
                    const thead = document.createElement('thead'); const headRow = document.createElement('tr');
                    this.markdownCells(line).forEach(value => {
                        const cell = document.createElement('th'); this.appendInlineMarkdown(cell, value); headRow.appendChild(cell);
                    });
                    thead.appendChild(headRow); table.appendChild(thead); index += 2;
                    const tbody = document.createElement('tbody');
                    while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
                        const row = document.createElement('tr');
                        this.markdownCells(lines[index]).forEach(value => {
                            const cell = document.createElement('td'); this.appendInlineMarkdown(cell, value); row.appendChild(cell);
                        });
                        tbody.appendChild(row); index += 1;
                    }
                    table.appendChild(tbody); wrap.appendChild(table); bubble.appendChild(wrap); continue;
                }

                const listMatch = line.match(/^\s*(?:([-*])|(\d+)\.)\s+(.+)$/);
                if (listMatch) {
                    const ordered = Boolean(listMatch[2]);
                    const list = document.createElement(ordered ? 'ol' : 'ul');
                    while (index < lines.length) {
                        const itemMatch = lines[index].match(/^\s*(?:([-*])|(\d+)\.)\s+(.+)$/);
                        if (!itemMatch || Boolean(itemMatch[2]) !== ordered) break;
                        const item = document.createElement('li'); this.appendInlineMarkdown(item, itemMatch[3]); list.appendChild(item); index += 1;
                    }
                    bubble.appendChild(list); continue;
                }

                const quote = line.match(/^>\s?(.+)$/);
                if (quote) {
                    const node = document.createElement('blockquote'); this.appendInlineMarkdown(node, quote[1]);
                    bubble.appendChild(node); index += 1; continue;
                }

                const paragraphLines = [line.trim()]; index += 1;
                while (index < lines.length && lines[index].trim()
                    && !/^(#{1,3})\s+/.test(lines[index])
                    && !/^\s*(?:[-*]|\d+\.)\s+/.test(lines[index])
                    && !/^>\s?/.test(lines[index])
                    && !(lines[index].includes('|') && index + 1 < lines.length && this.isMarkdownTableSeparator(lines[index + 1]))) {
                    paragraphLines.push(lines[index].trim()); index += 1;
                }
                const paragraph = document.createElement('p'); this.appendInlineMarkdown(paragraph, paragraphLines.join(' ')); bubble.appendChild(paragraph);
            }
        }

        showThinkingIndicator(label) {
            if (!this.activeAssistantBubble || this.activeAssistantText) return;
            const bubble = this.activeAssistantBubble;
            bubble.replaceChildren();
            bubble.classList.remove('ai-markdown', 'ai-streaming-text');
            bubble.classList.add('ai-thinking-bubble');
            const indicator = document.createElement('div');
            indicator.className = 'ai-thinking-indicator';
            indicator.setAttribute('role', 'status');
            indicator.setAttribute('aria-live', 'polite');
            const dots = document.createElement('span');
            dots.className = 'ai-thinking-dots';
            dots.setAttribute('aria-hidden', 'true');
            for (let index = 0; index < 3; index += 1) dots.appendChild(document.createElement('i'));
            const text = document.createElement('span');
            text.className = 'ai-thinking-label';
            text.textContent = label;
            indicator.append(dots, text);
            bubble.appendChild(indicator);
            this.scrollBottom();
        }

        startThinkingIndicator() {
            this.stopThinkingIndicator();
            this.showThinkingIndicator(this.t('thinking'));
            this.thinkingTimer = window.setTimeout(() => {
                this.thinkingTimer = null;
                if (this.streaming && !this.activeAssistantText) this.showThinkingIndicator(this.t('reasoning'));
            }, 1200);
        }

        stopThinkingIndicator() {
            if (this.thinkingTimer) window.clearTimeout(this.thinkingTimer);
            this.thinkingTimer = null;
            this.activeAssistantBubble?.classList.remove('ai-thinking-bubble');
        }

        appendArtifact(artifact, parent = null) {
            if (!artifact?.id || this.artifactIds.has(artifact.id)) return;
            this.artifactIds.add(artifact.id);
            const card = document.createElement('div'); card.className = 'ai-artifact';
            const title = document.createElement('div'); title.className = 'ai-artifact-title'; title.textContent = `${(artifact.type || '').toUpperCase()} · ${artifact.title || artifact.filename}`;
            const meta = document.createElement('div'); meta.className = 'ai-artifact-meta';
            meta.textContent = `${artifact.row_count || 0} ${this.t('rows')} · ${this.fileSize(artifact.size_bytes)} · ${this.formatDate(artifact.expires_at)}`;
            card.append(title, meta);
            if (artifact.source) {
                const source = document.createElement('div'); source.className = 'ai-artifact-meta';
                source.textContent = `${this.t('source')}: ${artifact.source}`; card.appendChild(source);
            }
            if (artifact.status === 'ready' && artifact.download_url) {
                const link = document.createElement('a'); link.href = artifact.download_url; link.textContent = this.t('download'); link.setAttribute('download', artifact.filename || ''); card.appendChild(link);
            } else {
                const expired = document.createElement('span'); expired.textContent = this.t('expired'); card.appendChild(expired);
                if (this.bootstrap?.can_generate_artifacts) {
                    const regenerate = document.createElement('button'); regenerate.type = 'button'; regenerate.className = 'ai-link-button'; regenerate.textContent = this.t('regenerate');
                    regenerate.addEventListener('click', async () => {
                        regenerate.disabled = true;
                        try {
                            const data = await this.api(`/api/ai/artifacts/${artifact.id}/regenerate`, {method:'POST'});
                            this.appendArtifact(data.artifact);
                        } catch (error) { this.notice(error.message); }
                        finally { regenerate.disabled = false; }
                    });
                    card.appendChild(regenerate);
                }
            }
            (parent || this.messages).appendChild(card); this.scrollBottom();
        }

        appendVisualization(visualization, parent = null) {
            if (visualization?.type === 'quality_today_overview') {
                this.appendQualityVisualization(visualization, parent);
                return;
            }
            if (visualization?.type !== 'production_area_progress') return;
            const id = visualization.id || JSON.stringify([visualization.type, visualization.date_from, visualization.date_to, visualization.areas]);
            if (this.visualizationIds.has(id)) return;
            this.visualizationIds.add(id);

            const card = document.createElement('section');
            card.className = 'ai-production-chart';
            card.setAttribute('aria-label', this.t('lineProgressTitle'));

            const title = document.createElement('div');
            title.className = 'ai-production-chart-title';
            title.textContent = this.t('lineProgressTitle');
            const range = visualization.date_from === visualization.date_to
                ? visualization.date_from
                : `${visualization.date_from || ''} – ${visualization.date_to || ''}`;
            const meta = document.createElement('div');
            meta.className = 'ai-production-chart-meta';
            meta.textContent = `${range || ''}${visualization.source ? ` · ${this.t('source')}: ${visualization.source}` : ''}`;
            card.append(title, meta);

            (visualization.areas || []).forEach(area => {
                const section = document.createElement('div');
                section.className = 'ai-production-area';
                const heading = document.createElement('div');
                heading.className = 'ai-production-area-heading';
                const name = document.createElement('strong');
                name.textContent = area.area || '';
                const lines = document.createElement('span');
                lines.textContent = area.plans
                    ? `${this.formatNumber(area.active_lines)} ${this.t('activeLines')} · ${this.formatNumber(area.plans)} ${this.t('rows')}`
                    : this.t('noPlans');
                heading.append(name, lines);
                section.appendChild(heading);

                const goal = Number(area.goal || 0);
                const bars = [
                    {label:this.t('goal'), value:goal, pct:goal > 0 ? 100 : 0, kind:'goal'},
                    {label:this.t('produced'), value:Number(area.produced || 0), pct:Number(area.produced_pct || 0), kind:'produced'},
                    {label:this.t('output'), value:Number(area.output || 0), pct:Number(area.output_pct || 0), kind:'output'}
                ];
                bars.forEach(item => {
                    const row = document.createElement('div');
                    row.className = 'ai-production-bar-row';
                    const label = document.createElement('span');
                    label.className = 'ai-production-bar-label';
                    label.textContent = item.label;
                    const track = document.createElement('div');
                    track.className = 'ai-production-bar-track';
                    const fill = document.createElement('div');
                    fill.className = `ai-production-bar-fill ${item.kind}`;
                    fill.style.width = `${Math.max(0, Math.min(100, item.pct))}%`;
                    track.appendChild(fill);
                    const value = document.createElement('span');
                    value.className = 'ai-production-bar-value';
                    value.textContent = item.kind === 'goal'
                        ? this.formatNumber(item.value)
                        : `${this.formatNumber(item.value)} · ${item.pct.toFixed(1)}%`;
                    row.append(label, track, value);
                    section.appendChild(row);
                });

                const statuses = Object.entries(area.status_counts || {});
                if (statuses.length) {
                    const status = document.createElement('div');
                    status.className = 'ai-production-status';
                    status.textContent = statuses.map(([name, count]) => `${name}: ${this.formatNumber(count)}`).join(' · ');
                    section.appendChild(status);
                }
                card.appendChild(section);
            });

            if ((visualization.omitted_areas || []).length) {
                const omitted = document.createElement('div');
                omitted.className = 'ai-production-omitted';
                omitted.textContent = `${this.t('omittedAreas')}: ${visualization.omitted_areas.join(', ')}`;
                card.appendChild(omitted);
            }
            (parent || this.messages).appendChild(card);
            this.scrollBottom();
        }

        appendQualityVisualization(visualization, parent = null) {
            const id = visualization.id || JSON.stringify([visualization.type, visualization.date_from, visualization.sources]);
            if (this.visualizationIds.has(id)) return;
            this.visualizationIds.add(id);
            const sourceLabels = {
                lqc_results:'qualityLqcResults', ict_history:'qualityIct',
                lqc_release_history:'qualityLqcRelease', vision_history:'qualityVision'
            };
            const card = document.createElement('section'); card.className = 'ai-quality-overview';
            const title = document.createElement('div'); title.className = 'ai-quality-title'; title.textContent = this.t('qualityTitle');
            const meta = document.createElement('div'); meta.className = 'ai-quality-meta';
            meta.textContent = visualization.date_from === visualization.date_to
                ? visualization.date_from || ''
                : `${visualization.date_from || ''} – ${visualization.date_to || ''}`;
            card.append(title, meta);
            const grid = document.createElement('div'); grid.className = 'ai-quality-grid';
            (visualization.sources || []).forEach(source => {
                const panel = document.createElement('article'); panel.className = 'ai-quality-source';
                const heading = document.createElement('div'); heading.className = 'ai-quality-source-heading';
                const name = document.createElement('strong'); name.textContent = this.t(sourceLabels[source.key]) || source.label || source.key;
                const badge = document.createElement('span'); badge.className = 'ai-quality-badge';
                let metrics = [];
                if (source.key === 'lqc_results') {
                    badge.textContent = source.inspected ? this.t(source.within_target ? 'onTarget' : 'offTarget') : this.t('noActivity');
                    badge.classList.add(source.inspected ? (source.within_target ? 'good' : 'warning') : 'empty');
                    metrics = [['inspected', source.inspected], ['defects', source.defects], ['ppm', source.ppm], ['target', source.target_ppm]];
                } else if (source.key === 'lqc_release_history') {
                    badge.textContent = source.total ? `${this.formatNumber(source.total)} ${this.t('scans').toLowerCase()}` : this.t('noActivity');
                    badge.classList.add(source.total ? (source.duplicates ? 'warning' : 'good') : 'empty');
                    metrics = [['scans', source.total], ['uniqueUnits', source.unique_units], ['lots', source.lots], ['duplicates', source.duplicates]];
                } else {
                    badge.textContent = source.total ? `${Number(source.pass_rate_pct || 0).toFixed(1)}%` : this.t('noActivity');
                    badge.classList.add(source.total ? 'neutral' : 'empty');
                    metrics = [['tests', source.total], ['uniqueUnits', source.unique_units], ['passed', source.passed], ['failed', source.failed]];
                }
                heading.append(name, badge); panel.appendChild(heading);
                const metricGrid = document.createElement('div'); metricGrid.className = 'ai-quality-metrics';
                metrics.forEach(([key, value]) => {
                    const metric = document.createElement('div'); metric.className = 'ai-quality-metric';
                    const amount = document.createElement('strong'); amount.textContent = this.formatNumber(value || 0);
                    const label = document.createElement('span'); label.textContent = this.t(key);
                    metric.append(amount, label); metricGrid.appendChild(metric);
                });
                panel.appendChild(metricGrid);
                if (source.pass_rate_pct !== undefined && source.total) {
                    const rate = document.createElement('div'); rate.className = 'ai-quality-rate';
                    const rateLabel = document.createElement('span'); rateLabel.textContent = `${this.t('passRate')} · ${Number(source.pass_rate_pct || 0).toFixed(1)}%`;
                    const track = document.createElement('div'); track.className = 'ai-quality-rate-track';
                    const fill = document.createElement('div'); fill.className = 'ai-quality-rate-fill'; fill.style.width = `${Math.max(0, Math.min(100, Number(source.pass_rate_pct || 0)))}%`;
                    track.appendChild(fill); rate.append(rateLabel, track); panel.appendChild(rate);
                }
                grid.appendChild(panel);
            });
            card.appendChild(grid);
            if ((visualization.omitted_sources || []).length) {
                const omitted = document.createElement('div'); omitted.className = 'ai-quality-omitted';
                omitted.textContent = `${this.t('omittedSources')}: ${visualization.omitted_sources.map(key => this.t(sourceLabels[key]) || key).join(', ')}`;
                card.appendChild(omitted);
            }
            (parent || this.messages).appendChild(card); this.scrollBottom();
        }

        async uploadPlanFile(file) {
            const name = (file.name || '').toLowerCase();
            if (!name.endsWith('.xlsx') && !name.endsWith('.xlsm')) {
                this.notice('Solo .xlsx o .xlsm'); return;
            }
            if (!this.currentConversation) await this.newChat(false);
            if (!this.currentConversation) return;
            const info = this.root.querySelector('#ai-attach-info');
            const nameEl = this.root.querySelector('#ai-attach-name');
            nameEl.textContent = 'Subiendo ' + file.name + '...';
            info.hidden = false;
            try {
                const fd = new FormData();
                fd.append('file', file);
                const data = await this.api(
                    `/api/ai/conversations/${this.currentConversation.public_id}/upload`,
                    { method: 'POST', body: fd });
                this.pendingFileRef = data.file_ref;
                nameEl.textContent = '📎 ' + data.filename;
            } catch (error) {
                this.pendingFileRef = null;
                info.hidden = true;
                this.notice(error.message || 'No se pudo subir el archivo');
            }
        }

        clearAttachment() {
            this.pendingFileRef = null;
            this.root.querySelector('#ai-attach-info').hidden = true;
            this.root.querySelector('#ai-attach-name').textContent = '';
        }

        async send() {
            const content = this.input.value.trim();
            if (!content || this.streaming) return;
            if (!this.currentConversation) await this.newChat(false);
            if (!this.currentConversation) return;
            this.lastUserMessage = content;
            this.root.querySelector('#ai-retry').hidden = true;
            this.input.value = '';
            this.appendMessage('user', content);
            this.activeAssistantBubble = this.appendMessage('assistant', '');
            this.activeAssistantText = '';
            this.setStreaming(true, this.t('thinking'));
            this.startThinkingIndicator();
            this.controller = new AbortController();
            const clientId = crypto.randomUUID
                ? crypto.randomUUID()
                : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, char => {
                    const value = Math.random() * 16 | 0;
                    return (char === 'x' ? value : (value & 0x3) | 0x8).toString(16);
                });
            try {
                const response = await fetch(`/api/ai/conversations/${this.currentConversation.public_id}/messages/stream`, {
                    method:'POST', signal:this.controller.signal,
                    headers:{'Content-Type':'application/json','Accept':'text/event-stream','X-Requested-With':'XMLHttpRequest'},
                    body:JSON.stringify({content, client_message_id:clientId, language:this.language.value, page_context:this.pageContext(), file_ref:this.pendingFileRef || null})
                });
                if (!response.ok) {
                    const data = await response.json().catch(() => ({}));
                    throw new Error(data.error || response.statusText);
                }
                this.clearAttachment();
                await this.consumeSSE(response.body);
            } catch (error) {
                this.root.querySelector('#ai-retry').hidden = false;
                if (error.name !== 'AbortError') {
                    this.stopThinkingIndicator();
                    this.activeAssistantText = `${this.t('error')}: ${error.message}`;
                    this.renderMarkdown(this.activeAssistantBubble, this.activeAssistantText);
                    this.notice(error.message);
                }
            } finally {
                this.setStreaming(false);
                this.controller = null;
                await this.loadConversations().catch(() => {});
            }
        }

        async consumeSSE(stream) {
            const reader = stream.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const {value, done} = await reader.read();
                buffer += decoder.decode(value || new Uint8Array(), {stream:!done});
                const blocks = buffer.split(/\r?\n\r?\n/);
                buffer = blocks.pop() || '';
                for (const block of blocks) this.handleSSE(block);
                if (done) break;
            }
            if (buffer.trim()) this.handleSSE(buffer);
        }

        handleSSE(block) {
            let event = 'message'; const dataLines = [];
            block.split(/\r?\n/).forEach(line => {
                if (line.startsWith('event:')) event = line.slice(6).trim();
                if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
            });
            let data = {}; try { data = JSON.parse(dataLines.join('\n') || '{}'); } catch (_) { return; }
            if (event === 'delta') {
                this.stopThinkingIndicator();
                this.activeAssistantBubble.classList.add('ai-streaming-text');
                this.activeAssistantText += data.text || '';
                this.activeAssistantBubble.textContent = this.activeAssistantText;
                this.scrollBottom();
            }
            if (event === 'tool_start') {
                const label = data.name === 'create_artifact' ? this.t('generating') : this.t('consulting');
                this.stopThinkingIndicator(); this.showThinkingIndicator(label); this.setStatus(label);
            }
            if (event === 'tool_end') { this.showThinkingIndicator(this.t('reasoning')); this.setStatus(this.t('reasoning')); }
            if (event === 'artifact_start' || event === 'artifact_progress') { this.showThinkingIndicator(data.message || this.t('generating')); this.setStatus(data.message || this.t('generating')); }
            if (event === 'artifact_ready') this.appendArtifact(data, this.activeAssistantBubble?.parentElement);
            if (event === 'visualization') this.appendVisualization(data, this.activeAssistantBubble?.parentElement);
            if (event === 'artifact_error') { this.setStatus(''); this.notice(data.message || this.t('error')); }
            if (event === 'usage') this.updateUsage(data, this.bootstrap?.limits);
            if (event === 'error') {
                this.stopThinkingIndicator();
                this.activeAssistantText += `${this.activeAssistantText ? '\n' : ''}${this.t('error')}: ${data.message || ''}`;
                this.renderMarkdown(this.activeAssistantBubble, this.activeAssistantText);
            }
            if (event === 'done') { this.stopThinkingIndicator(); this.renderMarkdown(this.activeAssistantBubble, this.activeAssistantText); this.setStatus(''); }
        }

        stop() { this.controller?.abort(); this.stopThinkingIndicator(); if (this.activeAssistantBubble) this.renderMarkdown(this.activeAssistantBubble, this.activeAssistantText); this.setStreaming(false); this.root.querySelector('#ai-retry').hidden = !this.lastUserMessage; }
        retry() { if (!this.lastUserMessage || this.streaming) return; this.input.value = this.lastUserMessage; this.send(); }
        setStreaming(active, status = '') { this.streaming = active; this.root.querySelector('#ai-send').disabled = active; this.input.disabled = active; this.root.querySelector('#ai-stop').hidden = !active; this.setStatus(status); }
        setStatus(text) { const node = this.root.querySelector('#ai-stream-status'); node.textContent = text || ''; node.hidden = !text; }
        scrollBottom() { requestAnimationFrame(() => { this.messages.scrollTop = this.messages.scrollHeight; }); }
        updateUsage(usage = {}, limits = {}) { const used = Number(usage.input_tokens || 0) + Number(usage.output_tokens || 0); this.root.querySelector('#ai-usage-label').textContent = limits.daily_token_limit ? `${used.toLocaleString()} / ${Number(limits.daily_token_limit).toLocaleString()} tokens` : ''; }

        async loadAudit() {
            if (!this.bootstrap?.can_audit) return;
            const user = encodeURIComponent(this.root.querySelector('#ai-audit-user').value.trim());
            const data = await this.api(`/api/ai/audit/conversations?limit=100&username=${user}`);
            const list = this.root.querySelector('#ai-audit-list'); list.innerHTML = '';
            data.conversations.forEach(conversation => {
                const button = document.createElement('button'); button.type = 'button'; button.className = 'ai-list-item';
                button.innerHTML = `<div class="ai-list-title"></div><div class="ai-list-meta"></div>`;
                button.querySelector('.ai-list-title').textContent = `${conversation.username} · ${conversation.title}`;
                button.querySelector('.ai-list-meta').textContent = this.formatDate(conversation.updated_at);
                button.addEventListener('click', async () => {
                    const detail = await this.api(`/api/ai/audit/conversations/${conversation.public_id}/messages?limit=100`);
                    list.innerHTML = '';
                    detail.messages.forEach(message => {
                        const item = document.createElement('div'); item.className = 'ai-list-item'; item.textContent = `${message.role}: ${message.content}`; list.appendChild(item);
                    });
                });
                list.appendChild(button);
            });
        }

        async loadLimits() {
            if (!this.bootstrap?.can_manage_limits) return;
            const data = await this.api('/api/ai/audit/limits');
            const list = this.root.querySelector('#ai-limits-list'); list.innerHTML = '';
            data.limits.forEach(limit => {
                const item = document.createElement('div'); item.className = 'ai-list-item';
                item.textContent = `${limit.subject_type}:${limit.subject_key} · req ${limit.daily_request_limit ?? '-'} · tokens ${limit.daily_token_limit ?? '-'} · files ${limit.daily_artifact_limit ?? '-'}`;
                list.appendChild(item);
            });
        }

        async saveLimit(event) {
            event.preventDefault();
            const value = id => this.root.querySelector(id).value;
            await this.api('/api/ai/audit/limits', {method:'PATCH', body:{subject_type:value('#ai-limit-type'),subject_key:value('#ai-limit-key'),daily_request_limit:value('#ai-limit-requests') || null,daily_token_limit:value('#ai-limit-tokens') || null,daily_artifact_limit:value('#ai-limit-artifacts') || null}});
            await this.loadLimits();
        }

        formatDate(value) { if (!value) return ''; const date = new Date(String(value).replace(' ', 'T')); return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString(); }
        formatNumber(value) { const number = Number(value || 0); return Number.isFinite(number) ? number.toLocaleString(undefined, {maximumFractionDigits:2}) : '0'; }
        fileSize(value) { const bytes = Number(value || 0); if (bytes < 1024) return `${bytes} B`; if (bytes < 1048576) return `${(bytes/1024).toFixed(1)} KB`; return `${(bytes/1048576).toFixed(1)} MB`; }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const root = document.getElementById('ai-assistant-root');
        if (root) new MESAI(root).init();
    });
})();
