'use client';

import * as React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { SubjectsTable } from '@/components/subjects/table';
import type { SubjectRow } from '@/components/subjects/data';

type Props = { data: SubjectRow[] };

export function SubjectsScreen({ data }: Props) {
  const [filtersOpen, setFiltersOpen] = React.useState(false);

  // Nota: por ahora los filtros son solo UI (no filtran los datos).
  // Cuando toque conectar, almacenamos estado y filtramos `data`.
  return (
    <div className="mx-auto max-w-6xl space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3">
        <Button
          variant="outline"
          onClick={() => setFiltersOpen((v) => !v)}
          aria-expanded={filtersOpen}
        >
          {filtersOpen ? 'Ocultar filtros' : 'Filtros'}
        </Button>

        <Button asChild>
          <Link href="/uploads/fichas">Subir fichas</Link>
        </Button>
      </div>

      {/* Panel de filtros (UI) */}
      {filtersOpen && (
        <div className="rounded-lg border bg-muted/30 p-4">
          <form className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="grid gap-1">
              <label htmlFor="periodo" className="text-xs text-muted-foreground">
                Periodo
              </label>
              <select id="periodo" className="h-9 rounded-md border bg-background px-2 text-sm">
                <option value="">Todos</option>
                <option value="ANUAL">Anual</option>
                <option value="SEMESTRAL">Semestral</option>
              </select>
            </div>

            <div className="grid gap-1">
              <label htmlFor="idioma" className="text-xs text-muted-foreground">
                Idioma
              </label>
              <select id="idioma" className="h-9 rounded-md border bg-background px-2 text-sm">
                <option value="">Todos</option>
                <option value="ESPAÑOL">Español</option>
                <option value="INGLÉS">Inglés</option>
              </select>
            </div>

            <div className="grid gap-1">
              <label htmlFor="extraccion" className="text-xs text-muted-foreground">
                Extracción
              </label>
              <select id="extraccion" className="h-9 rounded-md border bg-background px-2 text-sm">
                <option value="">Todas</option>
                <option value="ok">OK</option>
                <option value="incidencias">Con incidencias</option>
                <option value="parsing-error">Error de parsing</option>
              </select>
            </div>

            <div className="grid gap-1">
              <label htmlFor="activa" className="text-xs text-muted-foreground">
                Activa
              </label>
              <select id="activa" className="h-9 rounded-md border bg-background px-2 text-sm">
                <option value="">Todas</option>
                <option value="si">Sí</option>
                <option value="no">No</option>
              </select>
            </div>
          </form>
          {/* Cuando implementemos filtro real: botones Aplicar/Reset aquí */}
        </div>
      )}

      {/* Tabla */}
      <SubjectsTable data={data} />
    </div>
  );
}
