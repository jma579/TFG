'use client';

import { ColumnDef } from '@tanstack/react-table';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ConflictoOut, ConflictoSeveridad, ConflictoTipo } from '@/lib/api/conflictos';
import { 
  AlertCircle, 
  AlertTriangle, 
  Info, 
  ChevronRight, 
  ChevronDown,
  Users,
  Building2,
  GraduationCap,
  Scale,
  LucideIcon 
} from 'lucide-react';

// --- CONFIGURACIÓN VISUAL ---

type SeveridadConfig = {
  label: string;
  variant: "destructive" | "default" | "secondary" | "outline";
  icon: LucideIcon;
  color: string;
};

const severidadConfig: Record<ConflictoSeveridad, SeveridadConfig> = {
  critico: { 
    label: 'Crítico', 
    variant: 'destructive', 
    icon: AlertCircle,
    color: 'text-red-600'
  },
  no_bloqueante: { 
    label: 'No Bloqueante', 
    variant: 'default', 
    icon: AlertTriangle,
    color: 'text-orange-500' 
  },
  leve: { 
    label: 'Leve', 
    variant: 'secondary', 
    icon: Info,
    color: 'text-blue-500'
  },
};

type TipoConfig = {
  label: string;
  icon: LucideIcon;
};

const tipoConfig: Record<ConflictoTipo, TipoConfig> = {
  solapamiento_aula: { label: 'Aula', icon: Building2 },
  solapamiento_profesor: { label: 'Profesor', icon: GraduationCap },
  solapamiento_grupo: { label: 'Grupo', icon: Users },
  interferencia_conciliacion: { label: 'Conciliación', icon: Scale },
};

export const columns: ColumnDef<ConflictoOut>[] = [
  // 1. Columna Expansor
  {
    id: 'expander',
    header: () => null,
    cell: ({ row }) => {
      return (
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 p-0"
          onClick={() => row.toggleExpanded()}
        >
          {row.getIsExpanded() ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </Button>
      );
    },
    enableSorting: false,
    enableHiding: false,
  },
  
  // 2. Columna Severidad (Badge)
  {
    accessorKey: 'severidad',
    header: () => <div className="text-center">Severidad</div>,
    cell: ({ row }) => {
      const config = severidadConfig[row.original.severidad] || severidadConfig.leve;
      const Icon = config.icon;
      
      const badgeStyle = row.original.severidad === 'no_bloqueante' 
        ? "bg-orange-100 text-orange-700 hover:bg-orange-200 border-orange-200 shadow-none"
        : "shadow-none";

      return (
        <div className="flex justify-center">
          <Badge variant={config.variant} className={`gap-1 whitespace-nowrap ${badgeStyle}`}>
            <Icon className="w-3 h-3" />
            {config.label}
          </Badge>
        </div>
      );
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id));
    },
  },

  // 3. Columna Tipo (Icono + Texto)
  {
    accessorKey: 'tipo',
    header: 'Tipo',
    cell: ({ row }) => {
      const tipo = row.original.tipo;
      // Fallback seguro si el tipo no está en el mapa
      const defaultConfig: TipoConfig = { label: tipo, icon: Info };
      const config = tipoConfig[tipo] || defaultConfig;
      const Icon = config.icon;
      
      return (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Icon className="h-4 w-4" />
          <span>{config.label}</span>
        </div>
      );
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id));
    },
  },

  // 4. Columna Descripción
  {
    accessorKey: 'descripcion',
    header: 'Descripción del Conflicto',
    cell: ({ row }) => (
      <div className="flex flex-col max-w-[500px]">
        <span className="font-medium text-sm truncate" title={row.original.descripcion}>
          {row.original.descripcion}
        </span>
      </div>
    ),
  },

  // 5. Columna Acción (Resolver)
  {
    id: 'actions',
    cell: ({ row }) => (
      <div className="text-right">
        <Button asChild size="sm" variant="outline" className="h-8">
          <Link href={`/solucionador/${row.original.sesion_id}`}>
            Resolver
          </Link>
        </Button>
      </div>
    ),
  },
];