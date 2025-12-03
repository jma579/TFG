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
} from "lucide-react";

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

function classNames(...values: (string | false | null | undefined)[]) {
  return values.filter(Boolean).join(" ");
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-slate-800 bg-slate-950 text-slate-100">
      <div className="flex items-center gap-2 px-6 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-100 text-slate-900 font-semibold">
          DC
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Panel
          </span>
          <span className="text-sm font-semibold">Detector de conflictos</span>
        </div>
      </div>

      <nav className="mt-2 flex-1 space-y-4 overflow-y-auto px-3 pb-4">
        {navSections.map((section) => (
          <div key={section.label}>
            <p className="px-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {section.label}
            </p>
            <ul className="mt-1 space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href || pathname?.startsWith(item.href + "/");

                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={classNames(
                        "group flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                        isActive
                          ? "bg-slate-800 text-slate-50"
                          : "text-slate-300 hover:bg-slate-800/70 hover:text-slate-50"
                      )}
                    >
                      <Icon className="h-4 w-4 flex-shrink-0" />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-slate-800 px-6 py-4 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-800 text-xs font-medium">
            UD
          </div>
          <div className="flex flex-col">
            <span className="font-medium text-slate-100">Usuario demo</span>
            <span>Sesión activa</span>
          </div>
        </div>
      </div>
    </aside>
  );
}