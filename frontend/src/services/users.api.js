// frontend/src/services/users.api.js
const BASE = window.API_BASE_URL || "http://localhost:5000";

/* =========================================
   fetch helper con manejo explícito de 401
   ========================================= */
async function jsonFetch(url, opts = {}) {
  const r = await fetch(url, {
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(opts.body && { "Content-Type": "application/json" }),
      ...(opts.headers || {}),
    },
    ...opts,
  });

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
   Normalizadores para respuestas flexibles
   ========================================= */

// Garantiza que todo usuario tenga 'id' y homologa nombre/nip
function normalizeUser(u) {
  if (!u) return u;

  // Mapeo tolerante a distintos nombres de campos
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
    id: u.id ?? u.user_id ?? u._id ?? null,
    nombre,
    nip,
  };
}

// Extrae un array de items y total aunque la API cambie de shape
function normalizeListResponse(raw, { page, size }) {
  // Caso { data: { items, total, page, size } }
  const container = raw?.data && !Array.isArray(raw.data) ? raw.data : raw;

  // items puede venir en varios lugares
  const itemsArr =
    container?.items ??
    container?.data ??
    raw?.items ??
    raw?.data ??
    [];

  const items = Array.isArray(itemsArr) ? itemsArr.map(normalizeUser) : [];

  const total =
    Number(container?.total ?? raw?.total ?? items.length) || items.length;

  return {
    ...raw,
    items,
    total,
    page: Number(container?.page ?? raw?.page ?? page) || page,
    size: Number(container?.size ?? raw?.size ?? size) || size,
  };
}

/* =========================================
   USUARIOS (CRUD)
   ========================================= */

export const usersApi = {
  async list({ page = 1, size = 10, q = "" } = {}) {
    const qs = new URLSearchParams({ page, size });
    if (q) qs.set("q", q);

    const raw = await jsonFetch(`${BASE}/users?${qs.toString()}`, {
      method: "GET",
    });

    return normalizeListResponse(raw, { page, size });
  },

  // Devuelve SIEMPRE un usuario plano con 'id' normalizado + nombre/nip homologados
  async get(id) {
    const raw = await jsonFetch(`${BASE}/users/${encodeURIComponent(id)}`, {
      method: "GET",
    });
    const u = raw?.user ?? raw?.data ?? raw;
    return normalizeUser(u);
  },

  // Crea usuario; incluye nombre/nip y roles si se proporcionan
  async create({ email, password, is_active, nombre, nip, roles } = {}) {
    const payload = { email, password, is_active };
    if (nombre !== undefined) payload.nombre = nombre;
    if (nip !== undefined) payload.nip = nip;
    if (roles !== undefined) payload.roles = roles;

    return jsonFetch(`${BASE}/users`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // Actualiza usuario; incluye nombre/nip/roles solo si se proporcionan
  async update(id, { email, password, is_active, nombre, nip, roles } = {}) {
    const payload = {};
    if (email !== undefined) payload.email = email;
    if (password !== undefined && password !== "") payload.password = password;
    if (is_active !== undefined) payload.is_active = is_active;
    if (nombre !== undefined) payload.nombre = nombre;
    if (nip !== undefined) payload.nip = nip;
    if (roles !== undefined) payload.roles = roles;

    return jsonFetch(`${BASE}/users/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async remove(id) {
    return jsonFetch(`${BASE}/users/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
  },
};

/* =========================================
   Exports auxiliares (compatibilidad)
   ========================================= */
export const listUsers  = (args)            => usersApi.list(args);
export const getUser    = (id)              => usersApi.get(id);
export const createUser = (payload)         => usersApi.create(payload);
export const updateUser = (id, payload)     => usersApi.update(id, payload);
export const deleteUser = (id)              => usersApi.remove(id);
