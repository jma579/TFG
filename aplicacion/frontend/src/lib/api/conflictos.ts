// src/lib/api/conflictos.ts
import { api } from '@/lib/api/config';

export type ConflictoTipo =
  | 'SOLAPAMIENTO_PROFESOR'
  | 'SOLAPAMIENTO_AULA'
  | 'VIOLACION_RESTRICCION';

export type ConflictoEstado = 'ABIERTO' | 'RESUELTO' | 'IGNORADO';
// Se añade CRITICA para cubrir todos los posibles valores del backend
export type ConflictoSeveridad = 'INFO' | 'WARNING' | 'ERROR' | 'CRITICA';

export type ConflictoOut = {
  id: number;
  tipo: ConflictoTipo;
  severidad: ConflictoSeveridad;
  estado: ConflictoEstado;
  descripcion: string; // CORREGIDO: Alineado con Backend (era 'mensaje')
  
  // IDs Relacionados
  sesion_id: number;
  sesion_2_id?: number | null; // AÑADIDO: Vital para saber con quién choca
  profesor_id?: number | null;
  aula_id?: number | null;
  restriccion_id?: number | null; // AÑADIDO

  // Metadatos y Auditoría
  hash_deteccion: string;
  creado_en: string; // ISO Date string
  resuelto_en?: string | null;
  
  [key: string]: unknown;
};

export type ConflictoListResponse = {
  total: number;
  items: ConflictoOut[];
  page: number; // Backend siempre devuelve page/size obligatorios
  size: number;
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

// --- Endpoints ---

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
  // Este endpoint devuelve una lista plana (Array), no un objeto paginado
  return api.get(`/v0/conflictos/sesion/${sesionId}`);
}

export async function updateConflictoEstado(
  id: number,
  payload: ConflictoEstadoUpdateIn
): Promise<ConflictoOut> {
  return api.patch(`/v0/conflictos/${id}`, payload);
}