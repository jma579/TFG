import { api } from '@/lib/api/config';

export type FichaPipelineResult = {
  success: boolean;
  errors?: string[] | null;
  [key: string]: unknown;
};

export async function processFicha(file: File): Promise<FichaPipelineResult> {
  const form = new FormData();
  form.append('file', file); 

  return api.post('/v0/catalogo/fichas/process', form, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
}