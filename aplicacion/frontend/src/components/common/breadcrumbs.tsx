'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const LABELS: Record<string, string> = {
  uploads: 'Subidas',
  fichas: 'Fichas',
  horarios: 'Horarios',
  horario: 'Horario',
  conflictos: 'Conflictos',
};

export function Breadcrumbs() {
  const pathname = usePathname() || '/';
  const parts = pathname
    .split('/')
    .filter(Boolean)
    // ignorar el grupo (dashboard) que no forma parte de la URL pública
    .filter((seg) => seg !== '(dashboard)');

  if (parts.length === 0) return null;

  const segments = parts.map((seg, i) => {
    const href = '/' + parts.slice(0, i + 1).join('/');
    const label = LABELS[seg] ?? capitalize(seg);
    const isLast = i === parts.length - 1;

    return (
      <span key={href} className="inline-flex items-center gap-2">
        {i > 0 && <span className="text-muted-foreground">/</span>}
        {isLast ? (
          <span className="text-foreground">{label}</span>
        ) : (
          <Link href={href} className="text-muted-foreground hover:underline">
            {label}
          </Link>
        )}
      </span>
    );
  });

  return <nav className="text-sm">{segments}</nav>;
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
