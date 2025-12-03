'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { SubjectsTable } from '@/components/subjects/table';
import type { SubjectRow } from '@/components/subjects/data';
import { SubjectFormDialog } from '@/components/subjects/subject-form-dialog';
import { useToast } from '@/hooks/use-toast';
import { deleteAsignatura, updateAsignatura } from '@/lib/api/client';

type SubjectsScreenProps = {
  data: SubjectRow[];
};

export function SubjectsScreen({ data }: SubjectsScreenProps) {
  const { toast } = useToast();

  const [rows, setRows] = React.useState<SubjectRow[]>(data);
  const [filtersOpen, setFiltersOpen] = React.useState(false);

  const [editing, setEditing] = React.useState<SubjectRow | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);

  const handleEdit = (row: SubjectRow) => {
    setEditing(row);
    setDialogOpen(true);
  };

  const handleDelete = async (row: SubjectRow) => {
    try {
      await deleteAsignatura(Number(row.id));
      setRows((prev) => prev.filter((r) => r.id !== row.id));
      toast({
        title: 'Asignatura eliminada',
        description:
          'La asignatura se ha desactivado correctamente y ya no aparece en el listado.',
      });
    } catch (error: unknown) {
      toast({
        variant: 'destructive',
        title: 'Error al eliminar',
        description:
          error instanceof Error
            ? error.message
            : 'No se ha podido eliminar la asignatura.',
      });
    }
  };

  const handleSubmit = async (values: {
    nombre: string;
    ects: number | null;
    english_friendly: boolean;
    activo: boolean;
  }) => {
    if (!editing) return;
    setSaving(true);

    try {
      const updated = await updateAsignatura(Number(editing.id), {
        nombre: values.nombre,
        ects: values.ects,
        english_friendly: values.english_friendly,
        activo: values.activo,
      });

      setRows((prev) =>
        prev.map((row) =>
          row.id === String(updated.id)
            ? {
                ...row,
                nombre: (updated as { nombre?: string }).nombre ?? row.nombre,
                ects:
                  (updated as { ects?: number | null }).ects ?? row.ects,
                english_friendly:
                  (updated as { english_friendly?: boolean | null })
                    .english_friendly ?? row.english_friendly,
                activo:
                  (updated as { activo?: boolean | null }).activo ?? row.activo,
              }
            : row,
        ),
      );

      toast({
        title: 'Asignatura actualizada',
        description: 'Los cambios se han guardado correctamente.',
      });

      setDialogOpen(false);
      setEditing(null);
    } catch (error: unknown) {
      toast({
        variant: 'destructive',
        title: 'Error al actualizar',
        description:
          error instanceof Error
            ? error.message
            : 'No se ha podido actualizar la asignatura.',
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight">
            Fichas académicas
          </h1>
          <p className="text-sm text-muted-foreground">
            Asignaturas extraídas a partir de las fichas académicas.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setFiltersOpen((prev) => !prev)}
          >
            {filtersOpen ? 'Ocultar filtros' : 'Mostrar filtros'}
          </Button>
        </div>
      </div>

      {filtersOpen && (
        <div className="rounded-md border bg-card p-4">
          <p className="text-sm text-muted-foreground">
            Los filtros avanzados se conectarán más adelante. De momento son
            solo UI.
          </p>
        </div>
      )}

      <SubjectsTable data={rows} onEdit={handleEdit} onDelete={handleDelete} />

      <SubjectFormDialog
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