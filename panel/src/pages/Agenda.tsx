import { useQuery } from "@tanstack/react-query";
import { CalendarPlus, ChevronLeft, ChevronRight, List, Phone, Rows3 } from "lucide-react";
import { useState } from "react";
import { ESTADOS, EtiquetaEstado, telefonoLegible } from "../components/turnos";
import { Boton, Cargando, cx, Encabezado, Input, MensajeError, Modal, Tarjeta, useAvisos, Vacio } from "../components/ui";
import { api, type EstadoTurno, type Horario, type Profesional, type Turno } from "../lib/api";
import { useMutacion, useProfesionales } from "../lib/datos";
import { diaDe, diaSemana, fechaLarga, hora, hoyEn, minutosDelDia, sumarDias } from "../lib/fechas";
import { useNegocio } from "../lib/sesion";
import { NuevoTurno } from "./NuevoTurno";

const PX_POR_MIN = 1.4;

const COLOR_BLOQUE: Record<EstadoTurno, string> = {
  confirmado: "bg-marca-50 ring-marca-200 text-marca-900 hover:bg-marca-100",
  asistio: "bg-emerald-50 ring-emerald-200 text-emerald-900 hover:bg-emerald-100",
  ausente: "bg-red-50 ring-red-200 text-red-900 hover:bg-red-100",
  cancelado: "bg-slate-50 ring-slate-200 text-slate-400 line-through hover:bg-slate-100",
};

function useHorariosDelDia(profesionales: Profesional[], dia: string) {
  const ids = profesionales.map((p) => p.id);
  return useQuery({
    queryKey: ["n", profesionales[0]?.negocio_id, "horarios-todos", ids],
    queryFn: async () => {
      const r = await Promise.all(ids.map((id) => api<Horario[]>(`/admin/profesionales/${id}/horarios`)));
      return Object.fromEntries(ids.map((id, i) => [id, r[i]])) as Record<number, Horario[]>;
    },
    enabled: ids.length > 0,
    select: (todos) => {
      const d = diaSemana(dia);
      return Object.fromEntries(Object.entries(todos).map(([id, hs]) => [id, hs.filter((h) => h.dia_semana === d)])) as Record<number, Horario[]>;
    },
  });
}

const aMin = (h: string) => Number(h.slice(0, 2)) * 60 + Number(h.slice(3, 5));

export function Agenda() {
  const negocio = useNegocio();
  const tz = negocio.zona_horaria;
  const [dia, setDia] = useState(() => hoyEn(tz));
  const [vista, setVista] = useState<"grilla" | "lista">(() => (window.innerWidth < 768 ? "lista" : "grilla"));
  const [seleccionado, setSeleccionado] = useState<Turno | null>(null);
  const [nuevo, setNuevo] = useState(false);
  const [verCancelados, setVerCancelados] = useState(false);

  const profesQ = useProfesionales();
  const profesionales = (profesQ.data ?? []).filter((p) => p.activo);
  const horarios = useHorariosDelDia(profesionales, dia);
  const turnosQ = useQuery({
    queryKey: ["n", negocio.id, "turnos", dia, dia],
    queryFn: () => api<Turno[]>(`/admin/negocios/${negocio.id}/turnos?desde=${dia}&hasta=${dia}`),
  });
  const turnos = (turnosQ.data ?? []).filter((t) => verCancelados || t.estado !== "cancelado");

  // Rango horario visible: jornada de todos los profesionales + turnos fuera de horario
  let desde = 24 * 60,
    hasta = 0;
  for (const hs of Object.values(horarios.data ?? {}))
    for (const h of hs) {
      desde = Math.min(desde, aMin(h.hora_inicio));
      hasta = Math.max(hasta, aMin(h.hora_fin));
    }
  for (const t of turnos) {
    desde = Math.min(desde, minutosDelDia(t.inicio, tz));
    hasta = Math.max(hasta, minutosDelDia(t.fin, tz));
  }
  if (desde >= hasta) [desde, hasta] = [9 * 60, 18 * 60];
  desde = Math.floor(desde / 60) * 60;
  hasta = Math.ceil(hasta / 60) * 60;
  const horas = Array.from({ length: (hasta - desde) / 60 }, (_, i) => desde + i * 60);

  const esHoy = dia === hoyEn(tz);
  const cargando = profesQ.isPending || turnosQ.isPending;

  return (
    <>
      <Encabezado
        titulo="Agenda"
        acciones={
          <Boton onClick={() => setNuevo(true)}>
            <CalendarPlus className="size-4" /> Nuevo turno
          </Boton>
        }
      />

      <Tarjeta className="mb-4 flex flex-wrap items-center gap-3 p-3">
        <div className="flex items-center gap-1">
          <Boton variante="fantasma" className="px-2" onClick={() => setDia(sumarDias(dia, -1))} aria-label="Día anterior">
            <ChevronLeft className="size-5" />
          </Boton>
          <Boton variante="fantasma" className="px-2" onClick={() => setDia(sumarDias(dia, 1))} aria-label="Día siguiente">
            <ChevronRight className="size-5" />
          </Boton>
        </div>
        <h2 className="min-w-44 font-semibold text-slate-900 first-letter:uppercase">{fechaLarga(dia)}</h2>
        {!esHoy && (
          <Boton variante="secundario" className="py-1.5" onClick={() => setDia(hoyEn(tz))}>
            Hoy
          </Boton>
        )}
        <Input type="date" value={dia} onChange={(e) => e.target.value && setDia(e.target.value)} className="w-auto py-1.5" aria-label="Elegir día" />
        <div className="ml-auto flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={verCancelados} onChange={(e) => setVerCancelados(e.target.checked)} className="rounded border-slate-300 text-marca-600" />
            Cancelados
          </label>
          <div className="flex rounded-lg bg-slate-100 p-0.5">
            {(["grilla", "lista"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setVista(v)}
                aria-pressed={vista === v}
                className={cx("rounded-md p-1.5", vista === v ? "bg-white text-slate-900 shadow-sm" : "text-slate-500")}
                aria-label={v === "grilla" ? "Vista grilla" : "Vista lista"}
              >
                {v === "grilla" ? <Rows3 className="size-4" /> : <List className="size-4" />}
              </button>
            ))}
          </div>
        </div>
      </Tarjeta>

      <MensajeError error={turnosQ.error} />

      {cargando ? (
        <Cargando />
      ) : profesionales.length === 0 ? (
        <Tarjeta>
          <Vacio icono={<CalendarPlus className="size-6" />} titulo="Cargá profesionales y horarios" texto="La agenda se arma con los horarios de atención de cada profesional." />
        </Tarjeta>
      ) : vista === "lista" ? (
        <Tarjeta>
          {turnos.length === 0 ? (
            <Vacio icono={<CalendarPlus className="size-6" />} titulo="No hay turnos este día" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {turnos.map((t) => (
                <li key={t.id}>
                  <button onClick={() => setSeleccionado(t)} className="flex w-full flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 text-left hover:bg-slate-50">
                    <span className="w-24 font-semibold tabular-nums text-slate-900">
                      {hora(t.inicio, tz)} <span className="font-normal text-slate-400">– {hora(t.fin, tz)}</span>
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-slate-900">{t.cliente_nombre ?? telefonoLegible(t.cliente_telefono)}</span>
                      <span className="block truncate text-sm text-slate-500">
                        {t.servicio_nombre} · {t.profesional_nombre}
                      </span>
                    </span>
                    <EtiquetaEstado estado={t.estado} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Tarjeta>
      ) : (
        <Tarjeta className="overflow-x-auto">
          <div className="flex min-w-fit">
            {/* Columna de horas */}
            <div className="sticky left-0 z-10 w-14 shrink-0 border-r border-slate-200 bg-white">
              <div className="h-11 border-b border-slate-200" />
              <div className="relative" style={{ height: (hasta - desde) * PX_POR_MIN }}>
                {horas.map((m) => (
                  <span key={m} className="absolute right-2 -translate-y-1/2 text-xs text-slate-400 tabular-nums" style={{ top: (m - desde) * PX_POR_MIN }}>
                    {m > desde && `${String(m / 60).padStart(2, "0")}:00`}
                  </span>
                ))}
              </div>
            </div>

            {profesionales.map((p) => {
              const jornada = horarios.data?.[p.id] ?? [];
              return (
                <div key={p.id} className="w-56 min-w-44 flex-1 border-r border-slate-100 last:border-r-0">
                  <div className="flex h-11 items-center border-b border-slate-200 px-3">
                    <p className="truncate text-sm font-semibold text-slate-900">{p.nombre}</p>
                  </div>
                  <div className="relative bg-slate-50/80" style={{ height: (hasta - desde) * PX_POR_MIN }}>
                    {/* Horario de atención en blanco; fuera de horario queda gris */}
                    {jornada.map((h) => (
                      <div
                        key={h.hora_inicio}
                        className="absolute inset-x-0 bg-white"
                        style={{ top: (aMin(h.hora_inicio) - desde) * PX_POR_MIN, height: (aMin(h.hora_fin) - aMin(h.hora_inicio)) * PX_POR_MIN }}
                      />
                    ))}
                    {horas.map((m) => (
                      <div key={m} className="absolute inset-x-0 border-t border-slate-100" style={{ top: (m - desde) * PX_POR_MIN }} />
                    ))}
                    {turnos
                      .filter((t) => t.profesional_id === p.id)
                      .map((t) => {
                        const ini = minutosDelDia(t.inicio, tz);
                        const alto = Math.max((minutosDelDia(t.fin, tz) - ini) * PX_POR_MIN - 2, 22);
                        return (
                          <button
                            key={t.id}
                            onClick={() => setSeleccionado(t)}
                            className={cx("absolute inset-x-1 overflow-hidden rounded-md px-2 py-1 text-left ring-1 transition-colors", COLOR_BLOQUE[t.estado])}
                            style={{ top: (ini - desde) * PX_POR_MIN + 1, height: alto }}
                          >
                            <p className="truncate text-xs font-semibold">
                              {hora(t.inicio, tz)} · {t.cliente_nombre ?? telefonoLegible(t.cliente_telefono)}
                            </p>
                            {alto > 34 && <p className="truncate text-xs opacity-80">{t.servicio_nombre}</p>}
                          </button>
                        );
                      })}
                  </div>
                </div>
              );
            })}
          </div>
        </Tarjeta>
      )}

      <DetalleTurno turno={seleccionado} onCerrar={() => setSeleccionado(null)} />
      <NuevoTurno abierto={nuevo} onCerrar={() => setNuevo(false)} diaInicial={dia < hoyEn(tz) ? hoyEn(tz) : dia} />
    </>
  );
}

function DetalleTurno({ turno, onCerrar }: { turno: Turno | null; onCerrar: () => void }) {
  const negocio = useNegocio();
  const tz = negocio.zona_horaria;
  const avisar = useAvisos();
  const cambiar = useMutacion((estado: EstadoTurno) => api<Turno>(`/admin/turnos/${turno!.id}`, { method: "PATCH", json: { estado } }));

  if (!turno) return null;

  async function marcar(estado: EstadoTurno) {
    await cambiar.mutateAsync(estado);
    avisar(`Turno marcado como “${ESTADOS[estado].texto.toLowerCase()}”`);
    onCerrar();
  }

  const pasado = new Date(turno.inicio) < new Date();

  return (
    <Modal
      abierto
      onCerrar={() => {
        cambiar.reset();
        onCerrar();
      }}
      titulo={turno.cliente_nombre ?? "Turno"}
    >
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2.5 text-sm">
        <dt className="text-slate-500">Estado</dt>
        <dd>
          <EtiquetaEstado estado={turno.estado} />
        </dd>
        <dt className="text-slate-500">Horario</dt>
        <dd className="font-medium text-slate-900 first-letter:uppercase">
          {fechaLarga(diaDe(turno.inicio, tz))}, {hora(turno.inicio, tz)} – {hora(turno.fin, tz)}
        </dd>
        <dt className="text-slate-500">Servicio</dt>
        <dd className="text-slate-900">{turno.servicio_nombre}</dd>
        <dt className="text-slate-500">Profesional</dt>
        <dd className="text-slate-900">{turno.profesional_nombre}</dd>
        <dt className="text-slate-500">WhatsApp</dt>
        <dd>
          <a href={`https://wa.me/${turno.cliente_telefono}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 font-medium text-marca-700 hover:underline">
            <Phone className="size-3.5" /> {telefonoLegible(turno.cliente_telefono)}
          </a>
        </dd>
        {turno.notas && (
          <>
            <dt className="text-slate-500">Notas</dt>
            <dd className="whitespace-pre-wrap text-slate-900">{turno.notas}</dd>
          </>
        )}
      </dl>

      <MensajeError error={cambiar.error} />

      <div className="mt-6 flex flex-wrap gap-2 border-t border-slate-200 pt-4">
        {turno.estado === "confirmado" && pasado && (
          <>
            <Boton onClick={() => marcar("asistio")} cargando={cambiar.isPending}>
              Asistió
            </Boton>
            <Boton variante="secundario" onClick={() => marcar("ausente")} disabled={cambiar.isPending}>
              No vino
            </Boton>
          </>
        )}
        {turno.estado === "confirmado" && (
          <Boton variante="peligro" onClick={() => confirm("¿Cancelar este turno? El horario queda libre.") && marcar("cancelado")} disabled={cambiar.isPending}>
            Cancelar turno
          </Boton>
        )}
        {turno.estado !== "confirmado" && (
          <Boton variante="secundario" onClick={() => marcar("confirmado")} cargando={cambiar.isPending}>
            Volver a confirmado
          </Boton>
        )}
      </div>
    </Modal>
  );
}
