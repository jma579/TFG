'use client';

import * as React from 'react';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { createAula, updateAula, type AulaOut } from '@/lib/api/recursos/aulas';
import { useToast } from '@/hooks/use-toast';

const TIPOS_AULA = [
  { value: 'teorica', label: 'Teórica' },
  { value: 'laboratorio', label: 'Laboratorio' },
  { value: 'informatica', label: 'Informática' },
  { value: 'seminario', label: 'Seminario' },
  { value: 'taller', label: 'Taller' },
  { value: 'auditorio', label: 'Auditorio' },
  { value: 'biblioteca', label: 'Biblioteca' },
  { value: 'gimnasio', label: 'Gimnasio' },
  { value: 'virtual', label: 'Virtual' },
];

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData?: AulaOut | null;
  onSuccess?: (aula: AulaOut) => void;
};

export function RoomFormDialog({ open, onOpenChange, initialData, onSuccess }: Props) {
  const { toast } = useToast();
  const [loading, setLoading] = React.useState(false);

  const [formData, setFormData] = React.useState({
    nombre: '',
    codigo: '',
    tipo: 'teorica',
    capacidad: 40,
  });

  React.useEffect(() => {
    if (open) {
      if (initialData) {
        setFormData({
          nombre: initialData.nombre,
          codigo: initialData.codigo,
          tipo: initialData.tipo,
          capacidad: initialData.capacidad ?? 0,
        });
      } else {
        setFormData({
          nombre: '',
          codigo: '',
          tipo: 'teorica',
          capacidad: 40,
        });
      }
    }
  }, [open, initialData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      let result: AulaOut;

      if (initialData) {
        result = await updateAula(initialData.id, formData);
        toast({ title: 'Aula actualizada correctamente' });
      } else {
        result = await createAula(formData);
        toast({ title: 'Aula creada correctamente' });
      }

      onSuccess?.(result);
      onOpenChange(false);
    } catch (error: unknown) {
      console.error(error);
      toast({
        variant: 'destructive',
        title: 'Error al guardar',
        description: error instanceof Error ? error.message : 'Error desconocido',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{initialData ? 'Editar Aula' : 'Nueva Aula'}</DialogTitle>
          <DialogDescription>
            {initialData
              ? 'Modifica los datos del aula existente.'
              : 'Registra un nuevo espacio docente.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="nombre" className="text-right">
              Nombre
            </Label>
            <Input
              id="nombre"
              value={formData.nombre}
              onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
              className="col-span-3"
              placeholder="Ej. Aula 1.1"
              required
            />
          </div>

          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="codigo" className="text-right">
              Código
            </Label>
            <Input
              id="codigo"
              value={formData.codigo}
              onChange={(e) => setFormData({ ...formData, codigo: e.target.value })}
              className="col-span-3"
              placeholder="Ej. A1.1"
              required
            />
          </div>

          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="tipo" className="text-right">
              Tipo
            </Label>
            <div className="col-span-3">
              <Select
                value={formData.tipo}
                onValueChange={(val) => setFormData({ ...formData, tipo: val })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona tipo" />
                </SelectTrigger>
                <SelectContent>
                  {TIPOS_AULA.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="capacidad" className="text-right">
              Capacidad
            </Label>
            <Input
              id="capacidad"
              type="number"
              min={1}
              value={formData.capacidad}
              onChange={(e) => setFormData({ ...formData, capacidad: Number(e.target.value) })}
              className="col-span-3"
              required
            />
          </div>

          <DialogFooter className="mt-4">
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {initialData ? 'Guardar cambios' : 'Crear Aula'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}