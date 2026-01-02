import { api } from '@/lib/api/config';
import { ConflictoOut } from '@/lib/api/conflictos';

// --- Tipos ---
export type SesionAPI = {
  id: number;
  grupo_docente_id: number;
  asignatura_id: number;
  aula_id?: number | null;
  dia_semana: string;
  hora_inicio: string;
  hora_fin: string;
  [key: string]: unknown;
};

export type SesionWithConflictosOut = {
  sesion: SesionAPI;
  conflictos: ConflictoOut[];
};

export type SesionUpdateInput = {
  aula_id?: number | null;
  dia_semana?: string;
  hora_inicio?: string;
  hora_fin?: string;
};

// --- Funciones ---

export async function getSesionConConflictos(id: number): Promise<SesionWithConflictosOut> {
  return api.get(`/v0/docencia/sesiones/${id}`);
}

export async function updateSesion(
  id: number,
  data: SesionUpdateInput
): Promise<SesionWithConflictosOut> {
  return api.patch(`/v0/docencia/sesiones/${id}`, data);
}