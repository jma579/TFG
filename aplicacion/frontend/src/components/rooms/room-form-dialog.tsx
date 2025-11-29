'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import type { Room } from './data';

type RoomFormValues = {
  nombre: string;
  codigo: string;
  tipo: string;
  capacidad: string;
};

type RoomFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial: Room | null;
  onSubmit: (values: { nombre: string; codigo: string; tipo: string; capacidad: number | null }) => Promise<void> | void;
  saving: boolean;
};

export function RoomFormDialog({
  open,
  onOpenChange,
  initial,
  onSubmit,
  saving,
}: RoomFormDialogProps) {
  const [form, setForm] = React.useState<RoomFormValues>({
    nombre: '',
    codigo: '',
    tipo: '',
    capacidad: '',
  });

  React.useEffect(() => {
    if (initial) {
      setForm({
        nombre: initial.nombre,
        codigo: initial.codigo,
        tipo: initial.tipo,
        capacidad:
          initial.capacidad != null && !Number.isNaN(initial.capacidad)
            ? String(initial.capacidad)
            : '',
      });
    } else {
      setForm({ nombre: '', codigo: '', tipo: '', capacidad: '' });
    }
  }, [initial, open]);

  const handleChange = (field: keyof RoomFormValues, value: string) => {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedCap = form.capacidad.trim();
    const numericCap = trimmedCap ? Number(trimmedCap) : null;

    await onSubmit({
      nombre: form.nombre.trim(),
      codigo: form.codigo.trim(),
      tipo: form.tipo.trim(),
      capacidad: Number.isNaN(numericCap) ? null : numericCap,
    });
  };

  const isEdit = initial != null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Editar aula' : 'Nueva aula'}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Modifica los datos del aula y guarda los cambios.'
              : 'Introduce los datos para crear una nueva aula.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="nombre">Nombre</Label>
              <Input
                id="nombre"
                value={form.nombre}
                onChange={(e) => handleChange('nombre', e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="codigo">Código</Label>
              <Input
                id="codigo"
                value={form.codigo}
                onChange={(e) => handleChange('codigo', e.target.value)}
                required
              />
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="tipo">Tipo</Label>
            <Input
              id="tipo"
              value={form.tipo}
              onChange={(e) => handleChange('tipo', e.target.value)}
              placeholder="teorica, laboratorio, informatica…"
              required
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="capacidad">Capacidad</Label>
            <Input
              id="capacidad"
              type="number"
              min={0}
              value={form.capacidad}
              onChange={(e) => handleChange('capacidad', e.target.value)}
              placeholder="Número máximo de estudiantes"
            />
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
              Cancelar
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear aula'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}