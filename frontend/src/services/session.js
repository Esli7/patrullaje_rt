// TODAS las llamadas con cookies
const BASE_URL = window.API_BASE_URL || "http://localhost:5000";

export async function me(){
  // Endpoint protegido que devuelve info del usuario (ajusta si tu backend usa otro)
  const r = await fetch(`${BASE_URL}/auth/me`, {
    method: "GET",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  if (r.status === 401) throw new Error("No autenticado");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json(); // { email, ... } según tu backend
}

export async function logout(){
  // Debe existir en el backend para expirar cookie HttpOnly
  const r = await fetch(`${BASE_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: { "Accept": "application/json" },
  });
  // Aunque falle, redirigimos al login
  return r.ok;
}
