'use client';

import { useState } from 'react';
import { NavLink } from '@/components/common/nav-link';
import { Separator } from '@/components/ui/separator';
import { Home, AlertTriangle, Upload, Users, School, Calendar, NotebookText } from 'lucide-react';

import Link from 'next/link';

export function Sidebar() {
  const [openEntities, setOpenEntities] = useState(false);

  return (
    <aside className="bg-slate-900 text-slate-100 border-r border-slate-800 p-4">
      {/* Brand */}
      <div className="mb-4 px-2 flex items-center gap-2">
        <div className="h-6 w-6 rounded-md bg-slate-100/10 ring-1 ring-white/10" />
        <Link href="/app" className="text-sm font-semibold text-slate-100">
          Detector de Conflictos
        </Link>
      </div>

      {/* Navegación */}
      <nav className="space-y-1">
        <div className="px-2 py-1 text-[11px] uppercase tracking-wide text-slate-400">
          Principal
        </div>
        <NavLink href="/app" variant="sidebar" className="flex items-center gap-2">
          <Home className="h-4 w-4" />
          Inicio
        </NavLink>

        <NavLink href="/conflictos" variant="sidebar" className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4" />
          Conflictos
        </NavLink>

        <Separator className="my-3 bg-slate-800" />

        <div className="px-2 py-1 text-[11px] uppercase tracking-wide text-slate-400">
          Subidas
        </div>
        <NavLink href="/uploads/fichas" variant="sidebar" className="flex items-center gap-2">
          <Upload className="h-4 w-4" />
          Subir fichas
        </NavLink>
        <NavLink href="/uploads/horarios" variant="sidebar" className="flex items-center gap-2">
          <Upload className="h-4 w-4" />
          Subir horarios
        </NavLink>

        <Separator className="my-3 bg-slate-800" />

        <div className="px-2 py-1 text-[11px] uppercase tracking-wide text-slate-400">
          Datos
        </div>

        <NavLink href="/datos/fichas-academicas" variant="sidebar" className="flex items-center gap-2">
          <NotebookText className="h-4 w-4" />
          Fichas académicas
        </NavLink>

        <NavLink href="/datos/horarios" variant="sidebar" className="flex items-center gap-2">
          <Calendar className="h-4 w-4" />
          Horarios
        </NavLink>

        <NavLink href="/datos/profesores" variant="sidebar" className="flex items-center gap-2">
          <Users className="h-4 w-4" />
          Profesores
        </NavLink>

        <NavLink href="/datos/aulas" variant="sidebar" className="flex items-center gap-2">
          <School className="h-4 w-4" />
          Aulas
        </NavLink>

      </nav>
    </aside>
  );
}
