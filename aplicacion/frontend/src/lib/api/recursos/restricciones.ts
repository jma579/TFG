import { api } from '@/lib/api/config';

export type Restriccion = {
  id: number;
  profesor_id: number;
  dia_semana: number;
  hora_inicio: string;
  hora_fin: string;
};

export type ImportacionRestriccionesResponse = {
  registros_creados: number;
  registros_eliminados: number;
  errores: string[];
  warnings: string[];
};

/**
 * Obtiene todas las restricciones de un profesor específico.
 */
export async function getRestriccionesByProfesor(profesorId: string | number): Promise<Restriccion[]> {
  const response = await api.get<Restriccion[]>(
    `/v0/recursos/profesores/${profesorId}/restricciones`
  );
  // Soporta api que ya devuelve el payload o un AxiosResponse
  if (Array.isArray(response)) return response;
  return response?.data ?? [];
}

/**
 * Elimina una restricción específica por su ID.
 */
export async function eliminarRestriccion(id: number): Promise<void> {
  await api.delete(`/v0/recursos/restricciones/${id}`);
}

/**
 * Sube el archivo Excel de restricciones al servidor.
 */
export async function importarRestricciones(file: File): Promise<ImportacionRestriccionesResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<ImportacionRestriccionesResponse>(
    '/v0/recursos/restricciones/importar',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );

  return response.data;
}