"use client";

import { motion } from "framer-motion";
import { ArrowRight, Brain, Zap, ShieldCheck, Database, Search, Activity, GitPullRequest, TerminalSquare, LayoutDashboard } from "lucide-react";
import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black flex flex-col items-center relative overflow-x-hidden selection:bg-cyan-500/30 selection:text-cyan-50 font-sans">
      
      {/* Very subtle ambient glow */}
      <div className="absolute top-0 inset-x-0 flex justify-center pointer-events-none z-0">
        <div className="w-[800px] h-[400px] bg-gradient-to-b from-cyan-500/10 to-transparent blur-[120px] rounded-full" />
      </div>

      {/* Subtle Grid pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none z-0" />

      {/* Hero Section */}
      <main className="relative z-10 max-w-6xl mx-auto px-6 w-full flex flex-col items-center text-center pt-32 pb-20">
        
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/[0.03] text-muted-foreground text-xs font-medium tracking-wide mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          IncidentOS Engine v2.0 is Live
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-5xl md:text-8xl font-bold text-white tracking-tight leading-[1.05] mb-6"
        >
          Resolve Incidents <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-200 to-blue-500">
            At AI Speed.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-10 leading-relaxed font-light"
        >
          An enterprise-grade SRE platform powered by Hindsight Cloud Memory. 
          Instantly predict root causes, generate dynamic runbooks, and automate post-mortems based on your organization's actual history.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center gap-4"
        >
          <Link href="/dashboard">
            <button className="group flex items-center justify-center gap-2 px-8 py-3.5 bg-white text-black text-sm font-semibold rounded-lg hover:bg-gray-100 transition-colors shadow-lg shadow-white/5">
              <LayoutDashboard className="w-4 h-4" />
              <span>Launch Platform</span>
            </button>
          </Link>
          <Link href="/docs">
            <button className="group flex items-center justify-center gap-2 px-8 py-3.5 bg-transparent border border-white/10 text-white text-sm font-semibold rounded-lg hover:bg-white/[0.03] transition-colors">
              <span>Read the Docs</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </button>
          </Link>
        </motion.div>

        {/* MacBook Laptop Mock UI Preview */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="w-full max-w-5xl mx-auto mt-20 relative z-20 perspective-[2000px]"
        >
          {/* Screen / Lid */}
          <div className="relative mx-auto w-full md:w-[90%] rounded-t-3xl border-4 border-[#1a1a1a] bg-black p-2 md:p-3 shadow-2xl transition-transform hover:-translate-y-2 duration-500">
            {/* Webcam dot */}
            <div className="absolute top-1 md:top-2 left-1/2 -translate-x-1/2 w-1.5 h-1.5 md:w-2 md:h-2 bg-[#111] rounded-full z-20" />
            
            {/* Screen Content */}
            <div className="relative overflow-hidden rounded-t-2xl rounded-b-sm bg-surface-1 aspect-[16/10] border border-white/10">
               {/* Real Image Mockup */}
               <img 
                 src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=1200&auto=format&fit=crop" 
                 alt="IncidentOS Dashboard Preview" 
                 className="absolute inset-0 w-full h-full object-cover object-left-top opacity-80"
               />
               
               {/* Dark Overlay to make it blend well with the futuristic theme */}
               <div className="absolute inset-0 bg-gradient-to-tr from-cyan-900/30 to-purple-900/30 mix-blend-overlay" />
            </div>
          </div>

          {/* Base / Keyboard part */}
          <div className="relative mx-auto w-[105%] md:w-full h-4 md:h-6 rounded-b-2xl rounded-t-sm bg-gradient-to-b from-[#3a3a3a] via-[#1a1a1a] to-black shadow-[0_20px_40px_-10px_rgba(0,0,0,0.8)] flex justify-center">
            {/* Trackpad notch */}
            <div className="absolute top-0 h-1 md:h-2 w-16 md:w-24 rounded-b-lg bg-[#111]" />
          </div>
        </motion.div>

      </main>

      {/* Stats Section */}
      <section className="w-full border-y border-white/[0.05] bg-white/[0.01] py-16 mt-10 relative z-10">
        <div className="max-w-6xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-center divide-x divide-white/[0.05]">
          <div>
            <div className="text-4xl font-bold text-white mb-2">99.9%</div>
            <div className="text-sm text-muted-foreground">Historical Precision</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-white mb-2">10x</div>
            <div className="text-sm text-muted-foreground">Faster Resolution</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-white mb-2">24/7</div>
            <div className="text-sm text-muted-foreground">Automated Analysis</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-white mb-2">1,000+</div>
            <div className="text-sm text-muted-foreground">Incidents Memorized</div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="max-w-6xl mx-auto px-6 py-32 relative z-10 w-full">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Engineered for Reliability</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">Everything an SRE team needs to triage, mitigate, and learn from production outages.</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FeatureCard 
            icon={<Brain className="w-5 h-5 text-cyan-400" />}
            title="Semantic Memory Base"
            description="Llama 3.3 searches your historical database to map live symptoms to past outages in milliseconds."
          />
          <FeatureCard 
            icon={<TerminalSquare className="w-5 h-5 text-blue-400" />}
            title="Auto-Generated Runbooks"
            description="The AI dynamically generates priority-ordered mitigation commands that actually worked before."
          />
          <FeatureCard 
            icon={<ShieldCheck className="w-5 h-5 text-emerald-400" />}
            title="Systemic AI Reflection"
            description="Proactively analyzes batches of resolved incidents to find macro-vulnerabilities in your architecture."
          />
          <FeatureCard 
            icon={<Search className="w-5 h-5 text-purple-400" />}
            title="Recall Analyzer"
            description="Manually query your incident database using natural language to find exactly what you're looking for."
          />
          <FeatureCard 
            icon={<GitPullRequest className="w-5 h-5 text-orange-400" />}
            title="Automated Post-Mortems"
            description="Generate beautifully formatted markdown post-mortems with timeline and 5-Whys analysis instantly."
          />
          <FeatureCard 
            icon={<Database className="w-5 h-5 text-pink-400" />}
            title="Hindsight Cloud Sync"
            description="Your incident memory is synced continuously, ensuring the AI is always learning from the latest events."
          />
        </div>
      </section>

      {/* Footer CTA */}
      <section className="w-full bg-gradient-to-t from-cyan-900/10 to-transparent py-32 border-t border-white/[0.05] relative z-10">
        <div className="max-w-4xl mx-auto text-center px-6">
          <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 tracking-tight">Stop searching Confluence at 3 AM.</h2>
          <p className="text-lg text-muted-foreground mb-10">Let the AI remember how to fix your systems.</p>
          <Link href="/dashboard">
            <button className="px-8 py-4 bg-white text-black text-sm font-semibold rounded-lg hover:bg-gray-100 transition-colors shadow-[0_0_30px_rgba(255,255,255,0.1)]">
              Open Dashboard
            </button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full py-8 border-t border-white/[0.05] bg-black text-center relative z-10">
        <p className="text-xs text-muted-foreground">© 2026 IncidentOS AI. Built for the SRE Hackathon.</p>
      </footer>

    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="p-8 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.04] transition-colors flex flex-col">
      <div className="w-10 h-10 rounded-lg bg-white/[0.05] border border-white/[0.05] flex items-center justify-center mb-6">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-white mb-3">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed flex-1">{description}</p>
    </div>
  );
}
