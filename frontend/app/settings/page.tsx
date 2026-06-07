"use client";

import { useState } from "react";
import { Key, RefreshCw, Loader2, Trash2 } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [deduping, setDeduping] = useState(false);
  const [dedupResult, setDedupResult] = useState<string | null>(null);

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await api.syncFromHindsight();
      setSyncResult(`✅ Sync complete — fetched ${res.fetched}, added ${res.added}, updated ${res.updated}, total ${res.total}`);
    } catch (e: any) {
      setSyncResult(`❌ Sync failed: ${e.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleDedup = async () => {
    setDeduping(true);
    setDedupResult(null);
    try {
      const res = await api.deduplicate();
      setDedupResult(`✅ Dedup complete — ${res.before} → ${res.after} records, removed ${res.removed}`);
    } catch (e: any) {
      setDedupResult(`❌ Dedup failed: ${e.message}`);
    } finally {
      setDeduping(false);
    }
  };

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="glass-card overflow-hidden">
      <div className="px-5 py-4 border-b border-white/[0.05]">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      <div className="p-5 space-y-4">{children}</div>
    </div>
  );

  const Field = ({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) => (
    <div className="flex items-start justify-between gap-6">
      <div className="flex-1">
        <div className="text-sm font-medium text-foreground">{label}</div>
        {description && <div className="text-xs text-muted-foreground mt-0.5">{description}</div>}
      </div>
      <div className="flex-shrink-0 w-64">{children}</div>
    </div>
  );

  return (
    <MainLayout title="Settings" description="Configure IncidentOS AI and Hindsight Cloud connection">
      <div className="max-w-2xl space-y-4">


        <Section title="Memory Operations">
          <Field label="Sync from Hindsight Cloud" description="Pull all records from cloud bank into local memory with embeddings">
            <div className="space-y-2">
              <button onClick={handleSync} disabled={syncing}
                className="flex items-center gap-2 w-full justify-center px-4 py-2 rounded-lg bg-cyan-500/15 border border-cyan-500/25 text-cyan-400 text-sm font-medium hover:bg-cyan-500/25 disabled:opacity-50 transition-all">
                {syncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                {syncing ? "Syncing…" : "Sync Now"}
              </button>
              {syncResult && <p className="text-xs text-muted-foreground">{syncResult}</p>}
            </div>
          </Field>
          <div className="border-t border-white/[0.05] pt-4" />
          <Field label="Deduplicate Local Memory" description="Remove duplicate incidents (same ID or semantically identical titles)">
            <div className="space-y-2">
              <button onClick={handleDedup} disabled={deduping}
                className="flex items-center gap-2 w-full justify-center px-4 py-2 rounded-lg bg-orange-500/10 border border-orange-500/20 text-orange-400 text-sm font-medium hover:bg-orange-500/15 disabled:opacity-50 transition-all">
                {deduping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                {deduping ? "Deduplicating…" : "Deduplicate"}
              </button>
              {dedupResult && <p className="text-xs text-muted-foreground">{dedupResult}</p>}
            </div>
          </Field>
        </Section>
      </div>
    </MainLayout>
  );
}
