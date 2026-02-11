# Cook County Property Sales – Schema

**Source:** Cook County Assessor – Parcel Sales (SODA 2.0)
**Portal:** `datacatalog.cookcountyil.gov`
**Dataset ID:** `wvhk-k5uv`
**API Endpoint:** `https://datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json`

## Strategy

Rather than downloading millions of raw parcel sales, the fetcher uses
**SoQL server-side aggregation** to retrieve yearly summaries by township.

```
SELECT year, township_code,
       count(*) AS sales_count,
       avg(sale_price) AS avg_price,
       min(sale_price) AS min_price,
       max(sale_price) AS max_price,
       sum(sale_price) AS total_volume
WHERE sale_price > 10000
  AND class LIKE '2%'
  AND township_code IN ('70','71','72','73','74','75','76','77')
GROUP BY year, township_code
ORDER BY year DESC, township_code ASC
```

## Filters Applied

| Filter | Purpose |
|--------|---------|
| `sale_price > 10000` | Exclude nominal / non-arm's-length transfers |
| `class LIKE '2%'` | Residential properties only (Cook County class 2xx) |
| `township_code IN (...)` | Chicago-only townships (70–77) |

## Aggregated Columns (returned by API)

| Column | Type | Description |
|--------|------|-------------|
| year | text | Sale year |
| township_code | text | Cook County township code (70–77 for Chicago) |
| sales_count | number | Number of qualifying sales |
| avg_price | number | Mean sale price |
| min_price | number | Minimum sale price |
| max_price | number | Maximum sale price |
| total_volume | number | Sum of all sale prices |

## Township → Community Area Mapping

Township codes cover multiple community areas. The mapping is stored in
`knowledge_base/community_areas.json` under the `"townships"` key.

| Code | Name | # Community Areas |
|------|------|-------------------|
| 70 | South Chicago | 10 |
| 71 | Lake | 23 |
| 72 | West | 12 |
| 73 | North | 16 |
| 74 | Jefferson | 5 |
| 75 | Rogers Park | 5 |
| 76 | Lake View | 7 |
| 77 | Hyde Park | 1 |

## Notes

- Data granularity is **township level**, so community-area values are approximate.
- Property class `2xx` covers single-family, multi-family, and condominiums.
- The dataset covers 2000-present; most useful years are 2015+.
