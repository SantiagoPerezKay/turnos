import {
  Bot,
  Building2,
  CalendarDays,
  LayoutDashboard,
  LogOut,
  Menu,
  Scissors,
  Settings,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { useSesion } from "../lib/sesion";
import { cx, Select } from "./ui";

const NAV = [
  { a: "/", texto: "Inicio", icono: LayoutDashboard },
  { a: "/agenda", texto: "Agenda", icono: CalendarDays },
  { a: "/profesionales", texto: "Profesionales", icono: Users },
  { a: "/servicios", texto: "Servicios", icono: Scissors },
  { a: "/probar", texto: "Probar el bot", icono: Bot },
  { a: "/configuracion", texto: "Configuración", icono: Settings },
];

function Navegacion({ onNavegar }: { onNavegar?: () => void }) {
  const { usuario, esAdmin, negocios, negocio, elegirNegocio, logout } = useSesion();

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-4 py-5">
        <img src="/favicon.svg" alt="" className="size-8" />
        <span className="text-base font-semibold text-slate-900">Turnos</span>
      </div>

      {esAdmin && negocios.length > 0 && (
        <div className="px-3 pb-3">
          <label className="mb-1 block px-1 text-xs font-medium text-slate-500">Negocio</label>
          <Select value={negocio?.id ?? ""} onChange={(e) => elegirNegocio(Number(e.target.value))}>
            {negocios.map((n) => (
              <option key={n.id} value={n.id}>
                {n.nombre}
              </option>
            ))}
          </Select>
        </div>
      )}
      {!esAdmin && negocio && <p className="truncate px-4 pb-3 text-sm font-medium text-slate-600">{negocio.nombre}</p>}

      <nav className="flex-1 space-y-0.5 px-3">
        {negocio &&
          NAV.map(({ a, texto, icono: Icono }) => (
            <NavLink
              key={a}
              to={a}
              end={a === "/"}
              onClick={onNavegar}
              className={({ isActive }) =>
                cx(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-marca-50 text-marca-800" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                )
              }
            >
              <Icono className="size-4.5" />
              {texto}
            </NavLink>
          ))}
        {esAdmin && (
          <>
            <p className="px-3 pt-5 pb-1 text-xs font-semibold tracking-wide text-slate-400 uppercase">Administración</p>
            <NavLink
              to="/negocios"
              onClick={onNavegar}
              className={({ isActive }) =>
                cx(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-marca-50 text-marca-800" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                )
              }
            >
              <Building2 className="size-4.5" />
              Negocios
            </NavLink>
          </>
        )}
      </nav>

      <div className="border-t border-slate-200 p-3">
        <div className="flex items-center gap-3 px-2 py-1.5">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-marca-100 text-sm font-semibold text-marca-800">
            {usuario?.nombre.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-900">{usuario?.nombre}</p>
            <p className="truncate text-xs text-slate-500">{usuario?.email}</p>
          </div>
          <button onClick={logout} className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700" title="Cerrar sesión" aria-label="Cerrar sesión">
            <LogOut className="size-4.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

export function Layout() {
  const [menuAbierto, setMenuAbierto] = useState(false);

  return (
    <div className="min-h-dvh lg:pl-64">
      {/* Escritorio */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white lg:block">
        <Navegacion />
      </aside>

      {/* Móvil */}
      <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur lg:hidden">
        <button onClick={() => setMenuAbierto(true)} className="-ml-1 rounded-md p-1.5 text-slate-600 hover:bg-slate-100" aria-label="Abrir menú">
          <Menu className="size-5" />
        </button>
        <img src="/favicon.svg" alt="" className="size-7" />
        <span className="font-semibold text-slate-900">Turnos</span>
      </header>
      {menuAbierto && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setMenuAbierto(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-white shadow-xl">
            <button onClick={() => setMenuAbierto(false)} className="absolute top-4 right-3 rounded-md p-1.5 text-slate-500 hover:bg-slate-100" aria-label="Cerrar menú">
              <X className="size-5" />
            </button>
            <Navegacion onNavegar={() => setMenuAbierto(false)} />
          </aside>
        </div>
      )}

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <Outlet />
      </main>
    </div>
  );
}
