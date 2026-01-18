'use client';

import * as React from 'react';
import { Suspense } from 'react'; 
import { SchedulesScreen } from '@/components/schedules/schedules-screen';
import { listProgramas, type ProgramaOut } from '@/lib/api/catalogo/programas';
import { Loader2 } from 'lucide-react';

export default function HorariosPage() {
  const [programas, setProgramas] = React.useState<ProgramaOut[]>([]);
  
  React.useEffect(() => {
    // Carga inicial de la lista de programas para el selector
    listProgramas({ limit: 1000 })
      .then((res) => {
        setProgramas(res.items || []); 
      })
      .catch(err => console.error("Error cargando programas", err));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Consulta de Horarios</h1>
        <p className="text-muted-foreground">
          Visualiza las sesiones programadas por curso y grupo.
        </p>
      </div>

      <Suspense fallback={
        <div className="flex h-64 w-full items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }>
        <SchedulesScreen programas={programas} />
      </Suspense>
    </div>
  );
}