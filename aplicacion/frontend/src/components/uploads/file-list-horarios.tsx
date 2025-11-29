'use client';

import * as React from 'react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import type { UploadItem } from './types';

type Props = {
  items: (UploadItem & { confirmed?: boolean })[];
  onRemove: (id: string) => void;
};

function humanSize(bytes: number) {
  const units = ['B','KB','MB','GB'];
  let i = 0, v = bytes;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(v >= 10 ? 0 : 1)} ${units[i]}`;
}

function StatusBadge({ it }: { it: UploadItem & { confirmed?: boolean } }) {
  if (it.confirmed) return <Badge variant="secondary">Confirmado</Badge>;
  if (it.status === 'pending') return <Badge variant="outline">Pendiente</Badge>;
  if (it.status === 'uploading') return <Badge variant="default">Analizando…</Badge>;
  if (it.status === 'done') return <Badge variant="secondary">Listo para revisión</Badge>;
  return <Badge variant="destructive">Error</Badge>;
}

export function FileListHorarios({ items, onRemove }: Props) {
  if (!items.length) {
    return (
      <div className="rounded-md border bg-muted/20 p-6 text-center text-sm text-muted-foreground">
        No hay archivos seleccionados todavía.
      </div>
    );
  }

  return (
    <div className="rounded-md border bg-card">
      {items.map((it) => {
        const reviewHref = `/uploads/horarios/revision/${it.id}`;
        return (
          <div key={it.id} className="flex items-center gap-3 px-4 py-3">
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

                  {/* CTA cuando termine el análisis y no haya error */}
                  {it.status === 'done' && !it.confirmed && (
                  <Button asChild size="sm">
                      <Link href={reviewHref}>Revisar extracción</Link>
                  </Button>
                  )}

                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" aria-label="Más acciones">⋮</Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Acciones</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => onRemove(it.id)}>Eliminar</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>

              {/* Progreso individual */}
              <div className="mt-2">
                <Progress value={it.progress} />
                {it.status === 'error' && it.errorMessage && (
                  <p className="mt-1 text-xs text-destructive">{it.errorMessage}</p>
                )}
              </div>
            </div>
          </div>
        );
      })}

      <Separator />
      <p className="px-4 py-2 text-right text-xs text-muted-foreground">
        Archivos: {items.length}
      </p>
    </div>
  );
}
