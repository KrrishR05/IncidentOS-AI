"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Lightbulb, Target, AlertTriangle, ArrowRight, Loader2, Sparkles } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { api } from "@/lib/api";
import { Insight } from "@/lib/types";

export default function ReflectionPage() {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getInsights()
      .then(res => {
        setInsights(res.insights);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <MainLayout title="Systemic Reflection" description="AI-driven strategic insights across your recent incident history">
      <div className="max-w-4xl space-y-6">
        
        {/* Header Block */}
        <div className="glass-card p-6 flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-500/30 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white mb-1">AI Operational Insights</h2>
            <p className="text-sm text-foreground/80 leading-relaxed">
              The AI has scanned the last 30 resolved incidents across the Hindsight memory bank to identify recurring patterns, systemic vulnerabilities, and strategic action items to improve overall reliability.
            </p>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="glass-card p-12 flex flex-col items-center justify-center gap-4">
            <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
            <div className="text-sm text-muted-foreground animate-pulse">Running systemic reflection algorithm…</div>
          </div>
        )}

        {/* Empty State */}
        {!loading && insights.length === 0 && (
          <div className="glass-card p-12 flex flex-col items-center justify-center text-center">
            <Lightbulb className="w-12 h-12 text-muted-foreground/30 mb-4" />
            <h3 className="text-base font-medium text-white mb-2">No Insights Available</h3>
            <p className="text-sm text-muted-foreground max-w-sm">We need more resolved incidents in the database before the AI can find systemic patterns.</p>
          </div>
        )}

        {/* Insights List */}
        <AnimatePresence>
          {!loading && insights.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {insights.map((insight, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.15, duration: 0.5 }}
                  className="glass-card p-5 relative overflow-hidden group"
                >
                  <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none transition-opacity group-hover:opacity-10">
                    <Target className="w-24 h-24 text-white" />
                  </div>
                  
                  <div className="flex items-center gap-2 mb-3">
                    <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-purple-500/10 text-purple-400 border border-purple-500/20">
                      {insight.type}
                    </span>
                  </div>
                  
                  <h3 className="text-base font-semibold text-white mb-2">{insight.title}</h3>
                  <p className="text-sm text-foreground/80 leading-relaxed mb-4">{insight.body}</p>
                  
                  <div className="pt-4 border-t border-white/[0.06] mt-auto">
                    <div className="flex items-start gap-2">
                      <ArrowRight className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block mb-1">Strategic Action</span>
                        <p className="text-sm font-medium text-cyan-50">{insight.action}</p>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </AnimatePresence>
      </div>
    </MainLayout>
  );
}
