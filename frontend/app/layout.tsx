import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IncidentOS AI — AI-Powered Incident Response Platform",
  description: "Enterprise-grade AI operations platform for SRE teams powered by semantic memory",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="bg-surface-1 text-foreground antialiased" suppressHydrationWarning>{children}</body>
    </html>
  );
}
