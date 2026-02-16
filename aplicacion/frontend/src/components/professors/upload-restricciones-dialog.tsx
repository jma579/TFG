'use client';

import { FileText, Loader2, Upload, X } from 'lucide-react';
import * as React from 'react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { importarRestricciones } from '@/lib/api/recursos/restricciones';

interface UploadRestriccionesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function UploadRestriccionesDialog({
  open,
  onOpenChange,
  onSuccess,
}: UploadRestriccionesDialogProps) {
  const { toast } = useToast();
  const [file, setFile] = React.useState<File | null>(null);
  const [loading, setLoading] = React.useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);

    try {
      const res = await importarRestricciones(file);
      const creados = res?.registros_creados ?? 0;
      const eliminados = res?.registros_eliminados ?? 0;

      toast({
        title: "Importación completada",
        description: `Se han creado ${creados} franjas y eliminado ${eliminados}.`,
      });

      // Notificar al padre para refrescar la tabla
      if (onSuccess) {
        onSuccess();
      }

      // Limpiar y cerrar
      setFile(null);
      onOpenChange(false);
    } catch (error: unknown) {
      console.error("Error subiendo restricciones:", error);
      
      toast({
        variant: "destructive",
        title: "Error en la importación",
        description: "El servidor no pudo procesar el archivo. Verifique el formato.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Subir restricciones</DialogTitle>
          <DialogDescription>
            Seleccione el archivo Excel con las restricciones de los profesores.
            Este proceso reemplazará las restricciones actuales.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="flex flex-col items-center justify-center border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 transition-colors hover:border-muted-foreground/50">
            {!file ? (
              <label className="flex flex-col items-center justify-center cursor-pointer space-y-2 w-full">
                <div className="p-3 bg-primary/10 rounded-full">
                  <Upload className="h-6 w-6 text-primary" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium">Haga clic para seleccionar</p>
                  <p className="text-xs text-muted-foreground">Excel (.xlsx)</p>
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept=".xlsx"
                  onChange={handleFileChange}
                  disabled={loading}
                />
              </label>
            ) : (
              <div className="flex items-center justify-between w-full bg-muted/50 p-3 rounded-md">
                <div className="flex items-center gap-3">
                  <FileText className="h-8 w-8 text-primary" />
                  <div className="flex flex-col">
                    <span className="text-sm font-medium truncate max-w-[200px]">
                      {file.name}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {(file.size / 1024).toFixed(1)} KB
                    </span>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setFile(null)}
                  disabled={loading}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancelar
          </Button>
          <Button onClick={handleUpload} disabled={!file || loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Subiendo...
              </>
            ) : (
              'Subir archivo'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}