import { Breadcrumbs } from '@/components/common/breadcrumbs';
import { Sidebar } from '@/components/common/sidebar';
import { UserMenu } from '@/components/common/user-menu';
import { PageTitle } from '@/components/common/page-title';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh grid grid-cols-[240px_1fr]">
      <Sidebar />

      <div className="grid grid-rows-[56px_1fr]">
        <header className="border-b bg-background/50 px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <PageTitle />
            {/* Breadcrumbs solo saldrán cuando haya profundidad > 1 */}
            <Breadcrumbs className="hidden md:block" />
          </div>
          <UserMenu />
        </header>

        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
