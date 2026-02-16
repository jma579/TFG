import { api } from '@/lib/api/config';

export type ConflictoTipo =
  | 'solapamiento_profesor'
  | 'solapamiento_aula'
  | 'solapamiento_grupo'
  | 'incumplimiento_restriccion';

export type ConflictoSeveridad = 'critico' | 'no_bloqueante' | 'leve';
export type ConflictoEstado = 'por_revisar' | 'solucionado';


export type SesionResumen = {
  id: number;
  asignatura: string;
  grupo: string;
  horario: string;
  curso: string;
  aula?: string;
  titulacion?: string;
  mencion?: string;
  periodo?: string;
  programa_id?: number;
  curso_num?: number;
  periodo_code?: string;
};

export type ConflictoOut = {
  id: number;
  tipo: ConflictoTipo;
  severidad: ConflictoSeveridad;
  estado: ConflictoEstado;
  descripcion: string;
  
  sesion_id: number;
  sesion_2_id?: number | null;
  profesor_id?: number | null;
  aula_id?: number | null;
  restriccion_id?: number | null;

  sesion_1_detalle?: SesionResumen | null;
  sesion_2_detalle?: SesionResumen | null;

  hash_deteccion: string;
  creado_en: string; 
  resuelto_en?: string | null;
};

export type ConflictoListResponse = {
  total: number;
  items: ConflictoOut[];
  page: number;
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


export async function listConflictos(
  filters: ConflictoListFilters = {}
): Promise<ConflictoListResponse> {
  const { skip = 0, limit = 100, ...rest } = filters;
  
  const params = Object.fromEntries(
    Object.entries({ skip, limit, ...rest }).filter(([, v]) => v != null)
  );

  return api.get('/v0/conflictos', { params });
}

export async function resolverConflicto(id: number): Promise<ConflictoOut> {
  return api.patch(`/v0/conflictos/${id}`, { estado: 'solucionado' });
}