import { api } from '@/lib/api/config';

export type ProfesorAPI = {
  id: number;
  nombre: string;
  apellidos: string;
  email?: string | null;
  telefono?: string | null;
  departamento?: string | null;
  activo: boolean;
  total_restricciones?: number;
  [key: string]: unknown;
};

export type ProfesorListResponse = {
  total: number;
  items: ProfesorAPI[];
  page?: number;
  size?: number;
};

export type ProfesorCreateInput = {
  nombre: string;
  apellidos: string;
  email?: string | null;
  departamento?: string | null;
  activo?: boolean;
};

export type ProfesorUpdateInput = Partial<ProfesorCreateInput>;

export async function listProfesores(params?: { limit?: number; skip?: number }): Promise<ProfesorListResponse> {
  return api.get('/v0/recursos/profesores', { params });
}

export async function getAsignaturaProfesores(asignaturaId: number): Promise<ProfesorAPI[]> {
  return api.get(`/v0/catalogo/asignaturas/${asignaturaId}/profesores`);
}

export async function updateProfesor(id: number, data: ProfesorUpdateInput): Promise<ProfesorAPI> {
  return api.put(`/v0/recursos/profesores/${id}`, data);
}