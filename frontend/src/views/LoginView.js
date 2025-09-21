export class LoginView {
  constructor(cfg){
    this.form = document.querySelector(cfg.form);
    this.email = document.querySelector(cfg.email);
    this.password = document.querySelector(cfg.password);
    this.submitBtn = document.querySelector(cfg.submitBtn);
    this.formMsg = document.querySelector(cfg.formMsg);
    this.fieldErrorSelector = cfg.fieldErrorSelector;
    this.listeners = {};
  }

  on(evt, cb){ this.listeners[evt] = cb; }

  showFieldError(inputEl, msg){
    const wrap = inputEl.closest(".field");
    const small = wrap?.querySelector(`${this.fieldErrorSelector}[data-for="${inputEl.id}"]`);
    if (small) small.textContent = msg || "";
  }

  showFormMsg(msg, type="error"){
    this.formMsg.textContent = msg || "";
    this.formMsg.style.color = (type === "ok") ? "#86efac" : "#fca5a5";
  }

  disableSubmit(disabled=true){ this.submitBtn.disabled = !!disabled; }

  getValues(){ return { email: this.email.value.trim(), password: this.password.value }; }

  clearMessages(){
    this.showFieldError(this.email, "");
    this.showFieldError(this.password, "");
    this.showFormMsg("");
  }

  wireEvents(){
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/; // simple y suficiente
    const validateInstant = () => {
      const { email, password } = this.getValues();
      const eValid = emailRegex.test(email);
      const pValid = password.length >= 6 && password.length <= 72;
      this.disableSubmit(!(eValid && pValid));
      this.showFieldError(this.email, (!eValid && email) ? "Ingresa un email válido" : "");
      this.showFieldError(this.password, (!pValid && password) ? "Mín. 6, máx. 72 caracteres" : "");
    };

    ["input","blur"].forEach(ev=>{
      this.email.addEventListener(ev, validateInstant);
      this.password.addEventListener(ev, validateInstant);
    });

    this.form.addEventListener("submit", (e)=>{
      e.preventDefault();
      this.clearMessages();
      const cb = this.listeners["submit"];
      if (cb) cb(this.getValues());
    });

    this.disableSubmit(true);
  }
}
