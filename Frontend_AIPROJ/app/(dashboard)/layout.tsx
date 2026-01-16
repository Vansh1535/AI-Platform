"use client"

import { Sidebar } from "@/components/sidebar";
import { Navbar } from "@/components/navbar";
import { useSidebarStore } from "@/lib/store/sidebarStore";
import { cn } from "@/lib/utils";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { collapsed } = useSidebarStore();

  return (
    <div className="flex h-screen overflow-hidden bg-base-bg">
      <Sidebar />
      <div className={cn(
        "flex-1 flex flex-col transition-all duration-300",
        collapsed ? "lg:ml-16" : "lg:ml-64"
      )}>
        <Navbar />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
