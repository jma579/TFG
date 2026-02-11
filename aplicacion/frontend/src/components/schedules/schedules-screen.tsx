'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { Search, BookOpen, Loader2, Filter, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';

// Componentes y Tipos
import { ScheduleCard } from '@/components/schedules/schedule-card';
import type { ScheduleSummary } from '@/components/schedules/data';

// APIs
import { getDashboardResumen } from '@/lib/api/docencia/dashboard';
import { deleteHorario } from '@/lib/api/docencia/horarios'; // Nueva importación
import type { ProgramaOut } from '@/lib/api/catalogo/programas';

type SchedulesScreenProps = {
  programas: ProgramaOut[];
};

export function SchedulesScreen({ programas }: SchedulesScreenProps) {
  const { toast } = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const [data, setData] = React.useState<ScheduleSummary[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [selectedProgram, setSelectedProgram] = React.useState<string>("");
  const [searchTerm, setSearchTerm] = React.useState('');

  // Función de carga de datos (extraída para poder reutilizarla tras borrar)
  const fetchData = React.useCallback(async () => {
    if (!selectedProgram) {
      setData([]);
      return;
    }

    setLoading(true);
    try {
      const result = await getDashboardResumen({ 
        programa_id: Number(selectedProgram) 
      });
      setData(result);
    } catch {
      toast({
        variant: 'destructive',
        title: 'Error de conexión',
        description: 'No se pudieron obtener los datos del horario.',
      });
    } finally {
      setLoading(false);
    }
  }, [selectedProgram, toast]);

  React.useEffect(() => {
    const progId = searchParams.get('programa_id');
    if (progId && progId !== selectedProgram) {
      setSelectedProgram(progId);
    }
  }, [searchParams, selectedProgram]); 

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredData = React.useMemo(() => {
    // 1. Primero filtramos los que tienen al menos una sesión
    const withSessions = data.filter(item => item.total_sesiones > 0);

    if (!searchTerm) return withSessions;
    
    const lowerTerm = searchTerm.toLowerCase();
    return withSessions.filter((item) => 
      item.programa_nombre.toLowerCase().includes(lowerTerm) ||
      item.curso.toString().includes(lowerTerm) ||
      item.menciones.some(m => m.toLowerCase().includes(lowerTerm))
    );
  }, [data, searchTerm]);

  const handleProgramChange = (value: string) => {
    setSelectedProgram(value);
    const params = new URLSearchParams(searchParams);
    params.set('programa_id', value);
    router.replace(`${pathname}?${params.toString()}`);
  };

  const handleView = (item: ScheduleSummary) => {
    const params = new URLSearchParams();
    params.set('programa_id', String(item.programa_id));
    params.set('curso', String(item.curso));

    if (item.periodo) {
      params.set('periodo', item.periodo);
    }
    
    if (item.menciones && item.menciones.length > 0) {
        params.set('mencion', item.menciones[0]);
    }

    router.push(`/datos/horarios/detalle?${params.toString()}`);
  };
  // Lógica de borrado real conectada al Backend
  const handleDelete = async (item: ScheduleSummary) => {
    try {
      // El endpoint DELETE del backend sigue esperando un número entero (1 o 2)
      const numCuatri = item.periodo.includes('primer') ? 1 : 2;

      await deleteHorario({
        programa_id: item.programa_id,
        curso: item.curso,
        cuatrimestre: numCuatri, 
        mencion: item.menciones?.[0] || undefined
      });

      toast({
        title: "Horario eliminado",
        description: `Se han eliminado las sesiones de ${item.curso}º curso correctamente.`,
      });

      // Refrescamos la lista para que la tarjeta desaparezca o se actualice
      fetchData();
    } catch (error: unknown) {
      const errorDetail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || "No se pudo eliminar el horario.";
      toast({
        variant: 'destructive',
        title: 'Error al eliminar',
        description: errorDetail,
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between bg-background p-1">
        <div className="flex flex-1 flex-col gap-2 md:flex-row md:items-center w-full">
          <Select value={selectedProgram} onValueChange={handleProgramChange}>
            <SelectTrigger className="h-10 w-full md:w-[320px]">
              <SelectValue placeholder="Selecciona una titulación..." />
            </SelectTrigger>
            <SelectContent>
              {programas.map((p) => (
                <SelectItem key={p.id} value={String(p.id)}>
                  {p.nombre}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {selectedProgram && (
            <div className="relative w-full md:max-w-xs animate-in fade-in slide-in-from-left-2">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Filtrar por curso..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 h-10"
              />
            </div>
          )}
        </div>

        <Button asChild>
          <Link href="/uploads/horarios">
            <Plus className="mr-2 h-4 w-4" /> Subir horarios
          </Link>
        </Button>
      </div>

      {loading && (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {!selectedProgram && !loading && (
        <Card className="border-dashed shadow-sm bg-muted/30">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <BookOpen className="h-8 w-8 text-primary/60 mb-4" />
            <h3 className="text-lg font-semibold">Selecciona una titulación</h3>
          </CardContent>
        </Card>
      )}

      {selectedProgram && !loading && filteredData.length === 0 && (
        <Card className="border-dashed shadow-sm">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Filter className="h-8 w-8 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No hay horarios registrados.</p>
          </CardContent>
        </Card>
      )}

      {!loading && filteredData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in duration-500">
          {filteredData.map((item, idx) => (
            <ScheduleCard
              key={`${item.programa_id}-${item.curso}-${idx}`}
              data={item}
              onView={handleView}
              onDelete={handleDelete} // Prop actualizada
            />
          ))}
        </div>
      )}
    </div>
  );
}