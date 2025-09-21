import { loginRequest } from "../services/auth.js";

export class AuthController {
  constructor(view) { this.view = view; }

  init() {
    this.view.wireEvents();

    // handler del submit
    this.view.on("submit", async ({ email, password }) => {
      try {
        this.view.disableSubmit(true);
        const res = await loginRequest(email, password);  // { ok:true } y cookie seteada
        if (res?.ok) {
          this.view.showFormMsg("¡Bienvenido!", "ok");
          // redirige al dashboard
          window.location.href = "index.html";
        } else {
          throw new Error("Respuesta inválida");
        }
      } catch (err) {
        this.view.showFormMsg(err.message || "Error de autenticación", "error");
      } finally {
        this.view.disableSubmit(false);
      }
    });
  }
}

