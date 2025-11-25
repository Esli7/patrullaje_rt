// frontend/src/controllers/UsersController.js
import { usersApi } from "../services/users.api.js";

export class UsersController {
  constructor() {
    const { UsersView } = window._UsersViewCache || {};
    this.view = UsersView ? new UsersView() : null;
    this._deb = null;

    // Estado básico
    this.state = { page: 1, size: 10, q: "", total: 0, items: [] };
  }

  async init() {
    if (!this.view) {
      const mod = await import("../views/UsersView.js");
      this.view = new mod.UsersView();
    }

    // Tamaño de página inicial desde la vista (si lo expone)
    this.state.size = Number(this.view.pageSize || 10);

    // Enlaces de eventos de la vista
    this.view.on((ev, payload) => {
      if (ev === "prev") this.changePage(this.state.page - 1);
      if (ev === "next") this.changePage(this.state.page + 1);
      if (ev === "size") {
        this.state.size = parseInt(payload, 10) || 10;
        this.state.page = 1;
        this.load();
      }
      if (ev === "search") {
        this.state.q = payload || "";
        this.state.page = 1;
        this.loadDebounced();
      }
      if (ev === "open-create") this.view.openCreate();

      // payload puede venir como:
      // { id,email,nombre,nip,password,is_active, role }
      // o { id,email,nombre,nip,password,is_active, roles: [] }
      if (ev === "save") this.save(payload);
    });

    this.view.onRowAction((act, id) => this.rowAction(act, id));

    // Exponer un refresco global (útil si otro script quiere refrescar la tabla)
    window.__usersRefresh = this.load.bind(this);

    // Primera carga
    this.load();
  }

  loadDebounced() {
    clearTimeout(this._deb);
    this._deb = setTimeout(() => this.load(), 300);
  }

  async load() {
    const { page, size, q } = this.state;
    try {
      const res = await usersApi.list({ page, size, q });
      const items = res.items ?? res.data ?? [];
      const total = res.total ?? items.length;

      this.state.items = items;
      this.state.total = total;

      this.view.renderList({ items, page, size, total });
    } catch (err) {
      if (err?.code === 401) return this.handleAuthError();
      console.error("[UsersController.load]", err);
      this.view.toast(`Error cargando: ${err.message || err}`);
      this.view.renderList({ items: [], page: 1, size: this.state.size, total: 0 });
    }
  }

  async changePage(p) {
    if (p < 1) return;
    const maxPage = Math.max(1, Math.ceil(this.state.total / this.state.size));
    if (p > maxPage) return;
    this.state.page = p;
    await this.load();
  }

  async rowAction(act, id) {
    if (act === "view" || act === "edit") {
      try {
        const raw = await usersApi.get(id);
        const u = raw?.user ?? raw?.data ?? raw;
        if (!u || u.id == null) {
          this.view.toast("No se pudo obtener el usuario");
          return;
        }

        // Normaliza roles para la vista
        const roles = Array.isArray(u.roles) ? u.roles : (u.role ? [u.role] : []);
        const prefilled = { ...u, roles };

        if (act === "view") {
          this.view.openEdit(prefilled);
          // Si la vista tiene métodos/props para deshabilitar campos, respétalos
          this.view.$fldEmail && (this.view.$fldEmail.disabled = true);
          this.view.$fldNombre && (this.view.$fldNombre.disabled = true); // NUEVO
          this.view.$fldNip && (this.view.$fldNip.disabled = true);       // NUEVO
          this.view.$fldPassword && (this.view.$fldPassword.disabled = true);
          this.view.$fldActive && (this.view.$fldActive.disabled = true);
          this.view.$fldRole && (this.view.$fldRole.disabled = true); // compat select
          this.view.$btnSave && (this.view.$btnSave.disabled = true);
          this.view.setFormDisabled?.(true); // compat opcional (checkboxes)
        } else {
          this.view.openEdit(prefilled);
          this.view.$fldEmail && (this.view.$fldEmail.disabled = false);
          this.view.$fldNombre && (this.view.$fldNombre.disabled = false); // NUEVO
          this.view.$fldNip && (this.view.$fldNip.disabled = false);       // NUEVO
          this.view.$fldPassword && (this.view.$fldPassword.disabled = false);
          this.view.$fldActive && (this.view.$fldActive.disabled = false);
          this.view.$fldRole && (this.view.$fldRole.disabled = false);
          this.view.$btnSave && (this.view.$btnSave.disabled = false);
          this.view.setFormDisabled?.(false);
        }
      } catch (err) {
        if (err?.code === 401) return this.handleAuthError();
        this.view.toast(`Error obteniendo: ${err.message}`);
      }
      return;
    }

    if (act === "del") {
      if (!confirm(`¿Eliminar usuario #${id}?`)) return;
      try {
        await usersApi.remove(id);
        this.view.toast("Usuario eliminado");
        if (this.state.items.length === 1 && this.state.page > 1) this.state.page -= 1;
        this.load();
      } catch (err) {
        if (err?.code === 401) return this.handleAuthError();
        this.view.toast(`Error eliminando: ${err.message}`);
      }
    }
  }

  async save(payload) {
    // Normaliza roles: acepta roles[] o role string
    const roles =
      Array.isArray(payload?.roles) ? payload.roles
      : (payload?.role ? [payload.role] : undefined);

    // Extrae también nombre y nip
    const { id, email, nombre, nip, password, is_active } = payload || {};

    try {
      if (id) {
        // UPDATE
        const body = { email, is_active };
        if (nombre !== undefined) body.nombre = nombre; // NUEVO
        if (nip !== undefined) body.nip = nip;          // NUEVO
        if (password) body.password = password;
        if (roles !== undefined) body.roles = roles;

        await usersApi.update(id, body);
        this.view.toast("Usuario actualizado");
      } else {
        // CREATE
        if (!password) {
          this.view.toast("La contraseña es obligatoria");
          return;
        }
        const body = { email, password, is_active };
        if (nombre !== undefined) body.nombre = nombre; // NUEVO
        if (nip !== undefined) body.nip = nip;          // NUEVO
        if (roles !== undefined) body.roles = roles;

        await usersApi.create(body);
        this.view.toast("Usuario creado");
      }
      this.view.closeModal?.();
      this.load();
    } catch (err) {
      if (err?.code === 401) return this.handleAuthError();
      this.view.toast(`Error guardando: ${err.message}`);
    }
  }

  handleAuthError() {
    window.location.href = "login.html";
  }
}
