#!/usr/bin/env python3
"""
Socioeconomic Indicators Domain

Provides MCP tools for querying per-capita income, poverty, unemployment,
education, crowding, dependency ratio, and the composite hardship index
across Chicago's 77 community areas (2008-2012 ACS estimates).
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional

from base_domain import BaseDataDomain
from socioeconomic_data_fetcher import SocioeconomicDataFetcher


# ---------------------------------------------------------------------------
# Metric column mapping
# ---------------------------------------------------------------------------

METRIC_COLS: Dict[str, str] = {
    "income": "per_capita_income_",
    "poverty": "percent_households_below_poverty",
    "unemployment": "percent_aged_16_unemployed",
    "education": "percent_aged_25_without_high_school_diploma",
    "crowding": "percent_of_housing_crowded",
    "dependency": "percent_aged_under_18_or_over_64",
    "hardship": "hardship_index",
}

METRIC_LABELS: Dict[str, str] = {
    "income": "Per Capita Income ($)",
    "poverty": "% Households Below Poverty",
    "unemployment": "% Unemployed (16+)",
    "education": "% Without HS Diploma (25+)",
    "crowding": "% Housing Crowded",
    "dependency": "% Under 18 or Over 64",
    "hardship": "Hardship Index (1-100)",
}


def _load_community_area_lookup() -> Dict:
    path = Path("knowledge_base/community_areas.json")
    if not path.exists():
        return {"areas": {}, "aliases": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class SocioeconomicDataMCP(BaseDataDomain):
    """MCP domain for Chicago socioeconomic indicators."""

    def __init__(self, cache_dir: str = "./data/cache"):
        self.fetcher = SocioeconomicDataFetcher(cache_dir=cache_dir)
        self.df: Optional[pd.DataFrame] = None
        self._ca_lookup = _load_community_area_lookup()
        self._name_to_num: Dict[str, int] = {}
        for num_str, name in self._ca_lookup.get("areas", {}).items():
            self._name_to_num[name.lower()] = int(num_str)
        for alias, num in self._ca_lookup.get("aliases", {}).items():
            self._name_to_num[alias.lower()] = int(num)
        self.load_data()

    # ------------------------------------------------------------------
    # BaseDataDomain interface
    # ------------------------------------------------------------------

    @property
    def domain_name(self) -> str:
        return "socioeconomic"

    def load_data(self, **kwargs) -> bool:
        try:
            self.df = self.fetcher.fetch_all_data()
            if self.df is not None and not self.df.empty:
                self._prepare_dataframe()
                print(f"  ✅ Socioeconomic data loaded: {len(self.df)} rows")
                return True
            print("  ⚠️ Socioeconomic data is empty")
            return False
        except Exception as e:
            print(f"  ⚠️ Socioeconomic data load failed: {e}")
            return False

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "query_socioeconomic",
                "description": (
                    "Query socioeconomic indicators for Chicago community areas (2008-2012 ACS). "
                    "Returns per-capita income, poverty rate, unemployment, education levels, "
                    "housing crowding, dependency ratio, and the composite hardship index. "
                    "Use for questions like: 'Which area has the highest hardship index?', "
                    "'Compare poverty rates in Austin and Lincoln Park', "
                    "'Top 10 community areas by per capita income'."
                ),
                "parameters": {
                    "community_area": {
                        "type": "string",
                        "description": "Community area name or number (e.g., 'Englewood' or '68')",
                    },
                    "metric": {
                        "type": "string",
                        "description": (
                            "Indicator to query: 'income', 'poverty', 'unemployment', "
                            "'education', 'hardship', 'crowding', 'dependency', or 'all'. Default 'all'."
                        ),
                    },
                    "compare_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional community areas for side-by-side comparison",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top results for ranking queries (default 10)",
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "'highest' or 'lowest' — direction for ranking (default 'highest')",
                    },
                },
                "required": [],
            }
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "query_socioeconomic":
            return self.query_socioeconomic(
                community_area=arguments.get("community_area"),
                metric=arguments.get("metric", "all"),
                compare_areas=arguments.get("compare_areas"),
                top_n=arguments.get("top_n", 10),
                sort_order=arguments.get("sort_order", "highest"),
            )
        return {"error": f"Unknown socioeconomic tool: {tool_name}"}

    def format_result(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"❌ Error: {result['error']}"
        try:
            return self._format_socioeconomic_result(result)
        except Exception as e:
            return f"📋 **Raw Socioeconomic Result:** {json.dumps(result, indent=2)}\n\n⚠️ Format error: {e}"

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------

    def _prepare_dataframe(self):
        """Parse numeric columns and normalise names."""
        assert self.df is not None
        for col in METRIC_COLS.values():
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        if "ca" in self.df.columns:
            self.df["ca"] = pd.to_numeric(self.df["ca"], errors="coerce")

        # Standardise name
        if "community_area_name" in self.df.columns:
            self.df["community_area_clean"] = (
                self.df["community_area_name"].str.strip().str.title()
            )

        # Drop the "CHICAGO" total row for most analyses
        if "community_area_name" in self.df.columns:
            self.df = self.df[
                self.df["community_area_name"].str.upper() != "CHICAGO"
            ].copy()

    # ------------------------------------------------------------------
    # Community area resolution (shared logic with census domain)
    # ------------------------------------------------------------------

    def _resolve_community_area(self, value: str) -> Optional[str]:
        if value is None:
            return None
        val = str(value).strip()
        try:
            num = int(val)
            name = self._ca_lookup.get("areas", {}).get(str(num))
            if name:
                return name.title()
        except ValueError:
            pass
        lower = val.lower()
        num = self._name_to_num.get(lower)
        if num is not None:
            name = self._ca_lookup.get("areas", {}).get(str(num))
            if name:
                return name.title()
        for known_lower, known_num in self._name_to_num.items():
            if lower in known_lower or known_lower in lower:
                name = self._ca_lookup.get("areas", {}).get(str(known_num))
                if name:
                    return name.title()
        return val.title()

    # ------------------------------------------------------------------
    # Core query
    # ------------------------------------------------------------------

    def query_socioeconomic(
        self,
        community_area: Optional[str] = None,
        metric: str = "all",
        compare_areas: Optional[List[str]] = None,
        top_n: int = 10,
        sort_order: str = "highest",
    ) -> Dict[str, Any]:
        if self.df is None or self.df.empty:
            return {"error": "Socioeconomic data not loaded"}

        df = self.df.copy()
        result: Dict[str, Any] = {
            "data_period": "2008-2012 ACS estimates",
            "metric": metric,
            "total_areas": len(df),
        }

        # Resolve areas
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

        if areas_to_query:
            name_col = "community_area_clean"
            if name_col in df.columns:
                area_df = df[df[name_col].isin(areas_to_query)]
            else:
                area_df = df
            result["areas_queried"] = areas_to_query
            result["areas_found"] = len(area_df)
            result["area_data"] = self._extract_area_data(area_df, metric)
        else:
            result["ranking"] = self._build_ranking(df, metric, top_n, sort_order)

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_area_data(self, df: pd.DataFrame, metric: str) -> List[Dict[str, Any]]:
        rows = []
        for _, row in df.iterrows():
            entry: Dict[str, Any] = {
                "community_area": row.get("community_area_clean", row.get("community_area_name", "?")),
            }
            if metric == "all":
                for key, col in METRIC_COLS.items():
                    if col in row.index:
                        entry[METRIC_LABELS[key]] = self._safe_num(row[col])
            else:
                col = METRIC_COLS.get(metric)
                label = METRIC_LABELS.get(metric, metric)
                if col and col in row.index:
                    entry[label] = self._safe_num(row[col])
            rows.append(entry)
        return rows

    def _build_ranking(
        self, df: pd.DataFrame, metric: str, top_n: int, sort_order: str
    ) -> Dict[str, Any]:
        if metric == "all":
            metric = "hardship"  # default ranking for 'all'

        col = METRIC_COLS.get(metric)
        label = METRIC_LABELS.get(metric, metric)
        if col is None or col not in df.columns:
            return {"note": f"No column found for metric '{metric}'"}

        ascending = sort_order.lower() == "lowest"
        ranked = df.nsmallest(top_n, col) if ascending else df.nlargest(top_n, col)

        name_col = "community_area_clean" if "community_area_clean" in df.columns else "community_area_name"
        items = []
        for _, row in ranked.iterrows():
            items.append({
                "community_area": str(row.get(name_col, "?")),
                "value": self._safe_num(row.get(col)),
            })

        return {
            "ranked_by": label,
            "sort_order": sort_order,
            "top_n": top_n,
            "items": items,
        }

    @staticmethod
    def _safe_num(val):
        try:
            f = float(val)
            return int(f) if f == int(f) else round(f, 2)
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_socioeconomic_result(self, result: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("📊 **Socioeconomic Indicators**")
        lines.append(f"Data Period: {result.get('data_period', '?')}")
        lines.append(f"Metric: {result.get('metric', 'all')}")
        lines.append("")

        if "area_data" in result:
            for area in result["area_data"]:
                ca = area.pop("community_area", "?")
                lines.append(f"### {ca}")
                for label, val in area.items():
                    if val is not None:
                        if isinstance(val, int) and val > 999:
                            lines.append(f"  {label}: ${val:,}" if "Income" in label else f"  {label}: {val:,}")
                        elif isinstance(val, float):
                            lines.append(f"  {label}: {val}%")
                        else:
                            lines.append(f"  {label}: {val}")
                    else:
                        lines.append(f"  {label}: N/A")
                lines.append("")

        if "ranking" in result:
            ranking = result["ranking"]
            direction = "↑" if ranking.get("sort_order") == "highest" else "↓"
            lines.append(
                f"**Ranking by {ranking.get('ranked_by', '?')} {direction} "
                f"(Top {ranking.get('top_n', '?')}):**"
            )
            for i, item in enumerate(ranking.get("items", []), 1):
                val = item.get("value")
                if val is not None:
                    label_key = result.get("metric", "hardship")
                    if label_key == "income" and isinstance(val, (int, float)):
                        val_str = f"${val:,}"
                    elif isinstance(val, float):
                        val_str = f"{val}%"
                    elif isinstance(val, int) and val <= 100 and label_key != "income":
                        val_str = str(val)
                    else:
                        val_str = f"{val:,}" if isinstance(val, int) else str(val)
                else:
                    val_str = "N/A"
                lines.append(f"  {i}. {item['community_area']}: {val_str}")
            lines.append("")

        return "\n".join(lines)
