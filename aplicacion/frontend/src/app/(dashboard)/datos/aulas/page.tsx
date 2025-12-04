import { RoomsScreen } from '@/components/rooms/rooms-screen';
import { listAulas, type AulaOut } from '@/lib/api/client';
import type { Room } from '@/components/rooms/data';
import { PageTitle } from '@/components/common/page-title';

export default async function AulasPage() {
  const resp = await listAulas();

  const rooms: Room[] = (resp.items as AulaOut[]).map((aula) => ({
    id: String(aula.id),
    nombre: aula.nombre,
    codigo: aula.codigo,
    tipo: aula.tipo,
    capacidad: aula.capacidad ?? null,
  }));

  return (
    <div className="space-y-6">
      <PageTitle
        title="Gestión de Aulas"
        subtitle="Inventario de espacios y capacidades."
      />
      <RoomsScreen initialData={rooms} />
    </div>
  );
}
