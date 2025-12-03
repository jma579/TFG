'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { UploadItem } from './types';

type Props = {
  items: UploadItem[];
  onRemove: (id: string) => void;
  onRename?: (id: string) => void;
};

function humanSize(bytes: number) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v >= 10 ? 0 : 1)} ${units[i]}`;
}

function StatusBadge({ it }: { it: UploadItem }) {
  if (it.status === 'pending') return <Badge variant="outline">Pendiente</Badge>;
  if (it.status === 'uploading') return <Badge variant="default">Analizando…</Badge>;
  if (it.status === 'done') {
    if (it.result === 'ok') return <Badge variant="secondary">OK</Badge>;
    if (it.result === 'incidencias') return <Badge variant="default">Con incidencias</Badge>;
    return <Badge variant="destructive">Error</Badge>;
  }
  return <Badge variant="destructive">Error</Badge>;
}

function LoadingSpinner() {
  return (
    <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
      <span
        className="inline-block h-3 w-3 animate-spin rounded-full border border-current border-t-transparent"
        aria-hidden="true"
      />
      <span>Analizando ficha…</span>
    </div>
  );
}

export function FileList({ items, onRemove, onRename }: Props) {
  const [detailsItem, setDetailsItem] = React.useState<UploadItem | null>(null);

  if (!items.length) {
    return (
      <div className="rounded-md border bg-muted/20 p-6 text-center text-sm text-muted-foreground">
        No hay archivos seleccionados todavía.
      </div>
    );
  }

  return (
    <div className="rounded-md border bg-card">
      {items.map((it) => (
        <div key={it.id} className="flex items-center gap-3 px-4 py-3 border-b last:border-none">
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{it.file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {it.file.type || 'application/pdf'} · {humanSize(it.file.size)}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <StatusBadge it={it} />

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" aria-label="Más acciones">
                      ⋮
                    </Button>
                  </DropdownMenuTrigger>

                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Acciones</DropdownMenuLabel>

                    {it.status === 'done' && (
                      <DropdownMenuItem onClick={() => setDetailsItem(it)}>
                        Ver detalles
                      </DropdownMenuItem>
                    )}

                    <DropdownMenuItem onClick={() => onRename?.(it.id)}>
                      Renombrar
                    </DropdownMenuItem>

                    <DropdownMenuSeparator />

                    <DropdownMenuItem onClick={() => onRemove(it.id)}>
                      Eliminar
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            <div className="mt-2">
              {it.status === 'uploading' && <LoadingSpinner />}

              {it.status === 'done' && it.result && (
                <p className="text-xs text-muted-foreground">Resultado: {it.result}</p>
              )}

              {it.status === 'error' && it.errorMessage && (
                <p className="text-xs text-destructive">{it.errorMessage}</p>
              )}
            </div>
          </div>
        </div>
      ))}

      {/* Dialog global controlado por detailsItem */}
      <Dialog open={detailsItem != null} onOpenChange={(open) => !open && setDetailsItem(null)}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>
              Detalles del procesamiento
              {detailsItem && (
                <span className="block text-xs font-normal text-muted-foreground">
                  {detailsItem.file.name}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>

          {detailsItem?.backendResult ? (
            <div className="space-y-4">
              {detailsItem.backendResult.errors?.length ? (
                <div>
                  <p className="font-medium text-sm">Incidencias detectadas:</p>
                  <ul className="mt-1 list-disc list-inside text-sm text-red-600">
                    {detailsItem.backendResult.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="text-sm text-green-700">No se detectaron incidencias.</p>
              )}

              <Separator />

              <div className="max-h-64 overflow-auto rounded-md bg-muted/30 p-2">
                <pre className="text-xs">
                  {JSON.stringify(detailsItem.backendResult, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No hay información disponible.
            </p>
          )}

          <DialogFooter>
            <Button onClick={() => setDetailsItem(null)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Separator />
      <p className="px-4 py-2 text-right text-xs text-muted-foreground">Archivos: {items.length}</p>
    </div>
  );
}
