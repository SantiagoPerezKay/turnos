import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { Boton, Campo, Encabezado, Etiqueta, Input, MensajeError, Modal, Tarjeta, useAvisos, Vacio } from "../components/ui";
import { api, type Negocio } from "../lib/api";
import { useSesion } from "../lib/sesion";

export function Negocios() {
  const { negocios, negocio: activo, elegirNegocio } = useSesion();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const avisar = useAvisos();
  const [creando, setCreando] = useState(false);
  const [nombre, setNombre] = useState("");
  const [rubro, setRubro] = useState("");

  const crear = useMutation({
    mutationFn: (data: object) => api<Negocio>("/admin/negocios", { method: "POST", json: data }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["negocios"] }),
  });

  async function enviar(e: FormEvent) {
    e.preventDefault();
    const n = await crear.mutateAsync({ nombre, rubro: rubro || null });
    avisar(`Negocio “${n.nombre}” creado`);
    setNombre("");
    setRubro("");
    setCreando(false);
    elegirNegocio(n.id);
    navigate("/configuracion");
  }

  return (
    <>
      <Encabezado
        titulo="Negocios"
        descripcion="Todos los negocios que usan el sistema."
        acciones={
          <Boton onClick={() => setCreando(true)}>
            <Plus className="size-4" /> Nuevo negocio
          </Boton>
        }
      />
      <Tarjeta>
        {negocios.length === 0 ? (
          <Vacio icono={<Building2 className="size-6" />} titulo="Todavía no hay negocios" accion={<Boton onClick={() => setCreando(true)}>Crear el primero</Boton>} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {negocios.map((n) => (
              <li key={n.id} className="flex flex-wrap items-center gap-3 px-5 py-4">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-slate-900">{n.nombre}</p>
                  <p className="text-sm text-slate-500">{n.rubro ?? "Sin rubro"}</p>
                </div>
                {n.wa_phone_number_id ? <Etiqueta color="verde">WhatsApp</Etiqueta> : <Etiqueta color="ambar">Sin WhatsApp</Etiqueta>}
                {!n.activo && <Etiqueta color="rojo">Inactivo</Etiqueta>}
                {activo?.id === n.id ? (
                  <Etiqueta color="azul">Seleccionado</Etiqueta>
                ) : (
                  <Boton
                    variante="secundario"
                    className="py-1.5"
                    onClick={() => {
                      elegirNegocio(n.id);
                      navigate("/");
                    }}
                  >
                    Abrir
                  </Boton>
                )}
              </li>
            ))}
          </ul>
        )}
      </Tarjeta>

      <Modal
        abierto={creando}
        onCerrar={() => setCreando(false)}
        titulo="Nuevo negocio"
        pie={
          <>
            <Boton variante="secundario" onClick={() => setCreando(false)}>
              Cancelar
            </Boton>
            <Boton type="submit" form="form-negocio" cargando={crear.isPending}>
              Crear
            </Boton>
          </>
        }
      >
        <form id="form-negocio" onSubmit={enviar} className="space-y-4">
          <Campo etiqueta="Nombre">{(id) => <Input id={id} required autoFocus value={nombre} onChange={(e) => setNombre(e.target.value)} />}</Campo>
          <Campo etiqueta="Rubro (opcional)">{(id) => <Input id={id} placeholder="Peluquería, consultorio…" value={rubro} onChange={(e) => setRubro(e.target.value)} />}</Campo>
          <p className="text-sm text-slate-500">Después vas a poder completar los datos, conectar WhatsApp y crear el usuario del negocio.</p>
          <MensajeError error={crear.error} />
        </form>
      </Modal>
    </>
  );
}
