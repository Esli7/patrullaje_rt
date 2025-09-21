import { DashboardView } from "../views/DashboardView.js";
import { fetchUbicaciones } from "../services/api.js";

export class DashboardController {
  constructor() {
    this.view = new DashboardView();
    this.refreshInterval = null;
    this.pollMs = 5000; // refresco cada 5s
  }

  async init() {
    this.view.initMap();
    await this.loadData();
    this.refreshInterval = setInterval(() => this.loadData(), this.pollMs);
  }

  async loadData() {
    try {
      const ubicaciones = await fetchUbicaciones(); // ← usa tu api.js

      // KPIs
      const total = ubicaciones.length;
      const activas = ubicaciones.filter(u => u.estado?.toLowerCase() === "activa").length;
      const ultima = ubicaciones.length ? (ubicaciones[0].ts ? new Date(ubicaciones[0].ts).toLocaleString() : "—") : "—";

      this.view.updateKpis({ total, activas, ultima });

      // Renderiza
      this.view.updateMap(ubicaciones);
      this.view.updateTable(ubicaciones);

    } catch (err) {
      console.error("Error cargando ubicaciones:", err);
      this.view.showError("No se pudieron cargar ubicaciones");
    }
  }
}
