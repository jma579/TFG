// src/lib/api/docencia/sesiones.ts
import { api } from '@/lib/api/config';
import { ConflictoOut } from '@/lib/api/conflictos'; // Asegúrate que este tipo existe o defínelo

// --- Tipos alineados con tu Backend (sesion.py) ---

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
  // Profesores (según SesionOut en backend)
  profesores: Array<{
    profesor_id: number;
    rol_en_sesion?: string;
    nombre?: string;
    apellidos?: string;
  }>;
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

export type SesionUpdateInput = {
  aula_id?: number | null;
  dia_semana?: string;
  hora_inicio?: string;
  hora_fin?: string;
  // Agrega otros campos si tu SesionUpdate en backend lo permite
};

export type SesionFilters = {
  grupo_docente_id?: number;
  aula_id?: number;
  page?: number;
  size?: number;
};

// --- Funciones ---

// 1. FALTABA: Listar sesiones (Necesario para pintar el horario completo)
export async function listSesiones(filters: SesionFilters = {}): Promise<SesionListResponse> {
  const { page = 1, size = 100, ...rest } = filters;
  const params = {
    skip: (page - 1) * size,
    limit: size,
    ...rest,
  };
  return api.get('/v0/docencia/sesiones', { params });
}

// 2. Obtener una sola sesión
export async function getSesionConConflictos(id: number): Promise<SesionWithConflictosOut> {
  return api.get(`/v0/docencia/sesiones/${id}`); // Ojo: Verifica si tu backend devuelve SesionOut o SesionWithConflictosOut en el GET simple
}

// 3. CORRECCIÓN: El backend define @router.put, no patch
export async function updateSesion(
  id: number,
  data: SesionUpdateInput
): Promise<SesionWithConflictosOut> {
  return api.put(`/v0/docencia/sesiones/${id}`, data); 
}

export async function deleteSesion(id: number): Promise<void> {
  return api.delete(`/v0/docencia/sesiones/${id}`);
}