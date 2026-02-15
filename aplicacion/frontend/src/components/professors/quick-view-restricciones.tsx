'use client';

import { Calendar, Clock, Loader2 } from 'lucide-react';
import * as React from 'react';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { api } from '@/lib/api/config';

type Restriccion = {
  id: number;
  dia_semana: string;
  hora_inicio: string;
  hora_fin: string;
};

type QuickViewRestriccionesProps = {
  profesorId: string | null;
  profesorNombre: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function QuickViewRestricciones({
  profesorId,
  profesorNombre,
  open,
  onOpenChange,
}: QuickViewRestriccionesProps) {
  const [loading, setLoading] = React.useState(false);
  const [restricciones, setRestricciones] = React.useState<Restriccion[]>([]);

  React.useEffect(() => {
    if (open && profesorId) {
      const fetchRestricciones = async () => {
        setLoading(true);
        try {
          // Llamada al endpoint que creamos en el backend
          const res = await api.get<Restriccion[]>(`/v0/recursos/profesores/${profesorId}/restricciones`);
          setRestricciones(res.data ?? []);
        } catch (error) {
          console.error("Error cargando restricciones:", error);
        } finally {
          setLoading(false);
        }
      };
      fetchRestricciones();
    }
  }, [open, profesorId]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-lg">
            Restricciones: {profesorNombre}
          </DialogTitle>
        </DialogHeader>

        <div className="py-4">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : restricciones.length > 0 ? (
            <div className="space-y-3">
              {restricciones.map((r) => (
                <div 
                  key={r.id} 
                  className="flex items-center justify-between p-3 border rounded-lg bg-muted/30"
                >
                  <div className="flex items-center gap-3">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium capitalize">{r.dia_semana}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                      {r.hora_inicio.substring(0, 5)} - {r.hora_fin.substring(0, 5)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground italic">
              Este profesor no tiene restricciones registradas.
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}