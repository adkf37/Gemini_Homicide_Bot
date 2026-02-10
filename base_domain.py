#!/usr/bin/env python3
"""
Base Data Domain

Abstract base class that every data domain (homicides, census, property, etc.)
must implement.  The MCPIntegration registry discovers and dispatches to domains
through this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd


class BaseDataDomain(ABC):
    """Abstract interface for a data domain that provides MCP tools."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        """Short identifier, e.g. 'homicides', 'census', 'property'."""
        ...

    # ------------------------------------------------------------------
    # Data lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def load_data(self, **kwargs) -> bool:
        """Load / refresh the domain's data.  Return True on success."""
        ...

    @property
    def is_loaded(self) -> bool:
        """Whether the domain has data ready to query."""
        return getattr(self, "df", None) is not None

    # ------------------------------------------------------------------
    # Tool schema — consumed by the LLM prompt builder
    # ------------------------------------------------------------------

    @abstractmethod
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return tool definitions for the LLM prompt.

        Each dict has keys: name, description, parameters (dict), required (list).
        """
        ...

    # ------------------------------------------------------------------
    # Tool dispatch — called by MCPIntegration.call_tool()
    # ------------------------------------------------------------------

    @abstractmethod
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return the raw result dict."""
        ...

    # ------------------------------------------------------------------
    # Formatting — called by MCPIntegration.format_tool_result()
    # ------------------------------------------------------------------

    @abstractmethod
    def format_result(self, result: Dict[str, Any]) -> str:
        """Format a raw result dict into a human-readable string for the LLM."""
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_tool_names(self) -> List[str]:
        """Convenience: list of tool name strings owned by this domain."""
        return [t["name"] for t in self.get_tool_definitions()]
