import { useState, type FormEvent } from "react";
import { Boton, Campo, Input, MensajeError } from "../components/ui";
import { useSesion } from "../lib/sesion";

export function Login() {
  const { login } = useSesion();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-gradient-to-b from-marca-50 to-slate-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <img src="/favicon.svg" alt="" className="mx-auto size-12" />
          <h1 className="mt-4 text-2xl font-semibold tracking-tight text-slate-900">Ingresá a tu panel</h1>
          <p className="mt-1 text-sm text-slate-500">Gestioná los turnos que tus clientes sacan por WhatsApp</p>
        </div>
        <form onSubmit={enviar} className="space-y-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <Campo etiqueta="Email">
            {(id) => (
              <Input id={id} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            )}
          </Campo>
          <Campo etiqueta="Contraseña">
            {(id) => (
              <Input
                id={id}
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            )}
          </Campo>
          <MensajeError error={error} />
          <Boton type="submit" cargando={enviando} className="w-full">
            Ingresar
          </Boton>
        </form>
      </div>
    </div>
  );
}
