# Phase 4: Property / Real Estate Domain (Cook County Parcel Sales)

**Priority:** P1  
**Estimated effort:** Large  
**Status:** Not Started  
**Depends on:** Phase 1 (Foundation Refactor), Phase 2 (community area lookup table)

## Goal

Add Cook County Assessor Parcel Sales data as a domain, enabling questions about median home prices, sales volume, and property value trends by Chicago community area. This is the most complex new domain because the raw data is parcel-level and needs aggregation.

## Data Source

- **Dataset:** Assessor - Parcel Sales
- **Socrata ID:** `wvhk-k5uv`
- **Portal:** datacatalog.cookcountyil.gov (different Socrata domain than Chicago)
- **API endpoint:** `https://datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json`
- **Rows:** Very large (millions) — requires SoQL filtering to Chicago parcels only
- **Key columns:**
  - `pin` — 14-digit Parcel Index Number
  - `sale_price` — sale price in USD
  - `sale_date` — date of sale
  - `class` — property class code (2xx = residential)
  - `township_code` — used to filter to Chicago townships
  - `nbhd` — neighborhood code
- **Filtering strategy:** 
  - Filter to Chicago townships only (codes for Chicago proper)
  - Filter to residential classes (200-299)
  - Filter out likely non-arms-length transactions (< $10,000 already excluded)
  - Use `sale_filter_is_outlier = false` to exclude outliers

## Spatial Mapping Challenge

Parcel sales data uses PINs, not community areas. To map parcels to community areas:
- **Option A (recommended):** Pre-compute a PIN-prefix → community area mapping using the Assessor Parcel Universe dataset (`nj4t-kc8j`) which has coordinates, then spatial join
- **Option B (simpler):** Use the Parcel Universe's attached `chicago_community_area` or municipality fields if available
- **Option C (simplest MVP):** Fetch pre-aggregated data using SoQL `GROUP BY` on a joined field, or use ZIP code as a proxy and map ZIP → community area

For the MVP, use **Option C** — aggregate by year using SoQL, and use a ZIP-to-community-area mapping. Can be refined later.

## Tasks

### 4.1 Create `PropertyDataFetcher`

**File:** New `property_data_fetcher.py`

- Extends `BaseSocrataFetcher` with:
  - `base_domain = "datacatalog.cookcountyil.gov"` (not cityofchicago.org)
  - `dataset_id = "wvhk-k5uv"`
- Fetches with SoQL filters:
  ```
  $where=sale_price > 10000 AND class LIKE '2%' AND township_code IN ('70','71','72','73','74','75','76','77')
  $select=sale_date,sale_price,class,township_code,nbhd
  $limit=50000
  $order=sale_date DESC
  ```
- Longer cache (24 hours) since this data is large and doesn't change fast
- Cache as `data/cache/property_sales_cache.csv`

### 4.2 Create community area mapping

**File:** Extend `knowledge_base/community_areas.json`

- Add `zip_codes` field mapping each community area to its ZIP codes
- Add `township_codes` field if available
- This enables approximate mapping from property sales to community areas

### 4.3 Create `PropertyDataMCP`

**File:** New `property_mcp.py`

- Extends `BaseDataDomain`
- `domain_name = "property_sales"`
- `load_data()` — fetch via `PropertyDataFetcher`, aggregate to community area level
- `_aggregate_to_community_area()` — compute per-area statistics:
  - Median sale price
  - Mean sale price
  - Number of sales
  - Price percentiles (25th, 75th)
  - Year-over-year change
- Query method: `query_property_values(community_area, year, metric, compare_areas, top_n, property_type)`
  - `community_area` — name or number
  - `year` — filter by sale year
  - `metric` — "median_price", "mean_price", "sales_volume", "price_trend", "all"
  - `compare_areas` — comparison list
  - `top_n` — ranking
  - `property_type` — "single_family", "condo", "multi_family", "all" (based on class codes)

### 4.4 Create MCP tool schema

- Tool name: `query_property_values`
- Parameters:
  - `community_area` (string): Community area name or number
  - `year` (integer): Filter by sale year (default: latest full year)
  - `metric` (string): "median_price", "mean_price", "sales_volume", "price_trend", "all"
  - `compare_areas` (array of strings): For comparison
  - `top_n` (integer): For rankings
  - `property_type` (string): "single_family", "condo", "multi_family", "all"

### 4.5 Add schema documentation

**File:** New `knowledge_base/property_sales_schema.md`

- Document the aggregation methodology
- Note limitations (ZIP-to-community-area mapping is approximate)
- Explain property class codes (2xx residential subcategories)

## Acceptance Criteria

- [ ] `PropertyDataFetcher` fetches Chicago residential sales from Cook County Socrata
- [ ] Sales are aggregated to community area level with median/mean prices
- [ ] Tool auto-registered via domain registry
- [ ] Questions like "What's the median home price in Lincoln Park?" work
- [ ] Ranking queries work ("Which area has the highest home prices?")
- [ ] Year filtering works for trend questions
- [ ] Unit tests with fixture data

## Notes

- This domain has the longest data fetch time — good caching is critical
- The ZIP-to-community-area mapping is approximate; document this limitation
- Cook County Socrata may have different rate limits than Chicago's portal
- Consider a fallback: if API is slow/unavailable, ship a pre-aggregated CSV in `knowledge_base/`

## Files Changed

- `property_data_fetcher.py` (new)
- `property_mcp.py` (new)
- `knowledge_base/property_sales_schema.md` (new)
- `knowledge_base/community_areas.json` (modified — add ZIP mapping)
- `mcp_integration.py` (modified — register property domain)
- `tests/test_property_mcp.py` (new)
- `tests/fixtures/mini_property_sales.csv` (new)
