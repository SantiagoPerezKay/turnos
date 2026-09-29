import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Boton, Campo, cx, Input, MensajeError, Modal, Select, Textarea, useAvisos } from "../components/ui";
import { api, type Slot, type Turno } from "../lib/api";
import { useMutacion, useProfesionales, useServicios } from "../lib/datos";
import { hora, hoyEn } from "../lib/fechas";
import { useNegocio } from "../lib/sesion";

export function NuevoTurno({ abierto, onCerrar, diaInicial }: { abierto: boolean; onCerrar: () => void; diaInicial: string }) {
  const negocio = useNegocio();
  const tz = negocio.zona_horaria;
  const avisar = useAvisos();
  const servicios = (useServicios().data ?? []).filter((s) => s.activo);
  const profesionales = useProfesionales().data ?? [];

  const [servicioId, setServicioId] = useState<number | "">("");
  const [profesionalId, setProfesionalId] = useState<number | "">("");
  const [dia, setDia] = useState(diaInicial);
  const [slot, setSlot] = useState<Slot | null>(null);
  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");
  const [notas, setNotas] = useState("");

  useEffect(() => {
    if (abierto) {
      setDia(diaInicial);
      setSlot(null);
    }
  }, [abierto, diaInicial]);
  useEffect(() => setSlot(null), [servicioId, profesionalId, dia]);

  const servicio = servicios.find((s) => s.id === servicioId);
  const profesDelServicio = profesionales.filter((p) => p.activo && servicio?.profesional_ids.includes(p.id));

  const slots = useQuery({
    queryKey: ["n", negocio.id, "disponibilidad", servicioId, profesionalId, dia],
    queryFn: () =>
      api<Slot[]>(
        `/admin/negocios/${negocio.id}/disponibilidad?servicio_id=${servicioId}&desde=${dia}&hasta=${dia}` +
          (profesionalId ? `&profesional_id=${profesionalId}` : ""),
      ),
    enabled: abierto && !!servicioId && !!dia,
    staleTime: 0,
  });

  const crear = useMutacion((data: object) =>
    api<Turno>(`/admin/negocios/${negocio.id}/turnos`, { method: "POST", json: data }),
  );

  function cerrar() {
    crear.reset();
    setNombre("");
    setTelefono("");
    setNotas("");
    onCerrar();
  }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!slot) return;
    await crear.mutateAsync({
      servicio_id: servicioId,
      profesional_id: slot.profesional_id,
      inicio: slot.inicio,
      cliente_nombre: nombre,
      cliente_telefono: telefono,
      notas: notas || null,
    });
    avisar(`Turno reservado para ${nombre} a las ${hora(slot.inicio, tz)}`);
    cerrar();
  }

  // Agrupa horarios por profesional
  const porProfesional = new Map<string, Slot[]>();
  for (const s of slots.data ?? []) porProfesional.set(s.profesional, [...(porProfesional.get(s.profesional) ?? []), s]);

  return (
    <Modal
      abierto={abierto}
      onCerrar={cerrar}
      titulo="Nuevo turno"
      ancho="max-w-xl"
      pie={
        <>
          <Boton variante="secundario" onClick={cerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" form="form-nuevo-turno" cargando={crear.isPending} disabled={!slot || !nombre || !telefono}>
            Reservar
          </Boton>
        </>
      }
    >
      <form id="form-nuevo-turno" onSubmit={enviar} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Servicio">
            {(id) => (
              <Select id={id} required value={servicioId} onChange={(e) => { setServicioId(Number(e.target.value) || ""); setProfesionalId(""); }}>
                <option value="">Elegí un servicio</option>
                {servicios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nombre} ({s.duracion_min} min)
                  </option>
                ))}
              </Select>
            )}
          </Campo>
          <Campo etiqueta="Profesional">
            {(id) => (
              <Select id={id} value={profesionalId} disabled={!servicio} onChange={(e) => setProfesionalId(Number(e.target.value) || "")}>
                <option value="">Cualquiera</option>
                {profesDelServicio.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nombre}
                  </option>
                ))}
              </Select>
            )}
          </Campo>
        </div>

        <Campo etiqueta="Día">
          {(id) => <Input id={id} type="date" required min={hoyEn(tz)} value={dia} onChange={(e) => setDia(e.target.value)} />}
        </Campo>

        {servicioId !== "" && (
          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">Horario</p>
            {slots.isPending ? (
              <p className="text-sm text-slate-500">Buscando horarios…</p>
            ) : slots.error ? (
              <MensajeError error={slots.error} />
            ) : porProfesional.size === 0 ? (
              <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-500">No hay horarios libres ese día.</p>
            ) : (
              <div className="space-y-3">
                {[...porProfesional].map(([prof, lista]) => (
                  <div key={prof}>
                    {porProfesional.size > 1 && <p className="mb-1.5 text-xs font-medium text-slate-500">{prof}</p>}
                    <div className="flex flex-wrap gap-1.5">
                      {lista.map((s) => {
                        const elegido = slot?.inicio === s.inicio && slot.profesional_id === s.profesional_id;
                        return (
                          <button
                            type="button"
                            key={`${s.profesional_id}-${s.inicio}`}
                            onClick={() => setSlot(s)}
                            aria-pressed={elegido}
                            className={cx(
                              "rounded-md px-2.5 py-1.5 text-sm font-medium tabular-nums ring-1 transition-colors",
                              elegido ? "bg-marca-700 text-white ring-marca-700" : "bg-white text-slate-700 ring-slate-300 hover:bg-marca-50 hover:ring-marca-500",
                            )}
                          >
                            {hora(s.inicio, tz)}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {slot && (
          <div className="grid gap-4 border-t border-slate-200 pt-4 sm:grid-cols-2">
            <Campo etiqueta="Nombre del cliente">
              {(id) => <Input id={id} required value={nombre} onChange={(e) => setNombre(e.target.value)} />}
            </Campo>
            <Campo etiqueta="WhatsApp" ayuda="Con código de país, p. ej. 54 9 11 5555 4444">
              {(id) => <Input id={id} type="tel" required value={telefono} onChange={(e) => setTelefono(e.target.value)} />}
            </Campo>
            <Campo etiqueta="Notas (opcional)" className="sm:col-span-2">
              {(id) => <Textarea id={id} rows={2} value={notas} onChange={(e) => setNotas(e.target.value)} />}
            </Campo>
          </div>
        )}
        <MensajeError error={crear.error} />
      </form>
    </Modal>
  );
}
