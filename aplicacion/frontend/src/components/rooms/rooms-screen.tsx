'use client';

import * as React from 'react';

import { Card, CardContent } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import {
  type AulaOut,
  deleteAula,
  updateAula, 
} from '@/lib/api/recursos/aulas';

import type { Room } from './data';
import { RoomFormDialog } from './room-form-dialog';
import { RoomsTable } from './table';

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
    activo: aula.activo, 
  };
}

function mapRoomToAulaOut(room: Room): AulaOut {
  return {
    id: Number(room.id),
    nombre: room.nombre,
    codigo: room.codigo,
    tipo: room.tipo,
    capacidad: room.capacidad,
    activo: room.activo, 
  };
}

export function RoomsScreen({ initialData }: RoomsScreenProps) {
  const { toast } = useToast();

  const [rows, setRows] = React.useState<Room[]>(initialData);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Room | null>(null);

  const openNew = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = (room: Room) => {
    setEditing(room);
    setDialogOpen(true);
  };

  const handleToggleActive = async (room: Room) => {
    try {
      const nuevoEstado = !room.activo;
      const result = await updateAula(Number(room.id), { activo: nuevoEstado });
      
      handleSuccess(result);
      
      toast({
        title: nuevoEstado ? 'Aula activada' : 'Aula desactivada',
        description: `El aula ${room.codigo} ahora está ${nuevoEstado ? 'activa' : 'inactiva'}.`,
      });
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'No se pudo cambiar el estado.';
      toast({
        variant: 'destructive',
        title: 'Error al actualizar',
        description: msg,
      });
    }
  };

  const handleDelete = async (room: Room) => {
    if (!confirm('¿Estás seguro? Esta acción eliminará el aula permanentemente de la base de datos.')) return;

    try {
      await deleteAula(Number(room.id), true); 
      setRows((prev) => prev.filter((r) => r.id !== room.id));
      toast({
        title: 'Aula eliminada',
        description: 'El registro se ha eliminado físicamente.',
      });
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Error desconocido';
      toast({
        variant: 'destructive',
        title: 'No se puede eliminar',
        description: msg,
      });
    }
  };

  const handleSuccess = (aula: AulaOut) => {
    const newRoom = mapAulaToRoom(aula);
    setRows((prev) => {
      const exists = prev.some((r) => r.id === newRoom.id);
      if (exists) {
        return prev.map((r) => (r.id === newRoom.id ? newRoom : r));
      }
      return [...prev, newRoom];
    });
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-6">
          <RoomsTable 
            data={rows} 
            onEdit={openEdit} 
            onDelete={handleDelete} 
            onToggleActive={handleToggleActive}
            onCreate={openNew}
          />
        </CardContent>
      </Card>

      <RoomFormDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) setEditing(null);
        }}
        initialData={editing ? mapRoomToAulaOut(editing) : null}
        onSuccess={handleSuccess}
      />
    </div>
  );
}