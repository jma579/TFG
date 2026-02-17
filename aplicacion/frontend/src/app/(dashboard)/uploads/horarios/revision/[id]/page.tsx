'use client';

import { 
  AlertCircle,
  ArrowRight, 
  CheckCircle2, 
  Pencil, 
  Plus, 
  Sparkles, 
  Trash2,
  XCircle
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import * as React from 'react';

import { InteractiveScheduleGrid } from '@/components/solver/interactive-schedule-grid';
import { 
  ReviewBlock,
  ReviewDashboard 
} from '@/components/solver/review-dashboard';
import type { Session } from '@/components/solver/schedule-grid';
import { Button } from '@/components/ui/button';
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { 
  Dialog, 
  DialogContent, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  type AutocompleteOption,
  SimpleAutocomplete 
} from '@/components/ui/simple-autocomplete';
import { useToast } from '@/hooks/use-toast';
import { 
  type AsignaturaOut,
  listAsignaturas 
} from '@/lib/api/catalogo/asignaturas';
import { 
  listProgramas, 
  type ProgramaOut 
} from '@/lib/api/catalogo/programas';
import { 
  confirmHorario, 
  type HorarioTemporalOut,
  refineHorario 
} from '@/lib/api/docencia/horarios';
import { 
  type AulaOut,
  listAulas 
} from '@/lib/api/recursos/aulas';
import { PERIODOS } from '@/lib/constants/periodos';
import { useHorariosUploadsStore } from '@/stores/horarios-uploads';

// ============================================================================
// TIPOS
// ============================================================================

type RouteParams = { id: string };
type Props = { params: Promise<RouteParams> };

export type HorarioExtraido = {
  titulo: string;
  plan: string;
  periodo: string;
  horarios: HorarioExtraidoBloque[];
};

export type HorarioExtraidoBloque = {
  curso: string;
  periodo: string;
  mencion: string | null;
  pagina: number;
  sesiones: HorarioExtraidoSesion[];
};

export type HorarioExtraidoSesion = {
  asignatura: string;
  aula: string;
  dia: string;
  hora_inicio: string;
  hora_fin: string;
  tipo: string;
  grupo: string | null;
  grupo_codigo?: string | null; 
  match_confidence?: number;
  match_status?: string;       
  asignatura_sugerida?: string;
  manual_validated?: boolean;
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

// ============================================================================
// CONSTANTES
// ============================================================================

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
  'PRÁCTICAS DE LABORATORIO'
] as const;

const DIAS_SEMANA = [
  'LUNES', 
  'MARTES', 
  'MIÉRCOLES', 
  'JUEVES', 
  'VIERNES'
] as const;

const API_PAGE_SIZE = 1000;

// ============================================================================
// SUBCOMPONENTES
// ============================================================================

/**
 * Tarjeta informativa sobre el estado de coincidencia de una asignatura
 */
function MatchInfoCard({ status, originalName, suggestedName }: { status?: string; originalName: string; suggestedName?: string }) {
  if (!status) return null;
  const isExact = status === 'EXACT' || status === 'ALIAS_DB';
  if (isExact) {
      return (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1"><p className="font-semibold">Coincidencia Exacta</p></div>
          </div>
        </div>
      );
  }
  if (suggestedName) {
      return (
        <div className="mb-4 rounded-md border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-800">
          <div className="flex items-start gap-3">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="space-y-1"><p className="font-semibold">Sugerencia Automática</p>
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
        <div className="space-y-1"><p className="font-semibold">Sin Coincidencia</p></div>
      </div>
    </div>
  );
}

export default function RevisionHorarioPage({ params }: Props) {
  const { id } = React.use(params);
  const router = useRouter();
  const { toast } = useToast();

  const { items, updateHorario, confirm } = useHorariosUploadsStore();

  const item = React.useMemo(() => items.find((it) => it.id === id), [items, id]);

  const horarioTemporal: HorarioExtraido | undefined =
    item?.horarioTemporal as HorarioExtraido | undefined;

  // Estados de datos maestros
  const [listaAsignaturas, setListaAsignaturas] = React.useState<AsignaturaOut[]>([]);
  const [listaAulas, setListaAulas] = React.useState<AulaOut[]>([]);
  const [listaProgramas, setListaProgramas] = React.useState<ProgramaOut[]>([]);
  const [loadingError, setLoadingError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let mounted = true;
    
    async function loadData() {
      try {
        setLoadingError(null);
        const [resProgramas, resAsig, resAulas] = await Promise.all([
          listProgramas({ limit: API_PAGE_SIZE, activo: true }), 
          listAsignaturas({ limit: API_PAGE_SIZE, activo: true }), 
          listAulas({ size: API_PAGE_SIZE }),
        ]);
        
        if (mounted) {
          setListaProgramas(resProgramas.items || []);
          setListaAsignaturas(resAsig.items || []);
          setListaAulas(resAulas.items || []);
        }
      } catch (error) {
        console.error('Error cargando catálogo:', error);
        if (mounted) {
          setLoadingError('No se pudieron cargar los catálogos. Verifica la conexión.');
          toast({
            title: 'Error de carga',
            description: 'No se pudieron cargar los catálogos necesarios.',
            variant: 'destructive'
          });
        }
      }
    }
    
    loadData();
    return () => { mounted = false; };
  }, [toast]);

  const [draftHorario, setDraftHorario] = React.useState<HorarioExtraido | null>(null);

  React.useEffect(() => {
    if (horarioTemporal) {
      const cloned = JSON.parse(JSON.stringify(horarioTemporal)) as HorarioExtraido;
      setDraftHorario(cloned);
    }
  }, [horarioTemporal]);

  const horario = draftHorario ?? horarioTemporal;
  
  // Estados de UI
  const [isConfirming, setIsConfirming] = React.useState(false);
  const [confirmError, setConfirmError] = React.useState<string | null>(null);
  const [selectedBlockIndex, setSelectedBlockIndex] = React.useState(0);

  // Memoizaciones
  const bloques = React.useMemo(
    () => (horario?.horarios ?? []) as HorarioExtraidoBloque[], 
    [horario]
  );
  const unifiedNamesMap = React.useMemo(() => {
    const map = new Map<string, string>();
    if (!horario) return map;
    
    horario.horarios.forEach(bloque => {
      bloque.sesiones.forEach(sesion => {
        const raw = normalizeText(sesion.asignatura || '');
        if (sesion.asignatura_sugerida && raw) {
          map.set(raw, sesion.asignatura_sugerida);
        }
      });
    });
    return map;
  }, [horario]);

  const totalSessions = React.useMemo(() => {
    if (!horario) return 0;
    return mapHorarioToSessions(horario, unifiedNamesMap).length;
  }, [horario, unifiedNamesMap]);

  const sessions = React.useMemo<Session[]>(() => {
    if (!horario || bloques.length === 0) return [];
    const bloque = bloques[selectedBlockIndex];
    if (!bloque) return [];
    return mapBloqueToSessions(bloque, unifiedNamesMap);
  }, [bloques, horario, selectedBlockIndex, unifiedNamesMap]);

  const reviewBlock = React.useMemo(() => {
    if (!horario || bloques.length === 0) return null;
    const bloque = bloques[selectedBlockIndex];
    if (!bloque) return null;
    
    return {
      ...bloque,
      sesiones: bloque.sesiones.map((s, idx) => ({
        ...s,
        originalIndex: idx
      }))
    } as ReviewBlock;
  }, [bloques, horario, selectedBlockIndex]);

  const hasData = Boolean(horario && bloques.length > 0);
  const displayPlan = horario?.plan || horario?.titulo?.split(' - ')[0] || "Desconocido";

  // Estados de formularios
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

  // Detección de programa y periodo
  const detectedPrograma = React.useMemo(() => {
    if (!horario || !listaProgramas.length) return null;
    const planTexto = normalizeText(horario.plan || horario.titulo?.split(' - ')[0] || '');
    const exacto = listaProgramas.find(p => normalizeText(p.nombre) === planTexto);
    if (exacto) return exacto;
    const aprox = listaProgramas.find(p => {
        const pNombre = normalizeText(p.nombre);
        return pNombre.includes(planTexto) || planTexto.includes(pNombre);
    });
    return aprox || null;
  }, [horario, listaProgramas]);

  const detectedPeriodo = React.useMemo(() => {
      const texto = horario?.periodo || horario?.titulo?.split(' - ')[1] || '';
      return normalizeText(texto);
  }, [horario]);

  const getAsignaturaOptionsForBlock = React.useCallback((blockIdx: number): AutocompleteOption[] => {
      const bloque = bloques[blockIdx];
      if (!bloque) return [];

      if (!detectedPrograma) {
          return listaAsignaturas.map(a => ({ value: a.id, label: a.nombre, keywords: a.codigo_plan }));
      }

      const cursoNum = parseCursoNumerico(bloque.curso);
      const planNameNorm = normalizeText(detectedPrograma.nombre);
      
      const filtradas = listaAsignaturas.filter(asig => {
            if (!asig.titulaciones || asig.titulaciones.length === 0) return false; 

            const matchProgCurso = asig.titulaciones.some(t => {
                const pid = t.programa?.id;
                const matchId = pid != null && pid === detectedPrograma.id;
                const tProgName = normalizeText(t.programa.nombre || '');
                const matchName = tProgName.includes(planNameNorm) || planNameNorm.includes(tProgName);
                const isSameProgram = matchId || matchName;
                const c = t.curso;
                const matchCurso = c === null || c === undefined || c === cursoNum;
                return isSameProgram && matchCurso;
            });

            if (!matchProgCurso) return false;

            if (asig.periodo) {
                const pAsig = normalizeText(asig.periodo);
                if (pAsig.includes('anual')) return true;
                const esPrimero = detectedPeriodo.includes('primer') || detectedPeriodo.includes('1');
                const esSegundo = detectedPeriodo.includes('segundo') || detectedPeriodo.includes('2');
                if (esPrimero) {
                    return pAsig.includes('primer') || pAsig.includes('1') || pAsig.includes('s1');
                }
                if (esSegundo) {
                    return pAsig.includes('segundo') || pAsig.includes('2') || pAsig.includes('s2');
                }
                if (detectedPeriodo) {
                    return pAsig.includes(detectedPeriodo) || detectedPeriodo.includes(pAsig);
                }
            }
            return true;
        });

        return filtradas.map(a => ({ value: a.id, label: a.nombre, keywords: a.codigo_plan }));

  }, [listaAsignaturas, bloques, detectedPrograma, detectedPeriodo]);

  const activeAsignaturaOptions = React.useMemo(() => {
      return getAsignaturaOptionsForBlock(selectedBlockIndex);
  }, [getAsignaturaOptionsForBlock, selectedBlockIndex]);

  const currentPlanId = React.useMemo(() => {
    return listaProgramas.find((p) => p.nombre === infoForm.plan)?.id;
  }, [listaProgramas, infoForm.plan]);

  const programasOptions = React.useMemo(() => listaProgramas.map((p) => ({
      value: p.id,
      label: p.nombre,
      keywords: p.tipo,
  })), [listaProgramas]);

  const aulaOptions = React.useMemo(() => listaAulas.map((a) => ({
      value: a.id,
      label: a.nombre,
      keywords: a.codigo,
  })), [listaAulas]);

  /**
   * Determina si una asignatura es común/troncal basándose en el catálogo
   */
  const checkIsAsignaturaComun = React.useCallback((nombreAsignatura: string) => {
    if (!detectedPrograma || !listaAsignaturas.length) return false;
    
    const norm = normalizeText(nombreAsignatura);
    const found = listaAsignaturas.find(a => normalizeText(a.nombre) === norm);
    
    if (!found?.titulaciones) return false;

    const vinculacion = found.titulaciones.find(
      t => t.programa?.id === detectedPrograma.id
    );
    if (!vinculacion) return false;

    // Acceso seguro al tipo de asignatura
    type TitulacionConTipo = typeof vinculacion & { 
      tipo?: string; 
      tipo_asignatura?: string; 
    };
    
    const tipo = (
      (vinculacion as TitulacionConTipo).tipo || 
      (vinculacion as TitulacionConTipo).tipo_asignatura || 
      ''
    ).toString().toUpperCase();
    
    return tipo.includes('BASICA') || 
           tipo.includes('BÁSICA') || 
           tipo.includes('OBLIGATORIA') || 
           tipo.includes('TRONCAL');
  }, [listaAsignaturas, detectedPrograma]);

  // ========================================================================
  // HANDLERS
  // ========================================================================

  const handleUpdateDraft = (newHorario: HorarioExtraido) => {
    setDraftHorario(newHorario);
    if (item) {
      updateHorario(item.id, newHorario as HorarioTemporalOut);
    }
  };

  const handleBack = () => {
    if (item && draftHorario) {
      updateHorario(item.id, draftHorario as HorarioTemporalOut);
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
      const nuevoHorario = await refineHorario(horarioActualizado as HorarioTemporalOut);
      handleUpdateDraft(nuevoHorario as HorarioExtraido);
      setIsEditInfoOpen(false);
      toast({ 
        title: 'Horario Actualizado', 
        description: 'Contexto actualizado correctamente.' 
      });
    } catch (error) {
      console.error('Error refinando horario:', error);
      handleUpdateDraft(horarioActualizado);
      setIsEditInfoOpen(false);
      toast({
        title: 'Advertencia',
        description: 'Se guardaron los cambios pero no se pudo refinar automáticamente.',
        variant: 'destructive'
      });
    } finally {
      setIsRefining(false);
    }
  };
  const handleDeleteSession = (sesIndex: number) => {
    if (!draftHorario) return;
    const cloned = JSON.parse(JSON.stringify(draftHorario)) as HorarioExtraido;
    
    const targetBlock = cloned.horarios[selectedBlockIndex];
    if (!targetBlock?.sesiones?.[sesIndex]) return;
    
    const targetSession = targetBlock.sesiones[sesIndex];
    const targetId = generateSemanticId(targetSession, unifiedNamesMap);
    const targetCurso = targetBlock.curso;

    // Verificar si es común
    const nombreOficial = targetSession.asignatura_sugerida || targetSession.asignatura;
    const esComun = checkIsAsignaturaComun(nombreOficial);

    let deletedCount = 0;

    if (esComun) {
      cloned.horarios.forEach(bloque => {
        if (bloque.curso !== targetCurso) return; 
        const prevLen = bloque.sesiones.length;
        bloque.sesiones = bloque.sesiones.filter(s => 
          generateSemanticId(s, unifiedNamesMap) !== targetId
        );
        if (bloque.sesiones.length < prevLen) deletedCount++;
      });
      toast({ 
        title: 'Eliminada', 
        description: `Sesión común eliminada de ${deletedCount} grupo(s).` 
      });
    } else {
      if (targetBlock.sesiones) {
        targetBlock.sesiones.splice(sesIndex, 1);
        deletedCount = 1;
      }
      toast({ 
        title: 'Eliminada', 
        description: 'Sesión eliminada de este horario.' 
      });
    }

    handleUpdateDraft(cloned);
  };

  const handleDeleteFromModal = () => {
    if (!editingLocation) return;
    handleDeleteSession(editingLocation.sessionIndex);
    closeEditSesion();
  };

  const openEditSesion = (session: Session) => {
    if (!horario) return;
    
    const bloque = horario.horarios[selectedBlockIndex];
    const sessionIndex = bloque.sesiones.findIndex(s => 
      generateSemanticId(s, unifiedNamesMap) === session.id
    );
    
    if (sessionIndex === -1) return; 

    const sesion = bloque.sesiones[sessionIndex];
    if (!sesion) return;

    setEditingLocation({ blockIndex: selectedBlockIndex, sessionIndex });
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
      const updates = {
        asignatura: editingForm.asignatura,
        aula: editingForm.aula,
        dia: editingForm.dia,
        hora_inicio: editingForm.hora_inicio,
        hora_fin: editingForm.hora_fin,
        tipo: editingForm.tipo,
        grupo: editingForm.grupo || null,
        manual_validated: true,
        asignatura_sugerida: editingForm.asignatura 
      };
      Object.assign(sesion, updates);

      // PROPAGACIÓN DE EDICIÓN (Solo si es común o comparte ID previamente)
      // Simplificación: Propagamos si coincide nombre y grupo en el mismo curso
      const targetName = normalizeText(updates.asignatura || '');
      const targetGroup = normalizeText(updates.grupo || '');
      const esComun = checkIsAsignaturaComun(updates.asignatura);

      if (esComun) {
          cloned.horarios.forEach((bloque, idx) => {
            if (idx === blockIndex) return; 
            if (bloque.curso !== cloned.horarios[blockIndex].curso) return;

            bloque.sesiones.forEach(s => {
              const sName = normalizeText(s.asignatura_sugerida || s.asignatura || '');
                      const sGroup = normalizeText(s.grupo || '');
              
              if (sName === targetName && sGroup === targetGroup) {
                s.dia = updates.dia;
                s.hora_inicio = updates.hora_inicio;
                s.hora_fin = updates.hora_fin;
                s.aula = updates.aula;
              }
            });
          });
      }
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
    const currentBlock = cloned.horarios[selectedBlockIndex];
    
    const newSession = {
      ...createSessionForm,
      grupo: createSessionForm.grupo || null,
      match_status: 'MANUAL',
      manual_validated: true,
      asignatura_sugerida: createSessionForm.asignatura
    };

    const targetCurso = currentBlock.curso;
    const esComun = checkIsAsignaturaComun(newSession.asignatura);
    
    let addedCount = 0;

    if (!currentBlock.sesiones) currentBlock.sesiones = [];
    currentBlock.sesiones.push(JSON.parse(JSON.stringify(newSession)));
    addedCount++;

    if (esComun) {
      cloned.horarios.forEach((bloque, idx) => {
        if (idx === selectedBlockIndex) return;
        if (bloque.curso !== targetCurso) return;

        if (!bloque.sesiones) bloque.sesiones = [];
        bloque.sesiones.push(JSON.parse(JSON.stringify(newSession)));
        addedCount++;
      });
    }

    handleUpdateDraft(cloned);
    setIsCreateOpen(false);
    
    if (esComun && addedCount > 1) {
      toast({ 
        title: 'Creada', 
        description: `Sesión común añadida a ${addedCount} grupos.` 
      });
    } else {
      toast({ 
        title: 'Creada', 
        description: `Sesión añadida a este grupo.` 
      });
    }
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
    
    const targetId = session.id; 
    let updatedCount = 0;

    cloned.horarios.forEach((bloque) => {
      bloque.sesiones.forEach((sesion) => {
        const currentId = generateSemanticId(sesion, unifiedNamesMap);
        
        if (currentId === targetId) {
          const duration = timeToMinutes(sesion.hora_fin) - timeToMinutes(sesion.hora_inicio);
          const startMin = timeToMinutes(newStartTime);
          
          sesion.dia = DIAS_SEMANA[newDayIndex];
          sesion.hora_inicio = newStartTime;
          sesion.hora_fin = minutesToTimeLabel(startMin + duration);
          
          updatedCount++;
        }
      });
    });
    
    if (updatedCount > 0) {
      handleUpdateDraft(cloned);
    }
  };

  const handleConfirm = async () => {
    if (!horario || !item) return;
    
    // 1. Validar integridad localmente antes de enviar
    const hasInvalidSessions = horario.horarios?.some(tabla => 
      tabla.sesiones.some(s => {
        if (!s.hora_inicio || !s.hora_fin) return false;
        return s.hora_inicio >= s.hora_fin;
      })
    );

    if (hasInvalidSessions) {
      toast({ 
        title: 'Error de validación',
        description: 'No se puede confirmar: Hay sesiones con horarios inválidos (inicio >= fin). Por favor, corrígelas en la rejilla.',
        variant: 'destructive'
      });
      return;
    }

    setIsConfirming(true);
    setConfirmError(null); 
    try {
      const planAEnviar = horario.plan || horario.titulo?.split(' - ')[0] || "";
      const payload = { ...horario, plan: planAEnviar };
      await confirmHorario(payload as HorarioTemporalOut);
      confirm(item.id);
      toast({ 
        title: '¡Éxito!', 
        description: 'El horario se ha guardado correctamente.' 
      });
      router.push('/uploads/horarios'); 
    } catch (error: unknown) {
      const msg = (error as { 
        response?: { data?: { detail?: string } }; 
        message?: string;
      })?.response?.data?.detail 
        || (error as { message?: string })?.message 
        || 'Error desconocido al confirmar.';
      setConfirmError(msg); 
      toast({ 
        title: 'No se puede guardar', 
        description: 'Revisa los errores.', 
        variant: 'destructive' 
      });
    } finally {
      setIsConfirming(false);
    }
  };

  // ========================================================================
  // RENDER
  // ========================================================================

  if (!item || !horario) {
    return (
      <div className="p-8">
        <Card>
          <CardContent className="p-6">
            Cargando horario...
          </CardContent>
        </Card>
      </div>
    );
  }

  const editingBloque = editingLocation && horario?.horarios ? horario.horarios[editingLocation.blockIndex] : null;

  const editingOptions = editingLocation 
    ? getAsignaturaOptionsForBlock(editingLocation.blockIndex) 
    : activeAsignaturaOptions;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
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

      {/* Error de carga de catálogos */}
      {loadingError && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-amber-900 mb-1">
                Advertencia
              </h3>
              <p className="text-sm text-amber-700">{loadingError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Error de confirmación */}
      {confirmError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 animate-in slide-in-from-top-2">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
            <div className="flex-1"><h3 className="font-semibold text-red-900 mb-1">No se pudo confirmar</h3><p className="text-sm text-red-700">{confirmError}</p></div>
            <Button variant="ghost" size="sm" className="text-red-500" onClick={() => setConfirmError(null)}>Cerrar</Button>
          </div>
        </div>
      )}

      {/* Tarjeta de resumen */}
      <Card className="cursor-pointer hover:bg-muted/50 group" onClick={openEditInfo}>
        <CardHeader><CardTitle className="flex justify-between">Resumen <Pencil className="h-4 w-4 opacity-0 group-hover:opacity-100" /></CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            <div><p className="text-xs text-muted-foreground">Plan Detectado</p><p className="font-medium text-primary">{displayPlan}</p></div>
            <div><p className="text-xs text-muted-foreground">Total</p><p className="font-medium">{bloques.length} cursos · {totalSessions} sesiones</p></div>
          </div>
        </CardContent>
      </Card>

      {/* Selector de bloques */}
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

      {/* Dashboard de revisión */}
      {hasData && reviewBlock && (
        <ReviewDashboard 
          bloque={reviewBlock}
          onEditSession={(idx) => {
            const sesion = bloques[selectedBlockIndex].sesiones[idx];
            const fakeSession: Session = { 
              id: generateSemanticId(sesion, unifiedNamesMap),
              courseId: '',
              dayIndex: 0,
              start: '',
              end: '',
              title: '',
              room: '',
              teacher: '',
              color: 'blue'
            };
            openEditSesion(fakeSession);
          }}
          onDeleteSession={handleDeleteSession}
        />
      )}

      {/* Grid interactivo */}
      {hasData && (
        <InteractiveScheduleGrid
          sessions={sessions}
          onSessionClick={openEditSesion}
          onSessionMove={handleSessionMove}
        />
      )}

      {/* Diálogos */}
      
      {/* Dialog: Editar información general */}
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

      {/* Dialog: Editar sesión */}
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
            <SessionFormFieldsSmart 
              form={editingForm} 
              onChange={handleEditFieldChange} 
              asignaturaOptions={editingOptions} 
              aulaOptions={aulaOptions} 
            />
          )}
          <DialogFooter className="mt-4 flex flex-col-reverse sm:flex-row sm:justify-between gap-2">
            <Button 
              type="button"
              variant="ghost" 
              className="text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={handleDeleteFromModal}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Eliminar Sesión
            </Button>
            <div className="flex flex-col-reverse sm:flex-row gap-2">
              <Button variant="outline" onClick={closeEditSesion}>Cancelar</Button>
              <Button onClick={handleSaveSesion}>Guardar Cambios</Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Crear elemento */}
      <Dialog open={isCreateOpen} onOpenChange={(open) => !open && closeCreateDialog()}>
        <DialogContent>
          <DialogHeader><DialogTitle>Crear elemento</DialogTitle></DialogHeader>
          <div className="mb-4 flex gap-2">
            <Button size="sm" variant={createTab === 'session' ? 'default' : 'secondary'} disabled={!canCreateSession} onClick={() => setCreateTab('session')}>Nueva sesión</Button>
            <Button size="sm" variant={createTab === 'block' ? 'default' : 'secondary'} onClick={() => setCreateTab('block')}>Nuevo horario</Button>
          </div>
          {createTab === 'session' && (
            <SessionFormFieldsSmart 
              form={createSessionForm} 
              onChange={handleCreateFieldChange} 
              asignaturaOptions={activeAsignaturaOptions} 
              aulaOptions={aulaOptions} 
            />
          )}
          {createTab === 'block' && (
            <div className="space-y-3 py-2 text-sm">
              <div className="grid gap-2"><Label>Curso</Label><Input value={newBlockForm.curso} onChange={(e) => setNewBlockForm({ ...newBlockForm, curso: e.target.value })} /></div>
              <div className="grid gap-2"><Label>Mención</Label><Input value={newBlockForm.mencion} onChange={(e) => setNewBlockForm({ ...newBlockForm, mencion: e.target.value })} /></div>
            </div>
          )}
          <DialogFooter className="mt-4">
            {createTab === 'session' ? (
              <Button onClick={handleCreateSession} disabled={!canCreateSession}>
                Crear
              </Button>
            ) : (
              <Button onClick={handleCreateBlock} disabled={!newBlockForm.curso}>
                Crear
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog: Editar bloque */}
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

// ============================================================================
// COMPONENTES AUXILIARES
// ============================================================================

/**
 * Formulario inteligente para editar/crear sesiones
 */
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
        <SimpleAutocomplete 
          options={asignaturaOptions} 
          value={selectedAsigId} 
          initialValue={form.asignatura} 
          onChange={(val) => {
            const selected = asignaturaOptions.find((o) => o.value === val);
            if (selected) onChange('asignatura', selected.label);
          }} 
          placeholder="Buscar..." 
          emptyText="No se encontraron asignaturas"
        />
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
          placeholder="Buscar..." 
        />
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

// ============================================================================
// FUNCIONES AUXILIARES
// ============================================================================

/**
 * Genera un ID semántico único para una sesión basado en sus atributos
 */
function generateSemanticId(sesion: HorarioExtraidoSesion, unifiedMap: Map<string, string>): string {
  const rawName = normalizeText(sesion.asignatura || '');
  const unifiedName = unifiedMap.get(rawName) || rawName || 'UNK';
  
  const sName = unifiedName.trim().toUpperCase().replace(/\s+/g, '_');
  const sType = (sesion.tipo || 'GEN').trim().toUpperCase().replace(/\s+/g, '_');
  
  const groupSource = sesion.grupo_codigo || sesion.grupo || 'U';
  const sGroup = groupSource.trim().toUpperCase().replace(/\s+/g, '_');
  
  const sDay = (sesion.dia || 'UNK').trim().toUpperCase();
  const sStart = (sesion.hora_inicio || '00:00').trim();

  return `${sName}|${sType}|${sGroup}|${sDay}|${sStart}`;
}

/**
 * Normaliza texto removiendo acentos y convirtiendo a minúsculas
 */
function normalizeText(text: string): string {
  if (!text) return '';
  return text.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

/**
 * Mapea un horario completo a sesiones para el grid
 */
function mapHorarioToSessions(horario: HorarioExtraido, unifiedMap: Map<string, string>): Session[] {
  const sessions: Session[] = [];
  (horario.horarios || []).forEach((bloque) => {
    sessions.push(...mapBloqueToSessions(bloque, unifiedMap));
  });
  return sessions;
}

/**
 * Mapea un bloque de horario a sesiones para el grid
 */
function mapBloqueToSessions(bloque: HorarioExtraidoBloque, unifiedMap: Map<string, string>): Session[] {
  const sessions: Session[] = [];
  const seenIds = new Set<string>();

  (bloque.sesiones || []).forEach((sesion) => {
    const dayIndex = diaToDayIndex(sesion.dia);
    if (dayIndex < 0) return;

    const id = generateSemanticId(sesion, unifiedMap);
    
    if (seenIds.has(id)) return;
    seenIds.add(id);

    const hasAsignatura = sesion.asignatura_sugerida || 
                          sesion.manual_validated || 
                          sesion.match_status === 'EXACT' || 
                          sesion.match_status === 'ALIAS_DB';
    const hasAula = sesion.aula && sesion.aula !== 'POR DETERMINAR';

    const color: Session['color'] = (!hasAsignatura || !hasAula) ? 'red' : 'blue';

    const rawName = normalizeText(sesion.asignatura || '');
    const displayName = sesion.asignatura_sugerida || 
                        unifiedMap.get(rawName) || 
                        sesion.asignatura;

    sessions.push({
      id, 
      courseId: buildCourseIdFromCurso(bloque.curso),
      dayIndex,
      start: normalizeTime(sesion.hora_inicio),
      end: normalizeTime(sesion.hora_fin),
      title: displayName, 
      room: sesion.aula ?? '—',
      teacher: sesion.grupo ? `Grupo ${sesion.grupo}` : '',
      color,
    } as Session); 
  });
  
  return sessions;
}

/**
 * Convierte nombre de día a índice numérico (0-4)
 */
function diaToDayIndex(dia: string): number {
  const d = dia.trim().toUpperCase();
  if (d.startsWith('L')) return 0;
  if (d.startsWith('MA')) return 1;
  if (d.startsWith('MI')) return 2;
  if (d.startsWith('J')) return 3;
  if (d.startsWith('V')) return 4;
  return -1;
}

/**
 * Normaliza formato de hora a HH:MM
 */
function normalizeTime(value: string): string {
  if (!value) return value;
  const parts = value.split(':');
  return parts.length >= 2 
    ? `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}` 
    : value;
}

/**
 * Convierte hora HH:MM a minutos totales
 */
function timeToMinutes(value: string): number {
  if (!value) return 0;
  const [h, m] = value.split(':').map((n) => parseInt(n, 10) || 0);
  return h * 60 + m;
}

/**
 * Convierte minutos totales a formato HH:MM
 */
function minutesToTimeLabel(totalMin: number): string {
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/**
 * Genera ID de curso para visualización
 */
function buildCourseIdFromCurso(cursoTexto: string): string {
  if (cursoTexto.includes('1') || cursoTexto.toLowerCase().includes('primer')) return '1º';
  if (cursoTexto.includes('2') || cursoTexto.toLowerCase().includes('segundo')) return '2º';
  if (cursoTexto.includes('3') || cursoTexto.toLowerCase().includes('tercer')) return '3º';
  if (cursoTexto.includes('4') || cursoTexto.toLowerCase().includes('cuarto')) return '4º';
  if (cursoTexto.includes('5') || cursoTexto.toLowerCase().includes('quinto')) return '5º';
  return cursoTexto;
}

/**
 * Extrae número de curso de texto descriptivo
 */
function parseCursoNumerico(cursoTexto: string): number {
    const txt = normalizeText(cursoTexto);
    if (txt.includes('1') || txt.includes('primer')) return 1;
    if (txt.includes('2') || txt.includes('segundo')) return 2;
    if (txt.includes('3') || txt.includes('tercer')) return 3;
    if (txt.includes('4') || txt.includes('cuarto')) return 4;
    if (txt.includes('5') || txt.includes('quinto')) return 5;
    return 0; 
}

/**
 * Genera etiqueta visual para un bloque de horario
 */
function buildBloqueLabel(bloque: HorarioExtraidoBloque): string {
  const base = buildCourseIdFromCurso(bloque.curso);
  if (!bloque.mencion) return base;
  return `${base} - ${bloque.mencion.replace(/MENCI[ÓO]N\s+EN\s+/i, 'Mención ')}`;
}