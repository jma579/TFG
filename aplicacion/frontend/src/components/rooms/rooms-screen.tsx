'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RoomsTable } from './table';
import { RoomFormDialog } from './room-form-dialog';
import { roomsMock, locationsMock, type Room } from './data';
import { uid } from '@/lib/id';

export function RoomsScreen() {
  const [rows, setRows] = React.useState<Room[]>(roomsMock);
  const [filtersOpen, setFiltersOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const [locationFilter, setLocationFilter] = React.useState<string>('');

  // diálogo crear/editar
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Room | null>(null);

  const filtered = rows.filter((r) => {
    const byText =
      !search ||
      r.nombre.toLowerCase().includes(search.toLowerCase()) ||
      r.ubicacion.toLowerCase().includes(search.toLowerCase());
    const byLoc = !locationFilter || r.ubicacion === locationFilter;
    return byText && byLoc;
  });

  const openCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = (room: Room) => {
    setEditing(room);
    setDialogOpen(true);
  };

  const handleSubmit = (data: Omit<Room, 'id'>, editingId?: string) => {
    if (editingId) {
      setRows((prev) => prev.map((r) => (r.id === editingId ? { ...r, ...data } : r)));
    } else {
      setRows((prev) => [{ id: uid('room'), ...data }, ...prev]);
    }
  };

  const handleDelete = (id: string) => {
    setRows((prev) => prev.filter((r) => r.id !== id));
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3">
        <Button variant="outline" onClick={() => setFiltersOpen((v) => !v)} aria-expanded={filtersOpen}>
          {filtersOpen ? 'Ocultar filtros' : 'Filtros'}
        </Button>
        <Button onClick={openCreate}>Añadir aula</Button>
      </div>

      {/* Panel de filtros */}
      {filtersOpen && (
        <div className="rounded-lg border bg-muted/30 p-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="grid gap-1">
              <label className="text-xs text-muted-foreground">Buscar</label>
              <Input placeholder="Nombre o ubicación…" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <label className="text-xs text-muted-foreground">Ubicación</label>
              <select
                className="h-9 rounded-md border bg-background px-2 text-sm"
                value={locationFilter}
                onChange={(e) => setLocationFilter(e.target.value)}
              >
                <option value="">Todas</option>
                {locationsMock.map((loc) => (
                  <option key={loc} value={loc}>
                    {loc}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid items-end">
              <Button variant="outline" onClick={() => { setSearch(''); setLocationFilter(''); }}>
                Limpiar filtros
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Tabla */}
      <RoomsTable data={filtered} onEdit={openEdit} onDelete={handleDelete} />

      {/* Diálogo crear/editar */}
      <RoomFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmit={handleSubmit}
        locations={locationsMock}
        initial={editing}
      />
    </div>
  );
}
