"use client";

import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle, Search, Filter, Plus, CheckCircle,
  Clock, Brain, ChevronDown, X, Loader2, RefreshCw
} from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { IncidentModal } from "@/components/incidents/IncidentModal";

import { api } from "@/lib/api";
import { Incident, NewIncidentResponse } from "@/lib/types";
import { formatRelativeTime, cn, truncate, getSeverityFromTitle } from "@/lib/utils";

const SEVERITIES = ["all", "critical", "high", "medium", "low"];
const STATUSES = ["all", "open", "resolved"];

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("all");
  const [status, setStatus] = useState("all");
  const [showNew, setShowNew] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [aiResult, setAiResult] = useState<NewIncidentResponse | null>(null);
  const [loadingReal, setLoadingReal] = useState(false);

  useEffect(() => {
    setLoadingReal(true);
    api.getAllIncidents()
      .then(d => {
        const mapped = d.incidents.map(r => ({ ...r, severity: getSeverityFromTitle(r.title) }));
        setIncidents(mapped);
      })
      .catch(() => null)
      .finally(() => setLoadingReal(false));
  }, []);

  const filtered = useMemo(() => {
    return incidents.filter(inc => {
      const matchSearch = !search || inc.title.toLowerCase().includes(search.toLowerCase()) ||
        inc.incident_id.includes(search) || (inc.root_cause ?? "").toLowerCase().includes(search.toLowerCase());
      const matchSev = severity === "all" || inc.severity === severity;
      const matchStatus = status === "all" || inc.status === status;
      return matchSearch && matchSev && matchStatus;
    });
  }, [incidents, search, severity, status]);

  const handleSubmitNew = async () => {
    if (!newTitle.trim() || !newDesc.trim()) return;
    setSubmitting(true);
    try {
      const res = await api.createIncident({ title: newTitle, description: newDesc });
      setAiResult(res);
      const newInc: Incident = {
        incident_id: res.incident_id,
        title: res.title,
        description: res.description,
        status: "open",
        severity: getSeverityFromTitle(res.title),
        created_at: res.created_at,
        confidence: parseInt(res.ai_analysis.match(/(\d+)%/)?.[1] ?? "20"),
      };
      setIncidents(prev => [newInc, ...prev]);
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  const refresh = () => {
    setLoadingReal(true);
    api.getAllIncidents()
      .then(d => setIncidents(d.incidents.map(r => ({ ...r, severity: getSeverityFromTitle(r.title) }))))
      .catch(() => null)
      .finally(() => setLoadingReal(false));
  };

  const severityBadge = (s?: string) => {
    const classes: Record<string, string> = {
      critical: "badge-critical", high: "badge-high", medium: "badge-medium", low: "badge-low",
    };
    return classes[s ?? "low"] ?? "badge-low";
  };

  return (
    <MainLayout title="Incidents" description="Manage and analyze incidents with AI memory">
      <div className="space-y-4">
        {/* Toolbar */}
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-[240px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search incidents, IDs, root causes..."
              className="w-full pl-9 pr-4 py-2 text-sm bg-surface-2 border border-white/[0.07] rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-cyan-500/40 transition-all"
            />
          </div>

          {/* Severity filter */}
          <div className="flex items-center gap-1 bg-surface-2 border border-white/[0.07] rounded-lg p-1">
            {SEVERITIES.map(s => (
              <button key={s} onClick={() => setSeverity(s)}
                className={cn("px-3 py-1 rounded text-xs font-medium capitalize transition-all",
                  severity === s ? "bg-white/10 text-foreground" : "text-muted-foreground hover:text-foreground"
                )}>
                {s}
              </button>
            ))}
          </div>

          {/* Status filter */}
          <div className="flex items-center gap-1 bg-surface-2 border border-white/[0.07] rounded-lg p-1">
            {STATUSES.map(s => (
              <button key={s} onClick={() => setStatus(s)}
                className={cn("px-3 py-1 rounded text-xs font-medium capitalize transition-all",
                  status === s ? "bg-white/10 text-foreground" : "text-muted-foreground hover:text-foreground"
                )}>
                {s}
              </button>
            ))}
          </div>

          <button onClick={refresh} className="p-2 rounded-lg border border-white/[0.07] text-muted-foreground hover:text-foreground hover:bg-white/[0.04] transition-all">
            <RefreshCw className={cn("w-4 h-4", loadingReal && "animate-spin")} />
          </button>

          <button onClick={() => setShowNew(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500/15 border border-cyan-500/25 text-cyan-400 text-sm font-medium hover:bg-cyan-500/25 transition-all">
            <Plus className="w-4 h-4" />New Incident
          </button>
        </motion.div>

        {/* New Incident Form */}
        <AnimatePresence>
          {showNew && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
              <div className="glass-card p-5 border-cyan-500/15">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-white">Report New Incident</h3>
                  <button onClick={() => { setShowNew(false); setAiResult(null); }} className="text-muted-foreground hover:text-foreground">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                {!aiResult ? (
                  <div className="space-y-3">
                    <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Incident title..."
                      className="w-full px-3 py-2 text-sm bg-surface-3 border border-white/[0.07] rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-cyan-500/40" />
                    <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={3} placeholder="Describe what's happening..."
                      className="w-full px-3 py-2 text-sm bg-surface-3 border border-white/[0.07] rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-cyan-500/40 resize-none" />
                    <div className="flex justify-end gap-2">
                      <button onClick={() => setShowNew(false)} className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground border border-white/[0.07] transition-colors">Cancel</button>
                      <button onClick={handleSubmitNew} disabled={submitting || !newTitle || !newDesc}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 text-sm font-medium hover:bg-cyan-500/30 disabled:opacity-50 transition-all">
                        {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                        {submitting ? "Analyzing…" : "Submit & Analyze"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
                    <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold">
                      <CheckCircle className="w-4 h-4" />Incident created: #{aiResult.incident_id}
                    </div>
                    <div className="bg-cyan-500/5 border border-cyan-500/15 rounded-xl p-4">
                      <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold mb-2 uppercase tracking-wider">
                        <Brain className="w-3.5 h-3.5" />AI Analysis
                      </div>
                      <p className="text-sm text-foreground/80 whitespace-pre-wrap leading-relaxed">{aiResult.ai_analysis}</p>
                    </div>
                    {aiResult.suggested_actions.length > 0 && (
                      <div>
                        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Suggested Actions</div>
                        <ol className="space-y-1">
                          {aiResult.suggested_actions.map((a, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-foreground/80">
                              <span className="w-5 h-5 rounded flex-shrink-0 bg-white/[0.06] flex items-center justify-center text-xs font-mono text-cyan-400">{i + 1}</span>
                              {a}
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}
                    <button onClick={() => { setShowNew(false); setAiResult(null); setNewTitle(""); setNewDesc(""); }}
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors">Close ↗</button>
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Stats bar */}
        <div className="flex items-center gap-6 text-xs text-muted-foreground px-1">
          <span>Showing <span className="text-foreground font-medium">{filtered.length}</span> of {incidents.length}</span>
          <span>Resolved: <span className="text-emerald-400 font-medium">{incidents.filter(i => i.status === "resolved").length}</span></span>
          <span>Open: <span className="text-red-400 font-medium">{incidents.filter(i => i.status === "open").length}</span></span>
          <span>Critical: <span className="text-orange-400 font-medium">{incidents.filter(i => i.severity === "critical").length}</span></span>
        </div>

        {/* Incident Table */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  {["ID", "Title", "Status", "Severity", "Root Cause", "Confidence", "Created", "MTTR"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <AnimatePresence>
                  {filtered.map((inc, i) => (
                    <motion.tr
                      key={inc.incident_id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.02 }}
                      onClick={() => setSelected(inc)}
                      className="border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors cursor-pointer group"
                    >
                      <td className="px-4 py-3 text-xs font-mono text-muted-foreground group-hover:text-cyan-500 transition-colors">
                        #{inc.incident_id.slice(0, 6)}
                      </td>
                      <td className="px-4 py-3 text-sm text-foreground max-w-[220px]">
                        <div className="truncate">{inc.title}</div>
                        {inc.description && <div className="text-xs text-muted-foreground truncate mt-0.5">{truncate(inc.description, 60)}</div>}
                      </td>
                      <td className="px-4 py-3">
                        <span className={inc.status === "resolved" ? "badge-resolved" : "badge-open"}>
                          {inc.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={severityBadge(inc.severity)}>{inc.severity ?? "—"}</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground max-w-[160px]">
                        <div className="truncate">{inc.root_cause ?? "—"}</div>
                      </td>
                      <td className="px-4 py-3">
                        {inc.confidence ? (
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${inc.confidence}%`,
                                  background: inc.confidence >= 75 ? "#10b981" : inc.confidence >= 50 ? "#f59e0b" : "#6b7280"
                                }}
                              />
                            </div>
                            <span className="text-xs text-muted-foreground">{inc.confidence}%</span>
                          </div>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                        {formatRelativeTime(inc.created_at)}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                        {inc.resolved_at
                          ? `${Math.round((new Date(inc.resolved_at).getTime() - new Date(inc.created_at).getTime()) / 60000)}m`
                          : "—"}
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>

      <IncidentModal incident={selected} onClose={() => setSelected(null)} onResolved={refresh} />
    </MainLayout>
  );
}
