import { schedulesMock } from '@/components/schedules/data';
import { SchedulesScreen } from '@/components/schedules/schedules-screen';
import { PageTitle } from '@/components/common/page-title';

export const dynamic = 'force-dynamic';

export default function HorariosPage() {
  return (
    <div className="space-y-6">
      <PageTitle
        title="Consulta de Horarios"
        subtitle="Visualiza las sesiones programadas por curso y grupo."
      />
      <SchedulesScreen data={schedulesMock} />
    </div>
  );
}
