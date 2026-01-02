import { listAsignaturas, AsignaturaOut } from '@/lib/api/catalogo/asignaturas';
import { SubjectsScreen } from '@/components/subjects/subjects-screen';
import type { SubjectRow } from '@/components/subjects/data';
import { PageTitle } from '@/components/common/page-title';

export const dynamic = 'force-dynamic';

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
    titulaciones: a.titulaciones?.map((t) => ({
      titulacion: t.programa.nombre,
      tipo_asignatura: t.tipo_asignatura ?? '—',
      curso: t.curso ? `${t.curso}º` : '—',
    })) ?? [],
    num_profesores: a.num_profesores ?? 0,
    num_titulaciones: a.num_titulaciones ?? 0,
    parsing_ok: true,
    extraction_ok: true,
  };
}

export default async function FichasAcademicasPage() {
  // Puedes ajustar el limit según lo que esperes
  const resp = await listAsignaturas({limit: 1000});

  const data: SubjectRow[] = resp.items.map(mapAsignaturaToSubjectRow);

  return (
    <div className="space-y-6">
      <PageTitle
        title="Catálogo de Asignaturas"
        subtitle="Gestión de materias, créditos y guías docentes."
      />
      <SubjectsScreen data={data} />
    </div>
  );
}
