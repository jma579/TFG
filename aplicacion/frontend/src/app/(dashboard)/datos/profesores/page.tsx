import { listProfesores } from '@/lib/api/client';
import { ProfessorsTable } from '@/components/professors/table';
import type { Professor } from '@/components/professors/data';
import { PageTitle } from '@/components/common/page-title';

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
    <div className="space-y-6">
      <PageTitle
        title="Profesorado"
        subtitle="Directorio de docentes y sus departamentos."
      />
      <ProfessorsTable data={data} />
    </div>
  );
}
