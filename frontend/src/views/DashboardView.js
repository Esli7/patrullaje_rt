export class DashboardView {
  constructor() {
    this.kpiTotal   = document.querySelector("#kpiTotal");
    this.kpiActivas = document.querySelector("#kpiActivas");
    this.kpiUltima  = document.querySelector("#kpiUltima");
    this.tbody      = document.querySelector("#tblUbicaciones tbody");
    this.mapEl      = document.querySelector("#map");
    this.map        = null;
    this.markers    = new Map();
  }

  initMap() {
    if (this.map) return;
    this.map = L.map(this.mapEl).setView([14.6349, -90.5069], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 19,
    }).addTo(this.map);
  }

  updateKpis({ total, activas, ultima }) {
    this.kpiTotal.textContent   = total ?? "—";
    this.kpiActivas.textContent = activas ?? "—";
    this.kpiUltima.textContent  = ultima ?? "—";
  }

  updateTable(rows) {
    this.tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${escapeHtml(r.patrulla ?? "-")}</td>
        <td>${fmtNum(r.lat)}</td>
        <td>${fmtNum(r.lng)}</td>
        <td>${escapeHtml(r.estado ?? "-")}</td>
        <td>${r.ts ? new Date(r.ts).toLocaleString() : "—"}</td>
      </tr>
    `).join("");
  }

  updateMap(rows) {
    if (!this.map) return;
    const seen = new Set();
    const bounds = [];

    rows.forEach(r => {
      if (typeof r.lat !== "number" || typeof r.lng !== "number") return;
      const key = String(r.id ?? r.patrulla);
      seen.add(key);

      let m = this.markers.get(key);
      const latlng = [r.lat, r.lng];

      if (!m) {
        m = L.marker(latlng).addTo(this.map);
        this.markers.set(key, m);
      } else {
        m.setLatLng(latlng);
      }
      m.bindPopup(`<strong>${escapeHtml(r.patrulla ?? "Patrulla")}</strong><br/>
                   ${fmtNum(r.lat)}, ${fmtNum(r.lng)}<br/>
                   ${r.ts ? new Date(r.ts).toLocaleString() : ""}`);

      bounds.push(latlng);
    });

    // remover viejos
    for (const [key, marker] of this.markers.entries()) {
      if (!seen.has(key)) {
        this.map.removeLayer(marker);
        this.markers.delete(key);
      }
    }

    if (bounds.length) this.map.fitBounds(bounds, { padding: [20,20] });
  }

  showError(msg) {
    console.warn(msg);
  }
}

function fmtNum(n) {
  return typeof n === "number" ? n.toFixed(5) : "—";
}
function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;");
}
