'use client';

// ============================================================================
// IMPORTS
// ============================================================================

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

// Iconos
import { 
  ArrowLeft, Calendar, Loader2, Trash2, AlertTriangle, 
  Save, X, Edit, Plus, BookOpen, Clock, 
  Printer, ChevronDown, ChevronUp, ShieldCheck 
} from 'lucide-react';

// Componentes UI Base
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { SimpleAutocomplete, type AutocompleteOption } from '@/components/ui/simple-autocomplete';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { useToast } from '@/hooks/use-toast';

// Componentes de Dominio (Horarios y Conflictos)
// Importamos el tipo extendido si está exportado, o usamos la intersección aquí
import { InteractiveScheduleGrid, type SessionWithConflict } from '@/components/solver/interactive-schedule-grid';
import { DataTable } from '@/components/conflicts/data-table';
import { columns } from '@/components/conflicts/columns';

// Tipos del Grid Mock
import type { Session } from '@/components/solver/schedule-mock';

// APIs y Tipos
import type { ConflictoOut } from '@/lib/api/conflictos';
import { 
  listSesiones, 
  batchUpdateSesiones,
  validateBatchSesiones, 
  type SesionCreate, 
  type SesionUpdateWithId,
  type SesionOut as BaseSesionOut 
} from '@/lib/api/docencia/sesiones';
import { listAulas, type AulaOut } from '@/lib/api/recursos/aulas';
import { 
  listGruposDocentes, 
  createGrupoDocente, 
  type GrupoDocenteOut 
} from '@/lib/api/docencia/grupos-docentes';
import { listAsignaturas, type AsignaturaOut } from '@/lib/api/catalogo/asignaturas';
import { getPrograma, type ProgramaOut } from '@/lib/api/catalogo/programas'; 

// ============================================================================
// TIPOS EXTENDIDOS Y CONSTANTES
// ============================================================================

// Extendemos SesionOut para incluir conflictos y ID temporal
interface SesionOut extends BaseSesionOut {
  conflictos?: ConflictoOut[];
  temp_id?: number; 
}

const DIAS_BACKEND = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes'] as const;

const DIAS_OPTIONS = [
  { value: 'lunes', label: 'Lunes' },
  { value: 'martes', label: 'Martes' },
  { value: 'miercoles', label: 'Miércoles' },
  { value: 'jueves', label: 'Jueves' },
  { value: 'viernes', label: 'Viernes' },
];

const TIPOS_GRUPO = [
  { value: 'teoria', label: 'Teoría' },
  { value: 'practica', label: 'Práctica' },
  { value: 'laboratorio', label: 'Laboratorio' },
  { value: 'seminario', label: 'Seminario' },
  { value: 'taller', label: 'Taller' },
];

// Interfaces auxiliares
interface AsignaturaCompleta extends Omit<AsignaturaOut, 'titulaciones'> {
  id: number;
  nombre: string;
  codigo_plan?: string;
  titulaciones?: Array<{
    programa?: { id: number; nombre?: string }; 
    programa_id?: number;                       
    curso?: number;
    periodo?: string;
  }>;
}

interface GridSession extends Session {
  originalData: SesionOut;
  isNew?: boolean; 
}

interface EditSesionForm {
  dia_semana: string;
  hora_inicio: string;
  hora_fin: string;
  aula_id: number | null;
  asignatura_id?: number | null;
  tipo_grupo?: string;
  codigo_grupo?: string;
  grupo_docente_id?: number | null; 
}

type PendingChanges = {
  created: SesionCreate[];
  updated: Map<number, SesionUpdateWithId>;
  deleted: Set<number>;
};

// ============================================================================
// HELPERS DE NORMALIZACIÓN
// ============================================================================

function normalizeText(text: string): string {
  if (!text) return '';
  return text.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function normalizeDayToIndex(dia: string | null | undefined): number {
  if (!dia) return 0;
  const d = dia.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  if (d.startsWith('lu')) return 0;
  if (d.startsWith('ma')) return 1;
  if (d.startsWith('mi')) return 2;
  if (d.startsWith('ju')) return 3;
  if (d.startsWith('vi')) return 4;
  return 0;
}

function normalizeTime(value: string | null | undefined): string {
  if (!value) return '00:00';
  const parts = value.split(':');
  return parts.length >= 2 ? `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}` : value;
}

function timeToMinutes(value: string | null | undefined): number {
  if (!value) return 0;
  const [h, m] = value.split(':').map((n) => parseInt(n, 10) || 0);
  return h * 60 + m;
}

function minutesToTimeLabel(totalMin: number): string {
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function formatPeriodoLabel(rawPeriodo: string | null): string {
  if (!rawPeriodo) return 'PERIODO GENERAL';
  const norm = normalizeText(String(rawPeriodo));
  if (norm.includes('1') || norm.includes('primer')) return 'PRIMER CUATRIMESTRE';
  if (norm.includes('2') || norm.includes('segundo')) return 'SEGUNDO CUATRIMESTRE';
  if (norm.includes('anual')) return 'ANUAL';
  return rawPeriodo.toUpperCase().replace(/_/g, ' ');
}

// ============================================================================
// COMPONENTE PRINCIPAL
// ============================================================================

export default function DetalleHorarioPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  const pProgramaId = searchParams.get('programa_id');
  const pCurso = searchParams.get('curso');
  const pMencion = searchParams.get('mencion');
  const pPeriodo = searchParams.get('periodo');

  // --- Estados de Datos ---
  const [loading, setLoading] = React.useState(true);
  const [programa, setPrograma] = React.useState<ProgramaOut | null>(null);
  const [aulas, setAulas] = React.useState<AulaOut[]>([]);
  const [gruposMap, setGruposMap] = React.useState<Map<number, GrupoDocenteOut>>(new Map());
  const [asignaturasMap, setAsignaturasMap] = React.useState<Map<number, AsignaturaCompleta>>(new Map());
  
  // Estado principal de sesiones
  const [localSesiones, setLocalSesiones] = React.useState<SesionOut[]>([]);
  const [isConflictsOpen, setIsConflictsOpen] = React.useState(true);

  // --- Estados de Edición ---
  const [isEditMode, setIsEditMode] = React.useState(false);
  const [hasChanges, setHasChanges] = React.useState(false);
  const [pendingChanges, setPendingChanges] = React.useState<PendingChanges>({
    created: [], updated: new Map(), deleted: new Set()
  });

  // --- Estados de UI / Modales ---
  const [isEditOpen, setIsEditOpen] = React.useState(false);
  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [editingSesion, setEditingSesion] = React.useState<SesionOut | null>(null);
  const [isValidatingGlobal, setIsValidatingGlobal] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [isCreatingGroup, setIsCreatingGroup] = React.useState(false);
  const [intentoGuardar, setIntentoGuardar] = React.useState(false);

  // Formulario temporal
  const [form, setForm] = React.useState<EditSesionForm>({
    dia_semana: 'lunes',
    hora_inicio: '09:00',
    hora_fin: '10:00',
    aula_id: null,
    asignatura_id: null,
    tipo_grupo: 'teoria',
    codigo_grupo: 'UNICO'
  });

  // ==========================================================================
  // CARGA INICIAL DE DATOS
  // ==========================================================================
  
  const fetchData = React.useCallback(async () => {
    if (!pProgramaId || !pCurso) return;
    try {
      setLoading(true);
      const [resProg, resAulas, resAsignaturas] = await Promise.all([
        getPrograma(Number(pProgramaId)).catch(() => null),
        listAulas({ size: 1000 }),
        listAsignaturas({ limit: 1000, activo: true }) 
      ]);

      setPrograma(resProg);
      setAulas(resAulas.items || []);

      const asigMap = new Map<number, AsignaturaCompleta>();
      (resAsignaturas.items || []).forEach((a: AsignaturaOut) => {
          asigMap.set(a.id, a as unknown as AsignaturaCompleta);
      });
      setAsignaturasMap(asigMap);

      const resGrupos = await listGruposDocentes({ curso: Number(pCurso), size: 1000 });
      const gMap = new Map<number, GrupoDocenteOut>();
      (resGrupos.items || []).forEach((g: GrupoDocenteOut) => {
          if (asigMap.has(g.asignatura_id)) {
              gMap.set(g.id, g);
          }
      });
      setGruposMap(gMap);

      const validGrupoIds = new Set(Array.from(gMap.keys()));
      const resSesiones = await listSesiones({ size: 1000, curso: Number(pCurso), mencion: pMencion || undefined });
      
      const sesionesFiltradas = (resSesiones.items || []).filter((s: BaseSesionOut) => 
        validGrupoIds.has(s.grupo_docente_id)
      ) as SesionOut[]; 

      setLocalSesiones(sesionesFiltradas);
      setPendingChanges({ created: [], updated: new Map(), deleted: new Set() });
      setHasChanges(false);

    } catch (error) {
      console.error('Error cargando detalle:', error);
      toast({ title: 'Error de carga', description: 'No se pudo componer el horario completo.', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [pProgramaId, pCurso, pMencion, toast]);

  React.useEffect(() => { fetchData(); }, [fetchData]);

  // ==========================================================================
  // VALORES CALCULADOS (MEMO)
  // ==========================================================================

  // Conflictos únicos para la tabla global
  const uniqueConflicts = React.useMemo(() => {
    const map = new Map<string, ConflictoOut>();
    localSesiones.forEach(s => {
      if (s.conflictos && s.conflictos.length > 0) {
        s.conflictos.forEach(c => {
          map.set(c.hash_deteccion, c);
        });
      }
    });
    return Array.from(map.values());
  }, [localSesiones]);

  const aulaOptions = React.useMemo<AutocompleteOption[]>(
    () => aulas.map((a) => ({ value: a.id, label: a.nombre, keywords: a.codigo })), 
    [aulas]
  );
  
  const asignaturaOptions = React.useMemo<AutocompleteOption[]>(() => {
      if (!pProgramaId || !pCurso) return [];
      const targetProgId = Number(pProgramaId);
      const targetCurso = Number(pCurso);
      const targetPeriodoNorm = pPeriodo ? normalizeText(String(pPeriodo)) : '';
      
      return Array.from(asignaturasMap.values()).filter((a: AsignaturaCompleta) => {
            if (!a.titulaciones || a.titulaciones.length === 0) return false;
            const matchProgCurso = a.titulaciones.some(t => {
                const pId = t.programa?.id ?? t.programa_id;
                return pId === targetProgId && (t.curso === null || t.curso === undefined || t.curso === targetCurso);
            });
            if (!matchProgCurso) return false;
            if (targetPeriodoNorm) {
                const pAsig = normalizeText(String(a.periodo || ''));
                if (pAsig.includes('anual')) return true;
                const esPrimero = targetPeriodoNorm.includes('primer') || targetPeriodoNorm.includes('1') || targetPeriodoNorm === 's1';
                const esSegundo = targetPeriodoNorm.includes('segundo') || targetPeriodoNorm.includes('2') || targetPeriodoNorm === 's2';
                if (esPrimero) return pAsig.includes('primer') || pAsig.includes('1') || pAsig.includes('s1');
                if (esSegundo) return pAsig.includes('segundo') || pAsig.includes('2') || pAsig.includes('s2');
                return pAsig.includes(targetPeriodoNorm) || targetPeriodoNorm.includes(pAsig);
            }
            return true;
      }).map((a) => ({ 
        value: Number(a.id), 
        label: String(a.nombre), 
        keywords: a.codigo_plan ? String(a.codigo_plan) : undefined 
      }));
  }, [asignaturasMap, pProgramaId, pCurso, pPeriodo]);

  // --- GRID SESSIONS: Transformación con Indicadores Visuales ---
  const gridSessions = React.useMemo<SessionWithConflict[]>(() => {
    return localSesiones.map((dbSesion) => {
      const grupo = gruposMap.get(dbSesion.grupo_docente_id);
      const asignatura = grupo ? asignaturasMap.get(grupo.asignatura_id) : undefined;
      const aula = aulas.find(a => a.id === dbSesion.aula_id);
      const title = asignatura?.nombre || 'Asignatura desconocida';
      const subtitle = grupo ? `Grupo ${grupo.codigo} (${grupo.tipo})` : 'Sin grupo';
      const dayIndex = normalizeDayToIndex(dbSesion.dia_semana);

      // 1. Detectar si tiene conflictos
      const hasConflict = dbSesion.conflictos && dbSesion.conflictos.length > 0;

      // 2. Determinar color base (Estado)
      let color: Session['color'] = 'blue';
      
      if (dbSesion.id < 0) {
        color = 'green'; // Nuevo
      } else if (pendingChanges.updated.has(dbSesion.id)) {
        color = 'orange'; // Editado
      } else if (hasConflict) {
        color = 'red'; // Conflictivo (Guardado)
      }

      return {
        id: String(dbSesion.id),
        courseId: String(dbSesion.grupo_docente_id),
        dayIndex: dayIndex,
        start: normalizeTime(dbSesion.hora_inicio),
        end: normalizeTime(dbSesion.hora_fin),
        title: title,
        room: aula?.nombre || 'Sin Aula',
        teacher: subtitle, 
        color: color,
        originalData: dbSesion,
        isNew: dbSesion.id < 0,
        // 3. Pasar flag de conflicto explícito (independiente del color)
        hasConflict: hasConflict 
      } as GridSession & { hasConflict: boolean };
    });
  }, [localSesiones, gruposMap, asignaturasMap, aulas, pendingChanges]);

  // ==========================================================================
  // HANDLERS
  // ==========================================================================

  const toggleEditMode = () => {
    if (isEditMode && hasChanges) {
      if (!confirm('Tienes cambios sin guardar. ¿Seguro que quieres salir y perderlos?')) return;
      fetchData();
    }
    setIsEditMode(!isEditMode);
  };

  const handleSessionClick = (session: Session) => {
    if (!isEditMode) return;
    const original = (session as GridSession).originalData;
    if (!original) return;
    setEditingSesion(original);
    
    const diaBackend = original.dia_semana ? original.dia_semana.toLowerCase() : 'lunes';
    const diaLimpio = diaBackend.normalize('NFD').replace(/[\u0300-\u036f]/g, '');

    setForm({
      dia_semana: diaLimpio,
      hora_inicio: normalizeTime(original.hora_inicio),
      hora_fin: normalizeTime(original.hora_fin),
      aula_id: original.aula_id || null,
      grupo_docente_id: original.grupo_docente_id
    });

    setIntentoGuardar(false);
    setIsEditOpen(true);
  };

  const handleSessionMove = (session: Session, newDayIndex: number, newStartTime: string) => {
    if (!isEditMode) return;
    const original = (session as GridSession).originalData;
    if (!original) return;

    const duracionMin = timeToMinutes(original.hora_fin) - timeToMinutes(original.hora_inicio);
    const startMin = timeToMinutes(newStartTime);
    const newEndTime = minutesToTimeLabel(startMin + duracionMin);
    const newDay = DIAS_BACKEND[newDayIndex] || 'lunes';

    updateLocalSession(original.id, { dia_semana: newDay, hora_inicio: newStartTime, hora_fin: newEndTime });
  };

  const updateLocalSession = (id: number, updates: Partial<SesionOut>) => {
    setLocalSesiones(prev => prev.map(s => (s.id !== id ? s : { ...s, ...updates })));
    if (id > 0) {
      setPendingChanges(prev => {
        const existing = prev.updated.get(id) || { id };
        const updatedEntry = { ...existing, ...updates };
        const newMap = new Map(prev.updated);
        newMap.set(id, updatedEntry as SesionUpdateWithId);
        return { ...prev, updated: newMap };
      });
    }
    setHasChanges(true);
  };

  // --- VALIDACIÓN GLOBAL ---
  const handleValidateAll = async () => {
    setIsValidatingGlobal(true);
    try {
        // Preparamos payload
        const createdSessions = localSesiones.filter(s => s.id < 0).map(s => ({ 
            grupo_docente_id: s.grupo_docente_id, 
            aula_id: s.aula_id, 
            modalidad: 'presencial', 
            tipo_recurrencia: 'semanal', 
            dia_semana: s.dia_semana, 
            hora_inicio: s.hora_inicio, 
            hora_fin: s.hora_fin, 
            profesores: [],
            temp_id: s.id // ID temporal para rastreo
        } as SesionCreate));
        
        const updatedSessions = Array.from(pendingChanges.updated.values());
        const deletedIds = Array.from(pendingChanges.deleted);
        
        // Simular en backend
        const conflictosSimulados = await validateBatchSesiones({
            created: createdSessions,
            updated: updatedSessions,
            deleted: deletedIds
        });

        // Limpiar conflictos antiguos
        const sesionesLimpias = localSesiones.map(s => ({
            ...s, 
            conflictos: [] as ConflictoOut[] 
        }));
        
        const mapaSesiones = new Map(sesionesLimpias.map(s => [s.id, s]));
        
        // Asignar nuevos conflictos
        conflictosSimulados.forEach(conflicto => {
            if (conflicto.sesion_id && mapaSesiones.has(conflicto.sesion_id)) {
                const s = mapaSesiones.get(conflicto.sesion_id)!;
                if (!s.conflictos) s.conflictos = [];
                s.conflictos.push(conflicto);
            }
            if (conflicto.sesion_2_id && mapaSesiones.has(conflicto.sesion_2_id)) {
                const s = mapaSesiones.get(conflicto.sesion_2_id)!;
                if (!s.conflictos) s.conflictos = [];
                s.conflictos.push(conflicto);
            }
        });

        setLocalSesiones(Array.from(mapaSesiones.values()));
        
        toast({ 
            title: 'Validación Completa', 
            description: `Se detectaron ${conflictosSimulados.length} conflictos.`,
            className: conflictosSimulados.length === 0 ? 'bg-green-50 border-green-200' : ''
        });

    } catch (error) {
        console.error(error);
        toast({ title: 'Error', description: 'No se pudo validar el horario.', variant: 'destructive' });
    } finally {
        setIsValidatingGlobal(false);
    }
  };

  const handleSaveEditForm = () => {
    setIntentoGuardar(true);
    if (!form.aula_id) {
      toast({ title: 'Datos incompletos', description: 'Es necesario asignar un aula.', variant: 'destructive' });
      return;
    }

    if (!editingSesion) return;
    updateLocalSession(editingSesion.id, {
      dia_semana: form.dia_semana,
      hora_inicio: form.hora_inicio,
      hora_fin: form.hora_fin,
      aula_id: form.aula_id
    });
    setIsEditOpen(false);
    toast({ description: 'Cambio registrado (pendiente de guardar).' });
  };

  const handleDelete = () => {
    if (!editingSesion) return;
    setLocalSesiones(prev => prev.filter(s => s.id !== editingSesion.id));
    if (editingSesion.id > 0) {
      setPendingChanges(prev => {
        const newDeleted = new Set(prev.deleted);
        newDeleted.add(editingSesion.id);
        const newUpdated = new Map(prev.updated);
        newUpdated.delete(editingSesion.id);
        return { ...prev, deleted: newDeleted, updated: newUpdated };
      });
    }
    setIsEditOpen(false);
    setHasChanges(true);
    toast({ description: 'Sesión eliminada (pendiente de guardar).' });
  };

  const handleOpenCreate = () => {
    setForm({ dia_semana: 'lunes', hora_inicio: '09:00', hora_fin: '10:00', aula_id: null, asignatura_id: null, tipo_grupo: 'teoria', codigo_grupo: 'UNICO' });
    setIntentoGuardar(false);
    setIsCreateOpen(true);
  };

  const handleCreateSession = async () => {
    setIntentoGuardar(true);
    if (!form.asignatura_id || !form.tipo_grupo || !form.codigo_grupo || !form.aula_id) {
      toast({ title: 'Faltan datos', variant: 'destructive' });
      return;
    }
    setIsCreatingGroup(true);
    try {
      let targetGroupId: number | null = null;
      for (const group of gruposMap.values()) {
        if (group.asignatura_id === form.asignatura_id && group.tipo.toLowerCase() === form.tipo_grupo!.toLowerCase() && group.codigo.toLowerCase() === form.codigo_grupo!.toLowerCase()) {
          targetGroupId = group.id;
          break;
        }
      }
      if (!targetGroupId) {
        const newGroup = await createGrupoDocente({ asignatura_id: form.asignatura_id!, tipo: form.tipo_grupo!, codigo: form.codigo_grupo!, curso: Number(pCurso) || 1, turno: 'mañana' });
        targetGroupId = newGroup.id;
        setGruposMap(prev => new Map(prev).set(newGroup.id, newGroup));
      }
      const tempId = -1 * (Date.now() % 100000);
      const newSession: SesionOut = { id: tempId, grupo_docente_id: targetGroupId, aula_id: form.aula_id!, modalidad: 'presencial', tipo_recurrencia: 'semanal', dia_semana: form.dia_semana, hora_inicio: form.hora_inicio, hora_fin: form.hora_fin, inicio: null, fin: null, profesores: [], conflictos: [] };
      setLocalSesiones(prev => [...prev, newSession]);
      setHasChanges(true);
      setIsCreateOpen(false);
      toast({ title: 'Sesión creada', description: 'Recuerda guardar.' });
    } catch {
      toast({ title: 'Error', description: 'No se pudo crear.', variant: 'destructive' });
    } finally {
      setIsCreatingGroup(false);
    }
  };

  const handleSaveChanges = async () => {
    if (!hasChanges) return;
    setIsSaving(true);
    try {
      const createdSessions = localSesiones.filter(s => s.id < 0).map(s => ({ 
        grupo_docente_id: s.grupo_docente_id, 
        aula_id: s.aula_id, 
        modalidad: 'presencial', 
        tipo_recurrencia: 'semanal', 
        dia_semana: s.dia_semana, 
        hora_inicio: s.hora_inicio, 
        hora_fin: s.hora_fin, 
        profesores: [] 
      } as SesionCreate));
      const updatedSessions = Array.from(pendingChanges.updated.values());
      const deletedIds = Array.from(pendingChanges.deleted);
      await batchUpdateSesiones({ created: createdSessions, updated: updatedSessions, deleted: deletedIds });
      toast({ title: '¡Guardado!', description: 'Horario actualizado.' });
      await fetchData();
      setIsEditMode(false);
    } catch {
      toast({ title: 'Error', description: 'Fallo al guardar.', variant: 'destructive' });
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) return <div className="flex h-[80vh] items-center justify-center flex-col gap-4"><Loader2 className="h-10 w-10 animate-spin text-primary" /><p className="text-muted-foreground animate-pulse">Cargando horario...</p></div>;
  if (!pProgramaId || !pCurso) return <div className="p-8 flex flex-col items-center text-center gap-4"><AlertTriangle className="h-12 w-12 text-yellow-500" /><h2 className="text-xl font-bold">Faltan parámetros</h2><Button onClick={() => router.back()}>Volver</Button></div>;

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] print:h-auto print:block print:w-full print:p-4">
      
      {/* HEADER PRINCIPAL */}
      <div className="sticky top-0 z-30 flex flex-col gap-4 px-6 py-4 bg-transparent print:hidden">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-start gap-4">
            <Button variant="ghost" size="icon" className="-ml-2 mt-1 shrink-0" onClick={() => router.back()}><ArrowLeft className="h-5 w-5 text-muted-foreground" /></Button>
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground"><BookOpen className="h-3.5 w-3.5" /><span>Horarios</span><span>/</span><span className="text-foreground">Detalle</span></div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-foreground">{programa ? programa.nombre : 'Cargando...'}</h1>
                <div className="hidden sm:block h-6 w-[1px] bg-border mx-1" />
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="gap-1 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border-indigo-200">Curso {pCurso}</Badge>
                  {pMencion && <Badge variant="secondary" className="gap-1 bg-violet-50 text-violet-700 hover:bg-violet-100 border-violet-200">{pMencion}</Badge>}
                  {pPeriodo && <Badge variant="outline" className="gap-1 bg-emerald-50 text-emerald-700 border-emerald-200"><Clock className="h-3 w-3" />{pPeriodo.replace(/_/g, ' ')}</Badge>}
                  <span className="ml-2 text-sm text-muted-foreground font-medium">{localSesiones.length} sesiones</span>
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 self-start sm:self-center">
            {isEditMode ? (
               <>
                 <Button variant="outline" size="sm" onClick={handleOpenCreate} className="h-9 bg-background/80 backdrop-blur"><Plus className="mr-2 h-4 w-4" />Nueva Sesión</Button>
                 
                 {/* BOTÓN VALIDAR TODO */}
                 <Button 
                    variant="secondary" 
                    size="sm" 
                    onClick={handleValidateAll} 
                    disabled={isValidatingGlobal}
                    className="h-9 bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200"
                 >
                    {isValidatingGlobal ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShieldCheck className="mr-2 h-4 w-4" />}
                    Validar Todo
                 </Button>

                 <div className="h-6 w-[1px] bg-border mx-1 hidden sm:block" />
                 <Button variant="ghost" size="sm" onClick={toggleEditMode} disabled={isSaving} className="h-9 text-muted-foreground hover:text-foreground"><X className="mr-2 h-4 w-4" />Cancelar</Button>
                 <Button onClick={handleSaveChanges} disabled={!hasChanges || isSaving} className="h-9 min-w-[140px]">{isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}Guardar</Button>
               </>
            ) : (
               <>
                 <Button variant="outline" className="h-9 shadow-sm" onClick={() => window.print()}><Printer className="mr-2 h-4 w-4" />Imprimir</Button>
                 <Button onClick={toggleEditMode} className="h-9 shadow-sm"><Edit className="mr-2 h-4 w-4" />Editar Horario</Button>
               </>
            )}
          </div>
        </div>
      </div>

      {/* BARRA SUPERIOR DE CONFLICTOS */}
      {uniqueConflicts.length > 0 && !isEditMode && (
        <div className="px-6 pb-4 print:hidden animate-in fade-in slide-in-from-top-4">
          <Collapsible open={isConflictsOpen} onOpenChange={setIsConflictsOpen} className="border border-red-200 bg-red-50/50 rounded-lg shadow-sm">
            <div className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-red-100 text-red-600"><AlertTriangle className="h-5 w-5" /></div>
                <div><h3 className="text-sm font-semibold text-red-900">Conflictos detectados ({uniqueConflicts.length})</h3><p className="text-xs text-red-700">Hay incidencias que requieren atención.</p></div>
              </div>
              <CollapsibleTrigger asChild><Button variant="ghost" size="sm" className="hover:bg-red-100 text-red-700 gap-2"><span className="text-xs font-medium">{isConflictsOpen ? 'Ocultar' : 'Ver Lista'}</span>{isConflictsOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}</Button></CollapsibleTrigger>
            </div>
            <CollapsibleContent><div className="px-4 pb-4"><div className="bg-white rounded-md border border-red-100 overflow-hidden shadow-sm"><DataTable columns={columns} data={uniqueConflicts} emptyText="No hay conflictos." /></div></div></CollapsibleContent>
          </Collapsible>
        </div>
      )}

      {/* GRID */}
      <div className="flex-1 overflow-hidden px-6 pb-6 bg-muted/10 print:bg-white print:p-0 print:overflow-visible print:h-auto">
        <Card className={`h-full overflow-hidden border bg-background shadow-sm transition-all duration-300 ${isEditMode ? 'ring-2 ring-primary/10 border-primary/20' : ''} print:border-0 print:shadow-none print:h-auto print:overflow-visible`}>
          <CardContent className="p-0 h-full relative print:h-auto print:block">
             {isEditMode && (<div className="absolute top-3 right-3 z-20 flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20 shadow-sm animate-in fade-in zoom-in-95 print:hidden"><div className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />Modo Edición</div>)}
             {gridSessions.length > 0 || isEditMode ? (
               <InteractiveScheduleGrid sessions={gridSessions} onSessionClick={handleSessionClick} onSessionMove={handleSessionMove} readOnly={!isEditMode} className="h-full border-0 rounded-none print:h-auto" start="08:00" end="22:00" />
             ) : (
               <div className="flex h-full flex-col items-center justify-center space-y-4 p-8 text-muted-foreground print:hidden"><div className="rounded-full bg-muted p-4"><Calendar className="h-8 w-8 opacity-40" /></div><div className="text-center"><p className="text-lg font-medium text-foreground">No hay sesiones visibles</p></div></div>
             )}
          </CardContent>
        </Card>
      </div>

      {/* MODAL EDICIÓN */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader><DialogTitle>Editar Sesión</DialogTitle></DialogHeader>
          <div className="grid gap-4 py-4">
             {editingSesion && (
               <div className="rounded-md bg-muted/50 p-3 text-sm mb-2 border border-muted">
                 <p className="font-semibold text-foreground">{asignaturasMap.get(gruposMap.get(editingSesion.grupo_docente_id)?.asignatura_id || 0)?.nombre}</p>
                 <p className="text-muted-foreground text-xs mt-0.5">Grupo {gruposMap.get(editingSesion.grupo_docente_id)?.codigo} • {gruposMap.get(editingSesion.grupo_docente_id)?.tipo}</p>
                 
                 {/* VISUALIZACIÓN DE CONFLICTOS */}
                 {editingSesion.conflictos && editingSesion.conflictos.length > 0 && (
                  <div className="mt-3 bg-red-50 border border-red-200 rounded-md p-2 animate-in fade-in">
                    <div className="flex items-center gap-2 text-xs font-semibold text-red-800 mb-1">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span>Conflictos detectados:</span>
                    </div>
                    <ul className="list-disc list-inside pl-1 space-y-1 text-xs text-red-700/90 max-h-[80px] overflow-y-auto">
                      {editingSesion.conflictos.map((c, i) => (
                        <li key={i} title={c.descripcion} className="truncate">{c.descripcion}</li>
                      ))}
                    </ul>
                  </div>
                 )}
               </div>
             )}
            <div className="grid gap-2"><Label>Día</Label><Select value={form.dia_semana} onValueChange={(val) => setForm({...form, dia_semana: val})}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{DIAS_OPTIONS.map((opt) => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}</SelectContent></Select></div>
            <div className="grid grid-cols-2 gap-4"><div className="grid gap-2"><Label>Inicio</Label><Input type="time" value={form.hora_inicio} onChange={(e) => setForm({...form, hora_inicio: e.target.value})} /></div><div className="grid gap-2"><Label>Fin</Label><Input type="time" value={form.hora_fin} onChange={(e) => setForm({...form, hora_fin: e.target.value})} /></div></div>
            <div className="grid gap-2"><Label className={(!form.aula_id && intentoGuardar) ? 'text-destructive' : ''}>Aula {(!form.aula_id && intentoGuardar) && '*'}</Label><SimpleAutocomplete options={aulaOptions} value={form.aula_id ?? undefined} onChange={(val) => setForm({...form, aula_id: val ? Number(val) : null})} placeholder="Buscar aula..." className={(!form.aula_id && intentoGuardar) ? '[&_input]:border-destructive [&_input]:ring-1 [&_input]:ring-destructive' : ''} /></div>
          </div>
          <DialogFooter className="flex justify-between sm:justify-between items-center mt-2">
            <Button variant="destructive" size="icon" onClick={handleDelete} title="Eliminar sesión"><Trash2 className="h-4 w-4" /></Button>
            <div className="flex gap-2"><Button variant="outline" onClick={() => setIsEditOpen(false)}>Cancelar</Button><Button onClick={handleSaveEditForm}>Guardar</Button></div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* MODAL CREACIÓN */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}><DialogContent className="sm:max-w-[500px]"><DialogHeader><DialogTitle>Nueva Sesión</DialogTitle></DialogHeader><div className="grid gap-4 py-4"><div className="grid gap-2"><Label>Asignatura</Label><SimpleAutocomplete options={asignaturaOptions} value={form.asignatura_id ?? undefined} onChange={(val) => setForm({...form, asignatura_id: Number(val)})} placeholder="Buscar asignatura..." /></div><div className="grid gap-2"><Label>Aula</Label><SimpleAutocomplete options={aulaOptions} value={form.aula_id ?? undefined} onChange={(val) => setForm({...form, aula_id: val ? Number(val) : null})} placeholder="Buscar aula..." /></div><div className="grid gap-2"><Label>Día</Label><Select value={form.dia_semana} onValueChange={(val) => setForm({...form, dia_semana: val})}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{DIAS_OPTIONS.map((opt) => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}</SelectContent></Select></div><div className="grid grid-cols-2 gap-3"><div className="grid gap-2"><Label>Inicio</Label><Input type="time" value={form.hora_inicio} onChange={(e) => setForm({...form, hora_inicio: e.target.value})} /></div><div className="grid gap-2"><Label>Fin</Label><Input type="time" value={form.hora_fin} onChange={(e) => setForm({...form, hora_fin: e.target.value})} /></div></div><div className="grid gap-2"><Label>Tipo</Label><Select value={form.tipo_grupo} onValueChange={(val) => setForm({...form, tipo_grupo: val})}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{TIPOS_GRUPO.map((t) => <SelectItem key={t.value} value={t.value}>{String(t.label)}</SelectItem>)}</SelectContent></Select></div><div className="grid gap-2"><Label>Grupo</Label><Input value={form.codigo_grupo} onChange={(e) => setForm({...form, codigo_grupo: e.target.value})} placeholder="Ej: A, G1" /></div></div><DialogFooter className="mt-4"><Button variant="outline" onClick={() => setIsCreateOpen(false)}>Cancelar</Button><Button onClick={handleCreateSession} disabled={isCreatingGroup}>{isCreatingGroup ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear</Button></DialogFooter></DialogContent></Dialog>
    </div>
  );
}