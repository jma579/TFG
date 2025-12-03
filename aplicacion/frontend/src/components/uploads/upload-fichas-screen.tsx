'use client';

import * as React from 'react';
import { nanoid } from 'nanoid';
import { Button } from '@/components/ui/button';
import { DropzoneFichas } from './dropzone-fichas';
import { FileList } from './file-list';
import type { UploadItem } from './types';
import { processFicha } from '@/lib/api/client';
import { useToast } from '@/hooks/use-toast';

export function UploadFichasScreen() {
  const [items, setItems] = React.useState<UploadItem[]>([]);
  const disabled = items.length === 0 || items.some(i => i.status === 'uploading');
  const { toast } = useToast();

  const addFiles = (files: File[]) => {
    const next = files.map<UploadItem>((f) => ({
      id: nanoid(),
      file: f,
      status: 'pending',
      progress: 0,
    }));
    setItems((prev) => [...prev, ...next]);
  };

  const removeItem = (id: string) => {
    setItems(prev => prev.filter(i => i.id !== id));
  };

  const analyze = async () => {
  setItems(prev => prev.map(i => i.status === 'pending' ? { ...i, status: 'uploading' } : i));
  const updated: UploadItem[] = [];
  for (const item of items) {
    if (item.status !== 'pending') { updated.push(item); continue; }
    try {
      const res = await processFicha(item.file);
      const incidencias = !!res.errors && res.errors.length > 0;
      toast({
        title: incidencias
          ? 'Ficha procesada con incidencias'
          : 'Ficha procesada correctamente',
        description: incidencias
          ? `Se han detectado ${res.errors?.length ?? 0} incidencias en "${item.file.name}".`
          : `La ficha "${item.file.name}" se ha procesado sin incidencias.`,
      });
      updated.push({
        ...item,
        status: 'done',
        result: incidencias ? 'incidencias' : 'ok',
        backendResult: res,
      });
    } catch (error) {
      toast({
        title: 'Error al procesar la ficha',
        description:
          error instanceof Error
            ? error.message
            : `Error inesperado procesando "${item.file.name}".`,
        variant: 'destructive',
      });
      updated.push({
        ...item,
        status: 'error',
        errorMessage:
          error instanceof Error
            ? error.message
            : 'Error inesperado al procesar la ficha',
      });
    }
  }
  setItems(updated);
};


  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <DropzoneFichas onFiles={addFiles} />

      <div className="flex justify-end">
        <Button onClick={analyze} disabled={disabled}>
          Analizar fichas
        </Button>
      </div>

      <FileList items={items} onRemove={removeItem} />
    </div>
  );
}
