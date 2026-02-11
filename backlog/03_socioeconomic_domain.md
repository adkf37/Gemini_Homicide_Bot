# Phase 3: Socioeconomic Indicators Domain

**Priority:** P1  
**Estimated effort:** Small-Medium  
**Status:** Complete ✅  
**Depends on:** Phase 1 (Foundation Refactor), Phase 2 (community area lookup table)

## Goal

Add the Census Socioeconomic Indicators dataset as a domain, enabling questions about per capita income, poverty rates, unemployment, education levels, and the hardship index by Chicago community area. This dataset is simpler but has unique metrics not in the ACS data.

## Data Source

- **Dataset:** Census Data - Selected socioeconomic indicators in Chicago, 2008–2012
- **Socrata ID:** `kn9c-c2s2`
- **Portal:** data.cityofchicago.org
- **API endpoint:** `https://data.cityofchicago.org/resource/kn9c-c2s2.json`
- **Updated:** September 2014 (static dataset, 2008-2012 ACS estimates)
- **Rows:** 78 (77 community areas + Chicago total)
- **Key columns:**
  - `ca` — community area number (string)
  - `community_area_name` — name (e.g., "Rogers Park")
  - `percent_of_housing_crowded` — % of occupied housing with >1 person per room
  - `percent_households_below_poverty` — % below federal poverty level
  - `percent_aged_16_unemployed` — unemployment rate (age 16+)
  - `percent_aged_25_without_high_school_diploma` — % without HS diploma (age 25+)
  - `percent_aged_under_18_or_over_64` — dependency ratio
  - `per_capita_income_` — per capita income (USD)
  - `hardship_index` — composite hardship index (1-100)

## Tasks

### 3.1 Create `SocioeconomicDataFetcher`

**File:** New `socioeconomic_data_fetcher.py`

- Extends `BaseSocrataFetcher` with dataset ID `kn9c-c2s2`
- Tiny dataset (78 rows) — single JSON fetch, long cache (data is static)
- Cache as `data/cache/socioeconomic_cache.csv`
- Set `cache_expiry_hours = 168` (1 week) since data doesn't change

### 3.2 Create `SocioeconomicDataMCP`

**File:** New `socioeconomic_mcp.py`

- Extends `BaseDataDomain`
- `domain_name = "socioeconomic"`
- `load_data()` — fetch, normalize columns, convert numeric types
- Query method: `query_socioeconomic(community_area, metric, compare_areas, top_n, sort_order)`
  - `community_area` — name or number
  - `metric` — one of: "income", "poverty", "unemployment", "education", "hardship", "crowding", "dependency", "all"
  - `compare_areas` — list for comparison
  - `top_n` — for ranking ("top 10 by hardship index")
  - `sort_order` — "highest" or "lowest" (default: "highest")

### 3.3 Create MCP tool schema

- Tool name: `query_socioeconomic`
- Parameters:
  - `community_area` (string): Community area name or number
  - `metric` (string): "income", "poverty", "unemployment", "education", "hardship", "crowding", "dependency", "all"
  - `compare_areas` (array of strings): Additional areas for comparison
  - `top_n` (integer): Limit for ranking results
  - `sort_order` (string): "highest" or "lowest"
- Description should clarify that this is 2008-2012 data, useful for relative comparisons between areas

### 3.4 Add schema documentation

**File:** New `knowledge_base/socioeconomic_schema.md`

## Acceptance Criteria

- [ ] `SocioeconomicDataFetcher` fetches and caches the 78-row dataset
- [ ] `SocioeconomicDataMCP` answers queries like "Which community area has the highest hardship index?"
- [ ] Auto-registered via domain registry
- [ ] Ranking queries work (top N by any metric)
- [ ] Comparison queries work (compare 2-5 areas)
- [ ] Unit tests with fixture data

## Files Changed

- `socioeconomic_data_fetcher.py` (new)
- `socioeconomic_mcp.py` (new)
- `knowledge_base/socioeconomic_schema.md` (new)
- `mcp_integration.py` (modified — register socioeconomic domain)
- `tests/test_socioeconomic_mcp.py` (new)
- `tests/fixtures/mini_socioeconomic.csv` (new)
