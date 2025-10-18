'use client';

import * as React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { SchedulesTable } from './table';
import type { ScheduleRow } from './data';

export function SchedulesScreen({ data }: { data: ScheduleRow[] }) {
  const [filtersOpen, setFiltersOpen] = React.useState(false);

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex items-center justify-between gap-3">
        <Button variant="outline" onClick={() => setFiltersOpen((v) => !v)} aria-expanded={filtersOpen}>
          {filtersOpen ? 'Ocultar filtros' : 'Filtros'}
        </Button>
        <Button asChild>
          <Link href="/uploads/horarios">Subir horarios</Link>
        </Button>
      </div>

      {filtersOpen && (
        <div className="rounded-lg border bg-muted/30 p-4">
          <form className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="grid gap-1">
              <label className="text-xs text-muted-foreground">Titulación</label>
              <input className="h-9 rounded-md border bg-background px-2 text-sm" placeholder="Buscar..." />
            </div>
            <div className="grid gap-1">
              <label className="text-xs text-muted-foreground">Mención</label>
              <input className="h-9 rounded-md border bg-background px-2 text-sm" placeholder="— / texto" />
            </div>
            <div className="grid gap-1">
              <label className="text-xs text-muted-foreground">Curso</label>
              <input className="h-9 rounded-md border bg-background px-2 text-sm" placeholder="1º, 2º, 3ºA..." />
            </div>
            <div className="grid gap-1">
              <label className="text-xs text-muted-foreground">Status</label>
              <select className="h-9 rounded-md border bg-background px-2 text-sm">
                <option value="">Todos</option>
                <option value="ok">OK</option>
                <option value="con_conflictos">Con conflictos</option>
                <option value="procesando">Procesando</option>
              </select>
            </div>
          </form>
        </div>
      )}

      <SchedulesTable data={data} />
    </div>
  );
}
