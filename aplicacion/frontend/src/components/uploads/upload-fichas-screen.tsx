'use client';

import * as React from 'react';
import { nanoid } from 'nanoid';
import { Play, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { DropzoneFichas } from './dropzone-fichas';
import { FileList } from './file-list';
import type { UploadItem } from './types';
import { processFicha } from '@/lib/api/catalogo/fichas';
import { useToast } from '@/hooks/use-toast';

export function UploadFichasScreen() {
  const [items, setItems] = React.useState<UploadItem[]>([]);
  const isUploading = items.some((i) => i.status === 'uploading');
  const disabled = items.length === 0 || isUploading;
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
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  const renameItem = (id: string, newName: string) => {
    setItems((prev) =>
      prev.map((i) => {
        if (i.id === id) {
          // Creamos un nuevo objeto File con el nuevo nombre
          const renamedFile = new File([i.file], newName, { type: i.file.type });
          return { ...i, file: renamedFile };
        }
        return i;
      })
    );
  };

  const analyze = async () => {
    setItems((prev) =>
      prev.map((i) => (i.status === 'pending' ? { ...i, status: 'uploading' } : i))
    );
    
    const updated: UploadItem[] = [];
    
    for (const item of items) {
      if (item.status !== 'pending') {
        updated.push(item);
        continue;
      }
      try {
        const res = await processFicha(item.file);
        const incidencias = !!res.errors && res.errors.length > 0;
        
        if (items.length === 1) {
             toast({
                title: incidencias
                  ? 'Ficha procesada con incidencias'
                  : 'Ficha procesada correctamente',
                description: incidencias
                  ? `Se han detectado ${res.errors?.length ?? 0} incidencias en "${item.file.name}".`
                  : `La ficha "${item.file.name}" se ha procesado sin incidencias.`,
                variant: incidencias ? 'default' : 'default',
              });
        }

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
    
    if (items.length > 1) {
        toast({
            title: "Proceso finalizado",
            description: `Se han procesado ${items.length} archivos.`,
        })
    }
  };

  return (
    <Card className="border-border shadow-sm">
      <CardHeader>
        <CardTitle>Cargar Documentos</CardTitle>
        <CardDescription>
          Añade las guías docentes (PDF) para extraer la información académica automáticamente.
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-6">
        <DropzoneFichas onFiles={addFiles} />

        {items.length > 0 && (
          <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="mb-4 flex items-center gap-2">
                <Separator className="flex-1" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Archivos en cola ({items.length})
                </span>
                <Separator className="flex-1" />
            </div>
            <FileList items={items} onRemove={removeItem} onRename={renameItem} />
          </div>
        )}
      </CardContent>

      {items.length > 0 && (
        <CardFooter className="flex justify-between border-t bg-muted/40 px-6 py-4">
          <div className="text-sm text-muted-foreground">
            {items.filter(i => i.status === 'done').length > 0 && (
                <span>Procesados: {items.filter(i => i.status === 'done').length} / {items.length}</span>
            )}
          </div>
          <Button onClick={analyze} disabled={disabled} size="lg" className="min-w-[160px]">
            {isUploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Procesando...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Analizar Fichas
              </>
            )}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
