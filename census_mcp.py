#!/usr/bin/env python3
"""
Census / Demographics Domain (ACS 5-Year Data by Community Area)

Provides MCP tools for querying population, income distribution, race/ethnicity,
and age/gender demographics across Chicago's 77 community areas.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional

from base_domain import BaseDataDomain
from census_data_fetcher import CensusDataFetcher


# ---------------------------------------------------------------------------
# Column groups for structured queries
# ---------------------------------------------------------------------------

INCOME_COLS = [
    "under_25_000",
    "_25_000_to_49_999",
    "_50_000_to_74_999",
    "_75_000_to_125_000",
    "_125_000",
]

INCOME_LABELS = {
    "under_25_000": "Under $25k",
    "_25_000_to_49_999": "$25k–$50k",
    "_50_000_to_74_999": "$50k–$75k",
    "_75_000_to_125_000": "$75k–$125k",
    "_125_000": "Over $125k",
}

RACE_COLS = [
    "white",
    "black_or_african_american",
    "american_indian_or_alaska",
    "asian",
    "native_hawaiin_or_pacific",
    "other_race",
    "multiracial",
    "hispanic_or_latino",
    "white_not_hispanic_or_latino",
]

RACE_LABELS = {
    "white": "White",
    "black_or_african_american": "Black / African American",
    "american_indian_or_alaska": "American Indian / Alaska Native",
    "asian": "Asian",
    "native_hawaiin_or_pacific": "Native Hawaiian / Pacific Islander",
    "other_race": "Other Race",
    "multiracial": "Multiracial",
    "hispanic_or_latino": "Hispanic or Latino",
    "white_not_hispanic_or_latino": "White (non-Hispanic)",
}

AGE_GENDER_COLS = [
    "male_0_to_17", "male_18_to_24", "male_25_to_34",
    "male_35_to_49", "male_50_to_64", "male_65",
    "female_0_to_17", "female_18_to_24", "female_25_to_34",
    "female_35_to_49", "female_50_to_64", "female_65",
]


def _load_community_area_lookup() -> Dict:
    """Load the shared community area lookup JSON."""
    path = Path("knowledge_base/community_areas.json")
    if not path.exists():
        return {"areas": {}, "aliases": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class CensusDataMCP(BaseDataDomain):
    """MCP domain for ACS 5-Year census/demographics data."""

    def __init__(self, cache_dir: str = "./data/cache"):
        self.fetcher = CensusDataFetcher(cache_dir=cache_dir)
        self.df: Optional[pd.DataFrame] = None
        self._ca_lookup = _load_community_area_lookup()
        # Build a lowercase name → number map for fuzzy matching
        self._name_to_num: Dict[str, int] = {}
        for num_str, name in self._ca_lookup.get("areas", {}).items():
            self._name_to_num[name.lower()] = int(num_str)
        for alias, num in self._ca_lookup.get("aliases", {}).items():
            self._name_to_num[alias.lower()] = int(num)
        # Attempt to load data on construction
        self.load_data()

    # ------------------------------------------------------------------
    # BaseDataDomain interface
    # ------------------------------------------------------------------

    @property
    def domain_name(self) -> str:
        return "census_demographics"

    def load_data(self, **kwargs) -> bool:
        try:
            self.df = self.fetcher.fetch_all_data()
            if self.df is not None and not self.df.empty:
                self._prepare_dataframe()
                print(f"  ✅ Census data loaded: {len(self.df)} rows")
                return True
            print("  ⚠️ Census data is empty")
            return False
        except Exception as e:
            print(f"  ⚠️ Census data load failed: {e}")
            return False

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "query_census_demographics",
                "description": (
                    "Query ACS 5-Year census data for Chicago community areas. "
                    "Returns population, income distribution, race/ethnicity, and age/gender breakdowns. "
                    "Use for questions like: 'What is the population of Austin?', "
                    "'Which community area has the highest income?', "
                    "'Compare demographics of Hyde Park and Englewood'."
                ),
                "parameters": {
                    "community_area": {
                        "type": "string",
                        "description": "Community area name or number (e.g., 'Austin' or '25')",
                    },
                    "year": {
                        "type": "integer",
                        "description": "ACS survey year (default: latest available, e.g. 2023)",
                    },
                    "metric": {
                        "type": "string",
                        "description": (
                            "Category to query: 'population', 'income', 'race', 'age', or 'all'. "
                            "Default 'all'."
                        ),
                    },
                    "compare_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional community areas for side-by-side comparison",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "For ranking queries — return the top N areas (default 10)",
                    },
                },
                "required": [],
            }
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "query_census_demographics":
            return self.query_demographics(
                community_area=arguments.get("community_area"),
                year=arguments.get("year"),
                metric=arguments.get("metric", "all"),
                compare_areas=arguments.get("compare_areas"),
                top_n=arguments.get("top_n", 10),
            )
        return {"error": f"Unknown census tool: {tool_name}"}

    def format_result(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"❌ Error: {result['error']}"
        try:
            return self._format_demographics_result(result)
        except Exception as e:
            return f"📋 **Raw Census Result:** {json.dumps(result, indent=2)}\n\n⚠️ Format error: {e}"

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------

    def _prepare_dataframe(self):
        """Parse numeric columns and normalise community area names."""
        assert self.df is not None
        # Numeric conversion for all data columns
        numeric_cols = (
            INCOME_COLS + RACE_COLS + AGE_GENDER_COLS + ["total_population"]
        )
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        # Standardise community area name to title case for matching
        if "community_area" in self.df.columns:
            self.df["community_area_clean"] = (
                self.df["community_area"].str.strip().str.title()
            )

        # Parse ACS year
        if "acs_year" in self.df.columns:
            self.df["acs_year"] = pd.to_numeric(self.df["acs_year"], errors="coerce")

    # ------------------------------------------------------------------
    # Community area resolution
    # ------------------------------------------------------------------

    def _resolve_community_area(self, value: str) -> Optional[str]:
        """Resolve a community area name or number to the canonical name in the df."""
        if value is None:
            return None
        val = str(value).strip()

        # Try as a number first
        try:
            num = int(val)
            name = self._ca_lookup.get("areas", {}).get(str(num))
            if name:
                return name.title()
        except ValueError:
            pass

        # Try exact match (case-insensitive)
        lower = val.lower()
        num = self._name_to_num.get(lower)
        if num is not None:
            name = self._ca_lookup.get("areas", {}).get(str(num))
            if name:
                return name.title()

        # Fuzzy substring match against known names
        for known_lower, known_num in self._name_to_num.items():
            if lower in known_lower or known_lower in lower:
                name = self._ca_lookup.get("areas", {}).get(str(known_num))
                if name:
                    return name.title()

        return val.title()  # best-effort fallback

    # ------------------------------------------------------------------
    # Core query
    # ------------------------------------------------------------------

    def query_demographics(
        self,
        community_area: Optional[str] = None,
        year: Optional[int] = None,
        metric: str = "all",
        compare_areas: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> Dict[str, Any]:
        """Query census demographics data."""
        if self.df is None or self.df.empty:
            return {"error": "Census data not loaded"}

        df = self.df.copy()

        # Filter by year (default: latest)
        if "acs_year" in df.columns:
            available_years = sorted(df["acs_year"].dropna().unique())
            target_year = year if year and year in available_years else (available_years[-1] if available_years else None)
            if target_year is not None:
                df = df[df["acs_year"] == target_year]
        else:
            target_year = None

        result: Dict[str, Any] = {
            "acs_year": int(target_year) if target_year else "unknown",
            "metric": metric,
            "total_areas": len(df),
        }

        # Build list of areas to report on
        areas_to_query: List[str] = []
        if community_area:
            resolved = self._resolve_community_area(community_area)
            if resolved:
                areas_to_query.append(resolved)
        if compare_areas:
            for ca in compare_areas:
                resolved = self._resolve_community_area(ca)
                if resolved:
                    areas_to_query.append(resolved)

        # If specific areas requested, filter df
        if areas_to_query:
            if "community_area_clean" in df.columns:
                mask = df["community_area_clean"].isin(areas_to_query)
                area_df = df[mask]
            else:
                area_df = df
            result["areas_queried"] = areas_to_query
            result["areas_found"] = len(area_df)
            result["area_data"] = self._extract_area_data(area_df, metric)
        else:
            # Ranking mode — return top_n by the relevant metric
            result["ranking"] = self._build_ranking(df, metric, top_n)

        return result

    # ------------------------------------------------------------------
    # Data extraction helpers
    # ------------------------------------------------------------------

    def _extract_area_data(self, df: pd.DataFrame, metric: str) -> List[Dict[str, Any]]:
        """Extract metric data for each row in df."""
        rows = []
        for _, row in df.iterrows():
            entry: Dict[str, Any] = {
                "community_area": row.get("community_area_clean", row.get("community_area", "?")),
            }
            if metric in ("all", "population"):
                entry["total_population"] = self._safe_int(row.get("total_population"))

            if metric in ("all", "income"):
                entry["income_distribution"] = {}
                for col in INCOME_COLS:
                    if col in row.index:
                        entry["income_distribution"][INCOME_LABELS.get(col, col)] = self._safe_int(row[col])

            if metric in ("all", "race"):
                entry["race_ethnicity"] = {}
                for col in RACE_COLS:
                    if col in row.index:
                        entry["race_ethnicity"][RACE_LABELS.get(col, col)] = self._safe_int(row[col])

            if metric in ("all", "age"):
                entry["age_gender"] = {}
                for col in AGE_GENDER_COLS:
                    if col in row.index:
                        label = col.replace("_", " ").title()
                        entry["age_gender"][label] = self._safe_int(row[col])

            rows.append(entry)
        return rows

    def _build_ranking(self, df: pd.DataFrame, metric: str, top_n: int) -> Dict[str, Any]:
        """Build a ranking of community areas by the given metric."""
        if metric == "population" and "total_population" in df.columns:
            sort_col = "total_population"
            label = "Total Population"
        elif metric == "income":
            # Use the top income bracket as a proxy
            sort_col = "_125_000" if "_125_000" in df.columns else "total_population"
            label = "Households Over $125k"
        elif metric == "race":
            sort_col = "total_population"
            label = "Total Population (use area_data for race breakdown)"
        elif metric == "age":
            sort_col = "total_population"
            label = "Total Population (use area_data for age breakdown)"
        else:
            sort_col = "total_population" if "total_population" in df.columns else None
            label = "Total Population"

        if sort_col is None or sort_col not in df.columns:
            return {"note": "No suitable ranking column found"}

        ranked = df.nlargest(top_n, sort_col)
        items = []
        name_col = "community_area_clean" if "community_area_clean" in df.columns else "community_area"
        for _, row in ranked.iterrows():
            items.append({
                "community_area": str(row.get(name_col, "?")),
                "value": self._safe_int(row.get(sort_col)),
            })
        return {"ranked_by": label, "top_n": top_n, "items": items}

    @staticmethod
    def _safe_int(val) -> Optional[int]:
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_demographics_result(self, result: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("📊 **Census Demographics (ACS 5-Year)**")
        lines.append(f"Survey Year: {result.get('acs_year', '?')}")
        lines.append(f"Metric: {result.get('metric', 'all')}")
        lines.append("")

        # Area-specific data
        if "area_data" in result:
            for area in result["area_data"]:
                lines.append(f"### {area.get('community_area', '?')}")
                if "total_population" in area and area["total_population"] is not None:
                    lines.append(f"  Population: {area['total_population']:,}")
                if "income_distribution" in area:
                    lines.append("  **Income Distribution (households):**")
                    for label, val in area["income_distribution"].items():
                        lines.append(f"    {label}: {val:,}" if val else f"    {label}: N/A")
                if "race_ethnicity" in area:
                    lines.append("  **Race/Ethnicity:**")
                    for label, val in area["race_ethnicity"].items():
                        lines.append(f"    {label}: {val:,}" if val else f"    {label}: N/A")
                if "age_gender" in area:
                    lines.append("  **Age/Gender:**")
                    for label, val in area["age_gender"].items():
                        lines.append(f"    {label}: {val:,}" if val else f"    {label}: N/A")
                lines.append("")

        # Ranking
        if "ranking" in result:
            ranking = result["ranking"]
            lines.append(f"**Ranking by {ranking.get('ranked_by', '?')} (Top {ranking.get('top_n', '?')}):**")
            for i, item in enumerate(ranking.get("items", []), 1):
                val = item.get("value")
                val_str = f"{val:,}" if val is not None else "N/A"
                lines.append(f"  {i}. {item['community_area']}: {val_str}")
            lines.append("")

        return "\n".join(lines)
