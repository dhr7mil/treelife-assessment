"""
Pipedrive connector — discovers schema and queries deals/persons via Pipedrive API v1.
"""

import requests
from typing import Any


class PipedriveConnector:
    BASE = "https://api.pipedrive.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._test_connection()

    def _get(self, path: str, params: dict = None) -> dict:
        p = {"api_token": self.api_key, **(params or {})}
        r = requests.get(f"{self.BASE}{path}", params=p)
        if r.status_code == 401:
            raise ValueError("Invalid Pipedrive API key.")
        r.raise_for_status()
        return r.json()

    def _test_connection(self):
        try:
            self._get("/users/me")
        except Exception as e:
            raise ValueError(f"Pipedrive connection failed: {str(e)}")

    def get_schema(self) -> dict:
        deal_fields_r = self._get("/dealFields")
        person_fields_r = self._get("/personFields")
        pipelines_r = self._get("/pipelines")
        stages_r = self._get("/stages")

        def fmt_fields(raw):
            out = []
            for f in raw.get("data") or []:
                field = {
                    "name": f.get("key", ""),
                    "label": f.get("name", ""),
                    "type": f.get("field_type", "varchar"),
                    "standard": f.get("edit_flag", True),
                }
                if f.get("options"):
                    field["values"] = [o.get("label", "") for o in f["options"][:20]]
                out.append(field)
            return out

        pipelines = [{"id": p["id"], "name": p["name"]} for p in (pipelines_r.get("data") or [])]
        stages = [{"id": s["id"], "name": s["name"], "pipeline_id": s.get("pipeline_id")} for s in (stages_r.get("data") or [])]

        deals_r = self._get("/deals", {"limit": 1})
        persons_r = self._get("/persons", {"limit": 1})

        return {
            "platform": "Pipedrive",
            "objects": {
                "deals": {
                    "fields": fmt_fields(deal_fields_r),
                    "record_count": deals_r.get("additional_data", {}).get("pagination", {}).get("more_items_in_collection", "unknown"),
                    "pipelines": pipelines,
                    "stages": stages,
                },
                "contacts": {
                    "fields": fmt_fields(person_fields_r),
                    "record_count": persons_r.get("additional_data", {}).get("pagination", {}).get("more_items_in_collection", "unknown"),
                },
            },
        }

    def get_sample_records(self, limit: int = 20) -> dict:
        deals_r = self._get("/deals", {"limit": limit, "status": "all_not_deleted"})
        persons_r = self._get("/persons", {"limit": limit})

        deals = []
        for d in (deals_r.get("data") or []):
            row = {k: v for k, v in d.items() if v is not None}
            if isinstance(row.get("user_id"), dict):
                row["owner_name"] = row["user_id"].get("name", "")
            if isinstance(row.get("stage_id"), int):
                row["stage_id"] = row["stage_id"]
            deals.append(row)

        contacts = []
        for p in (persons_r.get("data") or []):
            row = {k: v for k, v in p.items() if v is not None}
            if isinstance(row.get("owner_id"), dict):
                row["owner_name"] = row["owner_id"].get("name", "")
            contacts.append(row)

        return {"deals": deals, "contacts": contacts}

    def query_deals(self, filters: dict) -> list:
        params = {"limit": 100, "status": "all_not_deleted"}

        status = filters.get("status")
        if status == "open":
            params["status"] = "open"
        elif status == "won":
            params["status"] = "won"
        elif status == "lost":
            params["status"] = "lost"

        owner_id = filters.get("owner_id")
        if owner_id:
            params["user_id"] = owner_id

        stage_id = filters.get("stage_id")
        if stage_id:
            params["stage_id"] = stage_id

        pipeline_id = filters.get("pipeline_id")
        if pipeline_id:
            params["pipeline_id"] = pipeline_id

        r = self._get("/deals", params)
        results = []
        for d in (r.get("data") or []):
            row = {k: v for k, v in d.items() if v is not None}
            if isinstance(row.get("user_id"), dict):
                row["owner_name"] = row["user_id"].get("name", "")
            results.append(row)

        # Post-filter by owner name if needed (for custom text fields)
        owner_name = filters.get("owner")
        owner_field = filters.get("owner_field")
        if owner_name and owner_field:
            results = [
                r for r in results
                if owner_name.lower() in str(r.get(owner_field, r.get("owner_name", ""))).lower()
            ]

        return results

    def query_contacts(self, filters: dict) -> list:
        params = {"limit": 100}
        r = self._get("/persons", params)
        results = []
        for p in (r.get("data") or []):
            row = {k: v for k, v in p.items() if v is not None}
            if isinstance(row.get("owner_id"), dict):
                row["owner_name"] = row["owner_id"].get("name", "")
            results.append(row)

        owner = filters.get("owner")
        if owner:
            results = [
                r for r in results
                if owner.lower() in str(r.get("owner_name", "")).lower()
            ]

        return results

    def get_all_deals(self) -> list:
        r = self._get("/deals", {"limit": 100, "status": "all_not_deleted"})
        results = []
        for d in (r.get("data") or []):
            row = {k: v for k, v in d.items() if v is not None}
            if isinstance(row.get("user_id"), dict):
                row["owner_name"] = row["user_id"].get("name", "")
            results.append(row)
        return results

    def get_all_contacts(self) -> list:
        r = self._get("/persons", {"limit": 100})
        results = []
        for p in (r.get("data") or []):
            row = {k: v for k, v in p.items() if v is not None}
            if isinstance(row.get("owner_id"), dict):
                row["owner_name"] = row["owner_id"].get("name", "")
            results.append(row)
        return results
