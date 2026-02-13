'use client';

import { AlertTriangle,Loader2, Play } from 'lucide-react';
import { useRouter } from 'next/navigation';
import * as React from 'react';

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
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
import { useHorariosUploadsStore } from '@/stores/horarios-uploads';

import { DropzoneHorarios } from './dropzone-horarios';
import { FileListHorarios } from './file-list-horarios';

export function UploadHorariosScreen() {
  const router = useRouter();

  const items = useHorariosUploadsStore((s) => s.items);
  const addFiles = useHorariosUploadsStore((s) => s.addFiles);
  const remove = useHorariosUploadsStore((s) => s.remove);
  const startAnalyze = useHorariosUploadsStore((s) => s.startAnalyze);
  const clear = useHorariosUploadsStore((s) => s.clear);

  const isUploading = items.some((i) => i.status === 'uploading');
  const disabledAnalyze = items.length === 0 || isUploading;

  const pendientesAnalizar = items.filter((i) => i.status === 'pending' || i.status === 'uploading').length;
  const pendientesConfirmar = items.filter((i) => i.status === 'done' && !i.confirmed).length;
  const hayPendientes = pendientesAnalizar + pendientesConfirmar > 0;

  const [open, setOpen] = React.useState(false);

  const handleTerminarClick = () => {
    if (hayPendientes) {
      setOpen(true); 
    } else {
      clear();
      router.push('/datos/horarios'); 
    }
  };

  const confirmarSalida = () => {
    setOpen(false);
    clear();
    router.push('/datos/horarios'); 
  };

  return (
    <Card className="border-border shadow-sm">
      <CardHeader>
        <CardTitle>Subir Horarios</CardTitle>
        <CardDescription>
          Analiza los documentos de horarios para extraer sesiones.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        <DropzoneHorarios onFiles={addFiles} />

        {items.length > 0 && (
          <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="mb-4 flex items-center gap-2">
                <Separator className="flex-1" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Archivos en cola ({items.length})
                </span>
                <Separator className="flex-1" />
            </div>
            <FileListHorarios items={items} onRemove={remove} />
          </div>
        )}
      </CardContent>

      {items.length > 0 && (
        <CardFooter className="flex justify-between border-t bg-muted/40 px-6 py-4">
          <div className="text-sm text-muted-foreground">
          </div>
          
          <div className="flex gap-3">
            <AlertDialog open={open} onOpenChange={setOpen}>
              <AlertDialogTrigger asChild>
                <Button variant="outline" onClick={handleTerminarClick}>
                  Terminar
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-amber-500" />
                    Hay archivos pendientes
                  </AlertDialogTitle>
                  <AlertDialogDescription className="space-y-2 pt-2">
                    {pendientesAnalizar > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                        <span>{pendientesAnalizar} archivo(s) pendiente(s) de analizar.</span>
                      </div>
                    )}
                    {pendientesConfirmar > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                        <span>{pendientesConfirmar} archivo(s) listo(s) para revisión pero sin confirmar.</span>
                      </div>
                    )}
                    <p className="pt-2 font-medium text-foreground">
                      Si sales ahora, perderás el progreso no guardado. ¿Quieres ir a la página de horarios de todos modos?
                    </p>
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Seguir aquí</AlertDialogCancel>
                  <AlertDialogAction onClick={confirmarSalida} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                    Terminar de todos modos
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            <Button onClick={startAnalyze} disabled={disabledAnalyze} className="min-w-[160px]">
              {isUploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Analizar horarios
                </>
              )}
            </Button>
          </div>
        </CardFooter>
      )}
    </Card>
  );
}