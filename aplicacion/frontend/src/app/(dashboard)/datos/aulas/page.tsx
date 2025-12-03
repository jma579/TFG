import { RoomsScreen } from '@/components/rooms/rooms-screen';
import { listAulas, type AulaOut } from '@/lib/api/client';
import type { Room } from '@/components/rooms/data';

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
    <div className="mx-auto max-w-6xl space-y-4">
      <RoomsScreen initialData={rooms} />
    </div>
  );
}
