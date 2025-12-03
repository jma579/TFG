// src/app/(public)/layout.tsx
import type { ReactNode } from 'react';

export default function PublicLayout({ children }: { children: ReactNode }) {
  // Layout específico para las páginas "públicas" (por ahora, /app)
  // Aquí NO hay sidebar ni barra superior del dashboard.
  return (
    <div className="min-h-screen bg-muted text-foreground">
      {children}
    </div>
  );
}
