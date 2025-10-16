export type Conflict = {
  id: string;
  titulo: string;
  tipo: 'Solape de aula' | 'Solape de profesor' | 'Capacidad de aula' | 'Otro';
  severidad: 'baja' | 'media' | 'alta' | 'crítica';
  estado: 'abierto' | 'en progreso' | 'resuelto';
};

export const conflictsMock: Conflict[] = [
  {
    id: 'C-001',
    titulo: 'Solape en Aula 2.3 (Lun 10:00-11:00)',
    tipo: 'Solape de aula',
    severidad: 'alta',
    estado: 'abierto',
  },
  {
    id: 'C-002',
    titulo: 'Profesor García asignado a 2 grupos (Mar 12:00-13:00)',
    tipo: 'Solape de profesor',
    severidad: 'crítica',
    estado: 'en progreso',
  },
  {
    id: 'C-003',
    titulo: 'Capacidad Aula 1.1 inferior al grupo',
    tipo: 'Capacidad de aula',
    severidad: 'media',
    estado: 'resuelto',
  },
];
