#!/usr/bin/env python3
"""
MCP Server for Chicago Homicide Data

This server provides tools to query and analyze the Chicago homicide dataset.
"""

import asyncio
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
import argparse

# Import MCP types
import mcp
from mcp import Tool

# Import data fetcher and base domain
from chicago_data_fetcher import ChicagoHomicideDataFetcher
from base_domain import BaseDataDomain

class HomicideDataMCP(BaseDataDomain):
    """MCP Server for Chicago Homicide Data Analysis."""

    # ------------------------------------------------------------------
    # BaseDataDomain interface
    # ------------------------------------------------------------------

    @property
    def domain_name(self) -> str:
        return "homicides"

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return tool definitions for the LLM prompt."""
        return [
            {
                "name": "query_homicides_advanced",
                "description": (
                    "Query homicide data with flexible filtering options. Use this for ALL data analysis "
                    "queries including: single years, year ranges, geographic filters, location searches, "
                    "arrest status, domestic cases, and overall statistics. Examples: 'homicides in 2023', "
                    "'overall statistics', 'homicides from 2015-2019 in ward 3', 'street homicides with arrests'."
                ),
                "parameters": {
                    "start_year": {"type": "integer", "description": "Start year for date range filter (or single year if used alone)"},
                    "end_year": {"type": "integer", "description": "End year for date range filter"},
                    "ward": {"type": "integer", "description": "Ward number to filter by (1-50)"},
                    "district": {"type": "integer", "description": "Police district number to filter by"},
                    "community_area": {"type": "integer", "description": "Community area number to filter by"},
                    "arrest_status": {"type": "boolean", "description": "Filter by arrest status: true for arrests made, false for no arrests"},
                    "domestic": {"type": "boolean", "description": "Filter by domestic violence cases"},
                    "location_type": {"type": "string", "description": "Filter by location type (e.g., 'STREET', 'APARTMENT', 'RESIDENCE')"},
                    "group_by": {"type": "string", "description": "Focus results on specific grouping for 'which X had the most' queries: 'ward', 'district', 'community_area', or 'location'"},
                    "top_n": {"type": "integer", "description": "Number of items to show in breakdowns (default 10)"},
                },
                "required": [],
            },
            {
                "name": "get_iucr_info",
                "description": (
                    "Get information and explanations about IUCR (Illinois Uniform Crime Reporting) codes. "
                    "Use this ONLY when users ask about what IUCR means, what specific codes mean, or need "
                    "educational information about crime classification codes."
                ),
                "parameters": {
                    "iucr_code": {"type": "string", "description": "Specific IUCR code to look up (optional, e.g., '0110'). If not provided, returns overview of IUCR system."},
                },
                "required": [],
            },
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the appropriate query method."""
        if tool_name == "query_homicides_advanced":
            return self.query_homicides_advanced(
                start_year=arguments.get("start_year"),
                end_year=arguments.get("end_year"),
                ward=arguments.get("ward"),
                district=arguments.get("district"),
                community_area=arguments.get("community_area"),
                arrest_status=arguments.get("arrest_status"),
                domestic=arguments.get("domestic"),
                location_type=arguments.get("location_type"),
                group_by=arguments.get("group_by"),
                top_n=arguments.get("top_n", 10),
                limit=arguments.get("limit", 100),
            )
        elif tool_name == "get_iucr_info":
            return self.get_iucr_info(arguments.get("iucr_code"))
        return {"error": f"Unknown homicide tool: {tool_name}"}

    def format_result(self, result: Dict[str, Any]) -> str:
        """Format homicide query results for the LLM."""
        if "error" in result:
            return f"❌ Error: {result['error']}"

        try:
            # Advanced query result
            if "total_matches" in result and "filters_applied" in result:
                return self._format_advanced_result(result)
            # Year query
            elif "year" in result and "records" in result:
                return self._format_year_result(result)
            # Statistics
            elif "total_homicides" in result:
                return self._format_statistics_result(result)
            # Location search
            elif "query" in result and "records" in result:
                return self._format_location_result(result)
            # IUCR specific
            elif "iucr_code" in result:
                return self._format_iucr_result(result)
            # IUCR overview
            elif "explanation" in result and "unique_codes_count" in result:
                return self._format_iucr_overview(result)
            # Fallback
            return f"📋 **Result:**\n```json\n{json.dumps(result, indent=2)}\n```"
        except Exception as e:
            return f"📋 **Raw Result:** {json.dumps(result, indent=2)}\n\n⚠️ Format error: {str(e)}"

    # -- Private formatting helpers ------------------------------------------------

    @staticmethod
    def _format_advanced_result(result: Dict[str, Any]) -> str:
        response = "🔍 **Advanced Homicide Query Results**\n"
        if result["filters_applied"]:
            response += f"**Filters Applied:** {', '.join(result['filters_applied'])}\n\n"
        response += "**Summary:**\n"
        response += f"  Total matches: {result['total_matches']}\n"
        response += f"  Arrests made: {result['arrest_count']} ({result['arrest_rate']})\n"
        response += f"  Domestic cases: {result['domestic_count']} ({result['domestic_rate']})\n\n"

        if result.get("primary_breakdown") and result["primary_breakdown"].get("data"):
            breakdown = result["primary_breakdown"]
            breakdown_type = breakdown["type"].replace("_", " ").title()
            response += f"**{breakdown_type} Breakdown (Ranked by Count):**\n"
            sorted_items = sorted(breakdown["data"].items(), key=lambda x: x[1], reverse=True)
            for item, count in sorted_items:
                label = item if breakdown["type"] == "location" else f"{breakdown_type} {item}"
                response += f"  {label}: {count} homicides\n"
            response += "\n"
            if sorted_items:
                top_item, top_count = sorted_items[0]
                response += f"**Answer: {breakdown_type} {top_item} had the most with {top_count} homicides.**\n\n"
        else:
            if result["year_breakdown"]:
                response += "**Year Breakdown:**\n"
                for year, count in sorted(result["year_breakdown"].items()):
                    response += f"  {year}: {count} homicides\n"
                response += "\n"
            if result.get("ward_breakdown"):
                response += f"**Ward Breakdown (Top {len(result['ward_breakdown'])}):**\n"
                for ward, count in sorted(result["ward_breakdown"].items(), key=lambda x: x[1], reverse=True):
                    response += f"  Ward {ward}: {count} homicides\n"
                response += "\n"
            if result.get("district_breakdown"):
                response += f"**District Breakdown (Top {len(result['district_breakdown'])}):**\n"
                for district, count in sorted(result["district_breakdown"].items(), key=lambda x: x[1], reverse=True):
                    response += f"  District {district}: {count} homicides\n"
                response += "\n"
            if result.get("community_area_breakdown"):
                response += f"**Community Area Breakdown (Top {len(result['community_area_breakdown'])}):**\n"
                for ca, count in sorted(result["community_area_breakdown"].items(), key=lambda x: x[1], reverse=True):
                    response += f"  Community Area {ca}: {count} homicides\n"
                response += "\n"

        if result.get("top_locations"):
            response += "**Top Locations:**\n"
            for location, count in list(result["top_locations"].items())[:3]:
                response += f"  {location}: {count} cases\n"
            response += "\n"

        if result.get("sample_records"):
            response += f"**Sample Records ({len(result['sample_records'])}):**\n"
            for i, rec in enumerate(result["sample_records"][:3], 1):
                response += f"{i}. **Case {rec['case_number']}** ({rec['year']})\n"
                response += f"   Ward: {rec['ward']}, District: {rec['district']}\n"
                response += f"   Location: {rec['block']}\n"
                response += f"   Arrest: {'Yes' if rec['arrest'] else 'No'}\n\n"
        return response

    @staticmethod
    def _format_year_result(result: Dict[str, Any]) -> str:
        response = f"📅 **Homicides in {result['year']}**\n"
        response += f"Total records: {result['total_records']}\n"
        response += f"Showing: {result['returned_records']} records\n\n"
        for i, rec in enumerate(result["records"][:5], 1):
            response += f"{i}. **Case {rec['case_number']}**\n"
            response += f"   Date: {rec['date']}\n"
            response += f"   Location: {rec['block']}\n"
            response += f"   Description: {rec['description']}\n"
            response += f"   Arrest: {'Yes' if rec['arrest'] else 'No'}\n\n"
        if result["returned_records"] > 5:
            response += f"... and {result['returned_records'] - 5} more records\n"
        return response

    @staticmethod
    def _format_statistics_result(result: Dict[str, Any]) -> str:
        response = "📊 **Homicide Statistics**\n"
        response += f"Total homicides: {result['total_homicides']}\n"
        response += f"Year range: {result['year_range']}\n"
        response += f"Arrests made: {result['arrests_made']} ({result['arrest_rate']})\n"
        response += f"Domestic cases: {result['domestic_cases']} ({result['domestic_rate']})\n\n"
        if "top_districts" in result:
            response += "**Top Districts:**\n"
            for district, count in list(result["top_districts"].items())[:3]:
                response += f"  District {district}: {count} cases\n"
        return response

    @staticmethod
    def _format_location_result(result: Dict[str, Any]) -> str:
        response = f"🔍 **Location Search: '{result['query']}'**\n"
        response += f"Total matches: {result['total_matches']}\n"
        response += f"Showing: {result['returned_records']} records\n\n"
        for i, rec in enumerate(result["records"][:3], 1):
            response += f"{i}. **Case {rec['case_number']}** ({rec['year']})\n"
            response += f"   Location: {rec['block']}\n"
            response += f"   Type: {rec['location_description']}\n"
            response += f"   Arrest: {'Yes' if rec['arrest'] else 'No'}\n\n"
        return response

    @staticmethod
    def _format_iucr_result(result: Dict[str, Any]) -> str:
        response = f"📋 **IUCR Code: {result['iucr_code']}**\n"
        response += f"Type: {result['primary_type']}\n"
        response += f"Description: {result['description']}\n"
        response += f"Total cases: {result['total_cases']}\n\n"
        response += result["explanation"]
        return response

    @staticmethod
    def _format_iucr_overview(result: Dict[str, Any]) -> str:
        response = "📋 **IUCR System Overview**\n"
        response += f"{result['explanation']}\n\n"
        response += f"Unique codes in dataset: {result['unique_codes_count']}\n"
        if "sample_codes" in result:
            response += f"Most common codes: {', '.join(result['sample_codes'])}\n"
        return response

    def __init__(
        self,
        csv_path: str,
        data_fetcher: Optional[ChicagoHomicideDataFetcher] = None,
        preloaded_df: Optional[pd.DataFrame] = None,
        force_refresh: bool = False
    ):
        self.csv_path = Path(csv_path)
        self.data_fetcher = data_fetcher
        self.df: Optional[pd.DataFrame] = None
        self.data_source: str = "uninitialized"
        self.load_data(preloaded_df=preloaded_df, force_refresh=force_refresh)

    def load_data(
        self,
        preloaded_df: Optional[pd.DataFrame] = None,
        force_refresh: bool = False,
        **kwargs,
    ) -> bool:
        """Load homicide data from a preloaded frame, API fetcher, or CSV."""
        try:
            if preloaded_df is not None:
                self.df = self._prepare_dataframe(preloaded_df)
                self.data_source = "api_preloaded"
                self._persist_dataframe()
                print(f"✅ Loaded {len(self.df)} homicide records from API fetcher")
                return

            if self.csv_path.exists() and not force_refresh:
                csv_df = pd.read_csv(self.csv_path)
                self.df = self._prepare_dataframe(csv_df)
                self.data_source = "csv"
                print(f"✅ Loaded {len(self.df)} homicide records from {self.csv_path}")
                return

            if self.data_fetcher is not None:
                try:
                    fetched_df = self.data_fetcher.fetch_all_data(force_refresh=force_refresh)
                    if fetched_df is not None and not fetched_df.empty:
                        self.df = self._prepare_dataframe(fetched_df)
                        self.data_source = "api"
                        self._persist_dataframe()
                        print(f"✅ Loaded {len(self.df)} homicide records via API fetcher")
                        return
                except Exception as api_error:
                    print(f"⚠️  API data fetch failed ({api_error}), attempting CSV fallback...")

            if self.csv_path.exists():
                csv_df = pd.read_csv(self.csv_path)
                self.df = self._prepare_dataframe(csv_df)
                self.data_source = "csv"
                print(f"✅ Loaded {len(self.df)} homicide records from {self.csv_path}")
                return

            raise FileNotFoundError(
                "No homicide data source available. Provide a CSV or enable the API fetcher."
            )

        except Exception as e:
            print(f"❌ Error loading homicide data: {e}")
            raise

    def _persist_dataframe(self) -> None:
        """Persist the in-memory dataframe to the canonical CSV location."""
        if self.df is None:
            return

        try:
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            self.df.to_csv(self.csv_path, index=False)
        except Exception as persist_error:
            print(f"⚠️  Unable to persist homicide dataset to {self.csv_path}: {persist_error}")

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize homicide dataframe columns."""
        clean_df = df.copy()

        # Normalize expected column casing if API returns lowercase headers
        column_mapping = {
            'id': 'ID',
            'case_number': 'Case Number',
            'block': 'Block',
            'iucr': 'IUCR',
            'primary_type': 'Primary Type',
            'description': 'Description',
            'location_description': 'Location Description',
            'arrest': 'Arrest',
            'domestic': 'Domestic',
            'district': 'District',
            'ward': 'Ward',
            'community_area': 'Community Area',
            'fbi_code': 'FBI Code',
            'x_coordinate': 'X Coordinate',
            'y_coordinate': 'Y Coordinate',
            'year': 'Year',
            'updated_on': 'Updated On',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'location': 'Location'
        }

        for source_col, target_col in column_mapping.items():
            if source_col in clean_df.columns and target_col not in clean_df.columns:
                clean_df[target_col] = clean_df[source_col]

        # Clean and standardize data
        # Specify date format to avoid parsing warning: MM/dd/yyyy HH:mm:ss AM/PM
        if 'Date' in clean_df.columns:
            clean_df['Date'] = pd.to_datetime(
                clean_df['Date'],
                format='%m/%d/%Y %I:%M:%S %p',
                errors='coerce'
            )

        if 'Year' in clean_df.columns:
            clean_df['Year'] = pd.to_numeric(clean_df['Year'], errors='coerce')

        if 'Arrest' in clean_df.columns:
            clean_df['Arrest'] = (
                clean_df['Arrest']
                .fillna(False)
                .astype(str)
                .str.lower()
                .isin(['true', '1', 'yes'])
            )

        if 'Domestic' in clean_df.columns:
            clean_df['Domestic'] = (
                clean_df['Domestic']
                .fillna(False)
                .astype(str)
                .str.lower()
                .isin(['true', '1', 'yes'])
            )

        return clean_df

    def get_records_by_year(self, year: int, limit: int = 100) -> Dict[str, Any]:
        """Get homicide records for a specific year."""
        if self.df is None:
            return {'error': "Homicide data not loaded"}
            
        try:
            filtered_df = self.df[self.df['Year'] == year].head(limit)
            
            records = []
            for _, row in filtered_df.iterrows():
                records.append({
                    'id': str(row.get('ID', '')),
                    'case_number': str(row.get('Case Number', '')),
                    'date': str(row.get('Date', '')),
                    'block': str(row.get('Block', '')),
                    'iucr': str(row.get('IUCR', '')),
                    'description': str(row.get('Description', '')),
                    'location_description': str(row.get('Location Description', '')),
                    'arrest': bool(row.get('Arrest', False)),
                    'domestic': bool(row.get('Domestic', False)),
                    'district': str(row.get('District', '')),
                    'ward': str(row.get('Ward', '')),
                    'community_area': str(row.get('Community Area', ''))
                })
            
            return {
                'year': year,
                'total_records': int(len(self.df[self.df['Year'] == year])),
                'returned_records': len(records),
                'records': records
            }
            
        except Exception as e:
            return {'error': f"Error querying year {year}: {str(e)}"}

    def get_statistics(self, start_year: Optional[int] = None, end_year: Optional[int] = None) -> Dict[str, Any]:
        """Get statistics about homicides."""
        if self.df is None:
            return {'error': "Homicide data not loaded"}
            
        try:
            df = self.df.copy()
            
            # Filter by year range if provided
            if start_year:
                df = df[df['Year'] >= start_year]
            if end_year:
                df = df[df['Year'] <= end_year]
            
            # Convert to regular Python types for JSON serialization
            by_year = {str(int(k)): int(v) for k, v in df.groupby('Year').size().to_dict().items() if pd.notna(k)}
            top_districts = {str(k): int(v) for k, v in df['District'].value_counts().head(5).to_dict().items() if pd.notna(k)}
            top_wards = {str(k): int(v) for k, v in df['Ward'].value_counts().head(5).to_dict().items() if pd.notna(k)}
            top_community_areas = {str(k): int(v) for k, v in df['Community Area'].value_counts().head(5).to_dict().items() if pd.notna(k)}
            
            stats = {
                'total_homicides': int(len(df)),
                'year_range': f"{int(df['Year'].min())} - {int(df['Year'].max())}",
                'arrests_made': int(df['Arrest'].sum()),
                'arrest_rate': f"{(df['Arrest'].sum() / len(df) * 100):.1f}%",
                'domestic_cases': int(df['Domestic'].sum()),
                'domestic_rate': f"{(df['Domestic'].sum() / len(df) * 100):.1f}%",
                'by_year': by_year,
                'top_districts': top_districts,
                'top_wards': top_wards,
                'top_community_areas': top_community_areas
            }
            
            return stats
            
        except Exception as e:
            return {'error': f"Error generating statistics: {str(e)}"}

    def search_by_location(self, location_query: str, limit: int = 50) -> Dict[str, Any]:
        """Search homicides by location."""
        if self.df is None:
            return {'error': "Homicide data not loaded"}
            
        try:
            df = self.df.copy()
            
            # Search in multiple location fields
            mask = (
                df['Block'].str.contains(location_query, case=False, na=False) |
                df['Location Description'].str.contains(location_query, case=False, na=False)
            )
            
            filtered_df = df[mask].head(limit)
            
            records = []
            for _, row in filtered_df.iterrows():
                records.append({
                    'id': str(row.get('ID', '')),
                    'case_number': str(row.get('Case Number', '')),
                    'date': str(row.get('Date', '')),
                    'year': str(row.get('Year', '')),
                    'block': str(row.get('Block', '')),
                    'location_description': str(row.get('Location Description', '')),
                    'arrest': bool(row.get('Arrest', False)),
                    'domestic': bool(row.get('Domestic', False))
                })
            
            return {
                'query': location_query,
                'total_matches': int(mask.sum()),
                'returned_records': len(records),
                'records': records
            }
            
        except Exception as e:
            return {'error': f"Error searching location '{location_query}': {str(e)}"}

    def get_iucr_info(self, iucr_code: Optional[str] = None) -> Dict[str, Any]:
        """Get information about IUCR codes."""
        if self.df is None:
            return {'error': "Homicide data not loaded"}
            
        try:
            if iucr_code:
                # Get specific IUCR code info
                iucr_df = self.df[self.df['IUCR'] == iucr_code]
                if iucr_df.empty:
                    return {'error': f"IUCR code '{iucr_code}' not found"}
                
                sample_row = iucr_df.iloc[0]
                return {
                    'iucr_code': iucr_code,
                    'primary_type': str(sample_row.get('Primary Type', '')),
                    'description': str(sample_row.get('Description', '')),
                    'total_cases': int(len(iucr_df)),
                    'explanation': "IUCR stands for Illinois Uniform Crime Reporting. It's a standardized system used by law enforcement agencies in Illinois to classify and report crimes."
                }
            else:
                # Get summary of IUCR codes
                return {
                    'explanation': "IUCR stands for Illinois Uniform Crime Reporting. It's a standardized system used by law enforcement agencies in Illinois to classify and report crimes.",
                    'most_common_code': str(self.df['IUCR'].mode().iloc[0] if not self.df['IUCR'].mode().empty else 'Unknown'),
                    'unique_codes_count': int(self.df['IUCR'].nunique()),
                    'sample_codes': list(self.df['IUCR'].value_counts().head(5).index.astype(str))
                }
                
        except Exception as e:
            return {'error': f"Error getting IUCR information: {str(e)}"}
    
    def query_homicides_advanced(self, 
                                start_year: Optional[int] = None,
                                end_year: Optional[int] = None,
                                ward: Optional[int] = None,
                                district: Optional[int] = None,
                                community_area: Optional[int] = None,
                                arrest_status: Optional[bool] = None,
                                domestic: Optional[bool] = None,
                                location_type: Optional[str] = None,
                                group_by: Optional[str] = None,
                                top_n: int = 1000,
                                limit: int = 1000) -> Dict[str, Any]:
        """Advanced homicide query with multiple filter options."""
        if self.df is None:
            return {'error': "Homicide data not loaded"}
            
        try:
            df = self.df.copy()
            filters_applied = []
            
            # Apply year range filter
            if start_year is not None:
                df = df[df['Year'] >= start_year]
                filters_applied.append(f"start_year: {start_year}")
            
            if end_year is not None:
                df = df[df['Year'] <= end_year]
                filters_applied.append(f"end_year: {end_year}")
            
            # Apply geographical filters
            if ward is not None:
                df = df[pd.to_numeric(df['Ward'], errors='coerce') == ward]
                filters_applied.append(f"ward: {ward}")
            
            if district is not None:
                df = df[pd.to_numeric(df['District'], errors='coerce') == district]
                filters_applied.append(f"district: {district}")
            
            if community_area is not None:
                df = df[pd.to_numeric(df['Community Area'], errors='coerce') == community_area]
                filters_applied.append(f"community_area: {community_area}")
            
            # Apply status filters
            if arrest_status is not None:
                df = df[df['Arrest'] == arrest_status]
                filters_applied.append(f"arrest_status: {arrest_status}")
            
            if domestic is not None:
                df = df[df['Domestic'] == domestic]
                filters_applied.append(f"domestic: {domestic}")
            
            # Apply location type filter
            if location_type is not None:
                df = df[df['Location Description'].str.contains(location_type, case=False, na=False)]
                filters_applied.append(f"location_type: {location_type}")
            
            # Calculate statistics
            total_matches = len(df)
            arrest_count = int(df['Arrest'].sum()) if len(df) > 0 else 0
            domestic_count = int(df['Domestic'].sum()) if len(df) > 0 else 0
            arrest_rate = (arrest_count / total_matches * 100) if total_matches > 0 else 0
            domestic_rate = (domestic_count / total_matches * 100) if total_matches > 0 else 0
            
            # Get breakdown by year if multiple years
            year_breakdown = {}
            if total_matches > 0:
                year_counts = df['Year'].value_counts().sort_index()
                for k, v in year_counts.items():
                    try:
                        # Convert to string first, then check and convert
                        k_str = str(k)
                        if k_str not in ['nan', 'None', '']:
                            year_key = str(int(float(k_str)))
                            year_breakdown[year_key] = int(v)
                    except (ValueError, TypeError, OverflowError):
                        continue
            
            # Get geographic breakdowns
            ward_breakdown = {}
            district_breakdown = {}
            community_area_breakdown = {}
            primary_breakdown = {}  # For group_by functionality
            
            if total_matches > 0:
                # Ward breakdown
                ward_counts = df['Ward'].value_counts().head(top_n)
                ward_breakdown = {str(k): int(v) for k, v in ward_counts.items() if k is not None and str(k) != 'nan'}
                
                # District breakdown
                district_counts = df['District'].value_counts().head(top_n)
                district_breakdown = {str(k): int(v) for k, v in district_counts.items() if k is not None and str(k) != 'nan'}
                
                # Community area breakdown
                ca_counts = df['Community Area'].value_counts().head(top_n)
                community_area_breakdown = {str(k): int(v) for k, v in ca_counts.items() if k is not None and str(k) != 'nan'}
                
                # Handle group_by for focused results
                if group_by:
                    group_by_lower = group_by.lower()
                    if group_by_lower in ['ward', 'wards']:
                        primary_breakdown = {'type': 'ward', 'data': ward_breakdown}
                    elif group_by_lower in ['district', 'districts']:
                        primary_breakdown = {'type': 'district', 'data': district_breakdown}
                    elif group_by_lower in ['community_area', 'community_areas', 'community area', 'community areas']:
                        primary_breakdown = {'type': 'community_area', 'data': community_area_breakdown}
                    elif group_by_lower in ['location', 'locations', 'block', 'blocks']:
                        location_counts = df['Block'].value_counts().head(top_n)
                        location_data = {str(k): int(v) for k, v in location_counts.items()}
                        primary_breakdown = {'type': 'location', 'data': location_data}
            
            # Get top locations within filtered data
            top_locations = {}
            if total_matches > 0 and len(df) > 0:
                location_counts = df['Block'].value_counts().head(5)
                top_locations = {str(k): int(v) for k, v in location_counts.items()}
            
            # Sample records
            sample_records = []
            for _, row in df.head(limit).iterrows():
                sample_records.append({
                    'id': str(row.get('ID', '')),
                    'case_number': str(row.get('Case Number', '')),
                    'date': str(row.get('Date', '')),
                    'year': int(row.get('Year', 0)) if pd.notna(row.get('Year')) else None,
                    'block': str(row.get('Block', '')),
                    'ward': str(row.get('Ward', '')),
                    'district': str(row.get('District', '')),
                    'community_area': str(row.get('Community Area', '')),
                    'location_description': str(row.get('Location Description', '')),
                    'arrest': bool(row.get('Arrest', False)),
                    'domestic': bool(row.get('Domestic', False))
                })
            
            return {
                'total_matches': total_matches,
                'filters_applied': filters_applied,
                'arrest_count': arrest_count,
                'arrest_rate': f"{arrest_rate:.1f}%",
                'domestic_count': domestic_count,
                'domestic_rate': f"{domestic_rate:.1f}%",
                'year_breakdown': year_breakdown,
                'ward_breakdown': ward_breakdown,
                'district_breakdown': district_breakdown,
                'community_area_breakdown': community_area_breakdown,
                'primary_breakdown': primary_breakdown,
                'top_locations': top_locations,
                'sample_records_count': len(sample_records),
                'sample_records': sample_records
            }
            
        except Exception as e:
            return {'error': f"Error in advanced query: {str(e)}"}

def create_homicide_tools() -> List[Tool]:
    """Create the MCP tools for homicide data analysis."""
    return [
        Tool(
            name="query_homicides_advanced",
            description="Query homicide data with flexible filtering options for all data analysis needs (years, ranges, geography, arrests, domestic, location types).",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_year": {"type": "integer", "description": "Start year for date range", "minimum": 2001, "maximum": 2024},
                    "end_year": {"type": "integer", "description": "End year for date range", "minimum": 2001, "maximum": 2024},
                    "ward": {"type": "integer", "description": "Ward number (1-50)", "minimum": 1, "maximum": 50},
                    "district": {"type": "integer", "description": "Police district (1-25)", "minimum": 1, "maximum": 25},
                    "community_area": {"type": "integer", "description": "Community area (1-77)", "minimum": 1, "maximum": 77},
                    "arrest_status": {"type": "boolean", "description": "true for arrests made, false for no arrests"},
                    "domestic": {"type": "boolean", "description": "true for domestic cases, false otherwise"},
                    "location_type": {"type": "string", "description": "Location type or keyword (e.g., 'STREET', 'APARTMENT')"},
                    "group_by": {"type": "string", "description": "Focus results on specific grouping: 'ward', 'district', 'community_area', or 'location'. Use for 'which X had the most' queries."},
                    "top_n": {"type": "integer", "description": "Number of items to show in breakdowns (default 10)", "default": 10, "minimum": 1, "maximum": 50},
                    "limit": {"type": "integer", "description": "Max sample records to include (default 100)", "default": 100, "minimum": 1, "maximum": 1000}
                }
            }
        ),
        Tool(
            name="get_iucr_info",
            description="Get information about IUCR codes (overview or details for a specific code).",
            inputSchema={
                "type": "object",
                "properties": {
                    "iucr_code": {"type": "string", "description": "Specific IUCR code to look up (optional)"}
                }
            }
        )
    ]

# Global instance
homicide_data = None

def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool calls and return results."""
    global homicide_data
    
    if homicide_data is None:
        return {"error": "Homicide data not loaded"}
    
    try:
        if tool_name == "query_homicides_advanced":
            return homicide_data.query_homicides_advanced(
                start_year=arguments.get("start_year"),
                end_year=arguments.get("end_year"),
                ward=arguments.get("ward"),
                district=arguments.get("district"),
                community_area=arguments.get("community_area"),
                arrest_status=arguments.get("arrest_status"),
                domestic=arguments.get("domestic"),
                location_type=arguments.get("location_type"),
                group_by=arguments.get("group_by"),
                top_n=arguments.get("top_n", 10),
                limit=arguments.get("limit", 100)
            )
            
        elif tool_name == "get_iucr_info":
            iucr_code = arguments.get("iucr_code")
            return homicide_data.get_iucr_info(iucr_code)
            
        else:
            return {"error": f"Unknown tool: {tool_name}"}
            
    except Exception as e:
        return {"error": f"Error executing {tool_name}: {str(e)}"}

def main():
    """Main entry point for testing the homicide data MCP."""
    global homicide_data
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Chicago Homicide Data MCP Server")
    parser.add_argument(
        "--csv-path", 
        default="./knowledge_base/Homicides_2001_to_present.csv",
        help="Path to the homicide CSV file"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode to verify data loading and tool functionality"
    )
    args = parser.parse_args()
    
    # Initialize the homicide data
    try:
        data_fetcher = ChicagoHomicideDataFetcher()
        homicide_data = HomicideDataMCP(
            args.csv_path,
            data_fetcher=data_fetcher,
            force_refresh=args.test
        )
        print(f"✅ Homicide MCP server initialized successfully")
        
        if args.test:
            print("\n🧪 Testing tools...")
            
            # Test statistics
            print("\n📊 Testing statistics...")
            stats = handle_tool_call("get_homicide_statistics", {})
            print(f"Total homicides: {stats.get('total_homicides', 'Unknown')}")
            print(f"Year range: {stats.get('year_range', 'Unknown')}")
            
            # Test year query
            print("\n📅 Testing year query (2023)...")
            year_data = handle_tool_call("get_homicides_by_year", {"year": 2023, "limit": 5})
            print(f"Found {year_data.get('total_records', 0)} records for 2023")
            
            # Test IUCR info
            print("\n📋 Testing IUCR info...")
            iucr_data = handle_tool_call("get_iucr_info", {})
            print(f"Unique IUCR codes: {iucr_data.get('unique_codes_count', 'Unknown')}")
            
            # Test location search
            print("\n🔍 Testing location search...")
            location_data = handle_tool_call("search_by_location", {"location_query": "STREET", "limit": 3})
            print(f"Found {location_data.get('total_matches', 0)} street homicides")
            
            print("\n✅ All tests completed successfully!")
        else:
            print("Use --test flag to run functionality tests")
            print("Available tools:", [tool.name for tool in create_homicide_tools()])
            
    except Exception as e:
        print(f"❌ Error initializing homicide data: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
