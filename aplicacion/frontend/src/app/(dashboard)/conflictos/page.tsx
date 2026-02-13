import { PageTitle } from '@/components/common/page-title';
import { columns } from '@/components/conflicts/columns';
import { DataTable } from '@/components/conflicts/data-table';
import { ConflictoOut, listConflictos } from '@/lib/api/conflictos';

export const dynamic = 'force-dynamic';

const CONFLICTS_LIMIT = 100;

export default async function ConflictosPage() {
  let data: ConflictoOut[] = [];
  let error: string | null = null;

  try {
    const response = await listConflictos({ 
      limit: CONFLICTS_LIMIT,
      estado: 'por_revisar' 
    });
    data = response.items;
  } catch (e) {
    console.error("Error cargando conflictos:", e);
    error = "No se pudieron cargar los conflictos. Verifica la conexión con la API.";
  }

  return (
    <div className="space-y-6 p-6">
      <PageTitle
        title="Auditoría de Conflictos"
        subtitle="Panel de control de calidad del horario académico. Revise y solucione las incidencias detectadas."
      />
      
      {error ? (
        <div className="p-4 text-red-600 bg-red-50 rounded-md border border-red-200">
          {error}
        </div>
      ) : (
        <DataTable 
          columns={columns} 
          data={data} 
          emptyText="¡Excelente! No hay conflictos pendientes de revisión."
        />
      )}
    </div>
  );
}