import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

type AppState = 'noData' | 'extractionPending' | 'extractionReady' | 'confirmed' | 'conflictsOpen';

export function DashboardStatusHorarios({ appState }: { appState: AppState }) {
  let status: { label: string; tone: 'secondary' | 'default' | 'outline'; desc: string } = {
    label: 'Sin datos',
    tone: 'outline',
    desc: 'No hay horarios subidos todavía.',
  };

  if (appState === 'extractionPending') {
    status = { label: 'Extracción en curso', tone: 'secondary', desc: 'Procesando el PDF…' };
  } else if (appState === 'extractionReady') {
    status = { label: 'Listo para confirmar', tone: 'default', desc: 'Hay un horario para revisión.' };
  } else if (appState === 'confirmed') {
    status = { label: 'Confirmado', tone: 'default', desc: 'Horario confirmado. Puedes resolver conflictos.' };
  } else if (appState === 'conflictsOpen') {
    status = { label: 'Con conflictos', tone: 'default', desc: 'Existen conflictos abiertos.' };
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Última extracción de horarios</CardTitle>
        <CardDescription>Estado general del horario detectado</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <Badge variant={status.tone}>{status.label}</Badge>
        <p className="text-sm text-muted-foreground">{status.desc}</p>

        {/* Placeholder de métricas simples (mock visual) */}
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div>
            <p className="text-muted-foreground">Sesiones</p>
            <p className="font-medium">—</p>
          </div>
          <div>
            <p className="text-muted-foreground">Celdas editadas</p>
            <p className="font-medium">—</p>
          </div>
          <div>
            <p className="text-muted-foreground">Última actualización</p>
            <p className="font-medium">—</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
