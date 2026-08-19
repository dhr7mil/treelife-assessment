"""
HubSpot connector — discovers schema and queries deals/contacts via HubSpot CRM API v3.
"""

import requests
from typing import Any


class HubSpotConnector:
    BASE = "https://api.hubapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._test_connection()

    def _test_connection(self):
        r = requests.get(f"{self.BASE}/crm/v3/objects/deals?limit=1", headers=self.headers)
        if r.status_code == 401:
            raise ValueError("Invalid HubSpot API key. Please check and try again.")
        if r.status_code not in (200, 404):
            raise ValueError(f"HubSpot connection error: {r.status_code} — {r.text[:200]}")

    def _get(self, path: str, params: dict = None) -> dict:
        r = requests.get(f"{self.BASE}{path}", headers=self.headers, params=params or {})
        r.raise_for_status()
        return r.json()

    def get_schema(self) -> dict:
        """Fetch all deal and contact properties (fields) from HubSpot."""
        deal_props_raw = self._get("/crm/v3/properties/deals")
        contact_props_raw = self._get("/crm/v3/properties/contacts")

        def fmt_props(props):
            out = []
            for p in props.get("results", []):
                field = {
                    "name": p["name"],
                    "label": p.get("label", p["name"]),
                    "type": p.get("type", "string"),
                    "standard": not p.get("hubspotDefined") == False,
                }
                if p.get("options"):
                    field["values"] = [o["label"] for o in p["options"][:20]]
                out.append(field)
            return out

        # Count records
        deal_count_r = self._get("/crm/v3/objects/deals", {"limit": 1})
        contact_count_r = self._get("/crm/v3/objects/contacts", {"limit": 1})

        return {
            "platform": "HubSpot",
            "objects": {
                "deals": {
                    "fields": fmt_props(deal_props_raw),
                    "record_count": deal_count_r.get("total", "unknown"),
                },
                "contacts": {
                    "fields": fmt_props(contact_props_raw),
                    "record_count": contact_count_r.get("total", "unknown"),
                },
            },
        }

    def get_sample_records(self, limit: int = 20) -> dict:
        """Fetch sample deals and contacts to understand real usage patterns."""
        # Get all deal properties to see which ones are actually used
        deal_props_raw = self._get("/crm/v3/properties/deals")
        all_deal_props = [p["name"] for p in deal_props_raw.get("results", [])][:50]

        contact_props_raw = self._get("/crm/v3/properties/contacts")
        all_contact_props = [p["name"] for p in contact_props_raw.get("results", [])][:50]

        deals_r = self._get("/crm/v3/objects/deals", {
            "limit": limit,
            "properties": ",".join(all_deal_props),
        })
        contacts_r = self._get("/crm/v3/objects/contacts", {
            "limit": limit,
            "properties": ",".join(all_contact_props),
        })

        deals = [{"id": d["id"], **d.get("properties", {})} for d in deals_r.get("results", [])]
        contacts = [{"id": c["id"], **c.get("properties", {})} for c in contacts_r.get("results", [])]

        return {"deals": deals, "contacts": contacts}

    def query_deals(self, filters: dict) -> list:
        """Query deals with filters derived from semantic map translation."""
        all_deal_props_r = self._get("/crm/v3/properties/deals")
        all_props = [p["name"] for p in all_deal_props_r.get("results", [])][:50]

        filter_groups = []
        hs_filters = filters.get("hubspot_filters", [])
        if hs_filters:
            filter_groups = [{"filters": hs_filters}]

        body = {
            "filterGroups": filter_groups,
            "properties": all_props,
            "limit": 100,
        }
        r = requests.post(
            f"{self.BASE}/crm/v3/objects/deals/search",
            headers=self.headers,
            json=body,
        )
        r.raise_for_status()
        data = r.json()

        results = []
        for d in data.get("results", []):
            row = {"id": d["id"]}
            row.update({k: v for k, v in d.get("properties", {}).items() if v})
            results.append(row)

        # Apply post-filter for owner text matching (for custom text fields)
        owner_field = filters.get("owner_field")
        owner_value = filters.get("owner")
        if owner_field and owner_value and not hs_filters:
            results = [
                r for r in results
                if owner_value.lower() in str(r.get(owner_field, "")).lower()
            ]

        return results

    def query_contacts(self, filters: dict) -> list:
        all_contact_props_r = self._get("/crm/v3/properties/contacts")
        all_props = [p["name"] for p in all_contact_props_r.get("results", [])][:50]

        filter_groups = []
        hs_filters = filters.get("hubspot_filters", [])
        if hs_filters:
            filter_groups = [{"filters": hs_filters}]

        body = {
            "filterGroups": filter_groups,
            "properties": all_props,
            "limit": 100,
        }
        r = requests.post(
            f"{self.BASE}/crm/v3/objects/contacts/search",
            headers=self.headers,
            json=body,
        )
        r.raise_for_status()
        data = r.json()

        results = []
        for c in data.get("results", []):
            row = {"id": c["id"]}
            row.update({k: v for k, v in c.get("properties", {}).items() if v})
            results.append(row)

        return results

    def get_all_deals(self) -> list:
        all_deal_props_r = self._get("/crm/v3/properties/deals")
        all_props = [p["name"] for p in all_deal_props_r.get("results", [])][:50]
        r = self._get("/crm/v3/objects/deals", {"limit": 100, "properties": ",".join(all_props)})
        return [{"id": d["id"], **d.get("properties", {})} for d in r.get("results", [])]

    def get_all_contacts(self) -> list:
        all_contact_props_r = self._get("/crm/v3/properties/contacts")
        all_props = [p["name"] for p in all_contact_props_r.get("results", [])][:50]
        r = self._get("/crm/v3/objects/contacts", {"limit": 100, "properties": ",".join(all_props)})
        return [{"id": c["id"], **c.get("properties", {})} for c in r.get("results", [])]
