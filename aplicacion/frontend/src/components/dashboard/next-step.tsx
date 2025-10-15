import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ListChecks } from 'lucide-react';

type AppState = 'noData' | 'extractionPending' | 'extractionReady' | 'confirmed' | 'conflictsOpen';

export function DashboardNextStep({ appState }: { appState: AppState }) {
  const { title, desc, ctaHref, ctaLabel } = (() => {
    switch (appState) {
      case 'extractionPending':
        return {
          title: 'Siguiente paso',
          desc: 'Estamos procesando tu PDF. En breve podrás revisar el horario.',
          ctaHref: '/uploads/horarios',
          ctaLabel: 'Ver subidas',
        };
      case 'extractionReady':
        return {
          title: 'Siguiente paso',
          desc: 'Hay un horario listo para confirmación.',
          ctaHref: '/horario',
          ctaLabel: 'Revisar horario',
        };
      case 'confirmed':
        return {
          title: 'Siguiente paso',
          desc: 'El horario está confirmado. Puedes resolver conflictos.',
          ctaHref: '/conflictos',
          ctaLabel: 'Abrir detector de conflictos',
        };
      case 'conflictsOpen':
        return {
          title: 'Siguiente paso',
          desc: 'Hay conflictos abiertos. Continúa resolviéndolos.',
          ctaHref: '/conflictos',
          ctaLabel: 'Reanudar resolución',
        };
      case 'noData':
      default:
        return {
          title: 'Siguiente paso',
          desc: 'Comienza por subir un PDF de horario y otro de fichas.',
          ctaHref: '/uploads/horarios',
          ctaLabel: 'Subir horarios',
        };
    }
  })();

  return (
    <Card className="col-span-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <ListChecks className="h-5 w-5" />
          {title}
        </CardTitle>
        <Button asChild>
          <Link href={ctaHref}>{ctaLabel}</Link>
        </Button>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{desc}</p>
        <ul className="mt-3 grid gap-2 text-sm">
          <li>☐ Subir horarios</li>
          <li>☐ Subir fichas</li>
          <li>☐ Confirmar horario</li>
          <li>☐ Resolver conflictos</li>
        </ul>
      </CardContent>
    </Card>
  );
}
