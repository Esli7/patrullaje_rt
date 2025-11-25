// frontend/src/services/session.js
// Centraliza la sesión de usuario en el frontend.
// Usa el authApi del services/api.js y expone alias compatibles (me/logout).

import { authApi } from "./api.js";

/* =========================
   Utilidades internas
   ========================= */
function roleOf(u, rolesArr = [], isAdmin = false) {
  // si el backend ya pone u.role, úsalo; si no, toma primer rol; si no, usa is_admin
  if (u && u.role) return String(u.role);
  if (Array.isArray(rolesArr) && rolesArr.length) return String(rolesArr[0]);
  return isAdmin ? "admin" : "user";
}

function setCaches({ user, roles, is_admin }) {
  window.__currentUser = user || null;
  window.__currentUserRoles = Array.isArray(roles) ? roles : [];
  window.__isAdmin = !!is_admin;

  // Notificación global de cambios de rol/usuario (la escucha UsersView, etc.)
  try {
    const flat = {
      ...(user || {}),
      roles: Array.isArray(roles) ? roles : [],
      is_admin: !!is_admin,
      role: roleOf(user || {}, roles, is_admin),
    };
    window.dispatchEvent(new CustomEvent("role-change", { detail: flat }));
  } catch {}
}

/* Coalescer para evitar múltiples /me simultáneos */
let _meInFlight = null;
async function callMeOnce() {
  if (_meInFlight) return _meInFlight;
  _meInFlight = authApi
    .me() // GET /api/auth/me (credentials: include)
    .finally(() => (_meInFlight = null));
  return _meInFlight;
}

/* =========================
   API pública (compatible)
   ========================= */

/**
 * Llama /api/auth/me y cachea el usuario globalmente en window.__currentUser
 * Estructura esperada backend: { ok, user:{...}, roles:[...], is_admin:boolean }
 */
export async function getCurrentUser(force = false) {
  if (!force && window.__currentUser) return window.__currentUser;

  let resp;
  try {
    resp = await callMeOnce();
  } catch (e) {
    // Intento único de refresh si el backend lo soporta
    try {
      await authApi.refresh(); // POST /api/auth/refresh
      resp = await callMeOnce();
    } catch {
      throw new Error("No autenticado");
    }
  }

  if (!resp?.ok) throw new Error("No autenticado");
  setCaches({ user: resp.user, roles: resp.roles, is_admin: resp.is_admin });
  return window.__currentUser;
}

/**
 * Alias compatible: me()
 * Devuelve un objeto “flat” para GuardController y otros:
 * { ...user, roles:[], is_admin:boolean, role:string }
 */
export async function me() {
  let data;
  try {
    data = await callMeOnce();
  } catch {
    // Refresh + retry (único intento)
    try {
      await authApi.refresh();
      data = await callMeOnce();
    } catch {
      throw new Error("No autenticado");
    }
  }
  if (!data?.ok) throw new Error("No autenticado");

  setCaches({ user: data.user, roles: data.roles, is_admin: data.is_admin });

  return {
    ...(data.user || {}),
    roles: Array.isArray(data.roles) ? data.roles : [],
    is_admin: !!data.is_admin,
    role: roleOf(data.user || {}, data.roles, data.is_admin),
  };
}

/** Devuelve el usuario cacheado si existe (sin red). */
export function currentUserCached() {
  return window.__currentUser || null;
}

/** True si el usuario actual es admin (según cache). */
export function isAdmin() {
  return !!window.__isAdmin;
}

/** True si el usuario tiene un rol concreto (según cache). */
export function hasRole(roleCode) {
  const roles = window.__currentUserRoles || [];
  return roles.includes(String(roleCode));
}

/** Logout en backend + limpia cache local (no bloquea si hay error). */
export async function signOut() {
  try {
    await authApi.logout(); // POST /api/auth/logout
  } finally {
    window.__currentUser = null;
    window.__currentUserRoles = [];
    window.__isAdmin = false;
    try {
      window.dispatchEvent(new CustomEvent("role-change", { detail: null }));
    } catch {}
  }
}

/** Alias compatible para GuardController */
export async function logout() {
  return signOut();
}
