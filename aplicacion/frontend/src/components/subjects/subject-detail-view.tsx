'use client';

import { Loader2 } from 'lucide-react';
import * as React from 'react';

import { Badge } from '@/components/ui/badge';
import {
  type AsignaturaOut,
  getAsignatura,
  getAsignaturaProgramas,
} from '@/lib/api/catalogo/asignaturas';
import { getAsignaturaProfesores } from '@/lib/api/recursos/profesores';

type Props = {
  asignaturaId: number;
  extractionStatus?: {
    success: boolean;
    errors?: string[] | null;
  };
  onDataLoaded?: (data: { 
    profesores: { nombre: string; apellidos: string }[]; 
    titulaciones: { titulacion: string; tipo_asignatura: string; curso: string }[] 
  }) => void;
};

type SubjectData = {
  asignatura: AsignaturaOut | null;
  profesores: { nombre: string; apellidos: string }[];
  titulaciones: { titulacion: string; tipo_asignatura: string; curso: string }[];
  loading: boolean;
  error?: string;
};

function formatPeriodo(periodo?: string): string {
  if (!periodo) return '-';
  
  switch (periodo.toLowerCase()) {
    case 'primer_cuatrimestre':
      return 'Primer Cuatrimestre';
    case 'segundo_cuatrimestre':
      return 'Segundo Cuatrimestre';
    case 'anual':
      return 'Anual';
    default:
      return periodo.charAt(0).toUpperCase() + periodo.slice(1).replace(/_/g, ' ');
  }
}

export function SubjectDetailView({ asignaturaId, extractionStatus, onDataLoaded }: Props) {
  const [data, setData] = React.useState<SubjectData>({
    asignatura: null,
    profesores: [],
    titulaciones: [],
    loading: true,
  });

  const onDataLoadedRef = React.useRef(onDataLoaded);

  React.useEffect(() => {
    onDataLoadedRef.current = onDataLoaded;
  }, [onDataLoaded]);

  React.useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        const [asignatura, programas, profesores] = await Promise.all([
          getAsignatura(asignaturaId),
          getAsignaturaProgramas(asignaturaId),
          getAsignaturaProfesores(asignaturaId),
        ]);

        if (!mounted) return;

        const titulaciones = programas.map((p) => ({
          titulacion: p.programa.nombre,
          tipo_asignatura: p.tipo_asignatura ?? '—',
          curso: p.curso != null ? `${p.curso}º` : '—',
        }));

        const teachers = profesores.map((p) => ({
          nombre: p.nombre,
          apellidos: p.apellidos,
        }));

        setData({
          asignatura,
          profesores: teachers,
          titulaciones,
          loading: false,
        });

        if (onDataLoadedRef.current) {
          onDataLoadedRef.current({ profesores: teachers, titulaciones });
        }
      } catch (err) {
        if (!mounted) return;
        setData((prev) => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : 'Error al cargar datos',
        }));
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, [asignaturaId]); 

  if (data.loading) {
    return (
      <div className="flex items-center justify-center py-8 text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Cargando detalles de la asignatura...
      </div>
    );
  }

  if (data.error) {
    return (
      <div className="rounded-md bg-red-50 p-4 text-sm text-red-600">
        Error: {data.error}
      </div>
    );
  }

  if (!data.asignatura) {
    return (
      <div className="py-4 text-sm text-muted-foreground">
        No se encontró la asignatura.
      </div>
    );
  }

  const { asignatura, profesores, titulaciones } = data;

  return (
    <div className="rounded-md border bg-muted/30 px-4 py-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider">Asignatura</p>
          <p className="text-base font-semibold text-foreground">{asignatura.nombre}</p>
        </div>
        <div className="flex items-center gap-2">
          {extractionStatus && (
            <Badge variant={extractionStatus.success ? 'secondary' : 'destructive'}>
              {extractionStatus.success ? 'Extracción OK' : 'Errores'}
            </Badge>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <p className="text-xs text-muted-foreground">Código plan</p>
          <p className="text-sm font-mono font-medium">{asignatura.codigo_plan}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Periodo</p>
          <p className="text-sm">
            {formatPeriodo(asignatura.periodo)}
            {asignatura.num_periodo ? ` · P${asignatura.num_periodo}` : ''}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">ECTS</p>
          <p className="text-sm">{asignatura.ects ?? '-'}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Modalidad</p>
          <p className="text-sm capitalize">{asignatura.modalidad ?? '-'}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Idioma</p>
          <p className="text-sm capitalize">{asignatura.idioma ?? '-'}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">English friendly</p>
          <p className="text-sm">{asignatura.english_friendly ? 'Sí' : 'No'}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Estado</p>
          <p className="text-sm">
            <span className={`inline-block w-2 h-2 rounded-full mr-1.5 ${asignatura.activo ? 'bg-green-500' : 'bg-slate-300'}`} />
            {asignatura.activo ? 'Activa' : 'Inactiva'}
          </p>
        </div>
        
        <div className="md:col-span-3 mt-2">
          <p className="text-xs text-muted-foreground mb-1">Profesores</p>
          <div className="text-sm bg-background rounded border p-2">
            {profesores.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {profesores.map((p, i) => (
                  <span key={i} className="inline-flex items-center px-2 py-1 rounded-md bg-slate-100 text-slate-700 text-xs">
                    {p.nombre} {p.apellidos}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-muted-foreground italic">No hay profesores asignados</span>
            )}
          </div>
        </div>

        <div className="md:col-span-3">
          <p className="text-xs text-muted-foreground mb-1">Titulaciones</p>
          <div className="text-sm bg-background rounded border p-2">
            {titulaciones.length > 0 ? (
              <ul className="space-y-1">
                {titulaciones.map((t, i) => (
                  <li key={i} className="flex items-center gap-2 text-slate-700">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    <span>{t.titulacion}</span>
                    <span className="text-slate-400 mx-1">•</span>
                    <span className="text-slate-500">{t.tipo_asignatura}</span>
                    <span className="text-slate-400 mx-1">•</span>
                    <span className="font-medium text-slate-600">{t.curso}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <span className="text-muted-foreground italic">No hay titulaciones vinculadas</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}