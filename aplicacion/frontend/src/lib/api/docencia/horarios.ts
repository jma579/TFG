import { api } from '@/lib/api/config';


export type MatchStatus = 
  | 'EXACT' 
  | 'ALIAS_DB' 
  | 'FUZZY_AUTO' 
  | 'FUZZY_LOW_CONFIDENCE' 
  | 'NO_MATCH';

export type HorarioTemporalSesion = {
  asignatura?: string | null;
  aula?: string | null;
  dia?: string | null;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  tipo?: string | null;
  grupo?: string | null;

  match_confidence?: number | null;     
  match_status?: MatchStatus | string | null; 
  asignatura_sugerida?: string | null; 

  manual_validated?: boolean;
  
  [key: string]: unknown;
};

export type HorarioTemporalTabla = {
  curso?: string | null;
  periodo?: string | null;
  mencion?: string | null;
  pagina?: number | null;
  sesiones: HorarioTemporalSesion[];
  [key: string]: unknown;
};

export type HorarioTemporalOut = {
  titulo?: string | null;
  plan?: string | null;
  periodo?: string | null;
  
  horarios: HorarioTemporalTabla[];
  
  extraction_metadata?: Record<string, unknown>;
  parsing_metadata?: Record<string, unknown>;
  [key: string]: unknown;
};

export type HorarioTemporalConfirmIn = HorarioTemporalOut;

export type HorarioConfirmResponse = {
  grupos: unknown[];    
  sesiones: unknown[];
  created_entities: Record<string, number>;
  warnings: string[];
  errors: string[];
  [key: string]: unknown;
};


// Funciones API

export async function extractHorario(file: File): Promise<HorarioTemporalOut> {
  const form = new FormData();
  form.append('file', file);

  const response = await api.post<HorarioTemporalOut>('/v0/docencia/horarios/extract', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  
  return response.data ?? response; 
}

export async function confirmHorario(
  payload: HorarioTemporalConfirmIn
): Promise<HorarioConfirmResponse> {
  const response = await api.post<HorarioConfirmResponse>('/v0/docencia/horarios/confirm', payload);
  return response.data ?? response;
}

export async function refineHorario(
  payload: HorarioTemporalConfirmIn
): Promise<HorarioTemporalOut> {
  const response = await api.post<HorarioTemporalOut>('/v0/docencia/horarios/refine', payload);
  
  return response.data ?? response;
}

export async function deleteHorario(params: {
  programa_id: number;
  curso: number;
  cuatrimestre: number;
  mencion?: string;
}) {
  const { data } = await api.delete('/v0/docencia/horarios', {
    params,
  });
  return data;
}