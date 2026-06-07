"use client";
import { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { ParticleBackground } from "@/components/ui/ParticleBackground";

interface MainLayoutProps {
  children: ReactNode;
  title?: string;
  description?: string;
}

export function MainLayout({ children, title, description }: MainLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-1">
      <ParticleBackground />
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <TopNav title={title} description={description} />
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-6 relative z-10">
          {children}
        </main>
      </div>
    </div>
  );
}
