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

export async function listProgramas(
  page = 1,
  size = 100,
  activo?: boolean
): Promise<ProgramaList> {
  return api.get('/v0/catalogo/programas', {
    params: { page, size, activo },
  });
}