'use client';

import * as React from 'react';

import type { Professor } from '@/components/professors/data';
import { ProfessorFormDialog } from '@/components/professors/professor-form-dialog';
import { ProfessorsTable } from '@/components/professors/table';
import { Card, CardContent } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { listProfesores, updateProfesor } from '@/lib/api/recursos/profesores'; 

const PROFESSORS_LIMIT = 1000;

type ProfessorsScreenProps = {
  data: Professor[];
};

export function ProfessorsScreen({ data }: ProfessorsScreenProps) {
  const { toast } = useToast();

  const [rows, setRows] = React.useState<Professor[]>(data);
  const [editing, setEditing] = React.useState<Professor | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);

  const refreshRows = async () => {
    try {
      const resp = await listProfesores({ limit: PROFESSORS_LIMIT });
      const nextRows = resp.items.map((p) => ({
        id: String(p.id),
        nombre: p.nombre,
        apellidos: p.apellidos,
        email: p.email ?? null,
        departamento: p.departamento ?? null,
        activo: p.activo,
      }));

      nextRows.sort((a, b) => {
        const nameA = `${a.nombre} ${a.apellidos}`.toLowerCase();
        const nameB = `${b.nombre} ${b.apellidos}`.toLowerCase();
        return nameA.localeCompare(nameB);
      });

      setRows(nextRows);
    } catch (error: unknown) {
      toast({
        variant: 'destructive',
        title: 'Error al refrescar',
        description:
          error instanceof Error
            ? error.message
            : 'No se pudieron recargar los profesores.',
      });
    }
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
    if (!editing) return;
    
    setSaving(true);

    try {
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
                total_restricciones: row.total_restricciones,
              }
            : row,
        ),
      );

      toast({
        title: 'Profesor actualizado',
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
            : 'Ha ocurrido un error inesperado.',
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-6">
          <ProfessorsTable 
            data={rows} 
            onEdit={handleEdit}
            onRefresh={refreshRows}
          />
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