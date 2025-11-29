import { notFound } from 'next/navigation';
import { InteractiveScheduleGrid } from '@/components/solver/interactive-schedule-grid';
import { sessionsMock } from '@/components/solver/schedule-mock';
import { RevisionActions } from '@/components/uploads/revision-actions';

export default async function RevisionHorarioPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const sessions = sessionsMock; // mock

  if (!sessions) return notFound();

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Revisión de horario extraído</h2>
          <p className="text-sm text-muted-foreground">
            ID de subida: <span className="font-mono">{id}</span>
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Revisa el horario detectado y realiza las correcciones necesarias antes de confirmar.
          </p>
        </div>
        <RevisionActions id={id} />
      </div>

      <InteractiveScheduleGrid start="08:30" end="20:00" stepMin={30} sessions={sessions} />
    </div>
  );
}
