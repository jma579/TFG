export type EstadoHorario = 'OK' | 'CONFLICTO' | 'PROCESANDO';

export type ScheduleSummary = {
  // Identificadores compuestos para usar como key
  programa_id: number;
  curso: number;
  periodo:string;
  
  // Datos visuales
  programa_nombre: string;
  menciones: string[]; // Lista de menciones o vacío
  
  // Métricas
  total_asignaturas: number;
  total_sesiones: number;
  
  // Estado
  estado: EstadoHorario;
  conflictos_count: number;
  
  // Metadatos
  ultima_actualizacion: string;
};