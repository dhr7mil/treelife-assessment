"""
Schema Discovery — uses an LLM to build a semantic map of how THIS specific
client actually uses their CRM, identifying quirks, non-standard field usage,
owner fields, status encoding, and hidden conventions.
"""

import json
import requests
from typing import Any


DISCOVERY_PROMPT = """You are a CRM analyst. You are given the schema (field definitions) and 
a sample of real records from a client's CRM. Your job is to figure out how this specific 
client actually uses their CRM — which may be very different from the textbook setup.

Pay close attention to:
1. Which field actually contains the owner/assignee of deals or contacts? 
   (It might not be the standard "owner" field — look for custom fields with names like 
   "Assigned To", "Lead Owner", "Rep", "Account Manager", etc.)
2. How does this client represent "lost" or "inactive" deals?
   (They might use a stage called "Dead Leads", "Closed Lost", "Graveyard", or similar 
   instead of setting the status to "lost")
3. How does this client represent "open" or "active" deals?
   (What stages or statuses mean "still in play"?)
4. Are there any naming conventions, typos, or inconsistencies in how names are entered?
5. Where is priority stored? (tags, a field, folder name, etc.)
6. Any other quirks that would trip up a naive system?

Schema:
{schema}

Sample records (first 15):
{sample}

Respond ONLY with a valid JSON object (no markdown, no explanation outside the JSON):
{{
  "summary": "One sentence describing what this CRM contains and how many records",
  "owner_fields": ["list", "of", "field", "names", "that", "contain", "owner/assignee"],
  "owner_field_primary": "the single best field name for owner",
  "owner_is_standard": true/false,
  "owner_notes": "e.g. names are hand-typed with inconsistent casing",
  "active_deal_definition": {{
    "description": "plain English description of what 'open/active' means for this client",
    "exclude_stages": ["stages", "that", "mean", "lost/inactive"],
    "include_stages": ["stages", "that", "mean", "active"],
    "status_values": ["active status values like 'open'"]
  }},
  "lost_deal_definition": {{
    "description": "plain English description of what 'lost' means for this client",
    "stages": ["stages", "that", "mean", "lost"],
    "status_values": ["lost status values if any"]
  }},
  "status_fields": [
    {{"field": "field_name", "meaning": "what values in this field mean"}}
  ],
  "priority_field": "field name for priority, or null if not found",
  "priority_values": {{"high": "value", "low": "value"}},
  "contact_owner_field": "field name for contact/lead owner",
  "quirks": ["list of non-standard things about this client's setup"],
  "object_types": ["deals", "contacts"]
}}"""


class SchemaDiscovery:
    def __init__(self, groq_api_key: str = None):
        self.groq_api_key = groq_api_key

    def build_semantic_map(self, schema: dict, sample_data: dict, platform: str) -> dict:
        """
        Given raw schema + sample records, build a semantic map of how this
        client actually uses their CRM.
        """
        # Truncate sample for prompt efficiency
        sample_truncated = {}
        for obj, records in sample_data.items():
            sample_truncated[obj] = records[:15]

        schema_str = json.dumps(schema, indent=2)[:6000]
        sample_str = json.dumps(sample_truncated, indent=2)[:6000]

        prompt = DISCOVERY_PROMPT.format(schema=schema_str, sample=sample_str)

        if self.groq_api_key:
            raw = self._call_groq(prompt)
        else:
            # Fallback: use mock data's built-in quirks
            raw = self._mock_semantic_map(schema)

        try:
            # Strip any markdown fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            semantic_map = json.loads(cleaned.strip())
        except Exception:
            # If parsing fails, return a basic map
            semantic_map = self._fallback_map(schema)

        semantic_map["platform"] = platform
        semantic_map["raw_schema"] = schema
        return semantic_map

    def _call_groq(self, prompt: str) -> str:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-oss-120b",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1500,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _mock_semantic_map(self, schema: dict) -> str:
        """Return a pre-built semantic map for the mock connector."""
        return json.dumps({
            "summary": "Sales CRM with 25 deals and 10 contacts across Sales and Enterprise pipelines",
            "owner_fields": ["assigned_to"],
            "owner_field_primary": "assigned_to",
            "owner_is_standard": False,
            "owner_notes": "Names are hand-typed with inconsistent casing (Garima, garima, GARIMA, Garima S.)",
            "active_deal_definition": {
                "description": "Active deals are in Discovery, Proposal, or Negotiation stages. Dead Leads stage = lost.",
                "exclude_stages": ["Dead Leads", "Closed Won"],
                "include_stages": ["Discovery", "Proposal", "Negotiation"],
                "status_values": ["active"],
            },
            "lost_deal_definition": {
                "description": "Lost deals are in the 'Dead Leads' stage — the status field still shows 'active'",
                "stages": ["Dead Leads"],
                "status_values": [],
            },
            "status_fields": [
                {"field": "stage", "meaning": "Discovery/Proposal/Negotiation = active; Dead Leads = lost; Closed Won = won"},
                {"field": "status", "meaning": "Mostly unreliable — most lost deals still show 'active'"},
            ],
            "priority_field": "tags",
            "priority_values": {"high": "high-priority", "low": None},
            "contact_owner_field": "lead_owner",
            "quirks": [
                "official_owner field is blank — team uses 'assigned_to' custom field instead",
                "'Dead Leads' stage = lost deals (status field NOT updated)",
                "Owner names have typos and inconsistent casing",
                "Priority tracked via 'high-priority' tag, not a dedicated field",
            ],
            "object_types": ["deals", "contacts"],
        })

    def _fallback_map(self, schema: dict) -> dict:
        """Basic fallback if LLM parsing fails."""
        return {
            "summary": "Schema loaded successfully",
            "owner_fields": ["owner", "assigned_to", "lead_owner"],
            "owner_field_primary": "owner",
            "owner_is_standard": True,
            "owner_notes": "",
            "active_deal_definition": {
                "description": "Deals with status 'open' or 'active'",
                "exclude_stages": [],
                "include_stages": [],
                "status_values": ["open", "active"],
            },
            "lost_deal_definition": {
                "description": "Deals marked as lost",
                "stages": ["lost", "closed lost"],
                "status_values": ["lost"],
            },
            "status_fields": [],
            "priority_field": None,
            "priority_values": {},
            "contact_owner_field": "lead_owner",
            "quirks": [],
            "object_types": ["deals", "contacts"],
        }
