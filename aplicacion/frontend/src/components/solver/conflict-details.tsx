import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { ConflictoOut } from '@/lib/api/conflictos';

type Props = {
  conflict: ConflictoOut;
  description?: string;
};

export function ConflictDetails({ conflict, description }: Props) {
  return (
    <Card>
      <CardHeader className="space-y-2">
        <CardTitle className="text-xl">
          {conflict.descripcion}
        </CardTitle>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">ID:</span>
          <span className="font-mono">{conflict.id}</span>

          <span className="text-muted-foreground">•</span>
          <span className="text-muted-foreground">Tipo:</span>
          <span>{conflict.tipo}</span>

          <span className="text-muted-foreground">•</span>
          <span className="text-muted-foreground">Severidad:</span>
          <Badge variant="destructive">{conflict.severidad}</Badge>

          <span className="text-muted-foreground">•</span>
          <span className="text-muted-foreground">Estado:</span>
          <Badge variant={conflict.estado === 'solucionado' ? 'outline' : 'default'}>
            {conflict.estado}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-2">
        <h3 className="text-sm font-medium">Descripción</h3>
        <p className="text-sm text-muted-foreground leading-6">
          {description ?? 'Este conflicto ha sido detectado automáticamente por el sistema a partir de los horarios y fichas cargados. Revisa el horario interactivo para aplicar la corrección adecuada y resolver la incidencia.'}
        </p>
      </CardContent>
    </Card>
  );
}
