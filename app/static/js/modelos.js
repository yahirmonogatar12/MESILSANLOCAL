(() => {
  const RX = {
    table: (window.IX_BOOT && IX_BOOT.table) || "raw",
    columns: [], rows: [], total: 0,
    limit: 200, offset: 0, search: "",
    timer: null
  };

  const $ = (id) => document.getElementById(id);
  const fmt = (n) => new Intl.NumberFormat('es-MX').format(n);
  const debounce = (fn, t=300) => { let h; return (...a)=>{ clearTimeout(h); h=setTimeout(()=>fn(...a), t); }; };

  function setStatus(msg){ $("ix-status").textContent = msg || ""; }

  function render() {
    const thead = $("ix-thead");
    const tbody = $("ix-tbody");
    // header
    if (RX.columns.length) {
      thead.innerHTML = "<tr>" + RX.columns.map(c => `<th title="${c}">${c}</th>`).join("") + "</tr>";
    } else {
      thead.innerHTML = "<tr><th>Sin columnas</th></tr>";
    }
    // body
    if (!RX.rows.length) {
      tbody.innerHTML = `<tr><td colspan="${RX.columns.length||1}">Sin datos</td></tr>`;
    } else {
      tbody.innerHTML = RX.rows.map(r => {
        const tds = RX.columns.map(c => `<td>${r[c] ?? ""}</td>`).join("");
        return `<tr>${tds}</tr>`;
      }).join("");
    }
    $("ix-counter").textContent = `${fmt(RX.total)} filas`;
    $("ix-page").textContent = `${Math.floor(RX.offset / RX.limit) + 1}`;
  }

  async function fetchColumns() {
    const u = new URL(location.origin + "/api/columns");
    u.searchParams.set("table", RX.table);
    const res = await fetch(u);
    if (!res.ok) throw new Error("Error cargando columnas");
    const js = await res.json();
    RX.columns = js.columns || [];
  }

  async function fetchData() {
    const u = new URL(location.origin + "/api/data");
    u.searchParams.set("table", RX.table);
    u.searchParams.set("limit", RX.limit);
    u.searchParams.set("offset", RX.offset);
    if (RX.search) u.searchParams.set("search", RX.search);
    const t0 = performance.now();
    const res = await fetch(u);
    if (!res.ok) throw new Error("Error cargando datos");
    const js = await res.json();
    RX.rows = js.rows || []; RX.total = js.total || 0;
    RX.limit = js.limit || RX.limit; RX.offset = js.offset || RX.offset; RX.search = js.search || RX.search;
    const ms = Math.round(performance.now() - t0);
    setStatus(`Actualizado: ${new Date().toLocaleTimeString()} · ${fmt(RX.total)} filas · ${ms} ms`);
    render();
  }

  async function refreshAll(){
    try {
      setStatus("Cargando…");
      if (!RX.columns.length) await fetchColumns();
      await fetchData();
    } catch (e) {
      setStatus("Error: " + (e && e.message || e));
    }
  }

  $("ix-refresh").addEventListener("click", () => { RX.offset = 0; refreshAll(); });
  $("ix-limit").addEventListener("change", () => {
    RX.limit = parseInt($("ix-limit").value,10) || 200; RX.offset = 0; refreshAll();
  });
  $("ix-prev").addEventListener("click", () => {
    RX.offset = Math.max(0, RX.offset - RX.limit); refreshAll();
  });
  $("ix-next").addEventListener("click", () => {
    const next = RX.offset + RX.limit; if (next < RX.total) { RX.offset = next; refreshAll(); }
  });
  $("ix-search").addEventListener("input", debounce(e => {
    RX.search = e.target.value.trim(); RX.offset = 0; refreshAll();
  }, 300));
  $("ix-interval").addEventListener("change", () => {
    const ms = parseInt($("ix-interval").value,10) || 0;
    if (RX.timer) { clearInterval(RX.timer); RX.timer = null; }
    if (ms > 0) RX.timer = setInterval(refreshAll, ms);
  });

  // init
  (async function init(){
    const ms = parseInt($("ix-interval").value,10) || 0;
    if (ms > 0) RX.timer = setInterval(refreshAll, ms);
    await refreshAll();
  })();
})();
