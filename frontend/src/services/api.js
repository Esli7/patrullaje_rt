const BASE_URL = window.API_BASE_URL || "http://localhost:5000";

// Normaliza respuesta de /ubicaciones a un array de objetos {id, patrulla, lat, lng, estado, ts}
function normalizeUbics(json){
  // Adecua según tu backend. Ejemplo esperado:
  // { ok:true, data:[ { id, patrulla, lat, lng, estado, ts } ] }
  if (Array.isArray(json)) return json;
  if (json?.data && Array.isArray(json.data)) return json.data;
  return [];
}

export async function fetchUbicaciones() {
  const r = await fetch(`${BASE_URL}/ubicaciones`, {
    method: "GET",
    credentials: "include",        // cookie HttpOnly
    headers: { "Accept": "application/json" },
  });
  if (r.status === 401) throw new Error("No autenticado");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const json = await r.json();
  return normalizeUbics(json);
}
