import { AlertTriangle, ArrowRight, BookOpen, Calendar, CheckCircle, Layers, Loader2, Trash2 } from 'lucide-react';
import React from 'react';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter,CardHeader, CardTitle } from '@/components/ui/card';

import { ScheduleSummary } from './data'; 

interface ScheduleCardProps {
  data: ScheduleSummary;
  onView: (data: ScheduleSummary) => void;
  onDelete: (data: ScheduleSummary) => void; 
}

export const ScheduleCard: React.FC<ScheduleCardProps> = ({ data, onView, onDelete }) => {
  const isConflict = data.estado === 'CONFLICTO';
  const isProcessing = data.estado === 'PROCESANDO';

  const esCursoGeneral = data.menciones.length === 0;
  const nombreItinerario = esCursoGeneral ? "Curso General / Troncal" : data.menciones[0];

  const numCuatri = data.periodo.includes('primer') ? 1 : 2;

  return (
    <Card className={`flex flex-col h-full border-l-4 ${
      isConflict ? 'border-l-red-500' : isProcessing ? 'border-l-blue-500' : 'border-l-green-500'
    } shadow-sm hover:shadow-md transition-all duration-200`}>
      
      {/* CABECERA */}
      <CardHeader className="pb-2 space-y-1">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">
              {numCuatri}º Cuatrimestre
            </p>
            <CardTitle className="text-2xl font-bold text-gray-900">
              {data.curso}º Curso
            </CardTitle>
          </div>
          
          {isConflict ? (
            <Badge 
              variant="destructive" 
              className="bg-red-100 text-red-700 border-red-200 hover:bg-red-200 px-2 py-1"
            >
              <AlertTriangle className="w-3.5 h-3.5 mr-1.5" />
              {data.conflictos_count} {data.conflictos_count === 1 ? 'Conflicto' : 'Conflictos'}
            </Badge>
          ) : isProcessing ? (
            <Badge variant="secondary" className="bg-blue-50 text-blue-700 border-blue-200">
              <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              Procesando
            </Badge>
          ) : (
            <Badge variant="secondary" className="bg-green-50 text-green-700 border-green-200">
              <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
              OK
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 pb-4 flex flex-col gap-4">
        {/* ITINERARIO */}
        <div>
          <div className="flex items-center gap-2 mb-1.5 text-xs text-gray-500 font-medium uppercase">
            <Layers className="w-3.5 h-3.5" />
            <span>Itinerario</span>
          </div>
          <div className={`flex items-center gap-2 px-3 py-2 rounded-md border text-sm font-medium w-full ${
            esCursoGeneral 
              ? "bg-gray-50 text-gray-700 border-gray-200" 
              : "bg-blue-50 text-blue-700 border-blue-100"
          }`}>
            <span className="truncate" title={nombreItinerario}>
              {nombreItinerario}
            </span>
          </div>
        </div>

        {/* MÉTRICAS */}
        <div className="mt-auto grid grid-cols-2 gap-3">
          <div className="bg-white p-2.5 rounded-lg border border-gray-100 shadow-sm flex flex-col items-center justify-center text-center">
            <span className="text-xl font-bold text-gray-900">{data.total_sesiones}</span>
            <div className="flex items-center gap-1.5 text-xs text-gray-500 font-medium mt-0.5">
              <Calendar className="w-3 h-3" />
              Sesiones
            </div>
          </div>
          <div className="bg-white p-2.5 rounded-lg border border-gray-100 shadow-sm flex flex-col items-center justify-center text-center">
            <span className="text-xl font-bold text-gray-900">{data.total_asignaturas}</span>
            <div className="flex items-center gap-1.5 text-xs text-gray-500 font-medium mt-0.5">
              <BookOpen className="w-3 h-3" />
              Asignaturas
            </div>
          </div>
        </div>
      </CardContent>

      {/* PIE DE TARJETA: ACCIONES */}
      <CardFooter className="pt-3 pb-3 flex gap-3 border-t bg-gray-50/30">
        
        {/* BOTÓN ELIMINAR CON DIÁLOGO DE CONFIRMACIÓN */}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button 
              variant="outline" 
              className="flex-1 border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 hover:border-red-300 h-9 transition-colors"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Eliminar
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>¿Estás seguro de eliminar este horario?</AlertDialogTitle>
              <AlertDialogDescription>
                Esta acción eliminará permanentemente la planificación de <strong>{data.curso}º Curso</strong>
                {!esCursoGeneral ? (
                  <> con mención en <strong>{nombreItinerario}</strong></>
                ) : null}
                . Esta acción no se puede deshacer.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction 
                onClick={() => onDelete(data)}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Eliminar Horario
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
        
        {/* BOTÓN VER HORARIO */}
        <Button 
          className="flex-1 h-9 bg-blue-600 hover:bg-blue-700 shadow-sm text-white"
          onClick={() => onView(data)}
        >
          Ver Horario <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </CardFooter>
    </Card>
  );
};