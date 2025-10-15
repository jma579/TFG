import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function MarketingFeatures() {
  return (
    <section className="border-b">
      <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
        <div className="grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Extracción estructurada</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Convierte PDFs de horarios en datos editables: asignatura, aula, profesor, día, inicio y fin.
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Edición en vivo</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Ajusta celdas y corrige errores del OCR/parseo directamente en la tabla de confirmación.
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Detección de conflictos</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Conflictos por aula, profesor y solapes. Visualiza, filtra y resuelve iterando.
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
