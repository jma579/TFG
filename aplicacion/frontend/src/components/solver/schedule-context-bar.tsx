'use client';

import * as React from 'react';
import { cn } from '@/lib/cn';

export type CourseRef = {
  id: string;
  label: string; // p.ej. "Grado en Matemáticas · 3ºA"
};

type Props = {
  title?: string;                     // por si quieres cambiar "Horario interactivo"
  courses: CourseRef[];               // 1 o 2 cursos implicados
  value?: string;                     // id seleccionado (opcional: controlado desde fuera)
  defaultValue?: string;              // id por defecto (si no es controlado)
  onChange?: (id: string) => void;    // callback al cambiar pestaña
};

export function ScheduleContextBar({
  title = 'Horario interactivo',
  courses,
  value,
  defaultValue,
  onChange,
}: Props) {
  const isControlled = value !== undefined;
  const [internal, setInternal] = React.useState(defaultValue ?? courses[0]?.id);
  const selected = isControlled ? value : internal;

  const select = (id: string) => {
    if (!isControlled) setInternal(id);
    onChange?.(id);
  };

  return (
    <div className="rounded-lg border bg-muted/40 px-3 py-2 md:px-4 md:py-3">
      <div className="flex items-center justify-between gap-3">
        {/* Izquierda: título */}
        <div className="text-sm font-medium tracking-wide text-foreground">
          {title}
        </div>

        {/* Derecha: “pestañas” de curso/titulación */}
        <div className="flex items-center gap-2">
          {courses.map((c) => {
            const active = c.id === selected;
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => select(c.id)}
                className={cn(
                  'whitespace-nowrap rounded-full border px-3 py-1.5 text-xs transition',
                  active
                    ? 'bg-background text-foreground shadow-sm'
                    : 'bg-transparent text-muted-foreground hover:bg-muted'
                )}
                aria-pressed={active}
              >
                {c.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
