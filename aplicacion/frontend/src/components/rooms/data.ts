export type Room = {
  id: string;
  nombre: string;
  capacidad: number;
  ubicacion: string; // facultad/localización
};

export const locationsMock = [
  'Facultad de Matemáticas',
  'Facultad de Física',
  'Edificio Aulas Norte',
  'Edificio Aulas Sur',
];

export const roomsMock: Room[] = [
  { id: 'R-101', nombre: 'Aula 1.1', capacidad: 40, ubicacion: 'Facultad de Matemáticas' },
  { id: 'R-102', nombre: 'Aula 2.3', capacidad: 60, ubicacion: 'Facultad de Física' },
  { id: 'R-103', nombre: 'Aula Magna', capacidad: 200, ubicacion: 'Edificio Aulas Norte' },
];
