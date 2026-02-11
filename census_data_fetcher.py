#!/usr/bin/env python3
"""
Fetcher for ACS 5-Year Community Area census data from the Chicago Data Portal.

Dataset: ACS 5 Year Data by Community Area
Socrata ID: t68z-cikk
Portal: data.cityofchicago.org
Rows: ~77 per ACS year (one per community area)
"""

from base_fetcher import BaseSocrataFetcher


class CensusDataFetcher(BaseSocrataFetcher):
    """Fetch ACS 5-Year census/demographics data by community area."""

    DATASET_ID = "t68z-cikk"

    def __init__(
        self,
        cache_dir: str = "./data/cache",
        cache_expiry_hours: int = 168,  # 1 week — data updates ~annually
    ):
        super().__init__(
            dataset_id=self.DATASET_ID,
            base_domain="data.cityofchicago.org",
            cache_dir=cache_dir,
            cache_expiry_hours=cache_expiry_hours,
            cache_filename="census_acs_cache.csv",
        )

    # The dataset is small (~77 rows per year).  The default
    # BaseSocrataFetcher.fetch_all_data() already handles
    # JSON fetch + pagination + caching, so no overrides are needed.
