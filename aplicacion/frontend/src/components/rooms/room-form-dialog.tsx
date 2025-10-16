'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogOverlay,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select';
import type { Room } from './data';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSubmit: (room: Omit<Room, 'id'>, editingId?: string) => void;
  locations: string[];
  initial?: Room | null; // si viene → editar
};

export function RoomFormDialog({ open, onOpenChange, onSubmit, locations, initial = null }: Props) {
  const [nombre, setNombre] = React.useState(initial?.nombre ?? '');
  const [capacidad, setCapacidad] = React.useState(initial?.capacidad?.toString() ?? '');
  const [ubicacion, setUbicacion] = React.useState(initial?.ubicacion ?? '');

  React.useEffect(() => {
    setNombre(initial?.nombre ?? '');
    setCapacidad(initial?.capacidad ? String(initial.capacidad) : '');
    setUbicacion(initial?.ubicacion ?? '');
  }, [initial]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const cap = parseInt(capacidad || '0', 10);
    if (!nombre.trim() || !ubicacion || isNaN(cap) || cap <= 0) return;
    onSubmit({ nombre: nombre.trim(), capacidad: cap, ubicacion }, initial?.id);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* Overlay con difuminado */}
      <DialogOverlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" />
      <DialogContent className="z-50 sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{initial ? 'Editar aula' : 'Añadir aula'}</DialogTitle>
          <DialogDescription>
            {initial ? 'Actualiza los datos del aula.' : 'Introduce los datos para registrar un aula.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={submit} className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="nombre">Nombre</Label>
            <Input id="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="capacidad">Capacidad</Label>
            <Input
              id="capacidad"
              inputMode="numeric"
              pattern="[0-9]*"
              value={capacidad}
              onChange={(e) => setCapacidad(e.target.value)}
              required
            />
          </div>

          <div className="grid gap-2">
            <Label>Ubicación</Label>
            <Select value={ubicacion} onValueChange={setUbicacion}>
              <SelectTrigger>
                <SelectValue placeholder="Selecciona ubicación" />
              </SelectTrigger>
              <SelectContent>
                {locations.map((loc) => (
                  <SelectItem key={loc} value={loc}>
                    {loc}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit">{initial ? 'Guardar' : 'Añadir'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
