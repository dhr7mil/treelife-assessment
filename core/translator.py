"""
Query Translator — takes a plain English question, uses the semantic map
to understand how THIS client's CRM works, generates the correct query,
executes it, and returns a trustworthy answer with reasoning.
"""

import json
import requests
import pandas as pd
from typing import Any


TRANSLATION_PROMPT = """You are an expert at querying business CRMs. You understand how businesses 
actually use their tools, which is often very different from how the tools were designed to be used.

You have been given a semantic map that describes exactly how THIS specific client has set up their CRM.
Use this map — not your general assumptions — to answer the user's question correctly.

SEMANTIC MAP (how this client actually uses their CRM):
{semantic_map}

USER QUESTION: {question}

Your job:
1. Identify what the user is really asking for (intent)
2. Use the semantic map to figure out the correct fields and values to filter on
3. Generate a filter plan that will get the right data from this client's CRM

Rules:
- NEVER assume standard field names. Always use the fields identified in the semantic map.
- If the user says "open" or "active" deals, use the active_deal_definition from the map
- If the user says "lost" deals, use the lost_deal_definition from the map  
- If the user mentions an owner name, use owner_field_primary with fuzzy matching
- If the user mentions "assigned to" or "owns", map to the owner_field_primary
- Be explicit about WHY you're using each field

Respond ONLY with valid JSON (no markdown):
{{
  "intent": "what the user is asking for in plain English",
  "object_type": "deals or contacts",
  "filters": {{
    "owner": "person name if filtering by owner, null otherwise",
    "owner_field": "the actual field name from semantic map to use for owner",
    "exclude_stages": ["stages to exclude if filtering for active/open"],
    "include_stages": ["stages to include, empty means all non-excluded"],
    "status": "active/won/lost/null — only use if reliable per semantic map",
    "tags": ["tag values to filter by"],
    "pipeline": "pipeline name if mentioned, null otherwise",
    "lead_status": "for contacts: lead status filter",
    "hubspot_filters": [],
    "owner_id": null,
    "stage_id": null,
    "pipeline_id": null
  }},
  "post_filters": {{
    "owner_fuzzy": true/false,
    "additional_notes": "any extra filtering logic to apply after fetching"
  }},
  "reasoning": "Step by step: what field I used for owner and why, how I defined 'open'/'lost'/etc based on THIS client's semantic map, any quirks I accounted for",
  "confidence": "high/medium/low",
  "confidence_note": "why confidence is not high, if applicable"
}}"""


ANSWER_PROMPT = """You are helping a business person understand their CRM data.

The user asked: {question}

We ran a query based on how this client actually uses their CRM and got back {count} records.

Semantic map context:
- Owner field used: {owner_field}
- How 'open/active' is defined for this client: {active_definition}
- How 'lost' is defined for this client: {lost_definition}
- Quirks noted: {quirks}

Query reasoning that was used: {reasoning}

Sample of records found: {sample_records}

Write a clear, friendly answer in 1-2 sentences. Include:
1. The direct answer (the number or list)
2. Any important caveat about how the data was interpreted for this specific client

Then write a "reasoning" explanation (2-3 sentences) explaining exactly:
- Which field was used for owner/assignee and why
- How "open", "lost", or other concepts were interpreted for this client
- Any quirks that were handled

Respond ONLY with JSON:
{{
  "headline": "the key number or brief result (e.g. '14 active deals' or 'Garima has 14 open deals')",
  "answer": "1-2 sentence plain English answer",
  "reasoning": "2-3 sentence explanation of HOW the answer was found, citing specific fields and semantic map insights"
}}"""


ZERO_RESULT_PROMPT = """You are helping a business person understand why a query returned zero results.

The user asked: {question}
The query returned 0 results.

Semantic map: {semantic_map}
Query that was run: {query_plan}

Diagnose why this might have happened. Consider:
1. Did we look in the right field?
2. Is the name spelled differently in the data?
3. Does the concept ("open", "lost") mean something different in this client's setup?
4. Are there any obvious alternative interpretations?

Respond ONLY with JSON:
{{
  "warning": "Plain English explanation of why zero results were found and what the user should check",
  "suggestions": ["suggestion 1", "suggestion 2"],
  "reasoning": "Technical explanation of what was searched and why it returned nothing"
}}"""


class QueryTranslator:
    def __init__(self, groq_api_key: str = None):
        self.groq_api_key = groq_api_key

    def answer(self, question: str, schema_map: dict, connector: Any, platform: str) -> dict:
        """Full pipeline: translate question → execute query → format answer."""

        # Step 1: Translate question to query plan
        query_plan = self._translate(question, schema_map)

        # Step 2: Execute query
        object_type = query_plan.get("object_type", "deals")
        filters = query_plan.get("filters", {})

        try:
            if object_type == "contacts":
                records = connector.query_contacts(filters)
            else:
                records = connector.query_deals(filters)
        except Exception as e:
            return {
                "error": f"Query execution failed: {str(e)}",
                "reasoning": query_plan.get("reasoning", ""),
            }

        # Step 3: Handle zero results
        if len(records) == 0:
            zero_result = self._diagnose_zero(question, schema_map, query_plan)
            return {
                "headline": "0 results",
                "warning": zero_result.get("warning", "No records found matching your query."),
                "reasoning": zero_result.get("reasoning", query_plan.get("reasoning", "")),
                "records": [],
            }

        # Step 4: Format answer
        answer = self._format_answer(question, records, query_plan, schema_map)

        # Build clean dataframe for display
        df_records = pd.DataFrame(records)
        # Drop columns that are all empty
        df_records = df_records.dropna(axis=1, how="all")
        # Keep only the most useful columns
        useful_cols = [c for c in df_records.columns
                       if not c.startswith("hs_") and c not in ["id"] and df_records[c].astype(str).str.len().mean() < 100]
        if useful_cols:
            df_records = df_records[useful_cols[:12]]

        return {
            "headline": answer.get("headline", f"{len(records)} records"),
            "answer": answer.get("answer", ""),
            "reasoning": answer.get("reasoning", query_plan.get("reasoning", "")),
            "records": df_records.to_dict("records"),
            "count": len(records),
        }

    def _translate(self, question: str, schema_map: dict) -> dict:
        """Use LLM to translate question into a query plan."""
        map_summary = {
            "owner_field_primary": schema_map.get("owner_field_primary"),
            "owner_fields": schema_map.get("owner_fields"),
            "owner_notes": schema_map.get("owner_notes"),
            "active_deal_definition": schema_map.get("active_deal_definition"),
            "lost_deal_definition": schema_map.get("lost_deal_definition"),
            "status_fields": schema_map.get("status_fields"),
            "priority_field": schema_map.get("priority_field"),
            "contact_owner_field": schema_map.get("contact_owner_field"),
            "quirks": schema_map.get("quirks"),
        }

        prompt = TRANSLATION_PROMPT.format(
            semantic_map=json.dumps(map_summary, indent=2),
            question=question,
        )

        if self.groq_api_key:
            raw = self._call_groq(prompt)
        else:
            raw = self._mock_translate(question, schema_map)

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            return json.loads(cleaned.strip())
        except Exception:
            return {
                "intent": question,
                "object_type": "deals",
                "filters": {},
                "reasoning": "Could not parse query plan, returning all records.",
                "confidence": "low",
            }

    def _format_answer(self, question: str, records: list, query_plan: dict, schema_map: dict) -> dict:
        sample = records[:5]
        # Simplify sample for prompt
        sample_clean = [{k: v for k, v in r.items() if v and str(v).strip() and k not in ["id"]}
                        for r in sample]

        prompt = ANSWER_PROMPT.format(
            question=question,
            count=len(records),
            owner_field=schema_map.get("owner_field_primary", "owner"),
            active_definition=json.dumps(schema_map.get("active_deal_definition", {})),
            lost_definition=json.dumps(schema_map.get("lost_deal_definition", {})),
            quirks=json.dumps(schema_map.get("quirks", [])),
            reasoning=query_plan.get("reasoning", ""),
            sample_records=json.dumps(sample_clean, indent=2)[:2000],
        )

        if self.groq_api_key:
            raw = self._call_groq(prompt)
        else:
            return {
                "headline": f"{len(records)} records found",
                "answer": f"Found {len(records)} records matching your query.",
                "reasoning": query_plan.get("reasoning", ""),
            }

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            return json.loads(cleaned.strip())
        except Exception:
            return {
                "headline": f"{len(records)} records",
                "answer": f"Found {len(records)} records matching your query.",
                "reasoning": query_plan.get("reasoning", ""),
            }

    def _diagnose_zero(self, question: str, schema_map: dict, query_plan: dict) -> dict:
        prompt = ZERO_RESULT_PROMPT.format(
            question=question,
            semantic_map=json.dumps({
                "owner_field": schema_map.get("owner_field_primary"),
                "quirks": schema_map.get("quirks"),
                "active_definition": schema_map.get("active_deal_definition"),
                "lost_definition": schema_map.get("lost_deal_definition"),
            }, indent=2),
            query_plan=json.dumps(query_plan, indent=2),
        )

        if self.groq_api_key:
            raw = self._call_groq(prompt)
            try:
                cleaned = raw.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("```")[1]
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:]
                return json.loads(cleaned.strip())
            except Exception:
                pass

        return {
            "warning": "No records found. This client may store this data differently than expected. Check the schema map above for how fields are actually used.",
            "reasoning": query_plan.get("reasoning", ""),
        }

    def _call_groq(self, prompt: str, max_tokens: int = 1000) -> str:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": max_tokens,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _mock_translate(self, question: str, schema_map: dict) -> str:
        """Fallback mock translation when no Groq key provided."""
        q = question.lower()
        owner = None
        for name in ["garima", "ishan", "priya"]:
            if name in q:
                owner = name.capitalize()
                break

        if "lost" in q or "dead" in q:
            filters = {
                "owner": owner,
                "owner_field": "assigned_to",
                "include_stages": ["Dead Leads"],
                "exclude_stages": [],
                "status": None,
                "tags": [],
            }
            reasoning = "Used 'Dead Leads' stage to identify lost deals, as this client does not use the standard 'lost' status field."
        elif "open" in q or "active" in q or "own" in q:
            filters = {
                "owner": owner,
                "owner_field": "assigned_to",
                "exclude_stages": ["Dead Leads", "Closed Won"],
                "include_stages": [],
                "status": None,
                "tags": [],
            }
            reasoning = "Used 'assigned_to' custom field for owner (standard owner field is blank). Excluded 'Dead Leads' and 'Closed Won' stages to identify active deals."
        elif "contact" in q or "lead" in q or "assigned" in q:
            filters = {
                "owner": owner,
                "owner_field": "lead_owner",
                "lead_status": None,
            }
            return json.dumps({
                "intent": question,
                "object_type": "contacts",
                "filters": filters,
                "reasoning": "Used 'lead_owner' field for contact assignment, as this client stores lead owners in a custom field.",
                "confidence": "high",
            })
        else:
            filters = {
                "owner": owner,
                "owner_field": "assigned_to",
                "exclude_stages": [],
                "include_stages": [],
                "status": None,
                "tags": [],
            }
            reasoning = "Used 'assigned_to' custom field for owner lookup."

        return json.dumps({
            "intent": question,
            "object_type": "deals",
            "filters": filters,
            "reasoning": reasoning,
            "confidence": "high",
        })
