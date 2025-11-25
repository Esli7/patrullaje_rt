// frontend/src/services/api.js

// ================================
// Base URL (si no trae /api se agrega)
// ================================
const rawBase = (window.API_BASE_URL || "http://localhost:5000").replace(/\/+$/,'');
export const BASE = rawBase.endsWith("/api") ? rawBase : `${rawBase}/api`;

/* =========================================
   Mecanismo de refresh (reintento único)
   ========================================= */
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
        if (data?.access_token) {
          localStorage.setItem("access_token", data.access_token);
        }
        return data;
      })
      .finally(() => (refreshing = null));
  }
  return refreshing;
}

/* =========================================
   fetch helper con manejo explícito de 401
   - Adjunta cookies y Bearer si existe
   - Reintenta una vez tras /auth/refresh
   - Evita caché **sin** romper CORS (GET => cache-buster en la URL)
   ========================================= */
export async function jsonFetch(url, opts = {}) {
  const baseOrAbs =
    /^https?:\/\//i.test(url) ? url : `${BASE}${url.startsWith("/") ? "" : "/"}${url}`;

  const token = localStorage.getItem("access_token");
  const headers = {
    Accept: "application/json",
    ...(opts.body && { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(opts.headers || {}),
  };

  const method = String(opts.method || "GET").toUpperCase();

  const finalUrl =
    method === "GET"
      ? `${baseOrAbs}${baseOrAbs.includes("?") ? "&" : "?"}_ts=${Date.now()}`
      : baseOrAbs;

  const exec = () =>
    fetch(finalUrl, {
      credentials: "include",
      ...(method === "GET" ? { cache: "no-store" } : {}),
      headers,
      ...opts,
    });

  let r = await exec();

  if (r.status === 401 && !opts._retried) {
    try {
      await runRefresh();
      return await jsonFetch(url, { ...opts, _retried: true });
    } catch {}
  }

  if (r.status === 401) {
    const err = new Error("No autenticado");
    err.code = 401;
    try { err.payload = await r.json(); } catch {}
    throw err;
  }

  if (!r.ok) {
    let msg = `HTTP ${r.status}`;
    try {
      const err = await r.json();
      if (err?.message || err?.msg) msg += `: ${err.message || err.msg}`;
    } catch {}
    const e = new Error(msg);
    e.code = r.status;
    throw e;
  }

  return r.status === 204 ? null : r.json();
}

/* =========================================
   Helpers de normalización
   ========================================= */

// Normaliza un usuario a una forma estándar para la UI
function normalizeUser(u) {
  if (!u || typeof u !== "object") return u;

  const id = u.id ?? u.user_id ?? u._id ?? null;
  const email = u.email ?? u.user_email ?? null;

  // Recoger posibles formas de enviar el array de roles
  const rolesRaw =
    Array.isArray(u.roles) ? u.roles
    : Array.isArray(u.role_codes) ? u.role_codes
    : Array.isArray(u.roles_codes) ? u.roles_codes
    : [];

  // rol único (compatibilidad)
  const roleSingle =
    u.role ?? u.rol ?? (rolesRaw.length ? rolesRaw[0] : undefined);

  // Siempre construimos una versión “bonita” para mostrar
  const role_display =
    (typeof u.role_display === "string" && u.role_display.trim())
      ? u.role_display.trim()
      : (rolesRaw.length ? rolesRaw.join(", ") : (roleSingle ?? null));

  const is_active = u.is_active ?? u.active ?? u.enabled ?? null;
  const created_at = u.created_at ?? u.createdAt ?? u.created ?? u.fecha_creacion ?? null;

  // <<< Añadido: mapear nombre/nip de forma tolerante >>>
  const nombre =
    u.nombre ??
    u.fullname ??
    u.full_name ??
    u.name ??
    null;

  const nip =
    u.nip ??
    u.pin ??
    null;

  return {
    ...u,
    id,
    email,
    roles: rolesRaw,
    role: roleSingle ?? null,   // compat
    role_display,               // <- usar en la vista
    is_active,
    created_at,
    nombre,                     // <- NUEVO
    nip,                        // <- NUEVO
  };
}

function extractUsersArray(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw.items)) return raw.items;
  if (Array.isArray(raw.data)) return raw.data;
  if (Array.isArray(raw.users)) return raw.users;
  if (Array.isArray(raw.rows)) return raw.rows;
  const c = raw.data;
  if (c) {
    if (Array.isArray(c.items)) return c.items;
    if (Array.isArray(c.data)) return c.data;
    if (Array.isArray(c.users)) return c.users;
    if (Array.isArray(c.rows)) return c.rows;
  }
  return [];
}

function extractMeta(raw, fallback) {
  const c = raw?.data && !Array.isArray(raw.data) ? raw.data : raw;
  const total = Number(c?.total ?? raw?.total ?? c?.count ?? raw?.count ?? fallback.total ?? 0) || 0;
  const page = Number(c?.page ?? raw?.page ?? fallback.page ?? 1) || 1;
  const size = Number(c?.size ?? raw?.size ?? fallback.size ?? 10) || 10;
  return { total, page, size };
}

function normalizeListResponse(raw, { page, size }) {
  const items = extractUsersArray(raw).map(normalizeUser);
  const meta = extractMeta(raw, { page, size, total: items.length });
  return { items, ...meta };
}

/* =========================================
   AUTH
   ========================================= */
export const authApi = {
  async login({ email, password }) {
    const data = await jsonFetch(`/auth/login`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (data?.access_token) localStorage.setItem("access_token", data.access_token);
    return data;
  },
  me() {
    return jsonFetch(`/auth/me`, { method: "GET" });
  },
  async logout() {
    localStorage.removeItem("access_token");
    return jsonFetch(`/auth/logout`, { method: "POST" });
  },
  async refresh() {
    const data = await jsonFetch(`/auth/refresh`, { method: "POST" });
    if (data?.access_token) localStorage.setItem("access_token", data.access_token);
    return data;
  },
};

/* =========================================
   ROLES (catálogo para el formulario)
   ========================================= */
export const rolesApi = {
  async list() {
    try {
      const r = await jsonFetch(`/users/roles`, { method: "GET" });
      return Array.isArray(r?.roles) ? r.roles : ["usuario", "patrullero", "admin"];
    } catch {
      // Fallback si el endpoint no existe o falla
      return ["usuario", "patrullero", "admin"];
    }
  },
};

/* =========================================
   UBICACIONES
   ========================================= */
function normalizeUbics(json) {
  let arr = [];

  if (Array.isArray(json)) {
    arr = json;
  } else if (json?.data && Array.isArray(json.data)) {
    arr = json.data;
  } else if (json?.items && Array.isArray(json.items)) {
    arr = json.items;
  } else if (json?.features && Array.isArray(json.features)) {
    return json.features
      .map((f) => ({
        patrulla: f.properties?.nombre || f.properties?.patrulla || f.id,
        lat: Number(f.geometry?.coordinates?.[1]),
        lng: Number(f.geometry?.coordinates?.[0]),
        estado:
          f.properties?.estado ??
          (typeof f.properties?.activo === "boolean"
            ? f.properties.activo
              ? "activa"
              : "inactiva"
            : undefined),
        ts: f.properties?.ts || f.properties?.updated_at || null,
        raw: f,
      }))
      .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng));
  } else {
    return [];
  }

  return arr
    .map((u) => ({
      patrulla: u.patrulla || u.nombre || u.id || "",
      lat: Number(
        u.lat ??
          u.latitude ??
          u.latitud ??
          u.y ??
          u.geometry?.coordinates?.[1]
      ),
      lng: Number(
        u.lng ??
          u.lon ??
          u.longitude ??
          u.longitud ??
          u.x ??
          u.geometry?.coordinates?.[0]
      ),
      estado:
        u.estado ??
        (typeof u.activo === "boolean" ? (u.activo ? "activa" : "inactiva") : undefined),
      ts: u.ts || u.updated_at || u.created_at || null,
      raw: u,
    }))
    .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng));
}

export async function fetchUbicaciones() {
  const json = await jsonFetch(`/ubicaciones`, { method: "GET" });
  return normalizeUbics(json);
}

/* =========================================
   USUARIOS (CRUD)
   ========================================= */
export const usersApi = {
  async list({ page = 1, size = 10, q = "" } = {}) {
    const qs = new URLSearchParams({ page, size });
    if (q) qs.set("q", q);

    try {
      const raw = await jsonFetch(`/users?${qs.toString()}`, { method: "GET" });
      return normalizeListResponse(raw, { page, size });
    } catch (e1) {
      console.debug("[usersApi.list] primer intento falló:", e1?.message || e1);
    }

    try {
      const raw = await jsonFetch(`/users`, { method: "GET" });
      return normalizeListResponse(raw, { page, size });
    } catch (e2) {
      console.debug("[usersApi.list] segundo intento falló:", e2?.message || e2);
    }

    try {
      const raw = await jsonFetch(`/users/list`, { method: "GET" });
      return normalizeListResponse(raw, { page, size });
    } catch (e3) {
      console.debug("[usersApi.list] tercer intento falló:", e3?.message || e3);
      return { items: [], total: 0, page, size };
    }
  },

  async get(id) {
    const raw = await jsonFetch(`/users/${encodeURIComponent(id)}`, { method: "GET" });
    const u = raw?.user ?? raw?.data ?? raw;
    return normalizeUser(u);
  },

  // ACEPTA 'roles' (array) y mantiene compat con 'role' (string)
  // >>> Corregido: también acepta y envía nombre y nip
  async create({ email, password, is_active, roles, role, nombre, nip }) {
    const payload = { email, password };
    if (is_active !== undefined) payload.is_active = is_active;
    if (Array.isArray(roles)) payload.roles = roles;
    else if (role) payload.roles = [String(role)];
    if (nombre !== undefined) payload.nombre = nombre; // <-- añadido
    if (nip !== undefined) payload.nip = nip;          // <-- añadido

    return jsonFetch(`/users`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // >>> Corregido: también acepta y envía nombre y nip
  async update(id, { email, password, is_active, roles, role, nombre, nip }) {
    const payload = {};
    if (email !== undefined) payload.email = email;
    if (password !== undefined && password !== "") payload.password = password;
    if (is_active !== undefined) payload.is_active = is_active;

    if (Array.isArray(roles)) payload.roles = roles;
    else if (role !== undefined) payload.roles = role ? [String(role)] : [];

    if (nombre !== undefined) payload.nombre = nombre; // <-- añadido
    if (nip !== undefined) payload.nip = nip;          // <-- añadido

    return jsonFetch(`/users/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async remove(id) {
    return jsonFetch(`/users/${encodeURIComponent(id)}`, { method: "DELETE" });
  },
};

// Alias (compatibilidad)
export const listUsers  = (args)        => usersApi.list(args);
export const getUser    = (id)          => usersApi.get(id);
export const createUser = (payload)     => usersApi.create(payload);
export const updateUser = (id, payload) => usersApi.update(id, payload);
export const deleteUser = (id)          => usersApi.remove(id);

/* =========================================
   PATRULLAS (CRUD) — NUEVO
   ========================================= */

// Normalizador para patrullas
function normalizePatrulla(p) {
  if (!p || typeof p !== "object") return p;
  return {
    ...p,
    id: p.id ?? p.patrulla_id ?? p._id ?? null,
    codigo: p.codigo ?? p.code ?? null,
    alias: p.alias ?? p.nombre ?? null,
    placa: p.placa ?? p.plate ?? null,
    is_activa: p.is_activa ?? p.activa ?? p.active ?? false,
    created_at: p.created_at ?? p.createdAt ?? p.fecha_creacion ?? null,
  };
}

// Normaliza lista genérica con mapper (evita tocar normalizeListResponse de usuarios)
function normalizeListGeneric(raw, { page, size }, mapFn) {
  const container = raw?.data && !Array.isArray(raw.data) ? raw.data : raw;
  const arr = container?.items ?? container?.data ?? raw?.items ?? raw?.data ?? [];
  const items = Array.isArray(arr) ? arr.map(mapFn) : [];
  const total = Number(container?.total ?? raw?.total ?? items.length) || items.length;
  return {
    items,
    total,
    page: Number(container?.page ?? raw?.page ?? page) || page,
    size: Number(container?.size ?? raw?.size ?? size) || size,
  };
}

export const patrullasApi = {
  async list({ page = 1, size = 10, q = "" } = {}) {
    const qs = new URLSearchParams({ page, size });
    if (q) qs.set("q", q);
    const raw = await jsonFetch(`/patrullas?${qs.toString()}`, { method: "GET" });
    return normalizeListGeneric(raw, { page, size }, normalizePatrulla);
  },
  async get(id) {
    const raw = await jsonFetch(`/patrullas/${encodeURIComponent(id)}`, { method: "GET" });
    const p = raw?.patrulla ?? raw?.data ?? raw;
    return normalizePatrulla(p);
  },
  async create({ codigo, alias, placa, is_activa }) {
    return jsonFetch(`/patrullas`, {
      method: "POST",
      body: JSON.stringify({ codigo, alias, placa, is_activa }),
    });
  },
  async update(id, { alias, placa, is_activa }) {
    const payload = {};
    if (alias !== undefined) payload.alias = alias;
    if (placa !== undefined) payload.placa = placa;
    if (is_activa !== undefined) payload.is_activa = is_activa;
    return jsonFetch(`/patrullas/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  async remove(id) {
    return jsonFetch(`/patrullas/${encodeURIComponent(id)}`, { method: "DELETE" });
  },
};

// Alias patrullas
export const listPatrullas  = (args)        => patrullasApi.list(args);
export const getPatrulla    = (id)          => patrullasApi.get(id);
export const createPatrulla = (payload)     => patrullasApi.create(payload);
export const updatePatrulla = (id, payload) => patrullasApi.update(id, payload);
export const deletePatrulla = (id)          => patrullasApi.remove(id);
