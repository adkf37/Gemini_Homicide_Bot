#!/usr/bin/env python3
"""Deterministic tests for cross-domain MCP operators."""

from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from cross_domain_mcp import CrossDomainAnalysisMCP
from homicide_mcp import HomicideDataMCP
from intelligent_mcp import IntelligentMCPHandler


def _fixture_path(name: str) -> str:
    return str(Path(__file__).parent / "fixtures" / name)


def _cross_domain_mcp() -> CrossDomainAnalysisMCP:
    homicide = HomicideDataMCP(csv_path=_fixture_path("mini_homicides.csv"), data_fetcher=None)
    census = SimpleNamespace(df=pd.read_csv(_fixture_path("mini_census.csv")))
    socioeconomic = SimpleNamespace(df=pd.read_csv(_fixture_path("mini_socioeconomic.csv")))
    return CrossDomainAnalysisMCP(
        {
            "homicides": homicide,
            "census_demographics": census,
            "socioeconomic": socioeconomic,
        }
    )


def test_homicide_rate_per_100k_by_community_area():
    cross_domain = _cross_domain_mcp()

    result = cross_domain.analyze_homicide_rates_by_community_area(
        start_year=2022,
        end_year=2022,
        top_n=3,
        sort_by="rate",
    )

    assert "error" not in result
    assert result["analysis"] == "homicide_rates_by_community_area"
    assert result["population_year"] == 2023
    assert result["rows"][0]["community_area"] == "Englewood"
    assert result["rows"][0]["homicide_rate_per_100k"] == 2.17


def test_domestic_homicide_context_joins_hardship_index():
    cross_domain = _cross_domain_mcp()

    result = cross_domain.analyze_homicide_socioeconomic_context(
        start_year=2022,
        end_year=2022,
        metric="hardship",
        top_n=5,
        sort_by="metric",
    )

    assert "error" not in result
    englewood = next(row for row in result["rows"] if row["community_area"] == "Englewood")
    assert englewood["metric_value"] == 97
    assert englewood["homicide_count"] == 1


def test_district_trend_comparison_is_deterministic():
    cross_domain = _cross_domain_mcp()

    result = cross_domain.compare_homicide_district_trends(
        period1_start=2020,
        period1_end=2021,
        period2_start=2022,
        period2_end=2023,
        top_n=1,
    )

    assert "error" not in result
    assert result["analysis"] == "homicide_district_trend_comparison"
    assert result["rows"][0]["district"] == 3
    assert result["rows"][0]["absolute_change"] == 2


def test_trace_finalizer_promotes_iteration_tool_usage():
    handler = IntelligentMCPHandler()
    trace = {
        "question": "Which district changed most?",
        "iterations": [
            {
                "iteration": 1,
                "needs_tool_call": True,
                "tool_call": {"name": "compare_homicide_district_trends", "arguments": {}},
                "tool_execution": {"raw_result": {"rows": []}, "latency_seconds": 0.25},
            }
        ],
        "final_answer": "District 3 changed most.",
    }

    finalized = handler._finalize_trace(trace)

    assert finalized["needs_tool_call"] is True
    assert finalized["tool_call"]["name"] == "compare_homicide_district_trends"
    assert finalized["tool_call_count"] == 1
    assert finalized["tools_used"] == ["compare_homicide_district_trends"]
