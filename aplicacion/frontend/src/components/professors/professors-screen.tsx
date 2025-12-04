'use client';

import * as React from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ProfessorsTable } from '@/components/professors/table';
import type { Professor } from '@/components/professors/data';
import { ProfessorFormDialog } from '@/components/professors/professor-form-dialog';
import { useToast } from '@/hooks/use-toast';
import { updateProfesor, createProfessor } from '@/lib/api/client';

type ProfessorsScreenProps = {
  data: Professor[];
};

export function ProfessorsScreen({ data }: ProfessorsScreenProps) {
  const { toast } = useToast();

  const [rows, setRows] = React.useState<Professor[]>(data);
  const [editing, setEditing] = React.useState<Professor | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);

  const handleCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const handleEdit = (row: Professor) => {
    setEditing(row);
    setDialogOpen(true);
  };

  const handleSubmit = async (values: {
    nombre: string;
    apellidos: string;
    email: string;
    departamento: string;
    activo: boolean;
  }) => {
    setSaving(true);

    try {
      if (editing) {
        const updated = await updateProfesor(Number(editing.id), {
          nombre: values.nombre,
          apellidos: values.apellidos,
          email: values.email || null,
          departamento: values.departamento || null,
          activo: values.activo,
        });

        setRows((prev) =>
          prev.map((row) =>
            row.id === String(updated.id)
              ? {
                  id: String(updated.id),
                  nombre: updated.nombre,
                  apellidos: updated.apellidos,
                  email: updated.email ?? null,
                  departamento: updated.departamento ?? null,
                  activo: updated.activo,
                }
              : row,
          ),
        );

        toast({
          title: 'Profesor actualizado',
          description: 'Los cambios se han guardado correctamente.',
        });
      } else {
        const created = await createProfessor({
          nombre: values.nombre,
          apellidos: values.apellidos,
          email: values.email || null,
          departamento: values.departamento || null,
          activo: values.activo,
        });

        setRows((prev) => [
          ...prev,
          {
            id: String(created.id),
            nombre: created.nombre,
            apellidos: created.apellidos,
            email: created.email ?? null,
            departamento: created.departamento ?? null,
            activo: created.activo,
          },
        ]);

        toast({
          title: 'Profesor creado',
          description: 'El profesor se ha añadido correctamente.',
        });
      }

      setDialogOpen(false);
      setEditing(null);
    } catch (error: unknown) {
      toast({
        variant: 'destructive',
        title: editing ? 'Error al actualizar' : 'Error al crear',
        description:
          error instanceof Error
            ? error.message
            : 'Ha ocurrido un error inesperado.',
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <Button onClick={handleCreate}>
          <Plus className="mr-2 h-4 w-4" /> Añadir profesor
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          <ProfessorsTable data={rows} onEdit={handleEdit} />
        </CardContent>
      </Card>

      <ProfessorFormDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) setEditing(null);
        }}
        initial={editing}
        onSubmit={handleSubmit}
        saving={saving}
      />
    </div>
  );
}
