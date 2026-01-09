'use client';

import * as React from 'react';
import Link from 'next/link';
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
// ✅ CORRECCIÓN: Usamos tu tipo real 'ProgramaOut'
import type { ProgramaOut } from '@/lib/api/catalogo/programas';

type SchedulesScreenProps = {
  programas: ProgramaOut[]; // ✅ Actualizado
};

export function SchedulesScreen({ programas }: SchedulesScreenProps) {
  const { toast } = useToast();

  const [data, setData] = React.useState<ScheduleSummary[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [selectedProgram, setSelectedProgram] = React.useState<string>("");
  const [searchTerm, setSearchTerm] = React.useState('');

  React.useEffect(() => {
    if (!selectedProgram) {
      setData([]);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      try {
        const result = await getDashboardResumen({ 
          programa_id: Number(selectedProgram) 
        });
        setData(result);
      } catch (error) {
        toast({
          variant: 'destructive',
          title: 'Error de conexión',
          description: 'No se pudieron obtener los datos del horario.',
        });
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedProgram, toast]);

  const filteredData = React.useMemo(() => {
    if (!searchTerm) return data;
    const lowerTerm = searchTerm.toLowerCase();
    
    return data.filter((item) => 
      item.programa_nombre.toLowerCase().includes(lowerTerm) ||
      item.curso.toString().includes(lowerTerm) ||
      item.menciones.some(m => m.toLowerCase().includes(lowerTerm))
    );
  }, [data, searchTerm]);

  // Handlers
  const handleView = (item: ScheduleSummary) => console.log("Ver", item);
  const handleSolve = (item: ScheduleSummary) => console.log("Resolver", item);

  return (
    <div className="space-y-6">
      
      {/* TOOLBAR */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between bg-background p-1">
        <div className="flex flex-1 flex-col gap-2 md:flex-row md:items-center w-full">
          
          <Select value={selectedProgram} onValueChange={setSelectedProgram}>
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
                placeholder="Filtrar por curso o mención..."
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

      {/* CONTENIDO */}
      {loading && (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {!selectedProgram && !loading && (
        <Card className="border-dashed shadow-sm bg-muted/30">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="p-4 bg-background rounded-full mb-4 shadow-sm">
              <BookOpen className="h-8 w-8 text-primary/60" />
            </div>
            <h3 className="text-lg font-semibold">Selecciona una titulación</h3>
            <p className="text-muted-foreground max-w-sm mt-1">
              Elige un grado en el menú superior para ver su planificación actual.
            </p>
          </CardContent>
        </Card>
      )}

      {selectedProgram && !loading && filteredData.length === 0 && (
        <Card className="border-dashed shadow-sm">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Filter className="h-8 w-8 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              No se encontraron horarios registrados para esta selección.
            </p>
          </CardContent>
        </Card>
      )}

      {!loading && filteredData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in duration-500">
          {filteredData.map((item, idx) => (
            <ScheduleCard
              key={`${item.programa_id}-${item.curso}-${item.cuatrimestre}-${item.menciones[0] || 'G'}-${idx}`}
              data={item}
              onView={handleView}
              onSolve={handleSolve}
            />
          ))}
        </div>
      )}
    </div>
  );
}