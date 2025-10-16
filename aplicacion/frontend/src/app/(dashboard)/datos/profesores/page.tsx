import { professorsMock } from '@/components/professors/data';
import { ProfessorsTable } from '@/components/professors/table';

export default function ProfesoresPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <ProfessorsTable data={professorsMock} />
    </div>
  );
}
