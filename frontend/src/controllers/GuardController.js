import { me, logout } from "../services/session.js";

function detectRole(u) {
  if (u?.role) return u.role;
  if (Array.isArray(u?.roles) && u.roles.length) return u.roles[0];
  if (typeof u?.is_admin === "boolean") return u.is_admin ? "admin" : "user";
  return "user";
}

export class GuardController {
  constructor({
    btnLogoutSel = "#btnLogout",
    userEmailSel = "#userEmail",
    userRoleSel = null,      // NUEVO (opcional) -> pinta el rol
    usersLinkSel = null,     // NUEVO (opcional) -> oculta link si no es admin
    requireAdmin = false,
  } = {}) {
    this.btnLogout = document.querySelector(btnLogoutSel);
    this.userEmailEl = document.querySelector(userEmailSel);
    this.userRoleEl  = userRoleSel ? document.querySelector(userRoleSel) : null;
    this.usersLinkEl = usersLinkSel ? document.querySelector(usersLinkSel) : null;

    this.requireAdmin = requireAdmin;
    this.user = null;
  }

  isAdmin() { return this.user?.role === "admin"; }
  hasRole(r) {
    if (!this.user) return false;
    if (this.user.role === r) return true;
    if (Array.isArray(this.user.roles)) return this.user.roles.includes(r);
    return false;
  }

  _applyRoleGuards() {
    const isAdmin = this.isAdmin();

    document.querySelectorAll("[data-admin-only]").forEach(el => {
      if (!isAdmin) { el.style.display = "none"; el.setAttribute("aria-hidden","true"); }
      else { el.style.removeProperty("display"); el.removeAttribute("aria-hidden"); }
    });

    document.querySelectorAll("[data-admin-disable]").forEach(el => {
      if (!isAdmin) { if ("disabled" in el) el.disabled = true; el.setAttribute("aria-disabled","true"); }
      else { if ("disabled" in el) el.disabled = false; el.removeAttribute("aria-disabled"); }
    });

    // rol en body (útil para CSS/JS condicional)
    const role = this.user?.role || "user";
    document.body.dataset.role = role;
    document.body.classList.remove("role-admin","role-user");
    document.body.classList.add(`role-${role}`);

    // pinta rol en cabecera si corresponde
    if (this.userRoleEl) {
      this.userRoleEl.textContent = role;
    }

    // oculta link Usuarios si no es admin (si se configuró)
    if (this.usersLinkEl) {
      if (!isAdmin) this.usersLinkEl.style.display = "none";
      else this.usersLinkEl.style.removeProperty("display");
    }
  }

  async ensureAuth() {
    try {
      const u = await me(); // /api/auth/me

      if (this.userEmailEl && u?.email) this.userEmailEl.textContent = u.email;

      const role = detectRole(u);
      this.user = {
        id: u?.id,
        email: u?.email,
        role,
        is_admin: !!u?.is_admin,
        roles: Array.isArray(u?.roles) ? u.roles : [],
      };
      window.CURRENT_USER = this.user;

      this._applyRoleGuards();

      if (this.requireAdmin && this.user.role !== "admin") {
        window.location.href = "index.html";
      }
    } catch {
      window.location.href = "login.html";
    }
  }

  wireLogout() {
    this.btnLogout?.addEventListener("click", async () => {
      try { await logout(); } finally { window.location.href = "login.html"; }
    });
  }

  async init() {
    await this.ensureAuth();
    this.wireLogout();
  }
}
