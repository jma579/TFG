'use client';

import * as React from 'react';
import { useCallback } from 'react';
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
    listProgramas({ limit: 1000, activo: true })
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

  const handleToggleActive = async (row: SubjectRow) => {
    try {
      const nuevoEstado = !row.activo;
      // Solo enviamos el campo activo
      await updateAsignatura(Number(row.id), { activo: nuevoEstado });

      // Actualización optimista del estado local
      setRows((prev) =>
        prev.map((r) =>
          r.id === row.id ? { ...r, activo: nuevoEstado } : r
        )
      );

      toast({
        title: nuevoEstado ? 'Asignatura activada' : 'Asignatura desactivada',
        description: `La asignatura ${row.codigo_plan} ahora está ${nuevoEstado ? 'activa' : 'inactiva'}.`,
      });
    } catch (error: unknown) {
      toast({
        variant: 'destructive',
        title: 'Error al cambiar estado',
        description: error instanceof Error ? error.message : 'No se pudo actualizar la asignatura.',
      });
    }
  };

  const handleDelete = async (row: SubjectRow) => {
    if (!confirm('¿Estás seguro? Esta acción eliminará la asignatura permanentemente de la base de datos.')) return;

    try {
      await deleteAsignatura(Number(row.id), true); // true = physical delete
      setRows((prev) => prev.filter((r) => r.id !== row.id));
      toast({
        title: 'Asignatura eliminada',
        description: 'El registro se ha eliminado físicamente.',
      });
    } catch (error: unknown) {
      toast({
        variant: 'destructive',
        title: 'No se puede eliminar',
        description: error instanceof Error ? error.message : 'Error al eliminar la asignatura.',
      });
    }
  };

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
  }, []);

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
             onToggleActive={handleToggleActive} 
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