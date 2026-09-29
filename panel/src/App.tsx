import { Building2 } from "lucide-react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { Layout } from "./components/Layout";
import { Cargando, Tarjeta, Vacio } from "./components/ui";
import { useSesion } from "./lib/sesion";
import { Agenda } from "./pages/Agenda";
import { Configuracion } from "./pages/Configuracion";
import { Inicio } from "./pages/Inicio";
import { Login } from "./pages/Login";
import { Negocios } from "./pages/Negocios";
import { ProbarBot } from "./pages/ProbarBot";
import { Profesionales } from "./pages/Profesionales";
import { Servicios } from "./pages/Servicios";

function SinNegocio() {
  const { esAdmin } = useSesion();
  return (
    <Tarjeta>
      <Vacio
        icono={<Building2 className="size-6" />}
        titulo={esAdmin ? "Todavía no hay negocios" : "Tu usuario no tiene un negocio asignado"}
        texto={esAdmin ? "Creá el primero desde la sección Negocios." : "Pedile al administrador que lo revise."}
      />
    </Tarjeta>
  );
}

export default function App() {
  const { usuario, cargando, negocio, esAdmin } = useSesion();

  if (cargando) return <Cargando />;
  if (!usuario) return <Login />;

  const conNegocio = (el: React.ReactNode) => (negocio ? el : <SinNegocio />);

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={conNegocio(<Inicio />)} />
          <Route path="agenda" element={conNegocio(<Agenda />)} />
          <Route path="profesionales" element={conNegocio(<Profesionales />)} />
          <Route path="servicios" element={conNegocio(<Servicios />)} />
          <Route path="probar" element={conNegocio(<ProbarBot />)} />
          <Route path="configuracion" element={conNegocio(<Configuracion />)} />
          {esAdmin && <Route path="negocios" element={<Negocios />} />}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
