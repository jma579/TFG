import { api } from '@/lib/api/config';

export type AulaOut = {
  id: number;
  nombre: string;
  codigo: string;
  tipo: string;
  capacidad: number | null;
};

export type AulaListResponse = {
  total: number;
  items: AulaOut[];
  page: number;
  size: number;
};

export type AulaFilters = {
  search?: string;
  tipo?: string;
  capacidadMin?: number;
  capacidadMax?: number;
  page?: number;
  size?: number;
};

export type AulaCreateInput = {
  nombre: string;
  codigo: string;
  tipo: string;
  capacidad?: number | null;
};

export type AulaUpdateInput = Partial<AulaCreateInput>;

export async function listAulas(filters: AulaFilters = {}): Promise<AulaListResponse> {
  const { search, capacidadMin, capacidadMax, page = 1, size = 100, ...rest } = filters;
  const skip = (page - 1) * size;

  // Mapeamos los filtros a los parámetros que espera el backend
  const params = {
    busqueda: search,
    capacidad_min: capacidadMin,
    capacidad_max: capacidadMax,
    skip,
    limit: size,
    ...rest,
  };

  return api.get('/v0/recursos/aulas', { params });
}

export async function createAula(input: AulaCreateInput): Promise<AulaOut> {
  return api.post('/v0/recursos/aulas', input);
}

export async function updateAula(id: number, input: AulaUpdateInput): Promise<AulaOut> {
  return api.put(`/v0/recursos/aulas/${id}`, input);
}

export async function deleteAula(id: number): Promise<void> {
  return api.delete(`/v0/recursos/aulas/${id}`);
}