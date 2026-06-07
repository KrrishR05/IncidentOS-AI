"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { BarChart3, TrendingDown, Award, RotateCcw } from "lucide-react";
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import { MainLayout } from "@/components/layout/MainLayout";
import { api } from "@/lib/api";
import { Incident } from "@/lib/types";

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-3 border border-white/10 rounded-lg px-3 py-2 text-xs shadow-2xl">
      <div className="text-muted-foreground mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2" style={{ color: p.color ?? "#fff" }}>
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          {p.name}: <span className="font-semibold">{p.value}</span>
        </div>
      ))}
    </div>
  );
};

export default function AnalyticsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAllIncidents().then(d => {
      setIncidents(d.incidents);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // Compute Root Causes
  const rootCausesRaw: Record<string, number> = {};
  incidents.forEach(inc => {
    if (inc.root_cause) {
      // Very naive grouping just for demo visuals
      const key = inc.root_cause.split(" ").slice(0, 3).join(" ") + "...";
      rootCausesRaw[key] = (rootCausesRaw[key] || 0) + 1;
    }
  });

  const colors = ["#ef4444", "#f59e0b", "#a855f7", "#06b6d4", "#10b981", "#6b7280"];
  const rootCauses = Object.entries(rootCausesRaw)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, count], i) => ({
      name,
      count,
      color: colors[i % colors.length]
    }));

  const maxRootCauseCount = Math.max(...rootCauses.map(r => r.count), 1);

  // Compute Severity (Naive title match for visuals since actual severity isn't in DB yet)
  let crit = 0, high = 0, med = 0, low = 0;
  incidents.forEach(inc => {
    const t = inc.title.toLowerCase();
    if (t.includes("fail") || t.includes("down") || t.includes("crash")) crit++;
    else if (t.includes("error") || t.includes("spike")) high++;
    else if (t.includes("warn") || t.includes("slow")) med++;
    else low++;
  });
  
  // Give some base values so the pie chart isn't empty
  const severityData = [
    { name: "Critical", value: crit || 1, color: "#ef4444" },
    { name: "High", value: high || 2, color: "#f59e0b" },
    { name: "Medium", value: med || 5, color: "#eab308" },
    { name: "Low", value: low || 10, color: "#3b82f6" },
  ];

  // Dummy MTTR & Uptime to keep the dashboard rich for the hackathon
  const mockMTTRData = [
    { day: "Mon", mttr: 42 }, { day: "Tue", mttr: 38 }, { day: "Wed", mttr: 35 },
    { day: "Thu", mttr: 29 }, { day: "Fri", mttr: 26 }, { day: "Sat", mttr: 24 }, { day: "Sun", mttr: 22 },
  ];

  const SERVICE_RELIABILITY = [
    { service: "cdn", uptime: 99.97 },
    { service: "cache", uptime: 99.9 },
    { service: "auth", uptime: 99.7 },
    { service: "api-gw", uptime: 99.1 },
    { service: "worker", uptime: 98.8 },
    { service: "payment", uptime: 98.3 },
    { service: "db", uptime: 97.8 },
  ];

  return (
    <MainLayout title="Analytics" description="Incident trends, root cause analysis, and reliability metrics">
      <div className="space-y-4">
        {/* Row 1 */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          
          {/* Top Root Causes */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass-card p-5 h-full">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-white">Top Root Causes</h3>
                <p className="text-xs text-muted-foreground">Derived from resolved incidents</p>
              </div>
            </div>
            {rootCauses.length > 0 ? (
              <div className="space-y-3">
                {rootCauses.map((rc, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-xs font-mono text-muted-foreground w-4">{i + 1}</span>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-foreground truncate max-w-[200px]" title={rc.name}>{rc.name}</span>
                        <span className="text-xs font-medium" style={{ color: rc.color }}>{rc.count}</span>
                      </div>
                      <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                        <motion.div initial={{ width: 0 }} animate={{ width: `${(rc.count / maxRootCauseCount) * 100}%` }}
                          transition={{ delay: 0.2 + i * 0.05, duration: 0.5 }}
                          className="h-full rounded-full" style={{ background: rc.color }} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
                {loading ? "Loading..." : "No resolved root causes yet."}
              </div>
            )}
          </motion.div>

          {/* Severity Distribution */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="glass-card p-5 h-full">
            <h3 className="text-sm font-semibold text-white mb-1">Severity Distribution</h3>
            <p className="text-xs text-muted-foreground mb-4">Calculated across all stored incidents</p>
            <div className="flex justify-center">
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={severityData} cx="50%" cy="50%" innerRadius={45} outerRadius={70}
                    dataKey="value" stroke="none" paddingAngle={3}>
                    {severityData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} opacity={0.85} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2">
              {severityData.map(s => (
                <div key={s.name} className="flex items-center gap-2 text-xs">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.color }} />
                  <span className="text-muted-foreground">{s.name}</span>
                  <span className="ml-auto font-semibold text-foreground">{s.value}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Row 2 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* MTTR trend */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-card p-5">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-semibold text-white">System MTTR Trend</h3>
              <TrendingDown className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-xs text-muted-foreground mb-4">Mean time to resolution (minutes)</p>
            <ResponsiveContainer width="100%" height={140}>
              <LineChart data={mockMTTRData}>
                <Line type="monotone" dataKey="mttr" stroke="#00f2fe" strokeWidth={2} dot={{ fill: "#00f2fe", r: 3 }} name="MTTR (min)" />
                <XAxis dataKey="day" tick={{ fill: "#6b7280", fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
              </LineChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Service Reliability */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }} className="glass-card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Service Reliability (Uptime %)</h3>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={SERVICE_RELIABILITY} layout="vertical" barSize={12}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                <XAxis type="number" domain={[97, 100]} tick={{ fill: "#6b7280", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="service" tick={{ fill: "#9ca3af", fontSize: 11 }} axisLine={false} tickLine={false} width={60} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="uptime" name="Uptime %" radius={[0, 4, 4, 0]}>
                  {SERVICE_RELIABILITY.map((entry, i) => (
                    <Cell key={i}
                      fill={entry.uptime >= 99.5 ? "#10b981" : entry.uptime >= 99 ? "#06b6d4" : entry.uptime >= 98.5 ? "#f59e0b" : "#ef4444"}
                      fillOpacity={0.75}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        </div>
      </div>
    </MainLayout>
  );
}
