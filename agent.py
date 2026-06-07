"""
Agent module — wraps Groq LLM calls for incident analysis and action suggestion.
All Groq errors are caught and re-raised as clean FastAPI HTTPExceptions so the
server never returns a raw 500 crash to the caller.
"""

import json
import logging
import os
from typing import List, Optional

from fastapi import HTTPException
from groq import Groq, GroqError
from dotenv import load_dotenv

from prompts import (
    INCIDENT_ANALYSIS_PROMPT,
    INCIDENT_ANALYSIS_WITH_MEMORY_PROMPT,
    SUGGESTED_ACTIONS_PROMPT,
    POSTMORTEM_PROMPT,
    INSIGHTS_PROMPT,
)

load_dotenv()

logger = logging.getLogger(__name__)

_client: Optional[Groq] = None

MODEL = "llama-3.3-70b-versatile"


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GROQ_API_KEY is not set. Please add it to your .env file.",
            )
        _client = Groq(api_key=api_key)
    return _client


def _call_groq(prompt: str, temperature: float = 0.3, max_tokens: int = 300) -> str:
    """Single Groq call with clean error handling. Returns the raw content string."""
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except HTTPException:
        raise  # already clean — let it propagate
    except GroqError as e:
        logger.error("Groq API error: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"Groq API error: {e}",
        )
    except Exception as e:
        logger.error("Unexpected error calling Groq: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error calling AI model: {e}",
        )


def analyze_incident(
    title: str,
    description: str,
    similar_incidents: Optional[List[dict]] = None,
) -> str:
    """Run LLM analysis on the incident, optionally enriched with past memory."""
    if similar_incidents:
        # Split into resolved vs unresolved (resolved are already sorted first)
        resolved = [i for i in similar_incidents if i.get("root_cause")]
        unresolved = [i for i in similar_incidents if not i.get("root_cause")]
        resolved_count = len(resolved)

        # Confidence scale per spec
        if resolved_count == 0:
            confidence_pct = 20
        elif resolved_count == 1:
            confidence_pct = 60
        else:
            confidence_pct = min(85 + (resolved_count - 2) * 5, 97)

        # Primary root cause + mitigation from the top resolved incident
        primary = resolved[0] if resolved else None
        primary_root_cause = primary["root_cause"] if primary else "unknown (no resolved incidents)"
        primary_mitigation = primary["mitigation_steps"] if primary else "none recorded"

        # Build past context block — resolved first, clearly labelled
        past_context_lines = []
        for inc in resolved:
            past_context_lines.append(
                f"[RESOLVED] Title: {inc['title']}\n"
                f"  Root cause: {inc['root_cause']}\n"
                f"  Mitigation: {inc['mitigation_steps']}"
            )
        for inc in unresolved:
            past_context_lines.append(
                f"[OPEN] Title: {inc['title']}\n"
                f"  Root cause: not yet determined"
            )
        past_context = "\n\n".join(past_context_lines)

        prompt = INCIDENT_ANALYSIS_WITH_MEMORY_PROMPT.format(
            title=title,
            description=description,
            past_incidents_context=past_context,
            resolved_count=resolved_count,
            primary_root_cause=primary_root_cause,
            primary_mitigation=primary_mitigation,
            confidence_pct=confidence_pct,
        )
    else:
        prompt = INCIDENT_ANALYSIS_PROMPT.format(title=title, description=description)

    return _call_groq(prompt, temperature=0.2, max_tokens=400)


def suggest_actions(
    title: str,
    description: str,
    analysis: str,
    similar_incidents: Optional[List[dict]] = None,
) -> List[str]:
    """Return a list of 4 suggested immediate actions for the on-call engineer."""
    past_context = "None"
    if similar_incidents:
        parts = []
        for inc in similar_incidents:
            mit = inc.get("mitigation_steps") or "N/A"
            parts.append(f"{inc['title']}: {mit}")
        past_context = "; ".join(parts)

    prompt = SUGGESTED_ACTIONS_PROMPT.format(
        title=title,
        description=description,
        analysis=analysis,
        past_context=past_context,
    )

    raw = _call_groq(prompt, temperature=0.2, max_tokens=300)

    # Extract JSON array from the response
    try:
        start = raw.index("[")
        end = raw.rindex("]") + 1
        actions = json.loads(raw[start:end])
        if isinstance(actions, list):
            return [str(a) for a in actions[:4]]
    except (ValueError, json.JSONDecodeError):
        logger.warning("Could not parse Groq actions JSON, falling back to line split.")

    # Fallback: split by newline
    lines = [line.strip("•- ").strip() for line in raw.split("\n") if line.strip()]
    return lines[:4]


def generate_postmortem(
    title: str,
    description: str,
    root_cause: str,
    mitigation: str,
) -> str:
    """Generate a Markdown postmortem report for a resolved incident."""
    prompt = POSTMORTEM_PROMPT.format(
        title=title,
        description=description,
        root_cause=root_cause,
        mitigation=mitigation,
    )
    # Using higher max_tokens for a full report and slightly higher temperature for creativity
    return _call_groq(prompt, temperature=0.4, max_tokens=1000)


def generate_insights(resolved_incidents: List[dict]) -> List[dict]:
    """Generate 4 systemic insights based on a batch of resolved incidents."""
    # We limit to the top 30 to avoid context length limits and high latency
    batch = resolved_incidents[:30]
    
    parts = []
    for inc in batch:
        parts.append(f"Title: {inc['title']}\nRoot Cause: {inc['root_cause']}\nMitigation: {inc['mitigation_steps']}")
        
    incidents_batch = "\n---\n".join(parts)
    
    prompt = INSIGHTS_PROMPT.format(incidents_batch=incidents_batch)
    raw = _call_groq(prompt, temperature=0.3, max_tokens=800)
    
    # Parse JSON array
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        data = json.loads(raw[start:end])
        if isinstance(data, list):
            return data[:4]
    except (ValueError, json.JSONDecodeError):
        logger.warning("Could not parse Groq insights JSON.")
        
    return []

