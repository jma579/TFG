import { PageTitle } from '@/components/common/page-title';
import { UploadFichasScreen } from '@/components/uploads/upload-fichas-screen';

export default function UploadFichasPage() {
  return (
    <div className="space-y-6">
      <PageTitle
        title="Subir Fichas Académicas"
        subtitle="Procesa y extrae información de las guías docentes en PDF."
      />
      <UploadFichasScreen />
    </div>
  );
}