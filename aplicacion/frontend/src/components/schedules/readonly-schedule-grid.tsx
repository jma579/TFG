'use client';

import * as React from 'react';
import { cn } from '@/lib/cn';
import { generateTimeSlots, overlapsSlot } from '@/lib/time';
import type { Session } from '@/components/solver/schedule-mock';

type Props = {
  sessions: Session[];
  start?: string;   // HH:MM
  end?: string;     // HH:MM
  stepMin?: number; // 30 por defecto
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
      <div className="grid" style={{ gridTemplateColumns: '120px repeat(5, minmax(160px, 1fr))' }}>
        {/* Cabecera */}
        <div className="sticky top-0 z-10 col-start-1 col-end-2 bg-card/95 backdrop-blur border-b px-3 py-2 text-sm font-medium">
          Hora
        </div>
        {DAYS.map((d, i) => (
          <div
            key={d}
            className="sticky top-0 z-10 bg-card/95 backdrop-blur border-b px-3 py-2 text-sm font-medium text-center"
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
                'sticky left-0 z-10 border-r bg-background/90 backdrop-blur px-3 py-2 text-sm font-medium',
                row < slots.length - 1 ? 'border-b' : ''
              )}
              style={{ gridColumnStart: 1, gridColumnEnd: 2 }}
            >
              {t}
            </div>

            {/* Celdas días: sin interacción */}
            {DAYS.map((_, dayIndex) => {
              const cellSessions = sessions.filter(
                (s) => s.dayIndex === dayIndex && overlapsSlot(t, stepMin, s.start, s.end)
              );
              return (
                <div
                  key={`${t}-${dayIndex}`}
                  className="relative h-10 border-b border-r text-sm"
                  style={{ gridColumnStart: dayIndex + 2, gridColumnEnd: dayIndex + 3 }}
                  aria-hidden
                >
                  <div className="absolute inset-1 flex flex-col gap-1">
                    {cellSessions.map((s) => (
                      <div
                        key={s.id}
                        className={cn(
                          'truncate rounded px-1.5 py-0.5 text-xs ring-1',
                          chipColor(s.color)
                        )}
                        title={`${s.title} — ${s.room} — ${s.teacher} (${s.start}-${s.end})`}
                      >
                        {s.title}
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

function chipColor(c: Session['color']) {
  switch (c) {
    case 'blue': return 'bg-blue-500/15 text-blue-700 ring-blue-500/30';
    case 'green': return 'bg-green-500/15 text-green-700 ring-green-500/30';
    case 'orange': return 'bg-amber-500/15 text-amber-700 ring-amber-500/30';
    case 'red': return 'bg-red-500/15 text-red-700 ring-red-500/30';
    case 'purple': return 'bg-violet-500/15 text-violet-700 ring-violet-500/30';
    default: return 'bg-primary/10 text-primary ring-primary/30';
  }
}
