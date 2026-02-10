# Phase 5: Multi-Tool Orchestration Loop

**Priority:** P0  
**Estimated effort:** Medium-Large  
**Status:** Not Started  
**Depends on:** Phase 1 (Foundation), at least one new domain from Phase 2/3/4

## Goal

Enable the LLM to call multiple tools in sequence within a single conversation turn, then synthesize a unified answer from all results. This is required for cross-domain queries like: *"Which community area had the highest homicide rate per capita last year, and what are the median income and home price there?"*

Currently, `handle_question_with_tools()` supports exactly ONE tool call. This phase adds a loop.

## Design

### Orchestration Flow

```
User Question
    │
    ▼
LLM Pass 1: "Which tools do I need?"
    │
    ├── TOOL_CALL: query_homicides_advanced {...}
    │       → execute → result_1
    │
    ▼
LLM Pass 2: "I got homicide data. Do I need more tools?"
    │       (include result_1 in context)
    │
    ├── TOOL_CALL: query_census_demographics {...}
    │       → execute → result_2
    │
    ▼
LLM Pass 3: "I got census data. Do I need more tools?"
    │       (include result_1 + result_2 in context)
    │
    ├── NO_MORE_TOOLS (or TOOL_CALL for a 3rd)
    │
    ▼
LLM Final Pass: "Synthesize all results into a coherent answer"
    │
    ▼
Final Answer (cross-domain, fused)
```

### Key Design Decisions

1. **Max tool calls per question:** 4 (configurable, prevents infinite loops)
2. **LLM decides when to stop:** After each tool result, the LLM can either call another tool or signal it has enough data
3. **Result accumulation:** All prior tool results are included in the context for each subsequent LLM pass
4. **Stop signal:** LLM responds without `TOOL_CALL:` prefix → synthesize final answer
5. **Timeout:** Total orchestration timeout of 60 seconds to prevent runaway chains

## Tasks

### 5.1 Modify `handle_question_with_tools()` to support a loop

**File:** Modify `intelligent_mcp.py`

- Replace single tool-call pattern with a loop:
  ```python
  max_tool_calls = 4
  tool_results = []
  
  for iteration in range(max_tool_calls):
      response = llm.generate_with_tools(question, tools, prior_results=tool_results)
      
      if not response.get("needs_tool_call"):
          break  # LLM has enough data, proceed to synthesis
      
      tool_call = self.parse_tool_call(response["content"])
      result = self.execute_tool_call(tool_call)
      tool_results.append({
          "tool_name": tool_call["name"],
          "arguments": tool_call.get("arguments", {}),
          "result": result["formatted_result"]
      })
  ```
- After the loop, send all accumulated results to the LLM for final synthesis
- Track the full interaction trace for debugging

### 5.2 Update `generate_with_tools()` to accept prior results

**File:** Modify `llama_client.py`

- Add `prior_tool_results` parameter to `generate_with_tools()`
- When prior results exist, append them to the prompt:
  ```
  You have already called the following tools and received these results:
  
  Tool 1: query_homicides_advanced({...})
  Result: [formatted result]
  
  Tool 2: query_census_demographics({...})
  Result: [formatted result]
  
  Based on these results and the original question, decide if you need to call another tool or if you have enough information to answer.
  ```

### 5.3 Update the synthesis prompt

**File:** Modify `intelligent_mcp.py`

- The follow-up prompt for final synthesis should handle multiple results:
  ```
  Based on the following data from multiple sources:
  
  [Source 1: Homicide Data]
  {result_1}
  
  [Source 2: Census Demographics]
  {result_2}
  
  [Source 3: Property Values]
  {result_3}
  
  Please answer the original question: "{question}"
  
  Provide a clear, coherent answer that integrates information from all data sources. Note any caveats about data freshness or methodology differences.
  ```

### 5.4 Update prompt registry for multi-tool awareness

**File:** Modify `prompt_registry.py`

- Update system prompt variants to instruct the LLM about multi-tool calling:
  - "You can call multiple tools in sequence to gather data from different domains"
  - "After each tool result, decide if you need more data before answering"
  - "When you have enough data, respond with your analysis (no TOOL_CALL)"
- Add examples of multi-tool sequences in the prompt

### 5.5 Add guardrails

- **Dedup:** Don't allow the same tool with identical arguments twice
- **Budget:** Track total API latency; abort if approaching timeout
- **Fallback:** If a tool fails, continue with available results rather than aborting entirely
- **Token budget:** Trim earlier tool results if the accumulated context exceeds the context window

## Acceptance Criteria

- [ ] LLM can call 2-4 tools per question when needed
- [ ] Single-tool questions still work (backward compatible)
- [ ] Cross-domain question triggers multiple tool calls and fused answer
- [ ] Maximum tool call limit prevents infinite loops
- [ ] Interaction trace captures all tool calls and results
- [ ] Web API response includes all tool calls in trace
- [ ] Timeout prevents runaway orchestration

## Test Cases

1. **Single-domain (regression):** "How many homicides in 2023?" → 1 tool call, same as before
2. **Cross-domain:** "What's the per capita income in the community area with the most homicides?" → 2 tool calls (homicides + socioeconomic)
3. **Triple-domain:** "Which area had the most homicides, what's the poverty rate there, and what are home prices like?" → 3 tool calls
4. **No tools needed:** "What is the MCP framework?" → 0 tool calls, direct LLM answer
5. **Max limit:** Adversarial prompt trying to trigger 10 tool calls → capped at 4

## Files Changed

- `intelligent_mcp.py` (modified — orchestration loop)
- `llama_client.py` (modified — prior results support)
- `prompt_registry.py` (modified — multi-tool instructions)
- `config.yaml` (modified — add `max_tool_calls` setting)
