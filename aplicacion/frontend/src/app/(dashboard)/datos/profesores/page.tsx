import { listProfesores } from '@/lib/api/client';
import { ProfessorsTable } from '@/components/professors/table';
import type { Professor } from '@/components/professors/data';

export default async function ProfesoresPage() {
  const resp = await listProfesores();

  const data: Professor[] = resp.items.map((p) => ({
    id: String(p.id),
    nombre: p.nombre,
    apellidos: p.apellidos,
    email: p.email ?? null,
    departamento: p.departamento ?? null,
    activo: p.activo,
  }));

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <ProfessorsTable data={data} />
    </div>
  );
}
