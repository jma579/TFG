'use client';

import * as React from 'react';
import { useCallback } from 'react'; // 1. Importamos useCallback
import { Card, CardContent } from '@/components/ui/card';
import { SubjectsTable } from '@/components/subjects/table';
import type { SubjectRow } from '@/components/subjects/data';
import { SubjectFormDialog } from '@/components/subjects/subject-form-dialog';
import { useToast } from '@/hooks/use-toast';
import { deleteAsignatura, updateAsignatura } from '@/lib/api/catalogo/asignaturas';
import { listProgramas, type ProgramaOut } from '@/lib/api/catalogo/programas';

type SubjectsScreenProps = {
  data: SubjectRow[];
};

export function SubjectsScreen({ data }: SubjectsScreenProps) {
  const { toast } = useToast();

  const [rows, setRows] = React.useState<SubjectRow[]>(data);
  const [programas, setProgramas] = React.useState<ProgramaOut[]>([]);

  const [editing, setEditing] = React.useState<SubjectRow | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    listProgramas(1, 1000, true)
      .then((res) => {
        if (res && res.items) {
          setProgramas(res.items);
        }
      })
      .catch((err) => console.error('Error cargando programas', err));
  }, []);

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

  // 2. Envolvemos la función con useCallback para estabilizarla
  const handleDataUpdate = useCallback((
    id: string, 
    data: { 
      profesores: { nombre: string; apellidos: string }[]; 
      titulaciones: { titulacion: string; tipo_asignatura: string; curso: string }[] 
    }
  ) => {
    setRows((prev) =>
      prev.map((row) =>
        row.id === id
          ? { ...row, profesores: data.profesores, titulaciones: data.titulaciones }
          : row
      )
    );
  }, []); // Array de dependencias vacío porque setRows es estable

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
      <Card>
        <CardContent className="pt-6">
           <SubjectsTable 
             data={rows} 
             onEdit={handleEdit} 
             onDelete={handleDelete} 
             onDataUpdate={handleDataUpdate}
             titulacionesDisponibles={programas}
           />
        </CardContent>
      </Card>

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