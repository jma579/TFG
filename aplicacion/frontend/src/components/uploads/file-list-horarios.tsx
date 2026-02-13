'use client';

import { 
  AlertCircle, 
  ArrowRight,
  CheckCircle2, 
  Clock, 
  FileText, 
  Loader2, 
  MoreVertical, 
  Trash2,
  XCircle} from 'lucide-react';
import Link from 'next/link';
import * as React from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator,
DropdownMenuTrigger, } from '@/components/ui/dropdown-menu';
import { Progress } from '@/components/ui/progress';

import type { UploadItem } from './types';

type ExtendedUploadItem = UploadItem & { 
  confirmed?: boolean; 
  progress?: number; 
};

type Props = {
  items: ExtendedUploadItem[];
  onRemove: (id: string) => void;
};

function humanSize(bytes: number) {
  const units = ['B','KB','MB','GB'];
  let i = 0, v = bytes;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(v >= 10 ? 0 : 1)} ${units[i]}`;
}

function StatusBadge({ it }: { it: ExtendedUploadItem }) {
  if (it.confirmed) {
    return (
      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 gap-1.5 font-normal">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Confirmado
      </Badge>
    );
  }
  if (it.status === 'pending') {
    return (
      <Badge variant="outline" className="bg-slate-50 text-slate-600 border-slate-200 gap-1.5 font-normal">
        <Clock className="h-3.5 w-3.5" />
        Pendiente
      </Badge>
    );
  }
  if (it.status === 'uploading') {
    return (
      <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 gap-1.5 font-normal">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Analizando...
      </Badge>
    );
  }
  if (it.status === 'done') {
    return (
      <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200 gap-1.5 font-normal">
        <AlertCircle className="h-3.5 w-3.5" />
        Listo para revisión
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200 gap-1.5 font-normal">
      <XCircle className="h-3.5 w-3.5" />
      Error
    </Badge>
  );
}

export function FileListHorarios({ items, onRemove }: Props) {
  if (!items.length) {
    return (
      <div className="rounded-md border border-dashed bg-muted/20 p-8 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <FileText className="h-6 w-6 text-muted-foreground" />
        </div>
        <h3 className="mt-2 text-sm font-semibold text-foreground">No hay archivos</h3>
        <p className="mt-1 text-sm text-muted-foreground">Sube los documentos de horarios para comenzar.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card shadow-sm divide-y">
      {items.map((it) => {
        const reviewHref = `/uploads/horarios/revision/${it.id}`;
        return (
          <div key={it.id} className="flex items-center gap-4 p-4 hover:bg-muted/30 transition-colors">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <FileText className="h-5 w-5" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">{it.file.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {it.file.type || 'application/pdf'} · {humanSize(it.file.size)}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <StatusBadge it={it} />

                  {it.status === 'done' && !it.confirmed && (
                  <Button asChild size="sm" variant="default" className="h-8 text-xs">
                      <Link href={reviewHref}>
                        Revisar
                        <ArrowRight className="ml-1.5 h-3 w-3" />
                      </Link>
                  </Button>
                  )}

                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                        <MoreVertical className="h-4 w-4" />
                        <span className="sr-only">Más acciones</span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Acciones</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem 
                        onClick={() => onRemove(it.id)}
                        className="text-red-600 focus:text-red-600 focus:bg-red-50"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Eliminar
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>

              <div className="mt-3">
                {it.status === 'uploading' && (
                  <Progress value={it.progress} className="h-1" />
                )}
                {it.status === 'error' && it.errorMessage && (
                  <p className="mt-1 text-xs text-red-600 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {it.errorMessage}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}