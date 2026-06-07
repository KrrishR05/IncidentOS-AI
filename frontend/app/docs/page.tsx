"use client";

import { useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { BookOpen, Terminal, Code, Cpu, Database, ChevronRight, Search, Activity, Link as LinkIcon, Network, Brain } from "lucide-react";

export default function DocsPage() {
  const [activeDoc, setActiveDoc] = useState("Introduction");

  const sections = {
    "Getting Started": ["Introduction", "Installation", "Quickstart"],
    "Core Concepts": ["Semantic Memory", "AI Triage", "Hindsight Cloud"],
    "API Reference": ["REST Endpoints", "Webhooks"]
  };

  const renderContent = () => {
    switch (activeDoc) {
      case "Introduction":
        return (
          <>
            <div className="flex items-center gap-3 mb-6 text-cyan-400">
              <BookOpen className="w-8 h-8" />
              <h1 className="text-3xl font-bold text-white m-0">Introduction to IncidentOS AI</h1>
            </div>
            
            <p className="text-lg text-muted-foreground leading-relaxed">
              IncidentOS AI is the next-generation platform for Site Reliability Engineers. It connects directly to your incident database and uses powerful Large Language Models (LLMs) to automate triage, resolution, and post-mortems.
            </p>

            <hr className="border-white/10 my-8" />

            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-purple-400" />
              How the Engine Works
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-6">
              Traditional incident management relies on manual keyword searches through outdated Confluence runbooks. IncidentOS changes the paradigm by utilizing <strong>Semantic Search</strong> and <strong>RAG (Retrieval-Augmented Generation)</strong>.
            </p>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
              <div className="bg-white/5 border border-white/10 p-5 rounded-xl">
                <h3 className="font-semibold text-white mb-2 flex items-center gap-2"><Database className="w-4 h-4 text-cyan-400" /> 1. Vectorization</h3>
                <p className="text-sm text-muted-foreground">Every resolved incident in your Hindsight Cloud is transformed into mathematical vectors.</p>
              </div>
              <div className="bg-white/5 border border-white/10 p-5 rounded-xl">
                <h3 className="font-semibold text-white mb-2 flex items-center gap-2"><Search className="w-4 h-4 text-emerald-400" /> 2. Live Matching</h3>
                <p className="text-sm text-muted-foreground">When an alert fires, the AI compares the live symptoms against the vector database in milliseconds.</p>
              </div>
            </div>
          </>
        );

      case "Installation":
        return (
          <>
            <div className="flex items-center gap-3 mb-6 text-blue-400">
              <Terminal className="w-8 h-8" />
              <h1 className="text-3xl font-bold text-white m-0">Installation</h1>
            </div>
            <p className="text-muted-foreground mb-6">You can spin up the backend API locally using Docker or standard Python tooling:</p>
            
            <div className="bg-black border border-white/10 rounded-xl p-6 mb-8 font-mono text-sm overflow-x-auto">
              <span className="text-cyan-400">$</span> git clone https://github.com/incidentos/core.git<br/>
              <span className="text-cyan-400">$</span> cd core<br/>
              <span className="text-cyan-400">$</span> python -m venv venv<br/>
              <span className="text-cyan-400">$</span> source venv/bin/activate<br/>
              <span className="text-cyan-400">$</span> pip install -r requirements.txt<br/>
              <span className="text-cyan-400">$</span> uvicorn main:app --reload
            </div>

            <h2 className="text-xl font-bold text-white mb-4">Connecting to Hindsight Cloud</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Create a <code>.env</code> file in the root directory and add your API keys:
            </p>
            <div className="bg-black border border-white/10 rounded-xl p-6 mb-8 font-mono text-sm">
              GROQ_API_KEY=gsk_your_groq_api_key<br/>
              HINDSIGHT_API_KEY=hsk_your_hindsight_key
            </div>
          </>
        );

      case "Quickstart":
        return (
          <>
            <div className="flex items-center gap-3 mb-6 text-emerald-400">
              <Activity className="w-8 h-8" />
              <h1 className="text-3xl font-bold text-white m-0">Quickstart</h1>
            </div>
            <p className="text-muted-foreground mb-6">Once the server is running, you can create your first incident via the UI or API:</p>
            
            <div className="bg-black border border-white/10 rounded-xl p-6 mb-8 font-mono text-sm">
              <span className="text-green-400">POST</span> /incident/new<br/>
              <span className="text-purple-400">Content-Type:</span> application/json<br/><br/>
              {'{'}<br/>
              &nbsp;&nbsp;"title": "Database connections spiking to 100%",<br/>
              &nbsp;&nbsp;"description": "API latency has increased to 5 seconds due to Postgres connection pool exhaustion."<br/>
              {'}'}
            </div>
            <p className="text-muted-foreground mb-6">The system will automatically run AI Triage and return suggested actions based on your memory bank.</p>
          </>
        );

      case "Semantic Memory":
        return (
          <>
            <div className="flex items-center gap-3 mb-6 text-purple-400">
              <Brain className="w-8 h-8" />
              <h1 className="text-3xl font-bold text-white m-0">Semantic Memory</h1>
            </div>
            <p className="text-muted-foreground mb-6 leading-relaxed">
              Unlike keyword search (e.g. searching "database" in Jira), Semantic Memory understands the <i>meaning</i> behind words. 
              If you have an open incident titled <strong>"Postgres timeout"</strong>, the system knows it is related to a past incident titled <strong>"DB connection pool exhausted"</strong>.
            </p>
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-6 flex gap-4 text-sm text-purple-200">
              <div className="mt-0.5 flex-shrink-0"><Network className="w-5 h-5 text-purple-400"/></div>
              <div>
                <strong>Under the hood:</strong> IncidentOS uses the <code>all-MiniLM-L6-v2</code> transformer model to generate dense embeddings for every incident title and description, performing high-speed cosine similarity searches via FAISS or exact math.
              </div>
            </div>
          </>
        );

      default:
        return (
          <>
            <div className="flex items-center gap-3 mb-6 text-white/50">
              <Code className="w-8 h-8" />
              <h1 className="text-3xl font-bold text-white m-0">{activeDoc}</h1>
            </div>
            <p className="text-muted-foreground">This section is currently under construction. Check back soon for updates!</p>
          </>
        );
    }
  };

  return (
    <MainLayout title="Documentation" description="Learn how to configure and use IncidentOS AI">
      <div className="flex flex-col md:flex-row gap-8 max-w-6xl mx-auto">
        
        {/* Docs Sidebar */}
        <div className="w-full md:w-64 flex-shrink-0 space-y-8">
          {Object.entries(sections).map(([category, items]) => (
            <div key={category}>
              <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">{category}</h4>
              <ul className="space-y-1">
                {items.map(item => (
                  <li key={item}>
                    <button 
                      onClick={() => setActiveDoc(item)}
                      className={`w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors text-left ${activeDoc === item ? "bg-cyan-500/10 text-cyan-400 font-medium" : "text-muted-foreground hover:text-white hover:bg-white/5"}`}
                    >
                      {activeDoc === item && <ChevronRight className="w-3.5 h-3.5" />}
                      {item}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Docs Content Area */}
        <div className="flex-1 min-w-0 glass-card p-8 md:p-12 prose prose-invert prose-cyan max-w-none">
          {renderContent()}
        </div>

      </div>
    </MainLayout>
  );
}
