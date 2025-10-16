// src/components/solver/solver-actions.tsx
'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

export function SolverActions({ conflictId }: { conflictId: string }) {
  const router = useRouter();

  const onGenerate = () => {
    // Aquí más adelante invocarás tu API de “generar informe” / “resolver”.
    // Por ahora, solo navegamos de vuelta a la lista de conflictos.
    console.warn('Generar informe (simulado) para conflicto:', conflictId);
    router.push('/conflictos');
  };

  return (
    <div className="sticky bottom-6 z-20">
      <div className="flex justify-end">
        <Button size="lg" onClick={onGenerate} aria-label="Generar informe y finalizar">
          Resolver conflicto
        </Button>
      </div>
    </div>
  );
}
