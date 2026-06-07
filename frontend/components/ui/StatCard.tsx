"use client";
import { motion } from "framer-motion";
import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  color?: "cyan" | "purple" | "green" | "red" | "orange" | "default";
  trend?: { value: number; label: string };
  delay?: number;
}

const colorMap = {
  cyan: {
    icon: "text-cyan-400",
    bg: "bg-cyan-500/10",
    border: "border-cyan-500/20",
    value: "text-cyan-300",
    glow: "shadow-neon-blue",
  },
  purple: {
    icon: "text-purple-400",
    bg: "bg-purple-500/10",
    border: "border-purple-500/20",
    value: "text-purple-300",
    glow: "shadow-neon-purple",
  },
  green: {
    icon: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
    value: "text-emerald-300",
    glow: "shadow-neon-green",
  },
  red: {
    icon: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/20",
    value: "text-red-300",
    glow: "shadow-neon-red",
  },
  orange: {
    icon: "text-orange-400",
    bg: "bg-orange-500/10",
    border: "border-orange-500/20",
    value: "text-orange-300",
    glow: "",
  },
  default: {
    icon: "text-muted-foreground",
    bg: "bg-white/[0.04]",
    border: "border-white/[0.06]",
    value: "text-white",
    glow: "",
  },
};

export function StatCard({ title, value, subtitle, icon, color = "default", trend, delay = 0 }: StatCardProps) {
  const c = colorMap[color];
  const trendPositive = (trend?.value ?? 0) >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: "easeOut" }}
      whileHover={{ y: -2, transition: { duration: 0.15 } }}
      className="glass-card p-5 flex flex-col gap-3 hover:border-white/10 transition-all duration-200 group cursor-default"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</span>
        <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-200 group-hover:scale-110", c.bg, c.border, "border")}>
          <span className={cn("w-4 h-4", c.icon)}>{icon}</span>
        </div>
      </div>

      <div>
        <div className={cn("text-3xl font-bold tracking-tight", c.value)}>{value}</div>
        {subtitle && <div className="text-xs text-muted-foreground mt-0.5">{subtitle}</div>}
      </div>

      {trend && (
        <div className={cn("flex items-center gap-1 text-xs font-medium", trendPositive ? "text-emerald-400" : "text-red-400")}>
          <span>{trendPositive ? "↑" : "↓"}</span>
          <span>{Math.abs(trend.value)}% {trend.label}</span>
        </div>
      )}
    </motion.div>
  );
}
