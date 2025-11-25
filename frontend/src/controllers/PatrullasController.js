// frontend/src/controllers/PatrullasController.js
import { patrullasApi } from "../services/api.js";

export class PatrullasController {
  constructor() {
    this.state = { page: 1, size: 10, q: "" };

    // Tabla y controles de listado
    this.tbl = document.querySelector("#tblPatrullas tbody");
    this.txtSearch = document.querySelector("#txtSearch");
    this.selPageSize = document.querySelector("#selPageSize");
    this.btnPrev = document.querySelector("#btnPrev");
    this.btnNext = document.querySelector("#btnNext");
    this.lblPage = document.querySelector("#lblPage");
    this.btnCreate = document.querySelector("#btnCreate");

    // Modal / formulario
    this.dlg = document.querySelector("#dlgPatrulla");
    this.frm = document.querySelector("#frmPatrulla");
    this.fldId = document.querySelector("#fldId");
    this.fldCodigo = document.querySelector("#fldCodigo");
    this.fldAlias = document.querySelector("#fldAlias");
    this.fldPlaca = document.querySelector("#fldPlaca");
    this.fldActiva = document.querySelector("#fldActiva");
    this.btnSave = document.querySelector("#btnSave");
    this.btnCancel = document.querySelector("#btnCancel");

    // Toast (ya existe en la página)
    this.toast = document.querySelector("#toast");

    // Pequeño debounce para búsqueda
    this._searchTimer = null;
  }

  init() {
    this.load();

    // Buscar (debounce)
    this.txtSearch?.addEventListener("input", () => {
      clearTimeout(this._searchTimer);
      this._searchTimer = setTimeout(() => {
        this.state.q = this.txtSearch.value.trim();
        this.state.page = 1;
        this.load();
      }, 250);
    });

    // Paginación
    this.selPageSize?.addEventListener("change", () => {
      this.state.size = Number(this.selPageSize.value) || 10;
      this.state.page = 1;
      this.load();
    });

    this.btnPrev?.addEventListener("click", () => {
      if (this.state.page > 1) {
        this.state.page--;
        this.load();
      }
    });

    this.btnNext?.addEventListener("click", () => {
      this.state.page++;
      this.load();
    });

    // Crear
    this.btnCreate?.addEventListener("click", () => this.openDialog());

    // Guardar
    this.frm?.addEventListener("submit", (e) => {
      e.preventDefault();
      this.save();
    });

    // Cancelar
    this.btnCancel?.addEventListener("click", (e) => {
      e.preventDefault();
      this.dlg.close();
    });

    // Cerrar con ESC
    this.dlg?.addEventListener("keydown", (e) => {
      if (e.key === "Escape") this.dlg.close();
    });
  }

  async load() {
    try {
      const { items, page, total, size } = await patrullasApi.list(this.state);
      this.render(items, page, total, size);
    } catch (e) {
      console.error("Error al cargar patrullas:", e);
      this.tbl.innerHTML = `<tr><td colspan="6">Error cargando patrullas</td></tr>`;
      this.showToast("Error cargando patrullas", true);
    }
  }

  render(items, page, total, size) {
    if (!Array.isArray(items) || items.length === 0) {
      this.tbl.innerHTML = `<tr><td colspan="6" class="muted">Sin resultados</td></tr>`;
    } else {
      this.tbl.innerHTML = items
        .map(
          (p) => `
        <tr>
          <td>${this.escape(p.codigo)}</td>
          <td>${this.escape(p.alias) || "—"}</td>
          <td>${this.escape(p.placa) || "—"}</td>
          <td>${p.is_activa ? "Sí" : "No"}</td>
          <td>${p.created_at ? this.formatDate(p.created_at) : "—"}</td>
          <td class="actions">
            <button class="btn btn-sm" data-act="edit" data-id="${p.id}">Editar</button>
            <button class="btn btn-sm btn-danger" data-act="del" data-id="${p.id}">Eliminar</button>
          </td>
        </tr>`
        )
        .join("");
    }

    // Acciones por fila
    this.tbl.querySelectorAll("button[data-act]").forEach((btn) =>
      btn.addEventListener("click", (e) => {
        const id = e.currentTarget.dataset.id;
        const act = e.currentTarget.dataset.act;
        if (act === "edit") this.edit(id);
        if (act === "del") this.remove(id);
      })
    );

    // Paginación
    this.lblPage.textContent = `Página ${page}`;
    this.btnPrev.disabled = page <= 1;
    this.btnNext.disabled = page * size >= total;
  }

  async edit(id) {
    try {
      const p = await patrullasApi.get(id);
      this.openDialog(p);
    } catch (e) {
      console.error("Error obteniendo patrulla:", e);
      this.showToast("No se pudo cargar la patrulla", true);
    }
  }

  openDialog(p = null) {
    // Rellena formulario
    this.fldId.value = p?.id || "";
    this.fldCodigo.value = p?.codigo || "";
    this.fldCodigo.disabled = !!p; // no editable al actualizar
    this.fldAlias.value = p?.alias || "";
    this.fldPlaca.value = p?.placa || "";
    this.fldActiva.checked = p?.is_activa ?? true;

    // Título
    document.querySelector("#dlgTitle").textContent = p ? "Editar Patrulla" : "Nueva Patrulla";

    // Abre modal y enfoca
    this.dlg.showModal();
    setTimeout(() => {
      if (p) this.fldAlias.focus();
      else this.fldCodigo.focus();
    }, 10);
  }

  async save() {
    // Validación simple
    if (!this.fldCodigo.value.trim()) {
      this.fldCodigo.focus();
      this.showToast("El código es requerido", true);
      return;
    }

    const id = this.fldId.value;
    const payload = {
      codigo: this.fldCodigo.value.trim(),
      alias: this.fldAlias.value.trim(),
      placa: this.fldPlaca.value.trim(),
      is_activa: this.fldActiva.checked,
    };

    // Estado de carga en el botón
    const prevText = this.btnSave.textContent;
    this.btnSave.disabled = true;
    this.btnSave.textContent = "Guardando…";

    try {
      if (id) {
        await patrullasApi.update(id, payload);
        this.showToast("Patrulla actualizada");
      } else {
        await patrullasApi.create(payload);
        this.showToast("Patrulla creada");
      }
      this.dlg.close();
      // Mantiene filtros / página actuales
      this.load();
    } catch (e) {
      console.error("Error guardando patrulla:", e);
      const msg = e?.message || "Error al guardar";
      this.showToast(msg, true);
    } finally {
      this.btnSave.disabled = false;
      this.btnSave.textContent = prevText;
    }
  }

  async remove(id) {
    if (!confirm("¿Eliminar esta patrulla?")) return;
    try {
      await patrullasApi.remove(id);
      this.showToast("Patrulla eliminada");
      this.load();
    } catch (e) {
      console.error("Error eliminando patrulla:", e);
      this.showToast("No se pudo eliminar", true);
    }
  }

  // ===== utilidades =====
  showToast(msg, isError = false) {
    if (!this.toast) return;
    this.toast.textContent = msg;
    this.toast.dataset.type = isError ? "error" : "ok";
    this.toast.hidden = false;
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      this.toast.hidden = true;
    }, 2000);
  }

  formatDate(value) {
    try {
      return new Date(value).toLocaleString();
    } catch {
      return "—";
    }
  }

  escape(s) {
    return (s ?? "").toString().replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }
}
