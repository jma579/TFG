'use client';

import * as React from 'react';
import { 
  CheckCircle2, AlertTriangle, ChevronDown, ChevronUp, 
  Sparkles, Check, Edit, Trash2, Info, Undo2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type ReviewSession = {
  originalIndex: number;
  asignatura: string;
  dia: string;
  hora_inicio: string;
  match_status?: string;
  manual_validated?: boolean;
  asignatura_sugerida?: string;
  [key: string]: unknown;
};

export type ReviewBlock = {
  sesiones: ReviewSession[];
  [key: string]: unknown;
};

interface ReviewDashboardProps {
  bloque: ReviewBlock;
  onConfirmSession: (originalIndex: number, newValue: boolean) => void;
  onEditSession: (originalIndex: number) => void;
  onDeleteSession: (originalIndex: number) => void;
  onConfirmAllSuggestions: () => void;
}

export function ReviewDashboard({ 
  bloque, 
  onConfirmSession, 
  onEditSession,
  onDeleteSession,
  onConfirmAllSuggestions 
}: ReviewDashboardProps) {
  const [isExpanded, setIsExpanded] = React.useState(true);

  // 1. FILTRO DE VISUALIZACIÓN (LISTA):
  // Mostramos sesiones dudosas (Fuzzy/NoMatch) independientemente de si ya las validaste o no.
  // Ocultamos las que son EXACTAS automáticas, porque esas no hay que revisarlas.
  const displaySessions = React.useMemo(() => {
    return (bloque.sesiones || [])
      .map((s, idx) => ({ ...s, originalIndex: idx }))
      .filter(s => {
        // Si es match exacto automático y el usuario no lo ha tocado, lo ocultamos (es ruido).
        const isAutoExact = !s.manual_validated && (s.match_status === 'EXACT' || s.match_status === 'ALIAS_DB');
        if (isAutoExact) return false;
        
        return true; 
      }); 
  }, [bloque.sesiones]);

  // 2. MÉTRICAS DE PROGRESO (SOLO LO QUE REQUIERE ATENCIÓN)
  // Total Tareas = Total Sesiones - Exactas Automáticas
  const totalReviewable = displaySessions.length;
  
  // Tareas Hechas = De las visibles, cuántas tienen el check manual
  const completedCount = displaySessions.filter(s => s.manual_validated).length;

  const progress = totalReviewable > 0 ? Math.round((completedCount / totalReviewable) * 100) : 100;

  // Pendientes para el botón masivo (No validadas y con sugerencia)
  const pendingSuggestionsCount = displaySessions.filter(s => !s.manual_validated && s.asignatura_sugerida).length;

  // Si no hay nada que revisar en absoluto (todo es exacto), no mostramos nada
  // O podríamos mostrar un mensaje de "Todo perfecto".
  if ((bloque.sesiones?.length || 0) > 0 && totalReviewable === 0) {
      return (
        <Card className="border-l-4 border-l-blue-500 mb-6 bg-blue-50/50">
            <div className="p-4 flex items-center gap-4">
                <div className="p-2 rounded-full bg-blue-100 text-blue-700">
                    <CheckCircle2 className="h-5 w-5" />
                </div>
                <div>
                    <h3 className="font-semibold text-sm text-blue-900">Curso verificado</h3>
                    <p className="text-xs text-blue-700">Todas las sesiones coinciden exactamente con la base de datos.</p>
                </div>
            </div>
        </Card>
      );
  }

  if ((bloque.sesiones?.length || 0) === 0) return null;

  return (
    <Card className="border-l-4 border-l-primary mb-6 transition-all duration-300">
      {/* HEADER */}
      <div 
        className="p-4 flex flex-col sm:flex-row items-center justify-between gap-4 cursor-pointer hover:bg-muted/50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-4 flex-1">
          <div className="p-2 rounded-full bg-blue-100 text-blue-700">
            <Info className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">Progreso de revisión manual</h3>
            <p className="text-xs text-muted-foreground">
              Has confirmado <strong>{completedCount}</strong> de <strong>{totalReviewable}</strong> sesiones dudosas ({progress}%).
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 min-w-[200px]">
           <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
             <div 
               className="h-full bg-blue-600 transition-all duration-500"
               style={{ width: `${progress}%` }} 
             />
           </div>
           {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </div>
      </div>

      {/* BODY */}
      {isExpanded && (
        <div className="border-t bg-muted/10 p-4 animate-in slide-in-from-top-2">
          {displaySessions.length > 0 && (
            <>
              <div className="flex justify-between items-center mb-4">
                <h4 className="text-sm font-medium">Sesiones pendientes de acción</h4>
                {pendingSuggestionsCount > 0 && (
                  <Button 
                    size="sm" 
                    onClick={(e) => { e.stopPropagation(); onConfirmAllSuggestions(); }}
                    className="bg-amber-600 hover:bg-amber-700 text-white"
                  >
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Confirmar {pendingSuggestionsCount} sugerencias restantes
                  </Button>
                )}
              </div>

              <ScrollArea className="h-[300px] rounded-md border bg-background">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[120px]">Estado</TableHead>
                      <TableHead>Texto Original</TableHead>
                      <TableHead>Valor Final</TableHead>
                      <TableHead>Horario</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {displaySessions.map((sesion) => {
                      const isConfirmed = sesion.manual_validated;
                      const hasSuggestion = !!sesion.asignatura_sugerida;
                      
                      let badgeVariant: "default" | "destructive" | "outline" | "secondary" = "outline";
                      let badgeClass = "";
                      let badgeText = "";

                      if (isConfirmed) {
                        badgeClass = "border-blue-500 text-blue-600 bg-blue-50";
                        badgeText = "Confirmado";
                      } else if (hasSuggestion) {
                        badgeClass = "border-amber-500 text-amber-600 bg-amber-50";
                        badgeText = "Por revisar";
                      } else {
                        badgeVariant = "destructive";
                        badgeText = "Sin match";
                      }

                      return (
                        <TableRow key={sesion.originalIndex} className={isConfirmed ? "bg-blue-50/30" : ""}>
                          <TableCell>
                            <Badge variant={badgeVariant} className={badgeClass}>
                              {badgeText}
                            </Badge>
                          </TableCell>
                          
                          <TableCell className="text-muted-foreground text-xs max-w-[200px] truncate" title={sesion.asignatura}>
                            <span className={isConfirmed ? "" : "line-through"}>
                               {sesion.asignatura}
                            </span>
                          </TableCell>
                          
                          <TableCell className="font-medium">
                            {isConfirmed ? (
                                <span className="flex items-center gap-2 text-blue-700">
                                  <CheckCircle2 className="h-3 w-3" />
                                  {/* Si está validado, mostramos el nombre actual (que ya es el bueno) */}
                                  {sesion.asignatura}
                                </span>
                            ) : hasSuggestion ? (
                              <span className="flex items-center gap-2 text-amber-700">
                                 <Sparkles className="h-3 w-3" />
                                 {sesion.asignatura_sugerida}
                              </span>
                            ) : (
                              <span className="text-destructive italic text-xs">Requiere asignar asignatura</span>
                            )}
                          </TableCell>
                          
                          <TableCell className="text-xs text-muted-foreground">
                            {sesion.dia} {sesion.hora_inicio}
                          </TableCell>
                          
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              {/* Botón TOGGLE de Confirmación */}
                              {hasSuggestion && (
                                <Button 
                                  size="icon" 
                                  variant={isConfirmed ? "default" : "ghost"} 
                                  className={cn(
                                    "h-8 w-8 transition-all",
                                    isConfirmed 
                                      ? "bg-green-600 hover:bg-green-700 text-white" // Estado Seleccionado
                                      : "text-green-600 hover:text-green-700 hover:bg-green-50" // Estado Pendiente
                                  )}
                                  title={isConfirmed ? "Deshacer confirmación" : "Confirmar sugerencia"}
                                  onClick={() => onConfirmSession(sesion.originalIndex, !isConfirmed)} // 👇 Toggle true/false
                                >
                                  {isConfirmed ? <Check className="h-4 w-4" /> : <Check className="h-4 w-4" />}
                                </Button>
                              )}
                              
                              <Button 
                                size="icon" 
                                variant="ghost" 
                                className="h-8 w-8 text-slate-600"
                                title="Editar manualmente"
                                onClick={() => onEditSession(sesion.originalIndex)}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>

                              <Button 
                                size="icon" 
                                variant="ghost" 
                                className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                                title="Eliminar sesión"
                                onClick={() => onDeleteSession(sesion.originalIndex)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </ScrollArea>
            </>
          )}
        </div>
      )}
    </Card>
  );
}