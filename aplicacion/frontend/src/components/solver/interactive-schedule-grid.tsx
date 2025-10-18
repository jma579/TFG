// src/components/solver/interactive-schedule-grid.tsx
'use client';

import type * as React from 'react';
import { ScheduleGrid } from './schedule-grid';

type Props = React.ComponentProps<typeof ScheduleGrid>;

/**
 * Wrapper cliente del ScheduleGrid.
 * No añade lógica adicional (ni event handlers) para evitar
 * pasar funciones desde Server Components.
 */
export function InteractiveScheduleGrid(props: Props) {
  return <ScheduleGrid {...props} />;
}
