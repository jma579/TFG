// Sesiones de prueba para dos cursos: mat-3A y fis-2B
// C-001: Solape en Aula 2.3 (Lun 10:00-11:00) — dos sesiones en mismo aula/tiempo (mismo curso)
// C-002: Prof. García en dos grupos (Mar 12:00-13:00) — dos cursos distintos misma hora
// C-003: Capacidad Aula 1.1 (Mié 09:00-10:00) — sesión simple que “marca” ese tramo

export type Session = {
  id: string;
  courseId: 'mat-3A' | 'fis-2B';
  dayIndex: 0 | 1 | 2 | 3 | 4; // 0=L, 1=M, 2=X, 3=J, 4=V
  start: string; // 'HH:MM'
  end: string;   // 'HH:MM'
  title: string;
  room: string;
  teacher: string;
  color?: 'blue' | 'green' | 'orange' | 'red' | 'purple';
};

export const sessionsMock: Session[] = [
  // --- C-001 Solape de aula (Lun 10:00-11:00) en Aula 2.3, mismo curso mat-3A ---
  {
    id: 'S-MAT-01',
    courseId: 'mat-3A',
    dayIndex: 0, start: '10:00', end: '11:00',
    title: 'Álgebra',
    room: 'Aula 2.3',
    teacher: 'Dra. López',
    color: 'blue',
  },
  {
    id: 'S-MAT-02',
    courseId: 'mat-3A',
    dayIndex: 0, start: '10:00', end: '11:00',
    title: 'Cálculo',
    room: 'Aula 2.3',
    teacher: 'Dr. Pérez',
    color: 'red',
  },

  // --- C-002 Solape de profesor (Mar 12:00-13:00), Prof. García en dos cursos ---
  {
    id: 'S-MAT-03',
    courseId: 'mat-3A',
    dayIndex: 1, start: '12:00', end: '13:00',
    title: 'Estadística',
    room: 'Aula 1.2',
    teacher: 'Prof. García',
    color: 'orange',
  },
  {
    id: 'S-FIS-01',
    courseId: 'fis-2B',
    dayIndex: 1, start: '12:00', end: '13:00',
    title: 'Mecánica',
    room: 'Aula 3.1',
    teacher: 'Prof. García',
    color: 'orange',
  },

  // --- C-003 Capacidad Aula 1.1 (Mié 09:00-10:00) ---
  {
    id: 'S-MAT-04',
    courseId: 'mat-3A',
    dayIndex: 2, start: '09:00', end: '10:00',
    title: 'Topología (Grupo grande)',
    room: 'Aula 1.1',
    teacher: 'Dra. Ruiz',
    color: 'green',
  },

  // --- Relleno para que el horario se vea “vivo” ---
  {
    id: 'S-MAT-05',
    courseId: 'mat-3A',
    dayIndex: 3, start: '11:30', end: '13:00',
    title: 'Análisis Numérico',
    room: 'Aula 2.1',
    teacher: 'Dr. Soto',
    color: 'purple',
  },
  {
    id: 'S-FIS-02',
    courseId: 'fis-2B',
    dayIndex: 4, start: '10:30', end: '12:00',
    title: 'Electro.',
    room: 'Aula 1.4',
    teacher: 'Dra. Vega',
    color: 'blue',
  },
];
