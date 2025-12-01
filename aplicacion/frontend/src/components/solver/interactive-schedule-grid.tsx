'use client';

import * as React from 'react';
import { cn } from '@/lib/cn';
import type { Session } from '@/components/solver/schedule-mock';

type Props = {
  sessions: Session[];
  start?: string; // HH:MM
  end?: string; // HH:MM
  stepMin?: number; // tamaño de fila en minutos (30 por defecto)
  className?: string;
  onSessionClick?: (session: Session) => void;
};

const DAYS = ['L', 'M', 'X', 'J', 'V'];

type LayoutInfo = {
  lane: number;  // índice dentro del grupo solapado
  lanes: number; // nº total de sesiones solapadas en ese grupo
};

export function InteractiveScheduleGrid({
  sessions,
  start = '08:30',
  end = '21:30',
  stepMin = 30,
  className,
  onSessionClick,
}: Props) {
  const startMin = timeToMinutes(start);
  const endMin = timeToMinutes(end);
  const totalMin = Math.max(endMin - startMin, stepMin);
  const slotCount = Math.ceil(totalMin / stepMin);

  const timeLabels = React.useMemo(
    () => generateTimeLabels(startMin, slotCount, stepMin),
    [startMin, slotCount, stepMin],
  );

  // Cálculo de lanes dinámicos por día
  const layoutById = React.useMemo(
    () => buildLayoutById(sessions),
    [sessions],
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
        {/* Cabecera hora */}
        <div className="sticky top-0 z-20 flex items-center justify-center border-b bg-muted text-[11px] font-medium">
          Hora
        </div>

        {/* Cabeceras de días */}
        {DAYS.map((d, index) => (
          <div
            key={d}
            className="sticky top-0 z-20 flex items-center justify-center border-b border-l bg-muted text-[11px] font-medium"
            style={{ gridColumn: index + 2 }}
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

        {/* Celdas de fondo */}
        {Array.from({ length: slotCount }).map((_, row) =>
          DAYS.map((_, dayIndex) => (
            <div
              key={`cell-${row}-${dayIndex}`}
              className="border-b border-l bg-background/60"
              style={{
                gridRow: row + 2,
                gridColumn: dayIndex + 2,
              }}
            />
          )),
        )}

        {/* Sesiones */}
        {sessions.map((session) => {
          const dayIndex = session.dayIndex ?? 0;
          if (dayIndex < 0 || dayIndex >= DAYS.length) return null;

          const rowStart =
            timeToSlotIndex(session.start, startMin, stepMin) + 2;
          const rowEnd =
            timeToSlotIndex(session.end, startMin, stepMin) + 2;

          if (rowEnd <= rowStart) return null;

          const layout =
            layoutById.get(String(session.id)) ??
            ({ lane: 0, lanes: 1 } as LayoutInfo);

          const widthPercent = 100 / layout.lanes;
          const leftPercent = layout.lane * widthPercent;

          return (
            <button
              key={session.id}
              type="button"
              className={cn(
                'my-[2px] flex flex-col items-stretch justify-center overflow-hidden rounded-sm border px-1 py-[2px] text-left text-[11px] shadow-sm ring-1',
                chipColor(session.color),
              )}
              style={{
                gridRow: `${rowStart} / ${rowEnd}`,
                gridColumn: dayIndex + 2,
                width: `calc(${widthPercent}% - 4px)`,
                marginLeft: `calc(${leftPercent}% + 2px)`,
              }}
              onClick={() => onSessionClick?.(session)}
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

              {/* 3ª línea: grupo (teacher = texto de grupo) */}
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
/* Cálculo de solapamientos y lanes dinámicos                                 */
/* -------------------------------------------------------------------------- */

function buildLayoutById(sessions: Session[]): Map<string, LayoutInfo> {
  const result = new Map<string, LayoutInfo>();

  // Agrupamos sesiones por día
  const byDay = new Map<
    number,
    { session: Session; start: number; end: number }[]
  >();

  sessions.forEach((s) => {
    const day = s.dayIndex ?? 0;
    const start = timeToMinutes(s.start);
    const end = timeToMinutes(s.end);
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day)!.push({ session: s, start, end });
  });

  byDay.forEach((list) => {
    // Ordenamos por inicio
    const sorted = [...list].sort((a, b) => a.start - b.start);

    type Item = (typeof sorted)[number];

    // 1) Dividimos en grupos conectados por solapamiento
    const groups: Item[][] = [];
    let currentGroup: Item[] = [];
    let currentEnd = -Infinity;

    for (const item of sorted) {
      if (currentGroup.length === 0) {
        currentGroup.push(item);
        currentEnd = item.end;
        continue;
      }

      if (item.start < currentEnd) {
        // Sigue solapando con el grupo actual
        currentGroup.push(item);
        currentEnd = Math.max(currentEnd, item.end);
      } else {
        // El nuevo ya no solapa con el grupo anterior → cerramos grupo
        groups.push(currentGroup);
        currentGroup = [item];
        currentEnd = item.end;
      }
    }
    if (currentGroup.length > 0) groups.push(currentGroup);

    // 2) Dentro de cada grupo asignamos lane (modelo Google Calendar)
    groups.forEach((group) => {
      const laneEnds: number[] = []; // fin de la última sesión de cada lane
      const laneOfItem = new Map<Item, number>();

      for (const item of group) {
        // buscamos un lane libre (su última sesión termina antes que empiece este)
        let laneIndex = laneEnds.findIndex((end) => item.start >= end);
        if (laneIndex === -1) {
          laneIndex = laneEnds.length;
          laneEnds.push(item.end);
        } else {
          laneEnds[laneIndex] = item.end;
        }
        laneOfItem.set(item, laneIndex);
      }

      const lanesCount = laneEnds.length || 1;

      for (const item of group) {
        const lane = laneOfItem.get(item) ?? 0;
        result.set(String(item.session.id), { lane, lanes: lanesCount });
      }
    });
  });

  return result;
}

/* -------------------------------------------------------------------------- */
/* Helpers de tiempo y estilos                                                */
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
