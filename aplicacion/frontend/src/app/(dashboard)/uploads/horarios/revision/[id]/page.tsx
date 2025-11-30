'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { InteractiveScheduleGrid } from '@/components/solver/interactive-schedule-grid';
import type { Session } from '@/components/solver/schedule-mock';
import {
  useHorariosUploadsStore,
  type HorarioUploadItem,
} from '@/stores/horarios-uploads';
import {
  confirmHorario,
  type HorarioTemporalOut,
} from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from '@/components/ui/card';

type RouteParams = { id: string };

type Props = {
  // En Next 15, params llega como Promise en componentes cliente
  params: Promise<RouteParams>;
};

/**
 * Tipo que refleja el JSON real que devuelve /docencia/horarios/extract.
 */
type HorarioExtraido = {
  titulo: string;
  plan: string;
  periodo: string;
  horarios: HorarioExtraidoBloque[];
  [key: string]: unknown;
};

type HorarioExtraidoBloque = {
  curso: string;
  periodo: string;
  mencion: string | null;
  pagina: number;
  sesiones: HorarioExtraidoSesion[];
  [key: string]: unknown;
};

type HorarioExtraidoSesion = {
  asignatura: string;
  aula: string;
  dia: string;
  hora_inicio: string;
  hora_fin: string;
  tipo: string;
  grupo: string | null;
  [key: string]: unknown;
};

export default function RevisionHorarioPage({ params }: Props) {
  const { id } = React.use(params);
  const router = useRouter();

  // Selector tipado del store
  const item = useHorariosUploadsStore(
    React.useCallback(
      (state) => state.items.find((it) => it.id === id),
      [id],
    ),
  ) as HorarioUploadItem | undefined;

  // El store tiene horarioTemporal con el resultado de extractHorario.
  const horarioTemporal: HorarioExtraido | undefined =
    item?.horarioTemporal as unknown as HorarioExtraido | undefined;

  const [isConfirming, setIsConfirming] = React.useState(false);
  const [confirmError, setConfirmError] = React.useState<string | null>(null);

  const sessions = React.useMemo<Session[]>(() => {
    if (!horarioTemporal) return [];
    return mapHorarioToSessions(horarioTemporal);
  }, [horarioTemporal]);

  const totalBloques = React.useMemo(
    () =>
      horarioTemporal && Array.isArray(horarioTemporal.horarios)
        ? horarioTemporal.horarios.length
        : 0,
    [horarioTemporal],
  );

  const hasData = Boolean(horarioTemporal && sessions.length > 0);

  const handleConfirm = async () => {
    if (!horarioTemporal || !item) return;

    setIsConfirming(true);
    setConfirmError(null);

    try {
      // Cast explícito para satisfacer el tipo esperado por confirmHorario.
      await confirmHorario(
        horarioTemporal as unknown as HorarioTemporalOut,
      );
      useHorariosUploadsStore.getState().confirm(item.id);
      router.push('/app/datos/horarios');
    } catch (error: unknown) {
      const message =
        error instanceof Error
          ? error.message
          : 'Error al confirmar el horario.';
      setConfirmError(message);
    } finally {
      setIsConfirming(false);
    }
  };

  if (!item) {
    return (
      <div className="mx-auto max-w-4xl p-4">
        <Card>
          <CardHeader>
            <CardTitle>Horario no encontrado</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              No se ha encontrado ningún archivo de horario asociado a esta
              URL. Es posible que la lista de subidas se haya limpiado o que
              el identificador no sea válido.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!horarioTemporal) {
    return (
      <div className="mx-auto max-w-4xl p-4">
        <Card>
          <CardHeader>
            <CardTitle>Horario sin datos de extracción</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              El archivo se ha registrado, pero no se dispone de datos de
              extracción en memoria. Vuelve a la pantalla de subida de
              horarios y lanza de nuevo el análisis.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Revisión de horario
          </h1>
          <p className="text-sm text-muted-foreground">
            ID de subida:{' '}
            <span className="font-mono text-xs">{id}</span>
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Revisa la información extraída del horario antes de confirmarla
            y crear las sesiones en la base de datos.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Button
            variant="outline"
            type="button"
            onClick={() => router.push('/app/uploads/horarios')}
            disabled={isConfirming}
          >
            Volver a subidas
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={isConfirming || !hasData}
          >
            {isConfirming ? 'Confirmando…' : 'Confirmar horario'}
          </Button>
          {confirmError && (
            <p className="max-w-xs text-right text-xs text-destructive">
              {confirmError}
            </p>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Resumen del horario</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          <p>
            <span className="font-medium">Título:</span>{' '}
            {horarioTemporal.titulo}
          </p>
          <p>
            <span className="font-medium">Plan:</span>{' '}
            {horarioTemporal.plan}
          </p>
          <p>
            <span className="font-medium">Periodo:</span>{' '}
            {horarioTemporal.periodo}
          </p>
          <p>
            <span className="font-medium">Bloques de horario detectados:</span>{' '}
            {totalBloques}
          </p>
          <p>
            <span className="font-medium">Sesiones detectadas:</span>{' '}
            {sessions.length}
          </p>

          {process.env.NODE_ENV === 'development' && (
            <pre className="mt-4 max-h-64 overflow-auto rounded bg-muted p-2 text-xs">
              {JSON.stringify(horarioTemporal, null, 2)}
            </pre>
          )}
        </CardContent>
      </Card>

      {hasData ? (
        <InteractiveScheduleGrid
          start="08:30"
          end="21:30"
          stepMin={30}
          sessions={sessions}
        />
      ) : (
        <div className="rounded-md border bg-muted/20 p-6 text-sm text-muted-foreground">
          No hay datos de horario para mostrar todavía.
        </div>
      )}
    </div>
  );
}

/**
 * Mapea el JSON devuelto por /horarios/extract (HorarioExtraido)
 * a la estructura Session usada por el grid.
 */
function mapHorarioToSessions(horario: HorarioExtraido): Session[] {
  const sessions: Session[] = [];

  const bloques = Array.isArray(horario.horarios)
    ? horario.horarios
    : [];

  bloques.forEach((bloque, bloqueIndex) => {
    const sesiones = Array.isArray(bloque.sesiones)
      ? bloque.sesiones
      : [];

    sesiones.forEach((sesion, sesionIndex) => {
      const dayIndex = diaToDayIndex(sesion.dia);
      if (dayIndex < 0) return;

      const session: Session = {
        id: `${bloqueIndex}-${sesionIndex}`,
        courseId: sesion.asignatura || 'SIN_ASIGNATURA',
        dayIndex,
        start: normalizeTime(sesion.hora_inicio),
        end: normalizeTime(sesion.hora_fin),
        title: buildSessionTitle(sesion, bloque),
        room: sesion.aula ?? '—',
        teacher: 'Profesor no asignado',
        color: 'blue',
      };

      sessions.push(session);
    });
  });

  return sessions;
}

/**
 * Normaliza "HH:MM:SS" → "HH:MM".
 */
function normalizeTime(value: string): string {
  if (!value) return value;
  const parts = value.split(':');
  if (parts.length >= 2) {
    return `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}`;
  }
  return value;
}

/**
 * Día backend → índice 0-4 (L–V) para el grid.
 */
function diaToDayIndex(dia: string): number {
  const d = dia.trim().toUpperCase();

  const map: Record<string, number> = {
    LUNES: 0,
    L: 0,
    MARTES: 1,
    M: 1,
    MIÉRCOLES: 2,
    MIERCOLES: 2,
    X: 2,
    JUEVES: 3,
    J: 3,
    VIERNES: 4,
    V: 4,
  };

  if (d in map) return map[d];

  if (d.startsWith('L')) return 0;
  if (d.startsWith('MA')) return 1;
  if (d.startsWith('MI')) return 2;
  if (d.startsWith('J')) return 3;
  if (d.startsWith('V')) return 4;

  return -1;
}

/**
 * Construye el título mostrado en la ficha de la sesión.
 */
function buildSessionTitle(
  s: HorarioExtraidoSesion,
  bloque: HorarioExtraidoBloque,
): string {
  const parts: string[] = [];

  if (s.asignatura) parts.push(s.asignatura);
  if (s.grupo) parts.push(`(${s.grupo})`);
  if (s.tipo) parts.push(`[${s.tipo}]`);
  if (bloque.curso) parts.push(`Curso ${bloque.curso}`);

  return parts.length ? parts.join(' ') : 'Sesión';
}
