// TODAS las llamadas al backend deben incluir credentials:"include"
const BASE_URL = window.API_BASE_URL || "http://localhost:5000";

export async function loginRequest(email, password) {
  const r = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    credentials: "include",                         // << envía/recibe cookie HttpOnly
    body: JSON.stringify({ email, password }),
  });

  let data = {};
  try { data = await r.json(); } catch (_) {}

  if (!r.ok) throw new Error(data?.msg || `HTTP ${r.status}`);
  if (!data?.ok) throw new Error("Respuesta inválida del servidor");

  // El token viene en cookie HttpOnly; no guardes nada en localStorage
  return data; // { ok: true }
}

// ejemplo de llamada autenticada desde el dashboard:
export async function me() {
  const r = await fetch(`${BASE_URL}/auth/me`, {
    method: "GET",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (r.status === 401) throw new Error("No autenticado");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json(); // { ok:true, user:{...} }
}
