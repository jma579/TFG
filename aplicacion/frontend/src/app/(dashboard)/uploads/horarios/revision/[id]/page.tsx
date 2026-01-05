'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Pencil, Sparkles, CheckCircle2, AlertTriangle, XCircle, ArrowRight, Loader2 } from 'lucide-react';
import { InteractiveScheduleGrid } from '@/components/solver/interactive-schedule-grid';
import type { Session } from '@/components/solver/schedule-mock';
import {
  useHorariosUploadsStore,
} from '@/stores/horarios-uploads';
// 👇 AÑADIDO: Importamos refineHorario
import { confirmHorario, refineHorario, type HorarioTemporalOut } from '@/lib/api/docencia/horarios';
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
import { SimpleAutocomplete, type AutocompleteOption } from '@/components/ui/simple-autocomplete';
import { listAsignaturas, type AsignaturaOut } from '@/lib/api/catalogo/asignaturas';
import { listAulas, type AulaOut } from '@/lib/api/recursos/aulas';
import { listProgramas, type ProgramaOut } from '@/lib/api/catalogo/programas';
import { PERIODOS } from '@/lib/constants/periodos';

type RouteParams = { id: string };

type Props = {
  params: Promise<RouteParams>;
};

// --- Tipos ---
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
  
  // Metadatos de Matcher
  match_confidence?: number;
  match_status?: string;       
  asignatura_sugerida?: string; 
  
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

// --- COMPONENTE: MatchInfoCard ---
function MatchInfoCard({ 
  status, 
  originalName, 
  suggestedName 
}: { 
  status?: string, 
  originalName: string, 
  suggestedName?: string 
}) {
  if (!status) return null;

  switch (status) {
    case 'EXACT':
      return (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1">
              <p className="font-semibold">Asignatura Validada</p>
              <p className="text-blue-700/80">
                El nombre detectado coincide exactamente con la base de datos.
              </p>
            </div>
          </div>
        </div>
      );

    case 'ALIAS_DB':
      return (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1">
              <p className="font-semibold">Alias Reconocido</p>
              <div className="flex flex-wrap items-center gap-1 text-blue-700/90">
                <span>Original: <strong>"{originalName}"</strong></span>
                <ArrowRight className="h-3 w-3" />
                <span>Oficial: <strong>"{suggestedName}"</strong></span>
              </div>
            </div>
          </div>
        </div>
      );

    case 'FUZZY_AUTO':
      return (
        <div className="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          <div className="flex items-start gap-3">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1">
              <p className="font-semibold">Predicción Automática</p>
              <div className="flex flex-wrap items-center gap-1 text-green-700/90">
                <span>PDF: <strong>"{originalName}"</strong></span>
                <ArrowRight className="h-3 w-3" />
                <span>Asignado a: <strong>"{suggestedName}"</strong></span>
              </div>
              <p className="mt-1 text-xs text-green-600">
                El sistema ha corregido el nombre automáticamente.
              </p>
            </div>
          </div>
        </div>
      );

    case 'FUZZY_LOW_CONFIDENCE':
      return (
        <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1">
              <p className="font-semibold">Revisión Recomendada</p>
              <div className="flex flex-wrap items-center gap-1 text-amber-700/90">
                <span>Detectado: <strong>"{originalName}"</strong></span>
                <ArrowRight className="h-3 w-3" />
                <span>Sugerencia: <strong>"{suggestedName}"</strong></span>
              </div>
              <p className="mt-1 text-xs text-amber-600">
                Confirma si esta suposición es correcta.
              </p>
            </div>
          </div>
        </div>
      );

    case 'NO_MATCH':
      return (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <div className="flex items-start gap-3">
            <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1">
              <p className="font-semibold">Asignatura Desconocida</p>
              <p className="text-red-700/90">
                No se encontró coincidencia para: <strong>"{originalName}"</strong>.
              </p>
              <p className="mt-1 text-xs text-red-600">
                Busca y selecciona la asignatura correcta abajo.
              </p>
            </div>
          </div>
        </div>
      );

    default:
      return null;
  }
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

  // Carga inicial
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
    return () => {
      mounted = false;
    };
  }, []);

  // --- OPCIONES ---
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
      (horarioTemporal.titulo ? horarioTemporal.titulo.split(' - ')[0] : '') ||
      ''
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


  // --- ESTADO LOCAL DEL HORARIO ---
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

  // --- DIÁLOGOS ---
  const [isEditInfoOpen, setIsEditInfoOpen] = React.useState(false);
  // 👇 NUEVO ESTADO: Controla si estamos recalculando los matches
  const [isRefining, setIsRefining] = React.useState(false);
  const [infoForm, setInfoForm] = React.useState({ plan: '', periodo: '' });

  const [editingLocation, setEditingLocation] = React.useState<{ blockIndex: number; sessionIndex: number } | null>(null);
  const [editingForm, setEditingForm] = React.useState<SesionFormState | null>(null);

  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [createTab, setCreateTab] = React.useState<'session' | 'block'>('session');
  const [createSessionForm, setCreateSessionForm] = React.useState<SesionFormState>(DEFAULT_SESSION_FORM);
  const [newBlockForm, setNewBlockForm] = React.useState({ curso: '', mencion: '' });
  
  const [isEditBlockOpen, setIsEditBlockOpen] = React.useState(false);
  const [editBlockForm, setEditBlockForm] = React.useState({ curso: '', mencion: '' });
  
  const canCreateSession = bloques.length > 0;

  // --- HANDLERS ---

  const handleBack = () => {
    if (item && draftHorario) {
      updateHorario(item.id, draftHorario as unknown as HorarioTemporalOut);
      toast({
        title: 'Borrador guardado',
        description: 'Puedes continuar editando más tarde.',
      });
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

  // 👇 FUNCIÓN ACTUALIZADA: RE-MATCHING
  const handleSaveInfo = async () => {
    // 1. Construimos el objeto con los nuevos metadatos
    const horarioActualizado = JSON.parse(JSON.stringify(draftHorario ?? horarioTemporal));
    horarioActualizado.plan = infoForm.plan;
    horarioActualizado.periodo = infoForm.periodo;
    // Combinamos título para asegurar que el Matcher recibe toda la info necesaria
    horarioActualizado.titulo = `${infoForm.plan} - ${infoForm.periodo}`;

    setIsRefining(true);
    try {
        toast({ title: 'Recalculando coincidencias...', description: 'Aplicando nuevo contexto...' });
        
        // 2. LLAMADA AL BACKEND: Recalcular Fuzzy Matches
        const nuevoHorario = await refineHorario(horarioActualizado as unknown as HorarioTemporalOut);

        // 3. Actualizamos el estado local con las nuevas sugerencias
        setDraftHorario(nuevoHorario as unknown as HorarioExtraido);
        
        // 4. Actualizamos el store global
        if (item) {
            updateHorario(item.id, nuevoHorario);
        }

        setIsEditInfoOpen(false);
        toast({ title: 'Horario Actualizado', description: 'Se han recalculado las sugerencias de asignaturas.' });

    } catch (error) {
        console.error(error);
        toast({ 
            title: 'Error', 
            description: 'No se pudieron recalcular las asignaturas. Se han guardado los cambios básicos.', 
            variant: 'destructive' 
        });
        
        // Fallback: Si falla el server, guardamos al menos los textos localmente
        setDraftHorario(horarioActualizado);
        setIsEditInfoOpen(false);
    } finally {
        setIsRefining(false);
    }
  };

  const currentPlanId = React.useMemo(
    () => listaProgramas.find((p) => p.nombre === infoForm.plan)?.id,
    [listaProgramas, infoForm.plan]
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
    
    // PRE-RELLENADO INTELIGENTE
    const nombrePreCargado = sesion.asignatura_sugerida || sesion.asignatura || '';

    setEditingForm({
      asignatura: nombrePreCargado,
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
      const sesion = cloned.horarios[blockIndex]?.sesiones?.[sessionIndex];

      if (!sesion) return prev;

      // Detectar cambio manual
      const haCambiadoNombre = editingForm.asignatura !== sesion.asignatura_sugerida && editingForm.asignatura !== sesion.asignatura;
      
      sesion.asignatura = editingForm.asignatura;
      sesion.aula = editingForm.aula;
      sesion.dia = editingForm.dia;
      sesion.hora_inicio = editingForm.hora_inicio;
      sesion.hora_fin = editingForm.hora_fin;
      sesion.tipo = editingForm.tipo;
      sesion.grupo = editingForm.grupo || null;

      if (haCambiadoNombre) {
        sesion.asignatura_sugerida = editingForm.asignatura;
      }

      return cloned;
    });
    closeEditSesion();
  };

  const openCreateDialog = () => {
    setCreateTab(canCreateSession ? 'session' : 'block');
    setCreateSessionForm(DEFAULT_SESSION_FORM);
    setNewBlockForm({ curso: '', mencion: '' });
    setIsCreateOpen(true);
  };

  const closeCreateDialog = () => setIsCreateOpen(false);

  const handleCreateFieldChange = <K extends keyof SesionFormState>(
    f: K,
    v: SesionFormState[K]
  ) => setCreateSessionForm((p) => ({ ...p, [f]: v }));

  const handleCreateSession = () => {
    if (!canCreateSession) return;

    setDraftHorario((prev) => {
      const source = prev ?? horario;
      if (!source) return prev;

      const cloned = JSON.parse(JSON.stringify(source)) as HorarioExtraido;
      const bloque = cloned.horarios[selectedBlockIndex];

      if (!bloque.sesiones) bloque.sesiones = [];

      bloque.sesiones.push({
        ...createSessionForm,
        grupo: createSessionForm.grupo || null,
        match_status: 'MANUAL',
      });

      return cloned;
    });
    setIsCreateOpen(false);
  };
  const handleCreateBlock = () => {
    const curso = newBlockForm.curso.trim();
    if (!curso) return;

    setDraftHorario((prev) => {
      const source = prev ?? horario;
      if (!source) return prev;

      const cloned = JSON.parse(JSON.stringify(source)) as HorarioExtraido;
      if (!cloned.horarios) cloned.horarios = [];

      cloned.horarios.push({
        curso,
        periodo: cloned.periodo,
        mencion: newBlockForm.mencion || null,
        pagina: cloned.horarios.length,
        sesiones: [],
      });

      return cloned;
    });
    setIsCreateOpen(false);
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
      const sesion = cloned.horarios[Number(blockStr)]?.sesiones?.[Number(sesStr)];

      if (!sesion) return prev;

      const duration = timeToMinutes(sesion.hora_fin) - timeToMinutes(sesion.hora_inicio);
      const startMin = timeToMinutes(newStartTime);

      sesion.dia = DIAS_SEMANA[newDayIndex];
      sesion.hora_inicio = newStartTime;
      sesion.hora_fin = minutesToTimeLabel(startMin + duration);

      return cloned;
    });
  };

  const handleConfirm = async () => {
    if (!horario || !item) return;

    setIsConfirming(true);
    setConfirmError(null);

    try {
      await confirmHorario(horario as unknown as HorarioTemporalOut);
      confirm(item.id);
      toast({ title: 'Horario confirmado', description: 'Guardado en BD.' });
      router.push('/datos/horarios');
    } catch (error: unknown) {
      setConfirmError(error instanceof Error ? error.message : 'Error al confirmar');
      toast({ title: 'Error', variant: 'destructive' });
    } finally {
      setIsConfirming(false);
    }
  };

  if (!item) {
    return (
      <div className="p-8">
        <Card>
          <CardContent className="p-6">Horario no encontrado</CardContent>
        </Card>
      </div>
    );
  }

  if (!horario) {
    return (
      <div className="p-8">
        <Card>
          <CardContent className="p-6">Sin datos</CardContent>
        </Card>
      </div>
    );
  }

  const editingBloque = editingLocation && horario?.horarios
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
            Revisa la información extraída del horario.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleBack}>
            Volver a subidas
          </Button>
          <Button onClick={handleConfirm} disabled={isConfirming || !hasData}>
            {isConfirming ? 'Guardando...' : 'Confirmar horario'}
          </Button>
        </div>
      </div>
      {confirmError && (
        <p className="text-right text-sm text-destructive">{confirmError}</p>
      )}

      <Card
        className="cursor-pointer transition-colors hover:bg-muted/50 group"
        onClick={openEditInfo}
      >
        <CardHeader>
          <CardTitle className="flex justify-between items-center">
            Resumen del horario
            <Pencil className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Plan de estudios</p>
              <p className="text-sm font-medium">{displayPlan}</p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Periodo</p>
              <p className="text-sm font-medium capitalize">
                {displayPeriodo.replace(/_/g, ' ')}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Estadísticas</p>
              <p className="text-sm font-medium">
                {bloques.length} horarios · {totalSessions} sesiones
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 rounded-md border bg-muted/40 px-4 py-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-medium text-muted-foreground">
              Selecciona el curso/mención:
            </p>
            <div className="flex flex-wrap gap-2">
              {bloques.map((b, i) => (
                <Button
                  key={i}
                  size="sm"
                  variant={i === selectedBlockIndex ? 'default' : 'outline'}
                  onClick={() => setSelectedBlockIndex(i)}
                >
                  {buildBloqueLabel(b)}
                </Button>
              ))}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            size="icon"
            variant="outline"
            onClick={openEditBlockDialog}
            disabled={!bloques.length}
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button size="icon" onClick={openCreateDialog}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {hasData && (
        <InteractiveScheduleGrid
          sessions={sessions}
          onSessionClick={openEditSesion}
          onSessionMove={handleSessionMove}
        />
      )}

      {/* --- DIALOGO 1: EDITAR INFO (CON LOADING) --- */}
      <Dialog open={isEditInfoOpen} onOpenChange={setIsEditInfoOpen}>
        <DialogContent className="overflow-visible">
          <DialogHeader>
            <DialogTitle>Editar información</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Plan de estudios</Label>
              <SimpleAutocomplete
                options={programasOptions}
                value={currentPlanId}
                initialValue={infoForm.plan}
                onChange={(val) => {
                  const selected = programasOptions.find((p) => p.value === val);
                  if (selected) {
                    setInfoForm({ ...infoForm, plan: selected.label });
                  }
                }}
                placeholder="Buscar grado/máster..."
                emptyText="No se encontraron titulaciones"
              />
              {!currentPlanId && infoForm.plan && (
                <p className="text-xs text-amber-600">
                  Valor actual: "{infoForm.plan}" (No registrado en BD)
                </p>
              )}
            </div>

            <div className="grid gap-2">
              <Label>Periodo</Label>
              <select
                className="flex h-9 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                value={infoForm.periodo}
                onChange={(e) =>
                  setInfoForm({ ...infoForm, periodo: e.target.value })
                }
              >
                <option value="" disabled>
                  Seleccionar periodo...
                </option>
                {PERIODOS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
                {infoForm.periodo &&
                  !PERIODOS.some((p) => p.value === infoForm.periodo) && (
                    <option value={infoForm.periodo}>{infoForm.periodo}</option>
                  )}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={handleSaveInfo} disabled={isRefining}>
                {isRefining ? (
                    <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Recalculando asignaturas...
                    </>
                ) : (
                    'Guardar y Recalcular'
                )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* --- DIALOGO 2: EDITAR SESIÓN (CON TARJETA INFO) --- */}
      <Dialog open={isEditOpen} onOpenChange={(open) => !open && closeEditSesion()}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Editar sesión</DialogTitle>
          </DialogHeader>

          {editingBloque && editingLocation && (
            <MatchInfoCard 
              status={editingBloque.sesiones[editingLocation.sessionIndex].match_status}
              originalName={editingBloque.sesiones[editingLocation.sessionIndex].asignatura}
              suggestedName={editingBloque.sesiones[editingLocation.sessionIndex].asignatura_sugerida}
            />
          )}

          {editingForm && (
            <SessionFormFieldsSmart
              form={editingForm}
              onChange={handleEditFieldChange}
              asignaturaOptions={asignaturaOptions}
              aulaOptions={aulaOptions}
            />
          )}
          
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={closeEditSesion}>
              Cancelar
            </Button>
            <Button onClick={handleSaveSesion}>Guardar cambios</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      <Dialog open={isCreateOpen} onOpenChange={(open) => !open && closeCreateDialog()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Crear elemento</DialogTitle>
          </DialogHeader>
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
            <SessionFormFieldsSmart
              form={createSessionForm}
              onChange={handleCreateFieldChange}
              asignaturaOptions={asignaturaOptions}
              aulaOptions={aulaOptions}
            />
          )}
          {createTab === 'block' && (
            <div className="space-y-3 py-2 text-sm">
              <div className="grid gap-2">
                <Label>Curso</Label>
                <Input
                  value={newBlockForm.curso}
                  onChange={(e) =>
                    setNewBlockForm({ ...newBlockForm, curso: e.target.value })
                  }
                  placeholder="1º, 2º..."
                />
              </div>
              <div className="grid gap-2">
                <Label>Mención</Label>
                <Input
                  value={newBlockForm.mencion}
                  onChange={(e) =>
                    setNewBlockForm({ ...newBlockForm, mencion: e.target.value })
                  }
                />
              </div>
            </div>
          )}
          <DialogFooter className="mt-4">
            {createTab === 'session' ? (
              <Button onClick={handleCreateSession} disabled={!canCreateSession}>
                Crear sesión
              </Button>
            ) : (
              <Button onClick={handleCreateBlock} disabled={!newBlockForm.curso}>
                Crear horario
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isEditBlockOpen} onOpenChange={setIsEditBlockOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar horario</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2 text-sm">
            <div className="grid gap-2">
              <Label>Curso</Label>
              <Input
                value={editBlockForm.curso}
                onChange={(e) =>
                  setEditBlockForm({ ...editBlockForm, curso: e.target.value })
                }
              />
            </div>
            <div className="grid gap-2">
              <Label>Mención</Label>
              <Input
                value={editBlockForm.mencion}
                onChange={(e) =>
                  setEditBlockForm({ ...editBlockForm, mencion: e.target.value })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button onClick={handleSaveBlock}>Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SessionFormFieldsSmart({
  form,
  onChange,
  asignaturaOptions,
  aulaOptions,
}: {
  form: SesionFormState;
  onChange: <K extends keyof SesionFormState>(f: K, v: SesionFormState[K]) => void;
  asignaturaOptions: AutocompleteOption[];
  aulaOptions: AutocompleteOption[];
}) {
  const selectedAsigId = React.useMemo(
    () => asignaturaOptions.find((opt) => opt.label === form.asignatura)?.value,
    [asignaturaOptions, form.asignatura]
  );
  const selectedAulaId = React.useMemo(
    () => aulaOptions.find((opt) => opt.label === form.aula)?.value,
    [aulaOptions, form.aula]
  );

  return (
    <div className="space-y-3 py-2 text-sm">
      <div className="grid gap-2">
        <Label>Asignatura</Label>
        <SimpleAutocomplete
          options={asignaturaOptions}
          value={selectedAsigId}
          initialValue={form.asignatura}
          onChange={(val) => {
            const selected = asignaturaOptions.find((o) => o.value === val);
            if (selected) onChange('asignatura', selected.label);
          }}
          placeholder="Introducir asignatura..."
          emptyText="No encontrada en este plan"
        />
        {!selectedAsigId && form.asignatura && (
          <p className="text-xs text-amber-600">
            Valor actual: "{form.asignatura}" (No está en la BD)
          </p>
        )}
      </div>
      <div className="grid gap-2">
        <Label>Aula</Label>
        <SimpleAutocomplete
          options={aulaOptions}
          value={selectedAulaId}
          initialValue={form.aula}
          onChange={(val) => {
            const selected = aulaOptions.find((o) => o.value === val);
            if (selected) onChange('aula', selected.label);
          }}
          placeholder="Introducir aula..."
        />
      </div>
      <div className="grid gap-2">
        <Label>Día</Label>
        <select
          className="h-9 rounded-md border px-3"
          value={form.dia}
          onChange={(e) => onChange('dia', e.target.value)}
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
          <Label>Inicio</Label>
          <Input
            type="time"
            value={form.hora_inicio}
            onChange={(e) => onChange('hora_inicio', e.target.value)}
          />
        </div>
        <div className="grid gap-2">
          <Label>Fin</Label>
          <Input
            type="time"
            value={form.hora_fin}
            onChange={(e) => onChange('hora_fin', e.target.value)}
          />
        </div>
      </div>
      <div className="grid gap-2">
        <Label>Tipo</Label>
        <select
          className="h-9 rounded-md border px-3"
          value={form.tipo}
          onChange={(e) => onChange('tipo', e.target.value)}
        >
          {TIPO_OPCIONES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>
      <div className="grid gap-2">
        <Label>Grupo</Label>
        <Input
          value={form.grupo}
          onChange={(e) => onChange('grupo', e.target.value)}
          placeholder="PL1, PA..."
        />
      </div>
    </div>
  );
}

// Helpers
function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function mapHorarioToSessions(horario: HorarioExtraido): Session[] {
  const sessions: Session[] = [];
  (horario.horarios || []).forEach((b, i) =>
    sessions.push(...mapBloqueToSessions(b, i))
  );
  return sessions;
}

// 🔥 FUNCIÓN IMPRESCINDIBLE PARA VER LOS COLORES RECALCULADOS
function mapBloqueToSessions(
  bloque: HorarioExtraidoBloque,
  bloqueIndex: number
): Session[] {
  const sessions: Session[] = [];
  (bloque.sesiones || []).forEach((sesion, sesionIndex) => {
    const dayIndex = diaToDayIndex(sesion.dia);
    if (dayIndex < 0) return;

    // 1. Determinar el color según el Status del Matcher
    let color: Session['color'] = 'blue';

    switch (sesion.match_status) {
      case 'EXACT':
      case 'ALIAS_DB':
        // Azul: Confirmado (Exacto o Alias conocido)
        color = 'blue'; 
        break;
      
      case 'FUZZY_AUTO':
        // Verde: Predicción Alta Confianza
        color = 'green'; 
        break;

      case 'FUZZY_LOW_CONFIDENCE':
        // Naranja: Revisión
        color = 'orange';
        break;

      case 'NO_MATCH':
      default:
        // Rojo: Error / No encontrado
        color = 'red';
        break;
    }

    // 2. Determinar el título a mostrar en el Grid
    const isError = color === 'red';
    const dbName = sesion.asignatura_sugerida;
    const rawName = sesion.asignatura;
    
    // Si hay sugerencia (verde/naranja/azul), usamos esa.
    const displayTitle = isError ? rawName : (dbName || rawName || 'Sin nombre');

    sessions.push({
      id: `${bloqueIndex}-${sesionIndex}`,
      courseId: buildCourseIdFromCurso(bloque.curso),
      dayIndex,
      start: normalizeTime(sesion.hora_inicio),
      end: normalizeTime(sesion.hora_fin),
      
      title: displayTitle, 
      room: sesion.aula ?? '—',
      teacher: sesion.grupo ? `Grupo ${sesion.grupo}` : '',
      
      color: color,
      
      // Pasamos metadatos para la tarjeta de info (MatchInfoCard)
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
  return parts.length >= 2
    ? `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}`
    : value;
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
  if (cursoTexto.includes('1') || cursoTexto.toLowerCase().includes('primer')) {
    return '1º';
  }
  if (cursoTexto.includes('2') || cursoTexto.toLowerCase().includes('segundo')) {
    return '2º';
  }
  if (cursoTexto.includes('3') || cursoTexto.toLowerCase().includes('tercer')) {
    return '3º';
  }
  if (cursoTexto.includes('4') || cursoTexto.toLowerCase().includes('cuarto')) {
    return '4º';
  }
  return cursoTexto;
}

function buildBloqueLabel(bloque: HorarioExtraidoBloque): string {
  const base = buildCourseIdFromCurso(bloque.curso);
  if (!bloque.mencion) return base;
  return `${base} - ${bloque.mencion.replace(/MENCI[ÓO]N\s+EN\s+/i, 'Mención ')}`;
}