import { listAsignaturas, AsignaturaOut } from '@/lib/api/client';
import { SubjectsScreen } from '@/components/subjects/subjects-screen';
import type { SubjectRow } from '@/components/subjects/data';

function mapAsignaturaToSubjectRow(a: AsignaturaOut): SubjectRow {
  return {
    id: String(a.id),
    codigo_plan: a.codigo_plan,
    nombre: a.nombre,
    periodo: a.periodo,
    num_periodo: a.num_periodo ?? 0,
    ects: a.ects ?? 0,
    modalidad: a.modalidad ?? '—',
    idioma: a.idioma ?? '—',
    english_friendly: a.english_friendly ?? false,
    activo: a.activo ?? true,
    profesores: [],
    titulaciones: [],
    parsing_ok: true,
    extraction_ok: true,
  };
}

export default async function FichasAcademicasPage() {
  // Puedes ajustar el limit según lo que esperes
  const resp = await listAsignaturas();

  const data: SubjectRow[] = resp.items.map(mapAsignaturaToSubjectRow);

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <SubjectsScreen data={data} />
    </div>
  );
}
