import type { ReactNode } from "react";
import { Sidebar } from "@/components/common/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-slate-100 text-slate-900">
      <Sidebar />
      <main className="flex-1 overflow-x-hidden overflow-y-auto">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-8 py-8">
          {children}
        </div>
      </main>
    </div>
  );
}