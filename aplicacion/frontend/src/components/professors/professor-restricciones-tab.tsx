'use client';

import { Calendar,Clock, Plus, Trash2 } from 'lucide-react';
import * as React from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api/config';

type Restriccion = {
  id: number;
  dia_semana: string;
  hora_inicio: string;
  hora_fin: string;
};

export function ProfessorRestriccionesTab({ 
  profesorId,
  onRestriccionesChanged 
}: { 
  profesorId: string;
  onRestriccionesChanged?: () => void;
}) {
  const { toast } = useToast();
  const [restricciones, setRestricciones] = React.useState<Restriccion[]>([]);
  const [loading, setLoading] = React.useState(true);
  
  // Estado para la nueva restricción
  const [nuevoDia, setNuevoDia] = React.useState('lunes');
  const [inicio, setInicio] = React.useState('08:00');
  const [fin, setFin] = React.useState('10:00');

  const cargar = React.useCallback(async () => {
    try {
      const res = await api.get(`/v0/recursos/profesores/${profesorId}/restricciones`);
      setRestricciones(res.data || res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [profesorId]);

  React.useEffect(() => { cargar(); }, [cargar]);

  const handleAdd = async () => {
    try {
      await api.post(`/v0/recursos/profesores/${profesorId}/restricciones`, {
        dia_semana: nuevoDia,
        hora_inicio: `${inicio}:00`,
        hora_fin: `${fin}:00`
      });
      toast({ title: "Restricción añadida" });
      await cargar();
      if (onRestriccionesChanged) onRestriccionesChanged();
    } catch {
      toast({ variant: "destructive", title: "Error al añadir" });
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/v0/recursos/restricciones/${id}`);
      setRestricciones(prev => prev.filter(r => r.id !== id));
      toast({ title: "Restricción eliminada" });
      if (onRestriccionesChanged) onRestriccionesChanged();
    } catch {
      toast({ variant: "destructive", title: "Error al eliminar" });
    }
  };

  if (loading) return <div className="p-4 text-center text-sm">Cargando franjas...</div>;

  return (
    <div className="space-y-6 py-4">
      <div className="grid grid-cols-4 gap-2 items-end bg-muted/30 p-3 rounded-lg border">
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase text-muted-foreground">Día</label>
          <Select value={nuevoDia} onValueChange={setNuevoDia}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {['lunes', 'martes', 'miercoles', 'jueves', 'viernes'].map(d => (
                <SelectItem key={d} value={d} className="capitalize">{d}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase text-muted-foreground">Inicio</label>
          <Input type="time" value={inicio} onChange={e => setInicio(e.target.value)} className="h-8 text-xs" />
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-bold uppercase text-muted-foreground">Fin</label>
          <Input type="time" value={fin} onChange={e => setFin(e.target.value)} className="h-8 text-xs" />
        </div>
        <Button size="sm" className="h-8 gap-1" onClick={handleAdd}>
          <Plus className="h-3 w-3" /> Añadir
        </Button>
      </div>

      <div className="space-y-2">
        {restricciones.map(r => (
          <div key={r.id} className="flex items-center justify-between p-2 border rounded-md text-sm">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1 w-24">
                <Calendar className="h-3 w-3 text-primary" />
                <span className="font-medium capitalize">{r.dia_semana}</span>
              </div>
              <div className="flex items-center gap-1 text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>{r.hora_inicio.substring(0, 5)} - {r.hora_fin.substring(0, 5)}</span>
              </div>
            </div>
            <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-500 hover:text-red-700" onClick={() => handleDelete(r.id)}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}