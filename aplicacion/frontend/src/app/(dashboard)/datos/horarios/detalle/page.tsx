'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { 
  ArrowLeft, Calendar, Loader2, Trash2, AlertTriangle 
} from 'lucide-react';

import { InteractiveScheduleGrid } from '@/components/solver/interactive-schedule-grid';
import type { Session } from '@/components/solver/schedule-mock';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from '@/components/ui/badge';

// --- APIS ---
import { listSesiones, updateSesion, deleteSesion, type SesionOut, type SesionUpdateInput } from '@/lib/api/docencia/sesiones';
import { listAulas, type AulaOut } from '@/lib/api/recursos/aulas';
import { listGruposDocentes, type GrupoDocenteOut } from '@/lib/api/docencia/grupos-docentes';
import { listAsignaturas, type AsignaturaOut } from '@/lib/api/catalogo/asignaturas';
import { getPrograma, type ProgramaOut } from '@/lib/api/catalogo/programas'; 

// --- CONSTANTES & UTILIDADES ---

// Valores exactos según backend/constants/enums.py
const DIAS_BACKEND = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes'] as const;

// Opciones para el Select (Value = Backend, Label = UI)
const DIAS_OPTIONS = [
  { value: 'lunes', label: 'Lunes' },
  { value: 'martes', label: 'Martes' },
  { value: 'miercoles', label: 'Miércoles' },
  { value: 'jueves', label: 'Jueves' },
  { value: 'viernes', label: 'Viernes' },
];

/**
 * Convierte cualquier formato de día (BD o UI) al índice 0-4 del Grid.
 * Maneja mayúsculas, minúsculas y tildes.
 */
function normalizeDayToIndex(dia: string | null | undefined): number {
  if (!dia) return 0; // Por defecto al Lunes si no hay dato
  
  // Normalizar: minúsculas y quitar tildes (NFD)
  const d = dia.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

  if (d.startsWith('lu')) return 0;
  if (d.startsWith('ma')) return 1;
  if (d.startsWith('mi')) return 2;
  if (d.startsWith('ju')) return 3;
  if (d.startsWith('vi')) return 4;
  
  return 0; // Fallback
}

// --- TIPOS EXTENDIDOS ---

interface AsignaturaConMencion extends AsignaturaOut {
  mencion?: string;
}

interface GridSession extends Session {
  originalData: SesionOut;
}

interface EditSesionForm {
  dia_semana: string;
  hora_inicio: string;
  hora_fin: string;
  aula_id: number | null;
}

export default function DetalleHorarioPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  // Parámetros de URL
  const pProgramaId = searchParams.get('programa_id');
  const pCurso = searchParams.get('curso');
  const pMencion = searchParams.get('mencion'); 

  // --- ESTADOS ---
  const [loading, setLoading] = React.useState(true);
  const [programa, setPrograma] = React.useState<ProgramaOut | null>(null);
  const [sesionesDb, setSesionesDb] = React.useState<SesionOut[]>([]);
  
  const [aulas, setAulas] = React.useState<AulaOut[]>([]);
  const [gruposMap, setGruposMap] = React.useState<Map<number, GrupoDocenteOut>>(new Map());
  const [asignaturasMap, setAsignaturasMap] = React.useState<Map<number, AsignaturaOut>>(new Map());

  // Estado de edición
  const [isEditOpen, setIsEditOpen] = React.useState(false);
  const [editingSesion, setEditingSesion] = React.useState<SesionOut | null>(null);
  
  // Formulario inicializado con valores seguros
  const [form, setForm] = React.useState<EditSesionForm>({
    dia_semana: 'lunes',
    hora_inicio: '',
    hora_fin: '',
    aula_id: null
  });
  const [isSaving, setIsSaving] = React.useState(false);

  // --- CARGA DE DATOS ---
  React.useEffect(() => {
    async function fetchData() {
      if (!pProgramaId || !pCurso) return;
      
      try {
        setLoading(true);

        // 1. Cargar datos básicos
        const [resProg, resAulas, resAsignaturas] = await Promise.all([
          getPrograma(Number(pProgramaId)).catch(() => null),
          listAulas({ size: 1000 }),
          listAsignaturas({ limit: 1000, activo: true }) 
        ]);

        setPrograma(resProg);
        setAulas(resAulas.items || []);

        // 2. Procesar Asignaturas y filtrar por MENCIÓN
        const asigMap = new Map<number, AsignaturaOut>();
        (resAsignaturas.items || []).forEach((a: AsignaturaOut) => {
            const asigExtendida = a as AsignaturaConMencion;
            const asigMencion = asigExtendida.mencion; 
            
            if (pMencion && asigMencion && asigMencion !== pMencion) {
                return; 
            }
            asigMap.set(a.id, a);
        });
        setAsignaturasMap(asigMap);

        // 3. Cargar Grupos Docentes del CURSO
        const resGrupos = await listGruposDocentes({ 
          curso: Number(pCurso), 
          size: 1000 
        });

        // 4. Filtrar Grupos
        const validGrupos: GrupoDocenteOut[] = [];
        const gMap = new Map<number, GrupoDocenteOut>();
        
        (resGrupos.items || []).forEach((g: GrupoDocenteOut) => {
            if (asigMap.has(g.asignatura_id)) {
                validGrupos.push(g);
                gMap.set(g.id, g);
            }
        });
        setGruposMap(gMap);

        const validGrupoIds = new Set(validGrupos.map(g => g.id));

        // 5. Cargar Sesiones (CORREGIDO: Límite 1000 para evitar error 422)
        const resSesiones = await listSesiones({ 
          size: 1000,
          curso: Number(pCurso),          // <--- Filtro de Curso
          mencion: pMencion || undefined  // <--- Filtro de Mención (si existe)
        });
        
        const sesionesFiltradas = (resSesiones.items || []).filter((s: SesionOut) => 
          validGrupoIds.has(s.grupo_docente_id)
        );

        setSesionesDb(sesionesFiltradas);

      } catch (error) {
        console.error("Error cargando detalle:", error);
        toast({
          title: "Error de carga",
          description: "No se pudo componer el horario completo.",
          variant: "destructive"
        });
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [pProgramaId, pCurso, pMencion, toast]);

  // --- TRANSFORMACIÓN: DB -> GRID ---
  const gridSessions = React.useMemo<Session[]>(() => {
    return sesionesDb.map((dbSesion) => {
      const grupo = gruposMap.get(dbSesion.grupo_docente_id);
      const asignatura = grupo ? asignaturasMap.get(grupo.asignatura_id) : undefined;
      const aula = aulas.find(a => a.id === dbSesion.aula_id);

      const title = asignatura?.nombre || "Asignatura desconocida";
      const subtitle = grupo ? `Grupo ${grupo.codigo} (${grupo.tipo})` : "Sin grupo";
      
      // SOLUCIÓN DÍA: Usar normalizador
      const dayIndex = normalizeDayToIndex(dbSesion.dia_semana);

      const sessionObj: GridSession = {
        id: String(dbSesion.id),
        courseId: String(dbSesion.grupo_docente_id),
        dayIndex: dayIndex,
        start: normalizeTime(dbSesion.hora_inicio),
        end: normalizeTime(dbSesion.hora_fin),
        title: title,
        room: aula?.nombre || 'Sin Aula',
        teacher: subtitle, 
        color: (grupo?.tipo === 'practica' || grupo?.tipo === 'laboratorio') ? 'orange' : 'blue',
        originalData: dbSesion 
      };

      return sessionObj;
    });
  }, [sesionesDb, gruposMap, asignaturasMap, aulas]);

  // --- HANDLERS ---

  const handleSessionClick = (session: Session) => {
    const original = (session as GridSession).originalData;
    if (!original) return;

    setEditingSesion(original);
    
    // Normalizamos el día al abrir para que coincida con el Select
    const diaBackend = original.dia_semana ? original.dia_semana.toLowerCase() : 'lunes';
    // Si viene con tilde desde DB por error antiguo, lo limpiamos
    const diaLimpio = diaBackend.normalize("NFD").replace(/[\u0300-\u036f]/g, "");

    setForm({
      dia_semana: diaLimpio,
      hora_inicio: normalizeTime(original.hora_inicio),
      hora_fin: normalizeTime(original.hora_fin),
      aula_id: original.aula_id || null 
    });
    setIsEditOpen(true);
  };

  const handleSessionMove = async (session: Session, newDayIndex: number, newStartTime: string) => {
    const original = (session as GridSession).originalData;
    if (!original) return;

    const duracionMin = timeToMinutes(original.hora_fin) - timeToMinutes(original.hora_inicio);
    const startMin = timeToMinutes(newStartTime);
    const newEndTime = minutesToTimeLabel(startMin + duracionMin);
    
    // Convertir índice visual (0..4) a string backend ('lunes'..'viernes')
    const newDay = DIAS_BACKEND[newDayIndex] || 'lunes';

    const previousState = [...sesionesDb];
    setSesionesDb(prev => prev.map(s => 
      s.id === original.id 
        ? { ...s, dia_semana: newDay, hora_inicio: newStartTime, hora_fin: newEndTime } 
        : s
    ));

    try {
      await updateSesion(original.id, {
        dia_semana: newDay,
        hora_inicio: newStartTime,
        hora_fin: newEndTime
      });
      toast({ description: "Sesión movida correctamente." });
    } catch (error) {
      console.error(error);
      setSesionesDb(previousState);
      toast({ title: "Error", description: "No se pudo mover la sesión.", variant: "destructive" });
    }
  };

  const handleSaveEdit = async () => {
    if (!editingSesion) return;
    setIsSaving(true);
    try {
      const payload: SesionUpdateInput = {
        dia_semana: form.dia_semana,
        hora_inicio: form.hora_inicio,
        hora_fin: form.hora_fin,
        aula_id: form.aula_id
      };

      const updated = await updateSesion(editingSesion.id, payload);
      
      // Actualizamos estado local con los datos que devuelve el server
      setSesionesDb(prev => prev.map(s => s.id === editingSesion.id ? updated.sesion : s));
      setIsEditOpen(false);
      toast({ title: "Guardado", description: "La sesión ha sido actualizada." });
    } catch (error) {
      console.error(error);
      toast({ title: "Error", description: "Fallo al guardar los cambios.", variant: "destructive" });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!editingSesion) return;
    if (!confirm("¿Eliminar sesión permanentemente?")) return;

    setIsSaving(true);
    try {
      await deleteSesion(editingSesion.id);
      setSesionesDb(prev => prev.filter(s => s.id !== editingSesion.id));
      setIsEditOpen(false);
      toast({ title: "Eliminado", description: "La sesión ha sido eliminada." });
    } catch (error) {
      console.error(error);
      toast({ title: "Error", description: "No se pudo eliminar.", variant: "destructive" });
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[80vh] items-center justify-center flex-col gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-muted-foreground animate-pulse">Cargando horario...</p>
      </div>
    );
  }

  if (!pProgramaId || !pCurso) {
    return (
      <div className="p-8 flex flex-col items-center text-center gap-4">
        <AlertTriangle className="h-12 w-12 text-yellow-500" />
        <h2 className="text-xl font-bold">Faltan parámetros de visualización</h2>
        <p>Selecciona una titulación y curso desde el panel principal.</p>
        <Button onClick={() => router.back()}>Volver</Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] space-y-4 p-4">
      {/* HEADER */}
      <div className="flex items-center justify-between border-b pb-4 bg-background">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              {programa ? programa.nombre : "Cargando..."}
            </h1>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="secondary">Curso {pCurso}</Badge>
              {pMencion && <Badge variant="outline">{pMencion}</Badge>}
              <span>• {sesionesDb.length} sesiones visibles</span>
            </div>
          </div>
        </div>
      </div>

      {/* GRID AREA */}
      <Card className="flex-1 overflow-hidden border bg-background shadow-sm">
        <CardContent className="p-0 h-full">
           {gridSessions.length > 0 ? (
             <InteractiveScheduleGrid
               sessions={gridSessions}
               onSessionClick={handleSessionClick}
               onSessionMove={handleSessionMove}
               className="h-full"
               start="08:00"
               end="22:00"
             />
           ) : (
             <div className="flex h-full flex-col items-center justify-center space-y-3 p-8 text-muted-foreground">
               <Calendar className="h-12 w-12 opacity-20" />
               <p className="text-lg font-medium">No hay sesiones para este criterio</p>
               <p className="text-sm">Si has seleccionado mención, verifica que las asignaturas la tengan asignada.</p>
             </div>
           )}
        </CardContent>
      </Card>

      {/* MODAL EDICION */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Editar Sesión</DialogTitle>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
             {editingSesion && (
               <div className="rounded-md bg-muted/50 p-3 text-sm mb-2">
                 <p className="font-semibold text-foreground">
                   {asignaturasMap.get(gruposMap.get(editingSesion.grupo_docente_id)?.asignatura_id || 0)?.nombre}
                 </p>
                 <p className="text-muted-foreground">
                   Grupo {gruposMap.get(editingSesion.grupo_docente_id)?.codigo} ({gruposMap.get(editingSesion.grupo_docente_id)?.tipo})
                 </p>
               </div>
             )}

            <div className="grid gap-2">
              <Label>Día</Label>
              <Select 
                value={form.dia_semana} 
                onValueChange={(val) => setForm({...form, dia_semana: val})}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {DIAS_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>Inicio</Label>
                <Input type="time" value={form.hora_inicio} onChange={(e) => setForm({...form, hora_inicio: e.target.value})} />
              </div>
              <div className="grid gap-2">
                <Label>Fin</Label>
                <Input type="time" value={form.hora_fin} onChange={(e) => setForm({...form, hora_fin: e.target.value})} />
              </div>
            </div>

            <div className="grid gap-2">
              <Label>Aula</Label>
              <Select 
                value={form.aula_id?.toString() || "no-aula"} 
                onValueChange={(val) => setForm({...form, aula_id: val === "no-aula" ? null : Number(val)})}
              >
                <SelectTrigger><SelectValue placeholder="Sin aula" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="no-aula">-- Sin Aula --</SelectItem>
                  {aulas.map((aula) => (
                    <SelectItem key={aula.id} value={String(aula.id)}>
                      {aula.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter className="flex justify-between sm:justify-between">
            <Button variant="destructive" size="icon" onClick={handleDelete} disabled={isSaving}>
              <Trash2 className="h-4 w-4" />
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsEditOpen(false)}>Cancelar</Button>
              <Button onClick={handleSaveEdit} disabled={isSaving}>
                {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Guardar
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// --- HELPERS ---
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