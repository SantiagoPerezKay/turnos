import { useQuery } from "@tanstack/react-query";
import { CalendarCheck, CalendarDays, CalendarPlus, MessageCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { EtiquetaEstado, telefonoLegible } from "../components/turnos";
import { Boton, Cargando, Encabezado, Etiqueta, Tarjeta, Vacio } from "../components/ui";
import { api, type Resumen, type Turno } from "../lib/api";
import { fechaLarga, hora, hoyEn } from "../lib/fechas";
import { useNegocio, useSesion } from "../lib/sesion";
import { NuevoTurno } from "./NuevoTurno";

export function Inicio() {
  const negocio = useNegocio();
  const { usuario } = useSesion();
  const tz = negocio.zona_horaria;
  const hoy = hoyEn(tz);
  const [nuevo, setNuevo] = useState(false);

  const resumen = useQuery({
    queryKey: ["n", negocio.id, "resumen"],
    queryFn: () => api<Resumen>(`/admin/negocios/${negocio.id}/resumen`),
  });
  const turnos = useQuery({
    queryKey: ["n", negocio.id, "turnos", hoy, hoy],
    queryFn: () => api<Turno[]>(`/admin/negocios/${negocio.id}/turnos?desde=${hoy}&hasta=${hoy}`),
  });
  const activos = (turnos.data ?? []).filter((t) => t.estado !== "cancelado");

  const tarjetas = [
    { texto: "Turnos hoy", valor: resumen.data?.turnos_hoy, icono: CalendarCheck },
    { texto: "Mañana", valor: resumen.data?.turnos_manana, icono: CalendarDays },
    { texto: "Esta semana", valor: resumen.data?.turnos_semana, icono: CalendarDays },
  ];

  return (
    <>
      <Encabezado
        titulo={`Hola, ${usuario?.nombre.split(" ")[0]}`}
        descripcion={`${negocio.nombre} · ${fechaLarga(hoy)}`}
        acciones={
          <Boton onClick={() => setNuevo(true)}>
            <CalendarPlus className="size-4" /> Nuevo turno
          </Boton>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tarjetas.map(({ texto, valor, icono: Icono }) => (
          <Tarjeta key={texto} className="p-5">
            <div className="flex items-center justify-between text-sm text-slate-500">
              {texto} <Icono className="size-4 text-slate-400" />
            </div>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">{valor ?? "–"}</p>
          </Tarjeta>
        ))}
        <Tarjeta className="p-5">
          <div className="flex items-center justify-between text-sm text-slate-500">
            WhatsApp <MessageCircle className="size-4 text-slate-400" />
          </div>
          <div className="mt-3">
            {resumen.data &&
              (resumen.data.whatsapp_conectado ? (
                <Etiqueta color="verde">Conectado</Etiqueta>
              ) : (
                <Etiqueta color="ambar">Sin conectar</Etiqueta>
              ))}
          </div>
          {resumen.data && !resumen.data.whatsapp_conectado && (
            <p className="mt-2 text-xs text-slate-500">Mientras tanto podés probar el bot desde “Probar el bot”.</p>
          )}
        </Tarjeta>
      </div>

      <Tarjeta className="mt-6">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 className="font-semibold text-slate-900">Turnos de hoy</h2>
          <Link to="/agenda" className="text-sm font-medium text-marca-700 hover:text-marca-800">
            Ver agenda →
          </Link>
        </div>
        {turnos.isPending ? (
          <Cargando />
        ) : activos.length === 0 ? (
          <Vacio icono={<CalendarDays className="size-6" />} titulo="No hay turnos para hoy" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {activos.map((t) => (
              <li key={t.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3">
                <span className="w-12 font-semibold tabular-nums text-slate-900">{hora(t.inicio, tz)}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-slate-900">{t.cliente_nombre ?? telefonoLegible(t.cliente_telefono)}</p>
                  <p className="truncate text-sm text-slate-500">
                    {t.servicio_nombre} · {t.profesional_nombre}
                  </p>
                </div>
                <EtiquetaEstado estado={t.estado} />
              </li>
            ))}
          </ul>
        )}
      </Tarjeta>

      <NuevoTurno abierto={nuevo} onCerrar={() => setNuevo(false)} diaInicial={hoy} />
    </>
  );
}
