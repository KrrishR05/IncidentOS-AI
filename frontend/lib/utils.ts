"use client";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

export function getMTTR(created: string, resolved?: string | null): string {
  if (!resolved) return "—";
  const diff = new Date(resolved).getTime() - new Date(created).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

export function getSeverityFromTitle(title: string) {
  const t = title.toLowerCase();
  if (t.includes("outage") || t.includes("critical") || t.includes("down")) return "critical";
  if (t.includes("degradation") || t.includes("spike") || t.includes("high")) return "high";
  if (t.includes("alert") || t.includes("warning")) return "medium";
  return "low";
}

export function truncate(str: string, n: number) {
  return str.length > n ? str.slice(0, n) + "…" : str;
}
