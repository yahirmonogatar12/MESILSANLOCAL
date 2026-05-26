// Modulo Control de squeegee.
// Extraido desde el <script> inline del template AJAX (2026-05-26).
// Datos hardcoded (placeholder): el backend real esta fuera de scope; cuando
// se decida persistirlos, sustituir SQ_DATA_DEMO por fetch('/api/squeegee').

(function () {
    const STYLESHEET_ID_SQ = "control-squeegee-css";
    const STYLESHEET_HREF_SQ = "/static/css/control_squeegee.css?v=20260526a";

    function ensureModuleStyles() {
        const cur = document.getElementById(STYLESHEET_ID_SQ);
        if (cur) {
            if (!cur.getAttribute("href")?.includes("20260526a")) {
                cur.setAttribute("href", STYLESHEET_HREF_SQ);
            }
            return;
        }
        const link = document.createElement("link");
        link.id = STYLESHEET_ID_SQ;
        link.rel = "stylesheet";
        link.href = STYLESHEET_HREF_SQ;
        document.head.appendChild(link);
    }

    const SQ_DATA_DEMO = [
        { codigo: "SQ-001", tipo: "Metálico",    material: "Acero",    dureza: "80 Shore A", estado: "Activo",        ultimoUso: "2024-01-15" },
        { codigo: "SQ-002", tipo: "Poliuretano", material: "PU",       dureza: "75 Shore A", estado: "Activo",        ultimoUso: "2024-01-16" },
        { codigo: "SQ-003", tipo: "Híbrido",     material: "Acero+PU", dureza: "78 Shore A", estado: "Mantenimiento", ultimoUso: "2024-01-10" },
    ];

    function sqMostrarCargando() {
        const m = document.getElementById("sq-modal-carga");
        if (m) m.style.display = "flex";
    }

    function sqOcultarCargando() {
        const m = document.getElementById("sq-modal-carga");
        if (m) m.style.display = "none";
    }

    function sqRenderizar(rows) {
        const tbody = document.getElementById("sq-cuerpo-tabla");
        if (!tbody) return;
        tbody.innerHTML = rows.map(sq => `
            <tr>
                <td>${sq.codigo}</td>
                <td>${sq.tipo}</td>
                <td>${sq.material}</td>
                <td>${sq.dureza}</td>
                <td><span class="sq-estado-${sq.estado.toLowerCase().replace(" ", "-")}">${sq.estado}</span></td>
                <td>${sq.ultimoUso}</td>
                <td><button class="sq-btn-accion" data-codigo="${sq.codigo}">Ver</button></td>
            </tr>
        `).join("");
        const c = document.getElementById("sq-total");
        if (c) c.textContent = rows.length;
    }

    function sqConsultar() {
        const inicio = document.getElementById("sq-fecha-inicio")?.value;
        const fin    = document.getElementById("sq-fecha-fin")?.value;
        if (!inicio || !fin) {
            alert("Por favor selecciona ambas fechas");
            return;
        }
        sqMostrarCargando();
        setTimeout(() => {
            sqRenderizar(SQ_DATA_DEMO);
            sqOcultarCargando();
        }, 600);
    }

    function sqInitListeners() {
        const root = document.getElementById("control-squeegee-unique-container");
        if (!root) return;
        if (root.dataset.sqInit === "1") return;
        root.dataset.sqInit = "1";

        const btn = document.getElementById("sq-btn-consultar");
        if (btn && !btn._sqBound) {
            btn.addEventListener("click", sqConsultar);
            btn._sqBound = true;
        }
        // Delegacion para los botones Ver
        root.addEventListener("click", function (e) {
            const t = e.target;
            if (t && t.classList && t.classList.contains("sq-btn-accion")) {
                alert("Ver detalle de squeegee: " + (t.dataset.codigo || ""));
            }
        });

        // Defaults de fecha
        const hoy = new Date().toISOString().split("T")[0];
        const fi = document.getElementById("sq-fecha-inicio"); if (fi && !fi.value) fi.value = hoy;
        const ff = document.getElementById("sq-fecha-fin");    if (ff && !ff.value) ff.value = hoy;

        sqConsultar();
    }

    window.initControlSqueegee = function () {
        ensureModuleStyles();
        sqInitListeners();
    };

    window.destroyControlSqueegee = function () {
        const root = document.getElementById("control-squeegee-unique-container");
        if (root) root.dataset.sqInit = "0";
    };

    // Auto-init para carga directa (no AJAX)
    const doInit = () => {
        if (document.getElementById("control-squeegee-unique-container")) {
            try { window.initControlSqueegee(); } catch (e) { console.warn("initControlSqueegee error", e); }
        }
    };
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", doInit);
    } else {
        doInit();
    }
})();
