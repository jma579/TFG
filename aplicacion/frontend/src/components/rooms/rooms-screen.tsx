'use client';

import * as React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { RoomsTable } from './table';
import { RoomFormDialog } from './room-form-dialog';
import type { Room } from './data';
import {
  deleteAula,
  type AulaOut,
} from '@/lib/api/recursos/aulas';
import { useToast } from '@/hooks/use-toast';

export type RoomsScreenProps = {
  initialData: Room[];
};

// Convierte de API (AulaOut) a Vista (Room)
function mapAulaToRoom(aula: AulaOut): Room {
  return {
    id: String(aula.id),
    nombre: aula.nombre,
    codigo: aula.codigo,
    tipo: aula.tipo,
    capacidad: aula.capacidad ?? null,
  };
}

// Convierte de Vista (Room) a API (AulaOut) para pasar al formulario
function mapRoomToAulaOut(room: Room): AulaOut {
  return {
    id: Number(room.id),
    nombre: room.nombre,
    codigo: room.codigo,
    tipo: room.tipo,
    capacidad: room.capacidad
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

  // ✅ NUEVO: Manejador de éxito que actualiza la tabla
  const handleSuccess = (aula: AulaOut) => {
    const newRoom = mapAulaToRoom(aula);
    
    setRows((prev) => {
      // Comprobamos si ya existe (edición) o es nueva (creación)
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
        initialData={editing ? mapRoomToAulaOut(editing) : null}
        onSuccess={handleSuccess}
      />
    </div>
  );
}