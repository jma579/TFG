'use client';

import { ColumnDef } from '@tanstack/react-table';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ConflictoOut, ConflictoSeveridad, ConflictoEstado } from '@/lib/api/conflictos';

// Mapeo visual para Severidad
const severidadToVariant: Record<
  ConflictoSeveridad,
  'secondary' | 'default' | 'destructive' | 'outline'
> = {
  INFO: 'secondary',
  WARNING: 'default',
  ERROR: 'destructive',
  CRITICA: 'destructive',
};

// Mapeo visual para Estado
const estadoToVariant: Record<ConflictoEstado, 'secondary' | 'default' | 'outline'> = {
  ABIERTO: 'default',
  IGNORADO: 'secondary',
  RESUELTO: 'outline',
};

// Helper para formatear el tipo de conflicto (ENUM -> Texto legible)
const formatTipo = (tipo: string) => {
  return tipo
    .replace('SOLAPAMIENTO_', 'Solape ')
    .replace('VIOLACION_', 'Violación ')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase());
};

export const columns: ColumnDef<ConflictoOut>[] = [
  {
    accessorKey: 'descripcion',
    header: 'Descripción',
    cell: ({ row }) => (
      <div className="flex flex-col">
        <span className="font-medium truncate max-w-[400px]" title={row.original.descripcion}>
          {row.original.descripcion}
        </span>
        <span className="text-xs text-muted-foreground">
           Detectado: {row.original.creado_en ? new Date(row.original.creado_en).toLocaleDateString() : '-'}
        </span>
      </div>
    ),
  },
  {
    accessorKey: 'tipo',
    header: () => <div className="text-center">Tipo</div>,
    cell: ({ row }) => (
      <div className="text-center text-sm text-muted-foreground">
        {formatTipo(row.original.tipo)}
      </div>
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
      <Button asChild size="sm" variant="ghost" className="ml-auto">
        <Link href={`/solucionador/${row.original.sesion_id}`}>
          Resolver
        </Link>
      </Button>
    ),
    enableSorting: false,
  },
];