import type { ReactNode } from "react";

import { Sidebar } from "@/components/common/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="fixed inset-0 flex overflow-hidden bg-muted/30">
      <Sidebar />
      <main className="flex-1 overflow-x-hidden overflow-y-auto">
        <div className="mx-auto flex max-w-6xl flex-col gap-8 px-8 py-10">
          {children}
        </div>
      </main>
    </div>
  );
}