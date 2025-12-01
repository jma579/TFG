'use client';

import * as React from 'react';
import { cn } from '@/lib/cn';
import type { Session } from '@/components/solver/schedule-mock';

type Props = {
  sessions: Session[];
  start?: string;   // HH:MM
  end?: string;     // HH:MM
  stepMin?: number; // tamaño de fila en minutos (30 por defecto)
  className?: string;
};

const DAYS = ['L', 'M', 'X', 'J', 'V'];

export function InteractiveScheduleGrid({
  sessions,
  start = '08:30',
  end = '21:30',
  stepMin = 30,
  className,
}: Props) {
  const startMin = timeToMinutes(start);
  const endMin = timeToMinutes(end);
  const totalMin = Math.max(endMin - startMin, stepMin);
  const slotCount = Math.ceil(totalMin / stepMin);

  const timeLabels = React.useMemo(
    () => generateTimeLabels(startMin, slotCount, stepMin),
    [startMin, slotCount, stepMin],
  );

  return (
    <div
      className={cn(
        'overflow-auto rounded-md border bg-background text-xs',
        className,
      )}
    >
      <div
        className="relative grid min-w-[720px]"
        style={{
          gridTemplateColumns: `80px repeat(${DAYS.length}, minmax(0, 1fr))`,
          gridTemplateRows: `32px repeat(${slotCount}, 32px)`,
        }}
      >
        {/* Cabecera de días */}
        <div className="sticky top-0 z-20 flex items-center justify-center border-b bg-muted text-[11px] font-medium">
          Hora
        </div>
        {DAYS.map((d) => (
          <div
            key={d}
            className="sticky top-0 z-20 flex items-center justify-center border-b border-l bg-muted text-[11px] font-medium"
          >
            {d}
          </div>
        ))}

        {/* Columna de horas */}
        {timeLabels.map((label, idx) => (
          <div
            key={`time-${idx}`}
            className="flex items-center justify-end border-b pr-2 text-[11px] text-muted-foreground"
            style={{ gridRow: idx + 2, gridColumn: 1 }}
          >
            {label}
          </div>
        ))}

        {/* Celdas de fondo (rejilla) */}
        {Array.from({ length: slotCount }).map((_, row) =>
          DAYS.map((_, col) => (
            <div
              key={`cell-${row}-${col}`}
              className="border-b border-l bg-background/60"
              style={{ gridRow: row + 2, gridColumn: col + 2 }}
            />
          )),
        )}

        {/* Bloques de sesión */}
        {sessions.map((session) => {
          const col = (session.dayIndex ?? 0) + 2; // 2 = 1 (horas) + 1 (offset)
          const rowStart =
            timeToSlotIndex(session.start, startMin, stepMin) + 2; // +2: cabecera + primera fila
          const rowEnd =
            timeToSlotIndex(session.end, startMin, stepMin) + 2;

          if (col < 2 || col > DAYS.length + 1 || rowEnd <= rowStart) {
            return null;
          }

          return (
            <button
              key={session.id}
              type="button"
              className={cn(
                "m-[2px] flex flex-col items-stretch justify-center overflow-hidden rounded-sm border px-1 py-[2px] text-left text-[11px] shadow-sm ring-1",
                chipColor(session.color),
              )}
              style={{
                gridColumn: col,
                gridRow: `${rowStart} / ${rowEnd}`,
              }}
            >
              {/* 1ª línea: asignatura */}
              <span className="truncate font-medium leading-tight">
                {session.title}
              </span>

              {/* 2ª línea: aula */}
              {session.room && (
                <span className="truncate text-[10px] leading-tight opacity-80">
                  {session.room}
                </span>
              )}

              {/* 3ª línea: grupo (si lo hay) */}
              {session.teacher && (
                <span className="truncate text-[10px] leading-tight opacity-70">
                  {session.teacher}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Helpers                                                                     */
/* -------------------------------------------------------------------------- */

function timeToMinutes(value: string): number {
  if (!value) return 0;
  const [h, m] = value.split(':').map((n) => parseInt(n, 10) || 0);
  return h * 60 + m;
}

function minutesToTimeLabel(totalMin: number): string {
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  const hh = String(h).padStart(2, '0');
  const mm = String(m).padStart(2, '0');
  return `${hh}:${mm}`;
}

function generateTimeLabels(
  startMin: number,
  slotCount: number,
  stepMin: number,
): string[] {
  const labels: string[] = [];
  for (let i = 0; i < slotCount; i += 1) {
    labels.push(minutesToTimeLabel(startMin + i * stepMin));
  }
  return labels;
}

function timeToSlotIndex(
  time: string,
  startMin: number,
  stepMin: number,
): number {
  const tMin = timeToMinutes(time);
  const diff = tMin - startMin;
  return Math.max(0, Math.floor(diff / stepMin));
}

function chipColor(c: Session['color']) {
  switch (c) {
    case 'blue':
      return 'bg-blue-500/15 text-blue-700 ring-blue-500/30';
    case 'green':
      return 'bg-green-500/15 text-green-700 ring-green-500/30';
    case 'orange':
      return 'bg-amber-500/15 text-amber-700 ring-amber-500/30';
    case 'red':
      return 'bg-red-500/15 text-red-700 ring-red-500/30';
    case 'purple':
      return 'bg-violet-500/15 text-violet-700 ring-violet-500/30';
    default:
      return 'bg-primary/10 text-primary ring-primary/30';
  }
}
