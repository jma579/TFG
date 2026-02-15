'use client';

import * as React from 'react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import type { Professor } from './data';
import { ProfessorRestriccionesTab } from './professor-restricciones-tab';

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
  }>({
    nombre: '',
    apellidos: '',
    email: '',
    departamento: '',
    activo: true,
  });

  React.useEffect(() => {
    if (initial) {
      setForm({
        nombre: initial.nombre,
        apellidos: initial.apellidos,
        email: initial.email ?? '',
        departamento: initial.departamento ?? '',
        activo: initial.activo,
      });
    } else {
      setForm({
        nombre: '',
        apellidos: '',
        email: '',
        departamento: '',
        activo: true,
      });
    }
  }, [initial, open]);

  const handleChange = (field: string, value: string | boolean | null) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const basicForm = (
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
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{initial ? 'Gestionar Profesor' : 'Nuevo profesor'}</DialogTitle>
        </DialogHeader>

        {initial ? (
          <Tabs defaultValue="basic" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="basic">Datos Basicos</TabsTrigger>
              <TabsTrigger value="restricciones">Restricciones Horarias</TabsTrigger>
            </TabsList>

            <TabsContent value="basic" className="space-y-4 py-4">
              {basicForm}
            </TabsContent>

            <TabsContent value="restricciones">
              <ProfessorRestriccionesTab profesorId={initial.id} />
            </TabsContent>
          </Tabs>
        ) : (
          <div className="space-y-4 py-4">
            {basicForm}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cerrar
          </Button>
          <Button onClick={() => onSubmit(form)} disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar Datos'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}