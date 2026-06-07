"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Brain, Loader2, AlertTriangle, CheckCircle, Sparkles } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { api } from "@/lib/api";
import { NewIncidentResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function RecallPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NewIncidentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRecall = async (q?: string) => {
    const qStr = q ?? query;
    if (!qStr.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await api.createIncident({
        title: qStr,
        description: qStr,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message ?? "Recall failed");
    } finally {
      setLoading(false);
    }
  };

  const confidenceMatch = result?.ai_analysis.match(/(\d+)%/);
  const confidence = confidenceMatch ? parseInt(confidenceMatch[1]) : 0;

  return (
    <MainLayout title="Recall Analyzer" description="Analyze memory recall using IncidentOS backend and Hindsight Cloud.">
      <div className="max-w-4xl mx-auto space-y-5">
        {/* Search bar */}
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="glass-card p-1.5">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleRecall()}
                placeholder="Describe an incident to search historical memory..."
                className="w-full pl-11 pr-4 py-3 bg-transparent text-base text-foreground placeholder:text-muted-foreground focus:outline-none"
              />
            </div>
            <button
              onClick={() => handleRecall()}
              disabled={loading || !query.trim()}
              className="flex items-center gap-2 px-5 py-3 rounded-xl bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 font-medium hover:bg-cyan-500/30 disabled:opacity-50 transition-all whitespace-nowrap"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              Recall
            </button>
          </div>
        </motion.div>

        {/* Results */}
        <AnimatePresence mode="wait">
          {loading && (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="glass-card p-12 flex flex-col items-center justify-center gap-4">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 rounded-full border-2 border-cyan-500/20 animate-ping" />
                <div className="w-16 h-16 rounded-full border-2 border-cyan-500/40 border-t-cyan-400 animate-spin" />
                <Brain className="absolute inset-0 m-auto w-6 h-6 text-cyan-400" />
              </div>
              <div className="text-sm text-muted-foreground animate-pulse">Searching memory bank…</div>
            </motion.div>
          )}

          {error && !loading && (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="glass-card p-6 flex items-center gap-3 border-red-500/15">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-sm text-foreground/80">{error}</p>
            </motion.div>
          )}

          {result && !loading && (
            <motion.div key="result" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              {/* Confidence bar */}
              <div className="glass-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-white">
                    <Brain className="w-4 h-4 text-cyan-400" />AI Recall Confidence
                  </div>
                  <span className="text-2xl font-bold" style={{
                    color: confidence >= 75 ? "#10b981" : confidence >= 50 ? "#f59e0b" : "#6b7280"
                  }}>{confidence}%</span>
                </div>
                <div className="h-2 bg-white/[0.06] rounded-full overflow-hidden">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${confidence}%` }} transition={{ duration: 1, ease: "easeOut" }}
                    className="h-full rounded-full"
                    style={{ background: confidence >= 75 ? "linear-gradient(90deg, #10b981, #06b6d4)" : confidence >= 50 ? "linear-gradient(90deg, #f59e0b, #f97316)" : "#6b7280" }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {confidence >= 75 ? "High confidence — multiple resolved incidents support this analysis" :
                    confidence >= 50 ? "Moderate confidence — some historical data available" :
                      "Low confidence — no similar resolved incidents found"}
                </p>
              </div>

              {/* AI Analysis */}
              <div className="glass-card p-5">
                <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-3">
                  <Sparkles className="w-3.5 h-3.5" />AI Reasoning
                </div>
                <p className="text-sm text-foreground/85 leading-relaxed whitespace-pre-wrap">{result.ai_analysis}</p>
              </div>

              {/* Similar incidents */}
              {result.similar_past_incidents.length > 0 && (
                <div className="glass-card p-5">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">
                    Retrieved Memories ({result.similar_past_incidents.length})
                  </div>
                  <div className="space-y-3">
                    {result.similar_past_incidents.map((inc, i) => (
                      <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}
                        className="bg-surface-3/60 border border-white/[0.05] rounded-xl p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono text-muted-foreground">#{inc.incident_id.slice(0, 8)}</span>
                          <div className="flex items-center gap-1.5">
                            <div className="h-1.5 w-20 bg-white/[0.06] rounded-full overflow-hidden">
                              <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${inc.similarity_score * 100}%` }} />
                            </div>
                            <span className="text-xs text-cyan-400 font-medium">{(inc.similarity_score * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                        <p className="text-sm font-medium text-foreground">{inc.title}</p>
                        {inc.root_cause && (
                          <div className="flex items-start gap-2 text-xs">
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                            <span className="text-emerald-400/80">{inc.root_cause}</span>
                          </div>
                        )}
                        {inc.mitigation_steps && (
                          <p className="text-xs text-muted-foreground pl-5">{inc.mitigation_steps}</p>
                        )}
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {/* Suggested actions */}
              {result.suggested_actions.length > 0 && (
                <div className="glass-card p-5">
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Runbook Steps</div>
                  <ol className="space-y-2">
                    {result.suggested_actions.map((action, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm">
                        <span className="w-6 h-6 rounded-lg bg-cyan-500/15 border border-cyan-500/20 flex items-center justify-center text-xs font-mono text-cyan-400 flex-shrink-0">
                          {i + 1}
                        </span>
                        <span className="text-foreground/80 leading-relaxed">{action}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </motion.div>
          )}

          {!result && !loading && !error && (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="glass-card p-16 flex flex-col items-center justify-center gap-4 text-center">
              <Search className="w-12 h-12 text-muted-foreground/30" />
              <h3 className="text-base font-semibold text-foreground">Ready to Recall</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                Enter an incident description above to search through the memory bank. The AI will retrieve the most relevant past incidents and generate a runbook.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </MainLayout>
  );
}
