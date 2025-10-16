import { schedulesMock } from '@/components/schedules/data';
import { SchedulesScreen } from '@/components/schedules/schedules-screen';

export default function HorariosPage() {
  return <SchedulesScreen data={schedulesMock} />;
}
