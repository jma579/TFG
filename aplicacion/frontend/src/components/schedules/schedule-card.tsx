import React from 'react';
import { ResumenHorario } from '@/types/dashboard';
import { Calendar, AlertTriangle, CheckCircle, ArrowRight, BookOpen, Layers, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';

interface ScheduleCardProps {
  data: ResumenHorario;
  onView: (data: ResumenHorario) => void;
  onSolve: (data: ResumenHorario) => void;
}

export const ScheduleCard: React.FC<ScheduleCardProps> = ({ data, onView, onSolve }) => {
  const isConflict = data.estado === 'CONFLICTO';
  const isProcessing = data.estado === 'PROCESANDO';

  // Lógica: Si la lista está vacía es curso general, si no, mostramos la mención.
  const esCursoGeneral = data.menciones.length === 0;
  const nombreItinerario = esCursoGeneral ? "Curso General / Troncal" : data.menciones[0];

  return (
    <Card className={`flex flex-col h-full border-l-4 ${
      isConflict ? 'border-l-red-500' : isProcessing ? 'border-l-blue-500' : 'border-l-green-500'
    } shadow-sm hover:shadow-md transition-all duration-200`}>
      
      {/* CABECERA: Título y Estado */}
      <CardHeader className="pb-2 space-y-1">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">
              {data.cuatrimestre}º Cuatrimestre
            </p>
            <CardTitle className="text-2xl font-bold text-gray-900">
              {data.curso}º Curso
            </CardTitle>
          </div>
          
          {isConflict ? (
            <Badge variant="destructive" className="bg-red-50 text-red-700 border-red-200">
              <AlertTriangle className="w-3.5 h-3.5 mr-1.5" />
              {data.conflictos_count}
            </Badge>
          ) : isProcessing ? (
            <Badge variant="secondary" className="bg-blue-50 text-blue-700 border-blue-200">
              <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
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
        
        {/* ZONA SUPERIOR: Itinerario (Justo debajo del título) */}
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

        {/* ZONA INFERIOR: Métricas (Resumen de contenido) */}
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

      {/* PIE: Acciones */}
      <CardFooter className="pt-3 pb-3 flex gap-3 border-t bg-gray-50/30">
        {isConflict ? (
          <Button 
            className="flex-1 bg-red-600 hover:bg-red-700 text-white shadow-sm h-9"
            onClick={() => onSolve(data)}
          >
            <AlertTriangle className="w-4 h-4 mr-2" />
            Resolver
          </Button>
        ) : (
          <div className="flex-1"></div> 
        )}
        
        <Button 
          variant={isConflict ? "outline" : "default"}
          className={`flex-1 h-9 ${!isConflict ? 'bg-blue-600 hover:bg-blue-700 shadow-sm' : 'border-gray-300'}`}
          onClick={() => onView(data)}
        >
          Ver Horario <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </CardFooter>
    </Card>
  );
};