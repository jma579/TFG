import Image from 'next/image';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export function MarketingHero() {
  return (
    <section className="border-b">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-16 md:grid-cols-2 md:py-20">
        <div className="space-y-5">
          <h1 className="text-3xl font-bold tracking-tight md:text-5xl">
            Detecta y corrige conflictos de horarios <span className="text-primary">en minutos</span>
          </h1>
          <p className="text-muted-foreground md:text-lg">
            Sube tus fichas y horarios, revisa la extracción en una tabla interactiva y resuelve
            solapes o asignaciones conflictivas en tiempo real.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link href="/login?view=accounts" prefetch>Empieza a resolver conflictos</Link>
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Demo local para TFG. Primera versión. No se requiere despliegue ni registro.
          </p>
        </div>

        {/* Imagen / mock de horario */}
        <div className="relative">
          <div className="rounded-xl border bg-card shadow-sm">
            <Image
              src="/hero-schedule.svg" // lo creamos en el paso 2
              alt="Vista previa del horario interactivo"
              width={1200}
              height={800}
              className="h-auto w-full"
              priority
            />
          </div>
        </div>
      </div>
    </section>
  );
}
