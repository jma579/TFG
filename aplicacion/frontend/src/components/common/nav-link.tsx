'use client';

import { cn } from '@/lib/cn';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

type Props = React.ComponentProps<typeof Link> & { exact?: boolean };

export function NavLink({ href, exact = false, className, ...props }: Props) {
  const pathname = usePathname();
  const isActive = exact ? pathname === href : pathname?.startsWith(String(href));


  return (
    <Link
      href={href}
      className={cn(
        'block rounded-lg px-3 py-2 text-sm transition',
        isActive
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground',
        className
      )}
      {...props}
    />
  );
}
