'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { Professor, TipoConciliacion } from './data';

type ProfessorFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial: Professor | null;
  onSubmit: (values: {
    nombre: string;
    apellidos: string;
    email: string;
    departamento: string;
    activo: boolean;
    conciliacion: TipoConciliacion; // <--- Nuevo campo
  }) => void;
  saving: boolean;
};

export function ProfessorFormDialog({
  open,
  onOpenChange,
  initial,
  onSubmit,
  saving,
}: ProfessorFormDialogProps) {
  const [form, setForm] = React.useState<{
    nombre: string;
    apellidos: string;
    email: string;
    departamento: string;
    activo: boolean;
    conciliacion: TipoConciliacion;
  }>({
    nombre: '',
    apellidos: '',
    email: '',
    departamento: '',
    activo: true,
    conciliacion: null,
  });

  React.useEffect(() => {
    if (initial) {
      setForm({
        nombre: initial.nombre,
        apellidos: initial.apellidos,
        email: initial.email ?? '',
        departamento: initial.departamento ?? '',
        activo: initial.activo,
        conciliacion: initial.conciliacion, // <--- Carga valor inicial
      });
    } else {
      setForm({
        nombre: '',
        apellidos: '',
        email: '',
        departamento: '',
        activo: true,
        conciliacion: null,
      });
    }
  }, [initial, open]);

  const handleChange = (field: string, value: string | boolean | null) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial ? 'Editar profesor' : 'Nuevo profesor'}</DialogTitle>
          <DialogDescription>
            {initial
              ? 'Actualiza los datos y preferencias del profesor.'
              : 'Introduce los datos del nuevo profesor.'}
          </DialogDescription>
        </DialogHeader>

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

          <div className="grid gap-3 md:grid-cols-2">
            {/* SELECTOR DE CONCILIACIÓN */}
            <div className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Conciliación</span>
              <Select
                value={form.conciliacion ?? 'none'} 
                onValueChange={(value) => handleChange('conciliacion', value === 'none' ? null : value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sin preferencia" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Ninguna</SelectItem>
                  <SelectItem value="entrada_tardia">Entrada Tardía (+2h)</SelectItem>
                  <SelectItem value="salida_temprana">Salida Temprana (-2h)</SelectItem>
                  <SelectItem value="mixta">Mixta (±1h)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">Estado</span>
              <Select
                value={form.activo ? 'active' : 'inactive'}
                onValueChange={(value) => handleChange('activo', value === 'active')}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Activo</SelectItem>
                  <SelectItem value="inactive">Inactivo</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={() => onSubmit(form)} disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar cambios'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}