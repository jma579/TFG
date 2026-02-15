import { api } from '@/lib/api/config';

export type ImportacionRestriccionesResponse = {
  registros_creados: number;
  registros_eliminados: number;
  errores: string[];
  warnings: string[];
};

/**
 * Sube el archivo Excel de restricciones al servidor.
 * El backend borrará todas las anteriores e insertará las nuevas (Atómico).
 */
export async function importarRestricciones(file: File): Promise<ImportacionRestriccionesResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return api.post('/v0/recursos/restricciones/importar', formData);
}