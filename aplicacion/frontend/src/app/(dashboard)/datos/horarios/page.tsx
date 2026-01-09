'use client';

import * as React from 'react';
import { SchedulesScreen } from '@/components/schedules/schedules-screen';
// ✅ CORRECCIÓN: Importamos ProgramaOut
import { listProgramas, ProgramaOut } from '@/lib/api/catalogo/programas';

export default function HorariosPage() {
  const [programas, setProgramas] = React.useState<ProgramaOut[]>([]);
  
  React.useEffect(() => {
    // ✅ CORRECCIÓN: Tu función listProgramas espera (page, size).
    // Pedimos página 1, 100 elementos (o 1000 si quieres asegurarte de traer todos)
    listProgramas(1, 1000)
      .then((res) => {
        // Tu API devuelve un objeto { total, items, ... }, así que usamos res.items
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

      <SchedulesScreen programas={programas} />
    </div>
  );
}