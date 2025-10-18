'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/cn';

type Props = React.ComponentProps<typeof Link> & {
  exact?: boolean;
  variant?: 'default' | 'sidebar';
};

export function NavLink({ href, exact = false, variant = 'default', className, ...props }: Props) {
  const pathname = usePathname();
  const isActive = exact ? pathname === href : pathname?.startsWith(String(href));

  const base =
    variant === 'sidebar'
      ? 'block rounded-md px-3 py-2 text-sm font-medium transition'
      : 'block rounded-lg px-3 py-2 text-sm transition';

  const active =
    variant === 'sidebar'
      ? 'bg-slate-800 text-white'
      : 'bg-primary/10 text-primary';

  const inactive =
    variant === 'sidebar'
      ? 'text-slate-300 hover:bg-slate-800 hover:text-white'
      : 'text-muted-foreground hover:bg-muted hover:text-foreground';

  return (
    <Link
      href={href}
      className={cn(base, isActive ? active : inactive, className)}
      {...props}
    />
  );
}
