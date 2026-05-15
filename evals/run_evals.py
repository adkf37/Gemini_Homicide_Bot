#!/usr/bin/env python3
"""Eval runner for the Gemini Homicide Bot.

Loads question cases from ``evals/homicide_qa.xml``, runs each prompt
through the live ``LocalLLMApp.ask_question_with_mcp`` pipeline (Gemini
+ MCP tools), and checks the answer text + tool-call trace against the
expected ``answer_contains`` / ``answer_regex`` and ``expected_tools``.

Output mirrors chicago-zoning-mcp/evals/eval_results_*.txt:

    PASS Q1 (1.2s): How many homicides happened in Chicago in 2023?
    FAIL Q3 (3.1s): How many homicides occurred in ward 10 in 2010?
      - missing expected text matching pattern: \\b\\d+\\b
      - missing expected tool: query_homicides_advanced

A summary appears at the bottom and the same content is written to
``evals/eval_results_<YYYYMMDD_HHMM>.txt``.

Usage:
    python evals/run_evals.py                  # run all cases
    python evals/run_evals.py --ids 1,2,14     # run a specific subset
    python evals/run_evals.py --limit 5        # stop after the first 5
    python evals/run_evals.py --xml evals/homicide_qa.xml --out evals/
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Ensure project root is importable when run as `python evals/run_evals.py`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Working directory is required to be the project root so relative paths
# in the data fetchers resolve (./data/cache/, ./knowledge_base/).
os.chdir(PROJECT_ROOT)


@dataclass
class EvalCase:
    """A single XML <question> case loaded from the suite."""

    id: str
    prompt: str
    tool: Optional[str] = None
    expected_tools: List[str] = field(default_factory=list)
    answer_exact: Optional[str] = None
    answer_contains: List[str] = field(default_factory=list)
    answer_regex: List[str] = field(default_factory=list)
    type: Optional[str] = None
    question_type: Optional[str] = None
    prompt_complexity: Optional[str] = None
    audience: Optional[str] = None
    data_source: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class EvalResult:
    case: EvalCase
    passed: bool
    elapsed_s: float
    failures: List[str] = field(default_factory=list)
    error: Optional[str] = None
    answer: str = ""
    tool_calls: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# XML loading
# ---------------------------------------------------------------------------

def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def load_cases(xml_path: Path) -> List[EvalCase]:
    """Parse the eval suite XML file into a list of EvalCase objects."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    cases: List[EvalCase] = []
    for q in root.findall("question"):
        prompt = (q.findtext("prompt") or "").strip()
        if not prompt:
            continue

        # `expected_tools` element overrides single `tool` attribute when present.
        expected_tools_text = q.findtext("expected_tools")
        expected = _split_csv(expected_tools_text)
        primary_tool = (q.attrib.get("tool") or "").strip() or None
        if not expected and primary_tool and primary_tool != "multi_step":
            expected = [primary_tool]

        answer_contains = [
            (el.text or "").strip()
            for el in q.findall("answer_contains")
            if (el.text or "").strip()
        ]
        answer_regex = [
            (el.text or "").strip()
            for el in q.findall("answer_regex")
            if (el.text or "").strip()
        ]
        answer_exact_el = q.find("answer")
        answer_exact = (
            (answer_exact_el.text or "").strip() if answer_exact_el is not None else None
        )

        cases.append(EvalCase(
            id=q.attrib.get("id", "?"),
            prompt=prompt,
            tool=primary_tool,
            expected_tools=expected,
            answer_exact=answer_exact,
            answer_contains=answer_contains,
            answer_regex=answer_regex,
            type=q.attrib.get("type"),
            question_type=q.attrib.get("question_type"),
            prompt_complexity=q.attrib.get("prompt_complexity"),
            audience=q.attrib.get("audience"),
            data_source=q.attrib.get("data_source"),
            notes=q.findtext("notes"),
        ))
    return cases


# ---------------------------------------------------------------------------
# Answer + tool checks
# ---------------------------------------------------------------------------

def _check_answer(case: EvalCase, answer: str) -> List[str]:
    """Return a list of failure messages (empty = pass)."""
    failures: List[str] = []
    if not answer:
        failures.append("empty answer from model")
        return failures

    lower_answer = answer.lower()

    if case.answer_exact:
        if case.answer_exact.lower() not in lower_answer:
            failures.append(f"missing exact answer: {case.answer_exact!r}")

    for needle in case.answer_contains:
        if needle.lower() not in lower_answer:
            failures.append(f"missing expected text: {needle!r}")

    for pattern in case.answer_regex:
        try:
            if not re.search(pattern, answer, re.IGNORECASE):
                failures.append(f"missing expected text matching pattern: {pattern}")
        except re.error as e:
            failures.append(f"bad regex {pattern!r}: {e}")

    return failures


def _check_tools(case: EvalCase, actual_tools: List[str]) -> List[str]:
    """Return failure messages for missing expected tool calls."""
    failures: List[str] = []
    if not case.expected_tools:
        return failures
    actual_set = {t for t in actual_tools if t}
    for tool in case.expected_tools:
        if tool not in actual_set:
            failures.append(f"missing expected tool: {tool}")
    return failures


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _extract_tool_names(trace: dict) -> List[str]:
    """Pull every tool name out of a LocalLLMApp interaction trace."""
    if not isinstance(trace, dict):
        return []
    names: List[str] = []
    for call in trace.get("tool_calls") or []:
        if isinstance(call, dict) and call.get("name"):
            names.append(call["name"])
    for execution in trace.get("tool_executions") or []:
        if isinstance(execution, dict):
            name = execution.get("name") or (execution.get("tool_call") or {}).get("name")
            if name and name not in names:
                names.append(name)
    if not names:
        single = trace.get("tool_call")
        if isinstance(single, dict) and single.get("name"):
            names.append(single["name"])
    return names


def run_case(app, case: EvalCase) -> EvalResult:
    """Run a single case through the LLM and return an EvalResult."""
    start = time.time()
    try:
        answer, trace = app.ask_question_with_mcp(case.prompt)
        elapsed = time.time() - start
        tool_calls = _extract_tool_names(trace or {})
        failures = _check_answer(case, answer or "") + _check_tools(case, tool_calls)
        return EvalResult(
            case=case,
            passed=not failures,
            elapsed_s=elapsed,
            failures=failures,
            answer=answer or "",
            tool_calls=tool_calls,
        )
    except Exception as e:
        elapsed = time.time() - start
        return EvalResult(
            case=case,
            passed=False,
            elapsed_s=elapsed,
            failures=[f"exception during execution: {e}"],
            error=traceback.format_exc(),
        )


def format_result_line(result: EvalResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    prefix = f"{status} Q{result.case.id} ({result.elapsed_s:.1f}s): {result.case.prompt}"
    if result.passed:
        return prefix
    lines = [prefix]
    for failure in result.failures:
        lines.append(f"  - {failure}")
    if result.tool_calls:
        lines.append(f"  - tools called: {', '.join(result.tool_calls)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Gemini Homicide Bot eval suite.")
    parser.add_argument("--xml", default="evals/homicide_qa.xml", help="Eval suite XML path")
    parser.add_argument("--out", default="evals", help="Directory to write the results file")
    parser.add_argument("--ids", default=None,
                        help="Comma-separated case IDs to run (default: all)")
    parser.add_argument("--limit", type=int, default=None, help="Stop after N cases")
    args = parser.parse_args()

    xml_path = Path(args.xml)
    if not xml_path.is_absolute():
        xml_path = PROJECT_ROOT / xml_path
    if not xml_path.exists():
        print(f"❌ Eval suite not found: {xml_path}", file=sys.stderr)
        return 2

    cases = load_cases(xml_path)
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",") if x.strip()}
        cases = [c for c in cases if c.id in wanted]
    if args.limit:
        cases = cases[: args.limit]

    if not cases:
        print("No eval cases to run.")
        return 0

    print(f"🚀 Loading LocalLLMApp (Gemini + MCP tools)…")
    # Imported lazily so --help works without spinning up the model.
    from main import LocalLLMApp  # noqa: WPS433

    app = LocalLLMApp()

    print(f"📋 Running {len(cases)} eval case(s) from {xml_path.name}")
    print("=" * 72)

    output_lines: List[str] = []
    results: List[EvalResult] = []
    for case in cases:
        result = run_case(app, case)
        results.append(result)
        line = format_result_line(result)
        print(line)
        output_lines.append(line)

    print("=" * 72)
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    summary = (
        f"Summary: {passed}/{len(results)} passed, {failed} failed"
        f" — total runtime {sum(r.elapsed_s for r in results):.1f}s"
    )
    print(summary)
    output_lines.append("")
    output_lines.append("=" * 72)
    output_lines.append(summary)

    # Write results file
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = PROJECT_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = out_dir / f"eval_results_{stamp}.txt"
    out_path.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"📝 Wrote results to {out_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
