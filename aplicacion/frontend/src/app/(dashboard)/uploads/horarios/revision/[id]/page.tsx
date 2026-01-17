'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { 
  Pencil, Loader2, CheckCircle2, AlertTriangle, 
  Sparkles, XCircle, ArrowRight, Plus, AlertCircle, Trash2
} from 'lucide-react';

import { InteractiveScheduleGrid } from '@/components/solver/interactive-schedule-grid';
import type { Session } from '@/components/solver/schedule-mock';

import { useHorariosUploadsStore } from '@/stores/horarios-uploads';
import { confirmHorario, refineHorario, type HorarioTemporalOut } from '@/lib/api/docencia/horarios';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { SimpleAutocomplete, type AutocompleteOption } from '@/components/ui/simple-autocomplete';

import { listAsignaturas, type AsignaturaOut } from '@/lib/api/catalogo/asignaturas';
import { listAulas, type AulaOut } from '@/lib/api/recursos/aulas';
import { listProgramas, type ProgramaOut } from '@/lib/api/catalogo/programas';
import { PERIODOS } from '@/lib/constants/periodos';

// Importamos el componente de revisión
import { ReviewDashboard, ReviewBlock } from '@/components/solver/review-dashboard';

type RouteParams = { id: string };
type Props = { params: Promise<RouteParams> };

// --- TIPOS ---
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
  
  match_confidence?: number;
  match_status?: string;       
  asignatura_sugerida?: string;
  manual_validated?: boolean;
  
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

const TIPO_OPCIONES = ['TEORÍA', 'PRÁCTICAS DE AULA', 'PRÁCTICAS DE LABORATORIO'] as const;
const DIAS_SEMANA = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES'] as const;

// --- COMPONENTE: MatchInfoCard (Tipado) ---
interface MatchInfoCardProps {
  status?: string;
  originalName: string;
  suggestedName?: string;
}

function MatchInfoCard({ status, originalName, suggestedName }: MatchInfoCardProps) {
  if (!status) return null;

  const isExact = status === 'EXACT' || status === 'ALIAS_DB';
  
  if (isExact) {
      return (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1">
              <p className="font-semibold">Coincidencia Exacta</p>
              <p className="text-blue-700/80">Nombre validado en BD.</p>
            </div>
          </div>
        </div>
      );
  }

  if (suggestedName) {
      return (
        <div className="mb-4 rounded-md border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-800">
          <div className="flex items-start gap-3">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1">
              <p className="font-semibold">Sugerencia Automática</p>
              <div className="flex flex-wrap items-center gap-1 text-indigo-700/90">
                <span>PDF: <strong>{`"${originalName}"`}</strong></span>
                <ArrowRight className="h-3 w-3" />
                <span>Sugerencia: <strong>{`"${suggestedName}"`}</strong></span>
              </div>
            </div>
          </div>
        </div>
      );
  }

  return (
    <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      <div className="flex items-start gap-3">
        <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <div className="space-y-1">
          <p className="font-semibold">Sin Coincidencia</p>
          <p className="text-red-700/90">
             Original: <strong>{`"${originalName}"`}</strong>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function RevisionHorarioPage({ params }: Props) {
  const { id } = React.use(params);
  const router = useRouter();
  const { toast } = useToast();

  const { items, updateHorario, confirm } = useHorariosUploadsStore();

  const item = React.useMemo(
    () => items.find((it) => it.id === id),
    [items, id]
  );

  const horarioTemporal: HorarioExtraido | undefined =
    item?.horarioTemporal as unknown as HorarioExtraido | undefined;

  // --- DATOS MAESTROS ---
  const [listaAsignaturas, setListaAsignaturas] = React.useState<AsignaturaOut[]>([]);
  const [listaAulas, setListaAulas] = React.useState<AulaOut[]>([]);
  const [listaProgramas, setListaProgramas] = React.useState<ProgramaOut[]>([]);

  React.useEffect(() => {
    let mounted = true;
    async function loadData() {
      try {
        const [resProgramas, resAsig, resAulas] = await Promise.all([
          listProgramas(1, 500, true),
          listAsignaturas({ limit: 1000, activo: true }),
          listAulas({ size: 1000 }),
        ]);

        if (mounted) {
          setListaProgramas(resProgramas.items || []);
          setListaAsignaturas(resAsig.items || []);
          setListaAulas(resAulas.items || []);
        }
      } catch (error) {
        console.error('Error cargando catálogo', error);
      }
    }
    loadData();
    return () => { mounted = false; };
  }, []);

  const programasOptions = React.useMemo<AutocompleteOption[]>(
    () => listaProgramas.map((p) => ({
      value: p.id,
      label: p.nombre,
      keywords: p.tipo,
    })),
    [listaProgramas]
  );

  const asignaturaOptions = React.useMemo<AutocompleteOption[]>(() => {
    if (!horarioTemporal) return [];
    const planHorario = normalizeText(
      horarioTemporal.plan ||
      (horarioTemporal.titulo ? horarioTemporal.titulo.split(' - ')[0] : '') || ''
    );
    const filtradas = listaAsignaturas.filter((asig) => {
      const match = asig.titulaciones?.some((t) => {
        const nombreProg = normalizeText(t.programa.nombre);
        return nombreProg.includes(planHorario) || planHorario.includes(nombreProg);
      });
      return match;
    });
    const listaFinal = filtradas.length > 0 ? filtradas : listaAsignaturas;
    return listaFinal.map((a) => ({
      value: a.id,
      label: a.nombre,
      keywords: a.codigo_plan,
    }));
  }, [listaAsignaturas, horarioTemporal]);

  const aulaOptions = React.useMemo<AutocompleteOption[]>(
    () => listaAulas.map((a) => ({
      value: a.id,
      label: a.nombre,
      keywords: a.codigo,
    })),
    [listaAulas]
  );

  const [draftHorario, setDraftHorario] = React.useState<HorarioExtraido | null>(null);

  React.useEffect(() => {
    if (horarioTemporal) {
      const cloned = JSON.parse(JSON.stringify(horarioTemporal)) as HorarioExtraido;
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
  const displayPlan = horario?.plan || horario?.titulo?.split(' - ')[0] || "Desconocido";
  const displayPeriodo = horario?.periodo || horario?.titulo?.split(' - ')[1] || "—";

  const [isEditInfoOpen, setIsEditInfoOpen] = React.useState(false);
  const [isRefining, setIsRefining] = React.useState(false);
  const [infoForm, setInfoForm] = React.useState({ plan: '', periodo: '' });

  const [editingLocation, setEditingLocation] = React.useState<{ blockIndex: number; sessionIndex: number } | null>(null);
  const [editingForm, setEditingForm] = React.useState<SesionFormState | null>(null);
  const [isEditOpen, setIsEditOpen] = React.useState(false);

  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [createTab, setCreateTab] = React.useState<'session' | 'block'>('session');
  const [createSessionForm, setCreateSessionForm] = React.useState<SesionFormState>(DEFAULT_SESSION_FORM);
  const [newBlockForm, setNewBlockForm] = React.useState({ curso: '', mencion: '' });
  
  const [isEditBlockOpen, setIsEditBlockOpen] = React.useState(false);
  const [editBlockForm, setEditBlockForm] = React.useState({ curso: '', mencion: '' });
  
  const canCreateSession = bloques.length > 0;

  const handleUpdateDraft = (newHorario: HorarioExtraido) => {
    setDraftHorario(newHorario);
    if (item) updateHorario(item.id, newHorario as unknown as HorarioTemporalOut);
  };

  const handleBack = () => {
    if (item && draftHorario) {
      updateHorario(item.id, draftHorario as unknown as HorarioTemporalOut);
    }
    router.push('/uploads/horarios');
  };

  const openEditInfo = () => {
    if (!horario) return;
    setInfoForm({
      plan: horario.plan || horario.titulo?.split(' - ')[0] || '',
      periodo: horario.periodo || horario.titulo?.split(' - ')[1] || '',
    });
    setIsEditInfoOpen(true);
  };

  const handleSaveInfo = async () => {
    const horarioActualizado = JSON.parse(JSON.stringify(draftHorario ?? horarioTemporal));
    horarioActualizado.plan = infoForm.plan;
    horarioActualizado.periodo = infoForm.periodo;
    horarioActualizado.titulo = `${infoForm.plan} - ${infoForm.periodo}`;

    setIsRefining(true);
    try {
        const nuevoHorario = await refineHorario(horarioActualizado as unknown as HorarioTemporalOut);
        handleUpdateDraft(nuevoHorario as unknown as HorarioExtraido);
        setIsEditInfoOpen(false);
        toast({ title: 'Horario Actualizado', description: 'Contexto actualizado.' });
    } catch (error) {
        handleUpdateDraft(horarioActualizado);
        setIsEditInfoOpen(false);
    } finally {
        setIsRefining(false);
    }
  };

  // --- HANDLERS INTERACTIVOS DE REVISIÓN ---

  const toggleSessionValidation = (sesIndex: number, isValid: boolean) => {
    if (!draftHorario) return;
    const cloned = JSON.parse(JSON.stringify(draftHorario)) as HorarioExtraido;
    const sesion = cloned.horarios[selectedBlockIndex]?.sesiones?.[sesIndex];
    if (sesion) {
        sesion.manual_validated = isValid;
        handleUpdateDraft(cloned);
    }
  };

  const confirmAllSuggestionsInBlock = () => {
    if (!draftHorario) return;
    const cloned = JSON.parse(JSON.stringify(draftHorario)) as HorarioExtraido;
    const bloque = cloned.horarios[selectedBlockIndex];
    if (bloque && bloque.sesiones) {
        let count = 0;
        bloque.sesiones.forEach(s => {
            // Si tiene sugerencia y no es exacto ni validado -> Validar
            const isExact = s.match_status === 'EXACT' || s.match_status === 'ALIAS_DB';
            if (s.asignatura_sugerida && !isExact && !s.manual_validated) {
                s.manual_validated = true;
                count++;
            }
        });
        if (count > 0) {
            handleUpdateDraft(cloned);
            toast({ title: 'Sugerencias confirmadas', description: `${count} sesiones validadas.` });
        }
    }
  };

  const handleDeleteSession = (sesIndex: number) => {
    if (!draftHorario) return;
    const cloned = JSON.parse(JSON.stringify(draftHorario)) as HorarioExtraido;
    const bloque = cloned.horarios[selectedBlockIndex];
    if (bloque && bloque.sesiones) {
        bloque.sesiones.splice(sesIndex, 1);
        handleUpdateDraft(cloned);
        toast({ title: 'Eliminada', description: 'Sesión eliminada.' });
    }
  };

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
      asignatura: sesion.asignatura_sugerida || sesion.asignatura || '',
      aula: sesion.aula ?? '',
      dia: sesion.dia ?? '',
      hora_inicio: sesion.hora_inicio ?? '',
      hora_fin: sesion.hora_fin ?? '',
      tipo: sesion.tipo ?? 'TEORÍA',
      grupo: sesion.grupo ?? '',
    });
    setIsEditOpen(true);
  };

  const closeEditSesion = () => {
    setEditingLocation(null);
    setEditingForm(null);
    setIsEditOpen(false);
  };

  const handleEditFieldChange = <K extends keyof SesionFormState>(field: K, value: SesionFormState[K]) => {
    setEditingForm((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  const handleSaveSesion = () => {
    if (!editingLocation || !editingForm) return;
    const cloned = JSON.parse(JSON.stringify(draftHorario ?? horario)) as HorarioExtraido;
    const { blockIndex, sessionIndex } = editingLocation;
    const sesion = cloned.horarios[blockIndex]?.sesiones?.[sessionIndex];

    if (sesion) {
      Object.assign(sesion, {
        asignatura: editingForm.asignatura,
        aula: editingForm.aula,
        dia: editingForm.dia,
        hora_inicio: editingForm.hora_inicio,
        hora_fin: editingForm.hora_fin,
        tipo: editingForm.tipo,
        grupo: editingForm.grupo || null,
        manual_validated: true,
        asignatura_sugerida: editingForm.asignatura
      });
    }
    handleUpdateDraft(cloned);
    closeEditSesion();
  };

  const openCreateDialog = () => {
    setCreateTab(canCreateSession ? 'session' : 'block');
    setCreateSessionForm(DEFAULT_SESSION_FORM);
    setNewBlockForm({ curso: '', mencion: '' });
    setIsCreateOpen(true);
  };
  const closeCreateDialog = () => setIsCreateOpen(false);
  const handleCreateFieldChange = <K extends keyof SesionFormState>(f: K, v: SesionFormState[K]) => setCreateSessionForm((p) => ({ ...p, [f]: v }));
  
  const handleCreateSession = () => {
    if (!canCreateSession) return;
    const cloned = JSON.parse(JSON.stringify(draftHorario ?? horario)) as HorarioExtraido;
    const bloque = cloned.horarios[selectedBlockIndex];
    if (!bloque.sesiones) bloque.sesiones = [];
    bloque.sesiones.push({
      ...createSessionForm,
      grupo: createSessionForm.grupo || null,
      match_status: 'MANUAL',
      manual_validated: true
    });
    handleUpdateDraft(cloned);
    setIsCreateOpen(false);
  };
  const handleCreateBlock = () => {
    const curso = newBlockForm.curso.trim();
    if (!curso) return;
    const cloned = JSON.parse(JSON.stringify(draftHorario ?? horario)) as HorarioExtraido;
    if (!cloned.horarios) cloned.horarios = [];
    cloned.horarios.push({
      curso,
      periodo: cloned.periodo,
      mencion: newBlockForm.mencion || null,
      pagina: cloned.horarios.length,
      sesiones: [],
    });
    handleUpdateDraft(cloned);
    setIsCreateOpen(false);
  };

  const openEditBlockDialog = () => {
    const bloque = bloques[selectedBlockIndex];
    if (!bloque) return;
    setEditBlockForm({ curso: bloque.curso, mencion: bloque.mencion || '' });
    setIsEditBlockOpen(true);
  };
  const handleSaveBlock = () => {
    const cloned = JSON.parse(JSON.stringify(draftHorario ?? horario)) as HorarioExtraido;
    const bloque = cloned.horarios[selectedBlockIndex];
    if (bloque) {
      bloque.curso = editBlockForm.curso;
      bloque.mencion = editBlockForm.mencion || null;
    }
    handleUpdateDraft(cloned);
    setIsEditBlockOpen(false);
  };

  const handleSessionMove = (session: Session, newDayIndex: number, newStartTime: string) => {
    const cloned = JSON.parse(JSON.stringify(draftHorario ?? horario)) as HorarioExtraido;
    const [blockStr, sesStr] = String(session.id).split('-');
    const sesion = cloned.horarios[Number(blockStr)]?.sesiones?.[Number(sesStr)];
    if (sesion) {
      const duration = timeToMinutes(sesion.hora_fin) - timeToMinutes(sesion.hora_inicio);
      const startMin = timeToMinutes(newStartTime);
      sesion.dia = DIAS_SEMANA[newDayIndex];
      sesion.hora_inicio = newStartTime;
      sesion.hora_fin = minutesToTimeLabel(startMin + duration);
      handleUpdateDraft(cloned);
    }
  };

  // --- 🔥 HANDLE CONFIRM CON GATEKEEPER ---
  const handleConfirm = async () => {
    if (!horario || !item) return;

    setIsConfirming(true);
    setConfirmError(null); 

    try {
      // Aseguramos que el campo 'plan' tenga valor antes de enviar.
      // Usamos la misma lógica que usas para 'displayPlan'.
      const planAEnviar = horario.plan || horario.titulo?.split(' - ')[0] || "";
      
      // Creamos una copia del horario asegurando que el plan está relleno
      const payload = {
        ...horario,
        plan: planAEnviar
      };

      await confirmHorario(payload as unknown as HorarioTemporalOut);
      
      // Si todo OK:
      confirm(item.id);
      toast({ title: '¡Éxito!', description: 'El horario se ha guardado correctamente.' });
      router.push('/uploads/horarios'); 
      
    } catch (error: unknown) {
      // Capturamos error 400 del Gatekeeper
      const msg = (error as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail 
        || (error as { message?: string })?.message 
        || 'Error desconocido al confirmar.';
      
      setConfirmError(msg); 
      
      toast({ 
        title: 'No se puede guardar', 
        description: 'Hay errores bloqueantes. Revisa la alerta en pantalla.', 
        variant: 'destructive' 
      });
    } finally {
      setIsConfirming(false);
    }
  };

  const currentPlanId = React.useMemo(() => listaProgramas.find((p) => p.nombre === infoForm.plan)?.id, [listaProgramas, infoForm.plan]);

  if (!item || !horario) return <div className="p-8"><Card><CardContent className="p-6">Cargando...</CardContent></Card></div>;

  const editingBloque = editingLocation && horario?.horarios ? horario.horarios[editingLocation.blockIndex] : null;

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1.5">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Revisión de horario</h1>
          <p className="text-lg text-muted-foreground">Verifica los datos extraídos antes de confirmar.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleBack}>Volver</Button>
          <Button onClick={handleConfirm} disabled={isConfirming || !hasData}>
            {isConfirming ? 'Guardando...' : 'Confirmar horario'}
          </Button>
        </div>
      </div>

      {/* 🔥 ALERTA DE ERROR BLOQUEANTE */}
      {confirmError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 animate-in slide-in-from-top-2">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-red-900 mb-1">No se pudo confirmar el horario</h3>
              <p className="text-sm text-red-700 leading-relaxed">
                {confirmError}
              </p>
            </div>
            <Button 
              variant="ghost" 
              size="sm" 
              className="text-red-500 hover:text-red-700 hover:bg-red-100"
              onClick={() => setConfirmError(null)}
            >
              Cerrar
            </Button>
          </div>
        </div>
      )}

      {/* INFO CARD */}
      <Card className="cursor-pointer hover:bg-muted/50 group" onClick={openEditInfo}>
        <CardHeader><CardTitle className="flex justify-between">Resumen <Pencil className="h-4 w-4 opacity-0 group-hover:opacity-100" /></CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            <div><p className="text-xs text-muted-foreground">Plan</p><p className="font-medium">{displayPlan}</p></div>
            <div><p className="text-xs text-muted-foreground">Periodo</p><p className="font-medium capitalize">{displayPeriodo.replace(/_/g, ' ')}</p></div>
            <div><p className="text-xs text-muted-foreground">Total</p><p className="font-medium">{bloques.length} cursos · {totalSessions} sesiones</p></div>
          </div>
        </CardContent>
      </Card>

      {/* SELECTOR BLOQUES */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 rounded-md border bg-muted/40 px-4 py-3 text-sm flex flex-wrap gap-3 items-center">
          <p className="font-medium text-muted-foreground">Curso:</p>
          <div className="flex flex-wrap gap-2">
            {bloques.map((b, i) => (
              <Button key={i} size="sm" variant={i === selectedBlockIndex ? 'default' : 'outline'} onClick={() => setSelectedBlockIndex(i)}>
                {buildBloqueLabel(b)}
              </Button>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <Button size="icon" variant="outline" onClick={openEditBlockDialog} disabled={!bloques.length}><Pencil className="h-4 w-4" /></Button>
          <Button size="icon" onClick={openCreateDialog}><Plus className="h-4 w-4" /></Button>
        </div>
      </div>

      {/* COMPONENTE DE REVISIÓN */}
      {hasData && (
        <ReviewDashboard 
           bloque={bloques[selectedBlockIndex] as unknown as ReviewBlock}
           onEditSession={(idx) => {
               setEditingLocation({ blockIndex: selectedBlockIndex, sessionIndex: idx });
               const sesion = bloques[selectedBlockIndex].sesiones[idx];
               setEditingForm({
                   asignatura: sesion.asignatura_sugerida || sesion.asignatura,
                   aula: sesion.aula || '',
                   dia: sesion.dia || '',
                   hora_inicio: sesion.hora_inicio || '',
                   hora_fin: sesion.hora_fin || '',
                   tipo: sesion.tipo || 'TEORÍA',
                   grupo: sesion.grupo || ''
               });
               setIsEditOpen(true);
           }}
           onDeleteSession={handleDeleteSession}
        />
      )}

      {/* CALENDARIO */}
      {hasData && (
        <InteractiveScheduleGrid
          sessions={sessions}
          onSessionClick={openEditSesion}
          onSessionMove={handleSessionMove}
        />
      )}

      {/* EDIT INFO DIALOG */}
      <Dialog open={isEditInfoOpen} onOpenChange={setIsEditInfoOpen}>
        <DialogContent className="overflow-visible">
          <DialogHeader><DialogTitle>Editar información</DialogTitle></DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Plan</Label>
              <SimpleAutocomplete options={programasOptions} value={currentPlanId} initialValue={infoForm.plan} onChange={(val) => {
                  const sel = programasOptions.find((p) => p.value === val);
                  if (sel) setInfoForm({ ...infoForm, plan: sel.label });
              }} placeholder="Buscar..." />
            </div>
            <div className="grid gap-2">
              <Label>Periodo</Label>
              <select className="h-9 rounded-md border px-3" value={infoForm.periodo} onChange={(e) => setInfoForm({ ...infoForm, periodo: e.target.value })}>
                {PERIODOS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>
          </div>
          <DialogFooter><Button onClick={handleSaveInfo} disabled={isRefining}>{isRefining ? 'Calculando...' : 'Guardar'}</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      {/* EDIT SESION DIALOG */}
      <Dialog open={isEditOpen} onOpenChange={(open) => !open && closeEditSesion()}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader><DialogTitle>Editar sesión</DialogTitle></DialogHeader>
          {editingBloque && editingLocation && (
            <MatchInfoCard 
              status={editingBloque.sesiones[editingLocation.sessionIndex].match_status}
              originalName={editingBloque.sesiones[editingLocation.sessionIndex].asignatura}
              suggestedName={editingBloque.sesiones[editingLocation.sessionIndex].asignatura_sugerida}
            />
          )}
          {editingForm && (
            <SessionFormFieldsSmart form={editingForm} onChange={handleEditFieldChange} asignaturaOptions={asignaturaOptions} aulaOptions={aulaOptions} />
          )}
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={closeEditSesion}>Cancelar</Button>
            <Button onClick={handleSaveSesion}>Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* CREATE DIALOG */}
      <Dialog open={isCreateOpen} onOpenChange={(open) => !open && closeCreateDialog()}>
        <DialogContent>
          <DialogHeader><DialogTitle>Crear elemento</DialogTitle></DialogHeader>
          <div className="mb-4 flex gap-2">
            <Button size="sm" variant={createTab === 'session' ? 'default' : 'secondary'} disabled={!canCreateSession} onClick={() => setCreateTab('session')}>Nueva sesión</Button>
            <Button size="sm" variant={createTab === 'block' ? 'default' : 'secondary'} onClick={() => setCreateTab('block')}>Nuevo horario</Button>
          </div>
          {createTab === 'session' && <SessionFormFieldsSmart form={createSessionForm} onChange={handleCreateFieldChange} asignaturaOptions={asignaturaOptions} aulaOptions={aulaOptions} />}
          {createTab === 'block' && (
            <div className="space-y-3 py-2 text-sm">
              <div className="grid gap-2"><Label>Curso</Label><Input value={newBlockForm.curso} onChange={(e) => setNewBlockForm({ ...newBlockForm, curso: e.target.value })} /></div>
              <div className="grid gap-2"><Label>Mención</Label><Input value={newBlockForm.mencion} onChange={(e) => setNewBlockForm({ ...newBlockForm, mencion: e.target.value })} /></div>
            </div>
          )}
          <DialogFooter className="mt-4">
            {createTab === 'session' ? <Button onClick={handleCreateSession} disabled={!canCreateSession}>Crear</Button> : <Button onClick={handleCreateBlock} disabled={!newBlockForm.curso}>Crear</Button>}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* EDIT BLOCK DIALOG */}
      <Dialog open={isEditBlockOpen} onOpenChange={setIsEditBlockOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Editar curso</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2 text-sm">
            <div className="grid gap-2"><Label>Curso</Label><Input value={editBlockForm.curso} onChange={(e) => setEditBlockForm({ ...editBlockForm, curso: e.target.value })} /></div>
            <div className="grid gap-2"><Label>Mención</Label><Input value={editBlockForm.mencion} onChange={(e) => setEditBlockForm({ ...editBlockForm, mencion: e.target.value })} /></div>
          </div>
          <DialogFooter><Button onClick={handleSaveBlock}>Guardar</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// CORRECCIÓN: Definición de tipos explícita en lugar de 'any'
interface SessionFormFieldsProps {
  form: SesionFormState;
  onChange: <K extends keyof SesionFormState>(f: K, v: SesionFormState[K]) => void;
  asignaturaOptions: AutocompleteOption[];
  aulaOptions: AutocompleteOption[];
}

function SessionFormFieldsSmart({
  form,
  onChange,
  asignaturaOptions,
  aulaOptions,
}: SessionFormFieldsProps) {
  const selectedAsigId = React.useMemo(() => asignaturaOptions.find((opt) => opt.label === form.asignatura)?.value, [asignaturaOptions, form.asignatura]);
  const selectedAulaId = React.useMemo(() => aulaOptions.find((opt) => opt.label === form.aula)?.value, [aulaOptions, form.aula]);

  return (
    <div className="space-y-3 py-2 text-sm">
      <div className="grid gap-2">
        <Label>Asignatura</Label>
        <SimpleAutocomplete options={asignaturaOptions} value={selectedAsigId} initialValue={form.asignatura} onChange={(val) => {
            const selected = asignaturaOptions.find((o) => o.value === val);
            if (selected) onChange('asignatura', selected.label);
          }} placeholder="Buscar..." emptyText="No encontrada" />
      </div>
      <div className="grid gap-2">
        <Label>Aula</Label>
        <SimpleAutocomplete options={aulaOptions} value={selectedAulaId} initialValue={form.aula} onChange={(val) => {
            const selected = aulaOptions.find((o) => o.value === val);
            if (selected) onChange('aula', selected.label);
          }} placeholder="Buscar..." />
      </div>
      <div className="grid gap-2">
        <Label>Día</Label>
        <select className="h-9 rounded-md border px-3" value={form.dia} onChange={(e) => onChange('dia', e.target.value)}>
          {DIAS_SEMANA.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="grid gap-2"><Label>Inicio</Label><Input type="time" value={form.hora_inicio} onChange={(e) => onChange('hora_inicio', e.target.value)} /></div>
        <div className="grid gap-2"><Label>Fin</Label><Input type="time" value={form.hora_fin} onChange={(e) => onChange('hora_fin', e.target.value)} /></div>
      </div>
      <div className="grid gap-2">
        <Label>Tipo</Label>
        <select className="h-9 rounded-md border px-3" value={form.tipo} onChange={(e) => onChange('tipo', e.target.value)}>
          {TIPO_OPCIONES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <div className="grid gap-2"><Label>Grupo</Label><Input value={form.grupo} onChange={(e) => onChange('grupo', e.target.value)} placeholder="Ej: PL1" /></div>
    </div>
  );
}

// --- HELPERS ---

function normalizeText(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function mapHorarioToSessions(horario: HorarioExtraido): Session[] {
  const sessions: Session[] = [];
  (horario.horarios || []).forEach((b, i) => sessions.push(...mapBloqueToSessions(b, i)));
  return sessions;
}

function mapBloqueToSessions(bloque: HorarioExtraidoBloque, bloqueIndex: number): Session[] {
  const sessions: Session[] = [];
  (bloque.sesiones || []).forEach((sesion, sesionIndex) => {
    const dayIndex = diaToDayIndex(sesion.dia);
    if (dayIndex < 0) return;

    let color: Session['color'] = 'blue';
    const hasAsignatura = sesion.asignatura_sugerida || sesion.manual_validated || sesion.match_status === 'EXACT' || sesion.match_status === 'ALIAS_DB';
    const hasAula = sesion.aula && sesion.aula !== 'POR DETERMINAR';

    if (!hasAsignatura || !hasAula) {
        color = 'red';
    } else {
        color = 'blue';
    }

    const displayName = sesion.asignatura_sugerida || sesion.asignatura;

    sessions.push({
      id: `${bloqueIndex}-${sesionIndex}`,
      courseId: buildCourseIdFromCurso(bloque.curso),
      dayIndex,
      start: normalizeTime(sesion.hora_inicio),
      end: normalizeTime(sesion.hora_fin),
      title: displayName, 
      room: sesion.aula ?? '—',
      teacher: sesion.grupo ? `Grupo ${sesion.grupo}` : '',
      color: color,
      
      originalName: sesion.asignatura,
      suggestedName: sesion.asignatura_sugerida,
      matchStatus: sesion.match_status,
    } as unknown as Session); 
  });
  return sessions;
}

function diaToDayIndex(dia: string): number {
  const d = dia.trim().toUpperCase();
  if (d.startsWith('L')) return 0;
  if (d.startsWith('MA')) return 1;
  if (d.startsWith('MI')) return 2;
  if (d.startsWith('J')) return 3;
  if (d.startsWith('V')) return 4;
  return -1;
}

function normalizeTime(value: string): string {
  if (!value) return value;
  const parts = value.split(':');
  return parts.length >= 2 ? `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}` : value;
}

function timeToMinutes(value: string): number {
  if (!value) return 0;
  const [h, m] = value.split(':').map((n) => parseInt(n, 10) || 0);
  return h * 60 + m;
}

function minutesToTimeLabel(totalMin: number): string {
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function buildCourseIdFromCurso(cursoTexto: string): string {
  if (cursoTexto.includes('1') || cursoTexto.toLowerCase().includes('primer')) return '1º';
  if (cursoTexto.includes('2') || cursoTexto.toLowerCase().includes('segundo')) return '2º';
  if (cursoTexto.includes('3') || cursoTexto.toLowerCase().includes('tercer')) return '3º';
  if (cursoTexto.includes('4') || cursoTexto.toLowerCase().includes('cuarto')) return '4º';
  if (cursoTexto.includes('5') || cursoTexto.toLowerCase().includes('quinto')) return '5º';
  return cursoTexto;
}

function buildBloqueLabel(bloque: HorarioExtraidoBloque): string {
  const base = buildCourseIdFromCurso(bloque.curso);
  if (!bloque.mencion) return base;
  return `${base} - ${bloque.mencion.replace(/MENCI[ÓO]N\s+EN\s+/i, 'Mención ')}`;
}