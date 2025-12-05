import { columns } from '@/components/conflicts/columns';
import { DataTable } from '@/components/conflicts/data-table';
import { conflictsMock } from '@/components/conflicts/data';
import { PageTitle } from '@/components/common/page-title';

export default function ConflictosPage() {
  return (
    <div className="space-y-6">
      <PageTitle
        title="Resolución de Conflictos"
        subtitle="Detecta y gestiona solapamientos en la programación académica."
      />
      <DataTable columns={columns} data={conflictsMock} />
    </div>
  );
}

