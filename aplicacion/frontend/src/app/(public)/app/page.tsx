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
  LucideIcon,
} from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { cn } from '@/lib/utils';

type HomeTile = {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
};

type Section = {
  title: string;
  items: HomeTile[];
};

const sections: Section[] = [
  {
    title: 'Gestión de Archivos',
    items: [
      {
        title: 'Subir fichas',
        description: 'Procesa PDFs de guías docentes.',
        href: '/uploads/fichas',
        icon: FileText,
      },
      {
        title: 'Subir horarios',
        description: 'Analiza horarios en PDF y extrae sesiones.',
        href: '/uploads/horarios',
        icon: Upload,
      },
    ],
  },
  {
    title: 'Planificación y Conflictos',
    items: [
      {
        title: 'Editor de horarios',
        description: 'Rejilla interactiva para crear o ajustar sesiones.',
        href: '/horario',
        icon: CalendarPlus,
      },
      {
        title: 'Resolver conflictos',
        description: 'Herramienta para detectar y solucionar solapamientos.',
        href: '/conflictos',
        icon: AlertTriangle,
      },
    ],
  },
  {
    title: 'Visualización de Datos',
    items: [
      {
        title: 'Horarios',
        description: 'Consulta de sesiones por curso.',
        href: '/datos/horarios',
        icon: CalendarRange,
      },
      {
        title: 'Asignaturas',
        description: 'Catálogo de materias y créditos.',
        href: '/datos/fichas-academicas',
        icon: BookOpen,
      },
      {
        title: 'Profesores',
        description: 'Listado del cuerpo docente.',
        href: '/datos/profesores',
        icon: Users,
      },
      {
        title: 'Aulas',
        description: 'Espacios y recursos disponibles.',
        href: '/datos/aulas',
        icon: Building2,
      },
    ],
  },
];

function UserBadge() {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1.5 text-sm font-medium shadow-sm transition-colors hover:bg-accent/50">
      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
        UD
      </div>
      <span className="text-muted-foreground">Usuario demo</span>
    </div>
  );
}

export default function AppHomePage() {
  return (
    <main className="min-h-screen bg-muted/30 py-12">
      <div className="mx-auto max-w-6xl space-y-10 px-6">
        {/* Cabecera */}
        <header className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight text-foreground">
              Panel de Control
            </h1>
            <p className="text-muted-foreground">
              Gestiona horarios, recursos y conflictos académicos desde un único lugar.
            </p>
          </div>
          <UserBadge />
        </header>

        <div className="grid gap-10">
          {sections.map((section) => (
            <section key={section.title} className="space-y-4">
              <h2 className="text-lg font-semibold tracking-tight text-foreground/90">
                {section.title}
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {section.items.map((tile) => {
                  const Icon = tile.icon;

                  return (
                    <Link key={tile.href} href={tile.href} className="group block h-full">
                      <Card className="relative h-full overflow-hidden border-muted-foreground/20 transition-all duration-200 hover:-translate-y-1 hover:shadow-md">
                        <CardHeader>
                          <div className="mb-2 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-muted-foreground transition-colors group-hover:bg-primary/10 group-hover:text-primary">
                            <Icon className="h-5 w-5" />
                          </div>
                          <CardTitle className="text-base font-medium">
                            {tile.title}
                          </CardTitle>
                          <CardDescription className="line-clamp-2 text-sm">
                            {tile.description}
                          </CardDescription>
                        </CardHeader>
                      </Card>
                    </Link>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}
