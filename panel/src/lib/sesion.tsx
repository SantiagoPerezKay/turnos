// Sesión del usuario y negocio activo.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, getToken, setOnUnauthorized, setToken, type Negocio, type Usuario } from "./api";

const NEGOCIO_KEY = "turnos.negocio";

interface Sesion {
  usuario: Usuario | null;
  cargando: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  esAdmin: boolean;
  negocios: Negocio[];
  negocio: Negocio | null;
  elegirNegocio: (id: number) => void;
}

const Ctx = createContext<Sesion | null>(null);

function leerNegocioGuardado(): number | null {
  try {
    const v = localStorage.getItem(NEGOCIO_KEY);
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}

export function SesionProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [token, setTokenState] = useState(getToken);
  const [negocioId, setNegocioId] = useState<number | null>(leerNegocioGuardado);

  const logout = useCallback(() => {
    setToken(null);
    setTokenState(null);
    qc.clear();
  }, [qc]);

  useEffect(() => setOnUnauthorized(logout), [logout]);

  const me = useQuery({
    queryKey: ["me", token],
    queryFn: () => api<Usuario>("/auth/me"),
    enabled: !!token,
    retry: false,
  });

  const negociosQ = useQuery({
    queryKey: ["negocios"],
    queryFn: () => api<Negocio[]>("/admin/negocios"),
    enabled: !!me.data,
  });

  const negocios = negociosQ.data ?? [];
  const negocio = negocios.find((n) => n.id === negocioId) ?? negocios[0] ?? null;

  const login = useCallback(async (email: string, password: string) => {
    const r = await api<{ token: string; usuario: Usuario }>("/auth/login", {
      method: "POST",
      json: { email, password },
    });
    setToken(r.token);
    setTokenState(r.token);
    if (r.usuario.negocio_id) setNegocioId(r.usuario.negocio_id);
  }, []);

  const elegirNegocio = useCallback(
    (id: number) => {
      setNegocioId(id);
      try {
        localStorage.setItem(NEGOCIO_KEY, String(id));
      } catch {
        /* sin almacenamiento */
      }
      // Los datos cacheados son del negocio anterior
      qc.removeQueries({ predicate: (q) => q.queryKey[0] === "n" });
    },
    [qc],
  );

  const valor = useMemo<Sesion>(
    () => ({
      usuario: me.data ?? null,
      cargando: !!token && (me.isPending || (!!me.data && negociosQ.isPending)),
      login,
      logout,
      esAdmin: me.data?.rol === "admin",
      negocios,
      negocio,
      elegirNegocio,
    }),
    [me.data, me.isPending, negociosQ.isPending, token, login, logout, negocios, negocio, elegirNegocio],
  );

  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

export function useSesion() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSesion fuera de SesionProvider");
  return s;
}

/** Negocio activo (las páginas internas solo se muestran si existe). */
export function useNegocio(): Negocio {
  const { negocio } = useSesion();
  if (!negocio) throw new Error("Sin negocio activo");
  return negocio;
}
