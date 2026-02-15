'use client';

import * as React from 'react';
import { Upload, AlertTriangle, FileCheck, XCircle } from 'lucide-react';
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

type UploadRestriccionesDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
};

export function UploadRestriccionesDialog({
  open,
  onOpenChange,
  onSuccess,
}: UploadRestriccionesDialogProps) {
  const { toast } = useToast();
  const [file, setFile] = React.useState<File | null>(null);
  const [uploading, setUploading] = React.useState(false);
  const [errors, setErrors] = React.useState<string[]>([]);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrors([]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setErrors([]);

    try {
      const res = await importarRestricciones(file);
      
      toast({
        title: 'Importación completada',
        description: `Se han creado ${res.registros_creados} restricciones y eliminado ${res.registros_eliminados} anteriores.`,
      });

      onSuccess?.();
      onOpenChange(false);
      setFile(null);
    } catch (error: unknown) {
        const err = error as { response?: { data?: { detail?: { errores?: string[] } } }; message?: string };
        const detail = err.response?.data?.detail;
        if (detail && detail.errores) {
        setErrors(detail.errores);
        } else {
        toast({
            variant: 'destructive',
            title: 'Error crítico',
            description: err.message || 'Error al conectar con el servidor.',
        });
        }
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => {
      if (!uploading) {
        onOpenChange(o);
        if (!o) { setFile(null); setErrors([]); }
      }
    }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Importar Restricciones
          </DialogTitle>
          <DialogDescription>
            Sube el archivo Excel con las restricciones horarias. 
            <span className="block mt-2 font-semibold text-amber-600 flex items-center gap-1">
              <AlertTriangle className="h-4 w-4" /> 
              Atención: Se borrarán todas las restricciones actuales.
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div 
            onClick={() => fileInputRef.current?.click()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
              ${file ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
            `}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              accept=".xlsx" 
              onChange={handleFileChange}
            />
            {file ? (
              <div className="flex flex-col items-center gap-2">
                <FileCheck className="h-8 w-8 text-primary" />
                <p className="text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">Haga clic para cambiar el archivo</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 text-muted-foreground">
                <Upload className="h-8 w-8" />
                <p className="text-sm">Haga clic para seleccionar el Excel</p>
                <p className="text-xs">Formato permitido: .xlsx</p>
              </div>
            )}
          </div>

          {errors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3 max-h-40 overflow-y-auto">
              <p className="text-xs font-bold text-red-700 flex items-center gap-1 mb-2">
                <XCircle className="h-3 w-3" /> Errores de validación:
              </p>
              <ul className="list-disc pl-4 space-y-1">
                {errors.map((err, i) => (
                  <li key={i} className="text-[11px] text-red-600">{err}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={uploading}>
            Cancelar
          </Button>
          <Button onClick={handleUpload} disabled={!file || uploading}>
            {uploading ? 'Procesando...' : 'Iniciar Importación'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}