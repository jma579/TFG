import { PageTitle } from '@/components/common/page-title';
import type { Room } from '@/components/rooms/data';
import { RoomsScreen } from '@/components/rooms/rooms-screen';
import { type AulaOut, listAulas } from '@/lib/api/recursos/aulas';

export const dynamic = 'force-dynamic';

export default async function AulasPage() {
  let rooms: Room[] = [];
  let error: string | null = null;

  try {
    const resp = await listAulas();

    rooms = resp.items.map((aula: AulaOut) => ({
      id: String(aula.id),
      nombre: aula.nombre,
      codigo: aula.codigo,
      tipo: aula.tipo,
      capacidad: aula.capacidad ?? null,
      activo: aula.activo,
    }));

    rooms.sort((a, b) => a.codigo.localeCompare(b.codigo));
  } catch (e) {
    console.error("Error cargando aulas:", e);
    error = "No se pudieron cargar las aulas. Verifica la conexión con la API.";
  }

  return (
    <div className="space-y-6">
      <PageTitle
        title="Aulas"
        subtitle="Gestión de espacios y capacidades."
      />
      
      {error ? (
        <div className="p-4 text-red-600 bg-red-50 rounded-md border border-red-200">
          {error}
        </div>
      ) : (
        <RoomsScreen initialData={rooms} />
      )}
    </div>
  );
}