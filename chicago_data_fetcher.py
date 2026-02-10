#!/usr/bin/env python3
"""
Chicago Homicide Data API Fetcher

Fetches homicide data from Chicago's open data API with pagination support.
Handles large datasets by automatically managing API limits and offsets.
"""

import requests
import pandas as pd
from typing import Dict, Any, Optional
from pathlib import Path
from io import StringIO

from base_fetcher import BaseSocrataFetcher


class ChicagoHomicideDataFetcher(BaseSocrataFetcher):
    """Fetches and caches Chicago homicide data from the city's open data API.
    
    Extends BaseSocrataFetcher but overrides fetch methods to use the
    special v3 CSV export endpoint (faster for this large dataset).
    """

    # The crimes dataset on the Chicago portal
    CRIMES_DATASET_ID = "ijzp-q8t2"
    # Special CSV export view for homicides
    CSV_VIEW_ID = "iyvd-p5ga"

    def __init__(self, cache_dir: str = "./data/cache"):
        super().__init__(
            dataset_id=self.CRIMES_DATASET_ID,
            base_domain="data.cityofchicago.org",
            cache_dir=cache_dir,
            cache_expiry_hours=6,
            cache_filename="homicides_cache.csv",
        )
        # CSV export endpoint (faster for bulk fetches)
        self.csv_url = f"https://data.cityofchicago.org/api/v3/views/{self.CSV_VIEW_ID}/query.csv"
        # Keep legacy attribute for backward compat
        self.base_url = self.csv_url

    # ------------------------------------------------------------------
    # Override: use the CSV endpoint for batched fetching
    # ------------------------------------------------------------------

    def get_total_record_count(self) -> int:
        """Get the total number of records available via API."""
        try:
            count_url = f"https://data.cityofchicago.org/resource/{self.CRIMES_DATASET_ID}.json?$select=count(*)"
            response = requests.get(count_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:
                return int(data[0].get("count", 0))
        except Exception as e:
            print(f"⚠️  Could not get record count: {e}")
        return 15000  # Conservative fallback

    def fetch_batch(self, offset: int, limit: int) -> pd.DataFrame:
        """Fetch a batch of records from the CSV API."""
        params = {"$offset": offset, "$limit": min(limit, self.max_limit)}
        try:
            print(f"  📥 Fetching records {offset:,} to {offset + limit:,}...")
            response = requests.get(self.csv_url, params=params, timeout=60)
            response.raise_for_status()
            if response.text.strip():
                df = pd.read_csv(StringIO(response.text))
                print(f"  ✅ Retrieved {len(df):,} records")
                return df
            print(f"  ⚠️  Empty response for offset {offset}")
            return pd.DataFrame()
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error fetching batch at offset {offset}: {e}")
            raise
        except pd.errors.EmptyDataError:
            print(f"  ⚠️  No more data available at offset {offset}")
            return pd.DataFrame()

    def fetch_all_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """Fetch all homicide data using the CSV endpoint with pagination."""
        if not force_refresh and self.is_cache_valid():
            print("📋 Using cached data (still fresh)")
            return self.load_from_cache()

        print("🌐 Fetching fresh data from Chicago Open Data API...")
        total_records = self.get_total_record_count()
        print(f"📊 Estimated total records: {total_records:,}")

        all_dataframes = []
        offset = 0
        batch_count = 0
        import time

        while True:
            try:
                batch_df = self.fetch_batch(offset, self.batch_size)
                if batch_df.empty:
                    print("  🏁 No more records available")
                    break
                all_dataframes.append(batch_df)
                batch_count += 1
                offset += len(batch_df)
                if len(batch_df) < self.batch_size:
                    print("  🏁 Reached end of dataset")
                    break
                time.sleep(0.5)
                if batch_count > 100:
                    print("  ⚠️  Reached batch limit, stopping")
                    break
            except Exception as e:
                print(f"❌ Error during batch fetch: {e}")
                if all_dataframes:
                    print("🔄 Using partial data fetched so far...")
                    break
                raise

        if not all_dataframes:
            raise ValueError("No data could be fetched from the API")

        print(f"🔗 Combining {len(all_dataframes)} batches...")
        combined_df = pd.concat(all_dataframes, ignore_index=True)

        initial_count = len(combined_df)
        combined_df = combined_df.drop_duplicates()
        final_count = len(combined_df)
        if initial_count != final_count:
            print(f"🧹 Removed {initial_count - final_count:,} duplicate records")

        print(f"✅ Successfully fetched {final_count:,} total records")
        self.save_to_cache(combined_df)
        return combined_df

def main():
    """Test the data fetcher."""
    fetcher = ChicagoHomicideDataFetcher()
    
    # Show cache info
    cache_info = fetcher.get_cache_info()
    print(f"📋 Cache info: {cache_info}")
    
    # Fetch data
    try:
        df = fetcher.fetch_all_data()
        print(f"\n📊 Data summary:")
        print(f"  Records: {len(df):,}")
        print(f"  Columns: {len(df.columns)}")
        print(f"  Date range: {df['Date'].min()} to {df['Date'].max()}")
        print(f"  Sample columns: {list(df.columns[:5])}")
        
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")

if __name__ == "__main__":
    main()
