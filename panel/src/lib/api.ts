// Cliente de la API del backend + tipos.

declare global {
  interface Window {
    __CONFIG__?: { API_URL?: string };
  }
}

const API_URL = (window.__CONFIG__?.API_URL || import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "turnos.token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* almacenamiento no disponible: la sesión dura lo que la pestaña */
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

let onUnauthorized: () => void = () => {};
export function setOnUnauthorized(fn: () => void) {
  onUnauthorized = fn;
}

function mensajeDeError(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // Errores de validación de FastAPI
    return detail.map((d: { msg?: string }) => d.msg?.replace(/^Value error, /, "")).filter(Boolean).join(". ");
  }
  return status >= 500 ? "Error del servidor. Probá de nuevo en un rato." : `Error ${status}`;
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers, body });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor.");
  }

  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized();
    throw new ApiError(res.status, mensajeDeError(data, res.status));
  }
  return data as T;
}

// ---------- Tipos ----------
export type Rol = "admin" | "negocio";

export interface Usuario {
  id: number | null;
  email: string | null;
  nombre: string;
  rol: Rol;
  negocio_id: number | null;
}

export interface UsuarioPanel {
  id: number;
  email: string;
  nombre: string;
  rol: Rol;
  negocio_id: number | null;
  activo: boolean;
}

export interface Negocio {
  id: number;
  nombre: string;
  rubro: string | null;
  direccion: string | null;
  telefono_contacto: string | null;
  zona_horaria: string;
  info_extra: string | null;
  wa_phone_number_id: string | null;
  intervalo_turnos_min: number;
  anticipacion_min_minutos: number;
  dias_max_reserva: number;
  horas_min_cancelacion: number;
  activo: boolean;
}

export interface Profesional {
  id: number;
  negocio_id: number;
  nombre: string;
  especialidad: string | null;
  activo: boolean;
}

export interface Servicio {
  id: number;
  negocio_id: number;
  nombre: string;
  descripcion: string | null;
  duracion_min: number;
  precio: string | null;
  activo: boolean;
  profesional_ids: number[];
}

export interface Horario {
  id?: number;
  dia_semana: number;
  hora_inicio: string; // "HH:MM:SS"
  hora_fin: string;
}

export interface Bloqueo {
  id: number;
  profesional_id: number;
  desde: string;
  hasta: string;
  motivo: string | null;
}

export type EstadoTurno = "confirmado" | "cancelado" | "asistio" | "ausente";

export interface Turno {
  id: number;
  inicio: string;
  fin: string;
  estado: EstadoTurno;
  notas: string | null;
  profesional_id: number;
  profesional_nombre: string;
  servicio_id: number;
  servicio_nombre: string;
  cliente_id: number;
  cliente_nombre: string | null;
  cliente_telefono: string;
}

export interface Slot {
  profesional_id: number;
  profesional: string;
  inicio: string;
  fin: string;
}

export interface Resumen {
  turnos_hoy: number;
  turnos_manana: number;
  turnos_semana: number;
  whatsapp_conectado: boolean;
}
