// frontend/src/views/DashboardView.js
export class DashboardView {
  constructor() {
    // ---- KPI y tabla
    this.kpiTotal   = document.querySelector("#kpiTotal");
    this.kpiActivas = document.querySelector("#kpiActivas");
    this.kpiUltima  = document.querySelector("#kpiUltima");
    this.tbody      = document.querySelector("#tblUbicaciones tbody");

    // 👇 Filtro y exportación de Ubicaciones
    this.ubiRange   = document.querySelector("#ubiRange");
    this.btnUbicCSV = document.querySelector("#btnExportUbicCSV");
    this.allRows    = []; // cache de todas las filas recibidas

    if (this.ubiRange) {
      this.ubiRange.addEventListener("change", () => this.renderTableFiltered());
    }
    if (this.btnUbicCSV) {
      this.btnUbicCSV.addEventListener("click", () => this.exportCurrentUbicacionesCSV());
    }

    // ---- Mapa
    this.mapEl   = document.querySelector("#map");
    this.map     = null;
    this.markers = new Map();          // key -> L.Marker (pulsante)
    this.accCircles = new Map();       // key -> L.Circle (accuracy)
    this.pulseLayer = null;            // capa para marcadores pulsantes
    this.pulsePane  = "pulsePane";     // pane por encima de markers por defecto
    this._firstFrame = true;           // controla el primer encuadre
    this.lastBounds = [];              // guarda los últimos puntos para reencuadre

    // ---- Donut (Chart.js)
    this.donutCanvas = document.getElementById("donutActivas"); // puede no existir aún
    this.donutChart  = null;

    // Colores (tomados de CSS vars con fallback seguros)
    this.COLOR_ACTIVAS   = cssVar("--ok", "#22c55e");
    this.COLOR_INACTIVAS = cssVar("--inactive", "#334155");

    // Color principal para el pulso (rojo)
    this.COLOR_PULSE = "#ef4444";
  }

  /* ======================= MAPA ======================= */
  initMap() {
    if (this.map || !this.mapEl) return;

    // Capas base
    const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 19,
    });
    const cartoDark = L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      { attribution: "&copy; OpenStreetMap &copy; CARTO", maxZoom: 20 }
    );
    const esriSat = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { attribution: "Tiles &copy; Esri", maxZoom: 19 }
    );

    this.map = L.map(this.mapEl, {
      center: [14.6349, -90.5069],
      zoom: 12,
      layers: [osm],
      zoomControl: true,
    });

    // Pane para los marcadores pulsantes (encima de markers normales)
    this.map.createPane(this.pulsePane);
    this.map.getPane(this.pulsePane).style.zIndex = 650; // > 600 (marker pane)

    // Capa para los pulsantes
    this.pulseLayer = L.layerGroup().addTo(this.map);

    // Control de capas base
    const baseLayers = { "OSM Claro": osm, "Carto Oscuro": cartoDark, "Satélite Esri": esriSat };
    L.control.layers(baseLayers, {}, { position: "topright", collapsed: true }).addTo(this.map);

    // Regla de escala
    L.control.scale({ imperial: false }).addTo(this.map);

    // Asegurar tamaño correcto y reencuadre cuando el layout termina
    this.map.whenReady(() => requestAnimationFrame(() => this._refreshAndReframe()));
    osm.on("load", () => this._refreshAndReframe());
    this.map.on("layeradd", () => this._refreshAndReframe());

    // Redimensionado de ventana
    window.addEventListener("resize", () => this._refreshAndReframe());

    // Observa cambios de tamaño del contenedor (panel, fullscreen, etc.)
    try {
      const wrap = this.mapEl.closest(".map-wrap") || this.mapEl;
      const ro = new ResizeObserver(() => this._refreshAndReframe());
      ro.observe(wrap);
      this._resizeObserver = ro;
    } catch (_) {}

    // Reencuadre cuando vuelve a ser visible (por si estaba en display:none)
    try {
      const io = new IntersectionObserver((entries) => {
        for (const e of entries) {
          if (e.isIntersecting) this._refreshAndReframe();
        }
      }, { threshold: 0.1 });
      io.observe(this.mapEl);
      this._visibilityObserver = io;
    } catch (_) {}

    // Exponer referencia global (fullscreen toggle)
    try { window.__leaflet_map = this.map; } catch (_) {}
  }

  _refreshAndReframe() {
    this.refreshSize();
    if (this.lastBounds.length) {
      // doble diferido para esperar paddings/transiciones del panel
      requestAnimationFrame(() => {
        this.autoFrame(this.lastBounds);
        setTimeout(() => this.autoFrame(this.lastBounds), 80);
      });
    }
  }

  refreshSize() {
    if (this.map && typeof this.map.invalidateSize === "function") {
      this.map.invalidateSize(true);
    }
  }

  /**
   * Encadra y centra los puntos de forma inteligente.
   * - 1 punto: setView con zoom cómodo (16–18).
   * - 2+ puntos: fit/fly bounds con padding.
   * - Siguientes renders: sólo fly si algo quedó fuera; si no, recentra suavemente.
   */
  autoFrame(boundsArray) {
    if (!this.map || !boundsArray.length) return;

    const pad  = [60, 60];
    const maxZ = 17;

    if (boundsArray.length === 1) {
      const target = boundsArray[0];
      const desired = Math.min(18, Math.max(16, this.map.getZoom() || 16));
      this.map.setView(target, desired, { animate: true });
      return;
    }

    const all = L.latLngBounds(boundsArray);

    if (this._firstFrame) {
      this._firstFrame = false;
      this.map.fitBounds(all, { padding: pad, maxZoom: maxZ });
      return;
    }

    const safeView = this.map.getBounds().pad(-0.10); // 10% margen interior
    if (!safeView.contains(all)) {
      this.map.flyToBounds(all, { padding: pad, maxZoom: maxZ, duration: 0.6 });
      return;
    }

    // Todo cabe: ajústalo suavemente al centro
    this.map.panInsideBounds(all, { paddingTopLeft: pad, paddingBottomRight: pad });
    const center = all.getCenter();
    if (this.map.getCenter().distanceTo(center) > 50) {
      this.map.panTo(center, { animate: true, duration: 0.5 });
    }
  }

  /**
   * Crea un icono div con el HTML de la sirena pulsante.
   * Requiere las clases CSS definidas en index.html (pulse-icon / pulse-marker / ring / dot).
   */
  makePulsingIcon(color = this.COLOR_PULSE) {
    return L.divIcon({
      className: "pulse-icon",
      html: `<div class="pulse-marker" style="--pulse-color:${color}">
               <span class="ring"></span><span class="dot"></span>
             </div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    });
  }

  updateMap(rows) {
    if (!this.map) return;

    const seen = new Set();
    const seenAcc = new Set();
    const bounds = [];

    rows.forEach(r => {
      if (typeof r.lat !== "number" || typeof r.lng !== "number") return;

      const key = String(r.id ?? r.patrulla ?? `${r.lat},${r.lng}`);
      seen.add(key);

      const latlng = [r.lat, r.lng];
      const color = this.COLOR_PULSE;

      let m = this.markers.get(key);
      if (!m) {
        m = L.marker(latlng, {
          icon: this.makePulsingIcon(color),
          pane: this.pulsePane,
          zIndexOffset: 999,
        }).addTo(this.pulseLayer);
        this.markers.set(key, m);
      } else {
        m.setLatLng(latlng).setIcon(this.makePulsingIcon(color));
      }

      m.bindPopup(
        `<strong>${escapeHtml(r.patrulla ?? "Patrulla")}</strong><br/>
         ${fmtNum(r.lat)}, ${fmtNum(r.lng)}<br/>
         ${r.ts ? new Date(r.ts).toLocaleString() : ""}`
      );

      bounds.push(latlng);

      if (typeof r.accuracy === "number" && r.accuracy > 0) {
        let c = this.accCircles.get(key);
        if (!c) {
          c = L.circle(latlng, {
            radius: r.accuracy,
            color: this.COLOR_ACTIVAS,
            weight: 1,
            fillColor: this.COLOR_ACTIVAS,
            fillOpacity: 0.12,
          }).addTo(this.map);
          this.accCircles.set(key, c);
        } else {
          c.setLatLng(latlng).setRadius(r.accuracy);
        }
        seenAcc.add(key);
      }
    });

    // limpiar marcadores/círculos viejos
    for (const [key, marker] of this.markers.entries()) {
      if (!seen.has(key)) { this.pulseLayer.removeLayer(marker); this.markers.delete(key); }
    }
    for (const [key, circle] of this.accCircles.entries()) {
      if (!seenAcc.has(key)) { this.map.removeLayer(circle); this.accCircles.delete(key); }
    }

    if (bounds.length) {
      this.lastBounds = bounds.slice();

      // Diferido: evita encuadrar antes de que el contenedor tenga su tamaño final
      requestAnimationFrame(() => {
        this.refreshSize();
        this.autoFrame(this.lastBounds);
        // respaldo por si el panel aún está animándose
        setTimeout(() => this.autoFrame(this.lastBounds), 80);
      });
    } else {
      this.lastBounds = [];
    }
  }

  /* ======================== KPIs ====================== */
  updateKpis({ total, activas, ultima }) {
    this.kpiTotal.textContent   = total ?? "—";
    this.kpiActivas.textContent = activas ?? "—";
    this.kpiUltima.textContent  = ultima ?? "—";

    const t = toInt(total);
    const a = toInt(activas);
    const inactivas = Math.max(0, t - a);
    this.updateDonut(a, inactivas);
  }

  /* ======================= TABLA ====================== */
  // Recibe todas las filas crudas y aplica el filtro seleccionado
  updateTable(rows) {
    this.allRows = Array.isArray(rows) ? rows.slice() : [];
    this.renderTableFiltered();
  }

  // Calcula el filtro temporal y re-pinta la tabla
  renderTableFiltered() {
    if (!this.tbody) return;

    const val = (this.ubiRange && this.ubiRange.value) ? this.ubiRange.value : "24h";
    const since = msFromRange(val); // epoch en ms o null

    const rows = (!since)
      ? this.allRows
      : this.allRows.filter(r => {
          const t = new Date(r.ts ?? r.updated_at ?? r.created_at).getTime();
          return Number.isFinite(t) && t >= since;
        });

    this.tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${escapeHtml(r.patrulla ?? "-")}</td>
        <td>${fmtNum(r.lat)}</td>
        <td>${fmtNum(r.lng)}</td>
        <td>${escapeHtml(r.estado ?? "-")}</td>
        <td>${fmtDate(r.ts ?? r.updated_at ?? r.created_at)}</td>
      </tr>
    `).join("");
  }

  // Exporta a CSV lo que esté actualmente filtrado en la tabla
  exportCurrentUbicacionesCSV() {
    // reutiliza el mismo filtrado que la tabla
    const val = (this.ubiRange && this.ubiRange.value) ? this.ubiRange.value : "24h";
    const since = msFromRange(val);

    const rows = (!since)
      ? this.allRows
      : this.allRows.filter(r => {
          const t = new Date(r.ts ?? r.updated_at ?? r.created_at).getTime();
          return Number.isFinite(t) && t >= since;
        });

    const header = ["Patrulla","Lat","Lng","Estado","Actualizado"];
    const lines = [header.map(csvEscape).join(",")];

    for (const r of rows) {
      lines.push([
        csvEscape(r.patrulla ?? "-"),
        csvEscape(typeof r.lat === "number" ? r.lat : ""),
        csvEscape(typeof r.lng === "number" ? r.lng : ""),
        csvEscape(r.estado ?? ""),
        csvEscape(fmtDate(r.ts ?? r.updated_at ?? r.created_at))
      ].join(","));
    }

    const csvContent = "\uFEFF" + lines.join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    const name = `ubicaciones_${val}.csv`;
    a.href = url; a.download = name; a.click();
    URL.revokeObjectURL(url);
  }

  /* ======================= DONUT ====================== */
  ensureDonutCanvas() {
    if (this.donutCanvas) return this.donutCanvas;
    const kpis = document.querySelector(".kpis");
    if (!kpis) return null;

    const card = document.createElement("div");
    card.className = "kpi";
    card.innerHTML = `
      <div class="kpi__label">Activas vs inactivas</div>
      <div style="display:flex;align-items:center;justify-content:center">
        <canvas id="donutActivas" width="140" height="140"></canvas>
      </div>
    `;
    kpis.appendChild(card);

    this.donutCanvas = card.querySelector("#donutActivas");
    return this.donutCanvas;
  }

  updateDonut(activas = 0, inactivas = 0) {
    const canvas = this.ensureDonutCanvas();
    if (!canvas || typeof window.Chart === "undefined") return;

    const data = [toInt(activas), toInt(inactivas)];
    if (this.donutChart) { this.donutChart.destroy(); this.donutChart = null; }

    this.donutChart = new window.Chart(canvas, {
      type: "doughnut",
      data: {
        labels: ["Activas", "Inactivas"],
        datasets: [{
          data,
          backgroundColor: [this.COLOR_ACTIVAS, this.COLOR_INACTIVAS],
          hoverBackgroundColor: [this.COLOR_ACTIVAS, this.COLOR_INACTIVAS],
          borderColor: cssVar("--panel", "#121a2a"),
          borderWidth: 2,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 12, usePointStyle: true } },
          tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.raw}` } }
        }
      }
    });
  }

  /* ======================= OTROS ====================== */
  showError(msg) { console.warn(msg); }
}

/* ------------ helpers ------------ */
function fmtNum(n) { return typeof n === "number" ? n.toFixed(5) : "—"; }
function fmtDate(ts){
  if (!ts) return "—";
  const d = new Date(ts);
  return Number.isFinite(d.getTime()) ? d.toLocaleString() : "—";
}
function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;");
}
function toInt(x) { const n = Number(x); return Number.isFinite(n) ? Math.trunc(n) : 0; }
function cssVar(name, fallback = "") {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}
// Escapa valores para CSV
function csvEscape(val){
  const s = String(val ?? "").replace(/"/g,'""');
  return `"${s}"`;
}

// Convierte el valor del select a un "desde" (epoch-ms).
// "1h", "6h", "24h", "7d", "30d" o "all" (null = sin filtro)
function msFromRange(val) {
  const now = Date.now();
  switch ((val || "").toLowerCase()) {
    case "1h":  return now - 1  * 60 * 60 * 1000;
    case "6h":  return now - 6  * 60 * 60 * 1000;
    case "24h": return now - 24 * 60 * 60 * 1000;
    case "7d":  return now - 7  * 24 * 60 * 60 * 1000;
    case "30d": return now - 30 * 24 * 60 * 60 * 1000;
    case "all":
    default:    return null;
  }
}
