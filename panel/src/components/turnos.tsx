import type { EstadoTurno } from "../lib/api";
import { Etiqueta } from "./ui";

export const ESTADOS: Record<EstadoTurno, { texto: string; color: "azul" | "verde" | "rojo" | "gris" }> = {
  confirmado: { texto: "Confirmado", color: "azul" },
  asistio: { texto: "Asistió", color: "verde" },
  ausente: { texto: "Ausente", color: "rojo" },
  cancelado: { texto: "Cancelado", color: "gris" },
};

export function EtiquetaEstado({ estado }: { estado: EstadoTurno }) {
  const e = ESTADOS[estado];
  return <Etiqueta color={e.color}>{e.texto}</Etiqueta>;
}

/** 5491155554444 → +54 9 11 5555-4444 (aprox., para lectura) */
export function telefonoLegible(t: string): string {
  const m = t.match(/^54(9?)(\d{2,4})(\d{3,4})(\d{4})$/);
  if (m) return `+54 ${m[1] ? "9 " : ""}${m[2]} ${m[3]}-${m[4]}`;
  return `+${t}`;
}
