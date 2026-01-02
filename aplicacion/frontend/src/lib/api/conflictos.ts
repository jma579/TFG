// src/lib/api/conflictos.ts
import { api } from '@/lib/api/config';

export type ConflictoTipo =
  | 'SOLAPAMIENTO_PROFESOR'
  | 'SOLAPAMIENTO_AULA'
  | 'VIOLACION_RESTRICCION';

export type ConflictoEstado = 'ABIERTO' | 'RESUELTO' | 'IGNORADO';
export type ConflictoSeveridad = 'INFO' | 'WARNING' | 'ERROR';

export type ConflictoOut = {
  id: number;
  tipo: ConflictoTipo;
  severidad: ConflictoSeveridad;
  estado: ConflictoEstado;
  mensaje: string;
  sesion_id?: number | null;
  profesor_id?: number | null;
  aula_id?: number | null;
  [key: string]: unknown;
};

export type ConflictoListResponse = {
  total: number;
  items: ConflictoOut[];
  page?: number;
  size?: number;
};

export type ConflictoListFilters = {
  tipo?: ConflictoTipo;
  severidad?: ConflictoSeveridad;
  estado?: ConflictoEstado;
  profesor_id?: number;
  aula_id?: number;
  sesion_id?: number;
  skip?: number;
  limit?: number;
};

export type ConflictoEstadoUpdateIn = {
  estado: ConflictoEstado;
};

export async function listConflictos(
  filters: ConflictoListFilters = {}
): Promise<ConflictoListResponse> {
  const { skip = 0, limit = 100, ...rest } = filters;
  
  const params = {
    skip,
    limit,
    ...rest
  };

  return api.get('/v0/conflictos', { params });
}

export async function listConflictosPorSesion(sesionId: number): Promise<ConflictoOut[]> {
  return api.get(`/v0/conflictos/sesion/${sesionId}`);
}

export async function updateConflictoEstado(
  id: number,
  payload: ConflictoEstadoUpdateIn
): Promise<ConflictoOut> {
  return api.patch(`/v0/conflictos/${id}`, payload);
}