import { api } from '@/lib/api/config';

// --- Tipos ---
export type HorarioTemporalSesion = {
  asignatura: string;
  aula?: string | null;
  dia: string;
  hora_inicio: string;
  hora_fin: string;
  tipo?: string | null;
  grupo?: string | null;
  [key: string]: unknown;
};

export type HorarioTemporalGrupo = {
  id: number;
  codigo: string;
  tipo: string;
  curso: number;
  turno?: string | null;
  asignatura_id: number;
  sesiones: HorarioTemporalSesion[];
  [key: string]: unknown;
};

export type HorarioTemporalOut = {
  id: number;
  grado: string;
  curso_academico: string;
  grupos: HorarioTemporalGrupo[];
  [key: string]: unknown;
};

export type HorarioTemporalConfirmIn = HorarioTemporalOut;

export type HorarioConfirmResponse = {
  success?: boolean;
  warnings?: string[];
  errors?: string[];
  [key: string]: unknown;
};

// --- Funciones ---

export async function extractHorario(file: File): Promise<HorarioTemporalOut> {
  const form = new FormData();
  form.append('file', file);

  return api.post('/v0/docencia/horarios/extract', form, {
    headers: {
      // Importante: Sobrescribimos el 'application/json' global
      'Content-Type': 'multipart/form-data',
    },
  });
}

export async function confirmHorario(
  payload: HorarioTemporalConfirmIn
): Promise<HorarioConfirmResponse> {
  return api.post('/v0/docencia/horarios/confirm', payload);
}