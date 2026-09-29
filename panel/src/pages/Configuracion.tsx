import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Boton, Campo, Encabezado, Etiqueta, Input, Interruptor, MensajeError, Modal, Select, Tarjeta, Textarea, useAvisos } from "../components/ui";
import { api, type Negocio, type UsuarioPanel } from "../lib/api";
import { useMutacion } from "../lib/datos";
import { useNegocio, useSesion } from "../lib/sesion";

const ZONAS = [
  "America/Argentina/Buenos_Aires",
  "America/Montevideo",
  "America/Santiago",
  "America/Asuncion",
  "America/La_Paz",
  "America/Lima",
  "America/Bogota",
  "America/Mexico_City",
  "Europe/Madrid",
];

function Seccion({ titulo, descripcion, children }: { titulo: string; descripcion?: string; children: React.ReactNode }) {
  return (
    <Tarjeta className="grid gap-6 p-5 md:grid-cols-[14rem_1fr] md:p-6">
      <div>
        <h2 className="font-semibold text-slate-900">{titulo}</h2>
        {descripcion && <p className="mt-1 text-sm text-slate-500">{descripcion}</p>}
      </div>
      <div>{children}</div>
    </Tarjeta>
  );
}

function useGuardarNegocio() {
  const negocio = useNegocio();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Negocio> & { wa_access_token?: string }) =>
      api<Negocio>(`/admin/negocios/${negocio.id}`, { method: "PATCH", json: data }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["negocios"] }),
  });
}

export function Configuracion() {
  const { esAdmin } = useSesion();
  return (
    <>
      <Encabezado titulo="Configuración" descripcion="Datos del negocio, reglas de reserva y accesos." />
      <div className="space-y-6">
        <DatosNegocio />
        <ReglasReserva />
        <WhatsApp editable={esAdmin} />
        <Usuarios />
        <CambiarPassword />
      </div>
    </>
  );
}

function DatosNegocio() {
  const negocio = useNegocio();
  const avisar = useAvisos();
  const guardar = useGuardarNegocio();
  const [f, setF] = useState(negocio);
  useEffect(() => setF(negocio), [negocio]);
  const set = (k: keyof Negocio) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  async function enviar(e: FormEvent) {
    e.preventDefault();
    await guardar.mutateAsync({
      nombre: f.nombre,
      rubro: f.rubro || null,
      direccion: f.direccion || null,
      telefono_contacto: f.telefono_contacto || null,
      info_extra: f.info_extra || null,
      zona_horaria: f.zona_horaria,
    });
    avisar("Datos guardados");
  }

  return (
    <Seccion titulo="Datos del negocio" descripcion="El bot usa esta información para responder a tus clientes.">
      <form onSubmit={enviar} className="grid gap-4 sm:grid-cols-2">
        <Campo etiqueta="Nombre">{(id) => <Input id={id} required value={f.nombre} onChange={set("nombre")} />}</Campo>
        <Campo etiqueta="Rubro">{(id) => <Input id={id} placeholder="Consultorio odontológico" value={f.rubro ?? ""} onChange={set("rubro")} />}</Campo>
        <Campo etiqueta="Dirección">{(id) => <Input id={id} value={f.direccion ?? ""} onChange={set("direccion")} />}</Campo>
        <Campo etiqueta="Teléfono para consultas" ayuda="El bot lo ofrece cuando no puede resolver algo.">
          {(id) => <Input id={id} value={f.telefono_contacto ?? ""} onChange={set("telefono_contacto")} />}
        </Campo>
        <Campo etiqueta="Información para el bot" className="sm:col-span-2" ayuda="Obras sociales, formas de pago, cómo llegar, qué traer… Todo lo que el bot deba saber.">
          {(id) => <Textarea id={id} rows={4} value={f.info_extra ?? ""} onChange={set("info_extra")} />}
        </Campo>
        <Campo etiqueta="Zona horaria">
          {(id) => (
            <Select id={id} value={f.zona_horaria} onChange={set("zona_horaria")}>
              {[...new Set([f.zona_horaria, ...ZONAS])].map((z) => (
                <option key={z} value={z}>
                  {z.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          )}
        </Campo>
        <div className="sm:col-span-2">
          <MensajeError error={guardar.error} />
          <div className="mt-2 flex justify-end">
            <Boton type="submit" cargando={guardar.isPending}>
              Guardar
            </Boton>
          </div>
        </div>
      </form>
    </Seccion>
  );
}

function ReglasReserva() {
  const negocio = useNegocio();
  const avisar = useAvisos();
  const guardar = useGuardarNegocio();
  const [r, setR] = useState(negocio);
  useEffect(() => setR(negocio), [negocio]);
  const num = (k: keyof Negocio) => (e: { target: { value: string } }) => setR({ ...r, [k]: Number(e.target.value) });

  async function enviar(e: FormEvent) {
    e.preventDefault();
    await guardar.mutateAsync({
      intervalo_turnos_min: r.intervalo_turnos_min,
      anticipacion_min_minutos: r.anticipacion_min_minutos,
      dias_max_reserva: r.dias_max_reserva,
      horas_min_cancelacion: r.horas_min_cancelacion,
    });
    avisar("Reglas guardadas");
  }

  return (
    <Seccion titulo="Reglas de reserva" descripcion="Cómo se arman los horarios que ofrece el bot.">
      <form onSubmit={enviar} className="grid gap-4 sm:grid-cols-2">
        <Campo etiqueta="Turnos cada (minutos)" ayuda="Cada cuánto empieza un turno posible: 15, 30…">
          {(id) => <Input id={id} type="number" min={5} max={240} step={5} value={r.intervalo_turnos_min} onChange={num("intervalo_turnos_min")} />}
        </Campo>
        <Campo etiqueta="Anticipación mínima (minutos)" ayuda="No ofrece turnos que empiecen antes de este margen.">
          {(id) => <Input id={id} type="number" min={0} step={15} value={r.anticipacion_min_minutos} onChange={num("anticipacion_min_minutos")} />}
        </Campo>
        <Campo etiqueta="Reservar hasta (días)" ayuda="Qué tan adelante se puede sacar turno.">
          {(id) => <Input id={id} type="number" min={1} max={365} value={r.dias_max_reserva} onChange={num("dias_max_reserva")} />}
        </Campo>
        <Campo etiqueta="Cancelar hasta (horas antes)">
          {(id) => <Input id={id} type="number" min={0} value={r.horas_min_cancelacion} onChange={num("horas_min_cancelacion")} />}
        </Campo>
        <div className="sm:col-span-2">
          <MensajeError error={guardar.error} />
          <div className="mt-2 flex justify-end">
            <Boton type="submit" cargando={guardar.isPending}>
              Guardar
            </Boton>
          </div>
        </div>
      </form>
    </Seccion>
  );
}

function WhatsApp({ editable }: { editable: boolean }) {
  const negocio = useNegocio();
  const avisar = useAvisos();
  const guardar = useGuardarNegocio();
  const [phoneId, setPhoneId] = useState(negocio.wa_phone_number_id ?? "");
  const [token, setToken] = useState("");
  useEffect(() => setPhoneId(negocio.wa_phone_number_id ?? ""), [negocio]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    await guardar.mutateAsync({ wa_phone_number_id: phoneId || null, ...(token ? { wa_access_token: token } : {}) });
    setToken("");
    avisar("WhatsApp actualizado");
  }

  return (
    <Seccion titulo="WhatsApp" descripcion="Número de WhatsApp Business por el que escriben tus clientes.">
      <div className="mb-4">
        {negocio.wa_phone_number_id ? <Etiqueta color="verde">Conectado</Etiqueta> : <Etiqueta color="ambar">Sin conectar</Etiqueta>}
      </div>
      {editable ? (
        <form onSubmit={enviar} className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Phone Number ID" ayuda="Meta → WhatsApp → Configuración de la API.">
            {(id) => <Input id={id} inputMode="numeric" value={phoneId} onChange={(e) => setPhoneId(e.target.value.trim())} />}
          </Campo>
          <Campo etiqueta="Token propio (opcional)" ayuda="Solo si este número usa otro token que el global. No se vuelve a mostrar.">
            {(id) => <Input id={id} type="password" autoComplete="off" placeholder="Sin cambios" value={token} onChange={(e) => setToken(e.target.value)} />}
          </Campo>
          <div className="sm:col-span-2">
            <MensajeError error={guardar.error} />
            <div className="mt-2 flex justify-end">
              <Boton type="submit" cargando={guardar.isPending}>
                Guardar
              </Boton>
            </div>
          </div>
        </form>
      ) : (
        <p className="text-sm text-slate-500">La conexión con WhatsApp la configura el administrador. Si necesitás cambiar el número, contactalo.</p>
      )}
    </Seccion>
  );
}

function Usuarios() {
  const negocio = useNegocio();
  const { esAdmin, usuario } = useSesion();
  const avisar = useAvisos();
  const [creando, setCreando] = useState(false);
  const [nuevo, setNuevo] = useState({ nombre: "", email: "", password: "" });

  const q = useQuery({
    queryKey: ["n", negocio.id, "usuarios"],
    queryFn: () => api<UsuarioPanel[]>(`/admin/negocios/${negocio.id}/usuarios`),
  });
  const crear = useMutacion((data: object) => api(`/admin/negocios/${negocio.id}/usuarios`, { method: "POST", json: data }), ["usuarios"]);
  const actualizar = useMutacion(({ id, ...data }: { id: number; activo: boolean }) => api(`/admin/usuarios/${id}`, { method: "PATCH", json: data }), ["usuarios"]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    await crear.mutateAsync(nuevo);
    avisar(`Usuario ${nuevo.email} creado`);
    setNuevo({ nombre: "", email: "", password: "" });
    setCreando(false);
  }

  return (
    <Seccion titulo="Usuarios" descripcion="Personas que pueden entrar a este panel.">
      <ul className="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200">
        {(q.data ?? []).map((u) => (
          <li key={u.id} className="flex items-center gap-3 px-4 py-3">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-900">
                {u.nombre} {u.id === usuario?.id && <span className="font-normal text-slate-400">(vos)</span>}
              </p>
              <p className="truncate text-xs text-slate-500">{u.email}</p>
            </div>
            {esAdmin ? (
              <Interruptor etiqueta={`Acceso de ${u.nombre}`} activo={u.activo} onChange={(activo) => actualizar.mutate({ id: u.id, activo })} />
            ) : (
              !u.activo && <Etiqueta>Sin acceso</Etiqueta>
            )}
          </li>
        ))}
        {q.data?.length === 0 && <li className="px-4 py-3 text-sm text-slate-500">Todavía no hay usuarios para este negocio.</li>}
      </ul>
      {esAdmin && (
        <div className="mt-4 flex justify-end">
          <Boton variante="secundario" onClick={() => setCreando(true)}>
            Agregar usuario
          </Boton>
        </div>
      )}
      <Modal
        abierto={creando}
        onCerrar={() => setCreando(false)}
        titulo="Nuevo usuario"
        pie={
          <>
            <Boton variante="secundario" onClick={() => setCreando(false)}>
              Cancelar
            </Boton>
            <Boton type="submit" form="form-usuario" cargando={crear.isPending}>
              Crear
            </Boton>
          </>
        }
      >
        <form id="form-usuario" onSubmit={enviar} className="space-y-4">
          <Campo etiqueta="Nombre">{(id) => <Input id={id} required value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} />}</Campo>
          <Campo etiqueta="Email">{(id) => <Input id={id} type="email" required value={nuevo.email} onChange={(e) => setNuevo({ ...nuevo, email: e.target.value })} />}</Campo>
          <Campo etiqueta="Contraseña inicial" ayuda="Mínimo 8 caracteres. La persona puede cambiarla después.">
            {(id) => <Input id={id} type="text" required minLength={8} autoComplete="off" value={nuevo.password} onChange={(e) => setNuevo({ ...nuevo, password: e.target.value })} />}
          </Campo>
          <MensajeError error={crear.error} />
        </form>
      </Modal>
    </Seccion>
  );
}

function CambiarPassword() {
  const { usuario } = useSesion();
  const avisar = useAvisos();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [repetir, setRepetir] = useState("");
  const cambiar = useMutation({ mutationFn: (data: object) => api("/auth/password", { method: "POST", json: data }) });

  if (!usuario?.id) return null;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    await cambiar.mutateAsync({ actual, nueva });
    setActual("");
    setNueva("");
    setRepetir("");
    avisar("Contraseña actualizada");
  }

  const noCoinciden = repetir.length > 0 && nueva !== repetir;

  return (
    <Seccion titulo="Tu contraseña">
      <form onSubmit={enviar} className="grid gap-4 sm:grid-cols-3">
        <Campo etiqueta="Actual">{(id) => <Input id={id} type="password" required autoComplete="current-password" value={actual} onChange={(e) => setActual(e.target.value)} />}</Campo>
        <Campo etiqueta="Nueva">{(id) => <Input id={id} type="password" required minLength={8} autoComplete="new-password" value={nueva} onChange={(e) => setNueva(e.target.value)} />}</Campo>
        <Campo etiqueta="Repetir nueva" ayuda={noCoinciden ? <span className="text-red-600">No coinciden</span> : undefined}>
          {(id) => <Input id={id} type="password" required autoComplete="new-password" value={repetir} onChange={(e) => setRepetir(e.target.value)} />}
        </Campo>
        <div className="sm:col-span-3">
          <MensajeError error={cambiar.error} />
          <div className="mt-2 flex justify-end">
            <Boton type="submit" cargando={cambiar.isPending} disabled={noCoinciden || !nueva}>
              Cambiar contraseña
            </Boton>
          </div>
        </div>
      </form>
    </Seccion>
  );
}
