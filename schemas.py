from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class NewIncidentRequest(BaseModel):
    title: str = Field(..., description="Short title of the incident")
    description: str = Field(..., description="Detailed description of the incident")


class ResolveIncidentRequest(BaseModel):
    incident_id: str = Field(..., description="ID of the incident to resolve")
    root_cause: str = Field(..., description="Root cause identified during resolution")
    mitigation_steps: str = Field(..., description="Steps taken to resolve the incident")


class SimilarIncident(BaseModel):
    incident_id: str
    title: str
    description: str
    root_cause: Optional[str] = None
    mitigation_steps: Optional[str] = None
    similarity_score: float
    created_at: str


class PostmortemResponse(BaseModel):
    incident_id: str
    markdown: str


class Insight(BaseModel):
    type: str
    title: str
    body: str
    action: str

class InsightsResponse(BaseModel):
    insights: List[Insight]


class NewIncidentResponse(BaseModel):
    incident_id: str
    title: str
    description: str
    status: str
    ai_analysis: str
    similar_past_incidents: List[SimilarIncident]
    suggested_actions: List[str]
    created_at: str


class ResolveIncidentResponse(BaseModel):
    incident_id: str
    status: str
    root_cause: str
    mitigation_steps: str
    memory_stored: bool
    resolved_at: str
