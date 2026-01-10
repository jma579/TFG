import { api } from '@/lib/api/config';

// ==========================================
// Tipos Sincronizados con Backend (Pydantic)
// ==========================================

export type MatchStatus = 
  | 'EXACT' 
  | 'ALIAS_DB' 
  | 'FUZZY_AUTO' 
  | 'FUZZY_LOW_CONFIDENCE' 
  | 'NO_MATCH';

export type HorarioTemporalSesion = {
  // Datos originales del PDF
  asignatura?: string | null;
  aula?: string | null;
  dia?: string | null;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  tipo?: string | null;
  grupo?: string | null;

  // --- NUEVOS CAMPOS: Fuzzy Match Metadata ---
  match_confidence?: number | null;     // 0 - 100
  match_status?: MatchStatus | string | null; 
  asignatura_sugerida?: string | null;  // Nombre oficial sugerido

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
  // Metadatos globales del documento
  titulo?: string | null;
  plan?: string | null;
  periodo?: string | null;
  
  // Lista de tablas detectadas
  horarios: HorarioTemporalTabla[];
  
  // SOLUCIÓN LINT: Usamos 'Record<string, unknown>' en lugar de 'any'
  extraction_metadata?: Record<string, unknown>;
  parsing_metadata?: Record<string, unknown>;
  [key: string]: unknown;
};

// Payload para confirmar
export type HorarioTemporalConfirmIn = HorarioTemporalOut;

export type HorarioConfirmResponse = {
  // SOLUCIÓN LINT: Usamos 'unknown[]' en lugar de 'any[]' por ahora
  // (Más adelante podrás importar los tipos reales GrupoDocenteOut y SesionOut)
  grupos: unknown[];    
  sesiones: unknown[];
  created_entities: Record<string, number>;
  warnings: string[];
  errors: string[];
  [key: string]: unknown;
};

// ==========================================
// Funciones API (Corregidas y Tipadas)
// ==========================================

export async function extractHorario(file: File): Promise<HorarioTemporalOut> {
  const form = new FormData();
  form.append('file', file);

  // Volvemos a capturar la respuesta entera por si tu interceptor ya devolvía 'data'
  const response = await api.post<HorarioTemporalOut>('/v0/docencia/horarios/extract', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  
  // Verificamos si response tiene .data o es directamente la data
  return response.data ?? response; 
}

export async function confirmHorario(
  payload: HorarioTemporalConfirmIn
): Promise<HorarioConfirmResponse> {
  const response = await api.post<HorarioConfirmResponse>('/v0/docencia/horarios/confirm', payload);
  return response.data ?? response;
}

// 👇 CORRECCIÓN AQUI: Manejo robusto de la respuesta
export async function refineHorario(
  payload: HorarioTemporalConfirmIn
): Promise<HorarioTemporalOut> {
  // Llamamos al nuevo endpoint de re-matching
  const response = await api.post<HorarioTemporalOut>('/v0/docencia/horarios/refine', payload);
  
  // Si tu interceptor devuelve la data directa, response es la data. 
  // Si devuelve el objeto AxiosResponse, response.data es la data.
  return response.data ?? response;
}