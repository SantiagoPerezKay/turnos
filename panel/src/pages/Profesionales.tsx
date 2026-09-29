import { useQuery } from "@tanstack/react-query";
import { CalendarOff, Plus, Trash2, UserPlus, Users } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Boton, Campo, Cargando, cx, Encabezado, Etiqueta, Input, Interruptor, MensajeError, Modal, Tarjeta, useAvisos, Vacio } from "../components/ui";
import { api, type Bloqueo, type Horario, type Profesional } from "../lib/api";
import { useMutacion, useProfesionales } from "../lib/datos";
import { aIsoEnZona, DIAS, fechaHoraCorta, hhmm, hoyEn, sumarDias } from "../lib/fechas";
import { useNegocio } from "../lib/sesion";

export function Profesionales() {
  const profesQ = useProfesionales();
  const [seleccionadoId, setSeleccionadoId] = useState<number | null>(null);
  const [creando, setCreando] = useState(false);
  const profesionales = profesQ.data ?? [];
  const seleccionado = profesionales.find((p) => p.id === seleccionadoId) ?? profesionales[0];

  return (
    <>
      <Encabezado
        titulo="Profesionales"
        descripcion="Quiénes atienden, en qué horarios y cuándo no están."
        acciones={
          <Boton onClick={() => setCreando(true)}>
            <UserPlus className="size-4" /> Nuevo profesional
          </Boton>
        }
      />

      {profesQ.isPending ? (
        <Cargando />
      ) : profesionales.length === 0 ? (
        <Tarjeta>
          <Vacio
            icono={<Users className="size-6" />}
            titulo="Todavía no cargaste profesionales"
            texto="Agregá a las personas que atienden y después configurá sus horarios."
            accion={<Boton onClick={() => setCreando(true)}>Agregar profesional</Boton>}
          />
        </Tarjeta>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
          <Tarjeta className="h-fit p-2">
            <ul className="space-y-0.5">
              {profesionales.map((p) => (
                <li key={p.id}>
                  <button
                    onClick={() => setSeleccionadoId(p.id)}
                    className={cx(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors",
                      seleccionado?.id === p.id ? "bg-marca-50" : "hover:bg-slate-50",
                    )}
                  >
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-600">
                      {p.nombre.replace(/^(Dra?\.|Lic\.)\s*/i, "").charAt(0)}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={cx("block truncate text-sm font-medium", p.activo ? "text-slate-900" : "text-slate-400")}>{p.nombre}</span>
                      {p.especialidad && <span className="block truncate text-xs text-slate-500">{p.especialidad}</span>}
                    </span>
                    {!p.activo && <Etiqueta>Inactivo</Etiqueta>}
                  </button>
                </li>
              ))}
            </ul>
          </Tarjeta>
          {seleccionado && <DetalleProfesional key={seleccionado.id} profesional={seleccionado} />}
        </div>
      )}

      <NuevoProfesional
        abierto={creando}
        onCerrar={() => setCreando(false)}
        onCreado={(id) => {
          setSeleccionadoId(id);
          setCreando(false);
        }}
      />
    </>
  );
}

function NuevoProfesional({ abierto, onCerrar, onCreado }: { abierto: boolean; onCerrar: () => void; onCreado: (id: number) => void }) {
  const negocio = useNegocio();
  const [nombre, setNombre] = useState("");
  const [especialidad, setEspecialidad] = useState("");
  const crear = useMutacion(
    (data: object) => api<Profesional>(`/admin/negocios/${negocio.id}/profesionales`, { method: "POST", json: data }),
    ["profesionales"],
  );

  async function enviar(e: FormEvent) {
    e.preventDefault();
    const p = await crear.mutateAsync({ nombre, especialidad: especialidad || null });
    setNombre("");
    setEspecialidad("");
    onCreado(p.id);
  }

  return (
    <Modal
      abierto={abierto}
      onCerrar={onCerrar}
      titulo="Nuevo profesional"
      pie={
        <>
          <Boton variante="secundario" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" form="form-nuevo-prof" cargando={crear.isPending}>
            Crear
          </Boton>
        </>
      }
    >
      <form id="form-nuevo-prof" onSubmit={enviar} className="space-y-4">
        <Campo etiqueta="Nombre">{(id) => <Input id={id} required autoFocus placeholder="Dra. Laura Gómez" value={nombre} onChange={(e) => setNombre(e.target.value)} />}</Campo>
        <Campo etiqueta="Especialidad (opcional)">
          {(id) => <Input id={id} placeholder="Odontología general" value={especialidad} onChange={(e) => setEspecialidad(e.target.value)} />}
        </Campo>
        <MensajeError error={crear.error} />
      </form>
    </Modal>
  );
}

function DetalleProfesional({ profesional }: { profesional: Profesional }) {
  const avisar = useAvisos();
  const [nombre, setNombre] = useState(profesional.nombre);
  const [especialidad, setEspecialidad] = useState(profesional.especialidad ?? "");
  const guardar = useMutacion(
    (data: Partial<Profesional>) => api<Profesional>(`/admin/profesionales/${profesional.id}`, { method: "PATCH", json: data }),
    ["profesionales"],
  );
  const cambios = nombre !== profesional.nombre || especialidad !== (profesional.especialidad ?? "");

  return (
    <div className="space-y-6">
      <Tarjeta className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <h2 className="font-semibold text-slate-900">Datos</h2>
          <label className="flex items-center gap-3 text-sm text-slate-600">
            {profesional.activo ? "Toma turnos" : "No toma turnos"}
            <Interruptor
              etiqueta="Activo"
              activo={profesional.activo}
              onChange={async (activo) => {
                await guardar.mutateAsync({ activo });
                avisar(activo ? "Profesional activado" : "Profesional desactivado");
              }}
            />
          </label>
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Nombre">{(id) => <Input id={id} value={nombre} onChange={(e) => setNombre(e.target.value)} />}</Campo>
          <Campo etiqueta="Especialidad">{(id) => <Input id={id} value={especialidad} onChange={(e) => setEspecialidad(e.target.value)} />}</Campo>
        </div>
        <MensajeError error={guardar.error} />
        {cambios && (
          <div className="mt-4 flex justify-end">
            <Boton
              cargando={guardar.isPending}
              onClick={async () => {
                await guardar.mutateAsync({ nombre, especialidad: especialidad || null });
                avisar("Datos guardados");
              }}
            >
              Guardar
            </Boton>
          </div>
        )}
      </Tarjeta>
      <EditorHorarios profesionalId={profesional.id} />
      <Bloqueos profesionalId={profesional.id} />
    </div>
  );
}

type Franja = { inicio: string; fin: string };

function EditorHorarios({ profesionalId }: { profesionalId: number }) {
  const negocio = useNegocio();
  const avisar = useAvisos();
  const q = useQuery({
    queryKey: ["n", negocio.id, "horarios", profesionalId],
    queryFn: () => api<Horario[]>(`/admin/profesionales/${profesionalId}/horarios`),
  });
  const [semana, setSemana] = useState<Franja[][] | null>(null);
  const [sucio, setSucio] = useState(false);

  useEffect(() => {
    if (q.data) {
      setSemana(DIAS.map((_, d) => q.data.filter((h) => h.dia_semana === d).map((h) => ({ inicio: hhmm(h.hora_inicio), fin: hhmm(h.hora_fin) }))));
      setSucio(false);
    }
  }, [q.data]);

  const guardar = useMutacion(
    (data: Horario[]) => api<Horario[]>(`/admin/profesionales/${profesionalId}/horarios`, { method: "PUT", json: data }),
    ["horarios", "horarios-todos"],
  );

  function editar(dia: number, fn: (f: Franja[]) => Franja[]) {
    setSemana((s) => s!.map((f, i) => (i === dia ? fn(f) : f)));
    setSucio(true);
  }

  async function enviar() {
    const data: Horario[] = semana!.flatMap((franjas, dia) => franjas.map((f) => ({ dia_semana: dia, hora_inicio: f.inicio, hora_fin: f.fin })));
    await guardar.mutateAsync(data);
    avisar("Horarios guardados");
  }

  return (
    <Tarjeta className="p-5">
      <h2 className="font-semibold text-slate-900">Horarios de atención</h2>
      <p className="mt-1 text-sm text-slate-500">El bot solo ofrece turnos dentro de estas franjas. Podés cargar más de una por día (p. ej. mañana y tarde).</p>

      {!semana ? (
        <Cargando />
      ) : (
        <div className="mt-4 divide-y divide-slate-100">
          {DIAS.map((nombreDia, d) => {
            const franjas = semana[d];
            const atiende = franjas.length > 0;
            return (
              <div key={d} className="flex flex-wrap items-start gap-x-4 gap-y-2 py-3">
                <label className="flex w-36 items-center gap-3 pt-1.5">
                  <Interruptor
                    etiqueta={`Atiende los ${nombreDia}`}
                    activo={atiende}
                    onChange={(v) => editar(d, () => (v ? [{ inicio: "09:00", fin: "13:00" }] : []))}
                  />
                  <span className={cx("text-sm font-medium", atiende ? "text-slate-900" : "text-slate-400")}>{nombreDia}</span>
                </label>
                <div className="flex flex-1 flex-col gap-2">
                  {!atiende && <span className="pt-1.5 text-sm text-slate-400">No atiende</span>}
                  {franjas.map((f, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <Input
                        type="time"
                        step={300}
                        value={f.inicio}
                        onChange={(e) => editar(d, (fs) => fs.map((x, j) => (j === i ? { ...x, inicio: e.target.value } : x)))}
                        className="w-28 py-1.5"
                        aria-label={`${nombreDia} desde`}
                      />
                      <span className="text-slate-400">a</span>
                      <Input
                        type="time"
                        step={300}
                        value={f.fin}
                        onChange={(e) => editar(d, (fs) => fs.map((x, j) => (j === i ? { ...x, fin: e.target.value } : x)))}
                        className="w-28 py-1.5"
                        aria-label={`${nombreDia} hasta`}
                      />
                      <button
                        onClick={() => editar(d, (fs) => fs.filter((_, j) => j !== i))}
                        className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-red-600"
                        aria-label="Quitar franja"
                      >
                        <Trash2 className="size-4" />
                      </button>
                      {i === franjas.length - 1 && (
                        <button
                          onClick={() => editar(d, (fs) => [...fs, { inicio: "14:00", fin: "18:00" }])}
                          className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-marca-700"
                          aria-label="Agregar franja"
                        >
                          <Plus className="size-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
      <MensajeError error={guardar.error} />
      {sucio && (
        <div className="mt-4 flex justify-end gap-2">
          <Boton variante="secundario" onClick={() => q.refetch()}>
            Descartar
          </Boton>
          <Boton onClick={enviar} cargando={guardar.isPending}>
            Guardar horarios
          </Boton>
        </div>
      )}
    </Tarjeta>
  );
}

function Bloqueos({ profesionalId }: { profesionalId: number }) {
  const negocio = useNegocio();
  const tz = negocio.zona_horaria;
  const avisar = useAvisos();
  const hoy = hoyEn(tz);
  const [abierto, setAbierto] = useState(false);
  const [desdeDia, setDesdeDia] = useState(hoy);
  const [hastaDia, setHastaDia] = useState(hoy);
  const [diaCompleto, setDiaCompleto] = useState(true);
  const [desdeHora, setDesdeHora] = useState("09:00");
  const [hastaHora, setHastaHora] = useState("13:00");
  const [motivo, setMotivo] = useState("");

  const q = useQuery({
    queryKey: ["n", negocio.id, "bloqueos", profesionalId],
    queryFn: () => api<Bloqueo[]>(`/admin/profesionales/${profesionalId}/bloqueos`),
  });
  const futuros = (q.data ?? []).filter((b) => new Date(b.hasta) > new Date());

  const crear = useMutacion(
    (data: object) => api<Bloqueo>(`/admin/profesionales/${profesionalId}/bloqueos`, { method: "POST", json: data }),
    ["bloqueos"],
  );
  const borrar = useMutacion((id: number) => api(`/admin/bloqueos/${id}`, { method: "DELETE" }), ["bloqueos"]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    const desde = aIsoEnZona(desdeDia, diaCompleto ? "00:00" : desdeHora, tz);
    // "Día completo" hasta las 00:00 del día siguiente
    const hasta = diaCompleto
      ? aIsoEnZona(sumarDias(hastaDia, 1), "00:00", tz)
      : aIsoEnZona(hastaDia, hastaHora, tz);
    await crear.mutateAsync({ desde, hasta, motivo: motivo || null });
    avisar("Bloqueo agregado");
    setMotivo("");
    setAbierto(false);
  }

  return (
    <Tarjeta className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-slate-900">Ausencias y bloqueos</h2>
          <p className="mt-1 text-sm text-slate-500">Vacaciones, feriados o ratos en que no atiende. Los turnos existentes no se cancelan solos.</p>
        </div>
        <Boton variante="secundario" onClick={() => setAbierto(true)}>
          <CalendarOff className="size-4" /> Agregar
        </Boton>
      </div>
      {futuros.length > 0 && (
        <ul className="mt-4 divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
          {futuros.map((b) => (
            <li key={b.id} className="flex items-center gap-3 px-4 py-2.5 text-sm">
              <span className="flex-1">
                <span className="font-medium text-slate-900">
                  {fechaHoraCorta(b.desde, tz)} → {fechaHoraCorta(b.hasta, tz)}
                </span>
                {b.motivo && <span className="text-slate-500"> · {b.motivo}</span>}
              </span>
              <button
                onClick={async () => {
                  await borrar.mutateAsync(b.id);
                  avisar("Bloqueo eliminado");
                }}
                className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-red-600"
                aria-label="Eliminar bloqueo"
              >
                <Trash2 className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <Modal
        abierto={abierto}
        onCerrar={() => setAbierto(false)}
        titulo="Agregar ausencia"
        pie={
          <>
            <Boton variante="secundario" onClick={() => setAbierto(false)}>
              Cancelar
            </Boton>
            <Boton type="submit" form="form-bloqueo" cargando={crear.isPending}>
              Guardar
            </Boton>
          </>
        }
      >
        <form id="form-bloqueo" onSubmit={enviar} className="space-y-4">
          <label className="flex items-center gap-3 text-sm font-medium text-slate-700">
            <Interruptor etiqueta="Días completos" activo={diaCompleto} onChange={setDiaCompleto} /> Días completos
          </label>
          <div className="grid grid-cols-2 gap-4">
            <Campo etiqueta="Desde">
              {(id) => <Input id={id} type="date" required value={desdeDia} onChange={(e) => { setDesdeDia(e.target.value); if (e.target.value > hastaDia) setHastaDia(e.target.value); }} />}
            </Campo>
            <Campo etiqueta="Hasta">{(id) => <Input id={id} type="date" required min={desdeDia} value={hastaDia} onChange={(e) => setHastaDia(e.target.value)} />}</Campo>
            {!diaCompleto && (
              <>
                <Campo etiqueta="Hora desde">{(id) => <Input id={id} type="time" required value={desdeHora} onChange={(e) => setDesdeHora(e.target.value)} />}</Campo>
                <Campo etiqueta="Hora hasta">{(id) => <Input id={id} type="time" required value={hastaHora} onChange={(e) => setHastaHora(e.target.value)} />}</Campo>
              </>
            )}
          </div>
          <Campo etiqueta="Motivo (opcional)">{(id) => <Input id={id} placeholder="Vacaciones" value={motivo} onChange={(e) => setMotivo(e.target.value)} />}</Campo>
          <MensajeError error={crear.error} />
        </form>
      </Modal>
    </Tarjeta>
  );
}
