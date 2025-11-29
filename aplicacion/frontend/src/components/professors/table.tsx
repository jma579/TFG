'use client';

import * as React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import type { Professor } from './data';
import { updateProfesor } from '@/lib/api/client';

type EstadoFilter = 'all' | 'active' | 'inactive';

type ProfessorFormState = {
  nombre: string;
  apellidos: string;
  email: string;
  departamento: string;
  activo: boolean;
};

type ProfessorsTableProps = {
  data: Professor[];
};

export function ProfessorsTable({ data }: ProfessorsTableProps) {
  const { toast } = useToast();

  const [rows, setRows] = React.useState<Professor[]>(data);
  const [search, setSearch] = React.useState('');
  const [estadoFilter, setEstadoFilter] = React.useState<EstadoFilter>('all');

  const [editing, setEditing] = React.useState<Professor | null>(null);
  const [form, setForm] = React.useState<ProfessorFormState | null>(null);
  const [saving, setSaving] = React.useState(false);

  const filteredRows = React.useMemo(() => {
    const q = search.trim().toLowerCase();

    return rows.filter((p) => {
      if (estadoFilter === 'active' && !p.activo) return false;
      if (estadoFilter === 'inactive' && p.activo) return false;

      if (q) {
        const haystack = `${p.nombre} ${p.apellidos} ${p.departamento ?? ''}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }

      return true;
    });
  }, [rows, search, estadoFilter]);

  const openEdit = (prof: Professor) => {
    setEditing(prof);
    setForm({
      nombre: prof.nombre,
      apellidos: prof.apellidos,
      email: prof.email ?? '',
      departamento: prof.departamento ?? '',
      activo: prof.activo,
    });
  };

  const closeEdit = () => {
    setEditing(null);
    setForm(null);
    setSaving(false);
  };

  const handleChange = (field: keyof ProfessorFormState, value: string | boolean) => {
    setForm((prev) =>
      prev
        ? {
            ...prev,
            [field]: value,
          }
        : prev,
    );
  };

  const handleSave = async () => {
    if (!editing || !form) return;
    setSaving(true);

    try {
      const updated = await updateProfesor(Number(editing.id), {
        nombre: form.nombre,
        apellidos: form.apellidos,
        email: form.email || null,
        departamento: form.departamento || null,
        activo: form.activo,
      });

      setRows((prev) =>
        prev.map((p) =>
          p.id === String(updated.id)
            ? {
                id: String(updated.id),
                nombre: updated.nombre,
                apellidos: updated.apellidos,
                email: updated.email ?? null,
                departamento: updated.departamento ?? null,
                activo: updated.activo,
              }
            : p,
        ),
      );

      toast({
        title: 'Profesor actualizado',
        description: 'Los cambios se han guardado correctamente.',
      });

      closeEdit();
    } catch (error: unknown) {
      toast({
        variant: 'destructive',
        title: 'Error al actualizar',
        description:
          error instanceof Error
            ? error.message
            : 'No se ha podido actualizar el profesor.',
      });
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Filtros */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight">Profesores</h1>
          <p className="text-sm text-muted-foreground">
            Listado de personal docente registrado en el sistema.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Input
            placeholder="Buscar por nombre o departamento…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-xs"
          />
          <Select
            value={estadoFilter}
            onValueChange={(value) => setEstadoFilter(value as EstadoFilter)}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Estado" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="active">Activos</SelectItem>
              <SelectItem value="inactive">Inactivos</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Tabla */}
      <div className="overflow-hidden rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Departamento</TableHead>
              <TableHead className="w-[120px] text-center">Estado</TableHead>
              <TableHead className="w-[120px] text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-6 text-center text-sm text-muted-foreground">
                  No hay profesores que coincidan con los filtros.
                </TableCell>
              </TableRow>
            ) : (
              filteredRows.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">
                    {p.nombre} {p.apellidos}
                  </TableCell>
                  <TableCell className="text-sm">
                    {p.email ? (
                      <a
                        href={`mailto:${p.email}`}
                        className="text-sm text-primary underline-offset-2 hover:underline"
                      >
                        {p.email}
                      </a>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm">
                    {p.departamento || <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell className="text-center">
                    {p.activo ? (
                      <Badge variant="outline" className="bg-emerald-50 text-emerald-700">
                        Activo
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="bg-slate-100 text-slate-600">
                        Inactivo
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="outline" onClick={() => openEdit(p)}>
                      Editar
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Diálogo de edición */}
      <Dialog
        open={!!editing}
        onOpenChange={(open) => {
          if (!open) {
            closeEdit();
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar profesor</DialogTitle>
            <DialogDescription>
              Actualiza los datos del profesor y guarda los cambios.
            </DialogDescription>
          </DialogHeader>

          {form && editing && (
            <div className="space-y-4 py-2">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground" htmlFor="nombre">
                    Nombre
                  </label>
                  <Input
                    id="nombre"
                    value={form.nombre}
                    onChange={(e) => handleChange('nombre', e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <label
                    className="text-xs font-medium text-muted-foreground"
                    htmlFor="apellidos"
                  >
                    Apellidos
                  </label>
                  <Input
                    id="apellidos"
                    value={form.apellidos}
                    onChange={(e) => handleChange('apellidos', e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground" htmlFor="email">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  placeholder="nombre.apellidos@universidad.es"
                />
              </div>

              <div className="space-y-1">
                <label
                  className="text-xs font-medium text-muted-foreground"
                  htmlFor="departamento"
                >
                  Departamento
                </label>
                <Input
                  id="departamento"
                  value={form.departamento}
                  onChange={(e) => handleChange('departamento', e.target.value)}
                  placeholder="Departamento"
                />
              </div>

              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Estado</span>
                <Select
                  value={form.activo ? 'active' : 'inactive'}
                  onValueChange={(value) => handleChange('activo', value === 'active')}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Activo</SelectItem>
                    <SelectItem value="inactive">Inactivo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={closeEdit} disabled={saving}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={saving || !form}>
              {saving ? 'Guardando…' : 'Guardar cambios'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
