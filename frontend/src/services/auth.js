// frontend/src/services/auth.js

// Normaliza la BASE para que SIEMPRE apunte a /api del backend
const rawBase = (window.API_BASE_URL || "http://localhost:5000").replace(/\/+$/, "");
const BASE = rawBase.endsWith("/api") ? rawBase : `${rawBase}/api`;

/* ===========================================================
   Helper: refresh (reintento único para evitar tormenta)
   =========================================================== */
let refreshing = null;
async function runRefresh() {
  if (!refreshing) {
    refreshing = fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json" },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error("refresh failed");
        const data = await r.json().catch(() => ({}));
        // Guardamos el nuevo access_token si viene (modo Bearer híbrido)
        if (data?.access_token) localStorage.setItem("access_token", data.access_token);
        return data;
      })
      .finally(() => (refreshing = null));
  }
  return refreshing;
}

/* ===========================================================
   Helper: fetch JSON con cookies + Bearer + auto-refresh
   =========================================================== */
async function jsonFetch(url, opts = {}) {
  const fullUrl = /^https?:\/\//i.test(url) ? url : `${BASE}${url.startsWith("/") ? "" : "/"}${url}`;

  const token = localStorage.getItem("access_token");
  const headers = {
    Accept: "application/json",
    ...(opts.body && { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(opts.headers || {}),
  };

  const exec = () =>
    fetch(fullUrl, {
      credentials: "include",
      headers,
      ...opts,
    });

  let r = await exec();

  // Si 401 y no hemos reintentado aún: ejecuta refresh y reintenta una vez
  if (r.status === 401 && !opts._retried) {
    try {
      await runRefresh();
      return await jsonFetch(url, { ...opts, _retried: true });
    } catch {
      // cae a manejo estándar de 401
    }
  }

  if (!r.ok) {
    let data;
    try { data = await r.json(); } catch {}
    const msg = data?.msg || data?.message || `HTTP ${r.status}`;
    const e = new Error(msg);
    e.code = r.status;
    e.payload = data;
    throw e;
  }

  return r.status === 204 ? null : r.json();
}

/* ===========================================================
   API pública (manteniendo tus mismas funciones)
   =========================================================== */

// Iniciar sesión: mantiene cookies httpOnly y, si viene, guarda access_token (modo híbrido)
export async function loginRequest(email, password) {
  const data = await jsonFetch(`/auth/login`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  // El backend puede devolver access_token además de la cookie httpOnly
  if (data?.access_token) localStorage.setItem("access_token", data.access_token);

  // compatibilidad con tu consumo actual
  if (data?.ok === false) throw new Error(data?.msg || "Respuesta inválida del servidor");
  return data; // { ok: true, access_token?, ... }
}

// Usuario autenticado (usa cookies y/o Bearer; con auto-refresh)
export async function me() {
  return jsonFetch(`/auth/me`, { method: "GET" }); // => { ok:true, user:{...}, roles:[...], ... }
}

/* Opcional: logout explícito */
export async function logout() {
  localStorage.removeItem("access_token");
  return jsonFetch(`/auth/logout`, { method: "POST" });
}
