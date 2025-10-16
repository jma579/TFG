'use client';

import { ColumnDef } from '@tanstack/react-table';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Conflict } from './data';

const severidadToVariant: Record<
  Conflict['severidad'],
  'secondary' | 'default' | 'destructive' | 'outline'
> = {
  baja: 'secondary',
  media: 'default',
  alta: 'destructive',
  crítica: 'destructive',
};

const estadoToVariant: Record<Conflict['estado'], 'secondary' | 'default' | 'outline'> = {
  abierto: 'default',
  'en progreso': 'secondary',
  resuelto: 'outline',
};

export const columns: ColumnDef<Conflict>[] = [
  {
    accessorKey: 'titulo',
    header: 'Título',
    cell: ({ row }) => <span className="font-medium">{row.original.titulo}</span>,
  },
    {
    accessorKey: 'tipo',
    header: () => <div className="text-center">Tipo</div>,
    cell: ({ row }) => (
        <div className="text-center text-sm text-muted-foreground">{row.original.tipo}</div>
    ),
    },
    {
    accessorKey: 'severidad',
    header: () => <div className="text-center">Severidad</div>,
    cell: ({ row }) => (
        <div className="text-center">
        <Badge variant={severidadToVariant[row.original.severidad]}>
            {row.original.severidad}
        </Badge>
        </div>
    ),
    },
    {
    accessorKey: 'estado',
    header: () => <div className="text-center">Estado</div>,
    cell: ({ row }) => (
        <div className="text-center">
        <Badge variant={estadoToVariant[row.original.estado]}>
            {row.original.estado}
        </Badge>
        </div>
    ),
    },
  {
    id: 'accion',
    header: '',
    cell: ({ row }) => (
      <Button asChild size="sm" className="ml-auto">
        <Link href={`/solucionador/${row.original.id}`}>Abrir solucionador</Link>
      </Button>
    ),
    enableSorting: false,
  },
];
