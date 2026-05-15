# Eval Suite

Inspired by [chicago-zoning-mcp/evals](https://github.com/adkf37/chicago-zoning-mcp/tree/main/evals).

## What's here

- **`homicide_qa.xml`** — 30 test cases covering homicide queries, census
  demographics, socioeconomic indicators, property values, multi-step /
  cross-domain orchestration, geographic-compatibility edge cases (the bug
  that motivated this suite: "how many homicides and people in ward 10 in
  2010?"), data-recency edge cases, and out-of-range inputs.
- **`run_evals.py`** — runs each `<question>` through the live
  `LocalLLMApp.ask_question_with_mcp` pipeline (Gemini + MCP tools), grades
  the answer against `<answer>` / `<answer_contains>` / `<answer_regex>`,
  and verifies the expected tools were called. Output mirrors the
  chicago-zoning-mcp result format.

## Running

From the project root:

```bash
# All 30 cases
python evals/run_evals.py

# Just the geographic-compatibility regression case
python evals/run_evals.py --ids 14

# Smoke-test the first 5
python evals/run_evals.py --limit 5
```

The Gemini API key must be available the same way the main app expects it
(see `gemini_secret.py` / environment variable).

Results are printed to stdout and saved to `evals/eval_results_<YYYYMMDD_HHMM>.txt`.

## Question schema

Each `<question>` may have:

| Attribute / element        | Purpose                                                        |
|----------------------------|----------------------------------------------------------------|
| `id`                       | Stable identifier (used by `--ids`)                            |
| `tool`                     | Primary expected tool name, or `multi_step`                    |
| `type`, `question_type`    | Classification metadata (factual / ranking / multi_step / …)   |
| `prompt_complexity`        | `simple` / `moderate` / `google_search` / `structured`         |
| `audience`                 | `general` / `homeowner` / `professional_developer`             |
| `data_source`              | Which dataset the question targets                             |
| `<prompt>`                 | The exact user prompt sent to the bot                          |
| `<answer>`                 | Single exact substring that must appear (case-insensitive)     |
| `<answer_contains>` (×N)   | Substrings that must appear                                    |
| `<answer_regex>` (×N)      | Regex patterns that must match                                 |
| `<expected_tools>`         | Comma-separated tool names expected to be called               |
| `<notes>`                  | Human-readable explanation (not used by the runner)            |

A case PASSES only if all `answer_*` checks succeed *and* every tool in
`expected_tools` was actually invoked.

## Adding new cases

Just append a new `<question>` element with a fresh `id`. Keep checks
loose enough that a slightly different phrasing of a correct answer still
passes (prefer `answer_regex` with character ranges over brittle exact
strings).
