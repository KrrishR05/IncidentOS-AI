import {
  AllIncidentsResponse,
  NewIncidentRequest,
  NewIncidentResponse,
  ResolveIncidentRequest,
  ResolveIncidentResponse,
  SystemStatus,
  SyncResponse,
  PostmortemResponse,
  InsightsResponse,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  getStatus: () => request<SystemStatus>("/status"),

  getAllIncidents: () => request<AllIncidentsResponse>("/incidents/all"),

  getIncident: (id: string) => request<AllIncidentsResponse>(`/incident/${id}`),

  createIncident: (data: NewIncidentRequest) =>
    request<NewIncidentResponse>("/incident/new", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  resolveIncident: (data: ResolveIncidentRequest) =>
    request<ResolveIncidentResponse>("/incident/resolve", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  syncFromHindsight: () =>
    request<SyncResponse>("/sync", { method: "POST" }),

  deduplicate: () =>
    request<{ ok: boolean; before: number; after: number; removed: number }>(
      "/deduplicate",
      { method: "POST" }
    ),

  generatePostmortem: (id: string) =>
    request<PostmortemResponse>(`/incident/${id}/postmortem`, { method: "POST" }),

  getInsights: () => request<InsightsResponse>("/incidents/insights"),
};
