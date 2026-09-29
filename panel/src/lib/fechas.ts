// Fechas siempre en la zona horaria del negocio (no la del navegador).

export const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

function partes(fecha: Date, tz: string) {
  const p = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(fecha);
  const get = (t: string) => p.find((x) => x.type === t)!.value;
  return { y: get("year"), m: get("month"), d: get("day"), h: get("hour"), min: get("minute") };
}

/** "YYYY-MM-DD" de hoy en la zona del negocio. */
export function hoyEn(tz: string): string {
  const { y, m, d } = partes(new Date(), tz);
  return `${y}-${m}-${d}`;
}

/** "YYYY-MM-DD" de un instante ISO, en la zona del negocio. */
export function diaDe(iso: string, tz: string): string {
  const { y, m, d } = partes(new Date(iso), tz);
  return `${y}-${m}-${d}`;
}

/** Minutos desde las 00:00 en la zona del negocio. */
export function minutosDelDia(iso: string, tz: string): number {
  const { h, min } = partes(new Date(iso), tz);
  return Number(h) * 60 + Number(min);
}

export function hora(iso: string, tz: string): string {
  const { h, min } = partes(new Date(iso), tz);
  return `${h}:${min}`;
}

export function sumarDias(dia: string, n: number): string {
  const [y, m, d] = dia.split("-").map(Number);
  const f = new Date(Date.UTC(y, m - 1, d + n));
  return f.toISOString().slice(0, 10);
}

/** 0 = lunes … 6 = domingo, igual que el backend. */
export function diaSemana(dia: string): number {
  const [y, m, d] = dia.split("-").map(Number);
  return (new Date(Date.UTC(y, m - 1, d)).getUTCDay() + 6) % 7;
}

export function fechaLarga(dia: string): string {
  const [y, m, d] = dia.split("-").map(Number);
  return new Intl.DateTimeFormat("es-AR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(y, m - 1, d)));
}

export function fechaHoraCorta(iso: string, tz: string): string {
  return new Intl.DateTimeFormat("es-AR", {
    timeZone: tz,
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(iso));
}

/** Convierte una fecha y hora "de pared" del negocio a ISO con offset correcto. */
export function aIsoEnZona(dia: string, horaHHMM: string, tz: string): string {
  const [y, m, d] = dia.split("-").map(Number);
  const [h, min] = horaHHMM.split(":").map(Number);
  const comoUtc = Date.UTC(y, m - 1, d, h, min);
  // Offset de la zona en ese instante (dos pasadas cubren cambios de horario)
  let ts = comoUtc;
  for (let i = 0; i < 2; i++) {
    const p = partes(new Date(ts), tz);
    const visto = Date.UTC(+p.y, +p.m - 1, +p.d, +p.h, +p.min);
    ts = comoUtc - (visto - ts);
  }
  return new Date(ts).toISOString();
}

export function hhmm(horaBackend: string): string {
  return horaBackend.slice(0, 5);
}
