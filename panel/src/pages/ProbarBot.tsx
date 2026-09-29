import { useQueryClient } from "@tanstack/react-query";
import { RotateCcw, SendHorizontal } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Boton, cx, Encabezado, Tarjeta } from "../components/ui";
import { api } from "../lib/api";
import { useNegocio } from "../lib/sesion";

// Teléfono ficticio del "cliente" de prueba (los turnos que reserve aparecen en la agenda)
const TELEFONO_PRUEBA = "5490000000000";

type Mensaje = { de: "cliente" | "bot"; texto: string; error?: boolean };

/** Formato de WhatsApp: *negrita* y saltos de línea. */
function TextoWhatsApp({ texto }: { texto: string }) {
  return (
    <>
      {texto.split(/(\*[^*\n]+\*)/g).map((parte, i) =>
        parte.startsWith("*") && parte.endsWith("*") && parte.length > 2 ? <strong key={i}>{parte.slice(1, -1)}</strong> : <span key={i}>{parte}</span>,
      )}
    </>
  );
}

export function ProbarBot() {
  const negocio = useNegocio();
  const qc = useQueryClient();
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [texto, setTexto] = useState("");
  const [esperando, setEsperando] = useState(false);
  const finRef = useRef<HTMLDivElement>(null);

  useEffect(() => finRef.current?.scrollIntoView({ behavior: "smooth" }), [mensajes, esperando]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    const t = texto.trim();
    if (!t || esperando) return;
    setTexto("");
    setMensajes((m) => [...m, { de: "cliente", texto: t }]);
    setEsperando(true);
    try {
      const r = await api<{ respuesta: string }>(`/admin/negocios/${negocio.id}/simular`, {
        method: "POST",
        json: { telefono: TELEFONO_PRUEBA, texto: t },
      });
      setMensajes((m) => [...m, { de: "bot", texto: r.respuesta }]);
      qc.invalidateQueries({ queryKey: ["n", negocio.id] }); // por si reservó o canceló
    } catch (err) {
      setMensajes((m) => [...m, { de: "bot", texto: err instanceof Error ? err.message : "Error", error: true }]);
    } finally {
      setEsperando(false);
    }
  }

  async function reiniciar() {
    await api(`/admin/negocios/${negocio.id}/simular/reiniciar`, { method: "POST", json: { telefono: TELEFONO_PRUEBA } });
    setMensajes([]);
  }

  return (
    <>
      <Encabezado
        titulo="Probar el bot"
        descripcion="Chateá como si fueras un cliente. Las reservas son reales y aparecen en la agenda; no se envía nada por WhatsApp."
        acciones={
          <Boton variante="secundario" onClick={reiniciar} disabled={esperando}>
            <RotateCcw className="size-4" /> Nueva conversación
          </Boton>
        }
      />
      <Tarjeta className="mx-auto flex h-[calc(100dvh-14rem)] min-h-96 max-w-2xl flex-col overflow-hidden">
        <div className="flex items-center gap-3 border-b border-slate-200 bg-[#075e54] px-4 py-3 text-white">
          <div className="flex size-9 items-center justify-center rounded-full bg-white/20 font-semibold">{negocio.nombre.charAt(0)}</div>
          <div>
            <p className="text-sm font-semibold">{negocio.nombre}</p>
            <p className="text-xs text-white/70">{esperando ? "escribiendo…" : "en línea"}</p>
          </div>
        </div>

        <div className="flex-1 space-y-2 overflow-y-auto bg-[#efeae2] p-4">
          {mensajes.length === 0 && (
            <div className="mx-auto mt-6 max-w-sm rounded-lg bg-white/80 p-4 text-center text-sm text-slate-600 shadow-sm">
              Probá con algo como: <em>“Hola, quiero sacar un turno para el jueves a la tarde”</em>
            </div>
          )}
          {mensajes.map((m, i) => (
            <div key={i} className={cx("flex", m.de === "cliente" ? "justify-end" : "justify-start")}>
              <div
                className={cx(
                  "max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap shadow-sm",
                  m.de === "cliente" ? "rounded-tr-none bg-[#d9fdd3] text-slate-900" : "rounded-tl-none bg-white text-slate-900",
                  m.error && "bg-red-50 text-red-700",
                )}
              >
                <TextoWhatsApp texto={m.texto} />
              </div>
            </div>
          ))}
          {esperando && (
            <div className="flex">
              <div className="flex gap-1 rounded-lg rounded-tl-none bg-white px-4 py-3 shadow-sm">
                {[0, 150, 300].map((d) => (
                  <span key={d} className="size-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: `${d}ms` }} />
                ))}
              </div>
            </div>
          )}
          <div ref={finRef} />
        </div>

        <form onSubmit={enviar} className="flex gap-2 border-t border-slate-200 bg-slate-50 p-3">
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Escribí un mensaje"
            aria-label="Mensaje"
            className="flex-1 rounded-full border-0 bg-white px-4 py-2 text-sm ring-1 ring-slate-300 focus:ring-2 focus:ring-marca-600 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!texto.trim() || esperando}
            className="flex size-10 items-center justify-center rounded-full bg-[#00a884] text-white disabled:opacity-50"
            aria-label="Enviar"
          >
            <SendHorizontal className="size-4.5" />
          </button>
        </form>
      </Tarjeta>
    </>
  );
}
