'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from '@/components/ui/select';
import { RoomsTable } from './table';
import { RoomFormDialog } from './room-form-dialog';
import type { Room } from './data';
import {
  listAulas,
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
  const [search, setSearch] = React.useState('');
  const [tipoFilter, setTipoFilter] = React.useState<string>('all');
  const [capacidadMin, setCapacidadMin] = React.useState<string>('');

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Room | null>(null);
  const [saving, setSaving] = React.useState(false);

  // Tipos de aula disponibles, derivados de los datos actuales
  const tiposDisponibles = React.useMemo(() => {
    const set = new Set<string>();
    rows.forEach((r) => {
      if (r.tipo) {
        set.add(r.tipo);
      }
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [rows]);

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    const minCap = capacidadMin.trim() ? Number(capacidadMin) : null;

    return rows.filter((r) => {
      if (tipoFilter !== 'all' && r.tipo !== tipoFilter) {
        return false;
      }

      if (minCap !== null && !Number.isNaN(minCap)) {
        if (r.capacidad == null || r.capacidad < minCap) {
          return false;
        }
      }

      if (q) {
        const haystack = `${r.nombre} ${r.codigo} ${r.tipo}`.toLowerCase();
        if (!haystack.includes(q)) {
          return false;
        }
      }

      return true;
    });
  }, [rows, search, tipoFilter, capacidadMin]);

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

  // Opcional: recarga manual desde el backend (por si quieres añadir un botón "Recargar")
  const handleReload = async () => {
    try {
      const resp = await listAulas();
      const mapped = resp.items.map(mapAulaToRoom);
      setRows(mapped);
      toast({ title: 'Aulas actualizadas', description: 'Se han recargado las aulas del servidor.' });
    } catch (error: unknown) {
      toast({
        variant: 'destructive',
        title: 'Error al recargar',
        description:
          error instanceof Error ? error.message : 'No se han podido recargar las aulas.',
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight">Aulas</h1>
          <p className="text-sm text-muted-foreground">
            Gestión de aulas registradas en el sistema.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Input
            placeholder="Buscar por nombre, código o tipo…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-xs"
          />

          <Select
            value={tipoFilter}
            onValueChange={(value) => setTipoFilter(value)}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Tipo de aula" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los tipos</SelectItem>
              {tiposDisponibles.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Input
            type="number"
            min={0}
            placeholder="Capacidad mínima"
            value={capacidadMin}
            onChange={(e) => setCapacidadMin(e.target.value)}
            className="w-36"
          />

          <Button variant="outline" onClick={handleReload}>
            Recargar
          </Button>

          <Button onClick={openNew}>Nueva aula</Button>
        </div>
      </div>

      <RoomsTable data={filtered} onEdit={openEdit} onDelete={handleDelete} />

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