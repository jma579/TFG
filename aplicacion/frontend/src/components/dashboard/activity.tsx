import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export function DashboardActivity() {
  // Mock estático de ejemplos (solo UI)
  const items = [
    { id: 1, text: 'Sin actividad reciente. Cuando subas un PDF aparecerá aquí.' },
    // { id: 2, text: 'Subiste 1 horario (GRADO X) — hace 5 min' },
    // { id: 3, text: 'Editaste 3 sesiones — hace 12 min' },
  ];

  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle>Actividad reciente</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.map((it, i) => (
          <div key={it.id} className="text-sm text-muted-foreground">
            {it.text}
            {i < items.length - 1 && <Separator className="my-3" />}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
