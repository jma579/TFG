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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { SubjectRow } from '@/components/subjects/data';
import {
  getAsignaturaProgramas,
  getAsignaturaProfesores,
  type AsignaturaProgramaAPI,
  type ProfesorAPI,
} from '@/lib/api/client';

// ------- Tipos internos -------

type SubjectDetails = {
  loading: boolean;
  error?: string;
  profesores: SubjectRow['profesores'];
  titulaciones: SubjectRow['titulaciones'];
};

// ------- UI helpers -------

function PeriodBadge({ row }: { row: SubjectRow }) {
  const label =
    row.periodo === 'ANUAL'
      ? 'Anual'
      : row.periodo === 'primer_cuatrimestre'
      ? '1º cuatri'
      : row.periodo === 'segundo_cuatrimestre'
      ? '2º cuatri'
      : row.periodo;

  return (
    <Badge variant="outline" className="font-normal">
      {label}
      {row.num_periodo ? ` · P${row.num_periodo}` : ''}
    </Badge>
  );
}

function ExtractionBadge({ row }: { row: SubjectRow }) {
  if (row.parsing_ok && row.extraction_ok) {
    return <Badge variant="secondary">OK</Badge>;
  }

  if (!row.parsing_ok) {
    return <Badge variant="destructive">Error parsing</Badge>;
  }

  if (!row.extraction_ok) {
    return <Badge variant="outline">Incidencias</Badge>;
  }

  return <Badge variant="outline">Desconocido</Badge>;
}

// ------- Bloque de detalle -------

function DetailBlock({
  row,
  details,
}: {
  row: SubjectRow;
  details?: SubjectDetails;
}) {
  const loading = details?.loading;
  const error = details?.error;

  const profesores =
    details && details.profesores.length > 0
      ? details.profesores
      : row.profesores;

  const titulaciones =
    details && details.titulaciones.length > 0
      ? details.titulaciones
      : row.titulaciones;

  return (
    <div className="rounded-md border bg-muted/30 px-4 py-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs text-muted-foreground">Asignatura</p>
          <p className="text-sm font-medium">{row.nombre}</p>
        </div>
        <div className="flex items-center gap-2">
          <PeriodBadge row={row} />
          <ExtractionBadge row={row} />
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div>
          <p className="text-xs text-muted-foreground">Código plan</p>
          <p className="text-sm font-mono">{row.codigo_plan}</p>
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
          <p className="text-xs text-muted-foreground">Estado</p>
          <p className="text-sm">{row.activo ? 'Activa' : 'Inactiva'}</p>
        </div>
        <div className="md:col-span-3">
          <p className="text-xs text-muted-foreground">Profesores</p>
          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando profesorado…</p>
          ) : error ? (
            <p className="text-sm text-destructive">
              Error al cargar profesorado: {error}
            </p>
          ) : (
            <p className="text-sm">
              {profesores.length
                ? profesores.map((p) => `${p.nombre} ${p.apellidos}`).join(' · ')
                : '—'}
            </p>
          )}
        </div>
        <div className="md:col-span-3">
          <p className="text-xs text-muted-foreground">Titulaciones</p>
          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando titulaciones…</p>
          ) : error ? (
            <p className="text-sm text-destructive">Error al cargar titulaciones.</p>
          ) : titulaciones.length ? (
            <ul className="list-disc pl-4 text-sm">
              {titulaciones.map((t, i) => (
                <li key={i}>
                  {t.titulacion} — {t.tipo_asignatura} — {t.curso}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm">—</p>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span>
          Parsing: {row.parsing_ok ? 'OK' : 'Con errores'} · Extracción:{' '}
          {row.extraction_ok ? 'OK' : 'Incidencias'}
        </span>
      </div>
    </div>
  );
}

// ------- Tabla con expand por fila y acciones -------

export type SubjectsTableProps = {
  data: SubjectRow[];
  onEdit: (row: SubjectRow) => void;
  onDelete: (row: SubjectRow) => void;
};

export function SubjectsTable({ data, onEdit, onDelete }: SubjectsTableProps) {
  const [expandedId, setExpandedId] = React.useState<string | null>(null);
  const [detailsById, setDetailsById] = React.useState<
    Record<string, SubjectDetails>
  >({});

  const loadDetails = React.useCallback(
    async (row: SubjectRow) => {
      const key = row.id;
      const existing = detailsById[key];

      if (
        existing &&
        !existing.error &&
        (existing.profesores.length > 0 || existing.titulaciones.length > 0)
      ) {
        return;
      }

      setDetailsById((prev) => ({
        ...prev,
        [key]: {
          loading: true,
          error: undefined,
          profesores: existing?.profesores ?? [],
          titulaciones: existing?.titulaciones ?? [],
        },
      }));

      try {
        const asignaturaId = Number(row.id);
        const [programas, profesores] = await Promise.all([
          getAsignaturaProgramas(asignaturaId),
          getAsignaturaProfesores(asignaturaId),
        ]);

        const titulaciones = programas.map((p) => ({
          titulacion: p.programa.nombre,
          tipo_asignatura: p.tipo_asignatura ?? '—',
          curso: p.curso != null ? `${p.curso}º` : '—',
        }));

        const teachers = profesores.map((p) => ({
          nombre: p.nombre,
          apellidos: p.apellidos,
        }));

        setDetailsById((prev) => ({
          ...prev,
          [key]: {
            loading: false,
            error: undefined,
            profesores: teachers,
            titulaciones,
          },
        }));
      } catch (error) {
        setDetailsById((prev) => ({
          ...prev,
          [key]: {
            loading: false,
            error:
              error instanceof Error
                ? error.message
                : 'Error al cargar docencia de la asignatura',
            profesores: [],
            titulaciones: [],
          },
        }));
      }
    },
    [detailsById],
  );

  const columns = React.useMemo<ColumnDef<SubjectRow>[]>(
    () => [
      {
        accessorKey: 'codigo_plan',
        header: 'Código',
        cell: ({ row }) => (
          <span className="font-mono text-sm">{row.original.codigo_plan}</span>
        ),
      },
      {
        accessorKey: 'nombre',
        header: 'Asignatura',
        cell: ({ row }) => <span className="font-medium">{row.original.nombre}</span>,
      },
      {
        id: 'periodo',
        header: 'Periodo',
        cell: ({ row }) => <PeriodBadge row={row.original} />,
      },
      {
        accessorKey: 'ects',
        header: 'ECTS',
        cell: ({ row }) => <span>{row.original.ects}</span>,
      },
      {
        accessorKey: 'modalidad',
        header: 'Modalidad',
        cell: ({ row }) => <span>{row.original.modalidad}</span>,
      },
      {
        accessorKey: 'idioma',
        header: 'Idioma',
        cell: ({ row }) => <span>{row.original.idioma}</span>,
      },
      {
        id: 'profesores',
        header: () => <div className="text-center">Profesores</div>,
        cell: ({ row }) => {
          const details = detailsById[row.original.id];
          const count = details?.profesores?.length ?? row.original.profesores.length;
          return <div className="text-center">{count}</div>;
        },
      },
      {
        id: 'titulaciones',
        header: () => <div className="text-center">Titulaciones</div>,
        cell: ({ row }) => {
          const details = detailsById[row.original.id];
          const count = details?.titulaciones?.length ?? row.original.titulaciones.length;
          return <div className="text-center">{count}</div>;
        },
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
            <div className="flex items-center justify-end gap-1">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  const nextId = isOpen ? null : row.original.id;
                  setExpandedId(nextId);
                  if (!isOpen) {
                    void loadDetails(row.original);
                  }
                }}
              >
                {isOpen ? 'Ocultar' : 'Ver detalles'}
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="icon" variant="ghost">
                    <span className="sr-only">Abrir menú</span>
                    ⋯
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>Acciones</DropdownMenuLabel>
                  <DropdownMenuItem onClick={() => onEdit(row.original)}>
                    Editar asignatura
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive"
                    onClick={() => onDelete(row.original)}
                  >
                    Eliminar (soft delete)
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          );
        },
      },
    ],
    [expandedId, detailsById, loadDetails, onEdit, onDelete],
  );

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const rowModel = table.getRowModel();
  const colCount = table.getAllLeafColumns().length;

  return (
    <div className="rounded-md border bg-card">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((hg) => (
            <TableRow key={hg.id}>
              {hg.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>

        <TableBody>
          {rowModel.rows.length === 0 && (
            <TableRow>
              <TableCell
                colSpan={colCount}
                className="py-8 text-center text-sm text-muted-foreground"
              >
                No hay asignaturas registradas.
              </TableCell>
            </TableRow>
          )}

          {rowModel.rows.map((row) => (
            <React.Fragment key={row.id}>
              <TableRow>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>

              {expandedId === row.original.id && (
                <TableRow>
                  <TableCell colSpan={colCount}>
                    <DetailBlock
                      row={row.original}
                      details={detailsById[row.original.id]}
                    />
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}