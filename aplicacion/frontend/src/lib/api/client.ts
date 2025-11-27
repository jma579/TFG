// Sugerido para src/lib/api/client.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!API_BASE_URL) {
  // Para el TFG es mejor fallar rápido si falta la config
  throw new Error(
    'NEXT_PUBLIC_API_BASE_URL no está definido. Configúralo en el entorno del frontend.',
  );
}

type FastAPIErrorResponse = {
  detail?: string | { msg?: string }[];
};

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const headers = new Headers(options.headers ?? {});

  // Aceptamos JSON siempre
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  const isFormData = options.body instanceof FormData;

  // Solo seteamos Content-Type si NO es FormData
  if (!isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  // 204 No Content
  if (res.status === 204) {
    return undefined as T;
  }

  let data: unknown;
  try {
    data = await res.json();
  } catch {
    // Si no hay JSON, devolvemos undefined y dejamos que el caller decida
    if (!res.ok) {
      throw new Error(`API error ${res.status} (${res.statusText})`);
    }
    return undefined as T;
  }

  if (!res.ok) {
  const errorData = data as FastAPIErrorResponse;
  const detail = errorData.detail;

  if (typeof detail === 'string') {
    throw new Error(detail);
  }

  if (Array.isArray(detail) && detail.length && detail[0]?.msg) {
    throw new Error(detail[0].msg ?? `API error ${res.status}`);
  }

  throw new Error(`API error ${res.status} (${res.statusText})`);
}

  return data as T;
}

// ==============================
// Tipos para fichas
// ==============================

export type FichaPipelineResult = {
  /** Indica si el pipeline ha sido exitoso */
  success: boolean;
  /** Lista de errores en texto plano (si los hay) */
  errors?: string[] | null;
  // El backend puede devolver campos adicionales (resumen de entidades, etc.)
  [key: string]: unknown;
};

export async function processFicha(file: File): Promise<FichaPipelineResult> {
  const form = new FormData();
  form.append('file', file);

  return apiFetch<FichaPipelineResult>('/v0/catalogo/fichas/process', {
    method: 'POST',
    body: form,
  });
}

// ==============================
// Tipos para horarios (extract / confirm)
// ==============================

export type HorarioTemporalSesion = {
  // Estos campos están documentados en el docstring del endpoint de extracción
  asignatura: string;
  aula?: string | null;
  dia: string; // Enum de DiaSemana en backend
  hora_inicio: string; // "HH:MM" o "HH:MM:SS"
  hora_fin: string; // "HH:MM" o "HH:MM:SS"
  tipo?: string | null; // tipo de grupo (T, P, L, etc.)
  grupo?: string | null; // código de grupo (T1, P1...)
  // Campos adicionales que pueda añadir el parser
  [key: string]: unknown;
};

export type HorarioTemporalTabla = {
  curso?: number | null;
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

// En esta fase, el contrato de entrada para confirmar es esencialmente el mismo
// horario temporal que devuelve /horarios/extract, pero editado por el usuario.
// Si el schema HorarioTemporalConfirmIn difiere en algo, se puede ajustar aquí
// fácilmente más adelante.
export type HorarioTemporalConfirmIn = HorarioTemporalOut;

export type HorarioConfirmResponse = {
  // El servicio de confirmación puede ir rellenando estos campos en fases futuras
  success?: boolean;
  warnings?: string[];
  errors?: string[];
  [key: string]: unknown;
};

export async function extractHorario(file: File): Promise<HorarioTemporalOut> {
  const form = new FormData();
  form.append('file', file);

  return apiFetch<HorarioTemporalOut>('/v0/docencia/horarios/extract', {
    method: 'POST',
    body: form,
  });
}

export async function confirmHorario(
  payload: HorarioTemporalConfirmIn,
): Promise<HorarioConfirmResponse> {
  return apiFetch<HorarioConfirmResponse>('/v0/docencia/horarios/confirm', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ==============================
// (Futuro) Sesiones + Conflictos
// ==============================
// Aquí se podrán añadir helpers como:
// - listSesiones
// - updateSesion
// - listConflictos
// - updateConflictoEstado
// usando apiFetch<T>() y los schemas reales del backend.
