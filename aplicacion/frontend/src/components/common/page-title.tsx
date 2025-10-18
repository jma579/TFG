// src/components/common/page-title.tsx
'use client';

import { usePathname } from 'next/navigation';

const LABELS: Record<string, string> = {
  app: 'Inicio',
  conflictos: 'Conflictos',
  uploads: 'Subidas',
  fichas: 'Subir fichas',
  horarios: 'Subir horarios',
  datos: 'Datos',
  'fichas-academicas': 'Fichas académicas',
  profesores: 'Profesores',
  aulas: 'Aulas',
  horario: 'Horario',
};

export function PageTitle() {
  const pathname = usePathname() || '/';
  const parts = pathname.split('/').filter(Boolean).filter((seg) => seg !== '(dashboard)');
  const last = parts[parts.length - 1] ?? 'app';
  const title = LABELS[last] ?? capitalize(last);

  return <h1 className="text-xl md:text-2xl font-semibold tracking-tight">{title}</h1>;
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
