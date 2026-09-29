import { Clock, Pencil, Plus, Scissors } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Boton, Campo, Cargando, Encabezado, Etiqueta, Input, Interruptor, MensajeError, Modal, Tarjeta, Textarea, useAvisos, Vacio } from "../components/ui";
import { api, type Servicio } from "../lib/api";
import { useMutacion, useProfesionales, useServicios } from "../lib/datos";
import { useNegocio } from "../lib/sesion";

const precioFmt = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 });

export function Servicios() {
  const serviciosQ = useServicios();
  const profesionales = useProfesionales().data ?? [];
  const [editando, setEditando] = useState<Servicio | "nuevo" | null>(null);
  const servicios = serviciosQ.data ?? [];
  const nombreProf = (id: number) => profesionales.find((p) => p.id === id)?.nombre ?? "";

  return (
    <>
      <Encabezado
        titulo="Servicios"
        descripcion="Lo que tus clientes pueden reservar, con su duración y quién lo atiende."
        acciones={
          <Boton onClick={() => setEditando("nuevo")}>
            <Plus className="size-4" /> Nuevo servicio
          </Boton>
        }
      />
      {serviciosQ.isPending ? (
        <Cargando />
      ) : servicios.length === 0 ? (
        <Tarjeta>
          <Vacio
            icono={<Scissors className="size-6" />}
            titulo="Todavía no hay servicios"
            texto="Por ejemplo: Consulta, Limpieza, Corte de pelo."
            accion={<Boton onClick={() => setEditando("nuevo")}>Agregar servicio</Boton>}
          />
        </Tarjeta>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {servicios.map((s) => (
            <Tarjeta key={s.id} className="flex flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <h3 className={s.activo ? "font-semibold text-slate-900" : "font-semibold text-slate-400"}>{s.nombre}</h3>
                <button onClick={() => setEditando(s)} className="-mt-1 -mr-1 rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label={`Editar ${s.nombre}`}>
                  <Pencil className="size-4" />
                </button>
              </div>
              {s.descripcion && <p className="mt-1 line-clamp-2 text-sm text-slate-500">{s.descripcion}</p>}
              <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                <span className="inline-flex items-center gap-1 text-slate-600">
                  <Clock className="size-3.5" /> {s.duracion_min} min
                </span>
                {s.precio && <span className="font-medium text-slate-900">· {precioFmt.format(Number(s.precio))}</span>}
                {!s.activo && <Etiqueta>Pausado</Etiqueta>}
              </div>
              <div className="mt-auto pt-4">
                {s.profesional_ids.length === 0 ? (
                  <Etiqueta color="ambar">Sin profesionales asignados</Etiqueta>
                ) : (
                  <p className="text-xs text-slate-500">{s.profesional_ids.map(nombreProf).join(", ")}</p>
                )}
              </div>
            </Tarjeta>
          ))}
        </div>
      )}
      <EditarServicio servicio={editando} onCerrar={() => setEditando(null)} />
    </>
  );
}

function EditarServicio({ servicio, onCerrar }: { servicio: Servicio | "nuevo" | null; onCerrar: () => void }) {
  const negocio = useNegocio();
  const avisar = useAvisos();
  const profesionales = (useProfesionales().data ?? []).filter((p) => p.activo);
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [duracion, setDuracion] = useState(30);
  const [precio, setPrecio] = useState("");
  const [activo, setActivo] = useState(true);
  const [profIds, setProfIds] = useState<number[]>([]);
  const esNuevo = servicio === "nuevo";

  useEffect(() => {
    if (!servicio) return;
    const s = servicio === "nuevo" ? null : servicio;
    setNombre(s?.nombre ?? "");
    setDescripcion(s?.descripcion ?? "");
    setDuracion(s?.duracion_min ?? 30);
    setPrecio(s?.precio ? String(Number(s.precio)) : "");
    setActivo(s?.activo ?? true);
    setProfIds(s?.profesional_ids ?? profesionales.map((p) => p.id));
  }, [servicio]);

  const guardar = useMutacion(
    (data: object) =>
      esNuevo
        ? api<Servicio>(`/admin/negocios/${negocio.id}/servicios`, { method: "POST", json: data })
        : api<Servicio>(`/admin/servicios/${(servicio as Servicio).id}`, { method: "PATCH", json: data }),
    ["servicios"],
  );

  async function enviar(e: FormEvent) {
    e.preventDefault();
    await guardar.mutateAsync({
      nombre,
      descripcion: descripcion || null,
      duracion_min: duracion,
      precio: precio === "" ? null : precio,
      activo,
      profesional_ids: profIds,
    });
    avisar(esNuevo ? "Servicio creado" : "Servicio guardado");
    cerrar();
  }

  function cerrar() {
    guardar.reset();
    onCerrar();
  }

  return (
    <Modal
      abierto={!!servicio}
      onCerrar={cerrar}
      titulo={esNuevo ? "Nuevo servicio" : "Editar servicio"}
      pie={
        <>
          <Boton variante="secundario" onClick={cerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" form="form-servicio" cargando={guardar.isPending}>
            Guardar
          </Boton>
        </>
      }
    >
      <form id="form-servicio" onSubmit={enviar} className="space-y-4">
        <Campo etiqueta="Nombre">{(id) => <Input id={id} required value={nombre} onChange={(e) => setNombre(e.target.value)} />}</Campo>
        <Campo etiqueta="Descripción (opcional)" ayuda="El bot la usa para responder consultas sobre el servicio.">
          {(id) => <Textarea id={id} rows={2} value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />}
        </Campo>
        <div className="grid grid-cols-2 gap-4">
          <Campo etiqueta="Duración (minutos)">
            {(id) => <Input id={id} type="number" required min={5} max={600} step={5} value={duracion} onChange={(e) => setDuracion(Number(e.target.value))} />}
          </Campo>
          <Campo etiqueta="Precio (opcional)">
            {(id) => <Input id={id} type="number" min={0} step="0.01" placeholder="Sin informar" value={precio} onChange={(e) => setPrecio(e.target.value)} />}
          </Campo>
        </div>
        <fieldset>
          <legend className="mb-2 text-sm font-medium text-slate-700">¿Quién lo atiende?</legend>
          {profesionales.length === 0 ? (
            <p className="text-sm text-slate-500">Primero cargá profesionales.</p>
          ) : (
            <div className="space-y-2">
              {profesionales.map((p) => (
                <label key={p.id} className="flex items-center gap-2.5 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    className="size-4 rounded border-slate-300 text-marca-600"
                    checked={profIds.includes(p.id)}
                    onChange={(e) => setProfIds((ids) => (e.target.checked ? [...ids, p.id] : ids.filter((x) => x !== p.id)))}
                  />
                  {p.nombre}
                </label>
              ))}
            </div>
          )}
        </fieldset>
        <label className="flex items-center gap-3 text-sm text-slate-700">
          <Interruptor etiqueta="Disponible para reservar" activo={activo} onChange={setActivo} /> Disponible para reservar
        </label>
        <MensajeError error={guardar.error} />
      </form>
    </Modal>
  );
}
