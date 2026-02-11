"""Central registry for system prompt variants used by LlamaClient.

Supports multi-domain tool calling (homicides, census, socioeconomic,
property sales) with iterative multi-tool orchestration — the LLM can
request up to 4 sequential tool calls before synthesizing a final answer.
"""

from typing import Any, Dict, List, Optional
import json

PROMPT_VARIANTS: Dict[str, Dict[str, Any]] = {
    "tool_use_v1": {
        "template": (
            "You are a multi-domain data analyst for Chicago.\n"
            "You have access to tools covering homicides, census demographics, "
            "socioeconomic indicators, and property sales.\n"
            "Use the provided tools to ground your answers in factual statistics.\n\n"
            "Available tools:\n"
            "{tool_summaries}\n\n"
            "Guidelines for tool usage:\n"
            "{guidelines}\n\n"
            "When a tool is required respond ONLY with a JSON object prefixed by 'TOOL_CALL:' on the same line.\n"
            "Format: TOOL_CALL: {{\"name\": \"tool_name\", \"arguments\": {{...}}}}\n\n"
            "{prior_results_section}"
            "Examples:\n"
            "{examples}\n\n"
            "If no more tools are needed, answer the question directly using any data already provided."
        ),
        "guidelines": [
            "You can call tools iteratively — after each tool result you will be prompted again. Call another tool if more data is needed to fully answer the question.",
            "Use `query_homicides_advanced` for homicide counts, trends, rankings, or filtered views.",
            "Use `get_iucr_info` for IUCR code explanations or taxonomy questions.",
            "Use `query_census_demographics` for population, income, race, or age data for community areas.",
            "Use `query_socioeconomic` for poverty rates, unemployment, crowded housing, dependency, or hardship indices.",
            "Use `query_property_values` for home prices, sales volume, and property value trends (township-level data).",
            "For cross-domain questions (e.g., 'homicide rate per capita'), call multiple tools in sequence: first homicides, then census for population, then synthesize.",
            "Do NOT repeat a tool call with the same arguments — the data is already available in the prior results.",
            "Always include `start_year`/`end_year` when a user references a specific year for homicide queries.",
            "For 'which/what had the most' style questions set `group_by` to ward, district, community_area, or location as appropriate.",
            "Supply integers for numeric parameters and `true`/`false` for booleans.",
            "When you have enough data to answer, respond with your analysis — do NOT call another tool."
        ],
        "examples": [
            {
                "question": "How many homicides in 2023?",
                "tool": "query_homicides_advanced",
                "arguments": {"start_year": 2023, "end_year": 2023}
            },
            {
                "question": "What is the population of Austin?",
                "tool": "query_census_demographics",
                "arguments": {"community_area": "Austin", "metric": "population"}
            },
            {
                "question": "Which areas have the highest hardship index?",
                "tool": "query_socioeconomic",
                "arguments": {"metric": "hardship", "top_n": 5}
            },
            {
                "question": "What are average home prices in Lincoln Park?",
                "tool": "query_property_values",
                "arguments": {"community_area": "Lincoln Park", "metric": "avg_price"}
            }
        ]
    },
    "tool_use_reasoned": {
        "template": (
            "You are an expert multi-domain data analyst for Chicago.\n"
            "You have access to tools covering homicides, census demographics, "
            "socioeconomic indicators, and property sales.\n"
            "Before selecting a tool, briefly reflect on the user's goal and required parameters.\n"
            "Keep the reflection concise (one sentence) then respond with the tool call if needed.\n\n"
            "Available tools:\n"
            "{tool_summaries}\n\n"
            "Reasoning and tool usage rules:\n"
            "{guidelines}\n\n"
            "When a tool is required respond ONLY with a JSON object prefixed by 'TOOL_CALL:' on the same line.\n"
            "Format: TOOL_CALL: {{\"name\": \"tool_name\", \"arguments\": {{...}}}}\n\n"
            "{prior_results_section}"
            "Examples:\n"
            "{examples}\n\n"
            "If no more tools are needed, answer the question directly using any data already provided."
        ),
        "guidelines": [
            "You can call tools iteratively — after each tool result you will be prompted again. Call another tool only if you still need more data.",
            "State the reasoning for the chosen tool before the TOOL_CALL: line.",
            "Map user questions about homicide counts or rankings to `query_homicides_advanced`.",
            "Map demographics/population questions to `query_census_demographics`.",
            "Map poverty/hardship/socioeconomic questions to `query_socioeconomic`.",
            "Map home price/property value questions to `query_property_values`.",
            "For cross-domain questions, call one tool at a time — you will get the result and can call another.",
            "Do NOT repeat a tool call with identical arguments.",
            "After executing tool(s), synthesize a clear answer by combining all results.",
            "Use `group_by` whenever the user asks for \"which\" entity had the most or for top-N rankings."
        ],
        "examples": [
            {
                "reasoning": "Need filtered homicide stats for 2023.",
                "tool": "query_homicides_advanced",
                "arguments": {"start_year": 2023, "end_year": 2023}
            },
            {
                "reasoning": "Need population to compute per-capita rate.",
                "tool": "query_census_demographics",
                "arguments": {"community_area": "Austin", "metric": "population"}
            },
            {
                "reasoning": "User wants socioeconomic hardship ranking.",
                "tool": "query_socioeconomic",
                "arguments": {"metric": "hardship", "top_n": 5}
            },
            {
                "reasoning": "User asks about property values in area.",
                "tool": "query_property_values",
                "arguments": {"community_area": "Lincoln Park", "metric": "avg_price"}
            }
        ]
    }
}


def _summarize_tool(tool: Dict[str, Any]) -> str:
    name = tool.get("name", "unknown_tool")
    description = tool.get("description", "")
    params = tool.get("parameters", {}) or {}
    required = set(tool.get("required", []) or [])

    if not params:
        return f"- {name}: {description}"

    param_summaries = []
    for param_name, param_info in params.items():
        hint = param_info.get("description", "")
        if param_name in required:
            hint = f"{hint} (required)" if hint else "required"
        param_summaries.append(f"{param_name}: {hint}".strip())

    params_text = "; ".join(param_summaries)
    return f"- {name}: {description}\n  Parameters: {params_text}"


def _format_examples(examples: List[Any]) -> List[str]:
    formatted: List[str] = []
    for example in examples:
        if isinstance(example, str):
            formatted.append(example)
            continue

        if not isinstance(example, dict):
            continue

        call_payload = json.dumps(
            {
                "name": example.get("tool"),
                "arguments": example.get("arguments", {})
            },
            ensure_ascii=False
        )

        if "reasoning" in example:
            formatted.append(f"- Reasoning: \"{example['reasoning']}\"\n  TOOL_CALL: {call_payload}")
        else:
            formatted.append(f"- Question: \"{example.get('question', 'Unknown question')}\"\n  TOOL_CALL: {call_payload}")
    return formatted


def build_tool_system_prompt(
    variant: str,
    tools: List[Dict[str, Any]],
    prior_tool_results: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Build a system prompt for tool usage based on a registered variant.

    Parameters
    ----------
    variant : str
        Name of the prompt variant (e.g. ``"tool_use_reasoned"``).
    tools : list[dict]
        Tool definition dicts (name, description, parameters…).
    prior_tool_results : list[dict] | None
        Results from previous tool calls in this orchestration loop.
        Each dict has ``tool_name`` and ``formatted_result`` keys.
    """
    variant_config = PROMPT_VARIANTS.get(variant, PROMPT_VARIANTS["tool_use_v1"])

    tool_lines = [_summarize_tool(tool) for tool in tools] if tools else ["- No tools available"]
    tool_section = "\n".join(tool_lines)

    guidelines = [str(rule) for rule in variant_config.get("guidelines", [])]
    guidelines_section = "\n".join(f"- {rule}" for rule in guidelines) if guidelines else "- Follow standard best practices."

    example_entries = variant_config.get("examples", [])
    example_lines = _format_examples(example_entries)
    examples_section = "\n".join(example_lines) if example_lines else "(No examples configured)"

    # Build prior results section (multi-tool loop context)
    prior_results_section = ""
    if prior_tool_results:
        parts = ["You have already called the following tools and received these results:\n"]
        for idx, pr in enumerate(prior_tool_results, 1):
            parts.append(f"--- Tool Call {idx}: {pr['tool_name']} ---")
            parts.append(pr["formatted_result"])
            parts.append("")
        parts.append(
            "If you need additional data from a DIFFERENT tool, emit another TOOL_CALL.\n"
            "If you have enough data to answer, respond directly — do NOT emit TOOL_CALL.\n\n"
        )
        prior_results_section = "\n".join(parts)

    template = variant_config.get("template", PROMPT_VARIANTS["tool_use_v1"]["template"])
    return template.format(
        tool_summaries=tool_section,
        guidelines=guidelines_section,
        examples=examples_section,
        prior_results_section=prior_results_section,
    )
