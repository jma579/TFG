import { api } from '@/lib/api/config';

export type GrupoDocenteOut = {
  id: number;
  asignatura_id: number;
  codigo: string;
  tipo: string;
  curso?: number | null;
  turno?: string | null;
};

export type GrupoDocenteListResponse = {
  total: number;
  items: GrupoDocenteOut[];
  page: number;
  size: number;
};

export type GrupoDocenteFilters = {
  asignatura_id?: number;
  tipo?: string;
  curso?: number;
  turno?: string;
  page?: number;
  size?: number;
};

export async function listGruposDocentes(filters: GrupoDocenteFilters = {}): Promise<GrupoDocenteListResponse> {
  const { page = 1, size = 100, ...rest } = filters;
  const params = {
    skip: (page - 1) * size,
    limit: size,
    ...rest,
  };
  return api.get('/v0/docencia/grupos-docentes', { params });
}