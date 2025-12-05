'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { RoomsTable } from './table';
import { RoomFormDialog } from './room-form-dialog';
import type { Room } from './data';
import {
  createAula,
  updateAula,
  deleteAula,
  type AulaOut,
} from '@/lib/api/client';
import { useToast } from '@/hooks/use-toast';

export type RoomsScreenProps = {
  initialData: Room[];
};

function mapAulaToRoom(aula: AulaOut): Room {
  return {
    id: String(aula.id),
    nombre: aula.nombre,
    codigo: aula.codigo,
    tipo: aula.tipo,
    capacidad: aula.capacidad ?? null,
  };
}

export function RoomsScreen({ initialData }: RoomsScreenProps) {
  const { toast } = useToast();

  const [rows, setRows] = React.useState<Room[]>(initialData);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Room | null>(null);
  const [saving, setSaving] = React.useState(false);

  const openNew = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = (room: Room) => {
    setEditing(room);
    setDialogOpen(true);
  };

  const handleDelete = async (room: Room) => {
    try {
      await deleteAula(Number(room.id));
      setRows((prev) => prev.filter((r) => r.id !== room.id));
      toast({
        title: 'Aula eliminada',
        description: 'El aula se ha eliminado correctamente.',
      });
    } catch (error: unknown) {
      toast({
        variant: 'destructive',
        title: 'Error al eliminar',
        description:
          error instanceof Error ? error.message : 'No se ha podido eliminar el aula.',
      });
    }
  };

  type RoomFormValues = {
    nombre: string;
    codigo: string;
    tipo: string;
    capacidad: number | null;
  };

  const handleSubmit = async (values: RoomFormValues) => {
    setSaving(true);
    try {
      if (editing) {
        const updated = await updateAula(Number(editing.id), {
          nombre: values.nombre,
          codigo: values.codigo,
          tipo: values.tipo,
          capacidad: values.capacidad,
        });

        setRows((prev) =>
          prev.map((r) => (r.id === String(updated.id) ? mapAulaToRoom(updated) : r)),
        );

        toast({
          title: 'Aula actualizada',
          description: 'Los cambios se han guardado correctamente.',
        });
      } else {
        const created = await createAula({
          nombre: values.nombre,
          codigo: values.codigo,
          tipo: values.tipo,
          capacidad: values.capacidad,
        });

        setRows((prev) => [...prev, mapAulaToRoom(created)]);

        toast({
          title: 'Aula creada',
          description: 'El aula se ha creado correctamente.',
        });
      }

      setDialogOpen(false);
      setEditing(null);
    } catch (error: unknown) {
      toast({
        variant: 'destructive',
        title: 'Error al guardar',
        description:
          error instanceof Error ? error.message : 'No se ha podido guardar el aula.',
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-6">
          <RoomsTable 
            data={rows} 
            onEdit={openEdit} 
            onDelete={handleDelete} 
            onCreate={openNew}
          />
        </CardContent>
      </Card>

      <RoomFormDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) {
            setEditing(null);
          }
        }}
        initial={editing}
        onSubmit={handleSubmit}
        saving={saving}
      />
    </div>
  );
}
