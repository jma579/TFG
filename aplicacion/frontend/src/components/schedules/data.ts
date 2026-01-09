export type EstadoHorario = 'OK' | 'CONFLICTO';

export type ScheduleSummary = {
  // Identificadores compuestos para usar como key
  programa_id: number;
  curso: number;
  cuatrimestre: number;
  
  // Datos visuales
  programa_nombre: string;
  menciones: string[]; // Lista de menciones o vacío
  
  // Métricas
  total_asignaturas: number;
  total_sesiones: number;
  
  // Estado
  estado: EstadoHorario;
  conflictos_count: number;
  ultima_actualizacion: string;
};