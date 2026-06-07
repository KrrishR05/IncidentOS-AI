"""
Auto-resolve script to bulk-enrich Hindsight database with resolved incident data.
It reads local memory, finds open incidents, generates fake (but realistic) root causes
and mitigations using Groq, and resolves them via memory.py (which pushes to Hindsight).
"""

import os
import json
import time
from dotenv import load_dotenv

import memory
import agent

load_dotenv()

PROMPT_TEMPLATE = """
You are an expert Site Reliability Engineer (SRE).
I am going to give you the title and description of a hypothetical production incident.
Please generate a realistic, plausible Root Cause (1 sentence) and Mitigation Steps (1-2 sentences).

Incident Title: {title}
Description: {description}

Return ONLY a valid JSON object in this format (no markdown, no extra text):
{{
    "root_cause": "The exact technical root cause...",
    "mitigation_steps": "The exact steps taken to fix it..."
}}
"""

def auto_resolve():
    print("--- IncidentOS AI Bulk Resolver ---")
    
    # 1. Get all local incidents
    all_incidents = memory.get_all_incidents()
    open_incidents = [inc for inc in all_incidents if not inc.get("root_cause")]
    
    print(f"Total incidents in memory: {len(all_incidents)}")
    print(f"Open incidents to resolve: {len(open_incidents)}")
    
    if not open_incidents:
        print("Nothing to resolve!")
        return

    # To avoid rate limits, let's limit how many we resolve in one run, or let the user interrupt.
    limit = min(50, len(open_incidents))  # Resolve 50 per run to be safe with Groq free tier
    print(f"\nProcessing {limit} incidents to prevent API rate limits...\n")

    success_count = 0

    for i, inc in enumerate(open_incidents[:limit]):
        print(f"[{i+1}/{limit}] Resolving: {inc['title']}")
        
        try:
            # Generate the prompt
            prompt = PROMPT_TEMPLATE.format(
                title=inc["title"],
                description=inc.get("description", "No description provided")
            )
            
            # Call Groq directly via the agent's internal method
            raw_response = agent._call_groq(prompt, temperature=0.7, max_tokens=150)
            
            # Extract JSON
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            if start == -1 or end == 0:
                print("  -> Failed to parse LLM response.")
                continue
                
            data = json.loads(raw_response[start:end])
            rc = data.get("root_cause")
            mit = data.get("mitigation_steps")
            
            if not rc or not mit:
                print("  -> Missing data in JSON.")
                continue
                
            # Resolve the incident locally & push to Hindsight
            success = memory.resolve_incident(inc["incident_id"], rc, mit)
            
            if success:
                print(f"  -> ✅ Resolved! Root Cause: {rc[:50]}...")
                success_count += 1
            else:
                print("  -> ❌ Failed to save resolution to memory.")
                
            # Small delay to respect rate limits
            time.sleep(1)
            
        except Exception as e:
            print(f"  -> ⚠️ Error: {e}")
            time.sleep(2) # Backoff
            
    print(f"\n--- Done! Successfully resolved {success_count} incidents. ---")
    print("Run this script again to resolve the next batch.")

if __name__ == "__main__":
    auto_resolve()
