
import { DashboardView } from "../views/DashboardView.js";
import { fetchUbicaciones } from "../services/api.js";

export class DashboardController {
  constructor() {
    this.view = new DashboardView();

    
    this.refreshInterval = null;
    this.pollMs = 5000; // refresco cada 5s (ajustable en caliente)
    this._running = false;
    this._isFirstLoad = true;

    
    this._onBeforeUnload = this.destroy.bind(this);
    this._onVisibilityChange = this._handleVisibility.bind(this);
    this._onSetPollMs = this._handleSetPollMs.bind(this);
  }

  async init() {
    // I...mapa ..vista
    this.view.initMap();

    
    await this.loadData();

    // Refresco periódico
    this._startPolling();

   
    document.addEventListener("visibilitychange", this._onVisibilityChange);

    
    // window.dispatchEvent(new CustomEvent('dashboard:setPollMs', { detail: 10000 }))
    window.addEventListener("dashboard:setPollMs", this._onSetPollMs);

    // Limpieza  la pestaña
    window.addEventListener("beforeunload", this._onBeforeUnload);
  }

  destroy() {
    this._stopPolling();
    window.removeEventListener("beforeunload", this._onBeforeUnload);
    document.removeEventListener("visibilitychange", this._onVisibilityChange);
    window.removeEventListener("dashboard:setPollMs", this._onSetPollMs);
  }

 
  _startPolling() {
    if (this.refreshInterval) clearInterval(this.refreshInterval);
    this._running = true;
    this.refreshInterval = setInterval(() => this.loadData(), this.pollMs);
  }

  _stopPolling() {
    this._running = false;
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  _handleVisibility() {
    
    if (document.hidden) {
      this._stopPolling();
    } else {
      this.loadData();
      if (!this._running) this._startPolling();
    }
  }

  _handleSetPollMs(e) {
    const ms = Number(e?.detail);
    if (!Number.isFinite(ms) || ms < 1000) return; // mínimo 1s por seguridad
    this.pollMs = ms;
    if (this._running) this._startPolling(); 
  }

  
  async loadData() {
    try {
      const ubicaciones = await fetchUbicaciones();

      // KPIs básicos
      const total      = ubicaciones.length;
      const activas    = ubicaciones.filter(u => (u.estado || "").toLowerCase() === "activa").length;
      const inactivas  = Math.max(total - activas, 0);
      const ultima     = total
        ? (ubicaciones[0].ts ? new Date(ubicaciones[0].ts).toLocaleString() : "—")
        : "—";

      this.view.updateKpis({ total, activas, ultima });

      // Renderiza mapa + tabla
      
      this.view.updateMap(ubicaciones, { isFirstLoad: this._isFirstLoad });
      this.view.updateTable(ubicaciones);

      // Snapshot para otros módulos (si lo necesitas)
      window.dispatchEvent(
        new CustomEvent("dashboard:snapshot", {
          detail: { total, activas, inactivas, ultima, ubicaciones }
        })
      );

     
      this._isFirstLoad = false;

    } catch (err) {
      console.error("Error cargando ubicaciones:", err);
      this.view.showError("No se pudieron cargar ubicaciones");
     
    }
  }
}
