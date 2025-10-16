export type ConflictRef = {
  id: string;
  titulo: string;
  severidad: 'baja' | 'media' | 'alta' | 'crítica';
};

export type ScheduleRow = {
  id: string;
  titulacion: string;
  mencion: string | null;
  curso: string;           // p.ej. "1º", "2º", "3ºA"
  cuatrimestre: 1 | 2;
  status: 'ok' | 'con_conflictos' | 'procesando';
  conflicts: ConflictRef[]; // si status = con_conflictos, lista aquí
};

export const schedulesMock: ScheduleRow[] = [
  {
    id: 'SCH-001',
    titulacion: 'Grado Matemáticas',
    mencion: null,
    curso: '3ºA',
    cuatrimestre: 1,
    status: 'con_conflictos',
    conflicts: [
      { id: 'C-001', titulo: 'Solape en Aula 2.3 (Lun 10:00-11:00)', severidad: 'alta' },
      { id: 'C-003', titulo: 'Capacidad Aula 1.1 (Mié 09:00-10:00)', severidad: 'media' },
    ],
  },
  {
    id: 'SCH-002',
    titulacion: 'Grado Física',
    mencion: 'Mención en Electrónica',
    curso: '2ºB',
    cuatrimestre: 1,
    status: 'con_conflictos',
    conflicts: [
      { id: 'C-002', titulo: 'Profesor García en dos grupos (Mar 12:00-13:00)', severidad: 'crítica' },
    ],
  },
  {
    id: 'SCH-003',
    titulacion: 'Grado Matemáticas',
    mencion: 'Mención en Estadística',
    curso: '4º',
    cuatrimestre: 2,
    status: 'ok',
    conflicts: [],
  },
  {
    id: 'SCH-004',
    titulacion: 'Grado Física',
    mencion: null,
    curso: '1º',
    cuatrimestre: 2,
    status: 'procesando',
    conflicts: [],
  },
];
