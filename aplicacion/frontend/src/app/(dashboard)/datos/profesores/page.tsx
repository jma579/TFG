import { PageTitle } from '@/components/common/page-title';
import type { Professor } from '@/components/professors/data';
import { ProfessorsScreen } from '@/components/professors/professors-screen';
import { listProfesores } from '@/lib/api/recursos/profesores';

export const dynamic = 'force-dynamic';

const PROFESSORS_LIMIT = 1000;

export default async function ProfesoresPage() {
  let data: Professor[] = [];
  let error: string | null = null;

  try {
    const resp = await listProfesores({ limit: PROFESSORS_LIMIT });

    data = resp.items.map((p) => ({
      id: String(p.id),
      nombre: p.nombre,
      apellidos: p.apellidos,
      email: p.email ?? null,
      departamento: p.departamento ?? null,
      activo: p.activo,
    }));

    // Ordenar alfabéticamente por nombre completo
    data.sort((a, b) => {
      const nameA = `${a.nombre} ${a.apellidos}`.toLowerCase();
      const nameB = `${b.nombre} ${b.apellidos}`.toLowerCase();
      return nameA.localeCompare(nameB);
    });
  } catch (e) {
    console.error("Error cargando profesores:", e);
    error = "No se pudieron cargar los profesores. Verifica la conexión con la API.";
  }

  return (
    <div className="space-y-6 p-6">
      <PageTitle
        title="Profesores"
        subtitle="Gestión del personal docente y departamentos."
      />
      
      {error ? (
        <div className="p-4 text-red-600 bg-red-50 rounded-md border border-red-200">
          {error}
        </div>
      ) : (
        <ProfessorsScreen data={data} />
      )}
    </div>
  );
}