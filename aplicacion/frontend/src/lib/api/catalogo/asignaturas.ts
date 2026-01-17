import { api } from '@/lib/api/config';

// --- Tipos ---
export type AsignaturaOut = {
  id: number;
  codigo_plan: string;
  nombre: string;
  periodo: string;
  num_periodo?: number | null;
  ects?: number | null;
  modalidad?: string | null;
  idioma?: string | null;
  english_friendly?: boolean | null;
  activo?: boolean | null;
  num_profesores?: number;
  num_titulaciones?: number;
  titulaciones?: {
    programa: { nombre: string };
    curso?: number | null;
    tipo_asignatura?: string | null;
  }[];
  [key: string]: unknown;
};

export type AsignaturaListResponse = {
  total: number;
  items: AsignaturaOut[];
  page?: number;
  size?: number;
};

export type AsignaturaProgramaAPI = {
  programa: {
    id: number;
    codigo_plan?: string;
    nombre: string;
    [key: string]: unknown;
  };
  curso: number | null;
  tipo_asignatura: string | null;
};

export type AsignaturaUpdateInput = {
  nombre?: string;
  ects?: number | null;
  english_friendly?: boolean | null;
  activo?: boolean | null;
};

// --- Funciones ---

export async function listAsignaturas(params?: {
  skip?: number;
  limit?: number;
  periodo?: string;
  modalidad?: string;
  idioma?: string;
  activo?: boolean;
}): Promise<AsignaturaListResponse> {
  return api.get('/v0/catalogo/asignaturas', { params });
}

export async function getAsignatura(id: number): Promise<AsignaturaOut> {
  return api.get(`/v0/catalogo/asignaturas/${id}`);
}

export async function updateAsignatura(
  id: number,
  data: AsignaturaUpdateInput
): Promise<AsignaturaOut> {
  return api.put(`/v0/catalogo/asignaturas/${id}`, data);
}

export async function deleteAsignatura(id: number, physical: boolean = false): Promise<void> {
  return api.delete(`/v0/catalogo/asignaturas/${id}`, {
    params: { physical }
  });
}

export async function getAsignaturaProgramas(
  asignaturaId: number
): Promise<AsignaturaProgramaAPI[]> {
  return api.get(`/v0/catalogo/asignaturas/${asignaturaId}/programas`);
}