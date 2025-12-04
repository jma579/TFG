import { listProfesores } from '@/lib/api/client';
import { ProfessorsScreen } from '@/components/professors/professors-screen';
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

  data.sort((a, b) => {
    const nameA = `${a.nombre} ${a.apellidos}`.toLowerCase();
    const nameB = `${b.nombre} ${b.apellidos}`.toLowerCase();
    return nameA.localeCompare(nameB);
  });

  return (
    <div className="space-y-6">
      <PageTitle
        title="Profesores"
        subtitle="Gestión del personal docente y departamentos."
      />
      <ProfessorsScreen data={data} />
    </div>
  );
}
