# Socioeconomic Indicators — Schema

**Dataset:** Census Data — Selected socioeconomic indicators in Chicago, 2008–2012  
**Socrata ID:** `kn9c-c2s2`  
**Portal:** data.cityofchicago.org  
**Updated:** September 2014 (static dataset — 2008–2012 ACS estimates)  
**Rows:** 78 (77 community areas + 1 "CHICAGO" total row)

## Columns

| Column | Type | Description |
|--------|------|-------------|
| `ca` | string | Community area number (1–77) |
| `community_area_name` | string | Community area name (e.g., "Rogers Park") |
| `percent_of_housing_crowded` | float | % of occupied housing units with >1 person per room |
| `percent_households_below_poverty` | float | % of households below the federal poverty level |
| `percent_aged_16_unemployed` | float | Unemployment rate for population 16+ |
| `percent_aged_25_without_high_school_diploma` | float | % of people 25+ without a high school diploma |
| `percent_aged_under_18_or_over_64` | float | Dependency ratio — % of population under 18 or over 64 |
| `per_capita_income_` | integer | Per-capita income in USD |
| `hardship_index` | integer | Composite hardship index (1–100, higher = more hardship) |

## Hardship Index

The hardship index is a composite score (1–100) based on six variables:

1. Crowded housing
2. Poverty rate
3. Unemployment
4. Education (no HS diploma)
5. Dependency ratio
6. Per-capita income (inverse)

Higher values indicate greater socioeconomic hardship.

## Notes

- This is a **static 2008–2012 dataset**. It does not update. Use for relative comparisons between community areas, not absolute current figures.
- Row 78 is "CHICAGO" — the citywide total. This row is excluded from queries by default.
- The `ca` column is a string in the raw API; it's converted to int for joins.
- Community area names in this dataset are in Title Case (e.g., "Rogers Park"), unlike the ACS dataset which uses UPPER CASE.
- Join key to other domains: community area number (`ca`).
