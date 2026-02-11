#!/usr/bin/env python3
"""
Fetcher for Cook County Assessor Parcel Sales (Chicago residential).

Dataset: Assessor — Parcel Sales
Socrata ID: wvhk-k5uv
Portal: datacatalog.cookcountyil.gov
Strategy: SoQL server-side aggregation by township_code + year so
          we transfer ~80 rows instead of millions.
"""

import requests
import pandas as pd
from pathlib import Path
from typing import Optional

from base_fetcher import BaseSocrataFetcher


class PropertyDataFetcher(BaseSocrataFetcher):
    """Fetch aggregated Chicago residential property sales data."""

    DATASET_ID = "wvhk-k5uv"
    # Chicago's 8 townships
    CHICAGO_TOWNSHIPS = ("70", "71", "72", "73", "74", "75", "76", "77")

    def __init__(
        self,
        cache_dir: str = "./data/cache",
        cache_expiry_hours: int = 24,
    ):
        super().__init__(
            dataset_id=self.DATASET_ID,
            base_domain="datacatalog.cookcountyil.gov",
            cache_dir=cache_dir,
            cache_expiry_hours=cache_expiry_hours,
            cache_filename="property_sales_cache.csv",
        )

    # ------------------------------------------------------------------
    # Override: use SoQL aggregation instead of raw row download
    # ------------------------------------------------------------------

    def fetch_all_data(self) -> Optional[pd.DataFrame]:
        """Fetch aggregated property sales grouped by township + year."""
        # Check cache first
        if self.is_cache_valid():
            print("📦 Using cached property sales data")
            return self.load_from_cache()

        print(f"🌐 Fetching aggregated property data from {self.base_domain}...")
        twn_list = ",".join(f"'{t}'" for t in self.CHICAGO_TOWNSHIPS)
        where_clause = (
            f"sale_price > 10000 AND class LIKE '2%' "
            f"AND township_code IN ({twn_list})"
        )
        params = {
            "$select": (
                "year, township_code, "
                "count(*) as sales_count, "
                "avg(sale_price) as avg_price, "
                "min(sale_price) as min_price, "
                "max(sale_price) as max_price, "
                "sum(sale_price) as total_volume"
            ),
            "$where": where_clause,
            "$group": "year, township_code",
            "$order": "year DESC, township_code",
            "$limit": 500,
        }
        url = self.get_resource_url()
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or not data:
                print("  ⚠️ No property data returned")
                return None
            df = pd.DataFrame(data)
            # Convert types
            for col in ("year", "sales_count"):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            for col in ("avg_price", "min_price", "max_price", "total_volume"):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            print(f"  ✅ Retrieved {len(df)} aggregated rows")
            self.save_to_cache(df)
            return df
        except Exception as e:
            print(f"  ⚠️ Property data fetch failed: {e}")
            cached = self.load_from_cache()
            if cached is not None:
                print("  📦 Falling back to stale cache")
            return cached
