#!/usr/bin/env python3
"""
Property / Real Estate Domain (Cook County Assessor Parcel Sales)

Provides MCP tools for querying residential property sale statistics
(average price, sales volume, trends) across Chicago.  Data is aggregated
at the township level (8 townships covering all 77 community areas), so
per-community-area figures are approximate.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional

from base_domain import BaseDataDomain
from property_data_fetcher import PropertyDataFetcher


def _load_community_area_lookup() -> Dict:
    path = Path("knowledge_base/community_areas.json")
    if not path.exists():
        return {"areas": {}, "aliases": {}, "townships": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class PropertyDataMCP(BaseDataDomain):
    """MCP domain for Chicago residential property sales."""

    def __init__(self, cache_dir: str = "./data/cache"):
        self.fetcher = PropertyDataFetcher(cache_dir=cache_dir)
        self.df: Optional[pd.DataFrame] = None
        self._ca_lookup = _load_community_area_lookup()

        # Build reverse map: community area number → township code
        self._ca_to_township: Dict[int, str] = {}
        for twn_code, info in self._ca_lookup.get("townships", {}).items():
            if twn_code.startswith("_"):
                continue
            for ca_num in info.get("community_areas", []):
                self._ca_to_township[ca_num] = twn_code

        # Name → number lookup
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
        return "property_sales"

    def load_data(self, **kwargs) -> bool:
        try:
            self.df = self.fetcher.fetch_all_data()
            if self.df is not None and not self.df.empty:
                print(f"  ✅ Property data loaded: {len(self.df)} aggregated rows")
                return True
            print("  ⚠️ Property data is empty")
            return False
        except Exception as e:
            print(f"  ⚠️ Property data load failed: {e}")
            return False

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "query_property_values",
                "description": (
                    "Query Chicago residential property sale statistics from Cook County "
                    "Assessor data. Returns average sale price, sales volume, and trends "
                    "by year and geographic area (township level, mapped to community areas). "
                    "Use for questions like: 'What are home prices in Lincoln Park?', "
                    "'Which area has the most expensive homes?', "
                    "'How have property values changed since 2020?'. "
                    "Note: prices are at township level (8 zones covering all 77 community areas)."
                ),
                "parameters": {
                    "community_area": {
                        "type": "string",
                        "description": "Community area name or number — returns data for the containing township",
                    },
                    "year": {
                        "type": "integer",
                        "description": "Filter by sale year (default: latest available)",
                    },
                    "metric": {
                        "type": "string",
                        "description": (
                            "'avg_price', 'sales_volume', 'price_trend', or 'all'. Default 'all'."
                        ),
                    },
                    "compare_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional community areas for comparison",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top results for ranking queries (default 8)",
                    },
                },
                "required": [],
            }
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "query_property_values":
            return self.query_property_values(
                community_area=arguments.get("community_area"),
                year=arguments.get("year"),
                metric=arguments.get("metric", "all"),
                compare_areas=arguments.get("compare_areas"),
                top_n=arguments.get("top_n", 8),
            )
        return {"error": f"Unknown property tool: {tool_name}"}

    def format_result(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"❌ Error: {result['error']}"
        try:
            return self._format_property_result(result)
        except Exception as e:
            return (
                f"📋 **Raw Property Result:** {json.dumps(result, indent=2)}\n\n"
                f"⚠️ Format error: {e}"
            )

    # ------------------------------------------------------------------
    # Community area → township resolution
    # ------------------------------------------------------------------

    def _resolve_to_township(self, value: str) -> Optional[str]:
        """Resolve a community area name/number to a township code string."""
        if value is None:
            return None
        val = str(value).strip()

        # Try as a number
        try:
            ca_num = int(val)
            return self._ca_to_township.get(ca_num)
        except ValueError:
            pass

        # Try by name/alias
        lower = val.lower()
        ca_num = self._name_to_num.get(lower)
        if ca_num is not None:
            return self._ca_to_township.get(ca_num)

        # Substring match
        for known_lower, known_num in self._name_to_num.items():
            if lower in known_lower or known_lower in lower:
                return self._ca_to_township.get(known_num)
        return None

    def _township_label(self, twn_code: str) -> str:
        info = self._ca_lookup.get("townships", {}).get(twn_code, {})
        name = info.get("name", f"Township {twn_code}")
        ca_nums = info.get("community_areas", [])
        areas_map = self._ca_lookup.get("areas", {})
        ca_names = [areas_map.get(str(n), str(n)) for n in ca_nums[:5]]
        suffix = f" (+{len(ca_nums) - 5} more)" if len(ca_nums) > 5 else ""
        return f"{name} (includes {', '.join(ca_names)}{suffix})"

    # ------------------------------------------------------------------
    # Core query
    # ------------------------------------------------------------------

    def query_property_values(
        self,
        community_area: Optional[str] = None,
        year: Optional[int] = None,
        metric: str = "all",
        compare_areas: Optional[List[str]] = None,
        top_n: int = 8,
    ) -> Dict[str, Any]:
        if self.df is None or self.df.empty:
            return {"error": "Property data not loaded"}

        df = self.df.copy()
        available_years = sorted(df["year"].dropna().unique())
        target_year = year if year and year in available_years else (
            int(available_years[-1]) if available_years else None
        )

        result: Dict[str, Any] = {
            "data_source": "Cook County Assessor Parcel Sales (residential, $10k+)",
            "granularity": "township (approximate community area mapping)",
            "available_years": [int(y) for y in available_years] if available_years else [],
        }

        # Resolve township(s)
        townships_to_query: List[str] = []
        resolved_labels: Dict[str, str] = {}
        for ca in ([community_area] if community_area else []) + (compare_areas or []):
            if ca:
                twn = self._resolve_to_township(ca)
                if twn and twn not in townships_to_query:
                    townships_to_query.append(twn)
                    resolved_labels[twn] = f"{ca} → {self._township_label(twn)}"

        if metric == "price_trend" or metric == "trend":
            result["trend"] = self._build_trend(df, townships_to_query or None)
            return result

        # Filter to target year for non-trend queries
        if target_year is not None:
            df = df[df["year"] == target_year]
        result["year"] = int(target_year) if target_year else "all"

        if townships_to_query:
            area_df = df[df["township_code"].isin(townships_to_query)]
            result["area_data"] = []
            for twn in townships_to_query:
                tdf = area_df[area_df["township_code"] == twn]
                if tdf.empty:
                    continue
                row = tdf.iloc[0]
                result["area_data"].append({
                    "township_code": twn,
                    "label": resolved_labels.get(twn, self._township_label(twn)),
                    "avg_price": self._safe_num(row.get("avg_price")),
                    "min_price": self._safe_num(row.get("min_price")),
                    "max_price": self._safe_num(row.get("max_price")),
                    "sales_count": self._safe_int(row.get("sales_count")),
                    "total_volume": self._safe_num(row.get("total_volume")),
                })
        else:
            # Ranking mode
            result["ranking"] = self._build_ranking(df, metric, top_n)

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_ranking(self, df: pd.DataFrame, metric: str, top_n: int) -> Dict[str, Any]:
        sort_col = "avg_price"
        label = "Average Sale Price"
        if metric == "sales_volume":
            sort_col = "sales_count"
            label = "Sales Count"
        elif metric in ("avg_price", "all"):
            sort_col = "avg_price"
            label = "Average Sale Price"

        if sort_col not in df.columns:
            return {"note": f"Column '{sort_col}' not found"}

        ranked = df.nlargest(min(top_n, len(df)), sort_col)
        items = []
        for _, row in ranked.iterrows():
            twn = str(row.get("township_code", "?"))
            items.append({
                "township_code": twn,
                "label": self._township_label(twn),
                "value": self._safe_num(row.get(sort_col)),
                "sales_count": self._safe_int(row.get("sales_count")),
            })
        return {"ranked_by": label, "top_n": top_n, "items": items}

    def _build_trend(self, df: pd.DataFrame, townships: Optional[List[str]] = None) -> Dict[str, Any]:
        """Year-over-year trend, optionally filtered to specific townships."""
        if townships:
            df = df[df["township_code"].isin(townships)]
        yearly = (
            df.groupby("year")
            .agg(avg_price=("avg_price", "mean"), total_sales=("sales_count", "sum"))
            .reset_index()
            .sort_values("year")
        )
        points = []
        for _, row in yearly.iterrows():
            points.append({
                "year": int(row["year"]),
                "avg_price": round(float(row["avg_price"])),
                "total_sales": int(row["total_sales"]),
            })
        return {"townships": townships or "all Chicago", "data_points": points}

    @staticmethod
    def _safe_num(val):
        try:
            f = float(val)
            return round(f) if f > 100 else round(f, 2)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(val) -> Optional[int]:
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_property_result(self, result: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("🏠 **Property Sales Data**")
        lines.append(f"Source: {result.get('data_source', '?')}")
        if "year" in result:
            lines.append(f"Year: {result['year']}")
        lines.append(f"Granularity: {result.get('granularity', '?')}")
        lines.append("")

        if "area_data" in result:
            for area in result["area_data"]:
                lines.append(f"### {area.get('label', '?')}")
                if area.get("avg_price") is not None:
                    lines.append(f"  Avg Sale Price: ${area['avg_price']:,}")
                if area.get("min_price") is not None:
                    lines.append(f"  Min Sale Price: ${area['min_price']:,}")
                if area.get("max_price") is not None:
                    lines.append(f"  Max Sale Price: ${area['max_price']:,}")
                if area.get("sales_count") is not None:
                    lines.append(f"  Sales Count: {area['sales_count']:,}")
                if area.get("total_volume") is not None:
                    lines.append(f"  Total Volume: ${area['total_volume']:,}")
                lines.append("")

        if "ranking" in result:
            ranking = result["ranking"]
            lines.append(f"**Ranking by {ranking.get('ranked_by', '?')} (Top {ranking.get('top_n', '?')}):**")
            for i, item in enumerate(ranking.get("items", []), 1):
                val = item.get("value")
                val_str = f"${val:,}" if val is not None else "N/A"
                cnt = item.get("sales_count")
                cnt_str = f" ({cnt:,} sales)" if cnt else ""
                lines.append(f"  {i}. {item.get('label', '?')}: {val_str}{cnt_str}")
            lines.append("")

        if "trend" in result:
            trend = result["trend"]
            lines.append(f"**Price Trend** (townships: {trend.get('townships', '?')}):")
            for pt in trend.get("data_points", []):
                lines.append(
                    f"  {pt['year']}: avg ${pt['avg_price']:,}  ({pt['total_sales']:,} sales)"
                )
            lines.append("")

        return "\n".join(lines)
