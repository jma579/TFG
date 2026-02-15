import React from 'react';
import { Calendar, Clock, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { getRestriccionesByProfesor, type Restriccion } from '@/lib/api/recursos/restricciones';

interface QuickViewRestriccionesProps {
  profesorId: string | null;
  profesorNombre: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Mapeo de días para convertir número o enum a texto
const DIAS_MAP: Record<number | string, string> = {
  1: 'Lunes',
  2: 'Martes',
  3: 'Miércoles',
  4: 'Jueves',
  5: 'Viernes',
  6: 'Sábado',
  7: 'Domingo',
  'MONDAY': 'Lunes',
  'TUESDAY': 'Martes',
  'WEDNESDAY': 'Miércoles',
  'THURSDAY': 'Jueves',
  'FRIDAY': 'Viernes',
  'SATURDAY': 'Sábado',
  'SUNDAY': 'Domingo',
};

const capitalizeFirstLetter = (str: string): string => {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
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
          // La función ya devuelve Promise<Restriccion[]> según restricciones.ts
          const data = await getRestriccionesByProfesor(profesorId);
          
          // Verificamos que sea un array antes de asignar
          if (Array.isArray(data)) {
            setRestricciones(data);
          } else {
            setRestricciones([]);
          }
        } catch (error) {
          console.error("Error cargando restricciones:", error);
          setRestricciones([]);
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
                    <span className="text-sm font-medium">
                      {capitalizeFirstLetter(DIAS_MAP[r.dia_semana] || String(r.dia_semana))}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                      {r.hora_inicio?.substring(0, 5)} - {r.hora_fin?.substring(0, 5)}
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