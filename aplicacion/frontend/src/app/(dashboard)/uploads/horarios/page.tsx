import { PageTitle } from '@/components/common/page-title';
import { UploadHorariosScreen } from '@/components/uploads/upload-horarios-screen';

export default function UploadHorariosPage() {
  return (
    <div className="space-y-6">
      <PageTitle
        title="Subir Horarios"
        subtitle="Analiza los documentos de horarios para extraer sesiones."
      />
      <UploadHorariosScreen />
    </div>
  );
}

