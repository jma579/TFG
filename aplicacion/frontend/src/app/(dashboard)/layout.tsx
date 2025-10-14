import { Breadcrumbs } from '@/components/common/breadcrumbs';
import { NavLink } from '@/components/common/nav-link';
import { Separator } from '@/components/ui/separator';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh grid grid-cols-[220px_1fr]">
      {/* Sidebar */}
      <aside className="border-r bg-background/50 p-4">
        <div className="mb-4 px-2">
          <h2 className="text-base font-semibold">Detector de Conflictos</h2>
          <p className="text-xs text-muted-foreground">TFG — UI</p>
        </div>

        <nav className="space-y-1">
          <div className="px-2 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">
            Subidas
          </div>
          <NavLink href="/uploads/fichas">Fichas</NavLink>
          <NavLink href="/uploads/horarios">Horarios</NavLink>

          <Separator className="my-3" />

          <div className="px-2 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">
            Revisión
          </div>
          <NavLink href="/horario">Horario</NavLink>
          <NavLink href="/conflictos">Conflictos</NavLink>
        </nav>
      </aside>

      {/* Main */}
      <div className="grid grid-rows-[56px_1fr]">
        {/* Header */}
        <header className="border-b bg-background/50 px-6 flex items-center justify-between">
          <Breadcrumbs />
          {/* espacio para acciones futuras: tema, cuenta, etc. */}
        </header>

        {/* Content */}
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
