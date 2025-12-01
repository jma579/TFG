"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { InteractiveScheduleGrid } from "@/components/solver/interactive-schedule-grid";
import type { Session } from "@/components/solver/schedule-mock";
import {
  useHorariosUploadsStore,
  type HorarioUploadItem,
} from "@/stores/horarios-uploads";
import {
  confirmHorario,
  type HorarioTemporalOut,
} from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";

type RouteParams = { id: string };

type Props = {
  // En Next 15, params llega como Promise en componentes cliente
  params: Promise<RouteParams>;
};

/**
 * Tipo que refleja el JSON real que devuelve /docencia/horarios/extract.
 */
export type HorarioExtraido = {
  titulo: string;
  plan: string;
  periodo: string;
  horarios: HorarioExtraidoBloque[];
  [key: string]: unknown;
};

export type HorarioExtraidoBloque = {
  curso: string;
  periodo: string;
  mencion: string | null;
  pagina: number;
  sesiones: HorarioExtraidoSesion[];
  [key: string]: unknown;
};

export type HorarioExtraidoSesion = {
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

  const horarioTemporal: HorarioExtraido | undefined =
    item?.horarioTemporal as unknown as HorarioExtraido | undefined;

  const [isConfirming, setIsConfirming] = React.useState(false);
  const [confirmError, setConfirmError] = React.useState<string | null>(null);

  const bloques = React.useMemo(
    () => (horarioTemporal?.horarios ?? []) as HorarioExtraidoBloque[],
    [horarioTemporal],
  );

  const [selectedBlockIndex, setSelectedBlockIndex] = React.useState(0);

  // Si cambia el número de bloques, nos aseguramos de que el índice siga siendo válido
  React.useEffect(() => {
    if (selectedBlockIndex >= bloques.length) {
      setSelectedBlockIndex(0);
    }
  }, [bloques.length, selectedBlockIndex]);

  const totalSessions = React.useMemo(() => {
    if (!horarioTemporal) return 0;
    return mapHorarioToSessions(horarioTemporal).length;
  }, [horarioTemporal]);

  const sessions = React.useMemo<Session[]>(() => {
    if (!horarioTemporal || bloques.length === 0) return [];
    const bloque = bloques[selectedBlockIndex];
    if (!bloque) return [];
    return mapBloqueToSessions(bloque, selectedBlockIndex);
  }, [bloques, horarioTemporal, selectedBlockIndex]);

  const hasData = Boolean(horarioTemporal && sessions.length > 0);

  const handleConfirm = async () => {
    if (!horarioTemporal || !item) return;

    setIsConfirming(true);
    setConfirmError(null);

    try {
      await confirmHorario(horarioTemporal as unknown as HorarioTemporalOut);
      useHorariosUploadsStore.getState().confirm(item.id);
      router.push("/app/datos/horarios");
    } catch (error: unknown) {
      const message =
        error instanceof Error
          ? error.message
          : "Error al confirmar el horario.";
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
              No se ha encontrado ningún archivo de horario asociado a esta URL.
              Es posible que la lista de subidas se haya limpiado o que el
              identificador no sea válido.
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
              extracción en memoria. Vuelve a la pantalla de subida de horarios
              y lanza de nuevo el análisis.
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
            ID de subida: <span className="font-mono text-xs">{id}</span>
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Revisa la información extraída del horario antes de confirmarla y
            crear las sesiones en la base de datos.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Button
            variant="outline"
            type="button"
            onClick={() => router.push("/app/uploads/horarios")}
            disabled={isConfirming}
          >
            Volver a subidas
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={isConfirming || !hasData}
          >
            {isConfirming ? "Confirmando…" : "Confirmar horario"}
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
            <span className="font-medium">Título:</span>{" "}
            {horarioTemporal.titulo}
          </p>
          <p>
            <span className="font-medium">Plan:</span>{" "}
            {horarioTemporal.plan}
          </p>
          <p>
            <span className="font-medium">Periodo:</span>{" "}
            {horarioTemporal.periodo}
          </p>
          <p>
            <span className="font-medium">Bloques de horario detectados:</span>{" "}
            {bloques.length}
          </p>
          <p>
            <span className="font-medium">Sesiones detectadas (total):</span>{" "}
            {totalSessions}
          </p>

          {process.env.NODE_ENV === "development" && (
            <pre className="mt-4 max-h-64 overflow-auto rounded bg-muted p-2 text-xs">
              {JSON.stringify(horarioTemporal, null, 2)}
            </pre>
          )}
        </CardContent>
      </Card>

      {bloques.length > 0 && (
        <div className="flex flex-col gap-3 rounded-md border bg-muted/40 px-4 py-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-medium">{horarioTemporal.titulo}</p>
              <p className="text-xs text-muted-foreground">
                Selecciona el curso/mención del que quieres ver el horario.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {bloques.map((bloque, index) => {
                const label = buildBloqueLabel(bloque);
                const isActive = index === selectedBlockIndex;
                return (
                  <Button
                    key={`${bloque.pagina}-${index}`}
                    type="button"
                    size="sm"
                    variant={isActive ? "default" : "outline"}
                    onClick={() => setSelectedBlockIndex(index)}
                  >
                    {label}
                  </Button>
                );
              })}
            </div>
          </div>
        </div>
      )}

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
 * Mapea todos los bloques a sesiones (para contar totales).
 */
function mapHorarioToSessions(horario: HorarioExtraido): Session[] {
  const sessions: Session[] = [];

  const bloques = Array.isArray(horario.horarios)
    ? horario.horarios
    : [];

  bloques.forEach((bloque, bloqueIndex) => {
    const bloqueSessions = mapBloqueToSessions(bloque, bloqueIndex);
    sessions.push(...bloqueSessions);
  });

  return sessions;
}

/**
 * Mapea un bloque concreto a sesiones para el grid.
 */
function mapBloqueToSessions(
  bloque: HorarioExtraidoBloque,
  bloqueIndex: number,
): Session[] {
  const sessions: Session[] = [];

  const sesiones = Array.isArray(bloque.sesiones)
    ? bloque.sesiones
    : [];

  sesiones.forEach((sesion, sesionIndex) => {
    const dayIndex = diaToDayIndex(sesion.dia);
    if (dayIndex < 0) return;

    const session: Session = {
      id: `${bloqueIndex}-${sesionIndex}`,
      courseId: buildCourseIdFromCurso(bloque.curso),
      dayIndex,
      start: normalizeTime(sesion.hora_inicio),
      end: normalizeTime(sesion.hora_fin),
      title: buildSessionTitle(sesion, bloque),
      room: sesion.aula ?? "—",
      teacher: sesion.grupo ? `Grupo ${sesion.grupo}` : "",   // ⬅️ aquí
      color: "blue",
    };

    sessions.push(session);
  });

  return sessions;
}

/**
 * Normaliza "HH:MM:SS" → "HH:MM".
 */
function normalizeTime(value: string): string {
  if (!value) return value;
  const parts = value.split(":");
  if (parts.length >= 2) {
    return `${parts[0].padStart(2, "0")}:${parts[1].padStart(2, "0")}`;
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

  if (d.startsWith("L")) return 0;
  if (d.startsWith("MA")) return 1;
  if (d.startsWith("MI")) return 2;
  if (d.startsWith("J")) return 3;
  if (d.startsWith("V")) return 4;

  return -1;
}

/**
 * Construye el título mostrado en la ficha de la sesión.
 */
function buildSessionTitle(
  s: HorarioExtraidoSesion,
  _bloque: HorarioExtraidoBloque,
): string {
  const asignatura = (s.asignatura ?? "").trim();
  return asignatura || "Sesión";
}

/**
 * Construye un id aproximado de curso a partir del texto de curso.
 */
function buildCourseIdFromCurso(cursoTexto: string): string {
  const n = getCourseNumberFromTexto(cursoTexto);
  if (n === null) return cursoTexto || "DESCONOCIDO";
  return `${n}º`;
}

/**
 * Intenta obtener el número de curso (1-5) a partir de textos del estilo
 * "PRIMER CURSO", "SEGUNDO CURSO" o "1º".
 */
function getCourseNumberFromTexto(cursoTexto: string): number | null {
  if (!cursoTexto) return null;
  const t = cursoTexto.toUpperCase();

  if (t.includes("PRIMER")) return 1;
  if (t.includes("SEGUNDO")) return 2;
  if (t.includes("TERCER")) return 3;
  if (t.includes("CUARTO")) return 4;
  if (t.includes("QUINTO")) return 5;

  const m = t.match(/[1-5]/);
  if (m) return parseInt(m[0], 10);

  return null;
}

/**
 * Devuelve una etiqueta amigable para el botón de selección de bloque.
 * Ejemplo: "1º", "4º - Mención en informática".
 */
function buildBloqueLabel(bloque: HorarioExtraidoBloque): string {
  const n = getCourseNumberFromTexto(bloque.curso);
  const base = n ? `${n}º` : bloque.curso || "Curso";

  if (!bloque.mencion) return base;

  const niceMention = prettifyMention(bloque.mencion);
  return `${base} - ${niceMention}`;
}

/**
 * Limpia el texto de mención (elimina prefix "MENCIÓN EN" y lo pasa a
 * "Mención en …" con capitalización básica).
 */
function prettifyMention(raw: string): string {
  if (!raw) return "Mención";
  let text = raw.trim();

  const m = text.match(/MENCI[ÓO]N\s+EN\s+(.+)/i);
  if (m) {
    text = m[1];
  }

  // Pasamos a minúsculas y luego capitalizamos cada palabra
  text = text.toLowerCase();
  text = text
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");

  return `Mención en ${text}`;
}
