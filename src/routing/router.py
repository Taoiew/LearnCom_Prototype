"""Simple routing logic."""

from enum import Enum


class RouteType(str, Enum):
    """Supported route types."""

    AGENT = "agent"
    RETRIEVAL = "retrieval"


class Router:
    """Selects a route by simple keyword matching."""

    def route(self, query: str) -> RouteType:
        query_lower = query.lower()
        if "search" in query_lower or "find" in query_lower:
            return RouteType.RETRIEVAL
        return RouteType.AGENT
