/* Control de maquinas de calidad (stations_qa).
 * CRUD AJAX para la tabla MySQL stations_qa.
 */
(function () {
  "use strict";

  const STYLESHEET_ID = "stations-qa-css";
  const STYLESHEET_HREF = "/static/css/stations_qa.css?v=20260609d";
  const API_BASE = "/api/control_calidad/stations_qa";

  let records = [];

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

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function getElements(root) {
    return {
      root,
      filters: root.querySelector("#stqa-filters"),
      search: root.querySelector("#stqa-search"),
      typeFilter: root.querySelector("#stqa-type-filter"),
      clear: root.querySelector("#stqa-clear"),
      exportBtn: root.querySelector("#stqa-export"),
      refresh: root.querySelector("#stqa-refresh"),
      create: root.querySelector("#stqa-new"),
      loading: root.querySelector("#stqa-loading"),
      tbody: root.querySelector("#stqa-tbody"),
      total: root.querySelector("#stqa-total"),
      active: root.querySelector("#stqa-active"),
      inactive: root.querySelector("#stqa-inactive"),
      formPanel: root.querySelector("#stqa-form-panel"),
      form: root.querySelector("#stqa-form"),
      formTitle: root.querySelector("#stqa-form-title"),
      id: root.querySelector("#stqa-id"),
      code: root.querySelector("#stqa-code"),
      name: root.querySelector("#stqa-name"),
      type: root.querySelector("#stqa-type"),
      host: root.querySelector("#stqa-host"),
      activeInput: root.querySelector("#stqa-active-input"),
      cancel: root.querySelector("#stqa-cancel"),
      cancelBottom: root.querySelector("#stqa-cancel-bottom"),
    };
  }

  function notify(message, type) {
    const old = document.querySelector(".stqa-toast");
    if (old) old.remove();
    const toast = document.createElement("div");
    toast.className = `stqa-toast stqa-toast--${type || "info"}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 4200);
  }

  function setLoading(elements, loading) {
    if (elements.loading) elements.loading.hidden = !loading;
    elements.root.classList.toggle("is-loading", loading);
    elements.root.querySelectorAll("button, input, select").forEach((el) => {
      if (elements.formPanel && !elements.formPanel.hidden && elements.formPanel.contains(el)) {
        return;
      }
      el.disabled = loading;
    });
  }

  async function fetchJson(url, options) {
    const headers = {
      "Content-Type": "application/json",
      ...(options && options.headers ? options.headers : {}),
    };
    const response = await fetch(url, {
      credentials: "same-origin",
      ...(options || {}),
      headers,
    });
    const text = await response.text();
    let payload = {};
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch (error) {
        payload = {};
      }
    }
    if (!response.ok || payload.success === false) {
      throw new Error(payload.error || `Solicitud fallida (${response.status})`);
    }
    return payload;
  }

  function buildListUrl(elements, base) {
    const params = new URLSearchParams();
    const q = elements.search.value.trim();
    const stationType = elements.typeFilter.value;
    if (q) params.set("q", q);
    if (stationType) params.set("station_type", stationType);
    const query = params.toString();
    return `${base || API_BASE}${query ? `?${query}` : ""}`;
  }

  function updateStats(elements) {
    const active = records.filter((item) => item.is_active).length;
    const inactive = records.length - active;
    elements.total.textContent = String(records.length);
    elements.active.textContent = String(active);
    elements.inactive.textContent = String(inactive);
  }

  function rowActions(row) {
    const nextTitle = row.is_active ? "Desactivar" : "Activar";
    const nextIcon = row.is_active ? "bi-toggle-on" : "bi-toggle-off";
    return `
      <div class="stqa-row-actions">
        <button class="stqa-icon-btn" type="button" title="Editar" aria-label="Editar ${esc(row.station_code)}" data-action="edit" data-id="${row.id}">
          <i class="bi bi-pencil" aria-hidden="true"></i>
        </button>
        <button class="stqa-icon-btn" type="button" title="${nextTitle}" aria-label="${nextTitle} ${esc(row.station_code)}" data-action="toggle" data-id="${row.id}">
          <i class="bi ${nextIcon}" aria-hidden="true"></i>
        </button>
        <button class="stqa-icon-btn stqa-danger" type="button" title="Eliminar" aria-label="Eliminar ${esc(row.station_code)}" data-action="delete" data-id="${row.id}">
          <i class="bi bi-trash" aria-hidden="true"></i>
        </button>
      </div>
    `;
  }

  function renderTable(elements) {
    updateStats(elements);
    if (!records.length) {
      elements.tbody.innerHTML = '<tr><td colspan="7" class="stqa-empty">Sin estaciones registradas</td></tr>';
      return;
    }
    elements.tbody.innerHTML = records
      .map((row) => {
        const statusClass = row.is_active ? "stqa-status--active" : "stqa-status--inactive";
        const statusText = row.is_active ? "Activa" : "Inactiva";
        return `
          <tr>
            <td>${esc(row.host_name || "-")}</td>
            <td><span class="stqa-code">${esc(row.station_code)}</span></td>
            <td>${esc(row.station_name)}</td>
            <td><span class="stqa-type">${esc(row.station_type)}</span></td>
            <td><span class="stqa-status ${statusClass}">${statusText}</span></td>
            <td>${esc(row.updated_at_utc || "-")}</td>
            <td>${rowActions(row)}</td>
          </tr>
        `;
      })
      .join("");
  }

  async function loadStations(elements) {
    setLoading(elements, true);
    try {
      const payload = await fetchJson(buildListUrl(elements));
      records = payload.records || [];
      renderTable(elements);
    } catch (error) {
      records = [];
      renderTable(elements);
      notify(error.message || "No fue posible cargar las estaciones.", "error");
    } finally {
      setLoading(elements, false);
    }
  }

  function resetForm(elements) {
    elements.id.value = "";
    elements.code.value = "";
    elements.name.value = "";
    elements.type.value = "ICT";
    elements.host.value = "";
    elements.activeInput.checked = true;
  }

  function openForm(elements, record) {
    resetForm(elements);
    if (record) {
      elements.formTitle.textContent = "Editar estacion";
      elements.id.value = String(record.id);
      elements.code.value = record.station_code || "";
      elements.name.value = record.station_name || "";
      elements.type.value = record.station_type || "ICT";
      elements.host.value = record.host_name || "";
      elements.activeInput.checked = Boolean(record.is_active);
    } else {
      elements.formTitle.textContent = "Nueva estacion";
    }
    elements.formPanel.hidden = false;
    elements.code.focus();
  }

  function closeForm(elements) {
    resetForm(elements);
    elements.formPanel.hidden = true;
  }

  function formPayload(elements) {
    return {
      station_code: elements.code.value.trim(),
      station_name: elements.name.value.trim(),
      station_type: elements.type.value,
      host_name: elements.host.value.trim(),
      is_active: elements.activeInput.checked,
    };
  }

  async function saveStation(elements) {
    const stationId = elements.id.value.trim();
    const payload = formPayload(elements);
    const method = stationId ? "PUT" : "POST";
    const url = stationId ? `${API_BASE}/${encodeURIComponent(stationId)}` : API_BASE;

    await fetchJson(url, {
      method,
      body: JSON.stringify(payload),
    });
    notify(stationId ? "Estacion actualizada." : "Estacion creada.", "success");
    closeForm(elements);
    await loadStations(elements);
  }

  function findRecord(id) {
    const numericId = Number(id);
    return records.find((item) => Number(item.id) === numericId);
  }

  async function toggleStation(elements, record) {
    const nextActive = !record.is_active;
    const actionText = nextActive ? "activar" : "desactivar";
    if (!confirm(`Desea ${actionText} la estacion ${record.station_code}?`)) return;
    await fetchJson(`${API_BASE}/${encodeURIComponent(record.id)}/active`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: nextActive }),
    });
    notify(nextActive ? "Estacion activada." : "Estacion desactivada.", "success");
    await loadStations(elements);
  }

  async function deleteStation(elements, record) {
    if (!confirm(`Eliminar la estacion ${record.station_code}? Esta accion no se puede deshacer.`)) return;
    await fetchJson(`${API_BASE}/${encodeURIComponent(record.id)}`, {
      method: "DELETE",
    });
    notify("Estacion eliminada.", "success");
    await loadStations(elements);
  }

  function bindEvents(elements) {
    elements.filters.addEventListener("submit", (event) => {
      event.preventDefault();
      loadStations(elements);
    });

    elements.typeFilter.addEventListener("change", () => loadStations(elements));
    elements.clear.addEventListener("click", () => {
      elements.search.value = "";
      elements.typeFilter.value = "";
      loadStations(elements);
    });
    elements.refresh.addEventListener("click", () => loadStations(elements));
    elements.exportBtn.addEventListener("click", () => {
      window.open(buildListUrl(elements, `${API_BASE}/export`), "_blank");
    });
    elements.create.addEventListener("click", () => openForm(elements));

    elements.cancel.addEventListener("click", () => closeForm(elements));
    elements.cancelBottom.addEventListener("click", () => closeForm(elements));
    elements.formPanel.addEventListener("click", (event) => {
      if (event.target === elements.formPanel) closeForm(elements);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !elements.formPanel.hidden) closeForm(elements);
    });
    elements.form.addEventListener("submit", (event) => {
      event.preventDefault();
      saveStation(elements).catch((error) => notify(error.message, "error"));
    });

    elements.tbody.addEventListener("click", (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      const record = findRecord(button.dataset.id);
      if (!record) {
        notify("La estacion ya no esta en la lista. Actualiza el modulo.", "error");
        return;
      }
      if (button.dataset.action === "edit") {
        openForm(elements, record);
      } else if (button.dataset.action === "toggle") {
        toggleStation(elements, record).catch((error) => notify(error.message, "error"));
      } else if (button.dataset.action === "delete") {
        deleteStation(elements, record).catch((error) => notify(error.message, "error"));
      }
    });
  }

  function inicializarStationsQA(root) {
    ensureStylesheet();
    const moduleRoot = typeof root === "string" ? document.querySelector(root) : root;
    if (!moduleRoot || moduleRoot.dataset.initialized === "true") return;
    moduleRoot.dataset.initialized = "true";
    const elements = getElements(moduleRoot);
    bindEvents(elements);
    loadStations(elements);
  }

  window.inicializarStationsQA = inicializarStationsQA;
  document.querySelectorAll("#stqa-module").forEach(inicializarStationsQA);
})();
