'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { DropzoneHorarios } from './dropzone-horarios';
import { FileListHorarios } from './file-list-horarios';
import { useHorariosUploadsStore } from '@/stores/horarios-uploads';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

export function UploadHorariosScreen() {
  const router = useRouter();

  const items = useHorariosUploadsStore((s) => s.items);
  const addFiles = useHorariosUploadsStore((s) => s.addFiles);
  const remove = useHorariosUploadsStore((s) => s.remove);
  const startAnalyze = useHorariosUploadsStore((s) => s.startAnalyze);
  const clear = useHorariosUploadsStore((s) => s.clear); // ← NUEVO

  const disabledAnalyze = items.length === 0 || items.some((i) => i.status === 'uploading');

  const pendientesAnalizar = items.filter((i) => i.status === 'pending' || i.status === 'uploading').length;
  const pendientesConfirmar = items.filter((i) => i.status === 'done' && !i.confirmed).length;
  const hayPendientes = pendientesAnalizar + pendientesConfirmar > 0;

  const [open, setOpen] = React.useState(false);

  const handleTerminarClick = () => {
    if (hayPendientes) {
      setOpen(true);
    } else {
      clear();            // ← limpia antes de salir
      router.push('/app');
    }
  };

  const confirmarSalida = () => {
    setOpen(false);
    clear();              // ← limpia aunque haya pendientes
    router.push('/app');
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <DropzoneHorarios onFiles={addFiles} />

      <div className="flex items-center justify-between">
        <div />
        <div className="flex gap-2">
          <Button onClick={startAnalyze} disabled={disabledAnalyze}>Analizar horarios</Button>

          <AlertDialog open={open} onOpenChange={setOpen}>
            <AlertDialogTrigger asChild>
              <Button variant="outline" onClick={handleTerminarClick}>Terminar</Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Hay archivos pendientes</AlertDialogTitle>
                <AlertDialogDescription>
                  {pendientesAnalizar > 0 && (<span className="block">• {pendientesAnalizar} archivo(s) pendiente(s) de analizar.</span>)}
                  {pendientesConfirmar > 0 && (<span className="block">• {pendientesConfirmar} archivo(s) listo(s) para revisión pero sin confirmar.</span>)}
                  <span className="block">¿Quieres volver igualmente a la página principal o prefieres seguir aquí para completar el proceso?</span>
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Seguir aquí</AlertDialogCancel>
                <AlertDialogAction onClick={confirmarSalida}>Terminar de todos modos</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <FileListHorarios items={items} onRemove={remove} />
    </div>
  );
}
