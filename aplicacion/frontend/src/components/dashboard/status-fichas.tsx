import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

type AppState = 'noData' | 'extractionPending' | 'extractionReady' | 'confirmed' | 'conflictsOpen';

export function DashboardStatusFichas({ appState }: { appState: AppState }) {
  const resumen =
    appState === 'noData'
      ? 'Aún no has subido ninguna ficha.'
      : 'Fichas cargadas. Preparado para enlazar con sesiones.';

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fichas subidas</CardTitle>
        <CardDescription>Estado de las fichas académicas</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-sm text-muted-foreground">{resumen}</p>

        {/* Placeholder de conteos (mock visual) */}
        <div className="grid grid-cols-3 gap-2 text-sm">
          <div>
            <p className="text-muted-foreground">Válidas</p>
            <p className="font-medium">—</p>
          </div>
          <div>
            <p className="text-muted-foreground">Con incidencias</p>
            <p className="font-medium">—</p>
          </div>
          <div>
            <p className="text-muted-foreground">Última subida</p>
            <p className="font-medium">—</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
