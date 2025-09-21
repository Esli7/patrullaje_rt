import { me, logout } from "../services/session.js";

export class GuardController {
  constructor({ btnLogoutSel = "#btnLogout", userEmailSel = "#userEmail" } = {}){
    this.btnLogout = document.querySelector(btnLogoutSel);
    this.userEmailEl = document.querySelector(userEmailSel);
  }

  async ensureAuth(){
    try{
      const user = await me(); // llama /auth/me con credentials: 'include'
      if (this.userEmailEl && user?.email) {
        this.userEmailEl.textContent = user.email;
      }
    }catch(e){
      // No autenticado → login
      window.location.href = "login.html";
    }
  }

  wireLogout(){
    this.btnLogout?.addEventListener("click", async ()=>{
      try{ await logout(); } finally {
        window.location.href = "login.html";
      }
    });
  }

  async init(){
    await this.ensureAuth();
    this.wireLogout();
  }
}
