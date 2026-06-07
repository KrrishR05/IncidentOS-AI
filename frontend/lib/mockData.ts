import { Incident, MemoryGraph, MemoryNode, MemoryLink } from "./types";
import { addDays, subDays, format } from "date-fns";

// ── Mock Incidents ────────────────────────────────────────────────────────────
const severities = ["critical", "high", "medium", "low"] as const;
const services = ["api-gateway", "database", "auth-service", "payment-svc", "cache", "worker", "cdn", "messaging"];
const rootCauses = [
  "connection pool exhaustion",
  "memory leak in worker process",
  "SSL certificate expired",
  "misconfigured rate limit",
  "disk I/O saturation",
  "DNS resolution failure",
  "deployment regression",
  "OOM killed pod",
];

function randItem<T>(arr: readonly T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}
function randInt(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export const mockIncidents: Incident[] = Array.from({ length: 48 }, (_, i) => {
  const resolved = i < 30;
  const rc = resolved ? randItem(rootCauses) : null;
  const svc = randItem(services);
  const sev = randItem(severities);
  const daysAgo = randInt(0, 30);
  const created = subDays(new Date(), daysAgo + randInt(0, 5));
  return {
    incident_id: Math.random().toString(16).slice(2, 10),
    title: `${svc} ${sev === "critical" ? "outage" : sev === "high" ? "degradation" : "alert"} — ${format(created, "MMM dd")}`,
    description: `${svc} is showing elevated error rates and latency spikes affecting downstream services.`,
    status: resolved ? "resolved" : "open",
    severity: sev,
    root_cause: rc,
    mitigation_steps: rc ? `Identified and fixed root cause: ${rc}. Applied mitigation and monitored recovery.` : null,
    created_at: created.toISOString(),
    resolved_at: resolved ? subDays(created, -randInt(0, 3)).toISOString() : null,
    confidence: resolved ? randInt(60, 95) : randInt(15, 40),
    similar_incidents_count: randInt(0, 5),
  };
});

// ── Trend data (last 14 days) ─────────────────────────────────────────────────
export const mockTrendData = Array.from({ length: 14 }, (_, i) => {
  const date = subDays(new Date(), 13 - i);
  return {
    date: format(date, "MMM dd"),
    open: randInt(2, 12),
    resolved: randInt(3, 15),
    critical: randInt(0, 3),
  };
});

// ── Severity distribution ─────────────────────────────────────────────────────
export const mockSeverityData = [
  { name: "Critical", value: 8, color: "#ef4444" },
  { name: "High", value: 14, color: "#f59e0b" },
  { name: "Medium", value: 18, color: "#3b82f6" },
  { name: "Low", value: 8, color: "#6b7280" },
];

// ── Memory growth data ────────────────────────────────────────────────────────
export const mockMemoryGrowth = Array.from({ length: 30 }, (_, i) => ({
  day: i + 1,
  memories: Math.floor(50 + i * 45 + Math.random() * 20),
}));

// ── MTTR data ─────────────────────────────────────────────────────────────────
export const mockMTTRData = Array.from({ length: 7 }, (_, i) => ({
  day: format(subDays(new Date(), 6 - i), "EEE"),
  mttr: randInt(8, 45),
}));

// ── AI Confidence trend ───────────────────────────────────────────────────────
export const mockConfidenceTrend = Array.from({ length: 14 }, (_, i) => ({
  date: format(subDays(new Date(), 13 - i), "MMM dd"),
  confidence: randInt(55, 92),
}));

// ── Activity feed ─────────────────────────────────────────────────────────────
export const mockActivity = [
  { id: 1, type: "resolved", title: "Database connection exhaustion resolved", time: "2 min ago", icon: "check" },
  { id: 2, type: "created", title: "New incident: API latency spike detected", time: "8 min ago", icon: "alert" },
  { id: 3, type: "ai", title: "AI recalled 3 similar past incidents", time: "15 min ago", icon: "brain" },
  { id: 4, type: "synced", title: "Hindsight Cloud sync: +12 records", time: "1h ago", icon: "refresh" },
  { id: 5, type: "resolved", title: "SSL certificate renewal completed", time: "2h ago", icon: "check" },
  { id: 6, type: "created", title: "Worker OOM incident opened", time: "3h ago", icon: "alert" },
  { id: 7, type: "ai", title: "AI confidence improved to 91%", time: "4h ago", icon: "brain" },
];

// ── Memory Graph ──────────────────────────────────────────────────────────────
export function generateMemoryGraph(incidents: Incident[]): MemoryGraph {
  const nodes: MemoryNode[] = [];
  const links: MemoryLink[] = [];
  const seenRoots = new Map<string, string>();
  const seenServices = new Map<string, string>();

  incidents.slice(0, 60).forEach((inc) => {
    const incNode: MemoryNode = {
      id: inc.incident_id,
      label: inc.title.slice(0, 30),
      type: "incident",
      size: inc.severity === "critical" ? 12 : inc.severity === "high" ? 9 : 7,
      color: inc.status === "resolved" ? "#10b981" : "#ef4444",
      data: inc,
    };
    nodes.push(incNode);

    // Root cause nodes
    if (inc.root_cause) {
      let rcId = seenRoots.get(inc.root_cause);
      if (!rcId) {
        rcId = `rc-${Math.random().toString(16).slice(2, 8)}`;
        seenRoots.set(inc.root_cause, rcId);
        nodes.push({
          id: rcId,
          label: inc.root_cause,
          type: "root_cause",
          size: 8,
          color: "#f59e0b",
        });
      }
      links.push({ source: inc.incident_id, target: rcId, type: "causal", strength: 0.8 });
    }

    // Service nodes (extract from title)
    const svcMatch = services.find((s) => inc.title.toLowerCase().includes(s));
    if (svcMatch) {
      let svcId = seenServices.get(svcMatch);
      if (!svcId) {
        svcId = `svc-${svcMatch}`;
        seenServices.set(svcMatch, svcId);
        nodes.push({
          id: svcId,
          label: svcMatch,
          type: "service",
          size: 10,
          color: "#a855f7",
        });
      }
      links.push({ source: inc.incident_id, target: svcId, type: "entity", strength: 0.5 });
    }
  });

  // Add some temporal links between nearby incidents
  for (let i = 0; i < Math.min(incidents.length - 1, 40); i++) {
    if (Math.random() > 0.7) {
      links.push({
        source: incidents[i].incident_id,
        target: incidents[i + 1].incident_id,
        type: "temporal",
        strength: 0.2,
      });
    }
  }

  return { nodes, links };
}
