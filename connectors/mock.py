"""
Mock CRM connector — simulates a messy, real-world CRM setup.

Quirks intentionally built in:
- Owner is stored in a custom field "Assigned To" (hand-typed, typos included)
  rather than the standard owner/assignee field
- "Lost" deals are NOT marked as lost — they're dragged into a stage called "Dead Leads"
  while their status remains "active"
- Priority is encoded in a tag, not the standard priority field
- Some deals have blank standard-owner fields
- Names have inconsistent casing and nicknames (Garima vs garima vs Garima S.)
"""

import random
from typing import Any


DEALS = [
    # ── Garima's deals ─────────────────────────────────────────────────────────
    {"id": "d001", "title": "Acme Corp Expansion", "assigned_to": "Garima", "official_owner": "", "stage": "Proposal", "status": "active", "value": 45000, "tags": ["high-priority"], "pipeline": "Sales"},
    {"id": "d002", "title": "TechNova Integration", "assigned_to": "Garima S.", "official_owner": "", "stage": "Negotiation", "status": "active", "value": 28000, "tags": ["high-priority"], "pipeline": "Sales"},
    {"id": "d003", "title": "BlueSky Renewal", "assigned_to": "garima", "official_owner": "", "stage": "Discovery", "status": "active", "value": 12000, "tags": [], "pipeline": "Sales"},
    {"id": "d004", "title": "Patel Industries", "assigned_to": "Garima", "official_owner": "", "stage": "Dead Leads", "status": "active", "value": 9000, "tags": [], "pipeline": "Sales"},
    {"id": "d005", "title": "MegaMart Pilot", "assigned_to": "Garima", "official_owner": "", "stage": "Proposal", "status": "active", "value": 67000, "tags": ["high-priority"], "pipeline": "Sales"},
    {"id": "d006", "title": "Sunrise Hotels", "assigned_to": "GARIMA", "official_owner": "", "stage": "Negotiation", "status": "active", "value": 31000, "tags": [], "pipeline": "Sales"},
    {"id": "d007", "title": "CloudPath Deal", "assigned_to": "Garima", "official_owner": "", "stage": "Discovery", "status": "active", "value": 22000, "tags": [], "pipeline": "Sales"},
    {"id": "d008", "title": "Old Retail Corp", "assigned_to": "Garima", "official_owner": "", "stage": "Dead Leads", "status": "active", "value": 5000, "tags": [], "pipeline": "Sales"},
    {"id": "d009", "title": "FintechX Platform", "assigned_to": "Garima S", "official_owner": "", "stage": "Proposal", "status": "active", "value": 89000, "tags": ["high-priority"], "pipeline": "Enterprise"},
    {"id": "d010", "title": "Landmark Realty", "assigned_to": "Garima", "official_owner": "", "stage": "Closed Won", "status": "won", "value": 55000, "tags": [], "pipeline": "Sales"},
    {"id": "d011", "title": "Vertex Analytics", "assigned_to": "Garima", "official_owner": "", "stage": "Discovery", "status": "active", "value": 17000, "tags": [], "pipeline": "Sales"},
    {"id": "d012", "title": "Crestwood Manufacturing", "assigned_to": "garima", "official_owner": "", "stage": "Negotiation", "status": "active", "value": 43000, "tags": ["high-priority"], "pipeline": "Sales"},
    {"id": "d013", "title": "Zephyr Logistics", "assigned_to": "Garima", "official_owner": "", "stage": "Dead Leads", "status": "active", "value": 8000, "tags": [], "pipeline": "Sales"},
    {"id": "d014", "title": "NovaStar Telecom", "assigned_to": "Garima", "official_owner": "", "stage": "Discovery", "status": "active", "value": 36000, "tags": [], "pipeline": "Enterprise"},
    {"id": "d015", "title": "HarborView Capital", "assigned_to": "Garima", "official_owner": "", "stage": "Proposal", "status": "active", "value": 71000, "tags": ["high-priority"], "pipeline": "Enterprise"},
    {"id": "d016", "title": "Stale Prospect 2022", "assigned_to": "Garima", "official_owner": "", "stage": "Dead Leads", "status": "active", "value": 3000, "tags": [], "pipeline": "Sales"},

    # ── Ishan's deals ─────────────────────────────────────────────────────────
    {"id": "d017", "title": "Global Pharma Deal", "assigned_to": "Ishan", "official_owner": "", "stage": "Proposal", "status": "active", "value": 52000, "tags": ["high-priority"], "pipeline": "Sales"},
    {"id": "d018", "title": "AutoDrive Systems", "assigned_to": "ishan", "official_owner": "", "stage": "Negotiation", "status": "active", "value": 34000, "tags": [], "pipeline": "Sales"},
    {"id": "d019", "title": "EduTech Platform", "assigned_to": "Ishan K.", "official_owner": "", "stage": "Dead Leads", "status": "active", "value": 11000, "tags": [], "pipeline": "Sales"},
    {"id": "d020", "title": "RetailMax Chain", "assigned_to": "Ishan", "official_owner": "", "stage": "Discovery", "status": "active", "value": 25000, "tags": [], "pipeline": "Sales"},
    {"id": "d021", "title": "SkyBridge Infra", "assigned_to": "Ishan", "official_owner": "", "stage": "Closed Won", "status": "won", "value": 98000, "tags": ["high-priority"], "pipeline": "Enterprise"},
    {"id": "d022", "title": "ClearView Insurance", "assigned_to": "Ishan", "official_owner": "", "stage": "Proposal", "status": "active", "value": 41000, "tags": [], "pipeline": "Sales"},

    # ── Priya's deals ─────────────────────────────────────────────────────────
    {"id": "d023", "title": "Quantum Computing Co", "assigned_to": "Priya", "official_owner": "", "stage": "Discovery", "status": "active", "value": 120000, "tags": ["high-priority"], "pipeline": "Enterprise"},
    {"id": "d024", "title": "BioMed Supplies", "assigned_to": "priya", "official_owner": "", "stage": "Dead Leads", "status": "active", "value": 7000, "tags": [], "pipeline": "Sales"},
    {"id": "d025", "title": "AgroTech Partners", "assigned_to": "Priya M", "official_owner": "", "stage": "Negotiation", "status": "active", "value": 38000, "tags": [], "pipeline": "Sales"},
]

CONTACTS = [
    {"id": "c001", "name": "Rajesh Sharma", "email": "rajesh@acmecorp.com", "lead_owner": "Garima", "lead_status": "Open", "source": "Website"},
    {"id": "c002", "name": "Anita Patel", "email": "anita@technova.io", "lead_owner": "Garima S.", "lead_status": "Open", "source": "Referral"},
    {"id": "c003", "name": "Vikram Singh", "email": "v.singh@bluesky.co", "lead_owner": "garima", "lead_status": "Open", "source": "LinkedIn"},
    {"id": "c004", "name": "Meena Joshi", "email": "meena@megamart.com", "lead_owner": "Garima", "lead_status": "Contacted", "source": "Website"},
    {"id": "c005", "name": "Arjun Nair", "email": "arjun@fintechx.com", "lead_owner": "Ishan", "lead_status": "Open", "source": "Referral"},
    {"id": "c006", "name": "Sunita Roy", "email": "sunita@global.ph", "lead_owner": "ishan", "lead_status": "Contacted", "source": "Cold Outreach"},
    {"id": "c007", "name": "Kiran Mehta", "email": "kiran@quantum.co", "lead_owner": "Priya", "lead_status": "Open", "source": "Conference"},
    {"id": "c008", "name": "Deepak Bose", "email": "deepak@agro.in", "lead_owner": "Priya M", "lead_status": "Contacted", "source": "Website"},
    {"id": "c009", "name": "Lakshmi Rao", "email": "lakshmi@clearview.in", "lead_owner": "Ishan", "lead_status": "Open", "source": "Referral"},
    {"id": "c010", "name": "Rohit Gupta", "email": "rohit@harborview.com", "lead_owner": "GARIMA", "lead_status": "Open", "source": "LinkedIn"},
]


class MockConnector:
    """Simulates a messy CRM with non-standard field usage."""

    def get_schema(self) -> dict:
        return {
            "platform": "Mock CRM (Messy Setup)",
            "objects": {
                "deals": {
                    "fields": [
                        {"name": "id", "type": "string", "standard": True},
                        {"name": "title", "type": "string", "standard": True},
                        {"name": "assigned_to", "type": "string", "standard": False, "note": "Custom field — hand typed names"},
                        {"name": "official_owner", "type": "string", "standard": True, "note": "Standard owner field — mostly blank"},
                        {"name": "stage", "type": "enum", "standard": True,
                         "values": ["Discovery", "Proposal", "Negotiation", "Closed Won", "Dead Leads"],
                         "note": "'Dead Leads' is used for lost deals, not a standard lost status"},
                        {"name": "status", "type": "enum", "standard": True,
                         "values": ["active", "won", "lost"],
                         "note": "Standard status — rarely updated, most lost deals still show 'active'"},
                        {"name": "value", "type": "number", "standard": True},
                        {"name": "tags", "type": "array", "standard": False, "values": ["high-priority"]},
                        {"name": "pipeline", "type": "string", "standard": True, "values": ["Sales", "Enterprise"]},
                    ],
                    "record_count": len(DEALS),
                },
                "contacts": {
                    "fields": [
                        {"name": "id", "type": "string", "standard": True},
                        {"name": "name", "type": "string", "standard": True},
                        {"name": "email", "type": "string", "standard": True},
                        {"name": "lead_owner", "type": "string", "standard": False, "note": "Custom field for owner — hand typed"},
                        {"name": "lead_status", "type": "enum", "standard": True, "values": ["Open", "Contacted", "Qualified", "Disqualified"]},
                        {"name": "source", "type": "string", "standard": False},
                    ],
                    "record_count": len(CONTACTS),
                },
            },
            "quirks_detected": [
                "official_owner field in deals is mostly empty — team uses 'assigned_to' instead",
                "'Dead Leads' stage is used to represent lost/inactive deals, not the standard status field",
                "Owner names in 'assigned_to' are inconsistently cased and sometimes abbreviated",
                "Priority encoded in tags ('high-priority') not the standard priority field",
            ]
        }

    def get_sample_records(self, limit: int = 20) -> dict:
        return {
            "deals": DEALS[:limit],
            "contacts": CONTACTS[:limit],
        }

    def query_deals(self, filters: dict) -> list:
        results = list(DEALS)

        owner = filters.get("owner")
        if owner:
            owner_lower = owner.lower().strip()
            results = [
                d for d in results
                if owner_lower in d.get("assigned_to", "").lower()
            ]

        exclude_stages = filters.get("exclude_stages", [])
        if exclude_stages:
            results = [d for d in results if d["stage"] not in exclude_stages]

        include_stages = filters.get("include_stages", [])
        if include_stages:
            results = [d for d in results if d["stage"] in include_stages]

        status = filters.get("status")
        if status:
            results = [d for d in results if d["status"] == status]

        tags = filters.get("tags", [])
        for tag in tags:
            results = [d for d in results if tag in d.get("tags", [])]

        pipeline = filters.get("pipeline")
        if pipeline:
            results = [d for d in results if d.get("pipeline", "").lower() == pipeline.lower()]

        return results

    def query_contacts(self, filters: dict) -> list:
        results = list(CONTACTS)

        owner = filters.get("owner")
        if owner:
            owner_lower = owner.lower().strip()
            results = [
                c for c in results
                if owner_lower in c.get("lead_owner", "").lower()
            ]

        status = filters.get("lead_status")
        if status:
            results = [c for c in results if c.get("lead_status", "").lower() == status.lower()]

        return results

    def get_all_deals(self) -> list:
        return DEALS

    def get_all_contacts(self) -> list:
        return CONTACTS
