#!/usr/bin/env python3
"""
Cross-domain analysis tools for Chicago public data.

These operators join homicide records with census and socioeconomic domains so
the LLM receives deterministic rates, rankings, and period comparisons instead
of trying to calculate them from raw rows.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from base_domain import BaseDataDomain
from socioeconomic_mcp import METRIC_COLS, METRIC_LABELS


def _load_community_area_lookup() -> Dict[str, Any]:
    path = Path("knowledge_base/community_areas.json")
    if not path.exists():
        return {"areas": {}, "aliases": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class CrossDomainAnalysisMCP(BaseDataDomain):
    """MCP domain for deterministic joins across registered data domains."""

    def __init__(self, domains: Dict[str, BaseDataDomain]):
        self.domains = domains
        self._ca_lookup = _load_community_area_lookup()
        self._name_to_num = {
            str(name).strip().lower(): int(num)
            for num, name in self._ca_lookup.get("areas", {}).items()
        }
        for alias, num in self._ca_lookup.get("aliases", {}).items():
            self._name_to_num[str(alias).strip().lower()] = int(num)

    @property
    def domain_name(self) -> str:
        return "cross_domain_analysis"

    @property
    def df(self) -> Optional[pd.DataFrame]:
        homicide = self._domain("homicides")
        return getattr(homicide, "df", None)

    def load_data(self, **kwargs) -> bool:
        return self.df is not None and not self.df.empty

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "analyze_homicide_rates_by_community_area",
                "description": (
                    "Calculate homicide counts and homicide rates per 100,000 residents by Chicago "
                    "community area by joining homicide records to ACS census population. Use for "
                    "rate questions, per-capita comparisons, and 'which community area has the "
                    "highest homicide rate' questions."
                ),
                "parameters": {
                    "start_year": {"type": "integer", "description": "Start homicide year"},
                    "end_year": {"type": "integer", "description": "End homicide year"},
                    "domestic": {"type": "boolean", "description": "Filter to domestic or non-domestic cases"},
                    "top_n": {"type": "integer", "description": "Number of rows to return (default 10)"},
                    "sort_by": {
                        "type": "string",
                        "description": "'rate', 'count', or 'community_area' (default 'rate')",
                    },
                },
                "required": [],
            },
            {
                "name": "analyze_homicide_socioeconomic_context",
                "description": (
                    "Join homicide concentrations to socioeconomic indicators such as hardship, "
                    "poverty, unemployment, income, education, crowding, or dependency. Use for "
                    "questions like domestic homicide concentration relative to hardship index."
                ),
                "parameters": {
                    "start_year": {"type": "integer", "description": "Start homicide year"},
                    "end_year": {"type": "integer", "description": "End homicide year"},
                    "metric": {
                        "type": "string",
                        "description": (
                            "Socioeconomic metric: hardship, poverty, unemployment, income, "
                            "education, crowding, dependency (default hardship)"
                        ),
                    },
                    "domestic_only": {"type": "boolean", "description": "Only count domestic homicides"},
                    "top_n": {"type": "integer", "description": "Number of rows to return (default 10)"},
                    "sort_by": {
                        "type": "string",
                        "description": "'rate', 'count', 'domestic_share', or 'metric' (default rate)",
                    },
                },
                "required": [],
            },
            {
                "name": "compare_homicide_district_trends",
                "description": (
                    "Compare homicide counts by police district across two year periods. Use for "
                    "district trend comparisons, increases/decreases, and period-over-period change."
                ),
                "parameters": {
                    "period1_start": {"type": "integer", "description": "First period start year"},
                    "period1_end": {"type": "integer", "description": "First period end year"},
                    "period2_start": {"type": "integer", "description": "Second period start year"},
                    "period2_end": {"type": "integer", "description": "Second period end year"},
                    "top_n": {"type": "integer", "description": "Number of districts to return (default 10)"},
                    "sort_by": {
                        "type": "string",
                        "description": "'absolute_change', 'pct_change', or 'period2_count'",
                    },
                },
                "required": ["period1_start", "period1_end", "period2_start", "period2_end"],
            },
            {
                "name": "analyze_homicide_rate_population_change",
                "description": (
                    "Compare community-area homicide rate change against population change across "
                    "two periods. Requires census data for at least two ACS years."
                ),
                "parameters": {
                    "period1_start": {"type": "integer", "description": "First homicide period start year"},
                    "period1_end": {"type": "integer", "description": "First homicide period end year"},
                    "period2_start": {"type": "integer", "description": "Second homicide period start year"},
                    "period2_end": {"type": "integer", "description": "Second homicide period end year"},
                    "census_year1": {"type": "integer", "description": "Population year for the first period"},
                    "census_year2": {"type": "integer", "description": "Population year for the second period"},
                    "top_n": {"type": "integer", "description": "Number of community areas to return"},
                    "sort_by": {
                        "type": "string",
                        "description": "'rate_change', 'population_change', or 'count_change'",
                    },
                },
                "required": ["period1_start", "period1_end", "period2_start", "period2_end"],
            },
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "analyze_homicide_rates_by_community_area":
            return self.analyze_homicide_rates_by_community_area(
                start_year=arguments.get("start_year"),
                end_year=arguments.get("end_year"),
                domestic=arguments.get("domestic"),
                top_n=arguments.get("top_n", 10),
                sort_by=arguments.get("sort_by", "rate"),
            )
        if tool_name == "analyze_homicide_socioeconomic_context":
            return self.analyze_homicide_socioeconomic_context(
                start_year=arguments.get("start_year"),
                end_year=arguments.get("end_year"),
                metric=arguments.get("metric", "hardship"),
                domestic_only=arguments.get("domestic_only", False),
                top_n=arguments.get("top_n", 10),
                sort_by=arguments.get("sort_by", "rate"),
            )
        if tool_name == "compare_homicide_district_trends":
            return self.compare_homicide_district_trends(
                period1_start=arguments.get("period1_start"),
                period1_end=arguments.get("period1_end"),
                period2_start=arguments.get("period2_start"),
                period2_end=arguments.get("period2_end"),
                top_n=arguments.get("top_n", 10),
                sort_by=arguments.get("sort_by", "absolute_change"),
            )
        if tool_name == "analyze_homicide_rate_population_change":
            return self.analyze_homicide_rate_population_change(
                period1_start=arguments.get("period1_start"),
                period1_end=arguments.get("period1_end"),
                period2_start=arguments.get("period2_start"),
                period2_end=arguments.get("period2_end"),
                census_year1=arguments.get("census_year1"),
                census_year2=arguments.get("census_year2"),
                top_n=arguments.get("top_n", 10),
                sort_by=arguments.get("sort_by", "rate_change"),
            )
        return {"error": f"Unknown cross-domain tool: {tool_name}"}

    def format_result(self, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"Error: {result['error']}"
        kind = result.get("analysis")
        if kind == "homicide_rates_by_community_area":
            return self._format_rate_result(result)
        if kind == "homicide_socioeconomic_context":
            return self._format_socioeconomic_context(result)
        if kind == "homicide_district_trend_comparison":
            return self._format_district_trends(result)
        if kind == "homicide_rate_population_change":
            return self._format_population_change(result)
        return f"Result:\n```json\n{json.dumps(result, indent=2)}\n```"

    def analyze_homicide_rates_by_community_area(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        domestic: Optional[bool] = None,
        top_n: int = 10,
        sort_by: str = "rate",
    ) -> Dict[str, Any]:
        homicide_df = self._filtered_homicides(start_year, end_year, domestic=domestic)
        if isinstance(homicide_df, dict):
            return homicide_df

        population_df = self._population_by_community_area()
        if population_df.empty:
            return {"error": "Census population data is not available for rate calculations"}

        joined = self._community_homicide_counts(homicide_df).merge(
            population_df, on="community_area_number", how="left"
        )
        joined["homicide_rate_per_100k"] = joined.apply(
            lambda row: self._rate(row["homicide_count"], row["population"]), axis=1
        )
        rows = self._rank(joined, sort_by, top_n, {
            "rate": "homicide_rate_per_100k",
            "count": "homicide_count",
            "community_area": "community_area_number",
        })

        return {
            "analysis": "homicide_rates_by_community_area",
            "filters": self._filters(start_year, end_year, domestic),
            "population_year": self._latest_census_year(),
            "total_homicides": int(homicide_df.shape[0]),
            "sort_by": sort_by,
            "top_n": int(top_n),
            "rows": self._records(rows),
        }

    def analyze_homicide_socioeconomic_context(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        metric: str = "hardship",
        domestic_only: bool = False,
        top_n: int = 10,
        sort_by: str = "rate",
    ) -> Dict[str, Any]:
        homicide_df = self._filtered_homicides(
            start_year, end_year, domestic=True if domestic_only else None
        )
        if isinstance(homicide_df, dict):
            return homicide_df

        counts = self._community_homicide_counts(homicide_df)
        if not domestic_only:
            domestic_counts = self._community_homicide_counts(
                homicide_df[homicide_df["Domestic"] == True], count_col="domestic_homicide_count"
            )
            counts = counts.merge(domestic_counts, on=["community_area_number", "community_area"], how="left")
            counts["domestic_homicide_count"] = counts["domestic_homicide_count"].fillna(0).astype(int)
        else:
            counts["domestic_homicide_count"] = counts["homicide_count"]

        population_df = self._population_by_community_area()
        socioeconomic_df = self._socioeconomic_by_community_area(metric)
        if socioeconomic_df.empty:
            return {"error": f"Socioeconomic metric '{metric}' is not available"}

        joined = counts.merge(population_df, on="community_area_number", how="left")
        joined = joined.merge(socioeconomic_df, on="community_area_number", how="left")
        joined["homicide_rate_per_100k"] = joined.apply(
            lambda row: self._rate(row["homicide_count"], row.get("population")), axis=1
        )
        joined["domestic_share"] = joined.apply(
            lambda row: self._share(row.get("domestic_homicide_count"), row.get("homicide_count")), axis=1
        )

        rows = self._rank(joined, sort_by, top_n, {
            "rate": "homicide_rate_per_100k",
            "count": "homicide_count",
            "domestic_share": "domestic_share",
            "metric": "metric_value",
        })

        return {
            "analysis": "homicide_socioeconomic_context",
            "filters": self._filters(start_year, end_year, True if domestic_only else None),
            "metric": metric,
            "metric_label": METRIC_LABELS.get(metric, metric),
            "population_year": self._latest_census_year(),
            "socioeconomic_period": "2008-2012 ACS estimates",
            "domestic_only": bool(domestic_only),
            "sort_by": sort_by,
            "top_n": int(top_n),
            "rows": self._records(rows),
        }

    def compare_homicide_district_trends(
        self,
        period1_start: Optional[int],
        period1_end: Optional[int],
        period2_start: Optional[int],
        period2_end: Optional[int],
        top_n: int = 10,
        sort_by: str = "absolute_change",
    ) -> Dict[str, Any]:
        missing = [
            name for name, value in {
                "period1_start": period1_start,
                "period1_end": period1_end,
                "period2_start": period2_start,
                "period2_end": period2_end,
            }.items()
            if value is None
        ]
        if missing:
            return {"error": f"Missing required parameters: {', '.join(missing)}"}

        df1 = self._filtered_homicides(period1_start, period1_end)
        df2 = self._filtered_homicides(period2_start, period2_end)
        if isinstance(df1, dict):
            return df1
        if isinstance(df2, dict):
            return df2

        counts1 = self._district_counts(df1, "period1_count")
        counts2 = self._district_counts(df2, "period2_count")
        joined = counts1.merge(counts2, on="district", how="outer").fillna(0)
        joined["period1_count"] = joined["period1_count"].astype(int)
        joined["period2_count"] = joined["period2_count"].astype(int)
        joined["absolute_change"] = joined["period2_count"] - joined["period1_count"]
        joined["pct_change"] = joined.apply(
            lambda row: None if row["period1_count"] == 0 else round(
                (row["absolute_change"] / row["period1_count"]) * 100, 1
            ),
            axis=1,
        )
        rows = self._rank(joined, sort_by, top_n, {
            "absolute_change": "absolute_change",
            "pct_change": "pct_change",
            "period2_count": "period2_count",
        })

        return {
            "analysis": "homicide_district_trend_comparison",
            "period1": {"start_year": int(period1_start), "end_year": int(period1_end)},
            "period2": {"start_year": int(period2_start), "end_year": int(period2_end)},
            "sort_by": sort_by,
            "top_n": int(top_n),
            "rows": self._records(rows),
        }

    def analyze_homicide_rate_population_change(
        self,
        period1_start: Optional[int],
        period1_end: Optional[int],
        period2_start: Optional[int],
        period2_end: Optional[int],
        census_year1: Optional[int] = None,
        census_year2: Optional[int] = None,
        top_n: int = 10,
        sort_by: str = "rate_change",
    ) -> Dict[str, Any]:
        census = self._census_df()
        if census is None or census.empty or "acs_year" not in census.columns:
            return {"error": "Census data with ACS years is required for population change analysis"}

        available_years = sorted(int(y) for y in census["acs_year"].dropna().unique())
        if len(available_years) < 2 and (census_year1 is None or census_year2 is None):
            return {
                "error": (
                    "Population change analysis requires at least two ACS years. "
                    f"Available years: {available_years}"
                )
            }

        year1 = int(census_year1) if census_year1 else available_years[0]
        year2 = int(census_year2) if census_year2 else available_years[-1]
        pop1 = self._population_by_community_area(year1).rename(columns={"population": "population_period1"})
        pop2 = self._population_by_community_area(year2).rename(columns={"population": "population_period2"})
        if pop1.empty or pop2.empty:
            return {"error": f"Population data unavailable for ACS years {year1} and {year2}"}

        df1 = self._filtered_homicides(period1_start, period1_end)
        df2 = self._filtered_homicides(period2_start, period2_end)
        if isinstance(df1, dict):
            return df1
        if isinstance(df2, dict):
            return df2

        counts1 = self._community_homicide_counts(df1, "period1_homicide_count")
        counts2 = self._community_homicide_counts(df2, "period2_homicide_count")
        joined = counts1.merge(counts2, on=["community_area_number", "community_area"], how="outer")
        joined = joined.merge(pop1, on="community_area_number", how="left")
        joined = joined.merge(pop2, on="community_area_number", how="left")
        joined[["period1_homicide_count", "period2_homicide_count"]] = (
            joined[["period1_homicide_count", "period2_homicide_count"]].fillna(0).astype(int)
        )
        joined["period1_rate_per_100k"] = joined.apply(
            lambda row: self._rate(row["period1_homicide_count"], row.get("population_period1")), axis=1
        )
        joined["period2_rate_per_100k"] = joined.apply(
            lambda row: self._rate(row["period2_homicide_count"], row.get("population_period2")), axis=1
        )
        joined["rate_change"] = joined["period2_rate_per_100k"] - joined["period1_rate_per_100k"]
        joined["population_change"] = joined["population_period2"] - joined["population_period1"]
        joined["count_change"] = joined["period2_homicide_count"] - joined["period1_homicide_count"]
        rows = self._rank(joined, sort_by, top_n, {
            "rate_change": "rate_change",
            "population_change": "population_change",
            "count_change": "count_change",
        })

        return {
            "analysis": "homicide_rate_population_change",
            "period1": {"start_year": int(period1_start), "end_year": int(period1_end), "census_year": year1},
            "period2": {"start_year": int(period2_start), "end_year": int(period2_end), "census_year": year2},
            "sort_by": sort_by,
            "top_n": int(top_n),
            "rows": self._records(rows),
        }

    def _domain(self, name: str) -> Optional[BaseDataDomain]:
        return self.domains.get(name)

    def _homicide_df(self) -> Optional[pd.DataFrame]:
        domain = self._domain("homicides")
        return getattr(domain, "df", None)

    def _census_df(self) -> Optional[pd.DataFrame]:
        domain = self._domain("census_demographics")
        return getattr(domain, "df", None)

    def _socioeconomic_df(self) -> Optional[pd.DataFrame]:
        domain = self._domain("socioeconomic")
        return getattr(domain, "df", None)

    def _filtered_homicides(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        domestic: Optional[bool] = None,
    ) -> Any:
        df = self._homicide_df()
        if df is None or df.empty:
            return {"error": "Homicide data is not loaded"}
        if "Year" not in df.columns:
            return {"error": "Homicide data is missing the Year column"}

        filtered = df.copy()
        filtered["Year"] = pd.to_numeric(filtered["Year"], errors="coerce")
        if start_year is not None:
            filtered = filtered[filtered["Year"] >= int(start_year)]
        if end_year is not None:
            filtered = filtered[filtered["Year"] <= int(end_year)]
        if domestic is not None:
            filtered = filtered[filtered["Domestic"] == bool(domestic)]
        return filtered

    def _community_homicide_counts(
        self, df: pd.DataFrame, count_col: str = "homicide_count"
    ) -> pd.DataFrame:
        if df.empty or "Community Area" not in df.columns:
            return pd.DataFrame(columns=["community_area_number", "community_area", count_col])
        working = df.copy()
        working["community_area_number"] = pd.to_numeric(
            working["Community Area"], errors="coerce"
        ).astype("Int64")
        working = working.dropna(subset=["community_area_number"])
        counts = (
            working.groupby("community_area_number")
            .size()
            .reset_index(name=count_col)
        )
        counts["community_area_number"] = counts["community_area_number"].astype(int)
        counts["community_area"] = counts["community_area_number"].map(self._community_area_name)
        return counts

    def _district_counts(self, df: pd.DataFrame, count_col: str) -> pd.DataFrame:
        if df.empty or "District" not in df.columns:
            return pd.DataFrame(columns=["district", count_col])
        working = df.copy()
        working["district"] = pd.to_numeric(working["District"], errors="coerce").astype("Int64")
        working = working.dropna(subset=["district"])
        counts = working.groupby("district").size().reset_index(name=count_col)
        counts["district"] = counts["district"].astype(int)
        return counts

    def _population_by_community_area(self, year: Optional[int] = None) -> pd.DataFrame:
        df = self._census_df()
        if df is None or df.empty or "total_population" not in df.columns:
            return pd.DataFrame(columns=["community_area_number", "population"])

        working = df.copy()
        if "acs_year" in working.columns:
            working["acs_year"] = pd.to_numeric(working["acs_year"], errors="coerce")
            target_year = int(year) if year else self._latest_census_year()
            if target_year is not None:
                working = working[working["acs_year"] == target_year]

        working["community_area_number"] = working.apply(self._row_community_area_number, axis=1)
        working["population"] = pd.to_numeric(working["total_population"], errors="coerce")
        return working.dropna(subset=["community_area_number", "population"])[
            ["community_area_number", "population"]
        ].assign(community_area_number=lambda d: d["community_area_number"].astype(int))

    def _socioeconomic_by_community_area(self, metric: str) -> pd.DataFrame:
        df = self._socioeconomic_df()
        col = METRIC_COLS.get(metric)
        if df is None or df.empty or col not in df.columns:
            return pd.DataFrame(columns=["community_area_number", "metric_value"])

        working = df.copy()
        if "ca" in working.columns:
            working["community_area_number"] = pd.to_numeric(working["ca"], errors="coerce")
        else:
            working["community_area_number"] = working.apply(self._row_community_area_number, axis=1)
        working["metric_value"] = pd.to_numeric(working[col], errors="coerce")
        return working.dropna(subset=["community_area_number", "metric_value"])[
            ["community_area_number", "metric_value"]
        ].assign(community_area_number=lambda d: d["community_area_number"].astype(int))

    def _latest_census_year(self) -> Optional[int]:
        df = self._census_df()
        if df is None or df.empty or "acs_year" not in df.columns:
            return None
        years = pd.to_numeric(df["acs_year"], errors="coerce").dropna()
        return int(years.max()) if not years.empty else None

    def _row_community_area_number(self, row: pd.Series) -> Optional[int]:
        for col in ("community_area_number", "ca", "Community Area"):
            if col in row.index and pd.notna(row[col]):
                try:
                    return int(float(row[col]))
                except (TypeError, ValueError):
                    pass
        for col in ("community_area", "community_area_clean", "community_area_name"):
            if col in row.index and pd.notna(row[col]):
                num = self._name_to_num.get(str(row[col]).strip().lower())
                if num is not None:
                    return num
        return None

    def _community_area_name(self, number: int) -> str:
        return self._ca_lookup.get("areas", {}).get(str(int(number)), f"Community Area {int(number)}")

    @staticmethod
    def _rate(count: Any, population: Any) -> Optional[float]:
        try:
            pop = float(population)
            if pop <= 0:
                return None
            return round((float(count) / pop) * 100000, 2)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _share(part: Any, whole: Any) -> Optional[float]:
        try:
            denominator = float(whole)
            if denominator <= 0:
                return None
            return round((float(part) / denominator) * 100, 1)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _rank(
        df: pd.DataFrame,
        sort_by: str,
        top_n: int,
        sort_columns: Dict[str, str],
    ) -> pd.DataFrame:
        if df.empty:
            return df
        sort_col = sort_columns.get(sort_by, next(iter(sort_columns.values())))
        ascending = sort_by in {"community_area"}
        ranked = df.copy()
        if sort_col in ranked.columns:
            ranked = ranked.sort_values(sort_col, ascending=ascending, na_position="last")
        return ranked.head(max(int(top_n), 1))

    @staticmethod
    def _signed(value: Any) -> str:
        if value is None:
            return "N/A"
        try:
            return f"{float(value):+g}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _records(df: pd.DataFrame) -> List[Dict[str, Any]]:
        records = []
        clean = df.where(pd.notna(df), None)
        for record in clean.to_dict(orient="records"):
            normalized = {}
            for key, value in record.items():
                if hasattr(value, "item"):
                    value = value.item()
                normalized[key] = value
            records.append(normalized)
        return records

    @staticmethod
    def _filters(
        start_year: Optional[int],
        end_year: Optional[int],
        domestic: Optional[bool],
    ) -> Dict[str, Any]:
        return {
            "start_year": start_year,
            "end_year": end_year,
            "domestic": domestic,
        }

    @staticmethod
    def _format_rate_result(result: Dict[str, Any]) -> str:
        lines = [
            "Homicide rates by community area",
            f"Population year: {result.get('population_year')}",
            f"Total homicides in scope: {result.get('total_homicides')}",
            "",
        ]
        for i, row in enumerate(result.get("rows", []), 1):
            rate = row.get("homicide_rate_per_100k")
            rate_text = f"{rate} per 100,000" if rate is not None else "rate unavailable"
            lines.append(
                f"{i}. {row.get('community_area')} (CA {row.get('community_area_number')}): "
                f"{row.get('homicide_count')} homicides, {rate_text}, population {row.get('population')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_socioeconomic_context(result: Dict[str, Any]) -> str:
        lines = [
            "Homicides and socioeconomic context",
            f"Metric: {result.get('metric_label')}",
            f"Population year: {result.get('population_year')}",
            "",
        ]
        for i, row in enumerate(result.get("rows", []), 1):
            lines.append(
                f"{i}. {row.get('community_area')} (CA {row.get('community_area_number')}): "
                f"{row.get('homicide_count')} homicides, "
                f"{row.get('homicide_rate_per_100k')} per 100,000, "
                f"domestic share {row.get('domestic_share')}%, "
                f"{result.get('metric')}={row.get('metric_value')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_district_trends(result: Dict[str, Any]) -> str:
        p1 = result.get("period1", {})
        p2 = result.get("period2", {})
        lines = [
            "Homicide district trend comparison",
            f"Period 1: {p1.get('start_year')}-{p1.get('end_year')}",
            f"Period 2: {p2.get('start_year')}-{p2.get('end_year')}",
            "",
        ]
        for i, row in enumerate(result.get("rows", []), 1):
            lines.append(
                f"{i}. District {row.get('district')}: {row.get('period1_count')} -> "
                f"{row.get('period2_count')} ({CrossDomainAnalysisMCP._signed(row.get('absolute_change'))} change, "
                f"{row.get('pct_change')}%)"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_population_change(result: Dict[str, Any]) -> str:
        p1 = result.get("period1", {})
        p2 = result.get("period2", {})
        lines = [
            "Homicide rate versus population change",
            f"Period 1: {p1.get('start_year')}-{p1.get('end_year')} using ACS {p1.get('census_year')}",
            f"Period 2: {p2.get('start_year')}-{p2.get('end_year')} using ACS {p2.get('census_year')}",
            "",
        ]
        for i, row in enumerate(result.get("rows", []), 1):
            lines.append(
                f"{i}. {row.get('community_area')} (CA {row.get('community_area_number')}): "
                f"rate {row.get('period1_rate_per_100k')} -> {row.get('period2_rate_per_100k')} "
                f"({CrossDomainAnalysisMCP._signed(row.get('rate_change'))}), "
                f"population change {CrossDomainAnalysisMCP._signed(row.get('population_change'))}, "
                f"homicide count change {CrossDomainAnalysisMCP._signed(row.get('count_change'))}"
            )
        return "\n".join(lines)
