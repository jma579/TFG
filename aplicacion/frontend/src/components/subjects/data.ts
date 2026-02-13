export type Titulacion = {
  titulacion: string;
  tipo_asignatura: string;
  curso: string; 
};

export type Teacher = {
  nombre: string;
  apellidos: string;
};

export type SubjectRow = {
  id: string;
  codigo_plan: string;
  nombre: string;
  periodo: string;     
  num_periodo: number; 
  ects: number;
  modalidad: string;   
  idioma: string;     
  english_friendly: boolean;
  activo: boolean;

  titulaciones: Titulacion[];
  profesores: Teacher[];
  
  num_profesores?: number;
  num_titulaciones?: number;

  parsing_ok: boolean;
  extraction_ok: boolean;
};