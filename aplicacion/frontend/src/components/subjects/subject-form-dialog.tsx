'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import type { SubjectRow } from '@/components/subjects/data';

export type SubjectFormValues = {
  nombre: string;
  ects: string; // se parsea a número al enviar
  english_friendly: boolean;
  activo: boolean;
};

export type SubjectFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial: SubjectRow | null;
  onSubmit: (values: {
    nombre: string;
    ects: number | null;
    english_friendly: boolean;
    activo: boolean;
  }) => Promise<void> | void;
  saving: boolean;
};

export function SubjectFormDialog({
  open,
  onOpenChange,
  initial,
  onSubmit,
  saving,
}: SubjectFormDialogProps) {
  const [form, setForm] = React.useState<SubjectFormValues>({
    nombre: '',
    ects: '',
    english_friendly: false,
    activo: true,
  });

  React.useEffect(() => {
    if (initial) {
      setForm({
        nombre: initial.nombre,
        ects:
          initial.ects != null && !Number.isNaN(initial.ects)
            ? String(initial.ects)
            : '',
        english_friendly: initial.english_friendly,
        activo: initial.activo,
      });
    } else {
      setForm({ nombre: '', ects: '', english_friendly: false, activo: true });
    }
  }, [initial, open]);

  const handleChange = <K extends keyof SubjectFormValues>(
    key: K,
    value: SubjectFormValues[K],
  ) => {
    setForm((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedEcts = form.ects.trim();
    const ectsNumber = trimmedEcts ? Number(trimmedEcts) : null;

    await onSubmit({
      nombre: form.nombre.trim(),
      ects: Number.isNaN(ectsNumber) ? null : ectsNumber,
      english_friendly: form.english_friendly,
      activo: form.activo,
    });
  };

  const isEdit = !!initial;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Editar asignatura' : 'Editar asignatura'}</DialogTitle>
          <DialogDescription>
            Modifica los campos básicos de la asignatura y guarda los cambios.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          {initial && (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="codigo_plan">Código plan</Label>
                <Input
                  id="codigo_plan"
                  value={initial.codigo_plan}
                  readOnly
                  className="bg-muted/50"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="periodo">Periodo</Label>
                <Input
                  id="periodo"
                  value={initial.periodo}
                  readOnly
                  className="bg-muted/50"
                />
              </div>
            </div>
          )}

          <div className="space-y-1">
            <Label htmlFor="nombre">Nombre</Label>
            <Input
              id="nombre"
              value={form.nombre}
              onChange={(e) => handleChange('nombre', e.target.value)}
              required
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="ects">ECTS</Label>
            <Input
              id="ects"
              type="number"
              min={1}
              max={60}
              value={form.ects}
              onChange={(e) => handleChange('ects', e.target.value)}
              placeholder="Créditos ECTS"
            />
          </div>

          <div className="flex flex-col gap-4 md:flex-row">
            <div className="flex items-center gap-2">
              <input
                id="english_friendly"
                type="checkbox"
                checked={form.english_friendly}
                onChange={(e) => handleChange('english_friendly', e.target.checked)}
                className="h-4 w-4 rounded border"
              />
              <div className="space-y-0.5">
                <Label htmlFor="english_friendly">English friendly</Label>
                <p className="text-xs text-muted-foreground">
                  Indica si la asignatura es amigable para estudiantes extranjeros.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                id="activo"
                type="checkbox"
                checked={form.activo}
                onChange={(e) => handleChange('activo', e.target.checked)}
                className="h-4 w-4 rounded border"
              />
              <div className="space-y-0.5">
                <Label htmlFor="activo">Activa</Label>
                <p className="text-xs text-muted-foreground">
                  Si se desactiva, dejará de aparecer en listados por defecto.
                </p>
              </div>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={saving}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Guardando…' : 'Guardar cambios'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}