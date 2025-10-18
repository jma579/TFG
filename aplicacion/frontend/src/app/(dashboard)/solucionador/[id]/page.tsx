// src/app/(dashboard)/solucionador/[id]/page.tsx
import { notFound } from 'next/navigation';
import { conflictsMock, type Conflict } from '@/components/conflicts/data';
import { ConflictDetails } from '@/components/solver/conflict-details';
import { ScheduleContextBar, type CourseRef } from '@/components/solver/schedule-context-bar';
import { InteractiveScheduleGrid } from '@/components/solver/interactive-schedule-grid';
import { sessionsMock } from '@/components/solver/schedule-mock';
import { SolverActions } from '@/components/solver/solver-actions';

type RouteParams = { id: string };

function buildDescription(c: Conflict): string {
  switch (c.tipo) {
    case 'Solape de aula':
      return 'Se han detectado sesiones solapadas en la misma aula. Prioriza el ajuste de una de las sesiones (hora o aula) para eliminar el solape.';
    case 'Solape de profesor':
      return 'El profesor aparece asignado a más de un grupo en el mismo intervalo. Ajusta la planificación de una de las sesiones para resolver el conflicto.';
    case 'Capacidad de aula':
      return 'La capacidad del aula podría ser insuficiente para el tamaño del grupo. Valora un cambio de aula o la división del grupo.';
    default:
      return 'Conflicto detectado. Revisa el horario interactivo para aplicar la corrección adecuada y resolver la incidencia.';
  }
}

/**
 * Mock simple: devuelve 1 o 2 cursos implicados según el tipo de conflicto.
 * Sustituiremos esta lógica cuando conectemos con el backend real.
 */
function getCoursesForConflict(c: Conflict): CourseRef[] {
  if (c.tipo === 'Solape de profesor') {
    return [
      { id: 'mat-3A', label: 'Grado Matemáticas · 3ºA' },
      { id: 'fis-2B', label: 'Grado Física · 2ºB' },
    ];
  }
  return [{ id: 'mat-3A', label: 'Grado Matemáticas · 3ºA' }];
}

export default async function SolucionadorPage({
  params,
}: {
  params: Promise<RouteParams>;
}) {
  // En Next 15, params es asíncrono:
  const { id } = await params;

  const conflict = conflictsMock.find((c) => c.id === id);
  if (!conflict) return notFound();

  const courses = getCoursesForConflict(conflict);
  const selectedCourseId = courses[0]?.id;

  // Sesiones a mostrar en el horario según el curso seleccionado (mock)
  const sessionsForCourse = sessionsMock.filter((s) => s.courseId === selectedCourseId);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* 1) Descripción detallada del conflicto */}
      <ConflictDetails conflict={conflict} description={buildDescription(conflict)} />

      {/* 2) Barra contextual: título y “pestañas” de curso/titulación */}
      <ScheduleContextBar courses={courses} defaultValue={selectedCourseId} />

      {/* 3) Horario interactivo con datos de prueba */}
      <InteractiveScheduleGrid
        start="08:30"
        end="20:00"
        stepMin={30}
        sessions={sessionsForCourse}
      />

      {/* 4) (Próximo paso) Botón “Resolver conflicto” abajo a la derecha */}
      <SolverActions conflictId={id} />
    </div>
  );
}
