import { api } from '@/lib/api/config';
import { ConflictoOut } from '@/lib/api/conflictos';

// --- Tipos Base ---

export type SesionOut = {
  id: number;
  grupo_docente_id: number;
  aula_id: number;
  modalidad: string;
  tipo_recurrencia: string;
  dia_semana?: string | null;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  inicio?: string | null;
  fin?: string | null;
  profesores: Array<{
    profesor_id: number;
    rol_en_sesion?: string;
    nombre?: string;
    apellidos?: string;
  }>;
};


export type SesionCreate = {
  grupo_docente_id: number;
  aula_id: number;
  modalidad: string; 
  tipo_recurrencia: string;
  dia_semana?: string | null;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  inicio?: string | null; 
  fin?: string | null;    
  profesores?: Array<{
    profesor_id: number;
    rol_en_sesion?: string;
  }>;
  temp_id?: number; 
};

export type SesionUpdate = Partial<SesionCreate>;
export type SesionUpdateWithId = SesionUpdate & { id: number };

export type SesionUpdateInput = SesionUpdate;


export type SesionWithConflictosOut = {
  sesion: SesionOut;
  conflictos: ConflictoOut[];
};

export type SesionBatchRequest = {
  created: SesionCreate[];
  updated: SesionUpdateWithId[];
  deleted: number[];
};

export type SesionBatchResponse = {
  status: string;
  created: SesionWithConflictosOut[];
  updated: SesionWithConflictosOut[];
  deleted_ids: number[];
};

export type SesionListResponse = {
  total: number;
  items: SesionOut[];
  page: number;
  size: number;
};

export type SesionFilters = {
  grupo_docente_id?: number;
  aula_id?: number;
  curso?: number;
  mencion?: string;
  programa_id?: number;
  periodo?: string;
  page?: number;
  size?: number;
};

export type SesionValidationResponse = {
  valid: boolean;
  conflictos: ConflictoOut[];
};

// Funciones 

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
  data: SesionUpdateInput
): Promise<SesionWithConflictosOut> {
  return api.put(`/v0/docencia/sesiones/${id}`, data); 
}

export async function validateBatchSesiones(payload: SesionBatchRequest): Promise<ConflictoOut[]> {
  return api.post('/v0/docencia/sesiones/validate-batch', payload);
}

export async function deleteSesion(id: number): Promise<void> {
  return api.delete(`/v0/docencia/sesiones/${id}`);
}

export async function batchUpdateSesiones(payload: SesionBatchRequest): Promise<SesionBatchResponse> {
  return api.post('/v0/docencia/sesiones/batch', payload);
}