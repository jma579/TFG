'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Upload, AlertTriangle } from 'lucide-react';

type Props = {
  canGoConflictos: boolean;
};

export function DashboardQuickActions({ canGoConflictos }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Acciones rápidas</CardTitle>
      </CardHeader>

      {/* 3 acciones en desktop */}
      <CardContent className="grid gap-3 md:grid-cols-3">
        <Button asChild variant="secondary" className="justify-start">
          <Link href="/uploads/horarios">
            <Upload className="mr-2 h-4 w-4" />
            Subir horarios
          </Link>
        </Button>

        <Button asChild variant="secondary" className="justify-start">
          <Link href="/uploads/fichas">
            <Upload className="mr-2 h-4 w-4" />
            Subir fichas
          </Link>
        </Button>

        <Button asChild disabled={!canGoConflictos} className="justify-start" variant="outline">
          <Link
            href={canGoConflictos ? '/conflictos' : '#'}
            aria-disabled={!canGoConflictos}
            className={!canGoConflictos ? 'pointer-events-none opacity-60' : ''}
          >
            <AlertTriangle className="mr-2 h-4 w-4" />
            Ir al detector de conflictos
          </Link>
        </Button>
      </CardContent>

      <p className="px-6 pb-4 text-xs text-muted-foreground">
        Flujo recomendado: sube horarios y fichas. La confirmación del horario ocurre dentro del
        proceso de subida.
      </p>
    </Card>
  );
}
