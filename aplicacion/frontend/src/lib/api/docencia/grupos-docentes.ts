import { api } from '@/lib/api/config'; 

export type GrupoDocenteOut = {
  id: number;
  asignatura_id: number;
  codigo: string;
  tipo: string; 
  curso: number;
  turno?: string;
  asignatura?: { nombre: string };
};

export type GrupoDocenteCreate = {
  asignatura_id: number;
  codigo: string;
  tipo: string;
  curso?: number;
  turno?: string;
};

export type GrupoDocenteList = {
  total: number;
  items: GrupoDocenteOut[];
  page: number;
  size: number;
};

export type GrupoDocenteFilters = {
  curso?: number;
  size?: number;
};


export async function listGruposDocentes(filters: GrupoDocenteFilters = {}): Promise<GrupoDocenteList> {
  const { size = 100, ...rest } = filters;
  const params = {
    limit: size,
    ...rest,
  };
  return api.get('/v0/docencia/grupos-docentes', { params });
}

export async function createGrupoDocente(data: GrupoDocenteCreate): Promise<GrupoDocenteOut> {
  return api.post('/v0/docencia/grupos-docentes', data);
}