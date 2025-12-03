"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { InteractiveScheduleGrid } from "@/components/solver/interactive-schedule-grid";
import type { Session } from "@/components/solver/schedule-mock";
import {
  useHorariosUploadsStore,
  type HorarioUploadItem,
} from "@/stores/horarios-uploads";
import { confirmHorario, type HorarioTemporalOut } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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

// Estado local del formulario de edición/creación de una sesión
interface SesionFormState {
  asignatura: string;
  aula: string;
  dia: string;
  hora_inicio: string;
  hora_fin: string;
  tipo: string;
  grupo: string;
}

const DEFAULT_SESSION_FORM: SesionFormState = {
  asignatura: "",
  aula: "",
  dia: "LUNES",
  hora_inicio: "09:30",
  hora_fin: "10:30",
  tipo: "TEORÍA",
  grupo: "",
};

const TIPO_OPCIONES = [
  "TEORÍA",
  "PRÁCTICAS DE AULA",
  "PRÁCTICAS DE LABORATORIO",
] as const;

const DIAS_SEMANA = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES"] as const;

/* -------------------------------------------------------------------------- */
/* Componente principal                                                       */
/* -------------------------------------------------------------------------- */

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

  // Copia editable local del horario (para no mutar el store directamente)
  const [draftHorario, setDraftHorario] = React.useState<HorarioExtraido | null>(
    null,
  );

  React.useEffect(() => {
    if (horarioTemporal) {
      // Clonamos profundo para evitar mutaciones sobre el objeto del store
      const cloned = JSON.parse(
        JSON.stringify(horarioTemporal),
      ) as HorarioExtraido;
      setDraftHorario(cloned);
    }
  }, [horarioTemporal]);

  const horario = draftHorario ?? horarioTemporal;

  const [isConfirming, setIsConfirming] = React.useState(false);
  const [confirmError, setConfirmError] = React.useState<string | null>(null);

  const bloques = React.useMemo(
    () => (horario?.horarios ?? []) as HorarioExtraidoBloque[],
    [horario],
  );

  const [selectedBlockIndex, setSelectedBlockIndex] = React.useState(0);

  // Si cambia el número de bloques, nos aseguramos de que el índice siga siendo válido
  React.useEffect(() => {
    if (selectedBlockIndex >= bloques.length) {
      setSelectedBlockIndex(0);
    }
  }, [bloques.length, selectedBlockIndex]);

  const totalSessions = React.useMemo(() => {
    if (!horario) return 0;
    return mapHorarioToSessions(horario).length;
  }, [horario]);

  const sessions = React.useMemo<Session[]>(() => {
    if (!horario || bloques.length === 0) return [];
    const bloque = bloques[selectedBlockIndex];
    if (!bloque) return [];
    return mapBloqueToSessions(bloque, selectedBlockIndex);
  }, [bloques, horario, selectedBlockIndex]);

  // Ahora consideramos que hay datos si existe al menos un bloque,
  // aunque ese bloque tenga 0 sesiones (tabla vacía).
  const hasData = Boolean(horario && bloques.length > 0);

  /* ------------------------------ Edición sesión ------------------------------ */

  const [editingLocation, setEditingLocation] = React.useState<{
    blockIndex: number;
    sessionIndex: number;
  } | null>(null);

  const [editingForm, setEditingForm] = React.useState<SesionFormState | null>(
    null,
  );

  const openEditSesion = (session: Session) => {
    if (!horario) return;

    const [blockStr, sesStr] = String(session.id).split("-");
    const blockIndex = Number(blockStr);
    const sessionIndex = Number(sesStr);
    if (Number.isNaN(blockIndex) || Number.isNaN(sessionIndex)) return;

    const bloque = horario.horarios[blockIndex];
    const sesion = bloque?.sesiones?.[sessionIndex];
    if (!bloque || !sesion) return;

    setEditingLocation({ blockIndex, sessionIndex });
    setEditingForm({
      asignatura: sesion.asignatura ?? "",
      aula: sesion.aula ?? "",
      dia: sesion.dia ?? "",
      hora_inicio: sesion.hora_inicio ?? "",
      hora_fin: sesion.hora_fin ?? "",
      tipo: sesion.tipo ?? "TEORÍA",
      grupo: sesion.grupo ?? "",
    });
  };

  const closeEditSesion = () => {
    setEditingLocation(null);
    setEditingForm(null);
  };

  const handleEditFieldChange = <K extends keyof SesionFormState>(
    field: K,
    value: SesionFormState[K],
  ) => {
    setEditingForm((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  const handleSaveSesion = () => {
    if (!editingLocation || !editingForm) return;

    setDraftHorario((prev) => {
      const source = prev ?? horario;
      if (!source) return prev;

      const cloned = JSON.parse(JSON.stringify(source)) as HorarioExtraido;
      const { blockIndex, sessionIndex } = editingLocation;
      const bloque = cloned.horarios[blockIndex];
      const sesion = bloque?.sesiones?.[sessionIndex];
      if (!bloque || !sesion) return prev;

      sesion.asignatura = editingForm.asignatura;
      sesion.aula = editingForm.aula;
      sesion.dia = editingForm.dia;
      sesion.hora_inicio = editingForm.hora_inicio;
      sesion.hora_fin = editingForm.hora_fin;
      sesion.tipo = editingForm.tipo;
      sesion.grupo = editingForm.grupo || null;

      return cloned;
    });

    closeEditSesion();
  };

  /* ------------------------- Creación sesión / horario ------------------------ */

  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [createTab, setCreateTab] = React.useState<"session" | "block">(
    "session",
  );
  const [createSessionForm, setCreateSessionForm] =
    React.useState<SesionFormState>(DEFAULT_SESSION_FORM);
  const [newBlockForm, setNewBlockForm] = React.useState<{
    curso: string;
    mencion: string;
  }>({ curso: "", mencion: "" });

  const canCreateSession = bloques.length > 0;
  const selectedBloque = bloques[selectedBlockIndex];

  const openCreateDialog = () => {
    const initialTab: "session" | "block" = canCreateSession ? "session" : "block";
    setCreateTab(initialTab);
    setCreateSessionForm(DEFAULT_SESSION_FORM);
    setNewBlockForm({ curso: "", mencion: "" });
    setIsCreateOpen(true);
  };

  const closeCreateDialog = () => {
    setIsCreateOpen(false);
  };

  const handleCreateFieldChange = <K extends keyof SesionFormState>(
    field: K,
    value: SesionFormState[K],
  ) => {
    setCreateSessionForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateSession = () => {
    if (!canCreateSession) return;

    setDraftHorario((prev) => {
      const source = prev ?? horario;
      if (!source) return prev;

      const cloned = JSON.parse(JSON.stringify(source)) as HorarioExtraido;

      if (
        selectedBlockIndex < 0 ||
        selectedBlockIndex >= cloned.horarios.length
      ) {
        return prev;
      }

      const bloque = cloned.horarios[selectedBlockIndex];
      if (!Array.isArray(bloque.sesiones)) {
        bloque.sesiones = [];
      }

      const nuevaSesion: HorarioExtraidoSesion = {
        asignatura: createSessionForm.asignatura,
        aula: createSessionForm.aula,
        dia: createSessionForm.dia,
        hora_inicio: createSessionForm.hora_inicio,
        hora_fin: createSessionForm.hora_fin,
        tipo: createSessionForm.tipo,
        grupo: createSessionForm.grupo || null,
      };

      bloque.sesiones.push(nuevaSesion);

      return cloned;
    });

    closeCreateDialog();
  };

  const handleCreateBlock = () => {
    const curso = newBlockForm.curso.trim();
    const mencionText = newBlockForm.mencion.trim();
    if (!curso) return;

    const newIndex = bloques.length;

    setDraftHorario((prev) => {
      const source = prev ?? horario;
      if (!source) return prev;

      const cloned = JSON.parse(JSON.stringify(source)) as HorarioExtraido;
      if (!Array.isArray(cloned.horarios)) {
        cloned.horarios = [];
      }

      const nuevoBloque: HorarioExtraidoBloque = {
        curso,
        periodo: cloned.periodo,
        mencion: mencionText || null,
        pagina: cloned.horarios.length,
        sesiones: [],
      };

      cloned.horarios.push(nuevoBloque);

      return cloned;
    });

    setSelectedBlockIndex(newIndex);
    closeCreateDialog();
  };

  /* --------------------------- Confirmación horario --------------------------- */

  const handleConfirm = async () => {
    if (!horario || !item) return;

    setIsConfirming(true);
    setConfirmError(null);

    try {
      await confirmHorario(horario as unknown as HorarioTemporalOut);
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

  /* --------------------------------- Render --------------------------------- */

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

  if (!horario) {
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

  const editingBloque =
    editingLocation && horario.horarios[editingLocation.blockIndex]
      ? horario.horarios[editingLocation.blockIndex]
      : null;

  const isEditOpen = Boolean(editingLocation && editingForm && editingBloque);

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
            <span className="font-medium">Título:</span> {horario.titulo}
          </p>
          <p>
            <span className="font-medium">Plan:</span> {horario.plan}
          </p>
          <p>
            <span className="font-medium">Periodo:</span> {horario.periodo}
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
              {JSON.stringify(horario, null, 2)}
            </pre>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between gap-4">
        {bloques.length > 0 ? (
          <div className="flex-1 rounded-md border bg-muted/40 px-4 py-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium">{horario.titulo}</p>
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
        ) : (
          // Cuando aún no hay bloques, dejamos espacio a la izquierda
          <div className="flex-1 rounded-md border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
            Crea un nuevo horario para comenzar a añadir sesiones.
          </div>
        )}

        <Button
          type="button"
          onClick={openCreateDialog}
          aria-label="Añadir sesión u horario"
          className="h-9 w-9 rounded-md bg-black text-white hover:bg-black/90"
        >
          +
        </Button>
      </div>

      {hasData ? (
        <InteractiveScheduleGrid
          start="08:30"
          end="21:30"
          stepMin={30}
          sessions={sessions}
          onSessionClick={openEditSesion}
        />
      ) : (
        <div className="rounded-md border bg-muted/20 p-6 text-sm text-muted-foreground">
          No hay datos de horario para mostrar todavía.
        </div>
      )}

      {/* Diálogo de edición de sesión */}
      <Dialog
        open={isEditOpen}
        onOpenChange={(open) => !open && closeEditSesion()}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Editar sesión
              {editingBloque ? ` · ${editingBloque.curso}` : ""}
            </DialogTitle>
          </DialogHeader>

          {editingForm && (
            <SessionFormFields
              form={editingForm}
              onChange={handleEditFieldChange}
            />
          )}

          <DialogFooter className="mt-4">
            <Button variant="outline" type="button" onClick={closeEditSesion}>
              Cancelar
            </Button>
            <Button type="button" onClick={handleSaveSesion}>
              Guardar cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo de creación (nueva sesión / nuevo horario) */}
      <Dialog
        open={isCreateOpen}
        onOpenChange={(open) => !open && closeCreateDialog()}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Crear elemento</DialogTitle>
          </DialogHeader>

          {/* Pestañas como dos botones negros */}
          <div className="mb-4 flex gap-2 text-xs">
            <button
              type="button"
              className={`h-8 rounded-md px-3 ${
                createTab === "session"
                  ? "bg-black text-white"
                  : "bg-black/60 text-white"
              } ${!canCreateSession ? "cursor-not-allowed opacity-50" : ""}`}
              onClick={() => canCreateSession && setCreateTab("session")}
            >
              Nueva sesión
            </button>
            <button
              type="button"
              className={`h-8 rounded-md px-3 ${
                createTab === "block"
                  ? "bg-black text-white"
                  : "bg-black/60 text-white"
              }`}
              onClick={() => setCreateTab("block")}
            >
              Nuevo horario
            </button>
          </div>

          {createTab === "session" && (
            <>
              {!canCreateSession ? (
                <p className="text-sm text-muted-foreground">
                  Primero crea un horario (curso/mención) antes de añadir
                  sesiones.
                </p>
              ) : (
                <>
                  {selectedBloque && (
                    <p className="mb-2 text-xs text-muted-foreground">
                      La sesión se añadirá a:{" "}
                      <span className="font-medium">
                        {buildBloqueLabel(selectedBloque)}
                      </span>
                    </p>
                  )}
                  <SessionFormFields
                    form={createSessionForm}
                    onChange={handleCreateFieldChange}
                  />
                </>
              )}
            </>
          )}

          {createTab === "block" && (
            <div className="space-y-3 py-2 text-sm">
              <div className="grid gap-2">
                <Label htmlFor="nuevo-curso">Curso</Label>
                <Input
                  id="nuevo-curso"
                  value={newBlockForm.curso}
                  onChange={(e) =>
                    setNewBlockForm((prev) => ({
                      ...prev,
                      curso: e.target.value,
                    }))
                  }
                  placeholder="1º, PRIMER CURSO, 4º, ..."
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="nueva-mencion">Mención (opcional)</Label>
                <Input
                  id="nueva-mencion"
                  value={newBlockForm.mencion}
                  onChange={(e) =>
                    setNewBlockForm((prev) => ({
                      ...prev,
                      mencion: e.target.value,
                    }))
                  }
                  placeholder="Mención en Computación, ..."
                />
              </div>
            </div>
          )}

          <DialogFooter className="mt-4">
            <Button variant="outline" type="button" onClick={closeCreateDialog}>
              Cancelar
            </Button>
            {createTab === "session" ? (
              <Button
                type="button"
                onClick={handleCreateSession}
                disabled={!canCreateSession}
              >
                Crear sesión
              </Button>
            ) : (
              <Button
                type="button"
                onClick={handleCreateBlock}
                disabled={!newBlockForm.curso.trim()}
              >
                Crear horario
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Formulario reutilizable de sesión                                          */
/* -------------------------------------------------------------------------- */

type SessionFormFieldsProps = {
  form: SesionFormState;
  onChange: <K extends keyof SesionFormState>(
    field: K,
    value: SesionFormState[K],
  ) => void;
};

function SessionFormFields({ form, onChange }: SessionFormFieldsProps) {
  return (
    <div className="space-y-3 py-2 text-sm">
      <div className="grid gap-2">
        <Label htmlFor="asignatura">Asignatura</Label>
        <Input
          id="asignatura"
          value={form.asignatura}
          onChange={(e) => onChange("asignatura", e.target.value)}
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="aula">Aula</Label>
        <Input
          id="aula"
          value={form.aula}
          onChange={(e) => onChange("aula", e.target.value)}
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="dia">Día</Label>
        <select
          id="dia"
          className="h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          value={form.dia}
          onChange={(e) => onChange("dia", e.target.value)}
        >
          {DIAS_SEMANA.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="grid gap-2">
          <Label htmlFor="hora_inicio">Hora inicio</Label>
          <Input
            id="hora_inicio"
            type="time"
            value={form.hora_inicio}
            onChange={(e) => onChange("hora_inicio", e.target.value)}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="hora_fin">Hora fin</Label>
          <Input
            id="hora_fin"
            type="time"
            value={form.hora_fin}
            onChange={(e) => onChange("hora_fin", e.target.value)}
          />
        </div>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="tipo">Tipo</Label>
        <select
          id="tipo"
          className="h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          value={form.tipo}
          onChange={(e) => onChange("tipo", e.target.value)}
        >
          {TIPO_OPCIONES.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="grupo">Grupo</Label>
        <Input
          id="grupo"
          value={form.grupo}
          onChange={(e) => onChange("grupo", e.target.value)}
          placeholder="PL1, PL2, ... (opcional)"
        />
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Helpers de mapeo y etiquetas                                               */
/* -------------------------------------------------------------------------- */

/**
 * Mapea todos los bloques a sesiones (para contar totales).
 */
function mapHorarioToSessions(horario: HorarioExtraido): Session[] {
  const sessions: Session[] = [];

  const bloques = Array.isArray(horario.horarios) ? horario.horarios : [];

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

  const sesiones = Array.isArray(bloque.sesiones) ? bloque.sesiones : [];

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
      teacher: sesion.grupo ? `Grupo ${sesion.grupo}` : "",
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
 * Título del bloque: sólo el nombre de la asignatura.
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
  text = text
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");

  return `Mención en ${text}`;
}
