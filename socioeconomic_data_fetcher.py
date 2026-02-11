#!/usr/bin/env python3
"""
Fetcher for Census Socioeconomic Indicators from the Chicago Data Portal.

Dataset: Census Data — Selected socioeconomic indicators in Chicago, 2008-2012
Socrata ID: kn9c-c2s2
Portal: data.cityofchicago.org
Rows: 78 (77 community areas + Chicago total)
"""

from base_fetcher import BaseSocrataFetcher


class SocioeconomicDataFetcher(BaseSocrataFetcher):
    """Fetch socioeconomic indicator data by community area."""

    DATASET_ID = "kn9c-c2s2"

    def __init__(
        self,
        cache_dir: str = "./data/cache",
        cache_expiry_hours: int = 720,  # 30 days — this is a static dataset
    ):
        super().__init__(
            dataset_id=self.DATASET_ID,
            base_domain="data.cityofchicago.org",
            cache_dir=cache_dir,
            cache_expiry_hours=cache_expiry_hours,
            cache_filename="socioeconomic_cache.csv",
        )

    # 78 rows total — single fetch, no pagination needed.
    # BaseSocrataFetcher defaults handle everything.
