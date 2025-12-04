"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AlertTriangle,
  CalendarRange,
  CalendarClock,
  Upload,
  FileUp,
  BookOpen,
  Users,
  School,
  LayoutDashboard,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navSections = [
  {
    label: "Planificación",
    items: [
      {
        label: "Crear horario",
        href: "/horario",
        icon: CalendarClock,
      },
      {
        label: "Resolver conflictos",
        href: "/conflictos",
        icon: AlertTriangle,
      },
    ],
  },
  {
    label: "Subidas",
    items: [
      {
        label: "Subir fichas",
        href: "/uploads/fichas",
        icon: Upload,
      },
      {
        label: "Subir horarios",
        href: "/uploads/horarios",
        icon: FileUp,
      },
    ],
  },
  {
    label: "Datos",
    items: [
      {
        label: "Ver horario",
        href: "/datos/horarios",
        icon: CalendarRange,
      },
      {
        label: "Ver asignaturas",
        href: "/datos/fichas-academicas",
        icon: BookOpen,
      },
      {
        label: "Ver profesores",
        href: "/datos/profesores",
        icon: Users,
      },
      {
        label: "Ver aulas",
        href: "/datos/aulas",
        icon: School,
      },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-border bg-slate-50 text-foreground">
      {/* Header */}
      <Link href="/app" className="flex items-center gap-3 px-6 py-6 transition-opacity hover:opacity-80">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
          <LayoutDashboard className="h-5 w-5" />
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Panel
          </span>
          <span className="text-sm font-bold tracking-tight">Detector</span>
        </div>
      </Link>

      {/* Navigation */}
      <nav className="mt-2 flex-1 space-y-6 overflow-y-auto px-4 pb-4">
        {navSections.map((section) => (
          <div key={section.label} className="space-y-2">
            <p className="px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
              {section.label}
            </p>
            <ul className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href || pathname?.startsWith(item.href + "/");

                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={cn(
                        "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all duration-200",
                        isActive
                          ? "bg-white text-primary shadow-sm ring-1 ring-border"
                          : "text-muted-foreground hover:bg-white hover:text-foreground hover:shadow-sm"
                      )}
                    >
                      <Icon
                        className={cn(
                          "h-4 w-4 flex-shrink-0 transition-colors",
                          isActive
                            ? "text-primary"
                            : "text-muted-foreground group-hover:text-foreground"
                        )}
                      />
                      <span>{item.label}</span>
                      {isActive && (
                        <div className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer / User Profile */}
      <div className="border-t border-border p-4">
        <div className="flex items-center gap-3 rounded-lg border border-border bg-white p-3 transition-colors hover:bg-white/80 shadow-sm">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
            UD
          </div>
          <div className="flex flex-col overflow-hidden">
            <span className="truncate text-sm font-medium text-foreground">
              Usuario demo
            </span>
            <span className="truncate text-xs text-muted-foreground">
              Sesión activa
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}