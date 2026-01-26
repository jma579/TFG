'use client';

import * as React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { ProfessorsTable } from '@/components/professors/table';
import type { Professor, TipoConciliacion } from '@/components/professors/data';
import { ProfessorFormDialog } from '@/components/professors/professor-form-dialog';
import { useToast } from '@/hooks/use-toast';
import { updateProfesor } from '@/lib/api/recursos/profesores'; 

type ProfessorsScreenProps = {
  data: Professor[];
};

export function ProfessorsScreen({ data }: ProfessorsScreenProps) {
  const { toast } = useToast();

  const [rows, setRows] = React.useState<Professor[]>(data);
  const [editing, setEditing] = React.useState<Professor | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);

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
    conciliacion: TipoConciliacion; // <--- Incluimos en submit
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
        conciliacion: values.conciliacion, // <--- Envíamos a API
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
                conciliacion: updated.conciliacion ?? null, // <--- Actualizamos vista local
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