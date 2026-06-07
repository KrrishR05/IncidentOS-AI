"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import {
  X, CheckCircle, AlertTriangle, Clock, Brain, ChevronRight,
  Copy, Check, Loader2, FileText
} from "lucide-react";
import { Incident, SimilarIncident } from "@/lib/types";
import { formatRelativeTime, getMTTR, cn } from "@/lib/utils";
import { api } from "@/lib/api";

interface IncidentModalProps {
  incident: Incident | null;
  onClose: () => void;
  onResolved?: () => void;
}

export function IncidentModal({ incident, onClose, onResolved }: IncidentModalProps) {
  const [resolveMode, setResolveMode] = useState(false);
  const [rootCause, setRootCause] = useState("");
  const [mitigation, setMitigation] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [postmortem, setPostmortem] = useState<string | null>(null);
  const [generatingPm, setGeneratingPm] = useState(false);

  if (!incident) return null;

  const handleGeneratePm = async () => {
    setGeneratingPm(true);
    setPostmortem(null);
    try {
      const res = await api.generatePostmortem(incident.incident_id);
      setPostmortem(res.markdown);
    } catch (e) {
      console.error(e);
      setPostmortem("Failed to generate post-mortem. Check server logs.");
    } finally {
      setGeneratingPm(false);
    }
  };

  const handleResolve = async () => {
    if (!rootCause.trim() || !mitigation.trim()) return;
    setLoading(true);
    try {
      await api.resolveIncident({
        incident_id: incident.incident_id,
        root_cause: rootCause,
        mitigation_steps: mitigation,
      });
      onResolved?.();
      onClose();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const copy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const severityColor: Record<string, string> = {
    critical: "text-red-400 bg-red-500/10 border-red-500/20",
    high: "text-orange-400 bg-orange-500/10 border-orange-500/20",
    medium: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
    low: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        {/* Backdrop */}
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          onClick={(e) => e.stopPropagation()}
          className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto glass-card border-white/10"
        >
          {/* Header */}
          <div className="sticky top-0 flex items-start justify-between p-6 border-b border-white/[0.06] bg-surface-2/90 backdrop-blur-xl">
            <div className="flex-1 min-w-0 pr-4">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-xs font-mono text-muted-foreground">#{incident.incident_id}</span>
                <span className={cn("px-2 py-0.5 rounded-full text-xs font-semibold border", incident.severity ? severityColor[incident.severity] : "text-gray-400 bg-gray-500/10 border-gray-500/20")}>
                  {incident.severity || "unknown"}
                </span>
                <span className={cn("px-2 py-0.5 rounded-full text-xs font-semibold border", incident.status === "resolved" ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : "text-red-400 bg-red-500/10 border-red-500/20")}>
                  {incident.status}
                </span>
              </div>
              <h2 className="text-lg font-semibold text-white leading-snug">{incident.title}</h2>
            </div>
            <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors flex-shrink-0">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6 space-y-5">
            {/* Description */}
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 block">Description</label>
              <p className="text-sm text-foreground/80 leading-relaxed">{incident.description}</p>
            </div>

            {/* Meta */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white/[0.03] rounded-xl p-3 border border-white/[0.05]">
                <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1.5"><Clock className="w-3 h-3" />Created</div>
                <div className="text-sm font-medium text-foreground">{formatRelativeTime(incident.created_at)}</div>
              </div>
              <div className="bg-white/[0.03] rounded-xl p-3 border border-white/[0.05]">
                <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1.5"><CheckCircle className="w-3 h-3" />MTTR</div>
                <div className="text-sm font-medium text-foreground">{getMTTR(incident.created_at, incident.resolved_at)}</div>
              </div>
            </div>

            {/* Root cause (if resolved) */}
            {incident.root_cause && (
              <div className="bg-emerald-500/5 border border-emerald-500/15 rounded-xl p-4 space-y-3">
                <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider">
                  <CheckCircle className="w-3.5 h-3.5" />Root Cause Identified
                </div>
                <p className="text-sm text-foreground/80">{incident.root_cause}</p>
                {incident.mitigation_steps && (
                  <>
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mt-2">Mitigation Applied</div>
                    <p className="text-sm text-foreground/80">{incident.mitigation_steps}</p>
                  </>
                )}
              </div>
            )}

            {/* AI Confidence */}
            {incident.confidence && (
              <div className="bg-cyan-500/5 border border-cyan-500/15 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider">
                    <Brain className="w-3.5 h-3.5" />AI Confidence
                  </div>
                  <span className="text-sm font-bold text-cyan-400">{incident.confidence}%</span>
                </div>
                <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${incident.confidence}%` }}
                    transition={{ duration: 0.8, ease: "easeOut", delay: 0.2 }}
                    className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-500"
                  />
                </div>
              </div>
            )}

            {/* Resolve form */}
            {incident.status === "open" && (
              <div>
                {!resolveMode ? (
                  <button
                    onClick={() => setResolveMode(true)}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-sm font-medium hover:bg-emerald-500/20 transition-all"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Mark as Resolved
                  </button>
                ) : (
                  <div className="space-y-3 bg-surface-3/60 rounded-xl p-4 border border-white/[0.05]">
                    <div className="text-sm font-semibold text-foreground">Resolve Incident</div>
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">Root Cause *</label>
                      <textarea
                        value={rootCause}
                        onChange={e => setRootCause(e.target.value)}
                        rows={2}
                        placeholder="What caused this incident?"
                        className="w-full bg-surface-4 border border-white/[0.07] rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-cyan-500/40 resize-none"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">Mitigation Steps *</label>
                      <textarea
                        value={mitigation}
                        onChange={e => setMitigation(e.target.value)}
                        rows={2}
                        placeholder="What steps fixed it?"
                        className="w-full bg-surface-4 border border-white/[0.07] rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-cyan-500/40 resize-none"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => setResolveMode(false)} className="flex-1 py-2 rounded-lg border border-white/10 text-sm text-muted-foreground hover:text-foreground transition-colors">
                        Cancel
                      </button>
                      <button
                        onClick={handleResolve}
                        disabled={loading || !rootCause.trim() || !mitigation.trim()}
                        className="flex-1 py-2 rounded-lg bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-sm font-medium hover:bg-emerald-500/30 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                      >
                        {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                        {loading ? "Resolving…" : "Confirm Resolve"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Post-Mortem Section (if resolved) */}
            {incident.status === "resolved" && (
              <div className="pt-2 border-t border-white/[0.05]">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <FileText className="w-4 h-4 text-purple-400" />
                    Automated Post-Mortem
                  </h3>
                  {!postmortem && (
                    <button
                      onClick={handleGeneratePm}
                      disabled={generatingPm}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-purple-500/30 bg-purple-500/10 text-purple-400 text-xs font-medium hover:bg-purple-500/20 transition-all disabled:opacity-50"
                    >
                      {generatingPm && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      {generatingPm ? "Generating…" : "Generate"}
                    </button>
                  )}
                </div>
                {postmortem && (
                  <div className="bg-surface-3/50 border border-white/[0.05] rounded-xl p-4 mt-2 max-h-[300px] overflow-y-auto custom-scrollbar prose prose-invert prose-sm max-w-none">
                    <div className="whitespace-pre-wrap font-sans text-sm text-foreground/90">{postmortem}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
