'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function Breadcrumbs({ className = '' }: { className?: string }) {
  const LABELS: Record<string, string> = {
    app: 'Inicio',
    conflictos: 'Conflictos',
    uploads: 'Subidas',
    fichas: 'Fichas',
    horarios: 'Horarios',
    datos: 'Datos',
    'fichas-academicas': 'Fichas académicas',
    profesores: 'Profesores',
    aulas: 'Aulas',
    horario: 'Horario',
  };

  const pathname = usePathname() || '/';
  const parts = pathname
    .split('/')
    .filter(Boolean)
    .filter((seg) => seg !== '(dashboard)');

  if (parts.length <= 1) return null;

  return (
    <nav className={`text-sm ${className}`}>
      {parts.map((seg, i) => {
        const href = '/' + parts.slice(0, i + 1).join('/');
        const label = LABELS[seg] ?? capitalize(seg);
        const isLast = i === parts.length - 1;
        return (
          <span key={href} className="inline-flex items-center gap-2">
            {i > 0 && <span className="text-muted-foreground">/</span>}
            {isLast ? (
              <span className="text-muted-foreground">{label}</span>
            ) : (
              <Link href={href} className="text-muted-foreground hover:underline">
                {label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
