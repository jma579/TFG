import type { FichaPipelineResult } from '@/lib/api/client';

export type UploadStatus = 'pending' | 'uploading' | 'done' | 'error';
export type UploadResult = 'ok' | 'incidencias';

export type UploadItem = {
  id: string;
  file: File;
  status: UploadStatus;
  result?: UploadResult;
  errorMessage?: string;
  backendResult?: FichaPipelineResult;
};