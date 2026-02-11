#!/usr/bin/env python3
"""
MCP Integration for the Llama RAG System

This module integrates Model Context Protocol tools with the main chat interface.
It uses a domain registry so new data domains (census, property, etc.) can be
added without modifying this file.
"""

from typing import Dict, List, Any, Optional
import json
from pathlib import Path

from base_domain import BaseDataDomain
from homicide_mcp import HomicideDataMCP
from chicago_data_fetcher import ChicagoHomicideDataFetcher
from census_mcp import CensusDataMCP
from socioeconomic_mcp import SocioeconomicDataMCP


class MCPIntegration:
    """Integration layer for MCP tools in the Llama RAG system."""

    def __init__(self):
        self.domains: Dict[str, BaseDataDomain] = {}
        # Maps tool_name -> domain_name for fast dispatch
        self._tool_domain_map: Dict[str, str] = {}
        self.initialize_mcp_tools()

    # ------------------------------------------------------------------
    # Domain registry
    # ------------------------------------------------------------------

    def register_domain(self, domain: BaseDataDomain) -> None:
        """Register a data domain and index its tools."""
        self.domains[domain.domain_name] = domain
        for tool_name in domain.get_tool_names():
            self._tool_domain_map[tool_name] = domain.domain_name
        print(f"  ✅ Registered domain '{domain.domain_name}' with {len(domain.get_tool_names())} tools")

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize_mcp_tools(self):
        """Initialize MCP tools and data sources."""
        try:
            self._init_homicide_domain()
            self._init_census_domain()
            self._init_socioeconomic_domain()
            # Future domains:
            # self._init_property_domain()
            total_tools = len(self._tool_domain_map)
            print(f"✅ MCP initialized with {total_tools} tools across {len(self.domains)} domain(s)")
        except Exception as e:
            print(f"❌ Error initializing MCP tools: {e}")

    def _init_homicide_domain(self):
        """Bootstrap the homicide domain."""
        csv_path = Path("./knowledge_base/Homicides_2001_to_present.csv")

        # Try API first, fall back to CSV
        try:
            fetcher = ChicagoHomicideDataFetcher()
            api_df = fetcher.fetch_all_data()
            domain = HomicideDataMCP(str(csv_path), data_fetcher=fetcher, preloaded_df=api_df)
        except Exception as api_error:
            print(f"⚠️  Unable to load homicide data from API: {api_error}")
            if csv_path.exists():
                domain = HomicideDataMCP(str(csv_path))
            else:
                print(f"⚠️ Homicide CSV not found at {csv_path}")
                return

        self.register_domain(domain)

    def _init_census_domain(self):
        """Bootstrap the census/demographics domain."""
        try:
            domain = CensusDataMCP()
            self.register_domain(domain)
        except Exception as e:
            print(f"⚠️  Unable to load census domain: {e}")

    def _init_socioeconomic_domain(self):
        """Bootstrap the socioeconomic indicators domain."""
        try:
            domain = SocioeconomicDataMCP()
            self.register_domain(domain)
        except Exception as e:
            print(f"⚠️  Unable to load socioeconomic domain: {e}")

    # ------------------------------------------------------------------
    # Backward-compatible helpers
    # ------------------------------------------------------------------

    @property
    def homicide_data(self) -> Optional[HomicideDataMCP]:
        """Convenience accessor used by legacy callers."""
        return self.domains.get("homicides")  # type: ignore[return-value]

    @property
    def available_tools(self) -> list:
        """Return flat list of all tool names (legacy compat)."""
        return list(self._tool_domain_map.keys())

    # ------------------------------------------------------------------
    # Tool catalogue
    # ------------------------------------------------------------------

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available MCP tools across all domains."""
        tools_info: List[Dict[str, str]] = []
        for domain in self.domains.values():
            for tdef in domain.get_tool_definitions():
                tools_info.append({
                    "name": tdef["name"],
                    "description": tdef["description"],
                    "domain": domain.domain_name,
                    "usage": f"Use /mcp {tdef['name']} to call this tool",
                })
        return tools_info

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """Collect tool definitions from every registered domain."""
        defs: List[Dict[str, Any]] = []
        for domain in self.domains.values():
            defs.extend(domain.get_tool_definitions())
        return defs

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route a tool call to the owning domain."""
        domain_name = self._tool_domain_map.get(tool_name)
        if domain_name is None:
            available = ", ".join(self._tool_domain_map.keys()) or "(none)"
            return {"error": f"Tool '{tool_name}' not found. Available tools: {available}"}
        domain = self.domains[domain_name]
        try:
            return domain.call_tool(tool_name, arguments)
        except Exception as e:
            return {"error": f"Error calling tool '{tool_name}': {str(e)}"}
    
    # ------------------------------------------------------------------
    # Result formatting
    # ------------------------------------------------------------------

    def format_tool_result(self, result: Dict[str, Any], tool_name: str = None) -> str:
        """Delegate formatting to the owning domain."""
        # Determine which domain produced this result
        domain = None
        if tool_name:
            domain_name = self._tool_domain_map.get(tool_name)
            if domain_name:
                domain = self.domains.get(domain_name)

        if domain is not None:
            return domain.format_result(result)

        # Fallback: try each domain, or generic JSON
        for d in self.domains.values():
            try:
                return d.format_result(result)
            except Exception:
                continue
        return f"📋 **Result:**\n```json\n{json.dumps(result, indent=2)}\n```"

    # ------------------------------------------------------------------
    # Command parsing (legacy /mcp CLI)
    # ------------------------------------------------------------------

    def parse_mcp_command(self, command_text: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Parse an MCP command from user input."""
        try:
            parts = command_text.strip().split(' ', 1)
            if len(parts) < 1:
                return None, None
            
            tool_name = parts[0]
            
            # Parse arguments (simple key=value format or JSON)
            arguments = {}
            if len(parts) > 1:
                args_text = parts[1].strip()
                
                # Try to parse as JSON first
                try:
                    arguments = json.loads(args_text)
                except json.JSONDecodeError:
                    # Parse as simple key=value pairs
                    if '=' in args_text:
                        for pair in args_text.split():
                            if '=' in pair:
                                key, value = pair.split('=', 1)
                                # Try to convert to appropriate type
                                try:
                                    # Try integer
                                    if value.isdigit():
                                        arguments[key] = int(value)
                                    # Try boolean
                                    elif value.lower() in ('true', 'false'):
                                        arguments[key] = value.lower() == 'true'
                                    else:
                                        arguments[key] = value
                                except:
                                    arguments[key] = value
                    else:
                        # Single argument, assume it's for the first parameter
                        if tool_name == "get_iucr_info":
                            arguments["iucr_code"] = args_text
                        elif tool_name == "query_homicides_advanced":
                            # For advanced queries, try to parse simple patterns
                            if args_text.isdigit():
                                # Could be year or ward - assume year for single number
                                arguments["start_year"] = int(args_text)
                                arguments["end_year"] = int(args_text)
                            else:
                                # Could be location type or other string parameter
                                arguments["location_type"] = args_text
            
            return tool_name, arguments
            
        except Exception as e:
            return None, {"error": f"Error parsing command: {str(e)}"}

# Create global instance
mcp_integration = MCPIntegration()
