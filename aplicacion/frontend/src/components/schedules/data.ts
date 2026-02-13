export type EstadoHorario = 'OK' | 'CONFLICTO' | 'PROCESANDO';

export type ScheduleSummary = {
  programa_id: number;
  curso: number;
  periodo:string;
  
  programa_nombre: string;
  menciones: string[]; 
  
  total_asignaturas: number;
  total_sesiones: number;
  
  estado: EstadoHorario;
  conflictos_count: number;
  
  ultima_actualizacion: string;
};

export type ScheduleRow = {
  id: string;
  titulacion: string;
  mencion: string | null;
  curso: number;
  cuatrimestre: number;
  status: 'ok' | 'procesando' | 'con_conflictos';
  conflicts: Array<{
    id: string;
    titulo: string;
    severidad: string;
  }>;
};