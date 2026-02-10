#!/usr/bin/env python3
"""
Base Socrata Data Fetcher

Abstract base class for fetching and caching data from Socrata open-data portals.
Subclass for each dataset/domain (homicides, census, property, etc.).
"""

import requests
import pandas as pd
import time
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import os


class BaseSocrataFetcher(ABC):
    """Base class for Socrata open-data API fetchers with caching."""

    def __init__(
        self,
        dataset_id: str,
        base_domain: str = "data.cityofchicago.org",
        cache_dir: str = "./data/cache",
        cache_expiry_hours: int = 6,
        cache_filename: Optional[str] = None,
    ):
        self.dataset_id = dataset_id
        self.base_domain = base_domain
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Pagination defaults (subclasses may override)
        self.batch_size = 10000
        self.max_limit = 50000

        # Cache settings
        self.cache_expiry_hours = cache_expiry_hours
        fname = cache_filename or f"{dataset_id.replace('-', '_')}_cache.csv"
        self.cache_file = self.cache_dir / fname
        self.metadata_file = self.cache_dir / f"{Path(fname).stem}_metadata.json"

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    def is_cache_valid(self) -> bool:
        """Check if cached data is still valid (not expired)."""
        if not self.cache_file.exists() or not self.metadata_file.exists():
            return False
        try:
            with open(self.metadata_file, "r") as f:
                metadata = json.load(f)
            cached_time = datetime.fromisoformat(metadata.get("fetched_at", "1970-01-01"))
            expiry_time = cached_time + timedelta(hours=self.cache_expiry_hours)
            return datetime.now() < expiry_time
        except Exception as e:
            print(f"⚠️  Error checking cache validity: {e}")
            return False

    def save_to_cache(self, df: pd.DataFrame) -> None:
        """Save DataFrame to cache with metadata."""
        try:
            df.to_csv(self.cache_file, index=False)
            metadata = {
                "fetched_at": datetime.now().isoformat(),
                "record_count": len(df),
                "columns": list(df.columns),
                "data_source": f"Socrata {self.base_domain}",
                "dataset_id": self.dataset_id,
            }
            with open(self.metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
            print(f"💾 Data cached to: {self.cache_file}")
        except Exception as e:
            print(f"⚠️  Could not cache data: {e}")

    def load_from_cache(self) -> pd.DataFrame:
        """Load data from cache."""
        try:
            df = pd.read_csv(self.cache_file)
            with open(self.metadata_file, "r") as f:
                metadata = json.load(f)
            cached_time = datetime.fromisoformat(metadata.get("fetched_at", "1970-01-01"))
            age_hours = (datetime.now() - cached_time).total_seconds() / 3600
            print(f"📋 Loaded {len(df):,} records from cache (age: {age_hours:.1f} hours)")
            return df
        except Exception as e:
            print(f"❌ Error loading cache: {e}")
            raise

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached data."""
        if not self.metadata_file.exists():
            return {"cached": False}
        try:
            with open(self.metadata_file, "r") as f:
                metadata = json.load(f)
            cached_time = datetime.fromisoformat(metadata.get("fetched_at", "1970-01-01"))
            age_hours = (datetime.now() - cached_time).total_seconds() / 3600
            return {
                "cached": True,
                "fetched_at": metadata.get("fetched_at"),
                "age_hours": round(age_hours, 1),
                "record_count": metadata.get("record_count", 0),
                "is_valid": self.is_cache_valid(),
                "cache_file": str(self.cache_file),
                "expires_in_hours": max(0, self.cache_expiry_hours - age_hours),
            }
        except Exception as e:
            return {"cached": False, "error": str(e)}

    def clear_cache(self) -> None:
        """Clear cached data."""
        try:
            if self.cache_file.exists():
                os.remove(self.cache_file)
                print(f"🗑️  Removed cache file: {self.cache_file}")
            if self.metadata_file.exists():
                os.remove(self.metadata_file)
                print(f"🗑️  Removed metadata file: {self.metadata_file}")
        except Exception as e:
            print(f"⚠️  Error clearing cache: {e}")

    # ------------------------------------------------------------------
    # Fetching — subclasses may override for non-standard endpoints
    # ------------------------------------------------------------------

    def get_resource_url(self) -> str:
        """Return the Socrata resource JSON API endpoint."""
        return f"https://{self.base_domain}/resource/{self.dataset_id}.json"

    def get_total_record_count(self) -> int:
        """Get the total number of records available via API."""
        try:
            url = f"{self.get_resource_url()}?$select=count(*)"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:
                return int(data[0].get("count", 0))
        except Exception as e:
            print(f"⚠️  Could not get record count: {e}")
        return 0

    def fetch_json_batch(self, offset: int, limit: int, extra_params: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """Fetch a batch of records from the Socrata JSON resource API."""
        params: Dict[str, Any] = {"$offset": offset, "$limit": min(limit, self.max_limit)}
        if extra_params:
            params.update(extra_params)
        try:
            print(f"  📥 Fetching records {offset:,} to {offset + limit:,}...")
            response = requests.get(self.get_resource_url(), params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                print(f"  ✅ Retrieved {len(df):,} records")
                return df
            print(f"  ⚠️  Empty response for offset {offset}")
            return pd.DataFrame()
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error fetching batch at offset {offset}: {e}")
            raise

    def fetch_all_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """Fetch all data with pagination and caching."""
        if not force_refresh and self.is_cache_valid():
            print("📋 Using cached data (still fresh)")
            return self.load_from_cache()

        print(f"🌐 Fetching fresh data from {self.base_domain} (dataset {self.dataset_id})...")
        total_records = self.get_total_record_count()
        if total_records:
            print(f"📊 Estimated total records: {total_records:,}")

        all_dataframes = []
        offset = 0
        batch_count = 0

        while True:
            try:
                batch_df = self.fetch_json_batch(offset, self.batch_size)
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
            raise ValueError(f"No data could be fetched from {self.base_domain}/{self.dataset_id}")

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
