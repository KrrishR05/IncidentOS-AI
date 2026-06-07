"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Bell,
  ChevronDown,
  User,
  Key,
  Plug,
  Building2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { SystemStatus } from "@/lib/types";

interface TopNavProps {
  title?: string;
  description?: string;
}

export function TopNav({ title, description }: TopNavProps) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    api.getStatus().then(setStatus).catch(() => null);
    const interval = setInterval(() => {
      api.getStatus().then(setStatus).catch(() => null);
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 flex items-center justify-between px-6 border-b border-white/[0.06] bg-surface-1/80 backdrop-blur-xl flex-shrink-0 z-10">

      <div className="flex items-center gap-4 flex-1">
        {title && (
          <div>
            <h1 className="text-base font-semibold text-white">{title}</h1>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </div>
        )}
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Backend status indicator */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium transition-all"
          style={{
            borderColor: status?.status === "online" ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)",
            color: status?.status === "online" ? "#10b981" : "#ef4444",
            background: status?.status === "online" ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
          }}
        >
          {status?.status === "online" ? (
            <CheckCircle className="w-3 h-3" />
          ) : (
            <XCircle className="w-3 h-3" />
          )}
          {status ? (status.status === "online" ? "Connected" : "Offline") : "Checking…"}
        </div>

        {/* Hindsight status */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs"
          style={{
            borderColor: status?.hindsight ? "rgba(0,242,254,0.2)" : "rgba(107,114,128,0.2)",
            color: status?.hindsight ? "#00f2fe" : "#6b7280",
            background: status?.hindsight ? "rgba(0,242,254,0.06)" : "transparent",
          }}
        >
          <Plug className="w-3 h-3" />
          Hindsight
        </div>



        <button className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center text-white text-xs font-bold">
          IO
        </button>
      </div>
    </header>
  );
}
