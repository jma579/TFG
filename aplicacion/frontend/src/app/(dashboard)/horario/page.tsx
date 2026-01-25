'use client';

import * as React from 'react';
import { 
  Loader2, Save, Plus, Trash2, 
  Search, AlertCircle, AlertTriangle, Eraser
} from 'lucide-react';

import { InteractiveScheduleGrid } from '@/components/solver/interactive-schedule-grid';
import type { Session } from '@/components/solver/schedule-mock';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SimpleAutocomplete, type AutocompleteOption } from '@/components/ui/simple-autocomplete';
import { Separator } from '@/components/ui/separator';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

// --- APIS ---
import { 
  listSesiones, 
  batchUpdateSesiones, 
  type SesionOut, 
  type SesionCreate 
} from '@/lib/api/docencia/sesiones';
import { listAulas, type AulaOut } from '@/lib/api/recursos/aulas';
import { 
  listGruposDocentes, 
  createGrupoDocente, 
  type GrupoDocenteOut 
} from '@/lib/api/docencia/grupos-docentes';
import { listAsignaturas, type AsignaturaOut } from '@/lib/api/catalogo/asignaturas';
import { listProgramas, type ProgramaOut } from '@/lib/api/catalogo/programas';

// --- CONSTANTES ---
const DIAS_BACKEND = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes'] as const;
const CURSOS = [1, 2, 3, 4, 5, 6];
const PERIODOS = [
  { value: 'primer_cuatrimestre', label: '1er Cuatrimestre' },
  { value: 'segundo_cuatrimestre', label: '2do Cuatrimestre' },
  { value: 'anual', label: 'Anual' },
];
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

const CODIGO_GRUPO_TEORIA = 'UNICO';

// --- UTILIDADES ---
function normalizeDayToIndex(dia: string | null | undefined): number {
  if (!dia) return 0;
  const d = dia.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  if (d.startsWith('lu')) return 0;
  if (d.startsWith('ma')) return 1;
  if (d.startsWith('mi')) return 2;
  if (d.startsWith('ju')) return 3;
  if (d.startsWith('vi')) return 4;
  return 0;
}
function normalizeText(text: string): string {
  if (!text) return "";
  return text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
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

// --- TIPOS ---
interface AsignaturaCompleta extends Omit<AsignaturaOut, 'titulaciones'> {
  id: number;
  nombre: string;
  codigo_plan?: string;
  periodo: string; 
  titulaciones?: Array<{
    programa?: { id: number; nombre?: string }; 
    programa_id?: number;                       
    curso?: number;
  }>;
  menciones?: Array<{ id: number; nombre: string; }>;
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

export default function GestionHorarioPage() {
  const { toast } = useToast();

  // --- ESTADOS ---
  const [selectedProgramaId, setSelectedProgramaId] = React.useState<number | null>(null);
  const [selectedCurso, setSelectedCurso] = React.useState<number | null>(null);
  const [selectedPeriodo, setSelectedPeriodo] = React.useState<string | null>(null);

  const [loading, setLoading] = React.useState(false);
  const [programas, setProgramas] = React.useState<ProgramaOut[]>([]);
  const [aulas, setAulas] = React.useState<AulaOut[]>([]);
  const [gruposMap, setGruposMap] = React.useState<Map<number, GrupoDocenteOut>>(new Map());
  const [asignaturasMap, setAsignaturasMap] = React.useState<Map<number, AsignaturaCompleta>>(new Map());
  const [localSesiones, setLocalSesiones] = React.useState<SesionOut[]>([]);
  const [existingSessionIds, setExistingSessionIds] = React.useState<number[]>([]);

  const [hasChanges, setHasChanges] = React.useState(false);
  const [isEditOpen, setIsEditOpen] = React.useState(false);
  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [editingSesion, setEditingSesion] = React.useState<SesionOut | null>(null);
  const [form, setForm] = React.useState<EditSesionForm>({
    dia_semana: 'lunes', hora_inicio: '09:00', hora_fin: '10:00',
    aula_id: null, asignatura_id: null, tipo_grupo: 'teoria', codigo_grupo: CODIGO_GRUPO_TEORIA
  });
  const [isSaving, setIsSaving] = React.useState(false);
  const [isCreatingGroup, setIsCreatingGroup] = React.useState(false);
  const [isOverwriteAlertOpen, setIsOverwriteAlertOpen] = React.useState(false);

  // --- CARGA INICIAL ---
  React.useEffect(() => {
    async function loadCatalogs() {
      try {
        const [resProg, resAulas, resAsignaturas] = await Promise.all([
          listProgramas({ limit: 1000 }), 
          listAulas({ size: 1000 }),
          listAsignaturas({ limit: 1000, activo: true })
        ]);
        setProgramas(resProg.items || []);
        setAulas(resAulas.items || []);
        
        const asigMap = new Map<number, AsignaturaCompleta>();
        (resAsignaturas.items || []).forEach((a: AsignaturaOut) => {
           asigMap.set(a.id, a as unknown as AsignaturaCompleta);
        });
        setAsignaturasMap(asigMap);
      } catch (e) {
        console.error("Error cargando catálogos", e);
        toast({ title: "Error", description: "No se pudieron cargar los datos base.", variant: "destructive" });
      }
    }
    loadCatalogs();
  }, [toast]);

  // --- COMPROBACIÓN ---
  const checkExistingData = React.useCallback(async () => {
    // Limpiamos siempre al cambiar parámetros
    setLocalSesiones([]); 
    setExistingSessionIds([]);
    setHasChanges(false);

    if (!selectedProgramaId || !selectedCurso || !selectedPeriodo) return;
    
    setLoading(true);
    try {
      const resGrupos = await listGruposDocentes({ curso: selectedCurso, size: 1000 });
      const gMap = new Map<number, GrupoDocenteOut>();
      (resGrupos.items || []).forEach((g: GrupoDocenteOut) => gMap.set(g.id, g));
      setGruposMap(gMap);

      // 🟢 CAMBIO CLAVE: Enviamos programa_id para que el backend filtre.
      // Ya no recibiremos sesiones de otras titulaciones ("manguera cerrada").
      const resSesiones = await listSesiones({ 
        size: 1000, 
        curso: selectedCurso,
        programa_id: selectedProgramaId 
      });

      // Ahora filtramos por Periodo (esto sí lo hacemos en front porque el backend no lo filtra por ahora)
      const sesionesPrevias = (resSesiones.items || []).filter((s: SesionOut) => {
         const grupo = gMap.get(s.grupo_docente_id);
         if (!grupo) return false;
         const asig = asignaturasMap.get(grupo.asignatura_id);
         if (!asig) return false;

         // Filtro Periodo
         const pPeriodoNorm = normalizeText(selectedPeriodo);
         const aPeriodoNorm = normalizeText(asig.periodo || '');
         
         const esAnual = aPeriodoNorm.includes('anual');
         const coincidePeriodo = aPeriodoNorm.includes(pPeriodoNorm) || pPeriodoNorm.includes(aPeriodoNorm);
         
         let matchFuzzy = false;
         if (!esAnual && !coincidePeriodo) {
             const esPrimero = pPeriodoNorm.includes('primer') || pPeriodoNorm.includes('1');
             const esSegundo = pPeriodoNorm.includes('segundo') || pPeriodoNorm.includes('2');
             
             if (esPrimero) matchFuzzy = aPeriodoNorm.includes('primer') || aPeriodoNorm.includes('1') || aPeriodoNorm.includes('s1');
             if (esSegundo) matchFuzzy = aPeriodoNorm.includes('segundo') || aPeriodoNorm.includes('2') || aPeriodoNorm.includes('s2');
         }

         return esAnual || coincidePeriodo || matchFuzzy;
      });

      if (sesionesPrevias.length > 0) {
        // Guardamos los IDs para detectar si el usuario intenta sobrescribir
        setExistingSessionIds(sesionesPrevias.map(s => s.id));
      }

    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [selectedProgramaId, selectedCurso, selectedPeriodo, asignaturasMap]);

  React.useEffect(() => {
    checkExistingData();
  }, [checkExistingData]);

  // --- OPCIONES ---
  const programaOptions = React.useMemo<AutocompleteOption[]>(() => 
    programas.map(p => ({ value: p.id, label: p.nombre })), 
  [programas]);

  const aulaOptions = React.useMemo<AutocompleteOption[]>(() => 
    aulas.map(a => ({ value: a.id, label: a.nombre, keywords: a.codigo })), 
  [aulas]);

  const asignaturaOptions = React.useMemo<AutocompleteOption[]>(() => {
    if (!selectedProgramaId || !selectedCurso) return [];
    
    const targetPeriodoNorm = selectedPeriodo ? normalizeText(selectedPeriodo) : '';

    return Array.from(asignaturasMap.values())
      .filter(a => {
        if (!a.titulaciones || a.titulaciones.length === 0) return false;
        
        const matchProgramaCurso = a.titulaciones.some(t => {
           const pId = t.programa?.id ?? t.programa_id;
           const cVal = t.curso ?? 0;
           return pId === selectedProgramaId && (cVal === selectedCurso || cVal === null);
        });

        if (!matchProgramaCurso) return false;

        if (!targetPeriodoNorm) return true;

        const aPeriodoNorm = normalizeText(String(a.periodo || ''));
        
        if (aPeriodoNorm.includes('anual')) return true;

        const esPrimero = targetPeriodoNorm.includes('primer') || targetPeriodoNorm.includes('1');
        const esSegundo = targetPeriodoNorm.includes('segundo') || targetPeriodoNorm.includes('2');

        if (esPrimero) {
            return aPeriodoNorm.includes('primer') || aPeriodoNorm.includes('1') || aPeriodoNorm.includes('s1');
        }
        if (esSegundo) {
            return aPeriodoNorm.includes('segundo') || aPeriodoNorm.includes('2') || aPeriodoNorm.includes('s2');
        }
        
        return aPeriodoNorm.includes(targetPeriodoNorm) || targetPeriodoNorm.includes(aPeriodoNorm);
      })
      .map(a => ({ value: a.id, label: a.nombre, keywords: a.codigo_plan }));
  }, [asignaturasMap, selectedProgramaId, selectedCurso, selectedPeriodo]);

  // --- GRID ---
  const gridSessions = React.useMemo<Session[]>(() => {
    return localSesiones.map((dbSesion) => {
      const grupo = gruposMap.get(dbSesion.grupo_docente_id);
      const asignatura = grupo ? asignaturasMap.get(grupo.asignatura_id) : undefined;
      const aula = aulas.find(a => a.id === dbSesion.aula_id);

      const title = asignatura?.nombre || "Asignatura desconocida";
      const isTeoria = grupo?.tipo.toLowerCase() === 'teoria';
      const subtitle = isTeoria 
        ? `Teoría (${grupo?.tipo})` 
        : `Grupo ${grupo?.codigo} (${grupo?.tipo})`;
        
      const dayIndex = normalizeDayToIndex(dbSesion.dia_semana);

      const isExisting = dbSesion.id > 0;

      return {
        id: String(dbSesion.id),
        courseId: String(dbSesion.grupo_docente_id),
        dayIndex: dayIndex,
        start: normalizeTime(dbSesion.hora_inicio),
        end: normalizeTime(dbSesion.hora_fin),
        title: title,
        room: aula?.nombre || 'Sin Aula',
        teacher: subtitle, 
        color: isExisting ? 'blue' : 'green', 
        originalData: dbSesion,
        isNew: !isExisting
      } as GridSession;
    });
  }, [localSesiones, gruposMap, asignaturasMap, aulas]);

  // --- HANDLERS ---
  const handleSessionClick = (session: Session) => {
    const original = (session as GridSession).originalData;
    if (!original) return;
    setEditingSesion(original);
    
    const diaBackend = original.dia_semana ? original.dia_semana.toLowerCase() : 'lunes';
    const grupo = gruposMap.get(original.grupo_docente_id);
    
    setForm({
      dia_semana: diaBackend,
      hora_inicio: normalizeTime(original.hora_inicio),
      hora_fin: normalizeTime(original.hora_fin),
      aula_id: original.aula_id || null,
      grupo_docente_id: original.grupo_docente_id,
      tipo_grupo: grupo?.tipo || 'teoria',
      codigo_grupo: grupo?.codigo || ''
    });
    setIsEditOpen(true);
  };

  const handleSessionMove = (session: Session, newDayIndex: number, newStartTime: string) => {
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
    setHasChanges(true);
  };

  const handleSaveEditForm = () => {
    if (!editingSesion) return;
    updateLocalSession(editingSesion.id, {
      dia_semana: form.dia_semana,
      hora_inicio: form.hora_inicio,
      hora_fin: form.hora_fin,
      aula_id: form.aula_id || 0 
    });
    setIsEditOpen(false);
  };

  const handleDelete = () => {
    if (!editingSesion) return;
    setLocalSesiones(prev => prev.filter(s => s.id !== editingSesion.id));
    setIsEditOpen(false);
    setHasChanges(true);
  };

  const handleClearGrid = () => {
    if (localSesiones.length === 0) return;
    if (confirm("¿Estás seguro de que quieres eliminar todas las sesiones de la rejilla?")) {
        setLocalSesiones([]);
        setHasChanges(true);
        toast({ description: "Rejilla limpiada." });
    }
  };

  const handleCreateSession = async () => {
    if (form.tipo_grupo !== 'teoria' && !form.codigo_grupo) {
        toast({ title: "Falta Grupo", description: "Debes indicar el código del grupo (ej: L1)", variant: "destructive" });
        return;
    }
    if (!form.asignatura_id || !form.tipo_grupo) return;

    setIsCreatingGroup(true);
    try {
      const codigoFinal = form.tipo_grupo === 'teoria' ? CODIGO_GRUPO_TEORIA : form.codigo_grupo;
      let targetGroupId: number | null = null;
      
      for (const group of gruposMap.values()) {
        if (group.asignatura_id === form.asignatura_id && 
            group.tipo.toLowerCase() === form.tipo_grupo!.toLowerCase() &&
            group.codigo.toLowerCase() === codigoFinal!.toLowerCase()) {
          targetGroupId = group.id;
          break;
        }
      }
      
      if (!targetGroupId) {
        const newGroup = await createGrupoDocente({
          asignatura_id: form.asignatura_id!,
          tipo: form.tipo_grupo!,
          codigo: codigoFinal!,
          curso: selectedCurso || 1,
          turno: 'mañana'
        });
        targetGroupId = newGroup.id;
        setGruposMap(prev => new Map(prev).set(newGroup.id, newGroup));
      }

      const tempId = -1 * (Date.now() % 100000); 
      const newSession: SesionOut = {
        id: tempId, grupo_docente_id: targetGroupId, aula_id: form.aula_id || 0, 
        modalidad: 'presencial', tipo_recurrencia: 'semanal',
        dia_semana: form.dia_semana, hora_inicio: form.hora_inicio, hora_fin: form.hora_fin,
        inicio: null, fin: null, profesores: [] 
      };
      setLocalSesiones(prev => [...prev, newSession]);
      setHasChanges(true);
      setIsCreateOpen(false);
    } catch (e) {
      console.error(e);
      toast({ title: "Error", description: "Error gestionando grupo docente", variant: "destructive" });
    } finally {
      setIsCreatingGroup(false);
    }
  };

  const handleSaveClick = () => {
    if (!hasChanges) return;
    if (existingSessionIds.length > 0) {
      setIsOverwriteAlertOpen(true);
    } else {
      performBatchSave();
    }
  };

  const performBatchSave = async () => {
    setIsSaving(true);
    try {
      const created = localSesiones.map(s => ({
          grupo_docente_id: s.grupo_docente_id, 
          aula_id: s.aula_id,
          modalidad: s.modalidad || 'presencial', 
          tipo_recurrencia: s.tipo_recurrencia || 'semanal',
          dia_semana: s.dia_semana, 
          hora_inicio: s.hora_inicio, 
          hora_fin: s.hora_fin, 
          profesores: []
      } as SesionCreate));

      const deleted = existingSessionIds; 

      await batchUpdateSesiones({ created, updated: [], deleted });
      toast({ title: "¡Guardado!", description: "Horario registrado correctamente." });
      
      setIsOverwriteAlertOpen(false);
      setHasChanges(false);
      checkExistingData();

    } catch (e) {
      console.error(e);
      toast({ title: "Error", description: "No se pudo guardar el horario.", variant: "destructive" });
    } finally {
      setIsSaving(false);
    }
  };

  const isSelectionComplete = selectedProgramaId && selectedCurso && selectedPeriodo;

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)]">
      
      <div className="px-6 pt-6 pb-4">
        <div className="space-y-1.5">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Gestión de Horarios
          </h1>
          <p className="text-lg text-muted-foreground">
            Crea o sobrescribe horarios verificando conflictos en tiempo real.
          </p>
        </div>
      </div>

      {/* --- HEADER FLOTANTE (TOOLBAR) --- */}
      <div className="px-6 pb-2 z-20">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 p-5 bg-background/80 backdrop-blur-md border rounded-2xl shadow-sm transition-all hover:shadow-md">
          
          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-6">
             <div className="space-y-2">
               <Label className="text-[11px] uppercase tracking-wider font-bold text-muted-foreground/80 ml-1">Titulación</Label>
               <SimpleAutocomplete 
                 options={programaOptions} 
                 value={selectedProgramaId ?? undefined} 
                 onChange={(val) => {
                    if (hasChanges && !confirm("Perderás el borrador actual. ¿Continuar?")) return;
                    setSelectedProgramaId(val ? Number(val) : null);
                 }} 
                 placeholder="Selecciona Grado..." 
               />
             </div>
             <div className="space-y-2">
               <Label className="text-[11px] uppercase tracking-wider font-bold text-muted-foreground/80 ml-1">Curso</Label>
               <Select value={selectedCurso?.toString()} onValueChange={(val) => {
                   if (hasChanges && !confirm("Perderás el borrador actual. ¿Continuar?")) return;
                   setSelectedCurso(Number(val));
               }}>
                 <SelectTrigger className="h-10 bg-background"><SelectValue placeholder="Curso..." /></SelectTrigger>
                 <SelectContent>
                   {CURSOS.map(c => <SelectItem key={c} value={String(c)}>{c}º Curso</SelectItem>)}
                 </SelectContent>
               </Select>
             </div>
             <div className="space-y-2">
               <Label className="text-[11px] uppercase tracking-wider font-bold text-muted-foreground/80 ml-1">Periodo</Label>
               <Select value={selectedPeriodo || ""} onValueChange={(val) => {
                   if (hasChanges && !confirm("Perderás el borrador actual. ¿Continuar?")) return;
                   setSelectedPeriodo(val);
               }}>
                 <SelectTrigger className="h-10 bg-background"><SelectValue placeholder="Cuatrimestre..." /></SelectTrigger>
                 <SelectContent>
                   {PERIODOS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                 </SelectContent>
               </Select>
             </div>
          </div>

          <div className="flex items-center gap-3 pb-0.5">
             <Separator orientation="vertical" className="h-10 mx-2 hidden md:block bg-border/60" />
             
             <Button 
                variant="outline" 
                size="icon" 
                className="h-10 w-10 rounded-xl text-muted-foreground hover:text-destructive hover:bg-destructive/10 hover:border-destructive/30 transition-colors"
                onClick={handleClearGrid}
                disabled={!isSelectionComplete || localSesiones.length === 0}
                title="Limpiar rejilla"
             >
                <Eraser className="h-5 w-5" />
             </Button>

             <Button 
               variant="outline" 
               className="h-10 rounded-xl border-dashed border-primary/40 text-primary hover:bg-primary/5 hover:border-primary"
               disabled={!isSelectionComplete} 
               onClick={() => {
                 setForm(prev => ({ 
                    ...prev, 
                    dia_semana: 'lunes', 
                    hora_inicio: '09:00', 
                    hora_fin: '10:00', 
                    aula_id: null, 
                    asignatura_id: null,
                    tipo_grupo: 'teoria', 
                    codigo_grupo: CODIGO_GRUPO_TEORIA
                 }));
                 setIsCreateOpen(true);
               }}
             >
               <Plus className="mr-2 h-4 w-4" /> Nueva Sesión
             </Button>

             <Button 
               onClick={handleSaveClick} 
               disabled={!hasChanges || isSaving}
               className={`h-10 rounded-xl px-6 font-medium shadow-md transition-all ${hasChanges ? "animate-pulse" : ""}`}
             >
               {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
               Guardar
             </Button>
          </div>
        </div>
      </div>

      {/* --- GRID --- */}
      <div className="flex-1 overflow-hidden bg-muted/5 px-6 pb-6 pt-2">
        {loading ? (
           <div className="h-full flex flex-col items-center justify-center gap-4">
             <Loader2 className="h-10 w-10 animate-spin text-primary" />
             <p className="text-muted-foreground">Verificando datos...</p>
           </div>
        ) : !isSelectionComplete ? (
           <div className="h-full flex flex-col items-center justify-center gap-4 text-center p-8 opacity-50">
             <div className="bg-muted p-6 rounded-full">
               <Search className="h-12 w-12 text-muted-foreground" />
             </div>
             <div>
               <h3 className="text-xl font-semibold">Selecciona los parámetros</h3>
               <p className="text-muted-foreground max-w-sm mt-2">
                 Define la Titulación, Curso y Periodo en la barra superior para comenzar.
               </p>
             </div>
           </div>
        ) : (
           <Card className="h-full border shadow-sm flex flex-col overflow-hidden rounded-2xl">
             <div className="flex-1 relative overflow-y-auto">
                {localSesiones.length === 0 && (
                   <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
                      <div className="bg-background/80 backdrop-blur-sm p-6 rounded-xl border shadow-sm text-center">
                         <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-3">
                            <AlertCircle className="h-6 w-6 text-muted-foreground" />
                         </div>
                         <p className="font-medium text-lg">Lienzo en blanco</p>
                         <p className="text-sm text-muted-foreground">Usa "Nueva Sesión" para añadir clases a este horario.</p>
                      </div>
                   </div>
                )}
                <InteractiveScheduleGrid 
                  sessions={gridSessions}
                  onSessionClick={handleSessionClick}
                  onSessionMove={handleSessionMove}
                  start="08:00"
                  end="22:00"
                  className="min-h-full border-0 rounded-none"
                />
             </div>
           </Card>
        )}
      </div>

      {/* --- ALERT SOBRESCRIBIR --- */}
      <AlertDialog open={isOverwriteAlertOpen} onOpenChange={setIsOverwriteAlertOpen}>
        <AlertDialogContent className="rounded-xl">
          <AlertDialogHeader>
            <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-amber-100 rounded-full">
                    <AlertTriangle className="h-5 w-5 text-amber-600" />
                </div>
                <AlertDialogTitle>Horario ya existente</AlertDialogTitle>
            </div>
            <AlertDialogDescription className="text-base leading-relaxed">
              Ya existe un horario registrado para esta configuración con <strong>{existingSessionIds.length} sesiones</strong>.
              <br/><br/>
              Si continúas, <strong>se eliminará el horario anterior</strong> y se guardará únicamente el que acabas de diseñar en pantalla.
              <br/><br/>
              ¿Deseas sobrescribirlo?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-lg">Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={performBatchSave} className="bg-amber-600 hover:bg-amber-700 rounded-lg">
              Sí, Sobrescribir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* --- MODAL CREACIÓN --- */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-[500px] rounded-xl">
          <DialogHeader><DialogTitle>Nueva Sesión</DialogTitle></DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Asignatura</Label>
              <SimpleAutocomplete options={asignaturaOptions} value={form.asignatura_id ?? undefined} onChange={(val) => setForm({...form, asignatura_id: Number(val)})} placeholder="Buscar asignatura..." emptyText="No se encontraron asignaturas para este curso" />
            </div>
            <div className="grid gap-2">
              <Label>Aula</Label>
              <SimpleAutocomplete options={aulaOptions} value={form.aula_id ?? undefined} onChange={(val) => setForm({...form, aula_id: val ? Number(val) : null})} placeholder="Buscar aula..." />
            </div>
            <div className="grid gap-2">
              <Label>Día</Label>
              <Select value={form.dia_semana} onValueChange={(val) => setForm({...form, dia_semana: val})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{DIAS_OPTIONS.map((opt) => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-2"><Label>Inicio</Label><Input type="time" value={form.hora_inicio} onChange={(e) => setForm({...form, hora_inicio: e.target.value})} /></div>
              <div className="grid gap-2"><Label>Fin</Label><Input type="time" value={form.hora_fin} onChange={(e) => setForm({...form, hora_fin: e.target.value})} /></div>
            </div>
            <div className="grid gap-2">
              <Label>Tipo</Label>
              <Select value={form.tipo_grupo} onValueChange={(val) => {
                  const isTeoria = val === 'teoria';
                  setForm({
                      ...form, 
                      tipo_grupo: val,
                      codigo_grupo: isTeoria ? CODIGO_GRUPO_TEORIA : '' 
                  });
              }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{TIPOS_GRUPO.map((t) => <SelectItem key={t.value} value={t.value}>{String(t.label)}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            
            {form.tipo_grupo !== 'teoria' && (
                <div className="grid gap-2 animate-in fade-in zoom-in-95 duration-200">
                    <Label>Grupo (Subgrupo)</Label>
                    <Input 
                        value={form.codigo_grupo} 
                        onChange={(e) => setForm({...form, codigo_grupo: e.target.value})} 
                        placeholder="Ej: L1, P2, A" 
                    />
                </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)} className="rounded-lg">Cancelar</Button>
            <Button onClick={handleCreateSession} disabled={!form.asignatura_id || !form.tipo_grupo || (!form.codigo_grupo && form.tipo_grupo !== 'teoria') || isCreatingGroup} className="rounded-lg">
                {isCreatingGroup ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}Crear
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* --- MODAL EDICIÓN --- */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="sm:max-w-[425px] rounded-xl">
          <DialogHeader><DialogTitle>Editar Sesión</DialogTitle></DialogHeader>
          <div className="grid gap-4 py-4">
             {editingSesion && (
               <div className="rounded-lg bg-muted/50 p-3 text-sm mb-2 border border-muted">
                 <p className="font-semibold">{asignaturasMap.get(gruposMap.get(editingSesion.grupo_docente_id)?.asignatura_id || 0)?.nombre}</p>
                 <p className="text-muted-foreground text-xs mt-0.5">
                    {form.tipo_grupo === 'teoria' ? 'Teoría' : `Grupo ${form.codigo_grupo} (${form.tipo_grupo})`}
                 </p>
               </div>
             )}
            <div className="grid gap-2">
              <Label>Día</Label>
              <Select value={form.dia_semana} onValueChange={(val) => setForm({...form, dia_semana: val})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{DIAS_OPTIONS.map((opt) => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2"><Label>Inicio</Label><Input type="time" value={form.hora_inicio} onChange={(e) => setForm({...form, hora_inicio: e.target.value})} /></div>
              <div className="grid gap-2"><Label>Fin</Label><Input type="time" value={form.hora_fin} onChange={(e) => setForm({...form, hora_fin: e.target.value})} /></div>
            </div>
            <div className="grid gap-2">
              <Label>Aula</Label>
              <SimpleAutocomplete options={aulaOptions} value={form.aula_id ?? undefined} onChange={(val) => setForm({...form, aula_id: val ? Number(val) : null})} placeholder="Buscar aula..." />
            </div>
          </div>
          <DialogFooter className="flex justify-between sm:justify-between">
            <Button variant="destructive" size="icon" onClick={handleDelete} className="rounded-lg"><Trash2 className="h-4 w-4" /></Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsEditOpen(false)} className="rounded-lg">Cancelar</Button>
              <Button onClick={handleSaveEditForm} className="rounded-lg">Aplicar</Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}