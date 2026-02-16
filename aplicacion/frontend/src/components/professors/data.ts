export type Professor = {
  id: string;
  nombre: string;
  apellidos: string;
  email: string | null;
  departamento: string | null;
  activo: boolean;
  total_restricciones?: number;
};