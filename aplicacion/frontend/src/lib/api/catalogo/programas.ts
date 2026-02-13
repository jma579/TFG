import { api } from '@/lib/api/config';

export type ProgramaOut = {
  id: number;
  nombre: string;
  tipo: string;
  activo: boolean;
};

export type ProgramaList = {
  total: number;
  items: ProgramaOut[];
  page: number;
  size: number;
};

export type ProgramaListResponse = {
  total: number;
  items: ProgramaOut[];
  page?: number;
  size?: number;
};

export async function listProgramas(params?: {
  skip?: number;
  limit?: number;
  activo?: boolean;
  tipo?: string;
}): Promise<ProgramaListResponse> {
  return api.get('/v0/catalogo/programas', { params });
}

export async function getPrograma(id: number): Promise<ProgramaOut> {
  return api.get(`/v0/catalogo/programas/${id}`);
}