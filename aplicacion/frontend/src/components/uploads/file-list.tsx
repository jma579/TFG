'use client';

import { 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  Eye, 
  FileText,
  Loader2, 
  MoreVertical,
  Pencil, 
  Trash2, 
  XCircle} from 'lucide-react';
import * as React from 'react';

import { SubjectDetailView } from '@/components/subjects/subject-detail-view';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';

import { UploadItem } from './types';

type Props = {
  items: UploadItem[];
  onRemove: (id: string) => void;
  onRename?: (id: string, newName: string) => void;
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
    if (it.result === 'ok') {
      return (
        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 gap-1.5 font-normal">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Completado
        </Badge>
      );
    }
    if (it.result === 'incidencias') {
      return (
        <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 gap-1.5 font-normal">
          <AlertCircle className="h-3.5 w-3.5" />
          Incidencias
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
  return (
    <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200 gap-1.5 font-normal">
      <XCircle className="h-3.5 w-3.5" />
      Error
    </Badge>
  );
}

type ExtractionSummaryResult = {
  asignatura_id?: number | string;
  programas_asociados?: unknown[];
  profesores_asociados?: unknown[];
  created_entities?: {
    asignaturas_creadas?: number;
    [key: string]: unknown;
  };
  [key: string]: unknown;
};

function ExtractionSummary({ result }: { result: ExtractionSummaryResult }) {
  if (!result) return null;
  
  const { asignatura_id, programas_asociados, profesores_asociados, created_entities } = result;

  return (
    <div className="grid grid-cols-2 gap-3 mb-4">
      <div className="bg-slate-50 p-3 rounded-md border border-slate-100">
        <span className="text-muted-foreground text-xs font-medium uppercase tracking-wider block mb-1">ID Asignatura</span>
        <span className="font-semibold text-slate-900">{asignatura_id ?? '-'}</span>
      </div>
      <div className="bg-slate-50 p-3 rounded-md border border-slate-100">
        <span className="text-muted-foreground text-xs font-medium uppercase tracking-wider block mb-1">Programas</span>
        <span className="font-semibold text-slate-900">{programas_asociados?.length ?? 0} vinculados</span>
      </div>
      <div className="bg-slate-50 p-3 rounded-md border border-slate-100">
        <span className="text-muted-foreground text-xs font-medium uppercase tracking-wider block mb-1">Profesores</span>
        <span className="font-semibold text-slate-900">{profesores_asociados?.length ?? 0} vinculados</span>
      </div>
      <div className="bg-slate-50 p-3 rounded-md border border-slate-100">
        <span className="text-muted-foreground text-xs font-medium uppercase tracking-wider block mb-1">Entidades</span>
        <span className="font-semibold text-slate-900">
            {created_entities?.asignaturas_creadas ?? 0} creadas
        </span>
      </div>
    </div>
  );
}

export function FileList({ items, onRemove, onRename }: Props) {
  const [detailsItem, setDetailsItem] = React.useState<UploadItem | null>(null);
  const [renamingItem, setRenamingItem] = React.useState<UploadItem | null>(null);
  const [newName, setNewName] = React.useState('');

  const handleRenameClick = (item: UploadItem) => {
    setRenamingItem(item);
    setNewName(item.file.name);
  };

  const handleRenameSave = () => {
    if (renamingItem && newName.trim()) {
      onRename?.(renamingItem.id, newName.trim());
      setRenamingItem(null);
    }
  };

  if (!items.length) {
    return (
      <div className="rounded-md border border-dashed bg-muted/20 p-8 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <FileText className="h-6 w-6 text-muted-foreground" />
        </div>
        <h3 className="mt-2 text-sm font-semibold text-foreground">No hay archivos</h3>
        <p className="mt-1 text-sm text-muted-foreground">Sube las guías docentes para comenzar.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card shadow-sm divide-y">
      {items.map((it) => (
        <div key={it.id} className="flex items-center gap-4 p-4 hover:bg-muted/30 transition-colors">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
            <FileText className="h-5 w-5" />
          </div>
          
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{it.file.name}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {humanSize(it.file.size)}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <StatusBadge it={it} />

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                      <MoreVertical className="h-4 w-4" />
                      <span className="sr-only">Más acciones</span>
                    </Button>
                  </DropdownMenuTrigger>

                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuLabel>Acciones</DropdownMenuLabel>

                    {it.status === 'done' && (
                      <DropdownMenuItem onClick={() => setDetailsItem(it)}>
                        <Eye className="mr-2 h-4 w-4 text-muted-foreground" />
                        Ver detalles
                      </DropdownMenuItem>
                    )}

                    <DropdownMenuItem onClick={() => handleRenameClick(it)}>
                      <Pencil className="mr-2 h-4 w-4 text-muted-foreground" />
                      Renombrar
                    </DropdownMenuItem>

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

            {it.status === 'error' && it.errorMessage && (
              <p className="mt-2 text-xs text-red-600 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                {it.errorMessage}
              </p>
            )}
          </div>
        </div>
      ))}

      {/* Dialog: Detalles */}
      <Dialog open={detailsItem != null} onOpenChange={(open) => !open && setDetailsItem(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-600" />
              Detalles de Extracción
            </DialogTitle>
            <DialogDescription>
              Información extraída del documento <span className="font-medium text-foreground">"{detailsItem?.file.name}"</span>.
            </DialogDescription>
          </DialogHeader>

          {detailsItem?.backendResult ? (
            <div className="space-y-4 py-2">
              {detailsItem.backendResult.errors?.length ? (
                <div className="rounded-md bg-red-50 p-3 border border-red-100">
                  <div className="flex items-center gap-2 text-red-800 font-medium text-sm mb-2">
                    <AlertCircle className="h-4 w-4" />
                    Incidencias detectadas
                  </div>
                  <ul className="list-disc list-inside text-xs text-red-700 space-y-1 ml-1">
                    {detailsItem.backendResult.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="rounded-md bg-green-50 p-3 border border-green-100 flex items-center gap-2 text-green-700 text-sm">
                  <CheckCircle2 className="h-4 w-4" />
                  Procesamiento completado sin incidencias.
                </div>
              )}

              <Separator />
              
              {detailsItem.backendResult.asignatura_id ? (
                <div className="mt-4">
                  <SubjectDetailView 
                    asignaturaId={Number(detailsItem.backendResult.asignatura_id)} 
                    extractionStatus={{
                      success: detailsItem.backendResult.success,
                      errors: detailsItem.backendResult.errors
                    }}
                  />
                </div>
              ) : (
                <div>
                  <h4 className="text-sm font-medium mb-3">Datos Extraídos</h4>
                  <ExtractionSummary result={detailsItem.backendResult} />
                </div>
              )}
            </div>
          ) : (
            <div className="py-8 text-center text-muted-foreground">
              No hay información detallada disponible para este archivo.
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailsItem(null)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Renombrar */}
      <Dialog open={renamingItem != null} onOpenChange={(open) => !open && setRenamingItem(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Renombrar archivo</DialogTitle>
            <DialogDescription>
              Cambia el nombre del archivo antes de procesarlo.
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nombre</Label>
              <Input
                id="name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Ej. Guia_Docente_2024.pdf"
                onKeyDown={(e) => e.key === 'Enter' && handleRenameSave()}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setRenamingItem(null)}>Cancelar</Button>
            <Button onClick={handleRenameSave}>Guardar cambios</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}