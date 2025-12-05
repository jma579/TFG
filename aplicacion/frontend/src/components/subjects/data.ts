// Tipos alineados con tu modelo SQLAlchemy + dataclasses de extracción

export type Titulacion = {
  titulacion: string;
  tipo_asignatura: string;
  curso: string; // p. ej. "3ºA"
};

export type Teacher = {
  nombre: string;
  apellidos: string;
};

export type SubjectRow = {
  // DB
  id: string;
  codigo_plan: string;
  nombre: string;
  periodo: string;      // Enum(Periodo) → string para el mock: "ANUAL" | "SEMESTRAL"
  num_periodo: number;  // p.ej. 1 ó 2 si es semestral
  ects: number;
  modalidad: string;    // Enum(ModalidadAsignatura)
  idioma: string;       // Enum(Idioma) → "ESPAÑOL", "INGLÉS", etc.
  english_friendly: boolean;
  activo: boolean;

  // Extracción (SubjectSheet)
  titulaciones: Titulacion[];
  profesores: Teacher[];
  
  // Contadores (para vista de lista)
  num_profesores?: number;
  num_titulaciones?: number;

  // Estados de extracción/parseo
  parsing_ok: boolean;
  extraction_ok: boolean;
};

export const subjectsMock: SubjectRow[] = [
  {
    id: 'ASG-001',
    codigo_plan: 'MAT001',
    nombre: 'Álgebra Lineal',
    periodo: 'SEMESTRAL',
    num_periodo: 1,
    ects: 6,
    modalidad: 'PRESENCIAL',
    idioma: 'ESPAÑOL',
    english_friendly: false,
    activo: true,
    titulaciones: [
      { titulacion: 'Grado Matemáticas', tipo_asignatura: 'Obligatoria', curso: '1º' },
    ],
    profesores: [{ nombre: 'Laura', apellidos: 'López' }],
    parsing_ok: true,
    extraction_ok: true,
  },
  {
    id: 'ASG-002',
    codigo_plan: 'MAT203',
    nombre: 'Cálculo Avanzado',
    periodo: 'ANUAL',
    num_periodo: 0,
    ects: 9,
    modalidad: 'PRESENCIAL',
    idioma: 'ESPAÑOL',
    english_friendly: false,
    activo: true,
    titulaciones: [
      { titulacion: 'Grado Matemáticas', tipo_asignatura: 'Obligatoria', curso: '2º' },
      { titulacion: 'Grado Física', tipo_asignatura: 'Optativa', curso: '3º' },
    ],
    profesores: [
      { nombre: 'Javier', apellidos: 'Pérez' },
      { nombre: 'Ana', apellidos: 'Ruiz' },
    ],
    parsing_ok: true,
    extraction_ok: false, // simula incidencias en extracción
  },
  {
    id: 'ASG-003',
    codigo_plan: 'FIS110',
    nombre: 'Mecánica Clásica',
    periodo: 'SEMESTRAL',
    num_periodo: 2,
    ects: 6,
    modalidad: 'PRESENCIAL',
    idioma: 'INGLÉS',
    english_friendly: true,
    activo: false,
    titulaciones: [{ titulacion: 'Grado Física', tipo_asignatura: 'Obligatoria', curso: '1º' }],
    profesores: [{ nombre: 'Carlos', apellidos: 'García' }],
    parsing_ok: false, // fallo de parsing
    extraction_ok: false,
  },
];
