'use client';

import { Loader2 } from 'lucide-react';
import * as React from 'react';

import { SchedulesScreen } from '@/components/schedules/schedules-screen';
import { listProgramas, type ProgramaOut } from '@/lib/api/catalogo/programas';

const PROGRAMAS_LIMIT = 1000;

export default function HorariosPage() {
  const [programas, setProgramas] = React.useState<ProgramaOut[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  
  React.useEffect(() => {
    listProgramas({ limit: PROGRAMAS_LIMIT })
      .then((res) => {
        setProgramas(res.items || []); 
        setError(null);
      })
      .catch((err) => {
        console.error("Error cargando programas:", err);
        setError("No se pudieron cargar los programas. Verifica la conexión con la API.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Consulta de Horarios</h1>
        <p className="text-muted-foreground">
          Visualiza las sesiones programadas por curso y grupo.
        </p>
      </div>

      {loading ? (
        <div className="flex h-64 w-full items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="p-4 text-red-600 bg-red-50 rounded-md border border-red-200">
          {error}
        </div>
      ) : (
        <SchedulesScreen programas={programas} />
      )}
    </div>
  );
}