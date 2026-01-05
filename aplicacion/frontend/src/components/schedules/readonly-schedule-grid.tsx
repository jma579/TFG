'use client';

import * as React from 'react';
import { cn } from '@/lib/cn';
import { generateTimeSlots, overlapsSlot } from '@/lib/time';
// Importamos los tipos del API para tener autocompletado del status
import type { MatchStatus } from '@/lib/api/docencia/horarios';

// Definimos nuestra propia interfaz de Sesión para la UI, extendiendo lo básico
export type GridSession = {
  id: string | number;
  title: string;        // Nombre de la asignatura (ya procesado/sugerido)
  originalName?: string;// Nombre original en el PDF (para comparar)
  start: string;        // HH:MM
  end: string;          // HH:MM
  dayIndex: number;     // 0=Lunes, 4=Viernes
  room?: string;
  teacher?: string;
  
  // Metadatos de inteligencia
  matchStatus?: MatchStatus | string | null;
  matchConfidence?: number | null;
  
  // Mantenemos color opcional por si se usa en otros contextos sin IA
  color?: string; 
};

type Props = {
  sessions: GridSession[];
  start?: string;   
  end?: string;     
  stepMin?: number; 
  className?: string;
};

const DAYS = ['L', 'M', 'X', 'J', 'V'];

export function ReadonlyScheduleGrid({
  sessions,
  start = '08:30',
  end = '20:00',
  stepMin = 30,
  className,
}: Props) {
  const slots = React.useMemo(() => generateTimeSlots(start, end, stepMin), [start, end, stepMin]);

  return (
    <div className={cn('relative rounded-lg border bg-card shadow-sm overflow-auto', className)}>
      <div className="grid" style={{ gridTemplateColumns: '80px repeat(5, minmax(140px, 1fr))' }}>
        {/* Cabecera */}
        <div className="sticky top-0 z-10 col-start-1 col-end-2 bg-card/95 backdrop-blur border-b px-2 py-2 text-xs font-medium text-muted-foreground">
          Hora
        </div>
        {DAYS.map((d, i) => (
          <div
            key={d}
            className="sticky top-0 z-10 bg-card/95 backdrop-blur border-b px-2 py-2 text-sm font-semibold text-center"
            style={{ gridColumnStart: i + 2, gridColumnEnd: i + 3 }}
          >
            {d}
          </div>
        ))}

        {/* Filas */}
        {slots.map((t, row) => (
          <React.Fragment key={t}>
            {/* Columna horas */}
            <div
              className={cn(
                'sticky left-0 z-10 border-r bg-background/95 backdrop-blur px-2 py-2 text-xs font-medium text-muted-foreground',
                row < slots.length - 1 ? 'border-b' : ''
              )}
              style={{ gridColumnStart: 1, gridColumnEnd: 2 }}
            >
              {t}
            </div>

            {/* Celdas días */}
            {DAYS.map((_, dayIndex) => {
              const cellSessions = sessions.filter(
                (s) => s.dayIndex === dayIndex && overlapsSlot(t, stepMin, s.start, s.end)
              );
              return (
                <div
                  key={`${t}-${dayIndex}`}
                  className="relative h-12 border-b border-r text-sm group hover:bg-muted/20 transition-colors"
                  style={{ gridColumnStart: dayIndex + 2, gridColumnEnd: dayIndex + 3 }}
                  aria-hidden
                >
                  <div className="absolute inset-1 flex flex-col gap-1 overflow-hidden">
                    {cellSessions.map((s) => (
                      <div
                        key={s.id}
                        className={cn(
                          'truncate rounded px-2 py-1 text-xs border shadow-sm transition-all',
                          getStatusStyles(s.matchStatus, s.color)
                        )}
                        title={getTooltipText(s)}
                      >
                        {/* Indicador visual si hay advertencia */}
                        {(s.matchStatus === 'FUZZY_LOW_CONFIDENCE' || s.matchStatus === 'NO_MATCH') && (
                            <span className="mr-1 inline-block font-bold">⚠️</span>
                        )}
                        <span className="font-medium">{s.title}</span>
                        {s.room && <span className="ml-1 opacity-75 text-[10px]">({s.room})</span>}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// --- Lógica de Estilos e Inteligencia ---

function getStatusStyles(status?: MatchStatus | string | null, fallbackColor?: string) {
  if (!status) {
      // Fallback para sesiones manuales o antiguas
      return 'bg-secondary/50 text-secondary-foreground border-transparent hover:bg-secondary/70';
  }

  switch (status) {
    case 'EXACT':
    case 'ALIAS_DB':
      // Verde Solido (Confianza Total)
      return 'bg-emerald-100 text-emerald-800 border-emerald-200 hover:bg-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800';
    
    case 'FUZZY_AUTO':
      // Verde "Mágico" (Detectado automáticamente con alta confianza)
      return 'bg-green-100 text-green-800 border-green-200 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800';

    case 'FUZZY_LOW_CONFIDENCE':
      // Ámbar/Naranja (Atención requerida)
      return 'bg-amber-100 text-amber-800 border-amber-300 hover:bg-amber-200 ring-1 ring-amber-300 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700';

    case 'NO_MATCH':
      // Rojo (Error crítico)
      return 'bg-red-100 text-red-800 border-red-300 hover:bg-red-200 ring-1 ring-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800';

    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

function getTooltipText(s: GridSession): string {
  let text = `${s.title}`;
  if (s.room) text += `\nAula: ${s.room}`;
  if (s.teacher) text += `\nProf: ${s.teacher}`;
  text += `\nHorario: ${s.start} - ${s.end}`;

  if (s.matchStatus === 'FUZZY_LOW_CONFIDENCE') {
      text += `\n\n⚠️ REVISIÓN REQUERIDA\nEl sistema no está 100% seguro.\nTexto original en PDF: "${s.originalName}"`;
  } else if (s.matchStatus === 'NO_MATCH') {
      text += `\n\n❌ ASIGNATURA DESCONOCIDA\nNo se encontró en base de datos.\nTexto original: "${s.originalName}"`;
  } else if (s.matchStatus === 'FUZZY_AUTO') {
      text += `\n\n✨ Detectado automáticamente\nOriginal: "${s.originalName}"`;
  }

  return text;
}