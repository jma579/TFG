'use client';

import { ColumnDef } from '@tanstack/react-table';
import { 
  AlertCircle, 
  AlertTriangle, 
  Building2, 
  ChevronDown,
  ChevronRight, 
  ExternalLink, 
  GraduationCap, 
  Info, 
  LucideIcon, 
  Scale, 
  Users} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ConflictoOut, ConflictoSeveridad, ConflictoTipo } from '@/lib/api/conflictos';

// ============================================================================
// CONFIGURACIÓN VISUAL
// ============================================================================

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

// ============================================================================
// COMPONENTE DE ACCIÓN INTELIGENTE (RESOLVER)
// ============================================================================

const ResolverActionCell = ({ conflicto }: { conflicto: ConflictoOut }) => {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);

  const s1 = conflicto.sesion_1_detalle;
  const s2 = conflicto.sesion_2_detalle;

  const getUrl = (progId?: number | null, curso?: number | null, periodoCode?: string | null) => {
    if (!progId || !curso) return '#';
    const params = new URLSearchParams();
    params.set('programa_id', String(progId));
    params.set('curso', String(curso));
    params.set('periodo', periodoCode || 'primer_cuatrimestre');
    return `/datos/horarios/detalle?${params.toString()}`;
  };

  if (!s2) {
    return (
      <Button asChild size="sm" variant="outline" className="h-8">
        <Link href={getUrl(s1?.programa_id, s1?.curso_num, s1?.periodo_code)}>
          Resolver
        </Link>
      </Button>
    );
  }

  const ctx1 = { pid: s1?.programa_id, curso: s1?.curso_num, periodo: s1?.periodo_code };
  const ctx2 = { pid: s2?.programa_id, curso: s2?.curso_num, periodo: s2?.periodo_code };

  const isSameContext = 
    ctx1.pid === ctx2.pid && 
    ctx1.curso === ctx2.curso && 
    ctx1.periodo === ctx2.periodo;

  if (isSameContext) {
    return (
      <Button asChild size="sm" variant="outline" className="h-8">
        <Link href={getUrl(s1?.programa_id, s1?.curso_num, s1?.periodo_code)}>
          Resolver
        </Link>
      </Button>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" className="h-8">
          Resolver...
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px] gap-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {/* Icono neutro */}
            <Scale className="h-5 w-5 text-muted-foreground" />
            Conflicto entre Horarios Diferentes
          </DialogTitle>
          <DialogDescription className="text-base">
            Este conflicto afecta a dos planificaciones distintas. Selecciona el horario al que deseas ir.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="group relative flex flex-col gap-3 rounded-xl border p-4 transition-all hover:bg-muted/50 hover:shadow-md cursor-pointer" onClick={() => {
              setIsOpen(false);
              router.push(getUrl(s1?.programa_id, s1?.curso_num, s1?.periodo_code));
          }}>
            <div className="flex items-center justify-between">
               <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">Sesión A</Badge>
            </div>
            <div className="space-y-1">
              <p className="font-semibold text-sm leading-tight">{s1?.asignatura}</p>
              <p className="text-xs text-muted-foreground">{s1?.titulacion} • {s1?.curso}</p>
              <p className="text-xs text-muted-foreground font-medium">{s1?.periodo}</p>
            </div>
            <Button className="w-full mt-2" variant="secondary" size="sm">
              Ir al Horario A <ExternalLink className="ml-2 h-3 w-3" />
            </Button>
          </div>

          <div className="group relative flex flex-col gap-3 rounded-xl border p-4 transition-all hover:bg-muted/50 hover:shadow-md cursor-pointer" onClick={() => {
              setIsOpen(false);
              router.push(getUrl(s2?.programa_id, s2?.curso_num, s2?.periodo_code));
          }}>
             <div className="flex items-center justify-between">
               <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">Sesión B</Badge>
             </div>
            <div className="space-y-1">
              <p className="font-semibold text-sm leading-tight">{s2?.asignatura}</p>
              <p className="text-xs text-muted-foreground">{s2?.titulacion} • {s2?.curso}</p>
              <p className="text-xs text-muted-foreground font-medium">{s2?.periodo}</p>
            </div>
             <Button className="w-full mt-2" variant="secondary" size="sm">
              Ir al Horario B <ExternalLink className="ml-2 h-3 w-3" />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ============================================================================
// DEFINICIÓN DE COLUMNAS
// ============================================================================

export const columns: ColumnDef<ConflictoOut>[] = [
  {
    id: 'expander',
    header: () => null,
    cell: ({ row }) => (
      <Button variant="ghost" size="icon" className="h-6 w-6 p-0 hover:bg-muted" onClick={() => row.toggleExpanded()}>
        {row.getIsExpanded() ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
      </Button>
    ),
  },
  
  {
    accessorKey: 'severidad',
    header: () => <div className="text-center">Severidad</div>,
    cell: ({ row }) => {
      const config = severidadConfig[row.original.severidad] || severidadConfig.leve;
      const Icon = config.icon;
      const badgeStyle = row.original.severidad === 'no_bloqueante' 
        ? "bg-orange-100 text-orange-700 hover:bg-orange-200 border-orange-200 shadow-none"
        : "shadow-none";
      return <div className="flex justify-center"><Badge variant={config.variant} className={`gap-1 whitespace-nowrap ${badgeStyle}`}><Icon className="w-3 h-3" />{config.label}</Badge></div>;
    },
    filterFn: (row, id, value) => value.includes(row.getValue(id)),
  },

  {
    accessorKey: 'tipo',
    header: 'Tipo',
    cell: ({ row }) => {
      const tipo = row.original.tipo;
      const config = tipoConfig[tipo] || { label: tipo, icon: Info };
      const Icon = config.icon;
      return <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium"><Icon className="h-4 w-4 text-slate-500" /><span>{config.label}</span></div>;
    },
    filterFn: (row, id, value) => value.includes(row.getValue(id)),
  },

  {
    accessorKey: 'descripcion',
    header: 'Descripción del Conflicto',
    cell: ({ row }) => (
      <div className="flex flex-col max-w-[450px]">
        <span className="font-medium text-sm truncate text-foreground" title={row.original.descripcion}>
          {row.original.descripcion}
        </span>
      </div>
    ),
  },

  {
    id: 'actions',
    header: () => <div className="text-right">Acciones</div>,
    cell: ({ row }) => (
      <div className="text-right">
        <ResolverActionCell conflicto={row.original} />
      </div>
    ),
  },
];