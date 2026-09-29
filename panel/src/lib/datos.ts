// Queries compartidas. Las claves empiezan con "n" + id de negocio (ver elegirNegocio).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Profesional, type Servicio } from "./api";
import { useNegocio } from "./sesion";

export function useProfesionales() {
  const { id } = useNegocio();
  return useQuery({
    queryKey: ["n", id, "profesionales"],
    queryFn: () => api<Profesional[]>(`/admin/negocios/${id}/profesionales`),
  });
}

export function useServicios() {
  const { id } = useNegocio();
  return useQuery({
    queryKey: ["n", id, "servicios"],
    queryFn: () => api<Servicio[]>(`/admin/negocios/${id}/servicios`),
  });
}

/** Mutación que invalida las queries del negocio al terminar. */
export function useMutacion<TIn, TOut = unknown>(fn: (data: TIn) => Promise<TOut>, invalidar: string[] = []) {
  const qc = useQueryClient();
  const { id } = useNegocio();
  return useMutation({
    mutationFn: fn,
    onSuccess: () =>
      Promise.all(
        invalidar.length
          ? invalidar.map((k) => qc.invalidateQueries({ queryKey: ["n", id, k] }))
          : [qc.invalidateQueries({ queryKey: ["n", id] })],
      ),
  });
}
