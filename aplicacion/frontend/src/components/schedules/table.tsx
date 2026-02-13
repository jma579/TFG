'use client';

import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table';
import Link from 'next/link';
import * as React from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

import type { ScheduleRow } from './data';

function StatusBadge({ s }: { s: ScheduleRow['status'] }) {
  if (s === 'ok') return <Badge variant="secondary">OK</Badge>;
  if (s === 'procesando') return <Badge variant="default">Procesando…</Badge>;
  return <Badge variant="destructive">Con conflictos</Badge>;
}

function ConflictsPanel({ row }: { row: ScheduleRow }) {
  if (!row.conflicts.length) return null;
  return (
    <div className="rounded-md border bg-muted/30 p-3">
      <p className="mb-2 text-xs text-muted-foreground">Conflictos detectados:</p>
      <ul className="space-y-2">
        {row.conflicts.map((c: ScheduleRow['conflicts'][number]) => (
          <li key={c.id} className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{c.titulo}</p>
              <p className="text-xs text-muted-foreground">Severidad: {c.severidad}</p>
            </div>
            <Button asChild size="sm">
              <Link href={`/solucionador/${c.id}`}>Abrir</Link>
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SchedulesTable({ data }: { data: ScheduleRow[] }) {
  const [expandedConflictsId, setExpandedConflictsId] = React.useState<string | null>(null);

  const columns = React.useMemo<ColumnDef<ScheduleRow>[]>(() => [
    {
      accessorKey: 'titulacion',
      header: 'Titulación',
      cell: ({ row }) => <span className="font-medium">{row.original.titulacion}</span>,
    },
    {
      accessorKey: 'mencion',
      header: 'Mención',
      cell: ({ row }) => <span className="text-sm text-muted-foreground">{row.original.mencion ?? '—'}</span>,
    },
    {
      accessorKey: 'curso',
      header: () => <div className="text-center">Curso</div>,
      cell: ({ row }) => <div className="text-center">{row.original.curso}</div>,
    },
    {
      accessorKey: 'cuatrimestre',
      header: () => <div className="text-center">Cuatr.</div>,
      cell: ({ row }) => <div className="text-center">{row.original.cuatrimestre}</div>,
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const s = row.original.status;
        const hasConflicts = s === 'con_conflictos' && row.original.conflicts.length > 0;
        const open = expandedConflictsId === row.original.id;
        return (
          <div className="flex items-center justify-between gap-3">
            <StatusBadge s={s} />
            {hasConflicts && (
              <Button
                size="sm"
                variant={open ? 'default' : 'outline'}
                onClick={() => setExpandedConflictsId(open ? null : row.original.id)}
              >
                {open ? 'Ocultar conflictos' : `Ver conflictos (${row.original.conflicts.length})`}
              </Button>
            )}
          </div>
        );
      },
    },
  ], [expandedConflictsId]);

  const table = useReactTable<ScheduleRow>({
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
            const conflictsOpen = expandedConflictsId === row.original.id;

            return (
              <React.Fragment key={row.id}>
                <TableRow>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>

                {conflictsOpen && (
                  <TableRow>
                    <TableCell colSpan={colCount}>
                      <ConflictsPanel row={row.original} />
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
