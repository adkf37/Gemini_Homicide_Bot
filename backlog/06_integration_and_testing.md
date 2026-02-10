# Phase 6: Integration, Testing, and Documentation

**Priority:** P1  
**Estimated effort:** Medium  
**Status:** Not Started  
**Depends on:** All previous phases

## Goal

Wire everything together: update question routing to handle multi-domain keywords, update the web UI to display multi-tool results, add comprehensive tests, and update all documentation.

## Tasks

### 6.1 Update question routing in `main.py`

**File:** Modify `main.py`

- Replace the hardcoded `homicide_keywords` list with a broader approach:
  - **Option A (simple):** Expand keywords to include census/property terms ("population", "income", "property", "home price", "median price", "poverty", "unemployment", "demographics", "census", "hardship")
  - **Option B (better):** Route ALL questions through the tool-calling path and let the LLM decide whether tools are needed. The LLM already handles "no tool needed" gracefully.
- Recommended: **Option B** — remove keyword gating entirely, always use `ask_question_with_mcp()`. The LLM's system prompt already instructs it to only call tools when relevant. This is simpler and more extensible.

### 6.2 Update web UI for multi-domain results

**File:** Modify `web/web_app.py`, `web/templates/index.html`, `web/static/styles.css`

- The `/api/chat` response already returns `tool_name` and `tool_data` — extend for multi-tool:
  - Return `tools_used: [{name, arguments, result_summary}]` array instead of single `tool_name`
  - Return `domains_queried: ["homicides", "census", "property"]` for UI display
- In the web UI:
  - Show a "Sources" badge or section listing which data domains were consulted
  - Optional: collapsible sections for each tool's raw result
  - Update the chat message template to handle multi-source answers

### 6.3 Update `config.yaml`

**File:** Modify `config.yaml`

- Add new configuration sections:
  ```yaml
  domains:
    homicides:
      enabled: true
      dataset_id: "ijzp-q8t2"
      cache_hours: 6
    census:
      enabled: true
      dataset_id: "t68z-cikk"
      cache_hours: 168
    socioeconomic:
      enabled: true
      dataset_id: "kn9c-c2s2"
      cache_hours: 168
    property:
      enabled: true
      dataset_id: "wvhk-k5uv"
      cache_hours: 24
  
  orchestration:
    max_tool_calls: 4
    timeout_seconds: 60
  ```

### 6.4 Update `requirements.txt`

- Review and add any new dependencies (likely none — all domains use `requests` + `pandas` already)

### 6.5 Add comprehensive tests

**File:** New and modified test files

- `tests/test_census_mcp.py` — unit tests for census domain
- `tests/test_socioeconomic_mcp.py` — unit tests for socioeconomic domain
- `tests/test_property_mcp.py` — unit tests for property domain
- `tests/test_tool_registry.py` — test dynamic tool registration and dispatch
- `tests/test_multi_tool.py` — test orchestration loop with mocked LLM
- `tests/test_base_fetcher.py` — test shared fetcher logic
- Update `tests/test_homicide_mcp.py` if interface changed in Phase 1

### 6.6 Create test fixtures

- `tests/fixtures/mini_census.csv` — 5-10 community areas from ACS data
- `tests/fixtures/mini_socioeconomic.csv` — 5-10 community areas
- `tests/fixtures/mini_property_sales.csv` — ~50 sample sales records

### 6.7 Update documentation

**Files:** Modify `README.md`, `IMPROVEMENTS.md`

- Update README:
  - New "Data Domains" section describing all 4 domains
  - Update tool listing (4+ tools now)
  - Add cross-domain query examples
  - Update architecture diagram
- Update IMPROVEMENTS.md with what was delivered
- Update `knowledge_base/` schema docs

### 6.8 End-to-end validation

Manual testing checklist:
- [ ] CLI: Ask single-domain homicide question → works as before
- [ ] CLI: Ask census question → new domain responds
- [ ] CLI: Ask cross-domain question → multi-tool orchestration
- [ ] Web UI: All of the above through the browser
- [ ] Web UI: Sources/domains displayed correctly
- [ ] API: `/api/health` returns domain status
- [ ] Error handling: domain unavailable → graceful degradation in other domains
- [ ] Cache: domains cache independently with correct TTLs

## Acceptance Criteria

- [ ] All existing tests still pass
- [ ] New test suite has >80% coverage of new code
- [ ] Cross-domain query example from original request works end-to-end
- [ ] Web UI displays multi-source answers cleanly
- [ ] README accurately reflects new capabilities
- [ ] No regressions in homicide-only queries

## Files Changed

- `main.py` (modified — routing)
- `web/web_app.py` (modified — multi-tool response)
- `web/templates/index.html` (modified — source display)
- `web/static/styles.css` (modified — source badges)
- `config.yaml` (modified — domain configs)
- `README.md` (modified — documentation)
- `IMPROVEMENTS.md` (modified — changelog)
- `tests/` (multiple new and modified files)
