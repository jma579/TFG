'use client';

import { 
AlertCircle, AlertTriangle,   CheckCircle2, ChevronDown, ChevronUp, 
Edit, MapPin,
  Sparkles, Trash2} from 'lucide-react';
import * as React from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type ReviewSession = {
  originalIndex: number;
  asignatura: string;
  aula?: string;
  dia: string;
  hora_inicio: string;
  hora_fin?: string;
  match_status?: string;
  manual_validated?: boolean;
  asignatura_sugerida?: string;
  match_confidence?: number;
  grupo?: string;
  tipo?: string;
  [key: string]: unknown;
};

export type ReviewBlock = {
  sesiones: ReviewSession[];
  [key: string]: unknown;
};

interface ReviewDashboardProps {
  bloque: ReviewBlock;
  onEditSession: (originalIndex: number) => void;
  onDeleteSession: (originalIndex: number) => void;
}


type SessionStatusType = 'ERROR_ASIGNATURA' | 'ERROR_AULA' | 'SUGGESTED' | 'VALID';

interface SessionStatus {
  type: SessionStatusType;
  color: 'red' | 'blue';
  label: string;
  icon: React.ReactNode;
  message?: string;
}

const getSessionStatus = (session: ReviewSession): SessionStatus => {
  const hasName = session.asignatura_sugerida || session.manual_validated;
  if (!hasName && (!session.match_status || session.match_status === 'NO_MATCH')) {
    return {
      type: 'ERROR_ASIGNATURA',
      color: 'red',
      label: 'Sin Asignatura',
      icon: <AlertCircle className="h-3 w-3" />,
      message: 'Asignatura desconocida'
    };
  }

  const aula = session.aula || "";
  if (!aula.trim() || aula === "POR DETERMINAR") {
    return {
      type: 'ERROR_AULA',
      color: 'red',
      label: 'Falta Aula',
      icon: <MapPin className="h-3 w-3" />,
      message: 'Aula no detectada'
    };
  }

  const isExact = session.match_status === 'EXACT' || session.match_status === 'ALIAS_DB';
  if (session.asignatura_sugerida && !isExact && !session.manual_validated) {
    return {
      type: 'SUGGESTED',
      color: 'blue',
      label: 'Sugerido',
      icon: <Sparkles className="h-3 w-3 text-indigo-400" />, 
      message: 'Nombre deducido automáticamente'
    };
  }

  return {
    type: 'VALID',
    color: 'blue',
    label: 'Correcto',
    icon: <CheckCircle2 className="h-3 w-3" />
  };
};

const DAY_ORDER: Record<string, number> = {
  LUNES: 1, MARTES: 2, MIERCOLES: 3, MIÉRCOLES: 3, 
  JUEVES: 4, VIERNES: 5, SABADO: 6, SÁBADO: 6, DOMINGO: 7
};

const sortSessions = (sessions: ReviewSession[]) => {
  return [...sessions].sort((a, b) => {
    const statusA = getSessionStatus(a);
    const statusB = getSessionStatus(b);

    const isRedA = statusA.color === 'red';
    const isRedB = statusB.color === 'red';

    if (isRedA && !isRedB) return -1;
    if (!isRedA && isRedB) return 1;

    if (statusA.type === 'SUGGESTED' && statusB.type === 'VALID') return -1;
    if (statusA.type === 'VALID' && statusB.type === 'SUGGESTED') return 1;

    const dayA = DAY_ORDER[(a.dia || "").toUpperCase()] || 8;
    const dayB = DAY_ORDER[(b.dia || "").toUpperCase()] || 8;
    if (dayA !== dayB) return dayA - dayB;

    return (a.hora_inicio || "").localeCompare(b.hora_inicio || "");
  });
};



export function ReviewDashboard({ 
  bloque, 
  onEditSession,
  onDeleteSession,
}: ReviewDashboardProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);

  const visibleSessions = React.useMemo(() => {
    if (!bloque.sesiones) return [];
    
    const withIndex = bloque.sesiones.map((s, idx) => ({ ...s, originalIndex: idx }));

    const filtered = withIndex.filter(s => {
       const isExact = s.match_status === 'EXACT' || s.match_status === 'ALIAS_DB';
       if (s.manual_validated) return false; 
       if (isExact) return false; 
       return true;
    });

    return sortSessions(filtered);
  }, [bloque.sesiones]);

  const errorCount = visibleSessions.filter(s => getSessionStatus(s).color === 'red').length;
  const suggestionCount = visibleSessions.length - errorCount;

  if (visibleSessions.length === 0) return null;

  return (
    <Card className={cn(
      "border-l-4 mb-6 transition-all duration-300",
      errorCount > 0 ? "border-l-red-500" : "border-l-indigo-500"
    )}>
      {/* HEADER */}
      <div 
        className="p-4 flex flex-col sm:flex-row items-center justify-between gap-4 cursor-pointer hover:bg-muted/50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-4 flex-1">
          <div className={cn(
            "p-2 rounded-full",
            errorCount > 0 ? "bg-red-100 text-red-700" : "bg-indigo-100 text-indigo-700"
          )}>
            {errorCount > 0 ? <AlertTriangle className="h-5 w-5" /> : <Sparkles className="h-5 w-5" />}
          </div>
          <div>
            <h3 className="font-semibold text-sm">
              {errorCount > 0 ? "Errores detectados" : "Sugerencias automáticas"}
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              {errorCount > 0 ? (
                <>
                  <strong className="text-red-600">{errorCount} errores bloqueantes</strong> que impiden guardar.
                  {suggestionCount > 0 && ` Además, hay ${suggestionCount} sugerencias automáticas disponibles para revisión.`}
                </>
              ) : (
                `Todo parece correcto. Hay ${suggestionCount} sesiones generadas automáticamente que podrías revisar (opcional).`
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
           {isExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </div>

      {/* BODY */}
      {isExpanded && (
        <div className="border-t bg-muted/5 p-4 animate-in slide-in-from-top-2">
          <ScrollArea className="h-[350px] rounded-md border bg-background">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[140px]">Estado</TableHead>
                  <TableHead>Asignatura / Aula</TableHead>
                  <TableHead>Horario</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleSessions.map((sesion) => {
                  const status = getSessionStatus(sesion);
                  const isRed = status.color === 'red';
                  const displayName = (sesion.asignatura_sugerida || sesion.asignatura || "Desconocida") as string;
                  
                  return (
                    <TableRow 
                      key={sesion.originalIndex} 
                      className={cn(isRed ? "bg-red-50/40 hover:bg-red-50/60" : "hover:bg-muted/50")}
                    >
                      <TableCell>
                        <Badge 
                          variant="outline" 
                          className={cn(
                            "gap-1.5 pl-1.5 pr-2.5 py-1 font-normal border shadow-sm",
                            status.type === 'ERROR_ASIGNATURA' && "border-red-200 bg-red-100 text-red-700",
                            status.type === 'ERROR_AULA' && "border-red-200 bg-red-100 text-red-700",
                            status.type === 'SUGGESTED' && "border-indigo-200 bg-indigo-50 text-indigo-700",
                            status.type === 'VALID' && "border-blue-200 bg-blue-50 text-blue-700",
                          )}
                        >
                          {status.icon}
                          <span>{status.label}</span>
                        </Badge>
                      </TableCell>
                      
                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <span 
                            className={cn(
                              "font-medium text-sm flex items-center gap-2",
                              status.type === 'ERROR_ASIGNATURA' ? "text-red-600" : "text-foreground"
                            )}
                          >
                             {displayName}
                             {status.type === 'SUGGESTED' && (
                               <Sparkles className="h-3 w-3 text-indigo-400" />
                             )}
                          </span>

                          <span className={cn(
                            "text-xs flex items-center gap-1",
                            status.type === 'ERROR_AULA' ? "text-red-600 font-semibold" : "text-muted-foreground"
                          )}>
                            <MapPin className="h-3 w-3" />
                            {sesion.aula || "Sin aula"}
                          </span>
                        </div>
                      </TableCell>
                      
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        <div className="flex flex-col">
                          <span className="font-medium text-foreground">{sesion.dia}</span>
                          <span>{sesion.hora_inicio} - {sesion.hora_fin}</span>
                        </div>
                      </TableCell>
                      
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button 
                            size="sm" 
                            variant={isRed ? "default" : "ghost"} 
                            className={cn(
                              "h-8 px-3 gap-2",
                              isRed && "bg-red-600 hover:bg-red-700 text-white shadow-sm"
                            )}
                            onClick={() => onEditSession(sesion.originalIndex)}
                          >
                            <Edit className="h-3.5 w-3.5" />
                            {isRed && <span>Corregir</span>}
                          </Button>

                          <Button 
                            size="icon" 
                            variant="ghost" 
                            className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-red-50"
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
        </div>
      )}
    </Card>
  );
}