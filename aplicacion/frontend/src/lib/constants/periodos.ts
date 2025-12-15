// Mapeo basado en tu archivo enums.py
export const PERIODOS = [
  { value: 'anual', label: 'Anual' },
  { value: 'primer_semestre', label: 'Primer Semestre' },
  { value: 'segundo_semestre', label: 'Segundo Semestre' },
  { value: 'primer_cuatrimestre', label: 'Primer Cuatrimestre' },
  { value: 'segundo_cuatrimestre', label: 'Segundo Cuatrimestre' },
  { value: 'tercer_cuatrimestre', label: 'Tercer Cuatrimestre' },
  { value: 'cuarto_cuatrimestre', label: 'Cuarto Cuatrimestre' },
] as const;

export function getPeriodoLabel(value: string): string {
  const found = PERIODOS.find(p => p.value === value);
  return found ? found.label : value;
}