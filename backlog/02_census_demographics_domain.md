# Phase 2: Census / Demographics Domain (ACS 5-Year Data)

**Priority:** P1  
**Estimated effort:** Medium  
**Status:** Complete ✅  
**Depends on:** Phase 1 (Foundation Refactor)

## Goal

Add the ACS 5-Year Community Survey data as a new data domain, enabling questions about population, income distribution, race/ethnicity, and age demographics by Chicago community area.

## Data Source

- **Dataset:** ACS 5 Year Data by Community Area
- **Socrata ID:** `t68z-cikk`
- **Portal:** data.cityofchicago.org
- **API endpoint:** `https://data.cityofchicago.org/resource/t68z-cikk.json`
- **Updated:** February 2025 (2023 ACS release)
- **Rows:** ~77 (one per community area per year)
- **Key columns:**
  - `acs_year` — survey year
  - `community_area` — community area name (e.g., "ALBANY PARK")
  - Income brackets: `under_25_000`, `_25_000_to_49_999`, `_50_000_to_74_999`, `_75_000_to_125_000`, `_125_000`
  - Gender/Age: `male_0_to_17`, `male_18_to_24`, ..., `female_65`
  - Race: `white`, `black_or_african_american`, `asian`, `hispanic_or_latino`, `multiracial`, etc.
  - `total_population`
  - `white_not_hispanic_or_latino`

## Tasks

### 2.1 Create `CensusDataFetcher`

**File:** New `census_data_fetcher.py`

- Extends `BaseSocrataFetcher` with dataset ID `t68z-cikk`
- Small dataset (~77 rows per year) — simple JSON fetch, no pagination needed
- Cache as `data/cache/census_acs_cache.csv`
- Override `fetch_all_data()` for the simpler Socrata resource API pattern (`/resource/{id}.json?$limit=5000`)

### 2.2 Create `CensusDataMCP`

**File:** New `census_mcp.py`

- Extends `BaseDataDomain`
- `domain_name = "census_demographics"`
- `load_data()` — fetch via `CensusDataFetcher`, normalize columns
- `_prepare_dataframe()` — parse numeric columns, standardize community area names (Title Case to match homicide data)
- Query method: `query_demographics(community_area, year, metric, compare_areas, top_n)`
  - `community_area` — name or number (lookup table for name↔number mapping)
  - `year` — ACS year filter (default: latest)
  - `metric` — one of: "population", "income", "race", "age", "all"
  - `compare_areas` — list of community area names/numbers for comparison
  - `top_n` — for ranking queries ("top 5 by population")

### 2.3 Create MCP tool schema

- Tool name: `query_census_demographics`
- Parameters:
  - `community_area` (string): Community area name or number
  - `year` (integer): ACS survey year (default: latest available)
  - `metric` (string): Category to query — "population", "income_distribution", "race_ethnicity", "age_gender", "all"
  - `compare_areas` (array of strings): Additional areas for comparison
  - `top_n` (integer): Number of top results for ranking queries
- Tool definition for LLM prompt with description and examples

### 2.4 Add community area lookup table

**File:** New `knowledge_base/community_areas.json`

- Map of community area number ↔ name (1 = Rogers Park, 2 = West Ridge, ..., 77 = Edgewater)
- Shared across all domains that use community areas as a key
- Include aliases for common names (e.g., "The Loop" = community area 32)

### 2.5 Add schema documentation

**File:** New `knowledge_base/census_acs_schema.md`

- Document all columns, their types, and what they represent
- Note data limitations (ACS is an estimate, not a census)
- Example queries

## Acceptance Criteria

- [ ] `CensusDataFetcher` fetches and caches ACS data from Socrata
- [ ] `CensusDataMCP` loads data, answers queries by community area
- [ ] Tool is auto-registered in `MCPIntegration` via the domain registry
- [ ] LLM can call `query_census_demographics` for questions like "What's the population of Austin?"
- [ ] Community area name/number lookup works bidirectionally
- [ ] Unit tests with fixture data (subset of ACS rows)

## Files Changed

- `census_data_fetcher.py` (new)
- `census_mcp.py` (new)
- `knowledge_base/community_areas.json` (new)
- `knowledge_base/census_acs_schema.md` (new)
- `mcp_integration.py` (modified — register census domain)
- `tests/test_census_mcp.py` (new)
- `tests/fixtures/mini_census.csv` (new)
