import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { MatchStatus } from '@/lib/api/docencia/horarios';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

type MatchColor = 'success' | 'warning' | 'destructive' | 'default';

export function getMatchColor(status?: MatchStatus | string | null): MatchColor {
  if (!status) return 'default';

  switch (status) {
    case 'EXACT':
    case 'ALIAS_DB':
    case 'FUZZY_AUTO':
      return 'success'; // Verde: Todo OK
    
    case 'FUZZY_LOW_CONFIDENCE':
      return 'warning'; // Naranja: Requiere revisión
    
    case 'NO_MATCH':
      return 'destructive'; // Rojo: Crítico
    
    default:
      return 'default';
  }
}

export function getMatchFeedbackMessage(status?: MatchStatus | string | null, sugerencia?: string | null): string | null {
  if (status === 'FUZZY_LOW_CONFIDENCE' && sugerencia) {
    return `Confianza baja. ¿Quizás quisiste decir: "${sugerencia}"?`;
  }
  if (status === 'NO_MATCH') {
    return 'No se ha encontrado ninguna asignatura similar en la base de datos.';
  }
  return null;
}