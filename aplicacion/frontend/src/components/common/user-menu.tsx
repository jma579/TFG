'use client';

import { useRouter } from 'next/navigation';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

const USER = {
  name: 'Usuario Demo',
  email: 'demo@universidad.es',
  image: '', // puedes poner una URL si quieres
};

export function UserMenu() {
  const router = useRouter();

  const onSignOut = () => {
    // sin auth real: te enviamos a seleccionar cuenta
    router.push('/login?view=accounts');
  };

  const initials = USER.name
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="outline-none">
        <Avatar className="h-8 w-8 ring-1 ring-border">
          {USER.image ? <AvatarImage src={USER.image} alt={USER.name} /> : null}
          <AvatarFallback className="text-xs">{initials || 'U'}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col">
            <span className="font-medium">{USER.name}</span>
            <span className="text-xs text-muted-foreground">{USER.email}</span>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onSignOut}>Cerrar sesión</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
