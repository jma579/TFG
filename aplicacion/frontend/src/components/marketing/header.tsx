'use client';

import Link from 'next/link';

import { Button } from '@/components/ui/button';

export function MarketingHeader() {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-md bg-primary" />
          <span className="text-sm font-semibold">Detector de Conflictos</span>
        </Link>

        {/* Acciones derechas */}
        <nav className="flex items-center gap-3">
          {/* (Opcional) En el futuro: /pricing si lo quisieras */}
          {/* <Link href="/pricing" className="text-sm text-muted-foreground hover:text-foreground">Precios</Link> */}
          <Button variant="ghost" asChild>
            <Link href="/login">Iniciar sesión</Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}
