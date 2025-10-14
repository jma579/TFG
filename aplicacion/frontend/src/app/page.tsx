import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function Page() {
  return (
    <main className="min-h-dvh p-8 flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Bienvenido</h1>
      <Button asChild><Link href="/uploads/fichas">Ir a la app</Link></Button>
    </main>
  );
}
