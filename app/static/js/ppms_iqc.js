/* PPM's IQC.
 * WF_004: garantiza CSS persistente propio si el template se carga por AJAX.
 */
(function () {
  "use strict";

  const STYLESHEET_ID = "ppms-iqc-css";
  const STYLESHEET_HREF = "/static/css/ppms_iqc.css?v=20260605a";

  function ensureStylesheet() {
    const existing = document.getElementById(STYLESHEET_ID);
    if (existing) {
      if (existing.getAttribute("href") !== STYLESHEET_HREF) {
        existing.setAttribute("href", STYLESHEET_HREF);
      }
      return;
    }
    const link = document.createElement("link");
    link.id = STYLESHEET_ID;
    link.rel = "stylesheet";
    link.href = STYLESHEET_HREF;
    document.head.appendChild(link);
  }

  function inicializarPPMsIQC(root) {
    ensureStylesheet();
    const moduleRoot = typeof root === "string" ? document.querySelector(root) : root;
    if (!moduleRoot || moduleRoot.dataset.initialized === "true") return;
    moduleRoot.dataset.initialized = "true";
  }

  window.inicializarPPMsIQC = inicializarPPMsIQC;
  document.querySelectorAll("#ppms-iqc-module").forEach(inicializarPPMsIQC);
})();
