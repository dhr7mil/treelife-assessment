# Treelife AI — Semantic Business Data Translation Layer

A layer that sits between plain English questions and business CRM tools, understanding how each specific client actually uses their tools — even when that's messy, non-standard, or inconsistent.

## 🚀 Live Demo

👉 **https://treelife-assessment-2zi68px6kvecesoz2tkhfl.streamlit.app/**

Select "Mock Demo (no API key needed)", enter a Groq API key, and start asking questions.

## The Problem It Solves

Most businesses don't use their CRM "correctly":
- The real owner is in a hand-typed custom field called "Assigned To", not the standard owner field
- "Lost" deals are quietly dragged into a "Dead Leads" stage, while status still says "active"
- Owner names have typos, nicknames, inconsistent casing ("Garima", "garima", "GARIMA")
- Priority is encoded in tags, not a dedicated field

A naive system searches for "owner = Garima" and finds nothing. This system figures out how THIS specific client works and searches the right place.

## How It Works

1. **Connect** → App calls CRM API, fetches all fields, stages, sample records
2. **Discover** → LLM reads schema + samples, builds a semantic map
3. **Ask** → User asks in plain English
4. **Translate** → LLM uses semantic map to build the correct query
5. **Execute** → App calls CRM API with correct filters
6. **Answer** → Plain English answer + full reasoning trace

## Supported Platforms

| Platform | Setup |
|----------|-------|
| Mock Demo | No API key needed — built-in messy demo data |
| HubSpot | Private App access token |
| Pipedrive | API token from Settings → Personal preferences → API |

## Architecture

```
app.py               — Streamlit UI
connectors/
  mock.py            — Mock CRM with intentionally messy data
  hubspot.py         — HubSpot CRM API v3
  pipedrive.py       — Pipedrive API v1
core/
  discovery.py       — Schema discovery + semantic map building
  translator.py      — NL question → query → answer
```

The architecture is connector-based — adding support for Excel, SQL, or Google Sheets means writing a new connector class with the same `get_schema()` and `query_deals()` interface, without touching the core translation logic.

## Getting API Keys

**Groq (free LLM — no credit card needed):**
1. Sign up at console.groq.com
2. Create an API key

**HubSpot:**
1. Settings → Integrations → Private Apps
2. Create app with scopes: `crm.objects.deals.read`, `crm.objects.contacts.read`
3. Copy the access token

**Pipedrive:**
1. Settings → Personal preferences → API
2. Copy your personal API token

## Example Questions

- "How many open deals does Garima own?"
- "Show all leads assigned to Ishan"
- "How many lost deals are there?"
- "Who has the most active deals?"
- "List all high priority deals"

---

Once that's committed, shall I build the CSV connector to make it stronger?
