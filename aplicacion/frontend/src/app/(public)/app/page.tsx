// src/app/(public)/app/page.tsx
'use client';

import Link from 'next/link';
import {
  Upload,
  CalendarPlus,
  CalendarRange,
  BookOpen,
  Users,
  Building2,
  AlertTriangle,
  FileText,
} from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';

type HomeTile = {
  title: string;
  description: string;
  href: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
};

const tiles: HomeTile[] = [
  {
    title: 'Subir ficha',
    description: 'Procesa PDFs de fichas académicas y actualiza el catálogo.',
    href: '/uploads/fichas',
    icon: FileText,
  },
  {
    title: 'Subir horario',
    description: 'Analiza horarios en PDF y genera sesiones temporales.',
    href: '/uploads/horarios',
    icon: Upload,
  },
  {
    title: 'Crear horario',
    description: 'Crea o ajusta un horario desde la rejilla interactiva.',
    href: '/horario',
    icon: CalendarPlus,
  },
  {
    title: 'Ver horario',
    description: 'Consulta y edita los horarios por curso y mención.',
    href: '/datos/horarios',
    icon: CalendarRange,
  },
  {
    title: 'Ver asignaturas',
    description: 'Explora y gestiona el catálogo de asignaturas.',
    href: '/datos/fichas-academicas',
    icon: BookOpen,
  },
  {
    title: 'Ver profesores',
    description: 'Gestiona la información del profesorado.',
    href: '/datos/profesores',
    icon: Users,
  },
  {
    title: 'Ver aulas',
    description: 'Consulta y actualiza las aulas disponibles.',
    href: '/datos/aulas',
    icon: Building2,
  },
  {
    title: 'Resolver conflictos',
    description: 'Accede al resolutor y gestiona solapamientos.',
    href: '/conflictos',
    icon: AlertTriangle,
  },
];

function UserBadge() {
  // Sustituye esto por tu componente real de usuario cuando lo tengas
  return (
    <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-[11px]">
        UD
      </span>
      <span>Usuario demo</span>
    </div>
  );
}

export default function AppHomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-primary/5 via-muted to-muted py-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4">
        {/* Cabecera sin sidebar */}
        <header className="flex items-center justify-between">
          <div className="space-y-2">
            <h1 className="text-2xl font-bold tracking-tight">
              Detector de conflictos
            </h1>
            <p className="max-w-2xl text-sm text-muted-foreground">
              Elige una acción para trabajar con horarios, fichas, recursos
              docentes y resolución de conflictos.
            </p>
          </div>

          <UserBadge />
        </header>

        {/* Tarjeta grande con mosaico */}
        <section className="rounded-2xl border border-primary/10 bg-background/80 px-6 py-6 shadow-sm backdrop-blur">
          <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-4">
            {tiles.map(({ title, description, href, icon: Icon }) => (
              <Link key={href} href={href} className="group">
                <Card className="flex h-full cursor-pointer flex-col border border-border/80 transition-all duration-150 group-hover:-translate-y-1 group-hover:border-primary/40 group-hover:shadow-md">
                  <CardHeader className="space-y-3">
                    <div className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                      <Icon className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-base">{title}</CardTitle>
                    <CardDescription className="text-sm">
                      {description}
                    </CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
