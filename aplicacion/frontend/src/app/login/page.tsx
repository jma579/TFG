'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function LoginPage() {
  const sp = useSearchParams();
  const router = useRouter();
  const view = (sp.get('view') ?? 'signin') as 'signin' | 'accounts';

  const goToApp = () => router.push('/app');

  return (
    <div className="min-h-dvh grid md:grid-cols-2">
      {/* Izquierda: panel principal (varía según view) */}
      <div className="border-r bg-background px-6 py-8 md:px-10 md:py-12 grid place-items-center">
        <div className="w-full max-w-md">
          {view === 'signin' ? (
            <Card>
              <CardHeader>
                <CardTitle>Iniciar sesión</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input type="email" placeholder="nombre@universidad.es" />
                </div>
                <div className="space-y-2">
                  <Label>Contraseña</Label>
                  <Input type="password" placeholder="••••••••" />
                </div>
                {/* Sin lógica real: botón lleva a la app */}
                <Button className="w-full" onClick={goToApp}>
                  Continuar
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Tu cuenta</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Accede con una cuenta existente (simulado).
                </p>
                {/* Listado simulado de cuentas */}
                <div className="space-y-2">
                  <Button variant="outline" className="w-full justify-start" onClick={goToApp}>
                    <span className="mr-2 inline-block h-6 w-6 rounded bg-primary/20" />
                    jose@universidad.es
                  </Button>
                  <Button variant="outline" className="w-full justify-start" onClick={goToApp}>
                    <span className="mr-2 inline-block h-6 w-6 rounded bg-primary/20" />
                    admin@centro.es
                  </Button>
                </div>
                <div className="text-xs text-muted-foreground">
                  También puedes{' '}
                  <button
                    className="underline underline-offset-4"
                    onClick={() => location.assign('/login?view=signin')}
                  >
                    iniciar sesión con email
                  </button>
                  .
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Derecha: panel secundario/ilustración */}
      <div className="hidden md:block bg-[radial-gradient(60%_60%_at_70%_30%,hsl(var(--muted))_0%,transparent_70%)]">
      </div>
    </div>
  );
}
