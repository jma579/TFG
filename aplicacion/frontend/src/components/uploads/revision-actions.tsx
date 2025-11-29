'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { useHorariosUploadsStore } from '@/stores/horarios-uploads';
import Link from 'next/link';

export function RevisionActions({ id }: { id: string }) {
  const router = useRouter();
  const confirm = useHorariosUploadsStore((s) => s.confirm);

  const onConfirm = () => {
    confirm(id);                // marca como confirmado en la store
    router.push('/uploads/horarios'); // vuelve al listado de subidas de horarios
  };

  return (
    <div className="flex gap-2">
      <Button asChild variant="outline">
        <Link href="/uploads/horarios">Cancelar</Link>
      </Button>
      <Button onClick={onConfirm}>Confirmar horario</Button>
    </div>
  );
}
