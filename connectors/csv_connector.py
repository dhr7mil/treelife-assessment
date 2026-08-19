"""
CSV/Excel connector — handles messy spreadsheet data.

Supports .csv, .xlsx, .xls files. Auto-detects which columns
represent owners, statuses, deal names, and values — even when
column names are non-standard or inconsistent.
"""

import pandas as pd
import io
from typing import Any


class CSVConnector:
    """
    Connects to a CSV or Excel file uploaded by the user.
    Treats each sheet/file as a 'deals' or 'contacts' object.
    Auto-detects column roles based on content and name patterns.
    """

    # Common patterns for owner/assignee columns
    OWNER_PATTERNS = [
        "assigned", "owner", "rep", "agent", "manager",
        "responsible", "handled", "account manager", "sales rep",
        "lead owner", "deal owner", "contact owner"
    ]

    # Common patterns for status/stage columns
    STATUS_PATTERNS = [
        "status", "stage", "state", "phase", "pipeline",
        "deal stage", "lead status", "opportunity stage"
    ]

    # Common patterns for deal name columns
    NAME_PATTERNS = [
        "title", "name", "deal", "opportunity", "subject",
        "company", "account", "lead", "contact name"
    ]

    # Common patterns for value/amount columns
    VALUE_PATTERNS = [
        "value", "amount", "revenue", "price", "deal value",
        "opportunity value", "arr", "mrr", "contract value"
    ]

    def __init__(self, file_bytes: bytes, filename: str):
        self.filename = filename
        self.file_bytes = file_bytes
        self.df = self._load_file(file_bytes, filename)
        self.column_roles = self._detect_column_roles()

    def _load_file(self, file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Load CSV or Excel file into a DataFrame."""
        name_lower = filename.lower()
        try:
            if name_lower.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes))
            elif name_lower.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(file_bytes))
            else:
                # Try CSV as fallback
                df = pd.read_csv(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Could not read file '{filename}': {str(e)}")

        if df.empty:
            raise ValueError("The file appears to be empty.")

        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]
        return df

    def _match_patterns(self, col_name: str, patterns: list) -> bool:
        col_lower = col_name.lower()
        return any(p in col_lower for p in patterns)

    def _detect_column_roles(self) -> dict:
        """Auto-detect which columns play which roles."""
        roles = {
            "owner": None,
            "status": None,
            "name": None,
            "value": None,
            "all_columns": list(self.df.columns),
        }

        for col in self.df.columns:
            if not roles["owner"] and self._match_patterns(col, self.OWNER_PATTERNS):
                roles["owner"] = col
            if not roles["status"] and self._match_patterns(col, self.STATUS_PATTERNS):
                roles["status"] = col
            if not roles["name"] and self._match_patterns(col, self.NAME_PATTERNS):
                roles["name"] = col
            if not roles["value"] and self._match_patterns(col, self.VALUE_PATTERNS):
                roles["value"] = col

        return roles

    def get_schema(self) -> dict:
        """Return schema info about the uploaded file."""
        col_details = []
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            unique_vals = self.df[col].dropna().unique()
            field = {
                "name": col,
                "label": col,
                "type": "string" if dtype == "object" else "number",
                "standard": False,
            }
            # Include unique values for low-cardinality columns (likely enums)
            if len(unique_vals) <= 20:
                field["values"] = [str(v) for v in unique_vals]
            col_details.append(field)

        quirks = []
        if self.column_roles["owner"]:
            # Check for inconsistent casing in owner field
            owner_col = self.column_roles["owner"]
            owners = self.df[owner_col].dropna().unique()
            owner_lower = [str(o).lower() for o in owners]
            if len(owners) != len(set(owner_lower)):
                quirks.append(f"Owner column '{owner_col}' has inconsistent casing")

        if not self.column_roles["owner"]:
            quirks.append("No obvious owner/assignee column detected — may be stored under an unusual name")
        if not self.column_roles["status"]:
            quirks.append("No obvious status/stage column detected")

        return {
            "platform": "CSV/Excel",
            "filename": self.filename,
            "objects": {
                "deals": {
                    "fields": col_details,
                    "record_count": len(self.df),
                    "detected_roles": self.column_roles,
                }
            },
            "quirks_detected": quirks,
        }

    def get_sample_records(self, limit: int = 20) -> dict:
        """Return sample records for schema discovery."""
        sample = self.df.head(limit).fillna("").astype(str)
        return {
            "deals": sample.to_dict("records"),
            "contacts": [],
        }

    def query_deals(self, filters: dict) -> list:
        """Filter the DataFrame based on translated query filters."""
        df = self.df.copy()

        # Owner filter — use detected owner column or override from filters
        owner = filters.get("owner")
        owner_field = filters.get("owner_field") or self.column_roles.get("owner")
        if owner and owner_field and owner_field in df.columns:
            owner_lower = owner.lower()
            df = df[df[owner_field].astype(str).str.lower().str.contains(owner_lower, na=False)]

        # Status/stage filter
        status_field = filters.get("status_field") or self.column_roles.get("status")

        exclude_stages = filters.get("exclude_stages", [])
        if exclude_stages and status_field and status_field in df.columns:
            df = df[~df[status_field].astype(str).isin(exclude_stages)]

        include_stages = filters.get("include_stages", [])
        if include_stages and status_field and status_field in df.columns:
            df = df[df[status_field].astype(str).isin(include_stages)]

        status = filters.get("status")
        if status and status_field and status_field in df.columns:
            df = df[df[status_field].astype(str).str.lower().str.contains(status.lower(), na=False)]

        # Tag/priority filter
        tags = filters.get("tags", [])
        if tags:
            for col in df.columns:
                if "tag" in col.lower() or "priority" in col.lower():
                    for tag in tags:
                        df = df[df[col].astype(str).str.lower().str.contains(tag.lower(), na=False)]
                    break

        return df.fillna("").astype(str).to_dict("records")

    def query_contacts(self, filters: dict) -> list:
        """For CSV, contacts = same file filtered differently."""
        return self.query_deals(filters)

    def get_all_deals(self) -> list:
        return self.df.fillna("").astype(str).to_dict("records")

    def get_all_contacts(self) -> list:
        return self.df.fillna("").astype(str).to_dict("records")
