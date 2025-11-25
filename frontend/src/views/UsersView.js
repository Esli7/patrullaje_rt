// frontend/src/views/UsersView.js

// ===== Helpers seguros para <dialog> (soportan UA sin showModal/close) =====
function openDialogSafe(dlg) {
  if (!dlg) return;

  if (typeof dlg.showModal === "function") {
    try {
      dlg.showModal();
      dlg.querySelector("input,select,textarea,button")?.focus();
      document.body.classList.add("has-modal");
      return;
    } catch (e) {
      console.debug("[UsersView] showModal() falló, se usa fallback:", e);
    }
  }

  dlg.setAttribute("open", "");
  Object.assign(dlg.style, {
    display: "block",
    position: "fixed",
    inset: "0",
    margin: "auto",
    zIndex: "1001",
  });

  const overlay = document.createElement("div");
  overlay.dataset.role = "dlg-overlay";
  Object.assign(overlay.style, {
    position: "fixed",
    inset: "0",
    background: "rgba(0,0,0,.55)",
    zIndex: "1000",
  });
  overlay.addEventListener("click", () => closeDialogSafe(dlg));
  document.body.appendChild(overlay);
  dlg._overlay = overlay;

  dlg.querySelector("input,select,textarea,button")?.focus();
  dlg._onKeydownEsc = (ev) => { if (ev.key === "Escape") closeDialogSafe(dlg); };
  document.addEventListener("keydown", dlg._onKeydownEsc);
  document.body.classList.add("has-modal");
}

function closeDialogSafe(dlg) {
  if (!dlg) return;
  if (typeof dlg.close === "function") { try { dlg.close(); } catch {} }
  dlg.removeAttribute("open");
  ["display","position","inset","margin","z-index"].forEach(p => dlg.style.removeProperty(p));
  if (dlg._overlay) { dlg._overlay.remove(); dlg._overlay = null; }
  if (dlg._onKeydownEsc) { document.removeEventListener("keydown", dlg._onKeydownEsc); dlg._onKeydownEsc = null; }
  document.body.classList.remove("has-modal");
}

// ===== Helpers de rol/permisos =====
function getRoleFromGlobals() {
  const bodyRole = document?.body?.dataset?.role;
  if (bodyRole) return bodyRole;
  const cu = (window.CURRENT_USER && window.CURRENT_USER.role) || null;
  if (cu) return cu;
  const cu2 = (window.__currentUser && window.__currentUser.role) || null;
  if (cu2) return cu2;
  const cu3 = (window.__ME && window.__ME.role) || null;
  if (cu3) return cu3;
  return "user";
}

function computePerms() {
  const role = getRoleFromGlobals();
  return { role, create: role === "admin", edit: role === "admin", del: role === "admin" };
}

/** Devuelve el rol a mostrar en la fila (usa role_display si existe) */
function userRole(u) {
  if (typeof u?.role_display === "string" && u.role_display.trim()) {
    return u.role_display.trim();
  }
  if (Array.isArray(u?.roles) && u.roles.length) {
    return u.roles.join(", ");
  }
  if (u?.role) return String(u.role);

  const me = (window.CURRENT_USER) || (window.__currentUser) || (window.__ME) || null;
  if (me) {
    const sameById = (u?.id != null && me.id != null && String(u.id) === String(me.id));
    const sameByEmail = (u?.email && me.email && String(u.email).toLowerCase() === String(me.email).toLowerCase());
    if ((sameById || sameByEmail) && me.role) return String(me.role);
  }
  return "—";
}

// ==========================================================================

export class UsersView {
  constructor() {
    this.perms = computePerms();

    // lista
    this.$tbody       = document.querySelector("#tblUsers tbody");
    this.$lblPage     = document.querySelector("#lblPage");
    this.$btnPrev     = document.querySelector("#btnPrev");
    this.$btnNext     = document.querySelector("#btnNext");
    this.$selPageSize = document.querySelector("#selPageSize");
    this.$txtSearch   = document.querySelector("#txtSearch");
    this.$btnCreate   = document.querySelector("#btnCreate");

    // modal
    this.$dlg         = document.querySelector("#dlgUser");
    this.$frm         = document.querySelector("#frmUser");
    this.$dlgTitle    = document.querySelector("#dlgTitle");
    this.$fldId       = document.querySelector("#fldId");
    this.$fldEmail    = document.querySelector("#fldEmail");
    this.$fldNombre   = document.querySelector("#fldNombre");  // NUEVO
    this.$fldNip      = document.querySelector("#fldNip");     // NUEVO
    this.$fldPassword = document.querySelector("#fldPassword");
    this.$pwdHint     = document.querySelector("#pwdHint");
    this.$fldRole     = document.querySelector("#fldRole");     // select (si existe en tu HTML)
    this.$fldActive   = document.querySelector("#fldActive");
    this.$btnCancel   = document.querySelector("#btnCancel");
    this.$btnSave     = document.querySelector("#btnSave");

    // toast
    this.$toast       = document.querySelector("#toast");

    this._applyPermsToCreateBtn();
    window.addEventListener("role-change", () => {
      this.perms = computePerms();
      this._applyPermsToCreateBtn();
    });
  }

  _applyPermsToCreateBtn() {
    if (!this.$btnCreate) return;
    const canCreate = !!this.perms.create;
    this.$btnCreate.disabled = !canCreate;
    this.$btnCreate.title = canCreate ? "" : "Solo administradores pueden crear usuarios";
  }

  // Firma: un solo callback (ev, payload)
  on(callback) {
    // listado
    this.$btnPrev?.addEventListener("click", (e) => { e.preventDefault(); callback("prev"); });
    this.$btnNext?.addEventListener("click", (e) => { e.preventDefault(); callback("next"); });
    this.$selPageSize?.addEventListener("change", () => callback("size", this.$selPageSize.value));
    this.$txtSearch?.addEventListener("input", () => callback("search", this.$txtSearch.value.trim()));

    // nuevo usuario
    this.$btnCreate?.addEventListener("click", (e) => {
      e.preventDefault();
      this.perms = computePerms();
      if (!this.perms.create) { this.toast("Necesitas rol administrador para crear usuarios"); return; }
      callback("open-create");
    });

    // submit del modal
    this.$frm?.addEventListener("submit", (e) => {
      e.preventDefault();
      const id        = this.$fldId.value || null;
      const email     = this.$fldEmail.value.trim();
      const nombre    = this.$fldNombre?.value.trim() || ""; // NUEVO
      const nip       = this.$fldNip?.value.trim() || "";    // NUEVO
      const password  = this.$fldPassword.value;             // vacío permitido en edición
      const role      = (this.$fldRole?.value || "user");
      const is_active = !!this.$fldActive.checked;

      if (!email) { this.toast("Email requerido"); return; }
      if (!id && !password) { this.toast("La contraseña es obligatoria"); return; }

      // Incluimos nombre y nip en el payload sin romper compat
      callback("save", { id, email, nombre, nip, password, is_active, role }); // NUEVO
    });

    // cancelar modal
    this.$btnCancel?.addEventListener("click", (e) => { e.preventDefault(); this.closeModal(); });
  }

  renderList({ items, page, size, total }) {
    this.perms = computePerms();
    this._applyPermsToCreateBtn();

    const esc = (s) => String(s ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
    const fmt = (iso) => { try { return new Date(iso).toLocaleString(); } catch { return iso || "—"; } };
    const btn = (label, act, id, disabled, extraClass = "") =>
      `<button class="btn ${extraClass}" data-act="${act}" data-id="${id}" ${disabled ? "disabled" : ""}>${label}</button>`;

    this.$tbody.innerHTML = (items || []).map(u => {
      const canEdit = this.perms.edit;
      const canDel  = this.perms.del;
      return `
        <tr>
          <td>${u.id}</td>
          <td>${esc(u.email)}</td>
          <td>${esc(u.nombre ?? "—")}</td>   <!-- NUEVO -->
          <td>${esc(u.nip ?? "—")}</td>      <!-- NUEVO -->
          <td>${esc(userRole(u))}</td>       <!-- rol -->
          <td>${u.is_active ? "Sí" : "No"}</td>
          <td>${u.created_at ? fmt(u.created_at) : "—"}</td>
          <td>
            <div class="actions" style="display:flex; gap:6px">
              ${btn("Ver",    "view", u.id, false)}
              ${btn("Editar", "edit", u.id, !canEdit)}
              ${btn("Eliminar","del", u.id, !canDel, "btn-danger")}
            </div>
          </td>
        </tr>
      `;
    }).join("") || `<tr><td colspan="8" class="muted">No hay resultados</td></tr>`; // ajustado a 8 columnas

    this.$tbody.querySelectorAll("button[data-act]")?.forEach(btnEl => {
      btnEl.addEventListener("click", () => {
        const id  = btnEl.getAttribute("data-id");
        const act = btnEl.getAttribute("data-act");
        if (act === "edit" && !this.perms.edit)  { this.toast("Solo administradores pueden editar");  return; }
        if (act === "del"  && !this.perms.del)   { this.toast("Solo administradores pueden eliminar"); return; }
        this._emitRowAction?.(act, id);
      });
    });

    const pages = Math.max(1, Math.ceil((total || 0) / (size || 10)));
    this.$lblPage.textContent = `Página ${page} de ${pages} — ${total ?? 0} usuarios`;
    this.$btnPrev.disabled = page <= 1;
    this.$btnNext.disabled = page >= pages;
  }

  onRowAction(handler) { this._emitRowAction = handler; }

  openCreate() {
    if (!this.$dlg) { alert("No se encontró el diálogo #dlgUser"); return; }
    this.perms = computePerms();
    if (!this.perms.create) { this.toast("Solo administradores pueden crear usuarios"); return; }

    this.$dlgTitle.textContent = "Nuevo usuario";
    this.$fldId.value = "";
    this.$fldEmail.value = "";
    this.$fldNombre && (this.$fldNombre.value = ""); // NUEVO
    this.$fldNip && (this.$fldNip.value = "");       // NUEVO
    this.$fldPassword.value = "";
    this.$pwdHint.textContent = "(requerida)";
    if (this.$fldRole) this.$fldRole.value = "user";
    this.$fldActive.checked = true;

    this.$fldEmail.disabled = false;
    this.$fldNombre && (this.$fldNombre.disabled = false); // NUEVO
    this.$fldNip && (this.$fldNip.disabled = false);       // NUEVO
    this.$fldPassword.disabled = false;
    this.$fldActive.disabled = false;
    if (this.$fldRole) this.$fldRole.disabled = false;
    if (this.$btnSave) this.$btnSave.disabled = false;

    this._showModal();
  }

  openEdit(user) {
    if (!this.$dlg) { alert("No se encontró el diálogo #dlgUser"); return; }
    this.perms = computePerms();

    this.$dlgTitle.textContent = `Editar usuario #${user.id}`;
    this.$fldId.value = user.id;
    this.$fldEmail.value = user.email || "";
    this.$fldNombre && (this.$fldNombre.value = user.nombre || ""); // NUEVO
    this.$fldNip && (this.$fldNip.value = user.nip || "");          // NUEVO
    this.$fldPassword.value = "";
    this.$pwdHint.textContent = "(deja vacío para no cambiar)";
    if (this.$fldRole) this.$fldRole.value = user.role || (Array.isArray(user.roles) && user.roles[0]) || "user";
    this.$fldActive.checked = !!user.is_active;

    const ro = !this.perms.edit;
    this.$fldEmail.disabled = ro;
    this.$fldNombre && (this.$fldNombre.disabled = ro); // NUEVO
    this.$fldNip && (this.$fldNip.disabled = ro);       // NUEVO
    this.$fldPassword.disabled = ro;
    this.$fldActive.disabled = ro;
    if (this.$fldRole) this.$fldRole.disabled = ro;
    if (this.$btnSave) this.$btnSave.disabled = ro;

    this._showModal();
  }

  closeModal() { closeDialogSafe(this.$dlg); }

  toast(msg) {
    if (!this.$toast) { alert(msg); return; }
    this.$toast.textContent = msg;
    this.$toast.hidden = false;
    clearTimeout(this._t);
    this._t = setTimeout(() => { this.$toast.hidden = true; }, 2500);
  }

  get pageSize() { return parseInt(this.$selPageSize?.value, 10) || 10; }
  set pageSize(v) { if (this.$selPageSize) this.$selPageSize.value = String(v); }
  set search(v)   { if (this.$txtSearch) this.$txtSearch.value = v || ""; }

  _showModal() { openDialogSafe(this.$dlg); }
}
