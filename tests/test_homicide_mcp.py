#!/usr/bin/env python3
"""
Unit tests for HomicideDataMCP using deterministic fixtures.
"""

import pytest
from pathlib import Path
import pandas as pd

from homicide_mcp import HomicideDataMCP


@pytest.fixture
def fixture_csv_path():
    """Return path to the mini test fixture CSV."""
    return str(Path(__file__).parent / "fixtures" / "mini_homicides.csv")


@pytest.fixture
def homicide_mcp(fixture_csv_path):
    """Create HomicideDataMCP instance with test fixture."""
    return HomicideDataMCP(csv_path=fixture_csv_path, data_fetcher=None)


class TestHomicideDataLoading:
    """Test data loading and preparation."""
    
    def test_fixture_loads(self, homicide_mcp):
        """Test that fixture CSV loads successfully."""
        assert homicide_mcp.df is not None
        assert len(homicide_mcp.df) == 20
    
    def test_column_normalization(self, homicide_mcp):
        """Test that columns are properly normalized."""
        df = homicide_mcp.df
        expected_columns = ['Year', 'Arrest', 'Domestic', 'District', 'Ward', 'Community Area']
        for col in expected_columns:
            assert col in df.columns
    
    def test_arrest_boolean_conversion(self, homicide_mcp):
        """Test that Arrest column is properly converted to boolean."""
        df = homicide_mcp.df
        assert df['Arrest'].dtype == bool
        # Fixture has specific arrest=True rows: 2, 5, 8, 11, 15, 19
        assert df['Arrest'].sum() == 6


class TestStatistics:
    """Test get_statistics method."""
    
    def test_overall_statistics(self, homicide_mcp):
        """Test overall statistics without filters."""
        result = homicide_mcp.get_statistics()
        
        assert 'error' not in result
        assert result['total_homicides'] == 20
        assert 'year_range' in result
        assert result['arrests_made'] == 6
        assert result['domestic_cases'] == 6
    
    def test_year_filtering(self, homicide_mcp):
        """Test statistics with year range filtering."""
        result = homicide_mcp.get_statistics(start_year=2023, end_year=2023)
        
        assert 'error' not in result
        # Fixture has 7 records in 2023: rows 11-17
        assert result['total_homicides'] == 7
    
    def test_top_districts(self, homicide_mcp):
        """Test that top districts are calculated correctly."""
        result = homicide_mcp.get_statistics()
        
        assert 'top_districts' in result
        # District 11 and 7 have most in fixture
        assert '11' in result['top_districts'] or '7' in result['top_districts']


class TestAdvancedQuery:
    """Test query_homicides_advanced method."""
    
    def test_year_range_filter(self, homicide_mcp):
        """Test filtering by year range."""
        result = homicide_mcp.query_homicides_advanced(
            start_year=2020,
            end_year=2021
        )
        
        assert 'error' not in result
        # Fixture: 2020 has 3 records, 2021 has 3 records
        assert result['total_matches'] == 6
    
    def test_arrest_status_filter(self, homicide_mcp):
        """Test filtering by arrest status."""
        result = homicide_mcp.query_homicides_advanced(arrest_status=False)
        
        assert 'error' not in result
        assert result['total_matches'] == 14  # 20 total - 6 arrests
        assert result['arrest_count'] == 0
    
    def test_domestic_filter(self, homicide_mcp):
        """Test filtering by domestic status."""
        result = homicide_mcp.query_homicides_advanced(domestic=True)
        
        assert 'error' not in result
        # Fixture has 6 domestic cases
        assert result['total_matches'] == 6
        assert result['domestic_count'] == 6
    
    def test_ward_filter(self, homicide_mcp):
        """Test filtering by ward."""
        result = homicide_mcp.query_homicides_advanced(ward=28)
        
        assert 'error' not in result
        # Ward 28 appears in multiple fixture rows
        assert result['total_matches'] > 0
    
    def test_district_filter(self, homicide_mcp):
        """Test filtering by district."""
        result = homicide_mcp.query_homicides_advanced(district=7)
        
        assert 'error' not in result
        # District 7 has 3 cases in fixture (rows 4, 5, 8)
        assert result['total_matches'] == 3
    
    def test_group_by_ward(self, homicide_mcp):
        """Test group_by ward functionality."""
        result = homicide_mcp.query_homicides_advanced(
            group_by="ward",
            top_n=5
        )
        
        assert 'error' not in result
        assert result['primary_breakdown']['type'] == 'ward'
        assert len(result['primary_breakdown']['data']) > 0
        # Ward 28 should be prominent (appears 6 times)
        assert '28' in result['primary_breakdown']['data']
    
    def test_group_by_district(self, homicide_mcp):
        """Test group_by district functionality."""
        result = homicide_mcp.query_homicides_advanced(
            group_by="district",
            top_n=3
        )
        
        assert 'error' not in result
        assert result['primary_breakdown']['type'] == 'district'
        assert len(result['primary_breakdown']['data']) > 0
    
    def test_multi_criteria_filter(self, homicide_mcp):
        """Test multiple filters at once."""
        result = homicide_mcp.query_homicides_advanced(
            start_year=2023,
            arrest_status=False,
            group_by="ward",
            top_n=3
        )
        
        assert 'error' not in result
        # 2023 has 7 records, 3 have arrests, so 4 without arrests
        assert result['total_matches'] == 4
        assert result['arrest_count'] == 0
        assert result['primary_breakdown']['type'] == 'ward'
    
    def test_top_n_limit(self, homicide_mcp):
        """Test that top_n parameter limits breakdown size."""
        result = homicide_mcp.query_homicides_advanced(
            group_by="ward",
            top_n=2
        )
        
        assert 'error' not in result
        # Should have at most 2 wards in primary breakdown
        assert len(result['primary_breakdown']['data']) <= 2


class TestLocationSearch:
    """Test search_by_location method."""
    
    def test_search_by_street_name(self, homicide_mcp):
        """Test searching by street name."""
        result = homicide_mcp.search_by_location("STATE ST")
        
        assert 'error' not in result
        assert result['total_matches'] >= 1
        assert result['query'] == "STATE ST"
    
    def test_search_case_insensitive(self, homicide_mcp):
        """Test that search is case-insensitive."""
        result1 = homicide_mcp.search_by_location("STREET")
        result2 = homicide_mcp.search_by_location("street")
        
        assert result1['total_matches'] == result2['total_matches']
    
    def test_search_limit(self, homicide_mcp):
        """Test that search respects limit parameter."""
        result = homicide_mcp.search_by_location("STREET", limit=3)
        
        assert 'error' not in result
        assert result['returned_records'] <= 3


class TestIUCRInfo:
    """Test get_iucr_info method."""
    
    def test_iucr_general_info(self, homicide_mcp):
        """Test getting general IUCR information."""
        result = homicide_mcp.get_iucr_info()
        
        assert 'error' not in result
        assert 'explanation' in result
        assert 'IUCR' in result['explanation']
    
    def test_specific_iucr_code(self, homicide_mcp):
        """Test getting info for specific IUCR code."""
        result = homicide_mcp.get_iucr_info("0110")
        
        assert 'error' not in result
        assert result['iucr_code'] == "0110"
        assert result['total_cases'] == 20  # All fixture records are 0110


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_year_range(self, homicide_mcp):
        """Test with year range that has no data."""
        result = homicide_mcp.query_homicides_advanced(
            start_year=1990,
            end_year=1995
        )
        
        assert 'error' not in result
        assert result['total_matches'] == 0
    
    def test_nonexistent_ward(self, homicide_mcp):
        """Test filtering by non-existent ward."""
        result = homicide_mcp.query_homicides_advanced(ward=99)
        
        assert 'error' not in result
        assert result['total_matches'] == 0
    
    def test_empty_location_search(self, homicide_mcp):
        """Test searching for non-existent location."""
        result = homicide_mcp.search_by_location("NONEXISTENT LOCATION XYZ")
        
        assert 'error' not in result
        assert result['total_matches'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
