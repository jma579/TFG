export type Professor = {
  id: string;
  nombre: string;       // "Ana Ruiz"
  departamento: string; // "Matemáticas", "Física", etc.
};

export const professorsMock: Professor[] = [
  { id: 'P-001', nombre: 'Laura López', departamento: 'Matemáticas' },
  { id: 'P-002', nombre: 'Carlos García', departamento: 'Física' },
  { id: 'P-003', nombre: 'Ana Ruiz', departamento: 'Estadística' },
  { id: 'P-004', nombre: 'Javier Pérez', departamento: 'Física' },
];
