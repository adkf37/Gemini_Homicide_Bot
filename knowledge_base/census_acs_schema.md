# Census ACS 5-Year Data — Schema

**Dataset:** ACS 5 Year Data by Community Area  
**Socrata ID:** `t68z-cikk`  
**Portal:** data.cityofchicago.org  
**Updated:** ~annually (latest: 2023 ACS release, Feb 2025)  
**Rows:** ~77 per ACS year (one per community area)

## Columns

| Column | Type | Description |
|--------|------|-------------|
| `acs_year` | string/int | ACS survey year (e.g., "2023") |
| `community_area` | string | Community area name, UPPER CASE (e.g., "ALBANY PARK") |
| `record_id` | string | Compound key: `{year}_{area_name}` |

### Income Distribution (household counts)

| Column | Description |
|--------|-------------|
| `under_25_000` | Households earning < $25,000 |
| `_25_000_to_49_999` | Households earning $25k–$50k |
| `_50_000_to_74_999` | Households earning $50k–$75k |
| `_75_000_to_125_000` | Households earning $75k–$125k |
| `_125_000` | Households earning > $125,000 |

### Age / Gender (population counts)

| Column | Description |
|--------|-------------|
| `male_0_to_17` | Males age 0–17 |
| `male_18_to_24` | Males age 18–24 |
| `male_25_to_34` | Males age 25–34 |
| `male_35_to_49` | Males age 35–49 |
| `male_50_to_64` | Males age 50–64 |
| `male_65` | Males age 65+ |
| `female_0_to_17` | Females age 0–17 |
| `female_18_to_24` | Females age 18–24 |
| `female_25_to_34` | Females age 25–34 |
| `female_35_to_49` | Females age 35–49 |
| `female_50_to_64` | Females age 50–64 |
| `female_65` | Females age 65+ |

### Race / Ethnicity (population counts)

| Column | Description |
|--------|-------------|
| `total_population` | Total population of community area |
| `white` | White (all ethnicities) |
| `black_or_african_american` | Black or African American |
| `american_indian_or_alaska` | American Indian / Alaska Native |
| `asian` | Asian |
| `native_hawaiin_or_pacific` | Native Hawaiian / Pacific Islander |
| `other_race` | Other race |
| `multiracial` | Two or more races |
| `hispanic_or_latino` | Hispanic or Latino (any race) |
| `white_not_hispanic_or_latino` | White, non-Hispanic |

## Notes

- **ACS is an estimate**, not a full census. Margins of error apply especially to smaller community areas.
- Race/ethnicity categories are not mutually exclusive: Hispanic/Latino overlaps with racial categories.
- `total_population` equals the sum of age/gender columns.
- Community area names are in UPPER CASE in the raw data — normalised to Title Case in the MCP domain.
- The universal join key across domains is the **community area number** (1–77). This dataset has names only; the number↔name mapping is in `community_areas.json`.
