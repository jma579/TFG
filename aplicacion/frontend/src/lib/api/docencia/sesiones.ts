// src/lib/api/docencia/sesiones.ts
import { api } from '@/lib/api/config';
import { ConflictoOut } from '@/lib/api/conflictos';

// --- Tipos alineados con tu Backend ---

export type SesionOut = {
  id: number;
  grupo_docente_id: number;
  aula_id: number;
  modalidad: string;
  tipo_recurrencia: string;
  // Campos de horario
  dia_semana?: string | null;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  inicio?: string | null;
  fin?: string | null;
  // Profesores
  profesores: Array<{
    profesor_id: number;
    rol_en_sesion?: string;
    nombre?: string;
    apellidos?: string;
  }>;
};

// Tipos para Creación y Edición
export type SesionCreate = {
  grupo_docente_id: number;
  aula_id: number;
  modalidad: string; // 'presencial', 'online', etc.
  tipo_recurrencia: string; // 'semanal', 'puntual', etc.
  dia_semana?: string | null;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  inicio?: string | null; // ISO Date string
  fin?: string | null;    // ISO Date string
  profesores?: Array<{
    profesor_id: number;
    rol_en_sesion?: string;
  }>;
};

// Update parcial
export type SesionUpdate = Partial<SesionCreate>;

// Update específico para Batch (necesita ID)
export type SesionUpdateWithId = SesionUpdate & { id: number };

// Payload del Batch
export type SesionBatchRequest = {
  created: SesionCreate[];
  updated: SesionUpdateWithId[];
  deleted: number[];
};

export type SesionListResponse = {
  total: number;
  items: SesionOut[];
  page: number;
  size: number;
};

export type SesionWithConflictosOut = {
  sesion: SesionOut;
  conflictos: ConflictoOut[];
};

// Mantenemos este tipo antiguo por compatibilidad si se usa en otros lados, 
// pero internamente SesionUpdate es más completo.
export type SesionUpdateInput = {
  aula_id?: number | null;
  dia_semana?: string;
  hora_inicio?: string;
  hora_fin?: string;
};

export type SesionFilters = {
  grupo_docente_id?: number;
  aula_id?: number;
  curso?: number;
  mencion?: string;
  page?: number;
  size?: number;
};

// --- Funciones ---

export async function listSesiones(filters: SesionFilters = {}): Promise<SesionListResponse> {
  const { page = 1, size = 100, ...rest } = filters;
  const params = {
    skip: (page - 1) * size,
    limit: size,
    ...rest,
  };
  return api.get('/v0/docencia/sesiones', { params });
}

export async function getSesionConConflictos(id: number): Promise<SesionWithConflictosOut> {
  return api.get(`/v0/docencia/sesiones/${id}`);
}

export async function createSesion(data: SesionCreate): Promise<SesionWithConflictosOut> {
  return api.post('/v0/docencia/sesiones', data);
}

export async function updateSesion(
  id: number,
  data: SesionUpdateInput | SesionUpdate // Admitimos ambos tipos
): Promise<SesionWithConflictosOut> {
  return api.put(`/v0/docencia/sesiones/${id}`, data); 
}

export async function deleteSesion(id: number): Promise<void> {
  return api.delete(`/v0/docencia/sesiones/${id}`);
}

export async function batchUpdateSesiones(payload: SesionBatchRequest): Promise<{ status: string, created_count: number }> {
  return api.post('/v0/docencia/sesiones/batch', payload);
}