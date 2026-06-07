// Shared TypeScript types for IncidentOS AI Frontend

export type Severity = "critical" | "high" | "medium" | "low";
export type IncidentStatus = "open" | "resolved";

export interface Incident {
  incident_id: string;
  title: string;
  description: string;
  status: IncidentStatus;
  severity?: Severity;
  root_cause?: string | null;
  mitigation_steps?: string | null;
  created_at: string;
  resolved_at?: string | null;
  similarity_score?: number;
  confidence?: number;
  similar_incidents_count?: number;
}

export interface SimilarIncident {
  incident_id: string;
  title: string;
  description: string;
  root_cause?: string | null;
  mitigation_steps?: string | null;
  similarity_score: number;
  created_at: string;
}

export interface NewIncidentRequest {
  title: string;
  description: string;
}

export interface NewIncidentResponse {
  incident_id: string;
  title: string;
  description: string;
  status: string;
  ai_analysis: string;
  similar_past_incidents: SimilarIncident[];
  suggested_actions: string[];
  created_at: string;
}

export interface ResolveIncidentRequest {
  incident_id: string;
  root_cause: string;
  mitigation_steps: string;
}

export interface ResolveIncidentResponse {
  incident_id: string;
  status: string;
  root_cause: string;
  mitigation_steps: string;
  memory_stored: boolean;
  resolved_at: string;
}

export interface AllIncidentsResponse {
  total: number;
  resolved: number;
  open: number;
  incidents: Incident[];
}

export interface SystemStatus {
  status: string;
  version: string;
  hindsight: boolean;
}

export interface SyncResponse {
  ok: boolean;
  fetched: number;
  added: number;
  updated: number;
  total: number;
}

export interface MemoryNode {
  id: string;
  label: string;
  type: "incident" | "entity" | "root_cause" | "service" | "mitigation";
  size?: number;
  color?: string;
  data?: Incident;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface MemoryLink {
  source: string;
  target: string;
  type: "semantic" | "temporal" | "entity" | "causal";
  strength?: number;
}

export interface MemoryGraph {
  nodes: MemoryNode[];
  links: MemoryLink[];
}

export interface RecallResult {
  incident_id: string;
  title: string;
  description: string;
  root_cause?: string | null;
  mitigation_steps?: string | null;
  similarity_score: number;
  confidence: number;
  ai_reasoning?: string;
}

export interface PostmortemResponse {
  incident_id: string;
  markdown: string;
}

export interface Insight {
  type: string;
  title: string;
  body: string;
  action: string;
}

export interface InsightsResponse {
  insights: Insight[];
}
