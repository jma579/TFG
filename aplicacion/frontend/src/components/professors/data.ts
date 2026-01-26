// Definimos el tipo aquí también para uso en componentes
export type TipoConciliacion = 'entrada_tardia' | 'salida_temprana' | 'mixta' | null;

export type Professor = {
  id: string;
  nombre: string;
  apellidos: string;
  email: string | null;
  departamento: string | null;
  activo: boolean;
  conciliacion: TipoConciliacion; // <--- Nuevo campo
};