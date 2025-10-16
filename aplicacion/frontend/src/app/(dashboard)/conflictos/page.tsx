import { columns } from '@/components/conflicts/columns';
import { DataTable } from '@/components/conflicts/data-table';
import { conflictsMock } from '@/components/conflicts/data';

export default function ConflictosPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <DataTable columns={columns} data={conflictsMock} />
    </div>
  );
}

