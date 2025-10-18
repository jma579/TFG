'use client';

import * as React from 'react';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { SubjectRow } from './data';

// --- helpers UI ---
function ExtractionBadge({ row }: { row: SubjectRow }) {
  if (!row.parsing_ok) return <Badge variant="destructive">Error de parsing</Badge>;
  if (!row.extraction_ok) return <Badge variant="default">Con incidencias</Badge>;
  return <Badge variant="secondary">OK</Badge>;
}

function DetailBlock({ row }: { row: SubjectRow }) {
  return (
    <div className="rounded-md border bg-muted/30 px-4 py-3">
      <div className="grid gap-3 md:grid-cols-3">
        <div>
          <p className="text-xs text-muted-foreground">Código plan</p>
          <p className="font-mono text-sm">{row.codigo_plan}</p>
        </div>
        <div className="md:col-span-2">
          <p className="text-xs text-muted-foreground">Nombre</p>
          <p className="font-medium">{row.nombre}</p>
        </div>

        <div>
          <p className="text-xs text-muted-foreground">Periodo</p>
          <p className="text-sm">
            {row.periodo}
            {row.num_periodo ? ` · P${row.num_periodo}` : ''}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">ECTS</p>
          <p className="text-sm">{row.ects}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Modalidad</p>
          <p className="text-sm">{row.modalidad}</p>
        </div>

        <div>
          <p className="text-xs text-muted-foreground">Idioma</p>
          <p className="text-sm">{row.idioma}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">English friendly</p>
          <p className="text-sm">{row.english_friendly ? 'Sí' : 'No'}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Activa</p>
          <p className="text-sm">{row.activo ? 'Sí' : 'No'}</p>
        </div>

        <div className="md:col-span-3">
          <p className="text-xs text-muted-foreground">Profesores</p>
          <p className="text-sm">
            {row.profesores.length
              ? row.profesores.map((p) => `${p.nombre} ${p.apellidos}`).join(' · ')
              : '—'}
          </p>
        </div>

        <div className="md:col-span-3">
          <p className="text-xs text-muted-foreground">Titulaciones</p>
          <ul className="text-sm list-disc pl-4">
            {row.titulaciones.map((t, i) => (
              <li key={i}>
                {t.titulacion} — {t.tipo_asignatura} — {t.curso}
              </li>
            ))}
          </ul>
        </div>

        <div className="md:col-span-3">
          <p className="text-xs text-muted-foreground">Estado de extracción</p>
          <div className="mt-1 flex items-center gap-2">
            <ExtractionBadge row={row} />
            {!row.parsing_ok && <span className="text-xs text-muted-foreground">Fallo en parsing</span>}
            {row.parsing_ok && !row.extraction_ok && (
              <span className="text-xs text-muted-foreground">Incidencias detectadas</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Tabla con expand por fila ---
export function SubjectsTable({ data }: { data: SubjectRow[] }) {
  const [expandedId, setExpandedId] = React.useState<string | null>(null);

  const columns = React.useMemo<ColumnDef<SubjectRow>[]>(() => [
    {
      accessorKey: 'codigo_plan',
      header: 'Código',
      cell: ({ row }) => <span className="font-mono text-sm">{row.original.codigo_plan}</span>,
    },
    {
      accessorKey: 'nombre',
      header: 'Asignatura',
      cell: ({ row }) => <span className="font-medium">{row.original.nombre}</span>,
    },
    {
      id: 'periodo',
      header: 'Periodo',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.periodo}
          {row.original.num_periodo ? ` · P${row.original.num_periodo}` : ''}
        </span>
      ),
    },
    {
      accessorKey: 'ects',
      header: () => <div className="text-center">ECTS</div>,
      cell: ({ row }) => <div className="text-center">{row.original.ects}</div>,
    },
    {
      accessorKey: 'modalidad',
      header: 'Modalidad',
      cell: ({ row }) => <span className="text-sm text-muted-foreground">{row.original.modalidad}</span>,
    },
    {
      accessorKey: 'idioma',
      header: 'Idioma',
      cell: ({ row }) => <span className="text-sm text-muted-foreground">{row.original.idioma}</span>,
    },
    {
      id: 'profesores',
      header: () => <div className="text-center">Profesores</div>,
      cell: ({ row }) => <div className="text-center">{row.original.profesores.length}</div>,
    },
    {
      id: 'titulaciones',
      header: () => <div className="text-center">Titulaciones</div>,
      cell: ({ row }) => <div className="text-center">{row.original.titulaciones.length}</div>,
    },
    {
      id: 'extraccion',
      header: 'Extracción',
      cell: ({ row }) => <ExtractionBadge row={row.original} />,
    },
    {
      id: 'acciones',
      header: '',
      enableSorting: false,
      cell: ({ row }) => {
        const isOpen = expandedId === row.original.id;
        return (
          <div className="flex justify-end">
            <Button
              size="sm"
              variant={isOpen ? 'default' : 'outline'}
              onClick={() => setExpandedId(isOpen ? null : row.original.id)}
            >
              {isOpen ? 'Ocultar detalles' : 'Ver detalles'}
            </Button>
          </div>
        );
      },
    },
  ], [expandedId]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const colCount = table.getAllLeafColumns().length;

  return (
    <div className="rounded-md border bg-card">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((hg) => (
            <TableRow key={hg.id}>
              {hg.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>

        <TableBody>
          {table.getRowModel().rows.map((row) => {
            const open = expandedId === row.original.id;
            return (
              <React.Fragment key={row.id}>
                <TableRow>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>

                {open && (
                  <TableRow>
                    <TableCell colSpan={colCount}>
                      <DetailBlock row={row.original} />
                    </TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
