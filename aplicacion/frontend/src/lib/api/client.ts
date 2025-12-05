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

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
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
// Asignaturas (listado + docencia + edición)
// ==============================

export type AsignaturaOut = {
  id: number;
  codigo_plan: string;
  nombre: string;
  periodo: string;
  num_periodo?: number | null;
  ects?: number | null;
  modalidad?: string | null;
  idioma?: string | null;
  english_friendly?: boolean | null;
  activo?: boolean | null;
  num_profesores?: number;
  num_titulaciones?: number;
  titulaciones?: {
    programa: { nombre: string };
    curso?: number | null;
    tipo_asignatura?: string | null;
  }[];
  // Campos adicionales que pueda devolver el backend
  [key: string]: unknown;
};

export type AsignaturaListResponse = {
  total: number;
  items: AsignaturaOut[];
  page?: number;
  size?: number;
};

export async function listAsignaturas(params?: {
  skip?: number;
  limit?: number;
  periodo?: string;
  modalidad?: string;
  idioma?: string;
  activo?: boolean;
}): Promise<AsignaturaListResponse> {
  const searchParams = new URLSearchParams();

  if (params?.skip != null) searchParams.set('skip', String(params.skip));
  if (params?.limit != null) searchParams.set('limit', String(params.limit));
  if (params?.periodo) searchParams.set('periodo', params.periodo);
  if (params?.modalidad) searchParams.set('modalidad', params.modalidad);
  if (params?.idioma) searchParams.set('idioma', params.idioma);
  if (params?.activo != null) searchParams.set('activo', String(params.activo));

  const qs = searchParams.toString();
  const path = qs
    ? `/v0/catalogo/asignaturas?${qs}`
    : '/v0/catalogo/asignaturas';

  return apiFetch<AsignaturaListResponse>(path);
}

export async function getAsignatura(id: number): Promise<AsignaturaOut> {
  return apiFetch<AsignaturaOut>(`/v0/catalogo/asignaturas/${id}`);
}

export type AsignaturaUpdateInput = {
  nombre?: string;
  ects?: number | null;
  english_friendly?: boolean | null;
  activo?: boolean | null;
};

export async function updateAsignatura(
  id: number,
  data: AsignaturaUpdateInput,
): Promise<AsignaturaOut> {
  return apiFetch<AsignaturaOut>(`/v0/catalogo/asignaturas/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteAsignatura(id: number): Promise<void> {
  await apiFetch<void>(`/v0/catalogo/asignaturas/${id}`, {
    method: 'DELETE',
  });
}

// ==============================
// Tipos para docencia de asignaturas
// ==============================

export type AsignaturaProgramaAPI = {
  programa: {
    id: number;
    codigo_plan?: string;
    nombre: string;
    // Permitimos campos extra por si el backend crece
    [key: string]: unknown;
  };
  curso: number | null;
  tipo_asignatura: string | null;
};

export async function getAsignaturaProgramas(
  asignaturaId: number,
): Promise<AsignaturaProgramaAPI[]> {
  return apiFetch<AsignaturaProgramaAPI[]>(
    `/v0/catalogo/asignaturas/${asignaturaId}/programas`,
  );
}

export type ProfesorAPI = {
  id: number;
  nombre: string;
  apellidos: string;
  email?: string | null;
  telefono?: string | null;
  departamento?: string | null;
  activo: boolean;
  [key: string]: unknown;
};

export async function getAsignaturaProfesores(
  asignaturaId: number,
): Promise<ProfesorAPI[]> {
  return apiFetch<ProfesorAPI[]>(
    `/v0/catalogo/asignaturas/${asignaturaId}/profesores`,
  );
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
  grupo?: string | null; //
  // Permitimos campos adicionales por si el backend crece
  [key: string]: unknown;
};

export type HorarioTemporalGrupo = {
  id: number;
  codigo: string;
  tipo: string; // teoría, práctica, etc. (puede ser enum en backend)
  curso: number;
  turno?: string | null;
  asignatura_id: number;
  sesiones: HorarioTemporalSesion[];
  [key: string]: unknown;
};

export type HorarioTemporalOut = {
  id: number;
  grado: string;
  curso_academico: string;
  grupos: HorarioTemporalGrupo[];
  // Otros campos que devuelva el backend
  [key: string]: unknown;
};

// En esta fase, el contrato de entrada para confirmar es esencialmente el mismo
// horario temporal que devuelve /horarios/extract, pero editado por el usuario.
// Si el schema HorarioTemporalConfirmIn difiere en algo, se puede ajustar aquí
// fácilmente más adelante.
export type HorarioTemporalConfirmIn = HorarioTemporalOut;

export type HorarioConfirmResponse = {
  // El servicio de confirmación puede ir rellenando estos campos en futuras fases
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
// Conflictos
// ==============================

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
  // timestamps, metadata, etc.
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

export async function listConflictos(
  filters: ConflictoListFilters = {},
): Promise<ConflictoListResponse> {
  const params = new URLSearchParams();

  if (filters.tipo) params.set('tipo', filters.tipo);
  if (filters.severidad) params.set('severidad', filters.severidad);
  if (filters.estado) params.set('estado', filters.estado);
  if (filters.profesor_id != null)
    params.set('profesor_id', String(filters.profesor_id));
  if (filters.aula_id != null)
    params.set('aula_id', String(filters.aula_id));
  if (filters.sesion_id != null)
    params.set('sesion_id', String(filters.sesion_id));

  const skip = filters.skip ?? 0;
  const limit = filters.limit ?? 100;

  params.set('skip', String(skip));
  params.set('limit', String(limit));

  const query = params.toString();

  return apiFetch<ConflictoListResponse>(
    `/v0/conflictos${query ? `?${query}` : ''}`,
  );
}

export async function listConflictosPorSesion(
  sesionId: number,
): Promise<ConflictoOut[]> {
  return apiFetch<ConflictoOut[]>(`/v0/conflictos/sesion/${sesionId}`);
}

export type ConflictoEstadoUpdateIn = {
  estado: ConflictoEstado;
};

export async function updateConflictoEstado(
  id: number,
  payload: ConflictoEstadoUpdateIn,
): Promise<ConflictoOut> {
  return apiFetch<ConflictoOut>(`/v0/conflictos/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

// ==============================
// Sesiones de docencia
// ==============================

export type SesionAPI = {
  id: number;
  grupo_docente_id: number;
  asignatura_id: number;
  aula_id?: number | null;
  dia_semana: string;
  hora_inicio: string;
  hora_fin: string;
  // Campos adicionales que pueda devolver el backend
  [key: string]: unknown;
};

export type SesionWithConflictosOut = {
  sesion: SesionAPI;
  conflictos: ConflictoOut[];
};

export async function getSesionConConflictos(
  id: number,
): Promise<SesionWithConflictosOut> {
  return apiFetch<SesionWithConflictosOut>(`/v0/docencia/sesiones/${id}`);
}

export type SesionUpdateInput = {
  aula_id?: number | null;
  dia_semana?: string;
  hora_inicio?: string;
  hora_fin?: string;
};

export async function updateSesion(
  id: number,
  data: SesionUpdateInput,
): Promise<SesionWithConflictosOut> {
  return apiFetch<SesionWithConflictosOut>(`/v0/docencia/sesiones/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// ==============================
// Recursos: Profesores
// ==============================

export type ProfesorListResponse = {
  total: number;
  items: ProfesorAPI[];
  page?: number;
  size?: number;
};

export type ProfesorUpdateInput = {
  nombre?: string;
  apellidos?: string;
  email?: string | null;
  departamento?: string | null;
  activo?: boolean;
};

export async function listProfesores(): Promise<ProfesorListResponse> {
  return apiFetch<ProfesorListResponse>('/v0/recursos/profesores');
}

export type ProfesorCreateInput = {
  nombre: string;
  apellidos: string;
  email?: string | null;
  departamento?: string | null;
  activo?: boolean;
};

export async function createProfessor(
  data: ProfesorCreateInput,
): Promise<ProfesorAPI> {
  return apiFetch<ProfesorAPI>('/v0/recursos/profesores', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProfesor(
  id: number,
  data: ProfesorUpdateInput,
): Promise<ProfesorAPI> {
  return apiFetch<ProfesorAPI>(`/v0/recursos/profesores/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ==============================
// Recursos: Aulas
// ==============================

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

export async function listAulas(
  filters: AulaFilters = {},
): Promise<AulaListResponse> {
  const params = new URLSearchParams();

  if (filters.search) {
    params.set('busqueda', filters.search);
  }
  if (filters.tipo) {
    params.set('tipo', filters.tipo);
  }
  if (filters.capacidadMin != null) {
    params.set('capacidad_min', String(filters.capacidadMin));
  }
  if (filters.capacidadMax != null) {
    params.set('capacidad_max', String(filters.capacidadMax));
  }

  const size = filters.size ?? 100;
  const page = filters.page ?? 1;
  const skip = (page - 1) * size;

  params.set('skip', String(skip));
  params.set('limit', String(size));

  const query = params.toString();

  return apiFetch<AulaListResponse>(
    `/v0/recursos/aulas${query ? `?${query}` : ''}`,
  );
}

export type AulaCreateInput = {
  nombre: string;
  codigo: string;
  tipo: string;
  capacidad?: number | null;
};

export type AulaUpdateInput = Partial<AulaCreateInput>;

export async function createAula(input: AulaCreateInput): Promise<AulaOut> {
  return apiFetch<AulaOut>('/v0/recursos/aulas', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function updateAula(
  id: number,
  input: AulaUpdateInput,
): Promise<AulaOut> {
  return apiFetch<AulaOut>(`/v0/recursos/aulas/${id}`, {
    method: 'PUT',
    body: JSON.stringify(input),
  });
}

export async function deleteAula(id: number): Promise<void> {
  await apiFetch<void>(`/v0/recursos/aulas/${id}`, {
    method: 'DELETE',
  });
}

// ==============================
// Catálogo: Programas (Titulaciones)
// ==============================

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
  activo?: boolean,
): Promise<ProgramaList> {
  const params = new URLSearchParams();
  params.set('page', page.toString());
  params.set('size', size.toString());
  if (activo !== undefined) {
    params.set('activo', activo.toString());
  }

  return apiFetch<ProgramaList>(`/v0/catalogo/programas?${params.toString()}`);
}

