'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Pencil } from 'lucide-react'; // Añadido Pencil
import { InteractiveScheduleGrid } from '@/components/solver/interactive-schedule-grid';
import type { Session } from '@/components/solver/schedule-mock';
import {
  useHorariosUploadsStore,
  type HorarioUploadItem,
} from '@/stores/horarios-uploads';
import { confirmHorario, type HorarioTemporalOut } from '@/lib/api/docencia/horarios';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';

type RouteParams = { id: string };

type Props = {
  params: Promise<RouteParams>;
};

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
  asignatura: '',
  aula: '',
  dia: 'LUNES',
  hora_inicio: '09:30',
  hora_fin: '10:30',
  tipo: 'TEORÍA',
  grupo: '',
};

const TIPO_OPCIONES = [
  'TEORÍA',
  'PRÁCTICAS DE AULA',
  'PRÁCTICAS DE LABORATORIO',
] as const;

const DIAS_SEMANA = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES'] as const;

export default function RevisionHorarioPage({ params }: Props) {
  const { id } = React.use(params);
  const router = useRouter();
  const { toast } = useToast();

  const item = useHorariosUploadsStore(
    React.useCallback(
      (state) => state.items.find((it) => it.id === id),
      [id]
    )
  ) as HorarioUploadItem | undefined;

  const horarioTemporal: HorarioExtraido | undefined =
    item?.horarioTemporal as unknown as HorarioExtraido | undefined;

  const [draftHorario, setDraftHorario] = React.useState<HorarioExtraido | null>(
    null
  );

  React.useEffect(() => {
    if (horarioTemporal) {
      const cloned = JSON.parse(
        JSON.stringify(horarioTemporal)
      ) as HorarioExtraido;
      setDraftHorario(cloned);
    }
  }, [horarioTemporal]);

  const horario = draftHorario ?? horarioTemporal;

  const [isConfirming, setIsConfirming] = React.useState(false);
  const [confirmError, setConfirmError] = React.useState<string | null>(null);

  const bloques = React.useMemo(
    () => (horario?.horarios ?? []) as HorarioExtraidoBloque[],
    [horario]
  );

  const [selectedBlockIndex, setSelectedBlockIndex] = React.useState(0);

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

  const hasData = Boolean(horario && bloques.length > 0);

  /* ------------------------------ NUEVO: Edición Info General ------------------------------ */
  
  const [isEditInfoOpen, setIsEditInfoOpen] = React.useState(false);
  const [infoForm, setInfoForm] = React.useState({ plan: '', periodo: '' });

  const openEditInfo = () => {
    if (!horario) return;
    // Rellenamos el formulario con los datos actuales o calculados
    setInfoForm({
      plan: horario.plan || horario.titulo?.split(' - ')[0] || '',
      periodo: horario.periodo || horario.titulo?.split(' - ')[1] || '',
    });
    setIsEditInfoOpen(true);
  };

  const handleSaveInfo = () => {
    setDraftHorario((prev) => {
      if (!prev) return prev;
      const cloned = { ...prev };
      cloned.plan = infoForm.plan;
      cloned.periodo = infoForm.periodo;
      // Actualizamos el título también para mantener coherencia
      cloned.titulo = `${infoForm.plan} - ${infoForm.periodo}`;
      return cloned;
    });
    setIsEditInfoOpen(false);
    toast({ title: 'Información actualizada' });
  };

  /* ------------------------------ Edición sesión ------------------------------ */

  const [editingLocation, setEditingLocation] = React.useState<{
    blockIndex: number;
    sessionIndex: number;
  } | null>(null);

  const [editingForm, setEditingForm] = React.useState<SesionFormState | null>(
    null
  );

  const openEditSesion = (session: Session) => {
    if (!horario) return;

    const [blockStr, sesStr] = String(session.id).split('-');
    const blockIndex = Number(blockStr);
    const sessionIndex = Number(sesStr);
    if (Number.isNaN(blockIndex) || Number.isNaN(sessionIndex)) return;

    const bloque = horario.horarios[blockIndex];
    const sesion = bloque?.sesiones?.[sessionIndex];
    if (!bloque || !sesion) return;

    setEditingLocation({ blockIndex, sessionIndex });
    setEditingForm({
      asignatura: sesion.asignatura ?? '',
      aula: sesion.aula ?? '',
      dia: sesion.dia ?? '',
      hora_inicio: sesion.hora_inicio ?? '',
      hora_fin: sesion.hora_fin ?? '',
      tipo: sesion.tipo ?? 'TEORÍA',
      grupo: sesion.grupo ?? '',
    });
  };

  const closeEditSesion = () => {
    setEditingLocation(null);
    setEditingForm(null);
  };

  const handleEditFieldChange = <K extends keyof SesionFormState>(
    field: K,
    value: SesionFormState[K]
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
  const [createTab, setCreateTab] = React.useState<'session' | 'block'>('session');
  const [createSessionForm, setCreateSessionForm] = React.useState<SesionFormState>(DEFAULT_SESSION_FORM);
  const [newBlockForm, setNewBlockForm] = React.useState<{
    curso: string;
    mencion: string;
  }>({ curso: '', mencion: '' });

  const [isEditBlockOpen, setIsEditBlockOpen] = React.useState(false);
  const [editBlockForm, setEditBlockForm] = React.useState<{
    curso: string;
    mencion: string;
  }>({ curso: '', mencion: '' });

  const canCreateSession = bloques.length > 0;
  const selectedBloque = bloques[selectedBlockIndex];

  const openCreateDialog = () => {
    const initialTab: 'session' | 'block' = canCreateSession ? 'session' : 'block';
    setCreateTab(initialTab);
    setCreateSessionForm(DEFAULT_SESSION_FORM);
    setNewBlockForm({ curso: '', mencion: '' });
    setIsCreateOpen(true);
  };

  const closeCreateDialog = () => {
    setIsCreateOpen(false);
  };

  const handleCreateFieldChange = <K extends keyof SesionFormState>(
    field: K,
    value: SesionFormState[K]
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

  const openEditBlockDialog = () => {
    const bloque = bloques[selectedBlockIndex];
    if (!bloque) return;
    setEditBlockForm({
      curso: bloque.curso,
      mencion: bloque.mencion || '',
    });
    setIsEditBlockOpen(true);
  };

  const handleSaveBlock = () => {
    setDraftHorario((prev) => {
      const source = prev ?? horario;
      if (!source) return prev;
      const cloned = JSON.parse(JSON.stringify(source)) as HorarioExtraido;
      const bloque = cloned.horarios[selectedBlockIndex];
      if (bloque) {
        bloque.curso = editBlockForm.curso;
        bloque.mencion = editBlockForm.mencion || null;
      }
      return cloned;
    });
    setIsEditBlockOpen(false);
  };

  const handleSessionMove = (
    session: Session,
    newDayIndex: number,
    newStartTime: string
  ) => {
    setDraftHorario((prev) => {
      const source = prev ?? horario;
      if (!source) return prev;

      const cloned = JSON.parse(JSON.stringify(source)) as HorarioExtraido;
      const [blockStr, sesStr] = String(session.id).split('-');
      const blockIndex = Number(blockStr);
      const sessionIndex = Number(sesStr);

      const bloque = cloned.horarios[blockIndex];
      const sesion = bloque?.sesiones?.[sessionIndex];
      if (!bloque || !sesion) return prev;

      const startMin = timeToMinutes(sesion.hora_inicio);
      const endMin = timeToMinutes(sesion.hora_fin);
      const duration = endMin - startMin;

      const newStartMin = timeToMinutes(newStartTime);
      const newEndMin = newStartMin + duration;

      sesion.dia = DIAS_SEMANA[newDayIndex];
      sesion.hora_inicio = newStartTime;
      sesion.hora_fin = minutesToTimeLabel(newEndMin);

      return cloned;
    });
  };

  const handleConfirm = async () => {
    if (!horario || !item) return;

    setIsConfirming(true);
    setConfirmError(null);

    try {
      await confirmHorario(horario as unknown as HorarioTemporalOut);
      useHorariosUploadsStore.getState().confirm(item.id);
      
      toast({
        title: 'Horario confirmado',
        description: 'El horario se ha guardado correctamente en la base de datos.',
      });

      router.push('/app/datos/horarios');
    } catch (error: unknown) {
      const message =
        error instanceof Error
          ? error.message
          : 'Error al confirmar el horario.';
      setConfirmError(message);
      
      toast({
        title: 'Error al guardar',
        description: message,
        variant: 'destructive',
      });
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
              El archivo se ha registrado, pero no se dispone de datos de extracción.
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
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1.5">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Revisión de horario
          </h1>
          <p className="text-lg text-muted-foreground">
            Revisa la información extraída y corrige las asignaciones usando datos oficiales.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2 sm:flex-row sm:items-center">
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
        </div>
      </div>
      {confirmError && (
        <p className="text-right text-sm text-destructive">
          {confirmError}
        </p>
      )}

      {/* --- TARJETA RESUMEN INTERACTIVA (CLICK PARA EDITAR) --- */}
      <Card 
        className="cursor-pointer transition-colors hover:bg-muted/50 group relative"
        onClick={openEditInfo}
        title="Haz clic para editar la información general"
      >
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Resumen del horario
            <Pencil className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">Plan de estudios</p>
              <p className="text-sm font-medium">
                {/* Fallback de visualización */}
                {horario.plan || horario.titulo?.split(' - ')[0] || 'Desconocido'}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">Periodo</p>
              <p className="text-sm font-medium capitalize">
                {horario.periodo || horario.titulo?.split(' - ')[1] || '—'}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">Estadísticas</p>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold">{bloques.length}</span>
                  <span className="text-muted-foreground">horarios</span>
                </div>
                <div className="h-4 w-px bg-border" />
                <div className="flex items-center gap-1.5">
                  <span className="font-bold">{totalSessions}</span>
                  <span className="text-muted-foreground">sesiones</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between gap-4">
        {bloques.length > 0 ? (
          <div className="flex-1 rounded-md border bg-muted/40 px-4 py-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="font-medium text-muted-foreground">
                Selecciona el curso o mención:
              </p>
              <div className="flex flex-wrap gap-2">
                {bloques.map((bloque, index) => {
                  const label = buildBloqueLabel(bloque);
                  const isActive = index === selectedBlockIndex;
                  return (
                    <Button
                      key={`${bloque.pagina}-${index}`}
                      type="button"
                      size="sm"
                      variant={isActive ? 'default' : 'outline'}
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
          <div className="flex-1 rounded-md border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
            Crea un nuevo horario para comenzar a añadir sesiones.
          </div>
        )}

        <div className="flex items-center gap-2">
          <Button
            type="button"
            onClick={openEditBlockDialog}
            size="icon"
            variant="outline"
            disabled={!bloques.length}
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            onClick={openCreateDialog}
            size="icon"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {hasData ? (
        <InteractiveScheduleGrid
          start="08:30"
          end="21:30"
          stepMin={30}
          sessions={sessions}
          onSessionClick={openEditSesion}
          onSessionMove={handleSessionMove}
        />
      ) : (
        <div className="rounded-md border bg-muted/20 p-6 text-sm text-muted-foreground">
          No hay datos de horario para mostrar todavía.
        </div>
      )}

      {/* --- DIÁLOGOS --- */}

      {/* NUEVO: Diálogo EDITAR INFO GENERAL */}
      <Dialog open={isEditInfoOpen} onOpenChange={(open) => !open && setIsEditInfoOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar información del horario</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="plan">Plan de estudios</Label>
              <Input
                id="plan"
                value={infoForm.plan}
                onChange={(e) => setInfoForm(prev => ({ ...prev, plan: e.target.value }))}
                placeholder="Ej. Grado en Matemáticas"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="periodo">Periodo</Label>
              <Input
                id="periodo"
                value={infoForm.periodo}
                onChange={(e) => setInfoForm(prev => ({ ...prev, periodo: e.target.value }))}
                placeholder="Ej. Primer Cuatrimestre"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditInfoOpen(false)}>Cancelar</Button>
            <Button onClick={handleSaveInfo}>Guardar cambios</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo Editar Bloque */}
      <Dialog open={isEditBlockOpen} onOpenChange={(open) => !open && setIsEditBlockOpen(false)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Editar horario (Curso/Mención)</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2 text-sm">
            <div className="grid gap-2">
              <Label htmlFor="edit-curso">Curso</Label>
              <Input
                id="edit-curso"
                value={editBlockForm.curso}
                onChange={(e) => setEditBlockForm((p) => ({ ...p, curso: e.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-mencion">Mención</Label>
              <Input
                id="edit-mencion"
                value={editBlockForm.mencion}
                onChange={(e) => setEditBlockForm((p) => ({ ...p, mencion: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setIsEditBlockOpen(false)}>Cancelar</Button>
            <Button onClick={handleSaveBlock}>Guardar cambios</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo Editar Sesión (Con Input normales) */}
      <Dialog open={isEditOpen} onOpenChange={(open) => !open && closeEditSesion()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar sesión {editingBloque ? ` · ${editingBloque.curso}` : ''}</DialogTitle>
          </DialogHeader>
          {editingForm && (
            <SessionFormFields
              form={editingForm}
              onChange={handleEditFieldChange}
            />
          )}
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={closeEditSesion}>Cancelar</Button>
            <Button onClick={handleSaveSesion}>Guardar cambios</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo Crear */}
      <Dialog open={isCreateOpen} onOpenChange={(open) => !open && closeCreateDialog()}>
        <DialogContent>
          <DialogHeader><DialogTitle>Crear elemento</DialogTitle></DialogHeader>
          <div className="mb-4 flex gap-2">
            <Button
              size="sm"
              variant={createTab === 'session' ? 'default' : 'secondary'}
              disabled={!canCreateSession}
              onClick={() => setCreateTab('session')}
            >
              Nueva sesión
            </Button>
            <Button
              size="sm"
              variant={createTab === 'block' ? 'default' : 'secondary'}
              onClick={() => setCreateTab('block')}
            >
              Nuevo horario
            </Button>
          </div>

          {createTab === 'session' && (
            <>
              {!canCreateSession ? (
                <p className="text-sm text-muted-foreground">Primero crea un horario (curso).</p>
              ) : (
                <SessionFormFields
                  form={createSessionForm}
                  onChange={handleCreateFieldChange}
                />
              )}
            </>
          )}

          {createTab === 'block' && (
             <div className="space-y-3 py-2 text-sm">
              <div className="grid gap-2">
                <Label htmlFor="nuevo-curso">Curso</Label>
                <Input
                  id="nuevo-curso"
                  value={newBlockForm.curso}
                  onChange={(e) => setNewBlockForm(p => ({ ...p, curso: e.target.value }))}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="nueva-mencion">Mención</Label>
                <Input
                  id="nueva-mencion"
                  value={newBlockForm.mencion}
                  onChange={(e) => setNewBlockForm(p => ({ ...p, mencion: e.target.value }))}
                />
              </div>
            </div>
          )}

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={closeCreateDialog}>Cancelar</Button>
            {createTab === 'session' ? (
              <Button onClick={handleCreateSession} disabled={!canCreateSession}>Crear sesión</Button>
            ) : (
              <Button onClick={handleCreateBlock} disabled={!newBlockForm.curso.trim()}>Crear horario</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Formulario de sesión clásico (Inputs de texto)
type SessionFormFieldsProps = {
  form: SesionFormState;
  onChange: <K extends keyof SesionFormState>(
    field: K,
    value: SesionFormState[K]
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
          onChange={(e) => onChange('asignatura', e.target.value)}
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="aula">Aula</Label>
        <Input
          id="aula"
          value={form.aula}
          onChange={(e) => onChange('aula', e.target.value)}
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="dia">Día</Label>
        <select
          id="dia"
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={form.dia}
          onChange={(e) => onChange('dia', e.target.value)}
        >
          {DIAS_SEMANA.map((d) => (
            <option key={d} value={d}>{d}</option>
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
            onChange={(e) => onChange('hora_inicio', e.target.value)}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="hora_fin">Hora fin</Label>
          <Input
            id="hora_fin"
            type="time"
            value={form.hora_fin}
            onChange={(e) => onChange('hora_fin', e.target.value)}
          />
        </div>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="tipo">Tipo</Label>
        <select
          id="tipo"
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={form.tipo}
          onChange={(e) => onChange('tipo', e.target.value)}
        >
          {TIPO_OPCIONES.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="grupo">Grupo</Label>
        <Input
          id="grupo"
          value={form.grupo}
          onChange={(e) => onChange('grupo', e.target.value)}
          placeholder="PL1, PL2..."
        />
      </div>
    </div>
  );
}

// Helpers
function mapHorarioToSessions(horario: HorarioExtraido): Session[] {
  const sessions: Session[] = [];
  const bloques = Array.isArray(horario.horarios) ? horario.horarios : [];
  bloques.forEach((bloque, bloqueIndex) => {
    const bloqueSessions = mapBloqueToSessions(bloque, bloqueIndex);
    sessions.push(...bloqueSessions);
  });
  return sessions;
}

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

function normalizeTime(value: string): string {
  if (!value) return value;
  const parts = value.split(":");
  if (parts.length >= 2) {
    return `${parts[0].padStart(2, "0")}:${parts[1].padStart(2, "0")}`;
  }
  return value;
}

function diaToDayIndex(dia: string): number {
  const d = dia.trim().toUpperCase();
  const map: Record<string, number> = {
    LUNES: 0, L: 0, MARTES: 1, M: 1, MIÉRCOLES: 2, MIERCOLES: 2, X: 2, JUEVES: 3, J: 3, VIERNES: 4, V: 4,
  };
  if (d in map) return map[d];
  return -1;
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

function buildSessionTitle(s: HorarioExtraidoSesion, _bloque: HorarioExtraidoBloque): string {
  const asignatura = (s.asignatura ?? "").trim();
  return asignatura || "Sesión";
}

function buildCourseIdFromCurso(cursoTexto: string): string {
  const n = getCourseNumberFromTexto(cursoTexto);
  if (n === null) return cursoTexto || "DESCONOCIDO";
  return `${n}º`;
}

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

function buildBloqueLabel(bloque: HorarioExtraidoBloque): string {
  const n = getCourseNumberFromTexto(bloque.curso);
  const base = n ? `${n}º` : bloque.curso || "Curso";
  if (!bloque.mencion) return base;
  const niceMention = prettifyMention(bloque.mencion);
  return `${base} - ${niceMention}`;
}

function prettifyMention(raw: string): string {
  if (!raw) return "Mención";
  let text = raw.trim();
  const m = text.match(/MENCI[ÓO]N\s+EN\s+(.+)/i);
  if (m) {
    text = m[1];
  }
  text = text.toLowerCase().split(/\s+/).filter(Boolean).map((w) => w[0].toUpperCase() + w.slice(1)).join(" ");
  return `Mención en ${text}`;
}