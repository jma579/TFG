'use client';

import { usePathname } from 'next/navigation';

import { cn } from '@/lib/utils';

const LABELS: Record<string, string> = {
  app: 'Inicio',
  conflictos: 'Resolución de Conflictos',
  uploads: 'Subidas',
  fichas: 'Subir Fichas Académicas',
  horarios: 'Subir Horarios',
  datos: 'Datos Maestros',
  'fichas-academicas': 'Fichas Académicas',
  profesores: 'Profesores',
  aulas: 'Aulas',
  horario: 'Editor de Horarios',
};

interface PageTitleProps {
  title?: string;
  subtitle?: string;
  className?: string;
}

export function PageTitle({ title, subtitle, className }: PageTitleProps) {
  const pathname = usePathname() || '/';
  
  const parts = pathname.split('/').filter(Boolean).filter((seg) => seg !== '(dashboard)');
  const last = parts[parts.length - 1] ?? 'app';
  const autoTitle = LABELS[last] ?? capitalize(last);

  return (
    <div className={cn("space-y-1.5", className)}>
      <h1 className="text-3xl font-bold tracking-tight text-foreground">
        {title || autoTitle}
      </h1>
      {subtitle && (
        <p className="text-muted-foreground text-lg">
          {subtitle}
        </p>
      )}
    </div>
  );
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
