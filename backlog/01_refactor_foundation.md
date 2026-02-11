# Phase 1: Refactor Foundation — Base Classes & Tool Registry

**Priority:** P0 (blocking all other phases)  
**Estimated effort:** Medium  
**Status:** Complete ✅

## Goal

Decouple the tightly-coupled, homicide-only architecture into an extensible plugin pattern so new data domains can be added without modifying the dispatch code. This phase touches no external data sources — it's purely a refactor of existing internals.

## Tasks

### 1.1 Extract `BaseSocrataFetcher` from `ChicagoHomicideDataFetcher`

**File:** New `base_fetcher.py`; modify `chicago_data_fetcher.py`

- Create an abstract base class `BaseSocrataFetcher` with:
  - `__init__(self, dataset_id, base_domain, cache_dir, cache_expiry_hours)` — configurable per dataset
  - `is_cache_valid()` — shared caching logic (already in homicide fetcher)
  - `fetch_batch(offset, limit)` — abstract or default Socrata CSV fetch
  - `fetch_all_data()` — shared pagination loop with dedup
  - `get_total_record_count()` — Socrata `$select=count(*)` pattern
  - `_load_cache()` / `_save_cache()` — shared file-based caching
- Refactor `ChicagoHomicideDataFetcher` to extend `BaseSocrataFetcher`, keeping only homicide-specific config (dataset ID `ijzp-q8t2`, view ID `iyvd-p5ga`)

### 1.2 Create `BaseDataDomain` abstract class

**File:** New `base_domain.py`

- Abstract base class `BaseDataDomain` with:
  - `domain_name: str` — e.g., "homicides", "census", "property"
  - `load_data() -> bool` — abstract, loads/caches DataFrame
  - `get_tools() -> List[mcp.Tool]` — returns MCP tool schemas for this domain
  - `get_tool_definitions() -> List[Dict]` — returns tool defs for the LLM prompt (name, description, parameters, required)
  - `call_tool(tool_name, arguments) -> Dict` — dispatch to the right query method
  - `format_result(result) -> str` — domain-specific result formatting
- Each domain registers itself with the tool registry on initialization

### 1.3 Refactor `HomicideDataMCP` to extend `BaseDataDomain`

**File:** Modify `homicide_mcp.py`

- Make `HomicideDataMCP` extend `BaseDataDomain`
- Implement `get_tool_definitions()` returning the existing 2 tool defs (currently hardcoded in `intelligent_mcp.py`)
- Implement `call_tool()` with internal dispatch to `query_homicides_advanced` / `get_iucr_info`
- Implement `format_result()` by moving formatting logic from `mcp_integration.py`
- All existing behavior preserved — this is a pure refactor

### 1.4 Build dynamic tool registry in `MCPIntegration`

**File:** Modify `mcp_integration.py`

- Replace hardcoded `self.homicide_data` member with `self.domains: Dict[str, BaseDataDomain]`
- Replace hardcoded `call_tool()` if/elif dispatch with:
  ```python
  def call_tool(self, tool_name, arguments):
      for domain in self.domains.values():
          tool_names = [t["name"] for t in domain.get_tool_definitions()]
          if tool_name in tool_names:
              return domain.call_tool(tool_name, arguments)
      return {"error": f"Unknown tool: {tool_name}"}
  ```
- Replace hardcoded `format_tool_result()` with delegation to the owning domain's `format_result()`
- Add `register_domain(domain: BaseDataDomain)` method
- `initialize_mcp_tools()` registers the homicide domain (and later, census/property domains)

### 1.5 Make `IntelligentMCPHandler.tools` dynamic

**File:** Modify `intelligent_mcp.py`

- Remove the hardcoded `self.tools` list from `__init__`
- Instead, `get_tools()` collects tool definitions from all registered domains via `mcp_integration`
- The follow-up prompt in `handle_question_with_tools()` should no longer say "about homicides" — make it generic: "Based on this data:"

## Acceptance Criteria

- [ ] All existing tests pass (`pytest tests/`)
- [ ] `HomicideDataMCP` extends `BaseDataDomain`
- [ ] `ChicagoHomicideDataFetcher` extends `BaseSocrataFetcher`
- [ ] `MCPIntegration.call_tool()` uses registry dispatch, not if/elif
- [ ] `IntelligentMCPHandler.tools` is built dynamically from registered domains
- [ ] No change in user-visible behavior — same questions, same answers

## Dependencies

None — this is the foundation phase.

## Files Changed

- `base_fetcher.py` (new)
- `base_domain.py` (new)
- `chicago_data_fetcher.py` (modified)
- `homicide_mcp.py` (modified)
- `mcp_integration.py` (modified)
- `intelligent_mcp.py` (modified)
