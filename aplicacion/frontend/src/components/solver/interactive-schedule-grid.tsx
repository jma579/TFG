'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import type { Session } from '@/components/solver/schedule-mock';

type Props = {
  sessions: Session[];
  start?: string; // HH:MM
  end?: string; // HH:MM
  stepMin?: number; // 30 por defecto
  className?: string;
  onSessionClick?: (session: Session) => void;
  onSessionMove?: (session: Session, newDayIndex: number, newStartTime: string) => void;
};

const DAYS = ['L', 'M', 'X', 'J', 'V'];

type LayoutInfo = {
  lane: number;
  lanes: number;
};

export function InteractiveScheduleGrid({
  sessions,
  start = '08:30',
  end = '21:30',
  stepMin = 30,
  className,
  onSessionClick,
  onSessionMove,
}: Props) {
  const startMin = timeToMinutes(start);
  const endMin = timeToMinutes(end);
  const totalMin = Math.max(endMin - startMin, stepMin);
  const slotCount = Math.ceil(totalMin / stepMin);

  // Estado para controlar si estamos arrastrando algo globalmente
  const [isDragging, setIsDragging] = React.useState(false);

  const timeLabels = React.useMemo(
    () => generateTimeLabels(startMin, slotCount, stepMin),
    [startMin, slotCount, stepMin],
  );

  const layoutById = React.useMemo(
    () => buildLayoutById(sessions),
    [sessions],
  );

  // --- Lógica Drag & Drop mejorada ---

  const handleDragStart = (e: React.DragEvent, session: Session) => {
    e.dataTransfer.setData('sessionId', String(session.id));
    e.dataTransfer.effectAllowed = 'move';

    // Cálculo del offset (dónde agarramos la caja)
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    const offsetY = e.clientY - rect.top;
    const SLOT_HEIGHT = 32; 
    const offsetSlots = Math.floor(offsetY / SLOT_HEIGHT);
    e.dataTransfer.setData('offsetSlots', String(offsetSlots));

    // Activamos el modo dragging con un micro-tick de retraso para que 
    // el navegador tenga tiempo de generar la "imagen fantasma" del drag
    // antes de que le quitemos los pointer-events al elemento original.
    setTimeout(() => setIsDragging(true), 0);
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, dayIndex: number, dropSlotIndex: number) => {
    e.preventDefault();
    // Importante: reseteamos estado aquí también por seguridad
    setIsDragging(false);

    const sessionId = e.dataTransfer.getData('sessionId');
    const offsetSlotsStr = e.dataTransfer.getData('offsetSlots');
    
    if (!sessionId) return;

    const session = sessions.find((s) => String(s.id) === sessionId);
    if (!session) return;

    const offsetSlots = parseInt(offsetSlotsStr || '0', 10);
    
    // Ajustamos el slot de inicio restando el offset
    let newStartSlot = dropSlotIndex - offsetSlots;
    if (newStartSlot < 0) newStartSlot = 0;

    const minutesFromStart = newStartSlot * stepMin;
    const newStartMin = startMin + minutesFromStart;
    const newStartTime = minutesToTimeLabel(newStartMin);

    onSessionMove?.(session, dayIndex, newStartTime);
  };

  return (
    <div
      className={cn(
        'overflow-auto rounded-md border bg-background text-xs select-none',
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

        {/* Celdas de fondo (Drop Zones) */}
        {Array.from({ length: slotCount }).map((_, row) =>
          DAYS.map((_, dayIndex) => (
            <div
              key={`cell-${row}-${dayIndex}`}
              className="border-b border-l bg-background/60 transition-colors hover:bg-muted/50"
              style={{
                gridRow: row + 2,
                gridColumn: dayIndex + 2,
              }}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, dayIndex, row)}
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
            <div
              key={session.id}
              draggable={!!onSessionMove}
              onDragStart={(e) => handleDragStart(e, session)}
              onDragEnd={handleDragEnd} // Limpiamos estado al terminar
              className={cn(
                'my-[2px] flex flex-col items-stretch justify-center overflow-hidden rounded-sm border px-1 py-[2px] text-left text-[11px] shadow-sm ring-1 transition-all',
                chipColor(session.color),
                onSessionMove ? 'cursor-grab active:cursor-grabbing' : '',
                // TRUCO CLAVE: Si estamos arrastrando, quitamos eventos de puntero a TODAS las sesiones
                // Esto permite que el evento 'drop' atraviese las sesiones y llegue a la celda de fondo.
                isDragging ? 'pointer-events-none opacity-80 z-0' : 'hover:z-30 hover:shadow-md cursor-pointer'
              )}
              style={{
                gridRow: `${rowStart} / ${rowEnd}`,
                gridColumn: dayIndex + 2,
                width: `calc(${widthPercent}% - 4px)`,
                marginLeft: `calc(${leftPercent}% + 2px)`,
                // Si no arrastramos, usamos z-index calculado. Si arrastramos, z-0 para no molestar.
                zIndex: isDragging ? 0 : 10 + layout.lane,
              }}
              onClick={(e) => {
                e.stopPropagation();
                if (!isDragging) onSessionClick?.(session);
              }}
            >
              <span className="truncate font-medium leading-tight">
                {session.title}
              </span>
              {session.room && (
                <span className="truncate text-[10px] leading-tight opacity-80">
                  {session.room}
                </span>
              )}
              {session.teacher && (
                <span className="truncate text-[10px] leading-tight opacity-70">
                  {session.teacher}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

function buildLayoutById(sessions: Session[]): Map<string, LayoutInfo> {
  const result = new Map<string, LayoutInfo>();
  const byDay = new Map<number, { session: Session; start: number; end: number }[]>();

  sessions.forEach((s) => {
    const day = s.dayIndex ?? 0;
    const start = timeToMinutes(s.start);
    const end = timeToMinutes(s.end);
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day)!.push({ session: s, start, end });
  });

  byDay.forEach((list) => {
    const sorted = [...list].sort((a, b) => a.start - b.start);
    type Item = (typeof sorted)[number];

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
        currentGroup.push(item);
        currentEnd = Math.max(currentEnd, item.end);
      } else {
        groups.push(currentGroup);
        currentGroup = [item];
        currentEnd = item.end;
      }
    }
    if (currentGroup.length > 0) groups.push(currentGroup);

    groups.forEach((group) => {
      const laneEnds: number[] = [];
      const laneOfItem = new Map<Item, number>();

      for (const item of group) {
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

function generateTimeLabels(startMin: number, slotCount: number, stepMin: number): string[] {
  const labels: string[] = [];
  for (let i = 0; i < slotCount; i += 1) {
    labels.push(minutesToTimeLabel(startMin + i * stepMin));
  }
  return labels;
}

function timeToSlotIndex(time: string, startMin: number, stepMin: number): number {
  const tMin = timeToMinutes(time);
  const diff = tMin - startMin;
  return Math.max(0, Math.floor(diff / stepMin));
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